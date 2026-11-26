"""Ain-Diab's dense historic grid must not collapse at the first bend."""
from dataclasses import replace

from api.providers.historical_f1results import HistoricalResultsProvider
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from domain import BASE_CONDITIONS, WeatherKind, WeatherModel, WeatherTransitionConfig
from engine import RuleBasedRaceController, SimulationEngine
from engine.controllers import EnvironmentState


GRID_2025 = (
    'max-verstappen', 'lando-norris', 'oscar-piastri', 'charles-leclerc',
    'lewis-hamilton', 'george-russell', 'kimi-antonelli', 'fernando-alonso',
    'lance-stroll', 'carlos-sainz', 'alexander-albon', 'pierre-gasly',
    'franco-colapinto', 'esteban-ocon', 'oliver-bearman', 'liam-lawson',
    'isack-hadjar', 'yuki-tsunoda', 'nico-hulkenberg', 'gabriel-bortoleto',
)


def make_track():
    return HistoricalResultsProvider().load('ain-diab', 1958)[0]


def test_pack_tuning_only_applies_to_the_validated_geometry():
    track = make_track()
    assert RuleBasedRaceController(track, seed=42)._ain_diab_pack_tuning
    assert not RuleBasedRaceController(replace(track, width_m=14), seed=42)._ain_diab_pack_tuning


def test_dense_pack_brakes_before_reaching_the_car_ahead():
    track = make_track()
    def command(car_count):
        controller = RuleBasedRaceController(track, seed=42)
        drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f'p{i}') for i in range(car_count)]
        states = {d.driver_id: d.initial_state() for d in drivers}
        for i, driver in enumerate(drivers):
            state = states[driver.driver_id]
            s = 300 if i == 0 else 370 if i == 1 else 100 + i * 2
            state.position_x, state.position_y = controller._point_at(s, centerline=True)
            state.heading_rad = float(controller._heading[controller._segment_at(s)])
            state.velocity_mps = 60.0 if i == 0 else 20.0
        env = EnvironmentState(20.0, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        return controller.compute_input(env, states['p0'])
    assert command(10).brake > 0.0
    assert command(2).brake == 0.0


def test_twenty_car_grid_clears_first_turn():
    track = make_track()
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=name, name=name)
               for i, name in enumerate(GRID_2025)]
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, num_laps=3,
                     random_seed=42, track_progress_laps=True)
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0.0))
    engine = SimulationEngine(config, track, drivers, weather_model=weather)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    for driver in drivers:
        engine.set_controller(driver.driver_id, controller)
    slow = {d.driver_id: 0 for d in drivers}
    longest_slow = dict(slow)
    try:
        for tick in range(600):
            engine._step_tick(0.1, 24)
            for driver in drivers:
                driver_id = driver.driver_id
                slow[driver_id] = (slow[driver_id] + 1 if tick > 100
                                   and engine.states[driver_id].velocity_mps < 1.4 else 0)
                longest_slow[driver_id] = max(longest_slow[driver_id], slow[driver_id])
        assert min(engine.race_progress_m.values()) > 800
        assert max(longest_slow.values()) <= 100  # 10 s below 5 km/h
    finally:
        engine.teardown()


def test_blocked_car_can_escape_toward_clear_grass_but_stops_for_an_obstacle():
    import math

    track = make_track()
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f'escape-{i}') for i in range(3)]
    states = {driver.driver_id: driver.initial_state() for driver in drivers}
    car, blocker, obstacle = (states[driver.driver_id] for driver in drivers)
    s = 650.0
    car.position_x, car.position_y = controller._point_at(s, 3.0, centerline=True)
    heading = float(controller._heading[controller._segment_at(s)])
    car.heading_rad = heading + math.pi / 2
    car.velocity_mps = 0.0
    blocker.position_x, blocker.position_y = controller._point_at(s + 6.0, 3.0, centerline=True)
    blocker.velocity_mps = 0.0
    obstacle.position_x, obstacle.position_y = controller._point_at(s - 100.0, centerline=True)
    for step in range(12):
        env = EnvironmentState(30.0 + step * 0.1, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        command = controller.compute_input(env, car)
    assert controller.last_authority[car.driver_id] == 'traffic-escape'
    assert command.throttle > 0.0 and command.brake == 0.0
    assert command.steering_yaw_rad == 0.0

    # A car moving into that route cancels the maneuver immediately.
    obstacle.position_x = car.position_x + 5.0 * math.cos(car.heading_rad)
    obstacle.position_y = car.position_y + 5.0 * math.sin(car.heading_rad)
    env = EnvironmentState(31.2, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
    command = controller.compute_input(env, car)
    assert controller.last_authority[car.driver_id] != 'traffic-escape'
    assert command.throttle == 0.0 and command.brake >= 0.8


def test_aligned_car_does_not_use_escape_to_overtake_queue():
    track = make_track()
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [replace(DEFAULT_DRIVERS[i], driver_id=f'queue-{i}') for i in range(2)]
    states = {driver.driver_id: driver.initial_state() for driver in drivers}
    for i, driver in enumerate(drivers):
        state = states[driver.driver_id]
        state.position_x, state.position_y = controller._point_at(650.0 + i * 6, 3.0, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(650.0)])
        state.velocity_mps = 0.0
    for step in range(15):
        env = EnvironmentState(30.0 + step * 0.1, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        controller.compute_input(env, states['queue-0'])
        assert controller.last_authority['queue-0'] != 'traffic-escape'


def test_displaced_car_moves_around_stationary_queue_in_physics():
    import math
    import pybullet as pb
    from engine.controllers import ManualController

    track = make_track()
    drivers = [replace(DEFAULT_DRIVERS[i], driver_id=f'physical-{i}') for i in range(2)]
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, track_progress_laps=True)
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0.0))
    engine = SimulationEngine(config, track, drivers, weather_model=weather)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(drivers[0].driver_id, controller)
    engine.set_controller(drivers[1].driver_id, ManualController(brake=1.0))
    s = 650.0
    heading = float(controller._heading[controller._segment_at(s)])
    client_id = engine.physics._client_id
    for i, driver in enumerate(drivers):
        x, y = controller._point_at(s + i * 6.0, 3.0, centerline=True)
        yaw = heading + (math.pi / 2 if i == 0 else 0.0)
        body = engine.handles[driver.driver_id].chassis_id
        pb.resetBasePositionAndOrientation(body, (x, y, 0.5), pb.getQuaternionFromEuler((0, 0, yaw)), physicsClientId=client_id)
        pb.resetBaseVelocity(body, (0, 0, 0), (0, 0, 0), physicsClientId=client_id)
    try:
        authorities = set()
        for _ in range(22):
            engine._step_tick(0.1, 24)
            authorities.add(controller.last_authority[drivers[0].driver_id])
        assert 'traffic-escape' in authorities
        assert engine.states[drivers[0].driver_id].velocity_mps > 1.0
        for _ in range(160):
            engine._step_tick(0.1, 24)
        assert abs(engine.race_lateral_m[drivers[0].driver_id]) < track.width_m / 2
        assert engine.states[drivers[0].driver_id].velocity_mps > 2.0
    finally:
        engine.teardown()


def test_aligned_car_chooses_free_side_and_brakes_if_it_becomes_occupied():
    track = make_track()
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f'route-{i}') for i in range(3)]
    states = {driver.driver_id: driver.initial_state() for driver in drivers}
    for i, driver in enumerate(drivers):
        state = states[driver.driver_id]
        state.position_x, state.position_y = controller._point_at(650.0 + (10 if i == 1 else -100 if i == 2 else 0), centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(650.0)])
        state.velocity_mps = 0.0
    for step in range(12):
        env = EnvironmentState(30.0 + step * 0.1, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        controller.compute_input(env, states['route-0'])
    assert controller.last_authority['route-0'] == 'traffic-avoid'
    lane = controller._style_for('route-0').queue_avoid_lane_m
    assert abs(lane) >= 3.4
    obstacle = states['route-2']
    obstacle.position_x, obstacle.position_y = controller._point_at(654.0, lane, centerline=True)
    env = EnvironmentState(31.2, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
    command = controller.compute_input(env, states['route-0'])
    assert controller.last_authority['route-0'] != 'traffic-avoid'
    assert command.throttle == 0.0 and command.brake >= 0.8


def test_aligned_car_waits_when_both_sides_are_occupied():
    track = make_track()
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f'full-{i}') for i in range(4)]
    states = {driver.driver_id: driver.initial_state() for driver in drivers}
    for i, (distance, lane) in enumerate(((0, 0), (10, 0), (8, -3.6), (8, 3.6))):
        state = states[drivers[i].driver_id]
        state.position_x, state.position_y = controller._point_at(650.0 + distance, lane, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(650.0)])
        state.velocity_mps = 0.0
    for step in range(15):
        env = EnvironmentState(30.0 + step * 0.1, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        controller.compute_input(env, states['full-0'])
        assert controller.last_authority['full-0'] != 'traffic-avoid'


def test_aligned_car_physically_passes_stationary_obstacle():
    import pybullet as pb
    from engine.controllers import ManualController

    track = make_track()
    drivers = [replace(DEFAULT_DRIVERS[i], driver_id=f'pass-{i}') for i in range(2)]
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, track_progress_laps=True)
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0.0))
    engine = SimulationEngine(config, track, drivers, weather_model=weather)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(drivers[0].driver_id, controller)
    engine.set_controller(drivers[1].driver_id, ManualController(brake=1.0))
    s = 650.0
    heading = float(controller._heading[controller._segment_at(s)])
    client_id = engine.physics._client_id
    for i, driver in enumerate(drivers):
        x, y = controller._point_at(s + i * 10.0, centerline=True)
        body = engine.handles[driver.driver_id].chassis_id
        pb.resetBasePositionAndOrientation(body, (x, y, 0.5), pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=client_id)
        pb.resetBaseVelocity(body, (0, 0, 0), (0, 0, 0), physicsClientId=client_id)
    try:
        authorities = set()
        for _ in range(150):
            engine._step_tick(0.1, 24)
            authorities.add(controller.last_authority[drivers[0].driver_id])
            assert not pb.getContactPoints(engine.handles[drivers[0].driver_id].chassis_id,
                                           engine.handles[drivers[1].driver_id].chassis_id,
                                           physicsClientId=client_id)
        assert 'traffic-avoid' in authorities
        assert engine.race_progress_m[drivers[0].driver_id] > engine.race_progress_m[drivers[1].driver_id] + 8.0
        assert abs(engine.race_lateral_m[drivers[0].driver_id]) <= track.width_m / 2
    finally:
        engine.teardown()


def test_aligned_car_chooses_the_unoccupied_side():
    track = make_track()
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f'side-{i}') for i in range(3)]
    states = {driver.driver_id: driver.initial_state() for driver in drivers}
    for i, (distance, lane) in enumerate(((0, 0), (10, 0), (8, -3.6))):
        state = states[drivers[i].driver_id]
        state.position_x, state.position_y = controller._point_at(650.0 + distance, lane, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(650.0)])
        state.velocity_mps = 0.0
    for step in range(12):
        env = EnvironmentState(30.0 + step * 0.1, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        controller.compute_input(env, states['side-0'])
    assert controller.last_authority['side-0'] == 'traffic-avoid'
    assert controller._style_for('side-0').queue_avoid_lane_m > 0


def test_avoidance_stops_if_obstacle_moves_into_chosen_lane():
    track = make_track()
    controller = RuleBasedRaceController(track, seed=42)
    drivers = [replace(DEFAULT_DRIVERS[i], driver_id=f'moving-{i}') for i in range(2)]
    states = {driver.driver_id: driver.initial_state() for driver in drivers}
    for i, driver in enumerate(drivers):
        state = states[driver.driver_id]
        state.position_x, state.position_y = controller._point_at(650.0 + i * 10, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(650.0)])
        state.velocity_mps = 0.0
    for step in range(12):
        env = EnvironmentState(30.0 + step * 0.1, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
        controller.compute_input(env, states['moving-0'])
    assert controller.last_authority['moving-0'] == 'traffic-avoid'
    lane = controller._style_for('moving-0').queue_avoid_lane_m
    states['moving-1'].position_x, states['moving-1'].position_y = controller._point_at(660.0, lane, centerline=True)
    env = EnvironmentState(31.2, 0, BASE_CONDITIONS[WeatherKind.DRY], track, states)
    command = controller.compute_input(env, states['moving-0'])
    assert command.throttle == 0 and command.brake >= 0.8
