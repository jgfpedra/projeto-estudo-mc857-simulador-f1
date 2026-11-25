"""Reproducible offline pace and track-departure measurements.

Run from backend, for example:
    python -m scripts.benchmarks.measure_bot_pace --track monza-open --cars 10 --seed 42
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import time

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from domain import BASE_CONDITIONS, Track, WeatherKind, WeatherModel, WeatherTransitionConfig
from engine import RuleBasedRaceController, SimulationEngine
from engine.publisher import Publisher


class RacecraftMetrics:
    """Count nearby on-track order swaps sustained for at least 0.5 s.

    This estimates position changes, not official overtakes. The sampling
    excludes the opening 20 seconds, pit stops and off-track excursions.
    """
    def __init__(self) -> None:
        self.pairs = {}
        self.passes = 0
        self.leader_changes = 0
        self.last_leader = None

    def observe(self, samples, leader) -> None:
        if self.last_leader is not None and leader != self.last_leader:
            self.leader_changes += 1
        self.last_leader = leader
        for i, (a, progress_a, valid_a) in enumerate(samples):
            for b, progress_b, valid_b in samples[i + 1:]:
                key = (a, b)
                gap = progress_a - progress_b
                if not valid_a or not valid_b or abs(gap) > 100.0:
                    self.pairs.pop(key, None)
                    continue
                sign = 1 if gap > 3.0 else -1 if gap < -3.0 else 0
                previous = self.pairs.get(key)
                if previous is None:
                    if sign:
                        self.pairs[key] = [sign, 0, 0]
                    continue
                if not sign or sign == previous[0]:
                    previous[1], previous[2] = 0, 0
                elif sign == previous[1]:
                    previous[2] += 1
                    if previous[2] >= 2:
                        previous[:] = [sign, 0, 0]
                        self.passes += 1
                else:
                    previous[1], previous[2] = sign, 1


class CollisionCounter(Publisher):
    def __init__(self) -> None:
        self.collisions = 0

    def publish(self, event) -> None:
        self.collisions += event.type == 'collision'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--track', choices=('monza-open', 'monza', 'interlagos', 'ain-diab'), default='monza-open')
    parser.add_argument('--cars', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--driver-ids', help='IDs separados por vírgulas, na ordem do grid')
    parser.add_argument('--seconds', type=float, default=300.0)
    args = parser.parse_args()
    if not 1 <= args.cars <= 24 or args.seconds <= 0:
        parser.error('--cars deve estar entre 1 e 24 e --seconds deve ser positivo')

    if args.track == 'monza-open':
        fixture = Path(__file__).resolve().parents[2] / 'tests/fixtures/monza_openf1_2024.json'
        track = Track.from_waypoints(**json.loads(fixture.read_text(encoding='utf-8')))
    elif args.track == 'ain-diab':
        from api.providers.historical_f1results import HistoricalResultsProvider
        track, _, _ = HistoricalResultsProvider().load('ain-diab', 1958)
    else:
        track = load_live_track(args.track, 2024 if args.track == 'monza' else 2023)
    driver_ids = [x.strip() for x in args.driver_ids.split(',')] if args.driver_ids else [f'd{i:02d}' for i in range(args.cars)]
    if len(driver_ids) != args.cars or len(set(driver_ids)) != args.cars or any(not x for x in driver_ids):
        parser.error('--driver-ids deve conter um ID diferente para cada carro')
    drivers = [
        replace(DEFAULT_DRIVERS[i % len(DEFAULT_DRIVERS)], driver_id=driver_ids[i], name=f'Driver {i}',
                starting_tyre_compound=DEFAULT_DRIVERS[0].starting_tyre_compound)
        for i in range(args.cars)
    ]
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, num_laps=6,
                     track_progress_laps=True, collision_events=True, random_seed=args.seed)
    weather = WeatherModel(BASE_CONDITIONS[WeatherKind.DRY], WeatherTransitionConfig.default(0.0))
    collisions = CollisionCounter()
    engine = SimulationEngine(config, track, drivers, weather_model=weather, publisher=collisions)
    engine.setup()
    controller = RuleBasedRaceController(track, seed=args.seed)
    for driver in drivers:
        engine.set_controller(driver.driver_id, controller)
    off_ticks = {driver.driver_id: 0 for driver in drivers}
    max_lateral = {driver.driver_id: 0.0 for driver in drivers}
    slow_ticks = {driver.driver_id: 0 for driver in drivers}
    longest_slow_ticks = dict(slow_ticks)
    racecraft = RacecraftMetrics()
    start = time.monotonic()
    try:
        for tick in range(int(args.seconds * 10)):
            engine._step_tick(.1, 24)
            for driver in drivers:
                driver_id = driver.driver_id
                lateral = abs(engine.race_lateral_m.get(driver_id, 0.0))
                max_lateral[driver_id] = max(max_lateral[driver_id], lateral)
                off_ticks[driver_id] += lateral > track.width_m / 2
                slow_ticks[driver_id] = (slow_ticks[driver_id] + 1 if tick > 100 and engine.states[driver_id].velocity_mps < 1.4 else 0)
                longest_slow_ticks[driver_id] = max(longest_slow_ticks[driver_id], slow_ticks[driver_id])
            if tick >= 200 and tick % 5 == 0 and args.cars > 1:
                samples = [(d.driver_id, engine.race_progress_m[d.driver_id],
                            not engine.states[d.driver_id].pitting
                            and abs(engine.race_lateral_m[d.driver_id]) <= track.width_m / 2)
                           for d in drivers]
                racecraft.observe(samples, engine.ranked_drivers()[0].driver_id)
            if args.cars == 1 and engine.states[drivers[0].driver_id].lap >= 2:
                break
        print(json.dumps({
            'track': args.track, 'seed': args.seed, 'cars': args.cars,
            'sim_s': round(engine.sim_ts, 1),
            'lap_times_s': {d.driver_id: [round(x, 1) for x in engine.states[d.driver_id].lap_times]
                            for d in drivers},
            'off_track_ticks': off_ticks,
            'max_lateral_m': {k: round(v, 2) for k, v in max_lateral.items()},
            'longest_below_1_4_mps_s': {k: round(v / 10, 1) for k, v in longest_slow_ticks.items()},
            'estimated_passes_after_20s': racecraft.passes,
            'leader_changes_after_20s': racecraft.leader_changes,
            'collision_events': collisions.collisions,
            'corner_exit_errors': {d.driver_id: controller._style_for(d.driver_id).corner_error_count for d in drivers},
            'final_order': [d.driver_id for d in engine.ranked_drivers()],
            'leader_to_last_gap_m': round(max(engine.race_progress_m.values()) - min(engine.race_progress_m.values()), 1),
            'wall_s': round(time.monotonic() - start, 1),
        }, ensure_ascii=False, indent=2))
    finally:
        engine.teardown()


if __name__ == '__main__':
    main()
