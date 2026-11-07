"""Race configuration dataclasses and named presets."""

from domain import (
    CarSpecs,
    CircuitLoadError,
    Driver,
    FastF1TrackLoader,
    Track,
    TyreCompound,
    build_interlagos_track,
)
from engine import SimulationConfig
from domain.weather import WeatherKind, BASE_CONDITIONS, WeatherTransitionConfig

__all__ = [
    "SimulationConfig",
    "DEFAULT_INTERLAGOS_CONFIG",
    "DEFAULT_DRIVERS",
    "INTERLAGOS_TRACK",
    "CircuitLoadError",
    "load_track",
    "interlagos_1v1_config",
    "interlagos_1v1_drivers",
]


# Carro de referência (estilo F1-like, valores aproximados)
RED_CAR = CarSpecs(
    name="Red Phantom",
    power_kw=735.0,           # ~1000 HP
    mass_kg=798.0,            # sem combustível
    fuel_capacity_kg=110.0,
    drag_coeff=0.85,
    frontal_area_m2=1.5,
    wheelbase_m=3.4,
    max_speed_kmh=330.0,
)

BLUE_CAR = CarSpecs(
    name="Blue Bolt",
    power_kw=730.0,
    mass_kg=802.0,
    fuel_capacity_kg=110.0,
    drag_coeff=0.86,
    frontal_area_m2=1.5,
    wheelbase_m=3.4,
    max_speed_kmh=328.0,
)


DEFAULT_INTERLAGOS_CONFIG = SimulationConfig(
    race_id="interlagos_001",
    num_laps=10,
    physics_sub_steps=24,        # 0.1s logic / (1/240s) = 24 sub-steps (sincroniza tempo)
    logic_step_hz=10.0,
    position_update_every_lap=1,
    pit_time_s=22.0,
    fuel_threshold_kg=40.0,     # piloto com <40kg de combustível faz pit
    tyre_life_threshold=35.0,   # pneu com <35% de vida faz pit
    gui=False,
    random_seed=42,
)


DEFAULT_DRIVERS = [
    Driver(
        driver_id="drv_01",
        name="P. Brasil",
        car_specs=RED_CAR,
        starting_tyre_compound=TyreCompound.MEDIUM,
        starting_fuel_pct=1.0,
        aggressive=1.0,
    ),
    Driver(
        driver_id="drv_02",
        name="A. Silva",
        car_specs=BLUE_CAR,
        starting_tyre_compound=TyreCompound.SOFT,
        starting_fuel_pct=1.0,
        aggressive=1.05,
    ),
]


INTERLAGOS_TRACK = build_interlagos_track()

_LOCAL_INTERLAGOS_ALIASES = {"interlagos", "sao-paulo", "são-paulo", "brazil"}
_TRACK_EVENT_ALIASES = {
    "interlagos": "São Paulo",
    "sao-paulo": "São Paulo",
    "são-paulo": "São Paulo",
    "brazil": "São Paulo",
}


def _parse_fastf1_event(track_name: str) -> str | int:
    stripped = track_name.strip()
    if stripped.isdigit():
        return int(stripped)
    return _TRACK_EVENT_ALIASES.get(stripped.lower(), stripped)


def load_track(
    track_name: str | None = None,
    year: int | None = None,
    session: str = "R",
    cache_dir: str | None = None,
) -> Track:
    """Carrega uma pista local ou um circuito real do FastF1.

    Sem ``track_name``, devolve o preset local de Interlagos. Sem ``year``,
    apenas aliases locais de Interlagos são aceitos; qualquer outro nome
    exige ``year`` e é buscado no FastF1 (sem fallback silencioso).
    """
    if track_name is None or not str(track_name).strip():
        return INTERLAGOS_TRACK

    normalized = track_name.strip().lower()
    if year is None:
        if normalized in _LOCAL_INTERLAGOS_ALIASES:
            return INTERLAGOS_TRACK
        raise ValueError(
            f"track '{track_name}' was not found locally; pass --year to load "
            "it from FastF1"
        )

    event = _parse_fastf1_event(track_name)
    return FastF1TrackLoader(cache_dir=cache_dir).load(
        year=year,
        event=event,
        session=session,
    )


def interlagos_1v1_config() -> SimulationConfig:
    return DEFAULT_INTERLAGOS_CONFIG


def interlagos_1v1_drivers() -> list:
    return list(DEFAULT_DRIVERS)
