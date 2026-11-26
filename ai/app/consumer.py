"""Consume live race events and publish engineer suggestions to Redis."""
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

import redis
from redis.sentinel import Sentinel

from client import call_model
from live_context import LiveRaceState, apply_event, format_live_context
from redis_listener import build_live_prompt
from schemas import fallback_output, validate_agent_output


LOG = logging.getLogger("ai_consumer")
INTERVAL = float(os.getenv("AI_INTERVAL_SECONDS", "10"))
TERMINAL = {"race_end", "race_cancelled", "race_error"}


def redis_client():
    sentinels = os.getenv("REDIS_SENTINELS", "")
    if sentinels:
        endpoints = [(host, int(port)) for host, port in
                     (item.strip().rsplit(":", 1) for item in sentinels.split(","))]
        return Sentinel(endpoints, socket_timeout=2).master_for(
            os.getenv("REDIS_SENTINEL_MASTER", "mymaster"),
            decode_responses=True, socket_connect_timeout=2)
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"),
                                decode_responses=True, socket_connect_timeout=2)


def publish_suggestion(client, channel, race_id, driver_id, lap, sim_ts, context):
    result = call_model(build_live_prompt(context))
    output = validate_agent_output(result["response"]) if result["ok"] else None
    output = output or fallback_output(result.get("error", "resposta em formato inválido"))
    # Ignore a result that arrived after the race ended.
    snapshot = client.get(f"race:{race_id}:snapshot")
    if not snapshot or json.loads(snapshot).get("status") not in ("starting", "running"):
        return
    output.update(type="ai_suggestion", race_id=race_id, driver_id=driver_id,
                  sim_ts=sim_ts, lap=lap, volta=lap)
    client.publish(channel, json.dumps(output, ensure_ascii=False))
    LOG.info("Sugestão publicada para %s, piloto %s", race_id, driver_id)


def consume(client):
    states = {}
    with ThreadPoolExecutor(max_workers=1) as executor, client.pubsub() as pubsub:
        pubsub.psubscribe("race:*:events")
        LOG.info("Aguardando eventos das corridas")
        for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            channel = message["channel"]
            try:
                event = json.loads(message["data"])
            except (ValueError, TypeError):
                continue
            if not isinstance(event, dict) or event.get("type") == "ai_suggestion":
                continue
            race_id = channel[len("race:"):-len(":events")]
            if event.get("type") in TERMINAL:
                states.pop(race_id, None)
                continue
            item = states.get(race_id)
            if item is None:
                raw = client.get(f"race:{race_id}:meta")
                if not raw:
                    continue
                meta = json.loads(raw)
                drivers = meta.get("drivers") or []
                driver_id = meta.get("user_driver_id") or (drivers[0].get("driver_id") if drivers else None)
                if not driver_id:
                    continue
                item = states[race_id] = {
                    "state": LiveRaceState(race_id=race_id), "driver_id": driver_id,
                    "last_sim_ts": 0.0, "future": None,
                }
            if event.get("type") == "race_recovered":
                item["last_sim_ts"] = float(event.get("sim_ts", 0))
            detected = apply_event(item["state"], event, item["driver_id"])
            if event.get("type") != "tick":
                continue
            sim_ts = float(event.get("sim_ts", 0))
            if sim_ts < item["last_sim_ts"]:
                item["last_sim_ts"] = sim_ts
            if sim_ts - item["last_sim_ts"] < INTERVAL:
                continue
            future = item["future"]
            if future is not None and not future.done():
                continue
            if future is not None:
                try:
                    future.result()
                except Exception:
                    LOG.exception("Falha ao gerar sugestão para %s", race_id)
            item["last_sim_ts"] = sim_ts
            detected.append(f"Atualização periódica (t={sim_ts:.0f}s de simulação)")
            state = item["state"]
            context = format_live_context(state, item["driver_id"], detected)
            item["future"] = executor.submit(
                publish_suggestion, client, channel, race_id, item["driver_id"],
                state.lap, sim_ts, context)


def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            consume(redis_client())
        except redis.RedisError:
            LOG.exception("Redis indisponível; tentando novamente")
            time.sleep(2)


if __name__ == "__main__":
    main()
