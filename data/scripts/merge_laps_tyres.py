import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "raw"


def merge_laps_and_tyres(driver_map, race_matches):
    """
    Usa cleaned_driver_2024.csv como fonte principal de voltas (já traz
    setores, composto e tyre life por volta, para todas as corridas),
    casando raceId via RoundNumber e driverId via código do piloto.
    """
    laps = pd.read_csv(RAW / "tyres" / "cleaned_driver_2024.csv")
    laps["Driver"] = laps["Driver"].str.strip().str.upper()

    # confirmar o valor exato usado pra sessão de corrida (ex: "R") antes de travar isso
    laps_race = laps[laps["Session"] == "R"].copy()

    laps_race = laps_race.merge(
        race_matches[["raceId", "round"]],
        left_on="RoundNumber",
        right_on="round",
        how="left"
    )

    laps_race = laps_race.merge(
        driver_map[["driverId", "code"]],
        left_on="Driver",
        right_on="code",
        how="left"
    )

    sem_raceid = laps_race["raceId"].isna().sum()
    sem_driverid = laps_race["driverId"].isna().sum()
    if sem_raceid > 0:
        print(f"[merge_laps_tyres] AVISO: {
              sem_raceid} linhas sem raceId (RoundNumber sem match)")
    if sem_driverid > 0:
        print(f"[merge_laps_tyres] AVISO: {
              sem_driverid} linhas sem driverId (código sem match)")

    return laps_race


if __name__ == "__main__":
    from driver_map import build_driver_map
    from match_races import match_all_races

    dm = build_driver_map()
    rm = match_all_races()
    df = merge_laps_and_tyres(dm, rm)
    print(df.head())
    print(df.shape)
