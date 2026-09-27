"""Driver Database abstraction and implementations.

Provides an interface (DriverDatabase) and implementations:
- FastF1DriverDatabase: loads drivers, current teams, and team colors for a given year using FastF1 and local cache.
- InMemoryDriverDatabase: in-memory implementation for testing and mocks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

class DriverDatabase(ABC):
    """Abstract base class representing Driver persistence."""

    @abstractmethod
    def get_all_drivers(
        self,
        year: Optional[int] = None,
        query: Optional[str] = None,
        nationality: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return list of drivers matching optional filters, pagination and year."""
        pass

    @abstractmethod
    def get_driver_by_id(
        self,
        driver_id: str,
        year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return single driver details by ID or code for a given year, or None if not found."""
        pass

    @abstractmethod
    def get_available_seasons(self, all_historical: bool = False) -> List[int]:
        """Return list of available season years (descending order)."""
        pass


class FastF1DriverDatabase(DriverDatabase):
    """Loads drivers, teams, and official team colors for a season year via FastF1."""

    def __init__(
        self,
        cache_dir: Optional[Path | str] = None,
        default_year: int = 2024,
    ):
        self.default_year = default_year
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).resolve().parent.parent / "cache"

        self._season_drivers_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._enable_cache()

    def _enable_cache(self) -> None:
        try:
            import fastf1
            if self.cache_dir:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                fastf1.Cache.enable_cache(str(self.cache_dir))
        except Exception:
            pass

    def load_season_drivers(self, year: int) -> List[Dict[str, Any]]:
        """Loads drivers from FastF1 session results for a given year with team and color."""
        if year in self._season_drivers_cache:
            return self._season_drivers_cache[year]

        import fastf1
        self._enable_cache()

        try:
            schedule = fastf1.get_event_schedule(year)
            events = schedule[schedule["EventFormat"] != "testing"]
        except Exception:
            return []

        if events.empty:
            return []

        drivers_map: Dict[str, Dict[str, Any]] = {}

        # Scan rounds in reverse (latest to earliest) to pick the most up-to-date team/color
        rounds = [int(ev["RoundNumber"]) for _, ev in events.iterrows()]
        rounds.reverse()

        for r_num in rounds:
            try:
                session = fastf1.get_session(year, r_num, "R")
                session.load(laps=False, telemetry=False, weather=False, messages=False)
                if session.results is None or session.results.empty:
                    continue

                for _, row in session.results.iterrows():
                    code = str(row.get("Abbreviation") or "").strip().upper()
                    if not code:
                        continue

                    if code not in drivers_map:
                        color = row.get("TeamColor")
                        if color and not str(color).startswith("#"):
                            color = f"#{color}"
                        elif not color:
                            color = None

                        perm_num = row.get("DriverNumber")
                        try:
                            perm_num = int(perm_num) if perm_num and str(perm_num).isdigit() else None
                        except Exception:
                            perm_num = None

                        driver_id = str(row.get("DriverId") or code.lower()).strip().lower().replace("_", "-")

                        country_code = row.get("CountryCode")
                        country_dict = {
                            "id": str(country_code).lower() if country_code else "unknown",
                            "name": str(country_code) if country_code else "Unknown",
                            "alpha3_code": str(country_code).upper() if country_code else None,
                        } if country_code else None

                        team_dict = {
                            "id": row.get("TeamId"),
                            "name": row.get("TeamName") or "Unknown",
                            "color": color,
                        }

                        drivers_map[code] = {
                            "id": driver_id,
                            "name": row.get("FullName") or row.get("BroadcastName") or code,
                            "first_name": row.get("FirstName"),
                            "last_name": row.get("LastName"),
                            "full_name": row.get("FullName"),
                            "abbreviation": code,
                            "permanent_number": perm_num,
                            "team": team_dict,
                            "country": country_dict,
                            "team_name": row.get("TeamName"),
                            "team_id": row.get("TeamId"),
                            "team_color": color,
                            "country_code": country_code,
                            "nationality_country_id": country_code,
                            "total_race_wins": 0,
                            "total_championship_wins": 0,
                            "total_podiums": 0,
                            "total_pole_positions": 0,
                            "total_points": 0.0,
                        }
            except Exception:
                continue

        # Sort drivers by team_name then name
        driver_list = sorted(
            drivers_map.values(),
            key=lambda d: (d.get("team_name") or "", d.get("name") or ""),
        )
        self._season_drivers_cache[year] = driver_list
        return driver_list

    def get_all_drivers(
        self,
        year: Optional[int] = None,
        query: Optional[str] = None,
        nationality: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        target_year = year if isinstance(year, int) else self.default_year
        drivers = list(self.load_season_drivers(target_year))

        if query and isinstance(query, str):
            q = query.strip().lower()
            drivers = [
                d for d in drivers
                if q in str(d.get("name", "")).lower()
                or q in str(d.get("first_name", "")).lower()
                or q in str(d.get("last_name", "")).lower()
                or q in str(d.get("full_name", "")).lower()
                or q in str(d.get("abbreviation", "")).lower()
                or q in str(d.get("id", "")).lower()
                or q in str(d.get("team_name", "")).lower()
            ]

        if nationality and isinstance(nationality, str):
            nat = nationality.strip().lower()
            drivers = [
                d for d in drivers
                if str(d.get("nationality_country_id", "")).lower() == nat
                or str(d.get("country_code", "")).lower() == nat
            ]

        offset_int = offset if isinstance(offset, int) else 0
        limit_int = limit if isinstance(limit, int) else None

        if offset_int:
            drivers = drivers[offset_int:]
        if limit_int is not None:
            drivers = drivers[:limit_int]

        return drivers

    def get_driver_by_id(
        self,
        driver_id: str,
        year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        target_year = year if isinstance(year, int) else self.default_year
        drivers = self.load_season_drivers(target_year)
        norm_id = driver_id.strip().lower().replace("_", "-")

        for d in drivers:
            if d.get("id") == norm_id or str(d.get("abbreviation", "")).lower() == norm_id:
                return d
        return None

    FASTF1_TELEMETRY_MIN_YEAR = 2018

    def get_available_seasons(self, all_historical: bool = False) -> List[int]:
        """Returns available seasons in FastF1 (descending order).

        If all_historical is False (default), returns years with full FastF1
        live timing/telemetry support (2018 to current season).
        If all_historical is True, returns all historical F1 seasons (1950 to present).
        """
        cache_key = "all" if all_historical else "modern"
        if not hasattr(self, "_available_seasons_cache"):
            self._available_seasons_cache: Dict[str, List[int]] = {}

        if cache_key in self._available_seasons_cache:
            return list(self._available_seasons_cache[cache_key])

        import datetime

        now_year = datetime.datetime.now().year

        if all_historical:
            try:
                import fastf1
                from fastf1.ergast import Ergast

                ergast = Ergast()
                df = ergast.get_seasons(limit=1000)
                seasons = [int(s) for s in df["season"].tolist() if str(s).isdigit()]
                seasons.sort(reverse=True)
                if seasons:
                    self._available_seasons_cache[cache_key] = seasons
                    return list(seasons)
            except Exception:
                pass
            fallback = list(range(now_year, 1949, -1))
            self._available_seasons_cache[cache_key] = fallback
            return fallback

        # Modern FastF1 seasons (2018 to current / next announced)
        max_year = now_year
        try:
            import fastf1

            self._enable_cache()
            try:
                next_sch = fastf1.get_event_schedule(now_year + 1)
                if next_sch is not None and not next_sch.empty:
                    max_year = now_year + 1
            except Exception:
                pass
        except Exception:
            pass

        seasons = list(range(max_year, self.FASTF1_TELEMETRY_MIN_YEAR - 1, -1))
        self._available_seasons_cache[cache_key] = seasons
        return list(seasons)


class InMemoryDriverDatabase(DriverDatabase):
    """In-memory driver database for tests and mocks."""

    def __init__(self, drivers: Optional[List[Dict[str, Any]]] = None):
        self._drivers: List[Dict[str, Any]] = list(drivers) if drivers else []
        self._drivers_by_id: Dict[str, Dict[str, Any]] = {
            d["id"].lower(): d for d in self._drivers if "id" in d
        }

    def add_driver(self, driver: Dict[str, Any]) -> None:
        self._drivers.append(driver)
        if "id" in driver:
            self._drivers_by_id[driver["id"].lower()] = driver

    def get_all_drivers(
        self,
        year: Optional[int] = None,
        query: Optional[str] = None,
        nationality: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = list(self._drivers)

        if query and isinstance(query, str):
            q = query.strip().lower()
            results = [
                d for d in results
                if q in str(d.get("name", "")).lower()
                or q in str(d.get("first_name", "")).lower()
                or q in str(d.get("last_name", "")).lower()
                or q in str(d.get("full_name", "")).lower()
                or q in str(d.get("abbreviation", "")).lower()
                or q in str(d.get("id", "")).lower()
                or q in str(d.get("team_name", "")).lower()
            ]

        if nationality and isinstance(nationality, str):
            nat = nationality.strip().lower()
            results = [
                d for d in results
                if str(d.get("nationality_country_id", "")).lower() == nat
                or str(d.get("country_code", "")).lower() == nat
            ]

        offset_int = offset if isinstance(offset, int) else 0
        limit_int = limit if isinstance(limit, int) else None

        if offset_int:
            results = results[offset_int:]
        if limit_int is not None:
            results = results[:limit_int]

        return results

    def get_driver_by_id(
        self,
        driver_id: str,
        year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        norm_id = driver_id.strip().lower().replace("_", "-")
        if norm_id in self._drivers_by_id:
            return self._drivers_by_id[norm_id]
        for d in self._drivers:
            if str(d.get("abbreviation", "")).lower() == norm_id:
                return d
            if str(d.get("id", "")).lower() == norm_id:
                return d
        return None

    def get_available_seasons(self, all_historical: bool = False) -> List[int]:
        """Returns mock seasons list."""
        if all_historical:
            return list(range(2026, 1949, -1))
        return [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]