#!/usr/bin/env python3
"""PASS-PARITY-1 offline audit; reads frozen CSV/log inputs, never simulates."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from pathlib import Path


REQUIRED = {
    'tick', 't_s', 'drv', 'speed', 's', 'lat', 'car_car', 'offtrack',
    'cum_dist', 'authority', 'p_state', 'body_x', 'body_y', 'ns_raw',
}
EXPECTED_ROWS = 30_000
EXPECTED_DRIVERS = 10
SAMPLES_PER_DRIVER = 3_000
EXPECTED_FIELDS = 54


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _load_csv(path):
    path = Path(path)
    blob = path.read_bytes()
    lines = blob.splitlines(keepends=True)
    header_index = next((i for i, line in enumerate(lines)
                         if line.strip() and not line.lstrip().startswith(b'#')),
                        None)
    if header_index is None:
        raise ValueError(f'CSV sem header: {path}')
    header_line_bytes = lines[header_index]
    header_line = header_line_bytes.decode('utf-8')
    data_lines = [(i, line) for i, line in enumerate(lines[header_index + 1:],
                                                        start=header_index + 1)
                  if line.strip()]
    reader = csv.DictReader(io.StringIO(header_line + ''.join(
        line.decode('utf-8') for _, line in data_lines)))
    fields = list(reader.fieldnames or ())
    if len(fields) != EXPECTED_FIELDS:
        raise ValueError(
            f'{path}: esperadas {EXPECTED_FIELDS} colunas, recebidas {len(fields)}')
    missing = REQUIRED - set(fields)
    if missing:
        raise ValueError(f'{path}: colunas ausentes: {sorted(missing)}')
    parsed = list(reader)
    if len(parsed) != EXPECTED_ROWS:
        raise ValueError(
            f'{path}: esperadas {EXPECTED_ROWS} linhas, recebidas {len(parsed)}')
    if len(parsed) != len(data_lines):
        raise ValueError(f'{path}: linhas CSV não têm mapeamento byte-a-byte')
    rows = []
    for row, (line_number, raw_line) in zip(parsed, data_lines):
        try:
            rows.append({
                **row,
                '_line_number': line_number + 1,
                '_raw_line': raw_line,
                'tick': int(row['tick']), 't_s': float(row['t_s']),
                'drv': str(row['drv']), 'speed': float(row['speed']),
                's': float(row['s']), 'lat': float(row['lat']),
                'offtrack': int(float(row['offtrack'])),
                'body_x': float(row['body_x']),
                'body_y': float(row['body_y']),
                'ns_raw': int(float(row['ns_raw'])),
            })
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f'{path}: registro inválido na linha {line_number + 1}') from exc
        numeric = (rows[-1]['t_s'], rows[-1]['speed'], rows[-1]['s'],
                   rows[-1]['lat'], rows[-1]['body_x'], rows[-1]['body_y'])
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError(f'{path}: valor não finito na linha {line_number + 1}')
        if abs(rows[-1]['t_s'] - rows[-1]['tick'] * 0.1) > 1e-9:
            raise ValueError(
                f'{path}: t_s não corresponde a tick na linha {line_number + 1}')
    by_key = {}
    by_driver = defaultdict(list)
    for row in rows:
        key = (row['tick'], row['drv'])
        if key in by_key:
            raise ValueError(f'{path}: chave duplicada {key}')
        by_key[key] = row
        by_driver[row['drv']].append(row)
    if len(by_driver) != EXPECTED_DRIVERS:
        raise ValueError(f'{path}: esperados {EXPECTED_DRIVERS} pilotos')
    for drv, samples in by_driver.items():
        samples.sort(key=lambda item: item['tick'])
        ticks = [item['tick'] for item in samples]
        if (len(ticks) != SAMPLES_PER_DRIVER or ticks[0] != 0
                or ticks[-1] != 5998
                or any(b - a != 2 for a, b in zip(ticks, ticks[1:]))):
            raise ValueError(f'{path}: grade/tamanho inválidos para {drv}')
    return dict(
        path=str(path), sha256=_sha256(path), size_bytes=path.stat().st_size,
        header_line=header_line_bytes, fields=fields, rows=rows, by_key=by_key,
        by_driver=dict(by_driver))


def _parse_pass_decision_log(path):
    records = {}
    for line_number, line in enumerate(Path(path).read_text(
            encoding='utf-8').splitlines(), start=1):
        prefix = '[pass-decision] '
        if not line.startswith(prefix):
            continue
        try:
            driver, payload = line[len(prefix):].split(': ', 1)
            stats = ast.literal_eval(payload)
        except (ValueError, SyntaxError) as exc:
            raise ValueError(f'linha [pass-decision] inválida: {line_number}') from exc
        if driver in records or not isinstance(stats, dict):
            raise ValueError(f'registro [pass-decision] duplicado/inválido: {driver}')
        records[driver] = stats
    if not records:
        raise ValueError('log sem resumo [pass-decision]')
    if len(records) != EXPECTED_DRIVERS:
        raise ValueError(
            f'log: esperados {EXPECTED_DRIVERS} resumos [pass-decision], '
            f'recebidos {len(records)}')
    return records


def _active_rows(rows):
    return [row for row in rows if row['p_state'] == 'DECISION_ACTIVE']


def _rejoin_until_by_driver(by_driver, hold_s=10.0):
    """Return samples through 10 s after each contiguous offtrack/rejoin run."""
    windows = defaultdict(list)
    for driver, samples in by_driver.items():
        ordered = sorted(samples, key=lambda row: row['t_s'])
        inside = False
        for row in ordered:
            in_rejoin = (bool(row['offtrack']) or row['authority'] in
                         ('rejoin', 'recovery_rejoin'))
            if not in_rejoin and inside:
                windows[driver].append((start, previous_t + hold_s))
            if in_rejoin:
                if not inside:
                    start = float(row['t_s'])
                previous_t = float(row['t_s'])
            inside = in_rejoin
        if inside:
            windows[driver].append((start, previous_t + hold_s))
    return windows


def _carveout_violations(rows, by_driver):
    rejoin_windows = _rejoin_until_by_driver(by_driver)
    violations = []
    for row in _active_rows(rows):
        reasons = []
        if row['t_s'] < 60.0:
            reasons.append('launch_t_lt_60')
        if row['offtrack'] or row['authority'] in ('rejoin', 'recovery_rejoin'):
            reasons.append('offtrack_or_rejoin')
        if any(start <= row['t_s'] <= end
               for start, end in rejoin_windows.get(row['drv'], ())):
            reasons.append('post_rejoin_10s')
        if reasons:
            violations.append(dict(tick=row['tick'], t_s=row['t_s'],
                                   drv=row['drv'], reasons=reasons))
    return violations


def _attempts_from_stats(stats_by_driver):
    attempts = []
    engaged = 0
    for driver, stats in stats_by_driver.items():
        engaged += int(stats.get('engaged', 0))
        for item in stats.get('attempts', []):
            attempts.append(dict(driver=driver, **item))
        active = stats.get('active_attempt')
        if active:
            attempts.append(dict(driver=driver, **active, outcome='active_at_finish'))
    return engaged, attempts


def audit(r1_path, r2_path, log_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    pin = manifest['inputs']['r1_csv']['sha256']
    r1 = _load_csv(r1_path)
    r2 = _load_csv(r2_path)
    if r1['sha256'] != pin:
        raise ValueError('R1 diverge do SHA-256 congelado no manifest')
    if r1['fields'] != r2['fields'] or r1['header_line'] != r2['header_line']:
        raise ValueError('headers/schema R1 e R2\' não são byte-idênticos')

    active = _active_rows(r2['rows'])
    if not active:
        raise ValueError('R2\' sem amostra DECISION_ACTIVE: não há t*')
    first_active = min(active, key=lambda row: (row['tick'], row['drv']))
    t_star = float(first_active['t_s'])
    if t_star < 60.0:
        raise ValueError(f't* < 60 s: {t_star}')

    keys = sorted(r1['by_key'], key=lambda key: (key[0], key[1]))
    if set(keys) != set(r2['by_key']):
        raise ValueError('chaves (tick, piloto) R1/R2\' divergentes')
    pre_star = []
    first_difference = None
    for key in keys:
        a, b = r1['by_key'][key], r2['by_key'][key]
        if a['_raw_line'] != b['_raw_line']:
            if first_difference is None:
                first_difference = dict(
                    tick=key[0], t_s=b['t_s'], drv=key[1],
                    r2_p_state=b['p_state'])
            if b['t_s'] < t_star:
                pre_star.append(dict(tick=key[0], t_s=b['t_s'], drv=key[1]))
    g2_pass = not pre_star
    active_on_t_star = any(
        row['p_state'] == 'DECISION_ACTIVE'
        and abs(float(row['t_s']) - t_star) <= 1e-9 for row in r2['rows'])
    first_diff_at_engage = bool(
        first_difference is not None
        and abs(float(first_difference['t_s']) - t_star) <= 1e-9
        and active_on_t_star)
    # At t* the p_state transition itself must make the first changed row.
    g2_pass = g2_pass and first_diff_at_engage

    stats = _parse_pass_decision_log(log_path)
    engaged_count, attempts = _attempts_from_stats(stats)
    if not attempts:
        attempt_starts = []
    else:
        attempt_starts = [float(item['start_s']) for item in attempts]
    active_t = min(float(row['t_s']) for row in active)
    start_matches = bool(attempt_starts and abs(min(attempt_starts) - active_t) <= 1e-9)
    attempts_match_engaged = len(attempts) == engaged_count
    attempts_after_launch = bool(attempt_starts) and all(
        start_s >= 60.0 for start_s in attempt_starts)
    carveout = _carveout_violations(r2['rows'], r2['by_driver'])
    g3_pass = bool(engaged_count > 0 and attempts and attempts_match_engaged
                   and attempts_after_launch and start_matches and not carveout)
    return {
        'schema': {
            'r1_rows': len(r1['rows']), 'r2_rows': len(r2['rows']),
            'r1_fields': len(r1['fields']), 'r2_fields': len(r2['fields']),
            'r1_sha256': r1['sha256'], 'r2_sha256': r2['sha256'],
            'r2_log_sha256': _sha256(log_path),
        },
        't_star_s': t_star,
        'first_difference': first_difference,
        'pre_t_star_differences': pre_star,
        'decision': {
            'engaged_total': engaged_count, 'attempt_count': len(attempts),
            'attempts': attempts, 'log_start_matches_csv_t_star': start_matches,
            'attempts_match_engaged_count': attempts_match_engaged,
            'all_attempts_start_at_or_after_60_s': attempts_after_launch,
            'carveout_violations': carveout,
        },
        'gates': {
            'g2_pre_engagement_row_identity': 'PASS' if g2_pass else 'FAIL',
            'g3_decision_operates_and_respects_carveouts':
                'PASS' if g3_pass else 'FAIL',
        },
        'all_gates_pass': bool(g2_pass and g3_pass),
    }


def _selftest():
    # Synthetic checks only; intentionally does not open race CSVs.
    rows = [dict(tick=i * 2, t_s=i * 0.2, drv='EGO', p_state='FOLLOW',
                 offtrack=0, authority='?') for i in range(4)]
    assert not _active_rows(rows)
    windows = _rejoin_until_by_driver({'EGO': [
        dict(t_s=1.0, offtrack=1, authority='?'),
        dict(t_s=1.2, offtrack=0, authority='?'),
    ]})
    assert windows['EGO'] == [(1.0, 11.0)]
    stats = {'LEC': dict(engaged=1, attempts=[dict(
        target_id='PIA', start_s=62.8, end_s=70.8, outcome='abort_timeout')],
        active_attempt=None)}
    engaged, attempts = _attempts_from_stats(stats)
    assert engaged == 1 and attempts[0]['start_s'] == 62.8
    print('PASS: synthetic audit helpers; no race CSV opened')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--r1', type=Path)
    parser.add_argument('--r2', type=Path)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        _selftest()
        return 0
    required = (args.r1, args.r2, args.log, args.manifest, args.output)
    if any(value is None for value in required):
        parser.error('--r1/--r2/--log/--manifest/--output são obrigatórios')
    if args.output.exists():
        parser.error(f'saída já existe; não sobrescrever: {args.output}')
    result = audit(args.r1, args.r2, args.log, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({
        't_star_s': result['t_star_s'],
        'gates': result['gates'],
        'all_gates_pass': result['all_gates_pass'],
        'output': str(args.output),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if result['all_gates_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
