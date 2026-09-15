import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "processed" / "f1.db"


def build_database(driver_map, race_matches, enriched_laps, year: int = 2024):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # limpa dados desse ano específico, se a tabela já existir
    for table in ["races", "laps", "safety_cars", "red_flags"]:
        try:
            conn.execute(f"DELETE FROM {table} WHERE year = ?", (year,))
        except sqlite3.OperationalError:
            pass  # tabela ainda não existe (primeira execução) — segue normal

    try:
        driver_map.to_sql("drivers_temp", conn, if_exists="replace", index=False)
        conn.execute("""
            INSERT INTO drivers 
            SELECT * FROM drivers_temp 
            WHERE driverId NOT IN (SELECT driverId FROM drivers)
        """)
        conn.execute("DROP TABLE drivers_temp")
    except sqlite3.OperationalError:
        # tabela drivers ainda não existe — cria direto
        driver_map.to_sql("drivers", conn, if_exists="replace", index=False)

    races_to_save = race_matches.drop(
        columns=["EventDate", "Year"], errors="ignore").copy()
    races_to_save["year"] = year
    races_to_save.to_sql("races", conn, if_exists="append", index=False)

    laps_to_save = enriched_laps.copy()
    laps_to_save["year"] = year
    laps_to_save.to_sql("laps", conn, if_exists="append", index=False)

    from merge_events import get_safety_cars_for_year, get_red_flags_for_year, load_fatal_accidents

    safety_cars = get_safety_cars_for_year(race_matches, year)
    safety_cars["year"] = year
    safety_cars.to_sql("safety_cars", conn, if_exists="append", index=False)

    red_flags = get_red_flags_for_year(race_matches, year)
    red_flags["year"] = year
    red_flags.to_sql("red_flags", conn, if_exists="append", index=False)

    fatal_drivers, fatal_marshalls = load_fatal_accidents()
    fatal_drivers.to_sql("fatal_accidents_drivers", conn,
                         if_exists="replace", index=False)
    fatal_marshalls.to_sql("fatal_accidents_marshalls", conn,
                           if_exists="replace", index=False)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_laps_race ON laps(raceId)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_laps_driver ON laps(driverId)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_races_year ON races(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_safety_cars_race ON safety_cars(raceId)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_red_flags_race ON red_flags(raceId)")

    conn.commit()
    conn.close()
    print(f"[build_database] dados de {year} gravados em {DB_PATH}")


if __name__ == "__main__":
    from driver_map import build_driver_map
    from match_races import match_all_races
    from merge_laps_tyres import merge_laps_and_tyres

    dm = build_driver_map()
    rm = match_all_races(year=2024)
    laps = merge_laps_and_tyres(dm, rm, year=2024)
    build_database(dm, rm, laps, year=2024)
