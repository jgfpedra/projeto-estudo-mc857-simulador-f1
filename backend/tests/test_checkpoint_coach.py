from dataclasses import replace

import pytest

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from engine import SimulationEngine, RuleBasedRaceController
from engine.checkpoint import capture, restore
from engine.coach_controller import CoachController


class Publisher:
    def __init__(self, client=None, race_id='race-test'):
        self.snapshot, self.timing, self.collisions = {'last_tick': None}, {}, {}
        self.client, self.race_id = client, race_id
    def publish(self, event): pass
    def flush(self): pass
    def close(self): pass


class FakeClient:
    """Só o necessário para o CommandBus ler/escrever a sequência."""
    def __init__(self):
        self.data = {}
    def get(self, key): return self.data.get(key)
    def set(self, key, value): self.data[key] = value
    def setex(self, key, ttl, value): self.data[key] = value


def _engine_with_coaches(drivers, base, publisher):
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False),
                              load_live_track('interlagos', 2023), drivers, publisher)
    engine.setup()
    for driver in drivers:
        engine.set_controller(driver.driver_id, CoachController(base, driver.driver_id, publisher=publisher))
    return engine


def test_checkpoint_accepts_shared_coach_controllers_and_restores_them():
    drivers = DEFAULT_DRIVERS[:2]
    client = FakeClient()
    publisher = Publisher(client)
    track = load_live_track('interlagos', 2023)
    base = RuleBasedRaceController(track, seed=7)
    engine = _engine_with_coaches(drivers, base, publisher)
    first = drivers[0].driver_id
    engine.race_started = True
    for _ in range(5):
        engine._step_tick(.1, 24)
    # Definido depois de avançar: o próprio coach recalcula _off_track a cada tick.
    coach = engine.controllers[first]
    coach._last_seq, coach._last_command, coach._off_track = 5, 'throttle', True

    restored = None
    try:
        data = capture(engine, publisher)  # antes: ValueError com CoachController
        restored = restore(data, Publisher(client))
        restored_coach = restored.controllers[first]
        assert isinstance(restored_coach, CoachController)
        assert restored_coach.base is restored.controllers[drivers[1].driver_id].base
        assert restored_coach._last_seq == 5
        assert restored_coach._last_command == 'throttle'
        assert restored_coach._off_track is True
        assert restored_coach.bus._seq >= 5
        assert restored.sim_ts == pytest.approx(engine.sim_ts)
        restored._step_tick(.1, 24)
    finally:
        if restored: restored.teardown()
        engine.teardown()


def test_checkpoint_rejects_coaches_with_different_base_controllers():
    drivers = DEFAULT_DRIVERS[:2]
    publisher = Publisher(FakeClient())
    track = load_live_track('interlagos', 2023)
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False), track, drivers, publisher)
    engine.setup()
    engine.set_controller(drivers[0].driver_id, CoachController(RuleBasedRaceController(track, seed=1), drivers[0].driver_id))
    engine.set_controller(drivers[1].driver_id, CoachController(RuleBasedRaceController(track, seed=2), drivers[1].driver_id))
    try:
        with pytest.raises(ValueError, match='controlador por regras compartilhado'):
            capture(engine, publisher)
    finally:
        engine.teardown()
