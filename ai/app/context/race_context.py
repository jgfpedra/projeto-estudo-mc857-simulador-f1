import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / \
    "data" / "processed" / "f1.db"


def _get_global_positions(conn, race_id: int, up_to_lap: int) -> pd.DataFrame:
    laps = pd.read_sql(
        """
        SELECT driverId, LapNumber, LapTime, Position, TyreLife
        FROM laps
        WHERE raceId = ? AND LapNumber <= ?
        ORDER BY driverId, LapNumber
        """,
        conn, params=[race_id, up_to_lap]
    )
    laps = laps.sort_values(["driverId", "LapNumber"])
    laps["cumulative_time"] = laps.groupby("driverId")["LapTime"].cumsum()
    return laps.groupby("driverId").tail(1).sort_values("Position")


def _get_safety_car_status(conn, race_id: int, up_to_lap: int) -> dict:
    sc = pd.read_sql(
        "SELECT Cause, Deployed, Retreated FROM safety_cars WHERE raceId = ?",
        conn, params=[race_id]
    )
    if sc.empty:
        return {"ativo": False, "causa": None, "historico_na_corrida": []}

    ativo_agora = sc[(sc["Deployed"] <= up_to_lap) & (sc["Retreated"] >= up_to_lap)]
    ja_ocorreu = sc[sc["Deployed"] <= up_to_lap]

    return {
        "ativo": not ativo_agora.empty,
        "causa": ativo_agora.iloc[0]["Cause"] if not ativo_agora.empty else None,
        "historico_na_corrida": ja_ocorreu[["Cause", "Deployed", "Retreated"]].to_dict("records"),
    }


def _get_red_flag_status(conn, race_id: int, up_to_lap: int) -> dict:
    rf = pd.read_sql(
        "SELECT Lap, Incident FROM red_flags WHERE raceId = ? AND Lap <= ?",
        conn, params=[race_id, up_to_lap]
    )
    if rf.empty:
        return {"ocorreu": False, "detalhes": None}
    return {"ocorreu": True, "detalhes": rf.iloc[-1].to_dict()}


def _detect_pit_stops_recent(positions: pd.DataFrame, conn, race_id: int, up_to_lap: int, lookback: int = 2) -> list:
    """Pilotos que trocaram de pneu (TyreLife=1) nas últimas `lookback` voltas."""
    recent = pd.read_sql(
        """
        SELECT driverId, LapNumber, TyreLife
        FROM laps
        WHERE raceId = ? AND LapNumber > ? AND LapNumber <= ?
        """,
        conn, params=[race_id, up_to_lap - lookback, up_to_lap]
    )
    pit_drivers = recent[recent["TyreLife"] == 1]["driverId"].unique().tolist()
    return [int(d) for d in pit_drivers]


def get_race_context(race_id: int,
                     followed_driver_id: int,
                     up_to_lap: int,
                     previous_state: dict = None) -> dict:
    """
    Monta o estado global da corrida numa volta específica, e detecta eventos
    relevantes comparando com `previous_state` (snapshot de uma chamada anterior,
    se houver — permite ao #22 chamar isso a cada N voltas e ver o que mudou).
    """
    conn = sqlite3.connect(DB_PATH)

    positions = _get_global_positions(conn, race_id, up_to_lap)
    safety_car = _get_safety_car_status(conn, race_id, up_to_lap)
    red_flag = _get_red_flag_status(conn, race_id, up_to_lap)
    recent_pits = _detect_pit_stops_recent(positions, conn, race_id, up_to_lap)

    conn.close()

    followed_row = positions[positions["driverId"] == followed_driver_id]
    followed_position = int(
        followed_row.iloc[0]["Position"]) if not followed_row.empty else None

    # pilotos "próximos" (posição -1 a +1) — relevantes pro piloto acompanhado
    nearby_positions = {followed_position - 1,
                        followed_position + 1} if followed_position else set()
    nearby_drivers = positions[positions["Position"].isin(
        nearby_positions)]["driverId"].tolist()

    current_state = {
        "volta_atual": up_to_lap,
        "total_pilotos_ativos": len(positions),
        "piloto_acompanhado_posicao": followed_position,
        "safety_car": safety_car,
        "red_flag": red_flag,
        "pit_stops_recentes": recent_pits,
        "pilotos_proximos": [int(d) for d in nearby_drivers],
        "classificacao_top5": positions.head(5)[["driverId", "Position"]].astype(int).to_dict("records"),
    }

    # --- detecção de eventos relevantes (diff com snapshot anterior) ---
    eventos = []

    positions_values = [d["Position"] for d in current_state["classificacao_top5"]]
    if len(positions_values) != len(set(positions_values)):
        current_state[
            "aviso_dado_inconsistente"] = "Posições duplicadas detectadas (comum durante safety car)"

    if previous_state:
        if not previous_state["safety_car"]["ativo"] and current_state["safety_car"]["ativo"]:
            eventos.append(f"Safety car ACIONADO (causa: {
                           current_state['safety_car']['causa']})")
        if previous_state["safety_car"]["ativo"] and not current_state["safety_car"]["ativo"]:
            eventos.append("Safety car RETIRADO, corrida retomada")

        if not previous_state["red_flag"]["ocorreu"] and current_state["red_flag"]["ocorreu"]:
            eventos.append("Bandeira vermelha acionada")

        if current_state["piloto_acompanhado_posicao"] != previous_state["piloto_acompanhado_posicao"]:
            eventos.append(
                f"Piloto mudou de posição: P{
                    previous_state['piloto_acompanhado_posicao']} "
                f"-> P{current_state['piloto_acompanhado_posicao']}"
            )

        rivais_fizeram_pit = set(current_state["pit_stops_recentes"]) & set(
            current_state["pilotos_proximos"])
        if rivais_fizeram_pit:
            eventos.append(f"Rival(is) próximo(s) fez(fizeram) pit stop: {
                           list(rivais_fizeram_pit)}")

    current_state["eventos_detectados"] = eventos
    return current_state


def should_trigger_alert(context: dict) -> bool:
    """
    Define se vale a pena gerar um novo alerta pro agente de IA nesta volta,
    evitando chamar o Llama a cada volta sem necessidade.
    """
    if context["eventos_detectados"]:
        return True
    if context["safety_car"]["ativo"]:
        return True  # mantém aviso ativo enquanto SC estiver rodando
    return False


def format_race_context(context: dict) -> str:
    linhas = [
        f"Volta {context['volta_atual']} — Posição do piloto acompanhado: P{
            context['piloto_acompanhado_posicao']}",
    ]

    if context["safety_car"]["ativo"]:
        linhas.append(f"SAFETY CAR ATIVO (causa: {context['safety_car']['causa']})")

    if context["red_flag"]["ocorreu"]:
        linhas.append("Corrida teve bandeira vermelha")

    if context["eventos_detectados"]:
        linhas.append("Eventos recentes: " + "; ".join(context["eventos_detectados"]))
    else:
        linhas.append("Sem eventos relevantes novos")

    if context.get("aviso_dado_inconsistente"):
        linhas.append(f"[AVISO] {context['aviso_dado_inconsistente']}")

    top5 = ", ".join(f"P{d['Position']}:#{d['driverId']
                                          }" for d in context["classificacao_top5"])
    linhas.append(f"Top 5: {top5}")

    return "\n".join(linhas)
