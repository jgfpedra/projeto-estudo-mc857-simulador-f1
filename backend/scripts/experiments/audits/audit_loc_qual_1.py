#!/usr/bin/env python3
"""Offline, preregistered temporal-quality measurement for LOC-QUAL-1."""

from __future__ import annotations

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)


import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import subprocess
import sys
from collections import Counter, defaultdict


ROOT = pathlib.Path(__file__).resolve().parents[4]
PREREG_COMMIT = "902097e33a34a7d158e33a3222a45e18307221df"
PREREG_SHA256 = "a04cacc452f2231a5f105b10c21bd1086343903ebbb7471ca3d484609de8937e"
REQUIRED_KEYS = (
    "date",
    "session_key",
    "driver_number",
    "meeting_key",
    "x",
    "y",
    "z",
)
GAP_LIMITS_S = (1.0, 3.0, 10.0)
SPEED_LIMITS_M_S = (60.0, 90.0, 120.0)
JUMP_LIMITS_M = (10.0, 30.0, 100.0)
PRIMARY_GAP_S = 3.0
PRIMARY_SPEED_M_S = 120.0
MIN_VALID_COVERAGE = 0.90
QUANTILES = (0.50, 0.90, 0.95, 0.99)
STREAMS = (
    {
        "order": 1,
        "track": "Monza",
        "kind": "historico",
        "session_key": 9590,
        "driver_number": 44,
        "path": "backend/experiments/fonte-2/location_9590_d44.json",
        "bytes": 4338361,
        "sha256": "19c61905ba527d9114aeb54dc38df33f587c244215898e6af9f87427e090fc45",
    },
    {
        "order": 2,
        "track": "Hungaroring",
        "kind": "historico",
        "session_key": 9566,
        "driver_number": 81,
        "path": "backend/cache/openf1_pistas_expand_1/location_9566_81.json",
        "bytes": 5055421,
        "sha256": "16572644c117cd3085c1fb193de65363daf7446713514d4c82acf860c052cf03",
    },
    {
        "order": 3,
        "track": "Silverstone",
        "kind": "historico",
        "session_key": 9558,
        "driver_number": 44,
        "path": "backend/cache/openf1_pistas_expand_1/location_9558_44.json",
        "bytes": 4793907,
        "sha256": "3a9ff9f8c5631557937de0dcb87abc19dbbe696c16c3f50fe2d235efcfd0806f",
    },
    {
        "order": 4,
        "track": "Montreal",
        "kind": "historico",
        "session_key": 9531,
        "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9531_1.json",
        "bytes": 3644352,
        "sha256": "12e0ae6a3b36b19da28ab41bca0e6f0462e22b3ddda35f93ab9d8821e3f5bbf4",
    },
    {
        "order": 5,
        "track": "Bahrain",
        "kind": "historico",
        "session_key": 9472,
        "driver_number": 11,
        "path": "backend/cache/openf1_pistas_expand_1/location_9472_11.json",
        "bytes": 5063347,
        "sha256": "03e70429ce0cfa6554388ee4d1acf50ed52e48039f26fbc3ba2657445c220092",
    },
    {
        "order": 6,
        "track": "Mexico",
        "kind": "historico",
        "session_key": 9625,
        "driver_number": 55,
        "path": "backend/cache/openf1_pistas_expand_1/location_9625_55.json",
        "bytes": 5225558,
        "sha256": "a139c6f272b41510115479ec3a7055c593a1018e9a396b287afb9bbc86c01af4",
    },
    {
        "order": 7,
        "track": "Zandvoort",
        "kind": "historico",
        "session_key": 9582,
        "driver_number": 4,
        "path": "backend/cache/openf1_pistas_expand_1/location_9582_4.json",
        "bytes": 4832394,
        "sha256": "d5a88777e21924c68254a00c952511826a91a2394ef1b3bfdc2fd79c99c77332",
    },
    {
        "order": 8,
        "track": "Suzuka",
        "kind": "historico",
        "session_key": 9496,
        "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9496_1.json",
        "bytes": 5853936,
        "sha256": "7b3f00ecbbd7c54c44831b4e7699bb9b61b08fcba42fb2384bbd6a7c0280cb10",
    },
    {
        "order": 9,
        "track": "LasVegas",
        "kind": "historico",
        "session_key": 9644,
        "driver_number": 63,
        "path": "backend/cache/openf1_pistas_expand_1/location_9644_63.json",
        "bytes": 4702363,
        "sha256": "782bd62606a964c33c4896ac34e70f95e01bf8263429acacf2bfa40fce120b48",
    },
    {
        "order": 10,
        "track": "Miami",
        "kind": "historico",
        "session_key": 9507,
        "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9507_1.json",
        "bytes": 4795031,
        "sha256": "fcb7235f8154b544b727f12038922a42e75296d89f092026bceb265d3399bd89",
    },
    {
        "order": 11,
        "track": "Bahrain",
        "kind": "alternativo",
        "session_key": 9472,
        "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9472_1.json",
        "bytes": 5028285,
        "sha256": "0acc7c3776dbffdc8636cca2b12c65467dcde7614f67df274287ac63261711c4",
    },
    {
        "order": 12,
        "track": "Miami",
        "kind": "alternativo",
        "session_key": 9507,
        "driver_number": 4,
        "path": "backend/cache/openf1_pistas_expand_1/location_9507_4.json",
        "bytes": 4794049,
        "sha256": "b230968a62fefb5bcc7158d3b3d908cebebfabe74989676226076e97cafdf57d",
    },
    {
        "order": 13,
        "track": "Suzuka",
        "kind": "alternativo",
        "session_key": 9496,
        "driver_number": 11,
        "path": "backend/cache/openf1_pistas_expand_1/location_9496_11.json",
        "bytes": 5893840,
        "sha256": "bf58f1a3b450c7bec4d994396096be62ee2c33a2a3a1b945c329f6a3280d2ff7",
    },
    {
        "order": 14,
        "track": "Suzuka",
        "kind": "alternativo",
        "session_key": 9496,
        "driver_number": 55,
        "path": "backend/cache/openf1_pistas_expand_1/location_9496_55.json",
        "bytes": 5890089,
        "sha256": "bb9947035b223763901839d723a67bbb87030687254b4c5eaea47465d7b5f7fc",
    },
    {
        "order": 15,
        "track": "Zandvoort",
        "kind": "alternativo",
        "session_key": 9582,
        "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9582_1.json",
        "bytes": 4834156,
        "sha256": "4b9798cf288e688f72987fffba6f64be108489c22c98a5a8d3e5b68545ad5721",
    },
    {
        "order": 16,
        "track": "Zandvoort",
        "kind": "alternativo",
        "session_key": 9582,
        "driver_number": 16,
        "path": "backend/cache/openf1_pistas_expand_1/location_9582_16.json",
        "bytes": 4868284,
        "sha256": "9829fc170b9012339b3a9fed6c15002432908b299a1dafcb88d4b2e1b827e50a",
    },
)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_text(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def identity_matches(value: object, expected: int) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value == expected
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value) == expected
    return False


def nearest_rank(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def interval_distribution(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "minimum_seconds": None,
            "maximum_seconds": None,
            "quantiles_seconds": {f"P{int(q * 100)}": None for q in QUANTILES},
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "minimum_seconds": ordered[0],
        "maximum_seconds": ordered[-1],
        "quantiles_seconds": {
            f"P{int(q * 100)}": nearest_rank(ordered, q) for q in QUANTILES
        },
    }


def distance_distribution(values: list[float]) -> dict[str, object]:
    return {
        "count": len(values),
        "quantiles_m": {
            f"P{int(q * 100)}": nearest_rank(values, q) for q in QUANTILES
        },
    }


def band_counts(
    values: list[float], limits: tuple[float, ...], unit: str
) -> dict[str, object]:
    result: dict[str, object] = {"denominator": len(values), "bands": {}}
    for limit in limits:
        count = sum(value > limit for value in values)
        key = f">{limit:g}{unit}"
        result["bands"][key] = {
            "count": count,
            "fraction": count / len(values) if values else None,
        }
    return result


def xy_distance(left: dict[str, object], right: dict[str, object]) -> float:
    dx = (right["x"] - left["x"]) / 10.0
    dy = (right["y"] - left["y"]) / 10.0
    return math.hypot(dx, dy)


def duplicate_summary(rows: list[dict[str, object]]) -> dict[str, int]:
    by_time: dict[dt.datetime, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["time"] is not None:
            by_time[row["time"]].append(row)
    repeated = [group for group in by_time.values() if len(group) > 1]
    conflicting = 0
    for group in repeated:
        coordinates = {
            (row["x"], row["y"])
            for row in group
            if row["x"] is not None and row["y"] is not None
        }
        if len(coordinates) > 1:
            conflicting += 1
    return {
        "duplicate_timestamp_groups": len(repeated),
        "excess_rows_in_duplicate_groups": sum(len(group) - 1 for group in repeated),
        "conflicting_xy_duplicate_groups": conflicting,
    }


def pair_metrics(rows: list[dict[str, object]]) -> tuple[dict[str, object], dict[str, list[float]]]:
    positive_dt: list[float] = []
    distances: list[float] = []
    speeds: list[float] = []
    delta_counts = Counter()
    valid_date_pairs = 0

    for left, right in zip(rows, rows[1:]):
        if left["time"] is None or right["time"] is None:
            continue
        valid_date_pairs += 1
        delta = (right["time"] - left["time"]).total_seconds()
        if delta < 0:
            delta_counts["negative"] += 1
            continue
        if delta == 0:
            delta_counts["zero"] += 1
            continue
        delta_counts["positive"] += 1
        positive_dt.append(delta)
        if left["x"] is None or left["y"] is None or right["x"] is None or right["y"] is None:
            continue
        distance = xy_distance(left, right)
        distances.append(distance)
        speeds.append(distance / delta)

    metrics = {
        "adjacent_file_pairs": max(0, len(rows) - 1),
        "pairs_with_usable_dates": valid_date_pairs,
        "delta_t_sign_counts": {
            "negative_inversions": delta_counts["negative"],
            "zero_duplicate_adjacencies": delta_counts["zero"],
            "positive_intervals": delta_counts["positive"],
        },
        "positive_interval_distribution": interval_distribution(positive_dt),
        "gap_bands": band_counts(positive_dt, GAP_LIMITS_S, "s"),
        "distance_quantiles": distance_distribution(distances),
        "jump_bands": band_counts(distances, JUMP_LIMITS_M, "m"),
        "implicit_speed_bands": band_counts(speeds, SPEED_LIMITS_M_S, "m/s"),
    }
    return metrics, {"dt": positive_dt, "distance": distances, "speed": speeds}


def build_rows(
    records: list[object],
    stream: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, object], int]:
    missing_key_counts: Counter[str] = Counter()
    unusable_value_counts: Counter[str] = Counter()
    identity_mismatches = 0
    invalid_records = 0
    rows: list[dict[str, object]] = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            record = {}
        missing = [key for key in REQUIRED_KEYS if key not in record]
        for key in missing:
            missing_key_counts[key] += 1

        timestamp = parse_utc(record.get("date")) if "date" in record else None
        x_value = finite_number(record.get("x")) if "x" in record else None
        y_value = finite_number(record.get("y")) if "y" in record else None
        if "date" in record and timestamp is None:
            unusable_value_counts["date"] += 1
        if "x" in record and x_value is None:
            unusable_value_counts["x"] += 1
        if "y" in record and y_value is None:
            unusable_value_counts["y"] += 1

        for field, expected in (
            ("session_key", stream["session_key"]),
            ("driver_number", stream["driver_number"]),
        ):
            if field in record and not identity_matches(record[field], expected):
                identity_mismatches += 1

        if missing or timestamp is None or x_value is None or y_value is None:
            invalid_records += 1
        rows.append(
            {
                "index": index,
                "time": timestamp,
                "x": x_value,
                "y": y_value,
            }
        )

    field_report = {
        "missing_required_keys": {key: missing_key_counts[key] for key in REQUIRED_KEYS},
        "unusable_values": {
            key: unusable_value_counts[key] for key in ("date", "x", "y")
        },
        "records_with_irrecoverable_fields": invalid_records,
        "identity_mismatch_values": identity_mismatches,
    }
    return rows, field_report, identity_mismatches


def preclean_metrics(
    rows: list[dict[str, object]],
    duplicates: dict[str, int],
) -> tuple[dict[str, object] | None, dict[str, list[float]] | None]:
    if duplicates["conflicting_xy_duplicate_groups"] > 0:
        return None, None

    ordered = sorted(rows, key=lambda row: (row["time"], row["index"]))
    coalesced: list[dict[str, object]] = []
    coalesced_groups = 0
    coalesced_excess = 0
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end]["time"] == ordered[position]["time"]:
            end += 1
        group = ordered[position:end]
        if len(group) > 1:
            coordinates = {(row["x"], row["y"]) for row in group}
            if len(coordinates) != 1:
                return None, None
            coalesced_groups += 1
            coalesced_excess += len(group) - 1
        coalesced.append(group[0])
        position = end

    observed_start = coalesced[0]["time"] if coalesced else None
    observed_end = coalesced[-1]["time"] if coalesced else None
    window = (
        (observed_end - observed_start).total_seconds()
        if observed_start is not None and observed_end is not None
        else 0.0
    )

    intervals: list[float] = []
    distances: list[float] = []
    speeds: list[float] = []
    cut_count = 0
    cut_seconds = 0.0
    retained_count = 0
    for left, right in zip(coalesced, coalesced[1:]):
        delta = (right["time"] - left["time"]).total_seconds()
        if delta <= 0:
            continue
        distance = xy_distance(left, right)
        speed = distance / delta
        intervals.append(delta)
        distances.append(distance)
        speeds.append(speed)
        if delta > PRIMARY_GAP_S or speed > PRIMARY_SPEED_M_S:
            cut_count += 1
            cut_seconds += delta
        else:
            retained_count += 1

    coverage = 1.0 - cut_seconds / window if window > 0 else None
    metrics = {
        "stable_sorted_points": len(ordered),
        "coalesced_points": len(coalesced),
        "coalesced_duplicate_groups": coalesced_groups,
        "coalesced_excess_rows": coalesced_excess,
        "observed_window": {
            "start_utc": utc_text(observed_start),
            "end_utc": utc_text(observed_end),
            "duration_seconds": window if window > 0 else None,
        },
        "positive_interval_distribution": interval_distribution(intervals),
        "gap_bands": band_counts(intervals, GAP_LIMITS_S, "s"),
        "distance_quantiles": distance_distribution(distances),
        "jump_bands": band_counts(distances, JUMP_LIMITS_M, "m"),
        "implicit_speed_bands": band_counts(speeds, SPEED_LIMITS_M_S, "m/s"),
        "cut_intervals_primary_rule": cut_count,
        "cut_interval_duration_seconds": cut_seconds,
        "retained_intervals_primary_rule": retained_count,
        "valid_window_coverage_fraction": coverage,
        "official_session_coverage": "FALTA_DADO(repo)",
    }
    return metrics, {"dt": intervals, "distance": distances, "speed": speeds}


def classify_stream(
    rows: list[dict[str, object]],
    field_report: dict[str, object],
    duplicates: dict[str, int],
    original_metrics: dict[str, object],
    cleaned_metrics: dict[str, object] | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if field_report["records_with_irrecoverable_fields"] > 0:
        return "só geometria", ["required_field_irrecoverable"]
    if duplicates["conflicting_xy_duplicate_groups"] > 0:
        return "só geometria", ["duplicate_timestamp_conflicting_xy"]

    raw_signs = original_metrics["delta_t_sign_counts"]
    raw_intervals = original_metrics["positive_interval_distribution"]["count"]
    raw_speeds = original_metrics["implicit_speed_bands"]
    raw_speed_count = raw_speeds["denominator"]
    raw_speed_over = raw_speeds["bands"][">120m/s"]["count"]
    row_count = len(rows)
    as_is = (
        row_count >= 2
        and raw_signs["negative_inversions"] == 0
        and raw_signs["zero_duplicate_adjacencies"] == 0
        and duplicates["duplicate_timestamp_groups"] == 0
        and raw_intervals == row_count - 1
        and raw_speed_count == row_count - 1
        and raw_speed_over == 0
        and all(
            value <= PRIMARY_GAP_S
            for value in original_metrics["_positive_dt_values"]
        )
    )
    if as_is:
        return "utilizável como está", reasons

    if raw_signs["negative_inversions"] > 0:
        reasons.append("original_order_not_strictly_increasing")
    if duplicates["duplicate_timestamp_groups"] > 0:
        reasons.append("duplicate_timestamps_require_coalescence")
    if cleaned_metrics is None:
        return "só geometria", reasons + ["precleaned_sequence_unavailable"]

    retained = cleaned_metrics["retained_intervals_primary_rule"]
    coverage = cleaned_metrics["valid_window_coverage_fraction"]
    if retained == 0:
        return "só geometria", reasons + ["no_valid_interval_remains"]
    if coverage is None or coverage < MIN_VALID_COVERAGE:
        return "só geometria", reasons + ["coverage_below_90_percent"]
    if cleaned_metrics["cut_intervals_primary_rule"] > 0:
        reasons.append("primary_rule_cuts_intervals")
    return "utilizável com pré-limpeza", reasons


def read_prereg_identity() -> None:
    path = ROOT / "backend" / "PREREG_LOC_QUAL_1.md"
    if not path.is_file() or sha256_file(path) != PREREG_SHA256:
        raise RuntimeError("prereg frozen ausente ou divergente do hash commitado")


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def process_stream(stream: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    source = ROOT / stream["path"]
    result: dict[str, object] = {
        "order": stream["order"],
        "track": stream["track"],
        "kind": stream["kind"],
        "session_key": stream["session_key"],
        "driver_number": stream["driver_number"],
        "path": stream["path"],
        "expected_bytes": stream["bytes"],
        "expected_sha256": stream["sha256"],
        "status": "FALTA_DADO(repo)",
        "classification": "FALTA_DADO(repo)",
    }
    empty_field_report = {
        "missing_required_keys": {key: 0 for key in REQUIRED_KEYS},
        "unusable_values": {key: 0 for key in ("date", "x", "y")},
        "records_with_irrecoverable_fields": 0,
        "identity_mismatch_values": 0,
    }
    empty = {
        "original": None,
        "precleaned": None,
        "coverage_window": None,
        "coverage_cut": None,
        "field_report": empty_field_report,
        "classification": "FALTA_DADO(repo)",
    }
    if not source.is_file():
        result["failure"] = "pinned_file_missing"
        return result, empty
    actual_bytes = source.stat().st_size
    actual_sha = sha256_file(source)
    result["actual_bytes"] = actual_bytes
    result["actual_sha256"] = actual_sha
    if actual_bytes != stream["bytes"] or actual_sha != stream["sha256"]:
        result["failure"] = "pinned_file_size_or_hash_mismatch"
        return result, empty
    try:
        records = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        result["failure"] = f"pinned_file_unreadable:{type(error).__name__}"
        return result, empty
    if not isinstance(records, list):
        result["failure"] = "json_root_is_not_a_list"
        return result, empty

    rows, field_report, identity_mismatches = build_rows(records, stream)
    result["record_count"] = len(records)
    result["field_report"] = field_report
    if identity_mismatches:
        result["failure"] = "session_or_driver_identity_does_not_match_pin"
        empty["field_report"] = field_report
        return result, empty

    duplicates = duplicate_summary(rows)
    original_metrics, raw_aggregate = pair_metrics(rows)
    original_metrics["inversions_in_original_order"] = original_metrics[
        "delta_t_sign_counts"
    ]["negative_inversions"]
    original_metrics["duplicate_timestamp_groups"] = duplicates[
        "duplicate_timestamp_groups"
    ]
    original_metrics["excess_rows_in_duplicate_groups"] = duplicates[
        "excess_rows_in_duplicate_groups"
    ]
    original_metrics["conflicting_xy_duplicate_groups"] = duplicates[
        "conflicting_xy_duplicate_groups"
    ]
    original_metrics["_positive_dt_values"] = raw_aggregate["dt"]

    has_irrecoverable = field_report["records_with_irrecoverable_fields"] > 0
    cleaned_metrics = None
    cleaned_aggregate = None
    if not has_irrecoverable and duplicates["conflicting_xy_duplicate_groups"] == 0:
        cleaned_metrics, cleaned_aggregate = preclean_metrics(rows, duplicates)

    classification, reasons = classify_stream(
        rows, field_report, duplicates, original_metrics, cleaned_metrics
    )
    original_metrics.pop("_positive_dt_values")
    result["status"] = "calculado"
    result["classification"] = classification
    result["classification_reasons"] = reasons
    valid_times = [row["time"] for row in rows if row["time"] is not None]
    observed_start = min(valid_times) if valid_times else None
    observed_end = max(valid_times) if valid_times else None
    result["observed_window"] = {
        "start_utc": utc_text(observed_start),
        "end_utc": utc_text(observed_end),
        "duration_seconds": (
            (observed_end - observed_start).total_seconds()
            if observed_start is not None and observed_end is not None
            else None
        ),
        "official_session_coverage": "FALTA_DADO(repo)",
    }
    result["original_order"] = original_metrics
    result["precleaned_view"] = cleaned_metrics
    aggregate_data = {
        "original": raw_aggregate,
        "precleaned": cleaned_aggregate,
        "coverage_window": (
            cleaned_metrics["observed_window"]["duration_seconds"]
            if cleaned_metrics is not None
            else None
        ),
        "coverage_cut": (
            cleaned_metrics["cut_interval_duration_seconds"]
            if cleaned_metrics is not None
            else None
        ),
        "field_report": field_report,
        "classification": classification,
    }
    return result, aggregate_data


def summarize_aggregate(
    stream_results: list[dict[str, object]],
    aggregate_data: list[dict[str, object]],
) -> dict[str, object]:
    classifications = Counter(
        result["classification"] for result in stream_results
    )
    raw_dt: list[float] = []
    raw_distance: list[float] = []
    raw_speed: list[float] = []
    pre_dt: list[float] = []
    pre_distance: list[float] = []
    pre_speed: list[float] = []
    raw_inversions = 0
    raw_duplicates = 0
    raw_duplicate_excess = 0
    raw_conflicts = 0
    invalid_records = 0
    missing_keys: Counter[str] = Counter()
    unusable_values: Counter[str] = Counter()
    pre_cut_count = 0
    pre_cut_seconds = 0.0
    pre_retained_count = 0
    pre_window_seconds = 0.0
    pre_window_streams = 0

    for result, data in zip(stream_results, aggregate_data, strict=True):
        field_report = data["field_report"]
        invalid_records += field_report["records_with_irrecoverable_fields"]
        for key, count in field_report["missing_required_keys"].items():
            missing_keys[key] += count
        for key, count in field_report["unusable_values"].items():
            unusable_values[key] += count
        if result.get("status") != "calculado":
            continue
        original = result["original_order"]
        raw_inversions += original["inversions_in_original_order"]
        raw_duplicates += original["duplicate_timestamp_groups"]
        raw_duplicate_excess += original["excess_rows_in_duplicate_groups"]
        raw_conflicts += original["conflicting_xy_duplicate_groups"]
        raw_dt.extend(data["original"]["dt"])
        raw_distance.extend(data["original"]["distance"])
        raw_speed.extend(data["original"]["speed"])
        if data["precleaned"] is not None:
            pre_dt.extend(data["precleaned"]["dt"])
            pre_distance.extend(data["precleaned"]["distance"])
            pre_speed.extend(data["precleaned"]["speed"])
            pre = result["precleaned_view"]
            pre_cut_count += pre["cut_intervals_primary_rule"]
            pre_cut_seconds += pre["cut_interval_duration_seconds"]
            pre_retained_count += pre["retained_intervals_primary_rule"]
            if data["coverage_window"] is not None:
                pre_window_streams += 1
                pre_window_seconds += data["coverage_window"]

    pre_coverage = (
        1.0 - pre_cut_seconds / pre_window_seconds
        if pre_window_seconds > 0
        else None
    )
    return {
        "streams_by_classification": {
            key: classifications[key]
            for key in (
                "utilizável como está",
                "utilizável com pré-limpeza",
                "só geometria",
                "FALTA_DADO(repo)",
            )
        },
        "field_report_totals": {
            "records_with_irrecoverable_fields": invalid_records,
            "missing_required_keys": {key: missing_keys[key] for key in REQUIRED_KEYS},
            "unusable_values": {
                key: unusable_values[key] for key in ("date", "x", "y")
            },
        },
        "original_order": {
            "inversions": raw_inversions,
            "duplicate_timestamp_groups": raw_duplicates,
            "excess_rows_in_duplicate_groups": raw_duplicate_excess,
            "conflicting_xy_duplicate_groups": raw_conflicts,
            "positive_interval_distribution": interval_distribution(raw_dt),
            "gap_bands": band_counts(raw_dt, GAP_LIMITS_S, "s"),
            "distance_quantiles": distance_distribution(raw_distance),
            "jump_bands": band_counts(raw_distance, JUMP_LIMITS_M, "m"),
            "implicit_speed_bands": band_counts(raw_speed, SPEED_LIMITS_M_S, "m/s"),
        },
        "precleaned_view": {
            "streams_with_precleaned_view": sum(
                data["precleaned"] is not None for data in aggregate_data
            ),
            "positive_interval_distribution": interval_distribution(pre_dt),
            "gap_bands": band_counts(pre_dt, GAP_LIMITS_S, "s"),
            "distance_quantiles": distance_distribution(pre_distance),
            "jump_bands": band_counts(pre_distance, JUMP_LIMITS_M, "m"),
            "implicit_speed_bands": band_counts(pre_speed, SPEED_LIMITS_M_S, "m/s"),
            "cut_intervals_primary_rule": pre_cut_count,
            "cut_interval_duration_seconds": pre_cut_seconds,
            "retained_intervals_primary_rule": pre_retained_count,
            "observed_window_seconds": pre_window_seconds,
            "streams_in_observed_window_coverage": pre_window_streams,
            "valid_window_coverage_fraction": pre_coverage,
        },
        "interpretation": "descritivo; pilotos alternativos não são pistas independentes",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    read_prereg_identity()
    instrument_path = pathlib.Path(__file__).resolve()
    instrument_sha = sha256_file(instrument_path)
    current_head = git_head()
    stream_results: list[dict[str, object]] = []
    aggregate_data: list[dict[str, object]] = []
    for stream in STREAMS:
        result, data = process_stream(stream)
        stream_results.append(result)
        aggregate_data.append(data)

    type_aggregates: dict[str, object] = {}
    for kind in ("historico", "alternativo"):
        matching = [
            (result, data)
            for result, data in zip(stream_results, aggregate_data, strict=True)
            if result["kind"] == kind
        ]
        type_aggregates[kind] = summarize_aggregate(
            [item[0] for item in matching], [item[1] for item in matching]
        )

    document = {
        "cycle": "LOC-QUAL-1",
        "classification_label": "diagnóstico exploratório",
        "prereg": {
            "path": "backend/PREREG_LOC_QUAL_1.md",
            "commit": PREREG_COMMIT,
            "sha256": PREREG_SHA256,
        },
        "instrument": {
            "path": "backend/scripts/experiments/audits/audit_loc_qual_1.py",
            "commit_at_measurement": current_head,
            "sha256": instrument_sha,
        },
        "runtime": {
            "implementation": sys.implementation.name,
            "python_version": ".".join(str(part) for part in sys.version_info[:3]),
            "external_dependencies": [],
        },
        "network_calls": 0,
        "simulations": 0,
        "frozen_path_writes": 0,
        "official_session_bounds": "FALTA_DADO(repo)",
        "nominal_location_cadence": "FALTA_DADO(repo)",
        "aggregation_note": "agregados por tipo são descritivos e não tratam pilotos como pistas independentes",
        "streams": stream_results,
        "aggregates_by_type": type_aggregates,
    }

    output_dir = pathlib.Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "results.json"
    encoded = (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    output_path.write_bytes(encoded)
    print(f"wrote {output_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
