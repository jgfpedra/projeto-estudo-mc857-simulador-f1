"""Driver Service for Formula 1 driver information and statistics.

Provides query, search, team and color access for driver records in a season year.
Supports database dependency injection (defaults to OpenF1DriverDatabase with FastF1 fallback).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.driver_db import DriverDatabase
from database.openf1_driver_db import OpenF1DriverDatabase


class DriverService:
    """Service to query driver records, teams, and colors by season year."""

    def __init__(
        self,
        db: Optional[DriverDatabase] = None,
    ):
        """Initialize DriverService with an injected database or fallback to OpenF1DriverDatabase."""
        if db is not None:
            self.db: DriverDatabase = db
        else:
            self.db = OpenF1DriverDatabase()

    def list_drivers(
        self,
        year: Optional[int] = None,
        query: Optional[str] = None,
        nationality: Optional[str] = None,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
    ) -> List[Dict[str, Any]]:
        """List drivers for a given year with optional filtering and pagination."""
        return self.db.get_all_drivers(
            year=year,
            query=query,
            nationality=nationality,
            limit=limit,
            offset=offset,
        )

    def get_driver(
        self,
        driver_id: str,
        year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve driver profile for a given year by ID or 3-letter code."""
        return self.db.get_driver_by_id(driver_id=driver_id, year=year)

    def get_available_seasons(self, all_historical: bool = False) -> List[int]:
        """Retrieve the available season years from FastF1 in descending order."""
        return self.db.get_available_seasons(all_historical=all_historical)
