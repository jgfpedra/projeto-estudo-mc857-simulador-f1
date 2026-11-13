#!/usr/bin/env python3
"""PROF-CURVA-1 Task 5 — mapa de viabilidade do teto local de curvatura.

OFFLINE por construção: zero corridas, zero rede, zero estado global. Compara,
nas duas pistas do estágio 0, o perfil de velocidade baseline do professor
(``VelocityProfile`` histórico) contra o perfil com teto
(``build_capped_velocity_profile``, exatamente os parâmetros do wiring
``--prof-curva``), e sobrepõe os eventos de saída observados no estágio 0
(métricas ``cmp=0`` já em disco).

Perguntas que o mapa responde (insumo do prereg do mecanismo, não decide sozinho):

1. Onde o teto engaja (segmentos de s em que ``v_cap < v_base``) e com quanta
   autoridade (Δv) por região crônica (C01/C06/C07/C08/Reta em Interlagos)?
2. Em cada evento de saída observado, o teto local em ``s_onset`` ficaria
   abaixo da velocidade de aproximação observada (``v_1s_mps``)? — se não fica,
   o mecanismo não teria evitado aquele evento.
3. Integral de volta teórica (Σ ds/v) baseline × teto vs Guarda de Ritmo:
   teto Interlagos 123,05 s pinado no prereg/Task 2; Monaco report-only
   (análogo +15% sobre a mediana OFF observada, para o prereg pinar).

Entradas (todas existentes, nada é gerado aqui):
- pistas congeladas: ``interlagos`` (164876196eb12174) e ``Monaco`` (67ca11dc211c8c78);
- fronteira: ``experiments/prof-curva-1/physics_frontier_current.json`` (default do wiring);
- eventos: ``experiments/prof-curva-1/c0/{INT,MON}_N{0..4}_metrics.json``.

Saída: ``experiments/prof-curva-1/c5/MAPA_VIABILIDADE.json`` (escrita exclusiva).
Determinístico: sem RNG, sem tempo de parede no payload.
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


import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent.parent
ROOT = BACKEND.parent
for path in (str(ROOT), str(BACKEND), str(BACKEND / "model_train")):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.domain.track_resolution import load_track_frozen  # noqa: E402
from backend.model_train.prof_curva import (  # noqa: E402
    _instantaneous_kappa_profile,
    build_capped_velocity_profile,
    load_physics_frontier,
)
from backend.model_train.velocity_profile import (  # noqa: E402
    VelocityProfile,
    compute_kappa_profile,
)

# Parâmetros EXATOS do wiring --prof-curva em race_diagnostic.py (Task 3).
GRIP_MULT = 0.788
SF = 0.80
DS_TARGET = 4.0
SMOOTH_WINDOW_M = 20.0
FRONTIER_REL = "experiments/prof-curva-1/physics_frontier_current.json"

# Guarda de Ritmo (prereg PREREG_PROF_CURVA_1.md, Decisão 3=b; pin Task 2).
GUARDA_INTERLAGOS_S = 123.05

C0_DIR = BACKEND / "experiments" / "prof-curva-1" / "c0"
OUT_DIR = BACKEND / "experiments" / "prof-curva-1" / "c5"
TRACKS = [("interlagos", "INT"), ("Monaco", "MON")]
SEEDS = [0, 1, 2, 3, 4]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def lap_integral(v_plan: np.ndarray, ds: float) -> float:
    """Integral teórica Σ ds/v sobre o laço fechado (piso 0,5 m/s anti-div0)."""
    v = np.maximum(np.asarray(v_plan, dtype=np.float64), 0.5)
    return float(np.sum(ds / v))


def circular_segments(mask: np.ndarray) -> List[List[int]]:
    """Segmentos contíguos (com fecho circular) onde mask é True, como listas de índices."""
    n = len(mask)
    if not mask.any():
        return []
    start = int(np.argmin(mask))  # primeiro False após wrap
    segments: List[List[int]] = []
    i = 0
    while i < n:
        if mask[(start + i) % n]:
            vals = []
            while i < n and mask[(start + i) % n]:
                vals.append((start + i) % n)
                i += 1
            segments.append(vals)
        else:
            i += 1
    return segments


def local_kappa(wps: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """k_local = max(|k_suavizada|, |k_instantânea|) — exatamente como prof_curva."""
    s_arr, k_smooth = compute_kappa_profile(
        wps, ds_target=DS_TARGET, smooth_window_m=SMOOTH_WINDOW_M
    )
    _, k_raw = _instantaneous_kappa_profile(wps, ds_target=DS_TARGET)
    k_local = np.maximum(np.abs(k_smooth), np.abs(k_raw))
    return s_arr, k_smooth, k_local


def analyze_track(track_name: str, frontier_path: Path) -> Dict[str, Any]:
    track = load_track_frozen(track_name)
    wps = np.array(track.waypoints, dtype=np.float64)
    track_sha = str(getattr(track, "frozen_sha256", "?"))

    base = VelocityProfile(
        wps, grip_mult=GRIP_MULT, sf=SF, ds_target=DS_TARGET,
        smooth_window_m=SMOOTH_WINDOW_M,
    )
    capped = build_capped_velocity_profile(
        wps, frontier_path=str(frontier_path), grip_mult=GRIP_MULT, sf=SF,
        ds_target=DS_TARGET, smooth_window_m=SMOOTH_WINDOW_M,
    )

    s_arr = np.asarray(base.s_arr, dtype=np.float64)
    ds = float(s_arr[1] - s_arr[0])
    v_base = np.asarray(base.v_plan, dtype=np.float64)
    v_cap = np.asarray(capped.v_plan, dtype=np.float64)

    _, _, k_local = local_kappa(wps)
    radius_local = 1.0 / np.maximum(np.abs(k_local), 1e-5)

    t_base = lap_integral(v_base, ds)
    t_cap = lap_integral(v_cap, ds)

    bind_mask = v_cap < (v_base - 1e-6)
    segments = []
    for idxs in circular_segments(bind_mask):
        s_vals = s_arr[idxs]
        segments.append({
            "s_lo_m": round(float(s_vals.min()), 1),
            "s_hi_m": round(float(s_vals.max()), 1),
            "len_m": round(float(len(idxs) * ds), 1),
            "n_points": len(idxs),
            "v_base_min_mps": round(float(v_base[idxs].min()), 2),
            "v_cap_min_mps": round(float(v_cap[idxs].min()), 2),
            "radius_min_m": round(float(radius_local[idxs].min()), 2),
        })
    segments.sort(key=lambda seg: seg["s_lo_m"])

    return {
        "track": track_name,
        "track_frozen_sha256": track_sha,
        "n_waypoints": int(len(wps)),
        "track_length_m": round(float(s_arr[-1] + ds), 1),
        "lap_integral_baseline_s": round(t_base, 3),
        "lap_integral_capped_s": round(t_cap, 3),
        "lap_integral_delta_s": round(t_cap - t_base, 3),
        "n_bind_points": int(bind_mask.sum()),
        "bind_segments": segments,
        "events": {},
    }


def overlay_events(result: Dict[str, Any], prefix: str) -> None:
    """Sobrepõe os eventos do estágio 0 ao mapa de teto da pista."""
    s_arr_ref = result["_s_arr"]
    ds = float(s_arr_ref[1] - s_arr_ref[0])
    v_cap = result["_v_cap"]
    v_base = result["_v_base"]
    radius_local = result["_radius"]
    n = len(s_arr_ref)

    by_corner: Dict[str, Dict[str, Any]] = {}
    total = 0
    total_bind = 0
    for seed in SEEDS:
        path = C0_DIR / f"{prefix}_N{seed}_metrics.json"
        with path.open("r", encoding="utf-8") as f:
            metrics = json.load(f)
        for exc in metrics.get("excursions", []):
            cid = str(exc.get("corner_id", "?"))
            s_onset = float(exc.get("s", 0.0))
            v_obs = float(exc.get("v_1s_mps", 0.0))
            idx = int(round(s_onset / ds)) % n
            cap_at = float(v_cap[idx])
            base_at = float(v_base[idx])
            binds = bool(cap_at < v_obs)
            total += 1
            total_bind += int(binds)
            entry = by_corner.setdefault(cid, {
                "n_events": 0,
                "n_binds": 0,
                "v_obs_max_mps": 0.0,
                "cap_at_onset_range_mps": [1e9, -1e9],
                "radius_at_onset_range_m": [1e9, -1e9],
            })
            entry["n_events"] += 1
            entry["n_binds"] += int(binds)
            entry["v_obs_max_mps"] = max(entry["v_obs_max_mps"], round(v_obs, 2))
            entry["cap_at_onset_range_mps"][0] = min(entry["cap_at_onset_range_mps"][0], round(cap_at, 2))
            entry["cap_at_onset_range_mps"][1] = max(entry["cap_at_onset_range_mps"][1], round(cap_at, 2))
            r_at = float(radius_local[idx])
            entry["radius_at_onset_range_m"][0] = min(entry["radius_at_onset_range_m"][0], round(r_at, 1))
            entry["radius_at_onset_range_m"][1] = max(entry["radius_at_onset_range_m"][1], round(r_at, 1))

    for cid, entry in by_corner.items():
        if entry["cap_at_onset_range_mps"][1] < 0:
            entry["cap_at_onset_range_mps"] = None
    result["events"] = {
        "source": f"c0/{prefix}_N0..4_metrics.json",
        "total_events": total,
        "total_binds": total_bind,
        "by_corner": by_corner,
    }


def observed_lap_median(prefix: str) -> float:
    laps: List[float] = []
    for seed in SEEDS:
        path = C0_DIR / f"{prefix}_N{seed}_metrics.json"
        with path.open("r", encoding="utf-8") as f:
            metrics = json.load(f)
        for laps_by_drv in metrics.get("lap_times_from_csv_s", {}).values():
            for lap in laps_by_drv:
                laps.append(float(lap))
    return float(np.median(laps)) if laps else float("nan")


def main() -> int:
    frontier_abs = (BACKEND / FRONTIER_REL).resolve()
    if not frontier_abs.exists():
        print(f"ERRO: fronteira ausente: {frontier_abs}", file=sys.stderr)
        return 2
    frontier_pairs = load_physics_frontier(str(frontier_abs), grip=GRIP_MULT)

    results: List[Dict[str, Any]] = []
    for track_name, prefix in TRACKS:
        result = analyze_track(track_name, frontier_abs)
        # referências internas para o overlay (removidas antes de serializar)
        wps = np.array(load_track_frozen(track_name).waypoints, dtype=np.float64)
        s_arr, _, k_local = local_kappa(wps)
        base = VelocityProfile(wps, grip_mult=GRIP_MULT, sf=SF,
                               ds_target=DS_TARGET, smooth_window_m=SMOOTH_WINDOW_M)
        capped = build_capped_velocity_profile(wps, frontier_path=str(frontier_abs),
                                               grip_mult=GRIP_MULT, sf=SF,
                                               ds_target=DS_TARGET,
                                               smooth_window_m=SMOOTH_WINDOW_M)
        result["_s_arr"] = s_arr
        result["_v_cap"] = np.asarray(capped.v_plan, dtype=np.float64)
        result["_v_base"] = np.asarray(base.v_plan, dtype=np.float64)
        result["_radius"] = 1.0 / np.maximum(np.abs(k_local), 1e-5)
        overlay_events(result, prefix)
        mediana = observed_lap_median(prefix)
        result["observed_off_lap_median_s"] = round(mediana, 3)
        if track_name == "interlagos":
            result["guarda_ceiling_s"] = GUARDA_INTERLAGOS_S
            result["guarda_burst_predicted"] = bool(
                result["lap_integral_capped_s"] > GUARDA_INTERLAGOS_S
            )
        else:
            result["guarda_ceiling_s"] = round(mediana * 1.15, 2)
            result["guarda_burst_predicted"] = bool(
                result["lap_integral_capped_s"] > mediana * 1.15
            )
            result["guarda_ceiling_note"] = (
                "análogo +15% sobre a mediana OFF observada (report-only; "
                "sem referência histórica Task 2 para Monaco) — PIN no prereg"
            )
        for key in ("_s_arr", "_v_cap", "_v_base", "_radius"):
            result.pop(key, None)
        results.append(result)

    payload = {
        "schema_version": "prof-curva-1/task5-mapa-viabilidade-v1",
        "metodo": "OFFLINE: perfis baseline×teto (parâmetros do wiring) + overlay "
                  "dos eventos do estágio 0; zero corridas, zero rede",
        "wiring_params": {
            "grip_mult": GRIP_MULT, "sf": SF, "ds_target": DS_TARGET,
            "smooth_window_m": SMOOTH_WINDOW_M,
        },
        "frontier_file": FRONTIER_REL,
        "frontier_sha256": sha256_file(frontier_abs),
        "frontier_effective_pairs_R_min_v": [
            [r, v] for r, v in sorted(frontier_pairs)
        ],
        "guarda_interlagos_ceiling_s": GUARDA_INTERLAGOS_S,
        "tracks": results,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "MAPA_VIABILIDADE.json"
    if out_path.exists():
        print(f"ERRO: saída já existe (escrita exclusiva): {out_path}", file=sys.stderr)
        return 3
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    # ---- impressão legível ----
    print(f"fronteira efetiva (R_min, v): {payload['frontier_effective_pairs_R_min_v']}")
    for r in results:
        print(f"\n=== {r['track']} (sha {r['track_frozen_sha256'][:16]}, "
              f"{r['track_length_m']} m) ===")
        print(f"integral baseline {r['lap_integral_baseline_s']} s | "
              f"capped {r['lap_integral_capped_s']} s | "
              f"Δ {r['lap_integral_delta_s']} s | guarda {r['guarda_ceiling_s']} s | "
              f"burst previsto: {r['guarda_burst_predicted']}")
        print(f"pontos de engage: {r['n_bind_points']} em {len(r['bind_segments'])} segmentos")
        for seg in r["bind_segments"]:
            print(f"  s {seg['s_lo_m']}-{seg['s_hi_m']} m ({seg['len_m']} m) "
                  f"v_base≥{seg['v_base_min_mps']} → cap {seg['v_cap_min_mps']} m/s "
                  f"(R_min {seg['radius_min_m']} m)")
        print(f"eventos estágio 0: {r['events']['total_events']} | "
              f"com teto abaixo da v observada: {r['events']['total_binds']}")
        for cid, e in sorted(r["events"]["by_corner"].items()):
            cap_lo, cap_hi = e["cap_at_onset_range_mps"]
            rad_lo, rad_hi = e["radius_at_onset_range_m"]
            print(f"  {cid}: {e['n_binds']}/{e['n_events']} bind | v_obs_max "
                  f"{e['v_obs_max_mps']} | cap {cap_lo}-{cap_hi} m/s | "
                  f"R {rad_lo}-{rad_hi} m")
    print(f"\nOK -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
