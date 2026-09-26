"""Unit tests for circuit layout evolution extraction, domain service, and API controller."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi import HTTPException

from scripts.fetch_track_layouts import (
    format_year_ranges,
    extract_layout_number,
    find_database_path,
    TrackLayoutExtractor,
)
from service.circuit_evolution import CircuitEvolutionService
from controller.circuit_controller import (
    get_circuit_service,
    list_circuits,
    get_circuit,
    get_circuit_layouts,
    get_circuit_layout,
    get_layout_svg,
)


# ==============================================================================
# Helper Function Tests
# ==============================================================================

def test_format_year_ranges_empty():
    assert format_year_ranges([]) == []


def test_format_year_ranges_single_year():
    assert format_year_ranges([1950]) == ["1950"]


def test_format_year_ranges_consecutive():
    assert format_year_ranges([1990, 1991, 1992, 1993]) == ["1990-1993"]


def test_format_year_ranges_discontinuous():
    years = [1973, 1974, 1975, 1976, 1977, 1979, 1980]
    assert format_year_ranges(years) == ["1973-1977", "1979-1980"]


def test_format_year_ranges_multiple_gaps():
    years = [2004, 2005, 2006, 2010, 2012, 2013, 2020]
    assert format_year_ranges(years) == ["2004-2006", "2010", "2012-2013", "2020"]


def test_extract_layout_number():
    assert extract_layout_number("interlagos-1") == 1
    assert extract_layout_number("silverstone-8") == 8
    assert extract_layout_number("spa-francorchamps-4") == 4
    assert extract_layout_number("nurburgring-12") == 12
    assert extract_layout_number("no-number") == 1


# ==============================================================================
# Database Extraction Tests
# ==============================================================================

def test_find_database_path():
    db_path = find_database_path()
    assert db_path.exists()
    assert db_path.stat().st_size > 0


def test_extractor_interlagos_evolution():
    db_path = find_database_path()
    extractor = TrackLayoutExtractor(
        db_path=db_path,
        styles=("white-outline", "black-outline"),
    )

    data = extractor.extract_evolution(circuit_id_filter="interlagos")
    assert data["total_circuits"] == 1
    circuit = data["circuits"][0]

    assert circuit["id"] == "interlagos"
    assert circuit["name"] == "José Carlos Pace"
    assert circuit["country"]["id"] == "brazil"
    assert circuit["layouts_count"] == 2

    l1, l2 = circuit["layouts"]

    # Historical layout (1973 - 1980)
    assert l1["id"] == "interlagos-1"
    assert l1["circuit_id"] == "interlagos"
    assert l1["effective"] is False
    assert l1["length"] == 7.873
    assert l1["turns"] == 26
    assert l1["first_year"] == 1973
    assert l1["last_year"] == 1980
    assert l1["year_ranges"] == ["1973-1977", "1979-1980"]
    assert "white-outline" in l1["svg"]
    assert l1["svg"]["white-outline"].startswith("https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/white-outline/interlagos-1.svg")

    # Modern layout (1990 - present)
    assert l2["id"] == "interlagos-2"
    assert l2["circuit_id"] == "interlagos"
    assert l2["effective"] is True
    assert l2["length"] == 4.309
    assert l2["turns"] == 15
    assert l2["first_year"] == 1990
    assert l2["last_year"] >= 2024
    assert l2["svg"]["black-outline"].startswith("https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/black-outline/interlagos-2.svg")


def test_extractor_silverstone_evolution():
    db_path = find_database_path()
    extractor = TrackLayoutExtractor(
        db_path=db_path,
        styles=("white-outline",),
    )

    data = extractor.extract_evolution(circuit_id_filter="silverstone")
    circuit = data["circuits"][0]
    assert circuit["id"] == "silverstone"
    assert circuit["layouts_count"] == 8
    layouts = circuit["layouts"]

    # Verify chronological ordering
    first_years = [l["first_year"] for l in layouts]
    assert first_years == sorted(first_years)
    assert layouts[0]["id"] == "silverstone-1"
    assert layouts[-1]["id"] == "silverstone-8"
    assert layouts[-1]["effective"] is True


def test_extractor_bahrain_sakhir_outer_track():
    db_path = find_database_path()
    extractor = TrackLayoutExtractor(
        db_path=db_path,
        styles=("white-outline",),
    )

    data = extractor.extract_evolution(circuit_id_filter="bahrain")
    circuit = data["circuits"][0]
    layout_map = {l["id"]: l for l in circuit["layouts"]}

    # Bahrain Outer Circuit used in 2020 Sakhir GP
    assert "bahrain-3" in layout_map
    b3 = layout_map["bahrain-3"]
    assert b3["first_year"] == 2020
    assert b3["last_year"] == 2020
    assert b3["turns"] == 11
    assert b3["length"] == 3.543


# ==============================================================================
# Domain Service Tests
# ==============================================================================

def test_circuit_evolution_service():
    service = CircuitEvolutionService()
    circuits = service.list_circuits()
    assert len(circuits) >= 70

    interlagos_summary = next(c for c in circuits if c["id"] == "interlagos")
    assert interlagos_summary["name"] == "José Carlos Pace"
    assert interlagos_summary["layouts_count"] == 2
    assert interlagos_summary["current_layout_id"] == "interlagos-2"

    circuit = service.get_circuit("interlagos")
    assert circuit is not None
    assert circuit["id"] == "interlagos"

    layouts = service.get_layouts("interlagos")
    assert layouts is not None
    assert len(layouts) == 2

    layout2 = service.get_layout("interlagos", "interlagos-2")
    assert layout2 is not None
    assert layout2["turns"] == 15

    # SVG URL retrieval
    svg_url = service.get_layout_svg_url("interlagos", "interlagos-2", style="white-outline")
    assert svg_url is not None
    assert svg_url.startswith("https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/white-outline/interlagos-2.svg")


def test_circuit_service_db_injection():
    from database.circuit_db import InMemoryCircuitDatabase, JSONCircuitDatabase
    from service.circuit_service import CircuitService

    mock_circuit = {
        "id": "mock-gp",
        "name": "Mock Circuit",
        "full_name": "Autódromo Mock",
        "country": {"id": "brazil", "name": "Brazil"},
        "layouts": [
            {
                "id": "mock-layout-1",
                "circuit_id": "mock-gp",
                "effective": True,
                "first_year": 2020,
                "last_year": 2025,
                "turns": 12,
                "svg": {"white-outline": "https://example.com/mock.svg"},
            }
        ],
    }

    in_memory_db = InMemoryCircuitDatabase([mock_circuit])
    service = CircuitService(db=in_memory_db)

    circuits = service.list_circuits()
    assert len(circuits) == 1
    assert circuits[0]["id"] == "mock-gp"
    assert circuits[0]["current_layout_id"] == "mock-layout-1"
    assert circuits[0]["first_year"] == 2020
    assert circuits[0]["last_year"] == 2025

    circuit = service.get_circuit("mock-gp")
    assert circuit is not None
    assert circuit["name"] == "Mock Circuit"

    layout = service.get_layout("mock-gp", "mock-layout-1")
    assert layout is not None
    assert layout["turns"] == 12

    svg_url = service.get_layout_svg_url("mock-gp", "mock-layout-1")
    assert svg_url == "https://example.com/mock.svg"


def test_get_circuit_service_singleton():
    s1 = get_circuit_service()
    s2 = get_circuit_service()
    assert s1 is s2
    assert s1 is not None


def test_controller_direct_parameter_injection():
    from database.circuit_db import InMemoryCircuitDatabase
    from service.circuit_service import CircuitService

    custom_db = InMemoryCircuitDatabase([
        {
            "id": "direct-param-track",
            "name": "Direct Track",
            "full_name": "Direct Track GP",
            "layouts": [],
        }
    ])
    custom_service = CircuitService(db=custom_db)

    # Calling endpoint directly by passing the service parameter
    circuits = list_circuits(service=custom_service)
    assert len(circuits) == 1
    assert circuits[0]["id"] == "direct-param-track"


# ==============================================================================
# API Controller Tests
# ==============================================================================

def test_api_list_circuits():
    service = get_circuit_service()
    data = list_circuits(service=service)
    assert isinstance(data, list)
    assert len(data) >= 70
    assert any(c["id"] == "interlagos" for c in data)


def test_api_get_circuit():
    service = get_circuit_service()
    data = get_circuit("interlagos", service=service)
    assert data["id"] == "interlagos"
    assert "layouts" in data
    assert len(data["layouts"]) == 2


def test_api_get_circuit_not_found():
    service = get_circuit_service()
    with pytest.raises(HTTPException) as exc_info:
        get_circuit("circuito-fantasma", service=service)
    assert exc_info.value.status_code == 404


def test_api_get_layouts():
    service = get_circuit_service()
    data = get_circuit_layouts("interlagos", service=service)
    assert len(data) == 2
    assert data[0]["id"] == "interlagos-1"
    assert data[1]["id"] == "interlagos-2"


def test_api_get_layout_detail():
    service = get_circuit_service()
    data = get_circuit_layout("interlagos", "interlagos-2", service=service)
    assert data["id"] == "interlagos-2"
    assert data["turns"] == 15


def test_api_get_layout_svg():
    service = get_circuit_service()
    response = get_layout_svg(
        "interlagos",
        "interlagos-2",
        style="white-outline",
        service=service,
    )
    assert response.status_code == 307
    assert response.headers["location"].startswith(
        "https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits/white-outline/interlagos-2.svg"
    )


def test_openapi_dto_schemas():
    from main import app

    schema = app.openapi()
    schemas = schema["components"]["schemas"]
    assert "CircuitSummaryDTO" in schemas
    assert "CircuitDTO" in schemas
    assert "CircuitLayoutDTO" in schemas
    assert "CountryDTO" in schemas
    assert "LocationDTO" in schemas

