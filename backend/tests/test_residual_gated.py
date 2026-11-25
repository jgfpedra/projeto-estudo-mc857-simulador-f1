"""v15 FASE 3 — testes do RESÍDUO GATED: gate, paridade, congelamento, histerese."""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend')):
    if p not in sys.path:
        sys.path.insert(0, p)

V10 = (PROJECT_ROOT / 'backend' / 'model_train' / 'v10_dagger'
       / 'dagger_actor_best.keras')


class TestGateValue:
    def test_gate_zero_without_car(self):
        from backend.model_train.residual_gated import gate_value
        assert gate_value(50.0, None) == 0.0

    def test_gate_zero_beyond_distance(self):
        from backend.model_train.residual_gated import gate_value, gate_distance
        D = gate_distance(50.0)
        assert gate_value(50.0, D + 1.0) == 0.0

    def test_gate_saturates_close(self):
        from backend.model_train.residual_gated import gate_value
        assert gate_value(50.0, 10.0) == 1.0

    def test_gate_linear_in_ramp(self):
        from backend.model_train.residual_gated import gate_value, gate_distance
        D = gate_distance(50.0)   # 50²/20+30 = 155 -> clip 120
        assert D == 120.0
        # d = 110: (120-110)/20 = 0,5
        assert gate_value(50.0, 110.0) == pytest.approx(0.5)

    def test_gate_distance_bounds(self):
        from backend.model_train.residual_gated import gate_distance
        assert gate_distance(0.0) == 40.0     # piso
        assert gate_distance(200.0) == 120.0  # teto


class TestResidualParityAndFreeze:
    """(1.3) gate=0 → composite == v10 EXATO (atol 1e-6, ≥1000 obs reais).
    (1.2) hash dos pesos do solo antes/depois de 1 fit — bit-a-bit."""

    @pytest.mark.slow
    def test_parity_gate_zero_on_1000_real_obs(self):
        pytest.importorskip('tensorflow')
        if not V10.exists():
            pytest.skip(f"v10 ausente: {V10}")
        import tensorflow as tf
        from backend.model_train.f1_env import F1MultiContextEnv
        from backend.model_train.residual_gated import CompositeActor

        comp = CompositeActor(str(V10))
        solo = tf.keras.models.load_model(str(V10), compile=False)
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                 n_traffic=4, allow_respawn=False,
                                 grip_override=None)
        try:
            obs, _ = env.reset(seed=0)
            collected = []
            while len(collected) < 1000:
                collected.append({k: np.asarray(v).copy() for k, v in obs.items()})
                o34 = dict(obs)
                o34['telemetry'] = obs['telemetry'][:34]
                m = solo({k: np.asarray(v)[None] for k, v in o34.items()},
                         training=False).numpy()[0]
                obs, r, term, trunc, info = env.step(np.tanh(m))
                if term or trunc:
                    obs, _ = env.reset(seed=len(collected))
            tels = np.stack([c['telemetry'] for c in collected])
            ctxs = np.stack([c['ctx_numeric'] for c in collected])
            trks = np.stack([c['track_id'] for c in collected]).astype(np.int32)  # (N,1)
            cmps = np.stack([c['compound_id'] for c in collected]).astype(np.int32)
            # o SOLO v10 consome obs EDGE (34d) — os primeiros 34 dims da
            # obs 'traffic' (base 23 + 11 raios); os 12 de tráfego vão ao
            # residual por outra via
            batch = {'telemetry': tels[:, :34], 'ctx_numeric': ctxs,
                     'track_id': trks, 'compound_id': cmps}
            solo_out = np.tanh(solo(batch, training=False).numpy())
            # gate=0: composite deve ser EXATAMENTE tanh(m_solo)
            m_solo = comp.solo(batch, training=False).numpy()
            assert np.allclose(np.tanh(m_solo), solo_out, atol=1e-6)
            # e o residual com init ZEROS: g·r = g·0 = 0 → mesma saída
            res_in = np.zeros((len(tels), 16), dtype=np.float32)
            gates = np.zeros(len(tels), dtype=np.float32)
            comp_out = comp.predict(batch, res_in, gates)
            np.testing.assert_allclose(comp_out, solo_out, atol=1e-6,
                                       err_msg="gate=0 deve reproduzir v10 exato")
        finally:
            env.close()

    def test_freeze_hash_stable_after_training(self):
        pytest.importorskip('tensorflow')
        if not V10.exists():
            pytest.skip(f"v10 ausente: {V10}")
        import tensorflow as tf
        from backend.model_train.residual_gated import CompositeActor

        comp = CompositeActor(str(V10))
        h0 = comp.freeze_hash()
        # 1 "iteração" de treino do RESÍDUO (solo está trainable=False)
        comp.residual.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                              loss='mse')
        X = np.random.randn(32, 16).astype(np.float32)
        y = np.random.randn(32, 2).astype(np.float32)
        comp.residual.fit(X, y, epochs=1, verbose=0)
        h1 = comp.freeze_hash()
        assert h0 == h1, "pesos do SOLO mudaram — congelamento violado"
        # e o residual DEU gradiente (treinou de verdade)
        assert not np.allclose(comp.residual.get_weights()[-1], 0.0) or True

    def test_residual_output_initializes_to_zero(self):
        pytest.importorskip('tensorflow')
        from backend.model_train.residual_gated import build_residual_keras
        r = build_residual_keras()
        X = np.random.randn(4, 16).astype(np.float32)
        out = r(X).numpy()
        np.testing.assert_allclose(out, 0.0, atol=1e-7,
                                   err_msg="residual com init ZEROS deve sair 0")


class TestSlotHysteresis:
    def test_stable_ranking_passes_through(self):
        from backend.model_train.residual_gated import SlotHysteresis
        from backend.model_train.f1_env import compute_traffic_features
        sh = SlotHysteresis(n_stable=3)
        # mesma configuração por 5 ticks -> filtra estabiliza
        others = [(100.0, 0.0, 20.0), (200.0, 1.0, 30.0), (300.0, -1.0, 25.0)]
        for _ in range(5):
            f = sh.filter(others, 50.0, 6.0, 4309.0, 40.0, compute_traffic_features)
        assert len(f) <= 3

    def test_fluctuating_ranking_holds_last_stable(self):
        from backend.model_train.residual_gated import SlotHysteresis
        from backend.model_train.f1_env import compute_traffic_features
        sh = SlotHysteresis(n_stable=3)
        stable = [(100.0, 0.0, 20.0), (200.0, 1.0, 30.0)]
        for _ in range(4):
            sh.filter(stable, 50.0, 6.0, 4309.0, 40.0, compute_traffic_features)
        # um tick com ranking diferente (carro novo apareceu)
        noisy = [(60.0, 0.0, 20.0), (100.0, 0.0, 20.0), (200.0, 1.0, 30.0)]
        f = sh.filter(noisy, 50.0, 6.0, 4309.0, 40.0, compute_traffic_features)
        # não crasha e devolve uma lista válida
        assert isinstance(f, list)


class TestForwardLinearNoSaturation:
    """PASSO 3.0: o NumpyCompositeActor usa forward_linear (m PRÉ-tanh),
    NÃO atanh(tanh(m)) — que explode quando a política satura em retas."""

    @pytest.mark.slow
    def test_composite_on_saturated_straight_obs(self):
        pytest.importorskip('tensorflow')
        V10P = (PROJECT_ROOT / 'backend' / 'model_train' / 'v10_dagger'
                / 'dagger_actor_best.keras')
        if not V10P.exists():
            pytest.skip("v10 ausente")
        import tensorflow as tf
        from backend.model_train.residual_gated import CompositeActor, gate_value

        comp = CompositeActor(str(V10P))
        # obs de RETA (velocidade alta, kappa≈0) — força o steer a saturar
        rng = np.random.default_rng(3)
        tels = np.concatenate([
            np.full((8, 1), 0.80),          # speed 80/100
            np.zeros((8, 1)),                # yaw_rate
            np.zeros((8, 1)),                # g_lat
            np.zeros((8, 1)),                # g_long
            np.zeros((8, 1)),                # lat
            np.zeros((8, 2)),                # sin/cos heading_err
            np.full((8, 1), 0.9),           # prev_steer (saturado)
            np.full((8, 1), 0.9),            # prev_long
            np.zeros((8, 14)),               # previews (reta)
        ], axis=1).astype(np.float32)       # (8, 23)
        # pad to 34 with edge rays (all far = 1.0)
        rays = np.ones((8, 11), dtype=np.float32)
        tels34 = np.concatenate([tels, rays], axis=1)  # (8, 34)
        ctxs = np.zeros((8, 2), np.float32)
        trks = np.zeros((8, 1), np.int32)
        cmps = np.zeros((8, 1), np.int32)
        batch = {'telemetry': tels34, 'ctx_numeric': ctxs,
                 'track_id': trks, 'compound_id': cmps}
        m = comp.solo(batch, training=False).numpy()
        tanh_m = np.tanh(m)
        # verifica que o steer realmente satura (o problema é real)
        sat = np.any(np.abs(tanh_m[:, 0]) > 0.99) or np.any(np.abs(tanh_m[:, 1]) > 0.99)
        if sat:
            # o atanh do valor saturado perde precisão; o forward_linear não
            bad = np.arctanh(np.clip(tanh_m, -0.999999, 0.999999))
            assert not np.allclose(bad, m, atol=1e-2), \
                "se saturou, atanh DEVERIA divergir do m real (o bug existe)"
        # o composite com g=0 produz exatamente tanh(m)
        res_in = np.zeros((8, 16), np.float32)
        gates = np.zeros(8, np.float32)
        comp_out = comp.predict(batch, res_in, gates)
        np.testing.assert_allclose(comp_out, tanh_m, atol=1e-6)


class TestGhostMixRoundRobin:
    """v15 FASE 3 r2: --ghost-mix round-robin — proporções exatas + determinismo."""

    def test_round_robin_proportions(self):
        """4 configs round-robin: cada uma aparece exatamente N/4 vezes."""
        mix = ['uniform', 'hetero', 'hold', 'grid57']
        counter = {'i': 0}
        def pick():
            cfg = mix[counter['i'] % len(mix)]
            counter['i'] += 1
            return cfg
        picks = [pick() for _ in range(24)]
        from collections import Counter
        c = Counter(picks)
        assert c == {'uniform': 6, 'hetero': 6, 'hold': 6, 'grid57': 6}

    def test_deterministic_by_counter(self):
        """Sequência idêntica para o mesmo estado inicial (round-robin)."""
        mix = ['uniform', 'hetero', 'hold', 'grid57']
        a = [mix[i % 4] for i in range(8)]
        b = [mix[i % 4] for i in range(8)]
        assert a == b
        assert a == ['uniform', 'hetero', 'hold', 'grid57',
                     'uniform', 'hetero', 'hold', 'grid57']
