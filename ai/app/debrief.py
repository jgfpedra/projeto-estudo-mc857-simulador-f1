"""Geração e persistência do debrief pós-corrida."""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from typing import Any, Optional

import redis

from client import call_model

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_URL = os.environ.get("REDIS_URL")
DEBRIEF_TTL_SECONDS = 7 * 24 * 60 * 60
DEBRIEF_OLLAMA_TIMEOUT = float(os.environ.get("DEBRIEF_OLLAMA_TIMEOUT", "60"))

TEXT_FIELDS = (
    "resumo_geral",
    "largada",
    "estrategia_pneus",
    "combustivel",
    "contatos_incidentes",
    "decisoes_engenheiro",
    "licoes_aprendidas",
)

DEBRIEF_PROMPT = """Você é o engenheiro chefe de uma equipe de Fórmula 1.
Analise somente os dados fornecidos e produza um debrief em português, em JSON
válido, sem markdown ou texto adicional. Não invente fatos: quando uma informação
não estiver disponível, declare essa limitação no campo correspondente.

Use exatamente esta estrutura:
{
  "resumo_geral": "resumo de 2 ou 3 frases com vencedor e fato marcante",
  "largada": "ganhos, perdas e incidentes iniciais observáveis",
  "estrategia_pneus": "compostos, paradas e preservação observados",
  "combustivel": "o que a telemetria permite concluir sobre combustível",
  "momentos_chave": [
    {"volta": 1, "evento": "descrição objetiva", "impacto": "alto"}
  ],
  "contatos_incidentes": "colisões, saídas de pista e penalidades registradas",
  "performance_pilotos": {
    "vencedor": "piloto e principal razão da vitória",
    "surpresa_positiva": "opcional",
    "decepcao": "opcional",
    "melhor_ultrapassagem": "opcional"
  },
  "decisoes_engenheiro": "análise dos comandos da IA e de seu timing",
  "licoes_aprendidas": "aprendizados objetivos para a próxima corrida"
}

O impacto de cada momento deve ser "alto", "medio" ou "baixo".

=== DADOS DA CORRIDA ===
{race_data}

=== CLASSIFICAÇÃO FINAL ===
{classification}

=== EVENTOS PRINCIPAIS ===
{events}

=== COMANDOS DA IA ===
{ai_commands}

=== ESTATÍSTICAS ===
{stats}
"""


def build_debrief_stats(
    events: list[dict],
    ai_commands: list[dict],
    total_time_s: float | None = None,
) -> dict[str, Any]:
    """Resume os dados brutos sem depender da interpretação do modelo."""
    counts = Counter(str(event.get("type", "unknown")) for event in events)
    command_counts = Counter(
        str(command.get("command", "unknown")) for command in ai_commands
    )
    sim_times = [
        float(event["sim_ts"])
        for event in events
        if isinstance(event.get("sim_ts"), (int, float))
    ]
    return {
        "eventos_registrados": len(events),
        "eventos_por_tipo": dict(counts),
        "pit_stops": counts["pit_stop"],
        "colisoes": counts["collision"],
        "saidas_de_pista": counts["off_track"],
        "mudancas_climaticas": counts["weather_changed"],
        "sugestoes_da_ia": counts["ai_suggestion"],
        "comandos_da_ia": len(ai_commands),
        "comandos_por_tipo": dict(command_counts),
        "tempo_total_s": total_time_s,
        "inicio_observado_sim_s": min(sim_times) if sim_times else None,
        "fim_observado_sim_s": max(sim_times) if sim_times else None,
    }


def build_race_data(
    race_meta: dict,
    classification: list[dict],
    events: list[dict],
    ai_commands: list[dict],
    stats: dict,
) -> dict[str, Any]:
    """Seleciona os metadados e a classificação relevantes para o prompt."""
    track = race_meta.get("track") if isinstance(race_meta.get("track"), dict) else {}
    return {
        "race_id": race_meta.get("race_id"),
        "circuito": track.get("name") or race_meta.get("track_name") or race_meta.get("circuit_id"),
        "temporada": race_meta.get("season"),
        "voltas_previstas": race_meta.get("num_laps"),
        "numero_de_pilotos": race_meta.get("num_drivers") or len(classification),
        "piloto_do_usuario": race_meta.get("user_driver_id"),
        "classificacao": [
            {
                "posicao": entry.get("position"),
                "piloto": entry.get("driver_name") or entry.get("driver_id"),
                "voltas": entry.get("laps_completed"),
                "tempo_total_s": entry.get("total_time_s"),
                "pit_stops": entry.get("pit_stops"),
            }
            for entry in classification[:10]
        ],
        "eventos_disponiveis": len(events),
        "comandos_disponiveis": len(ai_commands),
        "estatisticas_fornecidas": bool(stats),
    }


def _classification_text(classification: list[dict]) -> str:
    lines = []
    for entry in classification:
        lines.append(
            f"P{entry.get('position', '?')}: "
            f"{entry.get('driver_name') or entry.get('driver_id', '?')} — "
            f"{entry.get('laps_completed', '?')} voltas, "
            f"{entry.get('pit_stops', 0)} pit stops, "
            f"tempo {entry.get('total_time_s', '?')}s"
        )
    return "\n".join(lines) or "Classificação não disponível"


def _events_text(events: list[dict], limit: int = 40) -> str:
    if not events:
        return "Nenhum evento principal disponível"
    selected = events[-limit:]
    lines = [
        json.dumps(event, ensure_ascii=False, default=str)
        for event in selected
    ]
    omitted = len(events) - len(selected)
    if omitted > 0:
        lines.insert(0, f"{omitted} eventos anteriores omitidos do prompt")
    return "\n".join(lines)


def _commands_text(ai_commands: list[dict], limit: int = 20) -> str:
    if not ai_commands:
        return "Nenhum comando da IA registrado"
    lines = []
    for command in ai_commands[-limit:]:
        lines.append(
            f"volta {command.get('lap', '?')}, "
            f"{command.get('driver_name') or command.get('driver_id', '?')}: "
            f"{command.get('command', '?')} — "
            f"{command.get('reason') or 'sem motivo informado'}"
        )
    return "\n".join(lines)


def generate_debrief_prompt(
    race_meta: dict,
    classification: list[dict],
    events: list[dict],
    ai_commands: list[dict],
    stats: dict,
) -> str:
    """Monta o prompt preservando todos os dados recebidos."""
    race_data = build_race_data(
        race_meta, classification, events, ai_commands, stats
    )
    replacements = {
        "{race_data}": json.dumps(race_data, ensure_ascii=False, default=str, indent=2),
        "{classification}": _classification_text(classification),
        "{events}": _events_text(events),
        "{ai_commands}": _commands_text(ai_commands),
        "{stats}": json.dumps(stats, ensure_ascii=False, default=str, indent=2),
    }
    prompt = DEBRIEF_PROMPT
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


def validate_debrief_output(raw_output: str) -> dict[str, Any] | None:
    """Valida e normaliza o contrato específico do debrief."""
    try:
        text = raw_output.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        parsed = json.loads(text)
    except (json.JSONDecodeError, IndexError, AttributeError):
        return None

    if not isinstance(parsed, dict):
        return None
    required = set(TEXT_FIELDS) | {"momentos_chave", "performance_pilotos"}
    if required - parsed.keys():
        return None
    if any(not isinstance(parsed.get(field), str) or not parsed[field].strip() for field in TEXT_FIELDS):
        return None
    if not isinstance(parsed.get("performance_pilotos"), dict):
        return None
    if not isinstance(parsed.get("momentos_chave"), list):
        return None

    impact_aliases = {
        "alto": "alto", "alta": "alto",
        "medio": "medio", "médio": "medio", "media": "medio", "média": "medio",
        "baixo": "baixo", "baixa": "baixo",
    }
    moments = []
    for raw_moment in parsed["momentos_chave"]:
        if not isinstance(raw_moment, dict):
            return None
        event = raw_moment.get("evento")
        impact = impact_aliases.get(str(raw_moment.get("impacto", "")).lower())
        try:
            lap = int(raw_moment.get("volta"))
        except (TypeError, ValueError):
            return None
        if not isinstance(event, str) or not event.strip() or impact is None:
            return None
        moments.append({"volta": lap, "evento": event.strip(), "impacto": impact})

    performance = {
        key: value.strip()
        for key, value in parsed["performance_pilotos"].items()
        if key in {"vencedor", "surpresa_positiva", "decepcao", "melhor_ultrapassagem"}
        and isinstance(value, str) and value.strip()
    }
    return {
        **{field: parsed[field].strip() for field in TEXT_FIELDS},
        "momentos_chave": moments,
        "performance_pilotos": performance,
    }


def _driver_names(race_meta: dict) -> dict[str, str]:
    drivers = race_meta.get("drivers", [])
    if not isinstance(drivers, list):
        return {}
    return {
        str(driver.get("driver_id")): str(driver.get("name") or driver.get("driver_id"))
        for driver in drivers
        if isinstance(driver, dict) and driver.get("driver_id")
    }


def _count_pt(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def fallback_debrief(
    motivo: str,
    race_id: str,
    race_meta: Optional[dict] = None,
    classification: Optional[list[dict]] = None,
    events: Optional[list[dict]] = None,
    ai_commands: Optional[list[dict]] = None,
    stats: Optional[dict] = None,
) -> dict[str, Any]:
    """Produz um resumo factual quando o modelo não está disponível."""
    race_meta = race_meta or {}
    classification = classification or []
    events = events or []
    ai_commands = ai_commands or []
    stats = stats or build_debrief_stats(events, ai_commands)
    names = _driver_names(race_meta)
    winner = classification[0] if classification else {}
    winner_id = str(winner.get("driver_id", ""))
    winner_name = winner.get("driver_name") or names.get(winner_id, winner_id or "Vencedor não identificado")

    summary = (
        f"{winner_name} venceu após completar {winner.get('laps_completed', '?')} voltas."
        if classification else
        "A classificação final não estava disponível no momento da geração."
    )
    summary += (
        " Foram registrados "
        f"{_count_pt(stats.get('pit_stops', 0), 'pit stop', 'pit stops')}, "
        f"{_count_pt(stats.get('colisoes', 0), 'colisão', 'colisões')} e "
        f"{_count_pt(stats.get('saidas_de_pista', 0), 'saída', 'saídas')} de pista."
    )

    key_events = [
        event for event in events
        if event.get("type") in {"pit_stop", "collision", "off_track", "weather_changed", "race_control"}
    ][-6:]
    moments = []
    for event in key_events:
        event_type = str(event.get("type", "evento"))
        impact = "alto" if event_type in {"collision", "off_track", "race_control"} else "medio"
        moments.append({
            "volta": int(event.get("lap", 0) or 0),
            "evento": json.dumps(event, ensure_ascii=False, default=str),
            "impacto": impact,
        })

    command_counts = stats.get("comandos_por_tipo", {})
    decisions = (
        f"Foram emitidos {stats.get('comandos_da_ia', len(ai_commands))} comandos pela IA: "
        f"{json.dumps(command_counts, ensure_ascii=False)}."
        if ai_commands else
        "Não foram registrados comandos automáticos da IA para analisar."
    )
    incidents = (
        "O histórico contém "
        f"{_count_pt(stats.get('colisoes', 0), 'colisão', 'colisões')} e "
        f"{_count_pt(stats.get('saidas_de_pista', 0), 'saída', 'saídas')} de pista. "
        "Penalidades não foram inferidas sem registros explícitos."
    )
    return {
        "resumo_geral": summary,
        "largada": "Os dados de largada estão nos eventos registrados; não foram inferidas trocas de posição sem evidência.",
        "estrategia_pneus": f"Foram observados {_count_pt(stats.get('pit_stops', 0), 'pit stop', 'pit stops')}. A análise qualitativa dos stints requer o modelo ou dados adicionais.",
        "combustivel": "Não foi produzida uma interpretação automática do consumo sem uma resposta do modelo.",
        "momentos_chave": moments,
        "contatos_incidentes": incidents,
        "performance_pilotos": {"vencedor": winner_name} if classification else {},
        "decisoes_engenheiro": decisions,
        "licoes_aprendidas": "Revisar os eventos e os comandos registrados antes de atribuir causas não comprovadas ao resultado.",
        "fallback": True,
        "fallback_motivo": motivo,
        "race_id": race_id,
        "gerado_em": time.time(),
    }


def generate_debrief(
    race_id: str,
    race_meta: dict,
    classification: list[dict],
    events: list[dict],
    ai_commands: list[dict],
    stats: dict,
) -> dict[str, Any]:
    """Gera o debrief com o LLM ou com o fallback factual."""
    computed_stats = build_debrief_stats(
        events,
        ai_commands,
        total_time_s=stats.get("total_time_s") if isinstance(stats, dict) else None,
    )
    if isinstance(stats, dict):
        computed_stats.update(stats)

    prompt = generate_debrief_prompt(
        race_meta, classification, events, ai_commands, computed_stats
    )
    result = call_model(
        prompt,
        options={"num_predict": 900, "num_ctx": 4096},
        timeout=DEBRIEF_OLLAMA_TIMEOUT,
    )
    if result["ok"]:
        validated = validate_debrief_output(result["response"])
        if validated is not None:
            validated["race_id"] = race_id
            validated["gerado_em"] = time.time()
            validated["fallback"] = False
            return validated
        motivo = "resposta em formato inválido"
    else:
        motivo = result["error"]

    return fallback_debrief(
        motivo,
        race_id,
        race_meta=race_meta,
        classification=classification,
        events=events,
        ai_commands=ai_commands,
        stats=computed_stats,
    )


def save_debrief(redis_client: redis.Redis, race_id: str, debrief: dict) -> bool:
    """Persiste o JSON por sete dias, no namespace da corrida."""
    try:
        redis_client.setex(
            f"race:{race_id}:debrief",
            DEBRIEF_TTL_SECONDS,
            json.dumps(debrief, ensure_ascii=False, default=str),
        )
        return True
    except (redis.RedisError, TypeError, ValueError) as exc:
        print(f"[debrief] Erro ao salvar: {exc}")
        return False


def get_debrief(redis_client: redis.Redis, race_id: str) -> Optional[dict]:
    """Recupera um debrief persistido."""
    try:
        raw = redis_client.get(f"race:{race_id}:debrief")
        return json.loads(raw) if raw else None
    except (redis.RedisError, TypeError, json.JSONDecodeError) as exc:
        print(f"[debrief] Erro ao ler: {exc}")
        return None


def _new_redis_client() -> redis.Redis:
    if REDIS_URL:
        return redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def generate_and_save_debrief(
    race_id: str,
    race_meta: dict,
    classification: list[dict],
    events: list[dict],
    ai_commands: list[dict],
    stats: dict,
    redis_client=None,
) -> dict[str, Any]:
    """Executa o pipeline completo e confirma a persistência."""
    client = redis_client or _new_redis_client()
    owns_client = redis_client is None
    try:
        debrief = generate_debrief(
            race_id=race_id,
            race_meta=race_meta,
            classification=classification,
            events=events,
            ai_commands=ai_commands,
            stats=stats,
        )
        if not save_debrief(client, race_id, debrief):
            raise RuntimeError(f"Não foi possível salvar o debrief de {race_id}")
        return debrief
    finally:
        if owns_client:
            client.close()


if __name__ == "__main__":
    import sys

    selected_race = sys.argv[1] if len(sys.argv) > 1 else "test_race"
    redis_client = _new_redis_client()
    try:
        raw_meta = redis_client.get(f"race:{selected_race}:meta")
        raw_result = redis_client.get(f"race:{selected_race}:result")
        meta = json.loads(raw_meta) if raw_meta else {"race_id": selected_race}
        result = json.loads(raw_result) if raw_result else {}
        output = generate_and_save_debrief(
            race_id=selected_race,
            race_meta=meta,
            classification=result.get("final_classification", []),
            events=[],
            ai_commands=[],
            stats={"total_time_s": result.get("total_time_s")},
            redis_client=redis_client,
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        redis_client.close()
