"""Catálogo estático servido ao front (circuitos, traçados e pilotos por temporada).

Os dados vêm de ``backend/data/catalog.json``, gerado por
``scripts/build_catalog.py`` a partir do F1DB. A API só lê esse JSON — não
depende do ``f1db.db`` em tempo de execução.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
CATALOG_ENV_VAR = "F1_CATALOG_PATH"


class CatalogUnavailable(RuntimeError):
    """O catalog.json não existe (ou está ilegível)."""


class CatalogLookupError(ValueError):
    """Circuito, traçado ou piloto inexistente no catálogo."""


class Catalog:
    def __init__(self, raw: Dict[str, Any]) -> None:
        self.raw = raw
        self.circuits: List[Dict[str, Any]] = raw.get("circuits", [])
        self._circuit_by_id = {c["id"]: c for c in self.circuits}
        self.seasons: Dict[int, List[Dict[str, Any]]] = {
            int(year): drivers for year, drivers in raw.get("seasons", {}).items()
        }
        # Índice global de pilotos: a temporada mais recente vence (nome/país/
        # equipe mais atuais). Usado para resolver o grid por id.
        self._driver_by_id: Dict[str, Dict[str, Any]] = {}
        for year in sorted(self.seasons):
            for d in self.seasons[year]:
                self._driver_by_id[d["id"]] = d

    # -- temporadas / pilotos ------------------------------------------------

    def season_years(self) -> List[int]:
        return sorted(self.seasons, reverse=True)

    def season_drivers(self, year: int) -> Optional[List[Dict[str, Any]]]:
        return self.seasons.get(year)

    def driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        return self._driver_by_id.get(driver_id)

    # -- circuitos / traçados ------------------------------------------------

    def circuit(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        return self._circuit_by_id.get(circuit_id)

    def resolve_layout(
        self, circuit_id: str, layout_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Devolve (circuito, traçado). Sem ``layout_id``, usa o traçado atual."""
        circuit = self.circuit(circuit_id)
        if circuit is None:
            raise CatalogLookupError(f"circuito '{circuit_id}' não existe no catálogo")
        if not circuit["layouts"]:
            raise CatalogLookupError(f"circuito '{circuit_id}' não tem traçados cadastrados")

        wanted = layout_id or circuit["current_layout_id"]
        for layout in circuit["layouts"]:
            if layout["id"] == wanted:
                return circuit, layout
        valid = ", ".join(l["id"] for l in circuit["layouts"])
        raise CatalogLookupError(
            f"traçado '{layout_id}' não existe no circuito '{circuit_id}' (válidos: {valid})"
        )


def load_catalog(path: Optional[Path] = None) -> Catalog:
    """Lê o catálogo do disco (sem cache; veja :func:`get_catalog`)."""
    path = Path(path or os.environ.get(CATALOG_ENV_VAR) or DEFAULT_CATALOG_PATH)
    if not path.exists():
        raise CatalogUnavailable(
            f"catálogo não encontrado em {path}. Gere com: "
            "python scripts/build_catalog.py (dentro de backend/)"
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            return Catalog(json.load(f))
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise CatalogUnavailable(f"catálogo ilegível em {path}: {exc}") from exc


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    """Catálogo em cache (carregado uma vez por processo)."""
    return load_catalog()
