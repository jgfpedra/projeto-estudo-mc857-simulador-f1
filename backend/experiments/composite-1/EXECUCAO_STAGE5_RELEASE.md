# EXECUCAO STAGE 5 — RELEASE: Cerimônia de Desselo e Exame Final do Candidato Residual

**Agente:** Antigravity · **Data:** 2026-10-28 · **Branch:** `feat/sanidade-produto`  
**Freeze da etapa A:** `20c6969aec0506adc5e6c8e75c92567d9c791518` (`20c6969`, owner).  
**Prereg:** `PREREG_STAGE5_RELEASE.md` SHA `89df63f2d3b9d507f3394494fdaf791589c87fabda9f89d406497acc5103ef9c`.  
**Instrumento:** `scripts/eval_composite_residual_test.py` SHA `7dc77bc28461b1f8cb73ff69d3f0e3524febf0da49daa408688f1db468870222` (congelado).  
**Candidato Residual:** `experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz` SHA `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60`.  

---

## 1. Pré-Checks de Integridade (Pré-Execução)

Antes da primeira execução do instrumento, foram validados 100% dos pré-requisitos:
- **Git HEAD:** `20c6969` confirmado.
- **Hashes pré-execução conferidos:**
  - `PREREG_STAGE5_RELEASE.md` == `89df63f2d3b9…` (✓)
  - `scripts/eval_composite_residual_test.py` == `7dc77bc28461…` (✓)
  - `composite_residual_candidato_1_weights.npz` == `6210fff65b19…` (✓)
- **Git Status:** limpo (apenas strays conhecidos `.cursor/` e `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` não rastreados).
- **Inexistência prévia da saída:** `experiments/composite-1/STAGE5_RELEASE_VERDICT.json` confirmado como **AUSENTE** antes do disparo da Leitura 1.
- **Isolamento do Selo:** Zero acesso manual aos shards TEST (`A_A_ON_dump.jsonl_VER.json` e `B_B_ON_dump.jsonl_SAI.json`) fora do instrumento oficial.

---

## 2. Fase B-1 — Leitura 1 (Gravação do Veredicto Oficial)

Execução realizada a partir de `backend/` com `set -o pipefail` e `timeout --signal=TERM 2400s`:
```bash
set -o pipefail && timeout --signal=TERM 2400s \
.venv/bin/python scripts/eval_composite_residual_test.py \
--candidate experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz \
--out experiments/composite-1/STAGE5_RELEASE_VERDICT.json \
2>&1 | tee experiments/composite-1/0_stage5_selo_read1.log
```

- **Exit code:** 0.
- **Arquivo gravado:** `experiments/composite-1/STAGE5_RELEASE_VERDICT.json` (modo exclusivo `"x"`).
- **Log da leitura 1:** `experiments/composite-1/0_stage5_selo_read1.log` (tamanho 0 bytes, execução silenciosa com escrita atômica no arquivo).
- **Contagens verificadas no payload:**
  - Caso A (teste `VER`): 3.000 amostras
  - Caso B (teste `SAI`): 3.000 amostras
  - Total teste: 6.000 amostras

### Shards Revelados no Payload Oficial (Fonte: JSON)
Os hashes SHA-256 dos shards do bucket TEST foram revelados exclusivamente através da leitura pelo instrumento:
- `A_A_ON_dump.jsonl_VER.json`: `5ff4a203792eb4f47d94c403c83cb1a6fc94a6e0440b1ebff1b636a0915111c8`
- `B_B_ON_dump.jsonl_SAI.json`: `4db7f236c8bc40d75dd479bb496b92bb0278c2b88ce8b6a89cd260462a4bef74`

---

## 3. Fase B-2 — Leitura 2 (Auditoria de Determinismo Byte-a-Byte)

Execução realizada a partir de `backend/` sem a flag `--out`, separando stdout e stderr para conferência do Gate 5:
```bash
set -o pipefail && timeout --signal=TERM 2400s \
.venv/bin/python scripts/eval_composite_residual_test.py \
--candidate experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz \
2> experiments/composite-1/0_stage5_selo_read2_stderr.log \
| tee experiments/composite-1/0_stage5_selo_read2_stdout.log
```

- **Exit code:** 0.
- **Log stderr da leitura 2:** `experiments/composite-1/0_stage5_selo_read2_stderr.log` (tamanho 0 bytes, vazio; zero warnings/anomalias).
- **Saída stdout:** gravada em `experiments/composite-1/0_stage5_selo_read2_stdout.log`.

---

## 4. Avaliação dos 5 Gates de Release

A validação dos 5 critérios contratuais pré-ratificados no `PREREG_STAGE5_RELEASE.md` apresentou resultado positivo unânime:

| Gate | Critério Contratual | Valor Medido | Limiar / Alvo | Status |
|---|---|---|---|:---:|
| **Gate 1** | $\text{Huber}(cand) \le 0,80 \times \text{Huber}(null)$ | $0,288527$ (ratio: **0,407721**) | $\le 0,566126$ (ratio $\le 0,80$) | **PASS ✓** |
| **Gate 2** | $\text{MAE}(r_{cand}, r_{target}) < \text{MAE}(0, r_{target})$ | **0,585649** | $< 1,044025$ | **PASS ✓** |
| **Gate 3** | $\text{Média } \|r_{cand}\|_2 \le 2,0$ | **1,598454** | $\le 2,0$ | **PASS ✓** |
| **Gate 4** | $\text{nan\_inf\_count} == 0$ | **0** | $== 0$ | **PASS ✓** |
| **Gate 5** | Determinismo em 2 leituras (JSON bytes idênticos) | `cmp` exit 0 (bytes idênticos) | Bit-a-bit idêntico | **PASS ✓** |

### Verificação do Gate 5 via `cmp`:
```bash
cmp experiments/composite-1/STAGE5_RELEASE_VERDICT.json \
    experiments/composite-1/0_stage5_selo_read2_stdout.log
# Retorno: EXIT 0 (nenhuma divergência de byte)
```

- **SHA-256 do JSON (Leitura 1):** `5159af19052b7327eda73e3a07e4a6e156395508c096a390645d8ec042666049`
- **SHA-256 do stdout (Leitura 2):** `5159af19052b7327eda73e3a07e4a6e156395508c096a390645d8ec042666049`
- **Paridade:** 100% idênticos bit-a-bit.

### Veredicto Oficial do Selo:
$$\mathbf{SANCIONADO} \quad (5/5 \text{ Gates Aprovados})$$

O candidato residual `composite_residual_candidato_1_weights.npz` reduziu a perda Huber offline sobre o bucket TEST em **−59,2%** em relação à baseline nula ($r=0$, que espelha o aluno solo v10 isolado), superando com folga expressiva a meta contratual de 20% de redução (limiar $\le 0,80$).

---

## 5. Tabela Canônica de Métricas

| Métrica | Candidato Residual | Baseline Nula ($r=0$) | Delta / Ratio | Status |
|---|---|---|---|:---:|
| **Huber Loss ($\delta=1.0$)** | 0,288527 | 0,707658 | **0,407721** (−59,2%) | ✓ |
| **MAE no Espaço Residual** | 0,585649 | 1,044025 | **−0,458376** (−43,9%) | ✓ |
| **Norma L2 Média ($\|r\|_2$)** | 1,598454 | 0,000000 | +1,598454 rad/unid | ✓ ($\le 2,0$) |
| **Contagem NaN / Inf** | 0 | 0 | 0 | ✓ |
| **Total Amostras Teste** | 6.000 | 6.000 | 3.000 Caso A / 3.000 Caso B | ✓ |

---

## 6. Proveniência e Rastreabilidade Criptográfica

### Artefatos de Execução e Hashes SHA-256

| Artefato | Papel | SHA-256 |
|---|---|---|
| `STAGE5_RELEASE_VERDICT.json` | Veredicto JSON oficial (Leitura 1) | `5159af19052b7327eda73e3a07e4a6e156395508c096a390645d8ec042666049` |
| `0_stage5_selo_read2_stdout.log` | Saída bruta stdout (Leitura 2) | `5159af19052b7327eda73e3a07e4a6e156395508c096a390645d8ec042666049` |
| `0_stage5_selo_read1.log` | Log da Leitura 1 (stdout/stderr) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 B) |
| `0_stage5_selo_read2_stderr.log` | Log de stderr da Leitura 2 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 B) |

### Commit de Proveniência Formal
- **Commit:** `e017874bda36b641f3c00cf5edd1e677c9545b37` (`e017874`)
- **Mensagem:** `Selo STAGE 5: desselo TEST em 2 leituras (read1 JSON + read2 stdout byte-identico cmp exit 0; gates 4 computadas + gate 5 determinismo; cand 6210fff6; shas de shards revelados no payload)`
- **Conteúdo:** os 4 arquivos de log e veredicto acima (`git add -f`).

---

## 7. Disclosures e Declarações Formais

1. **ZERO leitura do TEST fora das 2 execuções:** Nenhuma ferramenta manual (`cat`, `head`, `grep`, `jq`, `python -c` ou hashers manuais) tocou os shards de teste `A_A_ON_dump.jsonl_VER.json` ou `B_B_ON_dump.jsonl_SAI.json`. O acesso ocorreu unicamente através das duas execuções estritas do instrumento oficial.
2. **Orçamento exato cumprido:** Foram executadas **exatamente 2 leituras** do instrumento e gerado **exatamente 1 commit** de proveniência. Zero terceira execução, zero re-runs.
3. **Produção intocada:** O diretório de pesos de produção (`backend/model_train/v15_residual/`) e o dicionário `PROFILES` de corrida em `run_race_10_cars.py` **NÃO FORAM MODIFICADOS**. A promoção é uma etapa solene separada condicionada a assinatura do dono.
4. **Zero treino, zero corrida, zero pip:** Nenhuma nova corrida foi disparada, nenhum treino foi realizado e o ambiente Python `.venv` permaneceu intacto.

---

## 8. Apêndice do dono — verificação independente e closing (2026-10-28)

Verificação executada pelo dono sobre os bytes commitados em `e017874` e o estado staged, **SEM** tocar no bucket TEST:

1. **Commit de proveniência com conteúdo exato:** `e017874` contém EXATAMENTE os 4 artefatos (JSON + 3 logs); nada além. Strays no estado: somente os 2 conhecidos e protetorados (`.cursor/`, `ANEXO_SAIDAS_1_ERRATAS.md`).
2. **Gate 5 provado em 2ª via pelo dono:** `cmp` do dono sobre os bytes commitados → exit 0; `STAGE5_RELEASE_VERDICT.json` e `0_stage5_selo_read2_stdout.log` = mesmo SHA `5159af19…049` (1.834 B ×2). Os logs `read1`/`stderr` = `e3b0c442…` (SHA-256 do vazio, 0 B) — isso NÃO é anomalia: é o comportamento CONTRATUAL do instrumento (modo `--out` não escreve nada no stdout/stderr; qualquer byte ali seria suspeito).
3. **Coerência criptográfica do payload:** `provenance.git_head_sha` = hash completo do freeze `20c6969aec0506adc5e6c8e75c92567d9c791518` → prova de que o desselo ocorreu ESTRITAMENTE pós-freeze; `script_sha256` = `7dc77bc2…` (SHA frozen, ainda == disco no closing → instrumento intocado pós-freeze); `candidate.sha256` == etalão `6210fff6…` (npz re-hashado pelo dono no closing); produção `v15_residual/residual_best_weights.npz` re-hashada `6a2dbf53…` — INTOCADA; counts 6.000 = 3.000 + 3.000.
4. **Aritmética das métricas recomputada:** 1 − 0,407721 = 0,5923 → **−59,2% Huber** ✓; MAE −43,9% ✓; limiar 0,8 × 0,707658 = 0,566126 ✓; ratio VAL→TEST 0,353 → 0,408 e MAE 0,470 → 0,586 e ‖r‖ 1,422 → 1,598 — degradação plausível val→holdout, ainda 2× dentro dos limiares; zero NaN/Inf. Nenhum número "bom demais para ser verdade"; o TEST confirmou o VAL sem heroísmo.
5. **Não-interferência do dono com o selo:** o dono NÃO executou 3ª leitura do instrumento (orçamento contratual = EXATAMENTE 2 execuções; "rerun pós-gate" = PARE por §6-6) e NÃO fez acesso manual aos shards (nem `stat`, nem `sha256sum`, nem `cat`). A propriedade de desselo em leitura única fica preservada no registro; re-derivação futura do veredicto é possível pela execução determinística do próprio instrumento (os SHAs dos shards agora são proveniência commitada) e exigiria nova emenda assinada do dono.
6. **Ledgers:** +1 linha IDÊNTICA byte-a-byte nos 3 (md5 `c036c0dd…` ×3, texto conforme §B-3) — commitadas pelo dono neste closing.
7. **Suíte:** nenhuma corrida nesta etapa → g0 permanece `460 = 20F/437P/3S` (fail-set canônico); collect com os 2 testes do instrumento = 462. Nenhuma mudança de código desde `20c6969`.
8. **Leitura honesta:** o sello sanciona o candidato no espaço residual OFFLINE (o release gate do ciclo); o histórico de pista do BASE-2 permanece — contatos −86,0% Interlagos / −69,8% Monaco vs blind, hesitações quase ao nível do blind, pace Interlagos quase recuperado, custo `fora` persistente (26,4/49,9 pp acima do blind; pior que B3.1 em Monaco). O sello NÃO promove nada sozinho.

**Veredicto do dono: ESTÁGIO 5 FECHADO (alínea a — tudo conforme, nenhuma PARE acionada). CANDIDATO RESIDUAL SANCIONADO PELO SELLO (5/5 gates). O ciclo COMPOSITE completo (COLLECT-1 → BASE-1 → TRAIN-1 → BASE-2 → STAGE 5) fechou com ZERO PAREs. A promoção a produção é um mini-estágio SEPARADO com prereg assinado pelo dono — não é automática.**
