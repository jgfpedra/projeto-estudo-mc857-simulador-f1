"""Testes do velocity_profile.py (Fase 1) — perfil de velocidade físico."""
import math
import numpy as np
import pytest


def _circle(r, n=100):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    return np.array(pts)


def _hairpin_track():
    pts = []
    for i in range(40):
        pts.append((i * 4.0, 0.0))
    for i in range(24):
        a = math.pi * i / 23
        pts.append((160 + 10 * math.sin(a), 10 - 10 * math.cos(a)))
    for i in range(1, 40):
        pts.append((160 + i * 4.0, 20))
    return np.array(pts)


class TestPhysicsParams:
    def test_a_lat_grows_with_downforce(self):
        from backend.model_train.velocity_profile import PhysicsParams as P
        assert P.a_lat(50, 1.0) > P.a_lat(20, 1.0)
        assert P.a_lat(80, 1.0) > P.a_lat(50, 1.0)

    def test_a_lat_realistic_grip_lower(self):
        from backend.model_train.velocity_profile import PhysicsParams as P
        assert P.a_lat(40, 0.788) < P.a_lat(40, 1.0)

    def test_v_curve_beats_constant(self):
        from backend.model_train.velocity_profile import PhysicsParams as P
        v_df = P.v_curve(0.02, 0.788)
        v_const = math.sqrt(14.0 / 0.02)
        assert v_df > v_const

    def test_v_curve_tight_corner_slow(self):
        from backend.model_train.velocity_profile import PhysicsParams as P
        assert P.v_curve(0.125, 0.788) < 12.0

    def test_a_brake_includes_drag(self):
        from backend.model_train.velocity_profile import PhysicsParams as P
        assert P.a_brake(60, 0.788) > P.a_brake(20, 0.788)

    def test_a_accel_positive(self):
        from backend.model_train.velocity_profile import PhysicsParams as P
        for v in (10, 20, 40, 60):
            assert P.a_accel(v, 0.788) > 0


class TestKappaProfile:
    def test_circle_kappa(self):
        from backend.model_train.velocity_profile import compute_kappa_profile
        s, k = compute_kappa_profile(_circle(50.0), ds_target=2.0, smooth_window_m=10.0)
        assert np.all(np.abs(k) > 0.012)
        assert np.all(np.abs(k) < 0.035)

    def test_straight_zero_kappa(self):
        from backend.model_train.velocity_profile import compute_kappa_profile
        # pista retangular FINA (sem as curvas fechadas nas pontas)
        pts = np.array([(i * 4.0, 0.0) for i in range(100)] +
                       [(i * 4.0, 200.0) for i in range(99, -1, -1)])
        s, k = compute_kappa_profile(pts, ds_target=4.0, smooth_window_m=10.0)
        # os trechos RETOS (meio de cada lado) devem ter kappa ~0;
        # as pontas terão kappa alto (curvas de 180°)
        # primeira reta (y=0): s ∈ [100, 300]; segunda (y=200): s ∈ [700, 900]
        straight = ((s > 100.0) & (s < 300.0)) | ((s > 700.0) & (s < 900.0))
        assert np.all(np.abs(k[straight]) < 0.02), \
            f"reta deve ter kappa ~0, max={np.abs(k[straight]).max():.4f}"

    def test_closed_loop(self):
        from backend.model_train.velocity_profile import compute_kappa_profile
        s, k = compute_kappa_profile(_circle(30.0), ds_target=4.0, smooth_window_m=10.0)
        assert len(s) == len(k)
        assert abs(k[0] - k[-1]) < 0.03

    def test_no_nan(self):
        from backend.model_train.velocity_profile import compute_kappa_profile
        s, k = compute_kappa_profile(_circle(40.0))
        assert np.all(np.isfinite(k)) and np.all(np.isfinite(s))


class TestVPlan:
    def test_hairpin_slow(self):
        from backend.model_train.velocity_profile import VelocityProfile
        vp = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.85)
        assert vp.v_min < 25.0

    def test_straight_fast(self):
        from backend.model_train.velocity_profile import VelocityProfile
        vp = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.85)
        assert vp.v_max > 40.0

    def test_brakes_before_corner(self):
        from backend.model_train.velocity_profile import VelocityProfile
        vp = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.85)
        assert vp.at(150.0) < vp.at(80.0)

    def test_interpolation(self):
        from backend.model_train.velocity_profile import VelocityProfile
        vp = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.85)
        for s in (50.0, 100.0, 200.0):
            v = vp.at(s)
            assert math.isfinite(v) and v > 0

    def test_sf_lower_slower(self):
        from backend.model_train.velocity_profile import VelocityProfile
        vp_f = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.85)
        vp_s = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.55)
        assert vp_s.v_min <= vp_f.v_min

    def test_wraps(self):
        from backend.model_train.velocity_profile import VelocityProfile
        vp = VelocityProfile(_hairpin_track(), grip_mult=0.788, sf=0.85)
        v = vp.at(vp.total_s + 10.0)
        assert math.isfinite(v) and v > 0


class TestCrossTrack:
    @pytest.mark.slow
    def test_interlagos_v_plan(self):
        from backend.model_train.velocity_profile import VelocityProfile
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
        vp = VelocityProfile(env._wps_arr, grip_mult=0.788, sf=0.55)
        assert 5.0 < vp.v_min < 20.0
        assert vp.v_max > 50.0
        env.close()
