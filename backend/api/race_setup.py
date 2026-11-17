"""Traduz o pedido do front (``RaceSetupRequest``) em objetos do motor.

Fica separado do ``RaceManager`` de propósito: aqui não há thread, PyBullet nem
WebSocket — só validação contra o catálogo e montagem de ``Track``, ``Driver`` e
``WeatherModel``. Isso deixa tudo testável sem rodar simulação.
"""

from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Set

# Garante "backend/" no sys.path (mesmo truque do race_manager / run_sim.py).
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from config import DEFAULT_DRIVERS, INTERLAGOS_TRACK, RED_CAR, load_track  # noqa: E402
from domain import (  # noqa: E402
    BASE_CONDITIONS,
    Driver,
    Track,
    TyreCompound,
    WeatherKind,
    WeatherModel,
    WeatherState,
    WeatherTransitionConfig,
)

from .catalog import Catalog, CatalogLookupError  # noqa: E402
from .schemas import (  # noqa: E402
    GridEntryOut,
    InitialWeatherOut,
    RaceSetupRequest,
    TyreName,
    WeatherChange,
    WeatherName,
)


class SetupError(ValueError):
    """Pedido inválido/impossível (vira HTTP 422)."""


class CatalogRequired(RuntimeError):
    """O pedido precisa do catálogo, mas ele não está disponível (vira HTTP 503)."""


# ---------------------------------------------------------------------------
# Clima
# ---------------------------------------------------------------------------

# O motor tem 4 estados de clima; o front tem 5. A intensidade da chuva vem do
# campo ``rainfall`` (mm/h), que já entra no cálculo de aderência do WET.
#   chuva fraca  -> DAMP (pista úmida, pneu intermediário) com 0,5 mm/h
#   chuva        -> WET padrão (2,5 mm/h)
#   chuva forte  -> WET com 8 mm/h (aderência cai para o piso do modelo)
WEATHER_PRESETS: Dict[WeatherName, tuple] = {
    WeatherName.dry: (WeatherKind.DRY, None),
    WeatherName.cloudy: (WeatherKind.CLOUDY, None),
    WeatherName.light_rain: (WeatherKind.DAMP, 0.5),
    WeatherName.rain: (WeatherKind.WET, None),
    WeatherName.heavy_rain: (WeatherKind.WET, 8.0),
}


def weather_state(name: WeatherName) -> WeatherState:
    kind, rainfall = WEATHER_PRESETS[name]
    base = BASE_CONDITIONS[kind]
    return replace(base, rainfall=rainfall) if rainfall is not None else base


def build_transition_config(
    initial_kind: WeatherKind, change: Optional[WeatherChange]
) -> WeatherTransitionConfig:
    """Sem ``change``: o clima nunca muda (o padrão do motor sortearia mudanças).

    Com ``change``: a cada volta, com ``probability_per_lap``, o clima muda para
    um dos climas possíveis (sorteio uniforme, sempre diferente do atual quando
    houver outro). O clima inicial também pode voltar a ser sorteado.
    """
    if change is None:
        return WeatherTransitionConfig.default(transition_prob_per_lap=0.0)

    allowed: Set[WeatherKind] = {WEATHER_PRESETS[w][0] for w in change.possible} | {initial_kind}
    matrix: Dict[WeatherKind, Dict[WeatherKind, float]] = {}
    for current in WeatherKind:
        targets = [k for k in allowed if k != current] or [current]
        share = 1.0 / len(targets)
        matrix[current] = {k: (share if k in targets else 0.0) for k in WeatherKind}
    return WeatherTransitionConfig(
        transition_matrix=matrix, transition_prob_per_lap=change.probability_per_lap
    )


def build_weather_model(
    initial: WeatherName, change: Optional[WeatherChange], seed: Optional[int] = None
) -> WeatherModel:
    state = weather_state(initial)
    return WeatherModel(
        state, build_transition_config(state.kind, change), rng=random.Random(seed)
    )


# ---------------------------------------------------------------------------
# Pneus
# ---------------------------------------------------------------------------

TYRE_MAP: Dict[TyreName, TyreCompound] = {
    TyreName.soft: TyreCompound.SOFT,
    TyreName.medium: TyreCompound.MEDIUM,
    TyreName.hard: TyreCompound.HARD,
    TyreName.intermediate: TyreCompound.INTERMEDIATE,
    TyreName.wet: TyreCompound.WET,
}


def resolve_initial_tyre(req: RaceSetupRequest) -> Optional[TyreName]:
    """Pneu pedido: ``initial_tyre`` > 1º stint > nada (None = padrão)."""
    if req.initial_tyre is not None:
        return req.initial_tyre
    if req.stints:
        return req.stints[0].compound
    return None


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------

@dataclass
class RaceSetup:
    track: Track
    drivers: List[Driver]
    weather_model: WeatherModel
    num_laps: int
    circuit_id: Optional[str]
    layout_id: Optional[str]
    initial_weather: InitialWeatherOut
    initial_tyre: Optional[TyreName]
    grid: List[GridEntryOut]
    warnings: List[str] = field(default_factory=list)


def build_race_setup(
    req: RaceSetupRequest,
    catalog: Optional[Catalog],
    *,
    track_loader: Callable[..., Track] = load_track,
    cache_dir: Optional[str] = None,
    seed: Optional[int] = None,
) -> RaceSetup:
    """Valida o pedido contra o catálogo e monta tudo o que o motor precisa.

    ``catalog`` só é exigido quando o pedido traz ``circuit`` ou ``grid``;
    ``POST /races {"laps": 5}`` continua funcionando sem catálogo.
    ``track_loader`` é injetável para testes (o real baixa dados do FastF1).
    """
    warnings: List[str] = []
    tyre = resolve_initial_tyre(req)

    # -- pista ---------------------------------------------------------------
    circuit_id: Optional[str] = None
    layout_id: Optional[str] = None
    if req.circuit is None:
        track = INTERLAGOS_TRACK
        circuit_id, layout_id = "interlagos", None
    else:
        if catalog is None:
            raise CatalogRequired("catálogo indisponível: não dá para resolver o circuito")
        try:
            circuit, layout = catalog.resolve_layout(req.circuit.id, req.circuit.layout_id)
        except CatalogLookupError as exc:
            raise SetupError(str(exc)) from exc
        if not layout["simulable"]:
            raise SetupError(
                f"o traçado '{layout['id']}' não é simulável (último uso: {layout['last_year']}; "
                "o motor precisa de dados do FastF1, disponíveis só de 2018 em diante). "
                "Escolha um traçado com simulable=true."
            )
        ref = layout["fastf1"]
        # Carrega por número da rodada: evita busca por nome (frágil) no FastF1.
        track = track_loader(str(ref["round"]), ref["year"], cache_dir=cache_dir)
        circuit_id, layout_id = circuit["id"], layout["id"]

    # -- grid ----------------------------------------------------------------
    drivers: List[Driver] = []
    if req.grid is None:
        drivers = [
            replace(d, starting_tyre_compound=TYRE_MAP[tyre]) if tyre else d
            for d in DEFAULT_DRIVERS
        ]
    else:
        if catalog is None:
            raise CatalogRequired("catálogo indisponível: não dá para resolver os pilotos do grid")
        unknown = [d for d in req.grid if catalog.driver(d) is None]
        if unknown:
            raise SetupError(f"pilotos desconhecidos no grid: {', '.join(unknown)}")
        compound = TYRE_MAP[tyre] if tyre else TyreCompound.MEDIUM
        for driver_id in req.grid:
            info = catalog.driver(driver_id)
            drivers.append(Driver(
                driver_id=driver_id,
                name=info["name"] or driver_id,
                car_specs=RED_CAR,  # mesmo carro p/ todos: o motor ainda não modela equipes
                starting_tyre_compound=compound,
            ))

    grid_out = [
        GridEntryOut(position=i + 1, driver_id=d.driver_id, name=d.name)
        for i, d in enumerate(drivers)
    ]

    # -- clima ---------------------------------------------------------------
    weather_model = build_weather_model(req.weather, req.weather_change, seed)
    cur = weather_model.current
    initial_weather = InitialWeatherOut(
        requested=req.weather, engine_kind=cur.kind.value, rainfall_mm_h=cur.rainfall
    )
    if req.weather_change and any(
        w in (WeatherName.light_rain, WeatherName.heavy_rain) for w in req.weather_change.possible
    ):
        warnings.append(
            "weather_change: durante a corrida o motor só tem 4 climas; chuva fraca vira DAMP e "
            "chuva forte vira WET padrão (a intensidade exata só vale para o clima inicial)."
        )

    # -- stints --------------------------------------------------------------
    if req.stints:
        warnings.append(
            "stints: aceitos e validados, mas o motor ainda não aplica a estratégia; "
            "os pit stops seguem decididos por desgaste de pneu e combustível."
        )

    return RaceSetup(
        track=track,
        drivers=drivers,
        weather_model=weather_model,
        num_laps=req.laps,
        circuit_id=circuit_id,
        layout_id=layout_id,
        initial_weather=initial_weather,
        initial_tyre=tyre,
        grid=grid_out,
        warnings=warnings,
    )
