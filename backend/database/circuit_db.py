"""Circuit Database abstraction and implementations.

Provides an interface (CircuitDatabase) and implementations:
- JSONCircuitDatabase: reads circuit layout evolutions from a JSON file.
- InMemoryCircuitDatabase: in-memory implementation useful for tests or mocked data.
Future implementations can connect to relational databases (e.g. SQLite, PostgreSQL).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class CircuitDatabase(ABC):
    """Abstract base class representing the Circuit persistence layer."""

    @abstractmethod
    def get_all_circuits(self) -> List[Dict[str, Any]]:
        """Return raw data for all circuits in the database."""
        pass

    @abstractmethod
    def get_circuit_by_id(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Return the circuit dictionary for a given circuit_id or None if not found."""
        pass

    def get_circuit(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_circuit_by_id."""
        return self.get_circuit_by_id(circuit_id)

    def get_layouts(self, circuit_id: str) -> Optional[List[Dict[str, Any]]]:
        """Return chronological layouts for a given circuit, or None if circuit not found."""
        circuit = self.get_circuit_by_id(circuit_id)
        if not circuit:
            return None
        return circuit.get("layouts", [])

    def get_layout(self, circuit_id: str, layout_id: str) -> Optional[Dict[str, Any]]:
        """Return a specific layout for a given circuit, or None if not found."""
        layouts = self.get_layouts(circuit_id)
        if layouts is None:
            return None
        for l in layouts:
            if l.get("id") == layout_id or l.get("layout_id") == layout_id:
                return l
        return None


class JSONCircuitDatabase(CircuitDatabase):
    """Circuit database backed by a JSON file (e.g. circuit_layouts_evolution.json)."""

    def __init__(self, json_path: Optional[Path | str] = None):
        if json_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            self.json_path = base_dir / "data" / "circuit_layouts_evolution.json"
        else:
            self.json_path = Path(json_path)

        self._data: Optional[Dict[str, Any]] = None
        self._circuits_by_id: Dict[str, Dict[str, Any]] = {}

    def _load_data(self) -> Dict[str, Any]:
        """Loads and caches data from the JSON file."""
        if self._data is None:
            if not self.json_path.exists():
                raise FileNotFoundError(
                    f"Circuit evolution data file not found at {self.json_path}. "
                    "Run 'python backend/scripts/fetch_track_layouts.py' first."
                )
            with open(self.json_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            self._circuits_by_id = {c["id"]: c for c in self._data.get("circuits", [])}
        return self._data

    def get_all_circuits(self) -> List[Dict[str, Any]]:
        """Return list of all circuits loaded from JSON."""
        data = self._load_data()
        return data.get("circuits", [])

    def get_circuit_by_id(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """Return circuit details by circuit_id from JSON cache."""
        self._load_data()
        return self._circuits_by_id.get(circuit_id)


class InMemoryCircuitDatabase(CircuitDatabase):
    """In-memory Circuit database, ideal for testing and mocks."""

    def __init__(self, circuits: Optional[List[Dict[str, Any]]] = None):
        self._circuits: List[Dict[str, Any]] = list(circuits) if circuits else []
        self._circuits_by_id: Dict[str, Dict[str, Any]] = {
            c["id"]: c for c in self._circuits if "id" in c
        }

    def add_circuit(self, circuit: Dict[str, Any]) -> None:
        """Add or replace a circuit in memory."""
        self._circuits.append(circuit)
        if "id" in circuit:
            self._circuits_by_id[circuit["id"]] = circuit

    def get_all_circuits(self) -> List[Dict[str, Any]]:
        return list(self._circuits)

    def get_circuit_by_id(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        return self._circuits_by_id.get(circuit_id)


# Aliases for repository terminology
CircuitRepository = CircuitDatabase
JSONCircuitRepository = JSONCircuitDatabase
