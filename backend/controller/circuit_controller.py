"""FastAPI controller for F1 circuit layout evolution and SVG endpoints.

Provides routes to:

- List all circuits with summary of layout evolutions
- Retrieve a single circuit with all chronological layouts
- Retrieve layouts and active years
- Serve or redirect to layout SVG graphics on GitHub
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from dto.circuit_dto import (
    CircuitDTO,
    CircuitLayoutDTO,
    CircuitSummaryDTO,
)
from service.circuit_service import CircuitService


router = APIRouter(
    prefix="/api/v1/circuits",
    tags=["Circuitos e Layouts"],
)


@lru_cache
def get_circuit_service() -> CircuitService:
    """Returns the singleton CircuitService instance."""
    return CircuitService()


@router.get(
    "",
    response_model=List[CircuitSummaryDTO],
    summary="Listar todos os circuitos com resumo de layouts",
    description="Retorna uma lista resumida de todos os circuitos da F1 com número de layouts e layout atual.",
)
def list_circuits(
    service: CircuitService = Depends(get_circuit_service),
) -> List[CircuitSummaryDTO]:
    """Retorna uma lista resumida de todos os circuitos da F1 com número de layouts e layout atual."""
    try:
        circuits = service.list_circuits()
        return [CircuitSummaryDTO.model_validate(c) for c in circuits]
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )


@router.get(
    "/{circuit_id}",
    response_model=CircuitDTO,
    summary="Obter detalhes do circuito e evolução completa de layouts",
    description="Retorna os dados completos do circuito e sua lista de layouts históricos ordenados por ano.",
    responses={
        404: {"description": "Circuito não encontrado"},
    },
)
def get_circuit(
    circuit_id: str,
    service: CircuitService = Depends(get_circuit_service),
) -> CircuitDTO:
    """Retorna os dados completos do circuito e sua lista de layouts históricos ordenados por ano."""
    circuit = service.get_circuit(circuit_id)

    if not circuit:
        raise HTTPException(
            status_code=404,
            detail=f"Circuito '{circuit_id}' não encontrado.",
        )

    return CircuitDTO.model_validate(circuit)


@router.get(
    "/{circuit_id}/layouts",
    response_model=List[CircuitLayoutDTO],
    summary="Listar evolução cronológica dos layouts de um circuito",
    description="Retorna o histórico de layouts do circuito (anos de uso, extensão, curvas, links SVG).",
    responses={
        404: {"description": "Circuito não encontrado"},
    },
)
def get_circuit_layouts(
    circuit_id: str,
    service: CircuitService = Depends(get_circuit_service),
) -> List[CircuitLayoutDTO]:
    """Retorna o histórico de layouts do circuito (anos de uso, extensão, curvas, links SVG)."""
    layouts = service.get_layouts(circuit_id)

    if layouts is None:
        raise HTTPException(
            status_code=404,
            detail=f"Circuito '{circuit_id}' não encontrado.",
        )

    return [CircuitLayoutDTO.model_validate(l) for l in layouts]


@router.get(
    "/{circuit_id}/layouts/{layout_id}",
    response_model=CircuitLayoutDTO,
    summary="Obter dados de um layout específico",
    description="Retorna informações detalhadas de um layout específico.",
    responses={
        404: {"description": "Layout não encontrado"},
    },
)
def get_circuit_layout(
    circuit_id: str,
    layout_id: str,
    service: CircuitService = Depends(get_circuit_service),
) -> CircuitLayoutDTO:
    """Retorna informações detalhadas de um layout específico."""
    layout = service.get_layout(circuit_id, layout_id)

    if not layout:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Layout '{layout_id}' não encontrado "
                f"para o circuito '{circuit_id}'."
            ),
        )

    return CircuitLayoutDTO.model_validate(layout)


@router.get(
    "/{circuit_id}/layouts/{layout_id}/svg",
    summary="Redirecionar para o SVG oficial no GitHub do F1DB",
    description="Redireciona (HTTP 307) para a URL do arquivo SVG vetorial oficial do layout hospedado no GitHub.",
    response_class=RedirectResponse,
    status_code=307,
    responses={
        307: {"description": "Redirecionamento temporário para a URL do arquivo SVG no GitHub"},
        404: {"description": "SVG não encontrado para o layout ou estilo solicitado"},
    },
)
def get_layout_svg(
    circuit_id: str,
    layout_id: str,
    style: str = Query(
        "white-outline",
        description=(
            "Estilo do SVG: 'white-outline', 'black-outline', "
            "'white' ou 'black'"
        ),
    ),
    service: CircuitService = Depends(get_circuit_service),
) -> RedirectResponse:
    """Redireciona para a URL direta do SVG vetorial hospedado no GitHub do F1DB."""
    svg_url = service.get_layout_svg_url(
        circuit_id,
        layout_id,
        style=style,
    )

    if not svg_url:
        raise HTTPException(
            status_code=404,
            detail=(
                f"SVG para layout '{layout_id}' "
                f"estilo '{style}' não encontrado."
            ),
        )

    return RedirectResponse(
        url=svg_url,
        status_code=307,
    )