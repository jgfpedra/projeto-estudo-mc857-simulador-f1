#!/usr/bin/env python3
"""PROF-CONTROL-1 — anatomia report-only da Descida do Lago (C01).

Instrumento de diagnóstico offline sobre a telemetria EXISTENTE da corrida de
referência do professor solo (Task 2 do PROF-CURVA-1): ``REF_INTERLAGOS_600S.csv``.
Zero corrida, zero rede, zero código de produção, zero alteração de pista.

Pergunta: por que o professor espalha tangencialmente na Descida do Lago
(s ∈ [0, 80] m) a ~60 km/h? Duas hipóteses excludentes, com veredito mecânico:

- HIPÓTESE A (saturação mecânica): |steer_rad| atingiu ≥ 98% do
  ``steer_limit_rad(v)`` canônico (``F1MultiContextEnv.steer_limit_rad``) em
  algum tick ANTES da saída (|lat| > 6,0 m) — o esterço disponível foi
  consumido e a física capou o volante;
- HIPÓTESE B (subesterço de controle / falta de feedforward): |steer_rad|
  permaneceu com folga (máximo pré-saída < 90% do teto) — o pure pursuit não
  pediu esterço suficiente para vencer o raio da curva e a deriva dos pneus;
- entre 90% e 98%: zona cinza (veredito registrado sem força).

Método por volta (4 voltas da referência):
1. segmenta laps pelas quebras de s (wrap em track_len);
2. recorta a janela s ∈ [0, 80] m;
3. por tick: v (m/s e km/h), a_lat = v²·|κ(s)| (κ canônico suavizado 30 m),
   steer_rad, steer_limit_rad(v), razão de saturação e |lat|;
4. instante de saída = primeiro tick da janela com |lat| > 6,0 m;
5. veredito A/B/CINZA pela razão máxima pré-saída.

Saída exclusiva: ``experiments/prof-control-1/LAGO_ANATOMY.json`` (a leitura é
determinística; repetição em processo separado deve ser byte-idêntica, cmp=0).
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
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from model_train.f1_env import F1MultiContextEnv  # noqa: E402
import model_train.f1_env as _f1env  # noqa: E402
from model_train.velocity_profile import compute_kappa_profile  # noqa: E402

VERSION = "prof-control-1/lago-anatomy-v1.0"

REF_CSV = BACKEND / "experiments" / "prof-curva-1" / "REF_INTERLAGOS_600S.csv"
REF_SHA256 = "c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a"
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"

# Janela e limiares pinados no prompt executivo
WINDOW_S_M = (0.0, 80.0)
LAT_EXIT_M = 6.0
RATIO_A = 0.98   # ≥ → Hipótese A (saturação mecânica)
RATIO_B = 0.90   # máx pré-saída < → Hipótese B (subesterço)

OUT_PATH = BACKEND / "experiments" / "prof-control-1" / "LAGO_ANATOMY.json"


def steer_limit_rad(speed_mps: float) -> float:
    """Teto canônico de esterço por velocidade (delegação ao env)."""
    return float(F1MultiContextEnv.steer_limit_rad(speed_mps))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def segment_laps(s_arr: np.ndarray, track_len: float) -> np.ndarray:
    """Id de lap por linha: incrementa quando s quebra para trás (wrap)."""
    laps = np.zeros(len(s_arr), dtype=int)
    lap = 0
    for i in range(1, len(s_arr)):
        if s_arr[i] < s_arr[i - 1] - track_len / 2.0:
            lap += 1
        laps[i] = lap
    return laps


def kappa_interp_fn(wps: np.ndarray, ds_target: float = 4.0,
                    smooth_window_m: float = 30.0) -> Callable[[float], float]:
    """κ(s) do perfil canônico suavizado (mesma convenção de
    build_corner_definitions)."""
    s_arr, kap = compute_kappa_profile(
        wps, ds_target=ds_target, smooth_window_m=smooth_window_m)
    abs_k = np.abs(kap)

    def kappa_at(s: float) -> float:
        return float(np.interp(s % s_arr[-1], s_arr, abs_k))

    return kappa_at


def classify_lap(rows: pd.DataFrame, kappa_at: Callable[[float], float],
                 window: Tuple[float, float] = WINDOW_S_M,
                 lat_exit: float = LAT_EXIT_M) -> Dict[str, Any]:
    """Anatomia de UMA lap dentro da janela s ∈ window; veredito A/B/CINZA."""
    win = rows[(rows["s"] >= window[0]) & (rows["s"] <= window[1])]
    win = win.sort_values("tick")
    ticks = win["tick"].to_numpy()
    t_s = win["t_s"].to_numpy(float)
    s_m = win["s"].to_numpy(float)
    v = win["speed"].to_numpy(float)
    steer = win["steer_rad"].to_numpy(float)
    lat = win["lat"].to_numpy(float)

    a_lat = np.array([v[i] * v[i] * kappa_at(s_m[i]) for i in range(len(win))])
    limits = np.array([steer_limit_rad(v[i]) for i in range(len(win))])
    ratio = np.abs(steer) / np.maximum(limits, 1e-12)

    exit_idx: Optional[int] = None
    for i in range(len(win)):
        if lat[i] > lat_exit:
            exit_idx = i
            break
    pre = slice(0, exit_idx) if exit_idx is not None else slice(0, len(win))
    ratio_pre = ratio[pre]
    if len(ratio_pre) > 0:
        r_max = float(ratio_pre.max())
        i_max = int(np.argmax(ratio_pre))
    else:
        r_max, i_max = float("nan"), -1

    if exit_idx is not None:
        r_exit = float(ratio[exit_idx])
        i1s = max(exit_idx - 5, 0)  # 1 s antes a 5 Hz
        r_1s = float(ratio[i1s])
        mean_2s = float(ratio[max(exit_idx - 10, 0):exit_idx].mean()) if exit_idx > 0 else float("nan")
        exit_info: Dict[str, Any] = {
            "tick": int(ticks[exit_idx]),
            "t_s": round(float(t_s[exit_idx]), 3),
            "s_m": round(float(s_m[exit_idx]), 3),
            "lat_m": round(float(lat[exit_idx]), 4),
            "v_kmh": round(float(v[exit_idx]) * 3.6, 3),
            "ratio_no_instante": round(r_exit, 6),
            "ratio_1s_antes": round(r_1s, 6),
            "ratio_medio_2s_antes": round(mean_2s, 6),
        }
    else:
        exit_info = {"ocorreu": False}

    if not exit_info.get("ocorreu", True):
        verdict = "SEM-SAIDA"
    elif r_max >= RATIO_A:
        verdict = "A-SATURACAO-MECANICA"
    elif r_max < RATIO_B:
        verdict = "B-SUBESTERCO-CONTROLE"
    else:
        verdict = "CINZA"

    return {
        "n_ticks_janela": int(len(win)),
        "tick_range": [int(ticks[0]), int(ticks[-1])] if len(win) else None,
        "t_s_range": [round(float(t_s[0]), 3), round(float(t_s[-1]), 3)] if len(win) else None,
        "v_kmh_range": [round(float(v.min()) * 3.6, 3), round(float(v.max()) * 3.6, 3)] if len(win) else None,
        "a_lat_max_ms2": round(float(a_lat.max()), 4) if len(win) else None,
        "kappa_max_1m": round(float(max(kappa_at(s) for s in s_m)) if len(win) else 0.0, 6),
        "saidas": exit_info,
        "ratio_max_pre_saida": round(r_max, 6) if r_max == r_max else None,
        "s_no_ratio_max": round(float(s_m[i_max]), 3) if i_max >= 0 else None,
        "n_ticks_ratio_ge_98pct": int((ratio_pre >= RATIO_A).sum()) if r_max == r_max else 0,
        "verdict": verdict,
        "ticks": {
            "t_s": [round(float(x), 3) for x in t_s],
            "s_m": [round(float(x), 3) for x in s_m],
            "v_mps": [round(float(x), 4) for x in v],
            "v_kmh": [round(float(x) * 3.6, 3) for x in v],
            "a_lat_ms2": [round(float(x), 4) for x in a_lat],
            "steer_rad": [round(float(x), 6) for x in steer],
            "steer_limit_rad": [round(float(x), 6) for x in limits],
            "ratio_saturacao": [round(float(x), 6) for x in ratio],
            "lat_m": [round(float(x), 4) for x in lat],
        },
    }


def analyze_dataframe(df: pd.DataFrame, kappa_at: Callable[[float], float],
                      track_len: float,
                      window: Tuple[float, float] = WINDOW_S_M
                      ) -> Dict[str, Any]:
    """Segmenta laps, recorta a janela e emite o veredito por lap + agregado.

    Rotulagem honesta: o segmento que contém o tick 0 é ``parcial-largada``
    (a corrida pode começar fora de s=0 — o REF largas em s≈2649) e o último
    segmento, se termina no último tick do CSV, é ``parcial-fim``; os demais
    são voltas ``completas``."""
    laps = segment_laps(df["s"].to_numpy(float), track_len)
    last_tick = int(df["tick"].max())
    payload_laps = []
    verdicts: List[str] = []
    n_seg = int(laps.max()) + 1
    for lap_id in range(n_seg):
        rows = df[laps == lap_id]
        if len(rows) == 0:
            continue
        res = classify_lap(rows, kappa_at, window=window)
        res["segmento"] = lap_id + 1
        if lap_id == 0 and float(rows["s"].iloc[0]) > window[1]:
            res["tipo"] = "parcial-largada"
        elif lap_id == n_seg - 1 and int(rows["tick"].max()) >= last_tick:
            res["tipo"] = "parcial-fim"
        else:
            res["tipo"] = "completa"
        payload_laps.append(res)
        verdicts.append(res["verdict"])
    if verdicts and all(v == verdicts[0] for v in verdicts):
        agregado = verdicts[0]
    else:
        agregado = "MISTO:" + ",".join(verdicts)
    return {
        "n_laps": len(payload_laps),
        "laps": payload_laps,
        "veredito_agregado": agregado,
        "contagem_verdicts": {v: verdicts.count(v) for v in sorted(set(verdicts))},
    }


def main() -> int:
    if not REF_CSV.exists():
        print(f"ERRO: referência ausente: {REF_CSV}", file=sys.stderr)
        return 2
    ref_sha = sha256_file(REF_CSV)
    if ref_sha != REF_SHA256:
        print(f"ERRO: SHA da referência divergente: {ref_sha}", file=sys.stderr)
        return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA da pista divergente: {track.get('sha256')}", file=sys.stderr)
        return 2
    wps = np.array(track["waypoints"], dtype=np.float64)
    track_len = float(np.hypot(*np.diff(np.vstack([wps, wps[:1]]), axis=0).T).sum())

    df = pd.read_csv(REF_CSV, comment="#")
    need = {"tick", "t_s", "speed", "s", "lat", "steer_rad"}
    if not need.issubset(df.columns):
        print(f"ERRO: colunas ausentes no CSV: {need - set(df.columns)}", file=sys.stderr)
        return 2

    kappa_at = kappa_interp_fn(wps)
    payload = analyze_dataframe(df, kappa_at, track_len)
    result = {
        "schema_version": VERSION,
        "origem": {
            "csv": str(REF_CSV.relative_to(BACKEND)),
            "csv_sha256": ref_sha,
            "n_linhas_dados": int(len(df)),
        },
        "pista": {
            "arquivo": str(TRACK_FILE.relative_to(BACKEND)),
            "sha256_pin": TRACK_SHA_PIN,
            "comprimento_m": round(track_len, 3),
        },
        "metodo": {
            "janela_s_m": list(WINDOW_S_M),
            "lat_saida_m": LAT_EXIT_M,
            "limiar_ratio_A": RATIO_A,
            "limiar_ratio_B": RATIO_B,
            "kappa": "perfil canônico suavizado 30 m (compute_kappa_profile, ds 4 m), |κ| interpolado em s",
            "steer_limit": "F1MultiContextEnv.steer_limit_rad: max(0.04, rad(45°)/(1+(v/25)²))",
            "f1_env_sha256": sha256_file(Path(_f1env.__file__).resolve()),
        },
        **payload,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        print(f"ERRO: saída já existe (escrita exclusiva): {OUT_PATH}", file=sys.stderr)
        return 3
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"referência: {result['origem']['n_linhas_dados']} linhas | "
          f"pista {result['pista']['comprimento_m']} m | "
          f"janela s {WINDOW_S_M} m | saída |lat| > {LAT_EXIT_M} m")
    for lap in result["laps"]:
        ex = lap["saidas"]
        print(f"segmento {lap['segmento']} ({lap['tipo']}): {lap['n_ticks_janela']} ticks | "
              f"v {lap['v_kmh_range']} km/h | a_lat máx {lap['a_lat_max_ms2']} m/s² | "
              f"κ máx {lap['kappa_max_1m']} 1/m")
        if ex.get("ocorreu", True):
            print(f"    saída: t {ex['t_s']} s, s {ex['s_m']} m, |lat| {ex['lat_m']} m, "
                  f"v {ex['v_kmh']} km/h | ratio máx pré-saída {lap['ratio_max_pre_saida']} "
                  f"(em s {lap['s_no_ratio_max']}; {lap['n_ticks_ratio_ge_98pct']} ticks ≥98%) | "
                  f"VEREDICTO: {lap['verdict']}")
        else:
            print(f"    sem saída na janela | ratio máx {lap['ratio_max_pre_saida']} | "
                  f"VEREDICTO: {lap['verdict']}")
    print(f"VEREDITO AGREGADO: {result['veredito_agregado']} {result['contagem_verdicts']}")
    print(f"OK -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
