"""Geometria de boxes parametrizável e fallback estimado para qualquer pista."""
from __future__ import annotations

import math
from bisect import bisect_right

from .track import PitLane


def ensure_pit_lane(track):
    """Prepara uma via aberta. Sem geometria medida, estima-se ao lado da reta.

    As coordenadas usam o mesmo referencial da pista; a origem e a largura
    estimadas são identificadas explicitamente para os consumidores.
    """
    if track.pit is not None and len(track.pit.waypoints) >= 2:
        return track.pit
    points = track.waypoints
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:] + points[:1])]
    starts = [0.0]
    for length in lengths:
        starts.append(starts[-1] + length)
    total = starts[-1]
    if total < 1e-6:
        raise ValueError('Pista sem comprimento para gerar boxes')
    sf_s = starts[track.start_finish_waypoint]
    # Aproximação ao redor da linha de chegada; a transição suave oferece
    # espaço para o carro mudar de faixa sem saltar de posição.
    before = min(500.0, total * .18)
    after = min(140.0, total * .06)

    # A entrada deve começar depois da última curva fechada anterior à linha.
    # Deslocar a via para o lado de dentro de um hairpin cria um atalho sobre
    # o asfalto e coloca o carro dos boxes no caminho de quem segue em corrida.
    def point_at(relative_s):
        s = (sf_s + relative_s) % total
        idx = min(bisect_right(starts, s) - 1, len(points) - 1)
        a, b = points[idx], points[(idx + 1) % len(points)]
        segment = lengths[idx]
        if segment < 1e-9:
            raise ValueError('Segmento degenerado ao gerar boxes')
        t = (s - starts[idx]) / segment
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    last_sharp = None
    relative_s = -before
    while relative_s <= -40.0:
        a, b, c = point_at(relative_s - 10.0), point_at(relative_s), point_at(relative_s + 10.0)
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = c[0] - b[0], c[1] - b[1]
        turn = abs(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy))
        if turn / 10.0 > .02:
            last_sharp = relative_s
        relative_s += 5.0
    if last_sharp is not None:
        # Deixe margem para terminar a curva antes de mudar de faixa.
        before = min(before, max(40.0, -last_sharp - 25.0))

    span = before + after
    count = max(20, math.ceil(span / 5.0))
    lane = []
    indices = []
    for i in range(count + 1):
        rel = -before + span * i / count
        s = (sf_s + rel) % total
        idx = min(bisect_right(starts, s) - 1, len(points)-1)
        a, b = points[idx], points[(idx + 1) % len(points)]
        seg = lengths[idx]
        if seg < 1e-9:
            raise ValueError('Segmento degenerado ao gerar boxes')
        t = (s-starts[idx]) / seg
        dx, dy = (b[0]-a[0])/seg, (b[1]-a[1])/seg
        # 120 m para cada mudança de faixa; no centro fica fora do asfalto.
        ramp = min(120.0, span * .25)
        ramp_in = min(1.0, max(0.0, (rel+before)/ramp))
        ramp_out = min(1.0, max(0.0, (after-rel)/ramp))
        blend = min(ramp_in, ramp_out)
        blend = blend * blend * (3.0 - 2.0 * blend)
        offset = (track.width_m / 2.0 + 4.0) * blend
        lane.append((a[0] + (b[0]-a[0])*t + dy*offset,
                     a[1] + (b[1]-a[1])*t - dx*offset))
        indices.append(idx)
    previous = track.pit
    track.pit = PitLane(entry_waypoint=indices[0], exit_waypoint=indices[-1],
                        speed_limit_kmh=previous.speed_limit_kmh if previous else 80.0,
                        waypoints=lane, width_m=6.0, source='estimated',
                        entry_s_m=(-before) % total)
    return track.pit
