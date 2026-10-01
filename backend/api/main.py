"""Entry point da api web do simulador.

Rodar localmente (de dentro da pasta backend/):

    uvicorn api.main:app --reload --port 8000

Endpoints:
- POST /races             -> cria e inicia uma corrida, devolve {race_id, ...}
- WS   /ws/races/{race_id} -> transmite os eventos da corrida em tempo real
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .race_manager import race_manager
from .schemas import RaceSetupRequest, RaceSetupResponse

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


@app.post("/races", response_model=RaceSetupResponse)
def create_race(req: RaceSetupRequest) -> RaceSetupResponse:
    """Configura e inicia uma nova corrida.

    O front deve guardar o ``race_id`` da resposta e usá-lo para abrir a
    conexão em ``/ws/races/{race_id}``.
    """
    try:
        race_id, track_obj, config = race_manager.create_race(
            laps=req.laps, track=req.track, year=req.year
        )
    except (ValueError, Exception) as exc:  # CircuitLoadError também cai aqui
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RaceSetupResponse(
        race_id=race_id,
        track_name=track_obj.name,
        num_laps=config.num_laps,
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
    except WebSocketDisconnect:
        pass
    finally:
        race_manager.unsubscribe(race_id, queue)
