from live_context import LiveRaceState, apply_event


def _state(n_cars, far_from_followed=()):
    positions = []
    for i in range(n_cars):
        did = f"C{i}"
        x = 1000.0 if did in far_from_followed else float(i)  # perto ou longe
        positions.append({"driver_id": did, "position_xy": [x, 0.0]})
    return LiveRaceState(positions=positions)


def test_rival_proximo_dispara():
    st = _state(5)
    ev = apply_event(st, {"type": "pit_stop", "driver_id": "C1",
                          "lap": 3, "new_compound": "HARD"}, "C0")
    assert ev


def test_rival_distante_nao_dispara():
    st = _state(5, far_from_followed={"C4"})
    ev = apply_event(st, {"type": "pit_stop", "driver_id": "C4",
                          "lap": 3, "new_compound": "HARD"}, "C0")
    assert ev == []
    assert "C4" in st.recent_pit_stops  # estado continua registrado


def test_poucos_carros_nao_filtra():
    st = _state(2, far_from_followed={"C1"})
    ev = apply_event(st, {"type": "pit_stop", "driver_id": "C1",
                          "lap": 3, "new_compound": "HARD"}, "C0")
    assert ev
