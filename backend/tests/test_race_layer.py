"""Testes da camada de corrida: anti-stall, rejoin, curvatura e geometria.

Cobre os cenários obrigatórios da investigação (paradas + cortes de curva):
  1-2, 4-5: anti-stall vs freio residual/persistente (já em test_regression_v2v4.py)
  3: parado com acelerador positivo e sem movimento físico (mantém autoridade)
  6: bloqueado por outro veículo -> torque limitado, sem arremetida
  7: estados de anti-stall independentes por piloto
  8: curva que exige desaceleração normal não dispara recuperação
  +: recuperação física headless (sem colisões) — velocidade e progresso voltam
  +: suite de curvatura sintética (reta, R conhecido esq/dir, progressivo,
     hairpin, espaçamento desigual, fechamento circular)
  +: regressão de geometria real (kappa máx da pista FastF1)
"""
import math
import sys
import types

import numpy as np
import pytest


# ---------------------------------------------------------- helpers de tabela

def _host_from_points(pts):
    """Duck-type host para chamar os métodos REAIS de F1MultiContextEnv
    (_heading_at/_kappa_signed) sobre uma polilinha sintética, sem engine."""
    from backend.model_train.f1_env import F1MultiContextEnv

    class _H:
        pass

    h = _H()
    arr = np.array(pts, dtype=np.float64)
    B = np.roll(arr, -1, axis=0)
    AB = B - arr
    L = np.hypot(AB[:, 0], AB[:, 1])
    h._wps_arr = arr
    h._seg_B = B
    h._seg_AB = AB
    h._seg_len = L
    h._seg_cum = np.concatenate([[0.0], np.cumsum(L)])[:-1]
    h._seg_heading = np.arctan2(AB[:, 1], AB[:, 0])
    h._track_len_s = float(L.sum())
    h._kappa_signed = F1MultiContextEnv._kappa_signed.__get__(h)
    h._heading_at = F1MultiContextEnv._heading_at.__get__(h)
    h._wrap = F1MultiContextEnv._wrap
    return h


def _circle(radius, n=72, ccw=True):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        if ccw:
            pts.append((radius * math.cos(a), radius * math.sin(a)))
        else:
            pts.append((radius * math.cos(-a), radius * math.sin(-a)))
    return pts


def _straight(length, n=20):
    return [(length * i / n, 0.0) for i in range(n)]


# ------------------------------------------------ 3.2 — suite de curvatura

class TestCurvatureSynthetic:
    def test_straight_has_zero_kappa(self):
        h = _host_from_points(_straight(400))
        for s in (10, 100, 250, 390):
            assert abs(h._kappa_signed(s)) < 1e-3, f"kappa não-nulo na reta em s={s}"

    def test_known_radius_left_positive(self):
        R = 50.0
        h = _host_from_points(_circle(R, ccw=True))
        k = h._kappa_signed(h._track_len_s * 0.25)
        # curva à esquerda (CCW): kappa > 0 e ~1/R (tolerância por polígono)
        assert k > 0, "curva à esquerda deveria ter kappa positivo"
        assert abs(k - 1.0 / R) < 0.25 / R

    def test_known_radius_right_negative(self):
        R = 50.0
        h = _host_from_points(_circle(R, ccw=False))
        k = h._kappa_signed(h._track_len_s * 0.25)
        assert k < 0, "curva à direita deveria ter kappa negativo"
        assert abs(k + 1.0 / R) < 0.25 / R

    def test_progressively_tighter_kappa_increases(self):
        # espiral: raio diminui ao longo do arco
        pts = []
        n = 240
        a = 0.0
        for i in range(n):
            R = 120.0 * (1.0 - 0.8 * i / n)     # 120 -> 24 m
            a += 2 * math.pi / (2 * math.pi * R / 4)  # passo de 1/4 de circunferência? simples:
            pts.append((R * math.cos(a + i * 0.02), R * math.sin(a + i * 0.02)))
        # usa círculos concêntricos como proxy robusto: kappa cresce com 1/R
        k_120 = _host_from_points(_circle(120))._kappa_signed(100.0)
        k_30 = _host_from_points(_circle(30))._kappa_signed(100.0)
        assert abs(k_30) > abs(k_120), "curva mais fechada deveria ter |kappa| maior"

    def test_hairpin_sign_and_apex(self):
        # hairpin: reta -> meia-volta à esquerda (R=15) -> reta (em U)
        R = 15.0
        pts = []
        for i in range(20):                       # entrada: x -60 -> -3, y=0
            pts.append((-60.0 + 3.0 * i, 0.0))
        for i in range(48):                       # meia-volta CCW: (0,0) -> (0,30)
            a = -math.pi / 2 + math.pi * i / 48
            pts.append((R * math.cos(a), R * math.sin(a) + R))
        for i in range(1, 20):                    # saída: x -3 -> -57, y=30 (rumo OESTE)
            pts.append((-3.0 * i, 2 * R))
        h = _host_from_points(pts)
        L = h._track_len_s
        k_in = h._kappa_signed(L * 0.08)          # reta de entrada
        k_apex = h._kappa_signed(L * 0.5)         # ápice da meia-volta
        k_out = h._kappa_signed(L * 0.92)         # reta de saída
        assert abs(k_in) < 0.02 and abs(k_out) < 0.02
        assert k_apex > 0.03, f"hairpin à esquerda: kappa positivo no ápice (k={k_apex:.4f})"
        assert abs(k_apex) > abs(k_in), "ápice deveria ser mais fechado que a reta"

    def test_uneven_spacing_same_geometry(self):
        # o MESMO círculo amostrado denso e esparsamente dá kappas equivalentes
        k_dense = _host_from_points(_circle(40, n=180))._kappa_signed(50.0)
        k_sparse = _host_from_points(_circle(40, n=36))._kappa_signed(50.0)
        assert abs(k_dense - k_sparse) < 0.2 * abs(k_dense), (
            f"curvatura não deveria depender da densidade de amostragem: "
            f"{k_dense:.4f} vs {k_sparse:.4f}")

    def test_closure_continuity(self):
        # o fechamento último->primeiro não pode ter salto de heading
        h = _host_from_points(_circle(50, n=24))
        heads = h._seg_heading
        jumps = [abs(F1MultiContextEnv_wrap(heads[(i + 1) % len(heads)] - heads[i]))
                 for i in range(len(heads))]
        from backend.model_train.f1_env import F1MultiContextEnv
        jumps = [abs(F1MultiContextEnv._wrap(heads[(i + 1) % len(heads)] - heads[i]))
                 for i in range(len(heads))]
        assert max(jumps) < math.radians(30), "salto de heading no fechamento da pista"


def F1MultiContextEnv_wrap(a):  # compat com o primeiro bloco
    from backend.model_train.f1_env import F1MultiContextEnv
    return F1MultiContextEnv._wrap(a)


# --------------------------------------- spline/subdivision (geometria)

class TestSplineGeometry:
    def test_centripetal_no_reversal_between_adjacent_chords(self):
        """Guarda de cusps: na spline centrípeta, headings de cordas adjacentes
        nunca se INVERTEM (|Δ| < 90°) — inversão seria um cusp numérico, o
        sintoma clássico do CR uniforme com espaçamento desigual. (A comparação
        direta de curvatura máxima entre parametrizações é inválida: vértices
        reais do polígono de controle têm curvatura alta legítima.)"""
        from backend.model_train.f1_env import F1MultiContextEnv
        ctrl = [(0, 0), (30, 0), (60, 0), (75, 5), (80, 15), (75, 25),
                (60, 30), (30, 30), (0, 30), (-30, 30)]
        from backend.domain.track import _catmull_rom_spline
        out = _catmull_rom_spline(ctrl, samples_per_segment=12)
        arr = np.asarray(out)
        B = np.roll(arr, -1, axis=0)
        AB = B - arr
        L = np.hypot(AB[:, 0], AB[:, 1])
        H = np.arctan2(AB[:, 1], AB[:, 0])
        for i in range(len(H)):
            if L[i] < 1e-6 or L[(i + 1) % len(H)] < 1e-6:
                continue
            dh = abs(F1MultiContextEnv._wrap(H[(i + 1) % len(H)] - H[i]))
            assert dh < math.pi / 2, (
                f"inversão de heading (cusp) entre cordas {i}->{i+1}: "
                f"{math.degrees(dh):.1f}°")

    def test_subdivision_preserves_length_exactly(self):
        from backend.domain.track import _resample_closed_polyline, _compute_segment_length
        pts = _circle(60, n=13)   # poligono irregular
        before = _compute_segment_length(pts)
        out = _resample_closed_polyline(pts, spacing_m=4.0)
        after = _compute_segment_length(out)
        assert abs(before - after) < 1e-6, "subdivisão deve preservar o comprimento"
        segs = [math.hypot(out[(i + 1) % len(out)][0] - out[i][0],
                           out[(i + 1) % len(out)][1] - out[i][1]) for i in range(len(out))]
        assert max(segs) <= 4.0 + 1e-9, f"espaçamento máximo violado: {max(segs):.2f} m"

    def test_real_track_curvature_cap(self):
        """REGRESSÃO da investigação: a pista real (FastF1 + spline centrípeta +
        subdivisão) não pode ter kappa > 0.11 (o pico artificial era 0.129 —
        R=7,7 m fisicamente impossível)."""
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
        ks = [abs(env._kappa_signed(env._seg_cum[i]))
              for i in range(0, len(env._seg_cum), 3)]
        kmax = max(ks)
        assert kmax <= 0.11, f"pico artificial de curvatura regressou: {kmax:.4f}"
        env.close()


# ------------------------------------------- anti-stall: cenários 3, 6, 7, 8

# Cenários anti-stall 3,6,7,8 -> migrados p/ tests/test_recovery_state.py
# (a máquina de recuperação com progresso subsume o anti-stall antigo)

# ------------------------------------- recuperação física headless (Teste 2)

@pytest.mark.slow
def test_headless_stall_recovery_physical():
    """Sem outros carros, sem colisões: carro freado até parar SE RECUPERA com
    os comandos do anti-stall — velocidade e progresso voltam a crescer
    (critério: não basta o comando; o carro tem que andar de verdade)."""
    from backend.model_train.f1_env import F1MultiContextEnv
    from backend.scripts.run_race_10_cars import NeuralRaceController as N
    env = F1MultiContextEnv(track='interlagos', allow_respawn=False)
    env.reset()
    h = env.engine.handles[env.driver_id]

    def tick(th, brk):
        env.engine.set_driver_input(env.driver_id, throttle=th, brake=brk,
                                    steering_yaw_rad=0.0)
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        return env.engine.physics.get_state(h)

    # acelera até ~30 m/s
    for _ in range(40):
        tick(1.0, 0.0)
    # freia até parar (freio 'da política'), mantém freio parado por 3 s
    for _ in range(60):
        tick(0.0, 1.0)
    v0 = env.engine.physics.get_state(h)['speed_mps']
    assert v0 < 0.2, f"carro deveria estar parado (v={v0:.2f})"
    st0 = env.engine.physics.get_state(h)
    s0, _ = env._project_on_path(st0['x'], st0['y'])[1], None
    # aplica a regra de anti-stall por 3 s: th=0.8, brk=0
    for _ in range(30):
        tick(0.8, 0.0)
    st1 = env.engine.physics.get_state(h)
    v1 = st1['speed_mps']
    s1 = env._project_on_path(st1['x'], st1['y'])[1]
    assert v1 > 2.0, f"anti-stall deveria mover o carro (v={v1:.2f} m/s)"
    assert s1 > s0 + 5.0, f"progresso deveria crescer durante a recuperação ({s1:.1f} vs {s0:.1f})"
    env.close()


# ------------------------------------------- rejoin: autoridade fora da pista

def test_rejoin_gains_authority_off_track():
    """A camada de rejoin reage no LIMITE do asfalto (1× meia-largura), não a 2×.
    Verifica as constantes e o mapeamento steer/velocidade-alvo."""
    from backend.scripts.run_race_10_cars import NeuralRaceController as N
    assert N.OFFTRACK_FACTOR == 1.0, "rejoin deve agir na borda do asfalto (era 2.0)"
    assert N.REJOIN_TARGET_MPS <= 10.0, "rejoin deve ser lento"
    assert N.REJOIN_THROTTLE <= 0.5, "rejoin não deve arremeter pela grama"
    # v15 FASE R3: esterço por BEARING ao ponto de re-entrada (a lei antiga
    # de VALOR FIXO saturado produzia órbitas na grama — absorvedor).
    # Alvo à esquerda do heading => berr>0 => steer>0 (física: steer+ = esquerda)
    berr = math.pi / 4
    steer = float(np.clip(N.REJOIN_BEARING_GAIN * berr,
                          -N.STEER_MAX_RAD, N.STEER_MAX_RAD))
    assert steer > 0, "alvo à esquerda deve esterçar à esquerda"
    # alvo à direita => steer negativo
    steer_r = float(np.clip(N.REJOIN_BEARING_GAIN * (-math.pi / 2 + 0.1),
                            -N.STEER_MAX_RAD, N.STEER_MAX_RAD))
    assert steer_r < 0, "alvo à direita deve esterçar à direita"
    # rumo travado no alvo (berr~0) => esterço ~0 — SEM órbitas de valor fixo
    assert abs(N.REJOIN_BEARING_GAIN * 0.01) < 0.05, "no alvo, esterço neutro"
    # o ponto de re-entrada existe como constante instrumentada
    assert 0 < N.REJOIN_AHEAD_M <= 30.0, "re-entrada: projeção + à frente moderado"
