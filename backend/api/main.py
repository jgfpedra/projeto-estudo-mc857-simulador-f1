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
from database.f1results_database import AmbiguousHistoricalEvent, F1ResultsDriverDatabase
from service.driver_service import DriverService
from .providers.historical_f1results import load_historical_snapshot


driver_service = DriverService()
app = FastAPI(title='F1 Simulator API')
origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:3001,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000,http://127.0.0.1:3001').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'], allow_headers=['*'])

@app.post('/races', response_model=RaceSetupResponse)
def create_race(req: RaceSetupRequest):
    try:
        if req.year is not None and req.season is not None and req.year != req.season:
            raise ValueError('year e season devem indicar a mesma temporada')
        race_id, track, config = race_manager.create_race(
            req.laps, req.track, req.season if req.season is not None else req.year,
            num_drivers=req.num_drivers, layout_id=req.layout_id
        )
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RaceSetupResponse(race_id=race_id, track_name=track.name, num_laps=config.num_laps)

@app.get('/seasons')
def list_seasons():
    return driver_service.get_available_seasons()


@app.get('/seasons/{season}/drivers')
def list_season_drivers(season: int):
    drivers = driver_service.list_drivers(year=season, limit=None)
    return [{**driver, 'number': driver.get('number', driver.get('permanent_number'))}
            for driver in drivers]


def event_summary(event, snapshot):
    circuit_id = event.get('circuit_id')
    race = snapshot['races'].get(f"{circuit_id}:{event['season']}") if circuit_id else None
    return {key: event.get(key) for key in ('id', 'season', 'round', 'grand_prix', 'circuit_id',
            'source_circuit_name', 'source_layout_id', 'circuit_length')} | {
        'geometry_available': bool(race and race['grand_prix'] == event['grand_prix'])}


@app.get('/seasons/{season}/events')
def list_season_events(season: int):
    database = F1ResultsDriverDatabase()
    snapshot = load_historical_snapshot()
    return {'season': season, 'source': database.provenance,
            'events': [event_summary(e, snapshot) for e in database.events(season)]}


@app.get('/seasons/{season}/circuits/{circuit_id}/drivers')
def list_historical_grid(season: int, circuit_id: str, grand_prix: str | None = None):
    from database.f1results_database import race_driver_record, roster_provenance
    catalog = race_manager.catalog
    circuit = catalog.find_circuit(circuit_id) if catalog else None
    if circuit is None:
        raise HTTPException(status_code=404, detail='Circuito não encontrado no catálogo F1DB')
    database = F1ResultsDriverDatabase()
    try:
        event, roster = database.race_roster(circuit['id'], season, grand_prix=grand_prix)
    except AmbiguousHistoricalEvent as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not roster:
        raise HTTPException(status_code=404, detail='Grid histórico indisponível')
    return {'season': season, 'circuit_id': circuit['id'], 'grand_prix': event['grand_prix'],
            'source': roster_provenance(database, event),
            'drivers': [race_driver_record(d) for d in roster]}


@app.get('/circuits')
def list_circuits(season: int | None = None):
    catalog = race_manager.catalog
    if catalog is None:
        raise HTTPException(status_code=503, detail='Catálogo F1DB indisponível')
    circuits = [{'id': c['id'], 'name': c['name'], 'full_name': c['full_name'],
                 'layouts_count': len(c.get('layouts', []))} for c in catalog.circuits]
    if season is None:
        return {'catalog': catalog.provenance, 'circuits': circuits}
    database = F1ResultsDriverDatabase()
    snapshot = load_historical_snapshot()
    events = [event_summary(e, snapshot) for e in database.events(season)]
    by_id = {c['id']: c for c in circuits}
    for event in events:
        item = by_id.get(event['circuit_id'])
        if item is not None:
            item.setdefault('events', []).append(event)
    return {'catalog': catalog.provenance, 'season': season, 'source': database.provenance,
            'circuits': [c for c in circuits if c.get('events')],
            'unmapped_events': [e for e in events if e['circuit_id'] not in by_id]}


@app.get('/circuits/{circuit_id}/layouts')
def circuit_layout_history(circuit_id: str):
    catalog = race_manager.catalog
    if catalog is None:
        raise HTTPException(status_code=503, detail='Catálogo F1DB indisponível')
    circuit = catalog.find_circuit(circuit_id)
    if circuit is None:
        raise HTTPException(status_code=404, detail='Circuito não encontrado no catálogo F1DB')
    return {'circuit_id': circuit['id'], 'name': circuit['full_name'],
            'catalog': catalog.provenance, 'layouts': circuit['layouts']}


@app.get('/races/{race_id}')
def get_race(race_id: str):
    try:
        meta = race_manager.metadata(race_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    if meta is None:
        raise HTTPException(status_code=404, detail='Corrida não encontrada')
    return meta

@app.get('/races/{race_id}/snapshot')
def get_race_snapshot(race_id: str):
    try:
        snapshot = race_manager.snapshot(race_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    if snapshot is None:
        raise HTTPException(status_code=404, detail='Corrida não encontrada')
    return snapshot

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
        start_event = await client.get(f'race:{race_id}:start')
        start_sent = bool(start_event)
        if start_event:
            await websocket.send_text(start_event)
        snapshot = await client.get(f'race:{race_id}:state')
        last_tick = -1.0
        if snapshot:
            if not start_sent:
                start_event = await client.get(f'race:{race_id}:start')
                if start_event:
                    await websocket.send_text(start_event)
                    start_sent = True
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
            nonlocal last_tick, start_sent
            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                payload = json.loads(message['data'])
                if payload.get('type') == 'race_start':
                    if start_sent:
                        continue
                    start_sent = True
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
