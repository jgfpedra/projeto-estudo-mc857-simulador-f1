"""PROF-CURVA-1 Task 1 — testes sintéticos de fit circular e classificação."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.calibrate_physics_frontier import (  # noqa: E402
    build_frontier,
    classify,
    fit_circle,
)


def test_fit_circle_recovers_known_radius_and_center():
    radius = 13.0
    cx0, cy0 = 4.5, -2.0
    theta = np.linspace(0.0, 2.0 * math.pi, 180, endpoint=False)
    x = cx0 + radius * np.cos(theta)
    y = cy0 + radius * np.sin(theta)
    cx, cy, r = fit_circle(x, y)
    assert r == pytest.approx(radius, abs=1e-6)
    assert cx == pytest.approx(cx0, abs=1e-6)
    assert cy == pytest.approx(cy0, abs=1e-6)


def test_fit_circle_rejects_too_few_points():
    assert fit_circle([0.0, 1.0], [0.0, 1.0]) == (None, None, None)


def test_classify_limpo():
    assert classify({"R_ratio": 1.05, "misalign_deg": 3.0}) == "LIMPO"
    assert classify({"R_ratio": 1.10, "misalign_deg": 4.99}) == "LIMPO"


def test_classify_marginal_not_limpo():
    assert classify({"R_ratio": 1.20, "misalign_deg": 8.0}) == "MARGINAL"
    assert classify({"R_ratio": 1.05, "misalign_deg": 10.0}) == "MARGINAL"


def test_classify_quebra():
    assert classify({"R_ratio": 1.50, "misalign_deg": 2.0}) == "QUEBRA"
    assert classify({"R_ratio": 1.05, "misalign_deg": 20.0}) == "QUEBRA"
    assert classify({"R_ratio": 1.40, "misalign_deg": 16.0}) == "QUEBRA"


def test_build_frontier_takes_smallest_limpo_radius():
    results = [
        {"grip": 0.788, "v_target": 10.0, "R_target": 16.0, "classe": "LIMPO"},
        {"grip": 0.788, "v_target": 10.0, "R_target": 13.0, "classe": "LIMPO"},
        {"grip": 0.788, "v_target": 10.0, "R_target": 8.0, "classe": "QUEBRA"},
        {"grip": 0.842, "v_target": 10.0, "R_target": 10.0, "classe": "MARGINAL"},
    ]
    frontier = build_frontier(results)
    assert frontier["real"]["10"] == 13.0
    assert frontier["soft"]["10"] is None
    assert frontier["real"]["25"] is None
