"""PROF-GRIP-1 Task 2 — contrato do mecanismo --prof-grip.

Cobre o mandato: fórmula exata do fator (piso max(0.1,·) + teto min(1,·) +
reserva sqrt(1/1,10)), janelas canônicas reais, cap do v_target (fora das
janelas = alvo histórico exato; dentro, alvo = v_plan·fator), bit-identidade
OFF (float equality == em steer e long), pacing-only (esterço intocado ON),
monotonicidade no grip e guarda professor-only.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from model_train.f1_env import F1MultiContextEnv  # noqa: E402
from model_train.prof_grip import (  # noqa: E402
    F_RESERVA,
    GRIP_REF,
    cap_v_target,
    corner_windows,
    fator_grip,
    grip_in_window,
    guard_professor_path,
)
from model_train.reference_controller import ReferenceController  # noqa: E402
from model_train.velocity_profile import VelocityProfile  # noqa: E402
from tests.test_prof_control import FakeEnv, _polyline_track  # noqa: E402

K_LD, LD_MIN, LD_MAX, WHEELBASE, MARGIN = 0.6, 5.0, 45.0, 3.4, 0.93


# ------------------------------------------------------------ fórmula
def test_fator_grip_formula_exata():
    assert fator_grip(GRIP_REF) == pytest.approx(F_RESERVA)  # grip=ref: só reserva
    esperado = min(1.0, math.sqrt(0.807 / 0.85)) * F_RESERVA
    assert fator_grip(0.807) == pytest.approx(esperado)      # grip do passe 5
    assert fator_grip(0.842) == pytest.approx(  # passe 1: acima do histórico
        math.sqrt(0.842 / 0.85) * F_RESERVA)
    assert fator_grip(0.95) == pytest.approx(F_RESERVA)      # min(1,·): nunca sobe
    assert fator_grip(0.0) == pytest.approx(                 # piso de finitude
        math.sqrt(0.1 / 0.85) * F_RESERVA)
    assert fator_grip(0.75) < fator_grip(0.80) < fator_grip(0.84)  # monotônico
    assert all(math.isfinite(fator_grip(g)) for g in
               (0.0, 0.1, 0.5, 0.807, 0.842, 0.95))


# ------------------------------------------------- janelas canônicas reais
def test_corner_windows_interlagos_real():
    import json
    track = json.load(open(BACKEND / "model_train" / "tracks_frozen"
                           / "interlagos_v2.json"))
    wps = np.array(track["waypoints"], dtype=np.float64)
    janelas = corner_windows(wps)
    assert set(janelas.keys()) == {"C01", "C06", "C07", "C08"}
    # C08/Junção: valores conhecidos do mapa do PROF-CURVA-1
    assert janelas["C08"][0] == pytest.approx(2276.239, abs=1e-2)
    assert janelas["C08"][1] == pytest.approx(2344.246, abs=1e-2)
    assert all(lo < hi for lo, hi in janelas.values())


# --------------------------------------------------------- cap do v_target
def test_cap_fora_da_janela_e_identidade():
    janelas = {"C01": (0.0, 80.0)}
    assert cap_v_target(30.0, 27.9, 1000.0, 0.79, janelas.values()) == 27.9
    assert grip_in_window(1000.0, janelas.values()) is False


def test_cap_dentro_da_janela_pneu_novo_e_noop():
    # passe 1 (grip 0.842): fator 0.9490 > margin 0.93 → o teto NÃO rebaixa
    # o alvo histórico (a volta limpa permanece limpa — propriedade pinnada)
    janelas = {"C01": (0.0, 80.0)}
    v_plan, v_hist = 30.0, 0.93 * 30.0
    assert cap_v_target(v_plan, v_hist, 40.0, 0.842,
                        janelas.values()) == pytest.approx(v_hist)


def test_cap_dentro_da_janela_pneu_gasto_binda():
    janelas = {"C01": (0.0, 80.0)}
    v_plan, v_hist = 30.0, 0.93 * 30.0
    cap = cap_v_target(v_plan, v_hist, 40.0, 0.79, janelas.values())
    assert cap == pytest.approx(v_plan * fator_grip(0.79))
    assert cap < v_hist                                 # pneu gasto → alvo cai
    # monotonicidade: grip menor → alvo menor ou igual
    seq = [cap_v_target(v_plan, v_hist, 40.0, g, janelas.values())
           for g in (0.842, 0.825, 0.807, 0.79, 0.75)]
    assert all(b <= a for a, b in zip(seq, seq[1:]))
    with pytest.raises(ValueError):
        cap_v_target(float("nan"), v_hist, 40.0, 0.79, janelas.values())


# ------------------------------------------------------------- guarda
def test_guarda_professor_only():
    assert guard_professor_path("professor", False, False) is True
    assert guard_professor_path("mixed", True, True) is True
    assert guard_professor_path("mixed", True, False) is False
    assert guard_professor_path("neural", False, False) is False
    assert guard_professor_path("professor", True, False) is False


# --------------------------------------------- integração (FakeGripEnv)
class FakeGripEnv(FakeEnv):
    """FakeEnv + clima/pneu: superfície que o teto grip-sensível consome."""

    def __init__(self, wps, cum, total, s0, v0, grip):
        super().__init__(wps, cum, total, s0, v0)
        self.engine.weather_model = SimpleNamespace(
            current=SimpleNamespace(kind="DRY", track_temp=30.0))

        class _Tyre:
            def __init__(self, g):
                self._g = g

            def grip_multiplier(self, kind, track_temp):
                return self._g

        self.engine.states = {"FAKE": SimpleNamespace(tyre=_Tyre(grip))}


def _historical_action(env, vp, s0, v0):
    """Réplica EXATA do bloco pré-Task-2 (steer + long), referência OFF."""
    ld_probe = float(np.clip(K_LD * v0, LD_MIN, LD_MAX))
    v_for_ld = min(v0, vp.at(s0 + ld_probe))
    ld = float(np.clip(K_LD * v_for_ld, LD_MIN, LD_MAX))
    tx, ty, _ = env._point_at(s0 + ld)
    st = env.state_snapshot
    dx, dy = tx - st["x"], ty - st["y"]
    alpha = math.atan2(dy, dx) - st["heading_rad"]
    alpha = (alpha + math.pi) % (2 * math.pi) - math.pi
    steer_rad = math.atan2(2.0 * WHEELBASE * math.sin(alpha), ld)
    steer_cmd = float(np.clip(steer_rad / env.steer_limit_rad(v0), -1.0, 1.0))
    v_tgt = vp.at(s0) * MARGIN
    long_cmd = float(np.clip((v_tgt - v0) / 8.0, -1.0, 1.0))
    return np.array([steer_cmd, long_cmd], dtype=np.float32)


def _make_controllers(s0, v0=None, grip=0.79, windows=None):
    """Controladores OFF/ON sobre a faixa sintética; v0 default = v_plan(s0)
    (rolando no alvo — o cap do grip aparece dentro da faixa do long_cmd)."""
    if windows is None:
        windows = {"C01": (0.0, 80.0)}
    wps, cum, total = _polyline_track()
    vp = VelocityProfile(np.array(wps, dtype=np.float64), grip_mult=0.788,
                         sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    if v0 is None:
        v0 = float(vp.at(s0))
    env = FakeGripEnv(wps, cum, total, s0, v0, grip)
    env.fix_pose(s0)
    off = ReferenceController(env, velocity_profile=vp, prof_grip=False)
    on = ReferenceController(env, velocity_profile=vp, prof_grip=True,
                             prof_grip_windows=windows)
    return env, vp, off, on


def test_bit_identidade_off_steer_e_long():
    # janelas restritas a (0,40): s0=60 está FORA → ON e OFF idênticos
    env, vp, off, on = _make_controllers(s0=60.0, grip=0.79,
                                         windows={"C01": (0.0, 40.0)})
    v0 = float(vp.at(60.0))  # o v0 real do estado do fake
    a_off = off.action(traffic=None)
    a_hist = _historical_action(env, vp, 60.0, v0)
    assert float(a_off[0]) == float(a_hist[0])   # steer: igualdade exata
    assert float(a_off[1]) == float(a_hist[1])   # long: igualdade exata
    a_on = on.action(traffic=None)               # fora da janela: ON ≡ OFF
    assert float(a_on[0]) == float(a_hist[0])
    assert float(a_on[1]) == float(a_hist[1])


def test_on_binda_na_janela_com_pneu_gasto():
    # janela (0,80): s0=40 dentro, grip 0.79 → alvo cai → long menor
    env, vp, off, on = _make_controllers(s0=40.0, grip=0.79)
    a_off = off.action(traffic=None)
    a_on = on.action(traffic=None)
    assert float(a_on[0]) == float(a_off[0])     # pacing-only: esterço intocado
    assert float(a_on[1]) < float(a_off[1])      # long menor (alvo capado)
    assert -1.0 <= float(a_on[1]) <= 1.0


def test_on_noop_com_pneu_novo_na_janela():
    # passe 1 (grip 0.842): fator 0.9490 > margin 0.93 → teto não rebaixa:
    # a volta limpa permanece limpa (igualdade exata mesmo dentro da janela)
    env, _vp, off, on = _make_controllers(s0=40.0, grip=0.842)
    a_off = off.action(traffic=None)
    a_on = on.action(traffic=None)
    assert float(a_on[1]) == float(a_off[1])
    assert float(a_on[0]) == float(a_off[0])
