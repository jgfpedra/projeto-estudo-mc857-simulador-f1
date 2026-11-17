"""Calibração limitada às geometrias de Monza verificadas."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import Track
from engine import RuleBasedRaceController, SimulationEngine


def _track(source):
    if source == "frozen":
        return load_live_track("monza", 2024)
    # Snapshot OpenF1: corrida 2024, sessão 9590, piloto 1, volta 43.
    data = json.loads((Path(__file__).parent / "fixtures" / "monza_openf1_2024.json").read_text())
    return Track.from_waypoints(**data)


@pytest.mark.parametrize("source,limit", [("frozen", 100.0), ("openf1", 120.0)])
def test_monza_flying_lap_improves_without_leaving_track(source, limit):
    track = _track(source)
    driver = DEFAULT_DRIVERS[0]
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, track_progress_laps=True,
                     num_laps=3, tyre_life_threshold=0, fuel_threshold_kg=0)
    engine = SimulationEngine(config, track, [driver])
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(driver.driver_id, controller)
    try:
        assert controller._monza_calibrated
        max_lateral = 0.0
        for _ in range(3500):
            engine._step_tick(.1, 24)
            max_lateral = max(max_lateral, abs(engine.race_lateral_m.get(driver.driver_id, 0)))
            if engine.states[driver.driver_id].lap >= 2:
                break
        else:
            pytest.fail("O piloto não completou duas voltas")
        assert engine.states[driver.driver_id].last_lap_time_s < limit
        assert max_lateral <= track.width_m / 2
    finally:
        engine.teardown()


def test_monza_tuning_requires_the_validated_track_geometry_and_width():
    track = _track("frozen")
    track.width_m += 1
    assert not RuleBasedRaceController(track)._monza_calibrated
    track.width_m -= 1
    x, y = track.waypoints[0]
    track.waypoints[0] = (x + .01, y)
    assert not RuleBasedRaceController(track)._monza_calibrated
