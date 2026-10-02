"""Domain layer.

Pure-Python business rules. No I/O, no PyBullet, no side-effects.
The Engine consumes these models to apply rules during the simulation.
"""

from .tyre import TyreCompound, TyreModel, TyreState, TYRE_CATALOG
from .weather import (
    WeatherKind,
    WeatherState,
    WeatherTransitionConfig,
    WeatherModel,
    BASE_CONDITIONS,
)
from .car import CarSpecs, CarState
from .track import (
    Track,
    Sector,
    PitLane,
    build_interlagos_track,
    compute_grid_positions,
    compute_grid_slot,
)
from .track_loader import CircuitLoadError, FastF1TrackLoader
from .driver import Driver, DriverState

__all__ = [
    "TyreCompound",
    "TyreModel",
    "TyreState",
    "TYRE_CATALOG",
    "WeatherKind",
    "WeatherState",
    "WeatherTransitionConfig",
    "WeatherModel",
    "BASE_CONDITIONS",
    "CarSpecs",
    "CarState",
    "Track",
    "Sector",
    "PitLane",
    "build_interlagos_track",
    "compute_grid_positions",
    "compute_grid_slot",
    "CircuitLoadError",
    "FastF1TrackLoader",
    "Driver",
    "DriverState",
]
