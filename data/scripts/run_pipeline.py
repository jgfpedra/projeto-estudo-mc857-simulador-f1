import sys
from pathlib import Path
from driver_map import build_driver_map
from match_races import match_all_races
from merge_laps_tyres import merge_laps_and_tyres
from build_database import build_database


def run_for_year(year: int):
    print(f"\n===== Processando temporada {year} =====")

    print("== Etapa 1: mapa de pilotos ==")
    driver_map = build_driver_map()

    print("== Etapa 2: casamento de corridas ==")
    race_matches = match_all_races(year=year)

    print("== Etapa 3: junção voltas + pneus + clima ==")
    enriched_laps = merge_laps_and_tyres(driver_map, race_matches, year=year)

    print("== Etapa 4: gravação no banco ==")
    build_database(driver_map, race_matches, enriched_laps, year=year)


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or [2024]
    for year in years:
        run_for_year(year)
    print("\nPipeline concluído.")
