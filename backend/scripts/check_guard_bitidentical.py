"""R5a 1.3 — GUARDA de determinismo: o instrumento NÃO pode contaminar a física.

Compara o CSV novo (com coletor ligado) contra o run de referência da R4:
todas as colunas ORIGINAIS, todas as linhas, BIT-IDÊNTICAS (string a string
após normalizar floats). O cabeçalho de versão e as colunas novas de impulso
não contam.

    python scripts/check_guard_bitidentical.py <ref.csv> <new.csv>
"""
import sys
import pandas as pd
import numpy as np


def main(ref_path, new_path):
    ref = pd.read_csv(ref_path, comment='#')
    new = pd.read_csv(new_path, comment='#')
    assert len(ref) == len(new), f"linhas: {len(ref)} vs {len(new)}"
    assert list(ref.columns) == [c for c in new.columns if c in ref.columns] or \
           set(ref.columns).issubset(set(new.columns)), "colunas originais sumiram"

    n_diff = 0
    report = []
    for col in ref.columns:
        a, b = ref[col], new[col]
        if pd.api.types.is_numeric_dtype(a):
            eq = (a.values == b.values) | (np.isnan(a.values) & np.isnan(b.values))
        else:
            eq = (a.astype(str).values == b.astype(str).values)
        if not eq.all():
            n_diff += int((~eq).sum())
            idx = np.where(~eq)[0][:3]
            report.append(f"  {col}: {int((~eq).sum())} diferenças — ex {[(int(i), a.iloc[i], b.iloc[i]) for i in idx]}")
    if n_diff == 0:
        print(f"GUARDA PASS: {len(ref)} linhas × {len(ref.columns)} colunas BIT-IDÊNTICAS")
        print("  (instrumento de contato não contamina a física)")
    else:
        print(f"GUARDA FAIL: {n_diff} valores divergem — BUG do instrumento:")
        print('\n'.join(report))
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
