import pandas as pd
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "processed" / "f1.db"

conn = sqlite3.connect(DB_PATH)
conn = sqlite3.connect(DB_PATH)

# 1. Tipo real da coluna em cada tabela
print(conn.execute("SELECT typeof(raceId) FROM races LIMIT 1").fetchone())
print(conn.execute("SELECT typeof(raceId) FROM laps LIMIT 1").fetchone())

# 2. Quais raceId realmente existem em laps
distinct_laps = pd.read_sql("SELECT DISTINCT raceId FROM laps ORDER BY raceId", conn)
print(distinct_laps)

# 3. Comparar contra os raceId esperados de 'races'
distinct_races = pd.read_sql(
    "SELECT raceId, round, name FROM races ORDER BY round", conn)
print(distinct_races)
