"""R3 V2 — avaliação do GATE MULTI-REALIZAÇÃO (pré-registrado 12:54:27Z).

Lê os CSVs do B3.1-v3 (seeds 0-2) + os logs de saída (paradas) e produz a
tabela por seed + medianas vs critérios do gate.

    python scripts/gate_multi_seed.py race_diag_b31_v3_seed0.log race_diag_b31_v3_seed1.log ...  # opcional p/ paradas
    python scripts/gate_multi_seed.py  # padrão: seeds 0,1,2 do v3
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
SF_S = 2655.0     # frozen v2 SF729 -> s=2655 m
TRACK_LEN = 4160.4

def laps_and_pace(df):
    """Voltas por cruzamento de SF + tempo mediano de volta por corrida."""
    times = []
    cars_with_lap = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        s, t = g.s.values, g.t_s.values
        ds = np.diff(s)
        idx = np.where((s[:-1] < SF_S) & (s[1:] >= SF_S) & (ds > 0) & (ds < 100))[0]
        ts = t[idx + 1]
        if len(ts) >= 1:
            cars_with_lap += 1
        if len(ts) >= 2:
            times.extend(np.diff(ts).tolist())
    return cars_with_lap, (float(np.median(times)) if times else None)

def preso_decomposition(df):
    """Réplica do critério do runner (janelas 30 s): ticks pilotagem/preso + carros."""
    tot_pilot = tot_preso = 0
    preso_cars = []
    t_end = float(df.t_s.max())
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        t = g.t_s.values; lat = g.lat.abs().values
        cum = g.cum_dist.values; offm = g.offtrack.values
        car_preso = 0
        for w0 in np.arange(0.0, t_end, 30.0):
            m = (t >= w0) & (t < w0 + 30.0)
            if not m.any() or not offm[m].any():
                continue
            if (lat[m].max() > 20.0) or ((cum[m].max() - cum[m].min()) < 5.0):
                car_preso += int(offm[m].sum())
            else:
                tot_pilot += int(offm[m].sum())
        if car_preso:
            preso_cars.append(drv)
            tot_preso += car_preso
    return tot_pilot, tot_preso, preso_cars

def hesitations(df):
    n = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        m = g.t_s.values > 20.0
        v, t = g.speed.values[m], g.t_s.values[m]
        i = 0
        while i < len(v):
            if v[i] < 0.5:
                j = i
                while j < len(v) and v[j] < 0.5:
                    j += 1
                dur = (t[min(j, len(t) - 1)] - t[i]) if j > i else 0.0
                if 0.3 <= dur < 3.0:
                    n += 1
                i = j
            else:
                i += 1
    return n

def stops_3s(log_path):
    txt = Path(log_path).read_text()
    if "nenhuma parada >= 3 s" in txt:
        return 0
    import re
    m = re.search(r"TOTAL: (\d+) paradas", txt)
    return int(m.group(1)) if m else -1

def main():
    rows = []
    for seed in (0, 1, 2):
        f = BACKEND / f"race_diag_b31_v3_seed{seed}.csv"
        log = BACKEND / f"race_diag_b31_v3_seed{seed}.log"
        df = pd.read_csv(f)
        cc = df[df.car_car > 0]
        cars_lap, pace = laps_and_pace(df)
        pilot, preso, preso_cars = preso_decomposition(df)
        hesit = hesitations(df)
        stop = stops_3s(log) if log.exists() else None
        rows.append(dict(seed=seed, cc=len(cc),
                         pos60=int((cc.t_s > 60).sum()),
                         off_pct=100 * df.offtrack.mean(),
                         pilot=pilot, preso=preso,
                         preso_cars=len(preso_cars),
                         cars_lap=cars_lap, pace=pace,
                         hesit=hesit, stop=stop))
    t = pd.DataFrame(rows)
    print("=== B3.1-v3 POR SEED (gate: TODO-seed + mediana) ===")
    print(t.round(1).to_string(index=False))
    print("\n=== MEDIANAS vs GATE (pré-registrado 2026-10-17T12:54:27Z) ===")
    med = dict(contatos=t.cc.median(), pos_largada=t.pos60.median(),
               fora_pilotagem_pct=t.pilot.median() / (len(pd.read_csv(BACKEND / 'race_diag_b31_v3_seed0.csv')) / 100),
               voltas=t.cars_lap.median(), rolante=t.pace.median())
    ok = dict(contatos=med['contatos'] < 1576, pos=med['pos_largada'] <= 100,
              fora=med['fora_pilotagem_pct'] <= 1.5, voltas=med['voltas'] >= 10,
              rolante=med['rolante'] <= 115.0)
    print(f"contatos   mediana {med['contatos']:7.0f}  < 1576    {'PASS' if ok['contatos'] else 'FAIL'}")
    print(f"pós-largada mediana {med['pos_largada']:6.0f}  <= 100     {'PASS' if ok['pos'] else 'FAIL'}")
    print(f"fora-pilot. mediana {med['fora_pilotagem_pct']:6.2f}%  <= 1,5%    {'PASS' if ok['fora'] else 'FAIL'}")
    print(f"voltas     mediana {med['voltas']:7.0f}  >= 10      {'PASS' if ok['voltas'] else 'FAIL'}")
    print(f"rolante    mediana {med['rolante']:7.1f}s  <= 115s    {'PASS' if ok['rolante'] else 'FAIL'}")
    allseed = dict(presos=(t.preso_cars == 0).all(),
                   stops=(t.stop == 0).all() if t.stop.notna().all() else None,
                   hesit=(t.hesit <= 3).all())
    print(f"\nTODO-SEED: carros-preso=0 em todas: {'PASS' if allseed['presos'] else 'FAIL'}"
          f" | paradas>=3s=0: {'PASS' if allseed['stops'] else ('?' if allseed['stops'] is None else 'FAIL')}"
          f" | hesit<=3: {'PASS' if allseed['hesit'] else 'FAIL'}")
    verde = all(ok.values()) and all(v is True for v in allseed.values())
    print(f"\n=== GATE: {'VERDE — promoção EM VIGOR' if verde else 'VERMELHO — árvore: diagnóstico dirigido + PARE'} ===")

if __name__ == '__main__':
    main()
