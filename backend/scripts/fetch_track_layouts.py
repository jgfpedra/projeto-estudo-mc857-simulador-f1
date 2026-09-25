"""Script to extract circuit layout evolution from F1DB with GitHub SVG links.

This script queries the F1DB database (f1db.db) to extract the chronological
evolution of track layouts for all Formula 1 circuits, tracks their usage across
F1 seasons and races, and generates direct GitHub links to the official F1DB
vector SVG assets for each layout, exporting a lightweight JSON dataset ready
for consumption by frontend and backend applications.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import re
import sqlite3
import sys
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple

# Base raw URL for F1DB SVG assets in GitHub
F1DB_RAW_BASE_URL = "https://raw.githubusercontent.com/f1db/f1db/main/src/assets/circuits"

AVAILABLE_STYLES = ("white-outline", "black-outline", "white", "black")
DEFAULT_STYLES = ("white-outline", "black-outline", "white", "black")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("track_layouts_evolution")


def format_year_ranges(years: List[int]) -> List[str]:
    """Compress a list of active years into readable range strings.

    Example:
        [1973, 1974, 1975, 1976, 1977, 1979, 1980] -> ['1973-1977', '1979-1980']
        [1950] -> ['1950']
        [2004, 2005, 2010, 2012, 2013] -> ['2004-2005', '2010', '2012-2013']
    """
    if not years:
        return []
    sorted_years = sorted(set(years))
    ranges: List[str] = []
    start = sorted_years[0]
    end = start

    for y in sorted_years[1:]:
        if y == end + 1:
            end = y
        else:
            ranges.append(f"{start}" if start == end else f"{start}-{end}")
            start = y
            end = y
    ranges.append(f"{start}" if start == end else f"{start}-{end}")
    return ranges


def extract_layout_number(layout_id: str) -> int:
    """Extract integer number from layout ID (e.g. 'interlagos-2' -> 2)."""
    match = re.search(r"-(\d+)$", layout_id)
    if match:
        return int(match.group(1))
    return 1


def find_database_path(candidate_path: Optional[str] = None) -> Path:
    """Locate the f1db SQLite database file or extract it from f1db-sqlite.zip."""
    if candidate_path:
        path = Path(candidate_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Specified database not found: {candidate_path}")

    # Default search locations
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_dir = repo_root / "backend"

    search_locations = [
        backend_dir / "f1db.db",
        repo_root / "f1db.db",
        Path.cwd() / "f1db.db",
        Path.cwd() / "backend" / "f1db.db",
    ]

    for loc in search_locations:
        if loc.exists() and loc.stat().st_size > 0:
            return loc

    # Check for f1db-sqlite.zip to extract if database not yet unpacked
    zip_locations = [
        backend_dir / "f1db-sqlite.zip",
        repo_root / "f1db-sqlite.zip",
        Path.cwd() / "f1db-sqlite.zip",
    ]

    for zip_loc in zip_locations:
        if zip_loc.exists():
            logger.info("Found database archive %s, extracting f1db.db...", zip_loc)
            with zipfile.ZipFile(zip_loc, "r") as z:
                for name in z.namelist():
                    if name.endswith("f1db.db"):
                        dest = backend_dir / "f1db.db"
                        with z.open(name) as src_file, open(dest, "wb") as dst_file:
                            dst_file.write(src_file.read())
                        logger.info("Extracted database to %s", dest)
                        return dest

    raise FileNotFoundError(
        "Could not find 'f1db.db' or 'f1db-sqlite.zip'. Please provide --db-path."
    )


class TrackLayoutExtractor:
    """Extracts track layout evolutions from F1DB SQLite with SVG GitHub links."""

    def __init__(
        self,
        db_path: Path,
        styles: Tuple[str, ...] = DEFAULT_STYLES,
    ):
        self.db_path = Path(db_path)
        self.styles = styles

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def extract_evolution(
        self, circuit_id_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query F1DB and construct complete evolution metadata for circuits and layouts."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # 1. Fetch circuits and country info
            circuit_query = """
                SELECT 
                    c.id,
                    c.name,
                    c.full_name,
                    c.previous_names,
                    c.type,
                    c.direction,
                    c.place_name,
                    c.country_id,
                    co.name as country_name,
                    co.alpha2_code,
                    co.alpha3_code,
                    co.continent_id,
                    c.latitude,
                    c.longitude,
                    c.length,
                    c.turns,
                    c.total_races_held
                FROM circuit c
                LEFT JOIN country co ON co.id = c.country_id
            """
            params: List[Any] = []
            if circuit_id_filter:
                circuit_query += " WHERE c.id = ?"
                params.append(circuit_id_filter)

            circuit_query += " ORDER BY c.id ASC"
            circuit_rows = cur.execute(circuit_query, params).fetchall()

            if not circuit_rows:
                logger.warning("No circuits found matching criteria.")
                return {"circuits": [], "total_circuits": 0, "total_layouts": 0}

            # 2. Fetch all circuit layouts
            layout_query = """
                SELECT 
                    cl.id,
                    cl.circuit_id,
                    cl.effective,
                    cl.length,
                    cl.turns
                FROM circuit_layout cl
            """
            if circuit_id_filter:
                layout_query += " WHERE cl.circuit_id = ?"
                layout_rows = cur.execute(layout_query, [circuit_id_filter]).fetchall()
            else:
                layout_rows = cur.execute(layout_query).fetchall()

            layouts_by_circuit: Dict[str, List[sqlite3.Row]] = {}
            for row in layout_rows:
                layouts_by_circuit.setdefault(row["circuit_id"], []).append(row)

            # 3. Fetch race occurrences per layout to determine active years
            race_query = """
                SELECT 
                    r.circuit_layout_id,
                    r.year
                FROM race r
            """
            if circuit_id_filter:
                race_query += " WHERE r.circuit_id = ?"
                race_rows = cur.execute(race_query, [circuit_id_filter]).fetchall()
            else:
                race_rows = cur.execute(race_query).fetchall()

            years_by_layout: Dict[str, List[int]] = {}
            for r in race_rows:
                years_by_layout.setdefault(r["circuit_layout_id"], []).append(r["year"])

        # 4. Assemble the structured evolution tree
        circuits_list: List[Dict[str, Any]] = []
        total_layouts_count = 0

        for c in circuit_rows:
            cid = c["id"]
            c_layouts = layouts_by_circuit.get(cid, [])
            layout_items: List[Dict[str, Any]] = []

            for l in c_layouts:
                lid = l["id"]
                years_active = sorted(list(set(years_by_layout.get(lid, []))))
                first_year = years_active[0] if years_active else None
                last_year = years_active[-1] if years_active else None
                year_ranges = format_year_ranges(years_active)

                # Direct GitHub links to the official F1DB repository
                svg_links = {
                    style: f"{F1DB_RAW_BASE_URL}/{style}/{lid}.svg"
                    for style in self.styles
                }

                layout_items.append({
                    "id": lid,
                    "circuit_id": cid,
                    "effective": bool(l["effective"]),
                    "length": float(l["length"]) if l["length"] is not None else None,
                    "turns": int(l["turns"]) if l["turns"] is not None else None,
                    "first_year": first_year,
                    "last_year": last_year,
                    "year_ranges": year_ranges,
                    "svg": svg_links,
                })

            # Sort layouts chronologically by first_year asc, then layout_number
            layout_items.sort(
                key=lambda item: (
                    item["first_year"] if item["first_year"] is not None else 9999,
                    extract_layout_number(item["id"]),
                )
            )

            total_layouts_count += len(layout_items)

            circuit_obj = {
                "id": cid,
                "name": c["name"],
                "full_name": c["full_name"],
                "previous_names": c["previous_names"],
                "type": c["type"],
                "direction": c["direction"],
                "place_name": c["place_name"],
                "country": {
                    "id": c["country_id"],
                    "name": c["country_name"],
                    "alpha2_code": c["alpha2_code"],
                    "alpha3_code": c["alpha3_code"],
                    "continent_id": c["continent_id"],
                },
                "location": {
                    "latitude": float(c["latitude"]) if c["latitude"] is not None else None,
                    "longitude": float(c["longitude"]) if c["longitude"] is not None else None,
                },
                "current_length_km": float(c["length"]) if c["length"] is not None else None,
                "current_turns": int(c["turns"]) if c["turns"] is not None else None,
                "total_races_held": int(c["total_races_held"]) if c["total_races_held"] is not None else 0,
                "layouts_count": len(layout_items),
                "layouts": layout_items,
            }
            circuits_list.append(circuit_obj)

        return {
            "version": "1.0",
            "source": "F1DB (Formula 1 Database)",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "styles_available": list(self.styles),
            "total_circuits": len(circuits_list),
            "total_layouts": total_layouts_count,
            "circuits": circuits_list,
        }


def export_json(data: Dict[str, Any], output_path: Path, pretty: bool = True) -> None:
    """Save structured evolution data to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)
    file_size_kb = output_path.stat().st_size / 1024
    logger.info("Saved evolution dataset to %s (%.1f KB)", output_path, file_size_kb)


def load_circuit_layouts_evolution(json_path: Optional[Path] = None) -> Dict[str, Any]:
    """Helper for backend services to load the generated evolution JSON dataset."""
    if json_path is None:
        default_paths = [
            Path(__file__).resolve().parent.parent / "data" / "circuit_layouts_evolution.json",
            Path.cwd() / "backend" / "data" / "circuit_layouts_evolution.json",
            Path.cwd() / "data" / "circuit_layouts_evolution.json",
        ]
        for p in default_paths:
            if p.exists():
                json_path = p
                break

    if json_path is None or not json_path.exists():
        raise FileNotFoundError(f"Circuit evolution JSON file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract F1 track layout evolutions with GitHub SVG links from F1DB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to f1db.db SQLite file (auto-detected if omitted).",
    )
    parser.add_argument(
        "--styles",
        type=str,
        default="white-outline,black-outline,white,black",
        help=f"Comma-separated list of SVG styles to include links for. Options: {', '.join(AVAILABLE_STYLES)}",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Path for output JSON file. Default: backend/data/circuit_layouts_evolution.json",
    )
    parser.add_argument(
        "--circuit",
        type=str,
        default=None,
        help="Filter extraction to a single circuit id (e.g. 'interlagos', 'monaco', 'silverstone').",
    )

    args = parser.parse_args()

    # Determine paths
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_dir = repo_root / "backend"

    db_path = find_database_path(args.db_path)
    logger.info("Using F1DB database at: %s", db_path)

    output_json = Path(args.output_json) if args.output_json else backend_dir / "data" / "circuit_layouts_evolution.json"

    # Parse styles
    requested_styles = tuple(s.strip() for s in args.styles.split(",") if s.strip())
    invalid_styles = [s for s in requested_styles if s not in AVAILABLE_STYLES]
    if invalid_styles:
        logger.error("Invalid styles requested: %s. Allowed: %s", invalid_styles, AVAILABLE_STYLES)
        return 1

    extractor = TrackLayoutExtractor(
        db_path=db_path,
        styles=requested_styles,
    )

    logger.info("Extracting circuit layout evolution from database...")
    data = extractor.extract_evolution(circuit_id_filter=args.circuit)
    logger.info(
        "Extracted %d circuits and %d layouts.",
        data["total_circuits"],
        data["total_layouts"],
    )

    export_json(data, output_json, pretty=True)
    logger.info("Complete! Output ready for frontend consumption.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
