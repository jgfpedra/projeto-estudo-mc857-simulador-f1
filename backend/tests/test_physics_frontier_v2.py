"""PROF-CURVA-1 Task 2 — contrato da calibração física v2."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from scripts.benchmarks.physics_frontier_v2 import (
    INSTRUMENT_VERSION,
    calibrate,
    classify_old,
    classify_stable,
    fit_circle,
    frontier,
    write_exclusive,
)

ARCHIVE_SOURCE_SHA256 = (
    "232e2a81282f4f9c8becf768f34a9d095b3242e253951c2ee167489e9c77189a"
)


@pytest.fixture(scope="module")
def minimal_payload():
    return calibrate(speeds=[4.0], radii=[20.0], grips=[(0.788, "real")])


def test_fit_circle_and_both_classification_contracts():
    cx, cy, radius = fit_circle([4.0, 0.0, -4.0], [0.0, 4.0, 0.0])
    assert cx == pytest.approx(0.0)
    assert cy == pytest.approx(0.0)
    assert radius == pytest.approx(4.0)

    assert classify_old({"R_ratio": 1.10, "misalign_deg": 4.99}) == "LIMPO"
    assert classify_old({"R_ratio": 1.10, "misalign_deg": 5.0}) == "MARGINAL"
    assert classify_stable({"lat_proxy": 0.5, "misalign_deg": 11.99}) == "ESTAVEL"
    assert classify_stable({"lat_proxy": 0.5, "misalign_deg": 12.0}) == "QUEBRA"


def test_minimal_real_grid_is_deterministic():
    kwargs = dict(speeds=[4.0], radii=[20.0, 40.0], grips=[(0.788, "real")])
    first = calibrate(**kwargs)
    second = calibrate(**kwargs)
    assert first == second
    assert len(first["measurements"]) == 2
    assert first["protocol"]["speeds_mps"] == [4.0]
    assert first["protocol"]["radii_m"] == [20.0, 40.0]
    assert first["protocol"]["grips"] == [{"value": 0.788, "label": "real"}]
    assert first["metrics_sha256"]


def test_output_refuses_model_train_and_overwrite(tmp_path: Path):
    payload = {"metrics_sha256": "synthetic"}
    with pytest.raises(ValueError, match="model_train"):
        write_exclusive(Path("model_train/physics_frontier_v2.json"), payload)

    output = tmp_path / "physics_frontier_v2.json"
    # tmp_path is intentionally outside backend/experiments; the refusal is
    # the same guard that prevents accidental writes to arbitrary locations.
    with pytest.raises(ValueError, match="experiments"):
        write_exclusive(output, payload)


def test_steer_saturation_flagged():
    # (25, 7): steer necessário atan(3.4/7)=0.452 rad > limite 0.393 rad a
    # 25 m/s -> saturado; (25, 10): abaixo do limite -> não saturado.
    payload = calibrate(speeds=[25.0], radii=[7.0, 10.0], grips=[(0.788, "real")])
    by_radius = {m["R_target"]: m for m in payload["measurements"]}
    assert by_radius[7.0]["steer_capped"] is True
    assert by_radius[10.0]["steer_capped"] is False


def test_schema_and_required_fields(minimal_payload):
    p = minimal_payload
    assert p["schema_version"] == "prof-curva-physics-frontier-v2"
    assert p["protocol"]["instrument_version"] == INSTRUMENT_VERSION
    assert p["protocol"]["source_sha256"] == ARCHIVE_SOURCE_SHA256
    assert p["protocol"]["source_script"].endswith("physics_radius_calibration.py")
    assert p["protocol"]["speeds_mps"] == [4.0]
    assert p["protocol"]["radii_m"] == [20.0]
    assert p["protocol"]["grips"] == [{"value": 0.788, "label": "real"}]
    assert p["protocol"]["criteria"]["stable"]["lat_proxy_m_max"] == 0.5
    required = {
        "R_eff", "R_ratio", "R_target", "classe_antiga", "classe_estavel",
        "grip", "lat_proxy", "misalign_deg", "steer_capped", "v_target",
    }
    assert required.issubset(set(p["measurements"][0].keys()))
    assert p["frontier_stable"]["real"]["4.0"] is not None
    assert len(p["metrics_sha256"]) == 64


def test_all_values_finite(minimal_payload):
    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                yield from walk(value)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            yield node

    values = list(walk(minimal_payload))
    assert values
    assert all(math.isfinite(float(value)) for value in values)


def test_frontier_monotonicity_synthetic():
    rows = []
    for speed, stable_r, quebra_r in [(4.0, 8.0, 4.0), (8.0, 12.0, 6.0),
                                      (16.0, 16.0, 8.0)]:
        for radius, classe in ((stable_r, True), (quebra_r, False)):
            rows.append({
                "grip": 0.788, "v_target": speed, "R_target": radius,
                "classe_antiga": "LIMPO" if classe else "QUEBRA",
                "classe_estavel": "ESTAVEL" if classe else "QUEBRA",
                "R_ratio": 1.0, "misalign_deg": 0.0, "lat_proxy": 0.1,
                "steer_capped": False, "R_eff": radius,
            })
    for criterion in ("classe_estavel", "classe_antiga"):
        grid = frontier(rows, criterion)
        # as chaves seguem str(speed) dos SPEEDS globais do módulo (ints)
        radii_seq = [grid["real"][key] for key in ("4", "8", "16")]
        assert radii_seq == [8.0, 12.0, 16.0]
        assert all(b >= a for a, b in zip(radii_seq, radii_seq[1:]))


def test_empty_stable_grade_fails_explicitly():
    # (25, 4) é filtrada ANTES de qualquer sim (steer_needed > 1,3x limite):
    # a grade não produz medição nenhuma -> nenhum raio estável -> falha loud.
    with pytest.raises(ValueError, match="nenhum raio estável"):
        calibrate(speeds=[25.0], radii=[4.0], grips=[(0.788, "real")])
