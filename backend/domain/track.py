"""Track domain module.

A pista é modelada como uma sequência de waypoints 2D ``(x, y)`` em metros,
em coordenadas mundiais. Os waypoints representam a linha central da pista.
Construímos também setores, linha de largada/chegada e pit lane.

A classe ``Track`` é agnóstica ao circuito. Circuitos reais podem ser criados
por ``Track.from_waypoints`` ou carregados do FastF1 através de
``FastF1TrackLoader``. ``build_interlagos_track`` permanece disponível como
um preset local para compatibilidade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence, Tuple

import numpy as np


Point2D = Tuple[float, float]


@dataclass
class Sector:
    """Setor da pista. Usado para tempos parciais e sector flags."""

    index: int
    name: str
    start_waypoint: int
    end_waypoint: int


@dataclass
class PitLane:
    """Pit lane: paralela à reta principal."""

    entry_waypoint: int  # índice do waypoint de entrada
    exit_waypoint: int  # índice do waypoint de saída
    speed_limit_kmh: float = 80.0
    time_penalty_s: float = 22.0


@dataclass
class Track:
    """Modelo de pista.

    Atributos
    ---------
    name : str
    waypoints : List[Tuple[float, float]]
        Lista de ``(x, y)`` em metros. A pista é fechada: o último ponto se
        conecta ao primeiro.
    length_m : float
        Comprimento total da pista em metros (soma dos segmentos).
    sectors : List[Sector]
    pit : PitLane
    start_finish_waypoint : int
        Índice do waypoint que marca a linha de largada/chegada.
    width_m : float
        Largura da pista em metros.
    source : str
        Origem dos dados da pista, por exemplo ``"manual"`` ou ``"fastf1"``.
    metadata : Mapping[str, object]
        Metadados opcionais do circuito (ano, evento, circuito FastF1, etc.).
    """

    name: str
    waypoints: List[Point2D]
    length_m: float
    sectors: List[Sector] = field(default_factory=list)
    pit: Optional[PitLane] = None
    start_finish_waypoint: int = 0
    width_m: float = 12.0
    source: str = "manual"
    metadata: Mapping[str, object] = field(default_factory=dict)
    initial_positions: List[Point2D] = field(default_factory=list)

    # --- construtores -------------------------------------------------------

    @classmethod
    def from_waypoints(
        cls,
        name: str,
        waypoints: Sequence[Point2D],
        length_m: Optional[float] = None,
        sectors: Optional[List[Sector]] = None,
        pit: Optional[PitLane] = None,
        start_finish_waypoint: int = 0,
        width_m: float = 12.0,
        source: str = "manual",
        metadata: Optional[Mapping[str, object]] = None,
        initial_positions: Optional[Sequence[Point2D]] = None,
    ) -> "Track":
        """Cria uma pista genérica a partir de waypoints ``(x, y)``.

        Quando ``length_m`` não é informado, o comprimento é calculado como a
        soma dos segmentos fechados entre waypoints adjacentes.
        """
        normalized: List[Point2D] = []
        for point in waypoints:
            if len(point) < 2:
                raise ValueError("each waypoint must contain x and y")
            normalized.append((float(point[0]), float(point[1])))

        if len(normalized) < 2:
            raise ValueError("waypoints must contain at least two points")
        if not 0 <= start_finish_waypoint < len(normalized):
            raise ValueError("start_finish_waypoint is outside the waypoint range")

        calculated_length = _compute_segment_length(normalized)
        sf_idx = int(start_finish_waypoint)
        width = float(width_m)

        if initial_positions is not None and len(initial_positions) > 0:
            grid: List[Point2D] = [
                (float(p[0]), float(p[1])) for p in initial_positions if len(p) >= 2
            ]
        else:
            grid = compute_grid_positions(
                normalized,
                start_finish_waypoint=sf_idx,
                num_slots=24,
                width_m=width,
            )

        return cls(
            name=name,
            waypoints=normalized,
            length_m=(calculated_length if length_m is None else float(length_m)),
            sectors=list(sectors or []),
            pit=pit,
            start_finish_waypoint=sf_idx,
            width_m=width,
            source=source,
            metadata=dict(metadata or {}),
            initial_positions=grid,
        )

    @classmethod
    def from_fastf1(
        cls,
        year: int,
        event: str | int,
        session: str = "R",
        **kwargs: Any,
    ) -> "Track":
        """Carrega um circuito do FastF1 sem acoplar a engine à biblioteca.

        Os argumentos adicionais são encaminhados para ``FastF1TrackLoader``.
        """
        from .track_loader import FastF1TrackLoader

        return FastF1TrackLoader().load(
            year=year,
            event=event,
            session=session,
            **kwargs,
        )

    # --- propriedades derivadas -------------------------------------------

    @property
    def length_km(self) -> float:
        return self.length_m / 1000.0

    def positions(self) -> Tuple[np.ndarray, np.ndarray]:
        """Devolve arrays ``(xs, ys)`` dos waypoints."""
        if not self.waypoints:
            return np.array([]), np.array([])
        xs = np.array([point[0] for point in self.waypoints])
        ys = np.array([point[1] for point in self.waypoints])
        return xs, ys

    def closest_waypoint(self, x: float, y: float) -> Tuple[int, float]:
        """Retorna (índice do waypoint mais próximo, distância)."""
        xs, ys = self.positions()
        if len(xs) == 0:
            return 0, 0.0
        dx = xs - x
        dy = ys - y
        dist2 = dx * dx + dy * dy
        idx = int(np.argmin(dist2))
        return idx, float(math.sqrt(dist2[idx]))

    def next_waypoint(self, idx: int, steps: int = 1) -> int:
        """Próximo waypoint cíclico."""
        if not self.waypoints:
            raise ValueError("track has no waypoints")
        n = len(self.waypoints)
        return (idx + steps) % n

    def waypoint(self, idx: int) -> Point2D:
        if not self.waypoints:
            raise ValueError("track has no waypoints")
        return self.waypoints[idx % len(self.waypoints)]

    def initial_position(self, index: int = 0) -> Point2D:        
        """Retorna a posição inicial (x, y) no grid de largada para o carro de índice `index`.
        Se o índice estiver além das posições pré-calculadas em `initial_positions`,
        computa o slot dinamicamente mantendo o espaçamento e padrão do grid."""
        if 0 <= index < len(self.initial_positions):
            return self.initial_positions[index]
        return compute_grid_slot(
            self.waypoints,
            start_finish_waypoint=self.start_finish_waypoint,
            slot_index=index,
            width_m=self.width_m,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "length_m": round(self.length_m, 1),
            "length_km": round(self.length_km, 3),
            "num_waypoints": len(self.waypoints),
            "sectors": [
                {
                    "index": sector.index,
                    "name": sector.name,
                    "start": sector.start_waypoint,
                    "end": sector.end_waypoint,
                }
                for sector in self.sectors
            ],
            "pit": {
                "entry": self.pit.entry_waypoint,
                "exit": self.pit.exit_waypoint,
                "speed_limit_kmh": self.pit.speed_limit_kmh,
                "time_penalty_s": self.pit.time_penalty_s,
            } if self.pit else None,
            "start_finish_waypoint": self.start_finish_waypoint,
            "width_m": self.width_m,
            "source": self.source,
            "metadata": dict(self.metadata),
            "initial_positions": [list(p) for p in self.initial_positions],
        }
        # ------------------------------------------------------------------
    # Distância à linha central — hot path com janela (hint)
    # ------------------------------------------------------------------

    def distance_to_centerline_near(
        self,
        x: float,
        y: float,
        hint_idx: int,
        window: int = 15,
    ) -> Tuple[float, int]:
        """Distância perpendicular ao segmento mais próximo, mas restringe
        a busca a uma janela de `2*window+1` segmentos em torno de `hint_idx`.

        Custo: O(window) — praticamente constante, independente do tamanho
        da pista. Use quando souber que o carro não teleporta entre ticks.

        Retorna (distância, índice do waypoint mais próximo dentro da janela).
        O segundo valor DEVE ser usado como hint_idx na próxima chamada.
        """
        n = len(self.waypoints)
        if n < 2:
            return 0.0, hint_idx
        best_dist2 = float("inf")
        best_idx = hint_idx % n
        # Clamp da janela se a pista for pequena — evita varrer segmentos 2x
        w = min(window, n // 2)
        for offset in range(-w, w + 1):
            i = (hint_idx + offset) % n
            ax, ay = self.waypoints[i]
            bx, by = self.waypoints[(i + 1) % n]
            abx, aby = bx - ax, by - ay
            seg_len2 = abx * abx + aby * aby
            if seg_len2 < 1e-9:
                continue
            t = max(0.0, min(1.0, ((x - ax) * abx + (y - ay) * aby) / seg_len2))
            cx, cy = ax + t * abx, ay + t * aby
            dx, dy = x - cx, y - cy
            dist2 = dx * dx + dy * dy
            if dist2 < best_dist2:
                best_dist2 = dist2
                best_idx = i
        return math.sqrt(best_dist2), best_idx

    def distance_to_centerline(self, x: float, y: float) -> float:
        """Fallback O(W) — use só em testes/APIs externas sem hint disponível."""
        n = len(self.waypoints)
        if n < 2:
            return 0.0
        best_dist2 = float("inf")
        for i in range(n):
            ax, ay = self.waypoints[i]
            bx, by = self.waypoints[(i + 1) % n]
            abx, aby = bx - ax, by - ay
            seg_len2 = abx * abx + aby * aby
            if seg_len2 < 1e-9:
                continue
            t = max(0.0, min(1.0, ((x - ax) * abx + (y - ay) * aby) / seg_len2))
            cx, cy = ax + t * abx, ay + t * aby
            dist2 = (x - cx) ** 2 + (y - cy) ** 2
            if dist2 < best_dist2:
                best_dist2 = dist2
        return math.sqrt(best_dist2)

    # ------------------------------------------------------------------
    # Superfície: versões com e sem distância pré-calculada
    # ------------------------------------------------------------------

    def surface_grip_factor_from_distance(
        self,
        dist: float,
        grass_falloff_m: float = 3.0,
    ) -> float:
        """Mesmo cálculo de `surface_grip_factor`, mas recebe a distância
        já calculada por `distance_to_centerline_near`. Evita recalcular.

        Use este no hot path da engine — a distância já vem do cálculo
        de posicionamento/limite de pista.
        """
        half_width = self.width_m / 2.0
        if dist <= half_width:
            return 1.0
        over = dist - half_width
        # Cai de 1.0 até 0.35 (grip residual na grama) ao longo de grass_falloff_m
        factor = 1.0 - min(1.0, over / grass_falloff_m) * 0.65
        return max(0.35, factor)

    def surface_grip_factor(
        self,
        x: float,
        y: float,
        hint_idx: Optional[int] = None,
        grass_falloff_m: float = 3.0,
    ) -> float:
        """Multiplicador de grip pela superfície.

        Se `hint_idx` for fornecido, usa a busca em janela (O(window)).
        Caso contrário, faz a busca completa O(W) — só para compat.
        """
        if hint_idx is None:
            dist = self.distance_to_centerline(x, y)
        else:
            dist, _ = self.distance_to_centerline_near(x, y, hint_idx=hint_idx)
        return self.surface_grip_factor_from_distance(dist, grass_falloff_m)

    def is_on_track_near(
        self,
        x: float,
        y: float,
        hint_idx: int,
        window: int = 15,
    ) -> Tuple[bool, int]:
        """Versão com hint de `is_on_track`. Retorna (bool, novo_hint)."""
        dist, new_idx = self.distance_to_centerline_near(x, y, hint_idx, window)
        return (dist <= (self.width_m / 2.0)), new_idx

    def is_on_track(self, x: float, y: float) -> bool:
        """Compat: usa busca completa. Prefira `is_on_track_near` no hot path."""
        return self.distance_to_centerline(x, y) <= (self.width_m / 2.0)


# -----------------------------------------------------------------------
# Funções de Grid de Largada e Curvas
# -----------------------------------------------------------------------

def compute_grid_slot(
    waypoints: Sequence[Point2D],
    start_finish_waypoint: int = 0,
    slot_index: int = 0,
    width_m: float = 12.0,
    slot_spacing_m: float = 8.0,
    first_slot_dist_m: float = 8.0,
) -> Point2D:
    """Calcula a posição (x, y) de um slot do grid de largada.

    Os slots são dispostos atrás da linha de largada/chegada em formação 2x2
    escalonada típica da F1.
    """
    n = len(waypoints)
    if n < 2:
        return (0.0, 0.0)
    sf_idx = start_finish_waypoint % n
    p_prev = waypoints[(sf_idx - 1) % n]
    p_curr = waypoints[sf_idx]
    p_next = waypoints[(sf_idx + 1) % n]

    tx = p_next[0] - p_prev[0]
    ty = p_next[1] - p_prev[1]
    tangent_len = math.hypot(tx, ty) or 1.0
    fx, fy = tx / tangent_len, ty / tangent_len
    nx, ny = -fy, fx

    dist_back = first_slot_dist_m + slot_index * slot_spacing_m
    lateral_offset = min(2.5, max(1.0, width_m * 0.22)) * (1.0 if slot_index % 2 == 0 else -1.0)
    px = p_curr[0] - dist_back * fx + lateral_offset * nx
    py = p_curr[1] - dist_back * fy + lateral_offset * ny
    return (float(px), float(py))


def compute_grid_positions(
    waypoints: Sequence[Point2D],
    start_finish_waypoint: int = 0,
    num_slots: int = 24,
    width_m: float = 12.0,
) -> List[Point2D]:
    """Gera lista de posições 2D para o grid de largada."""
    return [
        compute_grid_slot(
            waypoints,
            start_finish_waypoint=start_finish_waypoint,
            slot_index=i,
            width_m=width_m,
        )
        for i in range(max(1, num_slots))
    ]

def _catmull_rom_spline(
    points: Sequence[Point2D],
    samples_per_segment: int = 12,
) -> List[Point2D]:
    """Interpolação Catmull-Rom fechada para gerar uma curva suave."""
    n = len(points)
    if n < 3:
        return [(float(x), float(y)) for x, y in points]
    result: List[Point2D] = []
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        for t in np.linspace(0.0, 1.0, samples_per_segment, endpoint=False):
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            result.append((float(x), float(y)))
    return result


def _compute_segment_length(waypoints: Sequence[Point2D]) -> float:
    total = 0.0
    n = len(waypoints)
    for i in range(n):
        x1, y1 = waypoints[i]
        x2, y2 = waypoints[(i + 1) % n]
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def _scale_to_length(
    waypoints: Sequence[Point2D],
    target_length_m: float,
) -> List[Point2D]:
    """Escala waypoints uniformemente para atingir o comprimento alvo."""
    current = _compute_segment_length(waypoints)
    if current <= 0:
        return [(float(x), float(y)) for x, y in waypoints]
    scale = target_length_m / current
    return [(x * scale, y * scale) for x, y in waypoints]


# Coordenadas esquemáticas de Interlagos (~4.309 km).
_INTERLAGOS_KEYPOINTS: List[Point2D] = [
    (0.0, 0.0),       # reta principal / start-finish
    (300.0, 0.0),
    (380.0, 30.0),
    (430.0, 80.0),
    (470.0, 130.0),
    (450.0, 200.0),
    (380.0, 260.0),
    (300.0, 280.0),
    (180.0, 280.0),
    (60.0, 280.0),
    (-30.0, 260.0),
    (-90.0, 220.0),
    (-140.0, 160.0),
    (-160.0, 100.0),
    (-150.0, 40.0),
    (-90.0, 10.0),
    (-40.0, -20.0),
    (-10.0, -30.0),
    (40.0, -30.0),
    (120.0, -20.0),
]


def build_interlagos_track(
    target_length_m: float = 4309.0,
    samples_per_segment: int = 12,
) -> Track:
    """Constrói uma pista inspirada em Interlagos (José Carlos Pace).

    Retorna um objeto :class:`Track` com waypoints interpolados por Catmull-Rom,
    setores e pit lane.
    """
    smooth = _catmull_rom_spline(
        _INTERLAGOS_KEYPOINTS,
        samples_per_segment=samples_per_segment,
    )
    waypoints = _scale_to_length(smooth, target_length_m)

    start_finish = 0
    n = len(waypoints)
    s1_end = n // 3
    s2_end = 2 * n // 3
    sectors = [
        Sector(index=1, name="Sector 1", start_waypoint=0, end_waypoint=s1_end),
        Sector(index=2, name="Sector 2", start_waypoint=s1_end, end_waypoint=s2_end),
        Sector(index=3, name="Sector 3", start_waypoint=s2_end, end_waypoint=n - 1),
    ]

    pit_entry = int(n * 0.92)
    pit_exit = int(n * 0.04)
    pit = PitLane(entry_waypoint=pit_entry, exit_waypoint=pit_exit)

    return Track.from_waypoints(
        name="Interlagos",
        waypoints=waypoints,
        length_m=_compute_segment_length(waypoints),
        sectors=sectors,
        pit=pit,
        start_finish_waypoint=start_finish,
    )