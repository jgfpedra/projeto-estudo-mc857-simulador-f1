"""VARIEDADE-1 — veredito MECÂNICO (commitado ANTES das corridas; PADRÃO-OURO
3ª aplicação — reusa o stats do sanidade1b_verdict, mesma aritmética).

Prereg b237aeb §3-§6:
  P1/P2 (flags-off s0) == âncoras F4v15 BIT-IDÊNTICAS (return 2 = PARE —
    vazamento de RNG no caminho compartilhado).
  D2 == D1 (mesma (seed,N) 2×): BIT-IDÊNTICO — comparação BYTE-A-BYTE das
    linhas de dados (excl. '#') + stats idênticas. FAIL = PARE
    (o determinismo é infraestrutura e não pode morrer).
  D3 (N=2): 1ª divergência vs base (P1) E vs D1 < tick 200 (derivação §2:
    detector de colisão de streams).
  D1-D4: 10/10 voltas E 0 paradas >=3 s (a variedade não quebra a corrida).
  Contatos das D: SEM teto (report).

  .venv/bin/python scripts/analysis/variedade_verdict.py --selftest
  .venv/bin/python scripts/analysis/variedade_verdict.py \
    experiments/variedade-1/1_prot_v0.csv experiments/variedade-1/2_prot_comp.csv \
    experiments/variedade-1/3_var1_v0.csv experiments/variedade-1/4_var1_v0_rep.csv \
    experiments/variedade-1/5_var2_v0.csv experiments/variedade-1/6_var1_comp.csv
"""

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanidade1b_verdict import (F4V15_C, F4V15_X, _prot_ok, selftest,
                                stats)


def _data_lines(path):
    with open(path) as f:
        return [ln for ln in f.read().splitlines()
                if ln.strip() and not ln.startswith('#')]


def _first_div_tick(path_a, path_b):
    """1º tick onde QUALQUER coluna difere (linhas de dados, pareadas);
    None se bit-idênticas."""
    a, b = _data_lines(path_a), _data_lines(path_b)
    if len(a) != len(b):
        return -1
    for la, lb in zip(a, b):
        if la != lb:
            return int(la.split(',')[0])
    return None


def main(argv):
    if argv and argv[0] == '--selftest':
        return selftest()
    if len(argv) < 6:
        print(__doc__)
        return 3
    p1, p2 = stats(argv[0]), stats(argv[1])
    d1, d2, d3, d4 = (stats(argv[2]), stats(argv[3]),
                      stats(argv[4]), stats(argv[5]))
    print("=== VARIEDADE-1 (regime canônico; prereg b237aeb) ===")
    for nm, s in [('P1 v0 flags-off s0', p1), ('P2 comp flags-off s0', p2),
                  ('D1 v0 var=1 s0     ', d1), ('D2 v0 var=1 s0 REP ',
                                                d2),
                  ('D3 v0 var=2 s0     ', d3), ('D4 comp var=1 s0    ', d4)]:
        print(f"  {nm}: cc={s['cc']} pos={s['pos']} | hesit={s['hesit']} | "
              f"{s['n_comp']}/10 | par={s['par']} | rol={s['rol']} | "
              f"off={s['off']}% | exc {s['med_exc']:.1f}s wand={s['wand']} | "
              f"colado {s['glue']}s dead={s['dead']}")
    # ---- PROTEÇÕES (ABSOLUTO; PARE=2) ----
    ok1 = _prot_ok(p1, F4V15_C)
    ok2 = _prot_ok(p2, F4V15_X)
    print(f"\nPROTEÇÃO P1 == F4v15-v0 {F4V15_C}: "
          f"{'BIT-IDÊNTICO' if ok1 else 'DIVERGIU -> PARE IMEDIATO'}")
    print(f"PROTEÇÃO P2 == F4v15-comp {F4V15_X}: "
          f"{'BIT-IDÊNTICO' if ok2 else 'DIVERGIU -> PARE IMEDIATO'}")
    if not (ok1 and ok2):
        return 2
    checks = []
    # ---- D2 == D1: BYTE-A-BYTE (ABSOLUTO) ----
    same_bytes = _data_lines(argv[2]) == _data_lines(argv[3])
    same_stats = all(d1[k] == d2[k] for k in d1)
    checks.append((f"D2 == D1 byte-a-byte + stats: "
                   f"{'BIT-IDÊNTICAS' if same_bytes and same_stats else 'DIVERGIU'}",
                   same_bytes and same_stats))
    # ---- D3 diverge cedo da base E de D1 (ABSOLUTO) ----
    t_base = _first_div_tick(argv[4], argv[0])
    t_d1 = _first_div_tick(argv[4], argv[2])
    ok_div = (t_base is not None and 0 <= t_base < 200
              and t_d1 is not None and 0 <= t_d1 < 200)
    checks.append((f"D3 diverge <tick 200: vs base t={t_base}, vs D1 t={t_d1}",
                   ok_div))
    # ---- D1-D4 sanidade (ABSOLUTO) ----
    for nm, s in [('D1', d1), ('D2', d2), ('D3', d3), ('D4', d4)]:
        checks.append((f"{nm}: 10/10 voltas e 0 paradas",
                       s['n_comp'] == 10 and s['par'] == 0))
    print()
    all_ok = True
    for txt, val in checks:
        print(f"  {txt}: {'PASS' if val else 'FAIL'}")
        all_ok &= bool(val)
    if all_ok:
        print("\nVARIEDADE-1: TODOS OS CRITÉRIOS PASS — camada entregue como "
              "OPT-IN (default 0; canônico intocado; adoção = dono). "
              "Contatos variam naturalmente (sem teto — report acima).")
        return 0
    print("\nVARIEDADE-1: FAIL — seguir a árvore do prereg §6 "
          "(PARE; sem re-pin). O determinismo é infraestrutura e não morre.")
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
