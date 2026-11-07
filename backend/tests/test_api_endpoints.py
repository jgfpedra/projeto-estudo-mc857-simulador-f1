"""Testes HTTP/WebSocket da api com TestClient (sem rodar simulação nem baixar dados)."""

import asyncio
import concurrent.futures
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api import main
from api.catalog import CatalogUnavailable
from api.race_manager import RaceManager, race_manager
from api_fixtures import FakeLoader, make_catalog


@pytest.fixture()
def loader():
    return FakeLoader()


@pytest.fixture()
def client(monkeypatch, loader):
    # O POST cria a engine mas não a executa (sem thread de simulação / PyBullet).
    monkeypatch.setattr(RaceManager, "_run_engine", staticmethod(lambda engine: None))
    main.app.dependency_overrides[main.required_catalog] = make_catalog
    main.app.dependency_overrides[main.optional_catalog] = make_catalog
    main.app.dependency_overrides[main.get_track_loader] = lambda: loader
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()


# -- catálogo ---------------------------------------------------------------------

def test_circuits_traz_o_que_o_front_pediu(client):
    r = client.get("/circuits")
    assert r.status_code == 200
    interlagos = next(c for c in r.json() if c["id"] == "interlagos")
    assert interlagos["name"] == "José Carlos Pace"
    assert interlagos["city"] == "São Paulo"
    assert interlagos["country"] == {"name": "Brazil", "code": "BR"}      # código p/ emoji de bandeira
    assert interlagos["svg"]["black-outline"].endswith(".svg")
    assert [l["id"] for l in interlagos["layouts"]] == ["interlagos-1", "interlagos-2"]  # variações
    assert interlagos["layouts"][1]["is_current"] is True
    assert "fastf1" not in interlagos["layouts"][1]                       # detalhe interno não vaza


def test_seasons_lista_do_mais_recente_para_o_mais_antigo(client):
    assert client.get("/seasons").json() == [2025, 2024]


def test_pilotos_da_temporada(client):
    r = client.get("/seasons/2024/drivers")
    assert r.status_code == 200
    ver = next(d for d in r.json() if d["id"] == "max-verstappen")
    assert ver == {
        "id": "max-verstappen", "name": "Max Verstappen", "abbreviation": "VER", "number": 1,
        "team": "Red Bull", "team_id": "red-bull", "country": {"name": "Netherlands", "code": "NL"},
    }
    assert client.get("/seasons/2025/drivers").json()[0]["number"] == 3   # número muda por temporada


def test_temporada_inexistente_e_404(client):
    assert client.get("/seasons/1800/drivers").status_code == 404


def test_catalogo_ausente_e_503_com_instrucao(monkeypatch):
    def boom():
        raise CatalogUnavailable("catálogo não encontrado. Gere com: python scripts/build_catalog.py")
    monkeypatch.setattr(main, "get_catalog", boom)
    with TestClient(main.app) as c:
        r = c.get("/circuits")
    assert r.status_code == 503 and "build_catalog.py" in r.json()["detail"]


# -- POST /races -------------------------------------------------------------------

def test_post_races_contrato_completo(client, loader):
    body = {
        "circuit": {"id": "interlagos"},
        "laps": 6,
        "grid": ["lando-norris", "max-verstappen"],
        "weather": "light_rain",
        "weather_change": {"probability_per_lap": 0.1, "possible": ["cloudy", "rain"]},
        "stints": [{"compound": "soft", "laps": 2}, {"compound": "hard", "laps": 4}],
    }
    r = client.post("/races", json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["race_id"].startswith("race_") and j["ws_path"] == f"/ws/races/{j['race_id']}"
    assert (j["circuit_id"], j["layout_id"], j["num_laps"]) == ("interlagos", "interlagos-2", 6)
    assert [(g["position"], g["driver_id"]) for g in j["grid"]] == [(1, "lando-norris"), (2, "max-verstappen")]
    assert j["initial_weather"] == {"requested": "light_rain", "engine_kind": "DAMP", "rainfall_mm_h": 0.5}
    assert j["initial_tyre"] == "soft"
    assert any("stints" in w for w in j["warnings"])
    assert loader.calls == [("21", 2025)]
    assert race_manager.exists(j["race_id"])


def test_post_minimo_continua_funcionando_como_antes(client):
    r = client.post("/races", json={"laps": 3})
    assert r.status_code == 200
    j = r.json()
    assert j["track_name"] == "Interlagos" and j["num_laps"] == 3
    assert [g["driver_id"] for g in j["grid"]] == ["drv_01", "drv_02"] and j["warnings"] == []


def test_post_sem_catalogo_ainda_aceita_pedido_minimo(monkeypatch, loader):
    monkeypatch.setattr(RaceManager, "_run_engine", staticmethod(lambda engine: None))
    main.app.dependency_overrides[main.optional_catalog] = lambda: None
    main.app.dependency_overrides[main.get_track_loader] = lambda: loader
    try:
        with TestClient(main.app) as c:
            assert c.post("/races", json={"laps": 2}).status_code == 200
            r = c.post("/races", json={"grid": ["max-verstappen"]})
            assert r.status_code == 503
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize("body,fragment", [
    ({"grid": ["max-verstappen", "ghost"]}, "desconhecidos"),
    ({"circuit": {"id": "narnia"}}, "não existe no catálogo"),
    ({"circuit": {"id": "oldtrack"}}, "não é simulável"),
])
def test_post_erros_de_dominio_sao_422_com_mensagem(client, body, fragment):
    r = client.post("/races", json=body)
    assert r.status_code == 422 and fragment in r.json()["detail"]


def test_post_validacao_do_schema_e_422(client):
    assert client.post("/races", json={"laps": 0}).status_code == 422
    assert client.post("/races", json={"weather": "snow"}).status_code == 422
    r = client.post("/races", json={"laps": 10, "stints": [{"compound": "soft", "laps": 3}]})
    assert r.status_code == 422 and "soma das voltas" in r.text


def test_falha_do_fastf1_vira_502(client):
    from config import CircuitLoadError

    def broken(*a, **k):
        raise CircuitLoadError("sem rede")
    main.app.dependency_overrides[main.get_track_loader] = lambda: broken
    r = client.post("/races", json={"circuit": {"id": "interlagos"}})
    assert r.status_code == 502 and "FastF1" in r.json()["detail"]


# -- WebSocket ----------------------------------------------------------------------

def _recv(ws, timeout=3.0):
    """receive_json com timeout: sem isso, um bug de 'mensagem perdida' trava o pytest."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(ws.receive_json)
    try:
        return fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        raise AssertionError(f"nenhuma mensagem em {timeout}s no websocket") from None
    finally:
        pool.shutdown(wait=False)   # não esperar a thread presa no receive


def _wait_subscribed(race_id, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        with race_manager._lock:
            if race_manager._races[race_id].subscribers:
                return
        time.sleep(0.01)
    raise AssertionError("websocket não se inscreveu a tempo")


def _publish(payload, race_id):
    asyncio.run_coroutine_threadsafe(race_manager.broadcast(race_id, payload), race_manager.loop).result(3)


def test_websocket_transmite_e_fecha_no_race_end(client):
    race_id = client.post("/races", json={"laps": 1}).json()["race_id"]
    with client.websocket_connect(f"/ws/races/{race_id}") as ws:
        _wait_subscribed(race_id)
        _publish({"type": "tick", "lap": 0}, race_id)
        assert _recv(ws) == {"type": "tick", "lap": 0}
        _publish({"type": "race_end"}, race_id)
        assert _recv(ws) == {"type": "race_end"}
        with pytest.raises(WebSocketDisconnect) as exc:
            _recv(ws)
        assert exc.value.code == 1000                      # o servidor encerra o stream


def test_websocket_de_corrida_inexistente_fecha_com_4404(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/races/race_nao_existe"):
            pass
    assert exc.value.code == 4404


def test_assinante_tardio_recebe_o_race_start(client):
    """O motor começa antes do WS conectar: o race_start não pode se perder."""
    race_id = client.post("/races", json={"laps": 1}).json()["race_id"]
    _publish({"type": "race_start", "race_id": race_id}, race_id)   # publicado ANTES de alguém conectar
    _publish({"type": "tick", "lap": 0}, race_id)                   # tick comum não é guardado
    with client.websocket_connect(f"/ws/races/{race_id}") as ws:
        assert _recv(ws) == {"type": "race_start", "race_id": race_id}
        _wait_subscribed(race_id)
        _publish({"type": "tick", "lap": 1}, race_id)
        assert _recv(ws) == {"type": "tick", "lap": 1}      # o tick antigo não volta


def test_race_start_nao_duplica_para_quem_ja_estava_conectado(client):
    race_id = client.post("/races", json={"laps": 1}).json()["race_id"]
    with client.websocket_connect(f"/ws/races/{race_id}") as ws:
        _wait_subscribed(race_id)
        _publish({"type": "race_start", "race_id": race_id}, race_id)
        _publish({"type": "tick", "lap": 0}, race_id)
        assert _recv(ws)["type"] == "race_start"
        assert _recv(ws)["type"] == "tick"                   # sem race_start repetido
