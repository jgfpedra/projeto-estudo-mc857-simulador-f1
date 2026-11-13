"""Race order follows circuit position, including cars yet to complete a lap."""

from backend.domain import BASE_CONDITIONS, CarSpecs, Driver, Track, WeatherKind, WeatherModel
from backend.engine import RuleBasedRaceController, SimulationConfig, SimulationEngine
from backend.engine.controllers import EnvironmentState
from backend.model_train.f1_env import resolve_track
from backend.scripts.simulation import run_race_10_cars


class FakePhysics:
    def __init__(self, positions):
        self.positions = positions

    def get_state(self, handle):
        x, y = self.positions[handle]
        return {"x": x, "y": y, "speed_mps": 0.0}


class CapturePublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def test_race_randomization_defaults_and_explicit_replay(monkeypatch):
    monkeypatch.setattr(run_race_10_cars.secrets, "randbits", lambda bits: 1234)
    resolve = run_race_10_cars.resolve_race_randomization
    assert resolve(None, None, True) == (1234, "grid")
    assert resolve(0, "off", True) == (0, "off")
    assert resolve(None, None, False) == (0, "off")


def make_engine():
    track = Track.from_waypoints("square", [(0, 0), (100, 0), (100, 100), (0, 100)])
    specs = CarSpecs(name="car", power_kw=740, mass_kg=798, fuel_capacity_kg=110)
    drivers = [Driver(driver_id=name, name=name, car_specs=specs) for name in ("A", "B")]
    publisher = CapturePublisher()
    engine = SimulationEngine(
        SimulationConfig(gui=False, track_progress_laps=True), track, drivers,
        publisher=publisher,
    )
    engine.states = {driver.driver_id: driver.initial_state() for driver in drivers}
    engine.handles = {driver.driver_id: driver.driver_id for driver in drivers}
    engine.physics = FakePhysics({"A": (10, 0), "B": (20, 0)})
    return engine, publisher


def test_race_order_and_final_classification_follow_passes():
    engine, publisher = make_engine()
    engine._update_race_progress(0.1)
    assert [driver.driver_id for driver in engine.ranked_drivers()] == ["B", "A"]

    engine.physics.positions.update({"A": (25, 0), "B": (21, 0)})
    engine._update_race_progress(0.1)
    engine._publish_position_update(0)
    assert [item["driver_id"] for item in publisher.events[-1].positions] == ["A", "B"]
    engine._publish_race_end()
    assert [item["driver_id"] for item in publisher.events[-1].final_classification] == ["A", "B"]


def test_progress_wraps_at_start_line_and_laps_use_circuit_progress():
    engine, _ = make_engine()
    engine.physics.positions["A"] = (0, 10)
    engine._update_race_progress(0.1)
    assert engine.race_progress_m["A"] == -10.0
    engine.physics.positions["A"] = (5, 0)
    engine._update_race_progress(0.1)
    assert engine.race_progress_m["A"] == 5.0

    engine.last_pos = dict(engine.physics.positions)
    engine.cum_dist_m = {"A": 0.0, "B": 0.0}
    completed = []
    engine._complete_lap = lambda driver: completed.append(driver.driver_id)
    engine.cum_dist_m["A"] = 2.0 * engine._race_track_length
    engine._check_lap_completion()
    assert completed == []

    engine.race_progress_m["A"] = engine._race_track_length + 1.0
    engine._check_lap_completion()
    assert completed == ["A"]


def test_overtake_stays_active_until_opponent_is_behind():
    track = resolve_track("interlagos")
    controller = RuleBasedRaceController(track, seed=42)
    specs = CarSpecs(name="car", power_kw=740, mass_kg=798, fuel_capacity_kg=110)
    follower, opponent = [Driver(driver_id=name, name=name, car_specs=specs).initial_state()
                          for name in ("A", "B")]

    def place(state, s, lateral=0.0):
        state.position_x, state.position_y = controller._point_at(s, lateral, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(s)])

    place(follower, 500.0)
    place(opponent, 520.0)
    follower.velocity_mps, opponent.velocity_mps = 30.0, 25.0
    env = EnvironmentState(0.0, 0, WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY]).current,
                           track, {"A": follower, "B": opponent})
    controller.compute_input(env, follower)
    assert controller._styles["A"].avoid_target_id == "B"

    # Moving alongside removes the car from the narrow blocker corridor.
    place(follower, 500.0, lateral=4.0)
    env.sim_ts = 0.1
    controller.compute_input(env, follower)
    assert controller._styles["A"].avoid_target_id == "B"

    place(follower, 530.0, lateral=4.0)
    env.sim_ts = 0.2
    controller.compute_input(env, follower)
    assert controller._styles["A"].avoid_target_id is None


def test_driver_rhythm_repeats_for_the_same_seed():
    track = resolve_track("interlagos")
    specs = CarSpecs(name="car", power_kw=740, mass_kg=798, fuel_capacity_kg=110)
    state = Driver(driver_id="A", name="A", car_specs=specs).initial_state()
    controllers = [RuleBasedRaceController(track, seed=seed) for seed in (42, 42, 43)]
    state.position_x, state.position_y = controllers[0]._point_at(500.0, centerline=True)
    state.heading_rad = float(controllers[0]._heading[controllers[0]._segment_at(500.0)])
    state.velocity_mps = 30.0
    env = EnvironmentState(0.0, 0, WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY]).current,
                           track, {"A": state})
    for controller in controllers:
        controller.compute_input(env, state)
    targets = [controller._styles["A"].form_target for controller in controllers]
    assert 0.965 <= targets[0] <= 1.0
    assert targets[0] == targets[1]
    assert targets[0] != targets[2]


def test_seeded_start_reaction_holds_then_releases_throttle():
    track = resolve_track("interlagos")
    controller = RuleBasedRaceController(track, seed=123)
    specs = CarSpecs(name="car", power_kw=740, mass_kg=798, fuel_capacity_kg=110)
    state = Driver(driver_id="A", name="A", car_specs=specs).initial_state()
    state.position_x, state.position_y = controller._point_at(500.0, centerline=True)
    state.heading_rad = float(controller._heading[controller._segment_at(500.0)])
    state.velocity_mps = 0.0
    env = EnvironmentState(0.0, 0, WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY]).current,
                           track, {"A": state})
    assert controller.compute_input(env, state).throttle == 0.0
    assert 0.05 <= controller._styles["A"].start_reaction_s <= 0.75
    env.sim_ts = 1.0
    assert controller.compute_input(env, state).throttle > 0.0


def test_overtake_waits_when_both_sides_are_occupied():
    track = resolve_track("interlagos")
    controller = RuleBasedRaceController(track, seed=42)
    specs = CarSpecs(name="car", power_kw=740, mass_kg=798, fuel_capacity_kg=110)
    states = {name: Driver(driver_id=name, name=name, car_specs=specs).initial_state()
              for name in ("A", "B", "C", "D")}
    for name, s, lateral in (("A", 500.0, 0.0), ("B", 520.0, 0.0),
                             ("C", 490.0, -3.0), ("D", 490.0, 3.0)):
        state = states[name]
        state.position_x, state.position_y = controller._point_at(s, lateral, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(s)])
        state.velocity_mps = 25.0 if name == "B" else 30.0
    env = EnvironmentState(0.0, 0, WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY]).current,
                           track, states)
    controller.compute_input(env, states["A"])
    assert controller._styles["A"].avoid_target_id is None


def test_slipstream_requires_fast_aligned_cars():
    points = [(x, 0) for x in range(0, 201, 10)] + [(200, 100), (0, 100)]
    track = Track.from_waypoints("straight", points)
    specs = CarSpecs(name="car", power_kw=740, mass_kg=798, fuel_capacity_kg=110)
    drivers = [Driver(driver_id=name, name=name, car_specs=specs) for name in ("A", "B")]
    engine = SimulationEngine(SimulationConfig(gui=False), track, drivers)
    engine.states = {driver.driver_id: driver.initial_state() for driver in drivers}
    follower, leader = engine.states["A"], engine.states["B"]
    follower.position_x, follower.position_y = 50.0, 0.0
    leader.position_x, leader.position_y = 70.0, 0.0
    follower.heading_rad = leader.heading_rad = 0.0
    follower.velocity_mps = leader.velocity_mps = 60.0
    engine.prev_waypoint_idx = {"A": 5, "B": 7}
    factors = engine._compute_aero_drag_multipliers()
    assert factors["A"] < 1.0
    assert factors["B"] == 1.0

    leader.position_x = 90.0  # vácuo ainda atua a 40 m na reta
    assert engine._compute_aero_drag_multipliers()["A"] < 1.0
    leader.position_x = 70.0
    leader.position_y = 3.0
    assert engine._compute_aero_drag_multipliers()["A"] == 1.0
    leader.position_y = 0.0
    follower.velocity_mps = 10.0
    assert engine._compute_aero_drag_multipliers()["A"] == 1.0
