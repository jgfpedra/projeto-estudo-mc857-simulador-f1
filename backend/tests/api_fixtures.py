"""Catálogo pequeno e fake track loader compartilhados pelos testes da api."""

from api.catalog import Catalog
from config import INTERLAGOS_TRACK

FAKE_CATALOG = {
    "version": 1,
    "circuits": [
        {
            "id": "interlagos", "name": "José Carlos Pace", "full_name": "Autódromo José Carlos Pace",
            "city": "São Paulo", "country": {"name": "Brazil", "code": "BR"},
            "svg": {"black-outline": "https://x/interlagos-2.svg"},
            "current_layout_id": "interlagos-2", "simulable": True,
            "layouts": [
                {"id": "interlagos-1", "years": ["1973-1980"], "first_year": 1973, "last_year": 1980,
                 "length_km": 7.873, "turns": 26, "svg": {}, "is_current": False, "simulable": False, "fastf1": None},
                {"id": "interlagos-2", "years": ["1990-2026"], "first_year": 1990, "last_year": 2026,
                 "length_km": 4.309, "turns": 15, "svg": {"black-outline": "https://x/interlagos-2.svg"},
                 "is_current": True, "simulable": True, "fastf1": {"year": 2025, "round": 21}},
            ],
        },
        {
            "id": "oldtrack", "name": "Old Track", "full_name": None, "city": "Oldtown",
            "country": {"name": "United Kingdom", "code": "GB"}, "svg": None,
            "current_layout_id": "oldtrack-1", "simulable": False,
            "layouts": [
                {"id": "oldtrack-1", "years": ["1990"], "first_year": 1990, "last_year": 1990,
                 "length_km": 5.0, "turns": 12, "svg": {}, "is_current": True, "simulable": False, "fastf1": None},
            ],
        },
    ],
    "seasons": {
        "2024": [
            {"id": "max-verstappen", "name": "Max Verstappen", "abbreviation": "VER", "number": 1,
             "team": "Red Bull", "team_id": "red-bull", "country": {"name": "Netherlands", "code": "NL"}},
            {"id": "lando-norris", "name": "Lando Norris", "abbreviation": "NOR", "number": 4,
             "team": "McLaren", "team_id": "mclaren", "country": {"name": "United Kingdom", "code": "GB"}},
        ],
        "2025": [
            {"id": "max-verstappen", "name": "Max Verstappen", "abbreviation": "VER", "number": 3,
             "team": "Red Bull", "team_id": "red-bull", "country": {"name": "Netherlands", "code": "NL"}},
        ],
    },
}


def make_catalog() -> Catalog:
    return Catalog(FAKE_CATALOG)


class FakeLoader:
    """Substitui load_track (que baixaria dados do FastF1)."""

    def __init__(self):
        self.calls = []

    def __call__(self, track_name=None, year=None, session="R", cache_dir=None):
        self.calls.append((track_name, year))
        return INTERLAGOS_TRACK
