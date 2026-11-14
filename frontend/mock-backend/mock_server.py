"""
Servidor mock do contrato da corrida, para testar a tela do frontend sem o motor.

Implementa os mesmos endpoints que o backend real vai expor:
  GET  /circuits, /seasons, /seasons/{year}/drivers   (catálogo mínimo)
  POST /races                                         (cria e inicia a corrida)
  GET  /races/{race_id}                               (dados estáticos: pista e pilotos)
  GET  /races/{race_id}/snapshot                      (estado atual)
  WS   /ws/races/{race_id}                            (ticks a 10 Hz e eventos)

Uso (de dentro desta pasta):
  pip install -r requirements.txt
  uvicorn mock_server:app --port 8000

Variáveis de ambiente (opcionais):
  MOCK_LAPS=3       voltas das corridas criadas por POST /races
  MOCK_SPEED=2      segundos de simulação por segundo real
  MOCK_SEED=2025    semente: a mesma semente gera a mesma corrida
  MOCK_RED_FLAG=1   inclui uma bandeira vermelha
  MOCK_DEMO=1       cria ao subir uma corrida com id "demo" (abra /race-simulation/demo)
"""
from __future__ import annotations

import asyncio
import bisect
import math
import os
import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import Body, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

LAPS_DEFAULT = int(os.getenv("MOCK_LAPS", "3"))
SPEED = float(os.getenv("MOCK_SPEED", "2"))
SEED = int(os.getenv("MOCK_SEED", "2025"))
RED_FLAG = os.getenv("MOCK_RED_FLAG", "0") == "1"
DEMO = os.getenv("MOCK_DEMO", "1") == "1"

TICK_HZ = 10.0
DT = 1.0 / TICK_HZ
TRACK_LEN = 4309.0          # metros, como Interlagos
N_WP = 600
PIT_S = 20.0                # tempo na pit lane (s de simulação)
PIT_LANE_FACTOR = 0.25      # velocidade relativa dentro da pit lane
SC_FACTOR = 0.55            # velocidade relativa sob safety car
GRID_GAP_M = 8.0
TRACK_NAME = "Autódromo José Carlos Pace"
FRONTEND_ORIGIN = "http://localhost:5173"

DRIVERS: list[dict[str, Any]] = [
    dict(id="max-verstappen", abbr="VER", name="Max Verstappen", number=3, team_id="redbull", team="Red Bull Racing", color="#3671C6", country="Países Baixos", cc="NL"),
    dict(id="yuki-tsunoda", abbr="TSU", name="Yuki Tsunoda", number=22, team_id="redbull", team="Red Bull Racing", color="#3671C6", country="Japão", cc="JP"),
    dict(id="lando-norris", abbr="NOR", name="Lando Norris", number=1, team_id="mclaren", team="McLaren", color="#FF8000", country="Reino Unido", cc="GB"),
    dict(id="oscar-piastri", abbr="PIA", name="Oscar Piastri", number=81, team_id="mclaren", team="McLaren", color="#FF8000", country="Austrália", cc="AU"),
    dict(id="charles-leclerc", abbr="LEC", name="Charles Leclerc", number=16, team_id="ferrari", team="Ferrari", color="#E8002D", country="Mônaco", cc="MC"),
    dict(id="lewis-hamilton", abbr="HAM", name="Lewis Hamilton", number=44, team_id="ferrari", team="Ferrari", color="#E8002D", country="Reino Unido", cc="GB"),
    dict(id="george-russell", abbr="RUS", name="George Russell", number=63, team_id="mercedes", team="Mercedes", color="#27F4D2", country="Reino Unido", cc="GB"),
    dict(id="kimi-antonelli", abbr="ANT", name="Kimi Antonelli", number=12, team_id="mercedes", team="Mercedes", color="#27F4D2", country="Itália", cc="IT"),
    dict(id="fernando-alonso", abbr="ALO", name="Fernando Alonso", number=14, team_id="aston", team="Aston Martin", color="#229971", country="Espanha", cc="ES"),
    dict(id="lance-stroll", abbr="STR", name="Lance Stroll", number=18, team_id="aston", team="Aston Martin", color="#229971", country="Canadá", cc="CA"),
    dict(id="pierre-gasly", abbr="GAS", name="Pierre Gasly", number=10, team_id="alpine", team="Alpine", color="#FF87BC", country="França", cc="FR"),
    dict(id="franco-colapinto", abbr="COL", name="Franco Colapinto", number=43, team_id="alpine", team="Alpine", color="#FF87BC", country="Argentina", cc="AR"),
    dict(id="alexander-albon", abbr="ALB", name="Alexander Albon", number=23, team_id="williams", team="Williams", color="#64C4FF", country="Tailândia", cc="TH"),
    dict(id="carlos-sainz", abbr="SAI", name="Carlos Sainz", number=55, team_id="williams", team="Williams", color="#64C4FF", country="Espanha", cc="ES"),
    dict(id="esteban-ocon", abbr="OCO", name="Esteban Ocon", number=31, team_id="haas", team="Haas", color="#B6BABD", country="França", cc="FR"),
    dict(id="oliver-bearman", abbr="BEA", name="Oliver Bearman", number=87, team_id="haas", team="Haas", color="#B6BABD", country="Reino Unido", cc="GB"),
    dict(id="liam-lawson", abbr="LAW", name="Liam Lawson", number=30, team_id="rb", team="Racing Bulls", color="#6692FF", country="Nova Zelândia", cc="NZ"),
    dict(id="isack-hadjar", abbr="HAD", name="Isack Hadjar", number=6, team_id="rb", team="Racing Bulls", color="#6692FF", country="França", cc="FR"),
    dict(id="nico-hulkenberg", abbr="HUL", name="Nico Hülkenberg", number=27, team_id="sauber", team="Sauber", color="#52E252", country="Alemanha", cc="DE"),
    dict(id="gabriel-bortoleto", abbr="BOR", name="Gabriel Bortoleto", number=5, team_id="sauber", team="Sauber", color="#52E252", country="Brasil", cc="BR"),
]
DRIVER_BY_ID = {d["id"]: d for d in DRIVERS}


# ---------------------------------------------------------------------------
# Pista: laço fechado em metros, com comprimento TRACK_LEN
# ---------------------------------------------------------------------------

def _build_track() -> tuple[list[tuple[float, float]], list[float]]:
    raw = []
    for i in range(N_WP):
        th = 2 * math.pi * i / N_WP
        r = 1 + 0.18 * math.sin(2 * th + 0.5) + 0.10 * math.cos(3 * th)
        raw.append((1.6 * r * math.cos(th), r * math.sin(th)))
    raw.append(raw[0])

    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(raw, raw[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))

    k = TRACK_LEN / cum[-1]
    return [(x * k, y * k) for x, y in raw], [c * k for c in cum]


POINTS, CUM = _build_track()


def point_at(s: float) -> tuple[float, float, float, float, float]:
    """Posição, normal unitária e direção (graus) no ponto de comprimento s (m)."""
    s = s % TRACK_LEN
    i = min(max(bisect.bisect_right(CUM, s) - 1, 0), len(POINTS) - 2)
    seg = CUM[i + 1] - CUM[i]
    a = (s - CUM[i]) / seg if seg > 0 else 0.0
    x0, y0 = POINTS[i]
    x1, y1 = POINTS[i + 1]
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    return (
        x0 + dx * a,
        y0 + dy * a,
        -dy / length,
        dx / length,
        math.degrees(math.atan2(dy, dx)),
    )


def track_payload() -> dict[str, Any]:
    pts = [[round(x, 1), round(y, 1)] for x, y in POINTS[::1]]
    return {
        "name": TRACK_NAME,
        "length_m": TRACK_LEN,
        "start_finish_waypoint": 0,
        "waypoints": pts[:-1],  # o último ponto repete o primeiro
    }


# ---------------------------------------------------------------------------
# Simulação
# ---------------------------------------------------------------------------

@dataclass
class Car:
    idx: int                  # posição de largada (0 = pole)
    drv: dict[str, Any]
    base_lap: float
    dist: float               # metros percorridos desde a linha de chegada inicial (pode ser < 0 no grid)
    pit_at: float
    compound: str
    lane: float
    speed: float = 0.0        # m/s no último passo
    tyre_dist0: float = 0.0   # distância percorrida com o pneu atual
    pitted: bool = False
    pit_until: float = -1.0
    pit_stops: int = 0
    warned: bool = False
    finish_t: float | None = None
    t_hist: list[float] = field(default_factory=list)
    d_hist: list[float] = field(default_factory=list)


@dataclass
class RaceRun:
    race_id: str
    num_laps: int
    cars: list[Car]
    requested_weather: str
    sc_window: tuple[float, float]
    red_window: tuple[float, float] | None
    switch_t: float
    t: float = 0.0
    status: str = "GREEN"
    weather_kind: str = "DRY"
    weather_switched: bool = False
    finished: bool = False
    last_tick: dict[str, Any] | None = None
    classification: list[dict[str, Any]] | None = None
    pending: list[dict[str, Any]] = field(default_factory=list)
    subscribers: set[asyncio.Queue] = field(default_factory=set)


RACES: dict[str, RaceRun] = {}
MSG = {
    "SAFETY_CAR": "Safety car na pista",
    "RED_FLAG": "Bandeira vermelha: corrida suspensa",
    "GREEN": "Bandeira verde: corrida retomada",
}


def _new_race(race_id: str, laps: int, grid_ids: list[str], weather: str) -> RaceRun:
    rng = random.Random(f"{SEED}-{race_id}")
    total_m = laps * TRACK_LEN
    est_total_s = laps * 78.0

    cars = []
    for pos, drv_id in enumerate(grid_ids):
        cars.append(Car(
            idx=pos,
            drv=DRIVER_BY_ID[drv_id],
            base_lap=rng.uniform(77.0, 79.5),
            dist=-pos * GRID_GAP_M,
            pit_at=total_m * rng.uniform(0.35, 0.6),
            compound="SOFT" if rng.random() < 0.4 else "MEDIUM",
            lane=((pos % 5) - 2) * 5.0,
        ))

    sc_start = est_total_s * 0.3
    red = (est_total_s * 0.6, est_total_s * 0.6 + 25) if RED_FLAG else None
    return RaceRun(
        race_id=race_id,
        num_laps=laps,
        cars=cars,
        requested_weather=weather,
        sc_window=(sc_start, sc_start + 40),
        red_window=red,
        switch_t=est_total_s * 0.5,
    )


def _lap_of(run: RaceRun, c: Car) -> int:
    return min(run.num_laps, max(0, int(c.dist // TRACK_LEN)) + 1)


def _tyre_life(c: Car, run: RaceRun) -> float:
    worn = (c.dist - c.tyre_dist0) / (0.8 * run.num_laps * TRACK_LEN)
    return max(0.0, 100.0 * (1 - worn))


def _status_at(run: RaceRun, t: float) -> str:
    if run.red_window and run.red_window[0] <= t < run.red_window[1]:
        return "RED_FLAG"
    if run.sc_window[0] <= t < run.sc_window[1]:
        return "SAFETY_CAR"
    return "GREEN"


def _step(run: RaceRun) -> None:
    """Avança a simulação um passo (DT) e prepara eventos e o tick."""
    t = run.t
    total_m = run.num_laps * TRACK_LEN
    leader = max(run.cars, key=lambda c: c.dist)

    status = _status_at(run, t)
    if status != run.status:
        run.status = status
        run.pending.append({
            "type": "race_control", "sim_ts": round(t, 2), "lap": _lap_of(run, leader),
            "status": status, "message": MSG[status],
        })

    if not run.weather_switched and t >= run.switch_t:
        run.weather_switched = True
        run.weather_kind = "CLOUDY"
        run.pending.append({
            "type": "weather_changed", "sim_ts": round(t, 2), "lap": _lap_of(run, leader),
            "previous": {"kind": "DRY", "track_temp": 34.0, "rainfall": 0.0},
            "current": {"kind": "CLOUDY", "track_temp": 31.0, "rainfall": 0.0},
        })

    for c in run.cars:
        if c.finish_t is None and c.dist >= total_m:
            c.finish_t = t

        if c.finish_t is None:
            if not c.pitted and c.dist >= c.pit_at:
                c.pitted = True
                c.pit_until = t + PIT_S
                c.pit_stops += 1
                c.compound = "HARD" if c.compound != "HARD" else "MEDIUM"
                c.tyre_dist0 = c.dist
                c.warned = False
                run.pending.append({
                    "type": "pit_stop", "sim_ts": round(t, 2),
                    "driver_id": c.drv["id"], "driver_name": c.drv["name"],
                    "lap": _lap_of(run, c), "new_compound": c.compound,
                    "pit_time_s": PIT_S,
                })

            tyre_laps = (c.dist - c.tyre_dist0) / TRACK_LEN
            lap_time = c.base_lap + 0.02 * tyre_laps
            v = TRACK_LEN / lap_time
            factor = 1.0
            if status == "SAFETY_CAR":
                factor = SC_FACTOR
            if t < c.pit_until:
                factor = min(factor, PIT_LANE_FACTOR)
            if status == "RED_FLAG":
                factor = 0.0
            c.speed = v * factor
            c.dist += c.speed * DT

            life = _tyre_life(c, run)
            if not c.warned and life < 30:
                c.warned = True
                run.pending.append({
                    "type": "tyre_worn", "sim_ts": round(t, 2),
                    "driver_id": c.drv["id"], "driver_name": c.drv["name"],
                    "compound": c.compound, "tyre_life_pct": round(life, 1),
                    "age_laps": round(tyre_laps, 2),
                })
        else:
            c.speed = 0.0

        c.t_hist.append(t)
        c.d_hist.append(c.dist)

    run.t = round(t + DT, 4)


def _gap_to(leader: Car, d: float, t: float) -> float | None:
    """Tempo em que o líder passou pelo mesmo ponto em que o carro está agora."""
    idx = bisect.bisect_left(leader.d_hist, d)
    if idx >= len(leader.d_hist):
        return None
    return round(max(0.0, t - leader.t_hist[idx]), 3)


def _tick(run: RaceRun, t: float) -> dict[str, Any]:
    order = sorted(run.cars, key=lambda c: (-c.dist, c.idx))
    leader = order[0]
    positions = []
    track_temp = 34.0 - (3.0 if run.weather_kind == "CLOUDY" else 0.0) + 0.5 * math.sin(t / 30)

    for pos, c in enumerate(order, start=1):
        x, y, nx, ny, heading = point_at(c.dist)
        laps_behind = int(max(0.0, leader.dist - c.dist) // TRACK_LEN)
        if pos == 1:
            gap: float | None = 0.0
        elif laps_behind > 0 or c.dist <= 0:
            gap = None
        else:
            gap = _gap_to(leader, c.dist, t)

        positions.append({
            "driver_id": c.drv["id"],
            "position": pos,
            "lap": _lap_of(run, c),
            "position_xy": [round(x + nx * c.lane, 1), round(y + ny * c.lane, 1)],
            "speed_kmh": round(c.speed * 3.6, 1),
            "heading_deg": round(heading, 1),
            "tyre_compound": c.compound,
            "tyre_life_pct": round(_tyre_life(c, run), 1),
            "pitting": t < c.pit_until,
            "gap_to_leader_s": gap,
            "laps_behind": laps_behind,
        })

    return {
        "type": "tick",
        "sim_ts": round(t, 2),
        "lap": _lap_of(run, leader),
        "weather": {"kind": run.weather_kind, "track_temp": round(track_temp, 1), "rainfall": 0.0},
        "positions": positions,
    }


def _classification(run: RaceRun, t: float) -> list[dict[str, Any]]:
    order = sorted(run.cars, key=lambda c: (-c.dist, c.idx))
    return [{
        "position": pos,
        "driver_id": c.drv["id"],
        "driver_name": c.drv["name"],
        "laps_completed": min(run.num_laps, max(0, int(c.dist // TRACK_LEN))),
        "total_time_s": round(c.finish_t if c.finish_t is not None else t, 3),
        "best_lap_time_s": round(c.base_lap, 3),
        "pit_stops": c.pit_stops,
    } for pos, c in enumerate(order, start=1)]


def _broadcast(run: RaceRun, msg: dict[str, Any]) -> None:
    for q in list(run.subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass  # cliente lento: descarta a mensagem


async def _run_race(run: RaceRun) -> None:
    while not run.finished:
        _step(run)
        for ev in run.pending:
            _broadcast(run, ev)
        run.pending.clear()

        run.last_tick = _tick(run, run.t - DT)
        _broadcast(run, run.last_tick)

        leader = max(run.cars, key=lambda c: c.dist)
        if leader.finish_t is not None:
            run.finished = True
            run.classification = _classification(run, run.t)
            _broadcast(run, {
                "type": "race_end",
                "sim_ts": round(run.t, 2),
                "race_id": run.race_id,
                "final_classification": run.classification,
                "total_time_s": round(run.t, 3),
            })
            break

        await asyncio.sleep(DT / SPEED)


def _start(race_id: str, laps: int, grid_ids: list[str], weather: str) -> RaceRun:
    run = _new_race(race_id, laps, grid_ids, weather)
    RACES[race_id] = run
    asyncio.get_running_loop().create_task(_run_race(run))
    return run


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

app = FastAPI(title="F1 Simulator mock")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _on_startup() -> None:
    if DEMO:
        _start("demo", LAPS_DEFAULT, [d["id"] for d in DRIVERS], "dry")


@app.get("/circuits")
def list_circuits() -> list[dict[str, Any]]:
    svg = {"white-outline": f"{FRONTEND_ORIGIN}/interlagos-2.svg"}
    return [{
        "id": "interlagos",
        "name": "Interlagos",
        "full_name": TRACK_NAME,
        "city": "São Paulo",
        "country": {"name": "Brasil", "code": "BR"},
        "svg": svg,
        "current_layout_id": "interlagos-2",
        "simulable": True,
        "layouts": [{
            "id": "interlagos-2",
            "years": ["1990-2019", "2021-2026"],
            "first_year": 1990,
            "last_year": 2026,
            "length_km": TRACK_LEN / 1000,
            "turns": 15,
            "svg": svg,
            "is_current": True,
            "simulable": True,
        }],
    }]


@app.get("/seasons")
def list_seasons() -> list[int]:
    return [2025]


@app.get("/seasons/{year}/drivers")
def list_season_drivers(year: int) -> list[dict[str, Any]]:
    if year != 2025:
        raise HTTPException(404, detail=f"temporada {year} não encontrada")
    return [{
        "id": d["id"],
        "name": d["name"],
        "abbreviation": d["abbr"],
        "number": d["number"],
        "team": d["team"],
        "team_id": d["team_id"],
        "country": {"name": d["country"], "code": d["cc"]},
    } for d in DRIVERS]


@app.post("/races")
async def create_race(body: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    body = body or {}
    grid_ids = body.get("grid") or [d["id"] for d in DRIVERS]

    unknown = [g for g in grid_ids if g not in DRIVER_BY_ID]
    if unknown:
        raise HTTPException(422, detail=f"pilotos desconhecidos no grid: {', '.join(unknown)}")
    if len(set(grid_ids)) != len(grid_ids):
        raise HTTPException(422, detail="o grid contém pilotos repetidos")

    laps = int(body.get("laps", LAPS_DEFAULT))
    if not 1 <= laps <= 200:
        raise HTTPException(422, detail="o número de voltas precisa estar entre 1 e 200")

    race_id = f"race_{uuid.uuid4().hex[:8]}"
    _start(race_id, laps, grid_ids, body.get("weather", "dry"))

    warnings = []
    if body.get("stints"):
        warnings.append("stints: aceitos e validados, mas o mock ainda não aplica a estratégia.")

    return {
        "race_id": race_id,
        "ws_path": f"/ws/races/{race_id}",
        "track_name": TRACK_NAME,
        "num_laps": laps,
        "circuit_id": "interlagos",
        "layout_id": "interlagos-2",
        "grid": [
            {"position": i + 1, "driver_id": d, "name": DRIVER_BY_ID[d]["name"]}
            for i, d in enumerate(grid_ids)
        ],
        "initial_weather": {
            "requested": body.get("weather", "dry"),
            "engine_kind": "DRY",
            "rainfall_mm_h": 0.0,
        },
        "initial_tyre": body.get("initial_tyre"),
        "warnings": warnings,
    }


def _get_run(race_id: str) -> RaceRun:
    run = RACES.get(race_id)
    if run is None:
        raise HTTPException(404, detail=f"corrida {race_id} não encontrada")
    return run


@app.get("/races/{race_id}")
def get_race(race_id: str) -> dict[str, Any]:
    run = _get_run(race_id)
    return {
        "race_id": run.race_id,
        "season": 2025,
        "circuit_id": "interlagos",
        "layout_id": "interlagos-2",
        "num_laps": run.num_laps,
        "track": track_payload(),
        "drivers": [{
            "driver_id": c.drv["id"],
            "abbreviation": c.drv["abbr"],
            "name": c.drv["name"],
            "number": c.drv["number"],
            "team": c.drv["team"],
            "team_color": c.drv["color"],
            "grid_position": c.idx + 1,
        } for c in sorted(run.cars, key=lambda c: c.idx)],
    }


@app.get("/races/{race_id}/snapshot")
def get_snapshot(race_id: str) -> dict[str, Any]:
    run = _get_run(race_id)
    return {
        "race_id": run.race_id,
        "status": "finished" if run.finished else "running",
        "sim_ts": round(run.t, 2),
        "last_tick": run.last_tick,
        "classification": run.classification,
    }


@app.websocket("/ws/races/{race_id}")
async def race_ws(websocket: WebSocket, race_id: str) -> None:
    run = RACES.get(race_id)
    if run is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()

    if run.finished:
        # Corrida já encerrada: manda a classificação e fecha, como o backend real.
        await websocket.send_json({
            "type": "race_end", "sim_ts": round(run.t, 2), "race_id": run.race_id,
            "final_classification": run.classification, "total_time_s": round(run.t, 3),
        })
        await websocket.close(code=1000)
        return

    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    run.subscribers.add(queue)
    try:
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
            if msg["type"] == "race_end":
                break
        await websocket.close(code=1000)
    except Exception:
        # Cliente desconectou: nada a fazer, a corrida segue.
        pass
    finally:
        run.subscribers.discard(queue)
