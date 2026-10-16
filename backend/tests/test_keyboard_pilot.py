"""Testes do KeyboardPilot — controle por teclado da janela GUI (headless)."""

from __future__ import annotations

import math

import pytest

from engine.controllers import CarInput
from engine.keyboard_pilot import (
    KEY_IS_DOWN,
    KEY_WAS_RELEASED,
    KEY_WAS_TRIGGERED,
    KeyboardPilot,
    KeyboardPilotConfig,
)

DT = 0.1  # logic_step_hz padrão = 10 Hz

W, S, A, D, SPACE, R = (ord("w"), ord("s"), ord("a"), ord("d"), ord(" "), ord("r"))
UP, DOWN, LEFT_ARROW, RIGHT_ARROW = 65297, 65298, 65296, 65299

PRESS = KEY_IS_DOWN | KEY_WAS_TRIGGERED


def poll(pilot: KeyboardPilot, key, speed_mps=None, ticks=1, first=PRESS):
    """Roda ``ticks`` polls; primeiro poll com press, demais só IS_DOWN."""
    inp = None
    for i in range(ticks):
        state = first if i == 0 else KEY_IS_DOWN
        inp = pilot.update({key: state}, DT, speed_mps=speed_mps)
    return inp


def idle(pilot: KeyboardPilot, ticks, speed_mps=None):
    inp = None
    for _ in range(ticks):
        inp = pilot.update({}, DT, speed_mps=speed_mps)
    return inp


# ---------------------------------------------------------------------------
# Velocidade
# ---------------------------------------------------------------------------

def test_returns_car_input():
    pilot = KeyboardPilot()
    inp = pilot.update({}, DT)
    assert isinstance(inp, CarInput)


def test_accel_rate_is_continuous_per_tick():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=1)
    poll(pilot, W, ticks=4, first=KEY_IS_DOWN)
    # 5 ticks * 0.1s * 20 m/s² = 10 m/s (antes: +2 m/s por evento de tecla)
    assert pilot.speed_mps == pytest.approx(10.0, abs=1e-9)


def test_accel_caps_at_max_speed():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=1)
    for _ in range(100):
        poll(pilot, W, ticks=1, first=KEY_IS_DOWN)
    assert pilot.speed_mps == 80.0


def test_decel_rate_is_continuous_per_tick():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=20)  # 40 m/s
    assert pilot.speed_mps == pytest.approx(40.0, abs=1e-9)
    poll(pilot, S, ticks=10)  # -12 m/s² * 1.0s
    assert pilot.speed_mps == pytest.approx(28.0, abs=1e-9)


def test_coast_decays_when_no_keys():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=5)
    before = pilot.speed_mps
    idle(pilot, 20)
    assert pilot.speed_mps < before
    idle(pilot, 300)
    assert pilot.speed_mps == 0.0


def test_space_is_handbrake():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=5)
    pilot.update({W: KEY_WAS_RELEASED}, DT)  # solta o acelerador
    inp = poll(pilot, SPACE)
    assert inp.target_speed_mps == 0.0
    assert inp.brake == 1.0
    pilot.update({SPACE: KEY_WAS_RELEASED}, DT)
    assert pilot.brake == 0.0
    assert pilot.speed_mps == 0.0


def test_reset_zeroes_everything():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=5)
    poll(pilot, A, ticks=5)
    assert pilot.speed_mps > 0 and abs(pilot.steer_rad) > 0
    pilot.update({A: KEY_WAS_RELEASED}, DT)  # solta o volante
    inp = poll(pilot, R)
    assert inp.target_speed_mps == 0.0
    assert inp.steering_yaw_rad == 0.0
    assert inp.brake == 0.0


def test_dt_is_clamped():
    pilot = KeyboardPilot()
    pilot.update({W: PRESS}, dt=10.0)
    assert pilot.speed_mps == pytest.approx(20.0 * 0.25, abs=1e-9)


# ---------------------------------------------------------------------------
# Steering
# ---------------------------------------------------------------------------

def test_left_key_gives_positive_steering():
    """Convenção: positivo = esquerda (igual ao docstring de CarInput)."""
    pilot = KeyboardPilot()
    inp = poll(pilot, A)
    assert inp.steering_yaw_rad > 0.0


def test_right_key_gives_negative_steering():
    pilot = KeyboardPilot()
    inp = poll(pilot, D)
    assert inp.steering_yaw_rad < 0.0


def test_steering_moves_at_configured_rate():
    pilot = KeyboardPilot()
    poll(pilot, A, ticks=3)
    expected = math.radians(50.0) * 3 * DT
    assert pilot.steer_rad == pytest.approx(expected, abs=1e-9)


def test_steering_clamps_at_full_lock_low_speed():
    pilot = KeyboardPilot()
    poll(pilot, A, ticks=60, speed_mps=10.0)
    assert pilot.steer_rad == pytest.approx(math.radians(25.0), abs=1e-9)


def test_steering_lock_shrinks_at_high_speed():
    pilot = KeyboardPilot()
    poll(pilot, A, ticks=60, speed_mps=80.0)
    # 25° * min_steer_frac(0.40) = 10° em 80 m/s
    assert pilot.steer_rad == pytest.approx(math.radians(10.0), abs=1e-9)


def test_speed_sensitive_lock_uses_real_speed_argument():
    """O limit usa a velocidade real do carro, não só a alvo interna."""
    pilot = KeyboardPilot()
    pilot.speed_mps = 0.0  # alvo interna zerada
    poll(pilot, A, ticks=60, speed_mps=80.0)
    assert pilot.steer_rad == pytest.approx(math.radians(10.0), abs=1e-9)


def test_auto_centers_when_keys_released():
    pilot = KeyboardPilot()
    poll(pilot, A, ticks=3)
    assert pilot.steer_rad > 0
    idle(pilot, 80)
    assert pilot.steer_rad == 0.0


def test_auto_center_rate():
    pilot = KeyboardPilot()
    poll(pilot, A, ticks=3)  # 15°
    pilot.update({A: KEY_WAS_RELEASED}, DT)  # solta e centraliza 7° neste tick
    assert pilot.steer_rad == pytest.approx(math.radians(8.0), abs=1e-9)
    pilot.update({}, DT)
    assert pilot.steer_rad == pytest.approx(math.radians(1.0), abs=1e-9)
    pilot.update({}, DT)
    assert pilot.steer_rad == 0.0


# ---------------------------------------------------------------------------
# Semântica de eventos
# ---------------------------------------------------------------------------

def test_release_event_stops_acceleration():
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=3)
    before = pilot.speed_mps
    pilot.update({W: KEY_WAS_RELEASED}, DT)
    assert W not in pilot.held_keys
    assert pilot.speed_mps < before  # caiu pelo coast, não acelerou


def test_key_missing_for_polls_is_released():
    """Tecla ausente por N polls seguidos = solta (protege contra release perdido)."""
    pilot = KeyboardPilot()
    poll(pilot, W, ticks=1)
    # 3 polls ausentes ainda conta como mantida...
    idle(pilot, 3)
    assert W in pilot.held_keys
    # 4º poll ausente solta
    idle(pilot, 1)
    assert W not in pilot.held_keys


def test_arrow_keys_map_to_actions():
    pilot = KeyboardPilot()
    inp = pilot.update({UP: PRESS}, DT)
    assert inp.target_speed_mps > 0.0

    pilot2 = KeyboardPilot()
    inp2 = pilot2.update({LEFT_ARROW: PRESS}, DT)
    assert inp2.steering_yaw_rad > 0.0

    pilot3 = KeyboardPilot()
    poll(pilot3, W, ticks=10)  # 20 m/s
    pilot3.update({DOWN: PRESS}, DT)
    assert pilot3.speed_mps < 20.0  # seta baixo reduz, não acelera


def test_uppercase_letters_work():
    pilot = KeyboardPilot()
    inp = pilot.update({ord("W"): PRESS}, DT)
    assert inp.target_speed_mps > 0.0


def test_unknown_keys_ignored():
    pilot = KeyboardPilot()
    inp = pilot.update({ord("z"): PRESS}, DT)
    assert inp.target_speed_mps == 0.0
    assert inp.steering_yaw_rad == 0.0


def test_config_is_tunable():
    cfg = KeyboardPilotConfig(max_speed_mps=50.0, accel_rate_mps2=10.0)
    pilot = KeyboardPilot(cfg)
    for _ in range(100):
        pilot.update({W: KEY_IS_DOWN}, DT)
    assert pilot.speed_mps == 50.0
