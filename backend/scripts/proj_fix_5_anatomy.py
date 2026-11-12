#!/usr/bin/env python3
"""PROJ-FIX-5 v1.0: report-only anatomy from the frozen classified map."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


VERSION = "1.0"
BACKEND = Path(__file__).resolve().parents[1]
EXPERIMENT = BACKEND / "experiments" / "proj-fix-1"
MAP_PATH = EXPERIMENT / "classificacao_v12" / "mapa_nit2_ge10.csv"
SUMMARY_PATH = EXPERIMENT / "classificacao_v12" / "resumo_classes.json"
OUT_DIR = EXPERIMENT / "anatomia_v10"
EXPECTED_MAP_SHA256 = "1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f"
EXPECTED_SUMMARY_SHA256 = "9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05"
METRICS = ("delta_s_wrapped_m", "delta_cum_dist_m", "d_ns_raw")


class StopGate(RuntimeError):
    """A preregistered reconciliation or source-integrity gate failed."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def quantile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    position = p * (len(xs) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return xs[lower] * (1.0 - weight) + xs[upper] * weight


def finite_number(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise StopGate(f"campo inválido: {field}") from exc
    if not math.isfinite(value):
        raise StopGate(f"valor não finito: {field}")
    return value


def int_number(row: dict[str, str], field: str) -> int:
    value = finite_number(row, field)
    if not value.is_integer():
        raise StopGate(f"checkpoint não inteiro: {field}")
    return int(value)


def class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["class_xy_ns"]) for row in rows)
    return {name: counts[name] for name in ("C1", "C2", "C3", "C4", "C5") if counts[name]}


def validate(rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    actual_classes = Counter(str(row.get("class_xy_ns", "")) for row in rows)
    expected = {"C3": 46, "C5": 66}
    if len(rows) != 112:
        raise StopGate(f"mapa tem {len(rows)} linhas; esperado 112")
    if {k: actual_classes[k] for k in expected} != expected or sum(actual_classes.values()) != 112:
        raise StopGate(f"classes do mapa divergiram: {dict(actual_classes)}")

    mapping = summary.get("nit2_ge10_mapping", {})
    if {k: int(mapping.get(k, -1)) for k in ("C1", "C2", "C3", "C5")} != {
        "C1": 0, "C2": 0, "C3": 46, "C5": 66
    }:
        raise StopGate("nit2_ge10_mapping não reconcilia com 0/0/46/66")
    headline = summary.get("headline_ge30_mapping", {})
    if {k: int(headline.get(k, -1)) for k in ("C1", "C2", "C3", "C5")} != {
        "C1": 0, "C2": 0, "C3": 45, "C5": 0
    }:
        raise StopGate("headline_ge30_mapping não reconcilia com 0/0/45/0")
    reconciliation = summary.get("reconciliation", {})
    if any(int(reconciliation.get(key, -1)) != 112 for key in ("historical_ge10", "mapped_ge10")):
        raise StopGate("reconciliation não confirma 112/112 eventos ≥10 m")
    if int(reconciliation.get("historical_ge30", -1)) != 45 or int(reconciliation.get("mapped_ge30", -1)) != 45:
        raise StopGate("reconciliation não confirma 45/45 eventos headline")

    authority = Counter(row.get("authority", "") for row in rows)
    authority_class: dict[str, Counter[str]] = defaultdict(Counter)
    offtrack = Counter(row.get("offtrack", "") for row in rows)
    for row in rows:
        authority_class[row.get("authority", "")][row["class_xy_ns"]] += 1
    if authority != Counter({"rejoin": 112}):
        raise StopGate(f"authority divergiu do mapa publicado: {dict(authority)}")
    if offtrack != Counter({"1": 112}):
        raise StopGate(f"offtrack divergiu do mapa publicado: {dict(offtrack)}")

    checkpoints = [
        (str(row["drv"]), int_number(row, "tick_prev"), int_number(row, "tick"))
        for row in rows
    ]
    if len(set(checkpoints)) != 112:
        raise StopGate("chave de checkpoint (drv,tick_prev,tick) não é única")
    checkpoint_classes = Counter(str(row["class_xy_ns"]) for row in rows)
    if checkpoint_classes["C3"] != 46 or checkpoint_classes["C5"] != 66:
        raise StopGate("checkpoint não reproduz C3/C5=46/66")

    return {
        "map_rows": len(rows),
        "map_class_counts": {"C3": actual_classes["C3"], "C5": actual_classes["C5"]},
        "summary_class_counts": {"C3": int(mapping["C3"]), "C5": int(mapping["C5"])},
        "headline_counts": {"C3": int(headline["C3"]), "C5": int(headline["C5"])},
        "authority_counts": dict(authority),
        "authority_class_counts": {
            name: {"C3": values["C3"], "C5": values["C5"]}
            for name, values in sorted(authority_class.items())
        },
        "offtrack_counts": dict(offtrack),
        "checkpoint_basis": "(drv,tick_prev,tick)",
        "unique_checkpoints": len(set(checkpoints)),
        "checkpoint_class_counts": {"C3": checkpoint_classes["C3"], "C5": checkpoint_classes["C5"]},
    }


def anatomy(rows: list[dict[str, Any]], reconciliation: dict[str, Any]) -> dict[str, Any]:
    by_class: dict[str, dict[str, Any]] = {}
    for label in ("C3", "C5"):
        subset = [row for row in rows if row["class_xy_ns"] == label]
        by_class[label] = {"count": len(subset), "metrics": {}}
        for field in METRICS:
            values = [finite_number(row, field) for row in subset]
            by_class[label]["metrics"][field] = {
                "p50": quantile(values, 0.50),
                "p95": quantile(values, 0.95),
                "max": max(values) if values else None,
            }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["drv"])].append(row)
    per_car = []
    for driver, events in sorted(grouped.items()):
        events.sort(key=lambda row: finite_number(row, "t_s"))
        times = [finite_number(row, "t_s") for row in events]
        ticks = [int_number(row, "tick") for row in events]
        sec_gaps = [b - a for a, b in zip(times, times[1:])]
        tick_gaps = [b - a for a, b in zip(ticks, ticks[1:])]
        lap_count = None
        per_car.append({
            "driver": driver,
            "events": len(events),
            "mean_interval_s": sum(sec_gaps) / len(sec_gaps) if sec_gaps else None,
            "mean_interval_ticks": sum(tick_gaps) / len(tick_gaps) if tick_gaps else None,
            "events_per_lap": None,
            "lap_count": lap_count,
            "lap_cadence_status": "unavailable: lap denominator absent from permitted sources",
        })

    return {
        "version": VERSION,
        "per_class": by_class,
        "per_car": per_car,
        "coherence": reconciliation,
        "definitions": {
            "signed_values": True,
            "quantile": "linear interpolation at p*(n-1)",
            "lap_cadence": "unavailable; neither permitted input contains lap identity or total lap count",
            "mean_interval": "arithmetic mean of consecutive t_s differences; ticks also reported",
        },
    }


def markdown_report(result: dict[str, Any], source_hashes: dict[str, str]) -> str:
    lines = [
        "# PROJ-FIX-5 — anatomia v1.0",
        "",
        "Report-only; fonte limitada ao mapa NIT-2 e ao resumo v1.2.",
        "",
        "## Saltos por classe",
        "",
        "Valores assinados; p50/p95 usam interpolação linear. Máximo é o maior valor com sinal.",
        "",
        "| Classe | n | Métrica | p50 | p95 | máximo |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for cls in ("C3", "C5"):
        block = result["per_class"][cls]
        for field in METRICS:
            stats = block["metrics"][field]
            lines.append(f"| {cls} | {block['count']} | `{field}` | {stats['p50']:.9g} | {stats['p95']:.9g} | {stats['max']:.9g} |")
    lines += [
        "",
        "## Eventos por carro",
        "",
        "| Carro | Eventos | Eventos/volta | Intervalo médio (s) | Intervalo médio (ticks) |",
        "|---|---:|---:|---:|---:|",
    ]
    for car in result["per_car"]:
        interval_s = "n/a" if car["mean_interval_s"] is None else f"{car['mean_interval_s']:.9g}"
        interval_ticks = "n/a" if car["mean_interval_ticks"] is None else f"{car['mean_interval_ticks']:.9g}"
        lines.append(f"| {car['driver']} | {car['events']} | n/a* | {interval_s} | {interval_ticks} |")
    lines += [
        "",
        "* Eventos/volta indisponível: as fontes autorizadas não trazem volta por evento nem total de voltas; `s` não foi usado como substituto porque é o ponteiro em análise.",
        "",
        "## Coerência",
        "",
        f"- Mapa/resumo: {result['coherence']['map_rows']}/{result['coherence']['map_rows']} linhas; C3={result['coherence']['map_class_counts']['C3']}; C5={result['coherence']['map_class_counts']['C5']}.",
        f"- Autoridade: {result['coherence']['authority_counts']}; offtrack: {result['coherence']['offtrack_counts']}; checkpoints únicos por `{result['coherence']['checkpoint_basis']}`: {result['coherence']['unique_checkpoints']}.",
        f"- Hash mapa: `{source_hashes['map']}`.",
        f"- Hash resumo: `{source_hashes['summary']}`.",
        "",
        "## Limite",
        "",
        "A tabela não estima voltas, não lê replay e não mede dXY físico. As contagens públicas de PROJ-FIX-4 não foram reavaliadas além da reconciliação de integridade pinada.",
        "",
    ]
    return "\n".join(lines)


def selftest() -> None:
    assert quantile([0.0, 10.0], 0.5) == 5.0
    assert quantile([-3.0, 1.0, 9.0], 0.5) == 1.0
    assert quantile([], 0.95) is None
    synthetic = []
    for i in range(112):
        synthetic.append({
            "class_xy_ns": "C3" if i < 46 else "C5",
            "authority": "rejoin",
            "offtrack": "1",
            "drv": f"D{i % 10:02d}",
            "tick_prev": str(i * 2),
            "tick": str(i * 2 + 1),
            "t_s": str(i / 5),
            "delta_s_wrapped_m": str(i - 40),
            "delta_cum_dist_m": str(i / 10),
            "d_ns_raw": str(i % 20),
        })
    good_summary = {
        "nit2_ge10_mapping": {"C1": 0, "C2": 0, "C3": 46, "C5": 66},
        "headline_ge30_mapping": {"C1": 0, "C2": 0, "C3": 45, "C5": 0},
        "reconciliation": {"historical_ge10": 112, "mapped_ge10": 112, "historical_ge30": 45, "mapped_ge30": 45},
    }
    coherent = validate(synthetic, good_summary)
    result = anatomy(synthetic, coherent)
    assert result["per_class"]["C3"]["count"] == 46
    assert result["per_class"]["C5"]["count"] == 66
    assert len(result["per_car"]) == 10
    assert result["per_car"][0]["events"] > 1
    assert result["per_car"][0]["events_per_lap"] is None
    try:
        validate(synthetic[:-1] + [{**synthetic[-1], "class_xy_ns": "C3"}], good_summary)
    except StopGate:
        pass
    else:
        raise AssertionError("class count mismatch must stop")
    try:
        duplicate = list(synthetic)
        duplicate[-1] = {**duplicate[-1], "drv": synthetic[0]["drv"], "tick_prev": synthetic[0]["tick_prev"], "tick": synthetic[0]["tick"]}
        validate(duplicate, good_summary)
    except StopGate:
        pass
    else:
        raise AssertionError("duplicate checkpoint must stop")
    print(f"PROJ-FIX-5 anatomy selftest v{VERSION}: PASS (synthetic; no CSV/JSON opened)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run synthetic checks without reading inputs")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0

    try:
        map_hash = sha256(MAP_PATH)
        summary_hash = sha256(SUMMARY_PATH)
        if map_hash != EXPECTED_MAP_SHA256:
            raise StopGate(f"hash do mapa divergente: {map_hash}")
        if summary_hash != EXPECTED_SUMMARY_SHA256:
            raise StopGate(f"hash do resumo divergente: {summary_hash}")
        with MAP_PATH.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        with SUMMARY_PATH.open("r", encoding="utf-8") as f:
            summary = json.load(f)
        reconciliation = validate(rows, summary)
        result = anatomy(rows, reconciliation)
        result["source_hashes"] = {"map": map_hash, "summary": summary_hash}

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUT_DIR / "20_anatomia_v10.json"
        md_path = OUT_DIR / "21_anatomia_v10.md"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(markdown_report(result, result["source_hashes"]), encoding="utf-8")
        output_hashes = {p.name: sha256(p) for p in (json_path, md_path)}
        hash_path = OUT_DIR / "22_sha256.log"
        hash_path.write_text(
            "PROJ-FIX-5 anatomy v1.0\n"
            f"mapa_nit2_ge10.csv {map_hash}\n"
            f"resumo_classes.json {summary_hash}\n"
            f"20_anatomia_v10.json {output_hashes[json_path.name]}\n"
            f"21_anatomia_v10.md {output_hashes[md_path.name]}\n",
            encoding="utf-8",
        )
        print("PROJ-FIX-5 anatomy v1.0: PASS")
        for path in (json_path, md_path, hash_path):
            print(f"{path.relative_to(BACKEND)} sha256={sha256(path)}")
        return 0
    except (OSError, json.JSONDecodeError, StopGate, KeyError) as exc:
        print(f"PARE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
