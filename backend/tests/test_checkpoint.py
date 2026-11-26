from dataclasses import replace
from types import SimpleNamespace

import pybullet as pb
import pytest

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import TyreCompound
from engine import SimulationEngine, RuleBasedRaceController
from engine.checkpoint import capture, restore


class Publisher:
    def __init__(self):
        self.snapshot, self.timing, self.collisions = {'last_tick': None}, {}, {}
    def publish(self, event): pass
    def flush(self): pass
    def close(self): pass


def test_checkpoint_restores_physics_pit_weather_and_controller():
    track = load_live_track('interlagos', 2023)
    driver = DEFAULT_DRIVERS[0]
    publisher = Publisher()
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False), track, [driver], publisher)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(driver.driver_id, controller)
    restored = None
    try:
        engine.race_started = True
        for _ in range(10): engine._step_tick(.1, 24)
        state = engine.states[driver.driver_id]
        state.tyre.tyre_life = 51.2
        engine._pit_requests[driver.driver_id] = {'compound': TyreCompound.WET, 'fuel': 0, 'serviced': False}
        engine.pit_controller.progress[driver.driver_id] = 15.0
        cid = engine.physics._client_id
        expected = pb.getBasePositionAndOrientation(engine.handles[driver.driver_id].chassis_id, physicsClientId=cid)
        data = capture(engine, publisher)
        restored = restore(data, Publisher())
        assert restored.sim_ts == pytest.approx(engine.sim_ts)
        assert restored.states[driver.driver_id].tyre.tyre_life == 51.2
        assert restored._pit_requests[driver.driver_id]['compound'] == TyreCompound.WET
        assert restored.pit_controller.progress[driver.driver_id] == 15.0
        actual = pb.getBasePositionAndOrientation(restored.handles[driver.driver_id].chassis_id, physicsClientId=restored.physics._client_id)
        assert actual[0] == pytest.approx(expected[0])
        assert actual[1] == pytest.approx(expected[1])
        restored._step_tick(.1, 24)
        assert restored.sim_ts > engine.sim_ts
    finally:
        if restored: restored.teardown()
        engine.teardown()
