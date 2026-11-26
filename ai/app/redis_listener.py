import os
import json
import redis

from live_context import (
    LiveRaceState,
    apply_event,
    should_trigger_live,
    format_live_context
)
from client import call_model, warm_up
from schemas import validate_agent_output, fallback_output

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


def build_live_prompt(context_text: str) -> str:
    return f"""Você é um engenheiro de pista de Fórmula 1,
    acompanhando a corrida AO VIVO.
    Responda SOMENTE em JSON válido,
    sem texto antes ou depois, exatamente neste formato:

{{
  "type": "ai_suggestion",
  "aviso": "mensagem curta e direta ao piloto, em português",
  "previsao": {{
    "pit_stop_recomendado": true ou false,
    "volta_estimada": número da volta (inteiro) ou null,
    "composto_sugerido": "SOFT"|"MEDIUM"|"HARD"|"INTERMEDIATE"|"WET" ou null
  }},
  "urgencia": "baixa" | "media" | "alta"
}}

Você acompanha posições, combustível, pneus, clima e status de pista
(saídas/retornos da pista, voltas completadas e posições).

Se houver evento de saída de pista, avise EXPLICITAMENTE no campo "aviso":
- se foi VOCÊ quem saiu ou um RIVAL;
- o lado (esquerda/direita);
- se parece leve ou grave.

Não dê instruções de pilotagem (direção, curvas, aceleração).
Se nada exige ação, diga que está tudo sob controle e use urgência baixa.

=== ESTADO ATUAL DA CORRIDA ===
{context_text}
"""


def _race_id_from_channel(channel) -> str | None:
    """Extrai o ``race_id`` de um canal ``race:<id>:events``."""
    if isinstance(channel, bytes):
        channel = channel.decode("utf-8", "ignore")
    parts = str(channel).split(":")
    if len(parts) >= 3 and parts[0] == "race" and parts[2] == "events":
        return parts[1]
    return None


def run_listener(race_id: str | None, followed_driver_id: str, periodic_s: float = 10.0):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    if race_id:
        events_channel = f"race:{race_id}:events"
        pubsub.subscribe(events_channel)
        print(f"[ai_listener] assinando {events_channel}...")
    else:
        # Sem corrida explícita: acompanha qualquer corrida criada pela API.
        pattern = "race:*:events"
        pubsub.psubscribe(pattern)
        print(f"[ai_listener] assinando padrão {pattern} (todas as corridas)...")

    warm_up()

    states: dict[str, LiveRaceState] = {}
    last_periodic_sim_ts: dict[str, float] = {}

    for message in pubsub.listen():
        if message["type"] not in ("message", "pmessage"):
            continue

        current_race = _race_id_from_channel(message.get("channel"))
        if current_race is None:
            continue
        if race_id and current_race != race_id:
            continue

        state = states.get(current_race)
        if state is None:
            state = LiveRaceState(race_id=current_race)
            states[current_race] = state
            last_periodic_sim_ts[current_race] = 0.0
            print(f"[ai_listener] nova corrida detectada: {current_race}")

        try:
            event = json.loads(message["data"])
        except json.JSONDecodeError:
            print("[ai_listener] evento não é JSON válido, ignorando")
            continue

        if event.get("type") == "tick":
            sim_ts = event.get("sim_ts", 0.0)
            if int(sim_ts * 10) % 50 == 0:
                print(f"[ai_listener] tick recebido: lap={event.get('lap')} "
                      f"sim_ts={sim_ts:.1f}s")

        eventos = apply_event(state, event, followed_driver_id)

        if event.get("type") == "tick":
            sim_ts = event.get("sim_ts", 0.0)
            if sim_ts - last_periodic_sim_ts[current_race] >= periodic_s:
                last_periodic_sim_ts[current_race] = sim_ts
                eventos.append(
                    f"Atualização periódica (t={sim_ts:.0f}s de simulação)")
                print(f"[ai_listener] gatilho periódico em t={sim_ts:.1f}s")

        if not should_trigger_live(eventos):
            continue

        print(f"[ai_listener] volta {
              state.lap}: eventos detectados, acionando agente...")
        context_text = format_live_context(state, followed_driver_id, eventos)
        prompt = build_live_prompt(context_text)
        print(f"[DEBUG] contexto enviado ao modelo:\n{context_text}\n")

        model_result = call_model(prompt)
        if not model_result["ok"]:
            output = fallback_output(model_result["error"])
        else:
            validated = validate_agent_output(model_result["response"])
            output = validated if validated else fallback_output(
                "resposta em formato inválido")

        output["type"] = "ai_suggestion"
        output["volta"] = state.lap

        # publica de volta no mesmo canal, para o #42 (WebSocket Gateway) repassar
        events_channel = f"race:{current_race}:events"
        r.publish(events_channel, json.dumps(output, ensure_ascii=False))
        print(f"[ai_listener] sugestão publicada: {output['aviso']}")


if __name__ == "__main__":
    import sys
    raw_race_id = sys.argv[1] if len(sys.argv) > 1 else ""
    # Sem argumento (ou "all"/"*") acompanha todas as corridas via psubscribe.
    race_id = None if raw_race_id in ("", "all", "*") else raw_race_id
    driver_id = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("F1_FOLLOWED_DRIVER", "drv_02")
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    run_listener(race_id, driver_id, periodic_s=interval)
