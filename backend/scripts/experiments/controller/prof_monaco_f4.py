"""PROF-MONACO-1 — F4: verificação pós-bateria (probe commitado ANTES do uso).

FATOS a verificar antes do fechamento (a bateria mostrou 5 eps IDÊNTICAS
por braço — hipótese: em modo solo + clima SECA sem transição + sem
--variance, o SEED não tem NENHUM canal estocástico ⇒ seeds 0-4 produzem
a MESMA corrida determinística):
  V1: byte-identidade das linhas de DADOS entre os 5 seeds de cada braço
      (prof_s0 vs s1..s4; aluno_s0 vs s1..s4) — header weather_seed difere.
  V2: reconciliação com os números HERDADOS da ADOÇÃO-H-2 (aluno_B'
      45%/34 excursões/preso 118 s por ep 600 s; metaA 56,9% por 2 voltas):
      o aluno_s0 da bateria == aluno_Monaco_ep1 (mesma corrida s0 600 s)?
  V3: preso acumulado (R3) do aluno_s0 + sua cobertura pelo tempo-cascata
      da anatomia (o preso 118 s herdado vive DENTRO do churn de cascata?).

  .venv/bin/python scripts/experiments/controller/prof_monaco_f4.py
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

import numpy as np
import pandas as pd

BASE = Path('experiments/prof-monaco-1')
ADO = Path('experiments/adocao-h2')
WINDOW_S = 30.0   # R3 canônico: janela FIXA de 30 s


def data_lines(p):
    return [l for l in p.read_text().splitlines()
            if l.strip() and not l.startswith('#')]


def main():
    print("=== PROF-MONACO-1 F4: verificação pós-bateria (read-only) ===")
    # ---- V1: byte-identidade entre seeds (por braço) ----
    for braço, pref in [('PROFESSOR', 'prof'), ('ALUNO', 'aluno')]:
        ref = data_lines(BASE / f'{pref}_s0.csv')
        for k in range(1, 5):
            outro = data_lines(BASE / f'{pref}_s{k}.csv')
            same = ref == outro
            print(f"[V1] {braço} s0 vs s{k}: "
                  f"{'BIT-IDÊNTICA (dados)' if same else 'DIVERGE'}")
    # ---- V2: aluno da bateria == aluno_Monaco_ep1 da ADOÇÃO-H-2? ----
    a_bat = data_lines(BASE / 'aluno_s0.csv')
    a_ado = data_lines(ADO / 'aluno_Monaco_ep1.csv')
    print(f"[V2] aluno_s0 (bateria) vs aluno_Monaco_ep1 (ADOÇÃO-H-2): "
          f"{'BIT-IDÊNTICA' if a_bat == a_ado else 'DIVERGE'} "
          f"({len(a_bat)} vs {len(a_ado)} linhas)")
    # V2b: professor da bateria == metaA_mon_1 da ADOÇÃO-H-2 (600 s)?
    p_bat = data_lines(BASE / 'prof_s0.csv')
    p_ado = data_lines(ADO / 'metaA_mon_1.csv')
    print(f"[V2b] prof_s0 (bateria) vs metaA_mon_1 (ADOÇÃO-H-2): "
          f"{'BIT-IDÊNTICA' if p_bat == p_ado else 'DIVERGE'} "
          f"({len(p_bat)} vs {len(p_ado)} linhas)")
    # ---- V3: preso acumulado (R3) do aluno_s0 + cobertura cascata ----
    df = pd.read_csv(BASE / 'aluno_s0.csv', comment='#')
    # FÓRMULA CANÔNICA R3 (race_diagnostic.py:1026-1035): janelas FIXAS de
    # 30 s desde t=0 sobre a corrida; janela presa se lat_max>20 OU Δcum<5;
    # preso += ticks OFF-TRACK da janela.
    preso_ticks = 0
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        t = g['t_s'].values
        lat = g['lat'].abs().values
        cum = g['cum_dist'].values
        off = g['offtrack'].values
        t_end = float(t.max())
        for w0 in np.arange(0.0, t_end, WINDOW_S):
            m = (t >= w0) & (t < w0 + WINDOW_S)
            if not m.any() or not off[m].any():
                continue
            if (lat[m].max() > 20.0) or ((cum[m].max() - cum[m].min()) < 5.0):
                preso_ticks += int(off[m].sum())
    preso_s = preso_ticks * 0.2   # tick de export = 0,2 s
    print(f"[V3] preso acumulado (R3 CANÔNICO, janelas fixas 30 s) do "
          f"aluno_s0 = {preso_s:.1f} s | log da era: preso=1185 ticks "
          f"× 0,2 s = {1185 * 0.2:.1f} s — o herdado '118 s' era 1185 "
          f"ticks divididos por 10 (erro de TAXA: o R3 do runner opera "
          f"sobre LINHAS do CSV a 5 Hz, não ticks lógicos de 0,1 s)")
    an = pd.read_csv(BASE / 'tabela_anatomia.csv')
    casc = an[(an.perfil == 'ALUNO (v10-cego)')
              & (an.classe == 'REJOIN-CASCATA')]['tempo_acum_s'].sum() / 5.0
    print(f"     tempo-cascata médio por ep = {casc:.1f} s — o preso vive "
          f"DENTRO do churn de cascata ({preso_s:.1f} <= {casc:.1f}: "
          f"{'SIM' if preso_s <= casc else 'NÃO — investigar'})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
