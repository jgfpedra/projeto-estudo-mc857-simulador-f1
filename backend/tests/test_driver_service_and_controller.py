"""Unit tests for Driver database, FastF1 integration, service, controller, and OpenAPI schemas."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from database.driver_db import (
    FastF1DriverDatabase,
    InMemoryDriverDatabase,
)
from dto.driver_dto import DriverDTO
from service.driver_service import DriverService
from controller.driver_controller import (
    get_driver_service,
    list_drivers,
    get_driver,
)


def test_fastf1_driver_database_2024():
    db = FastF1DriverDatabase(default_year=2024)
    drivers = db.get_all_drivers(year=2024)
    assert len(drivers) >= 20

    # Every driver should have team name and team color
    for d in drivers:
        assert d.get("team_name") is not None
        assert d.get("team_color") is not None
        assert d["team_color"].startswith("#")

    # Specific check for Norris and Verstappen
    norris = db.get_driver_by_id("NOR", year=2024)
    assert norris is not None
    assert norris["team_name"] == "McLaren"
    assert norris["team_color"].upper() == "#FF8000"

    verstappen = db.get_driver_by_id("max-verstappen", year=2024)
    assert verstappen is not None
    assert verstappen["team_name"] == "Red Bull Racing"


def test_driver_service_in_memory_injection():
    mock_drivers = [
        {
            "id": "charles-leclerc",
            "name": "Charles Leclerc",
            "first_name": "Charles",
            "last_name": "Leclerc",
            "abbreviation": "LEC",
            "team_name": "Ferrari",
            "team_id": "ferrari",
            "team_color": "#E80020",
            "country_code": "MON",
            "total_race_wins": 8,
        },
        {
            "id": "lando-norris",
            "name": "Lando Norris",
            "first_name": "Lando",
            "last_name": "Norris",
            "abbreviation": "NOR",
            "team_name": "McLaren",
            "team_id": "mclaren",
            "team_color": "#FF8000",
            "country_code": "GBR",
            "total_race_wins": 4,
        },
    ]

    mem_db = InMemoryDriverDatabase(mock_drivers)
    service = DriverService(db=mem_db)

    drivers = service.list_drivers(year=2024)
    assert len(drivers) == 2
    assert drivers[0]["team_color"] in ["#E80020", "#FF8000"]

    # Query search
    ferrari_drivers = service.list_drivers(query="Ferrari")
    assert len(ferrari_drivers) == 1
    assert ferrari_drivers[0]["id"] == "charles-leclerc"

    # Get by abbreviation
    norris = service.get_driver("NOR")
    assert norris is not None
    assert norris["team_name"] == "McLaren"
    assert norris["team_color"] == "#FF8000"


def test_driver_controller_endpoints():
    mock_drivers = [
        {
            "id": "lewis-hamilton",
            "name": "Lewis Hamilton",
            "first_name": "Lewis",
            "last_name": "Hamilton",
            "abbreviation": "HAM",
            "team_name": "Mercedes",
            "team_id": "mercedes",
            "team_color": "#27F4D2",
            "country_code": "GBR",
        },
        {
            "id": "carlos-sainz",
            "name": "Carlos Sainz",
            "first_name": "Carlos",
            "last_name": "Sainz",
            "abbreviation": "SAI",
            "team_name": "Ferrari",
            "team_id": "ferrari",
            "team_color": "#E80020",
            "country_code": "ESP",
        },
    ]

    service = DriverService(db=InMemoryDriverDatabase(mock_drivers))

    # List drivers
    drivers = list_drivers(year=2024, service=service)
    assert len(drivers) == 2
    assert isinstance(drivers[0], DriverDTO)
    assert drivers[0].team_color is not None
    assert drivers[0]["team_name"] in ["Mercedes", "Ferrari"]

    # Filter query
    ferrari_only = list_drivers(query="Ferrari", service=service)
    assert len(ferrari_only) == 1
    assert ferrari_only[0]["id"] == "carlos-sainz"

    # Verify nested team and country objects
    assert drivers[0].team is not None
    assert drivers[0].team.name in ["Mercedes", "Ferrari"]
    assert drivers[0].country is not None


    # Get driver by code
    ham = get_driver("HAM", year=2024, service=service)
    assert isinstance(ham, DriverDTO)
    assert ham.abbreviation == "HAM"
    assert ham.team.name == "Mercedes"
    assert ham.team.color == "#27F4D2"
    assert ham.country.id == "gbr"

    # Not found
    with pytest.raises(HTTPException) as exc_info:
        get_driver("piloto-inexistente", service=service)
    assert exc_info.value.status_code == 404


def test_driver_openapi_schema_contains_team_and_country():
    from main import app

    schema = app.openapi()
    schemas = schema["components"]["schemas"]
    assert "DriverDTO" in schemas
    assert "TeamDTO" in schemas
    assert "CountryDTO" in schemas

    driver_schema = schemas["DriverDTO"]
    assert "properties" in driver_schema
    assert "team" in driver_schema["properties"]
    assert "country" in driver_schema["properties"]


def test_seasons_service_and_endpoints():
    from controller.season_controller import list_seasons, get_seasons_info
    from controller.driver_controller import list_driver_seasons

    service = DriverService(db=InMemoryDriverDatabase([]))

    # Test list_seasons endpoint function
    seasons = list_seasons(all_historical=False, service=service)
    assert isinstance(seasons, list)
    assert 2024 in seasons
    assert 2018 in seasons
    assert seasons[0] > seasons[-1]  # Descending order

    # Test list_driver_seasons alias
    driver_seasons = list_driver_seasons(all_historical=False, service=service)
    assert driver_seasons == seasons

    # Test get_seasons_info endpoint function
    info = get_seasons_info(all_historical=False, service=service)
    assert info.default_season == 2024
    assert info.total == len(seasons)
    assert info.seasons == seasons

    # Test FastF1DriverDatabase get_available_seasons
    fastf1_db = FastF1DriverDatabase()
    fastf1_seasons = fastf1_db.get_available_seasons(all_historical=False)
    assert 2024 in fastf1_seasons
    assert 2018 in fastf1_seasons
    assert fastf1_seasons[0] >= 2024


def test_seasons_openapi_schema():
    from main import app

    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/seasons" in paths
    assert "/api/v1/seasons/info" in paths
    assert "/api/v1/drivers/seasons" in paths

    schemas = schema["components"]["schemas"]
    assert "SeasonsResponseDTO" in schemas
