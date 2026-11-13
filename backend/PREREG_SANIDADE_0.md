# PREREG_SANIDADE_0 — ciclo de DEFEITOS DO PRODUTO (largada / grama / colagem)

Branch `feat/sanidade-produto` · 2026-10-20 · commitado ANTES da implementação.
**SEM promoção A×B, SEM flip de default, SEM re-pin do regime canônico R13.**
Pool: 70-79 é a ÚNICA década virgem; este ciclo consome **70-73** (74-79 ficam).

## §0 Diagnóstico (READ-ONLY; probes commitados v1→v2.2; output em
experiments/sanidade-0/diag_d1d2d3.txt)

- **D0 (validade do instrumento — lição R2 confirmada)**: a coluna `lat` do
  CSV é o **MÓDULO** (lat@0 = +1,9 para TODOS os slots vs grid físico ±1,9);
  o canal válido é **slat = obs4 × half_width** (hw = 6,00 derivado do
  próprio grid; ±1,90 exato pela paridade dos slots). TODA análise lateral
  deste ciclo usa slat.
- **D1 (CONTROLE F4v15)**: pós-largada t>20s = 2482 ✓; distribuição por t:
  20-30s 74 (3,0%) | 30-60s 358 (14,4%) | **>60s 2050 (82,6%)**; 20<t<60 =
  432 ⇒ **t<60s total = 1624** (t≤20 = 1192). 17 pares em contato pós-largada;
  top-5 detém 62% dos ticks (LEC×VER 138; NOR×PIA 124; PER×PIA 123; PER×SAI
  118; NOR×SAI 86) — o pós-largada é CONCENTRADO em poucos pares que moem
  juntos. **T1 (s≥2700): |Δlat| do vizinho<20m mediana 0,4 m; 10/10 <1,7 m**
  — o campo entra a T1 lateralmente SOBREPOSTO. Saídas de pista: 180
  inícios; **EMPURRÃO (contato ≤5s antes) 49 (27%) × PILOTAGEM 131 (73%)**.
  Largada t≤15s: máx|Δlat|/1s = 2,3-8,0 m/s (swerve lateral); flips de
  centro 1-6; cc_ev 596-8140.
- **D2 (grama)**: CONTROLE 180 excursões, **mediana 4,2s**, p75 14,1, máx
  23,6, **wanders>60s 0**; reentrada a 9,1 m/s; recupera 15 m/s em 1,0s;
  contato ≤30s pós-reentrada **68/180 (38%)**, gap mediana 3,0s. COMPOSITE
  219 excursões, mediana 4,2s, p75 10,2, máx 29,0, wanders 0; 9,2 m/s; 1,0s.
  Lei ATIVA (código): bearing R3 (alvo = projeção+10 m; ganho 2,0 clip
  ±0,79), teto 8 m/s, throttle 0,35; rejoin_gap (gap-check) DEFAULT OFF.
- **D3 (colados; slat; |Δlat|<2,0 ∧ Δs wrap<5,5; janela contígua >2s)**:
  CONTROLE **41 janelas, tempo colado 247s** (16% na largada),
  **deadlocks>10s 6**; esterço DIVERGENTE sem separar (FÍSICA) 12 ×
  CONVERGENTE/NULO (DECISÃO) 29; **|steer| médio ~0,05 nas retas — ninguém
  esterça** (o relato do dono confirmado: colados seguem reto); nas curvas
  lentas pares colados juntos a esterço 0,79 (full lock, mesma linha).
  COMPOSITE 7 janelas, **33s** (37% largada), deadlocks 0; 2×5.
- **CLIMA (weather-scan offline, instrumento validado 30/30)**: s70 SECA
  (v2 DRY→CLOUDY), s71 SECA, s72 SECA (v5 DRY→CLOUDY), s73 SECA — **0/4
  damp**; âncoras secas valem para o gate.

## §1 Mecanismos (camada-only; cada um com flag própria DEFAULT-OFF)

- **M1 `--grid staggered`** — layout alternativo JUSTIFICADO POR D1: o
  1-carro-por-fileira com gap ≥12 m exige grid_len = 9×12+6 = 114 m > reta
  de 45 m antes da SF (place_grid ABORTA por construção — a reta não cabe).
  PIN: **2 colunas com slat ±2,5 m (Δlat 5,0 m > corredor 3,5 do professor)
  ∧ Δlong 9,0 m** (grid_len 42 m ✓ cabe nos 45 m); nariz a 6 m antes da SF
  (âncora atual); ordem de largada continua semeada por `--variance grid`.
  Determinístico por seed.
- **M2 `--rejoin perceptive`** (base-layer: vale para TODOS os controllers;
  substitui o bearing QUANDO ON): (a) alvo de re-entrada com **ângulo raso**:
  ponto na linha central a `ahead = clip(|lat|/tan(15°), 10, 120)` m da
  projeção (ângulo de chegada ≤15°); (b) **teto condicionado à superfície**:
  grama 6,0 m/s (cap MENOR que os 8,0 atuais — aproximação controlada);
  asfalto LIBERA (fim do off-track = domínio do policy); (c) **prioridade de
  gap**: reusa o gap-check REPARADO (ead15a7: engate SÓ na transição
  off→on na borda, janela 10 s) com **X=20 m** (cotovelo do dossiê R13) e
  T_max 10 s. **PROIBIDO fade por progresso (lição ANTI-D3-1): o trigger é
  ESTADO (off-track), não progresso.**
- **M3 `--anti-glue`**: (i) física: chassis lateralFriction **0,05→0,01**
  (par-a-par; rodas intactas — o solo vem dos pneus por construção);
  DISCLOSE D3: a fricção já é ~0 e 29/41 janelas são DECISÃO (ninguém
  esterça) — (i) é cinto-e-suspensório pinnado, (ii)/(iii) carregam o peso;
  (ii) decisão **ESCOPADA a composite/professor** (race-blind preserva o
  v10): vizinho lateral com |Δlat|<2,5 m (base = LAT_CORRIDOR_M) ∧
  Δs wrap<10 m → esterço **+0,25 rad PARA FORA** + teto de aceleração
  th≤0,6; (iii) **deadlock-breaker** (todos os carros; emergência tipo
  rejoin, sob a flag): par colado (|Δlat|<2,5 ∧ Δs wrap<5,5) por **>3 s
  contíguos** → o de TRÁS cede (Δs wrap define; empate |Δs|<0,5 → cede o de
  FORA, maior |slat|): **lift (th=0) + offset 0,4 rad para fora** até
  |Δlat|>3 ou Δs>8. `authority='anti_glue'` quando o breaker age (SEM
  colunas novas no CSV — proteção bit-idêntica exige header igual).
- **BUNDLE `--modo espectador`** (GUI): liga M1+M2+M3 de uma vez. Defaults
  canônicos intactos; o bundle só embarca mecanismo VERDE no fecho.

## §2 Critérios — RECONCILIAÇÃO SISTEMÁTICA (ABSOLUTO / RE-ANCORADO c/
derivação / DROP — antes de qualquer run)

| critério | status | pin |
|---|---|---|
| PRIM-1 (M1, largada) | **RE-ANCORADO** | O literal "≤50% do controle 2482" mistura janelas: 2482 é t>20s e 82,6% disso vive em t>60s (D1) — fora do alcance de um mecanismo de LARGADA; o próprio alvo do critério é "contatos t<60s". **PIN: contatos t<60s (sum car_car, t_s<60) de CADA corrida all-v0 c/ bundle ON (s70 E s72) ≤ 812 = 50% de 1624** (t<60s do controle; derivação 3674−2050). |
| PRIM-2 (M2, grama) | **RE-ANCORADO (leitura divergente DIVULGADA)** | Âncora D2: mediana 4,2s (ambos os braços). O literal "≤2× melhor" (≤2,1s) CONTRADIZ o desenho do próprio M2 (ângulo raso + cap 6,0 = retorno MAIS LENTO e seguro; a mediana atual já é retorno limpo a 8 m/s — não há 2× a cortar sem SUBIR o teto, o oposto do pin). **PIN: mediana de duração de excursão de CADA corrida de gate ≤ 8,4s (= 2× a atual — tolerância de não-piora do trade-off de segurança) ∧ wanders>60s = 0 (ABSOLUTO; âncora 0/0)**. REPORT (não-gate): reentradas c/ contato ≤30s (âncora 38%). A leitura literal fica registrada como REJEITADA — revisão pode sobrepôr. |
| PRIM-3 (M3, colagem) | **RE-ANCORADO** | Fórmula EXATA do D3 (slat=obs4×hw; |Δlat|<2,0 ∧ Δs wrap<5,5; janela contígua >2s; deadlock >10s). **PIN: tempo total colado de CADA corrida: all-v0 ≤ 123,5s (−50% de 247s); all-composite ≤ 16,5s (−50% de 33s); deadlocks>10s = 0 (ABSOLUTO) em TODAS.** |
| NÃO-REG (5/5, CADA corrida de gate) | ABSOLUTO × RE-ANCORADO | 10/10 voltas **ABSOLUTO**; 0 paradas ≥3s **ABSOLUTO**; rolante ≤146s **RE-ANCORADO** (controle 136+10); contatos totais: all-v0 ≤ 3674 **ABSOLUTO** (âncora bit-idêntica da proteção); all-composite ≤ **752** **RE-ANCORADO** (o 1520 do prompt é a corrida do guard REPROVADO — NIT N1 o desligou; referência viva = F4v15 SEM guard; teto MAIS ESTRITO que o literal, divulgo); fora ≤29,9% **RE-ANCORADO** (p75 R12 seco; s70-73 SECAS pelo scan). |
| PROTEÇÃO | **ABSOLUTO** | 2 corridas seed 0 DRY com TODAS as flags novas OFF: P1 all-v0 **BIT-IDÊNTICO** à F4v15-controle (cc 3674, pós-larg 2482, rol 136,0, hesit 3, fora 22,1); P2 all-composite **BIT-IDÊNTICO** à F4v15-composite (cc 752, pós-larg 292, hesit 13, fora 25,2, rol 140). Divergência ⇒ **PARE imediato** (vazamento no caminho compartilhado), sem ler mais nada. |
| MISTAS | **DROP** | Fora do escopo do ciclo (o prompt não as orça; o bundle é produto/espectador). |

## §3 Veredito mecânico
`scripts/sanidade_verdict.py` commitado ANTES das corridas (PADRÃO-OURO).

```
.venv/bin/python scripts/sanidade_verdict.py \
  experiments/sanidade-0/1_prot_v0.csv experiments/sanidade-0/2_prot_comp.csv \
  experiments/sanidade-0/3_gate_v0_s70.csv experiments/sanidade-0/4_gate_comp_s71.csv \
  experiments/sanidade-0/5_gate_v0_s72.csv experiments/sanidade-0/6_gate_comp_s73.csv
```

Proteções primeiro (return 2 = PARE); depois PRIM-1/2/3 e não-reg por corrida.

## §4 Orçamento (6 corridas; SERIAIS; sequencial-puro; runs≠arquivos)
- P1: `race_diagnostic --actor model_train/v10_dagger/dagger_actor_best.keras
  --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed 0
  --gov vplan --variance grid,compound --out experiments/sanidade-0/1_prot_v0.csv`
- P2: idem + `--profile composite --out experiments/sanidade-0/2_prot_comp.csv`
- G1: idem P1 + `--grid staggered --rejoin perceptive --anti-glue --seed 70
  --out experiments/sanidade-0/3_gate_v0_s70.csv`
- G2: idem P2 + bundle + `--seed 71 --out .../4_gate_comp_s71.csv`
- G3: idem P1 + bundle + `--seed 72 --out .../5_gate_v0_s72.csv`
- G4: idem P2 + bundle + `--seed 73 --out .../6_gate_comp_s73.csv`

## §5 Árvore (pré-registrada)
- PRIM-1 FAIL ⇒ M1 research-negativo documentado e **SAI do bundle**.
- PRIM-2 (mediana ou wanders) FAIL ⇒ M2 sai do bundle.
- PRIM-3 (total ou deadlocks) FAIL ⇒ M3 sai do bundle.
- NÃO-REG FAIL ⇒ **PARE** com trade-off documentado (mecanismo não embarca).
- PROTEÇÃO FAIL ⇒ **PARE imediato** por vazamento.
- **Sem re-pin, sem re-run orçamentário, sem promoção.** O bundle espectador
  embarca SÓ mecanismo verde.

## §6 Suíte
Base 25F/310P/3S + testes novos (M1 layout; M2 alvo raso/caps/gap; M3 par
sintético separa + breaker; bundle). **ESPERADA ~25F/31xP/3S ±** (desvio a
justificar no fechamento).

## §7 Diagnóstico permitido
Read-only pós-veredito, com probes commitados antes de cada uso (nunca
inline). Zero re-run.

## §8 Intocáveis
mirrors/loader/v1s; fastf1==3.8.3; canônico R13 (v10-cego = race default)
intactos; 74-79 permanecem VIRGENS.
