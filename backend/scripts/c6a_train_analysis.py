#!/usr/bin/env python3
"""REALISMO-1 C6-A — análise offline de trenzinho/deadlock.

Lê somente CSVs já gravados. Não importa simulador, runner, controller ou
modelos e não executa corrida. O braço cego N=1..4 ainda não existe no cache;
o instrumento registra essa ausência sem fabricar dados.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
OUT_DIR = BACKEND / "experiments" / "realismo-1" / "c6"
TRACK_LENGTHS = {"interlagos": 4160.436950117386, "monaco": 3335.2}
HALF_WIDTH_M = 6.0
ROW_S = 0.2
GLUE_LAT_M = 2.0
GLUE_DS_M = 5.5
GLUE_MIN_ROWS = 10       # >2 s at 5 Hz
DEADLOCK_MIN_ROWS = 50   # >10 s at 5 Hz
OFFSET_LIMIT_M = 1.0

COMPOSITE = {
    ("interlagos", 0): "experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.csv",
    ("monaco", 0): "experiments/composite-1/promocao-1/3_R3_MONACO_RACE.csv",
}
for n, stem_i, stem_m in [
    (1, "1_OFF_INTERLAGOS_N1", "2_OFF_MONACO_N1"),
    (2, "3_OFF_INTERLAGOS_N2", "4_OFF_MONACO_N2"),
    (3, "5_OFF_INTERLAGOS_N3", "6_OFF_MONACO_N3"),
    (4, "7_OFF_INTERLAGOS_N4", "8_OFF_MONACO_N4"),
]:
    COMPOSITE[("interlagos", n)] = f"experiments/realismo-1/c0/{stem_i}.csv.gz"
    COMPOSITE[("monaco", n)] = f"experiments/realismo-1/c0/{stem_m}.csv.gz"

BLIND = {
    ("interlagos", 0): "experiments/composite-1/base-2/2_R2_INTERLAGOS_RACE_BLIND.csv",
    ("monaco", 0): "experiments/composite-1/base-2/4_R4_MONACO_RACE_BLIND.csv",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_ds(a: float, b: float, length: float) -> float:
    return (float(b) - float(a) + length / 2.0) % length - length / 2.0


def slot_map(df: pd.DataFrame) -> dict[str, int]:
    first_tick = int(df.tick.min())
    first = df[df.tick == first_tick]
    return {str(drv): i for i, drv in enumerate(first.drv.astype(str).tolist())}


def _pair_episodes(df: pd.DataFrame, length: float) -> list[dict[str, Any]]:
    rows = []
    groups = {str(d): g.sort_values("tick") for d, g in df.groupby("drv", sort=False)}
    drivers = sorted(groups)
    for ia, a in enumerate(drivers):
        for b in drivers[ia + 1:]:
            ga, gb = groups[a], groups[b]
            joined = ga[["tick", "s", "obs4"]].merge(
                gb[["tick", "s", "obs4"]], on="tick", suffixes=("_a", "_b"), how="inner")
            if joined.empty:
                continue
            ds = np.array([signed_ds(x, y, length)
                           for x, y in zip(joined.s_a, joined.s_b)])
            dlat = (joined.obs4_b.to_numpy(float) - joined.obs4_a.to_numpy(float)) * HALF_WIDTH_M
            good = (np.abs(ds) < GLUE_DS_M) & (np.abs(dlat) < GLUE_LAT_M)
            ticks = joined.tick.to_numpy(int)
            start = None
            for i, ok in enumerate(good):
                contiguous = (start is not None and i > 0 and ticks[i] == ticks[i - 1] + 2)
                if ok and start is None:
                    start = i
                elif ok and not contiguous:
                    start = i
                elif not ok or not contiguous:
                    if start is not None:
                        end = i - 1
                        n = end - start + 1
                        if n >= GLUE_MIN_ROWS:
                            rows.append({"drv_a": a, "drv_b": b,
                                         "start_tick": int(ticks[start]),
                                         "end_tick": int(ticks[end]),
                                         "rows": n,
                                         "deadlock": n > DEADLOCK_MIN_ROWS})
                    start = i if ok else None
            if start is not None:
                end = len(good) - 1
                n = end - start + 1
                if n >= GLUE_MIN_ROWS:
                    rows.append({"drv_a": a, "drv_b": b,
                                 "start_tick": int(ticks[start]),
                                 "end_tick": int(ticks[end]),
                                 "rows": n,
                                 "deadlock": n > DEADLOCK_MIN_ROWS})
    return rows


def analyze_csv(path: Path, track: str, profile: str, n: int,
                canonical_metrics: Path | None = None) -> dict[str, Any]:
    df = pd.read_csv(path, comment="#")
    required = {"tick", "t_s", "drv", "s", "obs4", "lat", "offtrack"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path}: missing {missing}")
    df = df.sort_values(["tick", "drv"], kind="stable").reset_index(drop=True)
    length = TRACK_LENGTHS[track]
    episodes = _pair_episodes(df, length)
    glued_rows = int(sum(e["rows"] for e in episodes))
    deadlocks = int(sum(bool(e["deadlock"]) for e in episodes))
    if canonical_metrics is not None and canonical_metrics.is_file():
        canonical = json.loads(canonical_metrics.read_text(encoding="utf-8"))["metrics"]
        glued_rows = int(canonical["glued_rows"])
        deadlocks = int(canonical["deadlocks"])
    train_mask = pd.Series(False, index=df.index)
    # A train row belongs to at least one >2 s glue episode.
    index_by = {(str(r.drv), int(r.tick)): i for i, r in df.iterrows()}
    for e in episodes:
        for tick in range(e["start_tick"], e["end_tick"] + 1, 2):
            for drv in (e["drv_a"], e["drv_b"]):
                i = index_by.get((drv, tick))
                if i is not None:
                    train_mask.iloc[i] = True
    crossings = []
    train_crossings = []
    for drv, g in df.groupby("drv", sort=False):
        g = g.sort_values("tick")
        prev_s = None
        prev_tick = None
        for idx, row in g.iterrows():
            if prev_s is not None and float(row.s) < prev_s - 2000.0:
                crossings.append(int(row.tick))
                if bool(train_mask.iloc[idx]):
                    train_crossings.append(int(row.tick))
            prev_s = float(row.s)
            prev_tick = int(row.tick)
    slots = slot_map(df)
    signed_lat = df.obs4.astype(float) * HALF_WIDTH_M
    baseline_rows = df[(df.offtrack == 0) & (df.t_s >= 1.0) & (df.t_s <= 20.0)].copy()
    baseline_rows["signed_lat_m"] = baseline_rows.obs4.astype(float) * HALF_WIDTH_M
    slot_medians = {}
    for drv, slot in sorted(slots.items(), key=lambda x: x[1]):
        vals = baseline_rows[baseline_rows.drv.astype(str) == drv].signed_lat_m
        slot_medians[str(slot)] = (None if vals.empty else float(vals.median()))
    valid_medians = [v for v in slot_medians.values() if v is not None]
    center = float(np.median(valid_medians)) if valid_medians else 0.0
    offsets = {str(slot): float(np.clip((slot_medians[str(slot)] or center) - center,
                                        -OFFSET_LIMIT_M, OFFSET_LIMIT_M))
               for slot in range(10)}
    return {
        "profile": profile, "track": track, "N": n,
        "source": str(path.relative_to(BACKEND)),
        "source_sha256": sha256_file(path),
        "sample_rows": int(len(df)),
        "drivers": int(df.drv.nunique()),
        "slots": slots,
        "pair_episodes": episodes,
        "metrics": {
            "glued_rows": glued_rows, "glued_s": round(glued_rows * ROW_S, 1),
            "deadlocks": deadlocks, "train_row_fraction": float(train_mask.mean()),
            "train_time_s": round(float(train_mask.sum()) * ROW_S, 1),
            "laps_total": len(crossings), "train_lap_crossings": len(train_crossings),
            "train_lap_fraction": (None if not crossings else len(train_crossings) / len(crossings)),
        },
        "slot_lateral_medians": slot_medians,
        "offset_derivation": {"center_m": center, "offsets_m": offsets,
                              "limit_m": OFFSET_LIMIT_M,
                              "formula": "clip(median_signed_lat_by_slot - pooled_median, -1, +1)"},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    results = []
    for (track, n), rel in sorted(COMPOSITE.items(), key=lambda x: (x[0][0], x[0][1])):
        if n == 0:
            stem = "3_ON_INTERLAGOS_N0" if track == "interlagos" else "4_ON_MONACO_N0"
            canonical = BACKEND / f"experiments/realismo-1/c3/{stem}_realismo.json"
        else:
            stem = (f"{2*n-1}_OFF_INTERLAGOS_N{n}" if track == "interlagos" else
                    f"{2*n}_OFF_MONACO_N{n}")
            canonical = BACKEND / f"experiments/realismo-1/c0/{stem}_realismo.json"
        results.append(analyze_csv(BACKEND / rel, track, "composite", n, canonical))
    blind_available = []
    blind_missing = []
    for track in ("interlagos", "monaco"):
        for n in range(5):
            rel = BLIND.get((track, n))
            if rel is None:
                blind_missing.append({"track": track, "N": n, "reason": "corrida cega N=1..4 não disponível; prevista para C6-B"})
            else:
                blind_available.append(analyze_csv(BACKEND / rel, track, "blind", n))
                results.append(blind_available[-1])
    offsets = {"composite": {}, "blind": {}}
    for profile in offsets:
        items = [r for r in results if r["profile"] == profile]
        for slot in range(10):
            vals = [r["offset_derivation"]["offsets_m"][str(slot)] for r in items]
            offsets[profile][str(slot)] = (None if not vals else float(np.median(vals)))
    payload = {"schema": "c6a-train-analysis-v1", "status": "REPORT_ONLY",
               "no_simulation": True, "results": results,
               "blind_missing": blind_missing, "derived_offsets_m": offsets,
               "offset_limit_m": OFFSET_LIMIT_M,
               "scope_note": "composite N=0..4 + blind N=0 disponíveis; blind N=1..4 reservados ao C6-B"}
    args.out.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    lines = ["# REALISMO-1 C6-A — análise offline de trenzinho", "",
             "**Estado:** report-only, zero simulação, zero alteração de produção.",
             "", "## Escopo", "",
             "Foram analisados composite OFF N=0..4 e blind N=0. Blind N=1..4 não existe no cache e permanece orçamento do C6-B.",
             "", "## Métricas", "", "| Perfil | Pista | N | colado s | deadlocks | fração tempo trem | voltas | fração voltas trem |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        m = r["metrics"]
        lines.append(f"| {r['profile']} | {r['track']} | {r['N']} | {m['glued_s']:.1f} | {m['deadlocks']} | {m['train_row_fraction']:.4f} | {m['laps_total']} | {m['train_lap_fraction'] if m['train_lap_fraction'] is not None else 'n/a'} |")
    lines += ["", "## Derivação dos offsets", "", "Os offsets são a mediana entre corridas disponíveis de `median_signed_lat_by_slot - pooled_median`, limitada a ±1,0 m. A aplicação C6-B deverá alterar somente `obs4` por `tels[i,4] = (signed - off_i)/hw`; a física e o CSV continuam físicos.", "", "| Slot | Composite m | Blind m |", "|---:|---:|---:|"]
    for i in range(10): lines.append(f"| {i} | {offsets['composite'].get(str(i))} | {offsets['blind'].get(str(i))} |")
    lines += ["", "## Dados ausentes e decisão", "", "- Não há corridas blind N=1..4; portanto a matriz completa C6-A dos dois perfis não existe ainda.", "- A análise não promove a flag nem autoriza C6-B.", "- O Dono deve decidir se o padrão composite é mensurável e congelar o prereg C6 antes das corridas cegas N=1..4.", "", "## Encerramento", "", "C6-A termina aqui para revisão e Freeze do Dono."]
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
