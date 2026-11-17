"""Testes do scripts/build_catalog.py com um F1DB sintético mínimo (sem rede)."""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_catalog  # noqa: E402


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "f1db.db"
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE country (id TEXT, name TEXT, alpha2_code TEXT, alpha3_code TEXT, continent_id TEXT);
    CREATE TABLE circuit (id TEXT, name TEXT, full_name TEXT, previous_names TEXT, type TEXT, direction TEXT,
        place_name TEXT, country_id TEXT, latitude REAL, longitude REAL, length REAL, turns INT, total_races_held INT);
    CREATE TABLE circuit_layout (id TEXT, circuit_id TEXT, effective INT, length REAL, turns INT);
    CREATE TABLE race (id INT, year INT, round INT, circuit_id TEXT, circuit_layout_id TEXT);
    CREATE TABLE race_data (race_id INT, type TEXT, driver_id TEXT, driver_number TEXT, constructor_id TEXT);
    CREATE TABLE driver (id TEXT, name TEXT, abbreviation TEXT, permanent_number TEXT, nationality_country_id TEXT);
    CREATE TABLE constructor (id TEXT, name TEXT);
    CREATE TABLE season_entrant_driver (year INT, driver_id TEXT, constructor_id TEXT, test_driver INT);

    INSERT INTO country VALUES ('brazil','Brazil','BR','BRA','south-america'),
                               ('united-kingdom','United Kingdom','GB','GBR','europe');
    INSERT INTO circuit VALUES
      ('interlagos','José Carlos Pace','Autódromo José Carlos Pace','','RACE','ANTI_CLOCKWISE','São Paulo','brazil',-23.7,-46.7,4.309,15,50),
      ('oldtrack','Old Track','Old Track Circuit','','RACE','CLOCKWISE','Oldtown','united-kingdom',52.0,-1.0,5.0,12,5);
    INSERT INTO circuit_layout VALUES ('interlagos-1','interlagos',0,7.873,26),
                                      ('interlagos-2','interlagos',1,4.309,15),
                                      ('oldtrack-1','oldtrack',1,5.0,12);
    -- 1979 (layout antigo) | 2024 e 2025 (com resultado) | 2026 (futura, sem resultado) | 1990 (oldtrack)
    INSERT INTO race VALUES (1,1979,1,'interlagos','interlagos-1'),
                            (2,2024,21,'interlagos','interlagos-2'),
                            (3,2025,21,'interlagos','interlagos-2'),
                            (4,2026,20,'interlagos','interlagos-2'),
                            (5,1990,3,'oldtrack','oldtrack-1'),
                            (6,2025,5,'interlagos','interlagos-2'),
                            (7,2025,6,'interlagos','interlagos-2');
    INSERT INTO constructor VALUES ('redbull','Red Bull'),('mercedes','Mercedes'),('team-a','Team A'),('team-b','Team B'),('oldteam','Old Team');
    INSERT INTO driver VALUES ('max-verstappen','Max Verstappen','VER','33','netherlands'),
                              ('lewis-hamilton','Lewis Hamilton','HAM','44','united-kingdom'),
                              ('test-guy','Test Guy','TST',NULL,'brazil'),
                              ('switcher','Switch Er','SWI',NULL,'brazil'),
                              ('old-driver','Old Driver','OLD',NULL,'united-kingdom');
    INSERT INTO country VALUES ('netherlands','Netherlands','NL','NLD','europe');
    INSERT INTO season_entrant_driver VALUES
      (2024,'max-verstappen','redbull',0),(2024,'lewis-hamilton','mercedes',0),(2024,'test-guy','mercedes',1),
      (2025,'switcher','team-a',0),(2025,'switcher','team-b',0),
      (1990,'old-driver','oldteam',0);
    -- resultados (o campeão corre com o #1 em 2024, não com o permanent_number 33)
    INSERT INTO race_data VALUES (2,'RACE_RESULT','max-verstappen','1','redbull'),
                                 (2,'RACE_RESULT','lewis-hamilton','44','mercedes'),
                                 (3,'RACE_RESULT','switcher','7','team-a'),
                                 (6,'RACE_RESULT','switcher','7','team-b'),
                                 (7,'RACE_RESULT','switcher','7','team-b'),
                                 (2,'QUALIFYING_RESULT','max-verstappen','1','redbull');
    """)
    c.commit()
    c.close()
    return path


def test_circuito_atual_e_referencia_fastf1(db_path):
    circuits = {c["id"]: c for c in build_catalog.build_circuits(db_path)}
    i = circuits["interlagos"]
    assert i["city"] == "São Paulo"
    assert i["country"] == {"name": "Brazil", "code": "BR"}
    assert i["current_layout_id"] == "interlagos-2"
    layouts = {l["id"]: l for l in i["layouts"]}
    assert layouts["interlagos-2"]["is_current"] is True
    assert layouts["interlagos-1"]["is_current"] is False
    # 2026 é futura (sem RACE_RESULT): a referência é a corrida mais recente COM resultado
    assert layouts["interlagos-2"]["fastf1"] == {"year": 2025, "round": 21}
    assert layouts["interlagos-2"]["simulable"] is True


def test_traçado_antigo_nao_e_simulavel(db_path):
    circuits = {c["id"]: c for c in build_catalog.build_circuits(db_path)}
    old = {l["id"]: l for l in circuits["interlagos"]["layouts"]}["interlagos-1"]
    assert old["simulable"] is False and old["fastf1"] is None
    assert circuits["oldtrack"]["simulable"] is False
    assert circuits["interlagos"]["simulable"] is True


def test_pilotos_sem_teste_e_com_numero_da_temporada(db_path):
    seasons = build_catalog.build_seasons(db_path)
    d2024 = {d["id"]: d for d in seasons["2024"]}
    assert "test-guy" not in d2024                      # piloto de teste fora
    assert d2024["max-verstappen"]["number"] == 1        # número da temporada, não o permanent_number (33)
    assert d2024["lewis-hamilton"]["number"] == 44
    assert d2024["max-verstappen"]["team"] == "Red Bull"
    assert d2024["max-verstappen"]["country"] == {"name": "Netherlands", "code": "NL"}


def test_piloto_com_duas_equipes_fica_na_equipe_com_mais_corridas(db_path):
    drivers = build_catalog.build_seasons(db_path)["2025"]
    assert [d["id"] for d in drivers] == ["switcher"]    # sem duplicata
    assert drivers[0]["team"] == "Team B"                # 2 corridas pela B vs 1 pela A


def test_sem_numero_conhecido_vira_none(db_path):
    assert build_catalog.build_seasons(db_path)["1990"][0]["number"] is None


def test_catalogo_completo_tem_metadados(db_path):
    cat = build_catalog.build_catalog(db_path)
    assert cat["version"] == build_catalog.CATALOG_VERSION
    assert cat["fastf1_min_year"] == 2018
    assert set(cat["seasons"]) == {"1990", "2024", "2025"}
