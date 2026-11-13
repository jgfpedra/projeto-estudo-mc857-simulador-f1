"""Report-only instrumentation for the measured Composite corpus.

This module deliberately does not load a model, create an environment, or run
a simulation. Raw measured CSVs are only admitted after an external,
deterministic reconstruction supplies the complete v15 residual contract.
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


import csv
import gzip
import hashlib
import json
import math
import re
import argparse
import sys
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

TRAFFIC_DIM = 12
RESIDUAL_DIM = 16
ACTION_DIM = 2
TELEMETRY_EDGE_DIM = 34
SPLIT_RULE = {"train": 80, "validation": 10, "test": 10}
SPLIT_RULE_NAME = "rank-80/10/10-per-run-v1"
SPLIT_BUCKETS = ("train", "validation", "test")
FROZEN_GEOMETRY_SHA256 = {
    "interlagos_v2": "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
    "monaco_v2": "af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2",
}

RACE_REQUIRED = {
    "tick", "t_s", "drv", "speed", "s", "lat", "th", "brk",
    "steer_rad", "car_car",
}
TRAFFIC_COLUMNS = {
    *(f"traffic_{i}" for i in range(TRAFFIC_DIM)),
}
GEOMETRY_RE = re.compile(r"(?:track_frozen_sha256|geometry_sha256)=([0-9a-fA-F]+)")


class CorpusError(ValueError):
    """Raised when a source or reconstructed row violates the frozen contract."""


REFERENCE_GAIN = 8.0
REFERENCE_WHEELBASE_M = 3.4
REFERENCE_LOOKAHEAD_GAIN = 0.6
REFERENCE_LOOKAHEAD_MIN_M = 5.0
REFERENCE_LOOKAHEAD_MAX_M = 45.0
REFERENCE_SPEED_MARGIN = 0.93
REFERENCE_D_AHEAD_M = 60.0
REFERENCE_D_FOLLOW_M = 25.0
REFERENCE_V_MARGIN = 2.0
REFERENCE_V_MIN_FOLLOW = 1.0
REFERENCE_G_SAFE_M = 6.0
REFERENCE_LAT_SAME_LINE_M = 2.6
REFERENCE_LAT_CORRIDOR_M = 3.5
REFERENCE_LAT_OFFSET_MAX_M = 2.5


def _signed_dist_s(s_other: float, s_ego: float, track_len_s: float) -> float:
    length = float(track_len_s)
    return ((s_other - s_ego + 0.5 * length) % length) - 0.5 * length


def _pure_traffic_adjust(
    s_ego: float,
    v_ego: float,
    lat_ego: float,
    traffic: Sequence[Mapping[str, object] | Sequence[float]],
    *,
    track_len_s: float,
    half_width: float,
) -> tuple[float | None, float]:
    """Return the stateless v-cap and lateral target from reference v15."""
    best_gap = math.inf
    best_car = None
    for car in traffic:
        if isinstance(car, Mapping):
            s_other = float(car["s"])
            lat_other = float(car["lat"])
            v_other = float(car["speed"])
        else:
            s_other, lat_other, v_other = map(float, car)
        gap = _signed_dist_s(s_other, s_ego, track_len_s)
        if (
            0.0 < gap < best_gap
            and gap < REFERENCE_D_AHEAD_M
            and abs(lat_other - lat_ego) < REFERENCE_LAT_SAME_LINE_M
        ):
            best_gap = gap
            best_car = (lat_other, v_other)
    if best_car is None:
        return None, 0.0

    lat_ahead, v_ahead = best_car
    v_cap = None
    if v_ego > v_ahead and v_ahead > REFERENCE_V_MIN_FOLLOW:
        v_cap = v_ahead + REFERENCE_V_MARGIN
        if best_gap < REFERENCE_D_FOLLOW_M:
            if best_gap < REFERENCE_G_SAFE_M:
                v_cap = max(v_ahead - 0.5, REFERENCE_V_MIN_FOLLOW)
            else:
                v_cap = v_ahead

    if (
        abs(lat_ahead - lat_ego) < REFERENCE_LAT_CORRIDOR_M
        and abs(lat_ahead) < half_width * 0.6
    ):
        offset_target = -math.copysign(
            REFERENCE_LAT_OFFSET_MAX_M,
            lat_ahead if abs(lat_ahead) > 0.5 else 1.0,
        )
    else:
        offset_target = 0.0
    return v_cap, offset_target


def pure_professor_action(
    state: Mapping[str, object],
    *,
    velocity_profile: object,
    track_len_s: float,
    point_at: Callable[[float], Sequence[float]],
    steer_limit_rad: Callable[[float], float],
    half_width: float = 6.0,
) -> list[float]:
    """Compute one pure, stateless v2 professor action.

    ``state`` contains only reconstructed physical state and traffic tuples.
    ``point_at`` must return ``(x, y, tangent_heading)`` from the frozen
    geometry. No controller object or mutable passage state is consulted.
    """
    s_ego = float(state["s"])
    speed = float(state["speed"])
    lat_ego = float(state["lat"])
    traffic = state.get("traffic", ())
    v_cap, offset_target = _pure_traffic_adjust(
        s_ego,
        speed,
        lat_ego,
        traffic,
        track_len_s=track_len_s,
        half_width=half_width,
    )

    ld_probe = float(np.clip(
        REFERENCE_LOOKAHEAD_GAIN * speed,
        REFERENCE_LOOKAHEAD_MIN_M,
        REFERENCE_LOOKAHEAD_MAX_M,
    ))
    v_for_ld = min(speed, float(velocity_profile.at(s_ego + ld_probe)))
    lookahead = float(np.clip(
        REFERENCE_LOOKAHEAD_GAIN * v_for_ld,
        REFERENCE_LOOKAHEAD_MIN_M,
        REFERENCE_LOOKAHEAD_MAX_M,
    ))
    target_x, target_y, target_heading = map(
        float, point_at(s_ego + lookahead)
    )
    if offset_target:
        normal_x = -math.sin(target_heading)
        normal_y = math.cos(target_heading)
        target_x += normal_x * offset_target
        target_y += normal_y * offset_target

    x = float(state["x"])
    y = float(state["y"])
    heading = float(state["heading"])
    alpha = math.atan2(target_y - y, target_x - x) - heading
    alpha = (alpha + math.pi) % (2.0 * math.pi) - math.pi
    steer_rad = math.atan2(
        2.0 * REFERENCE_WHEELBASE_M * math.sin(alpha),
        lookahead,
    )

    v_target = float(velocity_profile.at(s_ego)) * REFERENCE_SPEED_MARGIN
    if v_cap is not None:
        v_target = min(v_target, v_cap)
    long_cmd = float(np.clip(
        (v_target - speed) / REFERENCE_GAIN,
        -1.0,
        1.0,
    ))
    steer_cmd = float(np.clip(
        steer_rad / float(steer_limit_rad(speed)),
        -1.0,
        1.0,
    ))
    action = np.asarray([steer_cmd, long_cmd], dtype=np.float64)
    if not np.all(np.isfinite(action)):
        raise CorpusError("pure professor action is not finite")
    return action.tolist()


def pinned_solo_forward(
    rows: Sequence[Mapping[str, object]],
    actor: object,
) -> list[list[float]]:
    """Run the pinned NumPy solo forward twice with convention IDs equal to 0."""
    if not rows:
        return []
    telemetry = np.asarray(
        [row["telemetry_edge_34"] for row in rows],
        dtype=np.float32,
    )
    ctx = np.asarray([row["ctx"] for row in rows], dtype=np.float32)
    if telemetry.ndim != 2 or telemetry.shape[1] != TELEMETRY_EDGE_DIM:
        raise CorpusError("telemetry_edge_34 must be an Nx34 array")
    if ctx.ndim != 2 or ctx.shape[1] != 2:
        raise CorpusError("ctx must be an Nx2 array")
    zero_ids = np.zeros(len(rows), dtype=np.int32)
    first = np.asarray(
        actor.forward_linear(telemetry, ctx, zero_ids, zero_ids)
    )
    second = np.asarray(
        actor.forward_linear(telemetry, ctx, zero_ids, zero_ids)
    )
    if first.shape != (len(rows), ACTION_DIM):
        raise CorpusError("solo forward must return an Nx2 array")
    if not np.array_equal(first, second):
        raise CorpusError("nondeterministic solo forward")
    if not np.all(np.isfinite(first)):
        raise CorpusError("solo forward returned non-finite values")
    return first.tolist()


def load_pinned_solo_actor(
    keras_path: str | Path,
    npz_path: str | Path,
) -> object:
    """Load the frozen v10 actor through the runner's NPZ export path."""
    from scripts.simulation.run_race_10_cars import (
        NumpyNeuralActor,
        ensure_npz_weights_exist,
    )

    keras = Path(keras_path)
    npz = Path(npz_path)
    return NumpyNeuralActor(ensure_npz_weights_exist(keras, npz))


class FrozenTrackProvider:
    """Runner-equivalent provider backed only by a frozen track file."""

    def __init__(self, name: str):
        try:
            from domain.track_resolution import load_track_frozen
        except ModuleNotFoundError:
            from backend.domain.track_resolution import load_track_frozen

        self.track = load_track_frozen(name, strict=True)
        self.name = str(self.track.name)
        normalized = str(name).strip().lower()
        if normalized in {"interlagos", "interlagos_v2", "sao paulo", "brazil"}:
            self.geometry_id = "interlagos_v2"
        elif normalized in {"monaco", "monaco_v2"}:
            self.geometry_id = "monaco_v2"
        else:
            raise CorpusError(f"unsupported frozen track provider: {name}")
        self.geometry_sha256 = FROZEN_GEOMETRY_SHA256[self.geometry_id]
        self.frozen_file_sha256 = str(
            getattr(self.track, "frozen_sha256", "")
        )
        self.waypoints = np.asarray(self.track.waypoints, dtype=np.float64)
        self._seg_B = np.roll(self.waypoints, -1, axis=0)
        self._seg_AB = self._seg_B - self.waypoints
        self._seg_len = np.hypot(self._seg_AB[:, 0], self._seg_AB[:, 1])
        self._seg_cum = np.concatenate(
            [[0.0], np.cumsum(self._seg_len)]
        )[:-1]
        self._seg_heading = np.arctan2(
            self._seg_AB[:, 1], self._seg_AB[:, 0]
        )
        self.track_len_s = float(self._seg_len.sum())
        self.half_width = float(self.track.width_m) / 2.0
        self.velocity_profile_config = {
            "grip_mult": 0.788,
            "sf": 0.80,
            "ds_target": 4.0,
            "smooth_window_m": 20.0,
        }
        self.velocity_profile = _provider_velocity_profile(self)

    def point_at(self, s: float) -> tuple[float, float, float]:
        s = float(s) % self.track_len_s
        j = int(np.searchsorted(self._seg_cum, s, side="right") - 1)
        j = min(max(j, 0), len(self._seg_len) - 1)
        t = (s - self._seg_cum[j]) / max(self._seg_len[j], 1e-9)
        x = self.waypoints[j, 0] + t * self._seg_AB[j, 0]
        y = self.waypoints[j, 1] + t * self._seg_AB[j, 1]
        return float(x), float(y), float(self._seg_heading[j])

    def project_on_path(
        self, x: float, y: float
    ) -> tuple[float, float, int, float]:
        ap_x = float(x) - self.waypoints[:, 0]
        ap_y = float(y) - self.waypoints[:, 1]
        denom = (self._seg_len * self._seg_len) + 1e-9
        t = np.clip(
            (ap_x * self._seg_AB[:, 0] + ap_y * self._seg_AB[:, 1])
            / denom,
            0.0,
            1.0,
        )
        proj_x = self.waypoints[:, 0] + t * self._seg_AB[:, 0]
        proj_y = self.waypoints[:, 1] + t * self._seg_AB[:, 1]
        d = np.hypot(proj_x - float(x), proj_y - float(y))
        i = int(np.argmin(d))
        s = self._seg_cum[i] + float(t[i]) * self._seg_len[i]
        cross = self._seg_AB[i, 0] * (float(y) - proj_y[i]) - (
            self._seg_AB[i, 1] * (float(x) - proj_x[i])
        )
        signed = float(d[i]) if cross >= 0.0 else -float(d[i])
        return float(d[i]), float(s), i, signed

    def provenance(self) -> dict:
        return {
            "name": self.name,
            "geometry_id": self.geometry_id,
            "geometry_sha256": self.geometry_sha256,
            "frozen_file_sha256": self.frozen_file_sha256,
            "track_len_s": self.track_len_s,
            "half_width": self.half_width,
            "point_at_source": "f1_env.py:638-646",
            "project_on_path_source": "f1_env.py:607-625",
            "tables_source": "f1_env.py:405-414",
        }


def _provider_value(provider: object, name: str) -> object:
    if isinstance(provider, Mapping):
        try:
            return provider[name]
        except KeyError as exc:
            raise CorpusError(f"track provider missing {name}") from exc
    try:
        return getattr(provider, name)
    except AttributeError as exc:
        raise CorpusError(f"track provider missing {name}") from exc


def _provider_callable(provider: object, name: str) -> Callable:
    value = _provider_value(provider, name)
    if not callable(value):
        raise CorpusError(f"track provider {name} is not callable")
    return value


def _provider_velocity_profile(provider: object) -> object:
    if isinstance(provider, Mapping) and "velocity_profile" in provider:
        return provider["velocity_profile"]
    if hasattr(provider, "velocity_profile"):
        return getattr(provider, "velocity_profile")
    waypoints = _provider_value(provider, "waypoints")
    from backend.model_train.velocity_profile import VelocityProfile

    return VelocityProfile(
        np.asarray(waypoints, dtype=np.float64),
        grip_mult=0.788,
        sf=0.80,
        ds_target=4.0,
        smooth_window_m=20.0,
    )


def build_teacher_states(
    joined_rows: Sequence[Mapping[str, object]],
    main_rows_by_tick: Mapping[int, Sequence[Mapping[str, object]]],
    *,
    track_providers: Mapping[str, object],
    track_len_s: float | None = None,
    half_width: float | None = None,
) -> list[dict]:
    """Compose pure-teacher states from the committed dump/main JOIN.

    The main CSV is authoritative for ``s``, ``lat`` and ``speed``.  Geometry
    providers are the runner's exact ``point_at`` implementation and expose
    the frozen dimensions; no pose or track geometry is inferred here.
    """
    if not joined_rows:
        return []
    states = []
    for joined in joined_rows:
        main = joined.get("_main")
        if not isinstance(main, Mapping):
            raise CorpusError("joined row is missing main CSV projection")
        geometry_id = str(joined.get("geometry_id", ""))
        provider = track_providers.get(geometry_id)
        if provider is None:
            raise CorpusError(f"missing track provider: {geometry_id}")
        provider_len = float(_provider_value(provider, "track_len_s"))
        provider_half_width = float(_provider_value(provider, "half_width"))
        length = provider_len if track_len_s is None else float(track_len_s)
        width = provider_half_width if half_width is None else float(half_width)
        if not math.isfinite(length) or length <= 0.0:
            raise CorpusError("track_len_s must come from a positive provider")
        if not math.isfinite(width) or width <= 0.0:
            raise CorpusError("half_width must come from a positive provider")
        if not math.isclose(length, provider_len, rel_tol=0.0, abs_tol=1e-9):
            raise CorpusError("track_len_s diverges from track provider")
        if not math.isclose(width, provider_half_width, rel_tol=0.0, abs_tol=1e-9):
            raise CorpusError("half_width diverges from track provider")

        tick = int(main["tick"])
        drv = str(main["drv"])
        tick_rows = list(main_rows_by_tick.get(tick, ()))
        if len(tick_rows) != 10:
            raise CorpusError(f"tick {tick} does not contain exactly 10 main rows")
        tick_drivers = [str(row["drv"]) for row in tick_rows]
        if len(set(tick_drivers)) != 10:
            raise CorpusError(f"tick {tick} contains duplicate main drivers")
        if drv not in tick_drivers:
            raise CorpusError(f"joined driver absent from main tick: {tick}/{drv}")
        try:
            s_ego = float(main["s"])
            lat_ego = float(main["lat"])
            speed = float(main["speed"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CorpusError(f"invalid main projection at {tick}/{drv}") from exc
        point_at = _provider_callable(provider, "point_at")
        px, py, heading = map(float, point_at(s_ego))
        nx, ny = -math.sin(heading), math.cos(heading)
        traffic = []
        for other in tick_rows:
            other_drv = str(other["drv"])
            if other_drv == drv:
                continue
            try:
                traffic.append((
                    float(other["s"]),
                    float(other["lat"]),
                    float(other["speed"]),
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise CorpusError(
                    f"invalid traffic projection at {tick}/{other_drv}"
                ) from exc
        if len(traffic) != 9:
            raise CorpusError(f"tick {tick}/{drv} traffic snapshot is incomplete")
        states.append({
            "tick": tick,
            "drv": drv,
            "s": s_ego,
            "lat": lat_ego,
            "speed": speed,
            "x": px + nx * lat_ego,
            "y": py + ny * lat_ego,
            "heading": heading,
            "traffic": traffic,
            "track_len_s": length,
            "half_width": width,
        })
    return states


def _state_builder_audit(
    provider: object,
    *,
    track_len_s: float,
    half_width: float,
    keras_path: Path,
    npz_path: Path,
) -> dict:
    profile = _provider_velocity_profile(provider)
    if isinstance(provider, Mapping):
        profile_config = provider.get("velocity_profile_config")
    else:
        profile_config = getattr(provider, "velocity_profile_config", None)
    if profile_config is None:
        profile_config = {
            "grip_mult": 0.788,
            "sf": 0.80,
            "ds_target": 4.0,
            "smooth_window_m": 20.0,
        }
    return {
        "pose_formula": "point_at(s), normal=(-sin(ph),cos(ph)), +lat=left",
        "traffic_source": "f1_env.py:803-808:_all_cars_snapshot",
        "velocity_profile": {
            "provider": "race_diagnostic.py:542-544",
            "config": profile_config,
            "object_type": type(profile).__name__,
        },
        "track_len_s": float(track_len_s),
        "half_width": float(half_width),
        "steer_limit_source": "f1_env.py:530-531",
        "point_at_source": "F1MultiContextEnv._point_at",
        "keras_path": str(keras_path),
        "npz_path": str(npz_path),
        "keras_sha256": sha256_file(keras_path) if keras_path.is_file() else None,
        "npz_sha256": sha256_file(npz_path) if npz_path.is_file() else None,
        "quoted_sources": [
            "f1_env.py:414",
            "f1_env.py:_project_on_path",
            "f1_env.py:803-808",
            "race_diagnostic.py:494,542-544",
            "run_race_10_cars.py:1686,1805",
        ],
    }


def run_teacher_labeling(
    dump_path: str | Path,
    main_csv: str | Path,
    *,
    source_git_sha256: str,
    track_providers: Mapping[str, object],
    actor: object | None = None,
    keras_path: str | Path = "model_train/v10_dagger/dagger_actor_best.keras",
    npz_path: str | Path = "model_train/v10_dagger/dagger_actor_best_weights.npz",
) -> tuple[dict, dict]:
    """Run the deterministic 1F label composition without writing artifacts."""
    dump_rows, dump_audit = load_composite_dump(
        dump_path, source_git_sha256=source_git_sha256
    )
    if not dump_rows:
        raise CorpusError("dump has no data rows")
    geometry_id = str(dump_rows[0]["geometry_id"])
    provider = track_providers.get(geometry_id)
    if provider is None:
        raise CorpusError(f"missing track provider: {geometry_id}")
    track_len_s = float(_provider_value(provider, "track_len_s"))
    half_width = float(_provider_value(provider, "half_width"))
    joined, join_audit = join_dump_with_main_csv(
        dump_rows,
        main_csv,
        track_len_s=track_len_s,
        dump_sha256=dump_audit["sha256"],
    )
    episodes_by_run: dict[str, set[str]] = {}
    for row in joined:
        run = str(row["run"])
        drv = str(row["drv"])
        episodes_by_run.setdefault(run, set()).add(drv)
    episode_splits = {
        (run, drv): split
        for run, drivers in episodes_by_run.items()
        for drv, split in assign_episode_splits(run, drivers).items()
    }
    main_rows_by_tick: dict[int, list[dict]] = {}
    for row in joined:
        main = row["_main"]
        main_rows_by_tick.setdefault(int(main["tick"]), []).append(main)
    states = build_teacher_states(
        joined,
        main_rows_by_tick,
        track_providers=track_providers,
        track_len_s=track_len_s,
        half_width=half_width,
    )
    profile = _provider_velocity_profile(provider)
    point_at = _provider_callable(provider, "point_at")
    from backend.model_train.f1_env import F1MultiContextEnv

    professor_actions = professor_replay(
        states,
        lambda state: pure_professor_action(
            state,
            velocity_profile=profile,
            track_len_s=track_len_s,
            point_at=point_at,
            steer_limit_rad=F1MultiContextEnv.steer_limit_rad,
            half_width=half_width,
        ),
    )
    if actor is None:
        actor = load_pinned_solo_actor(keras_path, npz_path)
    solo_linear = pinned_solo_forward(joined, actor)
    dataset = convert_reconstructed(
        joined,
        professor_actions=professor_actions,
        solo_linear=solo_linear,
        episode_splits=episode_splits,
    )
    dataset["state_builder_provenance"] = _state_builder_audit(
        provider,
        track_len_s=track_len_s,
        half_width=half_width,
        keras_path=Path(keras_path),
        npz_path=Path(npz_path),
    )
    dataset_audit = audit_dataset(dataset)
    audit = {
        "dump": dump_audit,
        "join": join_audit,
        "state_builder": dataset["state_builder_provenance"],
        "dataset": dataset_audit,
        "split_rule": SPLIT_RULE_NAME,
        "split_counts": dataset_audit["split_counts"],
    }
    return dataset, audit


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_header(path: Path) -> tuple[str | None, list[str]]:
    comment = None
    with path.open(newline="", encoding="utf-8") as stream:
        for raw in stream:
            if raw.startswith("#"):
                if comment is None:
                    comment = raw.rstrip("\n")
                continue
            return comment, next(csv.reader([raw]))
    raise CorpusError(f"{path}: missing CSV header")


def _embedded_geometry(comment: str | None) -> str | None:
    if not comment:
        return None
    match = GEOMETRY_RE.search(comment)
    return match.group(1).lower() if match else None


def inspect_source(
    path: str | Path,
    *,
    expected_geometry_id: str | None = None,
    expected_geometry_sha256: str | None = None,
    expected_embedded_geometry_sha256: str | None = None,
    manifest_entry: Mapping[str, object] | None = None,
) -> dict:
    """Census one source without treating observed actions as labels."""
    source = Path(path)
    if not source.is_file():
        return {
            "path": str(source),
            "status": "rejected",
            "reason": "missing_source",
        }

    disk_sha = sha256_file(source)
    comment, header = _read_header(source)
    header_set = set(header)
    embedded = _embedded_geometry(comment)
    result = {
        "path": str(source),
        "sha256": disk_sha,
        "header_sha256": hashlib.sha256(
            ",".join(header).encode("utf-8")
        ).hexdigest(),
        "column_count": len(header),
        "header": header,
        "geometry_id": expected_geometry_id,
        "embedded_geometry_sha256": embedded,
        "manifest_untracked": bool(
            manifest_entry and manifest_entry.get("untracked_disclosure")
        ),
        "observed_action_columns": ["th", "brk", "steer_rad"] == [
            c for c in ("th", "brk", "steer_rad") if c in header_set
        ],
        "status": "candidate",
        "reason": None,
    }

    if manifest_entry and manifest_entry.get("disk_sha256") not in (None, disk_sha):
        result.update(status="rejected", reason="manifest_disk_hash_mismatch")
        return result
    source_class = manifest_entry.get("class") if manifest_entry else None
    if source_class and source_class != "race_timeseries":
        result.update(status="excluded", reason=f"manifest_class:{source_class}")
        return result
    if not manifest_entry and source.suffix.lower() not in {".csv", ".tsv"}:
        result.update(status="excluded", reason="report_or_metadata_source")
        return result
    if expected_geometry_id and not expected_geometry_sha256:
        result.update(status="rejected", reason="geometry_hash_not_pinned")
        return result
    if expected_geometry_sha256:
        expected_embedded = (
            expected_embedded_geometry_sha256 or expected_geometry_sha256
        )
        if not embedded or embedded.lower() != expected_embedded.lower():
            result.update(status="rejected", reason="geometry_hash_missing_or_mismatch")
            return result

    missing = sorted(RACE_REQUIRED - header_set)
    if missing:
        result.update(status="rejected", reason=f"missing_required:{','.join(missing)}")
        return result
    if result["manifest_untracked"]:
        result.update(status="rejected", reason="source_sem_blob_head")
        return result
    # The measured files expose legacy/res16d values, not the reconstructed
    # edge+traffic state required by v15. This is an explicit census result.
    missing_reconstruction = sorted(
        {"telemetry_edge_34", *TRAFFIC_COLUMNS, "geometry_id"} - header_set
    )
    if missing_reconstruction:
        result.update(
            status="rejected",
            reason="reconstruction_required:" + ",".join(missing_reconstruction),
        )
        return result
    result["status"] = "eligible"
    return result


def build_residual_input(
    traffic_features: Sequence[float],
    speed_mps: float,
    curvature_ahead: float,
    previous_steer: float,
    previous_longitudinal: float,
) -> list[float]:
    if len(traffic_features) != TRAFFIC_DIM:
        raise CorpusError(f"traffic_features must have {TRAFFIC_DIM} values")
    values = [
        *map(float, traffic_features),
        float(speed_mps) / 100.0,
        float(curvature_ahead) * 25.0,
        float(previous_steer),
        float(previous_longitudinal),
    ]
    if not all(math.isfinite(value) for value in values):
        raise CorpusError("residual input contains a non-finite value")
    return values


def _action(value: Sequence[float]) -> list[float]:
    if len(value) != ACTION_DIM or not all(math.isfinite(float(x)) for x in value):
        raise CorpusError("professor action must be finite float[2]")
    return [float(x) for x in value]


def professor_replay(
    states: Sequence[Mapping[str, object]],
    replay_action: Callable[[Mapping[str, object]], Sequence[float]],
) -> list[list[float]]:
    """Replay a pure professor twice per state and reject nondeterminism."""
    output = []
    for state in states:
        first = _action(replay_action(state))
        second = _action(replay_action(state))
        if first != second:
            raise CorpusError("professor replay is nondeterministic")
        output.append(first)
    return output


def _episode_key(row: Mapping[str, object]) -> str:
    try:
        return f"{row['run']}::{row['drv']}"
    except KeyError as exc:
        raise CorpusError(f"missing episode field: {exc.args[0]}") from exc


def _legacy_threshold_split_episode(run: str, drv: str) -> str:
    digest = hashlib.sha256(f"{run}::{drv}".encode("utf-8")).digest()[0] % 100
    if digest < SPLIT_RULE["train"]:
        return "train"
    if digest < SPLIT_RULE["train"] + SPLIT_RULE["validation"]:
        return "validation"
    return "test"


def assign_episode_splits(run: str, episode_ids: Iterable[str]) -> Mapping[str, str]:
    """Assign one run's episodes by full-hash rank, independent of row values."""
    drivers = [str(drv) for drv in episode_ids]
    if len(drivers) < 3:
        raise CorpusError("cannot split fewer than 3 episodes")
    if len(set(drivers)) != len(drivers):
        raise CorpusError("episode_ids contains duplicate drivers")

    ranked = sorted(
        drivers,
        key=lambda drv: (
            hashlib.sha256(f"{run}::{drv}".encode("utf-8")).hexdigest(),
            drv,
        ),
    )
    train_count = 8 * len(ranked) // 10
    validation_count = len(ranked) // 10
    train = ranked[:train_count]
    validation = ranked[train_count:train_count + validation_count]
    test = ranked[train_count + validation_count:]

    for bucket in (validation, test):
        if not bucket:
            if not train:
                raise CorpusError("cannot allocate nonempty split buckets")
            bucket.append(train.pop())

    return {
        drv: split
        for split, bucket in zip(SPLIT_BUCKETS, (train, validation, test))
        for drv in bucket
    }


def convert_reconstructed(
    rows: Sequence[Mapping[str, object]],
    *,
    professor_actions: Sequence[Sequence[float]],
    solo_linear: Sequence[Sequence[float]],
    episode_splits: Mapping[tuple[str, str], str] | None = None,
) -> dict:
    """Build v15 records from externally reconstructed, validated states.

    ``th``, ``brk`` and ``steer_rad`` are intentionally never read.
    ``solo_linear`` must come from the pinned NumPy v10 forward; this function
    does not execute that forward.
    """
    if episode_splits is None:
        raise CorpusError("episode_splits is required")
    if len(rows) != len(professor_actions) or len(rows) != len(solo_linear):
        raise CorpusError("rows, professor_actions and solo_linear lengths differ")
    previous_episode = None
    previous_tick = None
    records = []
    for row, action, solo in zip(rows, professor_actions, solo_linear):
        episode = _episode_key(row)
        split_key = (str(row["run"]), str(row["drv"]))
        if split_key not in episode_splits:
            raise CorpusError(
                f"episode missing from episode_splits: {split_key[0]}::{split_key[1]}"
            )
        split = episode_splits[split_key]
        if split not in SPLIT_BUCKETS:
            raise CorpusError(f"invalid split for episode {split_key}: {split}")
        tick = int(row["tick"])
        if previous_episode == episode and tick <= int(previous_tick):
            raise CorpusError("episode rows are duplicated or out of order")
        previous_episode, previous_tick = episode, tick
        if row.get("geometry_id") not in {"interlagos_v2", "monaco_v2"}:
            raise CorpusError("geometry_id is absent or not frozen")
        if row.get("geometry_sha256") != FROZEN_GEOMETRY_SHA256[row["geometry_id"]]:
            raise CorpusError("geometry_sha256 is absent or divergent")
        if not row.get("instrument_version"):
            raise CorpusError("instrument_version is absent")
        if not row.get("source_sha256"):
            raise CorpusError("source_sha256 is absent")
        if "source_git_sha256" not in row:
            raise CorpusError("source_git_sha256 provenance field is absent")
        telemetry = list(map(float, row["telemetry_edge_34"]))
        if len(telemetry) != TELEMETRY_EDGE_DIM:
            raise CorpusError("telemetry_edge_34 must have 34 values")
        if len(row["ctx"]) != 2:
            raise CorpusError("ctx must have 2 values")
        res_in = build_residual_input(
            row["traffic_features_12"],
            row["speed_mps"],
            row["curvature_ahead"],
            row["previous_steer"],
            row["previous_longitudinal"],
        )
        a_teacher = _action(action)
        m_solo = _action(solo)
        clipped = [max(-0.98, min(0.98, value)) for value in a_teacher]
        r_target = [math.atanh(value) - m for value, m in zip(clipped, m_solo)]
        records.append({
            "run": str(row["run"]),
            "drv": str(row["drv"]),
            "tick": tick,
            "t_s": float(row["t_s"]),
            "geometry_id": row["geometry_id"],
            "geometry_sha256": str(row["geometry_sha256"]),
            "source_sha256": str(row["source_sha256"]),
            "source_git_sha256": row["source_git_sha256"],
            "instrument_version": str(row["instrument_version"]),
            "track_id": int(row["track_id"]),
            "compound_id": int(row["compound_id"]),
            "telemetry": telemetry,
            "ctx": list(map(float, row["ctx"])),
            "res_inputs": res_in,
            "r_targets": r_target,
            "split": split,
        })
    return {
        "schema": "composite-corpus-v1",
        "contract": "v15-residual-gated",
        "instrument_version": "composite-corpus-v1",
        "telemetry_dim": TELEMETRY_EDGE_DIM,
        "res_inputs_dim": RESIDUAL_DIM,
        "r_targets_dim": ACTION_DIM,
        "split_rule": SPLIT_RULE_NAME,
        "records": records,
    }


def audit_dataset(dataset: Mapping[str, object]) -> dict:
    records = list(dataset.get("records", []))
    counts = {name: 0 for name in ("train", "validation", "test")}
    for record in records:
        split = record.get("split")
        if split not in counts:
            raise CorpusError(f"invalid split: {split}")
        counts[split] += 1
        if len(record["res_inputs"]) != RESIDUAL_DIM:
            raise CorpusError("invalid res_inputs width")
        if len(record["r_targets"]) != ACTION_DIM:
            raise CorpusError("invalid r_targets width")
    encoded = json.dumps(dataset, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": dataset.get("schema"),
        "record_count": len(records),
        "split_rule": dataset.get("split_rule"),
        "split_counts": counts,
        "dataset_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def load_composite_dump(
    path: str | Path,
    *,
    source_git_sha256: str,
) -> tuple[list[dict], dict]:
    """Load one committed recorder dump without running a model or simulator."""
    source = Path(path)
    source_sha256 = sha256_file(source)
    rows = []
    header = None
    with gzip.open(source, "rt", encoding="utf-8", newline="") as stream:
        for line_number, raw in enumerate(stream, 1):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CorpusError(f"{source}:{line_number}: invalid JSON") from exc
            if line_number == 1:
                if payload.get("_schema") != "composite-corpus-dump-v3":
                    raise CorpusError(f"{source}: unsupported dump schema")
                header = payload
                continue
            required = {
                "run", "drv", "tick", "t_s", "geometry_id",
                "geometry_sha256", "instrument_version", "track_id",
                "compound_id", "telemetry_edge_34", "ctx",
                "traffic_features_12", "speed_mps", "curvature_ahead",
                "previous_steer", "previous_longitudinal",
            }
            missing = sorted(required - payload.keys())
            if missing:
                raise CorpusError(
                    f"{source}:{line_number}: missing fields {','.join(missing)}"
                )
            compound_id = payload.get("compound_id")
            if (
                isinstance(compound_id, bool)
                or not isinstance(compound_id, int)
            ):
                raise CorpusError(
                    f"{source}:{line_number}: compound_id must be an integer"
                )
            enriched = dict(payload)
            enriched["source_sha256"] = source_sha256
            enriched["source_git_sha256"] = source_git_sha256
            rows.append(enriched)
    if header is None:
        raise CorpusError(f"{source}: missing schema record")
    if header.get("geometry_id") not in FROZEN_GEOMETRY_SHA256:
        raise CorpusError(f"{source}: geometry_id is absent or not frozen")
    if header.get("geometry_sha256") != FROZEN_GEOMETRY_SHA256[header["geometry_id"]]:
        raise CorpusError(f"{source}: geometry hash is absent or divergent")
    if not source_git_sha256:
        raise CorpusError(f"{source}: source Git blob is absent")
    return rows, {
        "path": str(source),
        "sha256": source_sha256,
        "source_git_sha256": source_git_sha256,
        "run": header.get("run"),
        "geometry_id": header.get("geometry_id"),
        "geometry_sha256": header.get("geometry_sha256"),
        "instrument_version": header.get("instrument_version"),
        "row_count": len(rows),
    }


def audit_dump_families(rows: Sequence[Mapping[str, object]]) -> dict:
    """Report only families derivable from the frozen dump columns."""
    launch = sum(float(row["t_s"]) < 60.0 for row in rows)
    return {
        "launch_t_lt_60s": int(launch),
        "nose_to_tail_gt_60s": {
            "status": "unavailable",
            "reason": "dump omits explicit gap/leader identity",
        },
        "monaco_rejoin": {
            "status": "unavailable",
            "reason": "dump omits rejoin phase markers",
        },
        "hesitations_post_reentry_le_10s": {
            "status": "unavailable",
            "reason": "dump omits reentry timestamps",
        },
    }


JOIN_REQUIRED_COLUMNS = (
    "tick", "t_s", "drv", "speed", "s", "lat", "offtrack", "authority",
)
NOSE_TO_TAIL_MAX_GAP_M = 40.0
NOSE_TO_TAIL_MAX_LAT_DIFF_M = 2.0
NOSE_TO_TAIL_MIN_SPEED_DELTA_MPS = -2.0
NOSE_TO_TAIL_SUSTAINED_SAMPLES = 5
HESITATION_SPEED_MPS = 0.5
REJOIN_WINDOW_S = 10.0


def _parse_metadata_header(raw: str, source: Path) -> dict[str, str]:
    if not raw.startswith("#"):
        raise CorpusError(f"{source}:1: missing metadata header")
    metadata = {}
    for segment in raw[1:].strip().split(" | "):
        if "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _parse_grid_order(metadata: Mapping[str, str], source: Path) -> list[str]:
    raw = metadata.get("grid_order")
    if raw is None:
        raise CorpusError(f"{source}: unparseable grid_order")
    if not re.fullmatch(r"\['[^']*'(?:, '[^']*')*\]", raw):
        raise CorpusError(f"{source}: unparseable grid_order")
    values = re.findall(r"'([^']*)'", raw)
    if (
        not values
        or any(not value for value in values)
        or len(values) != len(set(values))
    ):
        raise CorpusError(f"{source}: unparseable grid_order")
    return values


def _read_main_rows(
    path: str | Path,
) -> tuple[list[dict[str, str]], str, dict[str, str]]:
    source = Path(path)
    source_sha256 = sha256_file(source)
    with source.open(newline="", encoding="utf-8") as stream:
        metadata_line = stream.readline()
        metadata = _parse_metadata_header(metadata_line.rstrip("\r\n"), source)
        header_line_number = 1
        header_line = None
        for header_line_number, raw in enumerate(stream, 2):
            if not raw.startswith("#"):
                header_line = raw
                break
        if header_line is None:
            raise CorpusError(
                f"{source}:{header_line_number}: missing CSV header"
            )
        fieldnames = next(csv.reader([header_line]))
        reader = csv.DictReader(stream, fieldnames=fieldnames)
        missing = [name for name in JOIN_REQUIRED_COLUMNS
                   if name not in fieldnames]
        if missing:
            raise CorpusError(
                f"{source}:{header_line_number}: missing JOIN columns "
                f"{','.join(missing)}"
            )
        rows = []
        for line_number, row in enumerate(reader, header_line_number + 1):
            if None in row:
                raise CorpusError(f"{source}:{line_number}: malformed CSV row")
            rows.append(row)
    return rows, source_sha256, metadata


def _join_key(row: Mapping[str, object]) -> tuple[int, str]:
    try:
        return int(row["tick"]), str(row["drv"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CorpusError("JOIN key requires integer tick and driver") from exc


def join_dump_with_main_csv(
    dump_rows: Sequence[Mapping[str, object]],
    main_csv: str | Path,
    *,
    track_len_s: float,
    dump_sha256: str | None = None,
) -> tuple[list[dict], dict]:
    """Join the dump to its same-run main CSV by exact ``(tick, drv)``.

    The diagnostic CSV is sampled at 5 Hz while the recorder is logical-tick
    (10 Hz), so main rows are the authoritative, joinable subset. Every main
    key must exist exactly once in the dump; extra dump ticks are retained as
    unclassified recorder rows and reported in the audit.
    """
    if track_len_s <= 0:
        raise CorpusError("track_len_s must be positive")
    all_main_rows, main_sha256, main_metadata = _read_main_rows(main_csv)
    grid_order = _parse_grid_order(main_metadata, Path(main_csv))
    grid_index = {driver: index for index, driver in enumerate(grid_order)}
    seen_main = set()
    previous_order_key = None
    for row in all_main_rows:
        key = _join_key(row)
        if key[1] not in grid_index:
            raise CorpusError(
                f"main CSV driver absent from grid_order: {key[1]}"
            )
        if key in seen_main:
            raise CorpusError(f"main CSV duplicate JOIN key: {key[0]}/{key[1]}")
        order_key = (key[0], grid_index[key[1]])
        if previous_order_key is not None and order_key <= previous_order_key:
            raise CorpusError("main CSV JOIN keys are out of order")
        previous_order_key = order_key
        seen_main.add(key)
    main_rows = [
        row for row in all_main_rows
        if int(row["tick"]) % 2 == 0
    ]
    dump_by_key = {}
    for row in dump_rows:
        key = _join_key(row)
        if key in dump_by_key:
            raise CorpusError(f"dump duplicate JOIN key: {key[0]}/{key[1]}")
        dump_by_key[key] = row
    joined = []
    for row in main_rows:
        key = _join_key(row)
        dump_row = dump_by_key.get(key)
        if dump_row is None:
            raise CorpusError(
                f"JOIN key absent from dump: {key[0]}/{key[1]}"
            )
        enriched = dict(dump_row)
        enriched["_main"] = row
        joined.append(enriched)
    dump_totals: dict[str, int] = {}
    dump_paired: dict[str, int] = {}
    for row in dump_rows:
        driver = str(row["drv"])
        dump_totals[driver] = dump_totals.get(driver, 0) + 1
    for row in joined:
        driver = str(row["drv"])
        dump_paired[driver] = dump_paired.get(driver, 0) + 1
    dump_sources = {str(row.get("source_sha256", "")) for row in dump_rows}
    if dump_sha256 is None and len(dump_sources) == 1:
        dump_sha256 = next(iter(dump_sources)) or None
    if not dump_sha256:
        raise CorpusError("dump SHA-256 is required for JOIN pair provenance")
    pair_sha256 = hashlib.sha256(
        f"{dump_sha256}:{main_sha256}".encode()
    ).hexdigest()
    return joined, {
        "main_csv": str(main_csv),
        "main_sha256": main_sha256,
        "main_csv_metadata": main_metadata,
        "joined_rows": len(joined),
        "dump_rows": len(dump_rows),
        "unmatched_dump_rows": len(dump_rows) - len(joined),
        "paired_by_drv": {
            driver: {
                "paired": dump_paired.get(driver, 0),
                "total": total,
                "fraction": dump_paired.get(driver, 0) / total,
            }
            for driver, total in sorted(dump_totals.items())
        },
        "pair_sha256": pair_sha256,
    }


def classify_joined_families(
    joined_rows: Sequence[Mapping[str, object]],
    *,
    track_len_s: float,
) -> dict:
    """Classify families from the strict same-run JOIN, without imputation."""
    by_tick: dict[int, list[dict]] = {}
    by_driver: dict[str, list[dict]] = {}
    for row in joined_rows:
        main = row["_main"]
        tick, drv = _join_key(main)
        item = dict(main)
        item["_dump"] = row
        item["_tick"] = tick
        item["_drv"] = drv
        by_tick.setdefault(tick, []).append(item)
        by_driver.setdefault(drv, []).append(item)

    reentry_times: dict[str, list[float]] = {}
    for drv, rows in by_driver.items():
        rows.sort(key=lambda item: item["_tick"])
        was_off = False
        for item in rows:
            off = bool(int(float(item["offtrack"])))
            authority = str(item["authority"]).lower()
            if (was_off and not off) or "rejoin" in authority:
                reentry_times.setdefault(drv, []).append(float(item["t_s"]))
            was_off = off

    nose_state: dict[tuple[str, str], int] = {}
    family_counts = {
        "launch_t_lt_60s": 0,
        "nose_to_tail_gt_60s": 0,
        "monaco_rejoin": 0,
        "hesitations_post_reentry_le_10s": 0,
    }
    labels = []
    for tick in sorted(by_tick):
        current = by_tick[tick]
        for ego in current:
            t_s = float(ego["t_s"])
            drv = ego["_drv"]
            launch = t_s < 60.0
            rejoin = any(
                0.0 <= t_s - start <= REJOIN_WINDOW_S
                for start in reentry_times.get(drv, [])
            )
            hesitation = rejoin and float(ego["speed"]) < HESITATION_SPEED_MPS
            leader = None
            best_gap = None
            for other in current:
                if other["_drv"] == drv:
                    continue
                gap = (float(other["s"]) - float(ego["s"])) % track_len_s
                if gap <= 0.0 or gap > NOSE_TO_TAIL_MAX_GAP_M:
                    continue
                if abs(float(other["lat"]) - float(ego["lat"])) > NOSE_TO_TAIL_MAX_LAT_DIFF_M:
                    continue
                if best_gap is None or gap < best_gap:
                    best_gap, leader = gap, other
            nose = False
            if leader is not None:
                pair = (drv, leader["_drv"])
                speed_ok = (
                    float(ego["speed"]) - float(leader["speed"])
                    >= NOSE_TO_TAIL_MIN_SPEED_DELTA_MPS
                )
                count = nose_state.get(pair, 0) + 1 if speed_ok else 0
                nose_state[pair] = count
                nose = count >= NOSE_TO_TAIL_SUSTAINED_SAMPLES and t_s > 60.0
            else:
                for pair in [pair for pair in nose_state if pair[0] == drv]:
                    nose_state[pair] = 0
            family_counts["launch_t_lt_60s"] += int(launch)
            family_counts["nose_to_tail_gt_60s"] += int(nose)
            family_counts["monaco_rejoin"] += int(rejoin)
            family_counts["hesitations_post_reentry_le_10s"] += int(hesitation)
            labels.append({
                "tick": tick,
                "drv": drv,
                "launch": launch,
                "nose_to_tail": nose,
                "monaco_rejoin": rejoin,
                "hesitation_post_reentry": hesitation,
            })
    return {
        "family_counts": family_counts,
        "labels": labels,
        "rules": {
            "nose_to_tail_max_gap_m": NOSE_TO_TAIL_MAX_GAP_M,
            "nose_to_tail_max_lat_diff_m": NOSE_TO_TAIL_MAX_LAT_DIFF_M,
            "nose_to_tail_min_speed_delta_mps": NOSE_TO_TAIL_MIN_SPEED_DELTA_MPS,
            "nose_to_tail_sustained_samples": NOSE_TO_TAIL_SUSTAINED_SAMPLES,
            "rejoin_window_s": REJOIN_WINDOW_S,
            "hesitation_speed_mps": HESITATION_SPEED_MPS,
        },
    }


def write_json(path: str | Path, payload: Mapping[str, object]) -> str:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    destination.write_text(encoded, encoding="utf-8")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def census_manifest_sources(
    manifest_path: str | Path,
    source_paths: Iterable[str | Path],
    geometry_by_id: Mapping[str, Mapping[str, str]],
) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    entries = {
        key: entry
        for tier in ("tier_A", "tier_B")
        for entry in manifest.get(tier, [])
        for key in (entry["path"], str(entry["path"]).removeprefix("backend/"))
    }
    results = []
    for source_path in source_paths:
        relative = str(source_path)
        entry = entries.get(relative)
        geometry_id = entry.get("geometry_id") if entry else None
        results.append(inspect_source(
            source_path,
            expected_geometry_id=geometry_id,
            expected_geometry_sha256=geometry_by_id.get(geometry_id, {}).get("file_sha256"),
            expected_embedded_geometry_sha256=geometry_by_id.get(geometry_id, {}).get(
                "embedded_geometry_sha256"
            ),
            manifest_entry=entry,
        ))
    return {
        "schema": "composite-corpus-census-v1",
        "manifest_sha256": sha256_file(Path(manifest_path)),
        "sources": results,
    }


_CONVERT_1F_CASES = {
    "A": {
        "dump": Path("experiments/composite-1/A_ON_dump_interrupted3.jsonl.gz"),
        "main": Path("experiments/composite-1/A_ON_main_interrupted3.csv"),
        "track": "interlagos",
    },
    "B": {
        "dump": Path("experiments/composite-1/B_ON_dump.jsonl.gz"),
        "main": Path("experiments/composite-1/B_ON_main.csv"),
        "track": "Monaco",
    },
}
_DEFAULT_SOURCE_GIT_SHA256 = "7ef87c8f4e880b979c6dc8c77915a8f57356dd03"


def _write_1f_case_outputs(
    case: str,
    dataset: Mapping[str, object],
    audit: Mapping[str, object],
    out_dir: Path,
) -> None:
    records = sorted(
        list(dataset["records"]),
        key=lambda row: (str(row["run"]), str(row["drv"]), int(row["tick"])),
    )
    by_episode: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        by_episode.setdefault(
            (str(record["run"]), str(record["drv"])), []
        ).append(record)
    for (run, drv), episode_records in sorted(by_episode.items()):
        safe_run = re.sub(r"[^A-Za-z0-9_.-]+", "_", run)
        safe_drv = re.sub(r"[^A-Za-z0-9_.-]+", "_", drv)
        write_json(
            out_dir / f"{case}_{safe_run}_{safe_drv}.json",
            {"schema": "composite-corpus-v1", "records": episode_records},
        )
    write_json(out_dir / f"{case}_audit.json", audit)


def convert_1f_cli(
    *,
    case: str,
    out_dir: str | Path,
    write: bool,
    source_git_sha256: str,
) -> dict:
    selected = _CONVERT_1F_CASES if case == "all" else {case: _CONVERT_1F_CASES[case]}
    providers = {
        "interlagos_v2": FrozenTrackProvider("interlagos"),
        "monaco_v2": FrozenTrackProvider("Monaco"),
    }
    actor = load_pinned_solo_actor(
        "model_train/v10_dagger/dagger_actor_best.keras",
        "model_train/v10_dagger/dagger_actor_best_weights.npz",
    )
    result = {}
    for case_name, config in selected.items():
        expected_provider = providers[
            "interlagos_v2" if config["track"] == "interlagos" else "monaco_v2"
        ]
        dataset, audit = run_teacher_labeling(
            config["dump"],
            config["main"],
            source_git_sha256=source_git_sha256,
            track_providers=providers,
            actor=actor,
            keras_path="model_train/v10_dagger/dagger_actor_best.keras",
            npz_path="model_train/v10_dagger/dagger_actor_best_weights.npz",
        )
        if audit["dump"]["geometry_id"] != expected_provider.geometry_id:
            raise CorpusError(
                f"{case_name}: dump geometry diverges from fixed case provider"
            )
        dump_rows, dump_audit = load_composite_dump(
            config["dump"], source_git_sha256=source_git_sha256
        )
        joined, join_audit = join_dump_with_main_csv(
            dump_rows,
            config["main"],
            track_len_s=expected_provider.track_len_s,
            dump_sha256=dump_audit["sha256"],
        )
        family_audit = classify_joined_families(
            joined, track_len_s=expected_provider.track_len_s
        )
        audit = dict(audit)
        audit["families"] = family_audit["family_counts"]
        audit["provider"] = expected_provider.provenance()
        audit["paired_by_frac"] = join_audit["paired_by_drv"]
        if write:
            _write_1f_case_outputs(case_name, dataset, audit, Path(out_dir))
        result[case_name] = {
            "record_count": len(dataset["records"]),
            "episode_count": len({
                (str(row["run"]), str(row["drv"]))
                for row in dataset["records"]
            }),
            "split_counts": audit_dataset(dataset)["split_counts"],
            "families": audit["families"],
            "written": bool(write),
        }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    convert = subparsers.add_parser("convert-1f")
    convert.add_argument("--case", choices=("A", "B", "all"), default="all")
    convert.add_argument(
        "--source-git-sha256",
        default=_DEFAULT_SOURCE_GIT_SHA256,
    )
    convert.add_argument(
        "--out-dir",
        default="experiments/composite-1/shards",
    )
    convert.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "convert-1f":
        payload = convert_1f_cli(
            case=args.case,
            out_dir=args.out_dir,
            write=args.write,
            source_git_sha256=args.source_git_sha256,
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    raise CorpusError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
