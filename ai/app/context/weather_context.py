import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / \
    "data" / "processed" / "f1.db"

DRY_COMPOUNDS = {"SOFT", "MEDIUM", "HARD"}
WET_COMPOUNDS = {"INTERMEDIATE", "WET"}


def _get_race_weather(conn, race_id: int,
                      up_to_lap: int,
                      window: int = 5) -> pd.DataFrame:
    """
    Clima é o mesmo pra todos os pilotos numa dada volta (mesma pista, mesmo
    momento), então pega de qualquer piloto — usamos MIN(driverId) só pra
    ter uma linha por volta, evitando duplicar.
    """
    weather = pd.read_sql(
        """
        SELECT LapNumber, AirTemp, TrackTemp, Rainfall, Humidity
        FROM laps
        WHERE raceId = ? AND LapNumber <= ?
        GROUP BY LapNumber
        ORDER BY LapNumber
        """,
        conn, params=[race_id, up_to_lap]
    )
    return weather.tail(window)


def _get_driver_current_compound(conn,
                                 race_id: int,
                                 driver_id: int,
                                 up_to_lap: int) -> str:
    row = pd.read_sql(
        """
        SELECT Compound FROM laps
        WHERE raceId = ? AND driverId = ? AND LapNumber <= ?
        ORDER BY LapNumber DESC LIMIT 1
        """,
        conn, params=[race_id, driver_id, up_to_lap]
    )
    return row["Compound"].iloc[0] if not row.empty else None


def _detect_transition(weather_window: pd.DataFrame) -> str:
    """Compara a primeira metade da janela com a segunda pra detectar mudança de clima."""
    if len(weather_window) < 2:
        return "estavel"

    meio = len(weather_window) // 2
    inicio_chovendo = weather_window["Rainfall"].iloc[:meio or 1].mean() >= 0.5
    fim_chovendo = weather_window["Rainfall"].iloc[meio:].mean() >= 0.5

    if not inicio_chovendo and fim_chovendo:
        return "comecando_a_chover"
    if inicio_chovendo and not fim_chovendo:
        return "parando_de_chover"
    if fim_chovendo:
        return "chuva_estavel"
    return "seco_estavel"


def get_weather_context(race_id: int, driver_id: int, up_to_lap: int) -> dict:
    conn = sqlite3.connect(DB_PATH)

    weather_window = _get_race_weather(conn, race_id, up_to_lap)
    if weather_window.empty:
        conn.close()
        raise ValueError(f"Sem dados climáticos para raceId={
                         race_id} até a volta {up_to_lap}")

    current_compound = _get_driver_current_compound(conn, race_id, driver_id, up_to_lap)
    conn.close()

    latest = weather_window.iloc[-1]
    transicao = _detect_transition(weather_window)

    # sugestão de troca de composto baseada na transição + composto atual
    sugestao = None
    if transicao == "comecando_a_chover" and current_compound in DRY_COMPOUNDS:
        sugestao = "trocar para INTERMEDIATE (chuva começando, pneu seco perde aderência rapidamente)"
    elif transicao == "parando_de_chover" and current_compound in WET_COMPOUNDS:
        sugestao = "considerar troca para pneu seco (SOFT/MEDIUM) se a pista continuar secando"
    elif transicao == "chuva_estavel" and current_compound in DRY_COMPOUNDS:
        sugestao = "URGENTE: trocar para INTERMEDIATE/WET, pneu seco em pista molhada é perigoso"

    return {
        "driverId": driver_id,
        "volta_atual": up_to_lap,
        "composto_atual": current_compound,
        "chovendo_agora": bool(latest["Rainfall"]),
        "temperatura_ar": float(latest["AirTemp"]),
        "temperatura_pista": float(latest["TrackTemp"]),
        "umidade": float(latest["Humidity"]),
        "transicao_detectada": transicao,
        "sugestao_composto": sugestao,
    }


def format_weather_context(context: dict) -> str:
    linhas = [
        f"Clima atual: {'chovendo' if context['chovendo_agora'] else 'seco'} "
        f"(ar {context['temperatura_ar']}°C, pista {context['temperatura_pista']}°C, "
        f"umidade {context['umidade']}%)",
        f"Composto atual do piloto: {context['composto_atual']}",
    ]

    transicao_texto = {
        "comecando_a_chover": "Chuva começando agora",
        "parando_de_chover": "Chuva diminuindo/parando",
        "chuva_estavel": "Chuva estável",
        "seco_estavel": "Pista seca, sem mudança",
        "estavel": "Sem dados suficientes para detectar tendência",
    }
    linhas.append(f"Tendência: {transicao_texto.get(
        context['transicao_detectada'], context['transicao_detectada'])}")

    if context["sugestao_composto"]:
        linhas.append(f"Sugestão de pneu: {context['sugestao_composto']}")

    return "\n".join(linhas)
