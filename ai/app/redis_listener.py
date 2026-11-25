"""Serviço de IA ao vivo: escuta a corrida no Redis e publica sugestões.

Dois modos:

- **control**: assina ``race:control`` e inicia um listener para cada corrida
  criada pela API (``POST /races``). É o modo usado no fluxo ao vivo do viz3d.
- **single**: ``python redis_listener.py <race_id> <driver_id> [periodic_s]``,
  para testes manuais de uma corrida específica.

A IA produz dois tipos de saída no canal ``race:<id>:events``:

- ``ai_suggestion`` — texto curto para o HUD (o engenheiro falando);
- ``ai_command`` (via ``POST /races/{id}/commands``) — comando de alto nível
  que altera o carro acompanhado (pace, pneu, cuidado, defesa...).
"""

from __future__ import annotations

import json
import os
import random
import sys
import threading
import time

import redis
import requests

from live_context import (
    LiveRaceState,
    apply_event,
    format_live_context,
    lap_urgency_floor,
    max_urgency,
)
from client import call_model, warm_up
from schemas import validate_agent_output, fallback_output

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")

CONTROL_CHANNEL = "race:control"
# Piso de tempo simulado entre duas chamadas ao LLM. Eventos continuam sendo
# acumulados; o que se evita é uma chamada por tick. O modelo local leva mais
# que isso por chamada, então na prática ele roda quase de forma contínua.
# Intervalo mínimo entre chamadas ao LLM (evita flood de ticks)
MIN_TRIGGER_INTERVAL_S = 10.0
# Intervalo base do gatilho periódico (com jitter 0.75–1.35x)
# Aumentado para 60s para não spammar quando a corrida está estável
# Só dispara se passou tempo suficiente desde último evento tático real
PERIODIC_TRIGGER_S = 60.0


def build_live_prompt(context_text: str) -> str:
    return f"""Você é o ENGENHEIRO DE PISTA do piloto A. Silva (drv_02), carro #2.
Você fala DIRETAMENTE COM ELE pelo rádio. Use "você", "seu", "sua posição".

Responda SOMENTE em JSON válido, sem texto antes ou depois, exatamente neste formato:

{{
  "type": "ai_suggestion",
  "aviso": "mensagem curta e direta AO PILOTO ACOMPANHADO (drv_02), em português, nunca null, máx 20 palavras",
  "previsao": {{
    "pit_stop_recomendado": true ou false,
    "volta_estimada": número da volta (inteiro) ou null,
    "composto_sugerido": "SOFT"|"MEDIUM"|"HARD"|"INTERMEDIATE"|"WET" ou null
  }},
  "urgencia": "baixa" | "media" | "alta",
  "comando": {{
    "tipo": "push" | "overtake" | "defend" | "conserve" | "careful" | "neutral",
    "valor": número (use 0 quando não se aplicar),
    "motivo": "uma frase curta explicando por que o comando foi escolhido"
  }}
}}

REGRA CRÍTICA DO "aviso": 
- Fale COM o drv_02 (A. Silva). Use "você", "seu carro", "sua posição", "seu pneu".
- NUNCA cite nome/número de OUTRO piloto no aviso (ex.: NÃO diga "Piloto 03 está...").
- Se o evento for de RIVAL, diga "O rival à frente..." ou "O carro atrás...".
- NUNCA use null, "" ou "nenhum aviso". O aviso deve combinar com o comando.
- **PROIBIDO**: vocativos soltos como "seu!", "seu [nome]", "cara!", "piloto!" — use frases completas: "Mantenha a velocidade, você lidera" (não "Mantenha a velocidade, seu!").

Comandos de alto nível (para o SEU carro, drv_02):
- "push": você ataca, anda no limite;
- "overtake": você prepara ultrapassagem no rival à frente;
- "defend": você segura a posição contra quem vem atrás;
- "conserve": você economiza pneu/combustível;
- "careful": você reduz ritmo (pista suja, sua saída de pista, clima);
- "neutral": sem alteração.

Como escolher o comando PARA O drv_02:
- pneu/combustível OK, rival à frente PERTO e você ATRÁS: "overtake" ou "push";
- pneu/combustível OK, rival ATRÁS PERTO e você NA FRENTE: "defend";
- SEU pneu < 35% ou SEU combustível baixo: "conserve";
- pneu de RIVAL próximo crítico ou rival nos boxes: "push" ou "overtake";
- SUA saída de pista, pista suja ou clima ruim: "careful";
- nada exige ação: "neutral". Não use "conserve" por padrão.

VARIAÇÃO: não repita a última mensagem nem o mesmo comando sem motivo.
Se situação não mudou, responda "neutral" com frase DIFERENTE.

RÁDIO DA EQUIPE: informe interno. Use para escolher comando:
- ataque/janela ultrapassagem: "push" ou "overtake";
- defesa/DRS atrás: "defend";
- economia pneu/combustível: "conserve";
- cautela/detritos/pista suja: "careful";
- só informativo: "neutral".

URGÊNCIA POR VOLTA: o contexto dá o piso ("baixa"/"media"/"alta").
"urgencia" NUNCA pode ser menor que o piso. Última volta = "alta".

=== ESTADO ATUAL DA CORRIDA (seu carro = drv_02, A. Silva) ===
{context_text}
"""


def _post_command(race_id: str, driver_id: str, comando: dict | None) -> None:
    """Manda o comando de alto nível para o coach no backend.

    ``neutral`` também é enviado: ele limpa o comando anterior no coach, para o
    carro não ficar preso em "conserve" ou "push" o resto da corrida.
    """
    if not isinstance(comando, dict):
        return
    tipo = str(comando.get("tipo", "neutral")).strip().lower()
    if tipo in ("", "none"):
        tipo = "neutral"
    payload = {
        "driver_id": driver_id,
        "command": tipo,
        "value": float(comando.get("valor", 0.0) or 0.0),
        "reason": str(comando.get("motivo", "") or ""),
        "issued_by": "llm",
    }
    try:
        resp = requests.post(f"{API_URL}/races/{race_id}/commands", json=payload, timeout=3)
        print(f"[ai_listener] comando enviado: {tipo} ({resp.status_code})")
    except Exception as exc:  # noqa: BLE001 - o texto não pode cair por isso
        print(f"[ai_listener] falha ao enviar comando: {exc}")


def _seed_state(r: redis.Redis, state: LiveRaceState, race_id: str,
                followed_driver_id: str) -> None:
    """Lê meta e último tick do Redis para não começar cego numa conexão tardia."""
    try:
        raw_meta = r.get(f"race:{race_id}:meta")
        if raw_meta:
            state.total_laps = int(json.loads(raw_meta).get("num_laps") or 0)
    except Exception as exc:  # noqa: BLE001
        print(f"[ai_listener] não foi possível ler o meta inicial: {exc}")
    try:
        raw = r.get(f"race:{race_id}:state")
        if raw:
            apply_event(state, json.loads(raw), followed_driver_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[ai_listener] não foi possível ler o estado inicial: {exc}")


_SKIP_EVENT_TYPES = ("ai_suggestion", "ai_command", "ai_command_accepted")


def _drain_queued(pubsub, state: LiveRaceState, followed_driver_id: str,
                  pending: list[tuple], last_sim_ts: float,
                  meaningful_types: set[str]) -> tuple[bool, float, bool, list[str]]:
    """Consome a fila já recebida sem bloquear; devolve (race_end, sim_ts, had_meaningful, event_types).

    O modelo local leva mais tempo que o intervalo de acionamento. Sem drenar,
    a IA analisaria ticks cada vez mais antigos e se afastaria da corrida ao
    vivo. Drenar mantém o contexto no estado mais recente antes de falar.
    """
    had_meaningful = False
    event_types: list[str] = []
    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0)
        if message is None:
            return False, last_sim_ts, had_meaningful, event_types
        try:
            event = json.loads(message["data"])
        except (TypeError, json.JSONDecodeError):
            continue
        if event.get("type") in _SKIP_EVENT_TYPES:
            continue
        new_events = apply_event(state, event, followed_driver_id)
        ev_type = event.get("type", "")
        pending.extend([(lap, msg, ev_type) for lap, msg in new_events])
        last_sim_ts = float(event.get("sim_ts", last_sim_ts) or last_sim_ts)
        event_types.append(ev_type)
        if ev_type in meaningful_types:
            had_meaningful = True
        if ev_type == "race_end":
            return True, last_sim_ts, had_meaningful, event_types


def _should_stay_silent(had_events: bool, tipo: str, aviso: str,
                        last_command: str | None,
                        last_aviso: str | None,
                        last_tipo_semantic: str | None = None,
                        last_aviso_semantic: str | None = None,
                        event_types: list[str] | None = None,
                        semantic_cooldown: dict[str, float] | None = None,
                        now: float = 0.0,
                        cooldown_s: float = 45.0) -> bool:
    """
    Evita repetição semântica, não só literal.

    Grupos semânticos de comandos:
    - attack: push, overtake
    - defend: defend
    - conserve: conserve
    - careful: careful
    - neutral: neutral

    Eventos que MUDAM a situação tática (liberam repetição semântica):
    - off_track, tyre_worn, weather_changed, pit_stop, lap_completed
    - race_control (safety car, VSC), collision, position_update, on_track
    
    Eventos que NÃO mudam a situação (rádio é só sabor):
    - race_radio
    
    Se o comando cai no mesmo grupo semântico E o aviso é similar, silencia.
    Também respeita cooldown por grupo semântico (default 45s).
    """
    def semantic_group(cmd: str) -> str:
        cmd = cmd.lower().strip()
        if cmd in ("push", "overtake"):
            return "attack"
        if cmd == "defend":
            return "defend"
        if cmd == "conserve":
            return "conserve"
        if cmd == "careful":
            return "careful"
        return "neutral"

    def semantic_text(text: str) -> str:
        """Normaliza o texto pra comparação semântica."""
        t = text.lower().strip()
        for w in ["a ", "o ", "e ", "sua ", "seu ", "a ", "o ", "você ", "você", "mantenha ", "mantenho ", "defenda ", "defendo ", "ataque ", "ataque"]:
            t = t.replace(w, "")
        return t

    # Verifica se há evento tático real (não rádio)
    has_tactical_event = False
    if event_types:
        tactical_types = {"off_track", "tyre_worn", "weather_changed", "pit_stop",
                          "lap_completed", "race_control", "collision",
                          "position_update", "on_track", "race_start"}
        has_tactical_event = any(et in tactical_types for et in event_types)

    same_command_exact = last_command is not None and tipo == last_command
    same_text_exact = last_aviso is not None and aviso == last_aviso

    # Duplicata exata: sempre silencia
    if same_command_exact and same_text_exact:
        return True

    # Semântica: mesmo grupo de comando + texto similar
    current_sem_cmd = semantic_group(tipo)
    current_sem_text = semantic_text(aviso)

    if last_command is not None:
        last_sem_cmd = semantic_group(last_command)
        if current_sem_cmd == last_sem_cmd:
            # Mesmo grupo semântico de comando
            if last_aviso is not None:
                last_sem_text = semantic_text(last_aviso)
                if _text_similarity(current_sem_text, last_sem_text) > 0.6:
                    return True
            # Mesmo comando semântico: só fala se houve evento TÁTICO real
            if not has_tactical_event:
                return True

    # COOLDOWN por grupo semântico: não repetir grupo dentro de cooldown_s segundos
    # (exceto se houve evento tático real que justifique nova fala)
    if semantic_cooldown is not None and now > 0:
        last_used = semantic_cooldown.get(current_sem_cmd, 0.0)
        if now - last_used < cooldown_s and not has_tactical_event:
            return True

    # Sem evento tático e só o texto repete: silencia
    if not has_tactical_event and same_text_exact:
        return True

    return False


def _text_similarity(a: str, b: str) -> float:
    """Similaridade simples baseada em palavras em comum (Jaccard)."""
    if not a or not b:
        return 0.0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _sem_cmd(cmd: str) -> str:
    """Grupo semântico do comando."""
    cmd = cmd.lower().strip()
    if cmd in ("push", "overtake"):
        return "attack"
    if cmd == "defend":
        return "defend"
    if cmd == "conserve":
        return "conserve"
    if cmd == "careful":
        return "careful"
    return "neutral"


def _sem_text(text: str) -> str:
    """Normaliza texto para comparação semântica."""
    t = text.lower().strip()
    for w in ["a ", "o ", "e ", "sua ", "seu ", "você ", "você", "mantenha ", "mantenho ", "defenda ", "defendo ", "ataque ", "ataque"]:
        t = t.replace(w, "")
    return t


def run_listener(race_id: str, followed_driver_id: str, periodic_s: float = 10.0):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    events_channel = f"race:{race_id}:events"
    pubsub.subscribe(events_channel)

    print(f"[ai_listener] {race_id}: assinando {events_channel} "
          f"(piloto {followed_driver_id})...")

    state = LiveRaceState(race_id=race_id)
    _seed_state(r, state, race_id, followed_driver_id)
    # pending: lista de tuplas (lap, event_string) para filtrar por volta atual
    pending: list[tuple[int, str]] = []
    last_sim_ts = 0.0
    last_call_at = -1e9
    last_periodic_at = time.monotonic()
    # Intervalo periódico com jitter: o engenheiro não fala sempre no mesmo
    # relógio. O modelo local demora dezenas de segundos, então o espaçamento
    # real já varia; o jitter evita um padrão previsível no HUD.
    periodic_target = periodic_s * random.uniform(0.75, 1.35)
    last_command: str | None = None
    last_aviso: str | None = None
    last_sem_cmd: str | None = None
    last_sem_aviso: str | None = None
    # Tempo do último evento SIGNIFICATIVO (não-periódico): off_track, tyre_worn,
    # weather_changed, pit_stop, race_radio, lap_completed, race_control, etc.
    # O gatilho periódico só dispara se passou tempo suficiente desde o último
    # evento real, para não ficar repetindo "defenda" a cada 20s em cenário estático.
    last_meaningful_event_at = 0.0
    MEANINGFUL_EVENT_TYPES = {
        "off_track", "tyre_worn", "weather_changed", "pit_stop",
        "race_radio", "lap_completed", "race_control", "race_start",
        "position_update", "on_track", "collision"
    }
    # Eventos que mudam a situação tática (liberam repetição semântica)
    TACTICAL_EVENT_TYPES = {
        "off_track", "tyre_worn", "weather_changed", "pit_stop",
        "lap_completed", "race_control", "collision",
        "position_update", "on_track", "race_start"
    }
    # Acumula tipos de evento desde a última chamada ao LLM
    recent_event_types: list[str] = []
    # Cooldown por grupo semântico de comando (não repetir grupo dentro de X segundos)
    SEMANTIC_COOLDOWN_S = 45.0  # 45s entre comandos do mesmo grupo semântico
    last_semantic_command_at: dict[str, float] = {
        "attack": 0.0,    # push, overtake
        "defend": 0.0,    # defend
        "conserve": 0.0,  # conserve
        "careful": 0.0,   # careful
        "neutral": 0.0,   # neutral
    }
    # Eventos táticos que SEMPRE entram no contexto (ignoram filtro de volta)
    TACTICAL_EVENT_TYPES_FOR_CONTEXT = {
        "off_track", "tyre_worn", "weather_changed", "pit_stop",
        "lap_completed", "race_control", "collision",
        "position_update", "on_track", "race_start"
    }

    while True:
        # Um listener anexado a uma corrida que terminou enquanto o modelo
        # pensava nunca veria o `race_end`. O `result` é a fonte de verdade.
        if r.exists(f"race:{race_id}:result"):
            print(f"[ai_listener] {race_id}: corrida encerrada, saindo.")
            break

        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        event: dict | None = None
        if message is not None:
            try:
                event = json.loads(message["data"])
            except (TypeError, json.JSONDecodeError):
                print("[ai_listener] evento não é JSON válido, ignorando")
            if event is not None:
                event_type = event.get("type")
                # A própria IA também publica neste canal; não reagir a si mesma.
                if event_type in _SKIP_EVENT_TYPES:
                    continue
                new_events = apply_event(state, event, followed_driver_id)
                # Guarda também o tipo do evento para bypass do filtro de volta em eventos táticos
                pending.extend([(lap, msg, event_type) for lap, msg in new_events])
                last_sim_ts = float(event.get("sim_ts", last_sim_ts) or last_sim_ts)
                # Acumula tipo para decisão de silêncio semântico
                recent_event_types.append(event_type)
                # Atualiza tempo do último evento significativo (não-periódico)
                # e reseta o timer periódico para não disparar logo após evento real
                if event_type in MEANINGFUL_EVENT_TYPES:
                    last_meaningful_event_at = now
                    last_periodic_at = now
                if event_type == "race_end":
                    break

        now = time.monotonic()
        # Gatilho periódico só dispara se passou tempo suficiente desde o último
        # evento significativo. Isso evita repetir "defenda" a cada 20s quando
        # nada acontece na pista.
        time_since_meaningful = now - last_meaningful_event_at
        # Periódico só dispara se passou UM intervalo completo desde evento tático real
        # Isso evita falar "overtake" a cada 60s quando nada muda na pista
        periodic_due = (now - last_periodic_at >= periodic_target) and (time_since_meaningful >= periodic_target)
        if not pending and not periodic_due:
            continue
        # Corrida no grid esperando o visualizador: não gaste uma chamada do
        # modelo antes da largada. O gatilho periódico continua vencido e fala
        # assim que o primeiro tick chegar.
        if not pending and not state.positions:
            continue
        # Debounce: eventos são acumulados, mas o LLM não é chamado a cada tick.
        if now - last_call_at < MIN_TRIGGER_INTERVAL_S:
            continue

        # Antes de gastar uma chamada, traz o estado para o instante mais
        # recente que já chegou no Redis.
        ended, last_sim_ts, had_meaningful, drained_types = _drain_queued(
            pubsub, state, followed_driver_id, pending, last_sim_ts, MEANINGFUL_EVENT_TYPES)
        # Combina tipos do loop principal + drenados
        all_recent_types = recent_event_types + drained_types
        recent_event_types.clear()
        if had_meaningful:
            last_meaningful_event_at = now
        if ended:
            break
        last_call_at = time.monotonic()

        # Filtra eventos: só da volta atual (state.lap + 1) e anterior (state.lap)
        # para não poluir contexto com voltas passadas.
        # EXCEÇÃO: eventos táticos SEMPRE entram (ignoram filtro de volta).
        current_lap = state.lap + 1
        relevant_events = [
            msg for lap, msg, ev_type in pending
            if (lap >= current_lap - 1 and lap <= current_lap)
               or ev_type in TACTICAL_EVENT_TYPES_FOR_CONTEXT
        ]
        # Mantém no máximo 12 eventos mais recentes
        relevant_events = relevant_events[-12:]
        pending = []  # limpa após consumir
        had_events = bool(relevant_events)
        if not relevant_events:
            relevant_events.append(
                f"Atualização periódica (t={last_sim_ts:.0f}s de simulação)")

        print(f"[ai_listener] {race_id}: volta {current_lap}, "
              f"{len(relevant_events)} evento(s) da volta atual/anterior, acionando agente...")
        context_text = format_live_context(
            state, followed_driver_id, relevant_events,
            last_command=last_command, last_aviso=last_aviso)
        prompt = build_live_prompt(context_text)
        print(f"[DEBUG] contexto enviado ao modelo:\n{context_text}\n")

        model_result = call_model(prompt)
        if not model_result["ok"]:
            output = fallback_output(model_result["error"])
        else:
            validated = validate_agent_output(model_result["response"])
            output = validated if validated else fallback_output(
                "resposta em formato inválido")

        comando = output.get("comando") or {}
        tipo = str(comando.get("tipo", "neutral")).strip().lower()
        aviso = str(output.get("aviso", "")).strip()
        # A urgência acompanha a volta: mesmo que o modelo responda "baixa",
        # ela não pode cair abaixo do piso (última volta = alta).
        piso = lap_urgency_floor(current_lap, state.total_laps)
        output["urgencia"] = max_urgency(output.get("urgencia"), piso)

        # A engine pode terminar enquanto o modelo local pensa. Nesse caso o
        # CommandBus já foi removido e o POST daria 404; descarta a resposta.
        if r.exists(f"race:{race_id}:result"):
            print("[ai_listener] corrida encerrou durante a análise; "
                  "descartando a resposta.")
            break

        # Detecta mismatch entre conselho e realidade para resposta do piloto
        def _detect_mismatch(state: LiveRaceState, followed_driver_id: str,
                            tipo: str, aviso: str) -> bool:
            """Retorna True se o conselho contradiz a situação real."""
            followed = next((p for p in state.positions
                           if p.get("driver_id") == followed_driver_id), None)
            if not followed:
                return False
            
            pos = followed.get("position", 99)
            total = len(state.positions)
            aviso_lower = aviso.lower()
            
            # Se o aviso fala de OUTRO piloto (rival), não é mismatch nosso
            # O engenheiro pode alertar sobre rival: "rival à frente", "piloto 03", "carro atrás"
            rival_keywords = ["rival", "piloto 0", "carro à frente", "carro atrás", 
                             "o carro à frente", "o carro atrás", "carro da frente"]
            if any(kw in aviso_lower for kw in rival_keywords):
                return False  # Engenheiro falando do rival, não de nós
            
            # Liderando sem ninguém à frente -> defend/overtake não faz sentido
            if pos == 1:
                idx = state.positions.index(followed)
                if idx == 0 and tipo in ("defend", "overtake", "push"):
                    # Só faz sentido se tem rival muito colado à frente (idx > 0)
                    return True  # mismatch: defend/overtake liderando sozinho
            
            # Aviso menciona posição errada DO NOSSO carro
            if "terceira" in aviso_lower and pos == 1:
                return True
            if "segunda" in aviso_lower and pos == 1:
                return True
            if "último" in aviso_lower and pos == 1:
                return True
            if "lidera" in aviso_lower and pos != 1:
                return True
            
            # Comando conserve mas pneu/combustível ok
            if tipo == "conserve":
                tyre_life = followed.get("tyre_life_pct", 100)
                fuel = followed.get("fuel_kg", 100)
                if tyre_life > 50 and fuel > 50:
                    return True
            
            return False

        mismatch = _detect_mismatch(state, followed_driver_id, tipo, aviso)
        
        if _should_stay_silent(had_events, tipo, aviso, last_command, last_aviso,
                           last_sem_cmd, last_sem_aviso, all_recent_types,
                           semantic_cooldown=last_semantic_command_at,
                           now=now, cooldown_s=SEMANTIC_COOLDOWN_S):
            print("[ai_listener] sem mudança material; mantendo silêncio "
                  f"(comando {tipo}, última msg semântica {last_sem_cmd}, eventos: {all_recent_types}, cooldown={now - last_semantic_command_at.get(_sem_cmd(tipo), 0):.0f}s)")
        else:
            output["type"] = "ai_suggestion"
            output["sim_ts"] = last_sim_ts
            output["volta"] = state.lap + 1
            output["driver_id"] = followed_driver_id

            # Resposta do piloto (SÓ se mismatch real - engenheiro deu conselho incoerente)
            _DRIVER_SARCASTIC = [
                "Tá de sacanagem? Eu tô em P1!",
                "Engenheiro, você tá vendo a mesma corrida que eu?",
                "Como é que eu defendo de ninguém à minha frente?",
                "Ultrapassar quem? O ar?",
                "Me dá um rádio que preste, por favor.",
                "Você quer que eu bata no safety car também?",
                "Cara, eu tô LIDERANDO. Lê a tela aí.",
                "Pit stop agora? Com pneu zero? Tá louco?",
                "Push push push... eu não tenho DRS mágico não.",
                "Defender de fantasma é novidade pra mim.",
            ]
            if mismatch:
                output["resposta_piloto"] = random.choice(_DRIVER_SARCASTIC)
            else:
                output["resposta_piloto"] = None

            _post_command(race_id, followed_driver_id, comando)

            payload = json.dumps(output, ensure_ascii=False)
            r.publish(events_channel, payload)
            suggestions_key = f"race:{race_id}:suggestions"
            pipe = r.pipeline()
            pipe.lpush(suggestions_key, payload)
            pipe.ltrim(suggestions_key, 0, 49)
            pipe.expire(suggestions_key, 24 * 60 * 60)
            pipe.execute()
            print(f"[ai_listener] sugestão publicada: {aviso}"
                  f"{' | PILOTO: ' + output['resposta_piloto'] if output.get('resposta_piloto') else ''}")
            last_command, last_aviso = tipo, aviso
            last_sem_cmd, last_sem_aviso = _sem_cmd(tipo), _sem_text(aviso)
            # Atualiza cooldown do grupo semântico
            last_semantic_command_at[last_sem_cmd] = now

        last_periodic_at = time.monotonic()
        periodic_target = periodic_s * random.uniform(0.75, 1.35)

    pubsub.close()


def _active_races(r: redis.Redis) -> list[tuple[str, str]]:
    """Corridas ainda em andamento quando o serviço sobe.

    ``race:control`` não tem replay: uma corrida criada antes do listener não
    seria vista. Aqui lemos os metadados e confirmamos que o estado está
    avançando, para não anexar a corridas mortas de processos anteriores.
    """
    candidates: list[tuple[str, str, float]] = []
    for key in r.scan_iter("race:*:meta"):
        race_id = key[len("race:"):-len(":meta")]
        if r.exists(f"race:{race_id}:result"):
            continue
        raw_state = r.get(f"race:{race_id}:state")
        raw_meta = r.get(key)
        if not raw_state or not raw_meta:
            continue
        try:
            first = float(json.loads(raw_state).get("sim_ts", 0.0) or 0.0)
            meta = json.loads(raw_meta)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        followed = str(meta.get("followed_driver_id") or "drv_01")
        candidates.append((race_id, followed, first))

    if not candidates:
        return []

    time.sleep(0.6)
    active: list[tuple[str, str]] = []
    for race_id, followed, first in candidates:
        raw_state = r.get(f"race:{race_id}:state")
        try:
            second = float(json.loads(raw_state).get("sim_ts", 0.0) or 0.0) if raw_state else first
        except (TypeError, ValueError, json.JSONDecodeError):
            second = first
        if second > first:
            active.append((race_id, followed))
    return active


def _start_listener(threads: dict[str, threading.Thread], race_id: str,
                    followed: str) -> None:
    existing = threads.get(race_id)
    if existing is not None and existing.is_alive():
        return
    thread = threading.Thread(
        target=run_listener,
        args=(race_id, followed),
        kwargs={"periodic_s": PERIODIC_TRIGGER_S},
        daemon=True,
    )
    threads[race_id] = thread
    thread.start()
    print(f"[ai_listener] nova corrida {race_id}, piloto {followed}")


def run_control_listener():
    """Descobre corridas novas em ``race:control`` e abre um listener para cada."""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe(CONTROL_CHANNEL)
    print(f"[ai_listener] modo control: assinando {CONTROL_CHANNEL}...")
    warm_up()

    threads: dict[str, threading.Thread] = {}
    for race_id, followed in _active_races(r):
        print(f"[ai_listener] corrida em andamento encontrada: {race_id}")
        _start_listener(threads, race_id, followed)

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
        except json.JSONDecodeError:
            continue
        if data.get("type") != "race_created":
            continue
        race_id = data.get("race_id")
        if not race_id:
            continue
        followed = data.get("followed_driver_id", "drv_01")
        _start_listener(threads, race_id, followed)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        race_id = sys.argv[1]
        driver_id = sys.argv[2] if len(sys.argv) > 2 else "drv_01"
        interval = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
        warm_up()
        run_listener(race_id, driver_id, periodic_s=interval)
    else:
        run_control_listener()
