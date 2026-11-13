#!/usr/bin/env python3
"""TRAfego-MED-1B v1.0: auditoria report-only de fases em CSVs congelados.

--selftest usa somente dados sintéticos em memória. A execução real exige o
manifest congelado e faz o preflight integral de proveniência antes de abrir
qualquer linha de amostra para análise.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import csv
import hashlib
import json
import math
import subprocess
import sys
from statistics import median
from collections import Counter, defaultdict
from pathlib import Path

VERSION = "1.0"
BASE_COLUMNS = (
    "tick", "t_s", "drv", "speed", "s", "lat", "th", "brk",
    "steer_rad", "car_car",
)
EVENT_COLUMNS = (
    "sub", "drv_a", "drv_b", "body_a", "body_b", "cx", "cy", "nx",
    "ny", "f_n", "j_n", "dv_a", "dv_b", "ax", "ay", "bx", "by",
)
LAUNCH_S = 60.0
REJOIN_POST_S = 10.0
REGROUP_WINDOW_S = 60.0
REGROUP_LEADER_MPS = 10.0
LAT_CORRIDOR_M = 3.5
PAIR_LONGITUDINAL_M = 8.0
FOLLOW_SAME_LINE_M = 2.6
FOLLOW_AHEAD_M = 60.0
FOLLOW_CLOSE_M = 25.0
FOLLOW_MIN_AHEAD_MPS = 1.0
FOLLOW_REOPEN_GAP_M = 6.0
OVERTAKE_MIN_GAP_M = 15.0
OVERTAKE_MIN_DV_MPS = 1.0
OVERTAKE_MIN_WINDOW_S = 3.0
OVERTAKE_HYST_M = 10.0
HESITATION_MIN_MPS = 0.5
HESITATION_MIN_S = 0.3
HESITATION_MAX_S = 3.0
HESITATION_AFTER_S = 20.0
SEGMENT_M = 100.0
SAMPLE_CONTIGUITY_S = 0.301


class AuditError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_metadata(path: Path):
    """Only header and record count; invoked in preflight after freeze."""
    header = None
    rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for line in f:
            if line.lstrip().startswith("#") or not line.strip():
                continue
            if header is None:
                header = next(csv.reader([line]))
            else:
                rows += 1
    if header is None:
        raise AuditError(f"CSV vazio/sem cabeçalho: {path}")
    return header, rows


def csv_header(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for line in f:
            if line.lstrip().startswith("#") or not line.strip():
                continue
            return next(csv.reader([line]))
    raise AuditError(f"CSV vazio/sem cabeçalho: {path}")


def git_blob_sha(ref: str, relpath: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{relpath}"],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode:
        raise AuditError(f"git show falhou para Tier A: {ref}:{relpath}")
    return sha256_bytes(proc.stdout)


def preflight(manifest_path: Path, manifest: dict):
    """Fail closed before analysis: verify inventory, geometry and all 110 pins."""
    errors = []
    root = Path(__file__).resolve().parents[2]
    script_path = root / manifest["analysis_script_path"]
    if sha256_file(script_path) != manifest["analysis_script_sha256"]:
        errors.append(f"SHA do script congelado divergente: {script_path}")
    inventory_path = root / manifest["inventory_path"]
    if sha256_file(inventory_path) != manifest["inventory_sha256"]:
        errors.append(f"SHA do inventário divergente: {inventory_path}")
    for geom in manifest["geometries"]:
        path = root / geom["path"]
        if sha256_file(path) != geom["file_sha256"]:
            errors.append(f"SHA da geometria divergente: {path}")
        if geom.get("git_ref") and git_blob_sha(geom["git_ref"], geom["path"]) != geom["file_sha256"]:
            errors.append(f"blob Git da geometria divergente: {geom['path']}")
    entries = manifest["tier_A"] + manifest["tier_B"]
    if len(entries) != manifest["inventory_file_count"]:
        errors.append("contagem A+B não corresponde ao censo congelado")
    for entry in entries:
        path = root / entry["path"]
        if not path.is_file():
            errors.append(f"fonte ausente: {path}")
            continue
        digest = sha256_file(path)
        if digest != entry["disk_sha256"]:
            errors.append(f"SHA de disco divergente ({entry['tier']}): {path}")
            continue
        try:
            header = csv_header(path)
        except AuditError as exc:
            errors.append(str(exc))
            continue
        if len(header) != entry["column_count"] or header != entry["header_fields"]:
            errors.append(f"schema divergente: {path}")
        missing_required = [c for c in entry.get("required_columns", []) if c not in header]
        if missing_required:
            errors.append(f"colunas exigidas pelo manifest ausentes: {path}: {missing_required}")
        if entry["class"] == "race_timeseries" and not entry.get("analysis_arm"):
            errors.append(f"série sem rótulo de braço: {path}")
        if entry["tier"] == "B" and not entry.get("untracked_disclosure"):
            errors.append(f"Tier B sem disclosure untracked explícito: {path}")
        if entry["tier"] == "A":
            try:
                shown = git_blob_sha(entry["git_ref"], entry["path"])
            except AuditError as exc:
                errors.append(str(exc))
                continue
            if shown != entry["disk_sha256"] or shown != entry["git_sha256"]:
                errors.append(f"disco != git show no Tier A: {path}")
        else:
            stat_size = path.stat().st_size
            if stat_size != entry["size_bytes"]:
                errors.append(f"tamanho Tier B divergente: {path}")
            try:
                header, rows = csv_metadata(path)
            except AuditError as exc:
                errors.append(str(exc))
                continue
            if rows != entry["data_lines"]:
                errors.append(f"número de linhas Tier B divergente: {path}")
            if len(header) != entry["column_count"] or header != entry["header_fields"]:
                errors.append(f"schema Tier B divergente: {path}")
    if errors:
        raise AuditError("PARE antes de ler amostras:\n- " + "\n- ".join(errors))


def load_records(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        lines = (line for line in f if not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines)
        if not reader.fieldnames:
            raise AuditError(f"CSV sem schema: {path}")
        missing = [c for c in BASE_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise AuditError(f"schema de corrida incompleto em {path}: {missing}")
        return list(reader)


def sampling_precheck(path: Path):
    """Eligibility-only pass; excluded runs never enter metric loading."""
    by_driver = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        lines = (line for line in f if not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines)
        if not reader.fieldnames:
            return "sem schema"
        missing = [c for c in BASE_COLUMNS if c not in reader.fieldnames]
        if missing:
            return f"colunas obrigatórias ausentes: {missing}"
        for row in reader:
            drv = row.get("drv", "")
            t = number(row, "t_s")
            if not drv or t is None:
                return "drv/t_s ausente ou inválido na validação de elegibilidade"
            by_driver[drv].append(t)
    if len(by_driver) != 10:
        return f"número de carros={len(by_driver)} (esperado 10)"
    deltas = []
    for seq in by_driver.values():
        if any(b <= a for a, b in zip(seq, seq[1:])):
            return "t_s duplicado ou fora de ordem para um drv"
        deltas.extend(b - a for a, b in zip(seq, seq[1:]))
    if not deltas:
        return "sem intervalos temporais válidos"
    median_dt = median(deltas)
    if abs(median_dt - 0.2) > 0.051:
        return f"cadência mediana={median_dt:.3f}s (esperado 0,2s/5Hz)"
    if any(abs(d - 0.2) > 0.101 for d in deltas):
        return "intervalos não compatíveis com amostragem 5Hz"
    return None


def load_event_records(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        lines = (line for line in f if not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines)
        if not reader.fieldnames:
            return []
        missing = [c for c in EVENT_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise AuditError(f"schema de solver events incompleto em {path}: {missing}")
        return list(reader)


def number(row, field, default=None):
    value = row.get(field, "")
    if value is None or value == "":
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def geometry_length(path: Path) -> float:
    data = json.loads(path.read_text(encoding="utf-8"))
    pts = data.get("waypoints")
    if not isinstance(pts, list) or len(pts) < 3:
        raise AuditError(f"geometria sem waypoints válidos: {path}")
    total = 0.0
    for a, b in zip(pts, pts[1:] + pts[:1]):
        total += math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))
    return total


def positive_gap(a_s: float, b_s: float, length: float) -> float:
    return (b_s - a_s) % length


def pair_type(lat_a: float, lat_b: float) -> str:
    return "nose_a_tail" if abs(lat_a - lat_b) < LAT_CORRIDOR_M else "lateral"


def reconstruct_follow_modes(rows, length):
    """Exact geometry reconstruction of frozen ReferenceController thresholds."""
    by_tick = defaultdict(list)
    for row in rows:
        by_tick[int(float(row["tick"]))].append(row)
    modes = {}
    for tick, frame in by_tick.items():
        for ego in frame:
            if ego.get("t_mode") not in (None, ""):
                modes[(tick, ego["drv"])] = ego["t_mode"] in ("cap", "close")
                continue
            ego_s = number(ego, "s")
            ego_lat = number(ego, "lat")
            ego_v = number(ego, "speed")
            candidates = []
            if None not in (ego_s, ego_lat, ego_v):
                for other in frame:
                    if other["drv"] == ego["drv"]:
                        continue
                    os_ = number(other, "s")
                    olat = number(other, "lat")
                    ov = number(other, "speed")
                    if None in (os_, olat, ov) or abs(olat - ego_lat) >= FOLLOW_SAME_LINE_M:
                        continue
                    gap = positive_gap(ego_s, os_, length)
                    if 0.0 < gap < FOLLOW_AHEAD_M:
                        candidates.append((gap, ov))
            # min() is stable for equal gaps, matching the frozen controller's
            # first-in-traffic-order tie behavior (it updates only on gap < best).
            nearest = min(candidates, key=lambda candidate: candidate[0]) if candidates else None
            modes[(tick, ego["drv"])] = bool(
                nearest and nearest[0] >= FOLLOW_REOPEN_GAP_M and
                ego_v > nearest[1] > FOLLOW_MIN_AHEAD_MPS
            )
    return modes


def derive_progress(rows, length):
    """Use logged cumulative distance, else unwrap s using the pinned geometry."""
    ordered = sorted(rows, key=lambda r: (number(r, "t_s", 0.0), r["drv"]))
    by_driver = defaultdict(list)
    for r in ordered:
        by_driver[r["drv"]].append(r)
    result = {}
    for drv, seq in by_driver.items():
        prev_s = None
        lap = 0
        for r in sorted(seq, key=lambda x: number(x, "t_s", 0.0)):
            tick = int(float(r["tick"]))
            cum = number(r, "cum_dist")
            s = number(r, "s")
            if cum is not None:
                progress = cum
            else:
                if s is None:
                    continue
                if prev_s is not None and prev_s - s > length / 2:
                    lap += 1
                progress = lap * length + s
                prev_s = s
            result[(tick, drv)] = progress
    return result


def rejoin_masks(rows):
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["drv"]].append(row)
    mask = {}
    for drv, seq in by_driver.items():
        seq.sort(key=lambda r: number(r, "t_s", 0.0))
        active_until = -math.inf
        prev_off = False
        prev_auth_rejoin = False
        for row in seq:
            t = number(row, "t_s", 0.0)
            off = number(row, "offtrack", 0.0) == 1.0 if "offtrack" in row else False
            auth = str(row.get("authority", "")).lower() if "authority" in row else ""
            auth_rejoin = auth == "rejoin"
            entering = (off and not prev_off) or (auth_rejoin and not prev_auth_rejoin)
            if entering:
                active_until = math.inf
            # Re-entry: offtrack 1->0, or authority rejoin->other.
            exiting = (prev_off and not off) or (prev_auth_rejoin and not auth_rejoin)
            if exiting and math.isinf(active_until):
                active_until = t + REJOIN_POST_S
            is_rejoin = off or auth_rejoin or t <= active_until
            mask[(int(float(row["tick"])), drv)] = is_rejoin
            if active_until < t:
                active_until = -math.inf
            prev_off, prev_auth_rejoin = off, auth_rejoin
    return mask


def phase_labels(rows, length):
    """Return per-row frozen phase; precedence: launch > rejoin > regroup > cruise."""
    by_tick = defaultdict(list)
    by_driver = defaultdict(list)
    for row in rows:
        tick = int(float(row["tick"]))
        by_tick[tick].append(row)
        by_driver[row["drv"]].append(row)
    rejoin = rejoin_masks(rows)
    rejoin_observable = any("offtrack" in row or "authority" in row for row in rows)
    follow = reconstruct_follow_modes(rows, length) if length else {}
    progress = derive_progress(rows, length) if length else {}
    ticks = sorted(by_tick)
    leader_speed = {}
    follow_count = {}
    for tick in ticks:
        frame = by_tick[tick]
        active = [(progress.get((tick, r["drv"]), -math.inf), r) for r in frame]
        lead = max(active, key=lambda p: (p[0], p[1]["drv"]))[1]
        leader_speed[tick] = number(lead, "speed", 0.0)
        follow_count[tick] = sum(bool(follow.get((tick, r["drv"]), False)) for r in frame)
    times = {t: number(by_tick[t][0], "t_s", 0.0) for t in ticks}
    result = {}
    left = 0
    window_speed_sum = 0.0
    for i, tick in enumerate(ticks):
        t = times[tick]
        window_speed_sum += leader_speed[tick]
        while left <= i and times[ticks[left]] < t - REGROUP_WINDOW_S:
            window_speed_sum -= leader_speed[ticks[left]]
            left += 1
        window_count = i - left + 1
        mean_leader = window_speed_sum / window_count if window_count else math.inf
        regroup = bool(length and follow_count[tick] >= 2 and
                       window_count >= 2 and mean_leader < REGROUP_LEADER_MPS)
        for row in by_tick[tick]:
            drv = row["drv"]
            key = (tick, drv)
            if t < LAUNCH_S:
                result[key] = "LARGADA"
            elif not rejoin_observable:
                result[key] = "REJOIN_NA"
            elif rejoin.get(key, False):
                result[key] = "REJOIN"
            elif not length:
                result[key] = "CRUZEIRO_REGROUP_NA"
            elif regroup:
                result[key] = "REGROUP"
            else:
                result[key] = "CRUZEIRO"
    return result, rejoin, progress, rejoin_observable


def detect_hesitations(rows, phases):
    events = []
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["drv"]].append(row)
    for drv, seq in by_driver.items():
        seq.sort(key=lambda r: number(r, "t_s", 0.0))
        i = 0
        while i < len(seq):
            t = number(seq[i], "t_s", 0.0)
            v = number(seq[i], "speed", math.inf)
            if t <= HESITATION_AFTER_S or v >= HESITATION_MIN_MPS:
                i += 1
                continue
            j = i
            while j < len(seq) and number(seq[j], "speed", math.inf) < HESITATION_MIN_MPS:
                j += 1
            end_t = number(seq[j], "t_s") if j < len(seq) else number(seq[-1], "t_s", t)
            duration = end_t - t
            if HESITATION_MIN_S <= duration < HESITATION_MAX_S:
                tick = int(float(seq[i]["tick"]))
                events.append({
                    "drv": drv, "start_t_s": t, "duration_s": duration,
                    "phase": phases.get((tick, drv), "UNKNOWN"),
                })
            i = max(j, i + 1)
    return events


def contact_pairs(rows, phases, length):
    by_tick = defaultdict(list)
    for r in rows:
        by_tick[int(float(r["tick"]))].append(r)
    pair_records = []
    contact_rows = [r for r in rows if number(r, "car_car", 0.0) > 0]
    if not length:
        return contact_rows, pair_records
    for tick, frame in by_tick.items():
        positives = [r for r in frame if number(r, "car_car", 0.0) > 0]
        chosen = set()
        for i, a in enumerate(positives):
            sa, la = number(a, "s"), number(a, "lat")
            for b in positives[i + 1:]:
                sb, lb = number(b, "s"), number(b, "lat")
                if None in (sa, la, sb, lb):
                    continue
                ds = abs(sa - sb)
                if length:
                    ds = min(ds, abs(length - ds))
                if ds >= PAIR_LONGITUDINAL_M:
                    continue
                pair = tuple(sorted((a["drv"], b["drv"])))
                key = (tick, pair)
                if key in chosen:
                    continue
                chosen.add(key)
                pa = phases.get((tick, a["drv"]), "UNKNOWN")
                pb = phases.get((tick, b["drv"]), "UNKNOWN")
                pair_records.append({
                    "tick": tick, "drv_a": pair[0], "drv_b": pair[1],
                    "phase": phase_union(pa, pb),
                    "pair_type": pair_type(la, lb),
                    "lat_a": la, "lat_b": lb,
                    "pair_arm": group_pair(a, b),
                })
    return contact_rows, pair_records


def group_pair(a, b):
    ga = str(a.get("grupo", "all") or "all")
    gb = str(b.get("grupo", "all") or "all")
    return "×".join(sorted((ga, gb)))


def phase_union(a, b):
    order = {
        "LARGADA": 0, "REJOIN": 1, "REGROUP": 2,
        "CRUZEIRO": 3, "CRUZEIRO_REGROUP_NA": 4,
    }
    return min((a, b), key=lambda x: order.get(x, 9))


def opportunity_events(rows, phases, progress, length):
    if not length:
        return []
    by_tick = defaultdict(list)
    for row in rows:
        by_tick[int(float(row["tick"]))].append(row)
    ticks = sorted(by_tick)
    keys = set()
    qualifying = defaultdict(list)
    for tick in ticks:
        frame = by_tick[tick]
        for a in frame:
            sa, va, la = number(a, "s"), number(a, "speed"), number(a, "lat")
            if None in (sa, va, la):
                continue
            ahead = []
            for b in frame:
                if a["drv"] == b["drv"]:
                    continue
                sb, vb, lb = number(b, "s"), number(b, "speed"), number(b, "lat")
                if None in (sb, vb, lb):
                    continue
                gap = positive_gap(sa, sb, length)
                if gap > 0.0:
                    ahead.append((gap, b["drv"], b, vb, lb))
            if not ahead:
                continue
            gap, _, b, vb, lb = min(ahead, key=lambda x: (x[0], x[1]))
            if gap < OVERTAKE_MIN_GAP_M or abs(va - vb) < OVERTAKE_MIN_DV_MPS:
                continue
            key = (a["drv"], b["drv"])
            keys.add(key)
            qualifying[key].append({
                "tick": tick, "t": number(a, "t_s", 0.0),
                "gap": gap, "dv": va - vb, "lat_a": la, "lat_b": lb,
                "phase": phases.get((tick, a["drv"]), "UNKNOWN"),
                "pair_arm": group_pair(a, b),
            })
    events = []
    for key in keys:
        samples = sorted(qualifying[key], key=lambda x: x["t"])
        runs = []
        current = []
        for sample in samples:
            if current and sample["t"] - current[-1]["t"] > SAMPLE_CONTIGUITY_S:
                runs.append(current)
                current = []
            current.append(sample)
        if current:
            runs.append(current)
        drv_a, drv_b = key
        for run in runs:
            duration = run[-1]["t"] - run[0]["t"]
            if duration < OVERTAKE_MIN_WINDOW_S:
                continue
            start_tick = run[0]["tick"]
            pa = progress.get((start_tick, drv_a))
            pb = progress.get((start_tick, drv_b))
            swapped = False
            if pa is not None and pb is not None:
                start_diff = pa - pb
                sign = 1 if start_diff >= 0 else -1
                for item in run[1:]:
                    ca = progress.get((item["tick"], drv_a))
                    cb = progress.get((item["tick"], drv_b))
                    if ca is not None and cb is not None:
                        diff = ca - cb
                        if diff * sign <= 0 and abs(diff) >= OVERTAKE_HYST_M:
                            swapped = True
                            break
            if not swapped:
                events.append({
                    "drv_a": drv_a, "drv_b": drv_b,
                    "start_t_s": run[0]["t"], "duration_s": duration,
                    "gap_start_m": run[0]["gap"],
                    "dv_start_mps": run[0]["dv"],
                    "phase": run[0]["phase"],
                    "pair_type": pair_type(run[0]["lat_a"], run[0]["lat_b"]),
                    "pair_arm": run[0]["pair_arm"],
                })
    return events


def selftest():
    assert pair_type(0.0, 3.49) == "nose_a_tail"
    assert pair_type(0.0, 3.5) == "lateral"
    assert phase_union("CRUZEIRO", "REJOIN") == "REJOIN"
    assert phase_union("REGROUP", "LARGADA") == "LARGADA"
    rows = [
        {"tick": "0", "t_s": "0.0", "drv": "A", "speed": "10", "s": "0",
         "lat": "0", "th": "0", "brk": "0", "steer_rad": "0",
         "car_car": "0", "offtrack": "0", "authority": "policy"},
        {"tick": "2", "t_s": "0.2", "drv": "A", "speed": "10", "s": "1",
         "lat": "0", "th": "0", "brk": "0", "steer_rad": "0",
         "car_car": "0", "offtrack": "1", "authority": "rejoin"},
        {"tick": "4", "t_s": "0.4", "drv": "A", "speed": "10", "s": "2",
         "lat": "0", "th": "0", "brk": "0", "steer_rad": "0",
         "car_car": "0", "offtrack": "0", "authority": "policy"},
    ]
    mask = rejoin_masks(rows)
    assert mask[(2, "A")] is True and mask[(4, "A")] is True
    staggered_exit = [
        {"tick": "0", "t_s": "0", "drv": "B", "offtrack": "1", "authority": "rejoin"},
        {"tick": "2", "t_s": "1", "drv": "B", "offtrack": "0", "authority": "rejoin"},
        {"tick": "24", "t_s": "12", "drv": "B", "offtrack": "0", "authority": "policy"},
    ]
    staggered = rejoin_masks(staggered_exit)
    assert staggered[(24, "B")] is False
    hrows = []
    for i, v in enumerate([1.0, 0.2, 0.2, 1.0]):
        hrows.append({"tick": str(i * 2), "t_s": str(21 + i * 0.2),
                      "drv": "H", "speed": str(v)})
    hes = detect_hesitations(hrows, {(42, "H"): "CRUZEIRO"})
    assert len(hes) == 1 and hes[0]["duration_s"] >= 0.3
    print(f"trafego_med_1_taxonomy.py v{VERSION}: SELFTEST PASS (sintético; sem CSVs)")


def write_csv(path: Path, fields, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def run_analysis(manifest_path: Path, manifest: dict, out_dir: Path):
    output_names = (
        "1_phase_pair_arm.csv", "1b_phase_pair_aggregate.csv",
        "2_top_segments_car.csv", "3_reentry_launch_transfer.csv",
        "3b_transfer_by_arm.csv", "3c_run_coverage.csv",
    )
    occupied = [str(out_dir / name) for name in output_names if (out_dir / name).exists()]
    if occupied:
        raise AuditError("saídas não estão frescas; preservadas sem sobrescrever: " + ", ".join(occupied))
    preflight(manifest_path, manifest)
    root = Path(__file__).resolve().parents[2]
    geom_by_id = {g["id"]: geometry_length(root / g["path"]) for g in manifest["geometries"]}
    event_map = {e["path"]: e for e in manifest["tier_A"] + manifest["tier_B"]
                 if e["class"] == "solver_events"}
    all_entries = manifest["tier_A"] + manifest["tier_B"]
    candidate_entries = [e for e in all_entries if e["class"] == "race_timeseries"
                         and e["eligibility"] == "candidate"]
    sidecars = {}
    for raw_path, entry in event_map.items():
        base = raw_path.removesuffix("_events.csv") + ".csv"
        sidecars[base] = entry

    matrix = Counter()
    segments = Counter()
    phase_samples = Counter()
    transfer = defaultdict(Counter)
    run_summaries = []
    rejoin_available_by_run = {}
    raw_entries = []
    for entry in candidate_entries:
        run = entry["path"]
        ineligible = sampling_precheck(root / run)
        if ineligible:
            has_rejoin_fields = any(c in entry["header_fields"] for c in ("offtrack", "authority"))
            run_summaries.append({
                "run": run, "family": entry["family"], "arm": entry["analysis_arm"], "rows": "excluded",
                "drivers": "excluded",
                "geometry_id": entry.get("geometry_id") or "NA",
                "phase_coverage": "EXCLUDED before metric read: " + ineligible,
                "first_lap_coverage": "EXCLUDED before metric read",
                "rejoin_coverage": "EXCLUDED before metric read" if has_rejoin_fields else "NA: no offtrack/authority field",
                "solver_events_available": "yes" if sidecars.get(run) else "no",
                "hesitations": "", "missed_overtakes": "",
            })
            continue
        raw_entries.append(entry)
    for entry in raw_entries:
        run = entry["path"]
        rows = load_records(root / run)
        geom_id = entry.get("geometry_id")
        length = geom_by_id.get(geom_id) if geom_id else None
        phases, rejoin, progress, rejoin_observable = phase_labels(rows, length)
        rejoin_available_by_run[run] = rejoin_observable
        hesitations = detect_hesitations(rows, phases)
        contact_rows, pairs = contact_pairs(rows, phases, length)
        opportunities = opportunity_events(rows, phases, progress, length)
        tick_driver = {(int(float(r["tick"])), r["drv"]): r for r in rows}
        by_driver = defaultdict(list)
        for r in rows:
            by_driver[r["drv"]].append(r)
        pairs_by_tick_driver = defaultdict(list)
        for p in pairs:
            pairs_by_tick_driver[(p["tick"], p["drv_a"])].append(p)
            pairs_by_tick_driver[(p["tick"], p["drv_b"])].append(p)
        arm = entry["analysis_arm"]
        for r in rows:
            tick, drv = int(float(r["tick"])), r["drv"]
            phase = phases.get((tick, drv), "UNKNOWN")
            phase_samples[(run, arm, phase)] += 1
            if number(r, "offtrack", 0.0) == 1.0:
                matrix[(run, arm, "all", phase, "all", "offtrack_samples")] += 1
        transfer[run]
        for zero_key in (
            "launch_contact_samples", "first_lap_contact_samples",
            "first_lap_regroup_contact_samples", "first_lap_rejoin_contact_samples",
            "rejoin_contact_samples", "rejoin_pair_contacts_with_ontrack",
            "rejoin_solver_events", "hesitations", "launch_hesitations",
            "first_lap_hesitations", "first_lap_drivers",
        ):
            transfer[run][zero_key] = 0
        # 5 Hz car-car flag counts are per-car samples, matching the existing runner.
        for r in contact_rows:
            tick, drv = int(float(r["tick"])), r["drv"]
            phase = phases.get((tick, drv), "UNKNOWN")
            same_tick = pairs_by_tick_driver[(tick, drv)]
            if len(same_tick) == 1:
                ptype, pair_arm = same_tick[0]["pair_type"], same_tick[0]["pair_arm"]
            elif same_tick:
                ptype, pair_arm = "par_ambiguo", "multiplos_pares"
            else:
                ptype, pair_arm = "par_desconhecido", "unknown"
            matrix[(run, arm, pair_arm, phase, ptype, "car_car_samples")] += 1
            if rejoin.get((tick, drv), False):
                transfer[run]["rejoin_contact_samples"] += 1
        for p in pairs:
            matrix[(run, arm, p["pair_arm"], p["phase"], p["pair_type"], "reconstructed_pairs")] += 1
            a = tick_driver.get((p["tick"], p["drv_a"]))
            b = tick_driver.get((p["tick"], p["drv_b"]))
            if a and b:
                re_a = rejoin.get((p["tick"], p["drv_a"]), False)
                re_b = rejoin.get((p["tick"], p["drv_b"]), False)
                on_a = number(a, "offtrack", 0.0) == 0.0 and str(a.get("authority", "")).lower() != "rejoin"
                on_b = number(b, "offtrack", 0.0) == 0.0 and str(b.get("authority", "")).lower() != "rejoin"
                if (re_a and on_b) or (re_b and on_a):
                    transfer[run]["rejoin_pair_contacts_with_ontrack"] += 1
        for h in hesitations:
            matrix[(run, arm, "all", h["phase"], "all", "hesitations")] += 1
            transfer[run]["hesitations"] += 1
            if h["phase"] == "LARGADA":
                transfer[run]["launch_hesitations"] += 1
        for o in opportunities:
            matrix[(run, arm, o["pair_arm"], o["phase"], o["pair_type"], "missed_overtakes")] += 1
        for r in rows:
            tick, drv = int(float(r["tick"])), r["drv"]
            s = number(r, "s")
            if s is None:
                continue
            phase = phases.get((tick, drv), "UNKNOWN")
            s_local = s % length if length else s
            band = int(math.floor(s_local / SEGMENT_M) * SEGMENT_M)
            segments[(run, arm, phase, drv, band, "samples")] += 1
            if number(r, "car_car", 0.0) > 0:
                segments[(run, arm, phase, drv, band, "contacts")] += 1
        for h in hesitations:
            seq = sorted(by_driver[h["drv"]], key=lambda x: number(x, "t_s", 0.0))
            first = next((r for r in seq if number(r, "t_s", 0.0) == h["start_t_s"]), None)
            if first:
                s0 = number(first, "s")
                if s0 is not None:
                    band_s = s0 % length if length else s0
                    band = int(math.floor(band_s / SEGMENT_M) * SEGMENT_M)
                    segments[(run, arm, h["phase"], h["drv"], band, "hesitations")] += 1
        # Launch and first post-launch lap counters per driver.
        for drv, seq in by_driver.items():
            seq.sort(key=lambda r: number(r, "t_s", 0.0))
            end_lap = None
            if length:
                for prev, cur in zip(seq, seq[1:]):
                    if number(prev, "s", 0.0) - number(cur, "s", 0.0) > length / 2:
                        end_lap = number(cur, "t_s", math.inf)
                        break
            if end_lap is not None:
                transfer[run]["first_lap_drivers"] += 1
            for r in seq:
                t = number(r, "t_s", 0.0)
                if number(r, "car_car", 0.0) > 0 and t < LAUNCH_S:
                    transfer[run]["launch_contact_samples"] += 1
                elif end_lap is not None and number(r, "car_car", 0.0) > 0 \
                        and LAUNCH_S <= t <= end_lap:
                    transfer[run]["first_lap_contact_samples"] += 1
                    phase = phases.get((int(float(r["tick"])), drv), "UNKNOWN")
                    if phase == "REGROUP":
                        transfer[run]["first_lap_regroup_contact_samples"] += 1
                    elif phase == "REJOIN":
                        transfer[run]["first_lap_rejoin_contact_samples"] += 1
            if end_lap is not None:
                for h in hesitations:
                    if h["drv"] == drv and LAUNCH_S <= number(h, "start_t_s", math.inf) <= end_lap:
                        transfer[run]["first_lap_hesitations"] += 1
        run_summaries.append({
            "run": run, "family": entry["family"], "arm": arm, "rows": len(rows),
            "drivers": len({r["drv"] for r in rows}),
            "geometry_id": geom_id or "NA",
            "phase_coverage": (
                "REGROUP enabled" if length else "REGROUP_NA: no pinned source geometry"
            ) + ("; REJOIN unavailable" if not rejoin_observable else ""),
            "first_lap_coverage": "available" if length else "NA: no pinned source geometry",
            "rejoin_coverage": "available" if rejoin_observable else "NA: no offtrack/authority field",
            "solver_events_available": "yes" if sidecars.get(run) else "no",
            "hesitations": len(hesitations),
            "missed_overtakes": len(opportunities) if length else "NA: geometry not pinned",
        })
        ev_entry = sidecars.get(run)
        if ev_entry:
            ev_path = Path(ev_entry["path"])
            ev_rows = load_event_records(root / ev_path)
            # Event attribution follows sub->tick from the frozen file comment's value.
            sub_steps = int(ev_entry.get("sub_steps", 24))
            by_driver_rows = defaultdict(list)
            for rr in rows:
                by_driver_rows[rr["drv"]].append(rr)
            for drv in by_driver_rows:
                by_driver_rows[drv].sort(key=lambda rr: int(float(rr["tick"])))
            driver_ticks = {
                drv: [int(float(rr["tick"])) for rr in seq]
                for drv, seq in by_driver_rows.items()
            }
            for ev in ev_rows:
                tick_ev = int(float(ev["sub"])) // sub_steps
                def sample_at_or_before(drv):
                    seq = by_driver_rows.get(drv, [])
                    i = bisect_right(driver_ticks.get(drv, []), tick_ev) - 1
                    return seq[i] if i >= 0 else None
                a, b = sample_at_or_before(ev["drv_a"]), sample_at_or_before(ev["drv_b"])
                if not a or not b:
                    continue
                tkey = int(float(a["tick"]))
                ptype = pair_type(number(a, "lat", 0.0), number(b, "lat", 0.0))
                ph = phase_union(phases.get((tkey, ev["drv_a"]), "UNKNOWN"),
                                 phases.get((tkey, ev["drv_b"]), "UNKNOWN"))
                matrix[(run, arm, group_pair(a, b), ph, ptype, "solver_events")] += 1
                if ph == "REJOIN":
                    transfer[run]["rejoin_solver_events"] += 1
        if not length:
            for field in (
                "first_lap_contact_samples", "first_lap_regroup_contact_samples",
                "first_lap_rejoin_contact_samples", "first_lap_hesitations",
                "first_lap_drivers", "rejoin_pair_contacts_with_ontrack",
            ):
                transfer[run][field] = None
        if not rejoin_observable:
            for field in (
                "rejoin_contact_samples", "rejoin_pair_contacts_with_ontrack",
                "rejoin_solver_events",
            ):
                transfer[run][field] = None

    family_by_run = {e["path"]: e["family"] for e in raw_entries}
    length_by_run = {
        e["path"]: geom_by_id.get(e.get("geometry_id")) if e.get("geometry_id") else None
        for e in raw_entries
    }
    matrix_rows = []
    for (run, arm, pair_arm, phase, ptype, metric), count in sorted(matrix.items()):
        denom = phase_samples[(run, arm, phase)]
        matrix_rows.append({
            "run": run, "family": family_by_run[run], "arm": arm, "pair_arm": pair_arm,
            "phase": phase, "pair_type": ptype,
            "metric": metric, "count": count,
            "phase_vehicle_samples": denom,
            "per_10000_vehicle_samples": (10000.0 * count / denom) if denom else "",
        })
    agg = Counter()
    runs_by_key = defaultdict(set)
    for (run, arm, pair_arm, phase, ptype, metric), count in matrix.items():
        key = (family_by_run[run], arm, pair_arm, phase, ptype, metric)
        agg[key] += count
        runs_by_key[key].add(run)
    aggregate_rows = [
        {"family": k[0], "arm": k[1], "pair_arm": k[2], "phase": k[3],
         "pair_type": k[4], "metric": k[5],
         "runs": len(runs_by_key[k]), "count": value,
         "phase_vehicle_samples": sum(phase_samples[(run, k[1], k[3])]
                                      for run in runs_by_key[k]),
         "per_10000_vehicle_samples": (
             10000.0 * value /
             sum(phase_samples[(run, k[1], k[3])] for run in runs_by_key[k])
         ) if sum(phase_samples[(run, k[1], k[3])] for run in runs_by_key[k]) else "",
        }
        for k, value in sorted(agg.items())
    ]
    all_segment_rows = [
        {"run": k[0], "family": family_by_run[k[0]], "arm": k[1],
         "phase": k[2], "drv": k[3], "s_band_start_m": k[4], "metric": k[5], "count": v}
        for k, v in sorted(segments.items())
    ]
    best = defaultdict(list)
    for row in all_segment_rows:
        best[(row["run"], row["phase"], row["metric"])].append(row)
    segment_rows = []
    for key, values in best.items():
        segment_rows.extend(sorted(values, key=lambda r: (-r["count"], r["drv"], r["s_band_start_m"]))[:20])
    transfer_rows = [
        {"run": run, "family": family_by_run[run],
         "arm": next(e["analysis_arm"] for e in raw_entries if e["path"] == run),
         "first_lap_coverage": "available" if length_by_run[run] else "NA: no pinned source geometry",
         "rejoin_coverage": "available" if rejoin_available_by_run[run] else "NA: no offtrack/authority field",
         **dict(values)}
        for run, values in sorted(transfer.items())
    ]
    transfer_by_arm = defaultdict(Counter)
    transfer_runs_by_arm = Counter()
    transfer_first_lap_runs = Counter()
    transfer_rejoin_runs = Counter()
    for row in transfer_rows:
        group = (row["family"], row["arm"])
        transfer_runs_by_arm[group] += 1
        if length_by_run[row["run"]]:
            transfer_first_lap_runs[group] += 1
        if row["rejoin_coverage"] == "available":
            transfer_rejoin_runs[group] += 1
        for field in (
            "launch_contact_samples", "first_lap_contact_samples",
            "first_lap_regroup_contact_samples", "first_lap_rejoin_contact_samples",
            "rejoin_contact_samples", "rejoin_pair_contacts_with_ontrack",
            "rejoin_solver_events", "hesitations", "launch_hesitations",
            "first_lap_hesitations", "first_lap_drivers",
        ):
            value = row.get(field, 0)
            if isinstance(value, (int, float)):
                transfer_by_arm[group][field] += value
    transfer_aggregate_rows = [
        {"family": group[0], "arm": group[1], "runs": transfer_runs_by_arm[group],
         "first_lap_geometry_runs": transfer_first_lap_runs[group],
         "rejoin_observable_runs": transfer_rejoin_runs[group],
         **dict(values)}
        for group, values in sorted(transfer_by_arm.items())
    ]
    for row in transfer_aggregate_rows:
        if row["first_lap_geometry_runs"] == 0:
            for field in (
                "first_lap_contact_samples", "first_lap_regroup_contact_samples",
                "first_lap_rejoin_contact_samples", "first_lap_hesitations",
                "first_lap_drivers", "rejoin_pair_contacts_with_ontrack",
            ):
                row[field] = ""
        if row["rejoin_observable_runs"] == 0:
            for field in (
                "rejoin_contact_samples", "rejoin_pair_contacts_with_ontrack",
                "rejoin_solver_events",
            ):
                row[field] = ""
    write_csv(out_dir / "1_phase_pair_arm.csv",
              ["run", "family", "arm", "pair_arm", "phase", "pair_type", "metric", "count",
               "phase_vehicle_samples", "per_10000_vehicle_samples"], matrix_rows)
    write_csv(out_dir / "1b_phase_pair_aggregate.csv",
              ["family", "arm", "pair_arm", "phase", "pair_type", "metric", "runs", "count",
               "phase_vehicle_samples", "per_10000_vehicle_samples"], aggregate_rows)
    write_csv(out_dir / "2_top_segments_car.csv",
              ["run", "family", "arm", "phase", "drv", "s_band_start_m", "metric", "count"], segment_rows)
    write_csv(out_dir / "3_reentry_launch_transfer.csv",
              ["run", "family", "arm", "launch_contact_samples", "first_lap_contact_samples",
               "first_lap_regroup_contact_samples", "first_lap_rejoin_contact_samples",
               "rejoin_contact_samples", "rejoin_pair_contacts_with_ontrack",
               "rejoin_solver_events", "hesitations", "launch_hesitations",
               "first_lap_hesitations", "first_lap_drivers", "first_lap_coverage",
               "rejoin_coverage"],
              transfer_rows)
    write_csv(out_dir / "3b_transfer_by_arm.csv",
              ["family", "arm", "runs", "first_lap_geometry_runs", "rejoin_observable_runs",
               "launch_contact_samples", "first_lap_contact_samples",
               "first_lap_regroup_contact_samples", "first_lap_rejoin_contact_samples",
               "rejoin_contact_samples", "rejoin_pair_contacts_with_ontrack",
               "rejoin_solver_events", "hesitations", "launch_hesitations",
               "first_lap_hesitations", "first_lap_drivers"],
              transfer_aggregate_rows)
    write_csv(out_dir / "3c_run_coverage.csv",
              ["run", "family", "arm", "rows", "drivers", "geometry_id", "phase_coverage",
               "first_lap_coverage", "rejoin_coverage", "solver_events_available",
               "hesitations", "missed_overtakes"],
              run_summaries)
    print(f"TRAfego-MED-1B: {len(raw_entries)} séries processadas; saídas em {out_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.manifest:
        parser.error("--manifest é obrigatório fora de --selftest")
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("analysis_script_version") != VERSION:
        raise AuditError("versão do script não corresponde ao manifest congelado")
    out_dir = args.out_dir or manifest_path.parent
    run_analysis(manifest_path, manifest, out_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"PARE: {exc}", file=sys.stderr)
        raise SystemExit(2)
