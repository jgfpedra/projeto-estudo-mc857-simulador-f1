"""Adapter para carregar circuitos reais a partir do FastF1.

O FastF1 expõe os cantos do circuito em ``Session.get_circuit_info().corners``
(um DataFrame com colunas ``X``/``Y``). Esses pontos são interpolados com
Catmull-Rom para formar uma linha fechada usada pela engine e pelo PyBullet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .track import (
    PitLane,
    Point2D,
    Sector,
    Track,
    _catmull_rom_spline,
    _compute_segment_length,
    _scale_to_length,
    compute_grid_positions,
)


class CircuitLoadError(RuntimeError):
    """Falha ao obter ou converter um circuito do FastF1."""


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Normaliza dicts, Series e objetos simples retornados por bibliotecas externas."""
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            result = value.to_dict()
            if isinstance(result, Mapping):
                return result
        except (AttributeError, TypeError):
            pass
    if hasattr(value, "__dict__"):
        return vars(value)
    return {}


def _first_number(value: Any, names: Sequence[str]) -> Optional[float]:
    mapping = _as_mapping(value)
    for name in names:
        if name in mapping:
            candidate = mapping[name]
        elif hasattr(value, name):
            candidate = getattr(value, name)
        else:
            continue
        try:
            number = float(candidate)
        except (TypeError, ValueError):
            continue
        if number == number:  # NaN check
            return number
    return None


def _first_text(value: Any, names: Sequence[str]) -> Optional[str]:
    mapping = _as_mapping(value)
    for name in names:
        if name in mapping:
            candidate = mapping[name]
        elif hasattr(value, name):
            candidate = getattr(value, name)
        else:
            continue
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text and text.lower() != "nan":
            return text
    return None


def _points_from_table(raw_points: Any) -> list[Point2D]:
    """Extrai pares ``(x, y)`` de DataFrame, lista de dicts ou objetos com X/Y."""
    if raw_points is None:
        return []

    columns = getattr(raw_points, "columns", None)
    if columns is not None:
        col_map = {str(col).lower(): col for col in columns}
        if "x" in col_map and "y" in col_map:
            xs = list(raw_points[col_map["x"]])
            ys = list(raw_points[col_map["y"]])
            points: list[Point2D] = []
            for x, y in zip(xs, ys):
                try:
                    points.append((float(x), float(y)))
                except (TypeError, ValueError):
                    continue
            if points:
                return points

    if isinstance(raw_points, Mapping):
        raw_points = [raw_points]
    if not isinstance(raw_points, Sequence) or isinstance(raw_points, (str, bytes)):
        return []

    points = []
    for raw_point in raw_points:
        x = _first_number(raw_point, ("X", "x"))
        y = _first_number(raw_point, ("Y", "y"))
        if x is not None and y is not None:
            points.append((x, y))
    return points


def _extract_named_points(info: Any, names: Sequence[str]) -> list[Point2D]:
    mapping = _as_mapping(info)
    for name in names:
        if hasattr(info, name):
            points = _points_from_table(getattr(info, name))
            if points:
                return points
        if name in mapping:
            points = _points_from_table(mapping[name])
            if points:
                return points
    return []


def _nearest_waypoint(point: Point2D, waypoints: Sequence[Point2D]) -> int:
    x, y = point
    return min(
        range(len(waypoints)),
        key=lambda idx: (waypoints[idx][0] - x) ** 2 + (waypoints[idx][1] - y) ** 2,
    )


def _default_pit_lane(waypoint_count: int) -> PitLane:
    n = max(2, waypoint_count)
    return PitLane(
        entry_waypoint=int(n * 0.92) % n,
        exit_waypoint=int(n * 0.04) % n,
    )


def _pit_lane_from_info(info: Any, waypoints: Sequence[Point2D]) -> PitLane:
    points = _extract_named_points(info, ("PitLane", "pit_lane", "PitLanePoints"))
    if len(points) >= 2 and waypoints:
        return PitLane(
            entry_waypoint=_nearest_waypoint(points[0], waypoints),
            exit_waypoint=_nearest_waypoint(points[-1], waypoints),
        )
    return _default_pit_lane(len(waypoints))


def _start_finish_index(waypoints: Sequence[Point2D], info: Any) -> int:
    """Usa a origem do mapa FastF1 (linha de chegada) quando disponível."""
    explicit = _extract_named_points(
        info,
        ("StartFinish", "start_finish", "StartFinishLine"),
    )
    if explicit:
        return _nearest_waypoint(explicit[0], waypoints)
    return _nearest_waypoint((0.0, 0.0), waypoints)


def _even_sectors(waypoint_count: int) -> list[Sector]:
    n = waypoint_count
    s1_end = n // 3
    s2_end = 2 * n // 3
    return [
        Sector(index=1, name="Sector 1", start_waypoint=0, end_waypoint=s1_end),
        Sector(index=2, name="Sector 2", start_waypoint=s1_end, end_waypoint=s2_end),
        Sector(index=3, name="Sector 3", start_waypoint=s2_end, end_waypoint=n - 1),
    ]

class FastF1TrackLoader:
    """Carrega um circuito do FastF1 e o converte em ``Track``.

    Parameters
    ----------
    cache_dir:
        Diretório opcional usado pelo cache do FastF1. Quando informado, o
        cache é criado automaticamente para evitar downloads repetidos.
    fastf1_module:
        Injeção da biblioteca para testes.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        fastf1_module: Any | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._fastf1_module = fastf1_module

    def _get_fastf1(self) -> Any:
        if self._fastf1_module is not None:
            return self._fastf1_module
        try:
            import fastf1
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise CircuitLoadError(
                "FastF1 não está instalado. Instale as dependências do backend "
                "com: pip install -r backend/requirements.txt"
            ) from exc
        return fastf1

    def _enable_cache(self, fastf1: Any) -> None:
        if self.cache_dir is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache = getattr(fastf1, "Cache", None)
        if cache is None or not hasattr(cache, "enable_cache"):
            raise CircuitLoadError("FastF1 Cache API is not available")
        cache.enable_cache(str(self.cache_dir))

    def _grid_positions_from_telemetry(
        self,
        ff1_session: Any,
        scale: float = 1.0,
    ) -> list[Point2D]:
        """Usa a primeira amostra de telemetria (X, Y) de cada piloto, ordenada
        pela posição de largada (1º, 2º, 3º...), como grid real.

        Retorna uma lista posicional: índice 0 = pole, índice 1 = 2º lugar, etc.
        Requer sessão carregada com laps=True e telemetry=True.
        """
        try:
            results = ff1_session.results
            driver_order = list(results.sort_values("GridPosition")["Abbreviation"])
        except Exception:
            try:
                driver_order = list(ff1_session.laps["Driver"].unique())
            except Exception:
                return []

        try:
            laps = ff1_session.laps
        except Exception:
            return []
        if laps is None or len(laps) == 0:
            return []

        grid: list[Point2D] = []
        for drv in driver_order:
            try:
                drv_laps = laps.pick_driver(drv)
                first_lap = drv_laps.iloc[0]
                telemetry = first_lap.get_telemetry()
                if telemetry is None or len(telemetry) == 0:
                    continue
                sample = telemetry.iloc[0]
                grid.append((float(sample["X"]) * scale, float(sample["Y"]) * scale))
            except Exception:
                continue
        return grid

    def load(
        self,
        year: int,
        event: str | int,
        session: str = "R",
        *,
        samples_per_segment: int = 12,
        scale_to_official_length: bool = True,
        load_session: bool = True,
        grid_from_telemetry: bool = False
    ) -> Track:
        """Carrega os pontos do circuito e retorna um :class:`Track`.

        ``event`` aceita o nome usado pelo FastF1 (por exemplo ``"São Paulo"``)
        ou o número da rodada. ``session`` usa os códigos do FastF1, como ``R``,
        ``Q``, ``S`` e ``FP1``.
        """
        if samples_per_segment < 1:
            raise ValueError("samples_per_segment must be at least 1")

        fastf1 = self._get_fastf1()
        self._enable_cache(fastf1)

        try:
            ff1_session = fastf1.get_session(year, event, session)
        except Exception as exc:
            raise CircuitLoadError(
                f"FastF1 could not find session year={year!r} event={event!r} "
                f"session={session!r}"
            ) from exc

        if ff1_session is None:
            raise CircuitLoadError(
                f"FastF1 returned no session for year={year!r} event={event!r} "
                f"session={session!r}"
            )
        need_telemetry = load_session and grid_from_telemetry

        if load_session and hasattr(ff1_session, "load"):
            try:
                ff1_session.load(
                    #llaps=True if need_telemetry else False,
                    #telemetry=need_telemetry,
                    laps=True,
                    telemetry=True,
                    weather=False,
                    messages=False,
                )
            except TypeError:
                ff1_session.load(laps=need_telemetry, telemetry=need_telemetry, weather=False)
            except Exception as exc:
                raise CircuitLoadError(
                    f"FastF1 failed to load session year={year!r} event={event!r} "
                    f"session={session!r}"
                ) from exc

        try:
            raw_info = ff1_session.get_circuit_info()
        except Exception as exc:
            raise CircuitLoadError(
                f"FastF1 could not load circuit info for year={year!r} "
                f"event={event!r} session={session!r}: {exc}"
            ) from exc

        if raw_info is None:
            raise CircuitLoadError(
                f"FastF1 returned no circuit info for year={year!r} "
                f"event={event!r} session={session!r}"
            )

        corners = _extract_named_points(
            raw_info,
            ("corners", "Corners", "turns", "Turns"),
        )
        if len(corners) < 3:
            raise CircuitLoadError(
                "FastF1 did not return enough circuit corners; "
                f"check year={year!r}, event={event!r} and session={session!r}"
            )

        smooth_points = _catmull_rom_spline(
            corners,
            samples_per_segment=samples_per_segment,
        )
        if len(smooth_points) < 3:
            raise CircuitLoadError("unable to interpolate FastF1 circuit corners")

        official_length = _first_number(
            raw_info,
            ("Length", "length", "CircuitLength", "circuit_length"),
        )
        if official_length is None:
            official_length = _first_number(
                getattr(ff1_session, "event", None),
                ("CircuitLength", "circuit_length", "Length", "length"),
            )
        scale = 1.0
        if scale_to_official_length and official_length and official_length > 0:
            pre_scale_length = _compute_segment_length(smooth_points)
            scale = official_length / pre_scale_length if pre_scale_length > 0 else 1.0
            smooth_points = _scale_to_length(smooth_points, official_length)

        waypoints = [(float(x), float(y)) for x, y in smooth_points]
        length_m = _compute_segment_length(waypoints)
        event_obj = getattr(ff1_session, "event", None)
        circuit_name = (
            _first_text(raw_info, ("CircuitName", "circuit_name", "EventName", "event_name"))
            or _first_text(event_obj, ("EventName", "Location", "OfficialEventName", "Country"))
            or str(event)
        )
        metadata: dict[str, object] = {
            "year": year,
            "event": event,
            "session": session,
            "circuit_id": _first_text(raw_info, ("CircuitId", "circuit_id"))
            or _first_text(event_obj, ("CircuitId", "circuit_id")),
            "official_length_m": official_length,
            "corner_count": len(corners),
            "location": _first_text(raw_info, ("Location", "location"))
            or _first_text(event_obj, ("Location", "location")),
            "country": _first_text(raw_info, ("Country", "country"))
            or _first_text(event_obj, ("Country", "country")),
            "rotation_deg": _first_number(raw_info, ("rotation", "Rotation")),
            "latitude": _first_number(raw_info, ("Latitude", "latitude")),
            "longitude": _first_number(raw_info, ("Longitude", "longitude")),
            "altitude": _first_number(raw_info, ("Altitude", "altitude")),
        }

        sf_idx = _start_finish_index(waypoints, raw_info)
        grid_points = []
        if grid_from_telemetry:
            grid_points = self._grid_positions_from_telemetry(ff1_session, scale=scale)
        if not grid_points:
            grid_points = _extract_named_points(
                raw_info,
                (
                    "grid", "Grid",
                    "starting_grid", "StartingGrid",
                    "grid_positions", "GridPositions",
                    "grid_boxes", "GridBoxes",
                    "boxes",
                ),
            )
        if not grid_points:
            grid_points = compute_grid_positions(
                waypoints,
                start_finish_waypoint=sf_idx,
                num_slots=24,
                width_m=12.0,
            )

        return Track.from_waypoints(
            name=str(circuit_name),
            waypoints=waypoints,
            length_m=length_m,
            sectors=_even_sectors(len(waypoints)),
            pit=_pit_lane_from_info(raw_info, waypoints),
            start_finish_waypoint=sf_idx,
            source="fastf1",
            metadata=metadata,
            initial_positions=grid_points,
        )
