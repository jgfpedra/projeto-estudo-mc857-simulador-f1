#!/usr/bin/env python3
"""PROF-GRIP-1 (sequência) — calibração empírica da razão de demanda lateral.

Report-only, determinístico, offline (zero corrida nova). Contexto crítico
pinado no mandato: o simulador usa ``PhysicsParams.mu = 1,8`` COM downforce
— ``a_lat(v, grip) = (1,8·grip)·(mass·g + c_df·v²)/mass`` — capacidade real
de ~14-16 m/s², e NÃO o μ_eff·g ≈ 8 m/s² dos instrumentos anteriores.

Para cada passagem pelas 4 crônicas (C01, C06, C07, C08) em cada fonte
(``REF_INTERLAGOS_600S.csv``, ``CTRL_Interlagos_OFF.csv``,
``ON_Interlagos_N0.csv``):

- ápice real da passagem = tick de |κ suavizada| máxima dentro da janela
  canônica; trecho de contorno = linhas da janela;
- medições do passe: v, tyre_grip, lat_max, margem (6,0 − lat_max);
- capacidade lateral REAL canônica: ``PhysicsParams.a_lat(v_apex, grip)``;
- demanda em DUAS convenções de curvatura:
  * linha central: ``a_lat_center = v²·κ(s)`` (suavizada 30 m E instantânea);
  * trajetória real do carro: ``a_lat_path = v · yaw_rate(t)`` com
    ``yaw_rate = d(ψ)/dt`` derivado de body_x/body_y (ψ = atan2 das
    diferenças centrais de posição, unwrap, gradiente);
- razões de demanda = demanda / capacidade, por convenção;
- desfecho: LIMPA (lat_max ≤ 6,0) vs SAÍDA (> 6,0) com a margem.

Análise de separação por fonte × convenção: razões LIMPA vs SAÍDA, o limiar
que separa (se max_LIMPA < min_SAÍDA) e a contagem de overlap caso contrário
— respondendo se o erro vem da linha central vs trajetória real.

Saídas exclusivas (determinísticas, ``cmp=0`` entre execuções):
``experiments/prof-grip-1/LATERAL_DEMAND_CALIBRATION.json`` e ``.md``.
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
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from model_train.velocity_profile import PhysicsParams  # noqa: E402
from model_train.velocity_profile import VelocityProfile  # noqa: E402
from scripts import saidas_verdict as SV  # noqa: E402
from scripts.experiments.controller.prof_lago_anatomy import (  # noqa: E402  canônicos
    kappa_interp_fn,
    segment_laps,
    sha256_file,
)
from scripts.experiments.controller.prof_lat_threshold_audit import (  # noqa: E402
    contiguous_events,
)

VERSION = "prof-grip-1/lateral-demand-calibration-v1.0"

REF_CSV = BACKEND / "experiments" / "prof-curva-1" / "REF_INTERLAGOS_600S.csv"
REF_SHA256 = "c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a"
CTRL_CSV = BACKEND / "experiments" / "prof-grip-1" / "corridas" / "CTRL_Interlagos_OFF.csv"
ON_N0_CSV = BACKEND / "experiments" / "prof-grip-1" / "corridas" / "ON_Interlagos_N0.csv"
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

KRONICAS = ("C01", "C06", "C07", "C08")
HALF_WIDTH_M = 6.0

OUT_JSON = BACKEND / "experiments" / "prof-grip-1" / "LATERAL_DEMAND_CALIBRATION.json"
OUT_MD = BACKEND / "experiments" / "prof-grip-1" / "LATERAL_DEMAND_CALIBRATION.md"


def yaw_rate_series(x: np.ndarray, y: np.ndarray, t: np.ndarray) -> np.ndarray:
    """yaw_rate = d(ψ)/dt: ψ = atan2 das diferenças centrais de posição
    (mundo), unwrap, gradiente. Bordas tratadas pelo np.gradient."""
    vx = np.gradient(x, t)
    vy = np.gradient(y, t)
    psi = np.unwrap(np.arctan2(vy, vx))
    return np.gradient(psi, t)


def kappa_path_from_heading(v: float, yaw_rate: float) -> Optional[float]:
    """κ_path = yaw_rate / v (guard v > 0)."""
    if float(v) <= 0.0:
        return None
    return abs(float(yaw_rate)) / float(v)


def separation_stats(limpa: List[float], saida: List[float]) -> Dict[str, Any]:
    """Limiar que separa LIMPA de SAÍDA (se max_LIMPA < min_SAÍDA) ou overlap."""
    if not limpa or not saida:
        return {"separavel": None, "nota": "conjunto vazio"}
    lo_s, hi_s = min(saida), max(saida)
    lo_l, hi_l = min(limpa), max(limpa)
    separavel = hi_l < lo_s
    out: Dict[str, Any] = {
        "n_limpa": len(limpa), "n_saida": len(saida),
        "razao_max_limpa": round(hi_l, 4), "razao_min_limpa": round(lo_l, 4),
        "razao_min_saida": round(lo_s, 4), "razao_max_saida": round(hi_s, 4),
        "separavel": bool(separavel),
    }
    if separavel:
        out["limiar_separador"] = round((hi_l + lo_s) / 2.0, 4)
    else:
        out["overlap"] = round(max(0.0, hi_l - lo_s), 4)
    return out


def pass_summary(rows: pd.DataFrame, kappa_smooth_at, kappa_inst_at) -> Optional[Dict[str, Any]]:
    """Métricas de UMA passagem pela janela da crônica (apex = |κ suav| máx)."""
    if len(rows) == 0:
        return None
    rows = rows.sort_values("tick")
    s = rows["s"].to_numpy(float)
    v = rows["speed"].to_numpy(float)
    lat = rows["lat"].to_numpy(float)
    grip = rows["tyre_grip"].to_numpy(float)
    x = rows["body_x"].to_numpy(float)
    y = rows["body_y"].to_numpy(float)
    t = rows["t_s"].to_numpy(float)

    k_s = np.array([abs(kappa_smooth_at(float(sv))) for sv in s])
    k_i = np.array([abs(kappa_inst_at(float(sv))) for sv in s])
    i_apex = int(np.argmax(k_s))
    v_apex = float(v[i_apex])
    g_apex = float(grip[i_apex])

    yaw = yaw_rate_series(x, y, t)
    a_lat_path = np.array([float(v[i]) * abs(float(yaw[i])) for i in range(len(rows))])
    a_lat_cs = np.array([float(v[i]) ** 2 * k_s[i] for i in range(len(rows))])
    a_lat_ci = np.array([float(v[i]) ** 2 * k_i[i] for i in range(len(rows))])
    cap = PhysicsParams.a_lat(v_apex, g_apex)

    lat_max = float(lat.max())
    return {
        "n_ticks": int(len(rows)),
        "s_apex_m": round(float(s[i_apex]), 3),
        "v_apex_mps": round(v_apex, 3),
        "v_apex_kmh": round(v_apex * 3.6, 3),
        "grip_apex": round(g_apex, 4),
        "kappa_center_suav_1m": round(float(k_s[i_apex]), 6),
        "kappa_center_inst_1m": round(float(k_i[i_apex]), 6),
        "kappa_path_1m": round(abs(kappa_path_from_heading(v_apex, float(yaw[i_apex]))) or 0.0, 6),
        "lat_max_m": round(lat_max, 4),
        "margem_m": round(HALF_WIDTH_M - lat_max, 4),
        "desfecho": "SAÍDA" if lat_max > HALF_WIDTH_M else "LIMPA",
        "a_lat_capacidade_ms2": round(float(cap), 3),
        "a_lat_center_suav_ms2": round(float(a_lat_cs[i_apex]), 3),
        "a_lat_center_inst_ms2": round(float(a_lat_ci[i_apex]), 3),
        "a_lat_path_ms2": round(float(a_lat_path[i_apex]), 3),
        "a_lat_path_max_ms2": round(float(a_lat_path.max()), 3),
        "razao_center_suav": round(float(a_lat_cs[i_apex]) / float(cap), 4),
        "razao_center_inst": round(float(a_lat_ci[i_apex]) / float(cap), 4),
        "razao_path": round(float(a_lat_path[i_apex]) / float(cap), 4),
        "razao_path_max": round(float(a_lat_path.max()) / float(cap), 4),
    }


def analyze_source(label: str, csv_path: Path, wps: np.ndarray,
                   kappa_smooth_at, kappa_inst_at, track_len: float
                   ) -> Dict[str, Any]:
    csv_sha = sha256_file(csv_path)
    df = pd.read_csv(csv_path, comment="#")
    laps = segment_laps(df["s"].to_numpy(float), track_len)
    n_seg = int(laps.max()) + 1

    passes: List[Dict[str, Any]] = []
    for seg in range(n_seg):
        seg_rows = df[laps == seg]
        if len(seg_rows) == 0:
            continue
        for cid in KRONICAS:
            rows = seg_rows[
                (seg_rows["s"] >= windows_global[cid][0])
                & (seg_rows["s"] <= windows_global[cid][1])]
            ps = pass_summary(rows, kappa_smooth_at, kappa_inst_at)
            if ps is None:
                continue
            ps.update({"fonte": label, "segmento": seg + 1, "curva": cid})
            passes.append(ps)

    # separação por fonte × convenção
    separacao: Dict[str, Any] = {}
    for conv in ("razao_center_suav", "razao_center_inst", "razao_path",
                 "razao_path_max"):
        limpa = [p[conv] for p in passes if p["desfecho"] == "LIMPA"]
        saida = [p[conv] for p in passes if p["desfecho"] == "SAÍDA"]
        separacao[conv] = separation_stats(limpa, saida)
    return {
        "fonte": label,
        "csv": str(csv_path.relative_to(BACKEND)),
        "csv_sha256_prefix": csv_sha[:16],
        "n_linhas_dados": int(len(df)),
        "n_passes": len(passes),
        "passes": passes,
        "separacao": separacao,
    }


windows_global: Dict[str, Tuple[float, float]] = {}


def main() -> int:
    global windows_global
    sources = [
        ("REF_600S", REF_CSV, REF_SHA256),
        ("CTRL_OFF", CTRL_CSV, None),
        ("ON_N0", ON_N0_CSV, None),
    ]
    for _, path, pin in sources:
        if not path.exists():
            print(f"ERRO: telemetria ausente: {path}", file=sys.stderr)
            return 2
        sha = sha256_file(path)
        if pin is not None and sha != pin:
            print(f"ERRO: SHA divergente em {path}: {sha}", file=sys.stderr)
            return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA da pista divergente: {track.get('sha256')}", file=sys.stderr)
        return 2
    wps = np.array(track["waypoints"], dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    track_len = float(np.hypot(*np.diff(closed, axis=0).T).sum())

    corners = SV.build_corner_definitions(
        wps, kappa_thresh=0.006, merge_gap_m=40.0, generic_names=False)
    for cid in KRONICAS:
        c = next((c for c in corners if c["id"] == cid), None)
        if c is None:
            print(f"ERRO: {cid} ausente na definição canônica", file=sys.stderr)
            return 2
        windows_global[cid] = (float(c["s0"]), float(c["s1"]))

    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    kappa_inst_at = (lambda s: float(np.interp(
        s % float(k_s[-1] + (k_s[1] - k_s[0])), k_s, np.abs(k_i))))

    pistas = [analyze_source(label, path, wps, kappa_smooth_at,
                             kappa_inst_at, track_len)
              for label, path, _ in sources]

    payload = {
        "schema_version": VERSION,
        "contexto_fisico": {
            "mu": PhysicsParams.mu,
            "mass_kg": PhysicsParams.mass,
            "c_downforce": PhysicsParams.c_downforce(),
            "a_lat": "a_lat(v, grip) = (mu·grip)·(mass·g + c_df·v²)/mass — "
                      "capacidade real ~14-16 m/s² a v de corrida",
            "capacidade_exemplos": {
                "a_lat(0, 0.788)": round(float(PhysicsParams.a_lat(0.0, 0.788)), 3),
                "a_lat(20, 0.8)": round(float(PhysicsParams.a_lat(20.0, 0.8)), 3),
                "a_lat(30, 0.842)": round(float(PhysicsParams.a_lat(30.0, 0.842)), 3),
            },
        },
        "pista": {"sha256_pin": TRACK_SHA_PIN, "comprimento_m": round(track_len, 3)},
        "janelas_canonicas_m": {cid: [round(w[0], 3), round(w[1], 3)]
                                for cid, w in windows_global.items()},
        "metodo": {
            "apice": "tick de |κ suavizada| máxima na janela canônica",
            "capacidade": "PhysicsParams.a_lat(v_apex, tyre_grip_apex)",
            "demanda": {
                "center_suav": "v²·κ suavizada 30 m",
                "center_inst": "v²·κ instantânea (janela mínima)",
                "path": "v·yaw_rate com yaw_rate = d(ψ)/dt de body_x/body_y",
            },
            "desfecho": "LIMPA lat_max ≤ 6,0 | SAÍDA > 6,0",
        },
        "pistas": pistas,
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
        "# LATERAL DEMAND CALIBRATION — razão de demanda com a capacidade REAL",
        "",
        f"**Data:** 2026-11-07 · **Método:** report-only sobre telemetria "
        f"existente (zero corrida nova) · **Instrumento:** "
        f"`scripts/experiments/controller/prof_lateral_demand_calibration.py` (determinístico, "
        f"`cmp=0` ×2).",
        "",
        f"**Contexto físico:** μ = {PhysicsParams.mu} com downforce "
        f"(mass {PhysicsParams.mass} kg, c_df "
        f"{PhysicsParams.c_downforce():.6f}) → capacidade real canônica "
        f"`a_lat(v, grip)` ≈ 14-16 m/s² a v de corrida — NÃO μ_eff·g ≈ 8.",
        "",
        "## Separação LIMPA vs SAÍDA por fonte × convenção",
        "",
        "| fonte | convenção | n LIMPA | n SAÍDA | máx LIMPA | min SAÍDA | "
        "separável | limiar |",
        "|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for t in pistas:
        for conv, s in t["separacao"].items():
            if s.get("separavel") is None:
                continue
            linhas.append(
                f"| {t['fonte']} | {conv} | {s['n_limpa']} | {s['n_saida']} | "
                f"{s['razao_max_limpa']} | {s['razao_min_saida']} | "
                f"{'SIM' if s['separavel'] else 'NÃO (overlap)'} | "
                f"{s.get('limiar_separador', '—')} |")

    linhas += [
        "",
        "## Passes detalhados (todas as fontes)",
        "",
        "| fonte | seg | curva | desfecho | v apex (km/h) | grip | lat_max | "
        "margem | cap | center_suav | center_inst | path | razão path |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for t in pistas:
        for p in t["passes"]:
            linhas.append(
                f"| {t['fonte']} | {p['segmento']} | {p['curva']} | "
                f"{p['desfecho']} | {p['v_apex_kmh']} | {p['grip_apex']} | "
                f"{p['lat_max_m']} | {p['margem_m']:+.3f} | "
                f"{p['a_lat_capacidade_ms2']} | {p['a_lat_center_suav_ms2']} | "
                f"{p['a_lat_center_inst_ms2']} | {p['a_lat_path_ms2']} | "
                f"{p['razao_path']} |")
    linhas += [
        "",
        "## Leitura (report-only; veredito é do Dono)",
        "",
        "- as razões com a capacidade REAL recalibram todas as leituras "
        "anteriores (que usavam μ_eff·g ≈ 8 m/s²);",
        "- a convenção `path` (trajetória real derivada de body_x/body_y) "
        "mede a curvatura QUE O CARRO DE FATO PERCORREU — se divergir da "
        "linha central, o erro está na geometria da referência vs trajetória "
        "cortada;",
        "- a separação LIMPA/SAÍDA por razão é o teste do limiar de margem.",
    ]
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    for t in pistas:
        print(f"{t['fonte']}: {t['n_passes']} passes")
        for conv, s in t["separacao"].items():
            if s.get("separavel") is not None:
                print(f"  {conv}: máx LIMPA {s['razao_max_limpa']} | "
                      f"min SAÍDA {s['razao_min_saida']} | "
                      f"separável: {s['separavel']}")
    print(f"OK -> {OUT_JSON} + {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
