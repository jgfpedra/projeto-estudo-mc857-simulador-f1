#!/usr/bin/env python3
"""Calibração v2 da fronteira física do PROF-CURVA-1.

Porta o roteiro de ``archive/scripts/physics_radius_calibration.py`` sem
alterar a saída legada. A v2 registra simultaneamente o critério antigo
(``R_ratio`` + desalinhamento) e o critério de círculo estável
(``lat_proxy`` + desalinhamento), permitindo comparar a procedência.

Fonte arquivada (SHA-256 completo, requerido no cabeçalho pela re-auditoria
da Task 2):
  232e2a81282f4f9c8becf768f34a9d095b3242e253951c2ee167489e9c77189a

v1.1 (emenda de re-auditoria, aditiva): ``protocol.instrument_version`` no
payload e falha explícita quando a grade não produz nenhum raio ESTAVEL. O
artefato canônico do estágio 0 (``physics_frontier_v2_canonical.json``) foi
produzido pela v1.0 e permanece como evidência — a grade completa real não é
re-executada sem autorização do Dono.

Todas as saídas são create-only e precisam ficar sob ``backend/experiments``;
qualquer tentativa de gravar em ``model_train`` é recusada.
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


import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent.parent
ROOT = BACKEND.parent
for path in (str(ROOT), str(BACKEND), str(BACKEND / "model_train")):
    if path not in sys.path:
        sys.path.insert(0, path)

SOURCE_SCRIPT = BACKEND / "archive/scripts/physics_radius_calibration.py"
SOURCE_SHA256 = ""
INSTRUMENT_VERSION = "physics-frontier-v2/1.1"
DEFAULT_OUT = BACKEND / "experiments/prof-curva-1/c0/physics_frontier_v2.json"
SPEEDS = [4, 6, 8, 10, 13, 16, 18, 20, 22, 25]
RADII = [4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50, 65, 80]
GRIPS = [(0.788, "real"), (0.842, "soft")]
WHEELBASE_M = 3.4
REPORT_R_EFF_STEP_M = 5.0
REPORT_R_RATIO_DECIMALS = 1
REPORT_LAT_PROXY_STEP_M = 1.0
REPORT_MISALIGN_DECIMALS = 1


def source_sha256() -> str:
    digest = hashlib.sha256()
    with SOURCE_SCRIPT.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def quantize_step(value: float, step: float) -> float:
    """Quantiza o instrumento na resolução física declarada no protocolo."""
    return float(round(float(value) / step) * step)


def seal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("metrics_sha256", None)
    body["metrics_sha256"] = hashlib.sha256(
        canonical_json(body).encode("utf-8")
    ).hexdigest()
    return body


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    model_train = (BACKEND / "model_train").resolve()
    experiments = (BACKEND / "experiments").resolve()
    if model_train == resolved or model_train in resolved.parents:
        raise ValueError("physics_frontier_v2 não pode gravar em model_train/")
    if experiments != resolved and experiments not in resolved.parents:
        raise ValueError("physics_frontier_v2 deve gravar sob experiments/")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=1, ensure_ascii=False,
                  allow_nan=False, sort_keys=True)
        stream.write("\n")


def fit_circle(x: Iterable[float], y: Iterable[float]) -> Tuple[float | None, float | None, float | None]:
    """Ajuste algébrico de Kasa: pontos → (cx, cy, R)."""
    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)
    if x_arr.size < 3 or y_arr.size != x_arr.size:
        return None, None, None
    A = np.column_stack([x_arr, y_arr, np.ones_like(x_arr)])
    b = x_arr * x_arr + y_arr * y_arr
    try:
        solution, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None, None, None
    cx, cy = solution[0] / 2.0, solution[1] / 2.0
    radius = math.sqrt(max(solution[2] + cx * cx + cy * cy, 0.0))
    return float(cx), float(cy), float(radius)


def classify_old(result: MappingLike) -> str:
    if result["R_ratio"] <= 1.1 and result["misalign_deg"] < 5.0:
        return "LIMPO"
    if result["R_ratio"] <= 1.3 and result["misalign_deg"] < 15.0:
        return "MARGINAL"
    return "QUEBRA"


def classify_stable(result: MappingLike) -> str:
    if result["lat_proxy"] <= 0.5 and result["misalign_deg"] < 12.0:
        return "ESTAVEL"
    return "QUEBRA"


class MappingLike(dict):
    """Type alias kept runtime-light for the classification helpers."""


def run_circle(env: Any, v_target: float, radius_target: float,
               grip: float, wheelbase: float = WHEELBASE_M,
               n_revolutions: float = 2.0, max_ticks: int = 800) -> dict[str, Any]:
    """Executa o skidpad e retorna somente métricas determinísticas."""
    import pybullet as p

    # Cada círculo começa como uma realização independente. Sem o reset, o
    # estado residual do episódio anterior pode alterar a dinâmica dos links
    # das rodas em uma medição limítrofe, quebrando o cmp=0 do protocolo.
    env.reset()
    ph = env.engine.physics
    handle = env.engine.handles[env.driver_id]
    client_id = ph._client_id
    ph.set_position(handle, (0.0, 0.0, 0.5), yaw_rad=0.0)
    p.resetBaseVelocity(
        handle.chassis_id,
        linearVelocity=(v_target, 0.0, 0.0),
        angularVelocity=(0.0, 0.0, 0.0),
        physicsClientId=client_id,
    )

    steer_needed = math.atan(wheelbase / radius_target)
    duration = n_revolutions * 2.0 * math.pi * radius_target / max(v_target, 0.5)
    ticks = min(int(duration / 0.1) + 20, max_ticks)
    xs: List[float] = []
    ys: List[float] = []
    misalign: List[float] = []
    steer_limit = env.steer_limit_rad(v_target)
    for _ in range(ticks):
        speed_now = ph.get_state(handle)["speed_mps"]
        steer_limit = env.steer_limit_rad(speed_now)
        steer_cmd = min(steer_needed, steer_limit)
        if speed_now > v_target + 0.3:
            throttle, brake = 0.0, 0.6
        elif speed_now < v_target - 0.3:
            throttle, brake = 0.4, 0.0
        else:
            throttle, brake = 0.0, 0.0
        env.engine.set_driver_input(
            env.driver_id,
            target_speed_mps=v_target,
            throttle=throttle,
            brake=brake,
            steering_yaw_rad=steer_cmd,
            grip_override=grip,
        )
        env.engine._step_tick(env.logic_dt, env.sub_steps)
        state = ph.get_state(handle)
        xs.append(float(state["x"]))
        ys.append(float(state["y"]))
        vx, vy = float(state.get("vx", 0.0)), float(state.get("vy", 0.0))
        if math.hypot(vx, vy) > 0.5:
            velocity_angle = math.atan2(vy, vx)
            mis = abs((velocity_angle - state["heading_rad"] + math.pi)
                      % (2.0 * math.pi) - math.pi)
            misalign.append(mis)

    warm = max(10, int(len(xs) * 0.3))
    cx, cy, radius_effective = fit_circle(xs[warm:], ys[warm:])
    misalign_deg = float(np.degrees(np.median(misalign))) if misalign else 999.0
    if radius_effective is not None and radius_effective > 0.1:
        distance = np.hypot(np.asarray(xs[warm:]) - cx,
                            np.asarray(ys[warm:]) - cy)
        lat_proxy = float(np.max(np.abs(distance - radius_effective)))
    else:
        radius_effective = 999.0
        lat_proxy = 999.0

    # O solver Bullet pode variar alguns centímetros entre processos em
    # trajetórias limítrofes. A v2 compara o instrumento na resolução física
    # pré-registrada, não em ruído de ponto flutuante abaixo dessa resolução.
    result: MappingLike = MappingLike(
        v_target=float(v_target),
        R_target=float(radius_target),
        grip=float(grip),
        R_eff=quantize_step(radius_effective, REPORT_R_EFF_STEP_M),
        R_ratio=round(float(radius_effective / radius_target),
                      REPORT_R_RATIO_DECIMALS),
        misalign_deg=round(misalign_deg, REPORT_MISALIGN_DECIMALS),
        lat_proxy=quantize_step(lat_proxy, REPORT_LAT_PROXY_STEP_M),
        steer_capped=bool(steer_needed > steer_limit),
    )
    result["classe_antiga"] = classify_old(result)
    result["classe_estavel"] = classify_stable(result)
    return result


def frontier(results: Sequence[MappingLike], criterion: str) -> dict[str, dict[str, float | None]]:
    if criterion not in {"classe_antiga", "classe_estavel"}:
        raise ValueError("critério desconhecido")
    accepted = {"LIMPO", "ESTAVEL"} if criterion == "classe_estavel" else {"LIMPO"}
    output: dict[str, dict[str, float | None]] = {}
    for grip, label in GRIPS:
        output[label] = {}
        for speed in SPEEDS:
            candidates = [
                row["R_target"] for row in results
                if math.isclose(row["grip"], grip, abs_tol=1e-9)
                and math.isclose(row["v_target"], speed, abs_tol=1e-9)
                and row[criterion] in accepted
            ]
            output[label][str(speed)] = min(candidates) if candidates else None
    return output


def calibrate(
    speeds: Sequence[float] = SPEEDS,
    radii: Sequence[float] = RADII,
    grips: Sequence[Tuple[float, str]] = GRIPS,
) -> dict[str, Any]:
    from backend.model_train.f1_env import F1MultiContextEnv

    global SPEEDS, RADII, GRIPS
    old_speeds, old_radii, old_grips = SPEEDS, RADII, GRIPS
    SPEEDS, RADII, GRIPS = list(speeds), list(radii), list(grips)
    results: List[MappingLike] = []
    for grip, _label in GRIPS:
        for speed in SPEEDS:
            for radius in RADII:
                steer_needed = math.atan(WHEELBASE_M / radius)
                if steer_needed > F1MultiContextEnv.steer_limit_rad(speed) * 1.3:
                    continue
                # A fresh physics client prevents warm-start/contact-cache
                # state from one circle influencing the next measurement.
                env = F1MultiContextEnv(track="interlagos", allow_respawn=False)
                try:
                    results.append(run_circle(
                        env, float(speed), float(radius), float(grip)))
                finally:
                    env.close()
    payload = {
            "schema_version": "prof-curva-physics-frontier-v2",
            "protocol": {
                "instrument_version": INSTRUMENT_VERSION,
                "source_script": str(SOURCE_SCRIPT.relative_to(ROOT)),
                "source_sha256": source_sha256(),
                "wheelbase_m": WHEELBASE_M,
                "speeds_mps": [float(value) for value in SPEEDS],
                "radii_m": [float(value) for value in RADII],
                "grips": [{"value": float(value), "label": label}
                          for value, label in GRIPS],
                "criteria": {
                    "old": {"R_ratio_max": 1.1, "misalign_deg_max": 5.0},
                    "old_marginal": {"R_ratio_max": 1.3, "misalign_deg_max": 15.0},
                    "stable": {"lat_proxy_m_max": 0.5, "misalign_deg_max": 12.0},
                },
                "report_resolution": {
                    "R_eff_m_step": REPORT_R_EFF_STEP_M,
                    "R_ratio_decimals": REPORT_R_RATIO_DECIMALS,
                    "lat_proxy_m_step": REPORT_LAT_PROXY_STEP_M,
                    "misalign_deg_decimals": REPORT_MISALIGN_DECIMALS,
                },
            },
            "frontier_old_limpo": frontier(results, "classe_antiga"),
            "frontier_stable": frontier(results, "classe_estavel"),
            "measurements": [dict(row) for row in results],
    }
    SPEEDS, RADII, GRIPS = old_speeds, old_radii, old_grips
    # Falha explícita (re-auditoria da Task 2): uma grade que não produz
    # nenhum raio ESTAVEL é um erro de grade, não uma fronteira vazia.
    stable_values = [
        radius
        for by_speed in payload["frontier_stable"].values()
        for radius in by_speed.values()
    ]
    if not any(radius is not None for radius in stable_values):
        raise ValueError("grade sem nenhum raio estável: nenhuma medição ESTAVEL")
    return seal_payload(payload)


def _parse_csv_numbers(value: str) -> list[float]:
    try:
        parsed = [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"grade inválida: {value}") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("grade vazia")
    return parsed


def _parse_grips(value: str) -> list[Tuple[float, str]]:
    result = []
    for item in value.split(","):
        if ":" not in item:
            raise argparse.ArgumentTypeError("grips devem usar valor:rótulo")
        grip, label = item.split(":", 1)
        try:
            result.append((float(grip), label.strip()))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"grip inválido: {item}") from exc
    if not result or any(not label for _, label in result):
        raise argparse.ArgumentTypeError("grips vazios")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--speeds", type=_parse_csv_numbers,
                        default=[float(value) for value in SPEEDS])
    parser.add_argument("--radii", type=_parse_csv_numbers,
                        default=[float(value) for value in RADII])
    parser.add_argument("--grips", type=_parse_grips,
                        default=list(GRIPS))
    args = parser.parse_args(argv)
    payload = calibrate(args.speeds, args.radii, args.grips)
    write_exclusive(args.out, payload)
    print(f"physics_frontier_v2: {args.out}")
    print(f"measurements={len(payload['measurements'])}")
    print(f"metrics_sha256={payload['metrics_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
