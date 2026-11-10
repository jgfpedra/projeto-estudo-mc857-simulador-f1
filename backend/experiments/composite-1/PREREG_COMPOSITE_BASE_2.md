# PREREG COMPOSITE-BASE-2 — mediação do candidato residual em pista

**Versão:** 1.0 · **Estado:** pré-freeze; ZERO corrida, ZERO treino, ZERO edição de código, commit nenhum nesta etapa · **Data:** 2026-10-27 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `33da6b9638c5d3b9fcf595435ad806ef7f2eecac` (`33da6b9`), esperado. **Index:** nada staged (o único item não rastreado é `backend/ANEXO_SAIDAS_1_ERRATAS.md`; nenhum `.py`, nenhum artefato de corrida).

**Matriz de comandos fonte:** `experiments/composite-1/PREREG_COMPOSITE_BASE_1.md`, freeze `d1e811e1fef8282a38f386a80aab8631bf83ac33` + emenda operacional B.1 `84c44add218cf81014b61c42c467992e51d4ae52`. Os comandos abaixo são CORTADOS literalmente dessa matriz; a única adição é a flag de override nos dois braços composite.

## Proveniência e instrumentos (frozen, citados)

| Item | Caminho | SHA-256 |
|---|---|---|
| Instrumento de extração (INTOCÁVEL) | `scripts/base_metrics.py` | `9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728` |
| Instrumento de corrida (INTOCÁVEL) | `model_train/race_diagnostic.py` | `ccf9bb2c247e7bf30257cdc81e120ecc742f4d4f1129a3d11eb3445b8dfdf14e` |
| Candidato residual (alvo da mediação) | `experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz` | `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` |
| Baseline B3.1 = `PROFILES['composite']['residual_npz']` | `model_train/v15_residual/residual_best_weights.npz` | `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` |

O candidato é o artefato residual novo fechado em COMPOSITE-TRAIN-1 (`33da6b9`): byte-idêntico à réplica, pesos internos do `.keras` com max diff 0,0. Ele será injetado em pista SEM editar produção, exclusivamente via `--residual-override`. A resolução de `PROFILES` está em [run_race_10_cars.py](file:///home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend/scripts/run_race_10_cars.py#L71-L87) (`composite.residual_npz` → `v15_residual/residual_best_weights.npz`); a flag e o log nativo do override estão em [race_diagnostic.py](file:///home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend/model_train/race_diagnostic.py#L1024-L1026) e [linhas 1334–1350](file:///home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend/model_train/race_diagnostic.py#L1334-L1350).

## 1. Objetivo

Medir, **em corrida**, o comportamento do candidato residual TREINADO contra DOIS controles:

1. **braço blind (v10 edge)** — o mesmo ator v10 sem residual, `--obs-mode edge`;
2. **braço composite vigente do BASE-1** — o braço composite do BASE-1, cujo residual é o B3.1 (`PROFILES['composite']['residual_npz']`).

Este ciclo **MEDE**; nenhum gate de corrida pré-contratado é definido aqui. O ganho `−64,7%` (Huber) é **OFFLINE**: BC sem-gate, alvo `g=1`; em pista o gate `g ∈ [0,1]` modula a atuação do residual, logo o número offline não é transportado como gate de corrida. A leitura é qualitativa e ratificada pelo dono PÓS-números; os release criteria do Estágio 5 vêm depois. O bucket **TEST (A_VER/B_SAI) segue SELADO** — nenhuma corrida deste ciclo lê ou toca corpus/shard.

## 2. Matriz EXATA — 4 corridas (orçamento exato da etapa B)

Orçamento: **4 corridas**, uma de cada vez, NUNCA em paralelo. **Re-run de qualquer corrida = PARE.** Todas partem de `backend/`, são foreground, com `set -o pipefail`, `tee` e `timeout --signal=TERM 2400s`. Conclusão válida exige exit code 0, main CSV com exatamente **30.002 linhas físicas** (metadado + header + 30.000 amostras de 10 carros a 5 Hz) e SHA-256 registrado para log, main e events. O runner gera o sidecar de eventos como `<main sem .csv>_events.csv`.

| Run | Run-id | Pista | Braço | Papel |
|---|---|---|---|---|
| R2' | `R2_INTERLAGOS_RACE_BLIND` | Interlagos | race-blind (v10 edge) | controle blind |
| R1' | `R1_INTERLAGOS_RACE` | Interlagos | composite + override (candidato) | alvo primário |
| R4' | `R4_MONACO_RACE_BLIND` | Monaco | race-blind (v10 edge) | controle blind |
| R3' | `R3_MONACO_RACE` | Monaco | composite + override (candidato) | alvo secundário (report-only) |

**R2' — Interlagos race-blind = comando do R2 SEM mudanças (sem override):**

```
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-2/2_R2_INTERLAGOS_RACE_BLIND.csv 2>&1 | tee experiments/composite-1/base-2/2_R2_INTERLAGOS_RACE_BLIND.log
```

**R1' — Interlagos race composite = comando do R1 (`--profile composite`) + `--residual-override`:**

```
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --residual-override experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-2/1_R1_INTERLAGOS_RACE.csv 2>&1 | tee experiments/composite-1/base-2/1_R1_INTERLAGOS_RACE.log
```

**R4' — Monaco race-blind = comando do R4 SEM mudanças:**

```
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-2/4_R4_MONACO_RACE_BLIND.csv 2>&1 | tee experiments/composite-1/base-2/4_R4_MONACO_RACE_BLIND.log
```

**R3' — Monaco race composite = comando do R3 (`--profile composite`) + `--residual-override`:**

```
set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --residual-override experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-2/3_R3_MONACO_RACE.csv 2>&1 | tee experiments/composite-1/base-2/3_R3_MONACO_RACE.log
```

Artefatos sob `experiments/composite-1/base-2/` com a MESMA nomenclatura do BASE-1 (`1_R1_…`, `2_R2_…`, `3_R3_…`, `4_R4_…`). Antes de cada largada, confirmar que os três caminhos de saída (main CSV, events CSV, log) ainda **não existem**; não sobrescrever. Nenhum dump de treino é solicitado ou gravado.

## 3. GATE DE CONTROLE (novo)

R2' e R4' são braços **blind** e NÃO dependem do novo npz. Eles **DEVEM reproduzir BYTE-A-BYTE** os bytes do BASE-1:

| Artefato | SHA-256 BASE-1 |
|---|---|
| `2_R2_INTERLAGOS_RACE_BLIND.csv` | `9d2a08427d4c5bdad0d6611df2caa7b4d7f02c5a5584c71a49d412c763c67e12` |
| `2_R2_INTERLAGOS_RACE_BLIND_events.csv` | `4260568e2b453899cfc12e25576d780a2592338cd8909a369a7e4a3a3ce781ed` |
| `4_R4_MONACO_RACE_BLIND.csv` | `15fb3da069adb7369741e90fdffca00f12cbe2abd75481b217c9c962bfacdd11` |
| `4_R4_MONACO_RACE_BLIND_events.csv` | `8a5f461e010571341528a17ddf2aa612f245b74152755d3ef1e1596b5c4ca527` |

Os **logs** divergem apenas em timestamps (esperado; não é gate). **Divergência de CSV = PARE imediato** (física/ator solo mudou sem autorização).

## 4. GATE DO OVERRIDE

Cada log de corrida composite (R1', R3') DEVE conter as linhas nativas do `race_diagnostic` com o SHA de 16 hex do candidato na linha `RESIDUAL OVERRIDE` E o SHA de 16 hex do baseline B3.1 na linha `RESIDUAL BASELINE`:

- `[diag] RESIDUAL OVERRIDE (candidato): composite_residual_candidato_1_weights.npz sha256=6210fff65b19ad0e`
- `[diag] RESIDUAL BASELINE (r2): residual_best_weights.npz sha256=6a2dbf53a69fcac7`

**Falta de qualquer linha = PARE** (fallback silencioso proibido — lição A.2(a), cf. [race_diagnostic.py:1339-1350](file:///home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend/model_train/race_diagnostic.py#L1339-L1350)).

## 5. Forma canônica

Corrida única, foreground, `set -o pipefail`, `tee`, `timeout --signal=TERM 2400s`; verificação de pré-existência dos caminhos ANTES de cada largada. **Aborto pré-launch = quarentena + emenda do dono** (regra B.1 — corrida formal executa UMA vez; artefatos abortados vão para quarentena com SHAs e NUNCA são lidos para métricas).

## 6. g0 do BASE-2 (etapa B)

Log: `experiments/composite-1/base-2/0_full_suite_base_2.log`. Esperado **460 itens = 20 failed / 437 passed / 3 skipped**, com o **fail-set canônico EXATO**. Referências do pin:

- g0 1G: `0_full_suite_collect_1g.log` SHA `369874d3490956c53e651c9456590fb594121a2b552792f79c422a6b4a6d2357` → `20 failed / 423 passed / 3 skipped` (423 testes).
- g0 TRAIN-1: `train-1/0_full_suite_train_1.log` SHA `bf0517329d3ee61e3324653660441e021267fe087476fda3b33172b2f7b9e045` → `20 failed / 437 passed / 3 skipped` (460 testes).

**QUALQUER falha nova = PARE.**

## 7. Extração

`scripts/base_metrics.py` INTACTO (SHA `9107c2d0…`) — **2 leituras por corrida**: a 1ª grava com `--out` (criação exclusiva, sem sobrescrita) e a 2ª imprime em stdout. O `metrics_sha256` da 1ª e da 2ª leitura do MESMO run devem ser **idênticos** (determinismo do extrator). CLI por corrida: `--run-id <run-id> --log <main>.log --main-csv <main>.csv --events-csv <events>.csv [--out <run>_metrics.json]`.

## 8. Tabela de dados (no report da etapa B)

7 métricas canônicas + **contatos 5 Hz com `t ≤ 60 s`**, em **DIREÇÕES 3-way por pista**:

- **(i) candidato vs blind** — deltas absolutos (R1'−R2' em Interlagos; R3'−R4' em Monaco), sem classificação PASS/FAIL;
- **(ii) candidato vs composite BASE-1/B3.1** — melhor / empate / pior por métrica (os números do BASE-1 já ratificados na mesa);
- **(iii) top-5** pares do solver por corrida.

Mesa a comparar = BASE-1 ratificada: contatos `−36%` Interlagos / `−44%` Monaco (defender); ritmo `−8` cruzamentos e fora `+6,7 pp` em Interlagos, `−2,1 pp` em Monaco (recuperar); hesitações `+9` / `+7`. A métrica "presos" (`10/10`) é **degenerada** e **NÃO é alvo** — fica fora das tabelas de comparação. Deltas são calculados dos JSONs de métrica; sem narrativa preditiva.

## 9. PAREs obrigatórios

Parar diante de: **leitura de qualquer shard/TEST**; **edição de QUALQUER código** (`base_metrics`/`race_diagnostic`/produção/`train`); **promoção ou modificação de `PROFILES`**; **rerun pós-gate**; **exit 124** (timeout); log sem o sumário do runner; `pip`; ledgers/anexos; **commit**; corrida além das quatro declaradas; resultado métrico não determinístico entre as duas leituras dos mesmos bytes; schema incompatível; divergência de CSV no gate de controle (§3); ausência de qualquer linha do gate de override (§4).

---

## REPORT da etapa A

- **SHA-256 deste prereg:** computado e reportado ao dono após o write (arquivo único desta etapa).
- **HEAD:** `33da6b9638c5d3b9fcf595435ad806ef7f2eecac` (`33da6b9`) — esperado, conferido.
- **Estado staged:** vazio (nada staged; commit NÃO realizado).
- **Matriz cita os SHAs dos dois instrumentos** (`base_metrics.py` `9107c2d0…`, `race_diagnostic.py` `ccf9bb2c…`) **e o SHA do npz candidato** (`6210fff6…`), além do SHA do baseline B3.1 (`6a2dbf53…`) e dos SHAs dos CSVs de controle do BASE-1 (§3).
