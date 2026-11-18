# PREREG REALISMO-1 · C0 — matriz OFF N=1..4 e relatório de ruído

**Versão:** 1.0 · **Estado:** pré-freeze; ZERO corrida, ZERO extração da matriz, ZERO edição de código de produção, commit nenhum nesta etapa · **Data:** 2026-10-29 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `6edd4fb5acac1388d673db40b17d7243357223b5` (`6edd4fb`, closing do STAGE 6), esperado e conferido. **Index (staged pela etapa A, sem commit):** `backend/PLANO_REALISMO_BOTS_1.md`, `backend/scripts/realismo_metrics.py`, `backend/tests/test_realismo_metrics.py`, `backend/experiments/realismo-1/c0/0_full_suite_instrumento.log`, os 4 JSONs de `backend/experiments/realismo-1/c0/golden/` e este prereg. Strays conhecidos, nunca commitados: `.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.

**Plano-mãe:** `backend/PLANO_REALISMO_BOTS_1.md` v1.1 (aprovado pelo dono com 5 ajustes), seções D2 (protocolo), D3 (gates) e D4/C0. Caminhos abaixo são relativos a `backend/`.

## Proveniência e instrumentos (SHA-256 lidos do disco nesta etapa)

| Item | Caminho | SHA-256 |
|---|---|---|
| Runner de medição (INTOCÁVEL) | `model_train/race_diagnostic.py` | `ccf9bb2c247e7bf30257cdc81e120ecc742f4d4f1129a3d11eb3445b8dfdf14e` (= pin do BASE-2; sem mudança) |
| Runner visual / controller (INTOCÁVEL) | `scripts/run_race_10_cars.py` | `6f13b59cfb7e709081483be85e2ad14d7295f65981dc8705ca8bcc9a9b8b03b3` |
| Composite (INTOCÁVEL) | `model_train/residual_gated.py` | `955085c029f0c72cb1c0bb1faa57f4266084ceca22f694369f51267ecf9a73a9` |
| Extrator canônico (INTOCÁVEL) | `scripts/base_metrics.py` | `9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728` |
| Instrumento novo (Task 2) | `scripts/realismo_metrics.py` | `e5a7ecb42fd9bfd3297935d974a53174b51eb822a877b33e4ed4a208a590ac7b` |
| Testes do instrumento | `tests/test_realismo_metrics.py` | `b2a58ba4e53f0ad20ddba9b6530f42a0619e9e3658966bb1be1027b03263275f` |
| Dependência pinada no instrumento | `scripts/saidas_verdict.py` | `e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c` (idêntico à cópia da raiz `scripts/saidas_verdict.py`) |
| Dependência pinada no instrumento | `scripts/sanidade1b_verdict.py` | `c23f3c6692dfdb5add216e5d021cf1db6ba49b4113f1052d2aef2b54a74d8b16` |
| Residual de produção (STAGE 6) | `model_train/v15_residual/residual_best_weights.npz` | `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` |
| Pista Interlagos v2 | `model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` (embutido `164876196eb12174`) |
| Pista Monaco v2 | `model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` (embutido `67ca11dc211c8c78`) |
| OFF N=0 Interlagos (main) | `experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.csv` | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` |
| OFF N=0 Interlagos (events) | `experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE_events.csv` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` |
| OFF N=0 Interlagos (log) | `experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.log` | `1f587edee46335735f85ced6673cb733028046116858ed4cd6a36a0f232324b1` |
| OFF N=0 Monaco (main) | `experiments/composite-1/promocao-1/3_R3_MONACO_RACE.csv` | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` |
| OFF N=0 Monaco (events) | `experiments/composite-1/promocao-1/3_R3_MONACO_RACE_events.csv` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` |
| OFF N=0 Monaco (log) | `experiments/composite-1/promocao-1/3_R3_MONACO_RACE.log` | `0fb7dc6c0a827b6444f7887e978ec11494b7328d9c7abda602b8260c8928bf86` |
| g0 canônico anterior | `experiments/composite-1/promocao-1/0_full_suite_promocao_1.log` | `579a5e60232f6a5a1f2b0e15eddd7fc765182b52b9a44c4e40d26fd5749b62ed` |
| g0 da etapa A (instrumento) | `experiments/realismo-1/c0/0_full_suite_instrumento.log` | `b25c875cef56c6a79de2bacd119d381d904e7decda9322f61d04ec0ce889a3d9` |
| Golden N=0 Interlagos (leitura 1) | `experiments/realismo-1/c0/golden/1_R1_INTERLAGOS_N0_realismo.json` | `0154b67336056d776bd461e92031ef127543dfbf5123afacb5b090586de61e17` |
| Golden N=0 Interlagos (leitura 2) | `experiments/realismo-1/c0/golden/1_R1_INTERLAGOS_N0_realismo_read2.json` | `0154b67336056d776bd461e92031ef127543dfbf5123afacb5b090586de61e17` |
| Golden N=0 Monaco (leitura 1) | `experiments/realismo-1/c0/golden/3_R3_MONACO_N0_realismo.json` | `18d02e6d0ab6fcc49648e4a6107dfb271a9a1cf5e13c98842ea831d29b0b2bbe` |
| Golden N=0 Monaco (leitura 2) | `experiments/realismo-1/c0/golden/3_R3_MONACO_N0_realismo_read2.json` | `18d02e6d0ab6fcc49648e4a6107dfb271a9a1cf5e13c98842ea831d29b0b2bbe` |

`metrics_sha256` dos golden: Interlagos `b8bbb1cc16a385070f9c01d6ad0fda68a66279cc6278f57d8a895982a5bd4e73`; Monaco `b2f3a552c86db6262357d1d8939eae11522f368bc52667b193498b2ca54e9b07`. Os dois JSONs registram `instrument.realismo_metrics_sha256 = e5a7ecb4…` e os SHAs de log/main/events da promocao-1 da tabela acima.

## 1. Objetivo

1. Rodar UMA ÚNICA VEZ o braço OFF (código de produção atual, nenhuma flag nova) nas realizações N=1..4 das duas pistas: 8 corridas. Com N=0 (bytes commitados da promocao-1, nunca reexecutados), elas formam a **referência OFF canônica N=0..4** de todos os ciclos seguintes do plano.
2. Emitir o **relatório de ruído**: μ̂ e σ̂ de cada métrica de gate por pista sobre N=0..4 e a probabilidade de FAIL de cada gate do D3 sob a nula caótica (§7).
3. Este ciclo **MEDE**. Não há mecanismo, flag nova, mudança de código de produção nem gate de comportamento. A agregação final dos gates (§D3 do plano, coluna "Estado") é ratificada pelo dono no freeze do C1, com este relatório na mão.

## 2. Matriz EXATA — 8 corridas (orçamento exato da etapa B)

**Orçamento: 1 g0 + 8 corridas + 32 leituras de extração (2 por extrator × 2 extratores × 8 corridas, §6) + 4 leituras do relatório de ruído (2 por pista, §7) + 2 commits de proveniência. NADA além.** Corridas uma de cada vez, NUNCA em paralelo (inclusive com suítes de teste). Todas partem de `backend/`, em foreground, com `set -o pipefail`, `tee` e `timeout --signal=TERM 2400s`. Antes de cada largada, confirmar que os 3 caminhos de saída (main CSV, `_events.csv`, log) **não existem**. Conclusão válida exige os gates da §3.

Template LARGADA-FECHO-0 ("+1 re-smoke contingente s0"): declarado como **zero** neste ciclo. Não há smoke, porque nenhum código muda. Qualquer re-execução segue a regra B.1 (§4).

| k | Run-id | Pista | N | Saídas em `experiments/realismo-1/c0/` |
|---|---|---|---|---|
| 1 | `OFF_INTERLAGOS_N1` | interlagos | 1 | `1_OFF_INTERLAGOS_N1.{csv,log}` + `_events.csv` |
| 2 | `OFF_MONACO_N1` | Monaco | 1 | `2_OFF_MONACO_N1.{csv,log}` + `_events.csv` |
| 3 | `OFF_INTERLAGOS_N2` | interlagos | 2 | `3_OFF_INTERLAGOS_N2.{csv,log}` + `_events.csv` |
| 4 | `OFF_MONACO_N2` | Monaco | 2 | `4_OFF_MONACO_N2.{csv,log}` + `_events.csv` |
| 5 | `OFF_INTERLAGOS_N3` | interlagos | 3 | `5_OFF_INTERLAGOS_N3.{csv,log}` + `_events.csv` |
| 6 | `OFF_MONACO_N3` | Monaco | 3 | `6_OFF_MONACO_N3.{csv,log}` + `_events.csv` |
| 7 | `OFF_INTERLAGOS_N4` | interlagos | 4 | `7_OFF_INTERLAGOS_N4.{csv,log}` + `_events.csv` |
| 8 | `OFF_MONACO_N4` | Monaco | 4 | `8_OFF_MONACO_N4.{csv,log}` + `_events.csv` |

Comandos (argumentos explícitos; o zsh não divide variáveis não-quotadas):

```
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 1 --out experiments/realismo-1/c0/1_OFF_INTERLAGOS_N1.csv 2>&1 | tee experiments/realismo-1/c0/1_OFF_INTERLAGOS_N1.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 1 --out experiments/realismo-1/c0/2_OFF_MONACO_N1.csv 2>&1 | tee experiments/realismo-1/c0/2_OFF_MONACO_N1.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 2 --out experiments/realismo-1/c0/3_OFF_INTERLAGOS_N2.csv 2>&1 | tee experiments/realismo-1/c0/3_OFF_INTERLAGOS_N2.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 2 --out experiments/realismo-1/c0/4_OFF_MONACO_N2.csv 2>&1 | tee experiments/realismo-1/c0/4_OFF_MONACO_N2.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 3 --out experiments/realismo-1/c0/5_OFF_INTERLAGOS_N3.csv 2>&1 | tee experiments/realismo-1/c0/5_OFF_INTERLAGOS_N3.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 3 --out experiments/realismo-1/c0/6_OFF_MONACO_N3.csv 2>&1 | tee experiments/realismo-1/c0/6_OFF_MONACO_N3.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 4 --out experiments/realismo-1/c0/7_OFF_INTERLAGOS_N4.csv 2>&1 | tee experiments/realismo-1/c0/7_OFF_INTERLAGOS_N4.log
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --variedade 4 --out experiments/realismo-1/c0/8_OFF_MONACO_N4.csv 2>&1 | tee experiments/realismo-1/c0/8_OFF_MONACO_N4.log
```

Sem `--residual-override` (o residual de produção é o sancionado `6210fff6…`). `--track Monaco` com M maiúsculo (o loader é case-exato). Seeds sempre 0: os pools 76–79 continuam virgens. N=5..8 continuam SELADAS até o C7 (qualquer `--variedade` ≥ 5 neste ciclo = PARE).

## 3. Gates por corrida (falha = PARE)

| Gate | Critério | Como verificar |
|---|---|---|
| g1 | exit 0 do runner | `echo $?` imediatamente após o pipeline (pipefail) |
| g2 | integridade D2 | `realismo_metrics.py` com `--expect-variedade N` sai com 0 e `integrity.ok = true`: main CSV com 30.002 linhas físicas; `_events.csv` presente; log com `[diag] residual baseline sha256=6210fff65b19ad0e` exatamente 1 vez e nenhuma linha `RESIDUAL OVERRIDE`; CSV linha 1 com `track_frozen_sha256` = `164876196eb12174` (Interlagos) ou `67ca11dc211c8c78` (Monaco); linha `[diag] pista FROZEN` única com o mesmo sha e `variedade=N`; exatamente uma linha `[diag] VARIEDADE-1: N=N` |
| g3 | a variedade agiu | SHA-256 do main CSV de cada uma das 8 corridas difere do N=0 da mesma pista (§Proveniência) e das demais N da mesma pista. Um CSV byte-idêntico a outra realização = flag sem efeito = PARE |
| g4 | sumário do runner presente | o log contém exatamente uma vez `TOTAL fora:`, `CARROS-PRESO na sessão:` e `HESITAÇÕES` (pré-requisito do `base_metrics`) |

Sem `_events.csv` (corrida sem nenhum contato) o `base_metrics` não extrai: o resultado é preservado e a decisão é do dono (PARE).

## 4. Forma canônica e regra B.1

Corrida única por linha da matriz, foreground, `set -o pipefail`, `tee`, `timeout --signal=TERM 2400s`, checagem de pré-existência ANTES de cada largada. **Re-execução de qualquer corrida = PARE.** Aborto pré-launch = quarentena (artefatos movidos com SHAs para `experiments/realismo-1/c0/quarantine/`, nunca lidos para métricas) + emenda do dono antes de qualquer nova tentativa. Exit 124 (timeout) = PARE.

## 5. g0 (pin)

Antes da 1ª corrida, de `backend/`:

```
set -o pipefail && timeout --signal=TERM 2400s .venv/bin/python -m pytest -q tests 2>&1 | tee experiments/realismo-1/c0/0_full_suite_c0.log
```

Esperado: **481 itens = 20 failed / 458 passed / 3 skipped**, idêntico ao g0 da etapa A (`0_full_suite_instrumento.log`, SHA `b25c875c…`, 250,00 s), que por sua vez é o g0 canônico da promocao-1 (462 = 20F/439P/3S) + os 19 testes novos de `test_realismo_metrics.py`, todos PASS. O gate é o CONTEÚDO: diff itemizado das linhas `^FAILED` contra `composite-1/promocao-1/0_full_suite_promocao_1.log` deve ser vazio (20 linhas idênticas). pytest exit 1 é o esperado. Qualquer falha nova = PARE.

## 6. Extração (2 leituras por extrator, por corrida)

Para cada corrida k da §2, de `backend/` (`<P>` = `experiments/realismo-1/c0/<k>_OFF_<PISTA>_N<N>`):

1. `base_metrics` (INTOCADO): leitura 1 `.venv/bin/python scripts/base_metrics.py --run-id <run-id> --log <P>.log --main-csv <P>.csv --events-csv <P>_events.csv --out <P>_metrics.json`; leitura 2 sem `--out`, stdout redirecionado para `<P>_metrics_read2.json`.
2. `realismo_metrics`: leitura 1 `.venv/bin/python scripts/realismo_metrics.py --run-id <run-id> --log <P>.log --main-csv <P>.csv --events-csv <P>_events.csv --track <interlagos|Monaco> --expect-variedade <N> --out <P>_realismo.json`; leitura 2 sem `--out`, stdout para `<P>_realismo_read2.json`.

Gates de extração (falha = PARE): as duas leituras de cada extrator são byte-idênticas (`cmp` exit 0) e têm o mesmo `metrics_sha256`; `realismo_metrics` sai com 0; `canonical.metrics_sha256` dentro do JSON do `realismo_metrics` = `metrics_sha256` do JSON do `base_metrics` da mesma corrida (mesma função, mesmos bytes, mesmo run-id); `cross_checks.*.match` = true (FORA-PRESO da réplica = linha `FORA-PRESO:` do log; fora = `TOTAL fora:` do log).

## 7. Relatório de ruído (método pinado ANTES dos dados)

Comando, por pista (N=0 = golden da etapa A; N=1..4 = JSONs da §6):

```
.venv/bin/python scripts/realismo_metrics.py noise --track interlagos --off 0=experiments/realismo-1/c0/golden/1_R1_INTERLAGOS_N0_realismo.json 1=experiments/realismo-1/c0/1_OFF_INTERLAGOS_N1_realismo.json 2=experiments/realismo-1/c0/3_OFF_INTERLAGOS_N2_realismo.json 3=experiments/realismo-1/c0/5_OFF_INTERLAGOS_N3_realismo.json 4=experiments/realismo-1/c0/7_OFF_INTERLAGOS_N4_realismo.json --out experiments/realismo-1/c0/9_NOISE_INTERLAGOS.json
.venv/bin/python scripts/realismo_metrics.py noise --track Monaco --off 0=experiments/realismo-1/c0/golden/3_R3_MONACO_N0_realismo.json 1=experiments/realismo-1/c0/2_OFF_MONACO_N1_realismo.json 2=experiments/realismo-1/c0/4_OFF_MONACO_N2_realismo.json 3=experiments/realismo-1/c0/6_OFF_MONACO_N3_realismo.json 4=experiments/realismo-1/c0/8_OFF_MONACO_N4_realismo.json --out experiments/realismo-1/c0/10_NOISE_MONACO.json
```

Segunda leitura de cada um sem `--out`, stdout para `9_NOISE_INTERLAGOS_read2.json` / `10_NOISE_MONACO_read2.json`; `cmp` exit 0 obrigatório. O modo `noise` recusa entrada com `metrics_sha256` inválido, pista diferente, integridade falha ou N declarado ≠ `variedade` do log.

Método (implementado em `realismo_metrics.noise_report`, SHA acima):
- Por métrica de gate: valores por N, μ̂ (média) e σ̂ (desvio-padrão amostral, ddof=1) sobre N=0..4.
- **Nula caótica.** A simulação é determinística por (seed, N); um mecanismo de efeito nulo em média ainda produz uma realização nova. A realização OFF(N') faz o papel de "ON" contra OFF(N).
- Gates por realização (C1-P1, R-2-T1, C6 deadlocks): fração dos 20 pares ordenados OFF(N')×OFF(N), N' ≠ N, que reprovariam; e 1 − (1 − p)^5 como aproximação (rotulada) de "∀N" com realizações independentes.
- Gates por soma ou taxa (B-1, S-1, R-1, R-2, C1-P2, C2/C3, C5, C6 colado): ΣON ~ N(5μ̂, 5σ̂²) contra o limite calculado do ΣOFF observado, com correção de continuidade de 0,5; σ̂ = 0 vira comparação direta. Checagem de sanidade: a mesma regra aplicada a pares de realizações isoladas.
- Leitura: nos gates anti-regressão, P(FAIL | nula) é a taxa de **falso FAIL**; nos gates primários (melhora estrita), P(PASS | nula) é a taxa de **falso PASS**. Os dois números saem para todos os gates.
- Limitações declaradas: k = 5 realizações (σ̂ impreciso); aproximação normal; as 5 realizações compartilham o clima da seed 0 (correlacionadas).

## 8. Tabela de dados (report da etapa B)

Por pista: tabela OFF N=0..4 de todas as métricas de gate do D3 (contatos totais e t≤60 s, laps_total, linhas fora e fora%, saídas t≤60 s, Z_RETA, Z_T1 t≤60 s, C08 Junção em Interlagos, colado, deadlocks) mais FORA-PRESO, cascata e nova saída ≤ 5 s; μ̂/σ̂; P(FAIL|nula) e P(PASS|nula) por gate; disclosure por realização (aqui só o braço OFF existe). Números de outras eras (752/292, 292→846, 752→1520, 752→2336) só aparecem rotulados como "evidência qualitativa de ruído", nunca como σ (ajuste 1 do dono). Nenhum PASS/FAIL de comportamento é emitido no C0.

## 9. Commits de proveniência (mensagens propostas; ratificar no freeze)

1. Depois de g1–g4 PASS nas 8 corridas: `git add -f` dos 24 arquivos (`[1-8]_OFF_*.csv`, `_events.csv`, `.log`) → `REALISMO-1 C0 etapa B: matriz OFF N=1..4 — 8 corridas (provenance)`.
2. Depois da extração e do relatório de ruído: `git add -f` de `0_full_suite_c0.log`, dos 32 JSONs da §6 e dos 4 JSONs da §7 → `REALISMO-1 C0 etapa B: extração (2 leituras) + relatório de ruído (provenance)`.
3. `EXECUCAO_REALISMO_C0.md` staged, sem commit, mais 1 linha idêntica de ledger no fim de `backend/PROJECT_STATE.md`, `worklog.md` e `backend/model_train/AUDITORIA_RL.md` (caminhos absolutos). O dono commita no closing.

Em PARE, nada é commitado.

## 10. PAREs obrigatórios

Parar diante de: HEAD diferente do commit de freeze do dono que contém este prereg (o executor confere blob no HEAD == disco para o prereg, o instrumento, os testes e os golden); index sujo no início da etapa B (fora os strays conhecidos); qualquer SHA da tabela de proveniência divergente; edição de QUALQUER código (`race_diagnostic`, `run_race_10_cars`, `residual_gated`, `base_metrics`, `realismo_metrics`, `saidas_verdict`, `sanidade1b_verdict`); g0 com falha nova; gate g1–g4 reprovado; exit 124; re-execução de corrida; corrida além das 8 declaradas; `--variedade` ≥ 5; seed ≠ 0; leitura de shard TEST; edição de v1/v2; extração não determinística ou `cmp` divergente; `realismo_metrics` com exit ≠ 0; corrida sem `_events.csv`; `pip`; promoção ou mudança de `PROFILES`; commit fora da §9.

## Definições (D3 do plano; valores calculados pelo instrumento)

Glossário: o do D2 do plano. Contato = linha 5 Hz com `car_car > 0`; t ≤ 60 s ⇔ tick ≤ 600; t ≤ 10 s ⇔ tick ≤ 100; nova saída ≤ 5 s ⇔ intervalo até o fim da excursão anterior do mesmo carro ≤ 50 ticks; cascata = `anatomy_cascade` (≤ 10 s; wanderer > 60 s com precedência). Aritmética inteira dos gates: B-1 `(11·ΣOFF + 9) // 10`; R-1 `(95·ΣOFF) // 100`; R-2 `100·foraON ≤ 100·foraOFF + linhas`.

Zonas, calculadas da geometria frozen com `build_corner_definitions` + `match_corner` e conferidas com o D3 (tolerância 0,1 m; divergência = InstrumentError):

| Pista | Z_RETA (t ≤ 10 s) | Z_T1 (t ≤ 60 s) | C08 Junção |
|---|---|---|---|
| Interlagos v2 | [2608,1627; 2718,2886) | C10 [2718,2886; 2882,2996] | [2276,239; 2344,246] ± 30 m = [2246,2391; 2374,2462] |
| Monaco v2 | [3288,2346; 3331,2307) | C01 [3331,2307; 66,0349] (com wrap) | n/a |

O D3 do plano lista o início da Z_RETA de Monaco como 3288,3; o valor calculado é 3288,2346 (grid 3293,2346–3329,2346), dentro da tolerância de 0,1 m.

## Golden N=0 (etapa A; promocao-1)

| Métrica | Interlagos | Monaco | Esperado no plano | Situação |
|---|---|---|---|---|
| contatos 5 Hz | 107 | 210 | 107 / 210 | exato |
| contatos t ≤ 60 s | 95 | 96 | 95 / 96 | exato |
| laps_total | 44 | 31 | 44 / 31 | exato |
| fora% (linhas fora) | 26,4 (7905) | 49,9 (14963) | 26,4 / 49,9 | exato |
| hesitações | 3 | 5 | 3 / 5 | exato |
| FORA-PRESO / fora | 6281 / 7905 | 11294 / 14963 | 6281/7905 e 11294/14963 | exato (= linha `FORA-PRESO:` do log) |
| excursões | 219 | 384 | 219 / 384 | reconciliado (igual) |
| excursões t ≤ 60 s | 35 | 67 | 35 / 67 | reconciliado (igual) |
| saídas na Z_RETA | 12 | 6 | 12 / 6 | reconciliado (igual; mesmos carros, t e s do A1) |
| cascatas | 119 | 274 | 118 / 274 | Interlagos +1, explicado abaixo |
| nova saída ≤ 5 s (por reentrada) | 48/217 = 22,1% | 161/378 = 42,6% | 20,3% / 42,1% | explicado abaixo |
| saídas Z_T1 t ≤ 60 s | 12 | 9 | — | novo |
| saídas C08 Junção | 51 | n/a | — | novo |
| colado / deadlocks | 163 linhas (32,6 s) / 0 | 401 linhas (80,2 s) / 1 | — | novo |

Reconciliações (sondagem só-leitura sobre os mesmos bytes, sem arquivo novo):
- **Nova saída ≤ 5 s.** Os valores exploratórios 20,3% e 42,1% reaparecem exatamente com intervalo **< 5 s** (≤ 48 ticks): 44/217 = 20,28% e 159/378 = 42,06%. O glossário do plano diz **≤ 5 s** (≤ 50 ticks), que dá 48/217 = 22,1% e 161/378 = 42,6%. A diferença são os intervalos de exatamente 5,0 s (4 em Interlagos, 2 em Monaco). O instrumento segue o plano.
- **Cascatas em Interlagos.** Há 2 intervalos de exatamente 10,0 s. Com "≤ 10 s" (`anatomy_cascade` em ponto flutuante e a versão inteira do instrumento concordam) o total é 119; com "< 10 s", 117. O valor exploratório 118 é compatível com um desses casos de fronteira virando no ponto flutuante do script exploratório (não commitado). O instrumento conta em ticks inteiros, sem esse risco.

## Observações para o dono (não bloqueiam)

1. `sanidade1b_verdict.stats` fixa `L_TRACK = 4160,4` (Interlagos). O instrumento atribui ao atributo do módulo o comprimento da pista durante a chamada e o restaura depois (arquivo intocado). Em Interlagos o valor é o mesmo do original; em Monaco isso corrige o wrap de pares colados que atravessam s = 0. Teste: `test_glue_deadlock_uses_track_length_and_restores`.
2. `saidas_verdict.extract_excursions`: a janela de "tráfego nos 5 s anteriores" usa 25 ticks lógicos, ou seja, cerca de 2,4–2,5 s de amostras. O instrumento não usa a classificação solo; fica registrado como NIT, sem edição.
3. O teste golden (`test_golden_promocao_1_n0`, ~10 s) entrou na suíte e protege os exatos acima contra regressão do instrumento.

## REPORT da etapa A

- **SHA-256 deste prereg:** reportado ao dono após o write (um arquivo não carrega o próprio SHA).
- **HEAD:** `6edd4fb5acac1388d673db40b17d7243357223b5`, conferido no início; nada staged antes desta etapa.
- **g0 da etapa A:** 481 = 20F/458P/3S em 250,00 s; diff `^FAILED` contra a promocao-1 vazio (`FAILSET_IDENTICAL`); os 19 testes novos passam.
- **Golden:** 2 leituras por pista byte-idênticas (`cmp` exit 0); exatos do plano reproduzidos; reconciliações explicadas acima.
- **Zero corrida, zero commit, zero edição de arquivo existente nesta etapa.**
