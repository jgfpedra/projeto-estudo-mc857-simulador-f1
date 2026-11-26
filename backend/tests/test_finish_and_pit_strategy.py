"""Checkered flag and pit strategy behavior at the engine boundaries."""
from dataclasses import replace
import math

import pybullet as pb
import pytest
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import BASE_CONDITIONS, TyreCompound, WeatherKind, WeatherModel, WeatherTransitionConfig
from engine import RuleBasedRaceController, SimulationEngine
from engine.pit_strategy import decide_pit
from engine.publisher import Publisher

class Events(Publisher):
    def __init__(self): self.events = []
    def publish(self, event): self.events.append(event.to_dict())

def make_engine(n=3, laps=3):
    track = load_live_track('interlagos', 2023)
    drivers = [replace(DEFAULT_DRIVERS[0], driver_id=chr(ord('A')+i), name=chr(ord('A')+i)) for i in range(n)]
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0.0))
    events = Events()
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      num_laps=laps, track_progress_laps=True), track, drivers,
                              publisher=events, weather_model=weather)
    engine.setup()
    return engine, drivers, events

def test_checkered_waits_for_every_driver_including_lapped_car():
    engine, (leader, follower, lapped), events = make_engine()
    try:
        length = engine._race_track_length
        engine.states['A'].lap = 2
        engine.states['B'].lap = 2
        engine.states['C'].lap = 1
        engine.race_progress_m.update({'A': 2.99*length, 'B': 2.98*length, 'C': 1.99*length})
        engine.sim_ts = 100
        engine._complete_lap(leader)
        assert not engine.race_finished and engine.checkered_sim_ts == 100
        assert engine.finished_drivers['A'] == (3, 100)
        engine.sim_ts = 101
        engine._complete_lap(lapped)
        assert not engine.race_finished
        assert [d.driver_id for d in engine.ranked_drivers()] == ['A', 'B', 'C']
        engine.sim_ts = 102
        engine._complete_lap(follower)
        assert engine.race_finished
        engine._complete_lap(leader)
        assert engine.states['A'].lap == 3
        engine._publish_race_end()
        result = events.events[-1]['final_classification']
        assert [x['driver_id'] for x in result] == ['A', 'B', 'C']
        assert [x['laps_completed'] for x in result] == [3, 3, 2]
        assert all(x['finished'] for x in result)
    finally:
        engine.teardown()

def test_timeout_classification_marks_unfinished_drivers():
    engine, drivers, events = make_engine(n=2)
    try:
        engine.states['A'].lap = 2
        engine.sim_ts = 100
        engine._complete_lap(drivers[0])
        engine._publish_race_end()
        result = {item['driver_id']: item for item in events.events[-1]['final_classification']}
        assert result['A']['finished'] and not result['B']['finished']
    finally:
        engine.teardown()

def test_weather_changes_once_per_race_lap_not_per_driver():
    engine, drivers, _ = make_engine(n=2)
    calls = []
    def step(lap):
        calls.append(lap)
        return engine.weather_model.current
    engine.weather_model.step = step
    try:
        engine._complete_lap(drivers[0])
        engine._complete_lap(drivers[1])
        assert calls == [2]
    finally:
        engine.teardown()

@pytest.mark.parametrize('kind,rainfall,expected', [
    (WeatherKind.DAMP, 0.0, TyreCompound.INTERMEDIATE),
    (WeatherKind.WET, 0.5, TyreCompound.INTERMEDIATE),
    (WeatherKind.WET, 3.0, TyreCompound.WET),
])
def test_slicks_are_changed_when_rain_arrives(kind, rainfall, expected):
    driver = DEFAULT_DRIVERS[0]
    state = driver.initial_state()
    weather = replace(BASE_CONDITIONS[kind], rainfall=rainfall)
    decision = decide_pit(state, driver, weather, 4.3, 8, 6, 18)
    assert decision is not None and decision.reason == 'weather' and decision.compound == expected

def test_forecast_wear_and_fuel_and_no_unnecessary_final_lap_stop():
    driver = DEFAULT_DRIVERS[0]
    state = driver.initial_state()
    dry = BASE_CONDITIONS[WeatherKind.DRY]
    state.tyre.tyre_life = 22
    decision = decide_pit(state, driver, dry, 4.3, 5, 6, 18)
    assert decision and decision.reason == 'tyres' and decision.compound == TyreCompound.SOFT
    assert decide_pit(state, driver, dry, 4.3, .5, 6, 18) is None
    state.car.fuel_kg = .1
    decision = decide_pit(state, driver, dry, 4.3, .5, 6, 18)
    assert decision and decision.reason == 'fuel' and decision.fuel_kg > 0

def test_weather_retarget_and_manual_driver_control():
    engine, drivers, events = make_engine(n=2, laps=10)
    try:
        auto, user = drivers
        engine.user_driver_id = user.driver_id
        engine.weather_model.current = BASE_CONDITIONS[WeatherKind.WET]
        engine._step_tick(.1, 24)
        assert engine._pit_requests['A']['compound'] == TyreCompound.WET
        assert 'B' not in engine._pit_requests
        engine.weather_model.current = BASE_CONDITIONS[WeatherKind.DAMP]
        engine._step_tick(.1, 24)
        assert engine._pit_requests['A']['compound'] == TyreCompound.INTERMEDIATE
        assert any(e['type'] == 'pit_requested' and e['source'] == 'automatic' for e in events.events)
        engine.request_pit_stop('B', TyreCompound.HARD)
        engine._step_tick(.1, 24)
        assert engine._pit_requests['B']['compound'] == TyreCompound.HARD
        assert engine._pit_requests['B']['source'] == 'user'
    finally:
        engine.teardown()


def test_same_tick_finish_keeps_crossing_order():
    engine, (leader, follower), _ = make_engine(n=2)
    try:
        engine.states['A'].lap = engine.states['B'].lap = 2
        engine.sim_ts = 100
        # Grid order is A, B, but B is ahead at the finish.
        engine._complete_lap(follower)
        engine._complete_lap(leader)
        assert [d.driver_id for d in engine.ranked_drivers()] == ['B', 'A']
    finally:
        engine.teardown()


def test_bot_enters_and_changes_tyres_when_rain_starts():
    engine, (driver,), events = make_engine(n=1, laps=10)
    try:
        engine.set_controller(driver.driver_id, RuleBasedRaceController(engine.track, seed=42))
        engine.weather_model.current = BASE_CONDITIONS[WeatherKind.WET]
        a, b = engine.track.pit.waypoints[:2]
        heading = math.atan2(b[1] - a[1], b[0] - a[0])
        cid = engine.physics._client_id
        chassis = engine.handles[driver.driver_id].chassis_id
        pb.resetBasePositionAndOrientation(chassis, (a[0], a[1], .5),
            pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=cid)
        pb.resetBaseVelocity(chassis, (20 * math.cos(heading), 20 * math.sin(heading), 0), physicsClientId=cid)
        engine.last_pos[driver.driver_id] = a
        engine.prev_waypoint_idx[driver.driver_id] = engine.track.pit.entry_waypoint
        engine._update_race_progress(.1)
        for _ in range(550):
            engine._step_tick(.1, 24)
            if engine.states[driver.driver_id].pit_stop_done:
                break
        assert engine.states[driver.driver_id].pit_stop_done == 1
        assert engine.states[driver.driver_id].tyre.model.compound == TyreCompound.WET
        assert any(e['type'] == 'pit_requested' and e['source'] == 'automatic' for e in events.events)
        assert any(e['type'] == 'pit_stop' for e in events.events)
    finally:
        engine.teardown()


def test_weather_request_retargets_if_it_dries_but_fuel_still_requires_stop():
    engine, (driver,), _ = make_engine(n=1, laps=10)
    try:
        state = engine.states[driver.driver_id]
        state.car.fuel_kg = 1.0
        engine.weather_model.current = BASE_CONDITIONS[WeatherKind.WET]
        engine._step_tick(.1, 24)
        assert engine._pit_requests[driver.driver_id]['compound'] == TyreCompound.WET
        engine.weather_model.current = BASE_CONDITIONS[WeatherKind.DRY]
        engine._step_tick(.1, 24)
        request = engine._pit_requests[driver.driver_id]
        assert request['reason'] == 'fuel' and request['compound'] in (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)
    finally:
        engine.teardown()


def test_complete_race_continues_until_second_car_crosses():
    engine, drivers, events = make_engine(n=2, laps=1)
    controller = RuleBasedRaceController(engine.track, seed=42)
    for driver in drivers:
        engine.set_controller(driver.driver_id, controller)
    try:
        engine.run()
        assert len(engine.finished_drivers) == 2
        assert engine.sim_ts > engine.checkered_sim_ts
        classification = next(e['final_classification'] for e in events.events if e['type'] == 'race_end')
        assert all(item['finished'] and item['laps_completed'] == 1 for item in classification)
        assert classification[0]['finish_time_s'] < classification[1]['finish_time_s']
    finally:
        engine.teardown()


def test_dry_pit_plans_vary_by_driver_but_remain_reproducible_and_weather_safe():
    drivers = [replace(DEFAULT_DRIVERS[0], driver_id=f'plan-{i}') for i in range(24)]
    dry = BASE_CONDITIONS[WeatherKind.DRY]
    wet = BASE_CONDITIONS[WeatherKind.WET]
    def decisions(weather, seed):
        result = []
        for driver in drivers:
            state = driver.initial_state()
            state.car.fuel_kg = 0.1
            result.append(decide_pit(state, driver, weather, 4.3, 8, 6, 18, strategy_seed=seed).compound)
        return result
    dry_plans = decisions(dry, 42)
    assert set(dry_plans) == {TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD}
    assert dry_plans == decisions(dry, 42)
    assert dry_plans != decisions(dry, 43)
    assert set(decisions(wet, 42)) == {TyreCompound.WET}


def test_long_dry_race_bots_plan_different_stops_and_change_compound():
    drivers = [replace(DEFAULT_DRIVERS[0], driver_id=f'plan-{i}') for i in range(20)]
    dry = BASE_CONDITIONS[WeatherKind.DRY]
    windows = []
    for driver in drivers:
        state = driver.initial_state()
        assert decide_pit(state, driver, dry, 4.3, 9, 6, 18, strategy_seed=42, race_laps=10) is None
        for completed in range(2, 9):
            decision = decide_pit(state, driver, dry, 4.3, 10-completed, 6, 18,
                                  strategy_seed=42, race_laps=10)
            if decision:
                assert decision.reason == 'strategy'
                assert decision.compound != state.tyre.model.compound
                windows.append(completed)
                break
        else:
            pytest.fail('Bot did not plan a stop')
        state.pit_stop_done = 1
        assert decide_pit(state, driver, dry, 4.3, 3, 6, 18, strategy_seed=42, race_laps=10) is None
    assert len(set(windows)) >= 3
    short = drivers[0].initial_state()
    assert decide_pit(short, drivers[0], dry, 4.3, 3, 6, 18, strategy_seed=42, race_laps=5) is None


def test_early_fuel_stop_still_uses_a_different_dry_compound():
    driver = replace(DEFAULT_DRIVERS[0], driver_id='early-stop')
    state = driver.initial_state()
    state.car.fuel_kg = 0.1
    decision = decide_pit(state, driver, BASE_CONDITIONS[WeatherKind.DRY], 4.3, 9, 6, 18,
                          strategy_seed=42, race_laps=10)
    assert decision.reason == 'fuel'
    assert decision.compound != state.tyre.model.compound
