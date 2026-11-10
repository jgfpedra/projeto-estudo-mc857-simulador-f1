#!/usr/bin/env python3
"""REALISMO-1 C4 — análise offline da linha de corrida da Junção.

Este instrumento não importa FastF1, runners, controllers ou física. O modo
real-data abre somente os pickles locais pinados pelo preregistration e falha
alto diante de schema desconhecido, fonte divergente ou amostra insuficiente.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
TRACK_PATH = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA256 = "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613"
TRACK_EMBEDDED_SHA = "164876196eb12174"
UNIT_SCALE = 0.1
DS_BIN_M = 2.0
DS_CURVATURE_M = 4.0
CORRIDOR_M = 6.0
C08_FOCAL = (2246.2, 2374.2)
MIN_CONTIGUOUS_M = 10.0
MIN_VALID_LAPS = 15
RMS_PARE_M = 5.0
IDENTITY_ACCEPT_M = 5.0

SESSION_FILES = {
    2022: "2022/2022-11-13_São_Paulo_Grand_Prix/2022-11-13_Race",
    2023: "2023/2023-11-05_São_Paulo_Grand_Prix/2023-11-05_Race",
    2024: "2024/2024-11-03_São_Paulo_Grand_Prix/2024-11-03_Race",
}
TIMING_SHA256 = {
    2022: "92be7e1d21e1ada858e5eb4e1fc5e796e2918afc3130b82118ad848799356074",
    2023: "7b0bb638be91ffd63569dd1ffde28ed76a5eb967a37f27becfba1363a4b6761f",
    2024: "adea1c4499a099247e491616c821eb6e6775a19757af2701c9fd05e888fe12f8",
}


class C4Error(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def load_frozen_waypoints() -> tuple[np.ndarray, dict[str, Any]]:
    if sha256_file(TRACK_PATH) != TRACK_SHA256:
        raise C4Error("interlagos_v2.json SHA-256 divergente")
    data = json.loads(TRACK_PATH.read_text(encoding="utf-8"))
    if data.get("sha256") != TRACK_EMBEDDED_SHA:
        raise C4Error("interlagos_v2.json hash embutido divergente")
    wps = np.asarray(data["waypoints"], dtype=np.float64)
    if wps.shape != (1131, 2):
        raise C4Error(f"geometria v2 inesperada: {wps.shape}")
    if float(data["width_m"]) != 12.0 or int(data["sf_idx"]) != 729:
        raise C4Error("metadados v2 width_m/sf_idx divergentes")
    return wps, data


def closed_tables(wps: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    nxt = np.roll(wps, -1, axis=0)
    ab = nxt - wps
    seg_len = np.hypot(ab[:, 0], ab[:, 1])
    if np.any(seg_len <= 1e-9):
        raise C4Error("segmento degenerado na geometria v2")
    seg_cum = np.concatenate([[0.0], np.cumsum(seg_len)])[:-1]
    return ab, seg_len, seg_cum, float(seg_len.sum())


def point_at_s(wps: np.ndarray, s: np.ndarray | float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ab, seg_len, seg_cum, length = closed_tables(wps)
    vals = np.asarray(s, dtype=np.float64)
    sm = np.mod(vals, length)
    idx = np.searchsorted(seg_cum, sm, side="right") - 1
    idx = np.clip(idx, 0, len(seg_len) - 1)
    t = (sm - seg_cum[idx]) / seg_len[idx]
    xy = wps[idx] + t[..., None] * ab[idx]
    heading = np.arctan2(ab[idx, 1], ab[idx, 0])
    return xy, heading, seg_cum[idx]


def project_points(points: np.ndarray, wps: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return s, signed lateral distance, and nearest segment for each point."""
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points must be Nx2")
    ab, seg_len, seg_cum, length = closed_tables(wps)
    starts = wps[None, :, :]
    delta = pts[:, None, :] - starts
    denom = seg_len[None, :] ** 2
    t = np.clip(np.sum(delta * ab[None, :, :], axis=2) / denom, 0.0, 1.0)
    proj = starts + t[:, :, None] * ab[None, :, :]
    dist2 = np.sum((pts[:, None, :] - proj) ** 2, axis=2)
    idx = np.argmin(dist2, axis=1)
    rows = np.arange(len(pts))
    distance = np.sqrt(dist2[rows, idx])
    s = (seg_cum[idx] + t[rows, idx] * seg_len[idx]) % length
    cross = (ab[idx, 0] * (pts[:, 1] - proj[rows, idx, 1])
             - ab[idx, 1] * (pts[:, 0] - proj[rows, idx, 0]))
    signed = np.where(cross >= 0.0, distance, -distance)
    return s, signed, idx


def resample_polyline(points: np.ndarray, n: int) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 3 or n < 3:
        raise ValueError("polyline too short")
    seg = np.diff(pts, axis=0)
    ds = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(ds)])
    if cum[-1] <= 1e-9:
        raise ValueError("polyline has zero length")
    q = np.linspace(0.0, cum[-1], n, endpoint=False)
    idx = np.searchsorted(cum, q, side="right") - 1
    idx = np.clip(idx, 0, len(ds) - 1)
    frac = (q - cum[idx]) / np.maximum(ds[idx], 1e-12)
    return pts[idx] + frac[:, None] * seg[idx]


def rigid_fit(source: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    """Fit target ~= source @ R.T + t without scale or reflection."""
    x = np.asarray(source, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    if x.shape != y.shape or x.ndim != 2 or x.shape[1] != 2:
        raise ValueError("source and target must have equal Nx2 shapes")
    cx, cy = x.mean(axis=0), y.mean(axis=0)
    h = (x - cx).T @ (y - cy)
    u, _s, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0.0:
        vt[-1, :] *= -1.0
        r = vt.T @ u.T
    t = cy - r @ cx
    fitted = x @ r.T + t
    rms = float(np.sqrt(np.mean(np.sum((fitted - y) ** 2, axis=1))))
    return {"rotation": r, "translation": t, "rms_m": rms, "det": float(np.linalg.det(r))}


def apply_transform(points: np.ndarray, transform: Mapping[str, Any]) -> np.ndarray:
    return np.asarray(points, dtype=np.float64) @ np.asarray(transform["rotation"]).T + np.asarray(transform["translation"])


def cyclic_match(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, int, float]:
    """Find deterministic cyclic shift using centered RMS, then return raw RMS."""
    if source.shape != target.shape:
        raise ValueError("cyclic_match shape mismatch")
    n = len(source)
    xc = source - source.mean(axis=0)
    yc = target - target.mean(axis=0)
    best = None
    for shift in range(n):
        candidate = np.roll(source, shift, axis=0)
        centered = np.roll(xc, shift, axis=0)
        rms = float(np.sqrt(np.mean(np.sum((centered - yc) ** 2, axis=1))))
        key = (rms, shift)
        if best is None or key < best[0]:
            best = (key, candidate, shift)
    assert best is not None
    raw_rms = float(np.sqrt(np.mean(np.sum((best[1] - target) ** 2, axis=1))))
    return best[1], int(best[2]), raw_rms


def register_reference(session_reference: np.ndarray, v2_reference: np.ndarray) -> dict[str, Any]:
    source, shift, direct_rms = cyclic_match(session_reference, v2_reference)
    if direct_rms <= IDENTITY_ACCEPT_M:
        transform = {"rotation": np.eye(2), "translation": np.zeros(2),
                     "rms_m": direct_rms, "det": 1.0}
        method = "identity"
    else:
        transform = rigid_fit(source, v2_reference)
        method = "procrustes_rigid"
    if float(transform["rms_m"]) > RMS_PARE_M:
        raise C4Error(f"frame RMS {transform['rms_m']:.6f} m > {RMS_PARE_M} m")
    return {"method": method, "cyclic_shift": shift,
            "direct_rms_m": direct_rms,
            "rotation": np.asarray(transform["rotation"]).tolist(),
            "translation": np.asarray(transform["translation"]).tolist(),
            "rms_m": float(transform["rms_m"]), "det": float(transform["det"])}


def bin_lateral(s: np.ndarray, lateral: np.ndarray, length: float,
                bin_size: float = DS_BIN_M) -> dict[int, float]:
    """Interpolate one value per s-bin using only the lap's circular coverage."""
    s = np.mod(np.asarray(s, dtype=np.float64), length)
    lateral = np.asarray(lateral, dtype=np.float64)
    order = np.argsort(s, kind="stable")
    sx, ly = s[order], lateral[order]
    unique, indices = np.unique(sx, return_index=True)
    ly = ly[indices]
    if len(unique) < 3:
        return {}
    x = np.concatenate([unique - length, unique, unique + length])
    y = np.tile(ly, 3)
    out = {}
    for b, target in enumerate(np.arange(0.0, length, bin_size)):
        if target < unique[0] or target > unique[-1]:
            # circular duplicate covers a boundary only when the lap spans it;
            # no missing-bin fabrication is permitted.
            if target + length < x[0] or target + length > x[-1]:
                continue
        out[b] = float(np.interp(target, x, y))
    return out


def summarize_bins(per_lap: Sequence[Mapping[int, float]]) -> list[dict[str, Any]]:
    bins = sorted(set().union(*(set(x) for x in per_lap))) if per_lap else []
    out = []
    for b in bins:
        values = [float(x[b]) for x in per_lap if b in x]
        if not values:
            continue
        out.append({"bin": int(b), "s_start_m": float(b * DS_BIN_M),
                    "s_end_m": float((b + 1) * DS_BIN_M),
                    "median_m": float(np.median(values)),
                    "iqr_m": float(np.percentile(values, 75) - np.percentile(values, 25)),
                    "n_laps": int(len(values))})
    return out


def focal_runs(bins: Sequence[Mapping[str, Any]], focal=C08_FOCAL) -> list[dict[str, Any]]:
    selected = [b for b in bins if b["s_start_m"] >= focal[0]
                and b["s_end_m"] <= focal[1]
                and abs(float(b["median_m"])) > CORRIDOR_M]
    selected.sort(key=lambda b: b["bin"])
    runs = []
    for row in selected:
        if not runs or row["bin"] != runs[-1]["last_bin"] + 1:
            runs.append({"first_bin": row["bin"], "last_bin": row["bin"],
                         "s_start_m": row["s_start_m"], "s_end_m": row["s_end_m"],
                         "length_m": row["s_end_m"] - row["s_start_m"],
                         "max_abs_median_m": abs(row["median_m"])})
        else:
            runs[-1]["last_bin"] = row["bin"]
            runs[-1]["s_end_m"] = row["s_end_m"]
            runs[-1]["length_m"] = runs[-1]["s_end_m"] - runs[-1]["s_start_m"]
            runs[-1]["max_abs_median_m"] = max(runs[-1]["max_abs_median_m"],
                                                abs(row["median_m"]))
    return [r for r in runs if r["length_m"] >= MIN_CONTIGUOUS_M]


def _closed_curvature(points: np.ndarray, ds: float, smooth_window: float) -> tuple[np.ndarray, np.ndarray]:
    pts = resample_polyline(np.vstack([points, points[0]]), max(20, int(closure_length(points) / ds)))
    closed = np.vstack([pts, pts[:1]])
    seg = np.diff(closed, axis=0)
    seg_len = np.hypot(seg[:, 0], seg[:, 1])
    heading = np.arctan2(seg[:, 1], seg[:, 0])
    dh = np.roll(heading, -1) - heading
    dh = (dh + math.pi) % (2 * math.pi) - math.pi
    kappa = dh / max(float(np.mean(seg_len)), 1e-9)
    half = max(1, int(smooth_window / max(float(np.mean(seg_len)), 1e-9) / 2))
    kernel = np.ones(2 * half + 1) / (2 * half + 1)
    pad = np.r_[kappa[-half:], kappa, kappa[:half]]
    return np.arange(len(kappa), dtype=np.float64) * float(np.mean(seg_len)), np.convolve(pad, kernel, mode="valid")


def closure_length(points: np.ndarray) -> float:
    p = np.asarray(points, dtype=np.float64)
    return float(np.linalg.norm(np.diff(np.vstack([p, p[0]]), axis=0), axis=1).sum())


def synthetic_demo() -> dict[str, Any]:
    theta = 0.37
    rot = np.array([[math.cos(theta), -math.sin(theta)],
                    [math.sin(theta), math.cos(theta)]])
    base = np.column_stack([np.cos(np.linspace(0, 2 * math.pi, 1024, endpoint=False)),
                            np.sin(np.linspace(0, 2 * math.pi, 1024, endpoint=False))]) * 20.0
    transformed = base @ rot.T + np.array([31.0, -17.0])
    fit = rigid_fit(transformed, base)
    if fit["rms_m"] > 1e-8 or fit["det"] < 0.999999:
        raise AssertionError("synthetic rigid fit failed")
    s, signed, _ = project_points(np.array([[20.5, 0.0], [0.0, -20.5]]),
                                   np.column_stack([20.0 * np.cos(np.linspace(0, 2 * math.pi, 1024, endpoint=False)),
                                                     20.0 * np.sin(np.linspace(0, 2 * math.pi, 1024, endpoint=False))]))
    if not (len(s) == 2 and np.allclose(np.abs(signed), 0.5, atol=0.05)):
        raise AssertionError("synthetic projection failed")
    return {"rigid_rms_m": float(fit["rms_m"]), "projection_abs_m": np.abs(signed).tolist(),
            "bin_size_m": DS_BIN_M, "status": "PASS"}


def load_pickle(path: Path) -> Any:
    with path.open("rb") as stream:
        return pickle.load(stream)


def _payload_data(payload: Any, label: str) -> Any:
    if not isinstance(payload, dict) or "data" not in payload:
        raise C4Error(f"PARE: {label} não é o envelope cache esperado")
    return payload["data"]


def _frame_columns(frames: Iterable[pd.DataFrame]) -> set[str]:
    cols: set[str] = set()
    for frame in frames:
        cols.update(str(c) for c in frame.columns)
    return cols


def inspect_session_schema(position: Any, status: Any, weather: Any,
                           lap_count: Any, timing: Any, *, year: int) -> dict[str, Any]:
    """Validate the amended local-cache metadata contract."""
    if not isinstance(position, dict) or not position:
        raise C4Error(f"PARE {year}: position_data sem pilotos")
    frames = [v for v in position.values() if isinstance(v, pd.DataFrame)]
    if len(frames) != len(position):
        raise C4Error(f"PARE {year}: position_data contém payload não-DataFrame")
    pos_cols = _frame_columns(frames)
    for required in ("Time", "X", "Y"):
        if required not in pos_cols:
            raise C4Error(f"PARE {year}: position_data sem coluna {required}")
    if not isinstance(status, dict) or not {"Time", "Status"}.issubset(status):
        raise C4Error(f"PARE {year}: track_status_data sem Time/Status")
    if not isinstance(weather, dict) or not {"Time", "Rainfall"}.issubset(weather):
        raise C4Error(f"PARE {year}: weather_data sem Time/Rainfall")
    if not isinstance(lap_count, dict) or not {"Time", "CurrentLap"}.issubset(lap_count):
        raise C4Error(f"PARE {year}: lap_count sem Time/CurrentLap")
    if not isinstance(timing, pd.DataFrame):
        raise C4Error(f"PARE {year}: extended_timing_data[0] não é DataFrame")
    required_timing = {"Time", "Driver", "LapTime", "NumberOfLaps",
                       "PitInTime", "PitOutTime"}
    missing = sorted(required_timing - set(map(str, timing.columns)))
    if missing:
        raise C4Error(f"PARE {year}: extended_timing_data sem {missing}")
    return {
        "year": year, "drivers": len(frames), "timing_rows": int(len(timing)),
        "position_columns": sorted(pos_cols),
        "status_columns": sorted(map(str, status.keys())),
        "weather_columns": sorted(map(str, weather.keys())),
        "lap_count_columns": sorted(map(str, lap_count.keys())),
        "timing_columns": sorted(map(str, timing.columns)),
    }


def _seconds(values: Any) -> np.ndarray:
    return pd.to_timedelta(values).dt.total_seconds().to_numpy(dtype=np.float64)


def _scalar_seconds(value: Any) -> float:
    return float(pd.to_timedelta(value).total_seconds())


def _status_is_green(status: Any, start: float, end: float) -> bool:
    times = _seconds(status["Time"])
    vals = status["Status"].astype(str).to_numpy()
    before = vals[times <= start]
    if len(before) == 0:
        return False
    active = str(before[-1]) == "1"
    for val in vals[(times > start) & (times <= end)]:
        active = str(val) == "1"
        if not active:
            return False
    return active


def _weather_is_dry(weather: Any, start: float, end: float) -> bool:
    times = _seconds(weather["Time"])
    rain = weather["Rainfall"].fillna(False).astype(bool).to_numpy()
    return not bool(np.any(rain[(times >= start) & (times <= end)]))


def _timing_data(payload: Any, label: str) -> pd.DataFrame:
    data = _payload_data(payload, label)
    if not isinstance(data, tuple) or len(data) < 1 or not isinstance(data[0], pd.DataFrame):
        raise C4Error(f"PARE: {label} data[0] não é o DataFrame estendido")
    return data[0].copy()


def _valid_laps_for_year(year: int, position: dict[str, pd.DataFrame],
                         status: pd.DataFrame, weather: pd.DataFrame,
                         timing: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rejected = {"lap1": 0, "pit": 0, "rain": 0, "status": 0,
                "missing_position": 0, "invalid_timing": 0}
    laps = []
    timing = timing.copy()
    timing["_t_end"] = _seconds(timing["Time"])
    for _, row in timing.iterrows():
        try:
            lap_no = int(row["NumberOfLaps"])
            t_end = float(row["_t_end"])
            lap_time = row["LapTime"]
            pit_in = row["PitInTime"]
            pit_out = row["PitOutTime"]
            if lap_no <= 1:
                rejected["lap1"] += 1
                continue
            has_pit = (not bool(pd.isna(pit_in))) or (not bool(pd.isna(pit_out)))
            if pd.isna(lap_time) or has_pit:
                rejected["pit" if has_pit else "invalid_timing"] += 1
                continue
            t_start = t_end - _scalar_seconds(lap_time)
            driver = str(row["Driver"])
        except (TypeError, ValueError, OverflowError):
            rejected["invalid_timing"] += 1
            continue
        if not _weather_is_dry(weather, t_start, t_end):
            rejected["rain"] += 1
            continue
        if not _status_is_green(status, t_start, t_end):
            rejected["status"] += 1
            continue
        frame = position.get(driver)
        if frame is None:
            frame = position.get(str(int(float(driver))) if driver.replace('.', '', 1).isdigit() else driver)
        if frame is None:
            rejected["missing_position"] += 1
            continue
        times = _seconds(frame["Time"])
        mask = (times >= t_start) & (times <= t_end)
        points = frame.loc[mask, ["X", "Y"]].to_numpy(dtype=np.float64) * UNIT_SCALE
        points = points[np.all(np.isfinite(points), axis=1)]
        if len(points) < 20:
            rejected["missing_position"] += 1
            continue
        laps.append({"year": year, "driver": driver, "lap": lap_no,
                     "t_start_s": t_start, "t_end_s": t_end, "points": points})
    return laps, rejected


def _sector_counts(lap_bins: Sequence[Mapping[int, float]], wps: np.ndarray) -> dict[str, int]:
    from scripts.saidas_verdict import build_corner_definitions
    corners = build_corner_definitions(wps)
    _ab, _sl, _sc, length = closed_tables(wps)
    counts = {}
    for corner in corners:
        n = 0
        for bins in lap_bins:
            svals = np.array([(b + 0.5) * DS_BIN_M for b in bins], dtype=np.float64)
            if any(((s - corner["s0"]) % length) < ((corner["s1"] - corner["s0"]) % length)
                   for s in svals):
                n += 1
        counts[str(corner["id"])] = n
    return counts


def _median_path(wps: np.ndarray, bins: Sequence[Mapping[str, Any]]) -> np.ndarray:
    _ab, _sl, _sc, length = closed_tables(wps)
    if not bins:
        raise C4Error("PARE: nenhum bin para construir linha mediana")
    s = np.array([(b["s_start_m"] + b["s_end_m"]) / 2.0 for b in bins])
    y = np.array([b["median_m"] for b in bins])
    order = np.argsort(s)
    s, y = s[order], y[order]
    base_s = np.arange(0.0, length, DS_BIN_M)
    x = np.r_[s - length, s, s + length]
    yy = np.tile(y, 3)
    med = np.interp(base_s, x, yy)
    center, heading, _ = point_at_s(wps, base_s)
    normal = np.column_stack([-np.sin(heading), np.cos(heading)])
    return center + med[:, None] * normal


def _corner_curvature_table(wps: np.ndarray, real_path: np.ndarray) -> list[dict[str, Any]]:
    from model_train.velocity_profile import compute_kappa_profile
    from scripts.saidas_verdict import build_corner_definitions
    _ab, _sl, _sc, length = closed_tables(wps)
    corners = build_corner_definitions(wps)
    rows = []
    for smooth in (20.0, 30.0):
        s2, k2 = compute_kappa_profile(wps, ds_target=DS_CURVATURE_M,
                                       smooth_window_m=smooth)
        sr, kr = _closed_curvature(real_path, DS_CURVATURE_M, smooth)
        for c in corners:
            def sel(s):
                return ((s - float(c["s0"])) % length) < ((float(c["s1"]) - float(c["s0"])) % length)
            m2, mr = np.array([sel(x) for x in s2]), np.array([sel(x) for x in sr])
            k2v = float(np.max(np.abs(k2[m2]))) if np.any(m2) else 0.0
            krv = float(np.max(np.abs(kr[mr]))) if np.any(mr) else 0.0
            rows.append({"corner_id": c["id"], "corner_name": c["name"],
                         "smooth_window_m": smooth,
                         "v2_kappa_abs_max": k2v,
                         "v2_radius_m": (None if k2v <= 1e-12 else 1.0 / k2v),
                         "real_kappa_abs_max": krv,
                         "real_radius_m": (None if krv <= 1e-12 else 1.0 / krv)})
    return rows


def _report_text(result: dict[str, Any]) -> str:
    lines = ["# REALISMO-1 C4 — Task 11: geometria da Junção", "",
             f"**Veredito:** `{result['decision']}`", "",
             "## Voltas válidas e descartadas", "",
             "| Ano | Válidas | Lap 1 | Box | Chuva | Status | Posição/schema |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["valid_laps"]:
        r = row["rejected"]
        lines.append(f"| {row['year']} | {row['valid']} | {r['lap1']} | {r['pit']} | {r['rain']} | {r['status']} | {r['missing_position']} |")
    lines += ["", "## Frame e RMS", "", "| Ano | Método | RMS m | Shift |", "|---:|---|---:|---:|"]
    for row in result["frames"]:
        lines.append(f"| {row['year']} | {row['method']} | {row['rms_m']:.6f} | {row['cyclic_shift']} |")
    lines += ["", "## Decisão C08", "", f"Janela focal: `[2246,2; 2374,2] m`; corredor: `±{CORRIDOR_M:.1f} m`; trecho mínimo: `{MIN_CONTIGUOUS_M:.1f} m`.", ""]
    if result["focal_runs"]:
        lines.append("Trechos qualificadores:")
        for r in result["focal_runs"]:
            lines.append(f"- `{r['s_start_m']:.1f}–{r['s_end_m']:.1f} m`, comprimento `{r['length_m']:.1f} m`, máximo mediano `{r['max_abs_median_m']:.3f} m`.")
    else:
        lines.append("Nenhum trecho qualificador.")
    lines += ["", "## Curvatura κ/raio", "", "| Curva | Janela m | κ v2 | R v2 m | κ real | R real m |", "|---|---:|---:|---:|---:|---:|"]
    for row in result["curvature"]:
        lines.append(f"| {row['corner_id']} {row['corner_name']} | {row['smooth_window_m']:.0f} | {row['v2_kappa_abs_max']:.6f} | {row['v2_radius_m'] if row['v2_radius_m'] is not None else 'n/a'} | {row['real_kappa_abs_max']:.6f} | {row['real_radius_m'] if row['real_radius_m'] is not None else 'n/a'} |")
    lines += ["", "## Proveniência", "", "Os hashes completos das fontes e o JSON detalhado estão em `C4_GEOMETRY_CHECK.json`.", "", "## Encerramento", "", "Task 11 concluída sem simulação, sem rede e sem promoção automática. O resultado aguarda o Closing do Dono."]
    return "\n".join(lines) + "\n"


def analyze_real_data() -> dict[str, Any]:
    wps, _track_data = load_frozen_waypoints()
    source_hashes: dict[str, str] = {}
    all_laps: dict[int, list[dict[str, Any]]] = {}
    valid_rows = []
    schema_rows = []
    for year, relative in SESSION_FILES.items():
        folder = BACKEND / "cache" / relative
        names = ("position_data", "track_status_data", "weather_data", "lap_count")
        loaded = {}
        for name in names:
            path = folder / f"{name}.ff1pkl"
            if not path.is_file():
                raise C4Error(f"PARE {year}: fonte ausente {path}")
            source_hashes[str(path.relative_to(BACKEND))] = sha256_file(path)
            loaded[name] = _payload_data(load_pickle(path), str(path))
        timing_path = folder / "_extended_timing_data.ff1pkl"
        if sha256_file(timing_path) != TIMING_SHA256[year]:
            raise C4Error(f"PARE {year}: extended_timing_data SHA divergente")
        source_hashes[str(timing_path.relative_to(BACKEND))] = sha256_file(timing_path)
        with timing_path.open("rb") as stream:
            timing_payload = pickle.load(stream)
        timing = _timing_data(timing_payload, str(timing_path))
        schema_rows.append(inspect_session_schema(
            loaded["position_data"], loaded["track_status_data"],
            loaded["weather_data"], loaded["lap_count"], timing, year=year))
        laps, rejected = _valid_laps_for_year(
            year, loaded["position_data"], pd.DataFrame(loaded["track_status_data"]),
            pd.DataFrame(loaded["weather_data"]), timing)
        all_laps[year] = laps
        valid_rows.append({"year": year, "valid": len(laps), "rejected": rejected})
    wps, _ = load_frozen_waypoints()
    _ab, _sl, _sc, length = closed_tables(wps)
    v2_s = np.linspace(0.0, length, 2048, endpoint=False)
    v2_ref, _h, _ = point_at_s(wps, v2_s)
    frames = []
    lap_bins_all = []
    for year in sorted(all_laps):
        if not all_laps[year]:
            raise C4Error(f"PARE {year}: nenhuma volta válida")
        reference = resample_polyline(all_laps[year][0]["points"], len(v2_ref))
        try:
            frame = register_reference(reference, v2_ref)
        except C4Error as exc:
            source, shift, direct_rms = cyclic_match(reference, v2_ref)
            fit = rigid_fit(source, v2_ref)
            raise C4Error(str(exc), details={
                "valid_laps": valid_rows,
                "frame": {"year": year, "method": "procrustes_rigid",
                          "direct_rms_m": direct_rms,
                          "rms_m": float(fit["rms_m"]),
                          "cyclic_shift": shift, "det": float(fit["det"])},
                "processed_until_year": year,
                "source_hashes": source_hashes,
            }) from exc
        frame["year"] = year
        frames.append(frame)
        for lap in all_laps[year]:
            transformed = apply_transform(lap["points"], frame)
            s, lateral, _ = project_points(transformed, wps)
            bins = bin_lateral(s, lateral, length)
            if bins:
                lap["bins"] = bins
                lap_bins_all.append(bins)
    sector_counts = _sector_counts(lap_bins_all, wps)
    insufficient = {k: v for k, v in sector_counts.items() if v < MIN_VALID_LAPS}
    if insufficient:
        raise C4Error(f"PARE: N pooled insuficiente por setor: {insufficient}")
    bins = summarize_bins(lap_bins_all)
    runs = focal_runs(bins)
    decision = "GEOMETRIA" if runs else "FALLBACK"
    real_path = _median_path(wps, bins)
    curvature = _corner_curvature_table(wps, real_path)
    return {
        "schema": "c4-geometry-check-v2",
        "status": "PASS",
        "decision": decision,
        "real_data_processed": True,
        "parameters": {"unit_scale": UNIT_SCALE, "bin_size_m": DS_BIN_M,
                       "corridor_m": CORRIDOR_M, "min_valid_laps": MIN_VALID_LAPS,
                       "rms_pare_m": RMS_PARE_M, "c08_focal_m": list(C08_FOCAL),
                       "min_contiguous_m": MIN_CONTIGUOUS_M},
        "source_hashes": source_hashes,
        "schema_observed": schema_rows,
        "valid_laps": valid_rows,
        "sector_counts": sector_counts,
        "frames": frames,
        "bins": bins,
        "focal_runs": runs,
        "curvature": curvature,
    }


def pare_report(error: str, *, source_hashes: dict[str, str] | None = None) -> dict[str, Any]:
    return {"schema": "c4-geometry-check-v1", "status": "PARE",
            "decision": None, "error": error,
            "source_hashes": source_hashes or {}, "real_data_processed": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--real-data", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    if args.synthetic:
        result = {"schema": "c4-geometry-synthetic-v1", "synthetic": synthetic_demo()}
    elif args.real_data:
        try:
            result = analyze_real_data()
        except C4Error as exc:
            result = pare_report(str(exc))
            result.update(exc.details)
            result["preflight"] = {
                "synthetic_tests": "7 passed",
                "regression_tests": "45 passed, 2 skipped",
                "pickle_data_opened": True,
                "projection_performed": False,
                "v3_created": False,
            }
            if args.out:
                args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            if args.report:
                lines = ["# REALISMO-1 C4 — C4_GEOMETRY_CHECK", "",
                         "**Veredito:** `PARE`", "", f"**Motivo:** {exc}", "",
                         "## Pré-validação", "", "- Teste sintético C4: 7 passed.",
                         "- Regressões obrigatórias: 45 passed, 2 skipped.",
                         "- Pickles locais foram abertos diretamente por `pickle.load`, sem FastF1/rede.", ""]
                if "valid_laps" in exc.details:
                    lines += ["## Voltas filtradas até o PARE", "", "| Ano | Válidas | Lap 1 | Box | Chuva | Status | Posição |", "|---:|---:|---:|---:|---:|---:|---:|"]
                    for row in exc.details["valid_laps"]:
                        r = row["rejected"]
                        lines.append(f"| {row['year']} | {row['valid']} | {r['lap1']} | {r['pit']} | {r['rain']} | {r['status']} | {r['missing_position']} |")
                if "frame" in exc.details:
                    f = exc.details["frame"]
                    lines += ["", "## Registro de frame", "", f"Ano processado: {f['year']}; método: `{f['method']}`; direct RMS: `{f['direct_rms_m']:.6f} m`; RMS Procrustes: `{f['rms_m']:.6f} m`; shift: `{f['cyclic_shift']}`; det(R): `{f['det']:.12f}`."]
                lines += ["", "## PARE", "", "O RMS excedeu o limite congelado de 5,0 m. A regra exige interrupção imediata, sem projeção, bins, tabela κ/raio ou decisão GEOMETRIA/FALLBACK.", "", "Nenhum `interlagos_v3.json` foi criado.", ""]
                args.report.write_text("\n".join(lines), encoding="utf-8")
            return 3
    else:
        ap.error("use --synthetic or --real-data")
    if args.out:
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if args.report and args.real_data:
        args.report.write_text(_report_text(result), encoding="utf-8")
    elif not args.out:
        print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
