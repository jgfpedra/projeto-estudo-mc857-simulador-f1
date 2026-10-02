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

=== ESTADO ATUAL DA CORRIDA ===
{context_text}
"""


def run_listener(race_id: str, followed_driver_id: str):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    events_channel = f"race:{race_id}:events"
    pubsub.subscribe(events_channel)

    print(f"[ai_listener] assinando {events_channel}...")
    warm_up()

    state = LiveRaceState(race_id=race_id)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            event = json.loads(message["data"])
        except json.JSONDecodeError:
            print("[ai_listener] evento não é JSON válido, ignorando")
            continue

        eventos = apply_event(state, event)

        if not should_trigger_live(eventos):
            continue

        print(f"[ai_listener] volta {
              state.lap}: eventos detectados, acionando agente...")
        context_text = format_live_context(state, followed_driver_id, eventos)
        prompt = build_live_prompt(context_text)

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
        r.publish(events_channel, json.dumps(output, ensure_ascii=False))
        print(f"[ai_listener] sugestão publicada: {output['aviso']}")


if __name__ == "__main__":
    import sys
    race_id = sys.argv[1] if len(sys.argv) > 1 else "race_001"
    driver_id = sys.argv[2] if len(sys.argv) > 2 else "drv_01"
    run_listener(race_id, driver_id)
