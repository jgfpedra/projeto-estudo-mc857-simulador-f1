#!/usr/bin/env python3
"""PASS-DIAG-2 v1.5 frozen report-only analysis. Does not run simulations."""

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
import ast
import csv
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

VERSION = "1.5"
ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
OUT = ROOT / "experiments/pass-1/autopsia"
INPUTS = {
    "R1_CSV": ("experiments/pass-1/1_R1_OFF.csv", "5cb49097fea9bb066e9bef5ae62f4ee7c6f9ceb70485448792d33b533ce5cdaa"),
    "R2_CSV": ("experiments/pass-1/2_R2_ON.csv", "7d2c49b9b873fc4fc4888b1413cd47ae3b9dde040a4e1af111ac246c90e0a27c"),
    "R1_LOG": ("experiments/pass-1/1_R1_OFF.log", "f23a79771bd9f05d8e709f9bf67a93be8a93bf2e8129403db03972b0c0c23273"),
    "R2_LOG": ("experiments/pass-1/2_R2_ON.log", "213fb953c98e59a51e2178a9f05171560dd63ed15f675fcf6c2a86b33c783f1b"),
    "AUDIT": ("experiments/pass-1/4_AUDIT_PASS_1.json", "347216e6cf65f109ec82d927762bab5ffefea85c4913fca024891bf05e1a134b"),
    "EXECUCAO": ("experiments/pass-1/5_EXECUCAO_PASS_1.md", "e4f6ac05383d481c862cf679edac171547ccbde81c44557ecd2072f295281a67"),
    "GEOMETRY": ("model_train/tracks_frozen/interlagos_v2.json", "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613"),
}
GEOMETRY_COMMIT = "8136d54ec45f9f49b38a5893a812928474109535"
PREREG_REL = "backend/experiments/pass-1/autopsia/PREREG_PASS_DIAG_1B.md"
SCRIPT_REL = "backend/scripts/experiments/passing/pass_1_diag.py"
EXPECTED_COLUMNS = 54
REQUIRED_COLUMNS = {
    "tick", "t_s", "drv", "speed", "s", "lat", "car_car",
    "offtrack", "cum_dist", "authority", "p_state",
}
EXPECTED_ROWS = 30000
EXPECTED_DRIVERS = 10
EXPECTED_ROWS_PER_DRIVER = 3000
TRACK_BINS_M = 10.0
CONTACT_BIN_S = 5.0
ATTEMPT_LIMIT = 5
KNOWN_NET_SWAPS = 17
TRACK_LENGTH_PUBLISHED_M = 4160.436950117386
OUTPUT_NAMES = (
    "1_Q0_TENTATIVAS.csv", "2_Q0_INVERSOES.csv", "3_PACE_CURVATURA.csv",
    "4_REENTRADA_CONTATOS.csv", "5_PRIMEIRA_VOLTA.csv", "6_RESUMO.json",
)
START_EVENTS = {
    "start", "begin", "engage", "engaged", "active", "attempt_start",
    "start_attempt", "attempt_started", "activate",
}
END_EVENTS = {
    "abort", "aborted", "end", "exit", "finish", "finished", "complete",
    "completed", "consume", "consumed", "attempt_end", "attempt_finished",
    "deactivate", "release",
}


class Pare(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_blobs(commit: str) -> None:
    for rel in (PREREG_REL, SCRIPT_REL):
        disk = (REPO / rel).read_bytes()
        proc = subprocess.run(
            ["git", "show", f"{commit}:{rel}"],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if proc.returncode != 0 or proc.stdout != disk:
            raise Pare("freeze blob mismatch")
    geometry_rel = "backend/model_train/tracks_frozen/interlagos_v2.json"
    geometry = subprocess.run(
        ["git", "show", f"{GEOMETRY_COMMIT}:{geometry_rel}"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if geometry.returncode != 0 or hashlib.sha256(geometry.stdout).hexdigest() != INPUTS["GEOMETRY"][1]:
        raise Pare("geometry Git provenance mismatch")
    print("FREEZE PASS: prereg and script blobs match the supplied commit")


def verify_input_hashes() -> None:
    for role, (rel, expected) in INPUTS.items():
        path = ROOT / rel
        if not path.is_file() or sha256(path) != expected:
            raise Pare(f"source hash mismatch: {role}")
    print("SOURCE HASHES PASS: all pinned files match")


def _data_lines(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        first = f.readline()
        while first.startswith("#"):
            first = f.readline()
        if not first:
            raise Pare("empty CSV")
        yield first
        yield from f


def load_csv(role: str) -> tuple[list[str], list[dict[str, Any]]]:
    path = ROOT / INPUTS[role][0]
    reader = csv.DictReader(_data_lines(path))
    fields = reader.fieldnames or []
    if len(fields) != EXPECTED_COLUMNS or len(set(fields)) != len(fields) or not REQUIRED_COLUMNS.issubset(fields):
        print(f"SCHEMA FAIL {role}: fields={','.join(fields)}")
        raise Pare(f"schema mismatch: {role}")
    rows = list(reader)
    print(f"SCHEMA PASS {role}: fields={','.join(fields)}")
    if len(rows) != EXPECTED_ROWS:
        raise Pare(f"row-count schema mismatch: {role}")
    parsed: list[dict[str, Any]] = []
    try:
        for row in rows:
            parsed.append({
                **row,
                "tick": int(row["tick"]),
                "t_s": float(row["t_s"]),
                "drv": str(row["drv"]),
                "speed": float(row["speed"]),
                "s": float(row["s"]),
                "lat": float(row["lat"]),
                "car_car": float(row["car_car"]),
                "offtrack": int(float(row["offtrack"])),
                "cum_dist": float(row["cum_dist"]),
                "authority": str(row["authority"]),
                "p_state": str(row["p_state"]),
            })
    except (ValueError, TypeError, KeyError):
        raise Pare(f"numeric/schema conversion failed: {role}") from None
    by_driver: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in parsed:
        by_driver[row["drv"]].append(row)
    if len(by_driver) != EXPECTED_DRIVERS or any(len(v) != EXPECTED_ROWS_PER_DRIVER for v in by_driver.values()):
        raise Pare(f"driver-count schema mismatch: {role}")
    expected_ticks = list(range(0, 6000, 2))
    for group in by_driver.values():
        group.sort(key=lambda x: x["tick"])
        if [r["tick"] for r in group] != expected_ticks:
            raise Pare(f"tick-grid schema mismatch: {role}")
        for row in group:
            if not math.isfinite(row["t_s"]) or abs(row["t_s"] - row["tick"] / 10.0) > 1e-6:
                raise Pare(f"time-grid schema mismatch: {role}")
    return fields, parsed


def _audit_r2_records(attempts_by_run: Any) -> list[dict[str, Any]]:
    if not isinstance(attempts_by_run, dict) or set(attempts_by_run) != {"R2"}:
        raise Pare("audit pass_decision_attempts must be a dict containing only R2")
    records = attempts_by_run["R2"]
    if not isinstance(records, list) or len(records) != ATTEMPT_LIMIT:
        raise Pare("audit R2 attempt list differs from frozen declaration")
    required = {"driver_id", "target_id", "start_s", "end_s", "outcome"}
    for record in records:
        if not isinstance(record, dict) or set(record) != required:
            raise Pare("audit attempt record keys differ from frozen schema census")
        if not isinstance(record["driver_id"], str) or not record["driver_id"].strip():
            raise Pare("audit attempt driver_id schema invalid")
        if type(record["target_id"]) not in (str, int) or not str(record["target_id"]).strip():
            raise Pare("audit attempt target_id schema invalid")
        if not isinstance(record["outcome"], str):
            raise Pare("audit attempt outcome schema invalid")
        for key in ("start_s", "end_s"):
            value = record[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise Pare(f"audit attempt {key} schema invalid")
    return records


def validate_audit_schema() -> None:
    path = ROOT / INPUTS["AUDIT"][0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise Pare("audit JSON schema invalid") from None
    if not isinstance(data, dict) or "pass_decision_attempts" not in data:
        raise Pare("audit JSON schema missing required field name")
    _audit_r2_records(data["pass_decision_attempts"])
    print("AUDIT SCHEMA PASS: pass_decision_attempts is {R2: list}; record fields match frozen census")


def _norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value).strip().strip("\"'")


def _record_from_log_line(line: str) -> dict[str, str] | None:
    marker = "[pass-decision]"
    if marker not in line:
        return None
    payload = line.split(marker, 1)[1].strip()
    obj: dict[str, Any] = {}
    brace = payload.find("{")
    if brace >= 0:
        try:
            candidate, _ = json.JSONDecoder().raw_decode(payload[brace:])
            if isinstance(candidate, dict):
                obj.update(candidate)
        except json.JSONDecodeError:
            pass
    if not obj:
        for match in re.finditer(
            r"([A-Za-z][A-Za-z0-9_.-]*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^,\s]+)",
            payload,
        ):
            obj[match.group(1)] = match.group(2)
    out = {_norm_key(k): _text(v) for k, v in obj.items()}
    first = re.match(r"\s*([A-Za-z_-]+)", payload)
    if first:
        out.setdefault("token_event", _norm_key(first.group(1)))
    return out


def _pick(record: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for key in aliases:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _tick_value(record: dict[str, str], prefix: str) -> int | None:
    aliases = (
        f"{prefix}_tick", f"tick_{prefix}",
        "tick" if prefix == "start" else "end_tick",
        f"{prefix}_t_s", f"{prefix}_time_s", f"t_{prefix}_s",
    )
    value = _pick(record, aliases)
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    time_keys = {f"{prefix}_t_s", f"{prefix}_time_s", f"t_{prefix}_s"}
    if any(record.get(key) is not None for key in time_keys):
        number *= 10.0
    return int(round(number / 2.0) * 2)


def _event(record: dict[str, str]) -> str:
    raw = _pick(record, ("event", "action", "phase", "state", "status", "result", "token_event")) or ""
    event = _norm_key(raw)
    known = START_EVENTS | END_EVENTS
    if event in known:
        return event
    for candidate in sorted(known, key=len, reverse=True):
        if candidate in event:
            return candidate
    reason = _norm_key(_pick(record, ("reason", "abort_reason", "outcome")) or "")
    if "gap" in reason:
        return "abort_gap"
    if "timeout" in reason or "time" == reason:
        return "abort_timeout"
    if "contact" in reason or "solver" in reason:
        return "abort_contact"
    return ""


def _terminal_outcome(record: dict[str, str], event: str) -> str:
    raw = _norm_key(_pick(record, ("outcome", "reason", "abort_reason")) or event)
    if "gap" in raw:
        return "ABORT-GAP"
    if "timeout" in raw or raw == "time":
        return "ABORT-TIMEOUT"
    if "contact" in raw or "solver" in raw:
        return "ABORT-CONTATO"
    if raw in {"consume", "consumed", "complete", "completed", "finish", "finished"}:
        return "LOG-COMPLETE"
    return "UNKNOWN"


def _canonical_outcome(value: Any) -> str:
    if not isinstance(value, str):
        raise Pare("attempt outcome schema invalid")
    outcome = _norm_key(value)
    aliases = {
        "abort_gap": "abort_gap", "aborted_gap": "abort_gap", "gap": "abort_gap",
        "abort_timeout": "abort_timeout", "aborted_timeout": "abort_timeout", "timeout": "abort_timeout",
        "abort_contact": "abort_contact", "aborted_contact": "abort_contact", "contact": "abort_contact",
        "aborted_rejoin": "aborted_rejoin", "abort_rejoin": "aborted_rejoin",
        "aborted_target": "aborted_target", "abort_target": "aborted_target",
        "consumed": "consumed", "consume": "consumed",
    }
    if outcome not in aliases:
        raise Pare("unrecognized attempt outcome schema")
    return aliases[outcome]


def _tick_from_time(value: Any, is_tick: bool = False) -> int:
    if isinstance(value, bool):
        raise Pare("attempt time schema invalid")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise Pare("attempt time schema invalid") from None
    if not math.isfinite(number):
        raise Pare("attempt time schema invalid")
    scaled = number if is_tick else number * 10.0
    tick = int(round(scaled))
    if tick < 0 or tick > 5999 or abs(scaled - tick) > 1e-3:
        raise Pare("attempt time is off the frozen 0.1 s logical grid")
    return tick


def _sample_bounds(start_tick: int, end_tick: int, sample_ticks: list[int]) -> dict[str, Any]:
    """Map logical 0.1 s ticks to first/last inclusive 5 Hz CSV data rows."""
    if sample_ticks != sorted(set(sample_ticks)):
        raise Pare("CSV sample ticks are not unique and increasing")
    start_index = next((i for i, tick in enumerate(sample_ticks) if tick >= start_tick), len(sample_ticks))
    end_index = next((i for i in range(len(sample_ticks) - 1, -1, -1) if sample_ticks[i] <= end_tick), -1)
    estimable = start_index < end_index
    return {
        "estimable": estimable,
        "start_index": start_index if start_index < len(sample_ticks) else None,
        "end_index": end_index if end_index >= 0 else None,
        "sample_start_tick": sample_ticks[start_index] if start_index < len(sample_ticks) else None,
        "sample_end_tick": sample_ticks[end_index] if end_index >= 0 else None,
    }


def _field_value(record: dict[str, Any], aliases: tuple[str, ...], label: str) -> tuple[Any, str]:
    found = [(key, record[key]) for key in aliases if key in record]
    if not found:
        raise Pare(f"audit attempt schema missing {label} field")
    first = found[0][1]
    if any(value != first for _, value in found[1:]):
        raise Pare(f"audit attempt schema has conflicting {label} fields")
    return first, found[0][0]


def _attempt_time_tick(record: dict[str, Any], stem: str) -> int:
    tick_aliases = (f"{stem}_tick", f"tick_{stem}")
    seconds_aliases = (f"{stem}_s", f"{stem}_t_s", f"{stem}_time_s", f"t_{stem}_s")
    converted = []
    for alias in tick_aliases:
        if alias in record:
            converted.append(_tick_from_time(record[alias], is_tick=True))
    for alias in seconds_aliases:
        if alias in record:
            converted.append(_tick_from_time(record[alias], is_tick=False))
    if not converted:
        raise Pare(f"audit attempt schema missing {stem} time field")
    if len(set(converted)) != 1:
        raise Pare(f"audit attempt schema has conflicting {stem} time fields")
    return converted[0]


def _attempt_signature(record: dict[str, Any], driver: Any = None) -> tuple[str, str, int, int, str]:
    if not isinstance(record, dict):
        raise Pare("attempt record schema invalid")
    if driver is None:
        driver, _ = _field_value(record, ("driver", "ego", "drv", "pilot"), "driver")
    target, _ = _field_value(record, ("target_id", "target", "target_driver", "target_car"), "target")
    start_tick = _attempt_time_tick(record, "start")
    end_tick = _attempt_time_tick(record, "end")
    outcome, _ = _field_value(record, ("outcome", "logged_outcome", "reason", "abort_reason", "status"), "outcome")
    driver_key, target_key = _norm_key(driver), _norm_key(target)
    if not driver_key or not target_key or end_tick < start_tick:
        raise Pare("attempt identity or interval invalid")
    return driver_key, target_key, start_tick, end_tick, _canonical_outcome(outcome)


def _parse_summary_lines(lines: list[str], audit_attempts_by_run: dict[str, Any]) -> list[dict[str, Any]]:
    summary_keys = {
        "opportunities", "engaged", "aborted_gap", "aborted_timeout", "aborted_contact",
        "aborted_rejoin", "aborted_target", "consumed", "attempts", "active_attempt",
    }
    attempt_keys = {"target_id", "start_s", "end_s", "outcome"}
    summaries: dict[str, dict[str, Any]] = {}
    completed: list[dict[str, Any]] = []
    log_join_records: list[dict[str, Any]] = []
    for raw_line in lines:
        if "[pass-decision]" not in raw_line:
            continue
        line = raw_line.rstrip("\r\n")
        match = re.fullmatch(r"\[pass-decision\]\s+([^:]+):\s*(\{.*\})\s*", line)
        if not match:
            raise Pare("line format not predicted by census")
        driver = match.group(1).strip()
        driver_key = _norm_key(driver)
        if not driver_key or driver_key in summaries:
            raise Pare("duplicate or empty summary driver")
        try:
            summary = ast.literal_eval(match.group(2))
        except (SyntaxError, ValueError):
            raise Pare("summary dict literal invalid") from None
        if not isinstance(summary, dict) or set(summary) != summary_keys:
            raise Pare("summary dict schema differs from censused keys")
        if not isinstance(summary["attempts"], list):
            raise Pare("summary attempts field is not a list")
        for key in summary_keys - {"attempts", "active_attempt"}:
            if type(summary[key]) is not int or summary[key] < 0:
                raise Pare("summary counter schema invalid")
        summaries[driver_key] = summary
        for index, item in enumerate(summary["attempts"]):
            if not isinstance(item, dict) or set(item) != attempt_keys:
                raise Pare("attempt item schema differs from censused keys")
            if not isinstance(item["target_id"], (str, int)) or not str(item["target_id"]).strip():
                raise Pare("attempt target identifier invalid")
            signature = _attempt_signature(item, driver=driver)
            _, target_key, start_tick, end_tick, outcome = signature
            if not isinstance(item["outcome"], str):
                raise Pare("log attempt outcome schema invalid")
            log_join_records.append({
                "driver_id": driver,
                "target_id": item["target_id"],
                "start_s": float(item["start_s"]),
                "end_s": float(item["end_s"]),
                "outcome": item["outcome"],
            })
            completed.append({
                "driver": driver, "target": str(item["target_id"]),
                "attempt_id": f"{driver}:{item['target_id']}:{start_tick}:{index}",
                "start_tick": start_tick, "end_tick": end_tick,
                "logged_outcome": outcome,
            })
    if len(summaries) != EXPECTED_DRIVERS:
        raise Pare("summary driver count differs from frozen schema")
    if len(completed) != ATTEMPT_LIMIT:
        raise Pare("attempt count differs from frozen declaration")
    audit_records = _audit_r2_records(audit_attempts_by_run)
    if len(log_join_records) != len(audit_records) or len(log_join_records) != ATTEMPT_LIMIT:
        raise Pare("log/audit attempt join is not 5-to-5")
    matched_audit_indices: set[int] = set()
    for log_record in log_join_records:
        matches = []
        for index, audit_record in enumerate(audit_records):
            same_target = (
                type(audit_record["target_id"]) is type(log_record["target_id"])
                and audit_record["target_id"] == log_record["target_id"]
            )
            if (
                audit_record["driver_id"] == log_record["driver_id"]
                and same_target
                and abs(float(audit_record["start_s"]) - log_record["start_s"]) <= 1e-6
                and abs(float(audit_record["end_s"]) - log_record["end_s"]) <= 1e-6
                and audit_record["outcome"] == log_record["outcome"]
            ):
                matches.append(index)
        if len(matches) != 1 or matches[0] in matched_audit_indices:
            raise Pare("log/audit attempt join is not bijective")
        matched_audit_indices.add(matches[0])
    if len(matched_audit_indices) != len(audit_records):
        raise Pare("log/audit attempt join left unmatched audit records")
    print("ATTEMPT JOIN PASS: 5 log attempts bijectively matched to audit R2")
    return sorted(completed, key=lambda a: (a["start_tick"], str(a["driver"]), str(a["target"])))


def parse_attempts(log_path: Path) -> list[dict[str, Any]]:
    try:
        with log_path.open("r", encoding="utf-8", errors="strict") as source:
            lines = source.readlines()
        audit = json.loads((ROOT / INPUTS["AUDIT"][0]).read_text(encoding="utf-8"))
    except Exception:
        raise Pare("log or audit input could not be read") from None
    if not isinstance(audit, dict) or "pass_decision_attempts" not in audit:
        raise Pare("audit JSON missing pass_decision_attempts field")
    return _parse_summary_lines(lines, audit["pass_decision_attempts"])


def _driver_match(wanted: str, by_driver: dict[str, list[dict[str, Any]]]) -> str:
    normalized = _norm_key(wanted)
    matches = [
        driver for driver in by_driver
        if _norm_key(driver) == normalized
        or _norm_key(driver).endswith(normalized)
        or normalized.endswith(_norm_key(driver))
    ]
    if len(matches) != 1:
        raise Pare("pilot identifier does not map uniquely to CSV schema")
    return matches[0]


def _wrap_signed(delta: float, length: float) -> float:
    return ((delta + length / 2.0) % length) - length / 2.0


def _geometry() -> tuple[list[tuple[float, float]], list[float], float]:
    path = ROOT / INPUTS["GEOMETRY"][0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        points = [(float(point[0]), float(point[1])) for point in data["waypoints"]]
    except Exception:
        raise Pare("geometry schema invalid") from None
    if len(points) < 3:
        raise Pare("geometry has fewer than three waypoints")
    cumulative = [0.0]
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        cumulative.append(cumulative[-1] + math.hypot(next_point[0] - point[0], next_point[1] - point[1]))
    length = cumulative[-1]
    if abs(length - TRACK_LENGTH_PUBLISHED_M) > 0.01:
        raise Pare("geometry length mismatch")
    return points, cumulative, length


def _curvature(s: float, points: list[tuple[float, float]], cumulative: list[float], length: float) -> float:
    position = s % length
    index = min(
        range(len(points)),
        key=lambda i: min(abs(cumulative[i] - position), length - abs(cumulative[i] - position)),
    )
    a, b, c = points[(index - 1) % len(points)], points[index], points[(index + 1) % len(points)]
    ab = math.hypot(b[0] - a[0], b[1] - a[1])
    bc = math.hypot(c[0] - b[0], c[1] - b[1])
    ca = math.hypot(a[0] - c[0], a[1] - c[1])
    if min(ab, bc, ca) <= 1e-9:
        return 0.0
    cross = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    return 2.0 * cross / (ab * bc * ca)


def _profile(r1_by_driver: dict[str, list[dict[str, Any]]], length: float) -> tuple[list[float], list[int]]:
    count = math.ceil(length / TRACK_BINS_M)
    buckets: list[list[float]] = [[] for _ in range(count)]
    for rows in r1_by_driver.values():
        for row in rows:
            speed = row["speed"]
            if row["t_s"] >= 60.0 and row["offtrack"] == 0 and math.isfinite(speed) and speed > 0.0:
                index = min(count - 1, int((row["s"] % length) / (length / count)))
                buckets[index].append(speed)
    centers = [(i + 0.5) * length / count for i in range(count)]
    filled = [i for i, bucket in enumerate(buckets) if bucket]
    if not filled:
        raise Pare("empirical R1 pace profile has no populated bins")
    profile = [statistics.median(bucket) if bucket else math.nan for bucket in buckets]
    if len(filled) == 1:
        return [profile[filled[0]]] * count, filled
    for index in range(count):
        if math.isfinite(profile[index]):
            continue
        previous = max((i for i in filled if i < index), default=filled[-1] - count)
        following = min((i for i in filled if i > index), default=filled[0] + count)
        left, right = previous % count, following % count
        x = centers[index]
        x_left, x_right = centers[left], centers[right]
        if previous < 0:
            x_left -= length
        if following >= count:
            x_right += length
        if x < x_left:
            x += length
        ratio = (x - x_left) / (x_right - x_left)
        profile[index] = profile[left] + ratio * (profile[right] - profile[left])
    return profile, filled


def _vref(s: float, profile: list[float], length: float) -> float:
    count = len(profile)
    position = (s % length) / (length / count) - 0.5
    left_floor = math.floor(position)
    fraction = position - left_floor
    left, right = left_floor % count, (left_floor + 1) % count
    return profile[left] * (1.0 - fraction) + profile[right] * fraction


def _rows_by_driver(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[row["drv"]].append(row)
    for group in result.values():
        group.sort(key=lambda row: row["tick"])
    return result


def _attempt_metrics(
    attempts: list[dict[str, Any]],
    r2_by_driver: dict[str, list[dict[str, Any]]],
    profile: list[float],
    points: list[tuple[float, float]],
    cumulative: list[float],
    length: float,
) -> list[dict[str, Any]]:
    result = []
    for attempt in attempts:
        ego_rows = {row["tick"]: row for row in r2_by_driver[attempt["ego_csv"]]}
        target_rows = {row["tick"]: row for row in r2_by_driver[attempt["target_csv"]]}
        common_ticks = sorted(set(ego_rows) & set(target_rows))
        bounds = _sample_bounds(attempt["start_tick"], attempt["end_tick"], common_ticks)
        if not bounds["estimable"]:
            result.append({
                **attempt,
                **{key: value for key, value in bounds.items() if key not in {"start_index", "end_index"}},
                "outcome": "NÃO ESTIMÁVEL",
                "duration_s": (attempt["end_tick"] - attempt["start_tick"]) / 10.0,
                "min_gap_m": None,
                "lateral_progress_m": None,
                "pace_cost_s": None,
                "kappa_inv_m": None,
                "kappa_band": "não estimável",
                "near_consume": None,
            })
            continue
        ticks = common_ticks[bounds["start_index"]:bounds["end_index"] + 1]
        ego = [ego_rows[t] for t in ticks]
        target = [target_rows[t] for t in ticks]
        relative = [e["cum_dist"] - t["cum_dist"] for e, t in zip(ego, target)]
        completed_pass = relative[0] <= 0.0 and any(
            min(relative[i:i + 5]) > 0.0
            for i in range(max(0, len(relative) - 4))
        )
        consumed = relative[0] < 0.0 and max(relative) >= 10.0
        logged = _norm_key(attempt.get("logged_outcome", ""))
        if logged == "aborted_rejoin":
            outcome = "ABORT-CARVEOUT-REJOIN"
        elif logged == "aborted_target":
            outcome = "ABORT-CARVEOUT-TARGET"
        elif consumed:
            outcome = "CONSUMIDA"
        elif completed_pass:
            outcome = "TROCA-SEM-CONSUMO"
        elif "gap" in logged:
            outcome = "ABORT-GAP"
        elif "timeout" in logged or logged == "time":
            outcome = "ABORT-TIMEOUT"
        elif "contact" in logged or "solver" in logged:
            outcome = "ABORT-CONTATO"
        else:
            raise Pare("attempt outcome could not be classified")
        actual_s = expected_s = 0.0
        for previous, current in zip(ego, ego[1:]):
            distance = current["cum_dist"] - previous["cum_dist"]
            elapsed = current["t_s"] - previous["t_s"]
            if distance < 0.0 or elapsed <= 0.0:
                raise Pare("invalid odometer progression inside attempt")
            reference_speed = _vref((previous["s"] + current["s"]) / 2.0, profile, length)
            if reference_speed <= 0.0:
                raise Pare("invalid empirical R1 pace profile")
            actual_s += elapsed
            expected_s += distance / reference_speed
        kappa = _curvature(ego[0]["s"], points, cumulative, length)
        band = "<0.02" if kappa < 0.02 else "0.02-0.06" if kappa <= 0.06 else ">0.06"
        lateral_progress = max(abs(row["lat"] - ego[0]["lat"]) for row in ego)
        min_gap = min(abs(_wrap_signed(t["s"] - e["s"], length)) for e, t in zip(ego, target))
        duration = (attempt["end_tick"] - attempt["start_tick"]) / 10.0
        result.append({
            **attempt,
            **{key: value for key, value in bounds.items() if key not in {"start_index", "end_index"}},
            "outcome": outcome,
            "duration_s": duration,
            "min_gap_m": min_gap,
            "lateral_progress_m": lateral_progress,
            "pace_cost_s": actual_s - expected_s,
            "kappa_inv_m": kappa,
            "kappa_band": band,
            "near_consume": outcome in {"ABORT-GAP", "ABORT-TIMEOUT", "ABORT-CONTATO"}
            and lateral_progress >= 0.5 and min_gap >= 8.0,
        })
    return result


def _pace_union_cost(
    attempts: list[dict[str, Any]],
    r2_by_driver: dict[str, list[dict[str, Any]]],
    profile: list[float],
    length: float,
) -> float | None:
    total = 0.0
    by_ego: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for attempt in attempts:
        if attempt.get("estimable", True) and attempt.get("sample_start_tick") is not None:
            by_ego[attempt["ego_csv"]].append((attempt["sample_start_tick"], attempt["sample_end_tick"]))
    if not by_ego:
        return None
    for driver, spans in by_ego.items():
        merged: list[list[int]] = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        by_tick = {row["tick"]: row for row in r2_by_driver[driver]}
        for start, end in merged:
            seq = [by_tick[t] for t in range(start, end + 1, 2) if t in by_tick]
            for previous, current in zip(seq, seq[1:]):
                distance = current["cum_dist"] - previous["cum_dist"]
                reference = _vref((previous["s"] + current["s"]) / 2.0, profile, length)
                if distance < 0.0 or reference <= 0.0:
                    raise Pare("invalid pace union interval")
                total += (current["t_s"] - previous["t_s"]) - distance / reference
    return total


def _contact_windows(rows_by_driver: dict[str, list[dict[str, Any]]]) -> dict[str, list[tuple[float, float]]]:
    result = {}
    for driver, rows in rows_by_driver.items():
        flagged = [
            row["offtrack"] == 1 or "rejoin" in row["authority"].lower()
            for row in rows
        ]
        windows = []
        index = 0
        while index < len(rows):
            if not flagged[index]:
                index += 1
                continue
            end = index + 1
            while end < len(rows) and flagged[end]:
                end += 1
            if end < len(rows):
                start_s = rows[end]["t_s"]
                windows.append((start_s, start_s + 10.0))
            index = end
        merged: list[list[float]] = []
        for start_s, end_s in sorted(windows):
            if merged and start_s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end_s)
            else:
                merged.append([start_s, end_s])
        result[driver] = [(a, b) for a, b in merged]
    return result


def _active_for_driver(driver: str, tick: int, attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        attempt for attempt in attempts
        if attempt["start_tick"] <= tick <= attempt["end_tick"]
        and driver in (attempt["ego_csv"], attempt["target_csv"])
    ]


def _rejoin_rows(
    rows_by_driver: dict[str, list[dict[str, Any]]],
    windows: dict[str, list[tuple[float, float]]],
    attempts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    all_attempts = sorted(attempts, key=lambda a: a["start_tick"])
    for driver, rows in rows_by_driver.items():
        for index, (start_s, end_s) in enumerate(windows[driver], 1):
            selected = [row for row in rows if start_s <= row["t_s"] <= end_s]
            total = sum(row["car_car"] for row in selected)
            participant = sum(
                row["car_car"] for row in selected
                if _active_for_driver(driver, row["tick"], attempts)
            )
            nearest = min(
                all_attempts,
                key=lambda a: min(abs(start_s * 10 - a["start_tick"]), abs(start_s * 10 - a["end_tick"])),
                default=None,
            )
            lag_s = None
            if nearest is not None:
                boundary = nearest["start_tick"] if start_s * 10 < nearest["start_tick"] else nearest["end_tick"]
                lag_s = (start_s * 10 - boundary) / 10.0
            output.append({
                "driver": driver, "window_index": index, "reentry_t_s": start_s,
                "window_end_t_s": end_s, "contact_count": total,
                "attempt_participant_contact_count": participant,
                "field_contact_count_proxy": total - participant,
                "active_attempt_samples": sum(
                    bool(_active_for_driver(driver, row["tick"], attempts)) for row in selected
                ),
                "nearest_attempt_id": None if nearest is None else nearest.get("attempt_id"),
                "nearest_attempt_outcome": None if nearest is None else nearest.get("outcome"),
                "nearest_attempt_lag_s": lag_s,
            })
    return output


def _first_lap_timeline(
    rows_by_driver: dict[str, list[dict[str, Any]]],
    attempts: list[dict[str, Any]],
    length: float,
) -> list[dict[str, Any]]:
    bins: dict[tuple[str, int], dict[str, Any]] = defaultdict(
        lambda: {"contact_count": 0.0, "contact_rows": 0, "attempt_active_contact_count": 0.0}
    )
    for driver, rows in rows_by_driver.items():
        for row in rows:
            if row["cum_dist"] >= length:
                continue
            key = (driver, int(row["t_s"] // CONTACT_BIN_S))
            bins[key]["contact_count"] += row["car_car"]
            bins[key]["contact_rows"] += int(row["car_car"] > 0)
            if _active_for_driver(driver, row["tick"], attempts):
                bins[key]["attempt_active_contact_count"] += row["car_car"]
    return [
        {
            "driver": driver,
            "time_start_s": bin_index * CONTACT_BIN_S,
            "time_end_s": (bin_index + 1) * CONTACT_BIN_S,
            **values,
        }
        for (driver, bin_index), values in sorted(bins.items())
    ]


def _swaps(
    rows_by_driver: dict[str, list[dict[str, Any]]],
    attempts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    drivers = sorted(rows_by_driver)
    by_tick = {
        driver: {row["tick"]: row for row in rows_by_driver[driver]}
        for driver in drivers
    }
    common_ticks = sorted(set.intersection(*(set(by_tick[d]) for d in drivers)))
    state: dict[tuple[str, str], int] = {}
    for i, driver_a in enumerate(drivers):
        for driver_b in drivers[i + 1:]:
            delta = by_tick[driver_a][common_ticks[0]]["cum_dist"] - by_tick[driver_b][common_ticks[0]]["cum_dist"]
            state[(driver_a, driver_b)] = 1 if delta >= 10.0 else -1 if delta <= -10.0 else 0
    events = []
    for tick in common_ticks:
        t_s = by_tick[drivers[0]][tick]["t_s"]
        if t_s < 60.0:
            continue
        for i, driver_a in enumerate(drivers):
            for driver_b in drivers[i + 1:]:
                pair = (driver_a, driver_b)
                delta = by_tick[driver_a][tick]["cum_dist"] - by_tick[driver_b][tick]["cum_dist"]
                new_state = 1 if delta >= 10.0 else -1 if delta <= -10.0 else 0
                old_state = state[pair]
                if new_state and old_state and new_state != old_state:
                    active = [
                        a for a in attempts
                        if a["start_tick"] <= tick <= a["end_tick"]
                    ]
                    same_pair = [
                        a for a in active
                        if {a["ego_csv"], a["target_csv"]} == {driver_a, driver_b}
                    ]
                    pair_attempts = [
                        a for a in attempts
                        if driver_a in (a["ego_csv"], a["target_csv"])
                        or driver_b in (a["ego_csv"], a["target_csv"])
                    ]
                    field_nearest = min(
                        attempts,
                        key=lambda a: min(abs(tick - a["start_tick"]), abs(tick - a["end_tick"])),
                        default=None,
                    )
                    pilot_nearest = min(
                        pair_attempts,
                        key=lambda a: min(abs(tick - a["start_tick"]), abs(tick - a["end_tick"])),
                        default=None,
                    )
                    def lag_to(attempt):
                        if attempt is None:
                            return None
                        boundary = attempt["start_tick"] if tick < attempt["start_tick"] else attempt["end_tick"]
                        return (tick - boundary) / 10.0
                    if same_pair:
                        relation = "same_pair_active"
                    elif active:
                        relation = "other_attempt_active"
                    elif pilot_nearest and 0 <= tick - pilot_nearest["end_tick"] <= 20:
                        relation = "within_2s_after_same_pilot_attempt"
                    elif pilot_nearest and abs(tick - pilot_nearest["start_tick"]) <= 100:
                        relation = "within_10s_of_same_pilot_attempt"
                    else:
                        relation = "outside_attempt_window"
                    events.append({
                        "tick": tick, "t_s": t_s,
                        "pilot_a": driver_a, "pilot_b": driver_b,
                        "direction": "a_ahead" if new_state > old_state else "b_ahead",
                        "net_sign": 1 if new_state > old_state else -1,
                        "relation": relation,
                        "same_pilot_attempt_lag_s": lag_to(pilot_nearest),
                        "field_attempt_lag_s": lag_to(field_nearest),
                        "same_pair_consumed": bool(
                            same_pair and any(a.get("outcome") == "CONSUMIDA" for a in same_pair)
                        ),
                        "nearest_same_pilot_attempt_id": None if pilot_nearest is None else pilot_nearest.get("attempt_id"),
                        "nearest_field_attempt_id": None if field_nearest is None else field_nearest.get("attempt_id"),
                    })
                if new_state:
                    state[pair] = new_state
    return events


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


PASS_DIAG_2_PREREG = "backend/experiments/pass-1/autopsia/PREREG_PASS_DIAG_2.md"
PASS_DIAG_2_MANIFEST = "backend/experiments/pass-1/autopsia/1_MANIFEST_PASS_DIAG_2.json"
PASS_DIAG_2_CENSUS_FILES = (
    "backend/experiments/pass-1/autopsia/0_CENSO_FORMAS_PASS_DIAG_2.txt",
    "backend/experiments/pass-1/autopsia/0_CENSO_RESIDUOS_PASS_DIAG_2.txt",
    "backend/experiments/pass-1/autopsia/0_CENSO_SCHEMA_AUDIT_PASS_DIAG_2.txt",
)
PASS_DIAG_2_SELFTEST = "backend/experiments/pass-1/autopsia/0_selftest_v15.log"
PASS_DIAG_2_OUTPUT_NAMES = (
    "1_Q1_PRE60_DIVERGENCIA.csv", "2_Q2_GAPS_TENTATIVAS.csv",
    "3_Q2_FOLLOW_R1.csv", "4_RESUMO_PASS_DIAG_2.json",
)
PASS_DIAG_2_NONTRAJECTORY_EXCLUDED = {"tick", "t_s", "drv"}
PASS_DIAG_2_SAMPLE_DT_S = 0.2


def _pass2_xy_fields(fields: list[str]) -> tuple[str, str]:
    x_name = "body_x" if "body_x" in fields else "x" if "x" in fields else None
    y_name = "body_y" if "body_y" in fields else "y" if "y" in fields else None
    if x_name is None or y_name is None:
        raise Pare("Q1 trajectory XY schema missing")
    return x_name, y_name


def _pass2_cell_diff(left: Any, right: Any) -> tuple[bool, float | None]:
    try:
        left_num, right_num = float(left), float(right)
    except (TypeError, ValueError):
        return str(left).strip() != str(right).strip(), None
    if not math.isfinite(left_num) or not math.isfinite(right_num):
        raise Pare("Q1 contains non-finite aligned value")
    delta = abs(left_num - right_num)
    return delta > 1e-9, delta


def _pass2_first_differences(
    r1_rows: list[dict[str, Any]], r2_rows: list[dict[str, Any]], fields: list[str],
) -> dict[str, Any]:
    x_name, y_name = _pass2_xy_fields(fields)
    trajectory = ("s", x_name, y_name, "cum_dist", "speed", "lat")
    if any(name not in fields for name in trajectory):
        raise Pare("Q1 trajectory column schema missing")

    def keyed(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
        result: dict[tuple[str, int], dict[str, Any]] = {}
        for row in rows:
            if row["t_s"] >= 60.0:
                continue
            key = (row["drv"], row["tick"])
            if key in result:
                raise Pare("Q1 duplicate driver/tick key")
            result[key] = row
        return result

    r1, r2 = keyed(r1_rows), keyed(r2_rows)
    if set(r1) != set(r2):
        raise Pare("Q1 pre-60 driver/tick alignment mismatch")
    field_order = {name: index for index, name in enumerate(fields)}
    trajectory_set = set(trajectory)
    other_fields = [
        name for name in fields
        if name not in trajectory_set and name not in PASS_DIAG_2_NONTRAJECTORY_EXCLUDED
    ]
    trajectory_diffs: list[dict[str, Any]] = []
    other_diffs: list[dict[str, Any]] = []
    by_driver_trajectory: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for driver, tick in sorted(r1, key=lambda item: (item[1], item[0])):
        left, right = r1[(driver, tick)], r2[(driver, tick)]
        for name in trajectory:
            different, delta = _pass2_cell_diff(left[name], right[name])
            if different:
                item = {
                    "tick": tick, "t_s": left["t_s"], "driver": driver,
                    "field": name, "r1": left[name], "r2": right[name],
                    "abs_delta": delta,
                }
                trajectory_diffs.append(item)
                by_driver_trajectory[driver].append(item)
        for name in other_fields:
            different, delta = _pass2_cell_diff(left.get(name, ""), right.get(name, ""))
            if different:
                other_diffs.append({
                    "tick": tick, "t_s": left["t_s"], "driver": driver,
                    "field": name, "r1": left.get(name, ""),
                    "r2": right.get(name, ""), "abs_delta": delta,
                })
    trajectory_diffs.sort(key=lambda item: (item["tick"], field_order[item["field"]], item["driver"]))
    other_diffs.sort(key=lambda item: (item["tick"], field_order[item["field"]], item["driver"]))
    classification = (
        "TRAJECTORY_DIVERGENCE" if trajectory_diffs
        else "NONTRAJECTORY_ONLY" if other_diffs
        else "IDENTICAL_PRE60"
    )
    per_driver = []
    for driver in sorted({row["drv"] for row in r1_rows}):
        rows = by_driver_trajectory.get(driver, [])
        rows.sort(key=lambda item: (item["tick"], field_order[item["field"]]))
        per_driver.append(rows[0] if rows else {
            "tick": None, "t_s": None, "driver": driver, "field": None,
            "r1": None, "r2": None, "abs_delta": None,
        })
    return {
        "classification": classification,
        "trajectory_mismatch_count": len(trajectory_diffs),
        "other_field_mismatch_count": len(other_diffs),
        "first_trajectory": trajectory_diffs[0] if trajectory_diffs else None,
        "first_other_field": other_diffs[0] if other_diffs else None,
        "first_trajectory_by_driver": per_driver,
        "trajectory_fields": list(trajectory),
    }


def _pass2_unwrap_gaps(raw_gaps: list[float], length: float) -> list[float]:
    if not raw_gaps:
        return []
    result = [raw_gaps[0]]
    previous_raw = raw_gaps[0]
    for raw in raw_gaps[1:]:
        result.append(result[-1] + _wrap_signed(raw - previous_raw, length))
        previous_raw = raw
    return result


def _pass2_regression(times: list[float], gaps: list[float]) -> dict[str, Any]:
    if len(times) != len(gaps) or len(times) < 3:
        return {"estimable": False}
    xs = [value - times[0] for value in times]
    xbar, ybar = statistics.fmean(xs), statistics.fmean(gaps)
    sxx = sum((value - xbar) ** 2 for value in xs)
    if sxx <= 0.0:
        return {"estimable": False}
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, gaps)) / sxx
    intercept = ybar - slope * xbar
    residual_ss = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, gaps))
    slope_se = math.sqrt(max(0.0, residual_ss / (len(xs) - 2) / sxx))
    endpoint_gap = gaps[-1]
    projected = endpoint_gap + slope * 10.0
    half_band = 1.96 * slope_se * 10.0
    lower, upper = projected - half_band, projected + half_band
    if upper <= -10.0:
        projection = "PLAUSIBLE_CONSUMPTION"
    elif lower > -10.0:
        projection = "NOT_PLAUSIBLE_IN_10S"
    else:
        projection = "UNCERTAIN"
    return {
        "estimable": True, "n": len(times), "gap_slope_mps": slope,
        "closing_rate_mps": -slope, "slope_se_mps": slope_se,
        "g_start_m": gaps[0], "g_end_m": endpoint_gap,
        "g_end_plus_10s_m": projected, "g_end_plus_10s_lo95_m": lower,
        "g_end_plus_10s_hi95_m": upper, "projection": projection,
    }


def _pass2_attempt_gap_rows(
    attempts: list[dict[str, Any]],
    r2_by_driver: dict[str, list[dict[str, Any]]],
    length: float,
) -> list[dict[str, Any]]:
    result = []
    for attempt in attempts:
        ego_rows = {row["tick"]: row for row in r2_by_driver[attempt["ego_csv"]]}
        target_rows = {row["tick"]: row for row in r2_by_driver[attempt["target_csv"]]}
        common_ticks = sorted(set(ego_rows) & set(target_rows))
        bounds = _sample_bounds(attempt["start_tick"], attempt["end_tick"], common_ticks)
        base = {
            "driver": attempt["driver"], "target": attempt["target"],
            "start_tick_logical": attempt["start_tick"],
            "end_tick_logical": attempt["end_tick"],
            "sample_start_tick": bounds["sample_start_tick"],
            "sample_end_tick": bounds["sample_end_tick"],
        }
        if not bounds["estimable"]:
            result.append({**base, "estimable": False, "n": 0, "projection": "NAO_ESTIMAVEL"})
            continue
        ticks = common_ticks[bounds["start_index"]:bounds["end_index"] + 1]
        raw_gaps = [
            _wrap_signed(target_rows[tick]["s"] - ego_rows[tick]["s"], length)
            for tick in ticks
        ]
        gaps = _pass2_unwrap_gaps(raw_gaps, length)
        times = [ego_rows[tick]["t_s"] for tick in ticks]
        fit = _pass2_regression(times, gaps)
        if not fit["estimable"]:
            result.append({**base, **fit, "estimable": False, "projection": "NAO_ESTIMAVEL"})
        else:
            result.append({**base, **fit})
    return result


def _pass2_follow_rows(r1_by_driver: dict[str, list[dict[str, Any]]], length: float) -> list[dict[str, Any]]:
    by_tick: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for driver, rows in r1_by_driver.items():
        for row in rows:
            by_tick[row["tick"]][driver] = row
    counts: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for cars in by_tick.values():
        for ego, row in cars.items():
            totals[ego] += 1
            ahead = []
            for other, other_row in cars.items():
                if other == ego:
                    continue
                gap = _wrap_signed(other_row["s"] - row["s"], length)
                if gap > 0.0:
                    ahead.append((gap, other, other_row))
            if ahead:
                gap, _, other_row = min(ahead, key=lambda item: (item[0], item[1]))
                if gap < 60.0 and abs(other_row["speed"] - row["speed"]) < 0.2:
                    counts[ego] += 1
    result = []
    for driver in sorted(r1_by_driver):
        samples = totals[driver]
        seconds = counts[driver] * PASS_DIAG_2_SAMPLE_DT_S
        total_seconds = samples * PASS_DIAG_2_SAMPLE_DT_S
        result.append({
            "driver": driver, "follow_samples": counts[driver],
            "total_samples": samples, "follow_time_s": seconds,
            "race_time_s": total_seconds,
            "follow_fraction": seconds / total_seconds if total_seconds else None,
        })
    return result


def _pass2_verify_freeze_commit(commit: str) -> dict[str, Any]:
    manifest_path = REPO / PASS_DIAG_2_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        raise Pare("PASS-DIAG-2 manifest invalid") from None
    frozen_paths = [
        PASS_DIAG_2_PREREG, PASS_DIAG_2_MANIFEST, PASS_DIAG_2_SELFTEST,
        "backend/scripts/experiments/passing/pass_1_diag.py", *PASS_DIAG_2_CENSUS_FILES,
    ]
    file_pins = manifest.get("freeze_file_sha256", {})
    for rel in frozen_paths:
        disk = (REPO / rel).read_bytes()
        if rel != PASS_DIAG_2_MANIFEST and hashlib.sha256(disk).hexdigest() != file_pins.get(rel):
            raise Pare("PASS-DIAG-2 freeze file hash mismatch")
        proc = subprocess.run(
            ["git", "show", f"{commit}:{rel}"], cwd=REPO,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if proc.returncode != 0 or proc.stdout != disk:
            raise Pare("PASS-DIAG-2 freeze blob mismatch")
    census_pins = manifest.get("census_sha256", {})
    for rel in PASS_DIAG_2_CENSUS_FILES:
        if sha256(REPO / rel) != census_pins.get(rel):
            raise Pare("PASS-DIAG-2 census hash mismatch")
    if sha256(REPO / PASS_DIAG_2_SELFTEST) != manifest.get("selftest_sha256"):
        raise Pare("PASS-DIAG-2 selftest hash mismatch")
    expected_sources = {path: digest for path, digest in INPUTS.values()}
    if manifest.get("source_pins") != expected_sources:
        raise Pare("PASS-DIAG-2 source pins differ from frozen v1.4 inputs")
    return manifest


def run_pass_diag_2(commit: str) -> None:
    """Run only the PASS-DIAG-2 offline Q1/Q2 additions after the owner freeze."""
    output_paths = [OUT / name for name in PASS_DIAG_2_OUTPUT_NAMES]
    if any(path.exists() for path in output_paths):
        raise Pare("PASS-DIAG-2 output path already exists")
    manifest = _pass2_verify_freeze_commit(commit)
    verify_frozen_blobs(commit)
    verify_input_hashes()
    validate_audit_schema()
    r1_fields, r1_rows = load_csv("R1_CSV")
    r2_fields, r2_rows = load_csv("R2_CSV")
    if r1_fields != r2_fields:
        raise Pare("R1/R2 CSV field schema mismatch")
    x_name, y_name = _pass2_xy_fields(r1_fields)
    required = {"tick", "t_s", "drv", "s", x_name, y_name, "cum_dist", "speed", "lat"}
    if not required.issubset(r1_fields):
        raise Pare("PASS-DIAG-2 trajectory schema mismatch")
    q1 = _pass2_first_differences(r1_rows, r2_rows, r1_fields)
    attempts = parse_attempts(ROOT / INPUTS["R2_LOG"][0])
    if len(attempts) != ATTEMPT_LIMIT:
        raise Pare("PASS-DIAG-2 attempt count mismatch after frozen log/audit join")
    r1_by_driver = _rows_by_driver(r1_rows)
    r2_by_driver = _rows_by_driver(r2_rows)
    for attempt in attempts:
        attempt["ego_csv"] = _driver_match(str(attempt["driver"]), r2_by_driver)
        attempt["target_csv"] = _driver_match(str(attempt["target"]), r2_by_driver)
    _, _, length = _geometry()
    gap_rows = _pass2_attempt_gap_rows(attempts, r2_by_driver, length)
    follow_rows = _pass2_follow_rows(r1_by_driver, length)
    fit_rows = [row for row in gap_rows if row.get("estimable")]
    closing_rates = [float(row["closing_rate_mps"]) for row in fit_rows]
    projection_counts = {
        outcome: sum(row.get("projection") == outcome for row in fit_rows)
        for outcome in ("PLAUSIBLE_CONSUMPTION", "NOT_PLAUSIBLE_IN_10S", "UNCERTAIN")
    }
    projection_counts["NAO_ESTIMAVEL"] = len(gap_rows) - len(fit_rows)
    summary = {
        "instrument_version": VERSION,
        "analysis": "PASS-DIAG-2 Q1/Q2 report-only",
        "input_pins": {role: digest for role, (_, digest) in INPUTS.items()},
        "census_pins": manifest.get("census_sha256", {}),
        "q1": {
            "classification": q1["classification"],
            "trajectory_mismatch_count": q1["trajectory_mismatch_count"],
            "other_field_mismatch_count": q1["other_field_mismatch_count"],
            "first_trajectory": q1["first_trajectory"],
            "first_other_field": q1["first_other_field"],
            "trajectory_fields": q1["trajectory_fields"], "tolerance": 1e-9,
        },
        "q2": {
            "attempt_count": len(gap_rows), "estimable_count": len(fit_rows),
            "nonestimable_count": len(gap_rows) - len(fit_rows),
            "median_closing_rate_mps": statistics.median(closing_rates) if closing_rates else None,
            "mean_closing_rate_mps": statistics.fmean(closing_rates) if closing_rates else None,
            "projection_counts": projection_counts,
            "follow_driver_count": len(follow_rows),
            "follow_total_time_s": sum(row["follow_time_s"] for row in follow_rows),
        },
    }
    q1_rows = [
        {"scope": "global_first_trajectory", **(q1["first_trajectory"] or {})},
        {"scope": "global_first_other_field", **(q1["first_other_field"] or {})},
        *[{"scope": "driver_first_trajectory", **row} for row in q1["first_trajectory_by_driver"]],
    ]
    with tempfile.TemporaryDirectory(prefix="pass_diag_2_", dir=OUT) as temp_name:
        temp_dir = Path(temp_name)
        _write_csv(temp_dir / PASS_DIAG_2_OUTPUT_NAMES[0], q1_rows)
        _write_csv(temp_dir / PASS_DIAG_2_OUTPUT_NAMES[1], gap_rows)
        _write_csv(temp_dir / PASS_DIAG_2_OUTPUT_NAMES[2], follow_rows)
        (temp_dir / PASS_DIAG_2_OUTPUT_NAMES[3]).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for name, final_path in zip(PASS_DIAG_2_OUTPUT_NAMES, output_paths):
            os.replace(temp_dir / name, final_path)
    print("PASS-DIAG-2 ANALYSIS COMPLETE: Q1/Q2 outputs written")


def run_analysis(commit: str) -> None:
    verify_frozen_blobs(commit)
    verify_input_hashes()
    existing = [name for name in OUTPUT_NAMES if (OUT / name).exists()]
    if existing:
        raise Pare("an output path already exists; refusing to overwrite")
    validate_audit_schema()
    _, r1_rows = load_csv("R1_CSV")
    _, r2_rows = load_csv("R2_CSV")
    r1_by, r2_by = _rows_by_driver(r1_rows), _rows_by_driver(r2_rows)
    attempts = parse_attempts(ROOT / INPUTS["R2_LOG"][0])
    for attempt in attempts:
        attempt["ego_csv"] = _driver_match(str(attempt["driver"]), r2_by)
        attempt["target_csv"] = _driver_match(str(attempt["target"]), r2_by)
    points, cumulative, length = _geometry()
    profile, populated = _profile(r1_by, length)
    attempt_rows = _attempt_metrics(attempts, r2_by, profile, points, cumulative, length)
    for attempt in attempts:
        match = next(
            row for row in attempt_rows
            if row["start_tick"] == attempt["start_tick"]
            and row["driver"] == attempt["driver"]
            and row["target"] == attempt["target"]
        )
        attempt.update({
            key: match[key] for key in (
                "outcome", "duration_s", "min_gap_m", "lateral_progress_m",
                "pace_cost_s", "kappa_inv_m", "kappa_band", "near_consume", "estimable",
                "sample_start_tick", "sample_end_tick",
            )
        })
    swaps = _swaps(r2_by, attempts)
    net_swaps = sum(row["net_sign"] for row in swaps)
    windows = _contact_windows(r2_by)
    rejoin = _rejoin_rows(r2_by, windows, attempts)
    first_lap = {
        "R1": _first_lap_timeline(r1_by, [], length),
        "R2": _first_lap_timeline(r2_by, attempts, length),
    }
    pace_by_outcome: dict[str, list[float]] = defaultdict(list)
    for attempt in attempt_rows:
        if attempt["pace_cost_s"] is not None:
            pace_by_outcome[attempt["outcome"]].append(attempt["pace_cost_s"])
    pace_summary = {
        outcome: {
            "count": len(values),
            "p50_s": _quantile(values, 0.5),
            "p95_s": _quantile(values, 0.95),
        }
        for outcome, values in sorted(pace_by_outcome.items())
    }
    first_lap_totals = {
        arm: {
            "contact_count_sum_car_car": sum(float(row["contact_count"]) for row in series),
            "contact_bearing_rows": sum(int(row["contact_rows"]) for row in series),
        }
        for arm, series in first_lap.items()
    }
    union_cost = _pace_union_cost(attempts, r2_by, profile, length)
    estimable_pace_costs = [row["pace_cost_s"] for row in attempt_rows if row["pace_cost_s"] is not None]
    summary = {
        "version": VERSION,
        "sources": {
            role: {"path": rel, "sha256": digest}
            for role, (rel, digest) in INPUTS.items()
        },
        "geometry_track_length_m": length,
        "pace_profile": {
            "bin_width_m": TRACK_BINS_M,
            "populated_bins": len(populated),
            "total_bins": len(profile),
            "fallback": "circular linear interpolation; one-bin global fallback",
        },
        "published_exposure": {
            "net_post_launch_inversions": KNOWN_NET_SWAPS,
            "decision_attempts": ATTEMPT_LIMIT,
            "decision_consumed": 0,
            "first_lap_contact_count_R1": 4140,
            "first_lap_contact_count_R2": 171,
            "post_rejoin_contact_count_R1": 17,
            "post_rejoin_contact_count_R2": 29,
        },
        "observed": {
            "attempt_outcomes": {
                outcome: sum(row["outcome"] == outcome for row in attempt_rows)
                for outcome in sorted({row["outcome"] for row in attempt_rows})
            },
            "consumed_count": sum(row["outcome"] == "CONSUMIDA" for row in attempt_rows),
            "estimable_attempt_count": sum(row["estimable"] for row in attempt_rows),
            "non_estimable_attempt_count": sum(not row["estimable"] for row in attempt_rows),
            "swap_without_consumption_count": sum(row["outcome"] == "TROCA-SEM-CONSUMO" for row in attempt_rows),
            "near_consume_abort_count": sum(bool(row["near_consume"]) for row in attempt_rows),
            "net_pair_order_inversions": net_swaps,
            "published_inversion_count_match": net_swaps == KNOWN_NET_SWAPS,
            "first_lap_totals": first_lap_totals,
            "pace_by_outcome": pace_summary,
            "attempt_window_pace_cost_sum_s": sum(estimable_pace_costs) if estimable_pace_costs else None,
            "attempt_window_union_pace_cost_by_ego_s": union_cost,
            "pace_gap_reference_s": 137.01 - 134.03,
            "rejoin_contact_sum_car_car": sum(float(row["contact_count"]) for row in rejoin),
        },
        "caveats": [
            "Attempt-window pace excess is descriptive and can overlap across pilots; it is not causal attribution of the full lap-median gap.",
            "Contact involvement is a pilot-level proxy because contact partner identity is absent from the pinned CSV schema.",
            "Temporal proximity between an inversion and an attempt is not causal proof.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="pass_diag_1b_", dir=str(OUT)))
    try:
        _write_csv(temp_dir / OUTPUT_NAMES[0], attempt_rows)
        _write_csv(temp_dir / OUTPUT_NAMES[1], swaps)
        pace_rows = []
        for band in ("<0.02", "0.02-0.06", ">0.06"):
            group = [row for row in attempt_rows if row["kappa_band"] == band]
            for outcome in sorted({row["outcome"] for row in group}):
                values = [row["pace_cost_s"] for row in group if row["outcome"] == outcome and row["pace_cost_s"] is not None]
                pace_rows.append({
                    "kappa_band": band, "outcome": outcome, "count": len(values),
                    "pace_p50_s": _quantile(values, 0.5), "pace_p95_s": _quantile(values, 0.95),
                })
        non_estimable = sum(not row["estimable"] for row in attempt_rows)
        if non_estimable:
            pace_rows.append({
                "kappa_band": "não estimável", "outcome": "NÃO ESTIMÁVEL", "count": non_estimable,
                "pace_p50_s": None, "pace_p95_s": None,
            })
        _write_csv(temp_dir / OUTPUT_NAMES[2], pace_rows)
        _write_csv(temp_dir / OUTPUT_NAMES[3], rejoin)
        timeline_rows = [
            {"arm": arm, **row}
            for arm, rows in first_lap.items()
            for row in rows
        ]
        _write_csv(temp_dir / OUTPUT_NAMES[4], timeline_rows)
        (temp_dir / OUTPUT_NAMES[5]).write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for name in OUTPUT_NAMES:
            os.replace(temp_dir / name, OUT / name)
    finally:
        try:
            temp_dir.rmdir()
        except OSError:
            pass
    print("ANALYSIS PASS: output tables written")


def _prereg_pins() -> dict[str, str]:
    text = (ROOT / "experiments/pass-1/autopsia/PREREG_PASS_DIAG_1B.md").read_text(encoding="utf-8")
    pins: dict[str, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"\|\s*([^|]+?)\s*\|\s*([0-9a-f]{64})\s*\|", line.strip())
        if match:
            pins[match.group(1).strip()] = match.group(2)
    geometry = re.search(
        r"Geometria Tier A:\s*([^,]+),\s*commit de proveniência [0-9a-f]{40},\s*SHA-256 ([0-9a-f]{64})",
        text,
    )
    if geometry:
        pins[geometry.group(1).strip()] = geometry.group(2)
    return pins


def _pins_match_prereg() -> bool:
    frozen = _prereg_pins()
    expected = {path: digest for path, digest in INPUTS.values()}
    return frozen == expected


def selftest() -> None:
    assert _pins_match_prereg(), "input pins must match the frozen preregistration"
    logical_start = _attempt_time_tick({"start_s": 332.7}, "start")
    logical_end = _attempt_time_tick({"end_s": 333.1}, "end")
    assert logical_start == 3327 and logical_end == 3331
    mapped = _sample_bounds(logical_start, logical_end, [3326, 3328, 3330, 3332])
    assert mapped["estimable"]
    assert (mapped["sample_start_tick"], mapped["sample_end_tick"]) == (3328, 3330)
    short = _sample_bounds(3327, 3329, [3326, 3328, 3330])
    assert not short["estimable"] and short["sample_start_tick"] == short["sample_end_tick"] == 3328
    try:
        _tick_from_time(332.755)
    except Pare:
        pass
    else:
        raise AssertionError("genuinely off-grid time must PARE")
    summary_keys = {
        "opportunities", "engaged", "aborted_gap", "aborted_timeout", "aborted_contact",
        "aborted_rejoin", "aborted_target", "consumed", "attempts", "active_attempt",
    }
    expected_outcomes = ["abort_timeout", "abort_contact", "aborted_rejoin", "aborted_target", "consumed"]
    synthetic_attempts = [
        {"target_id": f"T{index}", "start_s": 60.0 + index * 2.0,
         "end_s": 61.0 + index * 2.0, "outcome": outcome}
        for index, outcome in enumerate(expected_outcomes)
    ]
    summary = {
        "opportunities": 5, "engaged": 5, "aborted_gap": 0, "aborted_timeout": 1,
        "aborted_contact": 1, "aborted_rejoin": 1, "aborted_target": 1, "consumed": 1,
        "attempts": synthetic_attempts, "active_attempt": None,
    }
    assert set(summary) == summary_keys
    synthetic_lines = [f"[pass-decision] SIM: {summary!r}"]
    synthetic_lines.extend(
        f"[pass-decision] SYN{index}: " + repr({
            "opportunities": 0, "engaged": 0, "aborted_gap": 0, "aborted_timeout": 0,
            "aborted_contact": 0, "aborted_rejoin": 0, "aborted_target": 0, "consumed": 0,
            "attempts": [], "active_attempt": None,
        })
        for index in range(EXPECTED_DRIVERS - 1)
    )
    synthetic_audit = {"R2": [
        {"driver_id": "SIM", **attempt}
        for attempt in synthetic_attempts
    ]}
    parsed = _parse_summary_lines(synthetic_lines, synthetic_audit)
    assert len(parsed) == ATTEMPT_LIMIT
    assert [item["logged_outcome"] for item in parsed] == expected_outcomes
    assert parsed[2]["target"] == "T2" and parsed[2]["start_tick"] == 640
    mismatched_audit = {"R2": [dict(item) for item in synthetic_audit["R2"]]}
    mismatched_audit["R2"][0]["target_id"] = "WRONG"
    try:
        _parse_summary_lines(synthetic_lines, mismatched_audit)
    except Pare:
        pass
    else:
        raise AssertionError("log/audit disagreement must PARE")
    assert _wrap_signed(5.0, 100.0) == 5.0
    assert _wrap_signed(98.0, 100.0) == -2.0
    assert _norm_key("ABORT-CONTACT") == "abort_contact"
    assert _event({"event": "abort"}) == "abort"
    assert _event({"action": "engage"}) == "engage"
    points = [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0)]
    cumulative = [0.0]
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        cumulative.append(cumulative[-1] + math.hypot(following[0] - point[0], following[1] - point[1]))
    length = cumulative[-1]
    ticks = list(range(0, 14, 2))
    def row(driver: str, tick: int, distance: float, s: float) -> dict[str, Any]:
        return {
            "drv": driver, "tick": tick, "t_s": tick / 10.0,
            "cum_dist": distance, "s": s, "lat": 0.0,
        }
    r2_by_driver = {
        "A": [row("A", tick, float(i), float(i)) for i, tick in enumerate(ticks)],
        "B": [row("B", tick, 1.0, 1.0) for tick in ticks],
    }
    synthetic = [{
        "driver": "A", "target": "B", "attempt_id": "synthetic",
        "start_tick": 0, "end_tick": 12, "logged_outcome": "abort_timeout",
        "ego_csv": "A", "target_csv": "B",
    }]
    profile = [20.0] * math.ceil(length / TRACK_BINS_M)
    result = _attempt_metrics(synthetic, r2_by_driver, profile, points, cumulative, length)
    assert result[0]["outcome"] == "TROCA-SEM-CONSUMO"
    carveout = _attempt_metrics(
        [{**synthetic[0], "logged_outcome": "aborted_rejoin"}],
        r2_by_driver, profile, points, cumulative, length,
    )
    assert carveout[0]["outcome"] == "ABORT-CARVEOUT-REJOIN"
    consumed_rows = dict(r2_by_driver)
    consumed_rows["A"] = [row("A", tick, float(i * 3), float(i)) for i, tick in enumerate(ticks)]
    consumed = _attempt_metrics(synthetic, consumed_rows, profile, points, cumulative, length)
    assert consumed[0]["outcome"] == "CONSUMIDA"
    short_attempt = [{**synthetic[0], "start_tick": 1, "end_tick": 3}]
    short_rows = {
        "A": [row("A", 2, 1.0, 1.0)],
        "B": [row("B", 2, 0.0, 0.0)],
    }
    short_result = _attempt_metrics(short_attempt, short_rows, profile, points, cumulative, length)
    assert short_result[0]["outcome"] == "NÃO ESTIMÁVEL"
    assert short_result[0]["pace_cost_s"] is None
    duplicate_audit = {"R2": [dict(item) for item in synthetic_audit["R2"]]}
    duplicate_audit["R2"][1] = dict(duplicate_audit["R2"][0])
    try:
        _parse_summary_lines(synthetic_lines, duplicate_audit)
    except Pare:
        pass
    else:
        raise AssertionError("non-bijective log/audit join must PARE")
    q1_fields = ["tick", "t_s", "drv", "s", "body_x", "body_y", "cum_dist", "speed", "lat", "p_state"]
    q1_r1 = [
        {"tick": 0, "t_s": 0.0, "drv": "A", "s": 10.0, "body_x": 1.0,
         "body_y": 2.0, "cum_dist": 0.0, "speed": 20.0, "lat": 0.0, "p_state": "follow"},
        {"tick": 0, "t_s": 0.0, "drv": "B", "s": 30.0, "body_x": 3.0,
         "body_y": 4.0, "cum_dist": 0.0, "speed": 20.0, "lat": 0.0, "p_state": "follow"},
    ]
    q1_r2 = [dict(row) for row in q1_r1]
    q1_r2[0]["speed"] += 1e-6
    q1_trajectory = _pass2_first_differences(q1_r1, q1_r2, q1_fields)
    assert q1_trajectory["classification"] == "TRAJECTORY_DIVERGENCE"
    assert q1_trajectory["first_trajectory"]["driver"] == "A"
    q1_other = [dict(row) for row in q1_r1]
    q1_other[0]["p_state"] = "cruise"
    assert _pass2_first_differences(q1_r1, q1_other, q1_fields)["classification"] == "NONTRAJECTORY_ONLY"
    q1_equal = [dict(row) for row in q1_r1]
    q1_equal[0]["speed"] += 5e-10
    assert _pass2_first_differences(q1_r1, q1_equal, q1_fields)["classification"] == "IDENTICAL_PRE60"
    times = [index / 5.0 for index in range(21)]
    closing = _pass2_regression(times, [30.0 - 3.0 * value for value in times])
    assert closing["estimable"] and abs(closing["closing_rate_mps"] - 3.0) < 1e-10
    assert closing["projection"] == "PLAUSIBLE_CONSUMPTION"
    stationary = _pass2_regression(times, [20.0] * len(times))
    assert stationary["estimable"] and abs(stationary["closing_rate_mps"]) < 1e-10
    assert stationary["projection"] == "NOT_PLAUSIBLE_IN_10S"
    assert not _pass2_regression(times[:2], [20.0, 20.0])["estimable"]
    assert _pass2_unwrap_gaps([20.0, 20.0, 20.0], 100.0) == [20.0, 20.0, 20.0]
    synthetic_ticks = list(range(0, 42, 2))
    synthetic_ego = [{
        "drv": "A", "tick": tick, "t_s": tick / 10.0,
        "s": (100.0 + tick / 10.0) % 100.0, "speed": 20.0,
    } for tick in synthetic_ticks]
    synthetic_target = [{
        "drv": "B", "tick": tick, "t_s": tick / 10.0,
        "s": (100.0 + tick / 10.0 + 30.0 - 3.0 * (tick / 10.0)) % 100.0,
        "speed": 17.0,
    } for tick in synthetic_ticks]
    synthetic_attempt = [{
        "driver": "A", "target": "B", "ego_csv": "A", "target_csv": "B",
        "start_tick": 0, "end_tick": 40,
    }]
    mapped_gap = _pass2_attempt_gap_rows(
        synthetic_attempt, {"A": synthetic_ego, "B": synthetic_target}, 100.0,
    )[0]
    assert mapped_gap["estimable"] and mapped_gap["n"] == 21
    assert abs(mapped_gap["closing_rate_mps"] - 3.0) < 1e-10
    short_gap = _pass2_attempt_gap_rows(
        [{**synthetic_attempt[0], "start_tick": 0, "end_tick": 0}],
        {"A": synthetic_ego, "B": synthetic_target}, 100.0,
    )[0]
    assert not short_gap["estimable"] and short_gap["projection"] == "NAO_ESTIMAVEL"
    follow_synthetic = {
        "A": [{"drv": "A", "tick": 0, "s": 100.0, "speed": 10.0}],
        "B": [{"drv": "B", "tick": 0, "s": 120.0, "speed": 10.0}],
        "C": [{"drv": "C", "tick": 0, "s": 80.0, "speed": 12.0}],
    }
    follow_result = _pass2_follow_rows(follow_synthetic, 4160.0)
    assert next(row for row in follow_result if row["driver"] == "A")["follow_time_s"] == 0.2
    print("SELFTEST PASS: v1.4 pins/join/ticks plus PASS-DIAG-2 Q1, gap regression, projection, wrap and follow fixtures")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--frozen-commit")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.run or not args.frozen_commit:
        print("FAIL: require --selftest or --run --frozen-commit <hash>")
        return 2
    try:
        run_analysis(args.frozen_commit)
    except Pare as error:
        print(f"PARE: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
