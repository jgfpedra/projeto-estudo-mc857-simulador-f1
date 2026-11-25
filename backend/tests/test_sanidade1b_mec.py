"""SANIDADE-1b — testes dos TETOS do M3-v2 (prereg 87214c7 §2/§7).

t2_1: preventivo — teto 1,0 s por episódio contíguo (10 ticks) + cooldown
      2,0 s: o offset aplica nos ticks 1..10, NÃO aplica durante o cooldown,
      e retoma depois (episódio 2 contado).
t2_2: preventivo — contagem máx 10 episódios por par por corrida: esgotado
      o par, hands-off (sem offset).
t2_3: preventivo — gate |Δv|<8 m/s (dv alto não recebe offset) e REVERT
      partner_offtrack (nunca age contra alvo na grama; D5).
t2_4: breaker — teto 4,0 s por episódio: engaja após 3 s colado, aplica por
      até 40 ticks, DESISTE (brk_done_run), não re-engaja no MESMO run
      contíguo, e re-engaja num run novo (eps por par contados).
t2_5: breaker — competência por velocidade: <25 m/s lift total (th=0) +
      0,4 rad (substituição); >=25 m/s suave (th<=0,5 + 0,15 aditivo); e
      contagem máx 8 eps/par/corrida.
t2_6: professor espelha via HERANÇA (_anti_glue_step compartilhado — nenhum
      re-implement no ProfessorRaceController) + wiring v2 (v1 MORTO).
"""
import inspect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.simulation.run_race_10_cars import NeuralRaceController as N


def _mk():
    """Instância mínima p/ unit-test do _anti_glue_step (constantes de
    classe; sem pesos/pybullet)."""
    c = N.__new__(N)
    c._glue_state = {}
    c._track_len_s = 4160.4
    return c


def _step(c, drv='A', p='B', ds=+7.0, dlat=+1.0, v=5.0, vp=5.0,
          slat_i=1.0, slat_p=2.0, p_off=False, th=0.9, brk=0.0,
          steer=0.0, scope=True):
    return c._anti_glue_step(drv, p, ds, dlat, v, vp, slat_i, slat_p,
                             p_off, th, brk, steer, scope)


def test_t2_1_prev_teto_1s_cooldown():
    c = _mk()
    applied = 0
    for k in range(10):                       # episódio 1: ticks 1..10
        th, brk, st, _ = _step(c, th=0.9, steer=0.0)
        if abs(st - (-0.25)) < 1e-9 and th <= 0.6:
            applied += 1
    assert applied == 10, f"episódio 1 deve aplicar 10 ticks (veio {applied})"
    # tick 11: TETO -> cooldown; offset NÃO aplica e th livre
    th, brk, st, _ = _step(c, th=0.9, steer=0.0)
    assert abs(st) < 1e-9 and th == 0.9, "teto 1s: cooldown deve suspender"
    for k in range(19):                        # cooldown 2 s = 20 ticks
        _step(c)
    th, brk, st, _ = _step(c, th=0.9, steer=0.0)
    assert abs(st - (-0.25)) < 1e-9, "pós-cooldown: episódio 2 retoma"
    assert c._glue_state['A']['prev_eps']['B'] == 2, "2 episódios contados"


def test_t2_2_prev_contagem_10_por_par():
    c = _mk()
    st = c._glue_state.setdefault(
        'A', dict(partner=None, ticks=0, breaking=False, prev_ticks=0,
                  prev_cool=0, prev_eps={'B': 10}, brk_ticks=0,
                  brk_done_run=False, brk_eps={}))
    th, brk, steer, _ = _step(c, th=0.9, steer=0.0)
    assert abs(steer) < 1e-9 and th == 0.9, \
        "10 episódios esgotados: preventivo hands-off no par B"
    # um par NOVO ainda recebe
    th, brk, steer, _ = _step(c, drv='A', p='C', th=0.9, steer=0.0)
    assert abs(steer - (-0.25)) < 1e-9, "par novo: offset aplica"


def test_t2_3_prev_dv_gate_e_revert_offtrack():
    c = _mk()
    th, brk, steer, _ = _step(c, v=20.0, vp=30.0, th=0.9)  # dv=10 > 8
    assert abs(steer) < 1e-9 and th == 0.9, "dv 10 m/s: sem offset (gate |dv|<8)"
    th, brk, steer, _ = _step(c, v=20.0, vp=26.0, th=0.9)  # dv=6 < 8
    assert abs(steer - (-0.25)) < 1e-9, "dv 6 m/s: offset aplica"
    # REVERT: parceiro na grama (D5) — nunca agir contra alvo off-track
    th, brk, steer, g = _step(c, p_off=True, th=0.9, steer=0.5)
    assert abs(steer - 0.5) < 1e-9 and th == 0.9 and not g, \
        "partner off-track: inerte (revert)"


def test_t2_4_breaker_teto_4s_desiste_e_re_engaja():
    c = _mk()
    g = False
    for k in range(31):                        # >3 s colado (ds=+2: eu atrás)
        th, brk, steer, g = _step(c, ds=+2.0, v=5.0, th=0.9, steer=0.1)
    assert g, "31 ticks colado: breaker deve engajar (sou o de trás)"
    st = c._glue_state['A']
    assert st['brk_eps']['B'] == 1
    # episódio breaker: 40 ticks de ação, depois DESISTE
    n_act = 0
    for k in range(45):
        th, brk, steer, g = _step(c, ds=+2.0, v=5.0, th=0.9, steer=0.1)
        if g:
            n_act += 1
    # 40 ticks de ação no TOTAL; o tick do engaje aplicou 1 no loop anterior
    assert n_act == 39, f"teto do episódio breaker = 40 ticks (veio {n_act})"
    assert not g and c._glue_state['A']['brk_done_run'], "desistiu"
    # mesmo run contíguo: NÃO re-engaja
    for k in range(40):
        _, _, _, g = _step(c, ds=+2.0, v=5.0)
    assert not g, "brk_done_run: sem re-engajo no mesmo run"
    # run novo (par some e volta): re-engaja (eps=2)
    _step(c, drv='A', p=None, p_off=True)      # limpa o run
    for k in range(35):
        th, brk, steer, g = _step(c, ds=+2.0, v=5.0, th=0.9)
    assert g and c._glue_state['A']['brk_eps']['B'] == 2


def test_t2_5_breaker_competencia_v_e_contagem():
    c = _mk()
    for k in range(31):                         # engaja a v=5 (< 25)
        th, brk, steer, g = _step(c, ds=+2.0, v=5.0, th=0.9, steer=0.1)
    assert g
    th, brk, steer, g = _step(c, ds=+2.0, v=5.0, th=0.9, steer=0.1)
    assert th == 0.0 and abs(steer + 0.4) < 1e-9, \
        "abaixo de 25 m/s: LIFT + 0,4 rad p/ FORA (dlat>0 -> -0,4; v1)"
    # acima de 25 m/s: suave — th só capado (sem lift), 0,15 aditivo
    c2 = _mk()
    for k in range(31):
        th, brk, steer, g = _step(c2, ds=+2.0, v=40.0, th=0.9, steer=0.1)
    assert g
    th, brk, steer, g = _step(c2, ds=+2.0, v=40.0, th=0.9, steer=0.1)
    assert th == 0.5 and abs(steer - (0.1 - 0.15)) < 1e-9, \
        "acima de 25 m/s: th<=0,5 + 0,15 aditivo (grip satura — R7b)"
    # contagem 8/par: esgotada, não engaja mais
    c3 = _mk()
    st = c3._glue_state.setdefault(
        'A', dict(partner=None, ticks=0, breaking=False, prev_ticks=0,
                  prev_cool=0, prev_eps={}, brk_ticks=0,
                  brk_done_run=False, brk_eps={'B': 8}))
    for k in range(40):
        th, brk, steer, g = _step(c3, ds=+2.0, v=5.0, th=0.9)
    assert not g, "8 episódios breaker esgotados: hands-off no par"


def test_t2_6_professor_espelha_por_heranca_e_v1_morto():
    src = inspect.getsource(N._anti_glue_step)
    assert 'PREV_MAX_EP_TICKS' in src or 'ANTI_GLUE_PREV' in src
    rd = (Path(__file__).resolve().parent.parent
          / 'model_train' / 'race_diagnostic.py').read_text()
    assert 'self._anti_glue_step(' in rd, "professor sem o helper herdado"
    assert 'def _anti_glue_step' not in rd, "professor NÃO re-implementa (herança)"
    rr = (Path(__file__).resolve().parent.parent
          / 'scripts' / 'simulation' / 'run_race_10_cars.py').read_text()
    assert 'SANIDADE-1b M3-v2' in rr and 'v1 MORTO' in rr
    # v2 substitui v1 ATRÁS DA MESMA FLAG (sem flag nova)
    assert 'anti_glue: bool = False' in rr
    assert 'def _anti_glue_step' in rr and rr.count('def _anti_glue_step') == 1
