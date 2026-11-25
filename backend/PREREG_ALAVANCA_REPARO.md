# PRÉ-REGISTO — CICLO ALAVANCA: REPARO DO INSTRUMENTO + RE-VALIDAÇÃO (3 estágios)
# Amenda commitada ANTES de qualquer run (regra: medição sem commit não existe).
# Orçamento: 22 runs seriais máx (2 smoke + 10 seco + 3 adverso + 7 report).
# PAREs em B (reparo incompleto), C (re-gate seco FAIL), D (adverso FAIL).

Branch: feat/rejoin-gap-check. Base: 9553105 (PARE-0c da SESSÃO ADVERSA).

## A.0 — pendências read-only da rodada anterior (respondidas)
- **Suite**: `25 failed, 280 passed, 2 skipped` (285,6 s). Destino dos skips:
  `test_composite_parity.py:54` (ARTEFATO DE COLEÇÃO — motor correto, paridade
  formal coberta por test_residual_numpy_equals_keras/test_gate_zero_equals_v10)
  e `test_regression_v2v4.py:59` (checkpoints v2/v4 não presentes).
- **git log (ordem cronológica confirmada)**: 1883d6d 18:22 → 7414fc7 18:26 →
  51ecce4 18:35 → cd20f00 18:43 → e8f564d 19:23 → 869cd65 19:25 → 50fa8ab
  20:46 → 3331ee8 20:46 → 120081e 20:49 → 9553105 21:31 (out/18).
- **Taxas secas históricas REPRODUZIDAS** com o script do prereg 1883d6d
  (`lever_gate_verdict.py`) sobre o corpus braço B cego 10-19
  (`experiments/diag-r2-r13/race_diag_r13_b_s1[0-9].csv`):
  [0,306; 0,328; 0,317; 0,441; 0,333; 0,406; 0,267; 0,310; 0,300; 0,350] →
  **mediana 0,323 | p25 0,307 | máx 0,441** — idênticas ao §1 do prereg.
  (Nota do corpus: s10 histórico tem par=4/wand=4 — o seed WET.)

## A.1 — REPARO (3 fixes, UMA intenção: restringir ao spec §3 do prereg original)
**(i) ENGate — engajamento só no retorno de excursão.** Fonte de verdade:
prereg 1883d6d §3 ("aplica-se DENTRO do estado rejoin", janela de 10 s a
partir da chegada à borda). Implementação: o controller não tem modo explícito
de histerese on-track — **a transição off→on detectada no loop de ações
(`_was_offtrack[drv]`, atualizado todo tick) É o "estado rejoin criado pelo
bearing pós-excursão"**, e a janela de 10 s (T_max) é a histerese. O estado do
gap-check só é criado no 1º tick on-track pós-excursão com `near_edge`.
Correção de diagnóstico da sessão anterior: `drv_lat` é a distância ABSOLUTA
à linha central (loop de observações) — `offtrack` e `near_edge` já eram
bilateral; `abs()` explícito adicionado por intenção. O vazamento vinha da
AUSEÊNCIA do requisito de excursão prévia, não do sinal.
**(ii) Telemetria EM FASE + KEYING POR CARRO.** Causa-raiz do "SAI crawl@0
com hold=0": o bloco usava `drv` STALE (bind do loop de observações ~linha
646 = ÚLTIMO driver) em vez de `drivers[i]` — **UM estado compartilhado por
todos os carros** (tick0 do primeiro que engajasse) **e flags escritas só na
chave do último**. Fix: `drv_id = drivers[i].driver_id` em todos os sítios
(engate, expiração, pop do rejoin, `_gap_hold`, `_gap_fb`); flags escritas
TODO tick por carro (mesma chamada que produziu a ação — a linha do CSV lê
após o predict_batch, mesma fase por construção). **Fallback = transição
0→1**: `fb_this_tick` marcado no tick do evento (o código antigo perdia o fb:
o pop de expiração apagava o estado antes da leitura da linha — fb era
INVISÍVEL; contagens antigas VOID).
**(iii) NADA mais muda**: X=20 m; crawl 4 m/s; T_max 10 s (100 ticks);
isenção de paradas (crawl 4 > 0,5); comando; colunas CSV; `offtrack`
unilateral→ já era absoluto (sem mudança).

## A.2 — Testes (tests/test_rejoin_gap.py, harness REAL do test_deep_rejoin:
pista frozen + engine pybullet + pesos v10 + `rejoin_gap=20`)
- **t1 NEGATIVO** (regressão da largada): on-track sem excursão prévia, gap
  9 m < X → NÃO engaja (estado vazio, hold 0, authority ≠ rejoin_gap) — falha
  no código contaminado (engajava 8/10 no tick 0).
- **t2 POSITIVO**: retorno off→on na borda com gap 9 m à frente → hold=1,
  crawl (th=REJOIN_THROTTLE, v=0), authority rejoin_gap, estado criado.
- **t3 TELEMETRIA EM FASE**: o holder (index 0) tem hold=1 NA SUA chave; os
  outros (incl. o ÚLTIMO driver, chave do bug stale-drv) têm 0; o crawl está
  na ação do holder e só dele.
- Suite após: **expectativa 25F/283P/2S** (280 + 3 novos).

## A.3 — Âncoras e pools (declaradas ANTES de qualquer run)
- **Secas 10-19 INALTERADAS**: taxa mediana 0,323 / p25 0,307 / máx 0,441
  (reproduzidas em A.0); GUARD-L ≤ 141 s; GUARD-F ≤ 33,6%.
- **Adversas** = `experiments/diag-alv-adverso/recontagem_cego_s0_9.csv`
  (commit 120081e): s2 0,277/23,0%/134 s/0 par/0 wand | s8 0,444/59,4%/150 s/
  14/17 | s9 0,348/46,9%/147 s/8/13.
- **X = 20 m** (inalterado).
- **Pool seco NOVO = seeds 30-39** — as 20-29 foram QUEIMADAS pelo instrumento
  contaminado (documentadas no PROJECT_STATE; NÃO reutilizadas para gate).
- **{2,8,9} POUPADOS** (nunca correram com tratamento); **40-49 reservado**.
- **Evidência do leak-check (sessão adversa, commitada em 9553105)**: 1ª
  divergência tick 0 (SAI: th 0,928→0,35, steer −0,438→−0,376) < 1ª reentrada
  tick 74; 8/10 carros com authority rejoin_gap no tick 0; self 10/10 secos
  FAIL (hold@0, reentradas ≥ tick 496); 1ª excursão 4,2 s→32,6 s; drift
  base-fresco ≡ histórico 0/30000 (isolamento válido).
- Artefatos novos: `race_diag_alv2_*` (alv2 = instrumento reparado);
  CSVs de gate vão ao corpus (`experiments/`).

## PASSO B — SMOKE DO REPARO (2 runs seriais, seed 0 seco, par fresco)
base (sem flag) vs gap (`--rejoin-gap 20`); identity por run. Leak-check
OBRIGATÓRIO, 3 condições — qualquer falha → **PARE (reparo incompleto;
conserte e re-smoke SEM consumir pools)**:
1. **1ª divergência ≥ 1ª reentrada** (`lever_leak_check.py pair`);
2. **hold EM FASE** (`lever_leak_check.py phase`): authority `rejoin_gap`
   ⟺ `rejoin_gap_hold`=1 linha a linha (0 violações) — o driver que executa
   crawl tem hold=1 no mesmo tick, sem flag em driver alheio;
3. **BÔNUS DECISIVO**: 1ª excursão (drv,t,s) do gap **bit-idêntica à
   histórica** `r10_blind_s0` (a largada NÃO muda) + drift base≡histórico = 0.
   → COMANDO B (por run, cwd=backend):
   `.venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed 0 --gov vplan --variance grid,compound [--rejoin-gap 20] --out experiments/diag-alv-seco/race_diag_alv2_[gap|base]_s0.csv`

## PASSO C — RE-GATE SECO (10 runs seriais, seeds 30-39; pool NOVO)
Critérios IDÊNTICOS ao prereg 1883d6d §5 (âncoras inalteradas):
- PASS-P: mediana(taxa) ≤ 0,307 | PASS-R: máx ≤ 0,323
- GUARD-V: 10/10 carros completam ≥1 volta | GUARD-P: paradas 0 | GUARD-W: 0
- GUARD-L: rolante mediana ≤ 141 s | GUARD-F: fora% ≤ 33,6%
- **Fallback RE-MEDIDO** (fb = transição 0→1 do instrumento reparado;
  contagem antiga VOID). Veredito por `lever_gate_verdict.py` (commit 1883d6d,
  inalterado). >10 eventos/run = PARE com diagnóstico.
- **EXPECTATION RESET (declarado ANTES)**: os números devem ser MENOS
  espetaculares que o gate contaminado (taxa 0,054/fora 10-15%) — o
  efeito-largada SOME com o reparo. Isso é CORREÇÃO DE ATRIBUIÇÃO, não
  regressão. O teto teórico do prereg §4 (≈0,149) continua a referência.
- FAIL → **PARE sem re-pin/re-run**: alavanca rejoin-only NÃO passa seca →
  opt-in research-grade documentado; o híbrido (e o dossiê LARGADA) vira
  candidato prioritário.

## PASSO D — GATE ADVERSO PAREADO (3 runs seriais, seeds {2,8,9})
Comando EXATO do prereg 3331ee8 §5 (inalterado; --out
`experiments/diag-alv-adverso/race_diag_alv_adv_s{N}.csv`); identity por run.
Critérios contra o MESMO seed histórico (recontagem 120081e):
- PASS-A: taxa_trat ≤ hist (0,277 / 0,444 / 0,348) em 3/3
- GUARD-V: completando_trat ≥ hist (10/10) em 3/3
- GUARD-L: rolante_trat ≤ hist+5 s (139 / 155 / 152) em 3/3
- GUARD-F: fora%_trat ≤ hist+2 pp (25,0 / 61,4 / 48,9) em 3/3
- **EMENDA GUARD-P (justificada pelas âncoras 0-a)**: paradas_trat ≤
  hist(mesmo seed) (s2⇒0; s8⇒14; s9⇒8) em 3/3 — exigir 0 absoluto onde o
  baseline histórico tem 8-14 confundiria CLIMA com ALAVANCA.
- **EMENDA GUARD-W**: wanderers_trat ≤ hist (s2⇒0; s8⇒17; s9⇒13) em 3/3.
- Fallback: >10 eventos/run → PARE com diagnóstico.
- Veredito por `lever_adverse_gate_verdict.py` EMENDADO (commitado junto a
  esta amenda). FAIL → PARE por seed; SEM re-pin, SEM re-run.

## PASSO E — REPORT-ONLY (SÓ se D TODOS-PASS; 7 runs, seeds {0,1,3,4,5,6,7})
Mesmo comando de D. Decomposição: fora% vs hold-s por run; contatos DURANTE
hold-ticks; rolante vs fora; 1ª excursão vs histórica (a largada DEVE
permanecer intocada no reparado).

## RAMOS
- B falha → PARE (reparo incompleto; conserte e re-smoke sem consumir pools).
- C FAIL → PARE: alavanca rejoin-only não passa seca → research-grade
  documentado; dossiê LARGADA vira candidato prioritário.
- D FAIL → PARE com diagnóstico por seed.
- TUDO PASS → PARE final: a revisão decide ADOÇÃO com números corrigidos e
  encaminha o dossiê LARGADA.
