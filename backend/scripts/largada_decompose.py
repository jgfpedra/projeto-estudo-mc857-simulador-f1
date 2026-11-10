"""LARGADA-1 0-c — DECOMPOSIÇÃO dos pares de contato da janela de largada (zero corridas).

Read-only sobre o corpus cego 0-19 (mesmos loaders/âncoras do
largada_anatomy.py, prereg 071bc37). Regiões pelo s do drv_a no tick do par
(tick par mais próximo ≤ tick do evento — CSV amostra a 5 Hz):
  GRID s ≤ 2656 | ENTRADA-S (2656, 2950] | PÓS-S > 2950

Saídas (âncoras, convenção 120081e — commitadas):
  experiments/largada_decomp_pares_s0_19.csv   (1 linha por par-distinto em W)
  experiments/largada_decomp_resumo_s0_19.csv  (por run + âncoras hist de cc)

ÁRVORE (avaliada aqui; pinada no prereg LARGADA-1): ENTRADA-S = pluralidade
ESTRITA dos pares em W -> ramo L-1a CAP; senão (GRID domina ou empate) ->
PARE-report (mudança de grid = era do dono; NADA roda).

    .venv/bin/python scripts/largada_decompose.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))
from lever_gate_verdict import stats
from largada_anatomy import BLIND, W, header_info, first_excursion, events_of

SF = 2656.0
S_CUT = 2950.0
ADVERSE = {2, 8, 9, 10, 12, 13, 14}   # 0-9: E5 {2,8,9}; 10-19: R13 {10,12,13,14}


def region(s):
    if s <= SF:
        return "GRID"
    if s <= S_CUT:
        return "ENTRADA-S"
    return "POS-S"


def fileira(pos):
    return (pos + 1) // 2


def main():
    pair_rows = []
    for s in range(20):
        path = BLIND[s]
        df = pd.read_csv(path, comment='#')
        ev = events_of(path)
        order, compounds = header_info(path)
        pos_of = {d: i + 1 for i, d in enumerate(order)}
        s_of = df.set_index(['tick', 'drv']).s
        vmean = df.groupby('tick').speed.mean()
        seen = set()
        for r in ev[ev.t <= W].itertuples():
            key = tuple(sorted((r.drv_a, r.drv_b)))
            if key in seen:
                continue
            seen.add(key)
            tk = (int(getattr(r, "sub")) // 24 // 2) * 2   # tick par ≤ evento (5 Hz)
            try:
                s_at = float(s_of.loc[(tk, r.drv_a)])
            except Exception:
                s_at = float('nan')
            pair_rows.append(dict(
                seed=s, drv_a=key[0], drv_b=key[1], t=round(float(r.t), 1),
                s=round(s_at, 1), regiao=region(s_at),
                fileira_a=fileira(pos_of.get(key[0], 0)),
                fileira_b=fileira(pos_of.get(key[1], 0)),
                comp_a=compounds.get(key[0], '?'), comp_b=compounds.get(key[1], '?'),
                mesma_fileira=fileira(pos_of.get(key[0], 0)) == fileira(pos_of.get(key[1], 0)),
                v_campo=round(float(vmean.get(tk, np.nan)), 1)))
    P = pd.DataFrame(pair_rows)
    out_p = BACKEND / "experiments" / "largada_decomp_pares_s0_19.csv"
    P.to_csv(out_p, index=False)

    run_rows = []
    for s in range(20):
        path = BLIND[s]
        df = pd.read_csv(path, comment='#')
        ev = events_of(path)
        order, compounds = header_info(path)
        pos_of = {d: i + 1 for i, d in enumerate(order)}
        s_of = df.set_index(['tick', 'drv']).s
        fx = first_excursion(df)
        sub = P[P.seed == s]
        adj = dict(par=None, regiao=None, mesma_fileira=None, comp=None, t=None, s=None)
        if ev is not None and fx:
            evd = ev[(ev.drv_a == fx[0]) | (ev.drv_b == fx[0])].copy()
            if len(evd):
                evd["dt"] = (evd.t - fx[1]).abs()
                r0 = evd.sort_values("dt").iloc[0]
                if r0["dt"] <= 2.0:
                    other = r0.drv_b if r0.drv_a == fx[0] else r0.drv_a
                    try:
                        s_at = float(s_of.loc[((int(r0["sub"]) // 24 // 2) * 2, r0.drv_a)])
                    except Exception:
                        s_at = float('nan')
                    adj = dict(par=f"{fx[0]}-{other}", regiao=region(s_at),
                               mesma_fileira=fileira(pos_of.get(fx[0], 0)) == fileira(pos_of.get(other, 0)),
                               comp=f"{compounds.get(fx[0], '?')}/{compounds.get(other, '?')}",
                               t=round(float(r0.t), 1), s=round(s_at, 1))
        st = stats(path)
        run_rows.append(dict(
            seed=s, clima="DAMP" if s in ADVERSE else "SECA",
            n_grid=int((sub.regiao == "GRID").sum()),
            n_entrada=int((sub.regiao == "ENTRADA-S").sum()),
            n_pos=int((sub.regiao == "POS-S").sum()),
            n_total=len(sub),
            exc_drv=fx[0] if fx else None,
            exc_grid_pos=pos_of.get(fx[0], None) if fx else None,
            adj_par=adj["par"], adj_regiao=adj["regiao"],
            adj_mesma_fileira=adj["mesma_fileira"], adj_comp=adj["comp"],
            cc_total=int(df.car_car.sum()),
            taxa=st["taxa"], rol=st["rol"], off=st["off"]))
    R = pd.DataFrame(run_rows)
    out_r = BACKEND / "experiments" / "largada_decomp_resumo_s0_19.csv"
    R.to_csv(out_r, index=False)

    print("=== 0-c DECOMPOSIÇÃO pares_W (20 runs cegos 0-19) ===")
    cnt = P.regiao.value_counts()
    print(f"\npares por REGIÃO (pooled): {dict(cnt)} | total {len(P)}")
    print("por run (GRID | ENTRADA-S | PÓS-S):")
    for r in run_rows:
        print(f"  s{r['seed']:>2} [{r['clima']}]: {r['n_grid']:>2} | {r['n_entrada']:>2} | {r['n_pos']:>2}"
              f" | exc {r['exc_drv']} P{r['exc_grid_pos']} | adj {r['adj_par']}@{r['adj_regiao']}"
              f"{' (mesma fileira)' if r['adj_mesma_fileira'] else ''} {r['adj_comp']}")
    same = P.mesma_fileira.mean()
    print(f"\npares da MESMA fileira do grid: {int(P.mesma_fileira.sum())}/{len(P)} ({100*same:.0f}%)")
    adj_reg = [r['adj_regiao'] for r in run_rows if r['adj_regiao']]
    print(f"pares ADJACENTES à 1ª excursão por região: "
          f"{ {k: adj_reg.count(k) for k in ('GRID','ENTRADA-S','POS-S')} }")
    print(f"posição no grid do driver da 1ª exc: {dict(R.exc_grid_pos.value_counts())}")
    print(f"cc_total hist por classe: SECA med {R[R.clima=='SECA'].cc_total.median():.0f} "
          f"(n={int((R.clima=='SECA').sum())}) | DAMP med {R[R.clima=='DAMP'].cc_total.median():.0f} "
          f"(n={int((R.clima=='DAMP').sum())})")
    dom = cnt.idxmax()
    entrada_dominante = cnt.get("ENTRADA-S", 0) == cnt.max() and \
        (cnt.get("ENTRADA-S", 0) > cnt.get("GRID", 0))
    print(f"\n=== ÁRVORE: {'ENTRADA-S DOMINANTE -> ramo L-1a CAP' if entrada_dominante else 'GRID/empate domina -> PARE-report (grid = era do dono)'} ===")
    print(f"-> {out_p}\n-> {out_r}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
