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
        pilotos,
        left_on="code",
        right_on="Abbreviation",
        how="inner"
    )

    print(f"[driver_map] {len(driver_map)}/{len(pilotos)
                                            } pilotos casados via código de 3 letras")

    if len(driver_map) < len(pilotos):
        nao_casados = pilotos[~pilotos["Abbreviation"].isin(driver_map["Abbreviation"])]
        print("[driver_map] Não casados (revisar manualmente):")
        print(nao_casados[["Abbreviation", "FullName"]])

    return driver_map[["driverId", "code", "Abbreviation", "DriverNumber", "forename", "surname"]]


if __name__ == "__main__":
    print(build_driver_map().head())
