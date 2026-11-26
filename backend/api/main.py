"""API HTTP e ponte Redis -> WebSocket para a visualização da corrida."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
import anyio
import redis
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from .race_manager import REDIS_URL, race_manager
from .redis_client import async_client, sync_client
from .schemas import (CoachCommandRequest, CoachCommandResponse, PitStopCancelResponse,
                      PitStopRequest, PitStopResponse, RaceSetupRequest, RaceSetupResponse)
from engine.coach_controller import CommandBus
from domain import TyreCompound
from database.f1results_database import AmbiguousHistoricalEvent, F1ResultsDriverDatabase
from service.driver_service import DriverService
from .providers.historical_f1results import load_historical_snapshot
from .providers.race_data import driver_record
from .providers.track_reference import verified_layout_ids
from storage import postgres


app = FastAPI(title='F1 Simulator API')
driver_service = DriverService(db=F1ResultsDriverDatabase() if postgres.configured() else None)

@app.on_event('startup')
def start_recovery():
    getattr(race_manager, "start_recovery", lambda: None)()
    if postgres.configured() and race_manager.catalog is not None:
        from storage.svg import warm_catalog
        warm_catalog(race_manager.catalog.circuits, verified_layout_ids(race_manager.catalog))

@app.on_event('shutdown')
def stop_recovery():
    getattr(race_manager, "stop_recovery", lambda: None)()

origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:3001,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000,http://127.0.0.1:3001').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['*'], allow_headers=['*'])

@app.post('/races', response_model=RaceSetupResponse)
def create_race(req: RaceSetupRequest):
    print(f"=== HTTP create_race: req={req.dict()} ===", flush=True)
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
                                       d.get('number', d.get('permanent_number')), d.get('team_name'),
                                       d.get('team_color'), color_source=d.get('team_color_source'))
                record['driver_id'] = driver_id
                selected_roster.append(record)
        options = {
            'selected_roster': selected_roster,
            'user_driver_id': req.user_driver_id,
            'random_seed': req.random_seed,
            'weather': req.weather.value if req.weather else None,
            'weather_change': req.weather_change.model_dump() if req.weather_change else None,
            'initial_tyre': (req.initial_tyre or (req.stints[0].compound if req.stints else None)).value
                            if req.initial_tyre or req.stints else None,
        }
        print(f"=== HTTP calling race_manager.create_race ===", flush=True)
        race_id, track, config = race_manager.create_race(
            req.laps, selected_track, season,
            num_drivers=len(req.grid) if req.grid is not None else req.num_drivers,
            layout_id=selected_layout, **{k: v for k, v in options.items() if v is not None},
        )
        print(f"=== HTTP race_manager.create_race returned: {race_id} ===", flush=True)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    warnings = ['Estratégia de stints ainda não é aplicada pela engine.'] if req.stints else []
    reference = getattr(track, 'metadata', {}).get('track_reference')
    if reference and reference['track_year'] != reference['driver_season']:
        warnings.append(f"Pilotos da temporada {reference['driver_season']}; a geometria do layout selecionado usa a referência de {reference['track_year']}.")
    return RaceSetupResponse(race_id=race_id, track_name=track.name, num_laps=config.num_laps,
                             ws_path=f"/ws/races/{race_id}", grid=req.grid or [],
                             initial_weather=req.weather.value if req.weather else 'dry', warnings=warnings)


# Task store for async race creation
_race_tasks: dict[str, dict] = {}
_task_lock = asyncio.Lock()


async def _create_race_task(task_id: str, req: RaceSetupRequest):
    """Background task to create race and update status."""
    async with _task_lock:
        _race_tasks[task_id] = {"status": "loading_circuit", "progress": 10, "message": "Baixando dados do circuito..."}

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
                                       d.get('number', d.get('permanent_number')), d.get('team_name'), d.get('team_color'))
                record['driver_id'] = driver_id
                selected_roster.append(record)
        options = {
            'selected_roster': selected_roster,
            'user_driver_id': req.user_driver_id,
            'random_seed': req.random_seed,
            'weather': req.weather.value if req.weather else None,
            'weather_change': req.weather_change.model_dump() if req.weather_change else None,
            'initial_tyre': (req.initial_tyre or (req.stints[0].compound if req.stints else None)).value
                            if req.initial_tyre or req.stints else None,
        }

        async with _task_lock:
            _race_tasks[task_id] = {"status": "loading_circuit", "progress": 30, "message": "Carregando geometria do circuito (pode demorar na primeira vez)..."}

        # Run the blocking race creation in a thread pool
        race_id, track, config = await asyncio.to_thread(
            race_manager.create_race,
            req.laps, selected_track, season,
            num_drivers=len(req.grid) if req.grid is not None else req.num_drivers,
            layout_id=selected_layout, **{k: v for k, v in options.items() if v is not None},
        )

        async with _task_lock:
            _race_tasks[task_id] = {"status": "ready", "progress": 100, "message": "Pronto!", "race_id": race_id, "track_name": track.name, "num_laps": config.num_laps}

    except Exception as exc:
        async with _task_lock:
            _race_tasks[task_id] = {"status": "error", "progress": 0, "message": str(exc)}


@app.post('/races/async', response_model=dict)
async def create_race_async(req: RaceSetupRequest, background_tasks: BackgroundTasks):
    """Inicia a criação da corrida em background e retorna um task_id para acompanhar o progresso."""
    import uuid
    task_id = str(uuid.uuid4())
    async with _task_lock:
        _race_tasks[task_id] = {"status": "starting", "progress": 0, "message": "Iniciando..."}
    background_tasks.add_task(_create_race_task, task_id, req)
    return {"task_id": task_id, "status_url": f"/races/status/{task_id}"}


@app.get('/races/status/{task_id}')
async def get_race_status(task_id: str):
    """Retorna o status da criação da corrida assíncrona."""
    async with _task_lock:
        task = _race_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return task


@app.get('/seasons')
def list_seasons():
    return driver_service.get_available_seasons()


@app.get('/seasons/{season}/drivers')
def list_season_drivers(season: int):
    drivers = driver_service.list_drivers(year=season, limit=None)
    return [{**driver, 'number': driver.get('number', driver.get('permanent_number')),
             'team': driver.get('team_name'), 'team_id': (driver.get('team') or {}).get('id'),
             'country': {'name': driver.get('country_name'), 'code': driver.get('country_code')}}
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
def list_circuits(season: int | None = None, include_unavailable: bool = False):
    catalog = race_manager.catalog
    if catalog is None:
        raise HTTPException(status_code=503, detail='Catálogo F1DB indisponível')
    available = verified_layout_ids(catalog)
    circuits = []
    for circuit in catalog.circuits:
        layouts = circuit.get('layouts', [])
        latest = max((item.get('last_year') or 0 for item in layouts), default=0)
        current_id = circuit.get('current_layout_id')
        detailed = [{**item, 'is_current': item['id'] == current_id if current_id else
                                         (item.get('last_year') or 0) == latest,
                     'simulable': item['id'] in available} for item in layouts
                    if include_unavailable or item['id'] in available]
        if postgres.configured():
            for item in detailed:
                item['svg'] = {
                    style: f"/circuits/svg/{item['id']}/{style}"
                    for style, url in (item.get('svg') or {}).items() if url
                }
        if not detailed and not include_unavailable:
            continue
        circuits.append({**circuit, 'layouts_count': len(detailed), 'layouts': detailed,
                         'simulable': any(item['simulable'] for item in detailed)})
    if season is None:
        return {'catalog': catalog.provenance, 'circuits': circuits}
    database = F1ResultsDriverDatabase()
    snapshot = load_historical_snapshot()
    events = [event_summary(e, snapshot) for e in database.events(season)]
    by_id = {c['id']: c for c in circuits}
    known_ids = {c['id'] for c in catalog.circuits}
    for event in events:
        item = by_id.get(event['circuit_id'])
        if item is not None:
            layout = catalog.find_layout(item, season)
            if include_unavailable or (layout and layout['id'] in available):
                item.setdefault('events', []).append(event)
    return {'catalog': catalog.provenance, 'season': season, 'source': database.provenance,
            'circuits': [c for c in circuits if c.get('events')],
            'unmapped_events': [e for e in events if e['circuit_id'] not in known_ids]}


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


@app.get('/circuits/svg/{layout_id}/{style}')
def circuit_svg(layout_id: str, style: str):
    catalog = race_manager.catalog
    if not postgres.configured() or catalog is None:
        raise HTTPException(404, 'Catálogo de SVG não configurado')
    layout = next((item for circuit in catalog.circuits for item in circuit.get('layouts', [])
                   if item['id'] == layout_id), None)
    url = (layout.get('svg') or {}).get(style) if layout else None
    if not url:
        raise HTTPException(404, 'SVG não encontrado')
    from storage.svg import PREFIX, get_svg
    if not url.startswith(PREFIX):
        raise HTTPException(404, 'Fonte de SVG não configurada')
    try:
        content = get_svg(layout_id, style, url)
    except (OSError, ValueError) as exc:
        # Preserve the catalog image during a transient preload or download failure.
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url)
    return Response(content=content, media_type='image/svg+xml', headers={
        'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'public, max-age=86400',
    })


@app.post('/races/{race_id}/drivers/{driver_id}/pit-stop', status_code=202, response_model=PitStopResponse)
def request_pit_stop(race_id: str, driver_id: str, req: PitStopRequest):
    try:
        race_manager.request_pit_stop(race_id, driver_id, TyreCompound(req.tyre_compound.value.upper()))
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PitStopResponse(race_id=race_id, driver_id=driver_id, tyre_compound=req.tyre_compound)


@app.delete('/races/{race_id}/drivers/{driver_id}/pit-stop', status_code=202,
            response_model=PitStopCancelResponse)
def cancel_pit_stop(race_id: str, driver_id: str):
    try:
        race_manager.cancel_pit_stop(race_id, driver_id)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PitStopCancelResponse(race_id=race_id, driver_id=driver_id)


@app.post('/races/{race_id}/drivers/{driver_id}/command', status_code=202,
          response_model=CoachCommandResponse)
def send_coach_command(race_id: str, driver_id: str, req: CoachCommandRequest):
    """Envia comando de alto nível para o engenheiro de pista do piloto.

    O comando é armazenado no Redis e lido pelo CoachController a cada tick.
    Comandos válidos: neutral, push/attack/atacar, conserve/economizar, careful/cuidado,
    defend/defender, overtake/ultrapassar, pace (usa `value` como multiplicador 0.5-1.15).
    """
    try:
        # Verifica se a corrida existe
        if not sync_client(REDIS_URL).exists(f'race:{race_id}:meta'):
            raise LookupError('Corrida não encontrada')
        # Bus do comando já existe no Redis com a corrida (criado no create_race)
        bus = CommandBus(sync_client(REDIS_URL), race_id, ttl=RACE_TTL)
        cmd = bus.push(driver_id, req.command.value, req.value, req.reason, req.issued_by)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail='Redis indisponível') from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CoachCommandResponse(
        race_id=race_id,
        driver_id=driver_id,
        command=cmd.command,
        value=cmd.value,
        reason=cmd.reason,
        issued_by=cmd.issued_by,
    )


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
    client = async_client(REDIS_URL)
    pubsub = client.pubsub()
    manager = race_manager
    attached = False
    viewer_id = uuid.uuid4().hex if getattr(manager, '_distributed', False) else None
    viewers_key = f'race:{race_id}:viewers'

    async def refresh_viewer():
        now = time.time()
        async with client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(viewers_key, '-inf', now)
            pipe.zadd(viewers_key, {viewer_id: now + 15.0})
            pipe.expire(viewers_key, 60)
            await pipe.execute()
    try:
        if not await client.exists(f'race:{race_id}:meta'):
            await websocket.close(code=4404)
            return
        # Inscrever antes de ler o último estado evita perder ticks na conexão.
        await pubsub.subscribe(f'race:{race_id}:events')
        await websocket.accept()
        if viewer_id is not None:
            await refresh_viewer()
        else:
            attached = manager.attach_viewer(race_id)
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
            if json.loads(result).get('type') == 'race_cancelled':
                await websocket.close(code=4410)
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
                if payload.get('type') == 'race_recovered':
                    last_tick = -1.0
                if payload.get('type') == 'tick':
                    if payload['sim_ts'] <= last_tick:
                        continue
                    last_tick = payload['sim_ts']
                await websocket.send_json(payload)
                if payload.get('type') == 'race_cancelled':
                    await websocket.close(code=4410)
                    return
                if payload.get('type') in ('race_end', 'race_error'):
                    return

        async def wait_for_disconnect():
            while True:
                if (await websocket.receive())['type'] == 'websocket.disconnect':
                    return

        tasks = [asyncio.create_task(forward()), asyncio.create_task(wait_for_disconnect())]
        if viewer_id is not None:
            async def heartbeat():
                while True:
                    await asyncio.sleep(5)
                    await refresh_viewer()
            tasks.append(asyncio.create_task(heartbeat()))
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
        if attached:
            manager.detach_viewer(race_id)
        with anyio.CancelScope(shield=True):
            if viewer_id is not None:
                with anyio.move_on_after(2):
                    try:
                        await client.zrem(viewers_key, viewer_id)
                    except redis.RedisError:
                        pass  # o heartbeat expira mesmo se o Redis estiver trocando de primário
            await pubsub.aclose()
            await client.aclose()
