"""Entry point da api web do simulador.

Rodar localmente (de dentro da pasta backend/):

    uvicorn api.main:app --reload --port 8000

Documentação interativa (contrato para o front): http://localhost:8000/docs

Catálogo (precisa de ``data/catalog.json`` — ``python scripts/build_catalog.py``):
- GET /circuits                  -> circuitos, países, SVG e variações de traçado
- GET /seasons                   -> temporadas disponíveis
- GET /seasons/{year}/drivers    -> pilotos de uma temporada

Corrida:
- POST /races                    -> cria e inicia uma corrida, devolve {race_id, ws_path, ...}
- WS   /ws/races/{race_id}       -> transmite os eventos em tempo real (fecha no race_end)
"""

from __future__ import annotations

import asyncio
import os
from typing import Callable, List, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import CircuitLoadError, load_track

from .catalog import Catalog, CatalogUnavailable, get_catalog
from .race_manager import race_manager
from .race_setup import CatalogRequired, SetupError, build_race_setup
from .schemas import (
    CircuitOut,
    RaceSetupRequest,
    RaceSetupResponse,
    SeasonDriverOut,
)

app = FastAPI(title="F1 Simulator API")

# Origens do front em dev (Vite) e do front "buildado" no docker-compose.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    # Guarda o event loop principal para o RaceManager poder repassar eventos
    # vindos da thread da engine de volta para as conexões websocket.
    race_manager.bind_loop(asyncio.get_running_loop())


# ---------------------------------------------------------------------------
# Dependências (sobrescritas nos testes)
# ---------------------------------------------------------------------------

def required_catalog() -> Catalog:
    try:
        return get_catalog()
    except CatalogUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def optional_catalog() -> Optional[Catalog]:
    """Para o POST /races, que funciona sem catálogo quando não usa circuito/grid."""
    try:
        return get_catalog()
    except CatalogUnavailable:
        return None


def get_track_loader() -> Callable:
    return load_track


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

@app.get("/circuits", response_model=List[CircuitOut], tags=["catálogo"])
def list_circuits(catalog: Catalog = Depends(required_catalog)):
    """Todos os circuitos, com país, cidade, SVG e variações de traçado."""
    return catalog.circuits


@app.get("/seasons", response_model=List[int], tags=["catálogo"])
def list_seasons(catalog: Catalog = Depends(required_catalog)):
    """Temporadas com pilotos cadastrados (mais recente primeiro)."""
    return catalog.season_years()


@app.get("/seasons/{year}/drivers", response_model=List[SeasonDriverOut], tags=["catálogo"])
def list_season_drivers(year: int, catalog: Catalog = Depends(required_catalog)):
    """Pilotos titulares de uma temporada (sem pilotos de teste)."""
    drivers = catalog.season_drivers(year)
    if drivers is None:
        raise HTTPException(status_code=404, detail=f"temporada {year} não encontrada")
    return drivers


# ---------------------------------------------------------------------------
# Corrida
# ---------------------------------------------------------------------------

@app.post("/races", response_model=RaceSetupResponse, tags=["corrida"])
def create_race(
    req: RaceSetupRequest,
    catalog: Optional[Catalog] = Depends(optional_catalog),
    track_loader: Callable = Depends(get_track_loader),
) -> RaceSetupResponse:
    """Configura e inicia uma nova corrida.

    Guarde o ``race_id`` e abra o WebSocket em ``ws_path``. Carregar um circuito
    real pode demorar (o FastF1 baixa os dados na 1ª vez): mostre um loading.
    """
    try:
        setup = build_race_setup(
            req,
            catalog,
            track_loader=track_loader,
            cache_dir=os.environ.get("FASTF1_CACHE_DIR"),
        )
    except SetupError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CatalogRequired as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CircuitLoadError as exc:
        raise HTTPException(status_code=502, detail=f"falha ao carregar o circuito no FastF1: {exc}") from exc

    race_id = race_manager.create_race(setup)

    return RaceSetupResponse(
        race_id=race_id,
        ws_path=f"/ws/races/{race_id}",
        track_name=setup.track.name,
        num_laps=setup.num_laps,
        circuit_id=setup.circuit_id,
        layout_id=setup.layout_id,
        grid=setup.grid,
        initial_weather=setup.initial_weather,
        initial_tyre=setup.initial_tyre,
        warnings=setup.warnings,
    )


@app.websocket("/ws/races/{race_id}")
async def race_websocket(websocket: WebSocket, race_id: str) -> None:
    if not race_manager.exists(race_id):
        # 4404: código de fechamento customizado (faixa 4000-4999 é livre).
        await websocket.close(code=4404)
        return

    await websocket.accept()
    queue = race_manager.subscribe(race_id)
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
            if payload.get("type") == "race_end":
                await websocket.close(code=1000)  # corrida acabou: encerra o stream
                break
    except WebSocketDisconnect:
        pass
    finally:
        race_manager.unsubscribe(race_id, queue)
