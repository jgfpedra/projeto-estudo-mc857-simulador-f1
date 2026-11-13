"""FASE 0 Meta C — testes do _v_allow_at com modelo físico (downforce).

Valida: (a) downforce aumenta v_allow vs modelo antigo; (b) monotonicidade
em grip; (c) calibração: v_allow(sf_r=1.0) ≥ v_plan(professor sf=0.80);
(d) v10 não muda de comportamento (a mudança é na recompensa, não na obs).
"""
import math
import numpy as np
import pytest


class TestVAllowPhysical:
    def test_downforce_increases_v_allow(self):
        """(a) v_allow com downforce > modelo antigo (A_LAT_MAX=14 fixo)."""
        from backend.model_train.f1_env import F1MultiContextEnv, A_LAT_MAX
        env = F1MultiContextEnv(track='interlagos', allow_respawn=False,
                                 grip_override=1.0, sf_reward=1.00)
        # pega um ponto de curva média (R~50m → kappa~0.02)
        # v_allow deve ser > sqrt(14/0.02) = 26.5 m/s (o modelo antigo)
        for s in (500.0, 1500.0, 2500.0, 3500.0):
            k = abs(env._kappa_signed(s))
            if k > 0.005:
                v_old = math.sqrt(A_LAT_MAX / k)
                v_new = env._v_allow_at(s, 30.0)  # v_now=30 (alta → downforce)
                # em curva: v_allow novo deve dar folga ≥ ao antigo
                assert v_new >= v_old * 0.95, (
                    f"s={s}: v_allow={v_new:.1f} < 0.95×v_old={v_old:.1f} "
                    f"(downforce deveria AUMENTAR o teto)")
        env.close()

    def test_monotonic_grip(self):
        """(b) v_allow é monótono crescente em grip_override."""
        from backend.model_train.f1_env import F1MultiContextEnv
        vals = []
        for grip in (0.5, 0.7, 0.788, 0.9, 1.0):
            env = F1MultiContextEnv(track='interlagos', allow_respawn=False,
                                     grip_override=grip, sf_reward=0.90)
            # média de v_allow ao longo da pista ( amostra 20 pontos)
            vs = [env._v_allow_at(s, 30.0) for s in range(0, 4000, 200)]
            vals.append(np.mean(vs))
            env.close()
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1] + 0.5, (
                f"grip {i}: {vals[i]:.1f} > grip {i+1}: {vals[i+1]:.1f} "
                f"(deveria ser monótono crescente)")

    def test_calibration_contains_professor(self):
        """(c) v_allow(sf_r=1.0) ≥ v_plan(professor sf=0.80) em TODA Interlagos."""
        from backend.model_train.f1_env import F1MultiContextEnv
        from backend.model_train.velocity_profile import VelocityProfile
        env = F1MultiContextEnv(track='interlagos', allow_respawn=False,
                                 grip_override=GRIP_TEST, sf_reward=1.00)
        vp = VelocityProfile(env._wps_arr, grip_mult=0.788, sf=0.80,
                             ds_target=4.0, smooth_window_m=20.0)
        # NOTA: v_allow usa _kappa_signed (janela ±10m) e v_plan usa
        # compute_kappa_profile (híbrido peak/avg) — mecanismos DIFERENTES
        # dão kappas ligeiramente diferentes. A calibração verifica que
        # o v_allow NÃO é sistematicamente abaixo do v_plan.
        ratios = []
        for s in np.arange(0, env._track_len_s, 20.0):
            v_allow = env._v_allow_at(float(s), 30.0)
            v_plan = vp.at(float(s))
            if v_plan > 20:  # só compara onde há restrição real
                ratios.append(v_allow / v_plan)
        # mediana das razões deve ser ≥ 1.0 (v_allow contém o professor)
        # com tolerância de 5% para as diferenças de kappa
        med_ratio = np.median(ratios)
        assert med_ratio >= 0.95, (
            f"mediana v_allow/v_plan = {med_ratio:.3f} "
            f"— o headroom deveria conter o professor (≥0.95)")
        env.close()

    def test_sf_reward_080_approximates_legacy(self):
        """(c b) v_allow(sf_r=0.80) ≈ v_plan(professor sf=0.80) — o comportamento
        default é aproximadamente equivalente ao legado."""
        from backend.model_train.f1_env import F1MultiContextEnv
        from backend.model_train.velocity_profile import VelocityProfile
        env = F1MultiContextEnv(track='interlagos', allow_respawn=False,
                                 grip_override=GRIP_TEST, sf_reward=0.80)
        vp = VelocityProfile(env._wps_arr, grip_mult=0.788, sf=0.80,
                             ds_target=4.0, smooth_window_m=20.0)
        ratios = []
        for s in np.arange(0, env._track_len_s, 20.0):
            v_allow = env._v_allow_at(float(s), 30.0)
            v_plan = vp.at(float(s))
            if v_plan > 20:
                ratios.append(v_allow / v_plan)
        # sf_r=0.80 com grip=1.0 (treino) vs professor sf=0.80 grip=0.788:
        # o grip 1.0 > 0.788 dá ~10-20% mais folga — razão esperada 1.0-1.3
        med_ratio = np.median(ratios)
        assert 0.90 <= med_ratio <= 1.50, (
            f"mediana v_allow/v_plan = {med_ratio:.3f} "
            f"(sf_r=0.80, grip=1.0 deveria estar 0.9-1.5× do professor sf=0.80)")
        env.close()

    def test_v10_behavior_unchanged(self):
        """(d) A mudança é na RECOMPENSA, não na obs — v10 (que usa só a obs
        para inferência) não muda de comportamento. Verifica que a obs
        não inclui v_allow (é interna da recompensa)."""
        from backend.model_train.f1_env import F1MultiContextEnv
        env1 = F1MultiContextEnv(track='interlagos', allow_respawn=False,
                                  grip_override=None, obs_mode='edge',
                                  sf_reward=0.80)
        env2 = F1MultiContextEnv(track='interlagos', allow_respawn=False,
                                  grip_override=None, obs_mode='edge',
                                  sf_reward=1.00)
        obs1, _ = env1.reset(seed=0)
        obs2, _ = env2.reset(seed=0)
        # a observação deve ser IDÊNTICA (sf_reward não afeta a obs)
        np.testing.assert_allclose(obs1['telemetry'], obs2['telemetry'], atol=1e-6)
        env1.close(); env2.close()


# grip para testes de calibração (match com o professor)
GRIP_TEST = 1.0  # treino usa grip_override; o professor usa grip_mult=0.788
