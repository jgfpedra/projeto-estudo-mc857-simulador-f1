# data/scripts/sanity_check.py
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "processed" / "f1.db"

conn = sqlite3.connect(DB_PATH)

print("== Contagem geral ==")
for table in ["drivers", "races", "laps", "safety_cars", "red_flags"]:
    count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn)["n"][0]
    print(f"{table}: {count} linhas")

print("\n== São Paulo GP 2024 (teve chuva forte + red flag) ==")
race = pd.read_sql(
    "SELECT raceId, name FROM races WHERE year = 2024 AND name LIKE '%São Paulo%'",
    conn
)
print(race)

race_id = int(race["raceId"].iloc[0])

print("\n== Amostra de voltas (Interlagos, sob chuva) ==")
laps = pd.read_sql(
    """
    SELECT driverId, LapNumber, LapTime, Compound, TyreLife, Rainfall, TrackTemp
    FROM laps
    WHERE raceId = ?
    ORDER BY LapNumber
    LIMIT 10
    """,
    conn, params=[race_id]
)
print(laps)

print("\n== Red flag registrada para essa corrida? ==")
rf = pd.read_sql("SELECT * FROM red_flags WHERE raceId = ?", conn, params=[race_id])
print(rf)

print("\n== Pit stops por piloto na corrida (via TyreLife resetando) ==")
pitstops = pd.read_sql(
    """
    SELECT driverId, LapNumber, Compound, TyreLife
    FROM laps
    WHERE raceId = ? AND TyreLife = 1
    ORDER BY driverId, LapNumber
    """,
    conn, params=[race_id]
)
print(pitstops)

conn.close()
