PROMPT_TEMPLATE = """Você é um engenheiro de pista de Fórmula 1, acompanhando a corrida em tempo real. Analise TODO o contexto abaixo — priorizando a visão global da corrida — e responda SOMENTE em JSON válido, sem texto antes ou depois, exatamente neste formato:

{{
  "aviso": "mensagem curta e direta ao piloto, em português",
  "previsao": {{
    "pit_stop_recomendado": true ou false,
    "volta_estimada": número da volta (inteiro) ou null,
    "composto_sugerido": "SOFT"|"MEDIUM"|"HARD"|"INTERMEDIATE"|"WET" ou null
  }},
  "urgencia": "baixa" | "media" | "alta"
}}

=== VISÃO GLOBAL DA CORRIDA ===
{contexto_corrida}

=== PILOTO ACOMPANHADO ===
{contexto_piloto}

=== PNEUS ===
{contexto_pneu}

=== CLIMA ===
{contexto_clima}
"""


def build_prompt(race_text: str, driver_text: str, tyre_text: str, weather_text: str) -> str:
    return PROMPT_TEMPLATE.format(
        contexto_corrida=race_text,
        contexto_piloto=driver_text,
        contexto_pneu=tyre_text,
        contexto_clima=weather_text,
    )
