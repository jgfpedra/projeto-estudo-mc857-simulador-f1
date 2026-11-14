#!/usr/bin/env python3
"""PROJ-GATE-2 frozen, report-only Monaco pointer autopsy (v1.0)."""

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
import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
OUTDIR = BACKEND / "experiments/proj-gate-1/autopsia"
TRACK_LEN_M = 3335.2
TRACK_SEGMENTS = 834
LOCALITY_LIMIT_M = 32.0
WINDOW_S = 10.0

CSV_HEADER = tuple((
    "tick,t_s,drv,speed,s,lat,th,brk,steer_rad,g_long,stuck_t,contacts,car_car,"
    "impulse,impulse_dv,offtrack,authority,g_gate,r_norm,composite_active,"
    "res_0,res_1,res_2,res_3,res_4,res_5,res_6,res_7,res_8,res_9,res_10,"
    "res_11,res_12,res_13,res_14,res_15,w_kind,w_grip,w_trans,tyre_life,"
    "tyre_grip,cum_dist,obs0,obs1,obs2,obs3,obs4,obs5,obs6,obs7,obs8,obs9,"
    "obs10,obs11,obs12,obs13,obs14,obs15,obs16,obs17,obs18,obs19,obs20,"
    "obs21,obs22,imp_events,imp_dv,imp_dv_max,body_x,body_y,ns_raw"
).split(","))
EVENT_HEADER = tuple(
    "sub,drv_a,drv_b,body_a,body_b,cx,cy,nx,ny,f_n,j_n,dv_a,dv_b,ax,ay,bx,by"
    .split(",")
)

INPUTS = {
    "R1_csv": ("backend/experiments/proj-gate-1/1_repro_off_monaco_s0.csv",
               "5c4bf9c", "6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7"),
    "R1_events": ("backend/experiments/proj-gate-1/1_repro_off_monaco_s0_events.csv",
                  "5c4bf9c", "b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4"),
    "R2_csv": ("backend/experiments/proj-gate-1/2_on_monaco_s0.csv",
               "5c4bf9c", "b9ea18f28a26f2035fe61c9370eec7a70eb2bcaa342897d08a71baaf686a4edc"),
    "R2_events": ("backend/experiments/proj-gate-1/2_on_monaco_s0_events.csv",
                  "5c4bf9c", "88fa98130b73b881750dab5f54a1fae02d07ce2a2162e1586332afec0660ac6a"),
}
SOURCES = {
    "Monaco_frozen": ("backend/model_train/tracks_frozen/Monaco_v2.json", "f2bd199",
                      "af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2"),
    "runner_frozen": ("backend/scripts/run_race_10_cars.py", "f2bd199",
                       "6f13b59cfb7e709081483be85e2ad14d7295f65981dc8705ca8bcc9a9b8b03b3"),
    "diagnostic_writer_frozen": ("backend/model_train/race_diagnostic.py", "f2bd199",
                                  "69f87d163a56fe310212158ff527f58bd891828ffd0e8c5f91c3f5d7d41a0491"),
    "classifier_v1_2": ("backend/scripts/experiments/project/proj_fix_3_classify.py", "f2bd199",
                        "bc0a7ba9a5a9e4194d6195f3bc830a7626133939b465829f8ee1225e30414bdd"),
    "g1_audit_source": ("backend/scripts/experiments/project/proj_gate_1_audit.py", "f2bd199",
                        "000537b11b16914d96907f15e80a50de6ab208bd5538fa8a0fe93fabe3cae4e7"),
    "PARE_PROJ_GATE_1": ("backend/experiments/proj-gate-1/PARE_PROJ_GATE_1.md", "a278cbe",
                          "6b89f7b03b2313b76c73117e795d0b9089da309fb4cccc6527edb3396673acb9"),
    "DOSSIER_PROJ_FIX_1": ("backend/experiments/proj-fix-1/DOSSIÊ_PROJ_GATE.md", "f2bd199",
                            "663d4ad9ff561080d4c2e1fe8d981dd00da01a10a919bb21e1b418a44c80185f"),
}
CSV_INPUT_NAMES = ("R1_csv", "R2_csv")
EVENT_INPUT_NAMES = ("R1_events", "R2_events")
NUMERIC_FIELDS = ("tick", "t_s", "speed", "s", "lat", "cum_dist", "body_x", "body_y")
EXPECTED_G2 = {"R1": (112, 45), "R2": (173, 108)}
EXPECTED_HESITATIONS_R2 = 28
CLASSES = ("C1", "C2", "C3", "C5")


class PareError(RuntimeError):
    """Frozen source/schema/input validation failed; analysis must stop."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob(revision: str, repo_path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{revision}:{repo_path}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode:
        raise PareError(f"PARE: git show falhou para {revision}:{repo_path}: "
                        f"{proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def verify_pins() -> dict:
    checks = {}
    for name, (repo_path, revision, expected) in {**INPUTS, **SOURCES}.items():
        disk_path = ROOT / repo_path
        if not disk_path.is_file():
            raise PareError(f"PARE: caminho D ausente: {repo_path}")
        disk_sha = sha256_file(disk_path)
        git_sha = sha256_bytes(git_blob(revision, repo_path))
        if disk_sha != expected or git_sha != expected or disk_sha != git_sha:
            raise PareError(
                f"PARE: hash/proveniência diverge em {repo_path}: "
                f"esperado={expected}, disco={disk_sha}, git_show={git_sha}"
            )
        checks[name] = {
            "path": repo_path, "revision": revision,
            "sha256_disk": disk_sha, "sha256_git_show": git_sha,
            "status": "PASS",
        }
    return checks


def first_noncomment_header(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8", newline="") as source:
        for line in source:
            if line.startswith("#"):
                continue
            return tuple(next(csv.reader([line])))
    raise PareError(f"PARE: arquivo CSV sem header: {path}")


def schema_preflight() -> dict:
    result = {}
    for name in CSV_INPUT_NAMES:
        path = ROOT / INPUTS[name][0]
        got = first_noncomment_header(path)
        if got != CSV_HEADER:
            raise PareError(f"PARE: schema de {name} diverge; got={got!r}")
        result[name] = {"columns": len(got), "header_sha256": sha256_bytes(",".join(got).encode()),
                        "status": "PASS"}
    for name in EVENT_INPUT_NAMES:
        path = ROOT / INPUTS[name][0]
        got = first_noncomment_header(path)
        if got != EVENT_HEADER:
            raise PareError(f"PARE: schema de {name} diverge; got={got!r}")
        result[name] = {"columns": len(got), "header_sha256": sha256_bytes(",".join(got).encode()),
                        "status": "PASS"}
    return result


def print_expected_schemas() -> None:
    # This is emitted before even hashing/opening CSV inputs.
    print("EXPECTED_RACE_CSV_HEADER=" + ",".join(CSV_HEADER))
    print("EXPECTED_EVENT_CSV_HEADER=" + ",".join(EVENT_HEADER))


def read_dict_rows(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        rows = csv.DictReader(line for line in source if not line.startswith("#"))
        if rows.fieldnames is None:
            raise PareError(f"PARE: sem header: {path}")
        fieldnames = tuple(rows.fieldnames)
        result = []
        for line_no, row in enumerate(rows, start=2):
            if None in row or any(value is None for value in row.values()):
                raise PareError(f"PARE: largura de linha inválida em {path}:{line_no}")
            if tuple(row) != fieldnames:
                raise PareError(f"PARE: ordem/colunas inválidas em {path}:{line_no}")
            result.append(dict(row))
    return fieldnames, result


def finite_float(value: str, *, path: Path, row_no: int, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PareError(f"PARE: número inválido {field} em {path}:{row_no}: {value!r}") from exc
    if not math.isfinite(number):
        raise PareError(f"PARE: valor não finito {field} em {path}:{row_no}: {value!r}")
    return number


def strict_int(value: str, *, path: Path, row_no: int, field: str) -> int:
    try:
        if not value or value.strip() != value or any(ch not in "+-0123456789" for ch in value):
            raise ValueError(value)
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise PareError(f"PARE: inteiro inválido {field} em {path}:{row_no}: {value!r}") from exc
    return number


def validate_event_file(name: str) -> int:
    path = ROOT / INPUTS[name][0]
    fields, rows = read_dict_rows(path)
    if fields != EVENT_HEADER:
        raise PareError(f"PARE: schema de eventos mudou após preflight: {name}")
    numeric = ("sub", "cx", "cy", "nx", "ny", "f_n", "j_n", "dv_a", "dv_b", "ax", "ay", "bx", "by")
    for ordinal, row in enumerate(rows, 2):
        strict_int(row["sub"], path=path, row_no=ordinal, field="sub")
        if not row["drv_a"] or not row["drv_b"] or not row["body_a"] or not row["body_b"]:
            raise PareError(f"PARE: evento sem identificador em {path}:{ordinal}")
        for field in numeric[1:]:
            finite_float(row[field], path=path, row_no=ordinal, field=field)
    return len(rows)


def load_run(name: str) -> tuple[list[dict], dict]:
    path = ROOT / INPUTS[f"{name}_csv"][0]
    fields, raw_rows = read_dict_rows(path)
    if fields != CSV_HEADER:
        raise PareError(f"PARE: schema de {name} diverge após preflight")
    parsed = []
    seen = set()
    by_driver = defaultdict(list)
    for ordinal, row in enumerate(raw_rows, 2):
        tick = strict_int(row["tick"], path=path, row_no=ordinal, field="tick")
        offtrack = strict_int(row["offtrack"], path=path, row_no=ordinal, field="offtrack")
        ns_raw = strict_int(row["ns_raw"], path=path, row_no=ordinal, field="ns_raw")
        if offtrack not in (0, 1):
            raise PareError(f"PARE: offtrack fora de 0/1 em {path}:{ordinal}")
        if not 0 <= ns_raw < TRACK_SEGMENTS:
            raise PareError(f"PARE: ns_raw fora de [0,833] em {path}:{ordinal}")
        if not row["drv"]:
            raise PareError(f"PARE: drv vazio em {path}:{ordinal}")
        sample = {
            "tick": tick, "drv": row["drv"], "offtrack": offtrack, "ns_raw": ns_raw,
            "t_s": finite_float(row["t_s"], path=path, row_no=ordinal, field="t_s"),
            "speed": finite_float(row["speed"], path=path, row_no=ordinal, field="speed"),
            "s": finite_float(row["s"], path=path, row_no=ordinal, field="s"),
            "lat": finite_float(row["lat"], path=path, row_no=ordinal, field="lat"),
            "cum_dist": finite_float(row["cum_dist"], path=path, row_no=ordinal, field="cum_dist"),
            "body_x": finite_float(row["body_x"], path=path, row_no=ordinal, field="body_x"),
            "body_y": finite_float(row["body_y"], path=path, row_no=ordinal, field="body_y"),
        }
        if abs(sample["t_s"] - tick / 10.0) > 1e-9:
            raise PareError(f"PARE: t_s/tick inconsistente em {path}:{ordinal}")
        key = (sample["drv"], tick)
        if key in seen:
            raise PareError(f"PARE: linha drv/tick duplicada em {path}:{ordinal}: {key}")
        seen.add(key)
        parsed.append(sample)
        by_driver[sample["drv"]].append(sample)
    if len(parsed) != 30_000 or len(by_driver) != 10:
        raise PareError(f"PARE: completude inesperada em {name}: rows={len(parsed)}, cars={len(by_driver)}")
    expected_ticks = list(range(0, 6000, 2))
    for driver, group in by_driver.items():
        group.sort(key=lambda item: item["tick"])
        got = [row["tick"] for row in group]
        if len(got) != 3000 or got != expected_ticks:
            raise PareError(f"PARE: sequência incompleta em {name}/{driver}")
    parsed.sort(key=lambda item: (item["drv"], item["tick"]))
    return parsed, {"data_rows": len(parsed), "drivers": sorted(by_driver),
                    "offtrack_samples": sum(row["offtrack"] for row in parsed)}


def load_classifier():
    sys.path.insert(0, str(BACKEND / "scripts"))
    from scripts.experiments.project import proj_fix_3_classify as frozen_classifier
    return frozen_classifier


def wrap_delta(delta: float, track_len: float = TRACK_LEN_M) -> float:
    return (delta + track_len / 2.0) % track_len - track_len / 2.0


def waypoint_gap_m(ns: int, wp: int) -> tuple[int, float]:
    gap = min((ns - wp) % TRACK_SEGMENTS, (wp - ns) % TRACK_SEGMENTS)
    return gap, gap * TRACK_LEN_M / TRACK_SEGMENTS


def nearest_waypoint(x: float, y: float, waypoints: list[tuple[float, float]]) -> int:
    # min() preserves the smallest index on exact distance ties.
    return min(range(len(waypoints)), key=lambda i: math.hypot(x - waypoints[i][0], y - waypoints[i][1]))


def linear_p95(values: list[float], classifier) -> float | None:
    return classifier._linear_percentile(values, 95.0)


def load_track() -> tuple[list[tuple[float, float]], dict]:
    path = ROOT / SOURCES["Monaco_frozen"][0]
    track = json.loads(path.read_text(encoding="utf-8"))
    raw = track.get("waypoints")
    if not isinstance(raw, list) or len(raw) != TRACK_SEGMENTS or int(track.get("n_wp", -1)) != TRACK_SEGMENTS:
        raise PareError("PARE: Monaco frozen não tem 834 waypoints declarados")
    waypoints = []
    for index, point in enumerate(raw):
        if not isinstance(point, list) or len(point) != 2:
            raise PareError(f"PARE: waypoint inválido em Monaco: {index}")
        x, y = float(point[0]), float(point[1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise PareError(f"PARE: waypoint não finito em Monaco: {index}")
        waypoints.append((x, y))
    official_len = float(track.get("official_length_m", math.nan))
    polyline_len = sum(math.dist(waypoints[i], waypoints[(i + 1) % len(waypoints)])
                       for i in range(len(waypoints)))
    if not math.isfinite(official_len) or not math.isfinite(polyline_len):
        raise PareError("PARE: Monaco frozen tem comprimento de pista inválido")
    if round(polyline_len, 1) != TRACK_LEN_M:
        raise PareError(f"PARE: comprimento polyline frozen arredondado diverge: {polyline_len}")
    return waypoints, {"name": track.get("name"), "n_wp": len(waypoints),
                       "official_length_metadata_m": official_len,
                       "polyline_length_m": polyline_len,
                       "track_len_used_m": TRACK_LEN_M,
                       "nominal_m_per_waypoint": TRACK_LEN_M / TRACK_SEGMENTS}


def summarize_distances(rows: list[dict], classifier) -> dict:
    values = [row["d_wp_m"] for row in rows]
    counts = Counter(row["gap_wp"] for row in rows)
    return {
        "samples": len(rows),
        "wrong_branch_samples": sum(row["wrong_branch"] for row in rows),
        "wrong_branch_fraction": (sum(row["wrong_branch"] for row in rows) / len(rows)) if rows else None,
        "p95_d_wp_m": linear_p95(values, classifier),
        "max_d_wp_m": max(values) if values else None,
        "histogram_gap_waypoints": {str(k): counts[k] for k in sorted(counts)},
    }


def compute_pointer_rows(samples: list[dict], waypoints: list[tuple[float, float]]) -> list[dict]:
    result = []
    for sample in samples:
        wp = nearest_waypoint(sample["body_x"], sample["body_y"], waypoints)
        gap, distance = waypoint_gap_m(sample["ns_raw"], wp)
        result.append({**sample, "nearest_waypoint": wp, "gap_wp": gap, "d_wp_m": distance,
                       "wrong_branch": distance > LOCALITY_LIMIT_M})
    return result


def reentry_windows(rows: list[dict], classifier) -> dict:
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["drv"]].append(row)
    windows = []
    for driver, group in by_driver.items():
        group.sort(key=lambda item: item["tick"])
        for prev, cur in zip(group, group[1:]):
            if prev["offtrack"] != 1 or cur["offtrack"] != 0:
                continue
            t0 = cur["t_s"]
            window_rows = [r for r in group if t0 <= r["t_s"] < t0 + WINDOW_S]
            wrong = [r["wrong_branch"] for r in window_rows]
            longest_wrong_run = run = 0
            for is_wrong in wrong:
                run = run + 1 if is_wrong else 0
                longest_wrong_run = max(longest_wrong_run, run)
            windows.append({
                "drv": driver, "reentry_tick": cur["tick"], "reentry_t_s": t0,
                "spatial_snap_distance_m": abs(cur["lat"]),
                "window_end_t_s_exclusive": t0 + WINDOW_S,
                "sample_rows": len(window_rows),
                "wrong_branch_samples": sum(wrong),
                "wrong_branch_fraction": (sum(wrong) / len(wrong)) if wrong else None,
                "p95_d_wp_m": linear_p95([r["d_wp_m"] for r in window_rows], classifier),
                "any_wrong_branch": any(wrong),
                "at_least_two_consecutive_wrong": longest_wrong_run >= 2,
                "longest_wrong_run_samples": longest_wrong_run,
            })
    pooled = [row for item in windows for row in by_driver[item["drv"]]
              if item["reentry_t_s"] <= row["t_s"] < item["window_end_t_s_exclusive"]]
    wrong = [row["wrong_branch"] for row in pooled]
    return {
        "definition": "observed offtrack 1->0 transition; [reentry_t_s,reentry_t_s+10s), 5Hz emitted rows; overlaps count once per window",
        "reentries": len(windows), "pooled_window_rows_with_overlap": len(pooled),
        "wrong_branch_samples_with_overlap": sum(wrong),
        "wrong_branch_fraction_with_overlap": (sum(wrong) / len(wrong)) if wrong else None,
        "p95_d_wp_m_with_overlap": linear_p95([row["d_wp_m"] for row in pooled], classifier),
        "windows_any_wrong": sum(item["any_wrong_branch"] for item in windows),
        "windows_any_wrong_fraction": (sum(item["any_wrong_branch"] for item in windows) / len(windows)) if windows else None,
        "windows_two_consecutive_wrong": sum(item["at_least_two_consecutive_wrong"] for item in windows),
        "windows_two_consecutive_wrong_fraction": (sum(item["at_least_two_consecutive_wrong"] for item in windows) / len(windows)) if windows else None,
        "individual_windows": windows,
    }


def by_driver_and_decile(rows: list[dict], classifier) -> tuple[list[dict], list[dict]]:
    groupings = (("drv", lambda r: r["drv"]),
                 ("pointer_s_decile", lambda r: min(9, int((r["s"] % TRACK_LEN_M) / TRACK_LEN_M * 10))))
    outputs = []
    for key_name, key_fn in groupings:
        groups = defaultdict(list)
        for row in rows:
            groups[key_fn(row)].append(row)
        records = []
        for key in sorted(groups):
            group = groups[key]
            distances = [row["d_wp_m"] for row in group]
            records.append({
                key_name: key, "offtrack_samples": len(group),
                "wrong_branch_samples": sum(row["wrong_branch"] for row in group),
                "wrong_branch_fraction": sum(row["wrong_branch"] for row in group) / len(group),
                "p95_d_wp_m": linear_p95(distances, classifier),
                "max_d_wp_m": max(distances),
            })
        outputs.append(records)
    return outputs[0], outputs[1]


def top_offtrack_episodes(rows: list[dict], classifier) -> list[dict]:
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["drv"]].append(row)
    episodes = []
    for driver, group in by_driver.items():
        group.sort(key=lambda item: item["tick"])
        active = []
        for row in group + [None]:
            if row is not None and row["offtrack"] == 1:
                active.append(row)
                continue
            if active:
                distances = [r["d_wp_m"] for r in active]
                episodes.append({
                    "drv": driver, "start_tick": active[0]["tick"], "end_tick": active[-1]["tick"],
                    "samples": len(active), "wrong_branch_samples": sum(r["wrong_branch"] for r in active),
                    "wrong_branch_fraction": sum(r["wrong_branch"] for r in active) / len(active),
                    "p95_d_wp_m": linear_p95(distances, classifier), "max_d_wp_m": max(distances),
                })
                active = []
    episodes.sort(key=lambda item: (-item["max_d_wp_m"], item["drv"], item["start_tick"]))
    return episodes[:10]


def hesitation_episodes(rows: list[dict]) -> list[dict]:
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["drv"]].append(row)
    result = []
    for driver, all_rows in by_driver.items():
        group = sorted((row for row in all_rows if row["t_s"] > 20.0), key=lambda item: item["t_s"])
        speeds = [row["speed"] for row in group]
        n = len(group)
        i = 0
        while i < n:
            if speeds[i] >= 0.5:
                i += 1
                continue
            j = i
            while j < n and speeds[j] < 0.5:
                j += 1
            duration = group[min(j, n - 1)]["t_s"] - group[i]["t_s"] if j > i else 0.0
            if 0.3 <= duration < 3.0:
                slow_rows = group[i:j]
                result.append({
                    "drv": driver, "start_tick": slow_rows[0]["tick"],
                    "end_tick": slow_rows[-1]["tick"], "start_t_s": slow_rows[0]["t_s"],
                    "end_t_s": slow_rows[-1]["t_s"], "duration_s_runner_rule": duration,
                    "start_d_wp_m": slow_rows[0]["d_wp_m"],
                    "max_d_wp_m_during_hesitation": max(r["d_wp_m"] for r in slow_rows),
                    "wrong_branch_at_start": slow_rows[0]["wrong_branch"],
                    "wrong_branch_samples_during_hesitation": sum(r["wrong_branch"] for r in slow_rows),
                    "offtrack_samples_during_hesitation": sum(r["offtrack"] for r in slow_rows),
                })
            i = j
    return sorted(result, key=lambda item: (item["drv"], item["start_tick"]))


def attach_reentry_timing(hesitations: list[dict], reentries: list[dict]) -> None:
    by_driver = defaultdict(list)
    for reentry in reentries:
        by_driver[reentry["drv"]].append(reentry)
    for hesitation in hesitations:
        same_driver = by_driver[hesitation["drv"]]
        timing = []
        for reentry in same_driver:
            delta = hesitation["start_t_s"] - reentry["reentry_t_s"]
            timing.append({
                "reentry_tick": reentry["reentry_tick"], "reentry_t_s": reentry["reentry_t_s"],
                "hesitation_minus_reentry_s": delta,
                "hesitation_within_post_reentry_10s": 0.0 <= delta < WINDOW_S,
            })
        hesitation["same_driver_reentry_timing"] = timing
        hesitation["nearest_reentry_abs_delta_s"] = (
            min((abs(item["hesitation_minus_reentry_s"]) for item in timing), default=None))


def g2_pairs(name: str, rows: list[dict]) -> tuple[list[dict], int]:
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["drv"]].append(row)
    pairs = []
    for driver, group in by_driver.items():
        group.sort(key=lambda item: item["tick"])
        for prev, cur in zip(group, group[1:]):
            if cur["offtrack"] != 1:
                continue
            delta_s = wrap_delta(cur["s"] - prev["s"])
            delta_dist = cur["cum_dist"] - prev["cum_dist"]
            error = abs(delta_s - delta_dist)
            pairs.append({
                "drv": driver, "tick_prev": prev["tick"], "tick": cur["tick"],
                "abs_projection_error_m": error,
            })
    return pairs, sum(row["offtrack"] for row in rows)


def classify_g2_pairs(rows: list[dict], g2: list[dict], classifier) -> list[dict]:
    samples = []
    for ordinal, row in enumerate(rows, 1):
        samples.append(classifier._parse_sample({
            "drv": row["drv"], "tick": str(row["tick"]),
            "body_x": str(row["body_x"]), "body_y": str(row["body_y"]),
            "ns_raw": str(row["ns_raw"]),
        }, ordinal))
    classified, invalid, pair_metrics = classifier._classify_samples(samples)
    if invalid:
        raise PareError(f"PARE: classifier v1.2 encontrou C4/invalid rows={len(invalid)}")
    classified_by_key = {(r["drv"], r["tick_prev"], r["tick"]): r for r in classified}
    mapped = []
    for event in g2:
        key = (event["drv"], event["tick_prev"], event["tick"])
        metric = pair_metrics.get(key)
        if metric is None:
            raise PareError(f"PARE: g2 par sem métricas v1.2: {key}")
        assigned = classified_by_key.get(key)
        label = assigned["class"] if assigned else "C5"
        mapped.append({**event, "class_xy_ns": label,
                       "dxy_m": metric["dxy_m"], "abs_d_ns_raw": metric["d_ns_raw"]})
    if len({(r["drv"], r["tick_prev"], r["tick"]) for r in mapped}) != len(mapped):
        raise PareError("PARE: mapeamento v1.2 g2 não é único")
    return mapped


def summarize_g2_subset(rows: list[dict], denominator: int, classifier) -> dict:
    result = {"event_pairs": len(rows), "per_offtrack_sample": len(rows) / denominator if denominator else None,
              "per_1000_offtrack_samples": 1000.0 * len(rows) / denominator if denominator else None,
              "classes": {}}
    for label in CLASSES:
        subset = [row for row in rows if row["class_xy_ns"] == label]
        result["classes"][label] = {
            "count": len(subset),
            "p95_dxy_m": linear_p95([row["dxy_m"] for row in subset], classifier),
            "p95_abs_d_ns_raw": linear_p95([row["abs_d_ns_raw"] for row in subset], classifier),
            "per_offtrack_sample": len(subset) / denominator if denominator else None,
            "per_1000_offtrack_samples": 1000.0 * len(subset) / denominator if denominator else None,
        }
    if sum(result["classes"][label]["count"] for label in CLASSES) != len(rows):
        raise PareError("PARE: classes C1/C2/C3/C5 não fecham os pares")
    return result


def compute_g2(runs: dict[str, list[dict]], classifier) -> dict:
    output = {"definition": "adjacent emitted samples per driver; current sample offtrack; |wrap(Δs,L)-Δcum_dist|",
              "track_length_m": TRACK_LEN_M, "runs": {}}
    for name, rows in runs.items():
        pairs, denominator = g2_pairs(name, rows)
        ge10 = [row for row in pairs if row["abs_projection_error_m"] >= 10.0]
        ge30 = [row for row in pairs if row["abs_projection_error_m"] >= 30.0]
        expected = EXPECTED_G2[name]
        if (len(ge10), len(ge30)) != expected:
            raise PareError(f"PARE: contagem g2 {name} diverge; got={(len(ge10), len(ge30))}, expected={expected}")
        mapped = classify_g2_pairs(rows, pairs, classifier)
        mapped_ge10 = [row for row in mapped if row["abs_projection_error_m"] >= 10.0]
        mapped_ge30 = [row for row in mapped if row["abs_projection_error_m"] >= 30.0]
        if len(mapped_ge10) != len(ge10) or len(mapped_ge30) != len(ge30):
            raise PareError(f"PARE: mapa v1.2 não reconcilia os cortes g2 em {name}")
        output["runs"][name] = {
            "offtrack_samples": denominator,
            "offtrack_pairs": len(pairs),
            "counts": {"ge10_m": len(ge10), "ge30_m": len(ge30)},
            "decomposition_ge10": summarize_g2_subset(mapped_ge10, denominator, classifier),
            "decomposition_ge30": summarize_g2_subset(mapped_ge30, denominator, classifier),
        }
    return output


def compute_branch_report(name: str, rows: list[dict], waypoints, classifier) -> tuple[dict, list[dict]]:
    pointer_rows = compute_pointer_rows(rows, waypoints)
    by_state = {}
    for label, selector in (("all", lambda r: True), ("ontrack", lambda r: r["offtrack"] == 0),
                            ("offtrack", lambda r: r["offtrack"] == 1)):
        by_state[label] = summarize_distances([r for r in pointer_rows if selector(r)], classifier)
    off_rows = [row for row in pointer_rows if row["offtrack"] == 1]
    by_car, by_decile = by_driver_and_decile(off_rows, classifier)
    observed_reentries = []
    by_driver = defaultdict(list)
    for row in pointer_rows:
        by_driver[row["drv"]].append(row)
    for driver, group in by_driver.items():
        group.sort(key=lambda item: item["tick"])
        for prev, cur in zip(group, group[1:]):
            if prev["offtrack"] == 1 and cur["offtrack"] == 0:
                observed_reentries.append({
                    "drv": driver, "reentry_tick": cur["tick"], "reentry_t_s": cur["t_s"],
                    "spatial_snap_distance_m": abs(cur["lat"]),
                })
    windows = reentry_windows(pointer_rows, classifier)
    hesitation = hesitation_episodes(pointer_rows)
    attach_reentry_timing(hesitation, observed_reentries)
    if name == "R2" and len(hesitation) != EXPECTED_HESITATIONS_R2:
        raise PareError(f"PARE: hesitações R2 divergentes: got={len(hesitation)}, expected={EXPECTED_HESITATIONS_R2}")
    result = {
        "run": name, "samples": len(rows), "offtrack_samples": len(off_rows),
        "branch_locality_proxy_ns_raw_vs_nearest_waypoint": by_state,
        "offtrack_by_driver": by_car,
        "offtrack_by_pointer_s_decile": by_decile,
        "top_10_offtrack_episodes_by_max_gap": top_offtrack_episodes(pointer_rows, classifier),
        "post_reentry_10s_windows": windows,
        "reentry_spatial_snap_distance": {
            "definition": "abs(lat) at the observed offtrack 1->0 sample; lat is signed distance to the nearest global segment projection",
            "reentries": len(observed_reentries),
            "p95_m": linear_p95([r["spatial_snap_distance_m"] for r in observed_reentries], classifier),
            "max_m": max((r["spatial_snap_distance_m"] for r in observed_reentries), default=None),
            "individual_reentries": observed_reentries,
            "target_to_discovery_distance": "not estimable: target/anchor coordinates are absent from frozen writer",
        },
        "recreated_runner_hesitations": {"count": len(hesitation), "episodes": hesitation},
    }
    return result, observed_reentries


def source_interpretation(pin_checks: dict) -> dict:
    return {
        "h1_anchor_target_reconstruction": {
            "status": "LOSING / not identifiable",
            "reason": "runner stores anchor pose/s/ns/projection_xy each logical predict_batch and caches target_xy, but v3.4 output has no anchor or target columns and emits only every second logical tick; post-step sample pose cannot reproduce unsampled pre-step anchor/target exactly.",
            "evidence": [
                "backend/scripts/simulation/run_race_10_cars.py:327-351 (anchor fields and target cache)",
                "backend/scripts/simulation/run_race_10_cars.py:794-800 (anchor updated on every on-track predict_batch)",
                "backend/scripts/simulation/run_race_10_cars.py:477-495 (target = projection_xy + ahead_m * heading; cached)",
                "backend/model_train/race_diagnostic.py:875-904,918-923 (controller each logical tick; writer every two ticks; row projection after step)",
                "backend/model_train/race_diagnostic.py:1291-1299 (fallback projection returns nearest-segment arc and spatial snap distance)",
                "backend/model_train/race_diagnostic.py:1010-1015 (only body_x/body_y/ns_raw added; no anchor/target)",
            ],
            "target_to_reentry_distance": "not estimable; no nearest-sample substitution",
        },
        "h2_environment_live_pointer": {
            "status": "not directly observable",
            "reason": "no env-internal pointer column exists in the frozen v3.4 CSV; ns_raw is a runner-side global nearest_segment result from sampled body XY.",
            "permitted_proxy": "ns_raw vs Euclidean nearest waypoint branch gap, with frozen 32 m locality threshold",
        },
        "h3_g2_measurement": {
            "status": "supported as mis-specified for internal-pointer locality",
            "reason": "frozen g2 counts |wrap(Δs,L)-Δcum_dist| for adjacent emitted samples whose current row is off-track; s is diagnostic controller._project/_proj output, cum_dist is engine odometer, and ns_raw is a separate XY nearest-segment recomputation.",
            "evidence": [
                "backend/scripts/experiments/project/proj_gate_1_audit.py:57-76 (exact g2 proxy formula)",
                "backend/model_train/race_diagnostic.py:918-923 (s recomputed from sampled XY through controller projection)",
                "backend/model_train/race_diagnostic.py:1291-1299 (fallback returns `s` and nearest-segment spatial distance)",
                "backend/model_train/race_diagnostic.py:1010-1015 (ns_raw separately recomputed from sampled XY)",
            ],
            "limit": "g2 remains a valid historical proxy count; it does not establish which pointer is internally used by the environment or target branch correctness.",
        },
        "provenance_checks": pin_checks,
    }


def selftest(classifier) -> str:
    assert len(CSV_HEADER) == 71 and len(EVENT_HEADER) == 17
    assert wrap_delta(6.0, 10.0) == -4.0
    assert waypoint_gap_m(0, TRACK_SEGMENTS - 1) == (1, TRACK_LEN_M / TRACK_SEGMENTS)
    test_points = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
    assert nearest_waypoint(0.5, 0.0, test_points) == 0  # tie -> menor índice
    synthetic = [
        {"drv": "SYN", "tick": "0", "body_x": "0", "body_y": "0", "ns_raw": "0"},
        {"drv": "SYN", "tick": "1", "body_x": "30", "body_y": "40", "ns_raw": "8"},
        {"drv": "SYN", "tick": "2", "body_x": "60", "body_y": "40", "ns_raw": "15"},
        {"drv": "SYN", "tick": "3", "body_x": "60", "body_y": "40", "ns_raw": "15"},
    ]
    parsed = [classifier._parse_sample(row, i) for i, row in enumerate(synthetic, 1)]
    classified, invalid, pair_metrics = classifier._classify_samples(parsed)
    assert not invalid
    assert [row["class"] for row in classified] == ["C1", "C2"]
    assert ("SYN", 2, 3) in pair_metrics and ("SYN", 2, 3) not in {
        (r["drv"], r["tick_prev"], r["tick"]) for r in classified
    }  # residual pair is C5
    assert linear_p95([0.0, 10.0], classifier) == 9.5
    return "SELFTEST OK: frozen headers, wrapped arc, circular branch gap, lowest-index tie, synthetic C1/C2/C5, v1.2 p95; no race inputs opened"


def markdown_report(geometry: dict, g2: dict, interpretation: dict, hashes: dict) -> str:
    r1 = geometry["runs"]["R1"]
    r2 = geometry["runs"]["R2"]
    r1g = g2["runs"]["R1"]
    r2g = g2["runs"]["R2"]
    def pct(value):
        return "n/a" if value is None else f"{100 * value:.2f}%"
    lines = [
        "# PROJ-GATE-2 — autópsia do PARE PROJ-GATE-1",
        "",
        "**Modo:** report-only; Monaco; zero simulações/smokes; suíte não executada.",
        "**Flag:** permanece default-OFF; nenhuma promoção.",
        "",
        "## Resultado de proveniência e método",
        "",
        "Todos os artefatos autorizados passaram hash de disco = `git show` = pino preregistrado; headers CSV/eventos e amostras passaram validação fechada. Ver `3_execution.log` e `3_branch_geometry.json` para os hashes completos.",
        "A comparação de ramo é o proxy registrado `ns_raw` contra `wp*` (waypoint Euclidiano mais próximo; empate no menor índice), local se gap circular × `3335.2/834 <= 32 m`. Ela não observa um campo de ponteiro interno do env.",
        f"A soma da polyline frozen é {geometry['track']['polyline_length_m']:.6f} m (3335.2 m a uma casa decimal); a métrica usa o pino preregistrado 3335.2/834 m por waypoint. `official_length_m` é metadado separado.",
        "",
        "## Scorecard H1/H2/H3",
        "",
        "| Hipótese | Resultado | Evidência e limite |",
        "|---|---|---|",
        f"| H1 — alvo congelado escolhe ramo errado | **LOSING / não identificável** | O estado da âncora/alvo não é gravado; âncora atualiza a 10 Hz e CSV registra 5 Hz após o passo. Distância alvo→reentrada não estimável. |",
        f"| H2 — ponteiro vivo do env salta >32 m | **não diretamente observável** | Proxy `ns_raw` errado em R2 off-track: {r2['branch_locality_proxy_ns_raw_vs_nearest_waypoint']['offtrack']['wrong_branch_samples']}/{r2['offtrack_samples']} ({pct(r2['branch_locality_proxy_ns_raw_vs_nearest_waypoint']['offtrack']['wrong_branch_fraction'])}); isso não mede estado interno do env. |",
        "| H3 — g2 mede o ponteiro interno para esse diagnóstico | **apoia a mis-especificação** | g2 é `|wrap(Δs,L)−Δcum_dist|`: `s` é arco recalculado no runner, `cum_dist` é odômetro; `ns_raw` é outro cálculo global de XY. O corte histórico segue válido como proxy, mas não identifica ponteiro/ramo. |",
        "",
        "## Localidade de ramo do proxy",
        "",
        "| Braço | Estado | Amostras | Ramo errado | Fração | p95 gap (m) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for run_name, run in (("R1 OFF", r1), ("R2 ON", r2)):
        for state in ("all", "ontrack", "offtrack"):
            data = run["branch_locality_proxy_ns_raw_vs_nearest_waypoint"][state]
            lines.append(f"| {run_name} | {state} | {data['samples']} | {data['wrong_branch_samples']} | {pct(data['wrong_branch_fraction'])} | {data['p95_d_wp_m']:.3f} |")
    lines += [
        "",
        "## Janela de 10 s após reentrada observada",
        "",
        "| Braço | Reentradas | Linhas pooled (sobreposição conta) | Fração ramo errado | p95 gap (m) | Janelas com erro | 2+ erros seguidos |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for run_name, run in (("R1 OFF", r1), ("R2 ON", r2)):
        w = run["post_reentry_10s_windows"]
        lines.append(f"| {run_name} | {w['reentries']} | {w['pooled_window_rows_with_overlap']} | {pct(w['wrong_branch_fraction_with_overlap'])} | {w['p95_d_wp_m_with_overlap']:.3f} | {w['windows_any_wrong']}/{w['reentries']} | {w['windows_two_consecutive_wrong']}/{w['reentries']} |")
    snap = r2["reentry_spatial_snap_distance"]
    lines += [
        "",
        "Na R2, a distância do spatial snap disponível é `abs(lat)` na amostra de reentrada: "
        f"{snap['reentries']} reentradas, p95 {snap['p95_m']:.3f} m, máximo {snap['max_m']:.3f} m. "
        "A distância alvo congelado→descoberta não é estimável; não foi substituída por esse snap.",
    ]
    lines += [
        "",
        "## g2 e decomposição v1.2",
        "",
        "| Braço | Off-track samples | Pares off-track | ≥10 m | /1000 amostras | ≥30 m | /1000 amostras |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for run_name, run in (("R1 OFF", r1g), ("R2 ON", r2g)):
        lines.append(f"| {run_name} | {run['offtrack_samples']} | {run['offtrack_pairs']} | {run['counts']['ge10_m']} | {1000*run['counts']['ge10_m']/run['offtrack_samples']:.3f} | {run['counts']['ge30_m']} | {1000*run['counts']['ge30_m']/run['offtrack_samples']:.3f} |")
    lines += ["", "Decomposição por classe (contagem; p95 de dxy / |Δns_raw|):", ""]
    for run_name, run in (("R1 OFF", r1g), ("R2 ON", r2g)):
        lines.append(f"**{run_name}:**")
        for threshold in ("ge10", "ge30"):
            part = run[f"decomposition_{threshold}"]
            labels = "; ".join(
                f"{label} {part['classes'][label]['count']} (p95 {part['classes'][label]['p95_dxy_m'] if part['classes'][label]['p95_dxy_m'] is not None else 'n/a'} m / {part['classes'][label]['p95_abs_d_ns_raw'] if part['classes'][label]['p95_abs_d_ns_raw'] is not None else 'n/a'} wp)"
                for label in CLASSES
            )
            lines.append(f"- {threshold}: {part['event_pairs']} pares; {labels}.")
        lines.append("")
    lines += [
        "## Hesitações e decisão",
        "",
        f"R2 recriou {r2['recreated_runner_hesitations']['count']} hesitações pela regra frozen do runner (28 publicadas). A interseção temporal por reentrada, carro e amostra está em `3_branch_geometry.json`; distância alvo/âncora é não estimável.",
        "",
        "**Encaminhamento único: arquivar esta bifurcação causal.** H1 não pode ser identificada com o writer congelado; H2 não tem leitura direta do ponteiro interno; H3 confirma que g2 responde a uma pergunta de divergência arco/odômetro, não à localidade do ponteiro. Os dados de `ns_raw` são reportados como geometria do proxy e não bastam para escolher V-A2 ou V-B. Arquivar aqui encerra somente essa bifurcação, sem afirmar que não exista defeito.",
        "",
        "### Artefatos e hashes",
        "",
    ]
    for label, path in (("3_branch_geometry.json", OUTDIR / "3_branch_geometry.json"),
                        ("4_g2_class_decomposition.json", OUTDIR / "4_g2_class_decomposition.json")):
        lines.append(f"- `{label}` SHA-256 `{sha256_file(path)}`")
    lines.append(f"- script v{VERSION} SHA-256 `{sha256_file(Path(__file__).resolve())}`")
    lines.append("")
    return "\n".join(lines)


def run_audit(classifier) -> None:
    print_expected_schemas()
    outputs = [OUTDIR / "3_branch_geometry.json", OUTDIR / "4_g2_class_decomposition.json",
               OUTDIR / "5_veredito.md", OUTDIR / "3_execution.log"]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise PareError("PARE: outputs não são fresh; recusa overwrite: " + ", ".join(existing))
    script_path = Path(__file__).resolve()
    script_rel = script_path.relative_to(ROOT).as_posix()
    committed_script_sha = sha256_bytes(git_blob("HEAD", script_rel))
    disk_script_sha = sha256_file(script_path)
    if committed_script_sha != disk_script_sha:
        raise PareError(f"PARE: script de audit não está congelado no HEAD: disco={disk_script_sha}, git={committed_script_sha}")
    pins = verify_pins()
    pins["PROJ_GATE_2_autopsy_v1_0"] = {
        "path": script_rel, "revision": "HEAD", "sha256_disk": disk_script_sha,
        "sha256_git_show": committed_script_sha, "status": "PASS",
    }
    schemas = schema_preflight()
    event_rows = {name: validate_event_file(name) for name in EVENT_INPUT_NAMES}
    runs = {}
    run_meta = {}
    for name in ("R1", "R2"):
        runs[name], run_meta[name] = load_run(name)
    if run_meta["R1"]["drivers"] != run_meta["R2"]["drivers"]:
        raise PareError("PARE: drivers R1/R2 divergem")

    # Frozen headline checks run before the descriptive decomposition.
    g2 = compute_g2(runs, classifier)
    geometry_runs = {}
    observed_reentries = {}
    waypoints, track_meta = load_track()
    for name in ("R1", "R2"):
        geometry_runs[name], observed_reentries[name] = compute_branch_report(name, runs[name], waypoints, classifier)

    source_findings = source_interpretation(pins)
    geometry = {
        "version": VERSION, "analysis": "report-only; no simulation/smoke/suite",
        "provenance": pins, "schema_preflight": schemas, "event_sidecar_rows_validated": event_rows,
        "track": track_meta, "thresholds": {"locality_limit_m": LOCALITY_LIMIT_M,
                                               "window_s": WINDOW_S, "g2_expected": EXPECTED_G2},
        "run_validation": run_meta, "source_findings": source_findings,
        "runs": geometry_runs,
    }
    g2["version"] = VERSION
    g2["classifier"] = {
        "version": classifier.VERSION,
        "path": SOURCES["classifier_v1_2"][0],
        "sha256": pins["classifier_v1_2"]["sha256_git_show"],
        "implementation": "imported unmodified; _parse_sample, _classify_samples, _linear_percentile",
    }
    g2["provenance"] = pins
    g2["schema_preflight"] = schemas

    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "3_branch_geometry.json").write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTDIR / "4_g2_class_decomposition.json").write_text(json.dumps(g2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = markdown_report(geometry, g2, source_findings, pins)
    (OUTDIR / "5_veredito.md").write_text(report, encoding="utf-8")
    log = {
        "version": VERSION, "status": "PASS", "prereg_commit": "0a269ff9f35d5baac512729a34e824e1861e37f2",
        "execution_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                          stdout=subprocess.PIPE, check=True).stdout.decode().strip(),
        "schemas": schemas, "pins": pins, "event_rows": event_rows,
        "run_validation": run_meta,
        "outputs": {p.name: sha256_file(p) for p in outputs[:-1]},
        "script_sha256": disk_script_sha,
    }
    (OUTDIR / "3_execution.log").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selftest", action="store_true", help="synthetic-only checks; no race inputs")
    mode.add_argument("--run", action="store_true", help="run the frozen offline autopsy once")
    args = parser.parse_args(argv)
    try:
        classifier = load_classifier()
        if args.selftest:
            result = selftest(classifier)
            script_sha = sha256_file(Path(__file__).resolve())
            log_text = result + f"\nscript_sha256={script_sha}\n"
            print(log_text, end="")
            log_path = OUTDIR / "2_selftest.log"
            if log_path.exists():
                raise PareError(f"PARE: selftest log already exists: {log_path}")
            OUTDIR.mkdir(parents=True, exist_ok=True)
            log_path.write_text(log_text, encoding="utf-8")
            return 0
        run_audit(classifier)
        return 0
    except PareError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
