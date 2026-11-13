#!/usr/bin/env python3
"""Offline execution of frozen PREREG_GATE_RE_DERIVE_1.

Reads only the exact, hash-pinned local streams listed in the prereg and the
local f1db database. It never calls an API and never writes geometry/cache
files. The sole output is a small audit JSON without raw telemetry.
"""
from __future__ import annotations

import csv
import hashlib
import inspect
import json
import math
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND / "scripts"))
import track_geometry_free as TGF  # noqa: E402

PREREG_COMMIT = "194a709"
UNIT_SCALE = 0.1
RESAMPLE_M = 10.0
MIN_STEP_M = 0.5
CELL_M = 60.0
MAX_SPEED_M_S = 120.0
MIN_RAW_SAMPLES = 100
MIN_WAYPOINTS = 50
MIN_SEGMENT_M = 5.0
MAX_SEGMENT_M = 15.0
SCALE_RATIO_MIN = 0.05
SCALE_RATIO_MAX = 0.50
TOPOLOGY_TOL_M = 0.1
EPSILON_PP = 1e-12
LOO_MULTIPLIER = 3.0
MIN_FIT_TRACKS = 5

OFFICIAL = {
    "Monza": ("monza", 5793.0),
    "Hungaroring": ("hungaroring", 4381.0),
    "Silverstone": ("silverstone", 5891.0),
    "Montreal": ("montreal", 4361.0),
    "Bahrain": ("bahrain", 5412.0),
    "Mexico": ("mexico-city", 4304.0),
    "Zandvoort": ("zandvoort", 4259.0),
    "Suzuka": ("suzuka", 5807.0),
    "LasVegas": ("las-vegas", 6201.0),
    "Miami": ("miami", 5412.0),
}

MONZA = {
    "key": "Monza",
    "session_key": 9590,
    "driver_number": 44,
    "path": "backend/experiments/fonte-2/location_9590_d44.json",
    "sha256": "19c61905ba527d9114aeb54dc38df33f587c244215898e6af9f87427e090fc45",
    "published_delta_pct": -0.64,
    "prior_status": "FONTE-2 demonstração; método",
}

HISTORICAL_SHAS = {
    "Hungaroring": "16572644c117cd3085c1fb193de65363daf7446713514d4c82acf860c052cf03",
    "Silverstone": "3a9ff9f8c5631557937de0dcb87abc19dbbe696c16c3f50fe2d235efcfd0806f",
    "Montreal": "12e0ae6a3b36b19da28ab41bca0e6f0462e22b3ddda35f93ab9d8821e3f5bbf4",
    "Bahrain": "03e70429ce0cfa6554388ee4d1acf50ed52e48039f26fbc3ba2657445c220092",
    "Mexico": "a139c6f272b41510115479ec3a7055c593a1018e9a396b287afb9bbc86c01af4",
    "Zandvoort": "d5a88777e21924c68254a00c952511826a91a2394ef1b3bfdc2fd79c99c77332",
    "Suzuka": "7b3f00ecbbd7c54c44831b4e7699bb9b61b08fcba42fb2384bbd6a7c0280cb10",
    "LasVegas": "782bd62606a964c33c4896ac34e70f95e01bf8263429acacf2bfa40fce120b48",
    "Miami": "fcb7235f8154b544b727f12038922a42e75296d89f092026bceb265d3399bd89",
}

ALTERNATES = [
    {
        "key": "Bahrain", "session_key": 9472, "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9472_1.json",
        "sha256": "0acc7c3776dbffdc8636cca2b12c65467dcde7614f67df274287ac63261711c4",
    },
    {
        "key": "Miami", "session_key": 9507, "driver_number": 4,
        "path": "backend/cache/openf1_pistas_expand_1/location_9507_4.json",
        "sha256": "b230968a62fefb5bcc7158d3b3d908cebebfabe74989676226076e97cafdf57d",
    },
    {
        "key": "Suzuka", "session_key": 9496, "driver_number": 11,
        "path": "backend/cache/openf1_pistas_expand_1/location_9496_11.json",
        "sha256": "bf58f1a3b450c7bec4d994396096be62ee2c33a2a3a1b945c329f6a3280d2ff7",
    },
    {
        "key": "Suzuka", "session_key": 9496, "driver_number": 55,
        "path": "backend/cache/openf1_pistas_expand_1/location_9496_55.json",
        "sha256": "bb9947035b223763901839d723a67bbb87030687254b4c5eaea47465d7b5f7fc",
    },
    {
        "key": "Zandvoort", "session_key": 9582, "driver_number": 1,
        "path": "backend/cache/openf1_pistas_expand_1/location_9582_1.json",
        "sha256": "4b9798cf288e688f72987fffba6f64be108489c22c98a5a8d3e5b68545ad5721",
    },
    {
        "key": "Zandvoort", "session_key": 9582, "driver_number": 16,
        "path": "backend/cache/openf1_pistas_expand_1/location_9582_16.json",
        "sha256": "9829fc170b9012339b3a9fed6c15002432908b299a1dafcb88d4b2e1b827e50a",
    },
]


def _round(value, digits=12):
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), digits)


def _official_lengths():
    con = sqlite3.connect(str(BACKEND / "f1db.db"))
    try:
        result = {}
        for key, (circuit_id, expected) in OFFICIAL.items():
            rows = con.execute(
                "select course_length from race where circuit_id=? and year=2024",
                (circuit_id,),
            ).fetchall()
            if len(rows) != 1 or rows[0][0] is None:
                raise RuntimeError(f"f1db 2024 ambígua/ausente para {key}: {rows}")
            measured = float(rows[0][0]) * 1000.0
            if abs(measured - expected) > 1e-9:
                raise RuntimeError(f"f1db diverge do prereg para {key}: {measured}")
            result[key] = measured
        return result
    finally:
        con.close()


def _historical_inventory():
    manifest_path = BACKEND / "experiments/pistas-expand-1/manifest_pistas_expand_1.csv"
    with manifest_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 9:
        raise RuntimeError(f"manifest deveria conter 9 linhas; encontrado {len(rows)}")
    result = [dict(MONZA)]
    for row in rows:
        key = row["chave_case_exata"]
        match = re.search(r"#(\d+)", row["driver"])
        if not match:
            raise RuntimeError(f"número de piloto ausente no manifest: {row}")
        driver = int(match.group(1))
        session = int(row["session_key"])
        relative = f"backend/cache/openf1_pistas_expand_1/location_{session}_{driver}.json"
        result.append({
            "key": key,
            "session_key": session,
            "driver_number": driver,
            "path": relative,
            "sha256": HISTORICAL_SHAS[key],
            "published_delta_pct": (-0.9982 if key == "LasVegas"
                                    else float(row["delta_pct"])),
            "prior_status": row["status"],
        })
    if len({item["key"] for item in result}) != 10:
        raise RuntimeError("inventário histórico não tem 10 chaves únicas")
    return sorted(result, key=lambda item: item["key"])


def _raw_data(item):
    path = ROOT / item["path"]
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != item["sha256"]:
        raise RuntimeError(f"hash diverge do prereg: {item['path']} {digest}")
    samples = json.loads(raw)
    if not isinstance(samples, list):
        raise RuntimeError(f"stream não é uma lista JSON: {item['path']}")
    return raw, samples


def _raw_gates(samples):
    checks = {
        "min_raw_samples": len(samples) >= MIN_RAW_SAMPLES,
        "required_fields": True,
        "finite_xy": True,
        "date_parseable_with_timezone": True,
        "date_unique": True,
        "date_lexical_order_matches_utc": True,
        "positive_intervals": True,
        "speed_le_120_m_s": True,
    }
    failures = []
    if not checks["min_raw_samples"]:
        failures.append("menos de 100 amostras brutas")
    parsed = []
    lexical_dates = []
    xy = []
    for i, sample in enumerate(samples):
        if not all(k in sample for k in ("x", "y", "date")):
            checks["required_fields"] = False
            continue
        try:
            x, y = float(sample["x"]), float(sample["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                checks["finite_xy"] = False
            xy.append((x * UNIT_SCALE, y * UNIT_SCALE))
        except (TypeError, ValueError):
            checks["finite_xy"] = False
        try:
            stamp = datetime.fromisoformat(str(sample["date"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timestamp sem fuso")
            parsed.append(stamp.astimezone(timezone.utc))
            lexical_dates.append(str(sample["date"]))
        except (TypeError, ValueError):
            checks["date_parseable_with_timezone"] = False
    if not checks["required_fields"]:
        failures.append("x/y/date ausente")
    if not checks["finite_xy"]:
        failures.append("x/y não finito ou não numérico")
    if not checks["date_parseable_with_timezone"] or len(parsed) != len(samples):
        checks["date_parseable_with_timezone"] = False
        failures.append("date não parseável com fuso")
    if len(parsed) == len(samples):
        if len(set(parsed)) != len(parsed):
            checks["date_unique"] = False
            failures.append("date duplicada")
        utc_order = sorted(parsed)
        lexical_indices = sorted(range(len(lexical_dates)),
                                 key=lambda i: lexical_dates[i])
        lexical_utc_order = [parsed[i] for i in lexical_indices]
        if lexical_utc_order != utc_order:
            checks["date_lexical_order_matches_utc"] = False
            failures.append("ordenação lexical de date diverge da ordem UTC")
    if checks["required_fields"] and checks["finite_xy"] and len(xy) == len(samples) \
            and len(parsed) == len(samples) and checks["date_parseable_with_timezone"]:
        max_speed = 0.0
        lexical_indices = sorted(range(len(lexical_dates)),
                                 key=lambda i: lexical_dates[i])
        ordered_times = [parsed[i] for i in lexical_indices]
        ordered_xy = [xy[i] for i in lexical_indices]
        for i in range(1, len(samples)):
            dt = (ordered_times[i] - ordered_times[i - 1]).total_seconds()
            if dt <= 0:
                checks["positive_intervals"] = False
                continue
            dx = ordered_xy[i][0] - ordered_xy[i - 1][0]
            dy = ordered_xy[i][1] - ordered_xy[i - 1][1]
            max_speed = max(max_speed, math.hypot(dx, dy) / dt)
        if not checks["positive_intervals"]:
            failures.append("intervalo temporal não positivo")
        if max_speed > MAX_SPEED_M_S:
            checks["speed_le_120_m_s"] = False
            failures.append(f"velocidade máxima {max_speed:.6f} m/s > 120 m/s")
    else:
        max_speed = None
        checks["positive_intervals"] = False
        checks["speed_le_120_m_s"] = False
    checks["passed"] = all(checks.values())
    return checks, failures, max_speed


def _point_segment_distance(p, a, b):
    ab = b - a
    denom = float(np.dot(ab, ab))
    if denom == 0.0:
        return float(np.linalg.norm(p - a))
    t = max(0.0, min(1.0, float(np.dot(p - a, ab)) / denom))
    return float(np.linalg.norm(p - (a + t * ab)))


def _orientation(a, b, c):
    return float((b[0] - a[0]) * (c[1] - a[1])
                 - (b[1] - a[1]) * (c[0] - a[0]))


def _segments_intersect(a, b, c, d):
    o1, o2 = _orientation(a, b, c), _orientation(a, b, d)
    o3, o4 = _orientation(c, d, a), _orientation(c, d, b)
    return ((o1 > 0 and o2 < 0 or o1 < 0 and o2 > 0)
            and (o3 > 0 and o4 < 0 or o3 < 0 and o4 > 0))


def _segment_distance(a, b, c, d):
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(
        _point_segment_distance(a, c, d),
        _point_segment_distance(b, c, d),
        _point_segment_distance(c, a, b),
        _point_segment_distance(d, a, b),
    )


def _min_nonadjacent_distance(line):
    n = len(line)
    best = math.inf
    best_pair = None
    for i in range(n):
        a, b = line[i], line[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            distance = _segment_distance(a, b, line[j], line[(j + 1) % n])
            if distance < best:
                best, best_pair = distance, (i, j)
    return best, best_pair


def _geometry(item, samples, official_m):
    line = TGF.filter_race_line(samples)
    if line is None:
        return {"extracted": False, "passed": False,
                "failures": ["filter_race_line retornou None"]}
    line = np.asarray(line, dtype=np.float64)
    failures = []
    if line.ndim != 2 or line.shape[1] != 2:
        return {"extracted": True, "passed": False,
                "failures": [f"shape inválido {line.shape}"]}
    finite = bool(np.isfinite(line).all())
    if not finite:
        failures.append("waypoints não finitos")
    if len(line) < MIN_WAYPOINTS:
        failures.append(f"menos de {MIN_WAYPOINTS} waypoints")
    if len(line) < 3 or not finite:
        return {"extracted": True, "passed": False, "n_waypoints": len(line),
                "failures": failures or ["geometria insuficiente"]}

    closed = np.vstack([line, line[:1]])
    segments = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    length_m = float(segments.sum())
    bbox = line.max(axis=0) - line.min(axis=0)
    bbox_diag_m = float(np.linalg.norm(bbox))
    scale_ratio = bbox_diag_m / official_m
    closure_m = float(np.linalg.norm(line[-1] - line[0]))
    spacing_ok = bool(np.all(segments >= MIN_SEGMENT_M)
                      and np.all(segments <= MAX_SEGMENT_M))
    scale_ok = SCALE_RATIO_MIN <= scale_ratio <= SCALE_RATIO_MAX
    topology_min, topology_pair = _min_nonadjacent_distance(line)
    topology_ok = topology_min > TOPOLOGY_TOL_M
    if not scale_ok:
        failures.append("plausibilidade de escala fora de [0,05;0,50]")
    if not spacing_ok:
        failures.append("segmento (incluindo fechamento) fora de [5;15] m")
    if closure_m < MIN_SEGMENT_M or closure_m > MAX_SEGMENT_M:
        failures.append("fechamento fora de [5;15] m")
    if not topology_ok:
        failures.append("distância entre segmentos não adjacentes ≤0,1 m")
    return {
        "extracted": True,
        "passed": not failures,
        "n_waypoints": int(len(line)),
        "length_m": _round(length_m, 6),
        "official_length_m": official_m,
        "delta_pct": _round(100.0 * (length_m - official_m) / official_m, 9),
        "bbox_diagonal_m": _round(bbox_diag_m, 6),
        "bbox_to_official_ratio": _round(scale_ratio, 12),
        "closure_m": _round(closure_m, 9),
        "min_segment_m": _round(float(segments.min()), 9),
        "max_segment_m": _round(float(segments.max()), 9),
        "min_nonadjacent_segment_distance_m": _round(topology_min, 9),
        "min_distance_pair_indices": list(topology_pair) if topology_pair else None,
        "gates": {
            "unit_conversion_x_y_dm_to_m": True,
            "bbox_scale_plausibility": scale_ok,
            "finite_waypoints": finite,
            "min_waypoints": len(line) >= MIN_WAYPOINTS,
            "spacing_and_continuity": spacing_ok,
            "closure": MIN_SEGMENT_M <= closure_m <= MAX_SEGMENT_M,
            "simple_cycle": topology_ok,
        },
        "failures": failures,
    }


def _audit_item(item, official_m, *, report_delta):
    raw, samples = _raw_data(item)
    item_result = {
        "track_key": item["key"],
        "session_key": item["session_key"],
        "driver_number": item["driver_number"],
        "source_path": item["path"],
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_samples": len(samples),
        "official_length_m": official_m,
        "prior_status": item.get("prior_status"),
        "published_delta_pct": item.get("published_delta_pct"),
    }
    raw_checks, raw_failures, max_speed = _raw_gates(samples)
    item_result["raw_gates"] = raw_checks
    item_result["raw_max_speed_m_s"] = _round(max_speed, 9)
    # Continue all structural diagnostics after a raw-gate failure. The
    # prereg excludes such a track from calibration; it does not prohibit
    # measuring the remaining gates for the final audit.
    geometry = _geometry(item, samples, official_m)
    item_result.update(geometry)
    item_result["structural_pass"] = bool(raw_checks["passed"] and geometry["passed"])
    item_result["failures"] = raw_failures + geometry.get("failures", [])
    if report_delta and item_result["structural_pass"]:
        item_result["new_delta_pct"] = geometry["delta_pct"]
        item_result["delta_reportable"] = True
    else:
        item_result["new_delta_pct"] = None
        item_result["delta_reportable"] = False
        if report_delta:
            # Failed alternates do not receive a reported length/delta under
            # the frozen eligibility rule.
            item_result.pop("length_m", None)
            item_result.pop("delta_pct", None)
    return item_result


def _loo(historical_results):
    eligible = {
        item["track_key"]: float(item["published_delta_pct"])
        for item in historical_results if item["structural_pass"]
    }
    folds = []
    for key in sorted(eligible):
        fit = [value for track, value in eligible.items() if track != key]
        record = {"excluded_track": key, "fit_track_count": len(fit),
                  "observed_delta_pct": eligible[key]}
        if len(fit) < MIN_FIT_TRACKS:
            record.update({"valid": False, "passed": False,
                           "reason": "menos de cinco pistas de ajuste"})
        else:
            median = float(np.median(fit))
            mad = float(np.median(np.abs(np.asarray(fit) - median)))
            scale = 1.4826 * mad
            record.update({"median_pct": _round(median, 12),
                           "mad_pct": _round(mad, 12),
                           "robust_scale_pct": _round(scale, 12)})
            if scale <= EPSILON_PP or not math.isfinite(scale):
                record.update({"valid": False, "passed": False,
                               "reason": "dispersão nula/abaixo do epsilon"})
            else:
                low, high = median - LOO_MULTIPLIER * scale, median + LOO_MULTIPLIER * scale
                passed = low <= eligible[key] <= high
                record.update({"valid": True, "lower_pct": _round(low, 12),
                               "upper_pct": _round(high, 12), "passed": passed})
        folds.append(record)
    return {
        "eligible_track_count": len(eligible),
        "eligible_tracks": sorted(eligible),
        "folds": folds,
        "all_folds_valid": bool(folds) and all(x["valid"] for x in folds),
        "all_folds_pass": bool(folds) and all(x["valid"] and x["passed"] for x in folds),
        "epsilon_pp": EPSILON_PP,
        "multiplier": LOO_MULTIPLIER,
        "minimum_fit_tracks": MIN_FIT_TRACKS,
    }


def main():
    params = inspect.signature(TGF.filter_race_line).parameters
    expected_defaults = {
        "min_step_m": MIN_STEP_M,
        "cell_m": CELL_M,
        "resample_m": RESAMPLE_M,
        "unit_scale": UNIT_SCALE,
    }
    for name, expected in expected_defaults.items():
        if params[name].default != expected:
            raise RuntimeError(f"parâmetro v4 diverge do prereg: {name}")

    official = _official_lengths()
    historical = []
    for item in _historical_inventory():
        historical.append(_audit_item(item, official[item["key"]], report_delta=False))

    loo = _loo(historical)
    alternates = []
    for item in ALTERNATES:
        alternates.append(_audit_item(item, official[item["key"]], report_delta=True))

    out = {
        "prereg_commit": PREREG_COMMIT,
        "method": "track_geometry_free.filter_race_line v4",
        "network_calls": 0,
        "simulations": 0,
        "frozen_path_writes": 0,
        "historical_tracks": historical,
        "loo": loo,
        "alternate_driver_streams": alternates,
        "counts": {
            "historical_streams_attempted": len(historical),
            "historical_v4_extractions": sum(bool(x.get("extracted")) for x in historical),
            "historical_structural_pass": sum(bool(x.get("structural_pass")) for x in historical),
            "alternate_streams_attempted": len(alternates),
            "alternate_v4_extractions": sum(bool(x.get("extracted")) for x in alternates),
            "alternate_structural_pass": sum(bool(x.get("structural_pass")) for x in alternates),
            "alternate_new_deltas_reported": sum(bool(x.get("delta_reportable")) for x in alternates),
        },
        "holdout_independent_tracks": 0,
        "decision": "RAMO_2_REPORT_ONLY",
        "decision_reason": "não há holdout independente por pista no escopo congelado",
    }
    output = BACKEND / "experiments/gate-re-derive-1/audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out["counts"], ensure_ascii=False, sort_keys=True))
    print(json.dumps({"loo_all_folds_valid": loo["all_folds_valid"],
                      "loo_all_folds_pass": loo["all_folds_pass"],
                      "eligible_tracks": loo["eligible_tracks"],
                      "holdout_independent_tracks": 0,
                      "decision": out["decision"]}, ensure_ascii=False, sort_keys=True))
    for item in alternates:
        print(json.dumps({"track": item["track_key"],
                          "driver": item["driver_number"],
                          "extracted": item.get("extracted", False),
                          "structural_pass": item.get("structural_pass", False),
                          "delta_reportable": item.get("delta_reportable", False),
                          "new_delta_pct": item.get("new_delta_pct"),
                          "failures": item.get("failures", [])},
                         ensure_ascii=False, sort_keys=True))
    print(f"audit={output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
