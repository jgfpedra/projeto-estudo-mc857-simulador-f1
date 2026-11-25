"""Domain service and models for F1 circuit layout evolution.

Provides structured access to historical circuit layouts, active years,
and GitHub SVG links for frontend consumption.
Maintains backwards compatibility by subclassing CircuitService with DB injection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from database.circuit_db import CircuitDatabase
from service.circuit_service import CircuitService


class CircuitEvolutionService(CircuitService):
    """Domain service to query circuit layout evolutions and SVG GitHub links.

    Subclasses CircuitService to support database dependency injection.
    """

    def __init__(
        self,
        db: Optional[CircuitDatabase] = None,
        json_path: Optional[Path | str] = None,
    ):
        super().__init__(db=db, json_path=json_path)
