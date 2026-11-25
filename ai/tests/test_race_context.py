from context.race_context import get_race_context, should_trigger_alert


def test_sem_safety_car_nao_dispara():
    ctx = get_race_context(race_id=1129, followed_driver_id=830, up_to_lap=24)
    assert ctx["safety_car"]["ativo"] is False
    assert should_trigger_alert(ctx) is False


def test_safety_car_aciona_e_dispara():
    before = get_race_context(race_id=1129, followed_driver_id=830, up_to_lap=24)
    after = get_race_context(race_id=1129, followed_driver_id=830,
                             up_to_lap=26, previous_state=before)
    assert after["safety_car"]["ativo"] is True
    assert should_trigger_alert(after) is True
    assert any("ACIONADO" in e for e in after["eventos_detectados"])


def test_safety_car_retirado_ainda_dispara():
    state_25 = get_race_context(1129, 830, up_to_lap=26)
    state_31 = get_race_context(1129, 830, up_to_lap=31, previous_state=state_25)
    assert state_31["safety_car"]["ativo"] is False
    assert any("RETIRADO" in e for e in state_31["eventos_detectados"])
