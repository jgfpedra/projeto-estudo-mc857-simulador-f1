import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from context.driver_context import get_driver_context, format_driver_context

# São Paulo 2024 (raceId=1141), volta 20 — meio da corrida, antes da chuva pesada
RACE_ID = 1141
DRIVER_ID = 830  # ajuste para um driverId real do seu banco (ex: Norris, Verstappen)
UP_TO_LAP = 20

context_lider = get_driver_context(1141, 847, 20)
print(context_lider)

context = get_driver_context(RACE_ID, DRIVER_ID, UP_TO_LAP)

print("=== Contexto bruto ===")
print(context)

print("\n=== Formatado para o prompt ===")
print(format_driver_context(context))
