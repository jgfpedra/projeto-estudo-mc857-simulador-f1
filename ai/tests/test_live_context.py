from live_context import (
    LiveRaceState,
    apply_event,
    format_live_context,
    lap_urgency_floor,
    max_urgency,
)


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


def _tick_positions():
    return [
        {"driver_id": "C0", "driver_name": "A", "velocity_mps": 40.0,
         "progress_m": 500.0, "fuel_kg": 100.0, "tyre_compound": "MEDIUM",
         "tyre_life_pct": 80.0, "position_xy": [0.0, 0.0]},
        {"driver_id": "C1", "driver_name": "B", "velocity_mps": 39.0,
         "progress_m": 480.0, "fuel_kg": 110.0, "tyre_compound": "SOFT",
         "tyre_life_pct": 97.0, "position_xy": [10.0, 0.0]},
    ]


def test_contexto_mostra_posicao_e_intervalos():
    st = LiveRaceState()
    apply_event(st, {"type": "tick", "sim_ts": 10.0, "lap": 0,
                     "positions": _tick_positions()}, "C1")
    texto = format_live_context(st, "C1", [])
    assert "P2 de 2" in texto
    assert "À frente de você: A (P1" in texto
    assert "0.5s" in texto
    assert "Leitura tática" in texto
    assert "último carro" in texto


def test_position_update_sem_rank_usa_ordem_da_lista():
    st = LiveRaceState()
    # position_update não passa pelo LivePublisher: sem campo `position`.
    apply_event(st, {"type": "position_update", "sim_ts": 5.0, "lap": 1,
                     "positions": _tick_positions()}, "C1")
    assert st.positions[0]["position"] == 1
    assert st.positions[1]["position"] == 2


def test_radio_aleatorio_entra_no_contexto():
    st = LiveRaceState()
    ev = apply_event(st, {"type": "race_radio", "state": "ataque",
                          "message": "Janela de DRS aberta."}, "C0")
    texto = format_live_context(st, "C0", ev)
    assert "Rádio da equipe (ataque): Janela de DRS aberta." in texto


def test_contexto_mostra_ultima_mensagem_do_engenheiro():
    st = LiveRaceState()
    texto = format_live_context(
        st, "C0", [], last_command="defend", last_aviso="Segure a posição")
    assert 'Última mensagem do engenheiro: "Segure a posição" (comando defend)' in texto


def test_urgencia_sobe_ao_longo_da_corrida():
    assert lap_urgency_floor(1, 3) == "baixa"
    assert lap_urgency_floor(2, 3) == "media"
    assert lap_urgency_floor(3, 3) == "alta"


def test_urgencia_alta_nos_15_por_cento_finais():
    # 10 voltas: 9 e 10 são "alta", 5..8 são "media".
    assert lap_urgency_floor(5, 10) == "media"
    assert lap_urgency_floor(8, 10) == "media"
    assert lap_urgency_floor(9, 10) == "alta"


def test_urgencia_sem_total_de_voltas_e_baixa():
    assert lap_urgency_floor(3, 0) == "baixa"
    assert lap_urgency_floor(0, 3) == "baixa"


def test_max_urgencia_respeita_o_piso():
    assert max_urgency("baixa", "alta") == "alta"
    assert max_urgency("alta", "baixa") == "alta"
    assert max_urgency("media", "media") == "media"
    assert max_urgency(None, "media") == "media"
    assert max_urgency("invalida", "baixa") == "baixa"


def test_contexto_mostra_urgencia_da_volta():
    st = LiveRaceState(lap=2, total_laps=3)
    texto = format_live_context(st, "C0", [])
    assert "Volta 3 de 3" in texto
    assert "Urgência da volta: alta" in texto
