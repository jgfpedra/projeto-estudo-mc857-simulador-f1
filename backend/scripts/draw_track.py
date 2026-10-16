#!/usr/bin/env python
"""Desenha a pista: gráfico matplotlib (padrão) ou ASCII no terminal.

Uso:
  .venv/bin/python scripts/draw_track.py                       # Interlagos (janela)
  .venv/bin/python scripts/draw_track.py --track Monza         # qualquer pista FastF1
  .venv/bin/python scripts/draw_track.py --csv pista.csv       # CSV com colunas X,Y
  .venv/bin/python scripts/draw_track.py --save pista.png      # salva em PNG (sem abrir janela)
  .venv/bin/python scripts/draw_track.py --ascii               # só no terminal (sem janela)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
for p in (str(BACKEND.parent), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np


def load_track(name=None, csv_path=None, year=2024):
    """Resolve a pista pelo mesmo caminho do env (FastF1/CSV/preset)."""
    if csv_path:
        import pandas as pd
        from backend.domain import Track
        ref = pd.read_csv(csv_path)
        return Track.from_waypoints(
            name=Path(csv_path).stem,
            waypoints=ref[['X', 'Y']].values.astype(float),
            width_m=12.0,
        )
    from backend.model_train.f1_env import resolve_track
    return resolve_track(track=name, year=year)


# ──────────────────────────────────────────────────────── desenho matplotlib
def plot_track(track, save_path=None, show=True):
    """Gráfico 2D da pista: asfalto preenchido, linha central, SF, curvas numeradas."""
    import matplotlib
    if save_path or not show:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon
    from matplotlib.collections import PolyCollection

    wps = np.array(track.waypoints, dtype=np.float64)
    hw = float(getattr(track, 'width_m', 12.0)) / 2.0
    n = len(wps)

    # bordas: centro ± normal × meia-largura
    d = np.roll(wps, -1, axis=0) - wps
    seg_len = np.hypot(d[:, 0], d[:, 1])
    heading = np.arctan2(d[:, 1], d[:, 0])
    nx = -np.sin(heading) * hw
    ny = np.cos(heading) * hw
    left = wps + np.column_stack([nx, ny])
    right = wps - np.column_stack([nx, ny])

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#16213e')

    # asfalto: polígono preenchido entre as bordas
    # (segmenta em fatias para curvas fechadas funcionarem bem)
    edge_poly = np.vstack([left, right[::-1]])
    ax.fill(edge_poly[:, 0], edge_poly[:, 1], color='#3a3a5c', zorder=1,
            alpha=0.85)

    # bordas (linhas brancas)
    ax.plot(left[:, 0], left[:, 1], color='white', lw=1.2, zorder=3)
    ax.plot(right[:, 0], right[:, 1], color='white', lw=1.2, zorder=3)

    # linha central tracejada
    ax.plot(wps[:, 0], wps[:, 1], color='#e0e0e0', lw=0.8, ls='--',
            zorder=2, alpha=0.6)

    # linha de largada/chegada (perpendicular à pista no wp SF)
    sf = track.start_finish_waypoint
    h = heading[sf]
    px, py = wps[sf]
    sx, sy = -math.sin(h), math.cos(h)
    sf_line = np.array([[px + sx * hw * 1.3, py + sy * hw * 1.3],
                        [px - sx * hw * 1.3, py - sy * hw * 1.3]])
    ax.plot(sf_line[:, 0], sf_line[:, 1], color='#ff4444', lw=3, zorder=4,
            solid_capstyle='round')
    ax.annotate('SF', (px, py), fontsize=10, fontweight='bold',
                color='#ff4444', ha='center', va='center',
                xytext=(px + sx * hw * 2.2, py + sy * hw * 2.2),
                zorder=5)

    # numera as curvas principais (mudanças de heading > 30°)
    kappas = np.abs(np.unwrap(heading))
    dh = np.diff(np.concatenate([heading, [heading[0]]]))
    dh = (dh + math.pi) % (2 * math.pi) - math.pi
    cum = np.cumsum(np.abs(dh))
    curve_idx = []
    last_s = -100
    for i in range(n):
        total = cum[i] - cum[i - 1] if i > 0 else cum[0]
        if abs(dh[i]) > 0.15 and i - last_s > 30:
            curve_idx.append(i)
            last_s = i
    for k, idx in enumerate(curve_idx[:20], start=1):
        ax.annotate(str(k), (wps[idx, 0], wps[idx, 1]), fontsize=8,
                    color='#00d4ff', ha='center', va='center',
                    fontweight='bold', zorder=5,
                    bbox=dict(boxstyle='circle,pad=0.15', fc='#16213e',
                              ec='#00d4ff', lw=0.5, alpha=0.8))

    # informações
    length_m = float(np.sum(seg_len))
    n_curves = len(curve_idx)
    ax.set_title(f"{track.name} — {n} waypoints, {length_m:.0f} m, "
                 f"{n_curves} curvas detectadas",
                 color='white', fontsize=13, fontweight='bold', pad=12)
    ax.text(0.02, 0.02,
            f'SF = wp {sf}  |  ── linha central  |  ── branco: bordas  |'
            f'  ● azul: curvas numeradas',
            transform=ax.transAxes, fontsize=8, color='#aaaacc',
            va='bottom')

    ax.set_aspect('equal')
    ax.tick_params(colors='#666699')
    for spine in ax.spines.values():
        spine.set_color('#333355')
    ax.grid(True, color='#222244', lw=0.3, alpha=0.5)
    plt.tight_layout()

    if save_path:
        fig.savefig(str(save_path), dpi=150, facecolor=fig.get_facecolor(),
                    bbox_inches='tight')
        print(f"[draw] salvo: {save_path}")
    if show:
        plt.show()
    plt.close(fig)


# ─────────────────────────────────────────────────────────────── desenho ASCII
def ascii_draw(track, width=100, height=28):
    """Desenha a pista como ASCII art no terminal."""
    wps = track.waypoints
    xs = [w[0] for w in wps]
    ys = [w[1] for w in wps]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    span_x = (x_max - x_min) or 1.0
    span_y = (y_max - y_min) or 1.0

    grid = [[' '] * width for _ in range(height)]
    sf = track.start_finish_waypoint

    hw = getattr(track, 'width_m', 12.0) / 2.0
    for i in range(len(wps)):
        x0, y0 = wps[i]
        x1, y1 = wps[(i + 1) % len(wps)]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        for side_sign in (-1, 0, +1):
            px = x0 + nx * hw * side_sign
            py = y0 + ny * hw * side_sign
            cx = int((px - x_min) / span_x * (width - 1))
            cy = int((y_max - py) / span_y * (height - 1))
            cx = max(0, min(width - 1, cx))
            cy = max(0, min(height - 1, cy))
            ch = '█' if side_sign == 0 else '░'
            if grid[cy][cx] == ' ':
                grid[cy][cx] = ch

    sx, sy = wps[sf]
    cx = int((sx - x_min) / span_x * (width - 1))
    cy = int((y_max - sy) / span_y * (height - 1))
    grid[max(0, cy - 1)][max(0, cx - 1)] = 'S'
    grid[min(height - 1, cy + 1)][min(width - 1, cx + 1)] = 'F'

    print()
    print(f"  {track.name} — {len(wps)} waypoints, SF no wp {sf}")
    print()
    for row in grid:
        print('  ' + ''.join(row))
    print()
    print(f"  █ = linha central  ░ = borda do asfalto  S/F = largada/chegada")
    print()


# ────────────────────────────────────────────────────────────────────── main
def main():
    ap = argparse.ArgumentParser(description="Desenha uma pista (matplotlib ou ASCII)")
    ap.add_argument('--track', type=str, default='interlagos',
                    help='nome da pista (FastF1: interlagos, Monza, Monaco, ...)')
    ap.add_argument('--csv', type=str, default=None,
                    help='CSV com colunas X,Y (alternativa ao FastF1)')
    ap.add_argument('--year', type=int, default=2024)
    ap.add_argument('--save', type=str, default=None,
                    help='salva em PNG (ex: --save pista.png) em vez de abrir janela')
    ap.add_argument('--ascii', action='store_true',
                    help='desenho ASCII no terminal (sem gráfico)')
    args = ap.parse_args()

    track = load_track(name=args.track, csv_path=args.csv, year=args.year)
    if args.ascii:
        ascii_draw(track)
    else:
        plot_track(track, save_path=args.save, show=(args.save is None))


if __name__ == '__main__':
    main()
