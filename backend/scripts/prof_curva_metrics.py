#!/usr/bin/env python3
"""Instrumento report-only de corridas solo do PROF-CURVA-1.

O instrumento lê somente o CSV 5 Hz, o log do runner e o sidecar de eventos.
As métricas de excursão são delegadas ao instrumento canônico
``saidas_verdict.py``; não há importação do simulador, controller ou treino.

Uso típico (a partir de ``backend/``)::

    .venv/bin/python scripts/prof_curva_metrics.py \
      --csv experiments/prof-curva-1/c0/INT_N0.csv \
      --log experiments/prof-curva-1/c0/INT_N0.log \
      --sidecar experiments/prof-curva-1/c0/INT_N0_events.csv \
      --track interlagos --expect-variedade 0 --mode off \
      --out experiments/prof-curva-1/c0/INT_N0.metrics.json

O JSON de saída é criado em modo exclusivo e contém ``metrics_sha256``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from scripts import saidas_verdict as SV  # noqa: E402


VERSION = "prof-curva-metrics-v1.0"
SAIDAS_VERDICT_SHA256 = (
    "e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c"
)
EXPECTED_TOTAL_LINES = 3002  # comentário + header + 3000 linhas a 5 Hz / 600 s
CSV_HEADER_LINES = 2
DT_S = 0.2
TICKS_PER_ROW = 2
STEER_MAX_RAD = math.radians(45.0)
STEER_MIN_RAD = 0.04
STEER_V0_MPS = 25.0
STEER_SATURATION_RATIO = 0.95
LAP_TIME_TOLERANCE_S = 0.3

RE_TRACK_SHA = re.compile(r"track_frozen_sha256=([0-9a-fA-F?]+)")
RE_VARIETY = re.compile(r"\bvariedade=(\d+)\b")
RE_CONFIG_SHA = re.compile(
    r"(?:prof[_-]?curva|prof[_-]?turn[_-]?cap|turn[_-]?cap)[^\n]*?"
    r"(?:sha256|config_sha)(?:=|:)\s*([0-9a-fA-F]{16,64})",
    re.IGNORECASE,
)
RE_TEMPOS = re.compile(
    r"^\s*(?P<drv>[A-Za-z0-9_.-]+):\s+\d+\s+voltas\s+\|\s+"
    r"tempos=\[(?P<values>[0-9.,\s]*)\]",
    re.MULTILINE,
)

REQUIRED_COLUMNS = {
    "tick", "t_s", "drv", "speed", "s", "lat", "steer_rad",
    "offtrack", "authority", "cum_dist", "obs4", "obs5", "obs6",
}


class MetricsIntegrityError(ValueError):
    """Entrada ou contrato de integridade do instrumento violado."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def seal_metrics(payload: Mapping[str, Any]) -> Dict[str, Any]:
    body = dict(payload)
    body.pop("metrics_sha256", None)
    body["metrics_sha256"] = hashlib.sha256(
        canonical_json(body).encode("utf-8")
    ).hexdigest()
    return body


def write_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True, indent=2,
                                ensure_ascii=False, allow_nan=False))
        stream.write("\n")


def normalize_track(track: str) -> str:
    key = str(track).strip().lower()
    if key not in SV.TRACKS:
        raise MetricsIntegrityError(
            f"pista não suportada: {track!r}; use {sorted(SV.TRACKS)}")
    return key


def verify_dependencies() -> str:
    """Confere o SHA do instrumento canônico antes de usá-lo."""
    actual = sha256_file(Path(SV.__file__).resolve())
    if actual != SAIDAS_VERDICT_SHA256:
        raise MetricsIntegrityError(
            f"saidas_verdict.py alterado: {actual} != {SAIDAS_VERDICT_SHA256}")
    required = ("build_corner_definitions", "match_corner", "extract_excursions")
    missing = [name for name in required if not callable(getattr(SV, name, None))]
    if missing:
        raise MetricsIntegrityError(
            f"saidas_verdict.py sem funções canônicas: {missing}")
    return actual


def read_csv(path: Path) -> Tuple[pd.DataFrame, str, int]:
    if not path.is_file():
        raise MetricsIntegrityError(f"CSV ausente: {path}")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MetricsIntegrityError(f"CSV não é UTF-8: {path}") from exc
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < CSV_HEADER_LINES:
        raise MetricsIntegrityError(f"CSV sem comentário/header: {path}")
    header = lines[0]
    if not header.startswith("#"):
        raise MetricsIntegrityError(f"CSV sem linha de metadados inicial: {path}")
    try:
        df = pd.read_csv(path, comment="#")
    except Exception as exc:
        raise MetricsIntegrityError(f"falha lendo CSV {path}: {exc}") from exc
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise MetricsIntegrityError(f"CSV sem colunas obrigatórias: {missing}")
    if df.empty:
        raise MetricsIntegrityError(f"CSV sem linhas de dados: {path}")
    if any(df[column].isna().any() for column in REQUIRED_COLUMNS):
        raise MetricsIntegrityError("CSV contém NaN em coluna obrigatória")
    return df, sha256_file(path), len(lines)


def verify_csv_integrity(
    header: str,
    line_count: int,
    data_rows: int,
    track: str,
    expected_total_lines: Optional[int],
) -> Dict[str, Any]:
    expected_track_sha = str(SV.TRACKS[track]["sha256"])
    match = RE_TRACK_SHA.search(header)
    if not match:
        raise MetricsIntegrityError("CSV sem track_frozen_sha256 no cabeçalho")
    actual_track_sha = match.group(1).lower()
    if actual_track_sha != expected_track_sha.lower():
        raise MetricsIntegrityError(
            f"SHA da pista divergente: {actual_track_sha} != {expected_track_sha}")
    if expected_total_lines is not None and line_count != expected_total_lines:
        raise MetricsIntegrityError(
            f"CSV tem {line_count} linhas não vazias; esperado {expected_total_lines}")
    if expected_total_lines is not None:
        expected_data_rows = expected_total_lines - CSV_HEADER_LINES
        if data_rows != expected_data_rows:
            raise MetricsIntegrityError(
                f"CSV tem {data_rows} linhas de dados; esperado {expected_data_rows}")
    return {
        "total_lines": line_count,
        "data_rows": data_rows,
        "track_sha16": actual_track_sha,
        "expected_total_lines": expected_total_lines,
    }


def parse_tempos(log_text: str) -> Dict[str, List[float]]:
    result: Dict[str, List[float]] = {}
    for match in RE_TEMPOS.finditer(log_text):
        values = [float(value.strip()) for value in match.group("values").split(",")
                  if value.strip()]
        result[match.group("drv")] = values
    if not result:
        raise MetricsIntegrityError("log sem linhas tempos=[...] por motorista")
    return result


def parse_log_integrity(
    log_path: Path,
    track: str,
    expected_variedade: Optional[int],
    mode: str,
    expected_config_sha256: Optional[str],
) -> Tuple[str, Dict[str, Any], Dict[str, List[float]]]:
    if not log_path.is_file():
        raise MetricsIntegrityError(f"log ausente: {log_path}")
    raw = log_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MetricsIntegrityError(f"log não é UTF-8: {log_path}") from exc

    variety = RE_VARIETY.search(text)
    if not variety:
        raise MetricsIntegrityError("log sem variedade=N")
    variety_value = int(variety.group(1))
    if expected_variedade is not None and variety_value != expected_variedade:
        raise MetricsIntegrityError(
            f"variedade divergente: {variety_value} != {expected_variedade}")

    config_match = RE_CONFIG_SHA.search(text)
    config_sha = config_match.group(1).lower() if config_match else None
    if mode == "off" and config_sha is not None:
        raise MetricsIntegrityError("SHA de configuração presente em corrida OFF")
    if mode == "on" and config_sha is None:
        raise MetricsIntegrityError("corrida ON sem SHA da configuração do teto")
    if (expected_config_sha256 is not None
            and config_sha != expected_config_sha256.lower()):
        raise MetricsIntegrityError(
            f"SHA da configuração divergente: {config_sha} != {expected_config_sha256}")

    # O log também deve identificar a pista frozen; a conferência principal é
    # feita no cabeçalho CSV, mas esta guarda evita misturar artefatos.
    expected_track_sha = str(SV.TRACKS[track]["sha256"]).lower()
    track_match = RE_TRACK_SHA.search(text)
    if track_match and track_match.group(1).lower() != expected_track_sha:
        raise MetricsIntegrityError("SHA da pista no log diverge do track solicitado")

    tempos = parse_tempos(text)
    return sha256_file(log_path), {
        "variedade": variety_value,
        "config_sha256": config_sha,
        "mode": mode,
    }, tempos


def steering_limit_rad(speed_mps: float) -> float:
    return max(STEER_MIN_RAD, STEER_MAX_RAD /
               (1.0 + (float(speed_mps) / STEER_V0_MPS) ** 2))


def _crossing_times(df: pd.DataFrame, track_length: float) -> Dict[str, List[float]]:
    """Interpolate t_s at each cumulative-distance lap crossing."""
    out: Dict[str, List[float]] = {}
    for drv, group in df.groupby("drv", sort=True):
        ordered = group.sort_values("tick").reset_index(drop=True)
        if len(ordered) < 2:
            out[str(drv)] = []
            continue
        t0 = float(ordered.loc[0, "t_s"])
        c0 = float(ordered.loc[0, "cum_dist"])
        cmax = float(ordered["cum_dist"].max())
        times: List[float] = []
        previous_crossing_t = t0
        lap = 1
        while c0 + lap * track_length <= cmax + 1e-9:
            target = c0 + lap * track_length
            for i in range(1, len(ordered)):
                prev_c = float(ordered.loc[i - 1, "cum_dist"])
                curr_c = float(ordered.loc[i, "cum_dist"])
                if curr_c + 1e-9 < target:
                    continue
                prev_t = float(ordered.loc[i - 1, "t_s"])
                curr_t = float(ordered.loc[i, "t_s"])
                if curr_c > prev_c:
                    frac = (target - prev_c) / (curr_c - prev_c)
                    crossing_t = prev_t + frac * (curr_t - prev_t)
                else:
                    crossing_t = curr_t
                times.append(round(crossing_t - previous_crossing_t, 3))
                previous_crossing_t = crossing_t
                break
            lap += 1
        out[str(drv)] = times
    return out


def _compare_lap_times(
    csv_laps: Mapping[str, List[float]],
    log_laps: Mapping[str, List[float]],
) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    if set(csv_laps) != set(log_laps):
        raise MetricsIntegrityError(
            f"motoristas de voltas divergem CSV/log: {sorted(csv_laps)} != {sorted(log_laps)}")
    for drv in sorted(csv_laps):
        csv_values = list(csv_laps[drv])
        log_values = list(log_laps[drv])
        if len(csv_values) != len(log_values):
            raise MetricsIntegrityError(
                f"quantidade de voltas divergente para {drv}: "
                f"CSV={len(csv_values)} log={len(log_values)}")
        deltas = [round(a - b, 3) for a, b in zip(csv_values, log_values)]
        if any(abs(delta) > LAP_TIME_TOLERANCE_S for delta in deltas):
            raise MetricsIntegrityError(
                f"tempos de volta divergentes para {drv}: CSV={csv_values} "
                f"log={log_values} delta={deltas}")
        checks[drv] = {
            "csv_s": csv_values,
            "log_s": log_values,
            "delta_s": deltas,
            "tolerance_s": LAP_TIME_TOLERANCE_S,
        }
    return checks


def _event_details(df: pd.DataFrame, events: pd.DataFrame) -> List[Dict[str, Any]]:
    by_driver = {
        str(drv): group.sort_values("tick").reset_index(drop=True)
        for drv, group in df.groupby("drv", sort=False)
    }
    details: List[Dict[str, Any]] = []
    for event_index, event in events.reset_index(drop=True).iterrows():
        drv = str(event["drv"])
        sub = by_driver[drv]
        positions = np.flatnonzero(sub["tick"].to_numpy() == int(event["tick"]))
        if len(positions) == 0:
            raise MetricsIntegrityError(
                f"evento {event_index} não encontra tick {event['tick']} no CSV")
        start = int(positions[0])
        count = max(1, int(round(float(event["dur_s"]) / DT_S)))
        segment = sub.iloc[start:start + count]
        previous = sub[(sub["t_s"] >= float(event["t_s"]) - 1.0 - 1e-9)
                       & (sub["t_s"] < float(event["t_s"]) - 1e-9)]
        ratios = []
        for _, row in previous.iterrows():
            limit = steering_limit_rad(float(row["speed"]))
            ratios.append(abs(float(row["steer_rad"])) / limit if limit else 0.0)
        max_ratio = max(ratios) if ratios else 0.0
        details.append({
            "event_index": int(event_index),
            "drv": drv,
            "tick": int(event["tick"]),
            "t_s": float(event["t_s"]),
            "s": float(event["s"]),
            "corner_id": str(event["corner_id"]),
            "corner_name": str(event["corner_name"]),
            "dur_s": float(event["dur_s"]),
            "v_1s_mps": float(event["v_1s_mps"]),
            "max_abs_lat_m": float(segment["lat"].abs().max()),
            "authority_start": str(segment.iloc[0]["authority"]),
            "steer_saturation_ratio_max": float(max_ratio),
            "steer_saturated_in_prior_1s": bool(
                max_ratio >= STEER_SATURATION_RATIO),
        })
    return details


def _corner_summary(events: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for event in events:
        cid = str(event["corner_id"])
        bucket = result.setdefault(cid, {
            "corner_name": str(event["corner_name"]),
            "n_events": 0,
            "s_values": [],
            "max_abs_lat_m": 0.0,
            "steer_saturated_events": 0,
        })
        bucket["n_events"] += 1
        bucket["s_values"].append(round(float(event["s"]), 3))
        bucket["max_abs_lat_m"] = max(
            float(bucket["max_abs_lat_m"]), float(event["max_abs_lat_m"]))
        bucket["steer_saturated_events"] += int(
            bool(event["steer_saturated_in_prior_1s"]))
    return result


def analyze_run(
    csv_path: str | Path,
    log_path: str | Path,
    sidecar_path: str | Path,
    *,
    track: str = "interlagos",
    expected_variedade: Optional[int] = None,
    mode: str = "off",
    expected_config_sha256: Optional[str] = None,
    expected_total_lines: Optional[int] = EXPECTED_TOTAL_LINES,
) -> Dict[str, Any]:
    """Analyze one run and return a deterministic, hash-sealed payload."""
    if mode not in {"off", "on"}:
        raise MetricsIntegrityError("mode deve ser 'off' ou 'on'")
    track = normalize_track(track)
    saidas_sha = verify_dependencies()
    csv_path, log_path, sidecar_path = map(Path, (csv_path, log_path, sidecar_path))
    if not sidecar_path.is_file():
        raise MetricsIntegrityError(f"sidecar ausente: {sidecar_path}")

    df, csv_sha, line_count = read_csv(csv_path)
    header = next(line for line in csv_path.read_text(encoding="utf-8-sig").splitlines()
                  if line.strip())
    integrity = verify_csv_integrity(
        header, line_count, len(df), track, expected_total_lines)
    log_sha, log_integrity, log_laps = parse_log_integrity(
        log_path, track, expected_variedade, mode, expected_config_sha256)

    cfg = SV.TRACKS[track]
    geom = SV.load_track_geometry(Path(cfg["file"]))
    corners = SV.build_corner_definitions(
        geom[0], generic_names=bool(cfg.get("generic_names", False)))
    events, reconciliation = SV.extract_excursions(df, corners, geom)
    details = _event_details(df, events)
    track_length = float(geom[4])
    lap_times = _crossing_times(df, track_length)
    lap_crosscheck = _compare_lap_times(lap_times, log_laps)

    off_ticks = int(df["offtrack"].astype(int).sum())
    payload: Dict[str, Any] = {
        "schema_version": VERSION,
        "track": track,
        "source_sha256": {
            "csv": csv_sha,
            "log": log_sha,
            "sidecar": sha256_file(sidecar_path),
            "saidas_verdict": saidas_sha,
            "track_file": sha256_file(Path(cfg["file"])),
        },
        "integrity": {
            **integrity,
            **log_integrity,
            "sidecar_present": True,
            "sidecar_bytes": sidecar_path.stat().st_size,
        },
        "sample_rows": int(len(df)),
        "driver_count": int(df["drv"].nunique()),
        "total_ticks": int(reconciliation["total_ticks"]),
        "off_ticks": off_ticks,
        "off_pct": round(100.0 * off_ticks / max(len(df), 1), 3),
        "n_events": int(len(details)),
        "excursions": details,
        "by_corner": _corner_summary(details),
        "lap_times_from_csv_s": lap_times,
        "lap_time_crosscheck": lap_crosscheck,
        "lap_counts": {drv: len(times) for drv, times in lap_times.items()},
        "track_length_m": track_length,
        "steer_saturation_threshold": STEER_SATURATION_RATIO,
    }
    return seal_metrics(payload)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--sidecar", required=True, type=Path)
    parser.add_argument("--track", default="interlagos")
    parser.add_argument("--expect-variedade", type=int, default=None)
    parser.add_argument("--mode", choices=["off", "on"], default="off")
    parser.add_argument("--expect-config-sha256", default=None)
    parser.add_argument("--expected-total-lines", type=int,
                        default=EXPECTED_TOTAL_LINES)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        payload = analyze_run(
            args.csv, args.log, args.sidecar,
            track=args.track,
            expected_variedade=args.expect_variedade,
            mode=args.mode,
            expected_config_sha256=args.expect_config_sha256,
            expected_total_lines=args.expected_total_lines,
        )
    except MetricsIntegrityError as exc:
        print(f"PARE: {exc}", file=sys.stderr)
        return 3
    if args.out is None:
        print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        write_exclusive(args.out, payload)
        print(f"metrics: {args.out} sha256={payload['metrics_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
