# PREREG STAGE 6 — PROMOÇÃO: a produção assume o candidato SANCIONADO

**Versão:** 1.0 · **Estado:** pré-freeze; ZERO troca, ZERO backup, ZERO corrida nesta etapa; ZERO edição de código · **Data:** 2026-10-28 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `227c9ba63e08a763388f5be8bf22658ac0d97ad3` (`227c9ba`, closing do STAGE 5), esperado. **Index:** limpo (apenas os 2 strays protetorados: `.cursor/` e `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` — NUNCA commit).

---

## 1. Contexto

1. **STAGE 5 fechado com veredicto SANCIONADO** (5/5 gates): veredicto oficial `experiments/composite-1/STAGE5_RELEASE_VERDICT.json` SHA `5159af19052b7327eda73e3a07e4a6e156395508c096a390645d8ec042666049`; desselo em `e017874`; closing `227c9ba`. O ciclo COMPOSITE (COLLECT-1 → BASE-1 → TRAIN-1 → BASE-2 → STAGE 5) fechou com ZERO PAREs.
2. O sello sanciona o candidato no espaço residual OFFLINE. A produção continua o baseline B3.1. Esta etapa executa a **primeira promoção de pesos do ciclo**.
3. **Registro de desenho do dono (pré-freeze):** `test_composite_parity.py::test_residual_numpy_equals_keras_on_random_inputs` RODA na suíte (TF disponível no venv — import verificado) e compara o npz carregado de produção contra o `residual_best.keras` FIXO (B3.1). Trocar o npz sozinho **quebraria a suíte**. A promoção é, portanto, do **PAR (npz + keras)**, com backup dos dois. O caminho de CORRIDA usa somente o npz (`PROFILES['race'/'composite'].residual_npz` → `scripts/run_race_10_cars.py:77-78/83-84`), sem entrada keras-residual — runtime e suíte permanecem coerentes.
4. **PROFILES e TODOS os .py permanecem intocados:** os NOMES de arquivo de produção são preservados (`residual_best_weights.npz` / `residual_best.keras`); o CONTEÚDO passa a ser o do sancionado. Os arquivos irmãos `residual_weave_*` de `v15_residual/` NÃO são tocados.

## 2. Objetivo e veredicto

Promover o candidato sancionado a produção com **prova física de equivalência** (determinismo de corrida): backup byte-verificado → troca byte-verificada → g0 pós-promoção idêntico ao canônico → R1''/R3'' (SEM `--residual-override`) reproduzindo byte-a-byte os CSVs/events de R1'/R3' do BASE-2 → linha nativa do runner exibindo o SHA do sancionado.

- **PROMOVIDO:** todos os gates PASS.
- **PARE:** qualquer falha → parar, preservar TODOS os artefatos, reportar, handoff; NADA é revertido pela etapa (a reversão é ato do dono no closing: restaurar produção do backup byte-verificado, via commit separado).

## 3. Par promovido e backups (pins cravados)

| Papel | Caminho | SHA-256 |
|---|---|---|
| Produção npz (ATUAL = B3.1) | `model_train/v15_residual/residual_best_weights.npz` | `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` |
| Produção keras (ATUAL = B3.1) | `model_train/v15_residual/residual_best.keras` | `5a2c20cedf90b6cccfd5551c3e2e7e5fd9d99f767a12ea284b75b0299349ee3a` |
| Candidato npz (SANCIONADO) | `experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz` | `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` |
| Candidato keras (SANCIONADO) | `experiments/composite-1/train-1/composite_residual_candidato_1.keras` | `f237ac9e382a7c5f73b6c37dcbf9c0e0473bd49b8d259cb79e2d2408accb1b0d` |

Fontes de comparação (BASE-2, commitados em `ab9da45`/`3a02c11`): `base-2/1_R1_INTERLAGOS_RACE.csv` `bc87d615…ce4c76` + `_events.csv` `7351454f…d7ced9a`; `base-2/3_R3_MONACO_RACE.csv` `dfe7b2dc…4669b5` + `_events.csv` `fa49a252…2b59a40`. g0 canônico: `base-2/0_full_suite_base_2.log` SHA `406952d3e5707af32e12a9269086fbddd6fc5fee52b2c4ba58055ff39a3ed707`.

## 4. Matriz de execução da etapa B (orçamento EXATO)

**Orçamento: EXATAMENTE 2 backups + 2 trocas + 1 g0 + 2 corridas + 2 commits; NADA além (sem extração `base_metrics`, sem instrumento novo, sem terceira corrida, sem rerun).** Commits só DEPOIS de TODOS os gates PASS; em PARE nada é commitado.

### P-0 — Pré-checks (nenhum dado novo é criado)
- HEAD == `227c9ba63e08a763388f5be8bf22658ac0d97ad3`; `git status` limpo (só strays conhecidos).
- Os 4 SHAs da §3 byte-exatos no disco. QUALQUER divergência = PARE.
- Confirmar que `experiments/composite-1/promocao-1/` e `archive/residual_promocao_stage6/` NÃO existem (preexistência = PARE, regra B.1).
- **Disclosure esperado:** após P-2, `git status` mostra `M` nos 2 arquivos de produção — isso é o estado NORMAL do estágio, não é PARE.

### P-1 — Backup solene (B3.1 preservado; NUNCA deletar)
```bash
mkdir -p archive/residual_promocao_stage6
cp model_train/v15_residual/residual_best_weights.npz archive/residual_promocao_stage6/residual_best_weights_B31_backup.npz
cp model_train/v15_residual/residual_best.keras archive/residual_promocao_stage6/residual_best_B31_backup.keras
```
Gate: sha256 dos 2 backups == pins da §3 (byte-exato). Divergência = PARE ANTES de qualquer troca.

### P-2 — Troca controlada (produção = sancionado)
```bash
cp experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz model_train/v15_residual/residual_best_weights.npz
cp experiments/composite-1/train-1/composite_residual_candidato_1.keras model_train/v15_residual/residual_best.keras
```
Gate: sha256 dos 2 arquivos de produção == pins do candidato (byte-exato). Se qualquer verificação pós-troca falhar: PARE imediato; a ÚNICA recuperação autorizada é restaurar a produção a partir do backup byte-verificado de P-1 e parar.

### P-3 — g0 pós-promoção
```bash
mkdir -p experiments/composite-1/promocao-1
set -o pipefail && timeout --signal=TERM 2400s .venv/bin/python -m pytest -q tests 2>&1 | tee experiments/composite-1/promocao-1/0_full_suite_promocao_1.log
```
Esperado: `460 itens = 20 failed / 437 passed / 3 skipped` com o fail-set canônico EXATO (diff bit-a-bit do fail-set vs `base-2/0_full_suite_base_2.log`; nenhuma falha nova — o teste de paridade npz↔keras DEVE continuar PASS com o PAR promovido). Exit 1 do pytest é o histórico esperado; o gate é o CONTEÚDO.

### P-4 — Corridas de prova (UMA por vez; NUNCA paralelo; antes de cada largada confirmar que main CSV, events e log NÃO existem)
R1'' Interlagos (comando EXATO do BASE-2 §2, a ÚNICA remoção é `--residual-override`):
```bash
set -o pipefail && timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.csv 2>&1 | tee experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.log
```
R3'' Monaco: idem com `--track Monaco`, outs `experiments/composite-1/promocao-1/3_R3_MONACO_RACE.csv` / `.log`.

## 5. Gates (pré-ratificados pelo dono)

| Gate | Critério | Como verificar |
|---|---|---|
| **g0** (pós-promoção) | 460 itens = 20F/437P/3S, fail-set canônico exato | contagem + diff do fail-set vs g0 base-2 |
| **g1** | exit 0 nas 2 corridas | código de saída |
| **g2** | main CSV com EXATAS 30.002 linhas físicas + `*_events.csv` presente + sumário do runner no log | `wc -l`, ls, grep dos blocos de summary |
| **g3** | `[diag] residual baseline sha256=6210fff65b19ad0e` presente EXATAMENTE 1× em cada log de corrida; `RESIDUAL OVERRIDE (candidato)` AUSENTE (== 0); `RESIDUAL BASELINE (r2)` também ausente (só existe com override) | `grep -c` |
| **g4** | cmp ×4 byte-a-byte: `promocao-1/1_R1…csv` vs `base-2/1_R1…csv`; events ×2; `3_R3_MONACO_RACE.csv` + events | `cmp` exit 0 em TODOS |

Logs NÃO são gate de byte-identidade (timestamps): divergem dos logs do BASE-2 nos blocos de linhas residuais (por desenho — linhas 6-8 do log do BASE-2) e timestamps. Qualquer outra divergência estrutural de log = anomaly a reportar.

## 6. Proveniência (EXATAMENTE 2 commits)

**Commit A** (promoção + g0): `git add archive/residual_promocao_stage6/residual_best_weights_B31_backup.npz archive/residual_promocao_stage6/residual_best_B31_backup.keras model_train/v15_residual/residual_best_weights.npz model_train/v15_residual/residual_best.keras` + `git add -f experiments/composite-1/promocao-1/0_full_suite_promocao_1.log` — mensagem: `Promocao STAGE 6: backup B3.1 (6a2dbf53/5a2c20ce) em archive + PAR candidato (6210fff6/f237ac9e) assume producao + g0 pos 460=20F/437P/3S failset canonico`.

**Commit B** (corridas de prova): `git add -f` dos 6 artefatos R1''/R3'' (main/events/log ×2) — mensagem: `Provenance STAGE 6 corridas R1''/R3'' sem override: cmp CSV+events byte-a-byte vs BASE-2 exit 0; residual baseline sha256=6210fff65b19ad0e = producao carrega o sancionado`.

**EXECUCAO_STAGE6_PROMOCAO.md** (executor escreve; STAGED, SEM commit — dono commita no closing): pré-checks; P-1/P-2 com SHAs antes/depois; g0 com contagem + diff do fail-set; tabela de gates g1–g4 com o resultado dos cmp ×4 e do grep do g3; disclosures fiéis. **Ledgers:** +1 linha IDÊNTICA em cada um (`backend/PROJECT_STATE.md`, `worklog.md`, `backend/model_train/AUDITORIA_RL.md`) com CAMINHOS ABSOLUTOS (o trap cwd-flip já mordeu 2× nesta fábula), UNCOMMITTED. Handoff `ai-memory` no wrap-up.

## 7. Forma canônica

Corrida única, foreground, `set -o pipefail`, `tee`, `timeout --signal=TERM 2400s`; worktree principal `…/backend`; branch `feat/sanidade-produto`; venv nativo `.venv/bin/python` — NUNCA pip; `git add -f` sob `experiments/` (`archive/` e `model_train/` são tracked normais); pré-existência aborta (regra B.1); zero paralelismo.

## 8. PAREs (gatilhos de aborto imediato)

1. Qualquer pin divergente em P-0 (HEAD, SHAs, preexistência de diretórios).
2. Backup com SHA divergente do pin de origem (PARE antes da troca).
3. Troca com SHA divergente do pin do candidato (PARE; única recuperação: restaurar produção do backup byte-verificado e parar).
4. g0 pós-promoção ≠ 460/20F/437P/3S ou fail-set ≠ canônico (QUALQUER teste novo a falhar — inclusive paridade — é PARE).
5. Corrida com exit ≠ 0, linhas ≠ 30.002, sidecar ausente ou sumário ausente.
6. g3 divergente: `residual baseline sha256` sem `6210fff65b19ad0e` (fallback silencioso ou troca falha), ou linha `RESIDUAL OVERRIDE` presente (flag que não foi passada).
7. `cmp` divergente em qualquer um dos 4 pares = promoção NÃO provada = PARE (preservar tudo; dono decide reversão no closing).
8. Corrida além das 2; rerun de qualquer fase pós-gate; extração/métricas extras; instrumento novo; edição de QUALQUER código (PROFILES/run_race/race_diagnostic intocados); promoção de terceiros artefatos (ex.: `residual_weave_*`); pip; `--profile race` (alias quebrado — NUNCA usar); tocar quarentena base-1, shards, anexo; commit de EXECUCAO/ledgers.
