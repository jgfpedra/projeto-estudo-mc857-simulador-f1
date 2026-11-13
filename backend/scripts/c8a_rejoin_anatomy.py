#!/usr/bin/env python3
"""C8-A: report-only anatomy of the promoted rejoin path.

This instrument reads existing C8-0 and REALISMO-1 C7 CSVs.  It does not
import the runner, controllers, models, or simulation engine and never starts
a simulation.
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
TRACK_LENGTHS = {"interlagos": 4160.436950117386, "monaco": 3335.2}
DT_S = 0.2
REENTRY_HORIZON_S = 10.0
SAFE_REENTRY_WINDOW_S = 5.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_gap(a: float, b: float, length: float) -> float:
    return (float(b) - float(a) + length / 2.0) % length - length / 2.0


def gap_at_reentry(
    frame: pd.DataFrame, driver: str, tick: int, track_length: float
) -> dict[str, float | None]:
    """Return nearest longitudinal gaps at one tick, excluding ``driver``."""
    row = frame[(frame["tick"] == tick) & (frame["drv"].astype(str) == driver)]
    if row.empty:
        raise ValueError(f"missing {driver=} at tick {tick}")
    ego_s = float(row.iloc[0]["s"])
    peers = frame[(frame["tick"] == tick) & (frame["drv"].astype(str) != driver)]
    ahead, behind = [], []
    for peer_s in peers["s"].astype(float):
        gap = signed_gap(ego_s, peer_s, track_length)
        if gap > 0:
            ahead.append(gap)
        elif gap < 0:
            behind.append(abs(gap))
    return {
        "ahead_m": None if not ahead else float(min(ahead)),
        "behind_m": None if not behind else float(min(behind)),
    }


def _transitions(values: pd.Series, on_value: int) -> list[int]:
    vals = values.astype(int).to_numpy()
    ticks = values.index.to_numpy()
    return [
        int(ticks[i])
        for i in range(1, len(vals))
        if vals[i] == on_value and vals[i - 1] != on_value
    ]


def find_reentry_windows(
    frame: pd.DataFrame,
    track_length: float,
    horizon_s: float = REENTRY_HORIZON_S,
    safe_window_s: float = SAFE_REENTRY_WINDOW_S,
) -> list[dict[str, Any]]:
    """Find offtrack->ontrack windows and classify local post-return risk."""
    events: list[dict[str, Any]] = []
    for driver, group in frame.groupby(frame["drv"].astype(str), sort=True):
        group = group.sort_values("tick").reset_index(drop=True)
        off = group["offtrack"].astype(int).to_numpy()
        ticks = group["tick"].astype(int).to_numpy()
        for i in range(1, len(group)):
            if off[i - 1] != 1 or off[i] != 0:
                continue
            start = i - 1
            while start > 0 and off[start - 1] == 1:
                start -= 1
            reentry_tick = int(ticks[i])
            reentry_t = float(group.iloc[i]["t_s"])
            gap = gap_at_reentry(frame, driver, reentry_tick, track_length)
            behind = gap["behind_m"]
            ahead = gap["ahead_m"]
            direction = (
                "behind"
                if ahead is None or (behind is not None and behind <= ahead)
                else "ahead"
            )
            window = group[
                (group["t_s"] > reentry_t)
                & (group["t_s"] <= reentry_t + horizon_s + 1e-9)
            ]
            safe_window = window[
                window["t_s"] <= reentry_t + safe_window_s + 1e-9
            ]
            exits = int(
                ((safe_window["offtrack"].astype(int).shift(fill_value=0) == 1)
                 & (safe_window["offtrack"].astype(int) == 0)).sum()
            )
            # car_car is a per-row contact count in the diagnostic CSV.
            contacts = int((safe_window["car_car"].astype(float) > 0).sum())
            events.append(
                {
                    "driver": driver,
                    "reentry_tick": reentry_tick,
                    "reentry_t_s": reentry_t,
                    "offtrack_duration_s": round((i - start) * DT_S, 3),
                    "speed_mps": float(group.iloc[i]["speed"]),
                    "abs_lat_m": abs(float(group.iloc[i]["lat"])),
                    "gap_ahead_m": gap["ahead_m"],
                    "gap_behind_m": gap["behind_m"],
                    "risk_direction": direction,
                    "contacts_within_5s": contacts,
                    "new_exits_within_5s": exits,
                    "contacts_within_10s": int(
                        (window["car_car"].astype(float) > 0).sum()
                    ),
                    "new_exits_within_10s": int(
                        ((window["offtrack"].astype(int).shift(fill_value=0) == 1)
                         & (window["offtrack"].astype(int) == 0)).sum()
                    ),
                }
            )
    return events


def _episode_profile(frame: pd.DataFrame) -> dict[str, Any]:
    """Summarize speed and lateral excursion during contiguous offtrack spans."""
    episodes: list[dict[str, Any]] = []
    for driver, group in frame.groupby(frame["drv"].astype(str), sort=True):
        group = group.sort_values("tick").reset_index(drop=True)
        mask = group["offtrack"].astype(int).to_numpy()
        start = None
        for i, value in enumerate(np.r_[mask, 0]):
            if value and start is None:
                start = i
            if start is None or value:
                continue
            span = group.iloc[start:i]
            duration = len(span) * DT_S
            episodes.append(
                {
                    "driver": driver,
                    "start_t_s": float(span.iloc[0]["t_s"]),
                    "duration_s": round(duration, 3),
                    "speed_mean_mps": float(span["speed"].mean()),
                    "speed_median_mps": float(span["speed"].median()),
                    "abs_lat_max_m": float(span["lat"].abs().max()),
                    "rows": int(len(span)),
                }
            )
            start = None
    durations = [e["duration_s"] for e in episodes]
    return {
        "episodes": episodes,
        "episode_count": len(episodes),
        "duration_total_s": round(sum(durations), 3),
        "speed_mean_mps": (
            None if not episodes else float(np.mean([e["speed_mean_mps"] for e in episodes]))
        ),
        "speed_by_time_outside_s": {
            label: (
                None
                if part.empty
                else float(part["speed"].mean())
            )
            for label, part in (
                ("0-1", frame[frame["offtrack"].astype(int).eq(1) & (frame["t_s"] <= 1)]),
                ("1-2", frame[frame["offtrack"].astype(int).eq(1) & (frame["t_s"] > 1) & (frame["t_s"] <= 2)]),
                ("2-5", frame[frame["offtrack"].astype(int).eq(1) & (frame["t_s"] > 2) & (frame["t_s"] <= 5)]),
                ("5+", frame[frame["offtrack"].astype(int).eq(1) & (frame["t_s"] > 5)]),
            )
        },
    }


def analyze_csv(path: Path, track: str, label: str, n: int) -> dict[str, Any]:
    frame = pd.read_csv(path, comment="#")
    required = {"tick", "t_s", "drv", "speed", "s", "lat", "offtrack", "authority", "car_car"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    frame = frame.sort_values(["tick", "drv"], kind="stable").reset_index(drop=True)
    reentries = find_reentry_windows(frame, TRACK_LENGTHS[track])
    authority = (
        frame.groupby("authority", dropna=False)
        .size()
        .sort_values(ascending=False)
        .astype(int)
        .to_dict()
    )
    reasons = (
        frame["rejoin_handoff_end_reason"]
        .dropna()
        .astype(str)
        .value_counts()
        .astype(int)
        .to_dict()
        if "rejoin_handoff_end_reason" in frame
        else {}
    )
    outside = frame[frame["offtrack"].astype(int).eq(1)]
    stuck_proxy = outside[outside["speed"].astype(float) < 5.0]
    return {
        "label": label,
        "track": track,
        "N": n,
        "source": str(path.relative_to(BACKEND)),
        "source_sha256": sha256_file(path),
        "sample_rows": int(len(frame)),
        "outside_rows": int(len(outside)),
        "outside_pct": round(float(100.0 * len(outside) / len(frame)), 4),
        "outside_stuck_proxy_rows": int(len(stuck_proxy)),
        "authority_rows": authority,
        "handoff_end_reasons": reasons,
        "ramp_active_rows": int(frame["rejoin_ramp_active"].astype(int).sum()),
        "grass_profile": _episode_profile(frame),
        "reentries": reentries,
        "reentry_count": len(reentries),
        "risk_summary": {
            "contacts_within_5s": sum(e["contacts_within_5s"] for e in reentries),
            "new_exits_within_5s": sum(e["new_exits_within_5s"] for e in reentries),
            "contacts_within_10s": sum(e["contacts_within_10s"] for e in reentries),
            "new_exits_within_10s": sum(e["new_exits_within_10s"] for e in reentries),
            "by_direction": {
                direction: {
                    "reentries": sum(e["risk_direction"] == direction for e in reentries),
                    "contacts_within_5s": sum(
                        e["contacts_within_5s"]
                        for e in reentries
                        if e["risk_direction"] == direction
                    ),
                    "new_exits_within_5s": sum(
                        e["new_exits_within_5s"]
                        for e in reentries
                        if e["risk_direction"] == direction
                    ),
                }
                for direction in ("behind", "ahead")
            },
        },
    }


def default_inputs() -> list[tuple[Path, str, str, int]]:
    root = BACKEND / "experiments" / "c8-rejoin" / "c8-0"
    inputs = []
    for track, prefix in (("interlagos", "INT"), ("monaco", "MON")):
        for n in range(5):
            inputs.append((root / f"{prefix}_N{n}.csv", "c8-0", track, n))
    c7 = BACKEND / "experiments" / "realismo-1" / "c7"
    for path in sorted(c7.glob("*_ON_*.csv")):
        if path.stem.endswith("_events"):
            continue
        parts = path.stem.split("_")
        track = parts[2].lower()
        n = int(parts[-1][1:])
        inputs.append((path, "c7-on", track, n))
    return inputs


def render_report(payload: dict[str, Any]) -> str:
    lines = [
        "# C8-A — achados da anatomia do rejoin",
        "",
        "**Estado:** report-only; zero simulação nova e zero alteração de produção.",
        "",
        "## Regra de ouro das constantes",
        "",
        "Toda constante numérica do C8 sai só do N=0: o perfil de velocidade na grama e os limiares do gap-check (gap, janela, teto). A anatomia de risco da reentrada (carro atrás × à frente, gap na reentrada), medida em N=0..4 e no C7 ON, entra como disclosure: ela só escolhe a forma do gap-check (direção e ponto de entrada) e nunca fixa um número.",
        "",
        "O instrumento usa N=0 apenas para o perfil de velocidade e para os valores a serem congelados no preregistro; N=1..4 e C7 ON são apenas divulgação.",
        "",
        "## Resumo das fontes",
        "",
        "| Fonte | Corridas | Reentradas | Fora (%) | Fora-preso proxy (v < 5 m/s) | Novas saídas <=5 s | Contatos <=5 s |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in payload["runs"]:
        r = item["risk_summary"]
        lines.append(
            f"| {item['label']} {item['track']} N={item['N']} | 1 | {item['reentry_count']} | "
            f"{item['outside_pct']:.2f} | {item['outside_stuck_proxy_rows']} | "
            f"{r['new_exits_within_5s']} | {r['contacts_within_5s']} |"
        )
    n0 = [x for x in payload["runs"] if x["label"] == "c8-0" and x["N"] == 0]
    lines += [
        "",
        "## Perfil congelável de N=0",
        "",
        "O perfil abaixo é o único candidato a fornecer constantes para o C8. Os demais resultados não alteram esses números.",
        "",
        "```json",
        json.dumps(n0, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Anatomia de risco",
        "",
        "A direção `behind`/`ahead` é uma classificação geométrica do menor gap longitudinal no instante da reentrada; ela não atribui causalidade física a um contato específico. Os eventos pós-retorno são contagens observacionais em janelas de 5 s e 10 s.",
        "",
        "| Fonte | Direção | Reentradas | Contatos <=5 s | Saídas <=5 s |",
        "|---|---|---:|---:|---:|",
    ]
    for item in payload["runs"]:
        for direction, data in item["risk_summary"]["by_direction"].items():
            lines.append(
                f"| {item['label']} {item['track']} N={item['N']} | {direction} | "
                f"{data['reentries']} | {data['contacts_within_5s']} | {data['new_exits_within_5s']} |"
            )
    lines += [
        "",
        "## Limitações",
        "",
        "- O CSV registra `car_car` por linha, mas não identifica o par causal do contato; por isso a separação frente/trás é uma classificação por gap, não uma atribuição de causa.",
        "- O proxy de FORA-PRESO é report-only (`offtrack` e velocidade abaixo de 5 m/s); a definição oficial de preso continua sendo a do diagnóstico R3.",
        "- O C7 ON foi incluído somente para disclosure.",
        "",
        "## Encerramento",
        "",
        "Os achados não promovem o mecanismo C8. O próximo passo permitido é o Freeze do Dono do `PREREG_C8.md`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=BACKEND / "experiments/c8-rejoin/c8/C8A_FINDINGS.json")
    parser.add_argument("--report", type=Path, default=BACKEND / "experiments/c8-rejoin/c8/C8A_FINDINGS.md")
    args = parser.parse_args()
    runs = [
        analyze_csv(path, track, label, n)
        for path, label, track, n in default_inputs()
        if path.is_file()
    ]
    payload = {
        "schema": "c8a-rejoin-anatomy-v1",
        "status": "REPORT_ONLY",
        "no_simulation": True,
        "constants_source": "c8-0 N=0 only",
        "reentry_horizon_s": REENTRY_HORIZON_S,
        "safe_reentry_window_s": SAFE_REENTRY_WINDOW_S,
        "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(render_report(payload), encoding="utf-8")
    print(f"[c8a] analyzed {len(runs)} existing runs; no simulation")
    print(f"[c8a] json={args.out} report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
