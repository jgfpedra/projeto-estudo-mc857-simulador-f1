"""Circuit Service for F1 circuit layout evolution.

Provides structured access to historical circuit layouts, active years,
and GitHub SVG links for frontend consumption.
Supports database dependency injection (defaults to JSONCircuitDatabase).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from database.circuit_db import (
    CircuitDatabase,
    JSONCircuitDatabase,
    InMemoryCircuitDatabase,
)


class CircuitService:
    """Service to query circuit layout evolutions and SVG GitHub links."""

    def __init__(
        self,
        db: Optional[CircuitDatabase] = None,
        json_path: Optional[Path | str] = None,
    ):
        """Initialize the circuit service with an injected database or fallback to JSON."""
        if db is not None:
            self.db: CircuitDatabase = db
        else:
            self.db = JSONCircuitDatabase(json_path=json_path)

    @property
    def json_path(self) -> Optional[Path]:
        """Backwards compatibility for inspecting the JSON path when using JSON DB."""
        return getattr(self.db, "json_path", None)

    def list_circuits(self) -> List[Dict[str, Any]]:
        """List summary of all available circuits."""
        circuits = self.db.get_all_circuits()
        summaries: List[Dict[str, Any]] = []

        for c in circuits:
            layouts = c.get("layouts", [])
            effective_layout = next((l for l in layouts if l.get("effective")), None)
            if not effective_layout and layouts:
                effective_layout = layouts[-1]

            first_year = min((l["first_year"] for l in layouts if l.get("first_year")), default=None)
            last_year = max((l["last_year"] for l in layouts if l.get("last_year")), default=None)
            current_id = (effective_layout.get("id") or effective_layout.get("layout_id")) if effective_layout else None

            summaries.append({
                "id": c["id"],
                "name": c["name"],
                "full_name": c["full_name"],
                "country": c.get("country"),
                "place_name": c.get("place_name"),
                "location": c.get("location"),
                "total_races_held": c.get("total_races_held", 0),
                "layouts_count": len(layouts),
                "first_year": first_year,
                "last_year": last_year,
                "current_layout_id": current_id,
                "current_length_km": c.get("current_length_km"),
                "current_turns": c.get("current_turns"),
            })
        return summaries

    def get_circuit(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Get full circuit details including layout evolution history."""
        return self.db.get_circuit_by_id(circuit_id)

    def get_layouts(self, circuit_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get list of chronological layouts for a given circuit."""
        return self.db.get_layouts(circuit_id)

    def get_layout(self, circuit_id: str, layout_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific layout."""
        return self.db.get_layout(circuit_id, layout_id)

    def get_layout_svg_url(
        self,
        circuit_id: str,
        layout_id: str,
        style: str = "white-outline",
    ) -> Optional[str]:
        """Retrieve the SVG GitHub link for a given layout and style."""
        layout = self.get_layout(circuit_id, layout_id)
        if not layout:
            return None
        return layout.get("svg", {}).get(style)
