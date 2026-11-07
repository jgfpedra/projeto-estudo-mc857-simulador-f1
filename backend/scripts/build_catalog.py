"""Gera ``backend/data/catalog.json``: o catálogo que a API serve ao front.

Fonte: F1DB (mesma base usada por ``fetch_track_layouts.py``). O catálogo é um
JSON leve, para a API não depender do ``f1db.db`` (~70 MB) em tempo de execução.

Conteúdo:
- ``circuits``: um item por circuito, com país (nome + código ISO alpha-2 para a
  bandeira), cidade, SVG e as variações de traçado ("layouts") com anos de uso.
  Cada layout leva ``simulable`` e, quando simulável, a referência
  ``fastf1 = {year, round}`` da corrida mais recente (com resultado) que usou
  aquele traçado — é com ela que o backend carrega a pista no FastF1.
- ``seasons``: por temporada, os pilotos titulares (sem pilotos de teste) com
  número do carro, equipe e país.

Uso (de dentro de ``backend/``; precisa de internet na 1ª vez para baixar o F1DB)::

    python scripts/build_catalog.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reaproveita o extrator de circuitos/layouts/SVG já existente.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_track_layouts import (  # noqa: E402
    TrackLayoutExtractor,
    extract_layout_number,
    find_database_path,
)

logger = logging.getLogger("build_catalog")

# O FastF1 só tem dados (e ``get_circuit_info``) a partir de 2018. Traçados que
# não foram usados desde então não conseguem ser carregados pelo motor.
FASTF1_MIN_YEAR = 2018

CATALOG_VERSION = 1


# ---------------------------------------------------------------------------
# Circuitos
# ---------------------------------------------------------------------------

def _fastf1_refs(conn: sqlite3.Connection, min_year: int) -> Dict[str, Tuple[int, int]]:
    """layout_id -> (ano, rodada) da corrida mais recente COM RESULTADO.

    O F1DB já traz o calendário de corridas futuras; elas não têm dados no
    FastF1, então só valem corridas com ``RACE_RESULT``.
    """
    rows = conn.execute(
        """
        SELECT r.circuit_layout_id AS layout_id, r.year AS year, r.round AS round
        FROM race r
        WHERE r.year >= ?
          AND r.circuit_layout_id IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM race_data rd
              WHERE rd.race_id = r.id AND rd.type = 'RACE_RESULT'
          )
        ORDER BY r.circuit_layout_id, r.year, r.round
        """,
        (min_year,),
    ).fetchall()
    refs: Dict[str, Tuple[int, int]] = {}
    for layout_id, year, rnd in rows:
        refs[layout_id] = (int(year), int(rnd))  # o último (maior ano) vence
    return refs


def build_circuits(db_path: Path, min_year: int = FASTF1_MIN_YEAR) -> List[Dict[str, Any]]:
    evolution = TrackLayoutExtractor(db_path).extract_evolution()
    conn = sqlite3.connect(str(db_path))
    try:
        refs = _fastf1_refs(conn, min_year)
    finally:
        conn.close()

    circuits: List[Dict[str, Any]] = []
    for c in evolution["circuits"]:
        layouts: List[Dict[str, Any]] = []
        for lay in c["layouts"]:
            ref = refs.get(lay["id"])
            layouts.append({
                "id": lay["id"],
                "years": lay["year_ranges"],
                "first_year": lay["first_year"],
                "last_year": lay["last_year"],
                "length_km": lay["length"],
                "turns": lay["turns"],
                "svg": lay["svg"],
                "simulable": ref is not None,
                "fastf1": {"year": ref[0], "round": ref[1]} if ref else None,
            })

        # Traçado atual = o usado por último; empate -> maior número do id.
        current: Optional[Dict[str, Any]] = None
        if layouts:
            current = max(
                layouts,
                key=lambda l: (
                    l["last_year"] if l["last_year"] is not None else -1,
                    extract_layout_number(l["id"]),
                ),
            )
        for lay in layouts:
            lay["is_current"] = lay is current

        country = c["country"] or {}
        circuits.append({
            "id": c["id"],
            "name": c["name"],
            "full_name": c["full_name"],
            "city": c["place_name"],
            "country": {"name": country.get("name"), "code": country.get("alpha2_code")},
            "svg": current["svg"] if current else None,
            "current_layout_id": current["id"] if current else None,
            "simulable": any(l["simulable"] for l in layouts),
            "layouts": layouts,
        })

    circuits.sort(key=lambda c: (c["name"] or c["id"]).lower())
    return circuits


# ---------------------------------------------------------------------------
# Pilotos por temporada
# ---------------------------------------------------------------------------

def _as_number(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def build_seasons(db_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # Número do carro NAQUELA temporada = o mais usado nos resultados de
        # corrida (o ``permanent_number`` do piloto só existe a partir de 2014 e
        # não reflete o #1 do campeão).
        numbers: Dict[Tuple[int, str], Tuple[int, int]] = {}
        for r in conn.execute(
            """
            SELECT r.year AS year, rd.driver_id AS driver_id,
                   rd.driver_number AS number, COUNT(*) AS n
            FROM race_data rd JOIN race r ON r.id = rd.race_id
            WHERE rd.type = 'RACE_RESULT' AND rd.driver_number IS NOT NULL
            GROUP BY r.year, rd.driver_id, rd.driver_number
            """
        ):
            num = _as_number(r["number"])
            key = (r["year"], r["driver_id"])
            if num is not None and (key not in numbers or r["n"] > numbers[key][1]):
                numbers[key] = (num, r["n"])

        # Corridas por (temporada, piloto, equipe): decide a equipe principal de
        # quem trocou de carro no meio do ano.
        starts: Dict[Tuple[int, str, str], int] = {}
        for r in conn.execute(
            """
            SELECT r.year AS year, rd.driver_id AS driver_id,
                   rd.constructor_id AS constructor_id, COUNT(*) AS n
            FROM race_data rd JOIN race r ON r.id = rd.race_id
            WHERE rd.type = 'RACE_RESULT'
            GROUP BY r.year, rd.driver_id, rd.constructor_id
            """
        ):
            starts[(r["year"], r["driver_id"], r["constructor_id"])] = r["n"]

        rows = conn.execute(
            """
            SELECT sed.year AS year, d.id AS id, d.name AS name,
                   d.abbreviation AS abbreviation, d.permanent_number AS permanent_number,
                   c.id AS team_id, c.name AS team,
                   co.name AS country_name, co.alpha2_code AS country_code
            FROM season_entrant_driver sed
            JOIN driver d ON d.id = sed.driver_id
            JOIN constructor c ON c.id = sed.constructor_id
            LEFT JOIN country co ON co.id = d.nationality_country_id
            WHERE sed.test_driver = 0
            ORDER BY sed.year, c.name, d.name
            """
        ).fetchall()
    finally:
        conn.close()

    # (ano, piloto) -> melhor linha (equipe com mais corridas)
    best: Dict[Tuple[int, str], sqlite3.Row] = {}
    for r in rows:
        key = (r["year"], r["id"])
        if key not in best:
            best[key] = r
            continue
        cur = best[key]
        if starts.get((r["year"], r["id"], r["team_id"]), 0) > starts.get(
            (cur["year"], cur["id"], cur["team_id"]), 0
        ):
            best[key] = r

    seasons: Dict[str, List[Dict[str, Any]]] = {}
    for (year, driver_id), r in best.items():
        number = numbers.get((year, driver_id), (None, 0))[0]
        if number is None:
            number = _as_number(r["permanent_number"])
        seasons.setdefault(str(year), []).append({
            "id": driver_id,
            "name": r["name"],
            "abbreviation": r["abbreviation"],
            "number": number,
            "team": r["team"],
            "team_id": r["team_id"],
            "country": {"name": r["country_name"], "code": r["country_code"]},
        })

    for drivers in seasons.values():
        drivers.sort(key=lambda d: (d["team"] or "", d["number"] if d["number"] is not None else 999, d["name"] or ""))
    return dict(sorted(seasons.items()))


# ---------------------------------------------------------------------------
# Montagem / CLI
# ---------------------------------------------------------------------------

def build_catalog(db_path: Path, min_year: int = FASTF1_MIN_YEAR) -> Dict[str, Any]:
    circuits = build_circuits(db_path, min_year)
    seasons = build_seasons(db_path)
    return {
        "version": CATALOG_VERSION,
        "source": "F1DB (Formula 1 Database)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fastf1_min_year": min_year,
        "circuits": circuits,
        "seasons": seasons,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description="Gera o catálogo (circuitos + pilotos por temporada) a partir do F1DB.")
    parser.add_argument("--db-path", default=None, help="Caminho do f1db.db (baixa automaticamente se omitido).")
    parser.add_argument("--output-json", default=None, help="Saída. Padrão: backend/data/catalog.json")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent.parent
    output = Path(args.output_json) if args.output_json else backend_dir / "data" / "catalog.json"

    db_path = find_database_path(args.db_path)
    logger.info("Usando F1DB em %s", db_path)
    catalog = build_catalog(db_path)

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))

    n_sim = sum(1 for c in catalog["circuits"] if c["simulable"])
    logger.info(
        "Catálogo salvo em %s (%.0f KB): %d circuitos (%d simuláveis), %d temporadas.",
        output, output.stat().st_size / 1024, len(catalog["circuits"]), n_sim, len(catalog["seasons"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
