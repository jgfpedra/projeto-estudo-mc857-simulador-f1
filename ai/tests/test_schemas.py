from schemas import validate_agent_output, fallback_output


def test_json_valido_completo():
    raw = '{"aviso": "teste", "previsao": {"pit_stop_recomendado": true, "volta_estimada": 30, "composto_sugerido": "SOFT"}, "urgencia": "alta"}'
    result = validate_agent_output(raw)
    assert result["aviso"] == "teste"
    assert result["urgencia"] == "alta"


def test_json_invalido_retorna_none():
    result = validate_agent_output("isso não é json")
    assert result is None


def test_urgencia_invalida_normalizada():
    raw = '{"aviso": "x", "previsao": {"pit_stop_recomendado": false, "volta_estimada": null, "composto_sugerido": null}, "urgencia": "xyz"}'
    result = validate_agent_output(raw)
    assert result["urgencia"] == "media"


def test_fallback_tem_flag():
    result = fallback_output("timeout")
    assert result["fallback"] is True
    assert "timeout" in result["aviso"]
