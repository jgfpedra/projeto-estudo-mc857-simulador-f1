import sqlite3
import pandas as pd
conn = sqlite3.connect("../../data/processed/f1.db")
df = pd.read_sql(
    "SELECT driverId, Position FROM laps WHERE raceId=1141 AND LapNumber=20 ORDER BY Position", conn)
print(df)
