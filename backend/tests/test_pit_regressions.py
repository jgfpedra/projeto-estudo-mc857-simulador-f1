"""Regressões de direção e desgaste durante a passagem física pelos boxes."""
import math
from dataclasses import replace

import pybullet as pb
import pytest

from api.providers.historical_f1results import HistoricalResultsProvider
from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import TyreCompound
from engine import RuleBasedRaceController, SimulationEngine


def test_tyre_fitted_before_the_line_only_ages_for_the_distance_driven():
    track = load_live_track("interlagos", 2023)
    driver = DEFAULT_DRIVERS[0]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      track_progress_laps=True, num_laps=3), track, [driver])
    engine.setup()
    try:
        engine.race_progress_m[driver.driver_id] = engine._race_track_length * .9
        engine._perform_pit(driver, TyreCompound.MEDIUM, 0)
        state = engine.states[driver.driver_id]
        life_decay = state.tyre.model.life_decay_per_lap
        engine._complete_lap(driver)
        assert state.tyre.age_laps == pytest.approx(.1)
        assert state.tyre.tyre_life == pytest.approx(
            100 - life_decay * (track.length_km / 4.5) * driver.aggressive * .1
        )
        engine._complete_lap(driver)
        assert state.tyre.age_laps == pytest.approx(1.1)
    finally:
        engine.teardown()


def test_okayama_pit_exit_resynchronizes_track_position():
    track = HistoricalResultsProvider().load("aida", 1994)[0]
    driver = DEFAULT_DRIVERS[0]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      track_progress_laps=True, num_laps=3), track, [driver])
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    engine.set_controller(driver.driver_id, controller)
    try:
        a, b = track.pit.waypoints[:2]
        angle = math.atan2(b[1]-a[1], b[0]-a[0])
        cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
        pb.resetBasePositionAndOrientation(car, (*a, .5),
            pb.getQuaternionFromEuler((0, 0, angle)), physicsClientId=cid)
        pb.resetBaseVelocity(car, (18*math.cos(angle), 18*math.sin(angle), 0), physicsClientId=cid)
        engine.prev_waypoint_idx[driver.driver_id] = track.pit.entry_waypoint
        engine.last_pos[driver.driver_id] = a
        engine._update_race_progress(.1)
        # Representa a última projeção da pista antes de entrar nos boxes.
        controller._project(driver.driver_id, *a)
        engine._pit_requests[driver.driver_id] = {"compound": TyreCompound.MEDIUM, "fuel": 0, "serviced": False}
        state = engine.states[driver.driver_id]
        for _ in range(600):
            engine._step_tick(.1, 24)
            if state.pit_stop_done and not state.pitting:
                break
        else:
            pytest.fail("O carro não completou a passagem pelos boxes")
        max_error = 0.0
        for _ in range(120):
            engine._step_tick(.1, 24)
            max_error = max(max_error, track.distance_to_centerline(state.position_x, state.position_y))
        assert max_error < track.width_m / 2
    finally:
        engine.teardown()


def test_pit_controller_follows_the_track_before_entry():
    track = load_live_track("interlagos", 2023)
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f"pit-{i}") for i in range(6)]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      track_progress_laps=True, num_laps=3), track, drivers)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    try:
        for i, driver in enumerate(drivers):
            engine.set_controller(driver.driver_id, controller)
            index, distance = track.pit.entry_waypoint, 0.0
            while distance < 100 + 12*i:
                prev = (index-1) % len(track.waypoints)
                distance += math.dist(track.waypoints[index], track.waypoints[prev])
                index = prev
            a, b = track.waypoints[index], track.waypoints[(index+1) % len(track.waypoints)]
            angle = math.atan2(b[1]-a[1], b[0]-a[0])
            cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
            pb.resetBasePositionAndOrientation(car, (*a, .5),
                pb.getQuaternionFromEuler((0, 0, angle)), physicsClientId=cid)
            pb.resetBaseVelocity(car, (30*math.cos(angle), 30*math.sin(angle), 0), physicsClientId=cid)
            engine.prev_waypoint_idx[driver.driver_id] = index
            engine.last_pos[driver.driver_id] = a
            engine._pit_requests[driver.driver_id] = {"compound": TyreCompound.MEDIUM, "fuel": 0, "serviced": False}
        engine._update_race_progress(.1)
        max_error = 0.0
        for _ in range(600):
            engine._step_tick(.1, 24)
            for driver in drivers:
                state = engine.states[driver.driver_id]
                if state.pitting and engine.pit_controller.has_entered(state):
                    max_error = max(max_error, engine.pit_controller.distance_to_lane(state.position_x, state.position_y))
            if all(engine.states[d.driver_id].pit_stop_done and not engine.states[d.driver_id].pitting for d in drivers):
                break
        else:
            pytest.fail("A fila não completou a passagem pelos boxes")
        assert max_error < track.pit.width_m / 2 + 1
    finally:
        engine.teardown()


def test_driver_brakes_instead_of_starting_pass_in_okayama_corner():
    from domain.weather import BASE_CONDITIONS, WeatherKind
    from engine.controllers import EnvironmentState

    track = HistoricalResultsProvider().load("aida", 1994)[0]
    controller = RuleBasedRaceController(track, seed=42)
    first, second = [d.initial_state() for d in DEFAULT_DRIVERS[:2]]
    for state, s, speed in ((first, 2740.0, 20.0), (second, 2748.0, 10.0)):
        state.position_x, state.position_y = controller._point_at(s, centerline=True)
        state.heading_rad = float(controller._heading[controller._segment_at(s)])
        state.velocity_mps = speed
    env = EnvironmentState(sim_ts=5.0, lap=0, weather=BASE_CONDITIONS[WeatherKind.DRY],
                           track=track, all_driver_states={first.driver_id: first, second.driver_id: second})
    command = controller.compute_input(env, first)
    assert controller._styles[first.driver_id].avoid_target_id is None
    assert command.brake > 0.0


def test_prince_george_pit_entry_does_not_cut_the_hairpin():
    from domain.pit_lane import ensure_pit_lane

    track = HistoricalResultsProvider().load("east-london", 1965)[0]
    lane = ensure_pit_lane(track)
    # No traçado histórico, a curva anterior à reta está ~400 m antes da linha.
    # A entrada deve começar depois dela, não no trecho anterior à curva.
    assert track.length_m - lane.entry_s_m < 360.0
    assert track.distance_to_centerline(*lane.waypoints[0]) < 1.0
    assert track.distance_to_centerline(*lane.waypoints[-1]) < 1.0
    a, b = lane.waypoints[:2]
    first_heading = math.atan2(b[1] - a[1], b[0] - a[0])
    travelled = 0.0
    for i in range(1, len(lane.waypoints) - 1):
        travelled += math.dist(lane.waypoints[i - 1], lane.waypoints[i])
        if travelled >= 100.0:
            c, d = lane.waypoints[i:i+2]
            last_heading = math.atan2(d[1] - c[1], d[0] - c[0])
            turn = (last_heading - first_heading + math.pi) % (2 * math.pi) - math.pi
            assert abs(turn) < math.radians(25)
            break
    else:
        pytest.fail("A entrada dos boxes não tem comprimento suficiente")


def test_prince_george_mixed_traffic_can_complete_pit_passage():
    track = HistoricalResultsProvider().load("east-london", 1965)[0]
    drivers = [replace(DEFAULT_DRIVERS[i % 2], driver_id=f"pit-{i}") for i in range(6)]
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      track_progress_laps=True, num_laps=3), track, drivers)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=42)
    try:
        for i, driver in enumerate(drivers):
            engine.set_controller(driver.driver_id, controller)
            index, distance = track.pit.entry_waypoint, 0.0
            while distance < 100 + 12*i:
                prev = (index-1) % len(track.waypoints)
                distance += math.dist(track.waypoints[index], track.waypoints[prev])
                index = prev
            a, b = track.waypoints[index], track.waypoints[(index+1) % len(track.waypoints)]
            angle = math.atan2(b[1]-a[1], b[0]-a[0])
            cid, car = engine.physics._client_id, engine.handles[driver.driver_id].chassis_id
            pb.resetBasePositionAndOrientation(car, (*a, .5),
                pb.getQuaternionFromEuler((0, 0, angle)), physicsClientId=cid)
            pb.resetBaseVelocity(car, (30*math.cos(angle), 30*math.sin(angle), 0), physicsClientId=cid)
            engine.prev_waypoint_idx[driver.driver_id] = index
            engine.last_pos[driver.driver_id] = a
            if i % 2 == 0:
                engine._pit_requests[driver.driver_id] = {"compound": TyreCompound.MEDIUM, "fuel": 0, "serviced": False}
        engine._update_race_progress(.1)
        max_lane_error = 0.0
        car_ids = {handle.chassis_id for handle in engine.handles.values()}
        contact_ticks = 0
        for _ in range(650):
            engine._step_tick(.1, 24)
            contacts = pb.getContactPoints(physicsClientId=engine.physics._client_id)
            if any(c[1] in car_ids and c[2] in car_ids and c[1] != c[2] and c[8] < 0 for c in contacts):
                contact_ticks += 1
            for driver in drivers[::2]:
                state = engine.states[driver.driver_id]
                if state.pitting and engine.pit_controller.has_entered(state):
                    max_lane_error = max(max_lane_error, engine.pit_controller.distance_to_lane(state.position_x, state.position_y))
            if all(engine.states[d.driver_id].pit_stop_done and not engine.states[d.driver_id].pitting for d in drivers[::2]):
                break
        else:
            pytest.fail("Os carros não completaram a passagem pelos boxes")
        assert max_lane_error < track.pit.width_m
        assert contact_ticks == 0
        assert all(engine.states[d.driver_id].pit_stop_done == 0 for d in drivers[1::2])
    finally:
        engine.teardown()


@pytest.mark.parametrize("circuit", ["interlagos", "east-london"])
def test_leader_crossing_line_in_pit_updates_tick_without_waiting_for_last_car(circuit):
    from engine.publisher import Publisher

    class Capture(Publisher):
        def __init__(self): self.events = []
        def publish(self, event): self.events.append(event.to_dict())

    track = (load_live_track("interlagos", 2023) if circuit == "interlagos"
             else HistoricalResultsProvider().load("east-london", 1965)[0])
    leader, follower = DEFAULT_DRIVERS[:2]
    publisher = Capture()
    engine = SimulationEngine(replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False,
                                      track_progress_laps=True, num_laps=3), track,
                              [leader, follower], publisher=publisher)
    engine.setup()
    engine.set_controller(leader.driver_id, RuleBasedRaceController(track, seed=42))
    try:
        a, b = track.pit.waypoints[:2]
        heading = math.atan2(b[1] - a[1], b[0] - a[0])
        cid, car = engine.physics._client_id, engine.handles[leader.driver_id].chassis_id
        pb.resetBasePositionAndOrientation(car, (*a, .5),
            pb.getQuaternionFromEuler((0, 0, heading)), physicsClientId=cid)
        pb.resetBaseVelocity(car, (18*math.cos(heading), 18*math.sin(heading), 0), physicsClientId=cid)
        engine.prev_waypoint_idx[leader.driver_id] = track.pit.entry_waypoint
        engine.last_pos[leader.driver_id] = a
        engine._update_race_progress(.1)
        engine.race_progress_m[leader.driver_id] = track.pit.entry_s_m
        engine._pit_requests[leader.driver_id] = {"compound": TyreCompound.MEDIUM, "fuel": 0, "serviced": False}
        for _ in range(650):
            engine._step_tick(.1, 24)
            if engine.states[leader.driver_id].lap:
                break
        else:
            pytest.fail("O líder não completou a volta pelos boxes")
        assert engine.states[leader.driver_id].pitting
        assert engine.states[follower.driver_id].lap == 0
        tick = next(event for event in reversed(publisher.events) if event["type"] == "tick")
        assert tick["lap"] == 1
        assert tick["positions"][0]["driver_id"] == leader.driver_id
        assert tick["positions"][0]["lap"] == 1
        assert tick["positions"][1]["lap"] == 0
        laps = [event for event in publisher.events if event["type"] == "lap_completed"]
        assert len(laps) == 1 and laps[0]["driver_id"] == leader.driver_id

        # O mesmo tick deve chegar coerente ao Redis, ao snapshot e ao WebSocket.
        import json
        from api.race_manager import LivePublisher
        from engine.events import TickEvent
        class Pipeline:
            def __init__(self): self.values, self.messages = {}, []
            def set(self, key, value, ex=None): self.values[key] = value; return self
            def publish(self, channel, value): self.messages.append((channel, value)); return self
            def execute(self): return []
        class Store:
            def __init__(self): self.pipe = Pipeline()
            def pipeline(self, transaction=True): return self.pipe
        store = Store()
        live = LivePublisher(store, "race_test")
        live.engine = engine
        live.publish(TickEvent(sim_ts=engine.sim_ts, lap=tick["lap"],
                               positions=tick["positions"], weather=tick["weather"]))
        saved = json.loads(store.pipe.values["race:race_test:snapshot"])["last_tick"]
        sent = json.loads(store.pipe.messages[-1][1])
        for published_tick in (saved, sent):
            assert published_tick["lap"] == published_tick["leader_lap"] == 1
            assert published_tick["positions"][0]["pitting"]
            assert published_tick["positions"][0]["lap"] == 1
    finally:
        engine.teardown()
