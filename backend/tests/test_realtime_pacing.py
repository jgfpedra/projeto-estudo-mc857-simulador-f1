"""O relógio de execução compensa atrasos sem saltar passos físicos."""
from dataclasses import replace

import pytest

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from engine import SimulationEngine


@pytest.mark.parametrize("work,expected", [
    ([.04, .16, .04, .04], .4),
    ([.16, .16, .16, .16], .64),
])
def test_realtime_pacing_recovers_transient_delay_but_never_skips_ticks(monkeypatch, work, expected):
    from engine import simulation

    class Clock:
        now = 0.0
        def monotonic(self): return self.now
        def sleep(self, duration): self.now += duration

    clock = Clock()
    monkeypatch.setattr(simulation.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(simulation.time, "sleep", clock.sleep)
    track = load_live_track("monza", 2024)
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=True),
                              track, [DEFAULT_DRIVERS[0]])
    engine.setup()
    durations = iter(work)
    steps = []
    def step(dt, substeps):
        clock.now += next(durations)
        engine.sim_ts += dt
        steps.append((dt, substeps))
        if len(steps) == len(work): engine.race_finished = True
    monkeypatch.setattr(engine, "_step_tick", step)
    try:
        engine.run()
        assert clock.now == pytest.approx(expected)
        assert steps == [(.1, 24)] * len(work)
        assert engine.sim_ts == pytest.approx(.4)
    finally:
        engine.teardown()


def test_projection_is_reused_for_an_unchanged_frame_but_not_after_movement(monkeypatch):
    from dataclasses import replace as change
    from domain.weather import BASE_CONDITIONS, WeatherKind
    from engine import RuleBasedRaceController
    from engine.controllers import EnvironmentState

    track = load_live_track("monza", 2024)
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [change(DEFAULT_DRIVERS[0], driver_id=f"driver-{i}") for i in range(3)]
    states = {d.driver_id: d.initial_state() for d in drivers}
    for i, state in enumerate(states.values()):
        state.position_x, state.position_y = track.waypoints[i * 5]
        state.velocity_mps = 10.0
    env = EnvironmentState(sim_ts=1, lap=0, weather=BASE_CONDITIONS[WeatherKind.DRY],
                           track=track, all_driver_states=states)
    calls = []
    project = controller._project
    def observed(driver_id, x, y):
        calls.append(driver_id)
        return project(driver_id, x, y)
    monkeypatch.setattr(controller, "_project", observed)
    for state in states.values(): controller.compute_input(env, state)
    assert sorted(calls) == sorted(states)
    states[drivers[0].driver_id].position_x += 1.0
    controller.compute_input(env, states[drivers[0].driver_id])
    assert calls.count(drivers[0].driver_id) == 2
