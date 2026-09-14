import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "raw"

def merge_weather(laps_enriched):
    """
    Anexa a leitura de clima mais próxima no tempo (merge_asof), agrupando
    por RoundNumber + Session, já que o clima é medido continuamente,
    não por volta.
    """
    weather = pd.read_csv(RAW / "tyres" / "cleaned_weather_2024.csv")

    weather["Time"] = pd.to_timedelta(weather["Time"], errors="coerce")
    laps_enriched = laps_enriched.copy()
    laps_enriched["Time"] = pd.to_timedelta(laps_enriched["Time"], errors="coerce")

    partes = []
    for (round_number, session), grupo in laps_enriched.groupby(["RoundNumber", "Session"]):
        clima_grupo = weather[
            (weather["RoundNumber"] == round_number) &
            (weather["Session"] == session)
        ].sort_values("Time")

        laps_ordenadas = grupo.sort_values("Time")

        if clima_grupo.empty:
            partes.append(laps_ordenadas)
            continue

        unido = pd.merge_asof(
            laps_ordenadas,
            clima_grupo[["Time", "AirTemp", "TrackTemp", "Humidity", "Rainfall", "WindSpeed"]],
            on="Time",
            direction="nearest"
        )
        partes.append(unido)

    return pd.concat(partes, ignore_index=True)


if __name__ == "__main__":
    from driver_map import build_driver_map
    from match_races import match_all_races
    from merge_laps_tyres import merge_laps_and_tyres

    dm = build_driver_map()
    rm = match_all_races()
    laps = merge_laps_and_tyres(dm, rm)
    print(merge_weather(laps).head())
