import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from client import warm_up
from agent import analyze_lap

RACE_ID = 1129       # Canadá 2024, safety car nas voltas 25-30
DRIVER_ID = 830
START_LAP = 23
END_LAP = 32

warm_up()

previous_state = None

for lap in range(START_LAP, END_LAP + 1):
    result = analyze_lap(RACE_ID, DRIVER_ID, lap, previous_race_state=previous_state)
    previous_state = result["race_state"]

    if not result["disparou"]:
        print(f"[volta {lap}] sem eventos relevantes, agente não acionado")
        continue

    output = result["output"]
    print(f"\n[volta {lap}] AGENTE ACIONADO (resposta em {output['tempo_resposta']}s)")
    print(f"  -> Aviso ao piloto: {output['aviso']}")
    print(f"  -> Previsão: {output['previsao']}")
    print(f"  -> Urgência: {output['urgencia']}" + (" [AJUSTADA]" if output.get("urgencia_ajustada") else ""))
    if output.get("fallback"):
        print(f"  [FALLBACK ATIVADO]")
