from context.weather_context import get_weather_context, format_weather_context


def test_deteccao_inicio_de_chuva():
    ctx = get_weather_context(race_id=1132, driver_id=4, up_to_lap=20)
    assert ctx["transicao_detectada"] == "comecando_a_chover"
    assert ctx["sugestao_composto"] is not None
    assert "INTERMEDIATE" in ctx["sugestao_composto"]
