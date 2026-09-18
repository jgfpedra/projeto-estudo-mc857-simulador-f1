"""Entry point: run the racing simulation.

A engine se inscreve num InputSource (default: in-memory) e consome inputs
publicados externamente. Não há mais "andar sozinho" — os carros só se movem
se um agente externo (teclado, IA, replay, etc.) publicar inputs.

Para testar com teclado:

Terminal 1 (engine):
    python scripts/run_sim.py --laps 10 --gui --camera follow --realtime

Terminal 2 (publisher de teclado, no mesmo diretório):
    python scripts/publish_keyboard.py --driver drv_01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Adiciona raiz do projeto no sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import (
    DEFAULT_INTERLAGOS_CONFIG,
    DEFAULT_DRIVERS,
    CircuitLoadError,
    load_track,
)
from domain.weather import (
    BASE_CONDITIONS,
    WeatherKind,
    WeatherTransitionConfig,
    WeatherModel,
)
from engine import (
    CarInput,
    FileInputSource,
    JSONLPublisher,
    InMemoryInputSource,
    NullPublisher,
    RedisInputSource,
    SimulationEngine,
)
from engine.publisher import RedisPublisher
import math


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Racing simulation with PyBullet.")
    p.add_argument("--laps", type=int, default=10, help="number of race laps")
    p.add_argument(
        "--track",
        default=None,
        help="circuit name, FastF1 event or round number. "
             "Omitted uses the local Interlagos preset.",
    )
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help="championship year used by FastF1 (required unless --track is Interlagos)",
    )
    p.add_argument(
        "--session",
        default="R",
        help="FastF1 session code (R, Q, S, FP1, ...). Default: R",
    )
    p.add_argument(
        "--fastf1-cache",
        default=os.environ.get("FASTF1_CACHE"),
        help="optional FastF1 cache directory (or FASTF1_CACHE env var)",
    )
    p.add_argument("--out", default="download/race_log.jsonl", help="JSONL output path")
    # Output publisher (state/events)
    p.add_argument("--redis", action="store_true",
                   help="also publish state/events to Redis")
    p.add_argument("--redis-host", default="localhost")
    p.add_argument("--redis-port", type=int, default=6379)
    # GUI
    p.add_argument("--gui", action="store_true", default=True, help="open PyBullet GUI (needs display)")
    p.add_argument("--camera", default="follow",choices=["overview", "follow", "none"],
                   help="camera mode in GUI")
    p.add_argument("--no-track-lines", action="store_true", help="don't draw racing line in GUI")
    p.add_argument("--realtime", default=True, action="store_true",
                   help="pace simulation to real time (use with --gui to watch)")
    # --- Input source (controle dos carros) ---
    p.add_argument(
        "--input-source",
        default="file",
        choices=["file", "memory", "redis"],
        help="where to consume car inputs from: file (default, shared cross-process IPC), "
             "memory (in-process), or redis (external broker)",
    )
    p.add_argument(
        "--keyboard",
        action="store_true",
        help="enable interactive keyboard control in this terminal (WASD controls drv_01)",
    )
    p.add_argument("--input-fallback", default="brake", choices=["brake", "neutral"],
                   help="what to do when no input received: brake (default, gradual) "
                        "or neutral (instant stop)")
    p.add_argument("--input-stale-after-s", type=float, default=2.0,
                   help="input considered stale after N seconds without update (default 2.0)")
    # -------------------------------------------
    p.add_argument("--seed", type=int, default=42, help="random seed")
    p.add_argument("--no-jsonl", action="store_true", help="disable JSONL output")
    p.add_argument("--summary", action="store_true", help="print summary at the end")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 60)
    print(" Racing Simulation — PyBullet + external inputs")
    print("=" * 60)

    # Config
    config = DEFAULT_INTERLAGOS_CONFIG
    config.num_laps = args.laps
    config.gui = args.gui
    config.random_seed = args.seed
    config.camera_mode = args.camera
    config.draw_track = not args.no_track_lines
    config.realtime = args.realtime
    config.input_fallback = args.input_fallback
    config.input_stale_after_s = args.input_stale_after_s

    try:
        track = load_track(
            track_name=args.track,
            year=args.year,
            session=args.session,
            cache_dir=args.fastf1_cache,
        )
    except (ValueError, CircuitLoadError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(
        f"[info] Track: {track.name} ({track.length_km:.3f} km, "
        f"{len(track.waypoints)} waypoints, source={track.source})"
    )

    # Drivers
    drivers = list(DEFAULT_DRIVERS)
    print(f"[info] Drivers: {len(drivers)}")
    for d in drivers:
        print(f"        - {d.driver_id} {d.name} ({d.car_specs.name}) "
              f"tyre={d.starting_tyre_compound.value} fuel={d.starting_fuel_pct*100:.0f}%")

    # Output publisher (state/events)
    out_path = args.out
    if not os.path.isabs(out_path):
        out_path = os.path.join(_ROOT, out_path)
    publishers = []
    jsonl_pub = None
    if not args.no_jsonl:
        jsonl_pub = JSONLPublisher(out_path)
        publishers.append(jsonl_pub)
        print(f"[info] JSONL log: {out_path}")
    if args.redis:
        redis_pub = RedisPublisher(
            race_id=config.race_id,
            host=args.redis_host,
            port=args.redis_port,
        )
        publishers.append(redis_pub)
        print(f"[info] Redis publisher enabled (race_id={config.race_id})")

    class MultiPublisher:
        def __init__(self, pubs):
            self._pubs = pubs
        def publish(self, event):
            for p in self._pubs:
                p.publish(event)
        def flush(self):
            for p in self._pubs:
                p.flush()
        def close(self):
            for p in self._pubs:
                p.close()

    publisher = MultiPublisher(publishers) if publishers else NullPublisher()

    # Input source (de onde a engine consome inputs dos carros)
    if args.input_source == "redis":
        input_source = RedisInputSource(
            race_id=config.race_id,
            host=args.redis_host,
            port=args.redis_port,
        )
        print(f"[info] Input source: Redis (race_id={config.race_id})")
        print(f"[info]   Publish inputs via: redis-cli HSET race:{config.race_id}:input drv_01 '<json>'")
    elif args.input_source == "file":
        input_source = FileInputSource(race_id=config.race_id)
        print(f"[info] Input source: File (IPC via {input_source.file_path})")
        print(f"[info]   Publish inputs via: python scripts/publish_keyboard.py --driver drv_01")
    else:
        input_source = InMemoryInputSource(fallback_race_id=config.race_id)
        print(f"[info] Input source: InMemory (in-process + IPC sync)")
        print(f"[info]   Publish inputs via: python scripts/publish_keyboard.py --driver drv_01")
    print(f"[info] Input fallback: {config.input_fallback} (stale after {config.input_stale_after_s}s)")

    # Weather model
    weather_model = WeatherModel(
        initial=BASE_CONDITIONS[WeatherKind.DRY],
        config=WeatherTransitionConfig.default(transition_prob_per_lap=0.06),
    )

    # Engine
    engine = SimulationEngine(
        config=config,
        track=track,
        drivers=drivers,
        publisher=publisher,
        weather_model=weather_model,
        input_source=input_source,
    )

    # Teclado interativo opcional diretamente neste terminal (estilo demo_external_input.py)
    if args.keyboard:
        import threading
        kb_speed = 0.0
        kb_steer = 0.0
        kb_brake = 0.0
        kb_running = True

        def terminal_keyboard_loop():
            nonlocal kb_speed, kb_steer, kb_brake, kb_running
            print("\n[keyboard] Interactive terminal controls active:")
            print("  w (+10 m/s), s (-10 m/s), a (left), d (right), space (stop), r (reset), q (quit)\n")
            while kb_running and not engine.race_finished:
                try:
                    prompt_str = f"\r[speed={kb_speed:5.1f} m/s | steer={math.degrees(kb_steer):+5.1f}° | brake={kb_brake:.1f}] > "
                    line = input(prompt_str).strip().lower()
                    if not line:
                        continue
                    k = line[0]
                    if k == "q":
                        engine.race_finished = True
                        kb_running = False
                        break
                    elif k == " ":
                        kb_speed = 0.0
                        kb_brake = 1.0
                    elif k == "r":
                        kb_speed = 0.0
                        kb_steer = 0.0
                        kb_brake = 0.0
                    elif k == "w":
                        kb_speed = min(80.0, kb_speed + 10.0)
                        kb_brake = 0.0
                    elif k == "s":
                        kb_speed = max(0.0, kb_speed - 10.0)
                        kb_brake = 0.5 if kb_speed == 0.0 else 0.0
                    elif k == "a":
                        kb_steer = max(-math.radians(25.0), kb_steer - math.radians(5.0))
                    elif k == "d":
                        kb_steer = min(math.radians(25.0), kb_steer + math.radians(5.0))
                    else:
                        continue

                    inp = CarInput(target_speed_mps=kb_speed, steering_yaw_rad=kb_steer, brake=kb_brake)
                    input_source.update_last_input("drv_01", inp, source="terminal_stdin")
                except (EOFError, KeyboardInterrupt):
                    kb_running = False
                    break

        t_kb = threading.Thread(target=terminal_keyboard_loop, daemon=True)
        t_kb.start()

    print(f"[info] Starting race ({config.num_laps} laps, race_id={config.race_id})")
    print(f"[info] ENGINE DOES NOT DRIVE THE CARS — inputs must come from external source!")
    t0 = time.time()
    try:
        engine.run()
    except KeyboardInterrupt:
        print("\n[warn] interrupted by user")
    finally:
        publisher.flush()
        publisher.close()
        engine.teardown()
    dt = time.time() - t0
    print(f"[info] Simulation finished in {dt:.2f}s (sim_ts={engine.sim_ts:.2f}s)")

    # Print stats do input source
    stats = engine.get_input_source_stats()
    print(f"[info] Input source stats: {stats}")

    if args.summary and jsonl_pub is not None:
        print()
        print("=" * 60)
        print(" Event summary")
        print("=" * 60)
        counts = {}
        last_lap_event = None
        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        ev = json.loads(line)
                        counts[ev["type"]] = counts.get(ev["type"], 0) + 1
                        if ev["type"] == "lap_completed":
                            last_lap_event = ev
                    except json.JSONDecodeError:
                        continue
        for k, v in sorted(counts.items()):
            print(f"  {k:25s} {v:6d}")
        if last_lap_event:
            print()
            print(" Last lap_completed event:")
            print(json.dumps(last_lap_event, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
