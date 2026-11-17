"""Testes da tradução pedido-do-front -> objetos do motor (sem PyBullet, sem rede)."""

import pytest
from pydantic import ValidationError

from api.race_setup import (
    CatalogRequired,
    SetupError,
    build_race_setup,
    build_transition_config,
    weather_state,
)
from api.schemas import RaceSetupRequest, WeatherChange, WeatherName
from api_fixtures import FakeLoader, make_catalog
from domain import TyreCompound, WeatherKind


def req(**kw):
    return RaceSetupRequest(**kw)


# -- clima ---------------------------------------------------------------------

@pytest.mark.parametrize("name,kind,rain", [
    (WeatherName.dry, WeatherKind.DRY, None),
    (WeatherName.cloudy, WeatherKind.CLOUDY, None),
    (WeatherName.light_rain, WeatherKind.DAMP, 0.5),
    (WeatherName.rain, WeatherKind.WET, None),
    (WeatherName.heavy_rain, WeatherKind.WET, 8.0),
])
def test_clima_inicial_mapeia_para_o_motor(name, kind, rain):
    st = weather_state(name)
    assert st.kind == kind
    if rain is not None:
        assert st.rainfall == rain


def test_aderencia_cai_com_a_intensidade_da_chuva():
    grips = [weather_state(w).grip_factor for w in
             (WeatherName.dry, WeatherName.cloudy, WeatherName.light_rain, WeatherName.rain, WeatherName.heavy_rain)]
    assert grips == sorted(grips, reverse=True)
    assert grips[-1] < grips[-2]          # chuva forte é pior que chuva


def test_sem_mudanca_de_clima_o_clima_nunca_muda():
    cfg = build_transition_config(WeatherKind.DRY, None)
    assert cfg.transition_prob_per_lap == 0.0   # o padrão do motor (5%) sortearia mudanças
    setup = build_race_setup(req(laps=3), None, seed=1)
    for lap in range(1, 200):
        assert setup.weather_model.step(lap).kind == WeatherKind.DRY


def test_mudanca_de_clima_sorteia_so_entre_os_climas_possiveis():
    change = WeatherChange(probability_per_lap=1.0, possible=[WeatherName.rain])
    setup = build_race_setup(req(laps=3, weather_change=change), None, seed=7)
    seen = {setup.weather_model.step(lap).kind for lap in range(1, 60)}
    assert seen <= {WeatherKind.DRY, WeatherKind.WET}       # nunca CLOUDY/DAMP
    assert WeatherKind.WET in seen


def test_matriz_de_transicao_tem_linhas_normalizadas_e_sem_ficar_parado():
    change = WeatherChange(probability_per_lap=0.2, possible=[WeatherName.cloudy, WeatherName.rain])
    cfg = build_transition_config(WeatherKind.DRY, change)
    assert cfg.transition_prob_per_lap == 0.2
    for current, row in cfg.transition_matrix.items():
        assert sum(row.values()) == pytest.approx(1.0)
        if current in (WeatherKind.DRY, WeatherKind.CLOUDY, WeatherKind.WET):
            assert row[current] == 0.0                       # quando muda, muda de verdade


def test_aviso_quando_chuva_fraca_ou_forte_entra_na_mudanca():
    change = WeatherChange(probability_per_lap=0.1, possible=[WeatherName.heavy_rain])
    assert any("weather_change" in w for w in build_race_setup(req(weather_change=change), None).warnings)
    ok = WeatherChange(probability_per_lap=0.1, possible=[WeatherName.rain])
    assert not any("weather_change" in w for w in build_race_setup(req(weather_change=ok), None).warnings)


# -- validação do pedido -----------------------------------------------------------

def test_stints_precisam_somar_as_voltas():
    with pytest.raises(ValidationError, match="soma das voltas"):
        req(laps=10, stints=[{"compound": "soft", "laps": 4}, {"compound": "hard", "laps": 4}])


def test_pneu_inicial_deve_bater_com_o_primeiro_stint():
    with pytest.raises(ValidationError, match="initial_tyre"):
        req(laps=6, initial_tyre="hard", stints=[{"compound": "soft", "laps": 3}, {"compound": "hard", "laps": 3}])


def test_pneu_inicial_vem_do_primeiro_stint_e_stints_geram_aviso():
    setup = build_race_setup(
        req(laps=6, stints=[{"compound": "soft", "laps": 3}, {"compound": "hard", "laps": 3}]), None)
    assert setup.drivers[0].starting_tyre_compound == TyreCompound.SOFT
    assert any("stints" in w for w in setup.warnings)


@pytest.mark.parametrize("bad", [
    dict(laps=0), dict(laps=201), dict(grid=[]), dict(grid=["a", "a"]),
    dict(grid=[f"d{i}" for i in range(25)]), dict(weather="snow"),
    dict(weather_change={"probability_per_lap": 1.5, "possible": ["rain"]}),
    dict(weather_change={"probability_per_lap": 0.1, "possible": []}),
    dict(weather_change={"probability_per_lap": 0.1, "possible": ["rain", "rain"]}),
])
def test_pedidos_invalidos_sao_rejeitados(bad):
    with pytest.raises(ValidationError):
        req(**bad)


# -- grid ------------------------------------------------------------------------

def test_grid_respeita_a_ordem_e_usa_ids_do_catalogo():
    setup = build_race_setup(req(grid=["lando-norris", "max-verstappen"]), make_catalog())
    assert [d.driver_id for d in setup.drivers] == ["lando-norris", "max-verstappen"]
    assert [(g.position, g.name) for g in setup.grid] == [(1, "Lando Norris"), (2, "Max Verstappen")]
    assert all(d.starting_tyre_compound == TyreCompound.MEDIUM for d in setup.drivers)


def test_pneu_inicial_vale_para_o_grid_todo():
    setup = build_race_setup(req(grid=["max-verstappen", "lando-norris"], initial_tyre="soft"), make_catalog())
    assert {d.starting_tyre_compound for d in setup.drivers} == {TyreCompound.SOFT}


def test_piloto_desconhecido_e_erro_claro():
    with pytest.raises(SetupError, match="desconhecidos.*ghost-driver"):
        build_race_setup(req(grid=["max-verstappen", "ghost-driver"]), make_catalog())


def test_sem_grid_usa_os_pilotos_padrao():
    assert [d.driver_id for d in build_race_setup(req(), None).drivers] == ["drv_01", "drv_02"]


# -- circuito ----------------------------------------------------------------------

def test_sem_circuito_usa_interlagos_local_sem_precisar_de_catalogo():
    loader = FakeLoader()
    setup = build_race_setup(req(), None, track_loader=loader)
    assert setup.circuit_id == "interlagos" and loader.calls == []


def test_circuito_carrega_pela_rodada_do_catalogo():
    loader = FakeLoader()
    setup = build_race_setup(req(circuit={"id": "interlagos"}), make_catalog(), track_loader=loader)
    assert loader.calls == [("21", 2025)]                 # rodada + ano da corrida de referência
    assert (setup.circuit_id, setup.layout_id) == ("interlagos", "interlagos-2")


def test_traçado_nao_simulavel_e_rejeitado_com_explicacao():
    with pytest.raises(SetupError, match="não é simulável"):
        build_race_setup(req(circuit={"id": "interlagos", "layout_id": "interlagos-1"}), make_catalog())
    with pytest.raises(SetupError, match="2018"):
        build_race_setup(req(circuit={"id": "oldtrack"}), make_catalog())


def test_circuito_ou_traçado_inexistente():
    with pytest.raises(SetupError, match="não existe no catálogo"):
        build_race_setup(req(circuit={"id": "narnia"}), make_catalog())
    with pytest.raises(SetupError, match="válidos: interlagos-1, interlagos-2"):
        build_race_setup(req(circuit={"id": "interlagos", "layout_id": "interlagos-9"}), make_catalog())


def test_circuito_e_grid_exigem_catalogo():
    with pytest.raises(CatalogRequired):
        build_race_setup(req(circuit={"id": "interlagos"}), None)
    with pytest.raises(CatalogRequired):
        build_race_setup(req(grid=["max-verstappen"]), None)
