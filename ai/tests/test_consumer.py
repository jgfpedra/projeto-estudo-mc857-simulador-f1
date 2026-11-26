import json
from unittest.mock import MagicMock, Mock

from consumer import consume, publish_suggestion


def test_suggestion_is_published_to_its_race_and_driver(monkeypatch):
    client = Mock()
    client.get.return_value = json.dumps({"status": "running"})
    monkeypatch.setattr("consumer.call_model", lambda prompt: {
        "ok": True,
        "response": json.dumps({
            "aviso": "Pneus gastos", "urgencia": "media",
            "previsao": {"pit_stop_recomendado": True, "volta_estimada": 3,
                         "composto_sugerido": "MEDIUM"},
        }),
    })
    publish_suggestion(client, "race:race_1:events", "race_1", "driver", 2, 11.0, "estado")
    channel, encoded = client.publish.call_args.args
    data = json.loads(encoded)
    assert channel == "race:race_1:events"
    assert (data["type"], data["race_id"], data["driver_id"]) == (
        "ai_suggestion", "race_1", "driver")
    assert data["aviso"] == "Pneus gastos"


def test_finished_race_does_not_receive_delayed_suggestion(monkeypatch):
    client = Mock()
    client.get.return_value = json.dumps({"status": "finished"})
    monkeypatch.setattr("consumer.call_model", lambda prompt: {"ok": False, "error": "teste"})
    publish_suggestion(client, "race:r:events", "r", "d", 1, 10, "estado")
    client.publish.assert_not_called()


def test_consumer_subscribes_and_uses_configured_driver(monkeypatch):
    client = MagicMock()
    client.get.return_value = json.dumps({"user_driver_id": "chosen", "drivers": [
        {"driver_id": "first"}, {"driver_id": "chosen"}]})
    pubsub = client.pubsub.return_value.__enter__.return_value
    pubsub.listen.return_value = iter([
        {"type": "pmessage", "channel": "race:r:events", "data": json.dumps({
            "type": "tick", "sim_ts": 10, "lap": 1,
            "positions": [{"driver_id": "chosen", "position_xy": [0, 0]}],
        })},
        {"type": "pmessage", "channel": "race:r:events", "data": json.dumps({
            "type": "ai_suggestion", "sim_ts": 11,
        })},
    ])
    publisher = Mock()
    monkeypatch.setattr("consumer.publish_suggestion", publisher)
    consume(client)
    pubsub.psubscribe.assert_called_once_with("race:*:events")
    publisher.assert_called_once()
    assert publisher.call_args.args[2:4] == ("r", "chosen")
