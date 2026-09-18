"""Event types published by the simulation engine.

Todos os eventos derivam de :class:`Event` e são serializáveis via
``to_dict()``. O ``Publisher`` é responsável por enviá-los
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    """Evento base. ``ts`` é timestamp Unix; ``sim_ts`` é tempo simulado (s)."""

    type: str
    ts: float = field(default_factory=time.time)
    sim_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class RaceStartEvent(Event):
    type: str = "race_start"
    race_id: str = ""
    track_name: str = ""
    num_laps: int = 0
    num_drivers: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RaceEndEvent(Event):
    type: str = "race_end"
    race_id: str = ""
    final_classification: List[Dict[str, Any]] = field(default_factory=list)
    total_time_s: float = 0.0


@dataclass
class LapCompletedEvent(Event):
    type: str = "lap_completed"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    lap_time_s: float = 0.0
    best_lap_time_s: float = 0.0
    fuel_kg: float = 0.0
    tyre: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeatherChangedEvent(Event):
    type: str = "weather_changed"
    lap: int = 0
    previous: Dict[str, Any] = field(default_factory=dict)
    current: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TyreWornEvent(Event):
    """Emitido quando a vida do pneu cruza um threshold crítico."""
    type: str = "tyre_worn"
    driver_id: str = ""
    driver_name: str = ""
    compound: str = ""
    tyre_life_pct: float = 0.0
    age_laps: float = 0.0


@dataclass
class PitStopEvent(Event):
    type: str = "pit_stop"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    new_compound: str = ""
    fuel_added_kg: float = 0.0
    pit_time_s: float = 0.0


@dataclass
class PositionUpdateEvent(Event):
    """Snapshot periódico com a posição de todos os pilotos."""
    type: str = "position_update"
    lap: int = 0
    positions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TickEvent(Event):
    """Tick de simulação (frequência menor que PositionUpdate)."""
    type: str = "tick"
    lap: int = 0
    tick_in_lap: int = 0
    positions: List[Dict[str, Any]] = field(default_factory=list)
    weather: Dict[str, Any] = field(default_factory=dict)
