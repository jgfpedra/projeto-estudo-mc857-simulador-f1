"""PROF-CURVA-1 Task 3 — testes unitários e de bit-identidade do teto local de curvatura."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model_train.prof_curva import (  # noqa: E402
    build_capped_velocity_profile,
    get_v_cap,
    load_physics_frontier,
)
from model_train.velocity_profile import VelocityProfile  # noqa: E402
from scripts import saidas_verdict as SV  # noqa: E402

FRONTIER_JSON = Path("experiments/prof-curva-1/physics_frontier_current.json")


def test_load_physics_frontier_returns_sorted_non_quebra_pairs():
    pairs = load_physics_frontier(FRONTIER_JSON, grip=0.788)
    assert len(pairs) >= 5
    # Garantir ordenação estrita por raio
    radii = [r for r, _ in pairs]
    assert radii == sorted(radii)
    # Raio mínimo medido sem quebra deve ser 10 m a 4 m/s
    assert pairs[0] == (10.0, 4.0)
    # Maior raio empírico medido sem quebra é 40 m a 13 m/s
    assert pairs[-1] == (40.0, 13.0)


def test_load_physics_frontier_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_physics_frontier("caminho_inexistente.json", grip=0.788)


def test_get_v_cap_interpolation_and_extrapolation():
    pairs = [(10.0, 4.0), (16.0, 6.0), (20.0, 8.0), (25.0, 10.0), (40.0, 13.0)]

    # Acima do raio máximo (sem teto artificial)
    assert get_v_cap(50.0, pairs) == 200.0
    assert get_v_cap(100.0, pairs) == 200.0

    # No nó exato
    assert get_v_cap(10.0, pairs) == pytest.approx(4.0)
    assert get_v_cap(20.0, pairs) == pytest.approx(8.0)
    assert get_v_cap(40.0, pairs) == pytest.approx(13.0)

    # Interpolação linear interna
    # R=13m: ponto médio entre (10, 4) e (16, 6) -> 5.0 m/s
    assert get_v_cap(13.0, pairs) == pytest.approx(5.0)

    # Abaixo do raio mínimo (escala sub-linear sqrt(R / R_min))
    # R=7.5m -> 4.0 * sqrt(7.5 / 10.0) ≈ 3.46 m/s
    v_sub = get_v_cap(7.5, pairs)
    assert v_sub < 4.0
    assert v_sub > 3.0


def test_build_capped_velocity_profile_caps_critical_corners_on_interlagos():
    track_file = SV.TRACKS["interlagos"]["file"]
    geom = SV.load_track_geometry(track_file)
    wps = np.array(geom[0], dtype=np.float64)

    vp_uncapped = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    vp_capped = build_capped_velocity_profile(
        wps, frontier_path=FRONTIER_JSON, grip_mult=0.788, sf=0.80, ds_target=4.0, smooth_window_m=20.0
    )

    # O perfil com teto deve ser menor ou igual ao uncapped em toda a pista
    assert np.all(vp_capped.v_plan <= vp_uncapped.v_plan + 1e-6)

    # Na Junção (s≈2310 m): raio de ~11m exigia 11.5 m/s uncapped. Com teto deve ser < 5.0 m/s
    v_juncao_capped = vp_capped.at(2310.0)
    assert v_juncao_capped < 5.0
    assert v_juncao_capped < vp_uncapped.at(2310.0) * 0.5

    # No Mergulho (s≈2043 m): uncapped era 14.5 m/s. Com teto deve ser < 7.0 m/s
    v_mergulho_capped = vp_capped.at(2043.0)
    assert v_mergulho_capped < 7.0
    assert v_mergulho_capped < vp_uncapped.at(2043.0)

    # No Bico de Pato (s≈1931 m): uncapped era 15.3 m/s. Com teto deve ser < 8.0 m/s
    v_bico_capped = vp_capped.at(1931.0)
    assert v_bico_capped < 8.0
    assert v_bico_capped < vp_uncapped.at(1931.0)

    # Na Reta dos Boxes (s≈700 m): ambas devem atingir velocidade alta (> 50 m/s)
    assert vp_capped.at(700.0) > 50.0
    assert vp_capped.at(700.0) == pytest.approx(vp_uncapped.at(700.0), rel=0.05)


def test_bit_identity_when_prof_curva_off():
    """Garante bit-identidade estrita quando a flag --prof-curva está OFF."""
    from model_train.race_diagnostic import ProfessorRaceController

    class FakeTrack:
        name = "interlagos"
        waypoints = SV.load_track_geometry(SV.TRACKS["interlagos"]["file"])[0]
        width_m = 12.0

    track = FakeTrack()

    # Instancia com prof_curva=False (default histórico)
    ctrl_default = ProfessorRaceController(track, sf=0.80, prof_curva=False)

    # Instancia baseline VelocityProfile direto
    vp_baseline = VelocityProfile(
        np.array(track.waypoints, dtype=np.float64),
        grip_mult=0.788,
        sf=0.80,
        ds_target=4.0,
        smooth_window_m=20.0,
    )

    # O v_plan do controller padrão deve ser byte a byte idêntico ao baseline
    assert np.array_equal(ctrl_default._vp.v_plan, vp_baseline.v_plan)

    # Instancia com prof_curva=True e verifica que ativa a diferenciação
    ctrl_on = ProfessorRaceController(
        track,
        sf=0.80,
        prof_curva=True,
        physics_frontier_file=str(FRONTIER_JSON),
    )
    assert not np.array_equal(ctrl_on._vp.v_plan, vp_baseline.v_plan)
    assert np.all(ctrl_on._vp.v_plan <= ctrl_default._vp.v_plan + 1e-6)
