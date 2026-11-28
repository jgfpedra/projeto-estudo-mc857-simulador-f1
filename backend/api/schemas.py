"""Modelos Pydantic da api (viram o Swagger em ``/docs``)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_GRID = 24  # slots do grid do motor (SimulationConfig.num_slots)


class RadioAudioRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=480)


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

    circuit: Optional[CircuitChoice] = Field(None, description="Omitido = Interlagos (pista local).")
    laps: int = Field(10, ge=1, le=200, description="Número de voltas.")
    grid: Optional[List[str]] = Field(
        None, min_length=1, max_length=MAX_GRID,
        description="ids dos pilotos em ordem de largada (1º = pole). Omitido = 2 pilotos padrão.",
        examples=[["max-verstappen", "lando-norris", "charles-leclerc"]],
    )
    num_drivers: int = Field(
        2, ge=1, le=MAX_GRID,
        description="Quantidade de corredores quando `grid` não é enviado. "
        "Ignorado se `grid` estiver presente.",
    )
    track: Optional[str] = Field(
        None, description="Circuito local legado (ex.: interlagos). "
        "Use `circuit` no contrato novo; sem `circuit`, o `track` é resolvido pelos providers.",
    )
    layout_id: Optional[str] = None
    year: Optional[int] = Field(None, description="Temporada dos pilotos; com grid e layout explícitos, a pista pode usar outro ano de referência do mesmo layout.")
    season: Optional[int] = Field(None, description="Alias de year para a temporada dos pilotos.")
    user_driver_id: Optional[str] = Field(None, description="Piloto cujo pit stop é solicitado manualmente.")
    random_seed: Optional[int] = Field(None, ge=0, le=4294967295,
                                       description="Semente dos bots e suas estratégias; omitida, é sorteada por corrida.")
    weather: Optional[WeatherName] = Field(None, description="Clima inicial. Omitido = dry.")
    weather_change: Optional[WeatherChange] = Field(
        None, description="Omitido = o clima não muda durante a corrida."
    )
    initial_tyre: Optional[TyreName] = Field(
        None, description="Pneu inicial de todos. Omitido = 1º stint de `stints`, ou medium."
    )
    stints: Optional[List[StintIn]] = Field(
        None, min_length=1,
        description="Estratégia de stints (composto + voltas). A soma das voltas deve ser igual a `laps`. "
        "ATENÇÃO: é validada e aceita, mas o motor ainda NÃO aplica (veja `warnings` na resposta).",
    )

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
            if self.initial_tyre is not None and self.stints[0].compound != self.initial_tyre:
                raise ValueError(
                    "initial_tyre deve ser igual ao composto do 1º stint "
                    f"({self.stints[0].compound.value}); envie só um dos dois ou deixe-os consistentes"
                )
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


# ---------------------------------------------------------------------------
# Coach commands (POST /races/{race_id}/drivers/{driver_id}/command)
# ---------------------------------------------------------------------------

class CoachCommandName(str, Enum):
    """Comandos de alto nível que o engenheiro entende."""
    neutral = "neutral"
    push = "push"
    attack = "attack"
    atacar = "atacar"
    conserve = "conserve"
    economizar = "economizar"
    careful = "careful"
    cuidado = "cuidado"
    defend = "defend"
    defender = "defender"
    overtake = "overtake"
    ultrapassar = "ultrapassar"
    pace = "pace"


class CoachCommandRequest(BaseModel):
    """Envia comando de alto nível para o engenheiro de um piloto."""
    model_config = ConfigDict(extra="forbid")

    command: CoachCommandName
    value: float = Field(0.0, ge=0.0, le=2.0, description="Usado apenas para 'pace' (multiplicador 0.5-1.15).")
    reason: str = Field("", description="Motivo do comando (exibido no HUD).")
    issued_by: str = Field("user", description="Origem: 'user', 'llm', 'ai', etc.")


class CoachCommandResponse(BaseModel):
    race_id: str
    driver_id: str
    command: str
    value: float
    reason: str
    issued_by: str
    status: str = "queued"
