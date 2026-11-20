#!/usr/bin/env python3
"""Exporta pilotos e eventos do F1 Results Database para catálogo local compacto."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from f1results_mapping import find_circuit, year_in_ranges


def file_sha256(path):
    result = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def build(db_path, f1db_path, layouts_path, release):
    circuits = json.loads(Path(f1db_path).read_text(encoding='utf-8'))['circuits']
    layouts = {c['id']: c.get('layouts', []) for c in json.loads(Path(layouts_path).read_text(encoding='utf-8'))['circuits']}
    conn = sqlite3.connect(f'file:{Path(db_path).resolve()}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    race_years = {}
    for row in conn.execute('SELECT CircuitLayoutID, Season FROM GrandsPrix WHERE CircuitLayoutID IS NOT NULL'):
        race_years.setdefault(row['CircuitLayoutID'], set()).add(row['Season'])
    mapping = {}
    for row in conn.execute('SELECT ID, Latitude, Longitude FROM CircuitLayouts ORDER BY ID'):
        mapping[row['ID']] = find_circuit(row['Latitude'], row['Longitude'], circuits, layouts,
                                          race_years.get(row['ID'], set()))
    drivers = {}
    for row in conn.execute('SELECT ID, Name, Nationality FROM Drivers ORDER BY ID'):
        if row['Name']:
            drivers[str(row['ID'])] = {'name': row['Name'], 'nationality': row['Nationality']}
    events = []
    rows = conn.execute('''SELECT ID, Season, RoundNumber, GrandPrixName, CircuitName,
                           CircuitLayoutID, CircuitLength FROM GrandsPrix ORDER BY Season, RoundNumber, ID''')
    for row in rows:
        cid = mapping.get(row['CircuitLayoutID'])
        valid = [v for v in layouts.get(cid, []) if year_in_ranges(row['Season'], v.get('years'))]
        if len(valid) != 1:
            cid = None
        entries = []
        for result in conn.execute('''SELECT driverid, number, team, starting_grid_position
            FROM GrandPrixResults WHERE grandprixid=? ORDER BY
            CASE WHEN starting_grid_position IS NULL THEN 1 ELSE 0 END,
            starting_grid_position, driverid''', (row['ID'],)):
            if str(result['driverid']) in drivers:
                entries.append([result['driverid'], result['number'], result['team'], result['starting_grid_position']])
        events.append({'id': row['ID'], 'season': row['Season'], 'round': row['RoundNumber'],
                       'grand_prix': row['GrandPrixName'], 'circuit_id': cid,
                       'source_circuit_name': row['CircuitName'], 'source_layout_id': row['CircuitLayoutID'],
                       'circuit_length': row['CircuitLength'], 'entries': entries})
    return {'source': 'F1 Results Database', 'source_url': 'https://github.com/mclarenmp4-22/f1resultsdatabase',
            'license': 'ODbL-1.0', 'release': release, 'db_sha256': file_sha256(db_path),
            'f1db_catalog_sha256': file_sha256(f1db_path), 'f1db_layouts_sha256': file_sha256(layouts_path),
            'drivers': drivers, 'events': events}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True)
    p.add_argument('--f1db-catalog', required=True)
    p.add_argument('--f1db-layouts', required=True)
    p.add_argument('--release', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    data = build(args.db, args.f1db_catalog, args.f1db_layouts, args.release)
    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    print('pilotos:', len(data['drivers']), 'eventos:', len(data['events']),
          'eventos sem vínculo F1DB:', sum(1 for e in data['events'] if e['circuit_id'] is None))


if __name__ == '__main__':
    main()
