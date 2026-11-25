import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / \
    "data" / "processed" / "f1.db"


def _get_current_stint(conn, race_id: int,
                       driver_id: int,
                       up_to_lap: int) -> pd.DataFrame:
    """Retorna as voltas do stint atual (desde a última troca de pneu até up_to_lap)."""
    laps = pd.read_sql(
        """
        SELECT LapNumber, LapTime, Compound, TyreLife, FreshTyre
        FROM laps
        WHERE raceId = ? AND driverId = ? AND LapNumber <= ?
        ORDER BY LapNumber
        """,
        conn, params=[race_id, driver_id, up_to_lap]
    )
    if laps.empty:
        return laps

    # o stint atual começa na última vez que TyreLife caiu (reset = pit stop)
    stint_start_idx = laps[laps["TyreLife"] < laps["TyreLife"].shift(1)].index
    start = stint_start_idx[-1] if len(stint_start_idx) > 0 else 0
    return laps.loc[start:]


def _estimate_degradation(stint_laps: pd.DataFrame) -> dict:
    if len(stint_laps) < 3:
        return {"segundos_por_volta": None,
                "nivel": "indeterminado (poucas voltas no stint)"}

    valid = stint_laps.iloc[1:] if len(stint_laps) > 3 else stint_laps

    x = valid["TyreLife"].values
    y = valid["LapTime"].values
    slope = np.polyfit(x, y, 1)[0]

    if slope < 0:
        nivel = "negativa (ritmo melhorando, possível efeito de combustível/pista)"
    elif slope < 0.05:
        nivel = "baixa"
    elif slope < 0.15:
        nivel = "media"
    else:
        nivel = "alta"

    return {"segundos_por_volta": round(float(slope), 3), "nivel": nivel}


def _get_historical_stint_length(conn, compound: str) -> dict:
    """
    Calcula, entre todas as corridas de 2024, a duração média/mediana de
    stints com esse composto — usado como referência de janela de pit stop.
    """
    stints = pd.read_sql(
        """
        SELECT raceId, driverId, Compound, MAX(TyreLife) as stint_length
        FROM laps
        WHERE Compound = ?
        GROUP BY raceId, driverId, Compound
        """,
        conn, params=[compound]
    )
    if stints.empty:
        return {"media": None, "mediana": None, "amostras": 0}

    return {
        "media": round(float(stints["stint_length"].mean()), 1),
        "mediana": round(float(stints["stint_length"].median()), 1),
        "amostras": int(len(stints)),
    }


def get_tyre_context(race_id: int, driver_id: int, up_to_lap: int) -> dict:
    conn = sqlite3.connect(DB_PATH)

    stint_laps = _get_current_stint(conn, race_id, driver_id, up_to_lap)
    if stint_laps.empty:
        conn.close()
        raise ValueError(f"Sem dados de pneu para driverId={
                         driver_id} até a volta {up_to_lap}")

    current = stint_laps.iloc[-1]
    compound = current["Compound"]
    tyre_life = int(current["TyreLife"])
    fresh_tyre = bool(current["FreshTyre"])

    degradation = _estimate_degradation(stint_laps)
    historical = _get_historical_stint_length(conn, compound)
    conn.close()

    voltas_restantes_estimadas = None
    if historical["media"] is not None:
        voltas_restantes_estimadas = max(0, round(historical["media"] - tyre_life))

    return {
        "driverId": driver_id,
        "volta_atual": up_to_lap,
        "composto_atual": compound,
        "voltas_no_pneu_atual": tyre_life,
        "pneu_era_novo_no_stint": fresh_tyre,
        "degradacao": degradation,
        "referencia_historica_2024": historical,
        "voltas_restantes_estimadas_ate_pit": voltas_restantes_estimadas,
    }


def format_tyre_context(context: dict) -> str:
    linhas = [
        f"Pneu atual: {context['composto_atual']
                       } ({context['voltas_no_pneu_atual']} voltas de uso)",
    ]

    deg = context["degradacao"]
    if deg["segundos_por_volta"] is not None:
        linhas.append(
            f"Degradação estimada: {deg['nivel']
                                    } ({deg['segundos_por_volta']}s/volta de perda)"
        )
    else:
        linhas.append(f"Degradação estimada: {deg['nivel']}")

    hist = context["referencia_historica_2024"]
    if hist["media"] is not None:
        linhas.append(
            f"Referência histórica 2024 para {
                context['composto_atual']} (todos os circuitos): "
            f"~{hist['media']} voltas (n={hist['amostras']})"
        )

    # decisão de pit stop: prioriza degradação real sobre média histórica genérica
    if deg["nivel"] == "alta":
        linhas.append("Janela de pit stop: recomendado em breve (degradação real alta)")
    elif deg["nivel"] == "baixa" and context["voltas_no_pneu_atual"] > (hist["media"] or 0):
        linhas.append(
            "Janela de pit stop: pneu já passou da média histórica, mas degradação real "
            "está baixa — não há urgência, mas fica fora do padrão observado em 2024"
        )
    elif context["voltas_restantes_estimadas_ate_pit"] is not None and context["voltas_restantes_estimadas_ate_pit"] <= 3:
        linhas.append(f"Janela de pit stop: aproximando-se (~{
                      context['voltas_restantes_estimadas_ate_pit']} voltas, baseado em histórico)")
    else:
        linhas.append("Janela de pit stop: sem urgência no momento")

    return "\n".join(linhas)
