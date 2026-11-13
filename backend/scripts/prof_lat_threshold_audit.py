#!/usr/bin/env python3
"""PROF-GRIP-1 (sequência) — auditoria de limiares de margem lateral e custo
de desaceleração. Report-only, determinístico, offline (zero corrida nova).

Sobre os controles OFF existentes do PROF-GRIP-1 (bit-idênticos ao histórico:
``corridas/CTRL_Interlagos_OFF.csv`` e ``CTRL_Monaco_OFF.csv``), varre a grade
de limiares de afastamento lateral ``|lat| >= {3,5, 4,0, 4,5, 5,0} m`` e
quantifica, por pista × limiar:

a) ticks em violação e % do tempo de corrida;
b) eventos contíguos (ativações) e duração média em segundos (5 Hz, dt=0,2 s);
c) mapeamento por setor via ``match_corner`` canônico: eventos nas 4 crônicas
   (C01/C06/C07/C08) vs outras curvas vs Reta (o setor do evento = mediana de
   s dentro do evento);
d) velocidade média e máxima durante a violação;
e) custo de desaceleração: por evento, o tempo para reduzir a velocidade
   característica (média do evento) em 10% e 20% com ``a_brake = 15 m/s²`` —
   ``t = Δv/a_brake`` — e a projeção somada por corrida e por volta.

Saídas exclusivas (determinísticas, ``cmp=0`` entre execuções):
``experiments/prof-grip-1/LAT_THRESHOLD_AUDIT.json`` e ``.md``.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from scripts import saidas_verdict as SV  # noqa: E402
from scripts.prof_lago_anatomy import (  # noqa: E402  canônicos
    segment_laps,
    sha256_file,
)

VERSION = "prof-grip-1/lat-threshold-audit-v1.0"

CORRIDAS = BACKEND / "experiments" / "prof-grip-1" / "corridas"
SOURCES = [
    ("interlagos", CORRIDAS / "CTRL_Interlagos_OFF.csv",
     BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json",
     "164876196eb12174"),
    ("Monaco", CORRIDAS / "CTRL_Monaco_OFF.csv",
     BACKEND / "model_train" / "tracks_frozen" / "Monaco_v2.json",
     "67ca11dc211c8c78"),
]
THRESHOLDS = [3.5, 4.0, 4.5, 5.0]
DT_S = 0.2                   # 5 Hz
A_BRAKE = 15.0               # m/s² (pinado no mandato)
DELTAS_V = [0.10, 0.20]      # frações da velocidade característica do evento
CRONICAS = ("C01", "C06", "C07", "C08")
HALF_WIDTH_M = 6.0

OUT_JSON = BACKEND / "experiments" / "prof-grip-1" / "LAT_THRESHOLD_AUDIT.json"
OUT_MD = BACKEND / "experiments" / "prof-grip-1" / "LAT_THRESHOLD_AUDIT.md"


def contiguous_events(mask: np.ndarray) -> List[Tuple[int, int]]:
    """Runs contíguos [start, end] (inclusive) onde mask é True."""
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    breaks = np.where(np.diff(idx) > 1)[0]
    starts = np.concatenate([[idx[0]], idx[breaks + 1]])
    ends = np.concatenate([idx[breaks], [idx[-1]]])
    return [(int(a), int(b)) for a, b in zip(starts, ends)]


def decel_cost_s(v_char_mps: float, delta_frac: float,
                 a_brake: float = A_BRAKE) -> float:
    """Tempo para reduzir a velocidade em delta_frac·v com a_brake."""
    if v_char_mps < 0.0 or not 0.0 < delta_frac <= 1.0 or a_brake <= 0.0:
        raise ValueError("parâmetros de custo de desaceleração inválidos")
    return float(delta_frac * v_char_mps / a_brake)


def sector_of(s_median: float, corners: Sequence[Dict[str, Any]],
              track_len: float) -> str:
    cid, _ = SV.match_corner(s_median, corners, track_len)
    return cid


def threshold_audit(rows: pd.DataFrame, threshold: float,
                    corners: Sequence[Dict[str, Any]],
                    track_len: float, n_laps: int) -> Dict[str, Any]:
    lat = rows["lat"].to_numpy(float)
    v = rows["speed"].to_numpy(float)
    s = rows["s"].to_numpy(float)
    mask = lat >= threshold
    n_ticks = int(mask.sum())
    events = contiguous_events(mask)
    ev_rows = []
    sector_counts: Dict[str, int] = {}
    for (a, b) in events:
        s_med = float(np.median(s[a:b + 1]))
        cid = sector_of(s_med, corners, track_len)
        sector_counts[cid] = sector_counts.get(cid, 0) + 1
        v_mean_ev = float(v[a:b + 1].mean())
        ev_rows.append({
            "n_ticks": b - a + 1,
            "dur_s": round((b - a + 1) * DT_S, 2),
            "t_start_s": round(float(rows["t_s"].iloc[a]), 3),
            "s_med_m": round(s_med, 3),
            "setor": cid,
            "v_media_mps": round(v_mean_ev, 3),
        })
    cronicas_n = sum(n for k, n in sector_counts.items() if k in CRONICAS)
    reta_n = sector_counts.get("Reta", 0)
    outras_n = sum(n for k, n in sector_counts.items()
                   if k not in CRONICAS and k != "Reta")
    viol_v = v[mask]
    total_cost = {str(d): 0.0 for d in DELTAS_V}
    for ev in ev_rows:
        for d in DELTAS_V:
            total_cost[str(d)] += decel_cost_s(ev["v_media_mps"], d)
    durs = [e["dur_s"] for e in ev_rows]
    return {
        "limiar_m": threshold,
        "ticks_violacao": n_ticks,
        "pct_tempo": round(100.0 * n_ticks / max(len(rows), 1), 4),
        "n_eventos": len(events),
        "duracao_media_s": round(float(np.mean(durs)), 3) if durs else None,
        "duracao_max_s": round(float(np.max(durs)), 3) if durs else None,
        "setores": {
            "cronicas_C01_C06_C07_C08": cronicas_n,
            "outras_curvas": outras_n,
            "reta": reta_n,
            "por_curva": dict(sorted(sector_counts.items())),
        },
        "v_media_violacao_mps": round(float(viol_v.mean()), 3) if n_ticks else None,
        "v_max_violacao_mps": round(float(viol_v.max()), 3) if n_ticks else None,
        "custo_desaceleracao": {
            "a_brake_ms2": A_BRAKE,
            "delta_v": DELTAS_V,
            "total_projeta_s_por_corrida": {str(d): round(total_cost[str(d)], 3)
                                            for d in DELTAS_V},
            "total_projeta_s_por_volta": {str(d): round(total_cost[str(d)] / n_laps, 3)
                                          for d in DELTAS_V} if n_laps else None,
        },
        "eventos": ev_rows,
    }


def analyze_csv(csv_path: Path, track_path: Path, track_pin: str,
                track_label: str) -> Dict[str, Any]:
    csv_sha = sha256_file(csv_path)
    with track_path.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != track_pin:
        raise ValueError(f"SHA da pista divergente: {track_path}")
    wps = np.array(track["waypoints"], dtype=np.float64)
    corners = SV.build_corner_definitions(
        wps, kappa_thresh=0.006, merge_gap_m=40.0, generic_names=False)
    closed = np.vstack([wps, wps[:1]])
    track_len = float(np.hypot(*np.diff(closed, axis=0).T).sum())

    df = pd.read_csv(csv_path, comment="#")
    n_laps = int(segment_laps(df["s"].to_numpy(float), track_len).max() + 1)

    por_limiar = {}
    for th in THRESHOLDS:
        por_limiar[str(th)] = threshold_audit(df, th, corners, track_len, n_laps)
    return {
        "pista": track_label,
        "csv": str(csv_path.relative_to(BACKEND)),
        "csv_sha256_prefix": csv_sha[:16],
        "track_sha256_pin": track_pin,
        "comprimento_m": round(track_len, 3),
        "n_linhas_dados": int(len(df)),
        "n_laps": n_laps,
        "por_limiar": por_limiar,
    }


def main() -> int:
    for _, csv_path, _, _ in SOURCES:
        if not csv_path.exists():
            print(f"ERRO: telemetria ausente: {csv_path}", file=sys.stderr)
            return 2
    tracks = []
    for label, csv_path, track_path, pin in SOURCES:
        tracks.append(analyze_csv(csv_path, track_path, pin, label))

    payload = {
        "schema_version": VERSION,
        "metodo": {
            "limiares_m": THRESHOLDS,
            "dt_s": DT_S,
            "a_brake_ms2": A_BRAKE,
            "delta_v": DELTAS_V,
            "setor_do_evento": "mediana de s dentro do evento → match_corner canônico",
            "custo": "t = Δv/a_brake com Δv = fração da v média do evento; "
                     "projeção somada por corrida e dividida por volta",
        },
        "pistas": tracks,
    }

    for out in (OUT_JSON, OUT_MD):
        if out.exists():
            print(f"ERRO: saída já existe (escrita exclusiva): {out}", file=sys.stderr)
            return 3
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    linhas = [
        "# LAT THRESHOLD AUDIT — limiares de margem lateral e custo de desaceleração",
        "",
        f"**Data:** 2026-11-07 · **Método:** report-only sobre os controles OFF "
        f"existentes (zero corrida nova) · **Instrumento:** "
        f"`scripts/prof_lat_threshold_audit.py` (determinístico, `cmp=0` ×2) · "
        f"**a_brake:** {A_BRAKE} m/s² (pinado no mandato).",
        "",
        "## Interlagos (CTRL_OFF, 4 voltas)",
        "",
        "| limiar (m) | ticks | % tempo | eventos | dur média (s) | crônicas | "
        "outras | reta | v média (m/s) | v máx (m/s) | custo 10% por volta (s) | "
        "custo 20% por volta (s) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    mon_lines = ["", "## Monaco (CTRL_OFF, 2 voltas)", "",
                 "| limiar (m) | ticks | % tempo | eventos | dur média (s) | "
                 "crônicas | outras | reta | v média (m/s) | v máx (m/s) | "
                 "custo 10% por volta (s) | custo 20% por volta (s) |",
                 "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for t in tracks:
        target = linhas if t["pista"] == "interlagos" else mon_lines
        for key in ("3.5", "4.0", "4.5", "5.0"):
            d = t["por_limiar"][key]
            cust = d["custo_desaceleracao"]["total_projeta_s_por_volta"]
            target.append(
                f"| {d['limiar_m']} | {d['ticks_violacao']} | {d['pct_tempo']} | "
                f"{d['n_eventos']} | {d['duracao_media_s']} | "
                f"{d['setores']['cronicas_C01_C06_C07_C08']} | "
                f"{d['setores']['outras_curvas']} | {d['setores']['reta']} | "
                f"{d['v_media_violacao_mps']} | {d['v_max_violacao_mps']} | "
                f"{cust['0.1']} | {cust['0.2']} |")
    linhas += mon_lines + [
        "",
        "## Leitura (report-only; veredito é do Dono)",
        "",
        "- limiares mais baixos contêm ≥ ticks (nesting) e revelam a fração "
        "do tempo que o carro já passa fora da MEIA margem antes de cruzar "
        "6,0 m;",
        "- o custo de desaceleração projeta quanto tempo uma intervenção de "
        "pacing pagaria por corrida/volta para desacelerar 10%/20% a cada "
        "evento de violação (estimativa cinemática linear, não simulação);",
        "- o mapeamento por setor mostra se a violação de margem se concentra "
        "nas 4 crônicas ou se é difusa (Reta/outras).",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    for t in tracks:
        for key in ("3.5", "4.0", "4.5", "5.0"):
            d = t["por_limiar"][key]
            print(f"{t['pista']} limiar {d['limiar_m']} m: "
                  f"{d['ticks_violacao']} ticks ({d['pct_tempo']}%) | "
                  f"{d['n_eventos']} eventos (dur média {d['duracao_media_s']} s) | "
                  f"crônicas {d['setores']['cronicas_C01_C06_C07_C08']} / "
                  f"outras {d['setores']['outras_curvas']} / "
                  f"reta {d['setores']['reta']}")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
