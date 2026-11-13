#!/usr/bin/env python3
"""PROJ-FIX-1 frozen offline XY/ns_raw jump classification, version 1.0."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


VERSION = "1.0"
FIELDS_EXPECTED = 71
TRACK_SEGMENTS = 834
PROJECTION_RUN = "composite_monaco_s0"
EXPECTED_GE10 = 112
EXPECTED_GE30 = 45
SCRIPT_PATH = Path(__file__).resolve()
BACKEND = SCRIPT_PATH.parent.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _projection49(path: Path) -> bytes:
    """Byte projection required by g1: split(',')[:49], including header."""
    projected = []
    with path.open("rb") as f:
        for line in f:
            if line.startswith(b"#"):
                continue
            if line.endswith(b"\r\n"):
                body, ending = line[:-2], b"\r\n"
            elif line.endswith(b"\n"):
                body, ending = line[:-1], b"\n"
            else:
                body, ending = line, b""
            projected.append(b",".join(body.split(b",")[:49]) + ending)
    return b"".join(projected)


def _iter_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        if rows.fieldnames is None:
            raise ValueError(f"sem header CSV: {path}")
        yield rows.fieldnames
        yield from rows


def _gate(replay: Path, anchor: Path) -> dict:
    if not replay.is_file() or not anchor.is_file():
        raise FileNotFoundError(f"replay/âncora ausente: {replay} / {anchor}")
    replay_projection = _projection49(replay)
    anchor_projection = _projection49(anchor)
    if replay_projection != anchor_projection:
        raise ValueError("g1 FAIL: projeção split(',')[:49] diverge da âncora R4")

    fields, *rows = _iter_csv(replay)
    if len(fields) != FIELDS_EXPECTED:
        raise ValueError(f"g2 FAIL: header tem {len(fields)} campos, esperado {FIELDS_EXPECTED}")
    if len(rows) == 0:
        raise ValueError("g2 FAIL: sem linhas de dados")
    index = {name: i for i, name in enumerate(fields)}
    required = {"body_x", "body_y", "ns_raw", "tick", "drv"}
    if not required.issubset(index):
        raise ValueError(f"g2 FAIL: faltam colunas {sorted(required - set(index))}")
    for line_no, row in enumerate(rows, 2):
        if None in row or None in row.values() or len(row) != FIELDS_EXPECTED:
            raise ValueError(f"g2 FAIL: linha {line_no} não tem {FIELDS_EXPECTED} campos")
        try:
            x, y = float(row["body_x"]), float(row["body_y"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"g2 FAIL: XY inválido na linha {line_no}") from exc
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"g2 FAIL: XY não finito na linha {line_no}")
        raw_ns = row["ns_raw"]
        if not re.fullmatch(r"[+-]?\d+", raw_ns or ""):
            raise ValueError(f"g2 FAIL: ns_raw não inteiro lexical na linha {line_no}: {raw_ns!r}")
        ns = int(raw_ns)
        if not 0 <= ns < TRACK_SEGMENTS:
            raise ValueError(f"g2 FAIL: ns_raw fora de [0,{TRACK_SEGMENTS - 1}] na linha {line_no}")
    return {
        "g1": "PASS",
        "g1_replay_projection_sha256": hashlib.sha256(replay_projection).hexdigest(),
        "g1_anchor_projection_sha256": hashlib.sha256(anchor_projection).hexdigest(),
        "g2": "PASS",
        "fields_per_row": FIELDS_EXPECTED,
        "data_rows": len(rows),
    }


def _parse_sample(row: dict, ordinal: int) -> dict:
    sample = {"ordinal": ordinal, "drv": str(row.get("drv", "")), "valid": True}
    reasons = []
    try:
        sample["tick"] = int(row.get("tick", ""))
    except (TypeError, ValueError):
        sample["tick"] = None
        reasons.append("tick")
    try:
        sample["x"] = float(row.get("body_x", ""))
        sample["y"] = float(row.get("body_y", ""))
        if not math.isfinite(sample["x"]) or not math.isfinite(sample["y"]):
            reasons.append("xy_nonfinite")
    except (TypeError, ValueError):
        sample["x"] = sample["y"] = math.nan
        reasons.append("xy_invalid")
    raw_ns = row.get("ns_raw", "")
    if not re.fullmatch(r"[+-]?\d+", raw_ns or ""):
        sample["ns"] = None
        reasons.append("ns_not_integer")
    else:
        sample["ns"] = int(raw_ns)
        if not 0 <= sample["ns"] < TRACK_SEGMENTS:
            reasons.append("ns_out_of_range")
    sample["valid"] = not reasons
    sample["invalid_reason"] = ";".join(reasons)
    return sample


def _classify_samples(samples: list[dict]) -> tuple[list[dict], list[dict]]:
    by_driver = defaultdict(list)
    invalid_rows = []
    for sample in samples:
        if not sample["valid"]:
            invalid_rows.append(sample)
        by_driver[sample["drv"]].append(sample)

    classified = []
    for drv, group in by_driver.items():
        group.sort(key=lambda s: (s["tick"] is None, s["tick"] if s["tick"] is not None else 0,
                                  s["ordinal"]))
        for prev, cur in zip(group, group[1:]):
            if not prev["valid"] or not cur["valid"]:
                continue
            if prev["tick"] is None or cur["tick"] is None or cur["tick"] <= prev["tick"]:
                continue
            dxy = math.hypot(cur["x"] - prev["x"], cur["y"] - prev["y"])
            dns = abs(cur["ns"] - prev["ns"])
            if dxy >= 30.0 and dns >= 8:
                label = "C1"
            elif dxy >= 30.0 and dns < 8:
                label = "C2"
            elif dxy < 30.0 and dns >= 8:
                label = "C3"
            else:
                continue
            classified.append({
                "drv": drv,
                "tick_prev": prev["tick"],
                "tick": cur["tick"],
                "dxy_m": dxy,
                "d_ns_raw": dns,
                "class": label,
            })
    return classified, invalid_rows


def _linear_percentile(values: list[float], percentile: float = 95.0):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _load_samples(replay: Path) -> list[dict]:
    fields, *rows = _iter_csv(replay)
    required = {"tick", "drv", "body_x", "body_y", "ns_raw"}
    if not required.issubset(fields):
        raise ValueError(f"faltam colunas no replay: {sorted(required - set(fields))}")
    return [_parse_sample(row, i) for i, row in enumerate(rows, 1)]


def _load_projection_events(path: Path) -> list[dict]:
    events = []
    fields, *rows = _iter_csv(path)
    required = {"run", "drv", "tick_prev", "tick", "abs_projection_error_m"}
    if not required.issubset(fields):
        raise ValueError(f"faltam colunas em saltos_projecao.csv: {sorted(required - set(fields))}")
    for row in rows:
        if row["run"] != PROJECTION_RUN:
            continue
        try:
            error = float(row["abs_projection_error_m"])
            if not math.isfinite(error) or error < 10.0:
                continue
            event = dict(row)
            event["tick_prev"] = int(row["tick_prev"])
            event["tick"] = int(row["tick"])
            event["abs_projection_error_m"] = error
            events.append(event)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"evento NIT-2 inválido: {row}") from exc
    return events


def _event_key(row: dict) -> tuple[str, int, int]:
    return str(row["drv"]), int(row["tick_prev"]), int(row["tick"])


def _summarize(classified: list[dict], invalid_rows: list[dict]) -> dict:
    result = {"C1": {}, "C2": {}, "C3": {}, "C4": {"count": len(invalid_rows)}}
    for label in ("C1", "C2", "C3"):
        part = [row for row in classified if row["class"] == label]
        result[label] = {
            "count": len(part),
            "p95_dxy_m": _linear_percentile([row["dxy_m"] for row in part]),
            "p95_abs_d_ns_raw": _linear_percentile([row["d_ns_raw"] for row in part]),
        }
    result["C4"]["rows"] = [
        {"drv": row["drv"], "tick": row["tick"], "reason": row["invalid_reason"]}
        for row in invalid_rows
    ]
    return result


def _write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _classify_run(replay: Path, anchor: Path, historical: Path, outdir: Path) -> dict:
    gate = _gate(replay, anchor)
    samples = _load_samples(replay)
    classified, invalid_rows = _classify_samples(samples)
    events = _load_projection_events(historical)
    ge10 = [event for event in events if event["abs_projection_error_m"] >= 10.0]
    ge30 = [event for event in events if event["abs_projection_error_m"] >= 30.0]
    if len(ge10) != EXPECTED_GE10 or len(ge30) != EXPECTED_GE30:
        raise ValueError(
            f"reconciliação histórica FAIL: >=10={len(ge10)} (esperado {EXPECTED_GE10}), "
            f">=30={len(ge30)} (esperado {EXPECTED_GE30})"
        )

    classified_by_key = {}
    for row in classified:
        key = _event_key(row)
        if key in classified_by_key:
            raise ValueError(f"par classificado duplicado: {key}")
        classified_by_key[key] = row

    mapped = []
    seen = set()
    for event in ge10:
        key = _event_key(event)
        if key in seen:
            raise ValueError(f"evento NIT-2 duplicado: {key}")
        seen.add(key)
        assignment = classified_by_key.get(key)
        if assignment is None:
            raise ValueError(f"evento NIT-2 sem classe XY/ns_raw: {key}")
        mapped.append({**event, "class_xy_ns": assignment["class"],
                       "dxy_m": assignment["dxy_m"], "d_ns_raw": assignment["d_ns_raw"]})

    mapped_ge30 = [row for row in mapped if row["abs_projection_error_m"] >= 30.0]
    if len(mapped_ge30) != EXPECTED_GE30 or len(mapped) != EXPECTED_GE10:
        raise ValueError("mapeamento 1:1 não fechou os cortes NIT-2 / headline")

    summary = _summarize(classified, invalid_rows)
    summary["headline_ge30_mapping"] = {
        label: sum(row["class_xy_ns"] == label for row in mapped_ge30)
        for label in ("C1", "C2", "C3")
    }
    summary["nit2_ge10_mapping"] = {
        label: sum(row["class_xy_ns"] == label for row in mapped)
        for label in ("C1", "C2", "C3")
    }
    summary["reconciliation"] = {
        "historical_ge10": len(mapped), "historical_ge30": len(mapped_ge30),
        "mapped_ge10": len(mapped), "mapped_ge30": len(mapped_ge30),
        "script_version": VERSION, "script_sha256": _sha256(SCRIPT_PATH),
        "replay_sha256": _sha256(replay), "anchor_sha256": _sha256(anchor),
        "historical_jumps_sha256": _sha256(historical),
        "gates": gate,
    }
    outdir.mkdir(parents=True, exist_ok=True)
    _write_csv(outdir / "pares_classificados.csv", classified,
               ["drv", "tick_prev", "tick", "dxy_m", "d_ns_raw", "class"])
    _write_csv(outdir / "mapa_nit2_ge10.csv", mapped)
    (outdir / "resumo_classes.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _selftest() -> int:
    synthetic = [
        {"drv": "TST", "tick": "0", "body_x": "0", "body_y": "0", "ns_raw": "0"},
        {"drv": "TST", "tick": "1", "body_x": "30", "body_y": "40", "ns_raw": "8"},
        {"drv": "TST", "tick": "2", "body_x": "60", "body_y": "40", "ns_raw": "15"},
        {"drv": "TST", "tick": "3", "body_x": "89.999", "body_y": "40", "ns_raw": "23"},
        {"drv": "TST", "tick": "4", "body_x": "nan", "body_y": "40", "ns_raw": "31"},
    ]
    samples = [_parse_sample(row, i) for i, row in enumerate(synthetic, 1)]
    classified, invalid = _classify_samples(samples)
    got = [row["class"] for row in classified]
    assert got == ["C1", "C2", "C3"], got
    assert len(invalid) == 1 and invalid[0]["tick"] == 4
    mapping = [
        {"drv": "TST", "tick_prev": 0, "tick": 1},
        {"drv": "TST", "tick_prev": 1, "tick": 2},
        {"drv": "TST", "tick_prev": 2, "tick": 3},
    ]
    class_by_key = {_event_key(row): row["class"] for row in classified}
    assert [class_by_key[_event_key(row)] for row in mapping] == ["C1", "C2", "C3"]
    assert _linear_percentile([0.0, 10.0], 95.0) == 9.5
    print(f"SELFTEST OK: proj-fix-1 classifier v{VERSION}; C1/C2/C3 boundaries, C4 invalid row, 1:1 keys, p95")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--classify", action="store_true")
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--anchor", type=Path)
    parser.add_argument("--historical-jumps", type=Path)
    parser.add_argument("--outdir", type=Path)
    args = parser.parse_args(argv)
    if args.selftest:
        if any((args.replay, args.anchor, args.historical_jumps, args.outdir)):
            parser.error("--selftest não lê arquivos de corrida ou opções de execução")
        return _selftest()
    if not args.replay or not args.anchor:
        parser.error("--gate/--classify requerem --replay e --anchor")
    try:
        if args.gate:
            print(json.dumps(_gate(args.replay, args.anchor), indent=2))
            return 0
        if not args.historical_jumps or not args.outdir:
            parser.error("--classify requer --historical-jumps e --outdir")
        _classify_run(args.replay, args.anchor, args.historical_jumps, args.outdir)
        return 0
    except Exception as exc:  # fail loud; do not continue to any later gate
        print(f"PARE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
