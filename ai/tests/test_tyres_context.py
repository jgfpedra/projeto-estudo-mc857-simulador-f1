# ai/scripts/test_tyre_context.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from context.tyre_context import get_tyre_context, format_tyre_context

RACE_ID = 1128
DRIVER_ID = 846
UP_TO_LAP = 70  # perto do fim, stint bem avançado

context = get_tyre_context(RACE_ID, DRIVER_ID, UP_TO_LAP)

print("=== Contexto bruto ===")
print(context)

print("\n=== Formatado para o prompt ===")
print(format_tyre_context(context))
