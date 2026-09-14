from pathlib import Path
from driver_map import build_driver_map
from match_races import match_all_races
from merge_laps_tyres import merge_laps_and_tyres
from merge_weather import merge_weather
from build_race_context import build_and_export_all

BASE_DIR = Path(__file__).resolve().parent.parent
INTERMEDIATE = BASE_DIR / "processed" / "_intermediate"

def main():
    INTERMEDIATE.mkdir(parents=True, exist_ok=True)

    print("== Etapa 1: mapa de pilotos ==")
    driver_map = build_driver_map()
    driver_map.to_csv(INTERMEDIATE / "driver_map.csv", index=False)

    print("\n== Etapa 2: casamento de corridas ==")
    race_matches = match_all_races()
    race_matches.to_csv(INTERMEDIATE / "race_matches.csv", index=False)

    print("\n== Etapa 3: junção voltas + pneus ==")
    enriched_laps = merge_laps_and_tyres(driver_map, race_matches)
    enriched_laps.to_csv(INTERMEDIATE / "laps_enriched.csv", index=False)

    print("\n== Etapa 4: junção clima ==")
    laps_weather = merge_weather(enriched_laps)
    laps_weather.to_csv(INTERMEDIATE / "laps_with_weather.csv", index=False)

    print("\n== Etapa 5: exportação do contexto por corrida ==")
    build_and_export_all(laps_weather, race_matches)

    print("\nPipeline concluído.")


if __name__ == "__main__":
    main()
