import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # -> data/
RAW = BASE_DIR / "raw"


def build_driver_map():
    drivers_ergast = pd.read_csv(RAW / "ergast" / "drivers.csv")
    drivers_ergast["code"] = drivers_ergast["code"].str.strip().str.upper()

    pilotos = pd.read_csv(RAW / "telemetry" / "pilotos.csv")
    pilotos["Abbreviation"] = pilotos["Abbreviation"].str.strip().str.upper()

    driver_map = drivers_ergast.merge(
        pilotos, left_on="code", right_on="Abbreviation", how="inner"
    )
    driver_map = driver_map.sort_values("driverId").drop_duplicates(
        subset="Abbreviation", keep="last")

    driver_map = driver_map[["driverId", "code",
                             "Abbreviation", "DriverNumber", "forename", "surname"]]

    MANUAL_DRIVER_OVERRIDES = [
        {"driverId": 862, "code": "DOO", "Abbreviation": "DOO", "DriverNumber": 61,
         "forename": "Jack", "surname": "Doohan"},
    ]
    for override in MANUAL_DRIVER_OVERRIDES:
        if override["Abbreviation"] not in driver_map["Abbreviation"].values:
            driver_map = pd.concat(
                [driver_map, pd.DataFrame([override])], ignore_index=True)
            print(f"[driver_map] override manual aplicado: {override['Abbreviation']}")

    print(f"[driver_map] {len(driver_map)} pilotos mapeados (incluindo overrides)")
    return driver_map


if __name__ == "__main__":
    print(build_driver_map().head())
