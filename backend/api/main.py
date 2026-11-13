"""API HTTP e ponte Redis -> WebSocket para a visualização da corrida."""
from __future__ import annotations

import asyncio
import json
import os
import anyio
import redis
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .race_manager import REDIS_URL, race_manager
from .schemas import RaceSetupRequest, RaceSetupResponse

app = FastAPI(title='F1 Simulator API')
origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:3001,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000,http://127.0.0.1:3001').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'], allow_headers=['*'])

@app.post('/races', response_model=RaceSetupResponse)
def create_race(req: RaceSetupRequest):
    try:
        race_id, track, config = race_manager.create_race(req.laps, req.track, req.year)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RaceSetupResponse(race_id=race_id, track_name=track.name, num_laps=config.num_laps)

@app.get('/races/{race_id}')
def get_race(race_id: str):
    try:
        meta = race_manager.metadata(race_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    if meta is None:
        raise HTTPException(status_code=404, detail='Corrida não encontrada')
    return meta

@app.websocket('/ws/races/{race_id}')
async def race_websocket(websocket: WebSocket, race_id: str):
    client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    pubsub = client.pubsub()
    try:
        if not await client.exists(f'race:{race_id}:meta'):
            await websocket.close(code=4404)
            return
        # Inscrever antes de ler o último estado evita perder ticks na conexão.
        await pubsub.subscribe(f'race:{race_id}:events')
        await websocket.accept()
        snapshot = await client.get(f'race:{race_id}:state')
        last_tick = -1.0
        if snapshot:
            payload = json.loads(snapshot)
            last_tick = payload['sim_ts']
            await websocket.send_json(payload)
        result = await client.get(f'race:{race_id}:result')
        if result:
            final_snapshot = await client.get(f'race:{race_id}:state')
            if final_snapshot:
                final_tick = json.loads(final_snapshot)
                if final_tick['sim_ts'] > last_tick:
                    await websocket.send_json(final_tick)
            await websocket.send_text(result)
            return

        async def forward():
            nonlocal last_tick
            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                payload = json.loads(message['data'])
                if payload.get('type') == 'tick':
                    if payload['sim_ts'] <= last_tick:
                        continue
                    last_tick = payload['sim_ts']
                await websocket.send_json(payload)
                if payload.get('type') in ('race_end', 'race_error'):
                    return

        async def wait_for_disconnect():
            while True:
                if (await websocket.receive())['type'] == 'websocket.disconnect':
                    return

        tasks = [asyncio.create_task(forward()), asyncio.create_task(wait_for_disconnect())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            # Desconexões podem cancelar o escopo ASGI durante a limpeza.
            with anyio.CancelScope(shield=True):
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except redis.RedisError:
        await websocket.close(code=1011)
    finally:
        with anyio.CancelScope(shield=True):
            await pubsub.aclose()
            await client.aclose()
