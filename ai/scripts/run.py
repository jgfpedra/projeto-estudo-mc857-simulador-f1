# ai/scripts/find_advanced_stint.py
import sqlite3
import pandas as pd

conn = sqlite3.connect("../../data/processed/f1.db")
df = pd.read_sql(
    """
    SELECT raceId, driverId, Compound, MAX(TyreLife) as max_tyrelife, MAX(LapNumber) as last_lap
    FROM laps
    GROUP BY raceId, driverId
    ORDER BY max_tyrelife DESC
    LIMIT 10
    """,
    conn
)
print(df)
