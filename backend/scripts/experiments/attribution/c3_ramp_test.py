#!/usr/bin/env python3
"""REALISMO-1 C3-A — verificação offline da mordida da rampa P2.

Lê somente os dois CSVs N=0 commitados da promocao-1 e as duas geometrias
frozen. Não importa runner, simulador, controller ou modelo e não executa
corridas.

Pergunta congelada: entre as reentradas observáveis que têm uma nova saída do
mesmo carro em até 10 s, em que fração a rampa hipotética P2 seria violada
pela velocidade observada nos 5 s seguintes?

Uma reentrada é a transição imediata offtrack=1 -> 0 para o mesmo carro na
telemetria 5 Hz. A nova saída é a primeira linha offtrack=1 em
(reentrada, reentrada+10 s]. O perfil v_plan é construído pela implementação
frozen de model_train.velocity_profile.VelocityProfile, com os parâmetros
exatos do runner --gov vplan, e é congelado no s da reentrada.
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
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve()
BACKEND = SCRIPT.parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from model_train.velocity_profile import VelocityProfile  # noqa: E402

PROMO = BACKEND / "experiments" / "composite-1" / "promocao-1"
OUT_DIR = BACKEND / "experiments" / "realismo-1" / "c3"
TRACK_DIR = BACKEND / "model_train" / "tracks_frozen"

TRACKS = {
    "interlagos": {
        "stem": "1_R1_INTERLAGOS_RACE",
        "geometry": TRACK_DIR / "interlagos_v2.json",
        "geometry_sha256": "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
        "geometry_sha16": "164876196eb12174",
    },
    "monaco": {
        "stem": "3_R3_MONACO_RACE",
        "geometry": TRACK_DIR / "Monaco_v2.json",
        "geometry_sha256": "af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2",
        "geometry_sha16": "67ca11dc211c8c78",
    },
}

# CSV: tick lógico de 0,1 s; somente ticks pares são persistidos (5 Hz).
TICKS_PER_SECOND = 10
ROWS_PER_SECOND = 5
NEW_EXIT_MAX_TICKS = 100       # 10 s, inclusivo
RAMP_WINDOW_TICKS = 50         # 5 s, inclusivo
V0_MPS = 8.0
HOLD_S = 5.0
TARGET_FRACTION = 0.80
BITE_THRESHOLD = 0.30

VP_PARAMS = {
    "grip_mult": 0.788,
    "sf": 0.80,
    "ds_target": 4.0,
    "smooth_window_m": 20.0,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def object_sha256(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_profile(track: str) -> Tuple[VelocityProfile, Dict]:
    cfg = TRACKS[track]
    path = cfg["geometry"]
    actual = sha256_file(path)
    if actual != cfg["geometry_sha256"]:
        raise RuntimeError(f"geometria {track}: SHA divergente: {actual}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("sha256") != cfg["geometry_sha16"]:
        raise RuntimeError(f"geometria {track}: sha256 embutido divergente")
    waypoints = np.asarray(data["waypoints"], dtype=np.float64)
    profile = VelocityProfile(waypoints, **VP_PARAMS)
    return profile, {
        "path": str(path.relative_to(BACKEND)),
        "sha256": actual,
        "sha16": cfg["geometry_sha16"],
        "waypoints": int(len(waypoints)),
        "total_s_m": float(profile.total_s),
    }


def ramp_ceiling(v_plan: float, elapsed_s: float) -> float:
    """Ceiling congelado: v0/hold de 5 s até 80% de v_plan."""
    target = TARGET_FRACTION * float(v_plan)
    return min(target, V0_MPS + max(target - V0_MPS, 0.0) * elapsed_s / HOLD_S)


def first_new_exit(g: pd.DataFrame, reentry_tick: int):
    future = g[(g["tick"] > reentry_tick)
               & (g["tick"] <= reentry_tick + NEW_EXIT_MAX_TICKS)
               & (g["offtrack"].astype(int) == 1)]
    if future.empty:
        return None
    row = future.iloc[0]
    return {
        "tick": int(row.tick),
        "t_s": round(float(row.t_s), 1),
        "s": round(float(row.s), 3),
        "dt_s": round((int(row.tick) - reentry_tick) / TICKS_PER_SECOND, 1),
    }


def inspect_window(g: pd.DataFrame, reentry_tick: int, v_plan: float) -> Dict:
    window = g[(g["tick"] >= reentry_tick)
               & (g["tick"] <= reentry_tick + RAMP_WINDOW_TICKS)].copy()
    samples = []
    for row in window.itertuples(index=False):
        elapsed_s = (int(row.tick) - reentry_tick) / TICKS_PER_SECOND
        ceiling = ramp_ceiling(v_plan, elapsed_s)
        speed = float(row.speed)
        excess = speed - ceiling
        samples.append({
            "tick": int(row.tick),
            "elapsed_s": round(elapsed_s, 1),
            "speed_mps": speed,
            "ceiling_mps": ceiling,
            "excess_mps": excess,
            "bites": bool(excess > 1e-12),
        })
    bite_samples = [s for s in samples if s["bites"]]
    complete = bool(samples) and int(samples[-1]["tick"]) >= reentry_tick + RAMP_WINDOW_TICKS
    return {
        "window_start_tick": int(reentry_tick),
        "window_end_tick": int(reentry_tick + RAMP_WINDOW_TICKS),
        "n_rows": len(samples),
        "complete_5s": complete,
        "ramp_bites": bool(bite_samples) if samples else None,
        "first_bite": (bite_samples[0] if bite_samples else None),
        "max_speed_mps": (max(s["speed_mps"] for s in samples) if samples else None),
        "max_ceiling_mps": (max(s["ceiling_mps"] for s in samples) if samples else None),
        "max_excess_mps": (max(s["excess_mps"] for s in samples) if samples else None),
        "samples": samples,
    }


def analyze_track(track: str) -> Dict:
    cfg = TRACKS[track]
    main = PROMO / f"{cfg['stem']}.csv"
    if not main.is_file():
        raise FileNotFoundError(main)
    profile, geometry = load_profile(track)
    df = pd.read_csv(main, comment="#")
    required = {"drv", "tick", "t_s", "offtrack", "s", "speed"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise RuntimeError(f"{main}: colunas ausentes: {missing}")
    df = df.sort_values(["drv", "tick"], kind="stable").reset_index(drop=True)

    reentries: List[Dict] = []
    critical: List[Dict] = []
    for drv, g0 in df.groupby("drv", sort=True):
        g = g0.reset_index(drop=True)
        for i in range(1, len(g)):
            if int(g.iloc[i - 1].offtrack) != 1 or int(g.iloc[i].offtrack) != 0:
                continue
            row = g.iloc[i]
            reentry_tick = int(row.tick)
            exit_after = first_new_exit(g, reentry_tick)
            rec = {
                "drv": str(drv),
                "reentry_tick": reentry_tick,
                "reentry_t_s": round(float(row.t_s), 1),
                "reentry_s": float(row.s),
                "reentry_speed_mps": float(row.speed),
                "new_exit_within_10s": bool(exit_after),
                "exit_after_10s": exit_after,
            }
            if exit_after is not None:
                v_plan = float(profile.at(float(row.s)))
                window = inspect_window(g, reentry_tick, v_plan)
                rec.update({
                    "v_plan_at_reentry_mps": v_plan,
                    "ramp_target_80pct_mps": TARGET_FRACTION * v_plan,
                    "ramp": window,
                })
                critical.append(rec)
            reentries.append(rec)

    critical_complete = [r for r in critical if r["ramp"]["complete_5s"]]
    bites = [r for r in critical_complete if r["ramp"]["ramp_bites"]]
    n_reentries = len(reentries)
    n_critical = len(critical)
    n_complete = len(critical_complete)
    bite_fraction = (len(bites) / n_complete if n_complete else None)
    all_windows_complete = n_complete == n_critical
    if not all_windows_complete:
        verdict = "C3_INCONCLUSIVO_CENSURA"
        recommendation = "não autorizar C3-B; revisar censura antes de decidir"
    elif bite_fraction is not None and bite_fraction >= BITE_THRESHOLD:
        verdict = "C3_MORDE"
        recommendation = "autorizar a redação de um prereg C3-B antes de qualquer produção/simulação"
    else:
        verdict = "C3_NAO_MORDE"
        recommendation = "não implementar C3-B; avançar para C4/C5 conforme plano"

    return {
        "track": track,
        "run": cfg["stem"],
        "source": {
            "main_csv": str(main.relative_to(BACKEND)),
            "main_csv_sha256": sha256_file(main),
            "rows": int(len(df)),
            "drivers": int(df["drv"].nunique()),
        },
        "geometry": geometry,
        "counts": {
            "reentries": n_reentries,
            "critical_reentries_new_exit_le_10s": n_critical,
            "critical_evaluable_complete_5s": n_complete,
            "critical_censored_or_incomplete": n_critical - n_complete,
            "ramp_bites": len(bites),
            "bite_fraction_evaluable": bite_fraction,
            "all_critical_windows_complete": all_windows_complete,
        },
        "decision": {
            "threshold_fraction": BITE_THRESHOLD,
            "verdict": verdict,
            "recommendation": recommendation,
        },
        "reentries": reentries,
    }


def make_report(payload: Dict, json_sha256: str) -> str:
    lines = [
        "# REALISMO-1 · C3-A — verificação offline da mordida da rampa P2",
        "",
        "**Estado:** report-only, zero simulação, zero edição de produção. Esta saída aguarda revisão do dono.",
        "",
        "## Pergunta e método",
        "",
        "A pergunta congelada foi se a rampa P2 ultrapassaria o teto em pelo menos 30% das reentradas que têm uma nova saída do mesmo carro em até 10 s.",
        "",
        "- Reentrada: transição imediata `offtrack=1 -> 0` para o mesmo `drv` no CSV 5 Hz.",
        "- Reentrada crítica: primeira linha futura `offtrack=1` em `(reentrada, reentrada+10 s]`.",
        "- O `v_plan` é calculado pela implementação frozen `VelocityProfile` e congelado no `s` da reentrada.",
        "- Teto da rampa: `min(0,8·v_plan, 8 + max(0,8·v_plan−8, 0)·elapsed/5)` m/s, com `elapsed` de 0 a 5 s.",
        "- Mordida: alguma velocidade observada estritamente acima do teto (`excesso > 0`). A janela usa ticks inteiros e inclui os extremos.",
        "",
        "## Parâmetros e proveniência",
        "",
        f"- Parâmetros da rampa: `v0={payload['parameters']['v0_mps']} m/s`, `hold={payload['parameters']['hold_s']} s`, `target={payload['parameters']['target_fraction']}·v_plan`.",
        f"- Perfil: `grip_mult={payload['parameters']['velocity_profile']['grip_mult']}`, `sf={payload['parameters']['velocity_profile']['sf']}`, `ds_target={payload['parameters']['velocity_profile']['ds_target']} m`, `smooth_window_m={payload['parameters']['velocity_profile']['smooth_window_m']} m`.",
        f"- SHA dos parâmetros: `{payload['parameter_sha256']}`.",
        f"- SHA do script: `{payload['script_sha256']}`.",
        f"- SHA do JSON: `{json_sha256}`.",
        "",
        "## Resultado",
        "",
        "| Pista | Reentradas | Críticas | Avaliáveis 5 s | Mordidas | Fração | Veredito |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in payload["tracks"]:
        c = result["counts"]
        fraction = "n/a" if c["bite_fraction_evaluable"] is None else f"{c['bite_fraction_evaluable']:.1%}"
        lines.append(
            f"| {result['track']} | {c['reentries']} | {c['critical_reentries_new_exit_le_10s']} | "
            f"{c['critical_evaluable_complete_5s']} | {c['ramp_bites']} | {fraction} | "
            f"{result['decision']['verdict']} |"
        )
    lines += [
        "",
        "A decisão é por pista. `C3_MORDE` exige todas as janelas críticas completas e fração avaliável maior ou igual a 30%.",
        "",
        "## Decisão operacional",
        "",
    ]
    for result in payload["tracks"]:
        lines.append(f"- **{result['track']}: {result['decision']['verdict']}** — {result['decision']['recommendation']}.")
    lines += [
        "",
        "## Caveats",
        "",
        "- N=0 é uma realização determinística e não representa a distribuição N=0..4. O resultado é uma triagem offline, não uma homologação comportamental.",
        "- Episódios são contados por reentrada, portanto um mesmo `drv` pode contribuir com vários episódios. O JSON registra `drivers` separadamente.",
        "- O teste mede se a telemetria frozen excede um teto hipotético. Não demonstra que uma implementação P2 causaria ou evitaria esse excesso.",
        "- Nenhum sidecar de eventos, log de runner, controller, peso ou simulador foi lido; a análise usa apenas os CSVs principais e as geometrias frozen.",
        "- A evidência completa por reentrada, incluindo cada amostra da janela de 5 s, está em `C3_RAMP_CHECK.json`.",
        "",
        "## Disposição",
        "",
        "C3-A permanece offline-only. Não implementar C3-B, não ajustar seus parâmetros e não executar simulação antes da revisão e autorização do dono.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "C3_RAMP_CHECK.json"
    report_path = OUT_DIR / "C3_FINDINGS.md"
    if json_path.exists() or report_path.exists():
        raise FileExistsError("C3-A já possui saída; não sobrescrever")

    tracks = [analyze_track(track) for track in ("interlagos", "monaco")]
    parameters = {
        "v0_mps": V0_MPS,
        "hold_s": HOLD_S,
        "target_fraction": TARGET_FRACTION,
        "bite_threshold_fraction": BITE_THRESHOLD,
        "new_exit_max_s": NEW_EXIT_MAX_TICKS / TICKS_PER_SECOND,
        "ramp_window_s": RAMP_WINDOW_TICKS / TICKS_PER_SECOND,
        "velocity_profile": VP_PARAMS,
        "timing": {
            "tick_s": 0.1,
            "csv_hz": ROWS_PER_SECOND,
            "new_exit_boundary": "(reentry, reentry+10s]",
            "ramp_boundary": "[reentry, reentry+5s]",
        },
    }
    payload = {
        "schema": "c3-ramp-check-v1",
        "source": "promocao-1 N0 frozen; offline-only",
        "method": {
            "reentry": "offtrack 1 -> 0 in the next 5 Hz row for the same drv",
            "critical_reentry": "first offtrack=1 for same drv in (reentry, reentry+10s]",
            "v_plan": "VelocityProfile at reentry s, frozen for the 5 s window",
            "bite": "any observed speed strictly above the ramp ceiling",
            "no_simulation": True,
            "production_edited": False,
        },
        "parameters": parameters,
        "parameter_sha256": object_sha256(parameters),
        "script_sha256": sha256_file(SCRIPT),
        "tracks": tracks,
    }
    payload["analysis_sha256"] = object_sha256(payload)
    json_path.write_text(json.dumps(payload, sort_keys=True, indent=2,
                                    ensure_ascii=False, allow_nan=False) + "\n",
                         encoding="utf-8")
    json_sha = sha256_file(json_path)
    report_path.write_text(make_report(payload, json_sha), encoding="utf-8")

    print(f"C3-A JSON -> {json_path}")
    print(f"C3-A report -> {report_path}")
    for result in tracks:
        c = result["counts"]
        print(result["track"], c["reentries"], c["critical_reentries_new_exit_le_10s"],
              c["ramp_bites"], c["bite_fraction_evaluable"], result["decision"]["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
