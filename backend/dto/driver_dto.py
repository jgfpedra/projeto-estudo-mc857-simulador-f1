"""Data Transfer Objects (DTOs) for Driver and Team endpoints.

Provides Pydantic models for structured driver representations,
OpenAPI/Swagger schema generation, and automatic data validation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
from pydantic import Field, model_validator

from .circuit_dto import BaseDTO, CountryDTO


class TeamDTO(BaseDTO):
    """Informações da equipe/construtor do piloto na Fórmula 1."""

    id: Optional[str] = Field(None, description="Identificador único da equipe (ex: 'ferrari', 'mclaren')", examples=["ferrari"])
    name: str = Field(..., description="Nome oficial da equipe/construtor", examples=["Ferrari"])
    color: Optional[str] = Field(None, description="Código de cor hexadecimal oficial da equipe", examples=["#E80020"])


class DriverDTO(BaseDTO):
    """Informações cadastrais, equipe, cor e estatísticas de um piloto de Fórmula 1."""

    id: str = Field(..., description="Identificador único do piloto (ex: 'ayrton-senna', 'lewis-hamilton')", examples=["ayrton-senna"])
    name: str = Field(..., description="Nome de exibição comum do piloto", examples=["Ayrton Senna"])
    first_name: Optional[str] = Field(None, description="Primeiro nome", examples=["Ayrton"])
    last_name: Optional[str] = Field(None, description="Sobrenome", examples=["Senna"])
    full_name: Optional[str] = Field(None, description="Nome completo de batismo", examples=["Ayrton Senna da Silva"])
    abbreviation: Optional[str] = Field(None, description="Código de 3 letras utilizado nas transmissões", examples=["SEN"])
    permanent_number: Optional[int] = Field(None, description="Número do piloto na F1", examples=[44])
    gender: Optional[str] = Field(None, description="Gênero ('MALE' ou 'FEMALE')", examples=["MALE"])
    date_of_birth: Optional[str] = Field(None, description="Data de nascimento (YYYY-MM-DD)", examples=["1960-03-21"])
    date_of_death: Optional[str] = Field(None, description="Data de falecimento, se aplicável (YYYY-MM-DD)", examples=["1994-05-01"])
    place_of_birth: Optional[str] = Field(None, description="Cidade ou local de nascimento", examples=["São Paulo"])

    # Modelos reaproveitados / aninhados
    country: Optional[Union[CountryDTO, Dict[str, Any], str]] = Field(None, description="Dados do país/nacionalidade do piloto")
    team: Optional[TeamDTO] = Field(None, description="Dados da equipe/construtor e cor oficial na temporada")

    # Recordes e estatísticas
    best_championship_position: Optional[int] = Field(None, description="Melhor colocação final em um campeonato de F1", examples=[1])
    best_starting_grid_position: Optional[int] = Field(None, description="Melhor posição em grid de largada", examples=[1])
    best_race_result: Optional[int] = Field(None, description="Melhor posição final de corrida", examples=[1])
    best_sprint_race_result: Optional[int] = Field(None, description="Melhor resultado em corrida Sprint", examples=[None])

    total_championship_wins: int = Field(0, description="Total de títulos mundiais conquistados", examples=[3])
    total_race_entries: int = Field(0, description="Total de Grandes Prêmios inscritos", examples=[162])
    total_race_starts: int = Field(0, description="Total de largadas em corridas principais", examples=[161])
    total_race_wins: int = Field(0, description="Total de vitórias em Grandes Prêmios", examples=[41])
    total_race_laps: int = Field(0, description="Total de voltas completadas em corridas", examples=[8219])
    total_podiums: int = Field(0, description="Total de pódios conquistados", examples=[80])
    total_points: float = Field(0.0, description="Total de pontos somados na carreira", examples=[614.0])
    total_championship_points: float = Field(0.0, description="Total de pontos válidos para campeonatos", examples=[610.0])
    total_pole_positions: int = Field(0, description="Total de pole positions", examples=[65])
    total_fastest_laps: int = Field(0, description="Total de voltas mais rápidas em corridas", examples=[19])
    total_sprint_race_starts: int = Field(0, description="Total de largadas em Sprints", examples=[0])
    total_sprint_race_wins: int = Field(0, description="Total de vitórias em corridas Sprint", examples=[0])
    total_driver_of_the_day: int = Field(0, description="Prêmios de Piloto do Dia", examples=[0])
    total_grand_slams: int = Field(0, description="Total de Grand Slams", examples=[4])

    @property
    def team_name(self) -> Optional[str]:
        """Acesso direto compatível ao nome da equipe."""
        return self.team.name if self.team else None

    @property
    def team_color(self) -> Optional[str]:
        """Acesso direto compatível à cor da equipe."""
        return self.team.color if self.team else None

    @property
    def country_code(self) -> Optional[str]:
        """Acesso direto compatível ao código do país."""
        if isinstance(self.country, CountryDTO):
            return self.country.alpha3_code or self.country.id.upper()
        if isinstance(self.country, dict):
            return self.country.get("alpha3_code") or self.country.get("id")
        return self.country

    @model_validator(mode="before")
    @classmethod
    def _migrate_flat_fields(cls, data: Any) -> Any:
        """Adapta dicionários com campos planos antigos para a estrutura aninhada de TeamDTO e CountryDTO."""
        if isinstance(data, dict):
            # Normalizar equipe para TeamDTO
            if "team" not in data and ("team_name" in data or "team_color" in data or "team_id" in data):
                t_name = data.get("team_name")
                if t_name:
                    data["team"] = {
                        "id": data.get("team_id"),
                        "name": t_name,
                        "color": data.get("team_color"),
                    }

            # Normalizar país para CountryDTO
            if "country" not in data and ("country_code" in data or "nationality_country_id" in data):
                code = data.get("country_code") or data.get("nationality_country_id")
                if code:
                    data["country"] = {
                        "id": str(code).lower(),
                        "name": str(code),
                        "alpha3_code": str(code).upper(),
                    }
        return data
