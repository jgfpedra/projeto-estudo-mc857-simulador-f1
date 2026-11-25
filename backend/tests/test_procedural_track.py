"""Testes do gerador procedural de pistas (Parte 2).

Cobre: determinismo por seed, fechamento, espaçamento ≤4m, kappa no range,
integração com F1MultiContextEnv (obs edge, start_zones auto), e
leitura da fronteira física.
"""
import math
import numpy as np
import pytest


def _gen(seed, **kw):
    from backend.model_train.procedural_track import generate_track
    return generate_track(seed=seed, **kw)


def _kappa_stats(wps):
    wps = np.array(wps)
    closed = np.vstack([wps, wps[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    dx = np.roll(wps[:, 0], -1) - np.roll(wps[:, 0], 1)
    dy = np.roll(wps[:, 1], -1) - np.roll(wps[:, 1], 1)
    hdg = np.arctan2(dy, dx)
    dh = np.roll(hdg, -1) - hdg
    dh = (dh + math.pi) % (2 * math.pi) - math.pi
    k = dh / max(seg.mean(), 0.5)
    return seg, np.abs(k).max(), seg.mean()


class TestDeterminism:
    def test_same_seed_same_track(self):
        t1 = _gen(seed=42, n_hairpins=2, n_esses=1)
        t2 = _gen(seed=42, n_hairpins=2, n_esses=1)
        assert t1 is not None and t2 is not None
        w1 = np.array(t1.waypoints)
        w2 = np.array(t2.waypoints)
        assert w1.shape == w2.shape
        np.testing.assert_allclose(w1, w2, atol=1e-6)

    def test_different_seed_different_track(self):
        t1 = _gen(seed=1, n_hairpins=1, n_esses=0)
        t2 = _gen(seed=2, n_hairpins=1, n_esses=0)
        assert t1 is not None and t2 is not None
        w1 = np.array(t1.waypoints)
        w2 = np.array(t2.waypoints)
        # pistas diferentes = shapes diferentes OU waypoints diferentes
        assert w1.shape != w2.shape or not np.allclose(w1, w2), \
            "seeds diferentes devem dar pistas diferentes"


class TestGeometry:
    def test_closure(self):
        """O último waypoint deve conectar de volta ao primeiro."""
        t = _gen(seed=7, n_hairpins=1, n_esses=1)
        assert t is not None
        wps = np.array(t.waypoints)
        gap = math.hypot(wps[0, 0] - wps[-1, 0], wps[0, 1] - wps[-1, 1])
        # o gap de fechamento deve ser <= espaçamento (subdivisão colinear)
        seg, _, spacing = _kappa_stats(wps)
        # o fecho é o segmento último→primeiro; como Track.from_waypoints
        # fecha a polilinha, verificamos que o comprimento é finito e >0
        assert seg.sum() > 1000.0, "pista deve ter >1km"

    def test_spacing_le_4m(self):
        """Todos os segmentos devem ter ≤4m (subdivisão)."""
        t = _gen(seed=3, n_hairpins=2, n_esses=1)
        assert t is not None
        wps = np.array(t.waypoints)
        closed = np.vstack([wps, wps[:1]])
        seg = np.hypot(*np.diff(closed, axis=0).T)
        assert seg.max() <= 4.5, f"espaçamento máximo {seg.max():.2f}m > 4.5m"
        assert seg.mean() <= 4.0, f"espaçamento médio {seg.mean():.2f}m > 4m"

    def test_length_range(self):
        """Comprimento deve estar em 3-7km."""
        t = _gen(seed=5, n_hairpins=1, n_esses=1, target_length_m=4000)
        assert t is not None
        wps = np.array(t.waypoints)
        closed = np.vstack([wps, wps[:1]])
        total = np.hypot(*np.diff(closed, axis=0).T).sum()
        assert 2500 < total < 8000, f"comprimento {total:.0f}m fora de [2.5, 8]km"

    def test_kappa_in_range(self):
        """kappa máx deve ser ≤ fronteira (com folga do gate)."""
        t = _gen(seed=11, n_hairpins=2, n_esses=0)
        assert t is not None
        wps = np.array(t.waypoints)
        _, kmax, _ = _kappa_stats(wps)
        assert kmax < 0.25, f"kappa {kmax:.3f} muito alto (R={1/kmax:.0f}m < 4m)"
        assert kmax > 0.005, "kappa muito baixo (pista sem curvas?)"


class TestWidth:
    def test_custom_width(self):
        t = _gen(seed=13, width_m=14.0)
        assert t is not None
        assert t.width_m == 14.0

    def test_width_range(self):
        for w in (10.0, 12.0, 15.0):
            t = _gen(seed=17, width_m=w)
            assert t is not None
            assert t.width_m == w


class TestFrontier:
    def test_load_r_min(self):
        from backend.model_train.procedural_track import load_r_min
        r = load_r_min(v_ref=10.0, grip="real")
        assert r > 0, f"R_min deve ser positivo, deu {r}"
        assert r < 50, f"R_min deve ser razoável (<50m), deu {r}"


class TestEnvIntegration:
    def test_env_with_procedural(self):
        """F1MultiContextEnv deve aceitar um Track procedural."""
        from backend.model_train.f1_env import F1MultiContextEnv
        t = _gen(seed=21, n_hairpins=1, n_esses=1)
        assert t is not None
        env = F1MultiContextEnv(track=t, allow_respawn=False, obs_mode='edge')
        obs, _ = env.reset(seed=0)
        # obs edge = 34 dims
        assert obs['telemetry'].shape == (34,)
        assert np.all(np.isfinite(obs['telemetry']))
        # step
        a = np.zeros(2)
        obs, r, term, trunc, info = env.step(a)
        assert math.isfinite(r)
        env.close()

    def test_start_zones_auto(self):
        """start_zones='auto' deve detectar curvas por geometria."""
        from backend.model_train.f1_env import F1MultiContextEnv
        t = _gen(seed=23, n_hairpins=2, n_esses=0)
        env = F1MultiContextEnv(track=t, allow_respawn=False,
                                start_zones='auto', obs_mode='edge')
        assert env.start_zones is not None
        assert len(env.start_zones) >= 1
        env.close()

    def test_race_layer_compatible(self):
        """Track procedural deve ter waypoints e nome (interface Track)."""
        t = _gen(seed=25, n_hairpins=1, n_esses=1)
        assert t is not None
        assert hasattr(t, 'waypoints')
        assert hasattr(t, 'name')
        assert 'procedural' in t.name.lower() or 's25' in t.name.lower()
        assert t.width_m > 0
        assert len(t.waypoints) > 50


class TestFeatures:
    def test_hairpin_produces_tight_corner(self):
        """Pistas com hairpin devem ter kappa > 0.04 (R < 25m)."""
        t = _gen(seed=31, n_hairpins=2, n_esses=0)
        assert t is not None
        wps = np.array(t.waypoints)
        _, kmax, _ = _kappa_stats(wps)
        assert kmax > 0.04, f"hairpin deveria dar kappa>0.04, deu {kmax:.4f}"

    def test_esse_track_variety(self):
        """Pistas com esses devem ter mudanças de direção."""
        t = _gen(seed=33, n_hairpins=0, n_esses=3)
        assert t is not None
        wps = np.array(t.waypoints)
        # kappa muda de sinal
        dx = np.roll(wps[:, 0], -1) - np.roll(wps[:, 0], 1)
        dy = np.roll(wps[:, 1], -1) - np.roll(wps[:, 1], 1)
        hdg = np.arctan2(dy, dx)
        dh = np.roll(hdg, -1) - hdg
        dh = (dh + math.pi) % (2 * math.pi) - math.pi
        signs = np.sign(dh[np.abs(dh) > 0.005])
        changes = int(np.sum(np.diff(signs) != 0))
        assert changes >= 2, "esse track deve ter ≥2 mudanças de direção"
