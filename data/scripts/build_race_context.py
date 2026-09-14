import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "processed" / "2024"


def build_race_context(race_id, enriched_laps, race_matches):
    race_info = race_matches[race_matches["raceId"] == race_id].iloc[0]
    race_laps = enriched_laps[enriched_laps["raceId"] == race_id]

    drivers_data = []
    for driver_id, grupo in race_laps.groupby("driverId"):
        if pd.isna(driver_id):
            continue
        drivers_data.append({
            "driverId": int(driver_id),
            "laps": grupo[[
                "LapNumber", "LapTime", "Compound", "TyreLife",
                "Sector1Time", "Sector2Time", "Sector3Time",
                "AirTemp", "TrackTemp", "Rainfall"
            ]].to_dict("records")
        })

    return {
        "raceId": int(race_id),
        "round": int(race_info["round"]),
        "name": race_info["name"],
        "drivers": drivers_data
    }


def build_and_export_all(enriched_laps, race_matches):
    PROCESSED.mkdir(parents=True, exist_ok=True)

    for race_id in race_matches["raceId"].unique():
        context = build_race_context(race_id, enriched_laps, race_matches)
        out_path = PROCESSED / f"race_{race_id}.json"
        with open(out_path, "w") as f:
            json.dump(context, f, indent=2, default=str)
        print(f"[build_race_context] exportado {out_path}")


if __name__ == "__main__":
    from driver_map import build_driver_map
    from match_races import match_all_races
    from merge_laps_tyres import merge_laps_and_tyres
    from merge_weather import merge_weather

    dm = build_driver_map()
    rm = match_all_races()
    laps = merge_laps_and_tyres(dm, rm)
    laps_weather = merge_weather(laps)
    build_and_export_all(laps_weather, rm)
