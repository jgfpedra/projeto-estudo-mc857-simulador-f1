#!/usr/bin/env python3
"""PROF-CONTROL-1 (sequência) — viabilidade do pacing sensível ao grip dinâmico.

Report-only, determinístico, offline (zero corrida, zero PyBullet, zero
alteração de produção). Estuda, sobre o ``VelocityProfile`` canônico do
professor (parâmetros exatos do wiring: grip 0,788, sf 0,80, ds 4 m,
suavização 20 m), um teto de velocidade **nas 4 curvas crônicas de
Interlagos** (C01 Lago, C06 Bico de Pato, C07 Mergulho, C08 Junção) que
escala com o grip remanescente do pneu:

    v_capped(s) = v_plan(s) · sqrt(grip / grip_ref)        (variante DIRETA)
    v_capped(s) = v_plan(s) · sqrt(grip / grip_ref / 1,10) (variante COM
                  RESERVA de 10% na capacidade lateral — evita o
                  tangenciamento a centímetros da zebra visto no
                  LAGO_APPROACH_FINDINGS)

Grade de degradação: grip ∈ {0,85, 0,84, 0,82, 0,80, 0,78, 0,75} (bracket
do intervalo medido no REF 0,842→0,807 e além). grip_ref = 0,85 (topo da
grade; fator 1,0 = no-op). Fora das janelas canônicas das 4 crônicas o
perfil é intocado.

Tempo de volta teórico piso: ``t_lap = Σ ds / max(v, 0,5)`` sobre o laço
fechado, comparado à Guarda de Ritmo **123,05 s** (107,0 × 1,15, pinada no
PROF-CURVA-1). O piso ignora perdas de rastreio e as transições de frenagem
a montante das janelas (o perfil não recebe passadas dinâmicas) — é um
LIMITE INFERIOR do lap corrido com o mecanismo; se o piso estoura a Guarda,
a quebra é garantida; se o piso cabe, a corrida pode ainda estourar.

Comprimento: o mandato pina 4156,75 m (= ``cum[-1]``, sem o segmento de
fecho); o laço fechado real mede 4160,437 m — ambos registrados, a
integração usa o laço fechado (diferença ≈ 0,1% do t_lap).

Saídas exclusivas (determinísticas, ``cmp=0`` entre execuções):
``experiments/prof-control-1/GRIP_PACING_FEASIBILITY.json`` e ``.md``.
"""
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


import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent.parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from model_train.velocity_profile import VelocityProfile  # noqa: E402
from scripts.experiments.controller.prof_lago_anatomy import sha256_file  # noqa: E402
from scripts import saidas_verdict as SV  # noqa: E402

VERSION = "prof-control-1/grip-pacing-feasibility-v1.0"

TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

GRIPS = [0.85, 0.84, 0.82, 0.80, 0.78, 0.75]
GRIP_REF = 0.85
RESERVE = 0.10
GUARDA_S = 123.05
MANDATE_LEN_M = 4156.75
CORNERS = ["C01", "C06", "C07", "C08"]
V_FLOOR_MPS = 0.5

OUT_JSON = BACKEND / "experiments" / "prof-control-1" / "GRIP_PACING_FEASIBILITY.json"
OUT_MD = BACKEND / "experiments" / "prof-control-1" / "GRIP_PACING_FEASIBILITY.md"


def scale_factor(grip: float, grip_ref: float = GRIP_REF,
                 reserve: float = 0.0) -> float:
    """sqrt(grip/grip_ref) com reserva opcional de capacidade lateral:
    reservar R da capacidade equivale a multiplicar por sqrt(1/(1+R))."""
    if grip <= 0.0 or grip_ref <= 0.0 or reserve < 0.0:
        raise ValueError("grip/grip_ref/reserva inválidos")
    return math.sqrt(float(grip) / float(grip_ref) / (1.0 + float(reserve)))


def apply_corner_scaling(v_plan: np.ndarray, s_arr: np.ndarray,
                         windows: Sequence[Tuple[float, float]],
                         factor: float) -> np.ndarray:
    """Aplica min(v·fator) apenas dentro das janelas (nunca escala para cima)."""
    v = np.asarray(v_plan, dtype=np.float64).copy()
    if factor >= 1.0:
        return v
    mask = np.zeros(len(s_arr), dtype=bool)
    for s_lo, s_hi in windows:
        mask |= (s_arr >= s_lo) & (s_arr <= s_hi)
    v[mask] = np.maximum(v[mask] * factor, V_FLOOR_MPS)
    return v


def lap_time(v_plan: np.ndarray, ds: float) -> float:
    """t_lap = Σ ds / max(v, 0,5) sobre o laço fechado."""
    v = np.maximum(np.asarray(v_plan, dtype=np.float64), V_FLOOR_MPS)
    return float(np.sum(ds / v))


def corner_time(v_plan: np.ndarray, s_arr: np.ndarray,
                window: Tuple[float, float], ds: float) -> float:
    mask = (s_arr >= window[0]) & (s_arr <= window[1])
    return lap_time(v_plan[mask], ds)


def main() -> int:
    if not TRACK_FILE.exists():
        print(f"ERRO: pista frozen ausente: {TRACK_FILE}", file=sys.stderr)
        return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA da pista divergente: {track.get('sha256')}", file=sys.stderr)
        return 2

    sv_sha = sha256_file(Path(SV.__file__).resolve())

    wps = np.array(track["waypoints"], dtype=np.float64)
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    s_arr = np.asarray(vp.s_arr, dtype=np.float64)
    v_base = np.asarray(vp.v_plan, dtype=np.float64)
    ds = float(s_arr[1] - s_arr[0])
    total_len = float(s_arr[-1] + ds)

    corners_all = SV.build_corner_definitions(
        wps, kappa_thresh=0.006, merge_gap_m=40.0, generic_names=False)
    windows = []
    for cid in CORNERS:
        c = next((c for c in corners_all if c["id"] == cid), None)
        if c is None:
            print(f"ERRO: {cid} ausente na definição canônica", file=sys.stderr)
            return 2
        windows.append((float(c["s0"]), float(c["s1"])))

    t_base = lap_time(v_base, ds)
    per_corner_base = {cid: round(corner_time(v_base, s_arr, w, ds), 3)
                       for cid, w in zip(CORNERS, windows)}

    grid: List[Dict[str, Any]] = []
    for grip in GRIPS:
        entry: Dict[str, Any] = {"grip": grip, "variantes": {}}
        for label, reserve in (("direta", 0.0), ("reserva_10pct", RESERVE)):
            factor = scale_factor(grip, GRIP_REF, reserve)
            v_capped = apply_corner_scaling(v_base, s_arr, windows, factor)
            t = lap_time(v_capped, ds)
            entry["variantes"][label] = {
                "fator": round(factor, 6),
                "t_lap_piso_s": round(t, 3),
                "delta_vs_base_s": round(t - t_base, 3),
                "guarda_123_05_burst": bool(t > GUARDA_S),
                "guarda_margem_s": round(GUARDA_S - t, 3),
                "custo_por_curva_s": {
                    cid: round(corner_time(v_capped, s_arr, w, ds)
                               - per_corner_base[cid], 3)
                    for cid, w in zip(CORNERS, windows)
                },
            }
        grid.append(entry)

    payload = {
        "schema_version": VERSION,
        "metodo": {
            "base": "VelocityProfile canônico do professor (grip 0,788, sf 0,80, "
                    "ds 4 m, suavização 20 m) — pacing/v_plan histórico",
            "escala": "v_capped = v_plan · sqrt(grip/grip_ref) NOS windows das 4 "
                      "crônicas; nunca escala para cima; fora das janelas intocado",
            "integracao": "t_lap = Σ ds/max(v, 0,5) sobre o laço fechado (piso: "
                          "sem passadas dinâmicas de frenagem a montante)",
            "guarda_s": GUARDA_S,
        },
        "proveniencia": {
            "track_file": str(TRACK_FILE.relative_to(BACKEND)),
            "track_sha256_pin": TRACK_SHA_PIN,
            "saidas_verdict_sha256_prefix": sv_sha[:16],
            "n_waypoints": int(len(wps)),
            "comprimento_mandato_m": MANDATE_LEN_M,
            "comprimento_laco_fechado_m": round(total_len, 3),
            "comprimento_nota": "o mandato pina 4156,75 m = cum[-1] (sem o "
                                "segmento de fecho ~3,69 m); a integração usa "
                                "o laço fechado (Δ ≈ 0,1% do t_lap)",
        },
        "constantes": {
            "grip_grid": GRIPS, "grip_ref": GRIP_REF,
            "reserva_variante_b": RESERVE,
            "janelas_canonicas_m": {cid: [round(w[0], 3), round(w[1], 3)]
                                    for cid, w in zip(CORNERS, windows)},
            "v_floor_mps": V_FLOOR_MPS,
        },
        "piso_base_s": round(t_base, 3),
        "custo_base_por_curva_s": per_corner_base,
        "grid_grip": grid,
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
        "# GRIP PACING FEASIBILITY — pacing sensível ao grip nas 4 crônicas",
        "",
        f"**Data:** 2026-11-07 · **Método:** offline report-only (zero corrida/"
        f"PyBullet) · **Instrumento:** `scripts/experiments/controller/prof_grip_pacing_feasibility.py` "
        f"(determinístico, `cmp=0` ×2) · **Guarda:** {GUARDA_S} s.",
        "",
        f"Piso base (v_plan histórico, sem mecanismo): **{t_base:.3f} s** "
        f"(piso teórico — ignora rastreio/transições; a mediana rolante OFF "
        f"observada é 130,195 s).",
        "",
        "| grip | fator direta | t_lap direta (s) | Δ vs base | guarda? | "
        "fator reserva | t_lap reserva (s) | Δ vs base | guarda? |",
        "|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for entry in grid:
        d = entry["variantes"]["direta"]
        r = entry["variantes"]["reserva_10pct"]
        linhas.append(
            f"| {entry['grip']:.2f} | {d['fator']:.4f} | {d['t_lap_piso_s']} | "
            f"{d['delta_vs_base_s']:+.3f} | "
            f"{'ESTOURA' if d['guarda_123_05_burst'] else 'cabe'} | "
            f"{r['fator']:.4f} | {r['t_lap_piso_s']} | "
            f"{r['delta_vs_base_s']:+.3f} | "
            f"{'ESTOURA' if r['guarda_123_05_burst'] else 'cabe'} |")
    linhas += [
        "",
        "## Custo por curva (s), variante DIRETA (Δ vs base)",
        "",
        "| grip | " + " | ".join(CORNERS) + " |",
        "|---:|" + "---:|" * len(CORNERS),
    ]
    for entry in grid:
        custos = entry["variantes"]["direta"]["custo_por_curva_s"]
        linhas.append(f"| {entry['grip']:.2f} | "
                      + " | ".join(f"{custos[c]:+.3f}" for c in CORNERS) + " |")
    linhas += [
        "",
        "## Leitura (report-only; veredito é do Dono)",
        "",
        "- o mecanismo só toca as janelas das 4 crônicas — retas e demais "
        "curvas ficam com o v_plan histórico;",
        "- o piso não inclui frenagens a montante nem perdas de rastreio: é "
        "limite INFERIOR do lap com o mecanismo (estouro no piso = quebra "
        "garantida; piso dentro da Guarda ainda pode estourar corrido);",
        "- a variante com reserva 10% existe para não repetir o tangenciamento "
        "a centímetros da zebra visto no LAGO_APPROACH_FINDINGS (a Volta 1 "
        "passou com margem de +6 cm).",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print(f"piso base: {t_base:.3f} s | laço {total_len:.3f} m "
          f"(mandato {MANDATE_LEN_M} m)")
    for entry in grid:
        d = entry["variantes"]["direta"]
        r = entry["variantes"]["reserva_10pct"]
        print(f"grip {entry['grip']:.2f}: direta {d['t_lap_piso_s']} s "
              f"(Δ{d['delta_vs_base_s']:+.3f}, guarda "
              f"{'ESTOURA' if d['guarda_123_05_burst'] else 'cabe'}) | "
              f"reserva {r['t_lap_piso_s']} s "
              f"(Δ{r['delta_vs_base_s']:+.3f}, guarda "
              f"{'ESTOURA' if r['guarda_123_05_burst'] else 'cabe'})")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
