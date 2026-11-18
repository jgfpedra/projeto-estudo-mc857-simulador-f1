# PRÉ-REGISTO — CICLO LARGADA, FASE 1a: LAUNCH-CAP (commitado ANTES de qualquer código/run)
# Orçamento: 12 runs seriais (1 base s50 + 1 smoke-par [reuso: base smoke serve de
# drift-check] + 10 tratamentos). PAREs: SELF falho; FAIL por seed; guardrail já PASS.

## 1. ÁRVORE AVALIADA (dados 0-c commitados, 82b12c6; scan 0-d commitado)
- **ENTRADA-S DOMINANTE**: 228/348 pares em W (65%) vs GRID 112 (32%) vs PÓS-S 8 →
  **ramo L-1a CAP** (a árvore do prompt). Pares adjacentes à 1ª excursão:
  **20/20 em ENTRADA-S, 0 no GRID** — a queixa original é 100% da compressão na
  entrada do Senna S. A massa de GRID (112 pares, 29% mesma fileira) PERMANECE
  endereçada só por mudança de cenário → decisão de era vai ao DONO no relatório.
- **Scan 50-59 (0-d)**: 1/10 DAMP (s50: v3 DRY→DAMP, v5 DAMP→WET); guardrail PASS.
  s50 exige base FRESCA (pareio GUARD-P/W + rolante damp).

## 2. MECANISMO — launch-cap (UMA variável: teto de velocidade na largada)
- **Lei**: enquanto `sim_ts < T_max` E `s < s_cut`: v_ceiling = k × v_plan(s);
  se `speed > v_ceiling` → mesma lei de freio do governor
  (`excess=(v−v_ceiling)/v_ceiling; brk=max(brk, clip(excess×0,8, 0,15, 1,0)); th=0`).
  ZERO constantes novas além de k/s_cut/T_max.
- **CONSTANTES PINADAS: k = 0,8 | s_cut = 2950 m | T_max = 30 s.**
  Derivação (medida, v_plan real do runner — grip 0,788/sf 0,80):
  v_plan: s2700=57,1 (cap 45,6) | s2725=45,7 (36,5) | s2750=34,3 (27,4) |
  s2800=20,3 (16,2) | s2850=33,5 (26,8) | s2900=44,2 (35,3).
  Velocidade medida (cegos s0, t≤15s): reta pós-SF med 24,0/p90 36,0 (cap mal
  toca — 36,5-45,6); **entrada do S med 17,9/p90 34,7/máx 48,4 vs teto 16,2-27,4
  → o cap remove até ~21 m/s de excesso de CHEGADA na zona da queixa**. T_max 30 s
  ≈ 5× a fase crítica (t_1ªexc med 6,2 s) e cobre a passagem; s_cut 2950 cobre o
  cluster inteiro das 1ªs excursões (2699,7-2814,0) + a saída do S.
- **Flag `--launch-cap` (store_true), DEFAULT OFF** — flag-off = regime canônico
  bit-idêntico. **NUNCA lê clima no runner** (lição GUI≠headless). O cap exige
  `--gov vplan` (_v_plan_cap); sem v_plan o cap é no-op documentado (o comando do
  gate usa vplan).
- **Composição com gov vplan**: ceiling efetivo = min(v_plan×GOV_MARGIN, k×v_plan)
  = k×v_plan (k < margin) — composição de min() como o prompt pede.
- **Precedência de autoridade**: rejoin/recovery/blocked (segurança) >
  **launch_cap** > governor > policy; o cap NÃO altera esterço nem camadas de
  segurança; carro off-track no窗口 segue rejoin (teto próprio).
- **Telemetria (CSV aditivo, flag on)**: `launch_cap_active` (1 = freando neste
  tick), keyed POR CARRO via `drivers[i]` (lição stale-drv do REPARO);
  **authority 'launch_cap' ⟺ launch_cap_active=1 linha a linha** (fase 1:1).

## 3. CRITÉRIOS DO GATE (âncoras citadas: largada_decomp_resumo/pares 82b12c6)
- **PRIMÁRIO-1 (higiene de contatos)**: pares_W mediana ≤ 8 E máx ≤ 14
  (âncora: 12-23/run, med 17,0, pooled 348; instrumento idêntico ao 0-c:
  pares distintos (drv_a,drv_b) com ≥1 evento solver em t ≤ 60 s).
- **PRIMÁRIO-2 (a queixa)**: ≥ 7/10 runs com `t_1ªexc > 12,4 s` (2× med âncora
  6,2) OU taxonomia ≠ CONTATO-ADJ (evento do dono em ±2 s). Run SEM excursão
  conta como PASS (a queixa sumiu naquele run).
- **NÃO-REGRESSÃO**:
  - rolante: SECAS ≤ 141 s (hist seca 136+5); s50 (DAMP) ≤ rol base fresca s50 + 5 s.
  - GUARD-V: 10/10 carros ≥ 1 volta.
  - paradas/wanderers: SECAS 0/0 absolutos; s50 ≤ base fresca da MESMA seed (lição C').
  - fora% ≤ 28,3 em todas (pin do prompt: hist 26,3 + 2 pp; caveat declarado: s50
    úmido pode refletir CLIMA — no FAIL, o diagnóstico por seed atribui via base).
  - contatos totais (soma `car_car` do CSV): SECA ≤ 3.197 (hist med 2.906 + 10%);
    DAMP ≤ 3.850 (hist med 3.500 + 10%).
- **EXPECTATIVA REPORT-ONLY (pré-registrada, NÃO-gating)**: fora% < 15% em ≥ 7/10
  → "cascata do pacing real"; fora% em 17,3-26,3 → "o efeito da era contaminada era
  artefato do keying". Qualquer resultado é informativo; NÃO muda o gate.
- **SELF BLOQUEANTE (padrão ADVERSO; smoke PRIMEIRO, seed 0 seco, par fresco)**:
  1. 1ª divergência base-vs-cap **== 1º tick com launch_cap_active=1** (o cap age
     on-track por design — divergência na aproximação é ESPERADA; o check é a
     coincidência exata com o cap, nenhum outro canal);
  2. fase: authority 'launch_cap' ⟺ active=1 com 0 violações;
  3. flag-off bit-idêntico ao base E base ≡ histórico r10_blind_s0 (drift 0/30000).
  Falha → PARE (consertar ANTES do pool; SEM consumir 50-59).
- **Testes de unidade (5; suite esperada 25F/289P/2S)**: t1 janela s/t (ativo
  dentro; inativo se t≥T_max OU s≥s_cut); t2 T_max expira; t3 s_cut libera;
  t4 telemetria per-carro (chave própria, lição stale-drv); t5 flag-off default
  + no-op (LAUNCH_CAP_ENABLED=False por construção).

## 4. GATE (runs SERIAIS; identity por run; tree limpa p/ decisão)
- Base fresca s50 SEM flag (report-only; pareio damp) → smoke-par seed 0
  (base+cap) → 10 tratamentos seeds 50-59 com `--launch-cap`.
- Comando tratamento (cwd=backend):
  `.venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed {N} --gov vplan --variance grid,compound --launch-cap --out experiments/diag-largada/race_diag_lg1_s{N}.csv`
  Base s50: idem sem `--launch-cap`, out `race_diag_lg1_base_s50.csv`.
  Smoke: seeds 0 → `race_diag_lg1_base_s0.csv` / `race_diag_lg1_cap_s0.csv`.
- Veredito mecânico por `scripts/largada_gate_verdict.py` (commitado junto;
  lê o scan CSV + bases frescas + âncoras da decomposição; SELF integrado).
- FAIL → PARE por seed com diagnóstico; SEM re-pin, SEM re-run.
  TUDO-PASS → PARE final: revisão decide adoção (opt-in, como a alavanca);
  decisão de grid-era vai ao dono (massa de GRID 112 persiste).
