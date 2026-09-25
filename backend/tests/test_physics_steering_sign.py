"""Valida a convenção de sinal do steering na física: positivo = esquerda.

Regressão para a inversão A/D: o docstring de ``CarInput`` e o
``scripts/publish_keyboard.py`` definem ``steering_yaw_rad > 0`` como
esquerda; o modelo lateral (bicycle + Pacejka) precisa confirmar isso.
"""

from __future__ import annotations

import math

import pybullet as p
import pytest

from engine.physics import PyBulletPhysics


@pytest.fixture()
def physics():
    phys = PyBulletPhysics(gui=False)
    phys.init()
    phys.create_ground_plane()
    yield phys
    phys.close()


def _drive(phys: PyBulletPhysics, steer_rad: float, seconds: float = 1.0):
    """Anda em linha reta inicial a 25 m/s com steering fixo e devolve o estado."""
    handle = phys.spawn_car(
        driver_id="drv_sign",
        mass_kg=800.0,
        start_pos=(0.0, 0.0, 0.5),
        start_yaw_rad=0.0,
    )
    p.resetBaseVelocity(
        handle.chassis_id, [25.0, 0.0, 0.0], [0.0, 0.0, 0.0],
        physicsClientId=phys._client_id,
    )
    tick_s = phys.time_step_s * 8  # sub_steps padrão de step_with_control
    ticks = max(1, int(seconds / tick_s))
    for _ in range(ticks):
        phys.step_with_control(
            [(handle, 25.0, steer_rad, 1.0, 0.0, None)], sub_steps=8
        )
    return phys.get_state(handle)


def test_positive_steering_turns_left(physics):
    st = _drive(physics, math.radians(10.0))
    assert st["heading_rad"] > 0.02, (
        f"steering positivo deveria virar à esquerda (yaw CCW), heading={st['heading_rad']}"
    )
    assert st["yaw_rate"] > 0.0


def test_negative_steering_turns_right(physics):
    st = _drive(physics, math.radians(-10.0))
    assert st["heading_rad"] < -0.02, (
        f"steering negativo deveria virar à direita (yaw CW), heading={st['heading_rad']}"
    )
    assert st["yaw_rate"] < 0.0
