import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

NEARBY_RADIUS_M = 100.0   # raio para considerar um rival "próximo"
FILTER_MIN_CARS = 4

# Ordem crescente de urgência usada pelo engenheiro e pelo piso por volta.
URGENCY_ORDER = {"baixa": 0, "media": 1, "alta": 2}


def lap_urgency_floor(lap: int, total_laps: int) -> str:
    """Urgência mínima esperada conforme a corrida avança.

    O engenheiro não pode tratar a última volta como se fosse a primeira: o
    piso sobe de ``baixa`` para ``media`` na metade da corrida e vira ``alta``
    na última volta (ou nos ~15% finais, para corridas mais curtas).
    """
    if total_laps <= 0 or lap <= 0:
        return "baixa"
    if lap >= total_laps:
        return "alta"
    progress = lap / total_laps
    if progress >= 0.85:
        return "alta"
    if progress >= 0.5:
        return "media"
    return "baixa"


def max_urgency(current: Optional[str], floor: str) -> str:
    """Devolve a mais alta entre a urgência do modelo e o piso da volta."""
    value = (current or "").strip().lower()
    if value not in URGENCY_ORDER:
        return floor
    if URGENCY_ORDER[value] >= URGENCY_ORDER[floor]:
        return value
    return floor


@dataclass
class LiveRaceState:
    """Estado da corrida mantido em memória, atualizado a cada evento recebido."""
    race_id: str = ""
    lap: int = 0
    total_laps: int = 0   # 0 = desconhecido (sem piso de urgência)
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


def nearby_driver_ids(state: "LiveRaceState",
                      followed_driver_id: str,
                      radius_m: float = NEARBY_RADIUS_M) -> Set[str]:
    """IDs dos pilotos a até radius_m do piloto acompanhado (inclui ele mesmo)."""
    followed = next((p for p in state.positions
                     if p.get("driver_id") == followed_driver_id), None)
    if followed is None:
        return {followed_driver_id}

    fx, fy = followed["position_xy"]
    ids = {followed_driver_id}
    for p in state.positions:
        px, py = p["position_xy"]
        if math.hypot(px - fx, py - fy) <= radius_m:
            ids.add(p["driver_id"])
    return ids


def _is_relevant(state: "LiveRaceState",
                 driver_id: str,
                 followed_driver_id: Optional[str]) -> bool:
    """Evento de um piloto só importa se for o acompanhado ou um rival próximo."""
    if followed_driver_id is None or len(state.positions) < FILTER_MIN_CARS:
        return True
    return driver_id in nearby_driver_ids(state, followed_driver_id)


def apply_event(state: LiveRaceState, event: dict,
                followed_driver_id: Optional[str] = None) -> List[tuple[int, str]]:
    """
    Atualiza o LiveRaceState com o evento recebido e retorna a lista de
    'eventos detectados' nessa atualização como tuplas (lap, event_string).
    """
    eventos: list[tuple[int, str]] = []
    event_type = event.get("type")
    # Volta do evento (vem no evento ou usa a volta atual do estado)
    event_lap = event.get("lap", state.lap)

    if event_type in ("position_update", "tick"):
        state.lap = event.get("lap", state.lap)
        if event.get("weather"):
            state.weather = event["weather"]
        new_positions = event.get("positions", [])
        current_by_driver = {}
        for idx, position in enumerate(new_positions):
            rank = int(position.get("position") or idx + 1)
            position["position"] = rank
            current_by_driver[position["driver_id"]] = rank
        if followed_driver_id is not None:
            old_pos = state.previous_positions_by_driver.get(followed_driver_id)
            new_pos = current_by_driver.get(followed_driver_id)
            if old_pos is not None and new_pos is not None and old_pos != new_pos:
                eventos.append((
                    state.lap,
                    f"Você mudou de posição: P{old_pos} -> P{new_pos}"
                ))
        state.previous_positions_by_driver = current_by_driver
        state.positions = new_positions

    elif event_type == "pit_stop":
        state.lap = event.get("lap", state.lap)
        driver_id = event.get("driver_id")
        state.recent_pit_stops.append(driver_id)
        if _is_relevant(state, driver_id, followed_driver_id):
            eventos.append((
                state.lap,
                f"Pit stop: piloto {driver_id} trocou para {event.get('new_compound')}"
            ))

    elif event_type == "tyre_worn":
        driver_id = event.get("driver_id")
        state.recent_tyre_warnings.append(driver_id)
        if _is_relevant(state, driver_id, followed_driver_id):
            eventos.append((
                state.lap,
                f"Pneu crítico: piloto {driver_id} ({event.get('tyre_life_pct')}% de vida)"
            ))

    elif event_type == "weather_changed":
        state.lap = event.get("lap", state.lap)
        state.weather = event.get("current", state.weather)
        prev_kind = event.get("previous", {}).get("kind")
        new_kind = event.get("current", {}).get("kind")
        if prev_kind != new_kind:
            state.weather_changed_recently = True
            eventos.append((state.lap, f"Clima mudou: {prev_kind} -> {new_kind}"))

    elif event_type == "lap_completed":
        state.lap = event.get("lap", state.lap)
        driver_id = event.get("driver_id")
        if _is_relevant(state, driver_id, followed_driver_id):
            eventos.append((
                state.lap,
                f"Volta completada: piloto {driver_id} na volta {event.get('lap')} ({event.get('lap_time_s')}s)"
            ))

    elif event_type == "off_track":
        driver_id = event.get("driver_id")
        state.lap = event.get("lap", state.lap)
        nome = event.get("driver_name", driver_id)
        quem = "Você" if driver_id == followed_driver_id else f"O rival {nome}"
        eventos.append((
            state.lap,
            f"{quem} saiu da pista ({event.get('side')}, "
            f"{event.get('distance_m')} m além da borda, "
            f"{event.get('speed_mps')} m/s) na volta {event.get('lap')}"
        ))

    elif event_type == "on_track":
        driver_id = event.get("driver_id")
        nome = event.get("driver_name", driver_id)
        quem = "Você" if driver_id == followed_driver_id else f"O rival {nome}"
        eventos.append((
            state.lap,
            f"{quem} voltou para a pista após {event.get('duration_s')}s"
        ))

    elif event_type == "race_radio":
        estado = event.get("state")
        prefixo = f"Rádio da equipe ({estado})" if estado else "Rádio da equipe"
        eventos.append((state.lap, f"{prefixo}: {event.get('message')}"))

    elif event_type == "race_start":
        eventos.append((state.lap, "Corrida iniciada"))

    elif event_type == "race_end":
        eventos.append((state.lap, "Corrida encerrada"))

    return eventos


def should_trigger_live(eventos_detectados: List[str]) -> bool:
    """
    Versão ao vivo do gatilho — sem safety car/red flag disponíveis na
    simulação, dispara em qualquer evento relevante detectado.
    """
    return len(eventos_detectados) > 0


def _progress(position: Dict[str, Any]) -> float:
    """Progresso de corrida do carro, em metros (campo do LivePublisher)."""
    return float(position.get("progress_m") or position.get("s_m") or 0.0)


def _gap_s(ahead: Dict[str, Any], behind: Dict[str, Any]) -> Optional[float]:
    """Intervalo aproximado em segundos, pelo progresso e pela velocidade."""
    distance = _progress(ahead) - _progress(behind)
    speed = float(behind.get("velocity_mps") or ahead.get("velocity_mps") or 0.0)
    if distance <= 0.0 or speed < 5.0:
        return None
    return distance / speed


def _describe_rival(rival: Dict[str, Any], relation: str) -> str:
    nome = rival.get("driver_name") or rival.get("driver_id", "?")
    pos = rival.get("position", "?")
    pneu = rival.get("tyre_compound")
    vida = rival.get("tyre_life_pct")
    extra = ""
    if pneu is not None and vida is not None:
        extra = f", pneu {pneu} {vida}%"
    return f"{relation}: {nome} (P{pos}{extra})"


def format_live_context(state: LiveRaceState,
                        followed_driver_id: str,
                        eventos: List[str],
                        last_command: Optional[str] = None,
                        last_aviso: Optional[str] = None) -> str:
    followed = next((p for p in state.positions if p.get(
        "driver_id") == followed_driver_id), None)

    total = len(state.positions)
    # `state.lap` é a menor volta completada entre os carros; a volta que está
    # sendo disputada é a seguinte.
    volta_atual = state.lap + 1
    if state.total_laps > 0:
        linhas = [f"Volta {volta_atual} de {state.total_laps}"]
    else:
        linhas = [f"Volta {volta_atual}"]
    # O engenheiro deve subir o tom ao longo da corrida. O piso é calculado
    # aqui e repetido na resposta do modelo pelo listener.
    urgencia = lap_urgency_floor(volta_atual, state.total_laps)
    if state.total_laps > 0:
        restantes = max(0, state.total_laps - volta_atual)
        linhas.append(
            f"Urgência da volta: {urgencia} "
            f"(faltam {restantes} volta(s) depois desta)"
        )
    else:
        linhas.append(f"Urgência da volta: {urgencia}")
    if followed:
        nome = followed.get("driver_name") or followed_driver_id
        pos = followed.get("position", "?")
        linhas.append(
            f"Carro acompanhado: {nome} ({followed_driver_id}) em P{pos} de {total}, "
            f"combustível {followed.get('fuel_kg')}kg, "
            f"pneu {followed.get('tyre_compound')} ({followed.get('tyre_life_pct')}% de vida), "
            f"ritmo {followed.get('velocity_mps')} m/s"
        )
        idx = state.positions.index(followed)
        gap_ahead: Optional[float] = None
        gap_behind: Optional[float] = None
        if idx > 0:
            ahead = state.positions[idx - 1]
            gap_ahead = _gap_s(ahead, followed)
            linhas.append(_describe_rival(ahead, "À frente de você") +
                          (f", {gap_ahead:.1f}s" if gap_ahead is not None else ""))
        else:
            linhas.append("À frente de você: ninguém, você lidera a corrida")
        if idx + 1 < total:
            behind = state.positions[idx + 1]
            gap_behind = _gap_s(followed, behind)
            linhas.append(_describe_rival(behind, "Atrás de você") +
                          (f", {gap_behind:.1f}s" if gap_behind is not None else ""))
        else:
            linhas.append("Atrás de você: ninguém, você é o último carro")
        # Leitura tática é um resumo, não uma ordem. Antes ela dizia "atacar" a
        # cada tick enquanto qualquer rival estivesse a menos de 2s, o que
        # fazia o engenheiro repetir push/overtake a corrida inteira. Agora só
        # destaca duelos realmente colados e deixa o rádio/eventos decidirem.
        pneu_gasto = isinstance(followed.get("tyre_life_pct"), (int, float)) and \
            followed["tyre_life_pct"] < 35.0
        combustivel_baixo = isinstance(followed.get("fuel_kg"), (int, float)) and \
            followed["fuel_kg"] < 40.0
        if pneu_gasto or combustivel_baixo:
            linhas.append(
                "Leitura tática: seu pneu/combustível está no limite; "
                "'conserve' tem prioridade sobre atacar."
            )
        elif gap_ahead is not None and gap_ahead < 0.9:
            linhas.append(
                "Leitura tática: rival à frente muito colado; 'overtake' ou "
                "'push' faz sentido agora."
            )
        elif gap_behind is not None and gap_behind < 0.9:
            linhas.append(
                "Leitura tática: rival atrás muito colado; 'defend' faz sentido agora."
            )
        elif total > 1:
            linhas.append(
                "Leitura tática: sem duelo imediato; use o rádio/eventos e evite "
                "repetir o mesmo comando."
            )
    if state.weather:
        kind = state.weather.get("kind", "?")
        track_temp = state.weather.get("track_temp")
        grip = state.weather.get("grip_factor")
        linhas.append(f"Clima: {kind}, pista {track_temp}°C, aderência {grip}")
    if eventos:
        linhas.append("Eventos recentes: " + "; ".join(eventos))
    else:
        linhas.append("Sem eventos relevantes novos")

    # O modelo tende a repetir a mesma frase quando o cenário não muda. Dar a
    # última mensagem explicitamente permite pedir variação e evita que o HUD
    # mostre "defenda" cinco vezes seguidas.
    if last_aviso:
        comando = f" (comando {last_command})" if last_command else ""
        linhas.append(f'Última mensagem do engenheiro: "{last_aviso}"{comando}')

    return "\n".join(linhas)
