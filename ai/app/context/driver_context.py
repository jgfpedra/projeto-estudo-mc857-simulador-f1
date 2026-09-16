import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / \
    "data" / "processed" / "f1.db"


def get_driver_context(race_id: int, driver_id: int, up_to_lap: int) -> dict:
    """
    Monta o contexto do piloto até uma volta específica da corrida:
    posição atual, gap pro líder e pro rival mais próximo, e histórico
    recente de ritmo.
    """
    conn = sqlite3.connect(DB_PATH)

    all_laps = pd.read_sql(
        """
        SELECT driverId, LapNumber, LapTime, Position
        FROM laps
        WHERE raceId = ? AND LapNumber <= ?
        ORDER BY driverId, LapNumber
        """,
        conn, params=[race_id, up_to_lap]
    )
    conn.close()

    if all_laps.empty:
        raise ValueError(f"Sem dados para raceId={race_id} até a volta {up_to_lap}")

    # tempo de corrida acumulado por piloto (aproximação: soma de LapTime)
    all_laps = all_laps.sort_values(["driverId", "LapNumber"])
    all_laps["cumulative_time"] = all_laps.groupby("driverId")["LapTime"].cumsum()

    # snapshot da última volta conhecida de cada piloto até up_to_lap
    latest = all_laps.groupby("driverId").tail(1).sort_values("Position")

    driver_row = latest[latest["driverId"] == driver_id]
    if driver_row.empty:
        raise ValueError(f"Piloto {driver_id} sem voltas até {up_to_lap} nessa corrida")
    driver_row = driver_row.iloc[0]

    current_position = int(driver_row["Position"])
    driver_time = driver_row["cumulative_time"]

    leader_row = latest[latest["Position"] == 1]
    gap_to_leader = None
    if not leader_row.empty and current_position != 1:
        gap_to_leader = round(driver_time - leader_row.iloc[0]["cumulative_time"], 3)

    rival_ahead_row = latest[latest["Position"] == current_position - 1]
    gap_to_rival_ahead = None
    if not rival_ahead_row.empty:
        gap_to_rival_ahead = round(
            driver_time - rival_ahead_row.iloc[0]["cumulative_time"], 3)

    rival_behind_row = latest[latest["Position"] == current_position + 1]
    gap_to_rival_behind = None
    if not rival_behind_row.empty:
        gap_to_rival_behind = round(
            rival_behind_row.iloc[0]["cumulative_time"] - driver_time, 3)

    # histórico recente de ritmo (últimas 5 voltas do próprio piloto)
    driver_laps = all_laps[all_laps["driverId"] == driver_id].tail(5)
    recent_laps = driver_laps["LapTime"].round(3).tolist()

    return {
        "driverId": driver_id,
        "volta_atual": up_to_lap,
        "posicao_atual": current_position,
        "gap_para_lider": float(gap_to_leader) if gap_to_leader is not None else None,
        "gap_para_rival_a_frente": float(gap_to_rival_ahead) if gap_to_rival_ahead is not None else None,
        "gap_para_rival_atras": float(gap_to_rival_behind) if gap_to_rival_behind is not None else None,
        "ultimas_voltas": [float(v) for v in recent_laps],
    }


def format_driver_context(context: dict) -> str:
    """Formata o contexto do piloto como texto pronto pra injetar no prompt."""
    linhas = [
        f"Posição atual: P{context['posicao_atual']} (volta {context['volta_atual']})",
    ]

    if context["gap_para_lider"] is not None:
        linhas.append(f"Gap para o líder: +{context['gap_para_lider']}s")
    else:
        linhas.append("Está na liderança")

    if context["gap_para_rival_a_frente"] is not None:
        linhas.append(
            f"Gap para o piloto à frente: +{context['gap_para_rival_a_frente']}s")

    if context["gap_para_rival_atras"] is not None:
        linhas.append(f"Gap para o piloto atrás: -{context['gap_para_rival_atras']}s")

    tendencia = "estável"
    voltas = context["ultimas_voltas"]
    if len(voltas) >= 3:
        if voltas[-1] > voltas[0] * 1.01:
            tendencia = "piorando (ritmo caindo)"
        elif voltas[-1] < voltas[0] * 0.99:
            tendencia = "melhorando"
    linhas.append(f"Últimas voltas: {voltas} (tendência: {tendencia})")

    return "\n".join(linhas)
