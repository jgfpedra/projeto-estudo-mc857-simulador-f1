# EXECUCAO STAGE 6 — PROMOÇÃO: O Candidato Sancionado Assume a Produção

**Agente:** Antigravity · **Data:** 2026-10-28 · **Branch:** `feat/sanidade-produto`  
**Freeze da etapa A:** `8fb53d55829d812a17b7cde2d92d86b73ea63d34` (`8fb53d5`, owner).  
**Prereg:** `PREREG_STAGE6_PROMOCAO.md` SHA `b9c3f8368a50e882953bc52a0ed0dd393f83d2cc60b715e28689efc78eefd249`.  

---

## 1. Pré-Checks P-0 (Pré-Execução)

Todos os pré-checks foram confirmados com paridade estrita antes de qualquer modificação no sistema de arquivos:
- **Git HEAD:** `8fb53d5` (✓)
- **Status inicial:** limpo (apenas strays conhecidos `.cursor/` e `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` não rastreados).
- **SHAs pré-execução conferidos no disco (4/4):**
  - Produção atual npz (B3.1): `model_train/v15_residual/residual_best_weights.npz` == `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` (✓)
  - Produção atual keras (B3.1): `model_train/v15_residual/residual_best.keras` == `5a2c20cedf90b6cccfd5551c3e2e7e5fd9d99f767a12ea284b75b0299349ee3a` (✓)
  - Candidato sancionado npz: `experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz` == `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` (✓)
  - Candidato sancionado keras: `experiments/composite-1/train-1/composite_residual_candidato_1.keras` == `f237ac9e382a7c5f73b6c37dcbf9c0e0473bd49b8d259cb79e2d2408accb1b0d` (✓)
- **Inexistência prévia de diretórios:** `experiments/composite-1/promocao-1/` e `archive/residual_promocao_stage6/` confirmados como inexistentes (✓).

---

## 2. Fases P-1 e P-2 — Backup Solene e Troca Controlada

### P-1: Backup Solene de B3.1
Os arquivos de produção vigentes foram preservados em `archive/residual_promocao_stage6/`:
- `archive/residual_promocao_stage6/residual_best_weights_B31_backup.npz`
  - SHA-256 medido: `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` (idêntico ao pin de origem B3.1 ✓)
- `archive/residual_promocao_stage6/residual_best_B31_backup.keras`
  - SHA-256 medido: `5a2c20cedf90b6cccfd5551c3e2e7e5fd9d99f767a12ea284b75b0299349ee3a` (idêntico ao pin de origem B3.1 ✓)

### P-2: Troca Controlada (Produção = Sancionado)
O PAR candidato sancionado assumiu os caminhos canônicos de produção:
- `model_train/v15_residual/residual_best_weights.npz`
  - SHA-256 pós-troca: `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` (idêntico ao candidato ✓)
- `model_train/v15_residual/residual_best.keras`
  - SHA-256 pós-troca: `f237ac9e382a7c5f73b6c37dcbf9c0e0473bd49b8d259cb79e2d2408accb1b0d` (idêntico ao candidato ✓)

---

## 3. Fase P-3 — g0 Pós-Promoção

Execução da suíte completa de testes pós-promoção:
- **Log:** `experiments/composite-1/promocao-1/0_full_suite_promocao_1.log`
- **Resultado:** 20 failed, 439 passed, 3 skipped em 201.16s (462 itens coletados, com os 2 testes novos de `test_eval_composite_residual_test.py`).
- **Fail-set canônico EXATO:** diff bit-a-bit da lista `^FAILED` vs `base-2/0_full_suite_base_2.log` retornou **zero diferenças** (`FAILSET_IDENTICAL_BIT_BY_BIT`).
- **Teste de paridade NPZ↔Keras:** `test_composite_parity.py::test_residual_numpy_equals_keras_on_random_inputs` passou sem falhas, validando a coerência do par promovido em conjunto.
- Exit code 1 do pytest esperado e histórico.

---

## 4. Fase P-4 — Corridas de Prova e Gates g1–g4

As corridas R1'' e R3'' foram disparadas de forma serial, em foreground, **sem `--residual-override`**, carregando a produção recém-promovida via `--profile composite`:

| Prova | Circuito | Linhas Main CSV | Events CSV | Exit | g3 (Linha Nativa) | g4 (`cmp` vs BASE-2) |
|---|---|---|---|:---:|---|:---:|
| **R1''** | Interlagos | 30.002 | Presente (4.390 ev) | 0 | `residual baseline sha256=6210fff65b19ad0e` (1×) · Override AUSENTE (0×) | **`cmp` CSV: exit 0 ✓**<br>**`cmp` Events: exit 0 ✓** |
| **R3''** | Monaco | 30.002 | Presente (8.493 ev) | 0 | `residual baseline sha256=6210fff65b19ad0e` (1×) · Override AUSENTE (0×) | **`cmp` CSV: exit 0 ✓**<br>**`cmp` Events: exit 0 ✓** |

### Auditoria Detalhada dos Gates g1 a g4:
1. **g1 (Exit 0):** R1'' exit 0, R3'' exit 0.
2. **g2 (Estrutura):** Ambos com exatamente 30.002 linhas físicas no main CSV, sidecars de eventos completos e blocos de sumário de encerramento presentes nos logs.
3. **g3 (Rastreio de Produção no Log):**
   - R1'': `grep -c "residual baseline sha256=6210fff65b19ad0e" == 1`; `grep -c "RESIDUAL OVERRIDE" == 0`; `grep -c "RESIDUAL BASELINE (r2)" == 0`.
   - R3'': `grep -c "residual baseline sha256=6210fff65b19ad0e" == 1`; `grep -c "RESIDUAL OVERRIDE" == 0`; `grep -c "RESIDUAL BASELINE (r2)" == 0`.
4. **g4 (Determinismo Físico Absoluto via `cmp` ×4):**
   - `cmp promocao-1/1_R1_INTERLAGOS_RACE.csv base-2/1_R1_INTERLAGOS_RACE.csv` → **EXIT 0** (`bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76`)
   - `cmp promocao-1/1_R1_INTERLAGOS_RACE_events.csv base-2/1_R1_INTERLAGOS_RACE_events.csv` → **EXIT 0** (`7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a`)
   - `cmp promocao-1/3_R3_MONACO_RACE.csv base-2/3_R3_MONACO_RACE.csv` → **EXIT 0** (`dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5`)
   - `cmp promocao-1/3_R3_MONACO_RACE_events.csv base-2/3_R3_MONACO_RACE_events.csv` → **EXIT 0** (`fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40`)

---

## 5. Proveniência e Commits Realizados

- **Commit A:** `c8270a5`  
  *Mensagem:* `Promocao STAGE 6: backup B3.1 (6a2dbf53/5a2c20ce) em archive + PAR candidato (6210fff6/f237ac9e) assume producao + g0 pos 460=20F/437P/3S failset canonico`  
  *Arquivos:* backups npz e keras em archive + produção npz e keras modificados + log do g0.
- **Commit B:** `608e671`  
  *Mensagem:* `Provenance STAGE 6 corridas R1''/R3'' sem override: cmp CSV+events byte-a-byte vs BASE-2 exit 0; residual baseline sha256=6210fff65b19ad0e = producao carrega o sancionado`  
  *Arquivos:* os 6 artefatos das corridas de prova R1'' e R3''.

---

## 6. Disclosures e Declarações Formais

1. **Equivalência física comprovada:** As corridas executadas puramente com a nova produção (`--profile composite`) reproduziram bit-a-bit os dados de telemetria e eventos de contato das corridas que usaram `--residual-override` no BASE-2.
2. **Orçamento exato cumprido:** Exatamente 2 backups, 2 trocas, 1 g0, 2 corridas e 2 commits. Zero execuções extras, zero retries.
3. **Código fonte intocado:** Nenhuma linha de código (`.py`), nem `residual_weave_*`, nem `PROFILES` foi modificada.

---

## 7. Apêndice do dono — verificação independente e closing (2026-10-28)

Verificação executada pelo dono sobre os bytes commitados em `c8270a5`/`608e671` e o estado staged:

1. **Commits com conteúdo exato:** `c8270a5` = EXATAMENTE 5 arquivos (2 backups + 2 de produção + log do g0); `608e671` = EXATAMENTE os 6 artefatos de corrida. **ZERO `.py` modificado desde `227c9ba`** (diff `--name-only` verificado pelo dono) — PROFILES, `run_race_10_cars.py`, `race_diagnostic.py` e `residual_weave_*` intocados.
2. **8/8 SHAs recomputados byte-exato pelo dono:** backups == pins B3.1 (`6a2dbf53…`/`5a2c20ce…`); produção pós-troca == pins do sancionado (`6210fff6…`/`f237ac9e…`); os 4 CSVs/events de prova == pins do BASE-2 (`bc87d615…`/`7351454f…`/`dfe7b2dc…`/`fa49a252…`).
3. **g3 pelo dono (grep próprio):** `residual baseline sha256=6210fff65b19ad0e` == 1× em cada log; `RESIDUAL OVERRIDE (candidato)` == 0 e `RESIDUAL BASELINE (r2)` == 0 em ambos — a produção carrega o sancionado diretamente, sem override e sem fallback silencioso.
4. **g2 pelo dono:** 30.002 linhas físicas ×2 (wc próprio); events 4.392/8.495 linhas == BASE-2.
5. **g0 — EMENDA DE CONTAGEM DO DONO (disclosure):** o log real é `20 failed, 439 passed, 3 skipped in 201.16s` = **462 itens** (os 460 canônicos + os 2 testes do instrumento do STAGE 5, ambos PASS). O pin do §4 P-3 do prereg ("460 = 20F/437P/3S") era **erro de desenho do dono** — a contagem da era BASE-2 foi herdada sem somar os 2 testes novos do selo na coleta (que o próprio STAGE 5 pinou: collect 462). O EXECUCAO cravou o número REAL em vez de forçar o pin errado — conduta correta. O gate SUBSTANTIVO cumpriu-se integralmente: fail-set canônico bit-a-bit idêntico ao g0 do base-2 (diff do dono: zero diferenças), zero falhas novas, paridade npz↔keras PASS com o PAR promovido. A linha de ledger (sugerida pelo dono com o número errado) foi **corrigida pelo dono antes do closing** para 462=20F/439P/3S, mantendo as 3 idênticas (md5 ×3).
6. **Determinismo físico duplo (a prova da promoção):** os CSVs/events de R1''/R3'' — corridas com a produção PROMOVIDA carregada nativamente, SEM `--residual-override` — são byte-a-byte os de R1'/R3' do BASE-2 (corridas com override do candidato). O caminho de produção carrega EXATAMENTE os pesos sancionados; mesmos 107/210 contatos, mesmas 44/31 voltas, zero mudança de comportamento em pista — provado por bytes, não por narrativa.
7. **Estado final do produto:** `model_train/v15_residual/` = PAR sancionado (npz `6210fff6…` + keras `f237ac9e…`); B3.1 preservado e commitado em `archive/residual_promocao_stage6/` (NUNCA deletar — precedente Monaco_v1); suíte 462 itens com o fail-set canônico de 20 estável desde 1E; strays protetorados intocados; shards TEST permanecem com SHAs agora públicos (proveniência do selo), quarentena intocada.
8. **Veredicto do dono: STAGE 6 FECHADO (alínea a — tudo conforme, nenhuma PARE acionada; 1 emenda de contagem do dono registrada no item 5). CANDIDATO RESIDUAL PROMOVIDO À PRODUÇÃO COM PROVA FÍSICA BYTE-A-BYTE. O CICLO COMPOSITE COMPLETO (COLLECT-1 → BASE-1 → TRAIN-1 → BASE-2 → STAGE 5 → STAGE 6) FECHADO COM ZERO PAREs.**
