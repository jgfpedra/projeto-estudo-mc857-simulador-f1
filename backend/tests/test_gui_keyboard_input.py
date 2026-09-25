"""Integração do controle GUI: teclado → KeyboardPilot → InputSource.

Cobre duas propriedades:

1. Enquanto o jogador pilota na janela GUI, o input é re-publicado a cada
   tick (nunca fica "stale" e o fallback não freia o carro sozinho).
2. Com o piloto em repouso a GUI não publica nada, deixando a fonte externa
   (ex.: ``scripts/publish_keyboard.py``) assumir o controle.
"""

from __future__ import annotations

import time

from config import DEFAULT_DRIVERS, INTERLAGOS_TRACK
from engine import EnvironmentState, InMemoryInputSource, SimulationConfig, SimulationEngine
from engine.keyboard_pilot import KEY_IS_DOWN, KEY_WAS_TRIGGERED

PRESS = KEY_IS_DOWN | KEY_WAS_TRIGGERED


def _make_engine() -> SimulationEngine:
    source = InMemoryInputSource(fallback_race_id=f"test_gui_kb_{time.time()}")
    config = SimulationConfig(
        num_laps=1,
        gui=False,  # DIRECT (headless); _poll_gui_keyboard é chamado direto
        input_stale_after_s=1.0,
        input_fallback="brake",
    )
    engine = SimulationEngine(
        config=config,
        track=INTERLAGOS_TRACK,
        drivers=list(DEFAULT_DRIVERS[:1]),
        input_source=source,
    )
    engine.setup()
    return engine


def test_idle_gui_does_not_publish():
    """GUI em repouso não pisa na fonte externa de inputs."""
    engine = _make_engine()
    try:
        drv_id = engine.drivers[0].driver_id
        engine._poll_gui_keyboard(0.1)
        assert engine.input_source.get_last_input(drv_id) is None
    finally:
        engine.teardown()


def test_held_key_publishes_target_speed():
    engine = _make_engine()
    try:
        drv_id = engine.drivers[0].driver_id
        engine.keyboard_pilot.update({ord("w"): PRESS}, 0.1)
        engine._poll_gui_keyboard(0.1)
        entry = engine.input_source.get_last_input(drv_id)
        assert entry is not None
        assert entry.source == "pybullet_gui"
        assert entry.car_input.target_speed_mps > 0.0
    finally:
        engine.teardown()


def test_publishes_every_tick_while_driving():
    """Mantém o input fresco tick a tick enquanto há controle ativo."""
    engine = _make_engine()
    try:
        drv_id = engine.drivers[0].driver_id
        engine.keyboard_pilot.update({ord("w"): PRESS}, 0.1)
        engine._poll_gui_keyboard(0.1)
        first = engine.input_source.get_last_input(drv_id)
        assert first is not None

        engine.keyboard_pilot.update({ord("w"): KEY_IS_DOWN}, 0.1)
        engine._poll_gui_keyboard(0.1)
        second = engine.input_source.get_last_input(drv_id)
        assert second.seq > first.seq
        assert second.car_input.target_speed_mps > first.car_input.target_speed_mps
    finally:
        engine.teardown()


def test_fallback_stale_does_not_brake_while_gui_polls():
    """Após dormir além de stale_after_s, um novo tick do GUI re-assume o
    controle: o input resolvido vem do piloto (brake=0), não do fallback."""
    engine = _make_engine()
    try:
        drv_id = engine.drivers[0].driver_id
        engine.keyboard_pilot.update({ord("w"): PRESS}, 0.1)
        engine._poll_gui_keyboard(0.1)
        time.sleep(1.1)  # maior que input_stale_after_s
        # Novo tick: a tecla ainda conta como mantida (1 poll ausente) e o
        # piloto continua com velocidade-alvo > 0 → publica de novo.
        engine._poll_gui_keyboard(0.1)

        state = engine.states[drv_id]
        env = EnvironmentState(
            sim_ts=engine.sim_ts,
            lap=engine.current_lap,
            weather=engine.weather_model.current,
            track=engine.track,
            all_driver_states=dict(engine.states),
        )
        car_input = engine._resolve_car_input(drv_id, env, state)
        # Fallback "brake" devolveria brake=1.0 (carro parado, speed decai p/ 0);
        # o piloto devolve o estado atual (sem freio fantasma).
        assert car_input.brake == 0.0
        assert car_input.target_speed_mps > 0.0
    finally:
        engine.teardown()
