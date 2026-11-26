"""PostgreSQL access and idempotent bootstrap of the bundled catalog snapshots."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Immutable commit: the built-in snapshots are preferred and the URLs are used
# only when the matching bundled snapshot is absent.
SNAPSHOT_COMMIT = '587c3b8'
SNAPSHOT_SHA256 = {
    'config/f1db_layouts.json': '6a64738fc5f0df2e23dd5fe56f17dd2307fa0ac0cf30f5147820bcfc86e2e918',
    'config/historical_tracks/f1results_rosters.json': '3a8ce1015ea1beed17d82d7bed29fb4b06698267b9ef7f8ad41fd20ec36483c5',
    'config/historical_tracks/f1results_tracks.json': '030dcddc8805e712ab88785cd07a73509ac4327dcc4a0f79dcbb46ab6fc325e1',
}
SNAPSHOTS = {
    'f1db_layouts': ('config/f1db_layouts.json', ('circuits',)),
    'f1results_rosters': ('config/historical_tracks/f1results_rosters.json', ('drivers', 'events')),
    'f1results_tracks': ('config/historical_tracks/f1results_tracks.json', ('geometries', 'races')),
}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS schema_migrations (version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
INSERT INTO schema_migrations (version) VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS catalog_snapshots (
    name text PRIMARY KEY, payload jsonb NOT NULL, sha256 text NOT NULL,
    provenance jsonb NOT NULL, imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS catalog_svg (
    layout_id text NOT NULL, style text NOT NULL, source_url text NOT NULL,
    svg text NOT NULL, sha256 text NOT NULL, imported_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(layout_id, style)
);
CREATE TABLE IF NOT EXISTS catalog_season_drivers (
    season integer PRIMARY KEY, drivers jsonb NOT NULL
);
'''


def configured():
    return bool(os.environ.get('DATABASE_URL'))


def connect():
    import psycopg
    from psycopg.rows import dict_row
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL não configurada')
    return psycopg.connect(url, connect_timeout=5, row_factory=dict_row)


def _read_snapshot(relative, required):
    path = ROOT / relative
    if path.is_file():
        raw = path.read_bytes()
    else:
        url = f'https://raw.githubusercontent.com/jgfpedra/projeto-estudo-mc857-simulador-f1/{SNAPSHOT_COMMIT}/backend/{relative}'
        with urllib.request.urlopen(url, timeout=20) as response:
            raw = response.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError('Snapshot excede o limite')
        if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA256.get(relative):
            raise ValueError(f'Hash do snapshot baixado não confere: {relative}')
    data = json.loads(raw)
    if not isinstance(data, dict) or any(key not in data for key in required):
        raise ValueError(f'Snapshot inválido: {relative}')
    return data, hashlib.sha256(raw).hexdigest()


def bootstrap():
    """Create schema and import missing snapshots under a DB transaction lock."""
    from psycopg.types.json import Jsonb
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(%s)', (73021488,))
        conn.execute(SCHEMA)
        existing = {row['name'] for row in conn.execute('SELECT name FROM catalog_snapshots')}
        for name, (relative, required) in SNAPSHOTS.items():
            if name in existing:
                continue
            data, digest = _read_snapshot(relative, required)
            provenance = {key: data.get(key) for key in ('source', 'source_url', 'license', 'release', 'db_sha256', 'generated_at')}
            conn.execute('INSERT INTO catalog_snapshots (name,payload,sha256,provenance) VALUES (%s,%s,%s,%s)',
                         (name, Jsonb(data), digest, Jsonb(provenance)))
        if conn.execute('SELECT season FROM catalog_season_drivers LIMIT 1').fetchone() is None:
            from database.f1results_database import F1ResultsDriverDatabase
            row = conn.execute("SELECT payload FROM catalog_snapshots WHERE name='f1results_rosters'").fetchone()
            catalog = F1ResultsDriverDatabase(data=row['payload'])
            for season in catalog.get_available_seasons():
                conn.execute('INSERT INTO catalog_season_drivers (season, drivers) VALUES (%s,%s)',
                             (season, Jsonb(catalog.load_season_drivers(season))))


def catalog(name):
    with connect() as conn:
        row = conn.execute('SELECT payload FROM catalog_snapshots WHERE name=%s', (name,)).fetchone()
    if row is None:
        raise RuntimeError(f'Catálogo {name} não foi inicializado')
    return row['payload']



def season_drivers(season):
    with connect() as conn:
        row = conn.execute('SELECT drivers FROM catalog_season_drivers WHERE season=%s', (season,)).fetchone()
    return row['drivers'] if row else []


if __name__ == '__main__' and configured():
    bootstrap()
