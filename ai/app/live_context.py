from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LiveRaceState:
    """Estado da corrida mantido em memória, atualizado a cada evento recebido."""
    race_id: str = ""
    lap: int = 0
    weather: Dict[str, Any] = field(default_factory=dict)
    positions: List[Dict[str, Any]] = field(
        default_factory=list)  # snapshot mais recente
    # driver_ids que pitaram recentemente
    recent_pit_stops: List[str] = field(default_factory=list)
    recent_tyre_warnings: List[str] = field(
        default_factory=list)  # driver_ids com pneu crítico
    weather_changed_recently: bool = False
    previous_positions_by_driver: Dict[str, int] = field(
        default_factory=dict)  # para detectar mudança


def apply_event(state: LiveRaceState, event: dict) -> List[str]:
    """
    Atualiza o LiveRaceState com o evento recebido e retorna a lista de
    'eventos detectados' nessa atualização (mesmo formato usado no #20).
    """
    eventos = []
    event_type = event.get("type")

    if event_type == "position_update" or event_type == "tick":
        state.lap = event.get("lap", state.lap)
        if event.get("weather"):
            state.weather = event["weather"]

        new_positions = event.get("positions", [])
        # detecta mudança de posição por piloto
        current_by_driver = {p["driver_id"]: idx + 1 for idx, p in enumerate(
            sorted(new_positions, key=lambda p: p.get("lap", 0), reverse=True)
        )}
        for driver_id, new_pos in current_by_driver.items():
            old_pos = state.previous_positions_by_driver.get(driver_id)
            if old_pos is not None and old_pos != new_pos:
                eventos.append(f"Piloto {driver_id} mudou de posição: P{
                               old_pos} -> P{new_pos}")
        state.previous_positions_by_driver = current_by_driver
        state.positions = new_positions

    elif event_type == "pit_stop":
        driver_id = event.get("driver_id")
        state.recent_pit_stops.append(driver_id)
        eventos.append(f"Pit stop: piloto {driver_id} trocou para {
                       event.get('new_compound')}")

    elif event_type == "tyre_worn":
        driver_id = event.get("driver_id")
        state.recent_tyre_warnings.append(driver_id)
        eventos.append(f"Pneu crítico: piloto {driver_id} ({
                       event.get('tyre_life_pct')}% de vida)")

    elif event_type == "weather_changed":
        state.weather = event.get("current", state.weather)
        state.weather_changed_recently = True
        prev_kind = event.get("previous", {}).get("kind", "?")
        new_kind = event.get("current", {}).get("kind", "?")
        eventos.append(f"Clima mudou: {prev_kind} -> {new_kind}")

    return eventos


def should_trigger_live(eventos_detectados: List[str]) -> bool:
    """
    Versão ao vivo do gatilho — sem safety car/red flag disponíveis na
    simulação, dispara em qualquer evento relevante detectado.
    """
    return len(eventos_detectados) > 0


def format_live_context(state: LiveRaceState,
                        followed_driver_id: str,
                        eventos: List[str]) -> str:
    followed = next((p for p in state.positions if p.get(
        "driver_id") == followed_driver_id), None)

    linhas = [f"Volta {state.lap}"]
    if followed:
        linhas.append(
            f"Piloto acompanhado: {followed.get('driver_name', followed_driver_id)}, "
            f"combustível {followed.get('fuel_kg')}kg, "
            f"pneu {followed.get('tyre_compound')} ({followed.get('tyre_life_pct')}%)"
        )
    if state.weather:
        linhas.append(f"Clima: {state.weather}")
    if eventos:
        linhas.append("Eventos recentes: " + "; ".join(eventos))
    else:
        linhas.append("Sem eventos relevantes novos")

    return "\n".join(linhas)
