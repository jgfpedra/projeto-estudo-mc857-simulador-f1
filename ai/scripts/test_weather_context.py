# ai/scripts/test_weather_context.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from context.weather_context import get_weather_context, format_weather_context

RACE_ID = 1132
UP_TO_LAP = 20  # 2 voltas depois do início da chuva (volta 18) — pega a transição

# pega um driverId qualquer que exista nessa corrida com pneu seco antes da chuva
DRIVER_ID = 4  # ajustar se necessário

context = get_weather_context(RACE_ID, DRIVER_ID, UP_TO_LAP)

print("=== Contexto bruto ===")
print(context)

print("\n=== Formatado para o prompt ===")
print(format_weather_context(context))
