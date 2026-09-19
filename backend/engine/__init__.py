"""Engine layer.

PyBullet physics + orchestration. Consumes :mod:`racing_sim.domain` and
publishes state/events.
"""

from .events import (
    Event,
    LapCompletedEvent,
    PitStopEvent,
    PositionUpdateEvent,
    RaceEndEvent,
    RaceStartEvent,
    TickEvent,
    TyreWornEvent,
    WeatherChangedEvent,
)
from .publisher import (
    JSONLPublisher,
    NullPublisher,
    Publisher,
    RedisPublisher,
)
from .physics import PhysicsCarHandle, PyBulletPhysics
from .simulation import SimulationConfig, SimulationEngine
from .controllers import (
    CarController,
    CarInput,
    EnvironmentState,
    ExternalController,
    InputSourceController,
    ManualController,
)
from .input_source import (
    FileInputSource,
    InputEntry,
    InputSource,
    InMemoryInputSource,
    RedisInputSource,
)

__all__ = [
    # Events
    "Event",
    "RaceStartEvent",
    "RaceEndEvent",
    "LapCompletedEvent",
    "WeatherChangedEvent",
    "TyreWornEvent",
    "PitStopEvent",
    "PositionUpdateEvent",
    "TickEvent",
    # Publishers
    "Publisher",
    "JSONLPublisher",
    "RedisPublisher",
    "NullPublisher",
    # Physics
    "PyBulletPhysics",
    "PhysicsCarHandle",
    # Simulation
    "SimulationEngine",
    "SimulationConfig",
    # Controllers
    "CarInput",
    "EnvironmentState",
    "CarController",
    "ManualController",
    "ExternalController",
    "InputSourceController",
    # Input sources
    "InputEntry",
    "InputSource",
    "InMemoryInputSource",
    "FileInputSource",
    "RedisInputSource",
]
