"""Modelos Pydantic da api (viram o Swagger em ``/docs``)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_GRID = 24  # slots do grid do motor (SimulationConfig.num_slots)


# ---------------------------------------------------------------------------
# Catálogo (GET /circuits, /seasons, /seasons/{year}/drivers)
# ---------------------------------------------------------------------------

class CountryOut(BaseModel):
    name: Optional[str] = Field(None, examples=["Brazil"])
    code: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 (para emoji de bandeira).", examples=["BR"])


class LayoutOut(BaseModel):
    id: str = Field(..., description="Use em POST /races → circuit.layout_id.", examples=["interlagos-2"])
    years: List[str] = Field(..., description="Anos em que o traçado foi usado.", examples=[["1990-2026"]])
    first_year: Optional[int] = None
    last_year: Optional[int] = None
    length_km: Optional[float] = Field(None, examples=[4.309])
    turns: Optional[int] = Field(None, examples=[15])
    svg: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="URLs do SVG do traçado, por estilo (ex.: black-outline, white-outline).",
    )
    is_current: bool = Field(..., description="Traçado atual/mais recente do circuito.")
    simulable: bool = Field(
        ...,
        description="Se o motor consegue simular esse traçado. Só os usados de 2018 em diante "
        "(é a faixa de dados do FastF1). Os demais servem só para exibição.",
    )


class CircuitOut(BaseModel):
    id: str = Field(..., examples=["interlagos"])
    name: Optional[str] = Field(None, examples=["José Carlos Pace"])
    full_name: Optional[str] = Field(None, examples=["Autódromo José Carlos Pace"])
    city: Optional[str] = Field(None, examples=["São Paulo"])
    country: CountryOut
    svg: Optional[Dict[str, Optional[str]]] = Field(None, description="SVG do traçado atual.")
    current_layout_id: Optional[str] = None
    simulable: bool = Field(..., description="Algum traçado do circuito é simulável.")
    layouts: List[LayoutOut] = Field(..., description="Variações de traçado.")


class SeasonDriverOut(BaseModel):
    id: str = Field(..., description="Use em POST /races → grid.", examples=["max-verstappen"])
    name: Optional[str] = Field(None, examples=["Max Verstappen"])
    abbreviation: Optional[str] = Field(None, examples=["VER"])
    number: Optional[int] = Field(None, description="Número do carro naquela temporada.", examples=[1])
    team: Optional[str] = Field(None, examples=["Red Bull"])
    team_id: Optional[str] = None
    country: CountryOut


# ---------------------------------------------------------------------------
# Setup da corrida (POST /races)
# ---------------------------------------------------------------------------

class WeatherName(str, Enum):
    dry = "dry"                # seco
    cloudy = "cloudy"          # nublado
    light_rain = "light_rain"  # chuva fraca
    rain = "rain"              # chuva
    heavy_rain = "heavy_rain"  # chuva forte


class TyreName(str, Enum):
    soft = "soft"
    medium = "medium"
    hard = "hard"
    intermediate = "intermediate"
    wet = "wet"


class CircuitChoice(BaseModel):
    id: str = Field(..., description="id do circuito (GET /circuits).", examples=["interlagos"])
    layout_id: Optional[str] = Field(
        None, description="Variação de traçado. Omitido = traçado atual.", examples=["interlagos-2"]
    )


class WeatherChange(BaseModel):
    """Mudança de clima durante a corrida (opcional)."""

    probability_per_lap: float = Field(
        ..., ge=0.0, le=1.0,
        description="Chance, a cada volta, de o clima mudar para um dos climas possíveis.",
        examples=[0.1],
    )
    possible: List[WeatherName] = Field(
        ..., min_length=1, description="Climas para os quais pode mudar (sorteio uniforme).",
        examples=[["cloudy", "rain"]],
    )

    @model_validator(mode="after")
    def _unique(self) -> "WeatherChange":
        if len(set(self.possible)) != len(self.possible):
            raise ValueError("possible não pode ter climas repetidos")
        return self


class StintIn(BaseModel):
    compound: TyreName
    laps: int = Field(..., ge=1)


class RaceSetupRequest(BaseModel):
    """Payload enviado pelo front para configurar/criar uma corrida.

    Interlagos 2023 e Monza 2024 usam traçados locais derivados de telemetria;
    outros anos ou circuitos seguem ``config.load_track``.
    """

    model_config = ConfigDict(extra="forbid")

    laps: int = Field(default=10, ge=1, le=200)
    num_drivers: int = Field(default=2, ge=1, le=24)
    track: Optional[str] = None
    layout_id: Optional[str] = None
    year: Optional[int] = Field(None, description="Temporada dos pilotos; com grid e layout explícitos, a pista pode usar outro ano de referência do mesmo layout.")
    season: Optional[int] = Field(None, description="Alias de year para a temporada dos pilotos.")
    circuit: Optional[CircuitChoice] = None
    grid: Optional[List[str]] = Field(None, min_length=1, max_length=24)
    user_driver_id: Optional[str] = Field(None, description="Piloto cujo pit stop é solicitado manualmente.")
    weather: Optional[WeatherName] = None
    weather_change: Optional[WeatherChange] = None
    initial_tyre: Optional[TyreName] = None
    stints: Optional[List[StintIn]] = Field(None, min_length=1)

    @model_validator(mode="after")
    def validate_race_setup(self):
        if self.grid is not None and len(set(self.grid)) != len(self.grid):
            raise ValueError("grid não pode ter pilotos repetidos")
        if self.user_driver_id is not None and self.grid is not None and self.user_driver_id not in self.grid:
            raise ValueError("user_driver_id deve pertencer ao grid")
        if self.stints is not None:
            total = sum(stint.laps for stint in self.stints)
            if total != self.laps:
                raise ValueError(f"a soma das voltas dos stints ({total}) deve ser igual a laps ({self.laps})")
            if self.initial_tyre is not None and self.initial_tyre != self.stints[0].compound:
                raise ValueError("initial_tyre deve ser igual ao composto do primeiro stint")
        return self


class GridEntryOut(BaseModel):
    position: int
    driver_id: str
    name: str


class InitialWeatherOut(BaseModel):
    requested: WeatherName
    engine_kind: str
    rainfall_mm_h: float


class RaceSetupResponse(BaseModel):
    race_id: str
    track_name: str
    num_laps: int
    ws_path: str
    grid: List[str] = Field(default_factory=list)
    initial_weather: str = "dry"
    warnings: List[str] = Field(default_factory=list)


class PitStopRequest(BaseModel):
    """Pedido de troca na próxima entrada dos boxes."""
    model_config = ConfigDict(extra="forbid")
    tyre_compound: TyreName

    @field_validator('tyre_compound', mode='before')
    @classmethod
    def normalize_compound(cls, value):
        return value.lower() if isinstance(value, str) else value


class PitStopResponse(BaseModel):
    race_id: str
    driver_id: str
    tyre_compound: TyreName
    status: str = 'queued'


class PitStopCancelResponse(BaseModel):
    race_id: str
    driver_id: str
    status: str = 'cancellation_queued'
