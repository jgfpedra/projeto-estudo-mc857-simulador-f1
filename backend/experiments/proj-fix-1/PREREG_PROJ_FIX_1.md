# PREREG — PROJ-FIX-1: atribuição instrumentada dos saltos (Monaco)

**Status:** congelado antes do replay e antes da leitura das classificações numéricas. Nenhuma correção de comportamento será proposta ou implementada neste ciclo.
**Ratificação de schema:** o dono ratificou g2 = **71 campos/linha** para R4 Composite (68 campos legados + `body_x`, `body_y`, `ns_raw`).
**Identidade:** FF1b R4 Composite Monaco, replay instrumentado v3.4, N=1.

## 1. Orçamento e imutabilidade

- 1 corrida de replay, sequencial, seed 0; N=1.
- Zero corridas de medição novas e zero smokes.
- Pools, controles, física e pistas frozen intocados. O ciclo não escreve em objetos de simulação.
- A única alteração anterior de comportamento neste checkout é inexistente: o runner atual apenas adiciona leituras read-only v3.4. Este ciclo adiciona artefatos offline de prereg/classificação e documentação.
- Sem reparo, promoção, retreino ou alteração de lógica nesta etapa.

## 2. Entradas congeladas e replay

Reexecutar R4 com a configuração congelada do FF1b: `--profile composite`, 10 carros, 6000 ticks, `--laps 99`, alias de pista `--track Monaco`, seed 0, clima `seeded`, governor `vplan`, variância `grid,compound`, writer default v3.4 (sem `RACE_DIAG_NO_XY=1`). O alias `Monaco` resolve `model_train/tracks_frozen/Monaco_v2.json`, short SHA `67ca11dc211c8c78`, SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`. Residual congelado: `model_train/v15_residual/residual_best_weights.npz`, SHA-256 `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6`.

Âncora R4 FF1b: `experiments/fail-forensics-2/4_composite_monaco_s0.csv`, SHA-256 `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022`. Seu header tem 68 campos; o writer v3.4 anexa as três colunas e a saída deve ter 71 campos por linha. A saída será `experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.csv`, com stdout/stderr e hashes em `1_replay_composite_monaco_s0_v34.log`.

Comando congelado, a executar uma única vez de `backend/`:

```bash
set -o pipefail
env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track Monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --out experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.csv 2>&1 \
  | tee experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.log
```

## 3. Gates de execução

Executar em ordem e parar imediatamente em qualquer divergência:

1. **g1 — writer passivo/replay determinístico:** remover linhas iniciadas por `#` de ambos os arquivos; para cada linha restante, incluindo header, fazer `split(',')[:49]` e comparar os bytes resultantes entre replay e âncora R4. Não usar biblioteca CSV nesta projeção.
2. **g2 — schema/valores:** todas as linhas CSV, incluindo header, têm 71 campos. Em cada linha de dados, `body_x` e `body_y` são finitos; `ns_raw` é inteiro lexical e satisfaz `0 <= ns_raw < 834` (Monaco frozen: 834 waypoints).
3. Verificar o registro da suíte atual contra os 20 FAILED canônicos da suíte pós-código LOC-XY-1. Qualquer identidade FAILED nova é PARE.

Falha em g1/g2 impede toda classificação. Não repetir o replay.

## 4. Classificação offline congelada

Antes de abrir os valores de classificação da saída R4, versionar `scripts/proj_fix_1_classify.py` (versão 1.0), executar seu `--selftest` sintético e registrar o SHA-256 do script e do log do selftest. O selftest não abre CSVs de corrida nem tabelas históricas.

Instrumento congelado: SHA-256 `a8d6b3202c80aa84e7b2af7a522801bf33ff6896e310873400b2d55608d6a73f`. Selftest sintético: `experiments/proj-fix-1/2_classifier_selftest.log`, SHA-256 `edfd299c9e9d364efb837fc41ac47b61df6717302034dd2817a798a0892ebb1f` (PASS). A suíte pós-código mais recente, `experiments/loc-xy-1/5_post_chain_fix_pytest.log`, SHA-256 `7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185`, registra 20 FAILED canônicos, 352 passed e 3 skipped; o ciclo atual não altera o runner nem os testes.

Para cada par de amostras de um mesmo carro adjacentes na ordem de `tick` (as linhas amostradas consecutivas do CSV), calcular `dXY = hypot(body_x_t-body_x_prev, body_y_t-body_y_prev)` e `d_ns = abs(ns_raw_t-ns_raw_prev)`. Classificar com estas condições e prioridade:

1. **C1 — descontinuidade composta:** `dXY >= 30 m` e `d_ns >= 8`.
2. **C2 — divergência física local:** `dXY >= 30 m` e `d_ns < 8`.
3. **C3 — reapontamento na vizinhança:** `dXY < 30 m` e `d_ns >= 8`.
4. **C4-diagnóstico:** linha com valor ausente, não finito ou inválido; contar a linha à parte e não classificar pares que a usam.

Os limiares são inclusivos/exclusivos exatamente como escritos. Linhas e pares são identificados por `(drv,tick)` e `(drv,tick_prev,tick)`. O classificador reporta contagens gerais C1–C4 e, para cada classe, p95 linear de `dXY` e de `d_ns`.

## 5. Reconciliação com FF1b/NIT-2

Fonte histórica congelada: `experiments/fail-forensics-2/veredito/saltos_projecao.csv`, somente linhas do run `composite_monaco_s0`. A identidade do evento é `(drv,tick_prev,tick)`. Mapear cada linha histórica ao par correspondente no replay, sem arredondar ou agrupar. Confirmar mapeamento 1:1 para todas as entradas NIT-2 `abs_projection_error_m >= 10 m` (esperado 112 eventos) e para o headline `>= 30 m` (esperado 45 eventos). A classificação dos 45 eventos deve fechar exatamente entre C1/C2/C3; qualquer evento sem classe, chave duplicada/ausente ou contagem diferente é PARE. Registrar a classe individual de cada evento e as contagens por classe nos dois cortes.

O proxy histórico permanece `abs(Δs_wrapped − Δcum_dist)`. Ele é usado apenas para localizar e reconciliar as entradas NIT-2; as novas classes usam XY físico e `ns_raw`. Esta etapa apenas decompõe os saltos: não recomenda nem implementa correção.

## 6. Fechamento

Versionar replay e log brutos, evidência g1/g2, saída do classificador, relatório de hashes, e atualizações correspondentes em `AUDITORIA_RL.md`, `PROJECT_STATE.md` e worklog. O ciclo termina com a decomposição e aguarda decisão do dono entre RECUP-1 para C1/C2 ou correção de projeção/gate para C3.
