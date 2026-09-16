from context.tyre_context import get_tyre_context, format_tyre_context


def test_stint_longo_monaco():
    ctx = get_tyre_context(race_id=1128, driver_id=846, up_to_lap=70)
    assert ctx["composto_atual"] == "HARD"
    assert ctx["voltas_no_pneu_atual"] == 70


def test_degradacao_tem_nivel_valido():
    ctx = get_tyre_context(race_id=1128, driver_id=846, up_to_lap=70)
    assert ctx["degradacao"]["nivel"] in {
        "negativa (ritmo melhorando, possível efeito de combustível/pista)",
        "baixa", "media", "alta", "indeterminado (poucas voltas no stint)"
    }


def test_formatacao_sem_contradicao():
    ctx = get_tyre_context(race_id=1128, driver_id=846, up_to_lap=70)
    texto = format_tyre_context(ctx)
    if "negativa" in ctx["degradacao"]["nivel"] or ctx["degradacao"]["nivel"] == "baixa":
        assert "PRÓXIMA" not in texto or "urgência" not in texto.lower()
