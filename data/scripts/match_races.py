import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "raw"


def match_all_races(year: int = 2024):
    races_ergast = pd.read_csv(RAW / "ergast" / "races.csv")
    races_year = races_ergast[races_ergast["year"] == year][
        ["raceId", "round", "name", "date"]
    ].copy()

    gp_events = pd.read_csv(RAW / "telemetry" / "GP.csv")
    gp_events_year = gp_events[gp_events["Year"] == year].copy()

    # renomeia pra evitar colisão de coluna (case-insensitive) no SQLite,
    # já que 'name'/'Name' e 'date'/'EventDate' são conceitos duplicados aqui
    gp_events_year = gp_events_year.rename(columns={
        "ID": "gp_id",
        "Name": "gp_name",
        "Location": "gp_location",
        "Country": "gp_country",
    })

    merged = races_year.merge(
        gp_events_year,
        left_on="date",
        right_on="EventDate",
        how="left"
    )

    sem_match = merged["gp_id"].isna().sum()
    if sem_match > 0:
        print(f"[match_races] AVISO: {sem_match} corridas de {
              year} sem correspondência em GP.csv")

    print(f"[match_races] {len(merged)} corridas de {year} mapeadas")
    return merged


if __name__ == "__main__":
    df = match_all_races()
    print(df[["raceId", "round", "name"]])
