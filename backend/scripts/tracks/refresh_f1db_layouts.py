#!/usr/bin/env python3
"""Atualiza o catálogo leve de layouts a partir do SQLite oficial do F1DB."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts.tracks.fetch_track_layouts import TrackLayoutExtractor


def convert(evolution, db_sha256, release=None):
    circuits = []
    for circuit in evolution['circuits']:
        country = circuit.get('country') or {}
        layouts = [
            {'id': item['id'], 'years': item.get('year_ranges', []),
             'first_year': item.get('first_year'), 'last_year': item.get('last_year'),
             'length_km': item.get('length'), 'turns': item.get('turns'),
             'svg': item.get('svg', {})}
            for item in circuit.get('layouts', [])
        ]
        circuits.append({'id': circuit['id'], 'name': circuit['name'],
                         'full_name': circuit['full_name'], 'city': circuit.get('place_name'),
                         'country': {'name': country.get('name'), 'code': country.get('alpha2_code')},
                         'layouts': layouts})
    return {'source':'F1DB (Formula 1 Database)', 'source_url':'https://github.com/f1db/f1db',
            'license':'CC-BY-4.0', 'license_url':'https://creativecommons.org/licenses/by/4.0/',
            'generated_at':evolution.get('generated_at'), 'catalog_commit':None,
            'f1db_release':release, 'source_db_sha256':db_sha256, 'circuits':circuits}


def find_changes(previous, current):
    """Compara layouts e anos de uso, ignorando metadados da extração."""
    def entries(catalog):
        return {(c['id'], layout['id']): layout for c in catalog['circuits']
                for layout in c.get('layouts', [])}

    before, after = entries(previous), entries(current)
    changes = []
    for key in sorted(before.keys() | after.keys()):
        if key not in before:
            kind = 'adicionado'
        elif key not in after:
            kind = 'removido'
        elif any(before[key].get(field) != after[key].get(field)
                 for field in ('years', 'length_km', 'turns')):
            kind = 'alterado'
        else:
            continue
        changes.append({'circuit_id': key[0], 'layout_id': key[1], 'change': kind})
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db-path', type=Path, required=True, help='SQLite obtido de uma release oficial do F1DB')
    parser.add_argument('--f1db-release', help='Identificador da release, por exemplo v2026.20.0')
    parser.add_argument('--output', type=Path, default=BACKEND / 'config' / 'f1db_layouts.json')
    parser.add_argument('--check', action='store_true', help='comparar com o catálogo existente sem alterá-lo')
    args = parser.parse_args()
    if not args.db_path.is_file():
        parser.error(f'SQLite não encontrado: {args.db_path}')
    with args.db_path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    data = convert(TrackLayoutExtractor(args.db_path).extract_evolution(), digest, args.f1db_release)
    if args.output.exists():
        previous = json.loads(args.output.read_text(encoding='utf-8'))
        changes = find_changes(previous, data)
        for change in changes:
            print(f"{change['circuit_id']}: {change['layout_id']} {change['change']}")
        print(f'{len(changes)} alteração(ões) de layout ou anos de uso')
        if args.check:
            return 1 if changes else 0
    elif args.check:
        parser.error(f'Catálogo para comparação não encontrado: {args.output}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f"{len(data['circuits'])} circuitos; catálogo gravado em {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
