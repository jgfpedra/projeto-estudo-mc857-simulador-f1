from context.driver_context import get_driver_context, format_driver_context
from context.tyre_context import get_tyre_context, format_tyre_context
from context.weather_context import get_weather_context, format_weather_context
from context.race_context import get_race_context, format_race_context, should_trigger_alert

from prompts.main_prompt import build_prompt
from client import call_model
from schemas import validate_agent_output, fallback_output


def _apply_urgencia_override(output: dict, race_state: dict) -> dict:
    """
    Garante urgência mínima em momentos objetivamente críticos, independente
    do julgamento do modelo.
    """
    eventos_criticos = ["Safety car ACIONADO",
                        "Safety car RETIRADO", "Bandeira vermelha"]
    tem_evento_critico = any(
        any(ec in evento for ec in eventos_criticos)
        for evento in race_state.get("eventos_detectados", [])
    )

    if tem_evento_critico and output["urgencia"] == "baixa":
        output["urgencia"] = "media"
        output["urgencia_ajustada"] = True

    if race_state["safety_car"]["ativo"] and output["urgencia"] == "baixa":
        output["urgencia"] = "media"
        output["urgencia_ajustada"] = True

    return output


def analyze_lap(race_id: int, driver_id: int, lap: int, previous_race_state: dict = None) -> dict:
    """
    Roda uma volta: monta o contexto global, decide se dispara o agente,
    e retorna o resultado (ou o estado sem alerta, se não for o momento).
    """
    race_state = get_race_context(race_id, driver_id, lap,
                                  previous_state=previous_race_state)

    if not should_trigger_alert(race_state):
        return {"disparou": False, "race_state": race_state}

    driver_ctx = get_driver_context(race_id, driver_id, lap)
    tyre_ctx = get_tyre_context(race_id, driver_id, lap)
    weather_ctx = get_weather_context(race_id, driver_id, lap)

    prompt = build_prompt(
        race_text=format_race_context(race_state),
        driver_text=format_driver_context(driver_ctx),
        tyre_text=format_tyre_context(tyre_ctx),
        weather_text=format_weather_context(weather_ctx),
    )

    model_result = call_model(prompt)

    if not model_result["ok"]:
        output = fallback_output(model_result["error"])
    else:
        validated = validate_agent_output(model_result["response"])
        output = validated if validated else fallback_output(
            "resposta em formato inválido")

    output = _apply_urgencia_override(output, race_state)

    output["volta"] = lap
    output["tempo_resposta"] = round(model_result["elapsed"], 2)
    return {"disparou": True, "race_state": race_state, "output": output}
