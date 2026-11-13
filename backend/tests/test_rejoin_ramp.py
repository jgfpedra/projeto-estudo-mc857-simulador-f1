"""REALISMO-1 C3-B — conformidade da flag --rejoin-ramp.

Testes de camada e parser; nenhum teste executa uma corrida de produto.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.model_train.f1_env import load_track_frozen  # noqa: E402
from backend.scripts.simulation.run_race_10_cars import (  # noqa: E402
    DEFAULT_MAPPINGS_PATH,
    MODEL_DIR,
    NeuralRaceController,
)

BACKEND = Path(__file__).resolve().parent.parent
DIAGNOSTIC = BACKEND / "model_train" / "race_diagnostic.py"
VISUAL = BACKEND / "scripts" / "simulation" / "run_race_10_cars.py"


class _FakeVelocityProfile:
    def __init__(self, value: float):
        self.value = float(value)

    def at(self, _s: float) -> float:
        return self.value


def _build(*, enabled: bool):
    track = load_track_frozen("interlagos", strict=True)
    ctrl = NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH,
        track=track,
        obs_mode="edge",
        rejoin_ramp=enabled,
    )
    if enabled:
        ctrl._v_plan_cap = _FakeVelocityProfile(20.0)
    return ctrl


def _step(ctrl, *, driver="VER", was_off=True, off=False, t=0.0,
          speed=8.0, th=0.4, brk=0.0):
    return ctrl._rejoin_ramp_step(
        driver,
        was_offtrack=was_off,
        offtrack=off,
        s_live=1000.0,
        speed=speed,
        sim_ts=t,
        th=th,
        brk=brk,
    )


def test_flag_off_is_noop_and_does_not_touch_ramp_state():
    ctrl = _build(enabled=False)
    before = (0.4, 0.2)
    assert _step(ctrl, was_off=True, off=False, th=before[0], brk=before[1]) == (
        False, False, before[0], before[1])
    assert ctrl.REJOIN_RAMP_ENABLED is False
    assert ctrl._rejoin_ramp_state == {}
    assert ctrl._rejoin_ramp_activation_count == 0
    assert ctrl._rejoin_ramp_brake_count == 0

    src = inspect.getsource(NeuralRaceController._rejoin_ramp_step)
    assert "if not self.REJOIN_RAMP_ENABLED" in src
    assert "steer" not in src


def test_parser_rejects_ramp_without_vplan_before_setup():
    for script, args in (
        (DIAGNOSTIC, ["--profile", "composite"]),
        (VISUAL, ["--profile", "race", "--no-gui"]),
    ):
        proc = subprocess.run(
            [sys.executable, str(script), *args, "--rejoin-ramp", "--gov", "off"],
            cwd=BACKEND,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert proc.returncode != 0
        assert "--rejoin-ramp requer --gov vplan" in proc.stderr


def test_ramp_formula_exact_at_low_and_high_vplan_limits():
    cap = NeuralRaceController.rejoin_ramp_v_cap
    assert cap(6.0, 0.0) == pytest.approx(4.8)
    assert cap(6.0, 5.0) == pytest.approx(4.8)
    assert cap(20.0, 0.0) == pytest.approx(8.0)
    assert cap(20.0, 2.5) == pytest.approx(12.0)
    assert cap(20.0, 5.0) == pytest.approx(16.0)


def test_window_is_per_driver_episode_and_includes_five_second_boundary():
    ctrl = _build(enabled=True)

    # Sem excursão anterior, a mesma pose não ativa a rampa.
    assert _step(ctrl, driver="VER", was_off=False, off=False)[0] is False
    # Permanecer fora não é a transição de ativação.
    assert _step(ctrl, driver="VER", was_off=True, off=True, t=0.1)[0] is False
    assert ctrl._rejoin_ramp_activation_count == 0

    # Primeira transição off->on inicia o episódio e o relógio.
    active, braked, th, brk = _step(
        ctrl, driver="VER", was_off=True, off=False, t=1.0, speed=8.0)
    assert (active, braked, th, brk) == (True, False, 0.4, 0.0)
    assert ctrl._rejoin_ramp_activation_count == 1

    # O limite de 5,0 s ainda pertence ao episódio.
    assert _step(ctrl, driver="VER", was_off=False, off=False,
                 t=6.0, speed=8.0)[0] is True
    # O primeiro tick posterior encerra a janela.
    assert _step(ctrl, driver="VER", was_off=False, off=False,
                 t=6.1, speed=8.0)[0] is False
    assert ctrl._rejoin_ramp_end_reason["VER"] == "deadline"

    # Nova excursão e nova transição criam novo episódio para VER.
    assert _step(ctrl, driver="VER", was_off=False, off=True, t=7.0)[0] is False
    assert _step(ctrl, driver="VER", was_off=True, off=False,
                 t=8.0, speed=8.0)[0] is True
    assert ctrl._rejoin_ramp_activation_count == 2
    # Outro carro não herda o relógio.
    assert _step(ctrl, driver="HAM", was_off=False, off=False, t=8.1)[0] is False


def test_ramp_brakes_with_standard_governor_law_and_preserves_steering():
    ctrl = _build(enabled=True)
    active, braked, th, brk = _step(
        ctrl, was_off=True, off=False, t=0.0, speed=20.0,
        th=0.7, brk=0.1)
    assert active is True and braked is True
    assert th == 0.0
    # v_cap=8; excess_frac=(20-8)/8; clip(1.2, .15, 1)=1.
    assert brk == pytest.approx(1.0)
    assert ctrl._rejoin_ramp_brake_count == 1
    assert ctrl._rejoin_ramp_brake_by_driver["VER"] == 1
    # O helper não recebe steer e, portanto, não pode alterá-lo.
    assert "steer" not in inspect.getsource(
        NeuralRaceController._rejoin_ramp_step)


def test_ramp_requires_vplan_defensively():
    ctrl = _build(enabled=True)
    del ctrl._v_plan_cap
    with pytest.raises(RuntimeError, match="--rejoin-ramp requer --gov vplan"):
        _step(ctrl, was_off=True, off=False)


def test_ramp_isolated_from_other_experimental_flags_and_wired_in_both_runners():
    signature = inspect.signature(NeuralRaceController.__init__)
    assert signature.parameters["rejoin_ramp"].default is False
    assert "rejoin_ramp" in inspect.getsource(NeuralRaceController.__init__)
    assert "--rejoin-ramp" in DIAGNOSTIC.read_text(encoding="utf-8")
    assert "--rejoin-ramp" in VISUAL.read_text(encoding="utf-8")
    src = inspect.getsource(NeuralRaceController.predict_batch)
    assert "_rejoin_ramp_step" in src
    assert "_rejoin_handoff_step" in src
    assert "_gapcheck_state" in src
    assert "_pguard_state" in src
    # A única entrada nova do mecanismo é a flag; as outras flags continuam
    # opt-in e não são consultadas pelo helper de C3-B.
    ramp_src = inspect.getsource(NeuralRaceController._rejoin_ramp_step)
    for forbidden in ("LAUNCH_CAP", "LAUNCH_STEER_MUTE", "PGUARD", "ANTI_GLUE",
                      "REJOIN_GAP", "REJOIN_HANDOFF"):
        assert forbidden not in ramp_src
