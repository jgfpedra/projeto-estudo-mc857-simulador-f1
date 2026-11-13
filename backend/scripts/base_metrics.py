#!/usr/bin/env python3
"""Report-only metrics extractor for frozen race-diagnostic artifacts.

This module only reads a runner log, main CSV, and solver-events CSV. It does
not import the simulator, controllers, models, or training pipeline.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable


VERSION = "base-metrics-v1.0"
MAIN_COLUMNS = {
    "tick", "t_s", "drv", "s", "lat", "cum_dist", "speed", "offtrack",
    "car_car",
}
EVENT_COLUMNS = {"sub", "drv_a", "drv_b"}


class MetricsInputError(ValueError):
    """A required input, schema, or runner-summary field is invalid."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _float(row: dict[str, str], field: str, *, source: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise MetricsInputError(f"{source}: invalid {field}={row.get(field)!r}") from exc
    if not math.isfinite(value):
        raise MetricsInputError(f"{source}: non-finite {field}={value!r}")
    return value


def _int(row: dict[str, str], field: str, *, source: str) -> int:
    value = _float(row, field, source=source)
    if not value.is_integer():
        raise MetricsInputError(f"{source}: expected integer {field}, got {value!r}")
    return int(value)


def _read_csv(path: Path, required: set[str], *,
              allow_empty: bool = False) -> tuple[list[dict[str, str]], bytes]:
    if not path.is_file():
        raise MetricsInputError(f"missing input file: {path}")
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        with io.StringIO(text, newline="") as stream:
            data_lines = (line for line in stream if line.strip() and not line.startswith("#"))
            reader = csv.DictReader(data_lines)
            headers = set(reader.fieldnames or ())
            missing = sorted(required - headers)
            if missing:
                raise MetricsInputError(
                    f"{path}: schema missing required columns {missing}; "
                    f"found {sorted(headers)}")
            rows = list(reader)
    except UnicodeDecodeError as exc:
        raise MetricsInputError(f"{path}: CSV is not UTF-8") from exc
    if not rows and not allow_empty:
        raise MetricsInputError(f"{path}: CSV has a valid header but no data rows")
    if any(None in row for row in rows):
        raise MetricsInputError(f"{path}: row has more values than its header")
    return rows, raw


def _findall_capture(found: list[str] | list[tuple[str, ...]]) -> str:
    """Normalize re.findall: a single group yields str, not a 1-tuple."""
    match = found[0]
    return match[0] if isinstance(match, tuple) else match


def _parse_runner_summary(log_text: str, *, driver_count: int) -> dict[str, object]:
    """Read the three legacy summary cells used for A-OFF calibration."""
    patterns = {
        "offtrack": re.compile(
            r"TOTAL fora:\s*(\d+)\s*ticks\s*\(([0-9]+(?:[.,][0-9]+)?)%\)"),
        "stuck": re.compile(r"CARROS-PRESO na sessão:\s*(\d+)\s*\("),
        "hesitations": re.compile(r"HESITAÇÕES[^\n]*?:\s*(\d+)\s*\("),
    }
    matches = {
        key: pattern.findall(log_text) for key, pattern in patterns.items()
    }
    missing = [name for name, found in matches.items() if len(found) != 1]
    if missing:
        counts = {name: len(found) for name, found in matches.items()}
        raise MetricsInputError(
            f"runner log must contain exactly one historical summary for each "
            f"of fora/presos/hesitações; found {counts}")
    off_ticks, off_pct = matches["offtrack"][0]
    return {
        "stuck_car_count": int(_findall_capture(matches["stuck"])),
        "driver_count": driver_count,
        "offtrack_ticks": int(off_ticks),
        "offtrack_pct": float(off_pct.replace(",", ".")),
        "hesitations": int(_findall_capture(matches["hesitations"])),
    }


def _stuck_drivers(rows: list[dict[str, str]]) -> list[str]:
    """Reproduce race_diagnostic.py's 30-second off-track stuck windows."""
    by_driver: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_driver.setdefault(row["drv"], []).append(row)
    stuck: set[str] = set()
    session_end = max(_float(row, "t_s", source="main") for row in rows)
    for driver, driver_rows in by_driver.items():
        ordered = sorted(driver_rows, key=lambda row: _float(row, "t_s", source="main"))
        for window_start in _window_starts(session_end):
            window = [row for row in ordered
                      if window_start <= _float(row, "t_s", source="main")
                      < window_start + 30.0]
            if not window or not any(_int(row, "offtrack", source="main")
                                     for row in window):
                continue
            lat_max = max(abs(_float(row, "lat", source="main")) for row in window)
            cum_values = [_float(row, "cum_dist", source="main") for row in window]
            if lat_max > 20.0 or max(cum_values) - min(cum_values) < 5.0:
                stuck.add(driver)
                break
    return sorted(stuck)


def _window_starts(session_end: float) -> Iterable[float]:
    start = 0.0
    while start < session_end:
        yield start
        start += 30.0


def _hesitation_count(rows: list[dict[str, str]]) -> int:
    """Reproduce the legacy t_s>20, speed<0.5, duration [0.3,3) rule."""
    by_driver: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_driver.setdefault(row["drv"], []).append(row)
    count = 0
    for driver_rows in by_driver.values():
        ordered = sorted(driver_rows, key=lambda row: _float(row, "t_s", source="main"))
        selected = [row for row in ordered
                    if _float(row, "t_s", source="main") > 20.0]
        speeds = [_float(row, "speed", source="main") for row in selected]
        times = [_float(row, "t_s", source="main") for row in selected]
        i = 0
        while i < len(speeds):
            if speeds[i] < 0.5:
                j = i
                while j < len(speeds) and speeds[j] < 0.5:
                    j += 1
                end_i = min(j, len(times) - 1)
                duration = times[end_i] - times[i]
                if 0.3 <= duration < 3.0:
                    count += 1
                i = j
            else:
                i += 1
    return count


def _lap_crossings(rows: list[dict[str, str]]) -> dict[str, int]:
    by_driver: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_driver.setdefault(row["drv"], []).append(row)
    result: dict[str, int] = {}
    for driver, driver_rows in by_driver.items():
        ordered = sorted(driver_rows, key=lambda row: _int(row, "tick", source="main"))
        progress = [_float(row, "s", source="main") for row in ordered]
        result[driver] = sum(
            progress[i] < progress[i - 1] - 2000.0
            for i in range(1, len(progress)))
    return dict(sorted(result.items()))


def _event_pair_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    pairs: Counter[str] = Counter()
    for row in rows:
        _int(row, "sub", source="events")
        a, b = str(row["drv_a"]), str(row["drv_b"])
        if not a or not b or a == b:
            raise MetricsInputError(f"events: invalid solver pair {a!r}, {b!r}")
        pairs["-".join(sorted((a, b)))] += 1
    return dict(sorted(pairs.items()))


def analyze_race(log_path: str | Path, main_path: str | Path,
                 events_path: str | Path, *, run_id: str) -> dict[str, object]:
    """Return deterministic report metrics and source hashes for one race."""
    paths = {"log": Path(log_path), "main": Path(main_path),
             "events": Path(events_path)}
    for name, path in paths.items():
        if not path.is_file():
            raise MetricsInputError(f"missing {name} input file: {path}")
    try:
        log_bytes = paths["log"].read_bytes()
        log_text = log_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MetricsInputError(f"{paths['log']}: log is not UTF-8") from exc
    main_rows, main_bytes = _read_csv(paths["main"], MAIN_COLUMNS)
    event_rows, event_bytes = _read_csv(
        paths["events"], EVENT_COLUMNS, allow_empty=True)
    drivers = sorted({row["drv"] for row in main_rows})
    if not drivers or "" in drivers:
        raise MetricsInputError(f"{paths['main']}: empty driver identifier")

    stuck_ids = _stuck_drivers(main_rows)
    off_values = [_int(row, "offtrack", source="main") for row in main_rows]
    if any(value not in (0, 1) for value in off_values):
        raise MetricsInputError("main: offtrack values must be 0 or 1")
    offtrack_pct = round(100.0 * sum(off_values) / len(off_values), 1)
    contact_rows = [row for row in main_rows
                    if _int(row, "car_car", source="main") > 0]
    contact_initial = sum(
        _float(row, "t_s", source="main") <= 60.0 for row in contact_rows)
    laps_by_driver = _lap_crossings(main_rows)
    runner_summary = _parse_runner_summary(log_text, driver_count=len(drivers))
    payload: dict[str, object] = {
        "schema_version": VERSION,
        "run_id": str(run_id),
        "source_sha256": {
            "events": _sha256_bytes(event_bytes),
            "log": _sha256_bytes(log_bytes),
            "main": _sha256_bytes(main_bytes),
        },
        "sample_rows": len(main_rows),
        "driver_count": len(drivers),
        "stuck_driver_ids": stuck_ids,
        "stuck_car_count": len(stuck_ids),
        "offtrack_pct": offtrack_pct,
        "hesitations": _hesitation_count(main_rows),
        "contacts_5hz_total": len(contact_rows),
        "contacts_5hz_t_le_60s": int(contact_initial),
        "solver_event_rows": len(event_rows),
        "solver_event_contacts_by_pair": _event_pair_counts(event_rows),
        "laps_by_driver": laps_by_driver,
        "laps_total": sum(laps_by_driver.values()),
        "runner_summary": runner_summary,
    }
    payload["metrics_sha256"] = _sha256_bytes(_canonical_json(payload).encode("utf-8"))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--main-csv", required=True, type=Path)
    parser.add_argument("--events-csv", required=True, type=Path)
    parser.add_argument("--out", type=Path,
                        help="optional new JSON path; existing paths are never overwritten")
    args = parser.parse_args()
    report = analyze_race(args.log, args.main_csv, args.events_csv,
                          run_id=args.run_id)
    text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
