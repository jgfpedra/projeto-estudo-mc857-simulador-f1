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
from fallback_tactical import get_fallback_tactical, build_race_context_from_state
from metrics import record_ollama_call, record_duplicate_suppressed, start_periodic_flush
from debrief import generate_and_save_debrief

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
MAX_DEBRIEF_EVENTS = 250
DEBRIEF_EVENT_TYPES = {
    "race_start", "race_end", "lap_completed", "pit_stop", "off_track",
    "on_track", "collision", "weather_changed", "tyre_worn", "race_control",
    "ai_suggestion", "ai_command",
}


def _should_stay_silent(is_real_event: bool, new_command: str, new_text: str,
                        last_command: str | None, last_text: str | None) -> bool:
    """
    Decide se o engenheiro deve ficar em silêncio (não publicar sugestão).

    Regras anti-repetição:
    - Evento real: fala se comando OU texto mudou (não engole mudança de plano).
    - Gatilho periódico: só fala se comando E texto são novos (não repete nem um nem outro).
    - Primeira mensagem: sempre fala.
    """
    if last_command is None or last_text is None:
        return False  # primeira mensagem sempre fala

    if is_real_event:
        # Evento real (ex.: rádio da equipe, saída de pista): não engole mudança de plano
        return new_command == last_command and new_text == last_text

    # Gatilho periódico (timer): silenciar se só comando OU só texto repete
    return new_command == last_command or new_text == last_text


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


def _load_race_meta(r, race_id: str) -> dict:
    """Lê os metadados usados tanto pelo acompanhamento quanto pelo debrief."""
    raw = r.get(f"race:{race_id}:meta")
    if not raw:
        return {}
    try:
        meta = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return meta if isinstance(meta, dict) else {}


def _resolve_followed_driver(r, race_id: str, default: str) -> str | None:
    """Piloto que o engenheiro acompanha naquela corrida.

    A API grava o piloto escolhido pelo jogador em ``race:<id>:meta``. Usar o
    valor da corrida é o que liga o seletor "Piloto Controlado / Focado" da UI
    ao engenheiro; o valor de ``F1_FOLLOWED_DRIVER`` fica só como fallback para
    corridas antigas ou criadas sem ``user_driver_id``.
    """
    meta = _load_race_meta(r, race_id)
    return meta.get("user_driver_id")


def run_listener(race_id: str | None, followed_driver_id: str, periodic_s: float = 10.0):
    sentinels = os.environ.get("REDIS_SENTINELS", "")
    if sentinels:
        from redis.sentinel import Sentinel
        addresses = [(host, int(port)) for host, port in
                     (item.strip().rsplit(":", 1) for item in sentinels.split(","))]
        r = Sentinel(addresses, socket_timeout=2).master_for(
            os.environ.get("REDIS_SENTINEL_MASTER", "mymaster"), decode_responses=True)
    else:
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

    # Verifica se deve usar Ollama (pode ser desabilitado via env ou Redis, padrão false)
    use_ollama_env = os.environ.get("USE_OLLAMA", "false").lower() == "true"
    # Redis pode sobrescrever o env (toggle dinâmico via API/frontend)
    use_ollama_redis = r.get("settings:use_ollama")
    use_ollama = use_ollama_redis == "true" if use_ollama_redis is not None else use_ollama_env
    if use_ollama:
        warm_up()
        print("[ai_listener] Ollama HABILITADO - modelo aquecido")
    else:
        print("[ai_listener] Ollama DESABILITADO - usando apenas fallback tático")

    # Inicia flush periódico de métricas no MLflow
    start_periodic_flush(interval_seconds=60)

    states: dict[str, LiveRaceState] = {}
    followed_by_race: dict[str, str] = {}
    last_periodic_sim_ts: dict[str, float] = {}
    # Estado anti-repetição por corrida
    last_command_by_race: dict[str, str | None] = {}
    last_text_by_race: dict[str, str | None] = {}
    # Histórico limitado para o debrief; ticks completos ficam de fora para
    # evitar crescimento de memória e prompts com milhares de posições.
    debrief_events: dict[str, list[dict]] = {}
    debrief_ai_commands: dict[str, list[dict]] = {}
    debrief_completed: set[str] = set()

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
            last_command_by_race[current_race] = None
            last_text_by_race[current_race] = None
            debrief_events[current_race] = []
            debrief_ai_commands[current_race] = []
            followed_by_race[current_race] = _resolve_followed_driver(
                r, current_race, followed_driver_id)
            print(f"[ai_listener] nova corrida detectada: {current_race} "
                  f"(seguindo {followed_by_race[current_race]})")

        followed = followed_by_race[current_race]

        try:
            event = json.loads(message["data"])
        except json.JSONDecodeError:
            print("[ai_listener] evento não é JSON válido, ignorando")
            continue

        if current_race in debrief_completed:
            continue

        event_type = event.get("type")
        if event_type in DEBRIEF_EVENT_TYPES:
            history = debrief_events[current_race]
            history.append(event)
            if len(history) > MAX_DEBRIEF_EVENTS:
                del history[:-MAX_DEBRIEF_EVENTS]
        if event_type == "ai_command":
            commands = debrief_ai_commands[current_race]
            commands.append(event)
            if len(commands) > MAX_DEBRIEF_EVENTS:
                del commands[:-MAX_DEBRIEF_EVENTS]

        if event_type == "race_end":
            print(f"[ai_listener] race_end detectado para {current_race}, gerando debrief...")
            try:
                classification = event.get("final_classification", [])
                if not isinstance(classification, list):
                    classification = []
                generate_and_save_debrief(
                    race_id=current_race,
                    race_meta=_load_race_meta(r, current_race),
                    classification=classification,
                    events=list(debrief_events[current_race]),
                    ai_commands=list(debrief_ai_commands[current_race]),
                    stats={
                        "total_time_s": event.get("total_time_s"),
                        "race_end_sim_ts": event.get("sim_ts"),
                    },
                    redis_client=r,
                )
                debrief_completed.add(current_race)
                print(f"[ai_listener] debrief gerado e salvo para {current_race}")
            except Exception as e:
                print(f"[ai_listener] ERRO ao gerar debrief: {e}")
            # Não processa mais nada após race_end
            continue

        if event.get("type") == "tick":
            sim_ts = event.get("sim_ts", 0.0)
            if int(sim_ts * 10) % 50 == 0:
                print(f"[ai_listener] tick recebido: lap={event.get('lap')} "
                      f"sim_ts={sim_ts:.1f}s")

        eventos = apply_event(state, event, followed)

        if event.get("type") == "tick":
            sim_ts = event.get("sim_ts", 0.0)
            if sim_ts - last_periodic_sim_ts[current_race] >= periodic_s:
                last_periodic_sim_ts[current_race] = sim_ts
                eventos.append(
                    f"Atualização periódica (t={sim_ts:.0f}s de simulação)")
                print(f"[ai_listener] gatilho periódico em t={sim_ts:.1f}s")

        if not followed or not should_trigger_live(eventos):
            continue

        print(f"[ai_listener] volta {state.lap}: eventos detectados, acionando agente...")
        context_text = format_live_context(state, followed, eventos)
        
        # Constrói contexto tático para fallback inteligente
        tactical_ctx = build_race_context_from_state(state, followed)

        # Verifica flag Redis dinamicamente (permite toggle sem restart)
        use_ollama_redis = r.get("settings:use_ollama")
        if use_ollama_redis is not None:
            use_ollama = use_ollama_redis == "true"

        if use_ollama:
            prompt = build_live_prompt(context_text)
            print(f"[DEBUG] contexto enviado ao modelo:\n{context_text}\n")

            model_result = call_model(prompt)

            if not model_result["ok"]:
                # Fallback tático baseado na situação real da corrida
                output = get_fallback_tactical(tactical_ctx)
                output["fallback_motivo"] = model_result["error"]
            else:
                validated = validate_agent_output(model_result["response"])
                if validated:
                    output = validated
                else:
                    # JSON inválido → fallback tático
                    output = get_fallback_tactical(tactical_ctx)
                    output["fallback_motivo"] = "resposta em formato inválido"
        else:
            # Ollama desabilitado: usa fallback direto
            output = get_fallback_tactical(tactical_ctx)
            output["fallback_motivo"] = "ollama_desabilitado"

        output["type"] = "ai_suggestion"
        output["volta"] = state.lap
        output["lap"] = state.lap
        output["driver_id"] = followed
        output["race_id"] = current_race
        output["sim_ts"] = event.get("sim_ts", last_periodic_sim_ts[current_race])

        # Anti-repetição: decide se deve ficar em silêncio
        new_command = output.get("comando", {}).get("tipo", "neutral")
        new_text = output.get("aviso", "")
        last_cmd = last_command_by_race.get(current_race)
        last_txt = last_text_by_race.get(current_race)

        # Determina se o gatilho foi evento real ou periódico
        is_real_event = any(e for e in eventos if not e.startswith("Atualização periódica"))

        if _should_stay_silent(is_real_event, new_command, new_text, last_cmd, last_txt):
            record_duplicate_suppressed()
            print(f"[ai_listener] sugestão suprimida (repetição): comando={new_command}, texto={new_text[:40]}...")
        else:
            # Atualiza estado anti-repetição
            last_command_by_race[current_race] = new_command
            last_text_by_race[current_race] = new_text

            # publica de volta no mesmo canal, para o #42 (WebSocket Gateway) repassar
            events_channel = f"race:{current_race}:events"
            r.publish(events_channel, json.dumps(output, ensure_ascii=False))
            fallback_tag = " [FALLBACK]" if output.get("fallback") else ""
            print(f"[ai_listener] sugestão publicada{fallback_tag}: {output['aviso']}")


if __name__ == "__main__":
    import sys
    raw_race_id = sys.argv[1] if len(sys.argv) > 1 else ""
    # Sem argumento (ou "all"/"*") acompanha todas as corridas via psubscribe.
    race_id = None if raw_race_id in ("", "all", "*") else raw_race_id
    driver_id = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("F1_FOLLOWED_DRIVER", "drv_02")
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    run_listener(race_id, driver_id, periodic_s=interval)
