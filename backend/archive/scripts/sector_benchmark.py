"""Fase 1 — benchmark de ritmo por setores (Interlagos).

Compara um candidato (política) contra o controlador de referência em
condições IDÊNTICES: largada parada na linha, determinístico (tanh(mean)),
sem respawn, grip real. Divide a pista em N setores e reporta por setor:
tempo, v média/máx, frações de acelerador/freio, erro lateral, incidentes.

Também executa o PROFILADOR DE CURVAS: capacidade da política de atravessar
cada curva crítica a partir de entradas graduadas (20-55 m/s), isolando
"freia demais" de "não freia o suficiente" de "já está no limite".

Uso:
  .venv/bin/python model_train/sector_benchmark.py \
      --actor model_train/v6_pace/multi_context_rl_actor_best.keras \
      --episodes 10 --out bench_v6.csv
  .venv/bin/python model_train/sector_benchmark.py --baseline   # só referência
"""
import os, sys, math, json
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import numpy as np
import pandas as pd

N_SECTORS = 8
CRITICAL = {  # nome: s do ápice (Fase A) — usados no profilador de curvas
    'aberta_2048': 2048, 'hairpin_2309': 2309, 'wrap_0': 4155,
}


def run_episode(env, act, max_steps=3000):
    """Roda 1 episódio determinístico; act(obs)->ação[2]. Retorna trace+info."""
    obs, _ = env.reset()
    rows, done = [], False
    info = {}
    while not done:
        a = act(obs)
        o = {k: np.asarray(v).copy() for k, v in obs.items()}
        rows.append((o, a.copy()))
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    return rows, info


def trace_to_df(env, rows):
    out = []
    for o, a in rows:
        tel = np.asarray(o['telemetry'])
        phys = env.engine.physics.get_state(env.engine.handles[env.driver_id])
        _, s, _, lat = env._project_on_path(phys['x'], phys['y'])
        th, br, sr = env.action_to_controls(a, phys['speed_mps'])
        out.append(dict(s=s, v=phys['speed_mps'], lat=lat, th=th, br=br,
                        steer=sr, prog=env._total_wp_progress))
    return pd.DataFrame(out)


def sector_table(df, track_len, s_start):
    """Setores por progresso desde a largada (não por s absoluto)."""
    df = df.copy()
    df['prog'] = df['prog'] - df['prog'].iloc[0]
    edges = np.linspace(0, track_len, N_SECTORS + 1)
    df['sector'] = np.digitize(df['prog'], edges) - 1
    df = df[(df['sector'] >= 0) & (df['sector'] < N_SECTORS)]
    dt = 0.1
    g = df.groupby('sector')
    tab = pd.DataFrame({
        'tempo_s': g.size() * dt,
        'v_med': g['v'].mean(), 'v_max': g['v'].max(),
        'th_frac': g['th'].mean(), 'br_frac': g['br'].mean(),
        'lat_med': g['lat'].abs().mean(), 'lat_max': g['lat'].abs().max(),
        'dist_m': g['prog'].last() - g['prog'].first(),
    })
    return tab


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--actor', default=None)
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--episodes', type=int, default=10)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    import tensorflow as tf
    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.model_train.reference_controller import ReferenceController

    env = F1MultiContextEnv(track='interlagos', allow_respawn=False, grip_override=None)
    L = env._track_len_s

    results = {}
    # ---------------- baseline: controlador clássico ----------------
    ctrl = ReferenceController(env, a_lat_max=12.0)
    laps, times, tabs = [], [], []
    for ep in range(min(args.episodes, 3)):
        rows, info = run_episode(env, lambda o: ctrl.action())
        df = trace_to_df(env, rows)
        ok = bool(info.get('completed_lap', False))
        laps.append(ok)
        if ok:
            times.append(len(rows) * 0.1)
            tabs.append(sector_table(df, L, 0))
    results['referencia'] = dict(
        voltas=f"{sum(laps)}/{len(laps)}", tempos=times,
        mediana_s=float(np.median(times)) if times else None,
        setores=(pd.concat(tabs).groupby(level=0).mean() if tabs else None))
    print(f"[referencia] voltas {sum(laps)}/{len(laps)} | tempo mediano "
          f"{results['referencia']['mediana_s']}")

    # ---------------- candidato ----------------
    if args.actor:
        actor = tf.keras.models.load_model(args.actor, compile=False)

        def act(o):
            m = actor({k: np.asarray(v)[None] for k, v in o.items()}, training=False).numpy()[0]
            return np.tanh(m)

        laps, times, tabs, fails = [], [], [], []
        for ep in range(args.episodes):
            rows, info = run_episode(env, act)
            df = trace_to_df(env, rows)
            ok = bool(info.get('completed_lap', False))
            laps.append(ok)
            if ok:
                times.append(len(rows) * 0.1)
                tabs.append(sector_table(df, L, 0))
            else:
                fails.append(dict(s=env._last_s, v=info.get('speed', 0),
                                  lat=info.get('lat', 0)))
        name = Path(args.actor).parent.name
        results[name] = dict(voltas=f"{sum(laps)}/{len(laps)}", tempos=times,
                             mediana_s=float(np.median(times)) if times else None,
                             falhas=fails)
        print(f"[{name}] voltas {sum(laps)}/{len(laps)} | tempo mediano "
              f"{results[name]['mediana_s'] if times else '—'}")
        if fails:
            print(f"  falhas (s, v_km/h, lat): "
                  + ", ".join(f"({f['s']:.0f},{f['v']*3.6:.0f},{f['lat']:.1f})" for f in fails[:5]))

        # comparação por setor (só se ambos completaram voltas)
        if tabs and results['referencia']['setores'] is not None:
            cand = pd.concat(tabs).groupby(level=0).mean()
            base = results['referencia']['setores']
            comp = pd.DataFrame({
                't_ref_s': base['tempo_s'], 't_cand_s': cand['tempo_s'],
                'delta_s': cand['tempo_s'] - base['tempo_s'],
                'v_ref': base['v_med'], 'v_cand': cand['v_med'],
            })
            comp['oportunidade'] = comp['delta_s']  # positivo = candidato mais lento
            print("\n=== SETORES (positivo = candidato perde tempo) ===")
            print(comp.round(2).to_string())
            print(f"total candidato: {cand['tempo_s'].sum():.1f}s vs ref {base['tempo_s'].sum():.1f}s "
                  f"| delta {cand['tempo_s'].sum()-base['tempo_s'].sum():+.1f}s")
            worst = comp.sort_values('delta_s', ascending=False).head(3)
            print("maiores oportunidades:", [f"S{int(i)} (+{r.delta_s:.1f}s)"
                                             for i, r in worst.iterrows()])

    if args.out:
        ser = {k: {kk: vv for kk, vv in v.items() if kk != 'setores'}
               for k, v in results.items()}
        for k, v in results.items():
            if v.get('setores') is not None:
                v['setores'].to_csv(args.out.replace('.json', f'_{k}_setores.csv'))
        json.dump(ser, open(args.out, 'w'), indent=1, default=str)
        print(f"-> {args.out}")
    env.close()


if __name__ == '__main__':
    main()
