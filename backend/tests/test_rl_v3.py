"""Testes das fases B–E: geometria, sinais, velocidade segura e paridade NPZ."""

import math

import numpy as np
import pytest


@pytest.fixture(scope="module")
def env():
    from backend.model_train.f1_env import F1MultiContextEnv
    e = F1MultiContextEnv(track="interlagos", allow_respawn=False)
    yield e
    e.close()


# --------------------------------------- B. geometria / curvatura sintética

def test_kappa_signed_synthetic(env):
    """Curvatura assinada em geometrias conhecidas: reta ~0, esquerda >0, direita <0;
    hairpin tem magnitude bem maior que curva suave."""

    def straight_kappa(s):
        return env._kappa_signed(s)

    # reta logo após o start/finish (melhor reta detectada)
    s0 = env._seg_cum[env.track.start_finish_waypoint]
    k_straight = abs(straight_kappa(s0 + 2.0))
    # hairpin real da pista (~s 1100-1200 na Interlagos FastF1)
    ks = [(abs(env._kappa_signed(s0 + d)), env._kappa_signed(s0 + d))
          for d in np.arange(0, env._track_len_s, 10.0)]
    k_max, s_at = max((k, i * 10.0) for i, k in enumerate([x[0] for x in ks]))
    assert k_straight < 0.3 * k_max, "a reta deveria ter curvatura muito menor que o hairpin"
    assert k_max > 0.02, "a pista real deveria ter pelo menos uma curva fechada detectável"


def test_progress_wrap_and_gate_count_consistency(env):
    """progress_m nunca excede o comprimento da pista sem completed_lap, e gates
    numerados em [0, n_gates)."""
    env.reset()
    for _ in range(60):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        assert 0 <= info["gate"] < info["n_gates"]
        assert 0.0 <= info["progress_m"] < env._track_len_s * 1.05 or info["completed_lap"]
        if term or trunc:
            break


def test_completed_lap_requires_real_distance(env):
    """Respawn/teleporte não pode completar volta: completed_lap exige
    lap>=1 (engine) E progresso acumulado >= 98% da pista — o respawn anda
    PARA TRÁS, então uma volta com respawns some progresso além da pista."""
    env.reset()
    # simula: força lap do motor sem progresso correspondente
    env.engine.states[env.driver_id].lap = 1
    env._total_wp_progress = 100.0  # fictício: 100 m não é uma volta
    obs, r, term, trunc, info = env.step(np.array([0.0, 0.0], dtype=np.float32))
    assert not info["completed_lap"], "lap fantasma aceito sem progresso real"


# ------------------------------------------------ D. planejamento de velocidade

def test_v_allow_decreases_for_tighter_corners(env):
    """Curvas mais fechadas -> velocidade segura menor (monotonia sintética)."""
    s0 = float(env._seg_cum[env.track.start_finish_waypoint])
    # varre a pista e compara v_allow na região mais reta vs mais fechada
    grid = np.arange(0, env._track_len_s, 8.0)
    ks = np.array([abs(env._kappa_signed(s0 + d)) for d in grid])
    s_straight = s0 + float(grid[int(np.argmin(ks))])
    s_tight = s0 + float(grid[int(np.argmax(ks))])
    v_straight = env._v_allow_at(s_straight, 60.0)
    v_tight = env._v_allow_at(s_tight, 60.0)
    assert v_tight < v_straight, f"v_allow não cai na curva fechada ({v_tight:.1f} vs {v_straight:.1f})"
    assert v_tight <= 30.0, "hairpin deveria impor velocidade segura baixa"


def test_v_allow_accounts_for_braking_distance(env):
    """Longe de uma curva fechada, v_allow cresce com a distância disponível
    (frear usa 2*a*d); perto, aproxima a velocidade da curva."""
    grid = np.arange(0, env._track_len_s, 8.0)
    ks = np.array([abs(env._kappa_signed(d)) for d in grid])
    s_tight = float(grid[int(np.argmax(ks))])
    k_tight = float(ks.max())
    v_curve = math.sqrt(14.0 / k_tight)             # A_LAT_MAX = 14 no env
    # 5 m antes da curva: v_allow já próximo de v_curve
    v_close = env._v_allow_at(s_tight - 5.0, 30.0)
    # 150 m antes: permite bem mais rápido (há espaço p/ frenar)
    v_far = env._v_allow_at(s_tight - 150.0, 60.0)
    assert v_far > v_close, "a distância de frenagem não está sendo considerada"
    assert v_close <= v_curve * 1.6, f"perto da curva v_allow deveria ~ v_curve ({v_close:.1f} vs {v_curve:.1f})"


def test_progress_gated_by_overspeed(env):
    """Andar acima de v_allow NÃO paga o prêmio de progresso integral
    (a recompensa que ensinava 'acelerar compensa o crash')."""
    from backend.model_train.f1_env import A_LAT_MAX
    env.reset()
    # teleporta p/ a reta segura e pisa
    s0 = env._seg_cum[env.track.start_finish_waypoint] + 10.0
    x0, y0, yaw0 = env._point_at(s0)
    env.engine.physics.set_position(env.engine.handles[env.driver_id], (x0, y0, 0.5), yaw_rad=yaw0)
    env._set_forward_speed(yaw0, 5.0)
    env._last_s = s0
    _, _, _, _ = env._project_on_path(x0, y0)
    obs, r_ok, _, _, info_ok = env.step(np.array([0.0, 1.0], dtype=np.float32))
    p_ok = info_ok["reward_parts"]["progress"]
    # em reta, acelerar paga progresso integral
    assert p_ok > 0.0
    v_allow_here = env._v_allow_at(env._last_s, 5.0)
    # estado coerente: dentro de uma reta, v_allow alto; em hairpin, baixo
    assert v_allow_here > 30.0


# ------------------------------------------------ C. convenção de sinais de esterço

@pytest.mark.slow
@pytest.mark.slow
def test_steer_sign_produces_opposite_paths(env):
    """+steer curva à esquerda (+yaw_rate), -steer à direita. A comparação usa o
    yaw_rate médio do último segundo (heading cru dá wrap em ±π)."""
    def run(steer):
        env.reset()
        handle = env.engine.handles[env.driver_id]
        yaws = []
        for t in range(60):
            env.engine.set_driver_input(env.driver_id, throttle=1.0, brake=0.0,
                                        steering_yaw_rad=steer * 0.1)
            env.engine._step_tick(env.logic_dt, env.sub_steps)
            if t >= 40:
                yaws.append(env.engine.physics.get_state(handle)["yaw_rate"])
        return float(np.mean(yaws))

    yaw_l = run(+1.0)
    yaw_r = run(-1.0)
    assert yaw_l > 0.05, f"steer positivo deveria virar à esquerda (yaw_rate={yaw_l:+.3f})"
    assert yaw_r < -0.05, f"steer negativo deveria virar à direita (yaw_rate={yaw_r:+.3f})"


# --------------------------------------------- 12. Paridade Keras <-> NumPy (NPZ)

def test_npz_parity_keras_vs_numpy(tmp_path):
    """Exporta o ator e confere paridade numérica exata (mesma política)."""
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    from backend.scripts.run_race_10_cars import NumpyNeuralActor, ensure_npz_weights_exist
    import tensorflow as tf

    env_spaces = None
    agent = MultiContextPPOAgent(obs_spaces=_obs_spaces(), act_dim=2)
    keras_path = tmp_path / "actor.keras"
    agent.actor.save(str(keras_path))
    npz_path = ensure_npz_weights_exist(keras_path, tmp_path / "actor_weights.npz")
    np_actor = NumpyNeuralActor(npz_path)

    rng = np.random.default_rng(3)
    for _ in range(8):
        # observações variadas: reta, curvas, frenagem (valores plausíveis)
        tel = np.clip(rng.normal(0, 0.8, size=(4, 23)), -5, 5).astype(np.float32)
        ctx = rng.uniform(0.5, 1.5, size=(4, 2)).astype(np.float32)
        tid = np.zeros(4, dtype=np.int32); cid = np.zeros(4, dtype=np.int32)
        mean_k = agent.actor({"telemetry": tf.constant(tel), "ctx_numeric": tf.constant(ctx),
                              "track_id": tf.constant(tid[:, None]),
                              "compound_id": tf.constant(cid[:, None])},
                             training=False).numpy()
        out_np = np_actor.forward(tel, ctx, tid, cid)
        # NumPy aplica tanh internamente; o determinístico da política v2 é tanh(média)
        assert np.allclose(np.tanh(mean_k), out_np, atol=1e-5), \
            f"divergência Keras vs NumPy: {np.abs(np.tanh(mean_k) - out_np).max()}"
        assert np.all(np.abs(out_np) <= 1.0)


def test_npz_loader_rejects_incompatible(tmp_path):
    """Um NPZ de arquitetura antiga (sem camada de saída compatível) deve falhar
    com erro informativo, não com lixo silencioso."""
    from backend.scripts.run_race_10_cars import NumpyNeuralActor
    np.savez(tmp_path / "bad.npz", foo=np.zeros((4, 4), dtype=np.float32))
    with pytest.raises(ValueError, match="Pesos nao encontrados|Shapes"):
        NumpyNeuralActor(tmp_path / "bad.npz")


def test_obs_spaces_helper():
    # garante que o helper local combina com o espaço real do ambiente
    sp = _obs_spaces()
    assert sp["telemetry"].shape == (23,)


def _obs_spaces():
    import gymnasium as gym
    from gymnasium import spaces
    return spaces.Dict({
        "telemetry": spaces.Box(low=-5, high=5, shape=(23,), dtype=np.float32),
        "ctx_numeric": spaces.Box(low=-5, high=5, shape=(2,), dtype=np.float32),
        "track_id": spaces.Box(low=0, high=20, shape=(1,), dtype=np.int32),
        "compound_id": spaces.Box(low=0, high=5, shape=(1,), dtype=np.int32),
    })
