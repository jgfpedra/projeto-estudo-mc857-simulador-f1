#!/usr/bin/env python3
"""Eventos aleatórios para exercitar a IA ao vivo.

O simulador real só gera evento de clima/pneu/pit em corridas longas. Numa
corrida curta (2–3 voltas) o engenheiro acaba repetindo "defenda" porque o
cenário quase não muda. Este script publica vários tipos de eventos em
``race:<id>:events`` em intervalos aleatórios, só para dar assunto novo à IA.

Importante: **não altera física, classificação nem resultado**. É um recurso de
demo/teste, ativado com ``--random-events`` no ``run_live_compare.py``.

Uso direto:
    python backend/scripts/visualization/random_events.py --race-id race_abc
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Rádio da equipe (evento race_radio) - já existia
RADIO_MESSAGES: list[tuple[str, str]] = [
    ("ataque", "O rival à frente está perdendo rendimento; é hora de atacar."),
    ("ataque", "Janela de DRS aberta na reta principal; prepare a ultrapassagem."),
    ("ataque", "O rival à frente está com o pneu traseiro no limite; pressione."),
    ("defesa", "O carro atrás está dentro do DRS; prepare-se para defender."),
    ("defesa", "Rival colado atrás; segure a linha e não deixe espaço."),
    ("defesa", "A diferença para o carro de trás caiu; defenda a posição."),
    ("economia", "A equipe pede economia de combustível até a próxima volta."),
    ("economia", "Pneu traseiro degradando; administre o ritmo neste stint."),
    ("cautela", "Detritos no setor 2; reduza o ritmo e evite a linha suja."),
    ("cautela", "Pista escorregadia na saída da última curva; cuidado."),
    ("cautela", "Bandeira amarela virtual no setor 1; mantenha a cautela."),
    ("info", "Pista seca e estável; mantenha o plano atual."),
    ("info", "Rival à frente entrou nos boxes; a janela está aberta."),
    ("info", "Previsão de chuva leve em cinco minutos; fique atento."),
    ("info", "Combustível dentro do plano; sem necessidade de economizar agora."),
]

# Novos tipos de evento para variar o contexto da IA
OFF_TRACK_MESSAGES = [
    ("esquerda", "leve", "Você saiu da pista à esquerda, leve, perdeu 0.3s"),
    ("direita", "leve", "Você saiu da pista à direita, leve, perdeu 0.2s"),
    ("esquerda", "grave", "Você saiu da pista à esquerda, grave, brita, perdeu 1.5s"),
    ("direita", "grave", "Você saiu da pista à direita, grave, grama, perdeu 1.2s"),
]

TYRE_WORN_COMPOUNDS = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
TYRE_WORN_LIFE = [15, 20, 25, 30, 35]

WEATHER_CHANGES = [
    ("DRY", "CLOUDY"),
    ("CLOUDY", "DAMP"),
    ("DAMP", "WET"),
    ("WET", "DAMP"),
    ("DAMP", "CLOUDY"),
    ("CLOUDY", "DRY"),
]

PIT_STOP_COMPOUNDS = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]

SAFETY_CAR_MESSAGES = [
    ("SAFETY_CAR", "Safety car na pista, agrupe-se"),
    ("VSC", "Virtual safety car, mantenha delta"),
    ("GREEN", "Bandeira verde, corrida relargada"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publica avisos de rádio aleatórios para a IA de uma corrida."
    )
    parser.add_argument("--race-id", required=True, help="corrida alvo")
    parser.add_argument("--redis-url", default=REDIS_URL, help="Redis (padrão: %(default)s)")
    parser.add_argument("--seed", type=int, default=None, help="semente do sorteio")
    parser.add_argument("--min-interval", type=float, default=10.0,
                        help="intervalo mínimo em segundos (padrão: 10)")
    parser.add_argument("--max-interval", type=float, default=22.0,
                        help="intervalo máximo em segundos (padrão: 22)")
    parser.add_argument("--max-events", type=int, default=0,
                        help="limite de eventos (0 = sem limite)")
    parser.add_argument("--max-duration-s", type=float, default=1800.0,
                        help="duração máxima em segundos (padrão: 1800)")
    args = parser.parse_args()
    if args.min_interval <= 0 or args.max_interval < args.min_interval:
        parser.error("intervalos inválidos: use 0 < min <= max")
    if args.max_duration_s <= 0:
        parser.error("--max-duration-s deve ser positivo")
    return args


def build_radio_event(rng: random.Random, race_id: str, lap: int = 0) -> dict:
    """Sorteia um aviso de rádio no formato consumido por ``live_context``."""
    state, message = rng.choice(RADIO_MESSAGES)
    return {
        "type": "race_radio",
        "race_id": race_id,
        "state": state,
        "message": message,
        "lap": int(lap),
    }


def build_off_track_event(rng: random.Random, race_id: str, lap: int = 0) -> dict:
    """Gera evento de saída de pista."""
    side, severity, message = rng.choice(OFF_TRACK_MESSAGES)
    distance = rng.uniform(0.5, 3.0) if severity == "leve" else rng.uniform(3.0, 8.0)
    speed = rng.uniform(20, 50)
    return {
        "type": "off_track",
        "race_id": race_id,
        "driver_id": "drv_02",  # piloto acompanhado
        "driver_name": "DRV_02",
        "side": side,
        "severity": severity,
        "distance_m": round(distance, 1),
        "speed_mps": round(speed, 1),
        "lap": int(lap),
        "message": message,
    }


def build_tyre_worn_event(rng: random.Random, race_id: str, lap: int = 0) -> dict:
    """Gera evento de pneu crítico."""
    compound = rng.choice(TYRE_WORN_COMPOUNDS)
    life = rng.choice(TYRE_WORN_LIFE)
    return {
        "type": "tyre_worn",
        "race_id": race_id,
        "driver_id": "drv_02",
        "compound": compound,
        "tyre_life_pct": life,
        "lap": int(lap),
    }


def build_weather_changed_event(rng: random.Random, race_id: str, lap: int = 0) -> dict:
    """Gera evento de mudança de clima."""
    prev, curr = rng.choice(WEATHER_CHANGES)
    return {
        "type": "weather_changed",
        "race_id": race_id,
        "previous": {"kind": prev},
        "current": {"kind": curr, "track_temp": rng.randint(25, 45), "grip_factor": round(rng.uniform(0.7, 1.0), 2)},
        "lap": int(lap),
    }


def build_pit_stop_event(rng: random.Random, race_id: str, lap: int = 0) -> dict:
    """Gera evento de pit stop (rival ou piloto acompanhado)."""
    driver_id = rng.choice(["drv_02", "drv_01", "drv_03", "drv_04"])
    compound = rng.choice(PIT_STOP_COMPOUNDS)
    return {
        "type": "pit_stop",
        "race_id": race_id,
        "driver_id": driver_id,
        "new_compound": compound,
        "pit_time_s": round(rng.uniform(20, 28), 1),
        "lap": int(lap),
    }


def build_safety_car_event(rng: random.Random, race_id: str, lap: int = 0) -> dict:
    """Gera evento de safety car / VSC / bandeira verde."""
    status, message = rng.choice(SAFETY_CAR_MESSAGES)
    return {
        "type": "race_control",
        "race_id": race_id,
        "status": status,
        "message": message,
        "lap": int(lap),
    }


EVENT_BUILDERS = [
    (build_radio_event, 0.40),           # 40% rádio
    (build_off_track_event, 0.15),       # 15% saída de pista
    (build_tyre_worn_event, 0.15),       # 15% pneu crítico
    (build_weather_changed_event, 0.10), # 10% mudança de clima
    (build_pit_stop_event, 0.10),        # 10% pit stop
    (build_safety_car_event, 0.10),      # 10% safety car/VSC
]


def pick_interval(rng: random.Random, min_interval: float, max_interval: float) -> float:
    return rng.uniform(min_interval, max_interval)


def _lap_of(r: redis.Redis, race_id: str) -> int:
    try:
        raw = r.get(f"race:{race_id}:state")
        if raw:
            return int(json.loads(raw).get("lap", 0) or 0)
    except (TypeError, ValueError, json.JSONDecodeError, redis.RedisError):
        pass
    return 0


def _race_started(r: redis.Redis, race_id: str) -> bool:
    """A corrida só larga quando o viz conecta e o status vira 'running'.

    O `race:<id>:state` existe mesmo com carros no grid (status='starting').
    O rádio deve esperar o status 'running' no snapshot.
    """
    try:
        raw = r.get(f"race:{race_id}:snapshot")
        if raw:
            snap = json.loads(raw)
            return snap.get("status") == "running"
    except (TypeError, ValueError, json.JSONDecodeError, redis.RedisError):
        pass
    return False


def run() -> int:
    args = parse_args()
    r = redis.Redis.from_url(args.redis_url, decode_responses=True,
                             socket_connect_timeout=2)
    try:
        r.ping()
    except redis.RedisError as exc:
        print(f"[random_events] Redis indisponível: {exc}", file=sys.stderr)
        return 1

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    channel = f"race:{args.race_id}:events"
    started = time.monotonic()
    sent = 0
    print(f"[random_events] {args.race_id}: rádio aleatório em {channel} "
          f"({args.min_interval:.0f}–{args.max_interval:.0f}s)")

    try:
        while True:
            if r.exists(f"race:{args.race_id}:result"):
                print("[random_events] corrida encerrada, parando.")
                break
            if args.max_events and sent >= args.max_events:
                print(f"[random_events] limite de {args.max_events} eventos atingido.")
                break
            if time.monotonic() - started >= args.max_duration_s:
                print("[random_events] duração máxima atingida, parando.")
                break

            if not _race_started(r, args.race_id):
                # A corrida fica no grid até o visualizador conectar. Rádio
                # antes da largada só confundiria o engenheiro.
                time.sleep(1.0)
                continue

            delay = pick_interval(rng, args.min_interval, args.max_interval)
            time.sleep(delay)
            if r.exists(f"race:{args.race_id}:result"):
                print("[random_events] corrida encerrada, parando.")
                break

            # Escolhe tipo de evento baseado nos pesos
            r_val = rng.random()
            cum = 0.0
            chosen_builder = build_radio_event
            for builder, weight in EVENT_BUILDERS:
                cum += weight
                if r_val <= cum:
                    chosen_builder = builder
                    break

            event = chosen_builder(rng, args.race_id, lap=_lap_of(r, args.race_id))
            r.publish(channel, json.dumps(event, ensure_ascii=False))
            sent += 1
            # Log amigável por tipo
            etype = event["type"]
            if etype == "race_radio":
                print(f"[random_events] {sent:02d} (rádio {event['state']}): {event['message']}")
            elif etype == "off_track":
                print(f"[random_events] {sent:02d} (off_track {event['side']} {event['severity']}): {event['message']}")
            elif etype == "tyre_worn":
                print(f"[random_events] {sent:02d} (tyre_worn {event['compound']} {event['tyre_life_pct']}%)")
            elif etype == "weather_changed":
                print(f"[random_events] {sent:02d} (weather {event['previous']['kind']}->{event['current']['kind']})")
            elif etype == "pit_stop":
                print(f"[random_events] {sent:02d} (pit_stop {event['driver_id']} {event['new_compound']})")
            elif etype == "race_control":
                print(f"[random_events] {sent:02d} (race_control {event['status']}): {event['message']}")
            else:
                print(f"[random_events] {sent:02d} ({etype})")
    except KeyboardInterrupt:
        print("\n[random_events] interrompido.")
    finally:
        r.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
