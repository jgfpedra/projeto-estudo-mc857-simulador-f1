"""CICLO LARGADA 0 — ANATOMIA OFFLINE da largada (ZERO corridas).

Prereg: PREREG_LARGADA_0.md (commit 071bc37, ANTES deste script).
Corpus: braços CEGOS 0-19 (r10_blind_s0-9 + r13_b_s10-19) — 20 runs.
Anexo CONTAMINADO (insumo de design, NUNCA evidência): alv_gap_s20-29 +
smoke_gap_s0 (instrumento contaminado pré-reparo, 11 runs).

SELF-checks (divergência → PARE, instrumento de análise regrediu):
  (i) 10 taxas da década 10-19 == [0,306;0,328;0,317;0,441;0,333;0,406;
      0,267;0,310;0,300;0,350] e mediana == 0,323;
  (ii) década 0-9 == recontagem_cego_s0_9.csv (120081e) campo a campo;
  (iii) 1ª excursão de r10_blind_s0 == ('RUS', 4,2, 2702,685).
Veredito: P-A >=14/20 em W | P-B >=12/20 em s∈[2650,2950] (emendado; a
região literal [550,850] é reportada) | P-C mediana share_largada >= 0,20
(FAIL = PARE — premissa do dossiê cai).

    .venv/bin/python scripts/largada_anatomy.py
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))
from lever_gate_verdict import stats  # instrumento canônico dos gates

CORPUS = BACKEND / "experiments"
W = 60.0
L_TRACK = 4160.4                    # polígono frozen (contrato de instrumento)
REGION = (2650.0, 2950.0)           # P-B EMENDADO (prereg §4)
REGION_LITERAL = (550.0, 850.0)    # região literal do prompt (report-only)
TAXAS_10_19 = [0.306, 0.328, 0.317, 0.441, 0.333, 0.406, 0.267, 0.310, 0.300, 0.350]
FIRST_EXC_S0 = ("RUS", 4.2, 2702.685)

BLIND = {s: CORPUS / "diag-r2-r13" / f"race_diag_r10_blind_s{s}.csv" for s in range(10)}
BLIND.update({s: CORPUS / "diag-r2-r13" / f"race_diag_r13_b_s{s}.csv" for s in range(10, 20)})
CONTAM = {s: CORPUS / "diag-alv-seco" / f"race_diag_alv_gap_s{s}.csv" for s in range(20, 30)}
CONTAM["s0smoke"] = CORPUS / "diag-alv-seco" / "race_diag_alv_smoke_gap_s0.csv"


def header_info(path):
    head = open(path).readline()
    grid = re.search(r"grid_order=\[(.*?)\]", head)
    comp = re.search(r"compounds=\{(.*?)\}", head)
    order = re.findall(r"'(\w+)'", grid.group(1)) if grid else []
    compounds = dict(re.findall(r"'(\w+)':\s*'(\w+)'", comp.group(1))) if comp else {}
    return order, compounds


def first_excursion(df):
    """1ª linha (por t_s) com offtrack=1 — coluna/critério dos gates (prereg §2)."""
    o = df[df.offtrack == 1]
    if not len(o):
        return None
    r = o.sort_values("t_s").iloc[0]
    return (r.drv, round(float(r.t_s), 1), round(float(r.s), 3))


def events_of(path):
    ep = Path(str(path).replace(".csv", "_events.csv"))
    if not ep.exists():
        return None
    ev = pd.read_csv(ep, comment='#')
    ev["t"] = (ev["sub"] // 24) * 0.1   # coluna 'sub' (ev.sub seria o método pandas)
    return ev


def anatomy(path, seed, decade):
    df = pd.read_csv(path, comment='#')
    ev = events_of(path)
    fx = first_excursion(df)
    off = df[df.offtrack == 1]
    off_w = off[off.t_s <= W]
    share = len(off_w) / len(off) if len(off) else 0.0
    pairs, firsts = set(), []
    if ev is not None:
        sticks = df.set_index(['tick', 'drv']).s
        for r in ev[ev.t <= W].itertuples():
            key = tuple(sorted((r.drv_a, r.drv_b)))
            if key in pairs:
                continue
            pairs.add(key)
            try:
                # CSV amostra só ticks pares (5 Hz): olha o par mais próximo ≤ tick
                tk = (int(r.sub // 24) // 2) * 2
                s_at = round(float(sticks.loc[(tk, r.drv_a)]), 1)
            except Exception:
                s_at = None
            firsts.append((key, round(float(r.t), 1), s_at))
    vs = {}
    for tt in (2.0, 4.0, 8.0, 15.0):
        vs[tt] = round(float(df[df.t_s == tt].speed.mean()), 1)
    g = df[df.t_s == 10.0]
    gap10 = None
    if len(g) == 10:
        ss = g.s.values
        gaps = []
        for x in ss:
            d = (ss - x) % L_TRACK
            d = d[d > 0]
            gaps.append(float(d.min()) if len(d) else np.nan)
        gap10 = round(float(np.nanmean(gaps)), 1)
    tax = "PILOTAGEM"
    if ev is not None and fx is not None:
        evd = ev[(ev.drv_a == fx[0]) | (ev.drv_b == fx[0])]
        if len(evd):
            dt = (evd.t - fx[1]).abs()
            tax = "CONTATO-ADJ" if dt.min() <= 2.0 else ("OUTRO" if dt.min() <= 10.0 else "PILOTAGEM")
    order, compounds = header_info(path)
    fileiras = []
    for i in range(0, 10, 2):
        d1, d2 = order[i], order[i + 1]
        fileiras.append(f"{d1}:{compounds.get(d1, '?')}+{d2}:{compounds.get(d2, '?')}")
    return dict(seed=seed, decada=decade,
                exc_drv=fx[0] if fx else None, exc_t=fx[1] if fx else None,
                exc_s=fx[2] if fx else None,
                in_W=bool(fx and fx[1] <= W),
                in_curva=bool(fx and REGION[0] <= fx[2] <= REGION[1]),
                in_literal=bool(fx and REGION_LITERAL[0] <= fx[2] <= REGION_LITERAL[1]),
                n_pares_W=len(pairs),
                pares_W="; ".join(f"{a}-{b}@{t}s(s={s})" for (a, b), t, s in firsts[:6]),
                v_t2=vs[2.0], v_t4=vs[4.0], v_t8=vs[8.0], v_t15=vs[15.0],
                gap10=gap10, share_largada=round(share, 3), taxonomia=tax,
                fileiras=" | ".join(fileiras))


def self_checks():
    ok = {}
    taxas = [stats(BLIND[s])['taxa'] for s in range(10, 20)]
    ok['(i) 10 taxas 10-19 + mediana 0,323'] = (
        [round(t, 3) for t in taxas] == TAXAS_10_19
        and round(float(np.median(taxas)), 3) == 0.323)
    R = pd.read_csv(CORPUS / "diag-alv-adverso" / "recontagem_cego_s0_9.csv").set_index('seed')
    diffs = []
    for s in range(10):
        st = stats(BLIND[s])
        for k in ('exc', 'reent', 'perigosas', 'taxa', 'off', 'rol', 'n_comp', 'par', 'wand'):
            if float(st[k]) != float(R.loc[s, k]):
                diffs.append((s, k, st[k], R.loc[s, k]))
    ok['(ii) década 0-9 == recontagem_cego_s0_9.csv'] = not diffs
    if diffs:
        print(f"  diffs (ii): {diffs[:8]}")
    fx0 = first_excursion(pd.read_csv(BLIND[0], comment='#'))
    ok['(iii) 1ª excursão s0 == RUS 4,2/2702,685'] = fx0 == FIRST_EXC_S0
    if fx0 != FIRST_EXC_S0:
        print(f"  (iii) medido: {fx0}")
    return ok


def main():
    print("=== LARGADA-0 — SELF-checks (instrumento de análise) ===")
    ok = self_checks()
    for k, v in ok.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    if not all(ok.values()):
        print("\nSELF-check FALHOU -> PARE (instrumento de análise regrediu)")
        return 1
    rows = [anatomy(BLIND[s], s, 0 if s < 10 else 1) for s in range(20)]
    T = pd.DataFrame(rows)
    out = CORPUS / "largada_anatomia_cego_s0_19.csv"
    T.to_csv(out, index=False)
    cols = ['seed', 'decada', 'exc_drv', 'exc_t', 'exc_s', 'in_W', 'in_curva',
            'taxonomia', 'n_pares_W', 'share_largada', 'v_t2', 'v_t4', 'v_t8',
            'v_t15', 'gap10']
    print("\n=== ANATOMIA POR RUN (braço cego 0-19) ===")
    print(T[cols].to_string(index=False))
    print(f"\nfileiras/compostos (exemplo s0): {T.fileiras.iloc[0]}")
    print(f"pares em W (exemplo s0): {T.pares_W.iloc[0]}")
    for dec, gdf in T.groupby('decada'):
        print(f"\n--- década {dec} ({'0-9' if dec == 0 else '10-19'}): share mediana "
              f"{gdf.share_largada.median():.3f} | in_W {int(gdf.in_W.sum())}/{len(gdf)} | "
              f"in_curva {int(gdf.in_curva.sum())}/{len(gdf)} | taxonomia {dict(gdf.taxonomia.value_counts())}")
    n_a, n_b = int(T.in_W.sum()), int(T.in_curva.sum())
    n_lit = int(T.in_literal.sum())
    med = float(T.share_largada.median())
    checks = {
        f'P-A >=14/20 1ª excursão em W': (n_a, n_a >= 14),
        f'P-B >=12/20 1ª excursão em s∈[2650,2950] (emendado)': (n_b, n_b >= 12),
        f'P-C mediana share_largada >= 0,20': (round(med, 3), med >= 0.20),
    }
    print(f"\n=== VEREDITO MECÂNICO ===")
    print(f"  [report] região literal do prompt [550,850]: {n_lit}/20")
    allp = True
    for k, (val, ok_) in checks.items():
        print(f"  {k}: {val} -> {'PASS' if ok_ else 'FAIL'}")
        allp &= ok_
    # ANEXO CONTAMINADO (insumo de design, NUNCA evidência)
    arows = []
    for k, p in sorted(CONTAM.items(), key=lambda x: str(x[0])):
        dfc = pd.read_csv(p, comment='#')
        fxc = first_excursion(dfc)
        arows.append(dict(run=k, rotulo="CONTAMINADO",
                          exc_drv=fxc[0] if fxc else None, exc_t=fxc[1] if fxc else None,
                          exc_s=fxc[2] if fxc else None,
                          off_pct=round(100 * float(dfc.offtrack.mean()), 1)))
    A = pd.DataFrame(arows)
    A.to_csv(CORPUS / "largada_anexo_CONTAMINADO.csv", index=False)
    print("\n=== ANEXO CONTAMINADO (30-39 pré-reparo + smoke; insumo de design) ===")
    print(A.to_string(index=False))
    print(f"\n-> {out}")
    print(f"-> {CORPUS / 'largada_anexo_CONTAMINADO.csv'}")
    if not allp:
        print("\n" + ("P-C FAIL: premissa 'maior fonte única' CAI -> PARE (re-prioritização com a revisão)"
                      if med < 0.20 else "P-A/P-B FAIL -> re-atribuição obrigatória no relatório (não PARE)"))
        return 0 if med >= 0.20 else 2
    print("\nLARGADA-0: P-A/P-B/P-C PASS — anatomia confirma a largada como fonte dominante; L-1 (pacing) proposal segue no relatório")
    return 0


if __name__ == '__main__':
    sys.exit(main())
