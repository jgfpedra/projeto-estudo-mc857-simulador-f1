#!/usr/bin/env python3
"""Offline, fail-closed report for REJOIN-TEL-1 v3.5 telemetry."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_TRACK = BACKEND / "model_train/tracks_frozen/Monaco_v2.json"
EXPECTED_TRACK_SHA = "af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2"
EXPECTED_R4_SHA = "6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7"
LEGACY_COLUMNS = (
    "tick,t_s,drv,speed,s,lat,th,brk,steer_rad,g_long,stuck_t,contacts,car_car,"
    "impulse,impulse_dv,offtrack,authority,g_gate,r_norm,composite_active,"
    "res_0,res_1,res_2,res_3,res_4,res_5,res_6,res_7,res_8,res_9,res_10,"
    "res_11,res_12,res_13,res_14,res_15,w_kind,w_grip,w_trans,tyre_life,"
    "tyre_grip,cum_dist,obs0,obs1,obs2,obs3,obs4,obs5,obs6,obs7,obs8,obs9,"
    "obs10,obs11,obs12,obs13,obs14,obs15,obs16,obs17,obs18,obs19,obs20,obs21,"
    "obs22,imp_events,imp_dv,imp_dv_max,body_x,body_y,ns_raw"
).split(",")
TEL_COLUMNS = [
    "off_window_id", "off_age_ticks", "anchor_x", "anchor_y", "anchor_s",
    "target_x", "target_y", "reentry_heading_err_deg", "target_kappa",
]
EXPECTED_COLUMNS = LEGACY_COLUMNS + TEL_COLUMNS
NUMERIC_COLUMNS = [
    "tick", "t_s", "speed", "s", "lat", "offtrack", "body_x", "body_y",
    "ns_raw", *TEL_COLUMNS,
]
OUTPUT_NAMES = [
    "3_rejoin_windows.csv", "4_hesitations.csv", "5_summary.json",
    "6_veredito.md", "7_hashes.json",
]


class AuditError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def csv_lines(path: Path):
    with path.open("rb") as f:
        for raw in f:
            if raw.startswith(b"#") or not raw.strip():
                continue
            yield raw.rstrip(b"\r\n")


def check_prefix(new_path: Path, reference_path: Path) -> dict:
    ref_sha = sha256_file(reference_path)
    if ref_sha != EXPECTED_R4_SHA:
        raise AuditError(f"PARE: SHA R4 v3.4 divergente: {ref_sha}")
    old_lines = list(csv_lines(reference_path))
    new_lines = list(csv_lines(new_path))
    if len(old_lines) != 30001 or len(new_lines) != 30001:
        raise AuditError(
            f"PARE: linhas para prefixo: R4={len(old_lines)-1}, v3.5={len(new_lines)-1}")
    for line_no, (old, new) in enumerate(zip(old_lines, new_lines), start=1):
        old_fields, new_fields = old.split(b","), new.split(b",")
        if len(old_fields) != 71 or len(new_fields) != 80:
            raise AuditError(f"PARE: schema no prefixo, linha CSV {line_no}")
        if b",".join(old_fields) != b",".join(new_fields[:71]):
            raise AuditError(f"PARE: prefixo [:71] divergiu na linha CSV {line_no}")
    return {"reference_path": str(reference_path), "reference_sha256": ref_sha,
            "new_path": str(new_path), "new_sha256": sha256_file(new_path),
            "rows_compared_including_header": len(old_lines),
            "prefix_columns": 71, "result": "PASS"}


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        lines = (line for line in f if not line.startswith("#"))
        reader = csv.DictReader(lines)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise AuditError(
                f"PARE: schema v3.5; esperado 80 colunas, recebido "
                f"{len(reader.fieldnames or [])}: {reader.fieldnames}")
        rows = list(reader)
    if len(rows) != 30000:
        raise AuditError(f"PARE: esperado 30000 linhas, recebido {len(rows)}")
    return rows


def number(row, field):
    try:
        value = float(row[field])
    except (ValueError, TypeError, KeyError) as e:
        raise AuditError(f"PARE: {field} não numérico: {row.get(field)!r}") from e
    if not math.isfinite(value):
        raise AuditError(f"PARE: {field} não finito: {value}")
    return value


def validate_rows(rows):
    by_driver = {}
    for idx, row in enumerate(rows):
        for field in NUMERIC_COLUMNS:
            number(row, field)
        try:
            tick = int(row["tick"])
            window_id = int(row["off_window_id"])
            age = int(row["off_age_ticks"])
            offtrack = int(row["offtrack"])
        except ValueError as e:
            raise AuditError(f"PARE: campo inteiro inválido na linha {idx+1}") from e
        if tick != number(row, "tick") or window_id != number(row, "off_window_id") \
                or age != number(row, "off_age_ticks"):
            raise AuditError(f"PARE: tick/ID/idade não inteiro na linha {idx+1}")
        if offtrack not in (0, 1):
            raise AuditError(f"PARE: offtrack inválido na linha {idx+1}")
        if window_id < 0 or age < 0 or (window_id == 0 and age != 0):
            raise AuditError(f"PARE: ID/idade inválidos na linha {idx+1}")
        if window_id > 0 and age < 0:
            raise AuditError(f"PARE: idade negativa na linha {idx+1}")
        if window_id > 0 and not (number(row, "target_x") != 0.0
                                   or number(row, "target_y") != 0.0
                                   or number(row, "target_kappa") != 0.0):
            raise AuditError(f"PARE: estado off sem alvo capturado na linha {idx+1}")
        if window_id == 0 and any(number(row, c) != 0.0
                                  for c in ("target_x", "target_y", "target_kappa")):
            raise AuditError(f"PARE: alvo sem janela off na linha {idx+1}")
        by_driver.setdefault(row["drv"], []).append(row)

    if len(by_driver) != 10:
        raise AuditError(f"PARE: esperado 10 carros, recebido {len(by_driver)}")
    all_windows = []
    for drv, group in by_driver.items():
        group.sort(key=lambda r: int(r["tick"]))
        ticks = [int(r["tick"]) for r in group]
        if ticks != list(range(0, 6000, 2)):
            raise AuditError(f"PARE: ticks ausentes/duplicados para {drv}")
        last_id = 0
        last_row_by_id = {}
        for row in group:
            wid = int(row["off_window_id"])
            tick, age = int(row["tick"]), int(row["off_age_ticks"])
            if wid == 0:
                if any(number(row, c) != 0.0 for c in
                       ("reentry_heading_err_deg",)):
                    # A reentry error belongs to the first on-track sample.
                    previous = last_row_by_id.get("_prior_off_id")
                    if previous == 0:
                        raise AuditError(
                            f"PARE: rumo não-zero fora de reentrada em {drv}:{tick}")
            else:
                if wid < last_id:
                    raise AuditError(f"PARE: ID de janela regressivo em {drv}:{tick}")
                prev = last_row_by_id.get(wid)
                if prev is not None:
                    if tick - int(prev["tick"]) != 2:
                        raise AuditError(f"PARE: janela descontínua em {drv}:{tick}")
                    if age - int(prev["off_age_ticks"]) != 2:
                        raise AuditError(f"PARE: idade não acompanha ticks em {drv}:{tick}")
                    for c in ("anchor_x", "anchor_y", "anchor_s"):
                        if number(row, c) != number(prev, c):
                            raise AuditError(f"PARE: âncora mudou durante off em {drv}:{tick}")
                last_id = wid
                last_row_by_id[wid] = row
            last_row_by_id["_prior_off_id"] = wid
        # Each non-zero ID may appear in only one contiguous run.
        ids = [int(r["off_window_id"]) for r in group if int(r["off_window_id"]) != 0]
        unique = list(dict.fromkeys(ids))
        if any(b <= a for a, b in zip(unique, unique[1:])):
            raise AuditError(f"PARE: IDs não crescentes em {drv}")
        for wid in unique:
            window_rows = [r for r in group if int(r["off_window_id"]) == wid]
            start_i = group.index(window_rows[0])
            next_row = group[start_i + len(window_rows)] if start_i + len(window_rows) < len(group) else None
            returned = next_row if next_row and int(next_row["off_window_id"]) == 0 else None
            all_windows.append(dict(drv=drv, window_id=wid, rows=window_rows,
                                    exit_row=window_rows[0], last_off_row=window_rows[-1],
                                    reentry_row=returned))
    if len(all_windows) != 345:
        raise AuditError(f"PARE: esperado 345 janelas visíveis, recebido {len(all_windows)}")
    return by_driver, all_windows


def load_geometry(path: Path):
    if sha256_file(path) != EXPECTED_TRACK_SHA:
        raise AuditError("PARE: SHA Monaco frozen divergente")
    track = json.loads(path.read_text(encoding="utf-8"))
    points = track.get("waypoints")
    if not isinstance(points, list) or len(points) != 834:
        raise AuditError("PARE: geometria Monaco esperada com 834 waypoints")
    points = [(float(p[0]), float(p[1])) for p in points]
    lengths = []
    headings = []
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        dx, dy = x2 - x1, y2 - y1
        lengths.append(math.hypot(dx, dy))
        headings.append(math.atan2(dy, dx))
    cumulative = [0.0]
    for length in lengths[:-1]:
        cumulative.append(cumulative[-1] + length)
    track_length = sum(lengths)
    if abs(track_length - 3335.2) > 0.2:
        raise AuditError(f"PARE: comprimento Monaco inesperado {track_length}")
    return points, lengths, headings, cumulative, track_length


def heading_at(s, headings, cumulative, track_length):
    s = float(s) % track_length
    lo, hi = 0, len(cumulative)
    while lo < hi:
        mid = (lo + hi) // 2
        if cumulative[mid] <= s:
            lo = mid + 1
        else:
            hi = mid
    idx = max(0, min(lo - 1, len(headings) - 1))
    return headings[idx]


def quantile_linear(values, q):
    if not values:
        return None
    values = sorted(float(v) for v in values)
    pos = (len(values) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (pos - low)


def pearson(xs, ys):
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    xx = sum((x - mx) ** 2 for x in xs)
    yy = sum((y - my) ** 2 for y in ys)
    if xx == 0 or yy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(xx * yy)


def build_windows(by_driver, windows, headings, cumulative, track_length):
    output = []
    reentry_by_driver = {}
    for window in windows:
        drv = window["drv"]
        exit_row = window["exit_row"]
        ret = window["reentry_row"]
        tick_out = int(exit_row["tick"])
        tick_ret = int(ret["tick"]) if ret else None
        duration_ticks = (tick_ret - tick_out if ret
                          else int(window["last_off_row"]["tick"]) - tick_out)
        target_x, target_y = number(exit_row, "target_x"), number(exit_row, "target_y")
        has_target = any(number(exit_row, c) != 0.0
                         for c in ("target_x", "target_y", "target_kappa"))
        lead = (math.hypot(target_x - number(exit_row, "body_x"),
                           target_y - number(exit_row, "body_y")) if has_target else None)
        err = number(ret, "reentry_heading_err_deg") if ret else None
        unidentifiable = False
        if ret:
            rows = by_driver[drv]
            j = next(i for i, r in enumerate(rows) if r is ret)
            if j > 0:
                prev = rows[j - 1]
                unidentifiable = math.hypot(number(ret, "body_x") - number(prev, "body_x"),
                                            number(ret, "body_y") - number(prev, "body_y")) <= 1e-9
                if not unidentifiable:
                    course = math.atan2(number(ret, "body_y") - number(prev, "body_y"),
                                        number(ret, "body_x") - number(prev, "body_x"))
                    expected_err = math.degrees(
                        (course - heading_at(number(ret, "s"), headings,
                                             cumulative, track_length) + math.pi)
                        % (2 * math.pi) - math.pi)
                    if abs(expected_err - err) > 1e-7:
                        raise AuditError(
                            f"PARE: rumo/tangente reconstruído diverge em {drv}:{tick_ret}")
        record = dict(
            drv=drv, off_window_id=window["window_id"],
            exit_tick=tick_out, last_off_sample_tick=int(window["last_off_row"]["tick"]),
            reentry_tick=tick_ret, duration_ticks_observed=duration_ticks,
            duration_s_observed=duration_ticks * 0.1, censored=ret is None,
            heading_err_deg=err, heading_course_unidentifiable=unidentifiable,
            target_kappa=number(exit_row, "target_kappa"),
            target_lead_m=lead,
            anchor_x=number(exit_row, "anchor_x"),
            anchor_y=number(exit_row, "anchor_y"),
            anchor_s=number(exit_row, "anchor_s"),
            target_x=target_x, target_y=target_y)
        output.append(record)
        if ret:
            reentry_by_driver.setdefault(drv, []).append(record)

    # Next observed off-window within 10 s after a sampled return.
    for record in output:
        retick = record["reentry_tick"]
        record["second_exit_within_10s"] = False
        if retick is None:
            continue
        next_starts = [w["exit_tick"] for w in output
                       if w["drv"] == record["drv"] and w["exit_tick"] > retick]
        if next_starts and min(next_starts) - retick <= 100:
            record["second_exit_within_10s"] = True
    return output


def detect_hesitations(by_driver):
    episodes = []
    for drv, rows in by_driver.items():
        rows = [r for r in rows if number(r, "t_s") > 20.0]
        n, i = len(rows), 0
        while i < n:
            if number(rows[i], "speed") >= 0.5:
                i += 1
                continue
            j = i + 1
            while j < n and number(rows[j], "speed") < 0.5:
                j += 1
            duration = number(rows[min(j, n - 1)], "t_s") - number(rows[i], "t_s")
            if 0.3 <= duration < 3.0:
                last = rows[j - 1] if j < n else rows[n - 1]
                episodes.append(dict(
                    drv=drv, tick_start=int(rows[i]["tick"]),
                    tick_end=int(last["tick"]), duration_s=duration,
                    offtrack_any=any(int(r["offtrack"]) for r in rows[i:j]),
                    reentry_tick=None, seconds_since_reentry=None,
                    within_10s_after_reentry=False))
            i = j
    return episodes


def analyze(rows, track_path):
    by_driver, windows = validate_rows(rows)
    points, lengths, headings, cumulative, track_length = load_geometry(track_path)
    window_table = build_windows(by_driver, windows, headings, cumulative, track_length)
    hesitations = detect_hesitations(by_driver)
    reentries = [w for w in window_table if w["reentry_tick"] is not None]
    for h in hesitations:
        prior = [w for w in reentries if w["drv"] == h["drv"]
                 and w["reentry_tick"] <= h["tick_start"]]
        if prior:
            nearest = max(prior, key=lambda w: w["reentry_tick"])
            delta = h["tick_start"] - nearest["reentry_tick"]
            h["reentry_tick"] = nearest["reentry_tick"]
            h["seconds_since_reentry"] = delta * 0.1
            h["within_10s_after_reentry"] = delta <= 100

    angle_rows = [w for w in reentries if not w["heading_course_unidentifiable"]]
    angle_x = [float(w["heading_err_deg"]) for w in angle_rows]
    angle_y = [int(w["second_exit_within_10s"]) for w in angle_rows]
    returned_seconds = [w["duration_s_observed"] for w in reentries]
    summary = dict(
        rows=len(rows), drivers=len(by_driver), visible_windows=len(window_table),
        expected_windows=345, observable_reentries=len(reentries),
        censored_windows=sum(bool(w["censored"]) for w in window_table),
        heading_threshold_deg=20.0,
        reentries_heading_abs_gt_20=sum(abs(x) > 20.0 for x in angle_x),
        reentries_heading_fraction_gt_20=(
            sum(abs(x) > 20.0 for x in angle_x) / len(angle_x) if angle_x else None),
        heading_vs_second_exit_pearson=pearson(angle_x, angle_y),
        heading_correlation_n=len(angle_x),
        return_seconds=dict(p50=quantile_linear(returned_seconds, 0.50),
                            p95=quantile_linear(returned_seconds, 0.95),
                            max=max(returned_seconds) if returned_seconds else None),
        hesitations_total=len(hesitations),
        hesitations_within_10s_after_reentry=sum(
            bool(h["within_10s_after_reentry"]) for h in hesitations),
        published_comparison={
            "R2_ON_hesitations": 28,
            "published_OFF_threshold": 12,
            "R2_ON_return_time": "not published in authorized result artifacts",
        },
        angle_course_unidentifiable=sum(
            bool(w["heading_course_unidentifiable"]) for w in reentries),
        geometry=dict(track_length_m=track_length, waypoint_count=len(points),
                      segments=len(lengths)))
    return summary, window_table, hesitations


def csv_text(rows, columns):
    import io
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def run_selftest():
    # Synthetic geometry and records only; deliberately opens no repository data.
    triangle = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    headings = [0.0, 2.0 * math.pi / 3.0, -3.0 * math.pi / 4.0]
    cumulative = [0.0, 1.0, 1.0 + math.sqrt(2.0)]
    length = 1.0 + 1.0 + math.sqrt(2.0)
    if abs(heading_at(0.5, headings, cumulative, length)) > 1e-12:
        raise AuditError("selftest: heading_at sintético")
    if quantile_linear([0.0, 10.0], 0.95) != 9.5:
        raise AuditError("selftest: quantil linear")
    if abs(pearson([1.0, 2.0, 3.0], [0.0, 1.0, 1.0]) - 0.8660254037844387) > 1e-12:
        raise AuditError("selftest: Pearson")
    synthetic = [
        {"tick": 0, "t_s": 20.1, "drv": "A", "speed": 0.4,
         "offtrack": 0, "off_window_id": 0, "off_age_ticks": 0},
        {"tick": 2, "t_s": 20.3, "drv": "A", "speed": 0.4,
         "offtrack": 0, "off_window_id": 0, "off_age_ticks": 0},
        {"tick": 4, "t_s": 20.5, "drv": "A", "speed": 2.0,
         "offtrack": 0, "off_window_id": 0, "off_age_ticks": 0},
    ]
    h = detect_hesitations({"A": synthetic})
    if len(h) != 1 or abs(h[0]["duration_s"] - 0.4) > 1e-12:
        raise AuditError("selftest: episódio de hesitação sintético")
    print("selftest sintético PASS; nenhum CSV/track/replay foi aberto")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="executa somente verificações sintéticas")
    ap.add_argument("--check-prefix", action="store_true",
                    help="compara [:71] do novo CSV ao R4 v3.4 e encerra")
    ap.add_argument("--input", type=Path)
    ap.add_argument("--reference", type=Path,
                    default=BACKEND / "experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.csv")
    ap.add_argument("--track", type=Path, default=DEFAULT_TRACK)
    ap.add_argument("--out-dir", type=Path,
                    default=BACKEND / "experiments/rejoin-tel-1/autopsia")
    args = ap.parse_args(argv)
    print(f"schema CSV esperado ({len(EXPECTED_COLUMNS)}): {','.join(EXPECTED_COLUMNS)}")
    if args.selftest:
        run_selftest()
        return 0
    if args.check_prefix:
        if not args.input:
            ap.error("--check-prefix requer --input")
        result = check_prefix(args.input, args.reference)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if not args.input:
        ap.error("--input é obrigatório fora de --selftest")
    for name in OUTPUT_NAMES:
        if (args.out_dir / name).exists():
            raise AuditError(f"PARE: saída já existe: {args.out_dir / name}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_csv(args.input)
    summary, windows, hesitations = analyze(rows, args.track)
    summary["input_sha256"] = sha256_file(args.input)
    summary["track_sha256"] = sha256_file(args.track)
    summary["audit_sha256"] = sha256_file(Path(__file__))
    summary["input_path"] = str(args.input)
    summary["track_path"] = str(args.track)
    window_cols = list(windows[0].keys()) if windows else []
    hesitation_cols = list(hesitations[0].keys()) if hesitations else [
        "drv", "tick_start", "tick_end", "duration_s", "offtrack_any",
        "reentry_tick", "seconds_since_reentry", "within_10s_after_reentry"]
    payloads = {
        "3_rejoin_windows.csv": csv_text(windows, window_cols),
        "4_hesitations.csv": csv_text(hesitations, hesitation_cols),
        "5_summary.json": json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    }
    fraction = summary["reentries_heading_fraction_gt_20"]
    correlation = summary["heading_vs_second_exit_pearson"]
    if fraction is not None and fraction > 0.5 and correlation is not None and correlation > 0:
        recommendation = (
            "RECOMENDAR RECUP-2 opt-in, com novo prereg e dois sims; a maioria das "
            "reentradas observáveis excedeu 20° e a associação heading/re-excursão "
            "foi positiva. Isto é evidência descritiva, não causalidade nem promoção.")
    elif len(windows) < 2 or correlation is None:
        recommendation = (
            "ARQUIVAR/ADIAR a hipótese angular por evidência insuficiente ou correlação "
            "não identificável; isto não afirma ausência de defeito.")
    else:
        recommendation = (
            "ARQUIVAR a hipótese angular neste ciclo: a assinatura combinada frozen "
            "(maioria >20° e associação positiva) não apareceu; isto não afirma "
            "ausência de defeito nem exclui outro mecanismo.")
    verdict = (
        "# REJOIN-TEL-1 — veredito report-only\n\n"
        f"- Janelas visíveis: {summary['visible_windows']} (esperadas 345); "
        f"reentradas observáveis: {summary['observable_reentries']}; censuradas: "
        f"{summary['censored_windows']}.\n"
        f"- Reentradas com `|heading_err| > 20°`: "
        f"{summary['reentries_heading_abs_gt_20']}/{summary['heading_correlation_n']} "
        f"({fraction if fraction is not None else 'n/a'}); correlação Pearson com "
        f"2ª saída em até 10 s: {correlation if correlation is not None else 'n/a'} "
        f"(n={summary['heading_correlation_n']}).\n"
        f"- Retorno observado: p50={summary['return_seconds']['p50']} s, "
        f"p95={summary['return_seconds']['p95']} s, max="
        f"{summary['return_seconds']['max']} s; R2-ON não tem estatística de retorno "
        "publicada nas fontes autorizadas.\n"
        f"- Hesitações R4: {summary['hesitations_total']}; em até 10 s após reentrada: "
        f"{summary['hesitations_within_10s_after_reentry']}; referências publicadas: "
        "R2 ON=28, limite OFF=12.\n\n"
        f"## Encaminhamento único\n\n{recommendation}\n\n"
        "Nenhuma correção foi aplicada, nenhuma promoção ocorreu e a suíte de "
        "referência não foi alterada.\n")
    payloads["6_veredito.md"] = verdict
    hashes = {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
              for name, text in payloads.items()}
    payloads["7_hashes.json"] = json.dumps(
        {"input_sha256": summary["input_sha256"],
         "track_sha256": summary["track_sha256"],
         "audit_sha256": summary["audit_sha256"],
         "outputs_sha256": hashes}, indent=2, ensure_ascii=False) + "\n"
    for name, content in payloads.items():
        out = args.out_dir / name
        if out.exists():
            raise AuditError(f"PARE: saída já existe: {out}")
        out.write_text(content, encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    for name in payloads:
        print(f"SHA256 {name} {sha256_file(args.out_dir / name)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
