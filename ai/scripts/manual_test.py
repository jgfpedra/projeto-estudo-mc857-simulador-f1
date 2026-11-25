# ai/scripts/manual_test.py
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

from schemas import validate_output
from client import call_model


FAKE_CONTEXT = {
    "piloto": {
        "nome": "Lando Norris",
        "posicao_atual": 2,
        "gap_para_lider": 3.4,
        "gap_para_rival_atras": 1.1,
        "ultimas_5_voltas": [78.2, 78.5, 78.9, 79.3, 79.6],
    },
    "pneu": {
        "composto_atual": "MEDIUM",
        "voltas_no_pneu_atual": 22,
        "degradacao_estimada": "alta",
    },
    "clima": {
        "chovendo": False,
        "temperatura_pista": 41.2,
        "tendencia": "temperatura subindo",
    },
    "corrida": {
        "volta_atual": 34,
        "total_voltas": 58,
        "safety_car_ativo": False,
        "evento_recente": "rival diretamente atrás fez pit stop há 2 voltas (pneu novo)",
    },
}

PROMPT_TEMPLATE = """Você é um engenheiro de pista de Fórmula 1.
Analise o contexto abaixo e responda SOMENTE em JSON válido,
sem nenhum texto antes ou depois, seguindo exatamente este formato:

{{
  "aviso": "mensagem curta e direta ao piloto, em português",
  "previsao_pit_stop": "volta estimada para o próximo pit stop, ou 'não recomendado agora'",
  "urgencia": "baixa" | "media" | "alta"
}}

Contexto da corrida:
{contexto}
"""


def main():
    prompt = PROMPT_TEMPLATE.format(contexto=json.dumps(
        FAKE_CONTEXT, ensure_ascii=False, indent=2))
    raw_output, elapsed = call_model(prompt)
    print(f"Tempo: {elapsed:.2f}s")
    print(validate_output(raw_output))


if __name__ == "__main__":
    main()
