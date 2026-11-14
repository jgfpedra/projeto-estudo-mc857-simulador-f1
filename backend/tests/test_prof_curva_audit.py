"""PROF-CURVA-1 Task 2 — testes sintéticos do auditor de telemetria solo."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.experiments.controller.prof_curva_audit import (  # noqa: E402
    HISTORICAL_BASELINE_LAP_S,
    RHYTHM_GUARD_MAX_DEGRADATION_PCT,
    parse_log_lap_times,
    render_markdown,
)


def test_parse_log_lap_times_extracts_correct_values(tmp_path: Path):
    log_file = tmp_path / "sample.log"
    log_file.write_text(
        "===== GATE ALL-PROFESSOR (v14) =====\n"
        "carros com >=1 volta: 1/1\n"
        "  VER: 4 voltas | tempos=[138.7, 130.5, 127.5, 129.8]\n"
        "contatos carro-carro: 0\n"
    )
    times = parse_log_lap_times(log_file)
    assert times == [138.7, 130.5, 127.5, 129.8]


def test_parse_log_lap_times_handles_missing_and_empty(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.log"
    assert parse_log_lap_times(non_existent) == []

    empty_log = tmp_path / "empty.log"
    empty_log.write_text("nenhum tempo de volta registrado\n")
    assert parse_log_lap_times(empty_log) == []


def test_render_markdown_contains_required_sections():
    fake_audit = {
        "instrument": "prof_curva_audit_v1",
        "csv_path": "fake.csv",
        "csv_sha256": "1234567890abcdef",
        "track": "interlagos",
        "track_sha256": "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
        "total_ticks": 3000,
        "off_ticks": 737,
        "off_pct": 24.6,
        "n_events": 20,
        "dur_median_s": 7.1,
        "lat_max_m": 39.7,
        "laps_count": 4,
        "lap_times": [138.7, 130.5, 127.5, 129.8],
        "lap_time_median_all_s": 130.2,
        "lap_time_median_later_s": 129.8,
        "best_lap_s": 127.5,
        "baseline_lap_s": HISTORICAL_BASELINE_LAP_S,
        "rhythm_guard_ceiling_s": 123.05,
        "degradation_pct": 21.31,
        "rhythm_guard_pass": False,
        "critical_corners": {
            "C01": {"saidas": 4, "taxa_por_volta": 1.0},
            "C06": {"saidas": 4, "taxa_por_volta": 1.0},
            "C07": {"saidas": 4, "taxa_por_volta": 1.0},
            "C08": {"saidas": 4, "taxa_por_volta": 1.0},
            "Reta": {"saidas": 4, "taxa_por_volta": 1.0},
        },
        "corner_counts": {"C01": 4, "C06": 4, "C07": 4, "C08": 4, "Reta": 4},
        "events": [],
    }
    md = render_markdown(fake_audit)
    assert "# Relatório de Referência Solo" in md
    assert "Descida do Lago (T4/T5)" in md
    assert "Junção (T12)" in md
    assert "Guarda de Ritmo" in md
    assert "123.05" in md
