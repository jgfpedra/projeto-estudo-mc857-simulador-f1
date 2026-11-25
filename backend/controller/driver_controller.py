"""FastAPI controller for F1 drivers endpoints.

Provides routes to:
- List drivers for a given season year with team names and team colors
- Retrieve detailed driver profile by ID or 3-letter code
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from dto.driver_dto import DriverDTO
from service.driver_service import DriverService


router = APIRouter(
    prefix="/api/v1/drivers",
    tags=["Pilotos"],
)


@lru_cache
def get_driver_service() -> DriverService:
    """Returns the singleton DriverService instance."""
    return DriverService()


@router.get(
    "",
    response_model=List[DriverDTO],
    summary="Listar pilotos de uma temporada com equipe e cor",
    description=(
        "Retorna a lista de pilotos da Fórmula 1 para o ano solicitado pelo frontend, "
        "incluindo o nome da equipe e a cor hexadecimal oficial de cada construtor via FastF1."
    ),
)
def list_drivers(
    year: Optional[int] = Query(
        None,
        description="Ano da temporada da F1 (ex: 2024, 2023). Se omitido, retorna 2024 por padrão.",
        examples=[2024],
    ),
    query: Optional[str] = Query(
        None,
        description="Termo para buscar por nome, sobrenome, equipe ou sigla (ex: 'Norris', 'Ferrari', 'HAM')",
    ),
    nationality: Optional[str] = Query(
        None,
        description="Filtro pelo código de país/nacionalidade (ex: 'GBR', 'MON', 'NED')",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=1000,
        description="Limite de registros retornados (paginação)",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Número de registros a pular (paginação)",
    ),
    service: DriverService = Depends(get_driver_service),
) -> List[DriverDTO]:
    """Retorna pilotos com base no ano e filtros informados."""
    year_val = year if isinstance(year, int) else None
    query_val = query if isinstance(query, str) else None
    nationality_val = nationality if isinstance(nationality, str) else None
    limit_val = limit if isinstance(limit, int) else 50
    offset_val = offset if isinstance(offset, int) else 0

    try:
        drivers = service.list_drivers(
            year=year_val,
            query=query_val,
            nationality=nationality_val,
            limit=limit_val,
            offset=offset_val,
        )
        return [DriverDTO.model_validate(d) for d in drivers]
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )


@router.get(
    "/seasons",
    response_model=List[int],
    summary="Listar anos das temporadas disponíveis no FastF1",
    description="Retorna a lista ordenada decrescente dos anos das temporadas com dados disponíveis no FastF1 (2018 até a atual).",
)
def list_driver_seasons(
    all_historical: bool = Query(
        False,
        description="Se True, retorna todas as temporadas desde 1950. Se False, retorna apenas temporadas suportadas pelo FastF1 (2018+).",
    ),
    service: DriverService = Depends(get_driver_service),
) -> List[int]:
    """Retorna os anos das temporadas disponíveis para consulta de pilotos."""
    return service.get_available_seasons(all_historical=all_historical)


@router.get(
    "/{driver_id}",
    response_model=DriverDTO,
    summary="Obter perfil, equipe e estatísticas de um piloto",
    description="Retorna as informações completas de um piloto pelo seu ID ou sigla oficial de 3 letras para a temporada solicitada.",
    responses={
        404: {"description": "Piloto não encontrado"},
    },
)
def get_driver(
    driver_id: str,
    year: Optional[int] = Query(
        None,
        description="Ano da temporada para obter a equipe e número correspondentes (ex: 2024)",
        examples=[2024],
    ),
    service: DriverService = Depends(get_driver_service),
) -> DriverDTO:
    """Retorna dados de um piloto pelo ID ou sigla."""
    year_val = year if isinstance(year, int) else None
    driver = service.get_driver(driver_id=driver_id, year=year_val)

    if not driver:
        raise HTTPException(
            status_code=404,
            detail=f"Piloto '{driver_id}' não encontrado para a temporada solicitada.",
        )

    return DriverDTO.model_validate(driver)
