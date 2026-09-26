"""Data Transfer Objects (DTOs) for Circuit and Layout endpoints.

Provides Pydantic models for structured request/response handling,
OpenAPI/Swagger schema generation, and automatic data validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class BaseDTO(BaseModel):
    """Base DTO supporting dict-like subscripting and attribute access."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __contains__(self, item: str) -> bool:
        return item in type(self).model_fields

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CountryDTO(BaseDTO):
    """Informações do país onde o circuito está localizado."""

    id: str = Field(..., description="Identificador do país", examples=["brazil"])
    name: str = Field(..., description="Nome do país", examples=["Brazil"])
    alpha2_code: Optional[str] = Field(None, description="Código ISO 3166-1 alfa-2", examples=["BR"])
    alpha3_code: Optional[str] = Field(None, description="Código ISO 3166-1 alfa-3", examples=["BRA"])
    continent_id: Optional[str] = Field(None, description="Identificador do continente", examples=["south-america"])


class LocationDTO(BaseDTO):
    """Coordenadas geográficas do circuito."""

    latitude: Optional[float] = Field(None, description="Latitude geográfica", examples=[-23.701111])
    longitude: Optional[float] = Field(None, description="Longitude geográfica", examples=[-46.697222])


class CircuitLayoutDTO(BaseDTO):
    """Dados de uma configuração de traçado (layout) histórico ou atual."""

    id: str = Field(..., description="Identificador único do layout", examples=["interlagos-2"])
    circuit_id: str = Field(..., description="Identificador do circuito pai", examples=["interlagos"])
    name: Optional[str] = Field(None, description="Nome do layout, quando disponível", examples=["Grand Prix Circuit"])
    effective: Optional[bool] = Field(None, description="Indica se é o traçado atualmente ativo", examples=[True])
    length: Optional[float] = Field(None, description="Extensão total da pista em quilômetros", examples=[4.309])
    turns: Optional[int] = Field(None, description="Número total de curvas do traçado", examples=[15])
    first_year: Optional[int] = Field(None, description="Primeiro ano em que o traçado foi utilizado", examples=[1990])
    last_year: Optional[int] = Field(None, description="Último ano em que o traçado foi utilizado", examples=[2026])
    year_ranges: List[str] = Field(
        default_factory=list,
        description="Intervalos de anos em que o traçado recebeu GPs",
        examples=[["1990-2019", "2021-2026"]],
    )
    svg: Dict[str, str] = Field(
        default_factory=dict,
        description="Links diretos no GitHub para o arquivo vetorial SVG em diferentes estilos",
        examples=[{
            "white-outline": "https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/white-outline/interlagos-2.svg",
            "black-outline": "https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/black-outline/interlagos-2.svg",
            "white": "https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/white/interlagos-2.svg",
            "black": "https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/black/interlagos-2.svg",
        }],
    )


class CircuitSummaryDTO(BaseDTO):
    """Resumo cadastral de um circuito com indicadores de traçado."""

    id: str = Field(..., description="Identificador do circuito", examples=["interlagos"])
    name: str = Field(..., description="Nome curto ou popular do circuito", examples=["José Carlos Pace"])
    full_name: str = Field(..., description="Nome oficial completo", examples=["Autódromo José Carlos Pace"])
    country: Optional[Union[CountryDTO, Dict[str, Any], str]] = Field(None, description="País do circuito")
    place_name: Optional[str] = Field(None, description="Cidade ou região", examples=["São Paulo"])
    location: Optional[Union[LocationDTO, Dict[str, Any]]] = Field(None, description="Coordenadas geográficas")
    total_races_held: int = Field(0, description="Total de corridas de F1 realizadas no circuito", examples=[42])
    layouts_count: int = Field(0, description="Número de configurações de traçado históricas", examples=[2])
    first_year: Optional[int] = Field(None, description="Primeiro ano com GP de F1", examples=[1973])
    last_year: Optional[int] = Field(None, description="Ano mais recente com GP de F1", examples=[2026])
    current_layout_id: Optional[str] = Field(None, description="ID do layout vigente", examples=["interlagos-2"])
    current_length_km: Optional[float] = Field(None, description="Extensão em km do traçado atual", examples=[4.309])
    current_turns: Optional[int] = Field(None, description="Curvas do traçado atual", examples=[15])


class CircuitDTO(BaseDTO):
    """Dados completos de um circuito, incluindo evolução histórica de traçados."""

    id: str = Field(..., description="Identificador do circuito", examples=["interlagos"])
    name: str = Field(..., description="Nome curto do circuito", examples=["José Carlos Pace"])
    full_name: str = Field(..., description="Nome oficial completo", examples=["Autódromo José Carlos Pace"])
    previous_names: Optional[str] = Field(None, description="Nomes históricos anteriores", examples=["Interlagos"])
    type: Optional[str] = Field(None, description="Tipo de circuito (ex: RACE, STREET)", examples=["RACE"])
    direction: Optional[str] = Field(None, description="Sentido da corrida (CLOCKWISE, ANTI_CLOCKWISE)", examples=["ANTI_CLOCKWISE"])
    place_name: Optional[str] = Field(None, description="Cidade ou localidade", examples=["São Paulo"])
    country: Optional[Union[CountryDTO, Dict[str, Any], str]] = Field(None, description="País do circuito")
    location: Optional[Union[LocationDTO, Dict[str, Any]]] = Field(None, description="Coordenadas geográficas")
    current_length_km: Optional[float] = Field(None, description="Extensão em km do traçado atual", examples=[4.309])
    current_turns: Optional[int] = Field(None, description="Curvas do traçado atual", examples=[15])
    total_races_held: int = Field(0, description="Total de corridas de F1 realizadas no circuito", examples=[42])
    layouts_count: int = Field(0, description="Total de variações de traçado", examples=[2])
    layouts: List[CircuitLayoutDTO] = Field(
        default_factory=list,
        description="Lista cronológica de configurações de traçado do circuito",
    )
