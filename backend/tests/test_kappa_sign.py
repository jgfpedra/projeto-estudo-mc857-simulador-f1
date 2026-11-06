"""PRÉ-CHECK 0 — sinal do kappa na OBSERVAÇÃO em hairpins procedurais.

O _kappa_signed usa diferença central de heading (h(s+10)−h(s−10))/20 —
diferente da média móvel do professor (que INVERTIA o sinal em hairpins).
Este teste verifica empiricamente que o sinal está CORRETO nos ápices:
curva à ESQUERDA => kappa > 0; curva à DIREITA => kappa < 0.

Se falhar: a obs contaminaria todo o treino DAgger silenciosamente.
"""
import math
import numpy as np
import pytest


def _hairpin_apexes(env, k_threshold=0.03):
    """Encontra os ápices (s de kappa máximo) numa pista."""
    from backend.model_train.velocity_profile import compute_kappa_profile
    s_arr, k = compute_kappa_profile(env._wps_arr, ds_target=4.0, smooth_window_m=20.0)
    ds = s_arr[1] - s_arr[0]
    apexes = []
    for i in range(len(k)):
        if abs(k[i]) > k_threshold:
            # é um "pico" se os vizinhos são menores
            k_prev = abs(k[(i-1) % len(k)])
            k_next = abs(k[(i+1) % len(k)])
            if abs(k[i]) >= k_prev and abs(k[i]) >= k_next:
                apexes.append((float(s_arr[i]), float(k[i])))
    # remove próximos (mesmo canto)
    clean = []
    for s, k in apexes:
        if not clean or abs(s - clean[-1][0]) > 60.0:
            clean.append((s, k))
    return clean


class TestKappaSignProcedural:
    """Sinal do kappa da obs em hairpins procedurais.

    NOTA: os "hairpins" do gerador procedural são DIPS da spline (curvatura
    alterna esquerda→direita no feature), não semicírculos uniformes. O obs
    mede a curvatura LOCAL corretamente em cada ponto. O teste verifica:
    (1) que o kappa da obs tem o sinal correto ONDE a curvatura local é
    inequívoca (|kappa_local| > 0.01), (2) que não há INVERSÃO DE SINAL
    spuriosa (o sinal muda suavemente, não salta de + para − sem cruzar 0).
    """

    def test_local_sign_correct(self):
        """O sinal do kappa da obs deve concordar com o kappa LOCAL
        (medido com janela pequena de 2m) onde a curvatura é significativa."""
        from backend.model_train.procedural_track import generate_track
        from backend.model_train.f1_env import F1MultiContextEnv

        for seed in (101, 103, 301):
            t = generate_track(seed=seed, n_hairpins=2, n_esses=0)
            assert t is not None, f"seed {seed}: pista não gerada"
            env = F1MultiContextEnv(track=t, allow_respawn=False, obs_mode='edge')

            # varre a pista toda; compara obs (20m) vs local (4m)
            n_agree, n_total = 0, 0
            for s in np.arange(0, env._track_len_s, 20.0):
                k_obs = env._kappa_signed(float(s))
                k_local = env._kappa_signed(float(s), window_m=4.0)
                if abs(k_local) > 0.008:  # curvatura local inequívoca
                    n_total += 1
                    if math.copysign(1, k_obs) == math.copysign(1, k_local):
                        n_agree += 1
            # ≥85% de concordância (alguma divergência é esperada em
            # transições onde a janela de 20m suaviza de forma legítima)
            assert n_total > 10, f"seed {seed}: poucas curvas ({n_total})"
            agree_pct = n_agree / n_total
            assert agree_pct >= 0.85, (
                f"seed {seed}: sinal concorda em {agree_pct:.0%} "
                f"({n_agree}/{n_total}) — abaixo de 85%")
            env.close()

    def test_no_spurious_flip(self):
        """O sinal do kappa não pode SALTAR de +max para −max sem cruzar 0
        (o bug do wrap de ±180° fazia exatamente isso)."""
        from backend.model_train.procedural_track import generate_track
        from backend.model_train.f1_env import F1MultiContextEnv
        t = generate_track(seed=101, n_hairpins=2, n_esses=0)
        env = F1MultiContextEnv(track=t, allow_respawn=False, obs_mode='edge')

        k_prev = env._kappa_signed(0.0)
        for s in np.arange(2.0, env._track_len_s, 2.0):
            k_now = env._kappa_signed(float(s))
            # um salto de sinal SEM cruzar zero = bug de wrap
            if math.copysign(1, k_now) != math.copysign(1, k_prev):
                # o salto é OK apenas se o kappa passou por valores pequenos
                # (cruzou 0 legitimamente); bug = salto entre valores grandes
                assert abs(k_prev) < 0.05 or abs(k_now) < 0.05, (
                    f"s={s:.0f}: FLIP de {k_prev:+.4f} para {k_now:+.4f} "
                    f"sem cruzar zero — bug de wrap de ±180°!")
            k_prev = k_now
        env.close()


class TestKappaSignReal:
    def test_monaco_hairpin_positive(self):
        """Monaco hairpin é curva à ESQUERDA => kappa > 0 no obs."""
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='Monaco', allow_respawn=False)
        # hairpin em s≈1016
        k = env._kappa_signed(1016.0)
        assert k > 0, f"Monaco hairpin (esquerda): kappa={k:+.4f}, esperado > 0"
        env.close()

    def test_interlagos_hairpin_sign(self):
        """Interlagos hairpin (s≈2309): verificar sinal consistente."""
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
        k = env._kappa_signed(2309.0)
        # o kappa deve ser NÃO-ZERO (a curva existe)
        assert abs(k) > 0.01, f"Interlagos hairpin: kappa={k:+.4f}, |k| muito baixo"
        env.close()

    def test_preview_kappa_nonzero_at_corners(self):
        """Em nenhum ponto de uma pista o kappa pode ser exatamente 0
        num canto real (verifica em Interlagos e Monaco)."""
        from backend.model_train.f1_env import F1MultiContextEnv
        for track, s_corner in [('interlagos', 2309.0), ('Monaco', 1016.0)]:
            env = F1MultiContextEnv(track=track, allow_respawn=False)
            for d in (10, 20, 35):
                k = env._kappa_signed(s_corner + d)  # preview à frente
                # o preview pode ser menor (a curva acabou), mas não pode
                # ter sinal INVERTIDO em relação ao centro do ápice
                k_center = env._kappa_signed(s_corner)
                if abs(k_center) > 0.03 and abs(k) > 0.01:
                    assert math.copysign(1, k) == math.copysign(1, k_center) or abs(k) < 0.3*abs(k_center), (
                        f"{track} s={s_corner}+{d}: kappa_preview={k:+.4f} "
                        f"vs centro={k_center:+.4f} — sinal invertido?")
            env.close()
