"""PASSO 0.1 (FASE 3 v14) — baseline PINADO do professor SOLO na corrida.

Resolve a inconsistência gate (107,9 s) vs medições anteriores no env
(111,6-114,6 s): o gate mede voltas ROLANTES (excl. volta 1 = largada
parada) em condições de corrida (grip real via modelo de pneu, composto
SOFT, engine da corrida); o env mede a volta de LARGADA parada com
composto MEDIUM. Este script replica EXATAMENTE a metodologia do gate
all-professor (mesma engine, mesmo grid, mesmo controlador e camadas de
autoridade) menos os outros 9 carros — o delta gate−solo é o custo real
do tráfego (baseline da FASE 4).

Uso:
  .venv/bin/python model_train/eval_teacher_solo.py --laps 3 --episodes 3
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
BACKEND = MODEL_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND), str(BACKEND / 'scripts')):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

import numpy as np


def run_solo_episode(track, laps: int, sf: float) -> dict:
    """1 corrida solo: professor no grid, `laps` voltas, tempos da engine."""
    import run_race_10_cars as R
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS
    from backend.model_train.race_diagnostic import ProfessorRaceController

    drivers = R.build_grid_drivers()[:1]          # VER (SOFT), P1, sozinho
    sim_config = SimulationConfig(
        race_id='solo', num_laps=laps, logic_step_hz=10.0,
        physics_sub_steps=24, gui=False, camera_mode='overview',
        draw_track=False, realtime=False, input_stale_after_s=300.0,
    )
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY]))
    engine.setup()
    R.place_grid(engine, track, drivers)
    engine.race_started = True

    ctrl = ProfessorRaceController(track, sf=sf)   # professor→rejoin→recovery→blocked
    wps = np.array(track.waypoints)
    dt = 0.1
    t = 0
    max_ticks = int((laps + 1) * 200 * 10)         # folga p/ voltas lentas
    while not engine.race_finished and t < max_ticks:
        actions = ctrl.predict_batch(engine, drivers, wps, track_id=0)
        th, brk, steer = actions[0]
        engine.set_driver_input(drivers[0].driver_id, throttle=th,
                                brake=brk, steering_yaw_rad=steer)
        engine._step_tick(dt, sim_config.physics_sub_steps)
        t += 1
    times = list(engine.states[drivers[0].driver_id].lap_times)
    offtrack_samples = 0
    engine.physics.close()
    return dict(ticks=t, lap_times=times, offtrack=offtrack_samples)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--track', default='interlagos')
    ap.add_argument('--laps', type=int, default=3)
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--sf', type=float, default=0.80)
    args = ap.parse_args()

    import run_race_10_cars as R
    track = R.resolve_track(track=args.track, year=2024, session='R')
    all_first, all_rolling = [], []
    for ep in range(args.episodes):
        r = run_solo_episode(track, args.laps, args.sf)
        ts = r['lap_times']
        first = ts[0] if ts else None
        rolling = ts[1:] if len(ts) > 1 else []
        all_first.append(first)
        all_rolling.extend(rolling)
        print(f"[ep {ep}] voltas: {[round(x, 1) for x in ts]} | "
              f"largada={first and round(first, 1)}s | rolantes={[round(x, 1) for x in rolling]}", flush=True)
    print(f"\n===== PROFESSOR SOLO (baseline FASE 4) — {args.track} =====")
    print(f"volta de LARGADA (parada): mediana {np.median(all_first):.1f}s "
          f"| amostras {len(all_first)}")
    print(f"voltas ROLANTES (baseline): mediana {np.median(all_rolling):.1f}s "
          f"| todas {[round(x, 1) for x in all_rolling]}")
    print(f"comparável ao gate all-professor (107,9 s rolantes c/ tráfego): "
          f"custo do tráfego = 107.9 − {np.median(all_rolling):.1f} "
          f"= {107.9 - np.median(all_rolling):+.1f}s")


if __name__ == '__main__':
    main()
