"""PROF-MONACO-1 — PASSO 0 reconciliações (probe commitado ANTES do uso).

Errata-SAIDAS-1-review (2026-10-22) prescreve:
  R5-a: IQR-B de C07 — original 24,2 vs republicado 23,6. Reconciliar contra
        o CSV (aqui: RECOMPUTADO do eventos_saidas_detalhados.csv BRUTO).
  R5-b: Reta-B solo — original 16/20=80% vs errata 11/20=55%. Idem, do raw.
  NIT-3: confirmar a rotulagem "C10 (Senna S)" contra o catálogo de curvas
        do CÓDIGO (build_corner_definitions do saidas_verdict) vs o sítio
        da Senna S da anatomia LARGADA-F0 (s 2699,7-2814,0 m).
  NIT-2: divulgar se a re-execução do veredito regenera as tabelas
        BYTE-IDÊNTICAS (re-run + diff por arquivo contra experiments/saidas-1).

  .venv/bin/python scripts/prof_monaco_p0.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import saidas_verdict as SV  # noqa: E402

EV = Path('experiments/saidas-1/eventos_saidas_detalhados.csv')
COMM = Path('experiments/saidas-1')
A = 'experiments/f4v15-wiring/1_controle.csv'
B = 'experiments/f4v15-wiring/2_allcomposite.csv'


def main():
    print("=== PROF-MONACO-1 P0: reconciliações R5-a/R5-b + NITs (read-only) ===")
    ev = pd.read_csv(EV)
    # ---- R5-a: IQR-B de C07 recomputado do raw ----
    c07b = ev[(ev.corner_id == 'C07') & (ev.perfil.str.startswith('B'))]
    q1, q3 = c07b.v_1s_kmh.quantile([0.25, 0.75])
    iqr = float(q3 - q1)
    print(f"[R5-a] C07-B IQR(raw, n={len(c07b)}) = {iqr:.4f} -> exibição 1 casa: {iqr:.1f}")
    print(f"       original display 24,2 | republicado 23,6 -> CANÔNICO = {iqr:.1f} "
          f"({'republicado CONFIRMA' if abs(iqr - 23.6) < 0.05 else 'DIVERGE — investigar'})")
    c07a = ev[(ev.corner_id == 'C07') & (ev.perfil.str.startswith('A'))]
    qa1, qa3 = c07a.v_1s_kmh.quantile([0.25, 0.75])
    print(f"       C07-A IQR(raw) = {qa3 - qa1:.4f} (referência A: 22,0-22,1)")
    # ---- R5-b: Reta-B solo recomputado do raw ----
    reta_b = ev[(ev.corner_id == 'Reta') & (ev.perfil.str.startswith('B'))]
    n_solo = int(reta_b.is_solo_15.sum())
    pct = 100.0 * n_solo / max(len(reta_b), 1)
    print(f"[R5-b] Reta-B solo(raw) = {n_solo}/{len(reta_b)} = {pct:.1f}%")
    print(f"       original 16/20=80% | errata 11/20=55% -> CANÔNICO = {n_solo}/{len(reta_b)} "
          f"({'errata CONFIRMA' if (n_solo, len(reta_b)) == (11, 20) else 'DIVERGE — investigar'})")
    # ---- NIT-3: C10 vs sítio Senna S (catálogo do código) ----
    wps, diff, seg, seg_cum, total, seg_head = SV.load_track_geometry()
    corners = SV.build_corner_definitions(wps)
    c10 = [c for c in corners if c['id'] == 'C10'][0]
    lo, hi = c10['s0'] - 30.0, c10['s1'] + 30.0   # margem do match_corner
    ok = lo <= 2700.0 and hi >= 2814.0
    print(f"[NIT-3] C10 = '{c10['name']}' s∈[{c10['s0']:.1f},{c10['s1']:.1f}] "
          f"κmax={c10['kmax']:.4f} | com margem 30 m: [{lo:.1f},{hi:.1f}]")
    print(f"       sítio Senna S da LARGADA-F0 = s 2699,7-2814,0 -> rótulo "
          f"{'CONFIRMADO' if ok else 'NÃO CONFIRMA'} contra o catálogo do código")
    # ---- NIT-2/golden: re-execução + diff byte a byte ----
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(
            [sys.executable, str(Path('scripts/saidas_verdict.py')), A, B,
             '--out-dir', td], capture_output=True, text=True)
        print(f"[NIT-2] re-execução do veredito nas F4v15: exit={r.returncode}")
        for f in sorted(COMM.glob('*.csv')):
            new = Path(td) / f.name
            if not new.exists():
                print(f"       {f.name}: AUSENTE na re-execução")
                continue
            if new.read_bytes() == f.read_bytes():
                print(f"       {f.name}: BYTE-IDÊNTICA")
            else:
                old_l = [x for x in f.read_text().splitlines() if not x.startswith('#')]
                new_l = [x for x in new.read_text().splitlines() if not x.startswith('#')]
                print(f"       {f.name}: {'DADOS idênticos (só comentários divergem)' if old_l == new_l else 'DADOS DIVERGEM'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
