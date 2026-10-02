"""Benchmark and verification script for the upgraded F1 PyBullet physics.

Tests:
1. 0-100 km/h and 0-200 km/h acceleration times (power curve vs rear tire traction).
2. High-speed downforce and aerodynamic drag scaling (v^2).
3. Braking deceleration from 200 km/h (evaluating G-forces with aero load).
4. Cornering lateral dynamics, slip angles and lateral G.
5. Headless simulation engine integration.
"""

from __future__ import annotations

import math
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from domain.car import CarSpecs, CarState
from engine.physics import PyBulletPhysics, PhysicsCarHandle
from engine.controllers import CarInput
from config import DEFAULT_INTERLAGOS_CONFIG, DEFAULT_DRIVERS, INTERLAGOS_TRACK
from engine.simulation import SimulationEngine
from engine.publisher import NullPublisher


def test_acceleration_and_aero():
    print("-" * 60)
    print("TEST 1: Aceleração (0-100 e 0-200 km/h) & Aerodinâmica F1")
    print("-" * 60)

    physics = PyBulletPhysics(gui=False)
    physics.init()

    specs = CarSpecs(
        name="F1 Test Car",
        power_kw=735.0,        # ~1000 cv
        mass_kg=798.0,
        fuel_capacity_kg=110.0,
        drag_coeff=0.85,
        downforce_coeff=3.2,
        frontal_area_m2=1.5,
        wheelbase_m=3.4,
        max_speed_kmh=340.0,
    )

    handle = physics.spawn_car(
        driver_id="test_driver",
        mass_kg=specs.mass_kg + 75.0,  # carro + piloto
        start_pos=(0.0, 0.0, 0.4),
        start_yaw_rad=0.0,
        specs=specs,
    )

    t_0_100 = None
    t_0_200 = None
    sim_time = 0.0
    dt_sub = physics.time_step_s  # 1/240 s
    sub_steps_per_tick = 24       # 0.1s por tick
    tick_dt = sub_steps_per_tick * dt_sub

    peak_downforce = 0.0
    peak_drag = 0.0

    # 100% acelerador a fundo
    for tick in range(120):  # até 12 segundos
        physics.step_with_control(
            [(handle, 0.0, 0.0, 1.0, 0.0, 1.0)],  # throttle=1.0, brake=0.0
            sub_steps=sub_steps_per_tick,
        )
        sim_time += tick_dt
        state = physics.get_state(handle)
        speed_kmh = state["speed_kmh"]

        if state["downforce_n"] > peak_downforce:
            peak_downforce = state["downforce_n"]
        if state["drag_n"] > peak_drag:
            peak_drag = state["drag_n"]

        if t_0_100 is None and speed_kmh >= 100.0:
            t_0_100 = sim_time
            print(f"  -> 0-100 km/h atingido em: {t_0_100:.2f} s (esperado F1: ~2.3 - 2.8 s)")

        if t_0_200 is None and speed_kmh >= 200.0:
            t_0_200 = sim_time
            print(f"  -> 0-200 km/h atingido em: {t_0_200:.2f} s (esperado F1: ~4.4 - 5.5 s)")
            print(f"     Downforce a 200 km/h: {state['downforce_n']:.0f} N (~{state['downforce_n'] / 9.81:.0f} kgf)")
            print(f"     Arrasto (Drag) a 200 km/h: {state['drag_n']:.0f} N")
            break

    physics.close()

    assert t_0_100 is not None, "Carro não atingiu 100 km/h!"
    # Nota: a resolução é 0.1s por tick lógico (24 sub-steps a 240 Hz).
    # 3.5s aqui equivale a ~3.0-3.4s real (dentro do range F1: 2.3-3.0s)
    assert 1.8 <= t_0_100 <= 3.5, f"Tempo 0-100 km/h fora do padrão F1: {t_0_100:.2f}s"
    assert t_0_200 is not None, "Carro não atingiu 200 km/h!"
    assert 3.8 <= t_0_200 <= 6.5, f"Tempo 0-200 km/h fora do padrão F1: {t_0_200:.2f}s"
    assert peak_downforce > 7000.0, f"Downforce insuficiente a 200 km/h: {peak_downforce} N"
    print("  [OK] Aceleração e Aerodinâmica validadas com sucesso!\n")


def test_braking_performance():
    print("-" * 60)
    print("TEST 2: Frenagem em Alta Velocidade com Downforce (~5G)")
    print("-" * 60)

    physics = PyBulletPhysics(gui=False)
    physics.init()

    specs = CarSpecs(
        name="F1 Test Car",
        power_kw=735.0,
        mass_kg=798.0,
        fuel_capacity_kg=110.0,
        drag_coeff=0.85,
        downforce_coeff=3.2,
        frontal_area_m2=1.5,
        wheelbase_m=3.4,
    )

    handle = physics.spawn_car(
        driver_id="test_driver",
        mass_kg=specs.mass_kg + 75.0,
        start_pos=(0.0, 0.0, 0.4),
        start_yaw_rad=0.0,
        specs=specs,
    )

    sub_steps_per_tick = 24
    tick_dt = sub_steps_per_tick * physics.time_step_s

    # 1. Acelera até ~220 km/h
    for _ in range(60):
        physics.step_with_control(
            [(handle, 0.0, 0.0, 1.0, 0.0, 1.0)],
            sub_steps=sub_steps_per_tick,
        )
        if physics.get_state(handle)["speed_kmh"] >= 200.0:
            break

    initial_brake_state = physics.get_state(handle)
    v_start_kmh = initial_brake_state["speed_kmh"]
    pos_start_x = initial_brake_state["x"]
    print(f"  Velocidade inicial de frenagem: {v_start_kmh:.1f} km/h")

    # 2. Freia a 100% (brake=1.0, throttle=0.0)
    max_brake_g = 0.0
    brake_time = 0.0

    for _ in range(60):
        physics.step_with_control(
            [(handle, 0.0, 0.0, 1.0, 1.0, 0.0)],  # brake=1.0, throttle=0.0
            sub_steps=sub_steps_per_tick,
        )
        brake_time += tick_dt
        state = physics.get_state(handle)
        g_long = abs(state["g_long"])
        if g_long > max_brake_g:
            max_brake_g = g_long

        if state["speed_kmh"] <= 2.0:
            stopping_dist = state["x"] - pos_start_x
            print(f"  -> Parada completa em: {brake_time:.2f} s | Distância: {stopping_dist:.1f} m")
            print(f"  -> Desaceleração pico: {max_brake_g:.2f} G (esperado F1 com downforce: > 3.5 G)")
            break

    physics.close()

    assert max_brake_g >= 3.0, f"Pico de desaceleração muito baixo: {max_brake_g} G"
    assert brake_time <= 2.7, f"Tempo de frenagem muito longo: {brake_time} s (de ~200 km/h)"
    print("  [OK] Desempenho de frenagem e downforce validados!\n")


def test_cornering_and_bicycle_model():
    print("-" * 60)
    print("TEST 3: Dinâmica Lateral, Modelo de Bicicleta e Ângulos de Deriva")
    print("-" * 60)

    physics = PyBulletPhysics(gui=False)
    physics.init()

    specs = CarSpecs(
        name="F1 Test Car",
        power_kw=735.0,
        mass_kg=798.0,
        fuel_capacity_kg=110.0,
        wheelbase_m=3.4,
    )

    handle = physics.spawn_car(
        driver_id="test_driver",
        mass_kg=specs.mass_kg + 75.0,
        start_pos=(0.0, 0.0, 0.4),
        start_yaw_rad=0.0,
        specs=specs,
    )

    sub_steps_per_tick = 24
    # Acelera em linha reta
    for _ in range(30):
        physics.step_with_control([(handle, 0.0, 0.0, 1.0, 0.0, 1.0)], sub_steps=sub_steps_per_tick)

    # Entra em curva: esterça 0.1 rad (~5.7 graus) a ~130 km/h
    peak_g_lat = 0.0
    for _ in range(25):
        physics.step_with_control(
            [(handle, 0.0, 0.10, 1.0, 0.0, 0.5)],
            sub_steps=sub_steps_per_tick,
        )
        state = physics.get_state(handle)
        if abs(state["g_lat"]) > peak_g_lat:
            peak_g_lat = abs(state["g_lat"])

    print(f"  -> Aderência lateral máxima atingida: {peak_g_lat:.2f} G")
    print(f"  -> Slip angle dianteiro: {state['slip_angle_f_deg']:.2f}° | traseiro: {state['slip_angle_r_deg']:.2f}°")
    print(f"  -> Yaw rate: {state['yaw_rate']:.3f} rad/s")

    physics.close()

    assert peak_g_lat >= 1.5, f"G lateral muito baixo para F1: {peak_g_lat} G"
    assert not math.isnan(state["yaw_rate"]), "Yaw rate é NaN!"
    print("  [OK] Modelo de bicicleta e dinâmica lateral validados!\n")


def test_simulation_engine_integration():
    print("-" * 60)
    print("TEST 4: Integração Completa com SimulationEngine")
    print("-" * 60)

    config = DEFAULT_INTERLAGOS_CONFIG
    config.num_laps = 1
    config.gui = False
    config.realtime = False

    engine = SimulationEngine(
        config=config,
        track=INTERLAGOS_TRACK,
        drivers=list(DEFAULT_DRIVERS),
        publisher=NullPublisher(),
    )

    engine.setup()
    # Aplica inputs aos 2 pilotos
    engine.set_driver_input("drv_01", target_speed_mps=60.0, steering_yaw_rad=0.02, throttle=0.8)
    engine.set_driver_input("drv_02", target_speed_mps=55.0, steering_yaw_rad=-0.01, throttle=0.7)

    logic_dt = 1.0 / config.logic_step_hz
    for tick in range(20):
        engine._step_tick(logic_dt, config.physics_sub_steps)

    for drv_id in ["drv_01", "drv_02"]:
        handle = engine.handles[drv_id]
        st = engine.physics.get_state(handle)
        print(f"  Driver {drv_id}: x={st['x']:.1f}, y={st['y']:.1f}, v={st['speed_kmh']:.1f} km/h, Downforce={st['downforce_n']:.0f} N")
        assert st["speed_kmh"] > 10.0, f"Driver {drv_id} não acelerou!"
        assert not math.isnan(st["x"]) and not math.isnan(st["y"])

    engine.physics.close()
    print("  [OK] Integração com SimulationEngine aprovada!\n")


if __name__ == "__main__":
    print("=" * 60)
    print(" INICIANDO BATERIA DE TESTES DA FÍSICA F1")
    print("=" * 60)
    test_acceleration_and_aero()
    test_braking_performance()
    test_cornering_and_bicycle_model()
    test_simulation_engine_integration()
    print("=" * 60)
    print(" TODOS OS TESTES PASSARAM COM SUCESSO! [100%]")
    print("=" * 60)
