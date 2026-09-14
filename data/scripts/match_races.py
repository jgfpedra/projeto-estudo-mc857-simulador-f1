import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "raw"


def match_all_races():
    """
    Casa cada corrida de 2024 (Ergast) com o evento equivalente em
    telemetry/GP.csv, via data. O `round` do Ergast é o que efetivamente
    usaremos como chave pra casar com RoundNumber do dataset de pneus/clima.
    """
    races_ergast = pd.read_csv(RAW / "ergast" / "races.csv")
    races_2024 = races_ergast[races_ergast["year"] == 2024][
        ["raceId", "round", "name", "date"]
    ].copy()

    gp_events = pd.read_csv(RAW / "telemetry" / "GP.csv")
    gp_events_2024 = gp_events[gp_events["Year"] == 2024]

    merged = races_2024.merge(
        gp_events_2024,
        left_on="date",
        right_on="EventDate",
        how="left"
    )

    sem_match = merged["ID"].isna().sum()
    if sem_match > 0:
        print(f"[match_races] AVISO: {sem_match} corridas sem correspondência em "
              f"telemetry/GP.csv (conferir formato de data). O pipeline segue "
              f"normalmente usando só o Ergast (raceId/round) pra essas.")

    print(f"[match_races] {len(merged)} corridas de 2024 mapeadas")
    return merged


if __name__ == "__main__":
    df = match_all_races()
    print(df[["raceId", "round", "name"]])
