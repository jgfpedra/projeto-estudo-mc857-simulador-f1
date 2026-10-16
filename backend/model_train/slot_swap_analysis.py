"""A1 (FASE 5 v14) — hipótese SLOT-SWAP: a obs 'traffic' ordena os 3 mais
próximos por |dist_s| a cada tick; em corrida densa esse ranking permuta
rápido (carros trocando de slot), e o ator v14 nunca viu essa dinâmica no
treino (fantasmas-professores mantêm gaps estáveis). Este módulo mede a taxa
de permutações do ranking nos contatos vs baseline, do CSV do race_diagnostic.

Métrica por carro e tick (amostrado a 5 Hz):
  n_swaps = nº de posições do top-3 ordenado que mudaram de carro vs tick
  anterior (entradas/saídas contam como permutação).
  taxa/s = n_swaps por transição × 5.
Janela de contato: ±window_s ao redor de qualquer tick com car_car > 0.

Uso:
  .venv/bin/python model_train/slot_swap_analysis.py --csv race_diag_v14_all.csv \
      --track-len 4309.0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
for p in (str(PROJECT_ROOT), str(MODEL_DIR.parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd


def signed_dist(s_o, s_ego, L):
    return ((np.asarray(s_o) - s_ego + 0.5 * L) % L) - 0.5 * L


def slot_swaps_from_trace(df: pd.DataFrame, track_len: float,
                          top_k: int = 3) -> pd.DataFrame:
    """Reconstrói por carro o ranking top_k por |dist_s| e conta permutações
    entre ticks consecutivos. Retorna df[(drv, tick)] com n_swaps, in_contact,
    near_contact (janela é aplicada depois). Ticks devem estar a 5 Hz."""
    ticks = np.sort(df.tick.unique())
    piv = df.pivot_table(index='tick', columns='drv', values='s')
    contacts = df[df.car_car > 0].groupby('drv').tick.apply(set).to_dict()
    rows = []
    L = float(track_len)
    for drv in piv.columns:
        prev_rank = None
        for t in ticks:
            s_row = piv.loc[t]
            s_ego = s_row[drv]
            others = [d for d in piv.columns if d != drv and not np.isnan(s_row[d])]
            if len(others) < top_k:
                prev_rank = None
                continue
            d = np.abs(signed_dist([s_row[o] for o in others], s_ego, L))
            order = np.argsort(d, kind='stable')[:top_k]
            rank = tuple(others[i] for i in order)
            n_swaps = 0 if prev_rank is None else sum(
                1 for a, b in zip(rank, prev_rank) if a != b)
            rows.append(dict(drv=drv, tick=t, n_swaps=n_swaps,
                             in_contact=int(t in contacts.get(drv, ()))))
            prev_rank = rank
    out = pd.DataFrame(rows)
    return out


def summarize_swaps(sw: pd.DataFrame, window_ticks: int = 25) -> dict:
    """Taxa média (swaps/s) no baseline vs janela de contato (±window_ticks).
    5 Hz: window_ticks=25 → ±5 s."""
    sw = sw.sort_values(['drv', 'tick']).copy()
    # janela ±window de qualquer contato do PRÓPRIO carro
    sw['near_contact'] = 0
    for drv, g in sw.groupby('drv'):
        ct = g.tick[g.in_contact == 1].values
        if len(ct) == 0:
            continue
        idx = sw.index[sw.drv == drv]
        ticks = sw.loc[idx, 'tick'].values
        near = np.zeros(len(ticks), dtype=bool)
        for c in ct:
            near |= (ticks >= c - window_ticks) & (ticks <= c + window_ticks)
        sw.loc[idx, 'near_contact'] = near.astype(int)
    base = sw[sw.near_contact == 0]
    near = sw[sw.near_contact == 1]
    rate = lambda g: 5.0 * g.n_swaps.mean()   # swaps por segundo
    # correlação ponto-bisserial in_contact-janela × n_swaps
    x = sw.near_contact.values.astype(float)
    y = sw.n_swaps.values.astype(float)
    r = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0
    return dict(n_transitions=len(sw),
                rate_base_per_s=rate(base) if len(base) else None,
                rate_near_contact_per_s=rate(near) if len(near) else None,
                ratio=(rate(near) / rate(base)) if len(base) and len(near) and rate(base) > 0 else None,
                point_bisserial=r,
                n_near=len(near), n_base=len(base))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--track-len', type=float, default=4309.0)
    ap.add_argument('--window-s', type=float, default=5.0)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    sw = slot_swaps_from_trace(df, args.track_len)
    res = summarize_swaps(sw, window_ticks=int(args.window_s * 5))
    print(f"[slot-swap] {args.csv} | transições: {res['n_transitions']}")
    print(f"  taxa BASE        : {res['rate_base_per_s']:.3f} swaps/s "
          f"(n={res['n_base']})")
    if res['rate_near_contact_per_s'] is not None:
        print(f"  taxa NOS CONTATOS: {res['rate_near_contact_per_s']:.3f} swaps/s "
              f"(n={res['n_near']}, janela ±{args.window_s:.0f}s)")
    if res['ratio'] is not None:
        print(f"  razão contato/base: {res['ratio']:.2f}× | "
              f"correlação ponto-bisserial: {res['point_bisserial']:.3f}")
        verdict = ("SIM — o ranking permuta mais rápido nos contatos; o swap de "
                   "slots é um candidato a driver da divergência eval↔corrida "
                   "(nota de design v15: histerese de slots)"
                   if res['ratio'] >= 1.5 else
                   "NÃO/FRACO — a taxa perto de contatos não difere o bastante "
                   "do baseline para explicar a divergência sozinha")
        print(f"  VEREDITO: {verdict}")


if __name__ == '__main__':
    main()
