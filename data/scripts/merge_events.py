import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "raw"


def get_safety_cars_for_year(race_matches, year: int):
    safety_cars = pd.read_csv(RAW / "events" / "safety_cars.csv")

    race_matches = race_matches.copy()
    race_matches["race_key"] = f"{year} " + race_matches["name"]

    merged = safety_cars.merge(
        race_matches[["raceId", "race_key"]],
        left_on="Race",
        right_on="race_key",
        how="inner"
    )
    print(f"[merge_events] ({len(
        merged)}/{len(safety_cars[safety_cars['Race'].str.startswith(str(year))])} safety cars casados p/ {year}")
    return merged.drop(columns=["race_key"])


def get_red_flags_for_year(race_matches, year: int):
    red_flags = pd.read_csv(RAW / "events" / "red_flags.csv")

    race_matches = race_matches.copy()
    race_matches["race_key"] = f"{year} " + race_matches["name"]

    merged = red_flags.merge(
        race_matches[["raceId", "race_key"]],
        left_on="Race",
        right_on="race_key",
        how="inner"
    )
    total_do_ano = len(red_flags[red_flags["Race"].str.startswith(str(year))])
    print(f"[merge_events] {len(merged)}/{total_do_ano} red flags casados p/ {year}")
    return merged.drop(columns=["race_key"])


def load_fatal_accidents():
    """
    Carregado uma vez só, sem filtro de ano — é dado histórico geral,
    não específico da temporada sendo processada.
    """
    drivers = pd.read_csv(RAW / "events" / "fatal_accidents_drivers.csv")
    marshalls = pd.read_csv(RAW / "events" / "fatal_accidents_marshalls.csv")
    return drivers, marshalls
