"""Pydantic DTOs for Formula 1 seasons and FastF1 available years."""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field

from .circuit_dto import BaseDTO


class SeasonDTO(BaseDTO):
    """Informações resumidas de uma temporada de Fórmula 1."""

    year: int = Field(..., description="Ano da temporada da F1", examples=[2024])
    has_telemetry: bool = Field(
        True,
        description="Indica se há telemetria completa e dados de sessão de Live Timing suportados pelo FastF1 (2018+)",
        examples=[True],
    )
    description: Optional[str] = Field(
        None,
        description="Descrição ou informações adicionais da temporada",
        examples=["Temporada 2024 de Fórmula 1"],
    )


class SeasonsResponseDTO(BaseDTO):
    """Resposta com lista de temporadas disponíveis e metadados."""

    seasons: List[int] = Field(
        ...,
        description="Lista ordenada decrescente dos anos das temporadas com dados disponíveis no FastF1",
        examples=[[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]],
    )
    default_season: int = Field(
        2024,
        description="Temporada recomendada para seleção inicial no frontend",
        examples=[2024],
    )
    total: int = Field(
        ...,
        description="Total de temporadas disponíveis",
        examples=[9],
    )
