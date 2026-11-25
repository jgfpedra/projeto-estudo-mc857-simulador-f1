"""PASSO 1 (FASE 3 v14) — TESTE DE PARIDADE da transferência v10→v14.

A transferência só é confiável se: v14 com os 12 dims de tráfego ZERADOS e a
mesma obs edge/ctx/emb do v10 produz SAÍDAS IDÊNTICAS ao v10 (atol 1e-6).
Sem este teste verde, o treino não começa (regra da task v14 FASE 3).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend')):
    if p not in sys.path:
        sys.path.insert(0, p)

V10_ACTOR = (PROJECT_ROOT / 'backend' / 'model_train' / 'v10_dagger'
             / 'dagger_actor_best.keras')

os_env = pytest.importorskip  # noqa (legibilidade)


def _build_pair():
    """(v10 carregado, v14 transferido) — usado por todos os testes."""
    pytest.importorskip('tensorflow')
    import tensorflow as tf
    from backend.model_train.transfer_v10_v14 import (build_traffic_actor,
                                                      transfer_edge_to_traffic)
    if not V10_ACTOR.exists():
        pytest.skip(f"checkpoint v10 ausente: {V10_ACTOR}")
    src = tf.keras.models.load_model(str(V10_ACTOR), compile=False)
    dst = build_traffic_actor(int(src.outputs[0].shape[-1]))
    transfer_edge_to_traffic(src, dst)
    return src, dst


def _dense_kernels(model):
    from backend.model_train.transfer_v10_v14 import _layers_by_type
    return [np.asarray(l.get_weights()[0]) for l in _layers_by_type(model, 'Dense')]


def _embeddings(model):
    from backend.model_train.transfer_v10_v14 import _layers_by_type
    return {np.asarray(l.get_weights()[0]).shape: np.asarray(l.get_weights()[0])
            for l in _layers_by_type(model, 'Embedding')}


class TestRowMapping:
    def test_first_dense_rows(self):
        src, dst = _build_pair()
        k10, k14 = _dense_kernels(src)[0], _dense_kernels(dst)[0]
        assert k14.shape == (60, 256) and k10.shape == (48, 256)
        np.testing.assert_array_equal(k14[0:34], k10[0:34])     # edge
        assert not k14[34:46].any(), "rows de tráfego devem ser ZERO"  # traffic
        np.testing.assert_array_equal(k14[46:48], k10[34:36])   # ctx
        np.testing.assert_array_equal(k14[48:60], k10[36:48])   # embeddings

    def test_bias_and_deep_layers_copied(self):
        src, dst = _build_pair()
        from backend.model_train.transfer_v10_v14 import _layers_by_type
        d10, d14 = (_layers_by_type(src, 'Dense'), _layers_by_type(dst, 'Dense'))
        # bias da 1ª Dense herdado
        np.testing.assert_array_equal(np.asarray(d14[0].get_weights()[1]),
                                      np.asarray(d10[0].get_weights()[1]))
        # profundas idênticas
        for s, d in zip(d10[1:], d14[1:]):
            for ws, wd in zip(s.get_weights(), d.get_weights()):
                np.testing.assert_array_equal(np.asarray(wd), np.asarray(ws))

    def test_embeddings_copied(self):
        src, dst = _build_pair()
        e10, e14 = _embeddings(src), _embeddings(dst)
        assert set(e10) == set(e14)
        for shape in e10:
            np.testing.assert_array_equal(e14[shape], e10[shape])


class TestParity:
    """v14 (tráfego zerado) == v10 na MESMA entrada — atol 1e-6."""

    def test_parity_random_inputs(self):
        src, dst = _build_pair()
        rng = np.random.default_rng(0)
        n = 32
        tel34 = rng.uniform(-5.0, 5.0, (n, 34)).astype(np.float32)
        tel46 = np.concatenate([tel34, np.zeros((n, 12), np.float32)], axis=1)
        ctx = rng.uniform(-1.0, 1.0, (n, 2)).astype(np.float32)
        trk = rng.integers(0, 20, (n, 1)).astype(np.int32)
        cmp_ = rng.integers(0, 5, (n, 1)).astype(np.int32)
        out10 = src({'telemetry': tel34, 'ctx_numeric': ctx,
                     'track_id': trk, 'compound_id': cmp_}, training=False).numpy()
        out14 = dst({'telemetry': tel46, 'ctx_numeric': ctx,
                     'track_id': trk, 'compound_id': cmp_}, training=False).numpy()
        np.testing.assert_allclose(out14, out10, atol=1e-6,
                                   err_msg="v14 com tráfego zerado divergiu do v10")

    def test_parity_real_env_obs(self):
        """Na obs REAL do env (traffic n=0): v14 produz o que o v10 produziria
        na parte edge — situação exata de deploy do estágio A."""
        src, dst = _build_pair()
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                n_traffic=0, allow_respawn=False)
        try:
            obs, _ = env.reset(seed=0)
            tel = obs['telemetry']
            assert tel.shape == (46,)
            assert not tel[34:46].any(), "com n_traffic=0 o bloco deve ser zero"
            batch = {k: np.asarray(v)[None] for k, v in obs.items()}
            out14 = dst(batch, training=False).numpy()
            batch10 = dict(batch)
            batch10['telemetry'] = tel[None, :34]
            out10 = src(batch10, training=False).numpy()
            np.testing.assert_allclose(out14, out10, atol=1e-6)
        finally:
            env.close()

    def test_initial_invariance_to_traffic(self):
        """Enquanto os rows 34-45 forem zero, a saída NÃO depende das dims de
        tráfego (a rede 'começa ignorando tráfego'). Depois do DAgger os
        rows recebem gradiente e isto deixa de valer — documento vivo do
        desenho do warm start."""
        _, dst = _build_pair()
        rng = np.random.default_rng(1)
        base = rng.uniform(-5.0, 5.0, (8, 34)).astype(np.float32)
        ctx = np.zeros((8, 2), np.float32)
        trk = np.zeros((8, 1), np.int32)
        cmp_ = np.zeros((8, 1), np.int32)
        zero = np.concatenate([base, np.zeros((8, 12), np.float32)], axis=1)
        rand = np.concatenate([base, rng.uniform(-5, 5, (8, 12)).astype(np.float32)], axis=1)
        o_zero = dst({'telemetry': zero, 'ctx_numeric': ctx,
                      'track_id': trk, 'compound_id': cmp_}, training=False).numpy()
        o_rand = dst({'telemetry': rand, 'ctx_numeric': ctx,
                      'track_id': trk, 'compound_id': cmp_}, training=False).numpy()
        np.testing.assert_allclose(o_zero, o_rand, atol=1e-6)


class TestTrafficRowsFrozenWithoutTrafficInputs:
    """PASSO 2 (FASE 3): no estágio A os INPUTS de tráfego são zero, logo o
    gradiente nos rows 34-45 da 1ª Dense é MATEMATICAMENTE nulo — o BC warm
    started NÃO pode movê-los. É isto que garante 'regressão zero' herdada
    da transferência (os rows só acordam no estágio B, com dados de tráfego)."""

    def test_bc_keeps_traffic_rows_zero(self):
        pytest.importorskip('tensorflow')
        from backend.model_train.train_dagger import train_bc
        from gymnasium import spaces
        src, dst = _build_pair()
        rng = np.random.default_rng(7)
        # dataset sintético com bloco de tráfego ZERO (estágio A) e rótulos
        # quaisquer — a propriedade é sobre os inputs, não sobre os rótulos
        n = 256
        tel = np.concatenate([rng.uniform(-5, 5, (n, 34)),
                              np.zeros((n, 12))], axis=1).astype(np.float32)
        states = [{'telemetry': tel[i],
                   'ctx_numeric': rng.uniform(-1, 1, 2).astype(np.float32),
                   'track_id': np.array([0], np.int32),
                   'compound_id': np.array([0], np.int32)} for i in range(n)]
        labels = [np.tanh(rng.normal(0, 0.3, 2)).astype(np.float32) for _ in range(n)]
        obs_space = {'telemetry': spaces.Box(-5, 5, (46,), np.float32),
                     'ctx_numeric': spaces.Box(-5, 5, (2,), np.float32)}
        agent, _ = train_bc(states, labels, states[:32], labels[:32], obs_space,
                            epochs=2, init_actor=dst)
        k = _dense_kernels(agent.actor)[0]
        assert not k[34:46].any(), \
            "rows de tráfego mexeram com inputs zero — quebra o desenho do estágio A"
        # ...e os rows de EDGE devem TER mexido (o fit realmente treinou)
        src_k = _dense_kernels(src)[0]
        assert not np.allclose(k[0:34], src_k[0:34]), \
            "BC não treinou nada — teste não exercita o caminho"
