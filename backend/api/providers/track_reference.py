"""Escolha auditável de um ano de referência para um layout F1DB explícito."""
from __future__ import annotations

from .historical_f1results import load_historical_snapshot

# Pistas locais derivadas de telemetria e validadas para a corrida ao vivo.
_FROZEN_REFERENCE_YEARS = {'interlagos': 2023, 'monza': 2024}


def candidate_reference_years(catalog, circuit, layout, excluded=()):
    """Anos conhecidos do mesmo layout, sem presumir corridas nos intervalos.

    Os snapshots locais têm precedência por oferecerem fallback offline; anos
    modernos restantes podem ser tentados pelos providers online. A lista é
    limitada para evitar uma sequência longa de requisições em caso de falha.
    """
    circuit_id, layout_id = circuit['id'], layout['id']
    def matches(year):
        found = catalog.find_layout(circuit, year)
        return found is not None and found['id'] == layout_id
    known = set()
    snapshot = load_historical_snapshot()
    for key in snapshot['races']:
        key_circuit, year_text = key.rsplit(':', 1)
        if key_circuit == circuit_id and year_text.isdigit():
            year = int(year_text)
            if matches(year):
                known.add(year)
    frozen = _FROZEN_REFERENCE_YEARS.get(circuit_id)
    candidates = []
    if frozen is not None and matches(frozen):
        candidates.append(frozen)
    candidates.extend(sorted(known, reverse=True))
    candidates.extend(year for year in (2025, 2024, 2023, 2022, 2021, 2019, 2018) if matches(year))
    excluded = set(excluded)
    ordered = []
    for year in candidates:
        if year not in excluded and year not in ordered:
            ordered.append(year)
    return ordered[:3]
