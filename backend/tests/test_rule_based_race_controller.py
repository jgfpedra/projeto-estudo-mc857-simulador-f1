"""Testes para o RuleBasedRaceController (controlador autônomo baseado em regras)."""

from __future__ import annotations

import math
import numpy as np
import pytest

from backend.domain import CarSpecs, Driver, WeatherKind, WeatherModel, BASE_CONDITIONS
from backend.model_train.f1_env import resolve_track
from backend.engine import SimulationConfig, SimulationEngine, RuleBasedRaceController
from backend.scripts.run_race_10_cars import place_grid


def test_rule_based_race_controller_init():
    track = resolve_track("interlagos")
    ctrl = RuleBasedRaceController(track, seed=42)
    assert len(ctrl._points) == len(track.waypoints)
    assert hasattr(ctrl, "_signed_curvature")
    assert len(ctrl._signed_curvature) == len(track.waypoints)
    assert ctrl.SPEED_PLAN_STEP_M <= 3.5


def test_interlagos_racing_line_opens_before_closed_turn():
    ctrl = RuleBasedRaceController(resolve_track("interlagos"), seed=42)

    # Entrada externa, aproximação do ápice e abertura na saída em cada curva.
    assert ctrl._line_offset_at(1890.0) > 1.0
    assert ctrl._line_offset_at(1930.0) < -2.0
    assert ctrl._line_offset_at(1960.0) > 1.0
    assert ctrl._line_offset_at(2280.0) > 1.0
    assert ctrl._line_offset_at(2310.0) < 0.0
    assert ctrl._line_offset_at(2340.0) > 1.0
    for start, end in ((1800, 2051), (2200, 2421)):
        max_offset = max(abs(ctrl._line_offset_at(float(s))) for s in range(start, end))
        assert max_offset < ctrl._half_width - 1.0
        for s in range(start, end, 2):
            x, y = ctrl._point_at(float(s))
            _, lateral = ctrl._project(f"line-{start}", x, y)
            assert abs(lateral) < ctrl._half_width - 1.0


@pytest.mark.parametrize("change", ["width", "geometry"])
def test_interlagos_racing_line_requires_matching_track(change):
    track = resolve_track("interlagos")
    if change == "width":
        track.width_m += 1.0
    else:
        x, y = track.waypoints[0]
        track.waypoints[0] = (x + 0.1, y)
    ctrl = RuleBasedRaceController(track, seed=42)

    assert abs(ctrl._line_offset_at(2280.0)) < 1.0
    assert ctrl._hairpin_speed_cap_mps == ctrl.HAIRPIN_SPEED_CAP_MPS


def test_rule_based_race_controller_closed_turn_planning():
    track = resolve_track("interlagos")
    ctrl = RuleBasedRaceController(track, seed=42)
    
    # Curva fechada da geometria congelada próxima a s = 2309 m.
    s_curve = 2309.5
    top_speed = 330.0 / 3.6
    mu = 1.8 * 0.84
    q = 0.00368
    
    # O alvo do hairpin foi elevado com margem, sem exceder 7,2 m/s.
    v_apex = ctrl._planned_speed(s_curve, top_speed, mu, q, 22.0, 10.0)
    assert 7.0 < v_apex <= 7.2
    
    # 60 m antes da curva, o plano já deve exigir desaceleração forte.
    v_approach = ctrl._planned_speed(s_curve - 60.0, top_speed, mu, q, 22.0, 70.0)
    assert v_approach < 50.0  # deve exigir menos de 180 km/h


def test_rule_based_race_controller_braking_commands():
    track = resolve_track("interlagos")
    ctrl = RuleBasedRaceController(track, seed=42)
    
    specs = CarSpecs("Red Bull", 750, 798, 110)
    driver = Driver("VER", "Max Verstappen", specs)
    state = driver.initial_state()
    
    # Quando a velocidade atual é muito maior que o alvo, o freio deve ser 1.0 (pleno)
    th, brk = ctrl._longitudinal_commands(
        state, speed=70.0, target_speed=50.0, effective_grip=1.0,
        effective_mu=1.8, downforce_per_speed_sq=0.00368, braking_accel=22.0
    )
    assert th == 0.0
    assert brk == 1.0
    
    # Quando o carro já está no alvo, freio é 0 e acelerador suave
    th_eq, brk_eq = ctrl._longitudinal_commands(
        state, speed=30.0, target_speed=30.0, effective_grip=1.0,
        effective_mu=1.8, downforce_per_speed_sq=0.00368, braking_accel=22.0
    )
    assert brk_eq == 0.0


def test_rule_based_race_controller_clean_lap_interlagos():
    track = resolve_track("interlagos")
    specs = CarSpecs("Red Bull", 750, 798, 110)
    driver = Driver("VER", "Max Verstappen", specs)
    cfg = SimulationConfig(
        num_laps=1, logic_step_hz=10.0, physics_sub_steps=24, gui=False, random_seed=42
    )
    wm = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY])
    engine = SimulationEngine(config=cfg, track=track, drivers=[driver], weather_model=wm)
    ctrl = RuleBasedRaceController(track, seed=42)
    engine.setup()
    place_grid(engine, track, [driver])
    engine.set_controller("VER", ctrl)
    engine.race_started = True

    dt = 0.1
    off_track_count = 0
    max_lat = 0.0
    corner_speeds_kmh = []
    earlier_corner_speeds_kmh = []

    for _ in range(1600):
        engine._step_tick(dt, cfg.physics_sub_steps)
        pos = engine.physics.get_state(engine.handles["VER"])
        s, lat = ctrl._project("VER", pos["x"], pos["y"])
        if 2280.0 <= s <= 2335.0:
            corner_speeds_kmh.append(pos["speed_kmh"])
        if 1888.0 <= s <= 1964.0:
            earlier_corner_speeds_kmh.append(pos["speed_kmh"])
        if abs(lat) > max_lat:
            max_lat = abs(lat)
        if abs(lat) > ctrl._half_width - 0.5:
            off_track_count += 1
        if engine.states["VER"].lap >= 1:
            break

    # Volta completa com 0 saídas de pista e mantendo-se dentro do corredor
    assert engine.states["VER"].lap >= 1
    assert off_track_count == 0
    assert max_lat <= ctrl._half_width
    assert corner_speeds_kmh and min(corner_speeds_kmh) > 12.5
    assert earlier_corner_speeds_kmh and min(earlier_corner_speeds_kmh) > 34.0
