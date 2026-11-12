"""FASE R3 F1 — teste SINTÉTICO do rejoin profundo (fix do absorvedor).

Cenário: carro sozinho a ~40 m da linha central (grama funda), v=0, heading
TANGENCIAL à pista. O rejoin por BEARING (R3) deve trazê-lo de volta:

  1. volta ao asfalto (|lat| <= meia-largura) em < 60 s;
  2. sem contato com outro chassi (só há 1 carro — trivial, mas assertado);
  3. reengate na direção correta: após re-entrar, atinge v >= 3 m/s e
     acumula progresso para frente (cum_dist cresce >= 5 m).

OBaseline R2 (lei antiga de esterço fixo): o carro ORBITAVA a ~1,5 m/s
por 500+s sem convergir (PER: lat 20-78 m por 500+s) — este teste falharia.
"""
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR.parent))

OFF_DIST_M = 40.0        # distância da linha central no início
T_LIMIT_S = 60.0          # limite para voltar ao asfalto
ZONE_S = 2600.0           # reta principal (heading ~55°), longe de curvas


def _pose_at_s(track, s):
    """(x, y, yaw, nx, ny) na linha central em s (interpola segmentos)."""
    wps = np.asarray(track.waypoints, dtype=np.float64)
    AB = np.roll(wps, -1, axis=0) - wps
    seg_len = np.hypot(AB[:, 0], AB[:, 1])
    seg_cum = np.concatenate([[0.0], np.cumsum(seg_len)])[:-1]
    s = s % float(seg_len.sum())
    j = int(np.searchsorted(seg_cum, s, side="right") - 1) % len(wps)
    t = (s - seg_cum[j]) / (seg_len[j] + 1e-9)
    x = wps[j, 0] + t * AB[j, 0]
    y = wps[j, 1] + t * AB[j, 1]
    yaw = math.atan2(AB[j, 1], AB[j, 0])
    L = seg_len[j]
    nx, ny = -AB[j, 1] / L, AB[j, 0] / L  # normal à esquerda
    return x, y, yaw, nx, ny


@pytest.mark.slow
def test_deep_rejoin_recovers_40m_in_under_60s():
    from backend.model_train.f1_env import load_track_frozen
    from backend.scripts.run_race_10_cars import (NeuralRaceController,
                                                  build_grid_drivers,
                                                  DEFAULT_MAPPINGS_PATH,
                                                  MODEL_DIR)
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS

    track = load_track_frozen("interlagos")  # FONTE da pista: frozen v2 (SF 729)
    drivers = build_grid_drivers()[:1]
    sim_config = SimulationConfig(race_id="rejoin-test", num_laps=99,
                                  logic_step_hz=10.0, physics_sub_steps=24,
                                  gui=False, camera_mode="overview",
                                  draw_track=False, realtime=False,
                                  input_stale_after_s=300.0)
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=WeatherModel(
                                  initial=BASE_CONDITIONS[WeatherKind.DRY]))
    engine.setup()
    engine.race_started = True

    ctrl = NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH, track=track, obs_mode="edge")

    # posiciona o carro na grama funda: ZONE_S + 40 m na normal à esquerda,
    # heading TANGENCIAL (precisa virar ~90° para mirar a re-entrada)
    x0, y0, yaw0, nx, ny = _pose_at_s(track, ZONE_S)
    px, py = x0 + nx * OFF_DIST_M, y0 + ny * OFF_DIST_M
    engine.physics.set_position(engine.handles[drivers[0].driver_id],
                                pos=(px, py, 0.5), yaw_rad=yaw0, reset_vel=True)

    half_width = track.width_m / 2.0
    dt = 1.0 / sim_config.logic_step_hz
    entered_s, v_at_entry, cum_at_entry = None, None, None
    n_ticks = int(T_LIMIT_S / dt)
    trace = []
    for t in range(n_ticks):
        actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
        th, brk, steer = actions[0]
        engine.set_driver_input(drivers[0].driver_id, throttle=th, brake=brk,
                                steering_yaw_rad=steer)
        engine._step_tick(dt, sim_config.physics_sub_steps)
        st = engine.physics.get_state(engine.handles[drivers[0].driver_id])
        dist_cl, _ = track.nearest_segment(st["x"], st["y"])
        if t % 5 == 0:
            trace.append((t * dt, dist_cl, st["speed_mps"], steer, th))
        if entered_s is None and dist_cl <= half_width:
            entered_s = t * dt
            v_at_entry = st["speed_mps"]
            cum_at_entry = float(engine.cum_dist_m.get(drivers[0].driver_id, 0.0))

    print(f"[rejoin] trace (t, dist_cl, v, steer, th): "
          f"{[(round(a,1), round(b,1), round(c,1), round(d,2), round(e,2)) for a,b,c,d,e in trace[:8]]}")
    print(f"[rejoin] ... {[(round(a,1), round(b,1), round(c,1), round(d,2), round(e,2)) for a,b,c,d,e in trace[-4:]]}")

    # 1. voltou ao asfalto dentro do limite
    assert entered_s is not None, (
        f"carro NÃO voltou ao asfalto em {T_LIMIT_S:.0f}s "
        f"(dist final={trace[-1][1]:.1f} m, v={trace[-1][2]:.2f} m/s) — absorvedor")
    assert entered_s < T_LIMIT_S, f"re-entrada demorou {entered_s:.1f}s (> {T_LIMIT_S:.0f}s)"

    # 2. sem contato com OUTRO chassi de carro (neste teste sóbrio de 1 carro
    #    o conjunto é vazio por construção; o assert fica pelo contrato)
    import pybullet as pb
    me = engine.handles[drivers[0].driver_id].chassis_id
    other_chassis = {engine.handles[d.driver_id].chassis_id for d in drivers[1:]}
    for c in pb.getContactPoints(me, physicsClientId=engine.physics._client_id):
        assert not (len(c) >= 10 and (c[1] in other_chassis or c[2] in other_chassis)), \
            "contato com outro chassis no retorno"

    # 3. reengate na direção correta: v >= 3 m/s e progresso p/ frente pós-entrada
    n_extra = int(10.0 / dt)
    v_max_after = 0.0
    for t in range(n_extra):
        actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
        th, brk, steer = actions[0]
        engine.set_driver_input(drivers[0].driver_id, throttle=th, brake=brk,
                                steering_yaw_rad=steer)
        engine._step_tick(dt, sim_config.physics_sub_steps)
        st = engine.physics.get_state(engine.handles[drivers[0].driver_id])
        v_max_after = max(v_max_after, st["speed_mps"])
    cum_after = float(engine.cum_dist_m.get(drivers[0].driver_id, 0.0))
    assert v_max_after >= 3.0, (
        f"pós re-entrada o carro não re-engajou: v_max={v_max_after:.2f} m/s em 10s "
        f"(recovery nunca sai com v<3)")
    assert cum_after - cum_at_entry >= 5.0, (
        f"sem progresso pós re-entrada: {cum_after - cum_at_entry:.1f} m em 10s")
    print(f"[rejoin] PASS: re-entrada em {entered_s:.1f}s (v={v_at_entry:.2f} m/s), "
          f"v_max pós={v_max_after:.1f} m/s, progresso {cum_after - cum_at_entry:.1f} m")
