"""Testes da camada de TRÁFEGO do professor (PASSO 1 v14 — gate all-professor).

Cobre os testes obrigatórios ANTES do gate (ver tasks v14):
  a) SINAL DO OFFSET: carro à frente à ESQUERDA da linha -> o follower
     desloca o PONTO DE PERSEGUIÇÃO à DIREITA (e vice-versa), com tráfego
     stubado (sem PyBullet — engine de mentira);
  b) CAR-FOLLOWING: fechando a 20 m/s de Δv -> v_alvo = v_ahead + 2;
     abaixo de D_FOLLOW -> v_alvo = v_ahead;
  c) MÉTRICA DE DISTÂNCIA: dist_s AO LONGO DA PISTA com sinal
     (positiva = à frente); carro 5 m atrás dá -5 (não +L-5);
  d) BACKWARDS COMPAT: tráfego None -> comportamento solo idêntico
     (offset zero, ponto de perseguição sem deslocamento, modo 'none').
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend')):
    if p not in sys.path:
        sys.path.insert(0, p)


# --------------------------------------------------------------- stub de env

def _circle(radius, n=72, ccw=True):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        if ccw:
            pts.append((radius * math.cos(a), radius * math.sin(a)))
        else:
            pts.append((radius * math.cos(-a), radius * math.sin(-a)))
    return pts


def _stub_env(ego_x, ego_y, speed_mps=30.0, heading_rad=None, half_width=6.0,
              pts=None):
    """Env duck-typed p/ o ReferenceController: métodos REAIS do
    F1MultiContextEnv emprestados sobre uma polilinha sintética (padrão do
    _host_from_points do test_race_layer), com engine/physics de mentira —
    nenhum PyBullet é instanciado."""
    from backend.model_train.f1_env import F1MultiContextEnv

    class _Phys:
        def __init__(self, state):
            self.state = state

        def get_state(self, handle):
            return self.state

    class _Engine:
        def __init__(self, state):
            self.handles = {'EGO': object()}
            self.physics = _Phys(state)

    class _H:
        # métodos REAIS do env — fonte única de verdade (sem duplicação)
        _project_on_path = F1MultiContextEnv._project_on_path
        _point_at = F1MultiContextEnv._point_at
        _kappa_signed = F1MultiContextEnv._kappa_signed
        _heading_at = F1MultiContextEnv._heading_at
        steer_limit_rad = staticmethod(F1MultiContextEnv.steer_limit_rad)

    h = _H()
    arr = np.array(pts if pts is not None else _circle(200.0), dtype=np.float64)
    B = np.roll(arr, -1, axis=0)
    AB = B - arr
    L = np.hypot(AB[:, 0], AB[:, 1])
    h._wps_arr = arr
    h._seg_AB = AB
    h._seg_len = L
    h._seg_cum = np.concatenate([[0.0], np.cumsum(L)])[:-1]
    h._seg_heading = np.arctan2(AB[:, 1], AB[:, 0])
    h._track_len_s = float(L.sum())
    h._half_width = half_width
    # heading default: tangente da pista na posição do ego
    if heading_rad is None:
        _, s, _, _ = F1MultiContextEnv._project_on_path(h, ego_x, ego_y)
        heading_rad = F1MultiContextEnv._heading_at(h, s)
    h.engine = _Engine({'x': ego_x, 'y': ego_y, 'speed_mps': speed_mps,
                        'heading_rad': heading_rad, 'yaw_rate': 0.0,
                        'g_lat': 0.0, 'g_long': 0.0})
    h.driver_id = 'EGO'
    return h


def _stub_controller(env, sf=0.80):
    from backend.model_train.reference_controller import ReferenceController
    from backend.model_train.velocity_profile import VelocityProfile
    vp = VelocityProfile(env._wps_arr, grip_mult=0.788, sf=sf,
                         ds_target=4.0, smooth_window_m=20.0)
    return ReferenceController(env, velocity_profile=vp)


# ------------------------------------------------- (c) métrica de distância

class TestSignedDistS:
    def test_ahead_positive_behind_negative(self):
        from backend.model_train.reference_controller import signed_dist_s
        L = 4309.0
        assert signed_dist_s(1005.0, 1000.0, L) == pytest.approx(5.0)
        # carro 5 m ATRÁS: -5, e NÃO +L-5 (o que o `% L` cru daria)
        assert signed_dist_s(995.0, 1000.0, L) == pytest.approx(-5.0)

    def test_wrap_forward_across_start(self):
        from backend.model_train.reference_controller import signed_dist_s
        L = 4309.0
        # ego no fim da pista, outro 20 m à frente (cruzou a largada)
        assert signed_dist_s(10.0, L - 10.0, L) == pytest.approx(20.0)
        # e o simétrico: 20 m atrás cruzando a largada
        assert signed_dist_s(L - 10.0, 10.0, L) == pytest.approx(-20.0)

    def test_range_half_track(self):
        from backend.model_train.reference_controller import signed_dist_s
        L = 4309.0
        for d in (-2000.0, -1000.0, 0.0, 999.99, 2000.0):
            assert -L / 2 <= signed_dist_s(1000.0 + d, 1000.0, L) < L / 2

    def test_professor_ignores_car_behind(self):
        """O professor só SEGUE carro à frente; carro atrás (dist_s<0) não
        entra na janela de car-following (não há defesa ativa no v14)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # carro 10 m ATRÁS, mais lento — não deve gerar cap nenhum
        v_cap, off = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(90.0, 0.0, 20.0)])
        assert v_cap is None
        assert ctrl.last_follow_mode == 'none'


# ------------------------------------------------------ (b) car-following

class TestCarFollowing:
    def test_closing_20mps_cap_is_vahead_plus_2(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # ego a 40, à frente a 50 m andando 20: fechando a 20 m/s
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(150.0, 0.0, 20.0)])
        assert v_cap == pytest.approx(22.0)   # v_ahead + V_MARGIN (2.0)
        assert ctrl.last_follow_mode == 'cap'

    def test_inside_d_follow_matches_vahead(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # gap 20 m < D_FOLLOW (25): colado, v_alvo = v_ahead
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(120.0, 0.0, 20.0)])
        assert v_cap == pytest.approx(20.0)
        assert ctrl.last_follow_mode == 'close'

    def test_no_cap_when_faster_ahead(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, _ = ctrl._traffic_adjust(100.0, 15.0, 0.0, [(150.0, 0.0, 25.0)])
        assert v_cap is None

    def test_beyond_d_ahead_ignored(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(170.0, 0.0, 20.0)])
        assert v_cap is None   # 70 m > D_AHEAD (60): fora do alcance

    def test_nearest_ahead_wins(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(180.0, 0.0, 20.0),   # 80 m à frente
                                         (125.0, 0.0, 18.0)])  # 25 m à frente
        assert v_cap == pytest.approx(18.0 + 2.0)   # segue o MAIS PRÓXIMO


# ------------------------------------------------- (a) sinal do offset

class TestOffsetSign:
    def test_traffic_adjust_offset_sign(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # carro à frente à ESQUERDA da linha (lat +2) -> offset p/ DIREITA (<0)
        _, off = ctrl._traffic_adjust(100.0, 30.0, 0.0, [(150.0, +2.0, 25.0)])
        assert off < 0
        # e vice-versa: carro à direita -> offset p/ ESQUERDA (>0)
        _, off = ctrl._traffic_adjust(100.0, 30.0, 0.0, [(150.0, -2.0, 25.0)])
        assert off > 0

    def test_pursuit_point_shifts_right_when_ahead_car_left(self):
        """(a) com tráfego stubado: o PONTO DE PERSEGUIÇÃO desloca à
        DIREITA quando o carro à frente está à esquerda — e à esquerda no
        caso espelho. Deslocamento medido na normal ESQUERDA da pista no
        ponto de perseguição (convenção do env: +lat = esquerda)."""
        env = _stub_env(200.0, 0.0, speed_mps=30.0)
        ctrl = _stub_controller(env)
        L = env._track_len_s
        _, s_ego, _, _ = env._project_on_path(200.0, 0.0)

        # linha de base solo
        ctrl.action(traffic=None)
        base = np.array(ctrl._last_pursuit)
        assert ctrl._lat_offset == 0.0

        # 30 ticks com carro à frente à ESQUERDA -> offset converge ao alvo
        for _ in range(30):
            ctrl.action(traffic=[(s_ego + 30.0, +2.0, 25.0)])
        # Exp2 (FASE 2b): com a máquina engajada (líder lento + fechando), o
        # alvo lateral é a LINHA DE PASSAGEM = lat_líder − lado·2,75 = −0,75
        # (2,75 m À DIREITA do líder — direção preservada; magnitude = margem
        # de passagem, não o corredor ±2,5 do centro)
        assert ctrl._lat_offset < -0.5, "pursuit deve estar à DIREITA do líder"
        assert ctrl._lat_offset == pytest.approx(2.0 - 2.75, abs=0.1)
        shifted = np.array(ctrl._last_pursuit) - base
        # normal esquerda no ponto de perseguição
        _, tx, ty, th = (None, *env._point_at(s_ego + 18.0))
        n_left = np.array([-math.sin(th), math.cos(th)])
        assert float(np.dot(shifted, n_left)) < -0.5, (
            "ponto de perseguição deveria deslocar à DIREITA (oposto da "
            "normal esquerda) quando o carro à frente está à esquerda")

    def test_pursuit_point_shifts_left_when_ahead_car_right(self):
        env = _stub_env(200.0, 0.0, speed_mps=30.0)
        ctrl = _stub_controller(env)
        _, s_ego, _, _ = env._project_on_path(200.0, 0.0)
        ctrl.action(traffic=None)
        base = np.array(ctrl._last_pursuit)
        for _ in range(30):
            ctrl.action(traffic=[(s_ego + 30.0, -2.0, 25.0)])
        # espelho: linha de passagem = −2,0 + 2,75 = +0,75 (À ESQUERDA do líder)
        assert ctrl._lat_offset > 0.5, "pursuit deve estar à ESQUERDA do líder"
        assert ctrl._lat_offset == pytest.approx(-2.0 + 2.75, abs=0.1)
        shifted = np.array(ctrl._last_pursuit) - base
        _, tx, ty, th = (None, *env._point_at(s_ego + 18.0))
        n_left = np.array([-math.sin(th), math.cos(th)])
        assert float(np.dot(shifted, n_left)) > 0.5

    def test_ahead_car_near_edge_no_offset(self):
        """Carro à frente colado na borda (|lat| > 0.6·hw): offset zero —
        o centro da pista está livre, não há por que deslocar."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        _, off = ctrl._traffic_adjust(100.0, 30.0, 0.0, [(150.0, +5.0, 25.0)])
        assert off == 0.0


# ----------------------------- (PASSO 0.2) condição de CORREDOR do offset

class TestOffsetCorridor:
    """PASSO 0.2 v14 FASE 3: o offset só dispara quando o líder está no MEU
    corredor lateral (|lat_ahead − lat_ego| < 3,5 m). Evidência do gate:
    pares de fileira do grid (Δlat = 3,8 m) cruzavam a pista e colidiam na
    largada (258 contatos, t=1,2-47,8 s)."""

    def test_opposite_grid_column_never_fires(self):
        """Caso do grid: líder na coluna oposta (Δlat=3,8 > 3,5) -> offset 0
        (o follower NÃO cruza a pista — fix da largada)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        _, off = ctrl._traffic_adjust(100.0, 30.0, -1.9, [(150.0, +1.9, 25.0)])
        assert off == 0.0
        # espelho
        _, off = ctrl._traffic_adjust(100.0, 30.0, +1.9, [(150.0, -1.9, 25.0)])
        assert off == 0.0

    def test_same_column_fires_away_from_leader(self):
        """Líder na MESMA coluna (Δlat≈0): dispara, p/ o lado oposto ao líder."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # líder à direita (-1,9), ego também à direita -> desloca à esquerda
        _, off = ctrl._traffic_adjust(100.0, 30.0, -1.9, [(150.0, -1.9, 25.0)])
        assert off > 0
        # líder à esquerda (+1,9), ego à esquerda -> desloca à direita
        _, off = ctrl._traffic_adjust(100.0, 30.0, +1.9, [(150.0, +1.9, 25.0)])
        assert off < 0

    def test_same_line_boundary(self):
        """FASE 2 (2.3): a fronteira efetiva agora é a MESMA LINHA
        (LAT_SAME_LINE_M=2,6 — janela calibrada 2,5-2,75). Δlat=2,5: líder
        legítimo (offset dispara); Δlat=2,7: carro LATERAL — nem offset nem
        cap (anti-recíproco do PASS)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        _, off_in = ctrl._traffic_adjust(100.0, 30.0, -1.25, [(150.0, +1.25, 25.0)])
        v_out, off_out = ctrl._traffic_adjust(100.0, 30.0, -1.35, [(150.0, +1.35, 25.0)])
        assert off_in != 0.0
        assert off_out == 0.0 and v_out is None, "carro lateral: nem cap nem offset"

    def test_lateral_car_no_cap_no_offset(self):
        """FASE 2 (2.3) — spec atualizada: a condição do corredor virava a
        segurança anti-recíproco — carro LATERAL (|Δlat| > 2,6, ex. passador
        ao lado) não gera cap NEM offset no seguidor."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, off = ctrl._traffic_adjust(100.0, 40.0, -1.9, [(150.0, +1.9, 20.0)])
        assert v_cap is None and off == 0.0


# ------------------------------------------------- (d) backwards compat

class TestSoloCompat:
    def test_traffic_none_keeps_solo_behavior(self):
        """traffic=None (solo, DAgger atual): offset NUNCA se move, ponto
        de perseguição idêntico ao _point_at puro, modo 'none'."""
        env = _stub_env(200.0, 0.0, speed_mps=30.0)
        ctrl = _stub_controller(env)
        for _ in range(10):
            a = ctrl.action()          # mesmo sem argumento
            assert ctrl._lat_offset == 0.0
            assert ctrl.last_follow_mode == 'none'
        _, s_ego, _, _ = env._project_on_path(200.0, 0.0)
        tx, ty, _ = env._point_at(s_ego + 18.0)
        assert ctrl._last_pursuit == pytest.approx((tx, ty))
        # ação em [-1,1]², dtype float32 (contrato do env)
        assert a.shape == (2,) and a.dtype == np.float32
        assert np.all(np.abs(a) <= 1.0)

    def test_traffic_empty_list_same_as_none(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl.action(traffic=[])
        assert ctrl._lat_offset == 0.0
        assert ctrl.last_follow_mode == 'none'


# --------------------- (FASE 6) líder parado = obstáculo a contornar

class TestStoppedLeader:
    """PASSO 2b FASE 6: líder com v < V_MIN_FOLLOW não gera v_cap — sem isso
    o professor rasteja a V_MARGIN m/s atrás de um carro parado (causa-raiz
    medida do encravamento); o corredor de offset desvia em vez de seguir."""

    def test_stopped_leader_no_cap(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(130.0, 0.0, 0.5)])
        assert v_cap is None, "líder parado não deve gerar cap (contorna)"
        assert ctrl.last_follow_mode == 'none'

    def test_slow_leader_still_caps(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(130.0, 0.0, 3.0)])
        assert v_cap == pytest.approx(5.0)   # 3,0 + V_MARGIN

    def test_stopped_leader_still_triggers_offset(self):
        """Sem cap mas COM offset: o ponto de perseguição desloca para o
        lado oposto do obstáculo (o mecanismo de contorno)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        _, off = ctrl._traffic_adjust(100.0, 30.0, 0.0, [(130.0, +0.5, 0.0)])
        assert off < 0   # líder à esquerda → desvia à direita


# ------------------ FASE 2 (v15): segurança anti-recíproco + máquina PASS

class TestPassSafety:
    """2.3: carros LATERAIS não são líderes — nem cap, nem offset."""

    def test_a_leader_with_car_alongside_leader_not_distracted(self):
        """(a) líder lento à frente + passador AO LADO (Δlat 2,8, dist 2 m):
        o cap/offset vêm SÓ do líder — o passador é invisível p/ o follow."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        traffic = [(150.0, 0.0, 20.0),        # líder legítimo (Δlat 0, à frente)
                   (102.0, 2.8, 30.0)]        # passador ao lado (Δlat 2,8 > 2,6)
        v_cap, off = ctrl._traffic_adjust(100.0, 40.0, 0.0, traffic)
        assert v_cap == pytest.approx(22.0)   # do líder (20+2), não do passador
        assert off < 0.0                      # offset pelo lado do líder (dir)
        # e o PASS do passador não foi corrompido pelo líder: (o estado do
        # EGO segue FOLLOW — o líder é legítimo, sem fechamento extra aqui)

    def test_b_two_passers_opposite_sides_no_mutual_evade(self):
        """(b) dois carros laterais (±2,8) — nenhum é líder: sem cap, sem
        offset (o mecanismo anti-recíproco: um não desvia para o outro)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, off = ctrl._traffic_adjust(100.0, 40.0, 0.0,
                                         [(102.0, +2.8, 30.0),
                                          (98.0, -2.8, 30.0)])
        assert v_cap is None and off == 0.0

    def test_d_stopped_leader_regression_still_works(self):
        """(d) regressão FASE 6: líder PARADO na mesma linha continua sem
        cap (V_MIN_FOLLOW) e com offset de contorno — a regra 2.3 não pode
        ter quebrado o cenário carro-parado."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        v_cap, off = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(130.0, 0.0, 0.5)])
        assert v_cap is None
        assert off != 0.0  # contorna


class TestPassStateMachine:
    """2.2: FOLLOW→PREPARE→PASS→RETURN com cap LEVANTADO no PASS."""

    def _prep(self, traffic, lat_ego=0.0, v=30.0):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # contrato do action(): v_plan_here = o PRÓPRIO profile em s (o
        # profile do círculo dá ~117 m/s — não 200: passar valor manual
        # inconsistente quebrava a condição "sem freio à frente")
        lift, off, state = ctrl._pass_layer(100.0, v, lat_ego, traffic,
                                            float(ctrl.v_profile.at(100.0)))
        return ctrl, lift, off, state

    def test_follow_to_prepare(self):
        """Fechando sobre líder lento em κ baixo, lado livre → PREPARE.
        Exp3: PREPARE JÁ pre-abre a margem (off = 2,75, não None)."""
        ctrl, lift, off, st = self._prep([(140.0, 0.0, 10.0)])  # 40 m, lento
        assert st == 'PREPARE'
        assert lift is False and off == pytest.approx(2.75)  # pré-abertura

    def test_no_prepare_without_straight_window(self):
        """Exp3: sem janela de reta (v_plan cai à frente), NÃO engaja —
        aborto por geometria, não por contato."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # stub do v_profile: v_plan alto em s mas baixo à frente (curva)
        class FakeVP:
            def __init__(self, real): self.real = real
            def at(self, s): return 10.0 if s > 150.0 else float(self.real.at(s))
        vp_orig = ctrl.v_profile
        ctrl.v_profile = FakeVP(vp_orig)
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 0.0, [(140.0, 0.0, 10.0)],
                                         float(vp_orig.at(100.0)))
        ctrl.v_profile = vp_orig
        assert st == 'FOLLOW', "sem janela de reta: não engaja"

    def test_no_prepare_with_planned_equal_pace(self):
        """Exp3: diferencial PLANEJADO — líder no MESMO plano (v_o = v_plan):
        sem diferencial, sem PREPARE (falsificação do controle homogêneo)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        vp = float(ctrl.v_profile.at(100.0))
        lift, off, st = ctrl._pass_layer(100.0, vp, 0.0, [(140.0, 0.0, vp)], vp)
        assert st == 'FOLLOW', "pace idêntico: nunca engaja"

    def test_c_prepare_aborts_with_third_car_on_target_side(self):
        """(c) terceiro carro no lado alvo (±25 m) → não inicia PASS."""
        ctrl, lift, off, st = self._prep([(140.0, 0.0, 10.0),   # líder
                                          (115.0, 2.75, 25.0)])  # 3º no lado alvo
        assert st == 'FOLLOW', "terceiro no lado alvo bloqueia o PREPARE"

    def test_prepare_applies_margin_immediately(self):
        """Exp2: PREPARE (sem commit ainda) JÁ desloca — margem materializada
        antes do commit (resolve o empurrão: lateral existe desde o início)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'PREPARE'
        ctrl._pass_target = (0.0, +1.0, 0)
        # gap 35 m (> 30 = sem commit) e Δv ZERO (cap equalizou — o caso que
        # travava o predicado antigo v_ego−v_o>0,5)
        lift, off, st = ctrl._pass_layer(100.0, 25.0, 0.0,
                                         [(135.0, 0.0, 25.0)], 200.0)
        assert st == 'PREPARE'
        assert off == pytest.approx(2.75)          # margem desde o PREPARE
        assert lift is False                       # cap segue até o commit

    def test_commit_by_gap_without_closing_speed(self):
        """Exp2: commit por GAP puro — d < 30 ⇒ PASS mesmo com Δv = 0 (o cap
        v_ahead+2 equalizou; o predicado antigo nunca sustentava)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'PREPARE'
        ctrl._pass_target = (0.0, +1.0, 0)
        lift, off, st = ctrl._pass_layer(100.0, 25.0, 0.0,
                                         [(125.0, 0.0, 25.0)], 200.0)  # 25 m, Δv 0
        assert st == 'PASS' and lift is True       # cap LEVANTADO
        assert off == pytest.approx(2.75)           # margem ≥ 2,5 m

    def test_pass_completes_to_return(self):
        """Alvo ≥ 8 m à frente (não mais líder válido < G_p... â 9 m ainda
        é < 45 m e Δlat 0 — válidona verdade: RETURN dispara a 9 m)."""
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'PASS'
        ctrl._pass_target = (0.0, +1.0, 0)
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 2.75,
                                         [(109.0, 0.0, 10.0)], 200.0)  # 9 m à frente
        assert st == 'RETURN' and off == 0.0 and lift is False

    def test_return_finishes_then_cooldown(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'RETURN'
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 0.3, [], 200.0)
        assert st == 'COOLDOWN' and ctrl._pass_cooldown > 0
        # durante cooldown não re-engaja
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 0.3, [(140.0, 0.0, 10.0)], 200.0)
        assert st == 'COOLDOWN'


class TestMachineOnlyFlag:
    """FASE 2b Exp1: com _overtake_machine_only, o offset do follow é
    SUPRIMIDO (o cap permanece) — só a máquina desloca lateralmente."""

    def test_flag_suppresses_follow_offset_keeps_cap(self):
        # s real do stub (carro em (200,0) do círculo → s≈0): líder a 30 m
        env = _stub_env(200.0, 0.0, speed_mps=30.0)
        ctrl = _stub_controller(env)
        _, s_ego, _, _ = env._project_on_path(200.0, 0.0)
        ctrl._overtake_machine_only = True
        ctrl.action(traffic=[(s_ego + 30.0, 0.0, 20.0)])
        # Exp3: com a PRÉ-ABERTURA, o próprio _pass_layer engaja PREPARE e
        # desloca a margem — o CORREDOR de follow é o que fica suprimido. O
        # teste verifica que o offset (se houver) vem da MÁQUINA (p_state
        # PREPARE), não do corredor: líder lento a 30 m com janela = PREPARE.
        assert ctrl.last_pass_state in ('PREPARE', 'PASS'), (
            f"com flag, quem desloca é a máquina (estado: {ctrl.last_pass_state})")
        assert ctrl.last_follow_mode in ('cap', 'close'), "cap de follow intacto"

    def test_without_flag_follow_offset_active(self):
        env = _stub_env(200.0, 0.0, speed_mps=30.0)
        ctrl = _stub_controller(env)
        _, s_ego, _, _ = env._project_on_path(200.0, 0.0)
        ctrl.action(traffic=[(s_ego + 30.0, 0.0, 20.0)])
        assert ctrl._lat_offset != 0.0, "sem flag, o corredor de offset age"


class TestPassCompletionSign:
    """FASE 2c: o teste de conclusão do PASS é ALVO ≥8 m ATRÁS (d_t < −8),
    não à frente — o sinal invertido fazia RETURN disparar 1 tick após o
    commit (manobra nunca acontecia; Δlat+3s medido ~0)."""

    def test_pass_holds_while_target_still_ahead(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'PASS'
        ctrl._pass_target = (0.0, +1.0, 0)
        # alvo 15 m À FRENTE (recém-commitado): PASS deve SEGURAR
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 2.0,
                                         [(115.0, 0.0, 20.0)], 200.0)
        assert st == 'PASS' and lift is True

    def test_pass_completes_only_when_target_behind_8m(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'PASS'
        ctrl._pass_target = (0.0, +1.0, 0)
        # alvo 9 m ATRÁS (d = -9): concluído -> RETURN
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 2.0,
                                         [(91.0, 0.0, 20.0)], 200.0)
        assert st == 'RETURN' and off == 0.0 and lift is False

    def test_pass_holds_at_target_5m_behind(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        ctrl._pass_state = 'PASS'
        ctrl._pass_target = (0.0, +1.0, 0)
        lift, off, st = ctrl._pass_layer(100.0, 30.0, 2.0,
                                         [(95.0, 0.0, 20.0)], 200.0)
        assert st == 'PASS', "alvo 5 m atrás: ainda não concluiu (margem <8 m)"


class TestCloseGapReopen:
    """v15 FASE 3 (0.2): gap < G_SAFE fechando → alvo ATRÁS do líder (reabre;
    o 'close' antigo mantinha v=v_ahead para sempre — contato a 3,7 m)."""

    def test_reopen_below_safe_gap(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # gap 5 m < G_SAFE (6): alvo = v_ahead − 0,5 = 19,5 (reabre)
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(105.0, 0.0, 20.0)])
        assert v_cap == pytest.approx(19.5)
        assert ctrl.last_follow_mode == 'reopen'

    def test_close_between_safe_and_follow(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # gap 15 m (entre 6 e 25): alvo = v_ahead (comportamento clássico)
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(115.0, 0.0, 20.0)])
        assert v_cap == pytest.approx(20.0)
        assert ctrl.last_follow_mode == 'close'

    def test_reopen_floors_at_min_follow(self):
        env = _stub_env(200.0, 0.0)
        ctrl = _stub_controller(env)
        # v_ahead = 1,2 (líder vivo mas MUITO lento): 1,2−0,5 = 0,7 < piso 1,0
        v_cap, _ = ctrl._traffic_adjust(100.0, 40.0, 0.0, [(105.0, 0.0, 1.2)])
        assert v_cap == pytest.approx(1.0)  # V_MIN_FOLLOW, não 0,7
