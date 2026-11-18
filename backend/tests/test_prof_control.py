"""PROF-CONTROL-1 Task 2 — contrato do mecanismo --prof-control.

Cobre o mandato da Task 2: derivação exata de c_ld (regra §3 do prereg
7fe656ac sobre o LAGO_ANATOMY.json), δ_ff em retas/curvas fechadas,
encurtamento do ld_eff no ápice com preservação em reta, confinamento
estrito de steer_cmd em [-1, 1] e bit-identidade estrita da flag OFF contra
o bloco histórico do ReferenceController (FakeEnv, integração).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from model_train.f1_env import F1MultiContextEnv  # noqa: E402
from model_train.prof_control import (  # noqa: E402
    delta_ff,
    derive_c_ld,
    lookahead_gain_factor,
    steer_command,
)
from model_train.reference_controller import ReferenceController  # noqa: E402
from model_train.velocity_profile import VelocityProfile  # noqa: E402

K_LD, LD_MIN, LD_MAX, WHEELBASE = 0.6, 5.0, 45.0, 3.4


# ---------------------------------------------------------------- derivação
def test_derive_c_ld_matches_pinned_rule():
    rec = derive_c_ld()
    assert rec["segmento"] == 3
    assert rec["s_exit_m"] == pytest.approx(32.819, abs=1e-9)
    assert rec["s_ratio_max_m"] == pytest.approx(21.726, abs=1e-9)
    assert rec["kappa_w_1m"] == pytest.approx(0.041173, abs=1e-9)
    assert rec["v_exit_mps"] == pytest.approx(75.974 / 3.6, abs=5e-4)
    assert rec["ld_alvo_m"] == pytest.approx(32.819 - 21.726, abs=1e-9)
    ld_base_esperado = min(max(K_LD * rec["v_exit_mps"], LD_MIN), LD_MAX)
    assert rec["ld_base_m"] == pytest.approx(ld_base_esperado, abs=1e-9)
    # aplicação da fórmula canônica §3, recalculada no teste
    esperado = (rec["ld_base_m"] / rec["ld_alvo_m"] - 1.0) / rec["kappa_w_1m"]
    assert rec["c_ld"] == pytest.approx(esperado, rel=1e-12)
    assert math.isfinite(rec["c_ld"]) and rec["c_ld"] > 0.0
    assert 3.0 < rec["c_ld"] < 4.0  # sanidade: ~3,4 conforme a anatomia


def test_delta_ff_retas_e_curvas_fechadas():
    assert delta_ff(0.0) == 0.0  # reta: feedforward nulo, comportamento OFF
    esperado_quina = math.atan(WHEELBASE * 0.127)  # Junção: κ_inst ≈ 0.127 1/m
    assert delta_ff(0.127) == pytest.approx(esperado_quina)
    assert delta_ff(-0.127) == pytest.approx(-esperado_quina)  # sinal
    assert abs(delta_ff(0.127)) < math.pi / 2  # confinado geometricamente
    with pytest.raises(ValueError):
        delta_ff(float("nan"))


def test_lookahead_preserva_reta_e_encurta_apice():
    rec = derive_c_ld()
    assert lookahead_gain_factor(0.0, rec["c_ld"]) == 1.0  # reta: ld_eff = ld
    # construção pinada: no ponto de razão máxima da C01, o ld_eff cai
    # EXATAMENTE no ld_alvo (arco até a saída) — o ponto de perseguição
    # permanece dentro do arco
    g = lookahead_gain_factor(rec["kappa_w_1m"], rec["c_ld"])
    assert rec["ld_base_m"] * g == pytest.approx(rec["ld_alvo_m"], abs=1e-9)
    # ápice mais fechado (Junção κ_inst ≈ 0.127) encurta ainda mais
    g_apice = lookahead_gain_factor(0.127, rec["c_ld"])
    assert g_apice < g
    assert rec["ld_base_m"] * g_apice < rec["ld_base_m"] * g


def test_steer_command_confinado_estrito():
    assert steer_command(10.0, 10.0, 0.39) == 1.0
    assert steer_command(-10.0, 0.0, 0.39) == -1.0
    normal = steer_command(0.10, 0.05, 0.39)
    assert normal == pytest.approx(0.15 / 0.39)
    assert -1.0 <= normal <= 1.0
    with pytest.raises(ValueError):
        steer_command(float("nan"), 0.0, 0.39)
    with pytest.raises(ValueError):
        steer_command(0.1, 0.0, 0.0)


# ------------------------------------------------- integração (FakeEnv)
def _polyline_track():
    """Faixa fechada: reta longa + quina de 90° à direita + retorno a 4 m."""
    p1 = np.linspace(np.array([0.0, 0.0]), np.array([120.0, 0.0]), 31)
    p2 = np.linspace(np.array([120.0, -4.0]), np.array([120.0, -60.0]), 15)
    p3 = np.array([[160.0, -60.0], [160.0, -100.0], [0.0, -100.0]])
    wps = np.vstack([p1, p2, p3])
    closed = np.vstack([wps, wps[:1]])
    seg = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    return wps, cum, float(seg.sum())


class FakeEnv:
    """Superfície mínima do env para ReferenceController.action()."""

    class _Engine:
        class _Physics:
            @staticmethod
            def get_state(_handle):
                return FakeEnv.state_snapshot

        def __init__(self):
            self.physics = self._Physics()

    def __init__(self, wps, cum, total, s0, v0):
        self.track = type("Track", (), {})()
        self.track.waypoints = wps
        self._wps = np.asarray(wps, dtype=np.float64)  # usado pós-del track
        self.driver_id = "FAKE"
        self._cum, self._total = cum, total
        self.engine = self._Engine()
        self.engine.handles = {"FAKE": object()}
        x, y, th = self._point_at(s0)
        FakeEnv.state_snapshot = {"x": x, "y": y, "speed_mps": v0,
                                  "heading_rad": th}
        self.state_snapshot = FakeEnv.state_snapshot
        self._limit = F1MultiContextEnv.steer_limit_rad

    def _point_at(self, s):
        s = s % self._total
        j = int(np.searchsorted(self._cum, s, side="right") - 1)
        j = min(max(j, 0), len(self._cum) - 1)
        k = (j + 1) % (len(self._cum))
        span = (self._cum[k] - self._cum[j]) if self._cum[k] > self._cum[j] \
            else (self._total - self._cum[j])
        t = min(max((s - self._cum[j]) / max(span, 1e-12), 0.0), 1.0)
        w = np.vstack([self._wps, self._wps[:1]])
        x = w[j, 0] * (1 - t) + w[k, 0] * t
        y = w[j, 1] * (1 - t) + w[k, 1] * t
        th = math.atan2(w[k, 1] - w[j, 1], w[k, 0] - w[j, 0])
        return float(x), float(y), th

    def _project_on_path(self, x, y):
        # o teste fixa a pose; a projeção devolve o s pré-acordado
        return x, self._s0, 0.0, 0.0

    def steer_limit_rad(self, speed_mps):
        return self._limit(speed_mps)

    def _kappa_signed(self, s):
        return 0.0  # não chamada com use_v_plan (v_plan explícito)

    def fix_pose(self, s0):
        self._s0 = s0
        x, y, th = self._point_at(s0)
        FakeEnv.state_snapshot["x"] = x
        FakeEnv.state_snapshot["y"] = y
        FakeEnv.state_snapshot["heading_rad"] = th


def _historical_steer(env, vp, s0, v0):
    """Réplica EXATA do bloco de direção pré-Task-2 (referência OFF)."""
    ld_probe = float(np.clip(K_LD * v0, LD_MIN, LD_MAX))
    v_for_ld = min(v0, vp.at(s0 + ld_probe))
    ld = float(np.clip(K_LD * v_for_ld, LD_MIN, LD_MAX))
    tx, ty, _ = env._point_at(s0 + ld)
    st = env.state_snapshot
    dx, dy = tx - st["x"], ty - st["y"]
    alpha = math.atan2(dy, dx) - st["heading_rad"]
    alpha = (alpha + math.pi) % (2 * math.pi) - math.pi
    steer_rad = math.atan2(2.0 * WHEELBASE * math.sin(alpha), ld)
    return float(np.clip(steer_rad / env.steer_limit_rad(v0), -1.0, 1.0))


def _make_controllers(s0, v0):
    wps, cum, total = _polyline_track()
    env = FakeEnv(wps, cum, total, s0, v0)
    env.fix_pose(s0)
    vp = VelocityProfile(np.array(wps, dtype=np.float64), grip_mult=0.788,
                         sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    off = ReferenceController(env, velocity_profile=vp, prof_control=False)
    on = ReferenceController(env, velocity_profile=vp, prof_control=True)
    return env, vp, off, on


def test_bit_identidade_off_contra_historico():
    env, vp, off, _on = _make_controllers(s0=60.0, v0=21.0)  # meio da reta
    a_off = off.action(traffic=None)
    a_hist = _historical_steer(env, vp, 60.0, 21.0)
    assert float(a_off[0]) == float(a_hist)  # igualdade EXATA de floats
    # … e também num ponto de quina (caminho OFF inalterado em todo s)
    env.fix_pose(126.0)
    a_off2 = off.action(traffic=None)
    a_hist2 = _historical_steer(env, vp, 126.0, 21.0)
    assert float(a_off2[0]) == float(a_hist2)
    assert -1.0 <= float(a_off2[0]) <= 1.0


def test_on_difere_da_off_na_quina_e_confina():
    env, _vp, off, on = _make_controllers(s0=120.0, v0=21.0)  # vértice da quina
    a_off = off.action(traffic=None)
    a_on = on.action(traffic=None)
    assert float(a_on[0]) != float(a_off[0])  # feedforward engaja na curva
    assert -1.0 <= float(a_on[0]) <= 1.0
    assert -1.0 <= float(a_on[1]) <= 1.0
    # ponto de perseguição do ON adiantado a menos: lookahead encurtado
    assert on._last_pursuit != off._last_pursuit


def test_on_igual_off_em_reta():
    env, _vp, off, on = _make_controllers(s0=60.0, v0=21.0)  # meio da reta
    a_off = off.action(traffic=None)
    a_on = on.action(traffic=None)
    # κ_inst=0 na reta: δ_ff=0 e g=1 → mecanismo transparente até em floats
    assert float(a_on[0]) == float(a_off[0])
    assert float(a_on[1]) == float(a_off[1])


def test_runner_path_com_prebuilt_kappa():
    """Caminho do runner: adapter SEM .track (regressão do Task 3) — o κ
    perfil chega pronto do ProfessorRaceController via prof_control_kappa."""
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    wps, cum, total = _polyline_track()
    env = FakeEnv(wps, cum, total, 120.0, 21.0)
    env.fix_pose(120.0)
    del env.track  # _RaceEnvView não expõe .track
    vp = VelocityProfile(np.array(wps, dtype=np.float64), grip_mult=0.788,
                         sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    kappa = _instantaneous_kappa_profile(np.array(wps, dtype=np.float64),
                                         ds_target=4.0)
    on = ReferenceController(env, velocity_profile=vp, prof_control=True,
                             prof_control_kappa=kappa)
    a = on.action(traffic=None)
    assert -1.0 <= float(a[0]) <= 1.0
    assert -1.0 <= float(a[1]) <= 1.0
    # no vértice da quina o mecanismo engaja (steer difere do OFF puro)
    off = ReferenceController(env, velocity_profile=vp, prof_control=False)
    a_off = off.action(traffic=None)
    assert float(a[0]) != float(a_off[0])
