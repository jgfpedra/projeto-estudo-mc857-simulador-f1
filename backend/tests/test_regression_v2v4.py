"""Testes da investigação de regressão v2 vs v4 (anti-stall, seleção, integridade).

Cobre:
1. (anti-stall -> migrado para tests/test_recovery_state.py): política que comanda freio persistente a
   0 m/s não pode mais travar o carro (o bug que produzia 0 km/h permanentes).
2. Timer do anti-stall só reseta quando o carro anda.
3. Divergência documentada v2 vs v4: v4 freia na curva-monstro, v2 acelera
   (regressão de comportamento — teste de caracterização, não de qualidade).
4. Metadados de checkpoint (training_meta.json) gravam iteração e lap%.
"""

import json
import math

import numpy as np
import pytest


# ------------------------------------------------ 1. Anti-stall autoritário




def test_v4_brakes_vs_v2_accelerates_at_monster_corner(tmp_path):
    """Teste de CARACTERIZAÇÃO da regressão (não de qualidade da política):
    na curva-monstro (s~28, previews kappa ~2.1 — 3.5x fora da distribuição de
    treino), v4 comanda freio e v2 acelera. Documenta o mecanismo raiz; se uma
    futura política corrigida mudar este comportamento, este teste deve ser
    atualizado conscientemente."""
    import os
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    import tensorflow as tf
    from gymnasium import spaces
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    from backend.model_train.f1_env import N_OBS_TELEMETRY

    # obs sintética do deadlock (capturada na corrida real, Fase D)
    tel = np.zeros((1, N_OBS_TELEMETRY), dtype=np.float32)
    tel[0, 4] = 0.68          # lat_err
    tel[0, 6] = 1.0           # cos_h
    tel[0, 7] = 0.94          # p_steer (freio travado à esquerda)
    tel[0, 8] = -0.99         # p_long
    tel[0, 9+2*0] = 2.15      # kappa@10m  (curva-monstro)
    tel[0, 9+2*1] = 1.88      # kappa@20m
    tel[0, 9] = 0.136         # dh@10m
    obs = {"telemetry": tel,
           "ctx_numeric": np.array([[0.5, 0.5]], dtype=np.float32),
           "track_id": np.zeros((1, 1), dtype=np.int32),
           "compound_id": np.zeros((1, 1), dtype=np.int32)}
    obs_spaces = spaces.Dict({
        "telemetry": spaces.Box(-5, 5, shape=(N_OBS_TELEMETRY,), dtype=np.float32),
        "ctx_numeric": spaces.Box(-5, 5, shape=(2,), dtype=np.float32),
        "track_id": spaces.Box(0, 20, shape=(1,), dtype=np.int32),
        "compound_id": spaces.Box(0, 5, shape=(1,), dtype=np.int32)})

    v2 = "archive/checkpoints/v2/multi_context_rl_actor_best.keras"
    v4 = "archive/checkpoints/v4/multi_context_rl_actor_best.keras"
    if not (Path(v2).exists() and Path(v4).exists()):
        pytest.skip("checkpoints v2/v4 não presentes")

    def act(path):
        actor = tf.keras.models.load_model(path, compile=False)
        m = actor(obs, training=False).numpy()[0]
        return float(np.tanh(m[1]))   # longitudinal

    lg_v2 = act(v2)
    lg_v4 = act(v4)
    # caracterização da regressão: v4 freia, v2 acelera
    assert lg_v4 < -0.5, f"v4 deveria frear no estado do deadlock (lg={lg_v4:+.2f})"
    assert lg_v2 > 0.0, f"v2 deveria acelerar no mesmo estado (lg={lg_v2:+.2f})"


# ---------------------------------------------- 3. Metadados de checkpoint

def test_checkpoint_metadata_written(tmp_path):
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    from gymnasium import spaces
    from backend.model_train.f1_env import N_OBS_TELEMETRY
    obs_spaces = spaces.Dict({
        "telemetry": spaces.Box(-5, 5, shape=(N_OBS_TELEMETRY,), dtype=np.float32),
        "ctx_numeric": spaces.Box(-5, 5, shape=(2,), dtype=np.float32),
        "track_id": spaces.Box(0, 20, shape=(1,), dtype=np.int32),
        "compound_id": spaces.Box(0, 5, shape=(1,), dtype=np.int32)})
    agent = MultiContextPPOAgent(obs_spaces=obs_spaces, act_dim=2)
    agent._save(tmp_path, meta={"iteration": 123, "lap_pct": 0.0, "mean_return": 42.5})
    meta_file = tmp_path / "training_meta_last.json"
    assert meta_file.exists()
    meta = json.load(open(meta_file))
    assert meta["iteration"] == 123
    assert meta["mean_return"] == 42.5
    agent._save(tmp_path, suffix="_best", meta={"iteration": 77, "lap_pct": 0.0})
    meta = json.load(open(tmp_path / "training_meta_best.json"))
    assert meta["iteration"] == 77


from pathlib import Path  # noqa: E402  (no fim p/ não atrapalhar import acima)
