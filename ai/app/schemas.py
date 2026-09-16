import json

REQUIRED_KEYS = {"aviso", "previsao", "urgencia"}
REQUIRED_PREVISAO_KEYS = {"pit_stop_recomendado", "volta_estimada", "composto_sugerido"}
VALID_URGENCIA = {"baixa", "media", "alta"}


def validate_agent_output(raw_output: str) -> dict | None:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        print("[schemas] ERRO: resposta não é JSON válido:", raw_output)
        return None

    missing = REQUIRED_KEYS - parsed.keys()
    if missing:
        print(f"[schemas] ERRO: faltando chaves de topo: {missing}")
        return None

    if not isinstance(parsed.get("previsao"), dict):
        print("[schemas] ERRO: 'previsao' deveria ser um objeto")
        return None

    missing_previsao = REQUIRED_PREVISAO_KEYS - parsed["previsao"].keys()
    if missing_previsao:
        print(f"[schemas] AVISO: faltando chaves em 'previsao': {
              missing_previsao} (preenchendo com None)")
        for key in missing_previsao:
            parsed["previsao"][key] = None

    if parsed["urgencia"] not in VALID_URGENCIA:
        print(f"[schemas] AVISO: urgencia inesperada '{
              parsed['urgencia']}', ajustando para 'media'")
        parsed["urgencia"] = "media"

    return parsed


def fallback_output(motivo: str) -> dict:
    """Usado quando o modelo falha/timeout — o sistema não pode travar esperando o Llama."""
    return {
        "aviso": f"[Engenheiro indisponível: {motivo}]",
        "previsao": {"pit_stop_recomendado": None, "volta_estimada": None, "composto_sugerido": None},
        "urgencia": "baixa",
        "fallback": True,
    }
