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
from service.driver_service import DriverService
from .providers.race_data import driver_record

app = FastAPI(title='F1 Simulator API')
driver_service = DriverService()
origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:3001,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000,http://127.0.0.1:3001').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'], allow_headers=['*'])

@app.post('/races', response_model=RaceSetupResponse)
def create_race(req: RaceSetupRequest):
    try:
        if req.year is not None and req.season is not None and req.year != req.season:
            raise ValueError('year e season devem indicar a mesma temporada')
        season = req.season if req.season is not None else req.year
        if req.circuit and req.track and req.circuit.id != req.track:
            raise ValueError('Informe um único circuito.')
        selected_track = req.circuit.id if req.circuit else req.track
        selected_layout = req.circuit.layout_id if req.circuit else req.layout_id
        selected_roster = None
        if req.grid is not None:
            if season is None or len(set(req.grid)) != len(req.grid):
                raise ValueError('Informe a temporada e pilotos diferentes para o grid.')
            available = {d['id']: d for d in driver_service.list_drivers(year=season, limit=None)}
            missing = [driver for driver in req.grid if driver not in available]
            if missing:
                raise ValueError('Pilotos indisponíveis nesta temporada: ' + ', '.join(missing))
            selected_roster = []
            for driver_id in req.grid:
                d = available[driver_id]
                record = driver_record(d.get('abbreviation') or '', d.get('name') or driver_id,
                                       d.get('permanent_number'), d.get('team_name'), d.get('team_color'))
                record['driver_id'] = driver_id
                selected_roster.append(record)
        options = {
            'selected_roster': selected_roster,
            'weather': req.weather.value if req.weather else None,
            'weather_change': req.weather_change.model_dump() if req.weather_change else None,
            'initial_tyre': req.initial_tyre.value if req.initial_tyre else None,
        }
        race_id, track, config = race_manager.create_race(
            req.laps, selected_track, season,
            num_drivers=len(req.grid) if req.grid is not None else req.num_drivers,
            layout_id=selected_layout, **{k: v for k, v in options.items() if v is not None},
        )
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RaceSetupResponse(race_id=race_id, track_name=track.name, num_laps=config.num_laps,
                             ws_path=f"/ws/races/{race_id}", grid=req.grid or [],
                             initial_weather=req.weather.value if req.weather else 'dry',
                             warnings=['Estratégia de stints ainda não é aplicada pela engine.'] if req.stints else [])

@app.get('/circuits')
def list_circuits():
    catalog = race_manager.catalog
    if catalog is None:
        raise HTTPException(status_code=503, detail='Catálogo F1DB indisponível')
    circuits = []
    for c in catalog.circuits:
        layouts = c.get('layouts', [])
        latest = max((item.get('last_year') or 0 for item in layouts), default=0)
        detailed = [{**item, 'is_current': (item.get('last_year') or 0) == latest,
                     'simulable': (item.get('last_year') or 0) >= 2018} for item in layouts]
        circuits.append({**c, 'layouts_count': len(layouts), 'layouts': detailed,
                         'simulable': any(item['simulable'] for item in detailed)})
    return {'catalog': catalog.provenance, 'circuits': circuits}


@app.get('/seasons')
def seasons():
    return driver_service.get_available_seasons()


@app.get('/seasons/{year}/drivers')
def season_drivers(year: int):
    drivers = driver_service.list_drivers(year=year, limit=None)
    return [{'id': d['id'], 'name': d.get('name'), 'abbreviation': d.get('abbreviation'),
             'number': d.get('permanent_number'), 'team': d.get('team_name'),
             'team_id': (d.get('team') or {}).get('id'),
             'country': {'name': None, 'code': d.get('country_code')}} for d in drivers]



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
