#!/usr/bin/env python3
"""PASS-1 offline audit. Reads completed CSVs and runner logs; never simulates."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from itertools import chain
from pathlib import Path


REQUIRED = {
    'tick', 't_s', 'drv', 'speed', 's', 'lat', 'car_car', 'offtrack',
    'cum_dist', 'authority',
}
REQUIRED_PROF = REQUIRED | {'p_state'}
ROW_TARGET = 30000


def _read_csv(path, require_professor_state=False):
    p = Path(path)
    blob = p.read_bytes()
    with p.open('r', newline='', encoding='utf-8') as f:
        lines = (line for line in f if line.strip() and not line.lstrip().startswith('#'))
        header_line = next(lines, None)
        if header_line is None:
            raise ValueError(f"CSV sem header: {p}")
        reader = csv.DictReader(chain((header_line,), lines))
        fields = list(reader.fieldnames)
        missing = (REQUIRED_PROF if require_professor_state else REQUIRED) - set(fields)
        if missing:
            raise ValueError(f"{p}: schema faltando colunas {sorted(missing)}")
        rows = []
        for row in reader:
            try:
                rows.append({
                    **row,
                    'tick': int(row['tick']), 't_s': float(row['t_s']),
                    'drv': str(row['drv']), 'speed': float(row['speed']),
                    's': float(row['s']), 'lat': float(row['lat']),
                    'car_car': int(float(row['car_car'])),
                    'offtrack': int(float(row['offtrack'])),
                    'cum_dist': float(row['cum_dist']),
                })
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"{p}: linha inválida perto do registro {len(rows)+2}") from exc
    if len(rows) != ROW_TARGET:
        raise ValueError(f"{p}: esperadas {ROW_TARGET} linhas de dados, recebidas {len(rows)}")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['drv']].append(row)
    if len(grouped) != 10:
        raise ValueError(f"{p}: esperados 10 carros, recebidos {len(grouped)}")
    for drv_rows in grouped.values():
        drv_rows.sort(key=lambda r: r['tick'])
        ticks = [r['tick'] for r in drv_rows]
        if len(ticks) != 3000 or ticks[0] != 0 or ticks[-1] != 5998:
            raise ValueError(
                f"{p}: cada carro deve conter 3000 amostras de tick 0 a 5998")
        if any((b - a) != 2 for a, b in zip(ticks, ticks[1:])):
            raise ValueError(f"{p}: ticks por carro não seguem amostragem 5 Hz")
        if any((b['t_s'] - a['t_s']) < 0.19 or (b['t_s'] - a['t_s']) > 0.21
               for a, b in zip(drv_rows, drv_rows[1:])):
            raise ValueError(f"{p}: amostragem diferente de 5 Hz")
    return dict(path=str(p), sha256=hashlib.sha256(blob).hexdigest(),
                size_bytes=len(blob), data_rows=len(rows), fields=fields,
                header_line_sha256=hashlib.sha256(
                    header_line.encode('utf-8')).hexdigest(),
                rows=rows, by_driver=dict(grouped))


def _hesitations(rows, threshold=0.5, min_duration=0.3, max_duration=3.0,
                 after_s=20.0):
    """Frozen race_diagnostic hesitation rule on emitted 5 Hz samples."""
    count = 0
    for drv_rows in _group(rows).values():
        samples = [r for r in sorted(drv_rows, key=lambda r: r['t_s'])
                   if r['t_s'] > after_s]
        i = 0
        while i < len(samples):
            if samples[i]['speed'] < threshold:
                j = i
                while j < len(samples) and samples[j]['speed'] < threshold:
                    j += 1
                end = min(j, len(samples) - 1)
                duration = samples[end]['t_s'] - samples[i]['t_s']
                if min_duration <= duration < max_duration:
                    count += 1
                i = j
            else:
                i += 1
    return count


def _group(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['drv']].append(row)
    return grouped


def _mixed_hesitations(rows):
    """A2 convention: after first >10 m/s, two or more consecutive <2 m/s rows."""
    total = 0
    for drv_rows in _group(rows).values():
        samples = sorted(drv_rows, key=lambda r: r['tick'])
        above = next((i for i, r in enumerate(samples) if r['speed'] > 10.0), None)
        if above is None:
            continue
        run = 0
        for row in samples[above:]:
            if row['speed'] < 2.0:
                run += 1
            else:
                if run >= 2:
                    total += 1
                run = 0
        if run >= 2:
            total += 1
    return total


def _lap_times(rows, track_length):
    all_laps = []
    completed = 0
    first_lap_rows = []
    for drv_rows in _group(rows).values():
        samples = sorted(drv_rows, key=lambda r: r['t_s'])
        first_lap_rows.extend(r for r in samples if r['cum_dist'] <= track_length)
        previous = samples[0]
        target = track_length
        crossings = []
        for current in samples[1:]:
            while current['cum_dist'] >= target and previous['cum_dist'] < target:
                span = current['cum_dist'] - previous['cum_dist']
                frac = 0.0 if span <= 0.0 else (target - previous['cum_dist']) / span
                cross_t = previous['t_s'] + frac * (current['t_s'] - previous['t_s'])
                crossings.append(cross_t)
                target += track_length
            previous = current
        completed += len(crossings)
        if crossings:
            all_laps.append(crossings[0] - samples[0]['t_s'])
            all_laps.extend(b - a for a, b in zip(crossings, crossings[1:]))
    return all_laps, completed, first_lap_rows


def _rolling_lap_times(rows, track_length):
    """Lap times after the first start-to-line interval, matching A2 rolling."""
    rolling = []
    for drv_rows in _group(rows).values():
        samples = sorted(drv_rows, key=lambda r: r['t_s'])
        crossings = []
        previous = samples[0]
        target = track_length
        for current in samples[1:]:
            while current['cum_dist'] >= target and previous['cum_dist'] < target:
                span = current['cum_dist'] - previous['cum_dist']
                frac = 0.0 if span <= 0.0 else (target - previous['cum_dist']) / span
                crossings.append(previous['t_s'] + frac *
                                 (current['t_s'] - previous['t_s']))
                target += track_length
            previous = current
        rolling.extend(b - a for a, b in zip(crossings, crossings[1:]))
    return rolling


def _rejoin_windows(rows):
    windows = defaultdict(list)
    for drv, samples in _group(rows).items():
        ordered = sorted(samples, key=lambda r: r['t_s'])
        was_rejoining = False
        for row in ordered:
            is_rejoining = (bool(row['offtrack']) or row.get('authority') in
                            ('rejoin', 'recovery_rejoin'))
            if was_rejoining and not is_rejoining:
                windows[drv].append((row['t_s'], row['t_s'] + 10.0))
            was_rejoining = is_rejoining
        # Merge overlapping post-reentry windows so samples/hesitations count
        # once when a driver briefly leaves and re-enters again.
        merged = []
        for start, end in sorted(windows[drv]):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        windows[drv] = merged
    return windows


def _count_in_windows(rows, windows):
    contacts = 0
    for row in rows:
        if any(start <= row['t_s'] <= end
               for start, end in windows.get(row['drv'], ())):
            contacts += int(row['car_car'] > 0)
    total_hesitations = 0
    for drv, samples in _group(rows).items():
        for start, end in windows.get(drv, ()):
            total_hesitations += _hesitations(
                [r for r in samples if start <= r['t_s'] <= end],
                after_s=-math.inf)
    return contacts, total_hesitations


def _settled_swaps(rows, launch_s=60.0, hysteresis_m=10.0):
    by_tick = defaultdict(list)
    for row in rows:
        by_tick[row['tick']].append(row)
    settled = {}
    total = postlaunch = 0
    for tick in sorted(by_tick):
        sample = by_tick[tick]
        sample.sort(key=lambda r: r['drv'])
        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                diff = sample[i]['cum_dist'] - sample[j]['cum_dist']
                if abs(diff) < hysteresis_m:
                    continue
                pair = (sample[i]['drv'], sample[j]['drv'])
                sign = 1 if diff > 0.0 else -1
                previous = settled.get(pair, sign)
                if previous != sign:
                    total += 1
                    if sample[i]['t_s'] > launch_s:
                        postlaunch += 1
                settled[pair] = sign
    return dict(total=total, post_launch=postlaunch)


def _metrics(run, track_length):
    rows = run['rows']
    laps, completed_laps, first_lap_rows = _lap_times(rows, track_length)
    windows = _rejoin_windows(rows)
    post_rejoin_contacts, post_rejoin_hesitations = _count_in_windows(rows, windows)
    carveout_active = 0
    if 'p_state' in run['fields']:
        for row in rows:
            if row.get('p_state') != 'DECISION_ACTIVE':
                continue
            if (row['t_s'] < 60.0 or row['offtrack'] > 0
                    or row.get('authority') in ('rejoin', 'recovery_rejoin') or any(
                    start <= row['t_s'] <= end for start, end in
                    windows.get(row['drv'], ()))):
                carveout_active += 1
    return dict(
        contacts=int(sum(r['car_car'] > 0 for r in rows)),
        hesitations=_hesitations(rows),
        offtrack_pct=100.0 * sum(r['offtrack'] > 0 for r in rows) / max(len(rows), 1),
        completed_laps=completed_laps,
        median_lap_s=statistics.median(laps) if laps else None,
        first_lap_contacts=int(sum(r['car_car'] > 0 for r in first_lap_rows)),
        first_lap_hesitations=_hesitations(first_lap_rows),
        post_rejoin_contacts=post_rejoin_contacts,
        post_rejoin_hesitations=post_rejoin_hesitations,
        rejoin_windows=sum(len(v) for v in windows.values()),
        carveout_active_samples=carveout_active,
        settled_swaps=_settled_swaps(rows),
    )


def _decision_stats(log_path):
    out = {}
    if not log_path:
        return out
    for line in Path(log_path).read_text(encoding='utf-8', errors='replace').splitlines():
        marker = '[pass-decision] '
        if not line.startswith(marker):
            continue
        driver, payload = line[len(marker):].split(': ', 1)
        out[driver] = ast.literal_eval(payload)
    return out


def _attempts_with_active(stats, run_end_s):
    attempts = []
    for driver_id, summary in stats.items():
        for attempt in summary.get('attempts', ()):
            attempts.append(dict(driver_id=driver_id, **attempt))
        active = summary.get('active_attempt')
        if active:
            attempts.append(dict(driver_id=driver_id, **active,
                                 end_s=run_end_s, outcome='active_at_end'))
    return attempts


def _events_during_attempts(csv_path, attempts):
    path = Path(csv_path).with_name(Path(csv_path).stem + '_events.csv')
    if not path.exists():
        return dict(path=None, sha256=None, size_bytes=None, matched_events=0,
                    event_count=0, matched=[],
                    evidence_complete=True,
                    evidence='runner emits this sidecar whenever solver events exist')
    blob = path.read_bytes()
    with path.open('r', newline='', encoding='utf-8') as f:
        lines = (line for line in f if line.strip() and not line.lstrip().startswith('#'))
        reader = csv.DictReader(lines)
        required = {'sub', 'drv_a', 'drv_b'}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path}: sidecar de contatos sem colunas {sorted(required)}")
        matched = []
        event_count = 0
        for row in reader:
            event_count += 1
            event_s = (int(row['sub']) // 24) * 0.1
            a, b = str(row['drv_a']), str(row['drv_b'])
            for attempt in attempts:
                if {a, b} != {str(attempt['driver_id']),
                              str(attempt['target_id'])}:
                    continue
                if float(attempt['start_s']) <= event_s <= float(attempt['end_s']):
                    matched.append(dict(sub=int(row['sub']), t_s=event_s,
                                        drv_a=a, drv_b=b,
                                        driver_id=attempt['driver_id'],
                                        target_id=attempt['target_id']))
    return dict(path=str(path), sha256=hashlib.sha256(blob).hexdigest(),
                size_bytes=len(blob), event_count=event_count,
                matched_events=len(matched),
                matched=matched, evidence_complete=True)


def _mixed_metrics(run, track_length):
    rows = run['rows']
    if 'grupo' not in run['fields']:
        raise ValueError(f"{run['path']}: R3 exige a coluna grupo")
    result = dict(total_contacts=int(sum(r['car_car'] > 0 for r in rows)), groups={})
    for group in ('professor', 'edge'):
        group_rows = [r for r in rows if r.get('grupo') == group]
        if not group_rows:
            raise ValueError(f"{run['path']}: grupo {group} ausente")
        _, completed, _ = _lap_times(group_rows, track_length)
        rolling = _rolling_lap_times(group_rows, track_length)
        result['groups'][group] = dict(
            cars=len({r['drv'] for r in group_rows}),
            contacts=int(sum(r['car_car'] > 0 for r in group_rows)),
            laps=completed,
            median_rolling_lap_s=(statistics.median(rolling)
                                  if rolling else None),
            hesitations=_mixed_hesitations(group_rows),
            offtrack_pct=100.0 * sum(r['offtrack'] > 0 for r in group_rows)
            / max(len(group_rows), 1),
        )
    return result


def _track_length(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    points = data.get('waypoints') or data.get('points')
    if not points:
        raise ValueError(f"geometria frozen sem waypoints: {path}")
    xy = [(float(p[0]), float(p[1])) for p in points]
    return sum(math.hypot(xy[(i + 1) % len(xy)][0] - x,
                          xy[(i + 1) % len(xy)][1] - y)
               for i, (x, y) in enumerate(xy))


def _audit(r1_path, r2_path, track_path, r1_log=None, r2_log=None,
           r3_path=None, r3_log=None):
    length = _track_length(track_path)
    track_blob = Path(track_path).read_bytes()
    r1 = _read_csv(r1_path, require_professor_state=True)
    r2 = _read_csv(r2_path, require_professor_state=True)
    m1, m2 = _metrics(r1, length), _metrics(r2, length)
    stats2 = _decision_stats(r2_log)
    stats2_sum = {key: sum(int(s.get(key, 0)) for s in stats2.values())
                   for key in ('opportunities', 'engaged', 'aborted_gap',
                               'aborted_timeout', 'aborted_contact',
                               'aborted_rejoin', 'aborted_target', 'consumed')}
    gates = {
        'g1_r1_rows': r1['data_rows'] == ROW_TARGET,
        'g1_r2_rows_and_schema': r2['data_rows'] == ROW_TARGET
                                 and r1['fields'] == r2['fields']
                                 and r1['header_line_sha256']
                                 == r2['header_line_sha256'],
        'g1_r2_decision_log_has_10_drivers': len(stats2) == 10,
        'g2_post_launch_settled_swaps_ge_5':
            m2['settled_swaps']['post_launch'] >= 5,
        'g3_contacts_le_r1_x_1_15': m2['contacts'] <= math.floor(m1['contacts'] * 1.15),
        'g3_hesitations_le_r1': m2['hesitations'] <= m1['hesitations'],
        'g3_offtrack_pct_le_r1': m2['offtrack_pct'] <= m1['offtrack_pct'],
        'g3_laps_ge_r1': m2['completed_laps'] >= m1['completed_laps'],
        'g3_median_lap_le_r1_plus_2pct':
            m2['median_lap_s'] is not None and m1['median_lap_s'] is not None
            and m2['median_lap_s'] <= m1['median_lap_s'] * 1.02,
        'g4_first_lap_contacts_zero': m2['first_lap_contacts'] == 0,
        'g4_first_lap_hesitations_zero': m2['first_lap_hesitations'] == 0,
        'g4_post_rejoin_contacts_le_r1':
            m2['post_rejoin_contacts'] <= m1['post_rejoin_contacts'],
        'g4_post_rejoin_hesitations_le_r1':
            m2['post_rejoin_hesitations'] <= m1['post_rejoin_hesitations'],
        'g5_no_decision_active_in_carveout': m2['carveout_active_samples'] == 0,
    }
    attempts2 = _attempts_with_active(
        stats2, max(r['t_s'] for r in r2['rows']) + 0.2)
    report = dict(version='1.0', track_length_m=length,
                  track_geometry=dict(path=str(track_path),
                      sha256=hashlib.sha256(track_blob).hexdigest(),
                      size_bytes=len(track_blob)),
                  logs={name: ({'path': str(path),
                      'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                      'size_bytes': Path(path).stat().st_size} if path else None)
                        for name, path in (('R1', r1_log), ('R2', r2_log),
                                           ('R3', r3_log))},
                  runs={'R1': {k: v for k, v in r1.items()
                               if k not in ('rows', 'by_driver')},
                        'R2': {k: v for k, v in r2.items()
                               if k not in ('rows', 'by_driver')}},
                  metrics={'R1': m1, 'R2': m2},
                  pass_decision_stats={'R2': stats2_sum},
                  pass_decision_attempts={'R2': attempts2}, gates=gates,
                  g2_pass_decision_consumed=stats2_sum['consumed'])
    if r3_path:
        r3 = _read_csv(r3_path)
        m3 = _mixed_metrics(r3, length)
        stats3 = _decision_stats(r3_log)
        attempts3 = _attempts_with_active(
            stats3, max(r['t_s'] for r in r3['rows']) + 0.2)
        events3 = _events_during_attempts(r3_path, attempts3)
        professor_stats = {d: s for d, s in stats3.items()
                           if d in {r['drv'] for r in r3['rows']
                                    if r.get('grupo') == 'professor'}}
        edge_pace_limit = 138.2 * 1.02
        r3_gates = {
            'g6_two_professor_cars': m3['groups']['professor']['cars'] == 2,
            'g6_eight_edge_cars': m3['groups']['edge']['cars'] == 8,
            'g6_total_contacts_le_published_84': m3['total_contacts'] <= 84,
            'g6_edge_rolling_pace_le_published_137_plus_2pct':
                m3['groups']['edge']['median_rolling_lap_s'] is not None
                and m3['groups']['edge']['median_rolling_lap_s'] <= edge_pace_limit,
            'g7_both_professors_engaged': len(professor_stats) == 2
                and all(int(s.get('engaged', 0)) > 0
                        for s in professor_stats.values()),
            'g7_no_solver_contact_on_attempt_pair':
                sum(int(s.get('aborted_contact', 0))
                    for s in professor_stats.values()) == 0
                and events3['matched_events'] == 0
                and events3['evidence_complete'],
            'g7_professor_hesitations_zero':
                m3['groups']['professor']['hesitations'] == 0,
        }
        report['runs']['R3'] = {k: v for k, v in r3.items()
                                if k not in ('rows', 'by_driver')}
        report['metrics']['R3'] = m3
        report['pass_decision_stats']['R3'] = professor_stats
        report['pass_decision_attempts'] = {'R3': attempts3}
        report['contact_events_R3'] = events3
        report['gates'].update(r3_gates)
    report['all_gates_pass'] = all(report['gates'].values())
    return report


def _selftest():
    # Synthetic-only checks: selftest never opens race CSVs.
    rows = [
        dict(tick=t, t_s=t * 0.2, drv='A', speed=(0.0 if 10 <= t <= 12 else 5.0),
             s=float(t), lat=0.0, car_car=0, offtrack=0,
             cum_dist=float(t), authority='professor', p_state='FOLLOW')
        for t in range(20)
    ]
    assert _hesitations(rows, after_s=-math.inf) == 1
    assert _settled_swaps([
        dict(tick=0, t_s=0.0, drv='A', cum_dist=20.0),
        dict(tick=0, t_s=0.0, drv='B', cum_dist=0.0),
        dict(tick=2, t_s=0.2, drv='A', cum_dist=0.0),
        dict(tick=2, t_s=0.2, drv='B', cum_dist=20.0),
    ]) == dict(total=1, post_launch=0)
    rejoin = _rejoin_windows([
        dict(t_s=0.0, drv='A', offtrack=0, authority='professor'),
        dict(t_s=1.0, drv='A', offtrack=1, authority='rejoin'),
        dict(t_s=2.0, drv='A', offtrack=0, authority='professor'),
    ])
    assert rejoin == {'A': [(2.0, 12.0)]}
    rolling = _rolling_lap_times([
        dict(t_s=0.0, drv='A', cum_dist=0.0),
        dict(t_s=4.0, drv='A', cum_dist=100.0),
        dict(t_s=8.0, drv='A', cum_dist=200.0),
        dict(t_s=12.0, drv='A', cum_dist=300.0),
    ], track_length=100.0)
    assert rolling == [4.0, 4.0]
    return 'PASS'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--r1')
    ap.add_argument('--r2')
    ap.add_argument('--r1-log')
    ap.add_argument('--r2-log')
    ap.add_argument('--r3')
    ap.add_argument('--r3-log')
    ap.add_argument('--track-json', default='model_train/tracks_frozen/interlagos_v2.json')
    ap.add_argument('--out')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        print(f"pass_decision_audit selftest: {_selftest()}")
        return 0
    if not args.r1 or not args.r2 or not args.r1_log or not args.r2_log or not args.out:
        ap.error('--r1, --r2, --r1-log, --r2-log e --out são obrigatórios fora de --selftest')
    if args.r3 and not args.r3_log:
        ap.error('--r3 exige --r3-log')
    report = _audit(args.r1, args.r2, args.track_json,
                    r1_log=args.r1_log, r2_log=args.r2_log,
                    r3_path=args.r3, r3_log=args.r3_log)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n',
                   encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
