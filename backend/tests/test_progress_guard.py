"""ANTI-D3-1 — testes unitários do progress-guard (prereg 57a9342 §Suíte).

t1: guard dispara após N=5 ticks sem Δprogresso (g>0,01 e delta<0,5 →
no_prog conta; 5º tick → fade>0 → g_eff < g nominal).
t2: fade é LINEAR até 0 em F=5 ticks adicionais (5 ticks sem progresso →
   fade 0,2 cada; no 5º tick do fade g_eff=0; retoma: delta>=0,5 → fade=0).
t3: retoma com progresso (após fade total, um tick c/ delta>=0,5 zera fade).
t4: gate fechado (g<=0,01) não acumula estado (o guard só vigia gate aberto).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.run_race_10_cars import NeuralRaceController as N


def _sim_guard(deltas, g_seq):
    """Replica o loop do predict_batch linha a linha e devolve g_eff por tick."""
    state = dict(no_prog=0, fade=0.0, last_cum=None)
    out = []
    cum = 100.0
    for delta, g in zip(deltas, g_seq):
        cum += delta
        if g > 0.01:
            if delta < 0.5:
                state['no_prog'] += 1
            else:
                state['no_prog'] = 0
                state['fade'] = 0.0
            if state['no_prog'] >= 5:
                state['fade'] = min(1.0, state['fade'] + 1.0 / 5.0)
            g_eff = g * (1.0 - state['fade'])
        else:
            state['no_prog'] = 0
            state['fade'] = 0.0
            g_eff = g
        out.append(round(g_eff, 4))
    return out, state


def test_t1_guard_dispara_apos_5_ticks_sem_progresso():
    deltas = [0.0] * 6 + [1.0]
    gs = [1.0] * 7
    out, st = _sim_guard(deltas, gs)
    assert out[:4] == [1.0] * 4, "antes do 5º tick sem progresso o g_eff = g"
    assert out[4] == 0.8, f"5º tick: fade 0,2 -> g_eff 0,8 (veio {out[4]})"
    assert out[5] == 0.6
    assert out[6] == 1.0 and st['fade'] == 0.0, "progresso retoma fade=0"


def test_t2_fade_linear_ate_zero_em_F5():
    deltas = [0.0] * 10
    gs = [1.0] * 10
    out, st = _sim_guard(deltas, gs)
    # ticks 5..9: fade 0,2 0,4 0,6 0,8 1,0
    assert out == [1.0, 1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.0, 0.0], out
    assert st['fade'] == 1.0


def test_t3_retoma_com_progresso_apos_fade_total():
    deltas = [0.0] * 8 + [2.0, 2.0]
    gs = [1.0] * 10
    out, st = _sim_guard(deltas, gs)
    assert out[7] == 0.2 and out[8] == 1.0 and out[9] == 1.0
    assert st['no_prog'] == 0 and st['fade'] == 0.0


def test_t4_gate_fechado_nao_acumula():
    deltas = [0.0] * 8
    gs = [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    out, st = _sim_guard(deltas, gs)
    assert st['no_prog'] == 0 and st['fade'] == 0.0
    assert out[6] == 0.0, "gate fechado: g_eff = g = 0 (guard inerte)"


def test_t5_estado_existe_no_controller():
    assert hasattr(N, '__init__') and hasattr(N, 'predict_batch')
    import inspect
    src = inspect.getsource(N.__init__)
    assert '_pguard_state' in src, "init não cria o estado do progress-guard"
    src2 = inspect.getsource(N.predict_batch)
    assert 'pguard_state' in src2 and 'no_prog' in src2, "loop sem o guard"


def test_t6_nit_n1_guard_flag_default_off_isola_bloco():
    """SANIDADE-0 NIT N1: o guard REPROVADO fica atrás de --pguard DEFAULT OFF.

    (a) assinatura do __init__ tem pguard=False; (b) o bloco do guard em
    predict_batch está condicionado a self.PGUARD_ENABLED; (c) o instrumento
    --pguard do race_diagnostic é store_true (default off)."""
    import inspect
    sig = inspect.signature(N.__init__)
    assert 'pguard' in sig.parameters, "flag pguard ausente no __init__"
    assert sig.parameters['pguard'].default is False, "default != False"
    src = inspect.getsource(N.predict_batch)
    assert 'if self.PGUARD_ENABLED:' in src, \
        "bloco do guard não condicionado à flag (NIT N1)"
    # o guard só pode tocar g DEPOIS do gate da flag
    gi = src.index('if self.PGUARD_ENABLED:')
    assert src.index("g = gate_value(") < gi, "gate nominal deve vir antes do bloco"
    rd = Path(__file__).resolve().parent.parent / 'model_train' / 'race_diagnostic.py'
    rsrc = rd.read_text()
    assert "add_argument('--pguard', action='store_true'" in rsrc, \
        "race_diagnostic sem --pguard store_true"
    assert 'pguard={args.pguard}' in rsrc, "identidade do log sem pguard"
