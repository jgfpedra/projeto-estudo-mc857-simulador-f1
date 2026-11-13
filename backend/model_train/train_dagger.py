"""DAgger multi-pista (Fase 2) — a peça que faltava. FASE 3 v14: tráfego.

Substitui o PPO-do-zero como método principal. O loop:
  1. Iter 0: BC com voltas do professor v2 + ruído de ação (estados fora da linha)
  2. Iter k: rollout do ALUNO (mistura β_k decrescente com o professor),
     rotula CADA estado com o professor v2, agrega ao dataset, retreina.

O professor v2 (velocity_profile + pure pursuit adaptado) está definido em
QUALQUER pose (inclusive fora da pista) — requisito do DAgger.

FASE 3 v14 (tráfego):
  - --obs-mode traffic (46d) + currículo --traffic-stages "n:iters,...":
    estágio A n=0 (regressão zero da transferência v10→v14), estágio B
    n=3-5 (principal), estágio C n=7-9 (só se B passar nos gates).
  - Professor de TRÁFEGO rotula: teacher.action(traffic=env.traffic_for(...))
    — a MESMA percepção que a política verá na obs (padrão validado na FASE 2).
  - train_bc com WARM START do checkpoint anterior: os 12 rows de tráfego
    da 1ª Dense ficam ZEROS (herdados da transferência) e SÓ recebem
    gradiente quando os inputs de tráfego forem não-zero (estágio B+);
    no estágio A (inputs zero) o gradiente neles é matematicamente nulo.
  - Gates por estágio (PASSO 3): SEM tráfego (Interlagos 3/3 + Suzuka 3/3
    obrigatório) e COM tráfego (voltas + contatos/lap).

Uso:
  .venv/bin/python model_train/train_dagger.py --obs-mode traffic \
      --traffic-stages "0:2,4:5,8:3" \
      --tracks "interlagos,Monza,Hungaroring,Mexico,procedural:301" \
      --val-track Zandvoort --epochs 50 \
      --init-actor model_train/v14_traffic/init_from_v10.keras \
      --save-dir model_train/v14_traffic
"""
import os, sys, json, math, time
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
from pathlib import Path
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR)):
    sys.path.insert(0, p)
import argparse
import numpy as np


def build_teacher(env, sf=0.80):
    from backend.model_train.reference_controller import ReferenceController
    from backend.model_train.velocity_profile import VelocityProfile
    vp = VelocityProfile(env._wps_arr, grip_mult=0.788, sf=sf,
                         ds_target=4.0, smooth_window_m=20.0)
    return ReferenceController(env, velocity_profile=vp,
                               lookahead_gain=0.6, lookahead_min_m=5.0)


def rollout_episode(env, teacher, actor, beta, rng, max_steps=1600,
                    noise_std=0.15):
    """Roda 1 episódio; devolve (estados, rótulos_do_professor, concluiu, info).

    A ação executada é mistura: a = β·professor + (1-β)·aluno + ruído.
    O RÓTULO é sempre o professor (DAgger: reduz covariate shift).
    FASE 3: o professor rotula COM tráfego — teacher.action(traffic=...),
    a mesma percepção da obs 'traffic' (env.traffic_for é a fonte única).
    """
    obs, _ = env.reset(seed=int(rng.integers(1e9)))
    # grip aleatório: o env amostra grip_override no reset() nativamente
    # (grip_random=(lo,hi) no construtor) — nada a fazer aqui
    states, labels, done = [], [], False
    steps = 0
    info = {}
    while not done and steps < max_steps:
        a_teacher = teacher.action(traffic=env.traffic_for(env.driver_id))
        if actor is not None and rng.random() > beta:
            import tensorflow as tf
            m = actor({k: np.asarray(v)[None] for k, v in obs.items()},
                      training=False).numpy()[0]
            a_student = np.tanh(m)
        else:
            a_student = a_teacher
        # ação executada = mistura + ruído
        a_exec = np.clip(beta * a_teacher + (1 - beta) * a_student +
                         rng.normal(0, noise_std, 2), -1, 1)
        o_copy = {k: np.asarray(v).copy() for k, v in obs.items()}
        states.append(o_copy)
        labels.append(a_teacher.astype(np.float32))  # rótulo SEMPRE do professor
        obs, r, term, trunc, info = env.step(a_exec)
        done = term or trunc
        steps += 1
    return states, labels, bool(info.get('completed_lap', False)), info


def train_bc(states, labels, val_states, val_labels, obs_space, act_dim=2,
            epochs=60, lr=1e-3, verbose=0, init_actor=None):
    """Treina o actor por BC (Huber, split por episódio).

    FASE 3 v14: WARM START de init_actor (transferência v10→v14 ou a iter
    anterior). Sem isso, cada iter recomeçaria de pesos aleatórios e:
    (a) perderia a herança de pilotagem do v10; (b) os 12 rows de tráfego
    nasceriam ALEATÓRIOS em vez de zeros (quebrando o desenho "começa
    ignorando tráfego" do PASSO 1).
    """
    import tensorflow as tf
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    agent = MultiContextPPOAgent(obs_spaces=obs_space, act_dim=act_dim)
    if init_actor is not None:
        agent.actor.set_weights(init_actor.get_weights())
    agent.actor.compile(optimizer=tf.keras.optimizers.Adam(lr), loss=tf.keras.losses.Huber(1.0))
    X = {k: np.array([s[k] for s in states]) for k in states[0]}
    y = np.clip(np.array(labels), -0.98, 0.98)
    y_atanh = 0.5 * (np.log1p(y) - np.log1p(-y))
    if val_states:
        Xv = {k: np.array([s[k] for s in val_states]) for k in val_states[0]}
        yv = np.clip(np.array(val_labels), -0.98, 0.98)
        yv_atanh = 0.5 * (np.log1p(yv) - np.log1p(-yv))
        hist = agent.actor.fit(X, y_atanh, validation_data=(Xv, yv_atanh),
                               epochs=epochs, batch_size=256, verbose=verbose)
        return agent, float(hist.history['val_loss'][-1])
    hist = agent.actor.fit(X, y_atanh, epochs=epochs, batch_size=256, verbose=verbose)
    return agent, float(hist.history['loss'][-1])


def rollout_residual_episode(env, teacher, solo, residual, beta, rng,
                              max_steps=1600, noise_std=0.15):
    """v15 FASE 3: rollout do COMPOSITE (solo congelado + residual).
    Ação executada = β·professor + (1−β)·composite + ruído.
    Rótulo: a_teacher do professor follow; r_target = atanh(a_teacher) − m_solo.
    Retorna (estados, res_inputs, gates, r_targets, completed, info).
    """
    from backend.model_train.residual_gated import (gate_value, build_residual_input)
    from backend.model_train.f1_env import OBS_MODES
    obs, _ = env.reset(seed=int(rng.integers(1e9)))
    states, res_inputs, gates_out, r_targets = [], [], [], []
    done, steps, info = False, 0, {}
    prev_steer, prev_long = 0.0, 0.0
    while not done and steps < max_steps:
        # m_solo do estado atual
        o34 = dict(obs)
        o34['telemetry'] = obs['telemetry'][:34]  # solo consome edge 34d
        m_solo = solo({k: np.asarray(v)[None] for k, v in o34.items()},
                      training=False).numpy()[0]
        a_solo = np.tanh(m_solo)
        # tráfego → res_in + gate
        v_ego = float(info.get('speed', 0.0)) if steps > 0 else 0.0
        if steps == 0:
            # primeiro step: lê do phys
            handle = env.engine.handles[env.driver_id]
            v_ego = env.engine.physics.get_state(handle)['speed_mps']
        traffic_feats = obs['telemetry'][34:46]  # 12d de tráfego da obs
        # d_ahead_min = menor dist do slot com ahead=1
        d_ahead_min = None
        for k in range(3):
            d_norm = traffic_feats[4*k]
            if traffic_feats[4*k+3] > 0.5:  # ahead flag
                d = d_norm * 100.0
                if d_ahead_min is None or d < d_ahead_min:
                    d_ahead_min = d
        g = gate_value(v_ego, d_ahead_min)
        kappa_ahead = float(obs['telemetry'][11]) / 25.0  # obs10 = k@10m*25
        res_in = build_residual_input(traffic_feats, v_ego, kappa_ahead,
                                       prev_steer, prev_long)
        # residual forward (Keras)
        r = residual(np.asarray(res_in)[None], training=False).numpy()[0]
        # composite
        a_comp = np.tanh(m_solo + g * r)
        # professor
        a_teacher = teacher.action(traffic=env.traffic_for(env.driver_id))
        # ação executada = mistura + ruído
        if rng.random() > beta:
            a_exec = a_comp
        else:
            a_exec = a_teacher
        a_exec = np.clip(a_exec + rng.normal(0, noise_std, 2), -1, 1)
        # r_target
        a_t = np.clip(a_teacher, -0.98, 0.98)
        r_t = np.arctanh(a_t) - m_solo
        # grava
        o_copy = {k: np.asarray(v).copy() for k, v in obs.items()}
        states.append(o_copy)
        res_inputs.append(res_in)
        gates_out.append(g)
        r_targets.append(r_t.astype(np.float32))
        # step
        obs, r, term, trunc, info = env.step(a_exec)
        done = term or trunc
        steps += 1
        a_exec_c = np.clip(a_exec, -1, 1)
        prev_steer, prev_long = float(a_exec_c[0]), float(a_exec_c[1])
    return states, res_inputs, gates_out, r_targets, bool(info.get('completed_lap', False)), info


def train_residual_bc(states, res_inputs, gates, r_targets, val_data,
                       residual, epochs=50, lr=1e-3):
    """Treina o residual com Huber em r_target. O SOLO NÃO é tocado."""
    import tensorflow as tf
    residual.compile(optimizer=tf.keras.optimizers.Adam(lr),
                     loss=tf.keras.losses.Huber(1.0))
    X = np.asarray(list(res_inputs), dtype=np.float32).reshape(-1, 16)
    y = np.asarray(list(r_targets), dtype=np.float32).reshape(-1, 2)
    if val_data and len(val_data) >= 2 and len(val_data[0]) > 0:
        Xv = np.asarray(list(val_data[0]), dtype=np.float32).reshape(-1, 16)
        yv = np.asarray(list(val_data[1]), dtype=np.float32).reshape(-1, 2)
        hist = residual.fit(X, y, validation_data=(Xv, yv),
                            epochs=epochs, batch_size=256, verbose=0)
        return float(hist.history['val_loss'][-1])
    hist = residual.fit(X, y, epochs=epochs, batch_size=256, verbose=0)
    return float(hist.history['loss'][-1])


def eval_det_with_time(env, actor, episodes=3, max_steps=1600):
    """Avaliação determinística que também retorna tempos de volta."""
    laps, progs, times = [], [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, steps = False, 0
        info = {}
        while not done and steps < max_steps:
            m = actor({k: np.asarray(v)[None] for k, v in obs.items()},
                      training=False).numpy()[0]
            obs, r, term, trunc, info = env.step(np.tanh(m))
            done = term or trunc
            steps += 1
        laps.append(bool(info.get('completed_lap', False)))
        progs.append(info.get('progress_m', 0))
        if laps[-1]:
            times.append(steps * 0.1)
    return sum(laps), float(np.mean(progs)), times


def eval_deterministic(env, actor, episodes=3, max_steps=1600):
    """Avaliação determinística pura (sem professor, sem ruído)."""
    import tensorflow as tf
    laps, progs = [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, steps = False, 0
        info = {}
        while not done and steps < max_steps:
            m = actor({k: np.asarray(v)[None] for k, v in obs.items()},
                      training=False).numpy()[0]
            obs, r, term, trunc, info = env.step(np.tanh(m))
            done = term or trunc
            steps += 1
        laps.append(bool(info.get('completed_lap', False)))
        progs.append(info.get('progress_m', 0))
    return sum(laps), float(np.mean(progs))


# ------------------------------------------------- gates da FASE 3 (PASSO 3)

def _ego_ghost_contacts(env):
    """Nº de pontos de contato físico entre o chassis do ALUNO e dos
    fantasmas neste instante (instrumento do gate COM tráfego)."""
    import pybullet as pb
    try:
        me = env.engine.handles[env.driver_id].chassis_id
        ghosts = {env.engine.handles[g].chassis_id for g in env._ghost_ids}
        if not ghosts:
            return 0
        n = 0
        for c in pb.getContactPoints(me, physicsClientId=env.engine.physics._client_id):
            if len(c) >= 10 and (c[1] in ghosts or c[2] in ghosts):
                if abs(float(c[9])) > 1.0:
                    n += 1
        return n
    except Exception:
        return 0


def eval_gate(actor, track_resolver, track_name, n_traffic, obs_mode,
              episodes=3, max_steps=1600, count_contacts=False, seed0=0,
              use_teacher=False):
    """PASSO 3 — gate determinístico: grip REAL, SEM respawn, obs do v14.

    count_contacts=True soma os pontos de contato aluno-fantasma por episódio.
    use_teacher=True mede o PROFESSOR com o MESMO instrumento (baseline de
    contatos/lap e voltas p/ comparar com o aluno — nunca compare unidades
    de instrumentos diferentes).
    """
    from backend.model_train.f1_env import F1MultiContextEnv
    env = F1MultiContextEnv(track=track_resolver(track_name), allow_respawn=False,
                            grip_override=None, obs_mode=obs_mode,
                            n_traffic=n_traffic)
    teacher = build_teacher(env) if use_teacher else None
    laps, times, contacts = [], [], 0
    try:
        for ep in range(episodes):
            obs, _ = env.reset(seed=seed0 + ep)
            done, steps = False, 0
            info = {}
            while not done and steps < max_steps:
                if use_teacher:
                    a = teacher.action(traffic=env.traffic_for(env.driver_id))
                else:
                    m = actor({k: np.asarray(v)[None] for k, v in obs.items()},
                              training=False).numpy()[0]
                    a = np.tanh(m)
                obs, r, term, trunc, info = env.step(a)
                steps += 1
                if count_contacts:
                    contacts += _ego_ghost_contacts(env)
                done = term or trunc
            ok = bool(info.get('completed_lap', False))
            laps.append(ok)
            if ok:
                times.append(steps * 0.1)
        n_laps = sum(laps)
        return dict(track=track_name, n_traffic=n_traffic, laps=n_laps,
                    episodes=episodes,
                    time_med=float(np.median(times)) if times else None,
                    contacts=contacts,
                    contacts_per_lap=(contacts / n_laps) if n_laps else None)
    finally:
        env.close()


def update_last_good(last_good, ok_gate, stage_info):
    """PASSO 0.1 (FASE 6): o 'último checkpoint bom' só avança quando o gate
    do estágio PASSA. Reprovado → mantém o verde anterior (ou None)."""
    return dict(stage_info) if ok_gate else last_good


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--obs-mode', default='edge',
                    choices=['legacy', 'edge', 'traffic'])
    ap.add_argument('--tracks', default='interlagos,Monza,Hungaroring,Silverstone')
    ap.add_argument('--val-track', default='Zandvoort')
    ap.add_argument('--iters', type=int, default=10,
                    help='ignorado quando --traffic-stages é dado')
    ap.add_argument('--episodes-per-track', type=int, default=2)
    ap.add_argument('--beta-start', type=float, default=1.0)
    ap.add_argument('--beta-end', type=float, default=0.0)
    ap.add_argument('--noise-std', type=float, default=0.15)
    ap.add_argument('--sf', type=float, default=0.80)
    ap.add_argument('--epochs', type=int, default=60)
    ap.add_argument('--init-actor', type=str, default=None,
                    help='checkpoint inicial (transferência v10→v14 na FASE 3)')
    ap.add_argument('--save-dir', required=True)
    ap.add_argument('--seed', type=int, default=42)
    # --- FASE 3 v14: currículo de tráfego --------------------------------
    ap.add_argument('--n-traffic', type=int, default=0,
                    help='nº de fantasmas (estágio único, sem --traffic-stages)')
    ap.add_argument('--traffic-stages', type=str, default=None,
                    help='currículo "n:iters,n:iters,..." — ex: "0:2,4:5,8:3"')
    ap.add_argument('--gate-tracks', type=str, default='interlagos,Suzuka',
                    help='pistas do gate SEM tráfego (Suzuka 3/3 obrigatório)')
    ap.add_argument('--residual', action='store_true',
                    help='v15 FASE 3: treina SÓ o residual (base v10 CONGELADA); '
                         'ação = composite; r_target = atanh(a_teacher) − m_solo')
    ap.add_argument('--solo-actor', type=str,
                    default='model_train/v10_dagger/dagger_actor_best.keras',
                    help='caminho do ator solo (v10) para o modo --residual')
    ap.add_argument('--solo-anchor', type=int, default=0,
                    help='FASE 6: eps SOLO (professor puro, n=0) por iter nos '
                         'estagios com trafego — ancora anti-esquecimento '
                         '(diagnostico: estagio B do v14b perdeu os esses de '
                         'Suzuka sem isso); rotaciona pelas pistas do pool')
    ap.add_argument('--ghost-hold', type=str, default=None,
                    help='FASE 6: "lo:hi" ticks — fantasmas PARAM no meio do '
                         'episodio (rotulos de contorno de carro parado)')
    ap.add_argument('--ghost-hold-n', type=int, default=1)
    ap.add_argument('--ghost-sf-range', type=str, default=None,
                    help='v15 FASE 3: "lo:hi" — sf por fantasma (heterogêneo)')
    ap.add_argument('--ghost-mix', type=str, default=None,
                    help='v15 FASE 3 r2: "uniform,hetero,hold,grid57" — '
                         'ROUND-ROBIN por episódio (determinístico). '
                         'uniform=sf 0,80 P10 | hetero=sf-range P10 | '
                         'hold=1 fantasma para+uniformes P10 | '
                         'grid57=hetero+grid_position(5,7)')
    ap.add_argument('--grid-position', type=str, default=None,
                    help='FASE 6: "lo:hi" (P5-P7) ou int — aluno no meio do '
                         'grid: fantasmas a frente E ATRAS (obs ahead=0)')
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out = Path(args.save_dir)
    out.mkdir(parents=True, exist_ok=True)
    tracks = [t.strip() for t in args.tracks.split(',')]
    gate_tracks = [t.strip() for t in args.gate_tracks.split(',')]

    # currículo: [(n_traffic, iters), ...]
    if args.traffic_stages:
        stages = []
        for part in args.traffic_stages.split(','):
            n_s, it_s = part.strip().split(':')
            stages.append((int(n_s), int(it_s)))
        if sum(it for _, it in stages) != args.iters:
            print(f"[INFO] --iters={args.iters} ignorado; --traffic-stages soma "
                  f"{sum(it for _, it in stages)} iters")
    else:
        stages = [(args.n_traffic, args.iters)]
    total_iters = sum(it for _, it in stages)

    # carrega envs (suporta 'procedural:<seed>' além de nomes FastF1)
    from backend.model_train.f1_env import F1MultiContextEnv

    # parâmetros validados por seed (do gate da Parte 2 — ver AUDITORIA_RL.md)
    PROCEDURAL_PARAMS = {
        101: dict(n_hairpins=2, n_esses=0),   # hairpin_A
        103: dict(n_hairpins=2, n_esses=0),   # hairpin_B
        107: dict(n_hairpins=3, n_esses=0),   # hairpin_C
        201: dict(n_hairpins=0, n_esses=3),   # esse_A
        203: dict(n_hairpins=0, n_esses=4),   # esse_B
        301: dict(n_hairpins=2, n_esses=2),   # mista_A
    }

    def _resolve(name):
        if name.startswith('procedural:'):
            from backend.model_train.procedural_track import generate_track
            seed = int(name.split(':')[1])
            params = PROCEDURAL_PARAMS.get(seed, dict(n_hairpins=2, n_esses=1))
            t = generate_track(seed=seed, **params)
            if t is None:
                raise ValueError(f"procedural:{seed} foi rejeitada pelo gate de kappa")
            return t
        return name  # nome FastF1

    def _parse_range(spec):
        if spec is None:
            return None
        if ':' in spec:
            lo, hi = spec.split(':')
            return (int(lo), int(hi))
        return int(spec)

    grid_pos = _parse_range(args.grid_position)
    hold_rng = _parse_range(args.ghost_hold)

    # v15 FASE 3 r2: mix de fantasmas ROUND-ROBIN por episódio
    ghost_mix = ([c.strip() for c in args.ghost_mix.split(',')]
                  if args.ghost_mix else None)
    _mix_counter = {'i': 0}
    def _mix_kwargs():
        """Retorna (kwargs_extras, rótulo da config) para o episódio atual.
        Round-robin determinístico: garante proporção EXATA das configs."""
        if ghost_mix is None:
            kw = {}
            if hold_rng is not None:
                kw['ghost_hold_ticks'] = hold_rng
                kw['ghost_hold_n'] = args.ghost_hold_n
            if grid_pos is not None:
                kw['grid_position'] = grid_pos
            if args.ghost_sf_range is not None:
                lo2, hi2 = args.ghost_sf_range.split(':')
                kw['ghost_sf_range'] = (float(lo2), float(hi2))
            return kw, 'fixed'
        cfg = ghost_mix[_mix_counter['i'] % len(ghost_mix)]
        _mix_counter['i'] += 1
        kw = {}
        if cfg == 'uniform':
            pass  # sf único 0,80 (default), P10 (default), sem hold
        elif cfg == 'hetero':
            if args.ghost_sf_range is not None:
                lo2, hi2 = args.ghost_sf_range.split(':')
                kw['ghost_sf_range'] = (float(lo2), float(hi2))
        elif cfg == 'hold':
            if hold_rng is not None:
                kw['ghost_hold_ticks'] = hold_rng
                kw['ghost_hold_n'] = args.ghost_hold_n
        elif cfg == 'grid57':
            if args.ghost_sf_range is not None:
                lo2, hi2 = args.ghost_sf_range.split(':')
                kw['ghost_sf_range'] = (float(lo2), float(hi2))
            kw['grid_position'] = (5, 7)
        else:
            raise ValueError(f"ghost-mix config desconhecida: {cfg}")
        return kw, cfg

    def _build_envs(n_traffic):
        envs, teachers = {}, {}
        kw = dict(allow_respawn=False, grip_random=(0.70, 1.0),
                  obs_mode=args.obs_mode, n_traffic=n_traffic)
        if n_traffic > 0:
            # FASE 6: fantasmas parados + carros atras (anti-encravamento)
            if hold_rng is not None:
                kw['ghost_hold_ticks'] = hold_rng
                kw['ghost_hold_n'] = args.ghost_hold_n
            if grid_pos is not None:
                kw['grid_position'] = grid_pos
            if args.ghost_sf_range is not None:
                lo2, hi2 = args.ghost_sf_range.split(':')
                kw['ghost_sf_range'] = (float(lo2), float(hi2))
        for tr in tracks + [args.val_track]:
            envs[tr] = F1MultiContextEnv(track=_resolve(tr), **kw)
            teachers[tr] = build_teacher(envs[tr], args.sf)
        return envs, teachers

    envs, teachers = _build_envs(stages[0][0])

    # ============ v15 FASE 3: modo --residual (base CONGELADA) =========
    if args.residual:
        import tensorflow as tf
        from backend.model_train.residual_gated import (CompositeActor,
                                                         build_residual_keras)
        solo = tf.keras.models.load_model(args.solo_actor, compile=False)
        residual = build_residual_keras()
        print(f"[residual] solo CONGELADO: {args.solo_actor}")
        print(f"[residual] estágios: {stages} | pool: {tracks} | âncora dupla ON")
        all_states_r, all_res_in, all_gates, all_r_t = [], [], [], []
        val_ri, val_rt = [], []
        global_iter_r = 0
        total_iters_r = sum(it for _, it in stages)
        for s_idx, (n_stage, n_iters) in enumerate(stages):
            if s_idx > 0 and n_stage != stages[s_idx - 1][0]:
                for e in envs.values(): e.close()
                envs, teachers = _build_envs(n_stage)
            print(f"\n[ESTÁGIO {s_idx}] n_traffic={n_stage}, {n_iters} iters")
            for _ in range(n_iters):
                beta = args.beta_start + (args.beta_end - args.beta_start) * \
                       global_iter_r / max(total_iters_r - 1, 1)
                t0 = time.time()
                it_ri, it_rt = [], []
                for tr in tracks:
                    for ep_i in range(args.episodes_per_track):
                        mix_kw, mix_label = _mix_kwargs()
                        ep_env = F1MultiContextEnv(
                            track=_resolve(tr), allow_respawn=False,
                            grip_random=(0.70, 1.0), obs_mode=args.obs_mode,
                            n_traffic=n_stage, **mix_kw)
                        try:
                            ep_teacher = build_teacher(ep_env)
                            ss, ri, gg, rt, ok, info = rollout_residual_episode(
                                ep_env, ep_teacher, solo, residual, beta, rng,
                                noise_std=args.noise_std)
                            print(f"    [ep {ep_i+1}/{args.episodes_per_track}] "
                                  f"{tr} mix={mix_label} n={n_stage}", flush=True)
                        finally:
                            ep_env.close()
                        it_ri.extend(ri); it_rt.extend(rt)
                # âncora (a): eps n=0 com r_target=0
                if args.solo_anchor > 0:
                    for k in range(args.solo_anchor):
                        tr_s = tracks[(global_iter_r * args.solo_anchor + k) % len(tracks)]
                        env_s = F1MultiContextEnv(track=_resolve(tr_s),
                                                  allow_respawn=False,
                                                  grip_random=(0.70, 1.0),
                                                  obs_mode=args.obs_mode,
                                                  n_traffic=0)
                        try:
                            ss, ri, gg, rt, ok, info = rollout_residual_episode(
                                env_s, teachers.get(tr_s, build_teacher(env_s)),
                                solo, residual, beta, rng, noise_std=args.noise_std)
                            rt = [np.zeros_like(x) for x in rt]  # r_target = 0
                        finally:
                            env_s.close()
                        it_ri.extend(ri); it_rt.extend(rt)
                # val
                ss, ri, gg, rt, ok, info = rollout_residual_episode(
                    envs[args.val_track], teachers[args.val_track],
                    solo, residual, beta, rng, noise_std=args.noise_std)
                val_ri.extend(ri); val_rt.extend(rt)
                all_res_in.extend(it_ri); all_r_t.extend(it_rt)
                print(f"[iter {global_iter_r+1}/{total_iters_r}] β={beta:.2f} "
                      f"n={n_stage} | dataset: {len(all_res_in)} (+{len(it_ri)})", flush=True)
                val_loss = train_residual_bc(None, all_res_in, None,
                                             all_r_t,
                                             (val_ri, val_rt), residual,
                                             epochs=args.epochs)
                global_iter_r += 1
                ckpt = out / f'residual_iter{global_iter_r}.keras'
                residual.save(str(ckpt))
                print(f"  val_loss={val_loss:.4f} | salvo {ckpt.name}", flush=True)
                # congelamento: verifica a cada iter
                h = CompositeActor(args.solo_actor)
                print(f"  solo_hash_estável: {h.freeze_hash()[:16]}...", flush=True)
        # salva o melhor (menor val_loss = último aqui; seleção real na FASE 4)
        import shutil
        best_src = out / f'residual_iter{total_iters_r}.keras'
        shutil.copy(str(best_src), str(out / 'residual_best.keras'))
        print(f"\n[residual] best -> {out / 'residual_best.keras'}")
        # exporta NPZ p/ o motor NumPy do runner
        from backend.model_train.residual_gated import export_residual_npz
        export_residual_npz(residual, out / 'residual_best_weights.npz')
        print(f"[residual] NPZ -> {out / 'residual_best_weights.npz'}")
        for e in envs.values(): e.close()
        return

    # dataset (AGREGA entre estágios — DAgger clássico)
    all_states, all_labels = [], []
    val_states, val_labels = [], []
    actor = None
    if args.init_actor:
        import tensorflow as tf
        print(f"[INFO] init_actor: {args.init_actor}")
        actor = tf.keras.models.load_model(args.init_actor, compile=False)
    meta = {'iters': [], 'obs_mode': args.obs_mode, 'sf': args.sf,
            'tracks': tracks, 'val_track': args.val_track,
            'stages': [dict(n_traffic=n, iters=it) for n, it in stages],
            'gates': [], 'init_actor': args.init_actor}

    # lição v13: verificação
    print(f"[protocolo] allow_respawn={envs[tracks[0]].allow_respawn}", flush=True)

    global_iter = 0
    last_good = None
    stage_stop = False
    for s_idx, (n_stage, n_iters) in enumerate(stages):
        if stage_stop:
            break
        if s_idx > 0 and n_stage != stages[s_idx - 1][0]:
            for e in envs.values():
                e.close()
            envs, teachers = _build_envs(n_stage)
            print(f"\n[ESTÁGIO {s_idx}] n_traffic={n_stage} — envs reconstruídos "
                  f"({len(envs)} pistas)", flush=True)
        print(f"\n========== ESTÁGIO {s_idx}: n_traffic={n_stage}, {n_iters} iters ==========",
              flush=True)

        stage_iters_meta = []
        for _ in range(n_iters):
            beta = args.beta_start + (args.beta_end - args.beta_start) * \
                global_iter / max(total_iters - 1, 1)
            t0 = time.time()
            it_states, it_labels = [], []
            for tr in tracks:
                env, teacher = envs[tr], teachers[tr]
                for _ in range(args.episodes_per_track):
                    ss, ll, ok, info = rollout_episode(
                        env, teacher, actor, beta, rng, noise_std=args.noise_std)
                    it_states.extend(ss)
                    it_labels.extend(ll)
            # FASE 6: ANCORA DE REPLAY — eps solo frescas (professor puro,
            # n=0, grip_random igual ao treino) rotacionando pelo pool: a
            # pilotagem limpa nunca perde gradiente para os dados de trafego.
            if n_stage > 0 and args.solo_anchor > 0:
                for k in range(args.solo_anchor):
                    tr_s = tracks[(global_iter * args.solo_anchor + k) % len(tracks)]
                    env_s = F1MultiContextEnv(track=_resolve(tr_s),
                                              allow_respawn=False,
                                              grip_random=(0.70, 1.0),
                                              obs_mode=args.obs_mode,
                                              n_traffic=0)
                    try:
                        ss, ll, ok, _ = rollout_episode(
                            env_s, build_teacher(env_s), actor, beta, rng,
                            noise_std=args.noise_std)
                    finally:
                        env_s.close()
                    it_states.extend(ss)
                    it_labels.extend(ll)
            for _ in range(1):
                ss, ll, ok, _ = rollout_episode(envs[args.val_track],
                                                teachers[args.val_track],
                                                actor, beta, rng, noise_std=args.noise_std)
                val_states.extend(ss)
                val_labels.extend(ll)

            all_states.extend(it_states)
            all_labels.extend(it_labels)
            print(f"[iter {global_iter+1}/{total_iters}] estágio {s_idx} β={beta:.2f} "
                  f"n_traffic={n_stage} | dataset: {len(all_states)} (+{len(it_states)})",
                  flush=True)

            # treina (WARM START do actor anterior/transferência)
            agent, val_loss = train_bc(all_states, all_labels, val_states,
                                       val_labels, envs[tracks[0]].observation_space,
                                       epochs=args.epochs, init_actor=actor)
            actor = agent.actor

            # avalia determinístico em treino (2 eps) + VAL (3 eps, seleção)
            eval_results = {}
            for tr in tracks:
                laps, prog = eval_deterministic(envs[tr], actor, episodes=2)
                eval_results[tr] = dict(laps=laps, prog=prog)
                print(f"  {tr:18s}: {laps}/2 voltas | prog={prog:.0f}m", flush=True)
            vl_laps, vl_prog, vl_times = eval_det_with_time(envs[args.val_track], actor, episodes=3)
            eval_results[args.val_track] = dict(laps=vl_laps, prog=vl_prog,
                                                time_med=float(np.median(vl_times)) if vl_times else None)
            print(f"  {args.val_track:18s}: {vl_laps}/3 voltas | "
                  f"tempo={np.median(vl_times) if vl_times else '—'}s", flush=True)

            n_val_laps = eval_results[args.val_track]['laps']
            iter_meta = dict(iter=global_iter + 1, stage=s_idx, n_traffic=n_stage,
                             beta=beta, dataset=len(all_states), val_loss=val_loss,
                             eval=eval_results, elapsed_s=time.time() - t0)
            meta['iters'].append(iter_meta)
            stage_iters_meta.append(iter_meta)
            json.dump(meta, open(out / 'training_meta.json', 'w'), indent=1)

            ckpt = out / f'dagger_actor_iter{global_iter+1}.keras'
            actor.save(ckpt)
            print(f"  val_loss={val_loss:.4f} | salvo {ckpt.name}", flush=True)
            global_iter += 1

        # melhor do ESTÁGIO (voltas VAL; desempate: tempo mediano, val_loss)
        def _sel_key(x):
            vl = x['eval'][args.val_track]
            return (vl['laps'], -(vl.get('time_med') or 9999), -x['val_loss'])
        best_iter = max(stage_iters_meta, key=_sel_key)
        best_src = out / f'dagger_actor_iter{best_iter["iter"]}.keras'
        import shutil
        best_dst = out / f'dagger_actor_best_s{s_idx}_n{n_stage}.keras'
        shutil.copy(best_src, best_dst)
        print(f"[estágio {s_idx}] melhor: iter {best_iter['iter']} -> {best_dst.name}",
              flush=True)
        # LIÇÃO FASE 3/4 (limitação 8): gate e CONTINUAÇÃO no BEST-POR-VAL —
        # nunca no último ator. Com β→0 os dados do aluno (ruído 0,15)
        # dominam o dataset e o ator final degrada (iter 10 da FASE 3:
        # Suzuka 0/3 com o best do estágio passando em tudo).
        import tensorflow as tf
        actor = tf.keras.models.load_model(str(best_dst), compile=False)

        # ---------------- PASSO 3: gates do estágio ----------------
        print(f"\n----- GATES do estágio {s_idx} (n_traffic={n_stage}) -----", flush=True)
        gate = dict(stage=s_idx, n_traffic=n_stage, best=str(best_dst))
        ok_gate = True
        for tr in gate_tracks:
            g1 = eval_gate(actor, _resolve, tr, n_traffic=0, obs_mode=args.obs_mode)
            gate[f'no_traffic_{tr}'] = g1
            ok = g1['laps'] == g1['episodes']
            ok_gate = ok_gate and ok
            print(f"  G1 sem tráfego {tr:12s}: {g1['laps']}/{g1['episodes']} voltas "
                  f"{'' if ok else '<< FALHOU'} | tempo={g1['time_med'] and round(g1['time_med'],1)}s",
                  flush=True)
            if 'Suzuka' in tr and g1['laps'] < g1['episodes']:
                print("  >> Suzuka 3/3 é OBRIGATÓRIO (task v14) — gate do estágio FALHOU",
                      flush=True)
        if n_stage > 0:
            # baseline do PROFESSOR com o MESMO instrumento (nunca comparar
            # contatos de unidades diferentes) — referência de contatos/lap
            tb = eval_gate(None, _resolve, 'interlagos', n_traffic=n_stage,
                           obs_mode=args.obs_mode, count_contacts=True,
                           use_teacher=True)
            gate['teacher_baseline'] = tb
            print(f"  [professor n={n_stage}]: {tb['laps']}/{tb['episodes']} voltas | "
                  f"contatos/lap={tb['contacts_per_lap'] and round(tb['contacts_per_lap'], 1)} | "
                  f"tempo={tb['time_med'] and round(tb['time_med'], 1)}s", flush=True)
            g2 = eval_gate(actor, _resolve, 'interlagos', n_traffic=n_stage,
                           obs_mode=args.obs_mode, count_contacts=True)
            gate['with_traffic'] = g2
            print(f"  G2 com tráfego n={n_stage}: {g2['laps']}/{g2['episodes']} voltas "
                  f"| contatos/lap={g2['contacts_per_lap'] and round(g2['contacts_per_lap'], 1)}",
                  flush=True)
            if g2['laps'] < 2:
                print("  >> menos de 2/3 voltas com tráfego — FALHOU", flush=True)
                ok_gate = False
        gate['passed'] = ok_gate
        # PASSO 0.1 (FASE 6): last_good só avança DEPOIS do gate passar —
        # antes, a linha [FINAL] apontava um checkpoint REPROVADO (v14b).
        last_good = update_last_good(
            last_good, ok_gate,
            dict(stage=s_idx, n_traffic=n_stage, path=str(best_dst),
                 iter=best_iter['iter']))
        meta['gates'].append(gate)
        json.dump(meta, open(out / 'training_meta.json', 'w'), indent=1)
        if not ok_gate:
            # PASSO 0 (sessão final): o estágio 0 pode reprovar (last_good
            # ainda None) — nunca crash no relatório
            if last_good is None:
                print(f"\n[GATE FALHOU no estágio {s_idx}] NENHUM estágio verde "
                      f"ainda — nenhum checkpoint aprovado neste run.", flush=True)
            else:
                print(f"\n[GATE FALHOU no estágio {s_idx}] Parando no último "
                      f"checkpoint bom: {last_good['path']} (estágio "
                      f"{last_good['stage']}, iter {last_good['iter']})", flush=True)
            stage_stop = True

    # resumo final
    if last_good:
        meta['last_good'] = last_good
    json.dump(meta, open(out / 'training_meta.json', 'w'), indent=1)
    print(f"\n[FINAL] último checkpoint bom: {last_good['path'] if last_good else None}")
    for e in envs.values():
        e.close()


if __name__ == '__main__':
    main()
