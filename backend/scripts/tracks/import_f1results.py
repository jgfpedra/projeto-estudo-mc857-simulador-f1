#!/usr/bin/env python3
"""Convert validated F1 Results Database SVG maps to an offline circuit snapshot.

Requires numpy, scipy, Pillow, scikit-image; these are only needed when importing.
The dataset itself is ODbL-1.0 and its maps are traced from StatsF1.
"""
from __future__ import annotations
import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import disk, skeletonize

from f1results_mapping import find_circuit, year_in_ranges

NS = '{http://www.w3.org/2000/svg}'


def line_coords(element):
    return tuple(float(element.get(key)) for key in ('x1', 'y1', 'x2', 'y2'))


def convert_svg(svg):
    root = ET.fromstring(svg)
    if root.get('data-start-finish') != 'exact':
        raise ValueError('largada não localizada com confiança pela fonte')
    if root.get('data-direction-tangent') not in ('Clockwise', 'Anticlockwise'):
        raise ValueError('sentido ausente ou ambíguo')
    width, height = int(root.get('width')), int(root.get('height'))
    if not (100 <= width <= 2000 and 100 <= height <= 2000):
        raise ValueError('dimensões inválidas do SVG')
    image = Image.new('L', (width, height))
    draw = ImageDraw.Draw(image)
    polylines = list(root.iter(NS + 'polyline'))
    if not polylines:
        raise ValueError('contorno ausente')
    for element in polylines:
        coords = [tuple(map(float, point.split(','))) for point in element.get('points', '').split()]
        if len(coords) >= 2:
            draw.line(coords, fill=255, width=1)
    band = ndimage.binary_dilation(np.asarray(image) > 0, structure=disk(6))
    skeleton = skeletonize(band)
    _, components = ndimage.label(skeleton, np.ones((3, 3)))
    if components != 1:
        raise ValueError('contorno desconectado')
    pixels = {(int(x), int(y)) for y, x in np.argwhere(skeleton)}
    if len(pixels) < 150:
        raise ValueError('contorno pequeno')
    def adjacent(p):
        x, y = p
        return {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx or dy) and (x + dx, y + dy) in pixels
                and not (dx and dy and ((x + dx, y) in pixels or (x, y + dy) in pixels))}
    graph = {p: adjacent(p) for p in pixels}
    leaves = deque(p for p, edges in graph.items() if len(edges) < 2)
    removed = 0
    while leaves:
        p = leaves.popleft()
        if p not in graph or len(graph[p]) >= 2:
            continue
        for neighbor in list(graph[p]):
            graph[neighbor].discard(p)
            if len(graph[neighbor]) < 2:
                leaves.append(neighbor)
        del graph[p]
        removed += 1
    if removed > min(30, len(pixels) * .01) or len(graph) < 150 or any(len(edges) != 2 for edges in graph.values()):
        raise ValueError('linha central ambígua ou ramificada')
    lines = list(root.iter(NS + 'line'))
    start_lines = [e for e in lines if e.get('stroke', '').lower() == '#ffd200']
    arrows = [e for e in lines if e.get('stroke', '').lower() == '#e10600']
    if len(start_lines) != 1 or len(arrows) != 1:
        raise ValueError('largada ou seta não identificada')
    x1, y1, x2, y2 = line_coords(start_lines[0])
    mid = ((x1+x2)/2, (y1+y2)/2)
    start = min(graph, key=lambda p: math.dist(p, mid))
    if math.dist(start, mid) > 15:
        raise ValueError('largada distante da linha central')
    ordered = [start]
    previous, current = None, start
    while True:
        choices = sorted(p for p in graph[current] if p != previous)
        nxt = choices[0]
        if nxt == start:
            break
        if len(ordered) >= len(graph):
            raise ValueError('ciclo não fechado')
        ordered.append(nxt)
        previous, current = current, nxt
    if len(ordered) != len(graph):
        raise ValueError('ciclo incompleto')
    x1, y1, x2, y2 = line_coords(arrows[0])
    arrow_mid = ((x1+x2)/2, (y1+y2)/2)
    index = min(range(len(ordered)), key=lambda i: math.dist(ordered[i], arrow_mid))
    if math.dist(ordered[index], arrow_mid) > 50:
        raise ValueError('seta distante da linha central')
    before, after = ordered[(index-8) % len(ordered)], ordered[(index+8) % len(ordered)]
    tx, ty = after[0]-before[0], after[1]-before[1]
    vx, vy = x2-x1, y2-y1
    divisor = math.hypot(tx, ty) * math.hypot(vx, vy)
    alignment = (tx*vx + ty*vy) / divisor if divisor else 0
    if abs(alignment) < .7:
        raise ValueError('sentido não concorda com o traçado')
    if alignment < 0:
        ordered = [ordered[0], *reversed(ordered[1:])]
    xy = np.asarray(ordered, dtype=float)
    xy = np.column_stack((ndimage.gaussian_filter1d(xy[:, 0], 2, mode='wrap'),
                          ndimage.gaussian_filter1d(xy[:, 1], 2, mode='wrap')))
    xy[:, 1] *= -1
    closed = np.vstack((xy, xy[0]))
    cumulative = np.r_[0., np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    perimeter = float(cumulative[-1])
    if perimeter < 100:
        raise ValueError('perímetro inválido')
    count = max(200, int(math.ceil(perimeter / 4)))
    targets = np.arange(count) * perimeter / count
    x = np.interp(targets, cumulative, closed[:, 0])
    y = np.interp(targets, cumulative, closed[:, 1])
    x -= x[0]
    y -= y[0]
    unit = np.column_stack((x / perimeter, y / perimeter))
    return {'points': [[round(float(a), 7), round(float(b), 7)] for a, b in unit],
            'start_finish': 'source_marker', 'direction': root.get('data-direction-tangent'),
            'arrow_alignment': round(abs(alignment), 3), 'start_error_px': round(math.dist(start, mid), 2),
            'source_start_confidence': root.get('data-start-finish')}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build(db_path, f1db_path, layouts_path, release):
    data = json.loads(Path(f1db_path).read_text(encoding='utf-8'))
    circuits = data['circuits']
    layouts = {c['id']: c.get('layouts', []) for c in json.loads(Path(layouts_path).read_text(encoding='utf-8'))['circuits']}
    conn = sqlite3.connect(f'file:{Path(db_path).resolve()}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    maps, stats = {}, Counter()
    race_years = {}
    for row in conn.execute('SELECT CircuitLayoutID, Season FROM GrandsPrix WHERE CircuitLayoutID IS NOT NULL'):
        race_years.setdefault(row['CircuitLayoutID'], set()).add(row['Season'])
    for row in conn.execute('SELECT ID, Latitude, Longitude, SVG, TrackDirection FROM CircuitLayouts'):
        cid = find_circuit(row['Latitude'], row['Longitude'], circuits, layouts, race_years.get(row['ID'], set()))
        if not cid:
            stats['circuito não identificado'] += 1
            continue
        if not row['SVG']:
            stats['SVG ausente'] += 1
            continue
        try:
            item = convert_svg(row['SVG'])
            if row['TrackDirection'] != item['direction']:
                raise ValueError('sentido do layout diverge da seta')
            points = item['points']
            area = sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(points, points[1:] + points[:1]))
            if abs(area) < 1e-8 or (area < 0) != (item['direction'] == 'Clockwise'):
                raise ValueError('sentido geométrico diverge da seta')
            item['circuit_id'] = cid
            item['source_layout_id'] = row['ID']
            item['source_direction'] = row['TrackDirection']
            maps[str(row['ID'])] = item
            stats['layout aceito'] += 1
        except (ValueError, ET.ParseError, TypeError) as exc:
            stats[str(exc)] += 1
    events = {}
    ambiguous = set()
    for row in conn.execute('SELECT Season, GrandPrixName, CircuitLayoutID, CircuitLength FROM GrandsPrix ORDER BY Season, RoundNumber'):
        item = maps.get(str(row['CircuitLayoutID']))
        if not item or not row['CircuitLength']:
            continue
        match = re.fullmatch(r'\s*([0-9]+(?:[.,][0-9]+)?)\s*km\s*', row['CircuitLength'], flags=re.I)
        if not match:
            continue
        length = float(match.group(1).replace(',', '.')) * 1000
        if not 1000 <= length <= 30000:
            continue
        valid = [layout for layout in layouts.get(item['circuit_id'], [])
                 if year_in_ranges(row['Season'], layout.get('years'))]
        if len(valid) != 1:
            stats['ano sem layout F1DB inequívoco'] += 1
            continue
        key = f"{item['circuit_id']}:{row['Season']}"
        value = {'source_layout_id': row['CircuitLayoutID'], 'length_m': length,
                 'grand_prix': row['GrandPrixName']}
        if key in events and (events[key]['source_layout_id'] != value['source_layout_id'] or events[key]['length_m'] != value['length_m']):
            ambiguous.add(key)
        elif key not in events:
            events[key] = value
    for key in ambiguous:
        events.pop(key, None)
    used = {str(v['source_layout_id']) for v in events.values()}
    maps = {k:v for k,v in maps.items() if k in used}
    return {'source': 'F1 Results Database; SVGs traced from StatsF1 maps',
            'source_url': 'https://github.com/mclarenmp4-22/f1resultsdatabase',
            'release': release, 'license': 'ODbL-1.0', 'db_sha256': sha256(db_path),
            'f1db_catalog_sha256': sha256(f1db_path), 'f1db_layouts_sha256': sha256(layouts_path), 'approximate': True,
            'geometries': maps, 'races': events}, stats, ambiguous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--f1db-catalog', required=True, help='F1DB catalog JSON with circuit coordinates')
    parser.add_argument('--f1db-layouts', required=True, help='F1DB layout history JSON')
    parser.add_argument('--release', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    snapshot, stats, ambiguous = build(args.db, args.f1db_catalog, args.f1db_layouts, args.release)
    Path(args.output).write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    print('layouts incluídos:',len(snapshot['geometries']),'circuitos:',len({v['circuit_id'] for v in snapshot['geometries'].values()}),'temporadas:',len(snapshot['races']))
    print('anos/circuito ambíguos ignorados:',len(ambiguous))
    print('diagnóstico:',dict(stats))

if __name__ == '__main__':
    main()
