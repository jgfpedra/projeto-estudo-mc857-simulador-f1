# PRÉ-REGISTO — CICLO ALAVANCA: SESSÃO ADVERSA (gate PAREADO, seeds {2,8,9})
# Commitado ANTES de qualquer run (regra: medição sem commit não existe).

Branch: feat/rejoin-gap-check (HEAD 869cd65 = gate seco TODOS-PASS). O pool
virgem 30-39 NÃO se aplica aqui: a seed É a condição climática (clima semeado
por seed, sha256 "<seed>//weather") → comparação PAREADA contra o histórico DO
MESMO seed. Conjunto adverso confirmado n=3 = **{2, 8, 9}** (regra w_trans
MECÂNICA, E5 do R13-FECHAMENTO, dossiê cab38ed; verificação por recontagem
abaixo). Runs ESTRITAMENTE seriais (paralelo diverge t≈3-4 s). ZERO corridas
além das 12 aqui preregistradas (2 smoke + 3 gate + 7 report).

## 1. CORPUS HISTÓRICO (braço CEGO, seeds 0-9)
`experiments/diag-r2-r13/race_diag_r10_blind_s{0..9}.csv` (+`_events.csv`) —
mesmo comando do tratamento (ator dagger_actor_best, obs edge, gov vplan,
600 s, Interlagos frozen v2 sha 164876196eb12174, variance grid,compound),
corridas da era R10. Instrumento de recontagem = `lever_gate_verdict.stats`
(o MESMO do gate seco — zero reimplementação):
- excursão = trecho contíguo off-track (coluna `offtrack`);
- reentrada = 1º tick on-track pós-excursão que termina antes do fim;
- PERIGOSA = contato do dono em ≤300 ticks da coluna `tick` (10 Hz → 30 s
  reais) após a reentrada; contato pelo solver-side (`_events.csv`,
  tick = sub//24);
- taxa = perigosas/reentradas POR RUN; rolante = mediana de tempo de volta;
- carros completando = cruzamentos de SF (s≥2655, ds∈(0,100)) − 1 ≥ 1 (`n_comp`);
- parada ≥3 s com v<0,5; wanderer >60 s fora (linhas a 5 Hz × 0,2 s).

## 2. 0-a — RECONTAGEM ADVERSA HISTÓRICA (commitada antes de qualquer run)
`scripts/lever_adverse_recount.py` emite POR SEED (0-9): excursões, reentradas,
perigosas, taxa, fora%, rolante, voltas (líder), carros completando, paradas,
wanderers + rótulo de clima (`weather_transitions` do cabeçalho do próprio CSV).
Saída: `experiments/diag-alv-adverso/recontagem_cego_s0_9.csv` — **COMMITADA**
(único artefato de dados no git; corpus bruto fica fora, convenção do repo).
O CSV derivado é a fonte ÚNICA das âncoras pareadas do veredito 0-d.

## 3. 0-b — SMOKE DE WIRING ADVERSO (seed 0, FORA do gate)
Par fresco, mesmo comando histórico, só a flag diferindo:
- base: `--seed 0` (sem --rejoin-gap) → `experiments/diag-alv-adverso/race_diag_alv_advbase_s0.csv`
- gap: `--seed 0 --rejoin-gap 20` → `experiments/diag-alv-adverso/race_diag_alv_advgap_s0.csv`
O CSV DEVE divergir: authority `rejoin_gap` > 0 E `rejoin_gap_hold` > 0.
Bit-idêntico → wiring morto no ramo adverso → PARE (instrumento antes de
interpretação). Nota: o par do smoke SECO não foi preservado (arquivo base não
existe mais); a cobertura de par-bit-a-bit desta sessão é ESTA (s0 adverso).

## 4. 0-c — CHECK DE NÃO-VAZAMENTO (`scripts/lever_leak_check.py`)
- (i) PAR (smoke adverso): 1º tick divergente base-vs-gap (colunas físicas
  comuns, comparação exata) DEVE ser ≥ 1º tick de reentrada — o hold só atua
  dentro do estado rejoin; antes disso a sim é bit-idêntica. Bônus
  report-only: 1º tick divergente == 1º tick de hold (o hold é o único canal
  de ação da alavanca).
- (ii) SELF (10 CSVs secos 20-29 + TODO tratamento desta sessão): para cada
  carro com hold, 1º tick de hold ≥ 1ª reentrada DO MESMO carro.
- (iii) BÔNUS largada: a 1ª excursão (drv, t_s, s) de cada run adversa é
  bit-idêntica à histórica do mesmo seed (a largada não mudou).
- (iv) REPORT-ONLY drift: base-fresco vs histórico s0 — nº de linhas
  divergentes nas colunas comuns (código atual vs era R10). >0 = caveat no
  relatório; NÃO bloqueia (os critérios 0-d permanecem trat-vs-hist pinados).
- FAIL em (i) ou (ii) → vazamento de wiring → PARE.

## 5. 0-d — GATE PAREADO (3 runs SERIAIS, seeds {2,8,9}; identity por run)
Comando EXATO (idêntico ao histórico + UMA flag; `--out` difere só no
caminho/nome do artefato — parâmetros de simulação idênticos), por seed N:
```
.venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed N --gov vplan --variance grid,compound --rejoin-gap 20 --out experiments/diag-alv-adverso/race_diag_alv_adv_sN.csv
```
(stdout → `experiments/diag-alv-adverso/race_diag_alv_adv_sN.log`; identity
conferida por run: ator/gov/profile=manual/pista-sha 164876196eb12174/
weather_seed=N/variance=grid,compound/rejoin_gap=20.0.)

CRITÉRIOS MECÂNICOS (cada seed contra o SEU histórico do recontagem_cego_s0_9):
- PASS-A: taxa_trat ≤ taxa_hist(mesmo seed) em 3/3
- GUARD-V: carros-completando_trat ≥ hist(mesmo seed) em 3/3
- GUARD-P: paradas_trat(≥3 s, v<0,5) = 0 — absoluto, 3/3
- GUARD-W: wanderers_trat(>60 s) = 0 — absoluto, 3/3
- GUARD-L: rolante_trat ≤ hist(mesmo seed) + 5 s em 3/3
  (NaN: hist NaN + trat com voltas → PASS; hist com voltas + trat NaN → FAIL;
  ambos NaN → PASS — pinado ANTES, mecanicamente)
- GUARD-F: fora%_trat ≤ hist(mesmo seed) + 2 pp em 3/3
- FALLBACK T_max: evento = transição 0→1 de `rejoin_gap_fb` por carro;
  contado e reportado (solta única por design, não é falha) — **>10
  eventos/run = PARE com diagnóstico**.

Veredito por `scripts/lever_adverse_gate_verdict.py` (commitado junto ao 0-a).

## 6. 0-e — REPORT-ONLY (SÓ se 0-d TODOS-PASS; 7 runs, seeds {0,1,3,4,5,6,7})
Mesmo comando do 0-d. Decomposição do efeito retroativo (SEM critérios):
fora% vs hold-s por run; contatos DURANTE hold-ticks (events cujo tick tem o
envolvido em hold); rolante vs fora.

## 7. RAMOS
- Smoke bit-idêntico (0-b) OU vazamento (0-c) → PARE: instrumento antes de
  interpretação.
- QUALQUER critério 0-d FAIL → PARE com diagnóstico por seed; SEM re-pin, SEM
  re-run; alavanca permanece opt-in documentada ("viva no seco, adverso
  reprovado").
- TODOS PASS → PARE: a revisão emite o prompt de ADOÇÃO (flip default +
  re-pin do regime canônico + identidade GUI↔headless com a flag + suite).
