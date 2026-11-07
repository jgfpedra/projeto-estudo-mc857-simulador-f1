"""Fase B+C — baseline na geometria atual + divergência v4 vs professor.

B: o controlador de referência completa a volta? Atravessa os dois pontos
   (s~2030 aberto, s~2286-2310 fechado) sem parar? Velocidade mínima em cada?
C: nos MESMOS estados da volta de referência, comparamos a ação da v4 com a
   do professor: onde a v4 freia e o professor acelera (assinatura OOD).
"""
import os, sys, math
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import numpy as np
import tensorflow as tf
from backend.model_train.f1_env import F1MultiContextEnv
from backend.model_train.reference_controller import ReferenceController

env = F1MultiContextEnv(track='interlagos', allow_respawn=False, grip_override=1.0)
ctrl = ReferenceController(env, a_lat_max=12.0)
v4 = tf.keras.models.load_model(str(MODEL_DIR / 'v4' / 'multi_context_rl_actor_best.keras'),
                                compile=False)
L = env._track_len_s

# ---------- Fase B: volta de referencia instrumentada ----------
obs, _ = env.reset(seed=1)
done, states = False, []
info = {}
while not done:
    a = ctrl.action()
    o = {k: np.asarray(v).copy() for k, v in obs.items()}
    states.append((o, a.copy()))
    obs, r, term, trunc, info = env.step(a)
    done = term or trunc
lap_ok = bool(info.get('completed_lap'))
print(f"[FaseB] volta de referencia: completed={lap_ok} | prog={info.get('progress_m', 0):.0f} m "
      f"| steps={len(states)} | tempo={len(states)*0.1:.0f}s")

s_track = []
for (o, a) in states:
    # recomputa s a partir da obs? melhor: refazemos com o trace abaixo
    pass

# re-corre com s anotado (barato: mesma dinâmica determinística)
obs, _ = env.reset(seed=1)
done, trace = False, []
while not done:
    phys = env.engine.physics.get_state(env.engine.handles[env.driver_id])
    _, s_now, _, lat_s = env._project_on_path(phys['x'], phys['y'])
    a = ctrl.action()
    trace.append(dict(s=s_now, v=phys['speed_mps'], lat=lat_s,
                      a_steer=a[0], a_long=a[1],
                      kappa_prev=np.asarray(obs['telemetry'])[10:23:2].copy()))
    obs, r, term, trunc, info = env.step(a)
    done = term or trunc

import pandas as pd
tr = pd.DataFrame(trace)
for label, lo, hi in [("curva aberta (R=18)", 1980, 2100),
                      ("hairpin (R=10)", 2250, 2360),
                      ("wrap (R=27)", 4100, 4160)]:
    seg = tr[(tr.s >= lo) & (tr.s <= hi)]
    if len(seg):
        print(f"[FaseB] {label}: v_min={seg.v.min():.1f} v_med={seg.v.mean():.1f} "
              f"v_max={seg.v.max():.1f} m/s | lat_max={seg.lat.abs().max():.1f} m "
              f"| parou(<0.5): {(seg.v < 0.5).sum()} amostras")

# ---------- Fase C: v4 vs professor nos mesmos estados ----------
print("\n[FaseC] acao longitudinal: v4 vs professor, por faixa de kappa preview max")
rows = []
for (o, a_teacher) in states:
    tel = np.asarray(o['telemetry'])
    kmax = float(np.abs(tel[10:23:2]).max()) / 25.0    # kappa preview max (rad/m)
    mean = v4({k: v[None] for k, v in o.items()}, training=False).numpy()[0]
    a_v4 = np.tanh(mean)
    rows.append(dict(kappa=kmax, v=tel[0]*100, teacher_long=a_teacher[1], v4_long=a_v4[1]))
R = pd.DataFrame(rows)
R['kbin'] = pd.cut(R.kappa, [0, 0.01, 0.02, 0.04, 0.06, 0.08, 0.12])
summ = R.groupby('kbin', observed=True).agg(
    n=('v4_long', 'size'),
    prof_long=('teacher_long', 'mean'), v4_long=('v4_long', 'mean'),
    v4_brake_frac=('v4_long', lambda x: (x < -0.3).mean()),
    prof_brake_frac=('teacher_long', lambda x: (x < -0.3).mean()),
    v_med=('v', 'mean'))
print(summ.round(2).to_string())
div = R[(R.v4_long < -0.3) & (R.teacher_long > 0.0)]
print(f"\nEstados onde v4 freia forte (<-0.3) e o professor acelera: "
      f"{len(div)}/{len(R)} ({100*len(div)/len(R):.0f}%)")
if len(div):
    print(f"  kappa medio nesses estados: {div.kappa.mean():.3f} | v media: {div.v.mean():.1f} m/s")
env.close()
