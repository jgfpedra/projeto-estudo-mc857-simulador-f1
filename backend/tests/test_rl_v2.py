"""Testes da arquitetura RL v2 (ambiente, ações 2D, PPO squashed, baseline clássico).

Cobre:
1. Conformidade Gymnasium (reset/step/spaces/dtypes).
2. Ausência de NaN/inf em observações e recompensas com ações aleatórias.
3. Semântica de sinais: erro lateral, heading, curvatura, comando longitudinal.
4. Conversão de ações [steer, long] -> (throttle, brake, steer_rad) e legado 3D.
5. Política tanh-squashed: ações sempre em (-1,1), logp consistente (ratio==1).
6. Checkpoints do PPO salvam/carregam com os shapes atuais.
7. Respawn não gera progresso fictício.
8. Baseline (pure pursuit + planejador) completa uma volta sem respawn — prova
   separável de física/percepção vs aprendizado.
"""

import math

import numpy as np
import pytest


@pytest.fixture(scope="module")
def env():
    from backend.model_train.f1_env import F1MultiContextEnv
    e = F1MultiContextEnv(track="interlagos", allow_respawn=True)
    yield e
    e.close()


@pytest.fixture(scope="module")
def env_eval():
    from backend.model_train.f1_env import F1MultiContextEnv
    e = F1MultiContextEnv(track="interlagos", allow_respawn=False)
    yield e
    e.close()


# ---------------------------------------------------------------- 1. API Gym

def test_reset_is_gymnasium_compliant(env):
    obs, info = env.reset()
    assert isinstance(info, dict)
    assert env.observation_space.contains(obs)


def test_step_returns_valid_tuple(env):
    env.reset()
    out = env.step(env.action_space.sample())
    obs, reward, terminated, truncated, info = out
    assert env.observation_space.contains(obs)
    assert np.isfinite(reward)
    assert isinstance(terminated, bool) and isinstance(truncated, bool)
    assert "progress_m" in info and "completed_lap" in info and "reward_parts" in info


def test_obs_shape_and_action_dim(env):
    from backend.model_train.f1_env import N_OBS_TELEMETRY
    obs, _ = env.reset()
    assert obs["telemetry"].shape == (N_OBS_TELEMETRY,)
    assert env.action_space.shape == (2,)
    assert np.allclose(env.action_space.low, -1.0) and np.allclose(env.action_space.high, 1.0)


# ------------------------------------------------- 2. NaN/inf com ações aleatórias

def test_no_nan_over_random_rollout(env):
    env.reset()
    rng = np.random.default_rng(0)
    for _ in range(120):
        a = rng.uniform(-1.0, 1.0, size=2).astype(np.float32)
        obs, r, term, trunc, info = env.step(a)
        assert np.all(np.isfinite(obs["telemetry"])), "NaN/inf na observação"
        assert np.isfinite(r), "recompensa não-finita"
        if term or trunc:
            env.reset()


# ------------------------------------------------------- 3. Conversão de ações

def test_action_to_controls_v2_semantics():
    from backend.model_train.f1_env import F1MultiContextEnv
    th, br, st = F1MultiContextEnv.action_to_controls([0.0, 1.0], 10.0)
    assert th == 1.0 and br == 0.0                      # long>0 -> throttle
    th, br, st = F1MultiContextEnv.action_to_controls([0.0, -1.0], 10.0)
    assert th == 0.0 and br == 1.0                      # long<0 -> brake
    th, br, st = F1MultiContextEnv.action_to_controls([1.0, 0.0], 0.0)
    lim = F1MultiContextEnv.steer_limit_rad(0.0)
    assert abs(st - lim) < 1e-9                         # steer=+1 -> lock total
    # limite encolhe com a velocidade
    assert F1MultiContextEnv.steer_limit_rad(60.0) < F1MultiContextEnv.steer_limit_rad(10.0)


def test_action_to_controls_legacy_3d():
    from backend.model_train.f1_env import F1MultiContextEnv
    th, br, st = F1MultiContextEnv.action_to_controls([0.7, 0.0, -0.5], 30.0)
    assert th == pytest.approx(0.7) and br == 0.0 and st < 0


# ------------------------------------------------- 4. Sinais (lateral/heading/kappa)

def test_signed_lateral_and_heading_sign(env):
    env.reset()
    # teleporta o carro 3 m à ESQUERDA da linha no start/finish
    s0 = env._seg_cum[env.track.start_finish_waypoint]
    x0, y0, yaw0 = env._point_at(s0 + 5.0)
    nx, ny = -math.sin(yaw0), math.cos(yaw0)
    env.engine.physics.set_position(env.engine.handles[env.driver_id],
                                    (x0 + 3 * nx, y0 + 3 * ny, 0.5), yaw_rad=yaw0)
    _, _, _, signed = env._project_on_path(x0 + 3 * nx, y0 + 3 * ny)
    assert signed > 0                      # esquerda da linha = positivo
    k_left = env._kappa_signed(s0 + 5.0)   # ponto de referência: função existe e é finita
    assert np.isfinite(k_left)


# ------------------------------------------------------- 5. PPO tanh-squashed

def test_squashed_policy_action_bounds_and_logp_consistency(env):
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    import tensorflow as tf
    agent = MultiContextPPOAgent(obs_spaces=env.observation_space, act_dim=2)
    obs, _ = env.reset()
    obs_b = {k: np.asarray(v)[None] for k, v in obs.items()}
    for _ in range(30):                     # ações sempre limitadas, mesmo sem clip do env
        a, logp = agent.act_batch(obs_b)
        assert np.all(np.abs(a) < 1.0)
        assert np.isfinite(logp).all()
    # ratio == 1 quando a política não mudou (logp do update == do rollout)
    from backend.model_train.train_multi_context_ppo import _tf_obs
    a, logp_rollout = agent.act_batch(obs_b)
    _, _, _, kl = agent._train_step(_tf_obs(obs_b),
                                    tf.convert_to_tensor(a, dtype=tf.float32),
                                    tf.convert_to_tensor(logp_rollout, dtype=tf.float32),
                                    tf.convert_to_tensor([0.0], dtype=tf.float32),
                                    tf.convert_to_tensor([0.0], dtype=tf.float32))
    assert abs(float(kl)) < 1e-4, f"logp rollout/update inconsistente (kl={kl})"


def test_checkpoint_roundtrip(env, tmp_path):
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    agent = MultiContextPPOAgent(obs_spaces=env.observation_space, act_dim=2)
    agent._save(tmp_path)
    obs, _ = env.reset()
    obs_b = {k: np.asarray(v)[None] for k, v in obs.items()}
    det_before = agent.act_det_batch(obs_b)
    agent2 = MultiContextPPOAgent(obs_spaces=env.observation_space, act_dim=2,
                                  init_actor_path=tmp_path / "multi_context_rl_actor.keras",
                                  init_critic_path=tmp_path / "multi_context_rl_critic.keras")
    det_after = agent2.act_det_batch(obs_b)
    assert np.allclose(det_before, det_after, atol=1e-5)


# ---------------------------------------------- 6. Respawn não gera progresso fictício

def test_respawn_does_not_create_fake_progress(env):
    env.reset()
    progress_before_tp = None
    for _ in range(400):
        # força saída: throttle total com esterço travado
        obs, r, term, trunc, info = env.step(np.array([1.0, 1.0], dtype=np.float32))
        if info["respawns_left"] < 5:      # houve respawn neste step
            # no step seguinte, o progresso não pode saltar > 5 m (o teleporte
            # anda para TRÁS na pista, jamais para frente)
            obs, r, term, trunc, info2 = env.step(np.array([0.0, 0.0], dtype=np.float32))
            assert info2["progress_m"] <= info["progress_m"] + 5.0
            break
        if term or trunc:
            env.reset()
    else:
        pytest.skip("nenhum respawn disparado em 400 passos")


# ---------------------------------------------------- 7. Baseline clássico (lento)

@pytest.mark.slow
def test_reference_controller_completes_lap(env_eval):
    """Prova separável: se o baseline clássico não completa a volta, o problema
    é da física/pista — não do RL. Lento (~1-2 min de sim)."""
    from backend.model_train.reference_controller import (
        ReferenceController, run_reference_episode)
    info = run_reference_episode(env_eval, ReferenceController(env_eval, a_lat_max=10.0))
    assert info["completed_lap"], f"baseline não completou a volta: prog={info['progress_m']:.0f}m"


# ---------------------------------------------------- 8. Skidpad (regressão física)

@pytest.mark.slow
def test_skidpad_radius_close_to_bicycle(env_eval):
    """Regressão do subesterço: 15° a ~20 m/s deve dar raio < 2x o bicicleta."""
    handle = env_eval.engine.handles[env_eval.driver_id]
    env_eval.reset()
    env_eval.engine.set_driver_input(env_eval.driver_id, throttle=0, brake=0,
                                     steering_yaw_rad=math.radians(15), grip_override=1.0)
    speeds, yaws = [], []
    for t in range(150):
        phys = env_eval.engine.physics.get_state(handle)
        v = phys["speed_mps"]
        env_eval.engine.set_driver_input(
            env_eval.driver_id, target_speed_mps=20.0,
            throttle=1.0 if v < 20 else 0.0, brake=0.5 if v > 22 else 0.0,
            steering_yaw_rad=math.radians(15), grip_override=1.0)
        env_eval.engine._step_tick(env_eval.logic_dt, env_eval.sub_steps)
        if t >= 90:
            speeds.append(v); yaws.append(abs(phys["yaw_rate"]))
    v_m, w_m = float(np.mean(speeds[-20:])), float(np.mean(yaws[-20:]))
    radius = v_m / max(w_m, 1e-6)
    bike = 3.4 / math.tan(math.radians(15))
    assert radius < 2.0 * bike, f"subesterço regressou: raio={radius:.1f} m vs bicicleta {bike:.1f} m"
