# ai/scripts/test_race_context.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from context.race_context import get_race_context, format_race_context, should_trigger_alert

RACE_ID = 1129
FOLLOWED_DRIVER = 830  # ajuste se necessário

# snapshot ANTES do safety car (volta 24)
state_before = get_race_context(RACE_ID, FOLLOWED_DRIVER, up_to_lap=24)
print("=== Antes do Safety Car (volta 24) ===")
print(format_race_context(state_before))
print(f"Deveria disparar alerta? {should_trigger_alert(state_before)}")

# snapshot DEPOIS do safety car entrar (volta 26), comparando com o anterior
state_after = get_race_context(RACE_ID, FOLLOWED_DRIVER, up_to_lap=26, previous_state=state_before)
print("\n=== Depois do Safety Car entrar (volta 26) ===")
print(format_race_context(state_after))
print(f"Deveria disparar alerta? {should_trigger_alert(state_after)}")

# snapshot DEPOIS do safety car sair (volta 31)
state_retreated = get_race_context(RACE_ID, FOLLOWED_DRIVER, up_to_lap=31, previous_state=state_after)
print("\n=== Depois do Safety Car sair (volta 31) ===")
print(format_race_context(state_retreated))
print(f"Deveria disparar alerta? {should_trigger_alert(state_retreated)}")
