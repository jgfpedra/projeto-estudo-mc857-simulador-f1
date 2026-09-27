"""FastAPI controller for Formula 1 seasons endpoints based on FastF1 data.

Provides routes to:
- List available season years for telemetry, live timing, and driver data
- Retrieve season metadata (default season, total seasons)
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from fastapi import APIRouter, Depends, Query

from dto.season_dto import SeasonsResponseDTO
from service.driver_service import DriverService

router = APIRouter(
    prefix="/api/v1/seasons",
    tags=["Temporadas"],
)


@lru_cache
def get_driver_service() -> DriverService:
    """Returns singleton DriverService instance used to query FastF1 seasons."""
    return DriverService()


@router.get(
    "",
    response_model=List[int],
    summary="Listar anos das temporadas disponíveis no FastF1",
    description=(
        "Retorna a lista ordenada decrescente dos anos das temporadas com dados disponíveis no FastF1. "
        "Por padrão, retorna as temporadas com suporte completo de telemetria, sessões e cores de equipe (2018 até hoje). "
        "Caso deseje todas as temporadas históricas desde 1950, utilize o parâmetro `all_historical=true`."
    ),
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]
                }
            }
        }
    },
)
def list_seasons(
    all_historical: bool = Query(
        False,
        description="Se True, retorna todas as temporadas da história da F1 (1950 até o presente). Se False, retorna apenas as temporadas com telemetria/live timing do FastF1 (2018+).",
        examples=[False],
    ),
    service: DriverService = Depends(get_driver_service),
) -> List[int]:
    """Retorna os anos das temporadas disponíveis no FastF1."""
    return service.get_available_seasons(all_historical=all_historical)


@router.get(
    "/info",
    response_model=SeasonsResponseDTO,
    summary="Obter metadados e temporadas disponíveis",
    description="Retorna lista de temporadas disponíveis juntamente com a temporada padrão recomendada e total de registros.",
)
def get_seasons_info(
    all_historical: bool = Query(
        False,
        description="Se True, inclui temporadas históricas completas",
        examples=[False],
    ),
    service: DriverService = Depends(get_driver_service),
) -> SeasonsResponseDTO:
    """Retorna objeto estruturado com temporadas disponíveis e metadados."""
    seasons = service.get_available_seasons(all_historical=all_historical)
    default_year = 2024 if 2024 in seasons else (seasons[0] if seasons else 2024)
    return SeasonsResponseDTO(
        seasons=seasons,
        default_season=default_year,
        total=len(seasons),
    )
