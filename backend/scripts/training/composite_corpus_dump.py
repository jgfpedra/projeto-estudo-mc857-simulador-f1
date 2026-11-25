"""Opt-in JSONL.GZ writer for the v15 Composite corpus contract."""
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


import gzip
import hashlib
import json
import pickle
from pathlib import Path
from typing import Mapping, Sequence

SCHEMA = "composite-corpus-dump-v3"
SUPPLEMENTARY_COMPOUNDS = {"HARD": 3}
TRAFFIC_DIM = 12
EDGE_DIM = 34


class CorpusDumpError(ValueError):
    """Raised when a dump row violates the frozen recording contract."""


def load_compound_mapping(path: str | Path) -> dict[str, int]:
    with Path(path).open("rb") as stream:
        payload = pickle.load(stream)
    compounds = payload.get("compounds") if isinstance(payload, dict) else None
    if not isinstance(compounds, dict) or not compounds:
        raise CorpusDumpError("mappings.pkl lacks non-empty 'compounds' mapping")
    result = {}
    for name, value in compounds.items():
        if not isinstance(name, str) or not isinstance(value, int):
            raise CorpusDumpError("compound mapping must be str -> int")
        result[name] = value
    for name, value in SUPPLEMENTARY_COMPOUNDS.items():
        if name in result and result[name] != value:
            raise CorpusDumpError(
                f"supplementary compound mapping collides for {name!r}"
            )
        result[name] = value
    return result


def resolve_compound_id(compound, compound_mapping: Mapping[str, int]) -> int:
    name = getattr(compound, "value", compound)
    if name is None:
        raise ValueError("compound is None; cannot resolve compound_id")
    key = str(name)
    if key not in compound_mapping:
        raise ValueError(f"compound {key!r} absent from frozen mapping")
    return int(compound_mapping[key])


def _finite_vector(name: str, values: Sequence[float], size: int) -> list[float]:
    if len(values) != size:
        raise CorpusDumpError(f"{name} must have {size} values")
    result = [float(value) for value in values]
    if not all(map(lambda value: value == value and abs(value) != float("inf"),
                   result)):
        raise CorpusDumpError(f"{name} contains a non-finite value")
    return result


class CompositeCorpusDump:
    """Deterministic, fail-loud JSONL.GZ writer.

    The writer owns only previous-action state. It never feeds a recorded row
    back into the simulator or the policy.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        run: str,
        geometry_id: str,
        geometry_sha256: str,
        instrument_version: str = "composite-corpus-dump-v3",
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = gzip.GzipFile(
            filename=str(self.path), mode="wb", mtime=0
        )
        self._text = self._stream
        self.run = str(run)
        self.geometry_id = str(geometry_id)
        self.geometry_sha256 = str(geometry_sha256)
        self.instrument_version = str(instrument_version)
        self._last_tick: dict[str, int] = {}
        self._previous_actions: dict[str, tuple[float, float]] = {}
        self.rows = 0
        self._write({
            "_schema": SCHEMA,
            "instrument_version": self.instrument_version,
            "run": self.run,
            "geometry_id": self.geometry_id,
            "geometry_sha256": self.geometry_sha256,
        })

    def _write(self, payload: Mapping[str, object]) -> None:
        encoded = (
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        self._text.write(encoded)

    def write_row(
        self,
        *,
        drv: str,
        tick: int,
        t_s: float,
        track_id: int,
        compound_id: int,
        telemetry_edge_34: Sequence[float],
        ctx: Sequence[float],
        traffic_features_12: Sequence[float],
        speed_mps: float,
        curvature_ahead: float,
    ) -> None:
        driver = str(drv)
        tick = int(tick)
        previous_tick = self._last_tick.get(driver)
        if previous_tick is not None and tick <= previous_tick:
            raise CorpusDumpError(
                f"duplicate/out-of-order tick for {driver}: {tick} <= {previous_tick}"
            )
        row = {
            "run": self.run,
            "drv": driver,
            "tick": tick,
            "t_s": float(t_s),
            "geometry_id": self.geometry_id,
            "geometry_sha256": self.geometry_sha256,
            "instrument_version": self.instrument_version,
            "track_id": int(track_id),
            "compound_id": int(compound_id),
            "telemetry_edge_34": _finite_vector(
                "telemetry_edge_34", telemetry_edge_34, EDGE_DIM
            ),
            "ctx": _finite_vector("ctx", ctx, 2),
            "traffic_features_12": _finite_vector(
                "traffic_features_12", traffic_features_12, TRAFFIC_DIM
            ),
            "speed_mps": float(speed_mps),
            "curvature_ahead": float(curvature_ahead),
            "previous_steer": self._previous_actions.get(driver, (0.0, 0.0))[0],
            "previous_longitudinal": self._previous_actions.get(driver, (0.0, 0.0))[1],
        }
        if not all(
            value == value and abs(value) != float("inf")
            for value in (
                row["t_s"], row["speed_mps"], row["curvature_ahead"],
            )
        ):
            raise CorpusDumpError(f"non-finite scalar in row {driver}/{tick}")
        self._write(row)
        self._last_tick[driver] = tick
        self.rows += 1

    def observe_action(self, drv: str, action: Sequence[float]) -> None:
        if len(action) != 2:
            raise CorpusDumpError("recorded action must have two values")
        self._previous_actions[str(drv)] = (
            float(action[0]), float(action[1])
        )

    def close(self) -> str:
        if self._stream is None:
            raise CorpusDumpError("dump already closed")
        self._stream.close()
        self._stream = None
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def __enter__(self) -> "CompositeCorpusDump":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._stream is not None:
            self.close()
