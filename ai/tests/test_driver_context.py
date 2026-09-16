from context.driver_context import get_driver_context, format_driver_context


def test_meio_do_pelotao():
    ctx = get_driver_context(race_id=1141, driver_id=830, up_to_lap=20)
    assert ctx["posicao_atual"] == 6
    assert ctx["gap_para_rival_a_frente"] == 0.593
    assert len(ctx["ultimas_voltas"]) == 5


def test_lider_sem_gap():
    ctx = get_driver_context(race_id=1141, driver_id=847, up_to_lap=20)
    assert ctx["posicao_atual"] == 1
    assert ctx["gap_para_lider"] is None
    assert ctx["gap_para_rival_a_frente"] is None


def test_formatacao_nao_quebra():
    ctx = get_driver_context(race_id=1141, driver_id=830, up_to_lap=20)
    texto = format_driver_context(ctx)
    assert "P6" in texto
    assert isinstance(texto, str)
