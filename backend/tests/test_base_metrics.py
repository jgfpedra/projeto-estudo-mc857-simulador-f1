import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.base_metrics import (
    MetricsInputError,
    _parse_runner_summary,
    analyze_race,
)


BACKEND = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]],
               metadata: str = "# fixture\n") -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(metadata)
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _fixture_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    log = tmp_path / "fixture.log"
    main = tmp_path / "fixture.csv"
    events = tmp_path / "fixture_events.csv"
    log.write_text(
        "TOTAL fora: 2 ticks (12.5%) | FORA-PILOTAGEM: 0 | FORA-PRESO: 2\n"
        "CARROS-PRESO na sessão: 1 (LEC — gate exige 0)\n"
        "HESITAÇÕES (v<0,5 m/s por 0,3-3 s, pós-largada): 1 (gate: <=3)\n",
        encoding="utf-8",
    )
    headers = ["tick", "t_s", "drv", "s", "lat", "cum_dist", "speed",
               "offtrack", "car_car"]
    rows = []
    times = [0.0, 0.2, 20.2, 20.4, 20.6, 20.8, 21.0, 21.2]
    for drv in ("LEC", "HAM"):
        for i, t_s in enumerate(times):
            speed = 0.0 if drv == "LEC" and 20.2 <= t_s <= 20.8 else 5.0
            offtrack = int(drv == "LEC" and t_s in (0.0, 0.2))
            lat = 21.0 if offtrack else 0.0
            progress = ([100, 150, 200, 250, 300, 350, 400, 450][i]
                        if drv == "LEC" else
                        [3000, 3010, 500, 510, 520, 530, 540, 550][i])
            rows.append({
                "tick": i * 2,
                "t_s": t_s,
                "drv": drv,
                "s": progress,
                "lat": lat,
                "cum_dist": i * 5.0,
                "speed": speed,
                "offtrack": offtrack,
                "car_car": int(drv == "LEC" and t_s == 20.2),
            })
    _write_csv(main, headers, rows)
    _write_csv(events, ["sub", "drv_a", "drv_b"], [
        {"sub": 12, "drv_a": "LEC", "drv_b": "HAM"},
        {"sub": 13, "drv_a": "HAM", "drv_b": "LEC"},
    ])
    return log, main, events


def test_synthetic_metrics_and_canonical_hash(tmp_path):
    log, main, events = _fixture_inputs(tmp_path)
    first = analyze_race(log, main, events, run_id="synthetic")
    second = analyze_race(log, main, events, run_id="synthetic")

    assert first == second
    assert first["driver_count"] == 2
    assert first["stuck_driver_ids"] == ["LEC"]
    assert first["stuck_car_count"] == 1
    assert first["offtrack_pct"] == 12.5
    assert first["hesitations"] == 1
    assert first["contacts_5hz_total"] == 1
    assert first["contacts_5hz_t_le_60s"] == 1
    assert first["solver_event_rows"] == 2
    assert first["solver_event_contacts_by_pair"] == {"HAM-LEC": 2}
    assert first["laps_by_driver"] == {"HAM": 1, "LEC": 0}
    assert first["laps_total"] == 1

    own_hash = first.pop("metrics_sha256")
    canonical = json.dumps(first, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    assert own_hash == hashlib.sha256(canonical).hexdigest()


def test_a_off_matches_frozen_historical_summary_cell_by_cell():
    prereg = (BACKEND / "experiments/composite-1/PREREG_COMPOSITE_BASE_1.md")
    prereg_text = prereg.read_text(encoding="utf-8")
    root = BACKEND / "experiments/composite-1"
    filenames = ("A_OFF.log", "A_OFF_main.csv", "A_OFF_main_events.csv")
    paths = {name: root / name for name in filenames}
    for name, path in paths.items():
        pin = re.search(
            rf"`{re.escape(name)}`(?: SHA-256)? `([0-9a-f]{{64}})`",
            prereg_text,
        )
        assert pin, f"missing frozen SHA-256 for {name} in prereg"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin.group(1)

    report = analyze_race(paths["A_OFF.log"], paths["A_OFF_main.csv"],
                          paths["A_OFF_main_events.csv"],
                          run_id="A-OFF-calibration")
    # Published calibration values, recomputed independently from the main CSV.
    assert report["driver_count"] == 10
    assert report["stuck_car_count"] == 10
    assert report["offtrack_pct"] == 25.2
    assert report["hesitations"] == 14
    # Historical runner summary must match each formula-derived cell.
    legacy = report["runner_summary"]
    assert legacy["stuck_car_count"] == report["stuck_car_count"] == 10
    assert legacy["driver_count"] == report["driver_count"] == 10
    assert legacy["offtrack_pct"] == report["offtrack_pct"] == 25.2
    assert legacy["hesitations"] == report["hesitations"] == 14


def test_schema_precheck_fails_loudly(tmp_path):
    log, _main, events = _fixture_inputs(tmp_path)
    bad_main = tmp_path / "bad.csv"
    _write_csv(bad_main, ["tick", "drv"], [{"tick": 0, "drv": "LEC"}])
    with pytest.raises(MetricsInputError, match="schema missing required columns"):
        analyze_race(log, bad_main, events, run_id="bad-schema")


def test_empty_solver_sidecar_with_header_is_valid(tmp_path):
    log, main, events = _fixture_inputs(tmp_path)
    _write_csv(events, ["sub", "drv_a", "drv_b"], [])
    report = analyze_race(log, main, events, run_id="no-solver-events")
    assert report["solver_event_rows"] == 0
    assert report["solver_event_contacts_by_pair"] == {}


def test_parse_runner_summary_reads_multi_digit_cells():
    summary = _parse_runner_summary(
        "CARROS-PRESO na sessão: 12 (...)\n"
        "HESITAÇÕES (v<0,5 m/s por 0,3-3 s, pós-largada): 23 (...)\n"
        "TOTAL fora: 12345 ticks (12,3%)\n",
        driver_count=10,
    )
    assert summary == {
        "stuck_car_count": 12,
        "driver_count": 10,
        "offtrack_ticks": 12345,
        "offtrack_pct": 12.3,
        "hesitations": 23,
    }


def test_parse_runner_summary_rejects_duplicate_cell():
    with pytest.raises(MetricsInputError, match="exactly one historical summary"):
        _parse_runner_summary(
            "TOTAL fora: 2 ticks (12.5%)\n"
            "CARROS-PRESO na sessão: 1 (LEC)\n"
            "CARROS-PRESO na sessão: 1 (LEC)\n"
            "HESITAÇÕES (v<0,5 m/s por 0,3-3 s, pós-largada): 1 (gate: <=3)\n",
            driver_count=2,
        )


def test_parse_runner_summary_rejects_missing_cell():
    with pytest.raises(MetricsInputError, match="exactly one historical summary"):
        _parse_runner_summary(
            "TOTAL fora: 2 ticks (12.5%)\n"
            "CARROS-PRESO na sessão: 1 (LEC)\n",
            driver_count=2,
        )
