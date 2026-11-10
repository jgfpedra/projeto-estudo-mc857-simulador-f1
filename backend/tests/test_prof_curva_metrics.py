"""PROF-CURVA-1 Task 3 — instrumento report-only de corridas solo."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.prof_curva_metrics import (
    EXPECTED_TOTAL_LINES,
    MetricsIntegrityError,
    analyze_run,
    canonical_json,
    write_exclusive,
)


BACKEND = Path(__file__).resolve().parents[1]
REF_CSV = BACKEND / "experiments/prof-curva-1/REF_INTERLAGOS_600S.csv"
REF_LOG = BACKEND / "experiments/prof-curva-1/REF_INTERLAGOS_600S.log"
MONACO_CSV = BACKEND / "experiments/prof-monaco-1/prof_s0.csv"
MONACO_LOG = BACKEND / "experiments/prof-monaco-1/prof_s0.log"


def _empty_sidecar(path: Path) -> Path:
    path.write_text("sub,drv_a,drv_b,j_n,dv_a,dv_b\n", encoding="utf-8")
    return path


def test_reference_metrics_reuse_canonical_excursion_instrument(tmp_path: Path):
    payload = analyze_run(
        REF_CSV,
        REF_LOG,
        _empty_sidecar(tmp_path / "REF_INTERLAGOS_600S_events.csv"),
        track="interlagos",
        expected_variedade=0,
        mode="off",
    )

    assert payload["integrity"]["total_lines"] == EXPECTED_TOTAL_LINES
    assert payload["sample_rows"] == 3000
    assert payload["off_ticks"] == 737
    assert payload["off_pct"] == pytest.approx(24.567, abs=0.001)
    assert payload["n_events"] == 20
    assert {cid: row["n_events"] for cid, row in payload["by_corner"].items()} == {
        "C01": 4,
        "C06": 4,
        "C07": 4,
        "C08": 4,
        "Reta": 4,
    }
    assert payload["lap_time_crosscheck"]["VER"]["delta_s"]
    assert all(
        abs(delta) <= 0.3
        for delta in payload["lap_time_crosscheck"]["VER"]["delta_s"]
    )
    assert all("authority_start" in event for event in payload["excursions"])
    assert all("max_abs_lat_m" in event for event in payload["excursions"])
    assert payload["metrics_sha256"] == hashlib.sha256(
        canonical_json({
            key: value for key, value in payload.items()
            if key != "metrics_sha256"
        }).encode("utf-8")
    ).hexdigest()


def test_reference_metrics_are_deterministic(tmp_path: Path):
    sidecar = _empty_sidecar(tmp_path / "events.csv")
    first = analyze_run(REF_CSV, REF_LOG, sidecar, expected_variedade=0)
    second = analyze_run(REF_CSV, REF_LOG, sidecar, expected_variedade=0)
    assert first == second


def test_monaco_golden_matches_prof_monaco_reference(tmp_path: Path):
    payload = analyze_run(
        MONACO_CSV,
        MONACO_LOG,
        _empty_sidecar(tmp_path / "monaco_events.csv"),
        track="monaco",
        expected_variedade=0,
    )
    assert payload["off_pct"] == pytest.approx(56.933, abs=0.001)
    assert payload["n_events"] == 41


def test_missing_sidecar_is_a_formal_integrity_failure(tmp_path: Path):
    with pytest.raises(MetricsIntegrityError, match="sidecar ausente"):
        analyze_run(
            REF_CSV,
            REF_LOG,
            tmp_path / "missing_events.csv",
            expected_variedade=0,
        )


def test_on_run_requires_configuration_sha(tmp_path: Path):
    sidecar = _empty_sidecar(tmp_path / "events.csv")
    with pytest.raises(MetricsIntegrityError, match="sem SHA da configuração"):
        analyze_run(
            REF_CSV,
            REF_LOG,
            sidecar,
            expected_variedade=0,
            mode="on",
        )


def test_wrong_track_header_is_rejected(tmp_path: Path):
    csv_copy = tmp_path / "wrong_track.csv"
    raw = REF_CSV.read_text(encoding="utf-8")
    csv_copy.write_text(
        raw.replace("track_frozen_sha256=164876196eb12174",
                    "track_frozen_sha256=67ca11dc211c8c78", 1),
        encoding="utf-8",
    )
    with pytest.raises(MetricsIntegrityError, match="SHA da pista divergente"):
        analyze_run(
            csv_copy,
            REF_LOG,
            _empty_sidecar(tmp_path / "events.csv"),
            expected_variedade=0,
        )


def test_metrics_output_is_create_only(tmp_path: Path):
    output = tmp_path / "metrics.json"
    write_exclusive(output, {"metrics_sha256": "synthetic"})
    with pytest.raises(FileExistsError):
        write_exclusive(output, {"metrics_sha256": "replacement"})
