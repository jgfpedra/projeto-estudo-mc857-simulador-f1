import json

import redis_listener


class FakePubSub:
    def __init__(self, events):
        self.events = events

    def subscribe(self, _channel):
        pass

    def psubscribe(self, _pattern):
        pass

    def listen(self):
        for event in self.events:
            yield {
                "type": "message",
                "channel": "race:race_test:events",
                "data": json.dumps(event),
            }


class FakeRedis:
    def __init__(self, events):
        self.pubsub_client = FakePubSub(events)
        self.meta = {
            "race_id": "race_test",
            "followed_driver_id": "drv_02",
            "track": {"name": "Interlagos"},
        }
        self.published = []

    def pubsub(self):
        return self.pubsub_client

    def get(self, key):
        if key == "race:race_test:meta":
            return json.dumps(self.meta)
        return None

    def publish(self, channel, data):
        self.published.append((channel, data))


def test_listener_envia_historico_e_classificacao_ao_debrief(monkeypatch):
    events = [
        {"type": "race_start", "race_id": "race_test", "sim_ts": 0.0, "lap": 0},
        {"type": "pit_stop", "race_id": "race_test", "sim_ts": 20.0, "lap": 1,
         "driver_id": "drv_02", "new_compound": "MEDIUM"},
        {"type": "ai_command", "race_id": "race_test", "sim_ts": 21.0, "lap": 1,
         "driver_id": "drv_02", "command": "conserve", "reason": "Pneus desgastados"},
        {"type": "race_end", "race_id": "race_test", "sim_ts": 60.0, "total_time_s": 60.0,
         "final_classification": [
             {"position": 1, "driver_id": "drv_02", "laps_completed": 3},
         ]},
    ]
    client = FakeRedis(events)
    captured = {}

    monkeypatch.setattr(redis_listener.redis, "Redis", lambda **_kwargs: client)
    monkeypatch.setattr(redis_listener, "warm_up", lambda: None)
    monkeypatch.setattr(redis_listener, "start_periodic_flush", lambda **_kwargs: None)
    monkeypatch.setattr(
        redis_listener,
        "call_model",
        lambda *_args, **_kwargs: {"ok": False, "error": "offline", "elapsed": 0.0},
    )

    def capture_debrief(**kwargs):
        captured.update(kwargs)
        return {"race_id": kwargs["race_id"]}

    monkeypatch.setattr(redis_listener, "generate_and_save_debrief", capture_debrief)
    redis_listener.run_listener("race_test", "drv_02")

    assert captured["race_id"] == "race_test"
    assert captured["race_meta"]["track"]["name"] == "Interlagos"
    assert captured["classification"][0]["driver_id"] == "drv_02"
    assert [event["type"] for event in captured["events"]] == [
        "race_start", "pit_stop", "ai_command", "race_end",
    ]
    assert captured["ai_commands"] == [events[2]]
    assert captured["stats"]["total_time_s"] == 60.0
    assert captured["redis_client"] is client
