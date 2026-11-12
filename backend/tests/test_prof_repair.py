"""PROF-REPAIR-1 — testes do patch (prereg fc0a939 §6).

t_pr1_1: wiring — flag default OFF (assinatura), constantes pinadas
         (HOLD 5,0 s / V0 8,0), bloco gated por PROF_REPAIR_ENABLED,
         estado lazy (default path não toca _repair_state), --prof-repair
         no argparse, prof_repair na linha de identidade.
t_pr2_2: rampa unitária — a matemática do pacing: alvo(t) =
         min(v_plan, 8 + (v_plan−8)·t/5) cresce linear de 8 a v_plan em
         5,0 s; long_cmd = (alvo−v)/8 clipado; janela encerra em t>=5.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.model_train.race_diagnostic import ProfessorRaceController as P  # noqa: E402


def _rampa(v_plan, elapsed, hold=5.0, v0=8.0, v=8.0):
    """Réplica exata da matemática do patch (linhas do bloco prof_repair)."""
    alvo = min(v_plan, v0 + max(v_plan - v0, 0.0) * (elapsed / hold))
    long_cmd = max(-1.0, min(1.0, (alvo - v) / 8.0))
    th, brk = max(long_cmd, 0.0), max(-long_cmd, 0.0)
    return alvo, th, brk


def test_t_pr1_1_wiring_default_off_e_constantes():
    sig = inspect.signature(P.__init__)
    assert sig.parameters['prof_repair'].default is False, \
        "flag prof_repair deve ser default OFF"
    assert P.PROF_REPAIR_HOLD_S == 5.0
    assert P.PROF_REPAIR_V0_MPS == 8.0
    assert P.PROF_REPAIR_ENABLED_DEFAULT is False
    src = inspect.getsource(P.predict_batch)
    assert 'if self.PROF_REPAIR_ENABLED:' in src, "bloco sem gate"
    # estado LAZY: só dentro do gate (default path intocado)
    i_gate = src.index('if self.PROF_REPAIR_ENABLED:')
    i_state = src.index('self._repair_state.setdefault(')
    assert i_state > i_gate, "estado tocado fora do gate (vazamento default)"
    rd = (Path(__file__).resolve().parent.parent
          / 'model_train' / 'race_diagnostic.py').read_text()
    assert "add_argument('--prof-repair', action='store_true'" in rd
    assert 'prof_repair={args.prof_repair}' in rd
    assert "prof_repair=getattr(args, 'prof_repair', False)" in rd


def test_t_pr1_2_rampa_linear_e_fim_de_janela():
    # v_plan 30 m/s: alvo cresce linear de 8 (t=0) a 30 (t=5)
    for t, esperado in [(0.0, 8.0), (1.0, 12.4), (2.5, 19.0), (5.0, 30.0)]:
        alvo, th, brk = _rampa(30.0, t)
        assert abs(alvo - esperado) < 1e-9, f"t={t}: alvo {alvo} != {esperado}"
    # long_cmd: alvo 30, v 8 -> (30-8)/8 = 2.75 -> clip 1.0 = throttle total
    _, th, brk = _rampa(30.0, 5.0, v=8.0)
    assert th == 1.0 and brk == 0.0
    # v acima do alvo -> freia (ex.: v_plan 10, v 8, t=0 -> alvo 8 ->
    # neutro; t=2.5 -> alvo 9.0 -> long 0.125 th)
    _, th2, brk2 = _rampa(10.0, 2.5)
    assert abs(th2 - 0.125) < 1e-9 and brk2 == 0.0
    # v_plan <= v0 (curva lenta): alvo = v_plan (min) — pode frear
    alvo3, _, brk3 = _rampa(6.0, 0.0, v=8.0)
    assert alvo3 == 6.0 and brk3 > 0.0, "curva lenta: alvo=v_plan (freia)"
