# ai/app/schemas.py
REQUIRED_KEYS = {"aviso", "previsao_pit_stop", "urgencia"}
VALID_URGENCIA = {"baixa", "media", "alta"}


def validate_output(raw_output: str) -> dict | None:
    import json
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        print("[ERRO] Resposta não é JSON válido:", raw_output)
        return None

    missing = REQUIRED_KEYS - parsed.keys()
    if missing:
        print(f"[ERRO] Faltando chaves: {missing}")
        return None

    if parsed["urgencia"] not in VALID_URGENCIA:
        print(f"[AVISO] Valor inesperado de urgencia: {parsed['urgencia']}")

    return parsed
