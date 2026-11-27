"""Reinício do engenheiro de IA no fluxo de recuperação da API."""
import json
from types import SimpleNamespace

import engine.checkpoint as checkpoint
from api import race_manager as race_manager_module
from api.race_manager import RaceManager
from engine.coach_controller import CoachController, CommandBus


class Pipeline:
    def __init__(self, client):
        self.client = client
        self.sets = []

    def watch(self, key):
        return self

    def get(self, key):
        return self.client.get(key)

    def multi(self):
        return self

    def set(self, key, value, ex=None):
        self.sets.append((key, value))
        return self

    def publish(self, channel, payload):
        return self

    def execute(self):
        for key, value in self.sets:
            self.client.data[key] = value
        self.sets = []
        return []

    def reset(self):
        self.sets = []


class Client:
    def __init__(self, race_id):
        self.data = {
            f"race:{race_id}:checkpoint": "checkpoint",
            f"race:{race_id}:meta": json.dumps({
                "race_id": race_id,
                "num_laps": 7,
                "user_driver_id": "drv_1",
                "drivers": [{"driver_id": "drv_1", "name": "Piloto 1"}],
            }),
        }

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True

    def eval(self, script, num_keys, key, token):
        if self.data.get(key) == token:
            del self.data[key]
        return 1

    def pipeline(self, transaction=True):
        return Pipeline(self)


def test_recovery_restarts_ai_engineer_with_restored_command_bus(monkeypatch):
    race_id = "race_recovery_ai"
    client = Client(race_id)
    shared_bus = CommandBus(client, race_id)
    shared_bus._seq = 42
    coach = CoachController(object(), "drv_1", bus=shared_bus)
    restored_engine = SimpleNamespace(
        sim_ts=12.5,
        controllers={"drv_1": coach},
    )

    def fake_restore(encoded, publisher):
        assert encoded == "checkpoint"
        publisher.engine = restored_engine
        publisher.snapshot = {
            "race_id": race_id,
            "status": "running",
            "sim_ts": restored_engine.sim_ts,
            "last_tick": None,
        }
        return restored_engine

    monkeypatch.setattr(checkpoint, "restore", fake_restore)
    manager = RaceManager(client=client, provider=object(), catalog={})
    engine_threads = []
    monkeypatch.setattr(
        manager,
        "_start_engine_thread",
        lambda engine, publisher: engine_threads.append((engine, publisher)),
    )

    created = []

    class AiEngineerStub:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.started = False
            created.append(self)

        def start(self):
            self.started = True

    monkeypatch.setattr(race_manager_module, "AiEngineer", AiEngineerStub)

    manager._recover_race(race_id)

    assert len(engine_threads) == 1
    assert engine_threads[0][0] is restored_engine
    assert len(created) == 1
    ai_engineer = created[0]
    assert ai_engineer.started is True
    assert ai_engineer.kwargs["engine"] is restored_engine
    assert ai_engineer.kwargs["publisher"] is engine_threads[0][1]
    assert ai_engineer.kwargs["total_laps"] == 7
    assert ai_engineer.kwargs["user_driver_id"] == "drv_1"
    assert ai_engineer.kwargs["command_bus"] is shared_bus
    assert ai_engineer.kwargs["command_bus"]._seq == 42
    assert manager._ai_engineers[race_id] is ai_engineer
