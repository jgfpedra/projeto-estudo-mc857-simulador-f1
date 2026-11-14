"""Consulta o catálogo versionado de layouts F1DB sem presumir geometria."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / 'config' / 'f1db_layouts.json'
ALIASES = {'brazil':'interlagos', 'sao paulo':'interlagos', 'são paulo':'interlagos',
           'sao-paulo':'interlagos', 'são-paulo':'interlagos'}


def normalize(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def year_in_ranges(year, ranges):
    """Não preenche intervalos sem corrida entre os anos registrados."""
    for value in ranges or []:
        match = re.fullmatch(r'\s*(\d{4})(?:\s*[-–]\s*(\d{4}))?\s*', str(value))
        if match:
            first, last = int(match.group(1)), int(match.group(2) or match.group(1))
            if first <= year <= last:
                return True
    return False


class LayoutCatalog:
    def __init__(self, data):
        self.data = data
        self.circuits = data.get('circuits', [])

    def find_circuit(self, name):
        name = ALIASES.get(str(name or '').strip().lower(), name)
        wanted = normalize(name)
        matches = [c for c in self.circuits if wanted and wanted in {
            normalize(c.get('id')), normalize(c.get('name')),
            normalize(c.get('full_name')), normalize(c.get('city'))}]
        return matches[0] if len(matches) == 1 else None

    def find_layout(self, circuit, season):
        matches = [layout for layout in circuit.get('layouts', [])
                   if year_in_ranges(season, layout.get('years'))]
        return matches[0] if len(matches) == 1 else None

    @property
    def provenance(self):
        return {key:self.data.get(key) for key in ('source','source_url','license',
                'license_url','generated_at','catalog_commit','f1db_release','source_db_sha256')}


@lru_cache(maxsize=4)
def load_layout_catalog(path=None):
    path = Path(path or os.environ.get('F1DB_LAYOUTS_PATH') or DEFAULT_PATH)
    with path.open(encoding='utf-8') as stream:
        data = json.load(stream)
    if not isinstance(data.get('circuits'), list):
        raise ValueError('Catálogo F1DB inválido: circuits ausente')
    return LayoutCatalog(data)
