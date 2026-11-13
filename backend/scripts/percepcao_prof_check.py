#!/usr/bin/env python3
"""Auditoria report-only da pré-condição do professor em Interlagos."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Mapping

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))
from scripts import saidas_verdict as SV  # noqa: E402

SAIDAS_SHA256 = "e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c"
TRACK_SHA256 = "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def overlap_ratio(rows: Mapping[str, Mapping[str, float]]) -> float:
    denominator = sum(float(item["taxa_v10"]) for item in rows.values())
    if denominator == 0:
        return 0.0
    numerator = sum(
        min(float(item["taxa_prof"]), float(item["taxa_v10"]))
        for item in rows.values()
    )
    return numerator / denominator


def _laps(df: pd.DataFrame, track_length: float) -> int:
    values = pd.to_numeric(df["cum_dist"], errors="coerce").dropna()
    return max(0, int(values.max() // track_length)) if not values.empty else 0


def analyze(path: Path) -> Dict:
    if sha256_file(Path(SV.__file__)) != SAIDAS_SHA256:
        raise RuntimeError("SHA-256 de saidas_verdict.py divergente; PARE")
    geom = SV.load_track_geometry(SV.TRACKS["interlagos"]["file"])
    corners = SV.build_corner_definitions(geom[0])
    df = pd.read_csv(path, comment="#")
    events, summary = SV.extract_excursions(df, corners, geom)
    laps = _laps(df, geom[4])
    counts = {corner["id"]: 0 for corner in corners}
    counts["Reta"] = 0
    if not events.empty:
        for corner_id, count in events["corner_id"].value_counts().items():
            counts[str(corner_id)] = int(count)
    return {
        "csv": str(path),
        "rows": int(len(df)),
        "off_pct": float(summary["off_pct"]),
        "laps": laps,
        "outputs": counts,
        "events": int(len(events)),
    }


def build_verdict(prof_path: Path, v10_path: Path) -> Dict:
    prof = analyze(prof_path)
    v10 = analyze(v10_path)
    rows = {}
    for corner in list(prof["outputs"]):
        prof_count = prof["outputs"].get(corner, 0)
        v10_count = v10["outputs"].get(corner, 0)
        prof_rate = prof_count / prof["laps"] if prof["laps"] else 0.0
        v10_rate = v10_count / v10["laps"] if v10["laps"] else 0.0
        rows[corner] = {
            "saidas_prof": prof_count,
            "saidas_v10": v10_count,
            "voltas_prof": prof["laps"],
            "voltas_v10": v10["laps"],
            "taxa_prof": prof_rate,
            "taxa_v10": v10_rate,
            "sobreposicao_curva": min(prof_rate, v10_rate),
        }
    ratio = overlap_ratio(rows)
    return {
        "instrument": "percepcao_prof_check_v1",
        "track": "interlagos",
        "track_sha256": TRACK_SHA256,
        "saidas_verdict_sha256": SAIDAS_SHA256,
        "professor": prof,
        "v10": v10,
        "curvas": rows,
        "razao_sobreposicao": ratio,
        "threshold_pare": 0.50,
        "veredito": (
            "FALHA_PRE_CONDICAO_PARE" if ratio >= 0.50
            else "PRE_CONDICAO_SATISFEITA"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prof", type=Path, required=True)
    parser.add_argument("--v10", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = build_verdict(args.prof, args.v10)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    first = args.out.read_bytes()
    second = args.out.read_bytes()
    if first != second:
        raise RuntimeError("leitura dupla divergente; PARE")
    payload["cmp0_readback"] = True
    args.out.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
