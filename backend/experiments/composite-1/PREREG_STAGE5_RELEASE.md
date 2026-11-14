# PREREG STAGE 5 — RELEASE: Exame Final do Candidato Residual sob o Bucket TEST

**Versão:** 1.0 · **Estado:** pré-freeze; ZERO leitura do bucket TEST (nem uma linha); ZERO treino; ZERO corrida; ZERO promoção; commit nenhum nesta etapa · **Data:** 2026-10-28 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `d36a0e124ca25ceb9e014513e741d55e7f812ca4` (`d36a0e1`), esperado. **Index:** limpo (arquivos não rastreados de fases anteriores ignorados; nenhum `.py` de produção editado).

---

## 1. Contexto e Histórico

1. **COMPOSITE-BASE-2 fechado e ratificado** (closing `d36a0e1`):
   - O candidato residual demonstrou o perfil mais forte já medido em pista contra o controle blind (`v10 edge`):
     - Contatos: **−86,0%** em Interlagos (107 vs 764) e **−69,8%** em Monaco (210 vs 696).
     - Hesitações: **+1** em Interlagos (3 vs 2) e **−3** em Monaco (5 vs 8).
     - Ritmo de corrida (pace) em Interlagos quase totalmente recuperado (44 voltas vs 49 blind; vs 41 do baseline B3.1).
     - Custos observados: saídas de pista (fora) nas duas pistas ficaram acima do blind (+3,8 pp em Interlagos; +2,4 pp em Monaco) e em Monaco o fora ficou acima do B3.1 (+4,5 pp).
   - Conforme contratado no PREREG BASE-2, **nenhum gate de corrida foi pré-contratado** naquele estágio (o ciclo mediu; o ganho Huber offline de −64,7% foi formulado sob BC com $g=1$, enquanto na pista o gate dinâmico $g \in [0,1]$ modula a atuação).
   - A decisão de release do ciclo COMPOSITE pertence exclusiva e soberanamente a este **ESTÁGIO 5**.

2. **Candidato Residual Etalonado para o Exame:**
   - Artefato: `experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz`
   - SHA-256 etalonado: `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60`
   - O candidato é rigorosamente byte-idêntico à sua réplica (`train-1/composite_residual_replica_1_weights.npz`), gerado sob sementes fixadas e op-determinism no ciclo TRAIN-1.

3. **Bucket TEST Selado:**
   - Shards de teste: `A_A_ON_dump.jsonl_VER.json` (Caso A, piloto VER, 3.000 registros) + `B_B_ON_dump.jsonl_SAI.json` (Caso B, piloto SAI, 3.000 registros) = **6.000 registros**.
   - Selado desde a coleta com protocolo `rank-80/10/10-per-run-v1` (PREREG CORPUS 1).
   - O bucket TEST tem **AGORA UMA LEITURA AUTORIZADA**: exclusivamente via o instrumento oficial `scripts/eval_composite_residual_test.py`, e **ESTRITAMENTE DEPOIS do freeze do dono (Etapa B)**.
   - **Zero leitura pré-freeze** — nem smell, nem `head`, nem `grep`, nem `ls` dos registros. Intocabilidade absoluta até a autorização de execução na Etapa B.

---

## 2. Objetivo

1. Realizar o **exame final do candidato residual** etalonado computando os gatilhos de release pré-ratificados diretamente sobre os **6.000 registros do bucket TEST**, com contagens estritas por shard.
2. Esta é a **ÚNICA** leitura autorizada do bucket TEST de todo o ciclo composite.
3. **SEM retreino:** o instrumento é puramente inferencial em NumPy puro; zero gradiente, zero otimizador, zero ajuste de parâmetros.
4. **SEM corrida:** nenhuma simulação dinâmica em pista ocorre neste estágio.
5. **A PROMOÇÃO É UMA ETAPA SEPARADA:** a promoção do candidato para produção (`model_train/v15_residual/`) é um ato solene e separado, condicionado a assinatura explícita do dono PÓS-veredicto. Neste ciclo, qualquer alteração em arquivos de produção ou em `PROFILES` segue **ESTRITAMENTE PROIBIDA**. O instrumento emitirá veredicto de avaliação recomendando ou não a liberação.

---

## 3. Gates de Release (Pré-Ratificados pelo Dono)

Os critérios de liberação estendem as bases contratuais ratificadas na Emenda O-1 do TRAIN-1, agora avaliadas sobre o conjunto de teste não visto (TEST split):

| Gate | Critério | Métrica / Condição | Formulação |
|---|---|---|---|
| **Gate 1** | **Huber Improvement Ratio** | $\text{Huber}(cand) \le 0,80 \times \text{Huber}(null\ r=0)$ | Perda Huber ($\delta=1.0$) do candidato no resíduo deve ser pelo menos 20% menor que a perda nula ($r=0$). |
| **Gate 2** | **MAE Residual vs Baseline Nula** | $\text{MAE}(r_{cand}, r_{target}) < \text{MAE}(0, r_{target})$ | O erro absoluto médio das predições residuais deve ser estritamente inferior ao MAE da ação residual nula. |
| **Gate 3** | **Magnitude Média Limitada** | $\text{Média } \|r_{cand}\|_2 \le 2,0$ | A norma L2 média dos vetores residuais preditos deve ser contida em até 2,0 rad/unid. |
| **Gate 4** | **Finitude Numérica Estrita** | $\text{nan\_inf\_count} == 0$ | Zero ocorrência de `NaN`, `+Inf` ou `-Inf` em qualquer predição ou cálculo. |
| **Gate 5** | **Determinismo do Instrumento** | $2 \text{ leituras com JSON bytes idênticos}$ | Comparação byte-a-byte estrita entre as leituras (Run 1 com `--out` vs Run 2 stdout). |

### Regra de Veredicto

- **SANCIONADO:** A aprovação em **5/5 gates** sanciona tecnicamente o candidato pelo selo para recomendação de release.
- **NÃO LIBERADO:** A falha em **qualquer um** dos 5 gates resulta imediatamente em veredicto negativo (`NAO_LIBERADO`). Sem retry, sem novo treino, sem afrouxamento de limiares neste ciclo.

---

## 4. Protocolo de Execução da Etapa B (Orçamento Exato)

A etapa B executará exatamente **duas leituras** sequenciais do instrumento oficial, sem processos concorrentes e sem intermediários:

1. **Leitura 1 (Gravação do Veredicto Formal):**
   ```bash
   .venv/bin/python scripts/eval_composite_residual_test.py \
     --candidate experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz \
     --out experiments/composite-1/STAGE5_RELEASE_VERDICT.json
   ```
   - O arquivo de saída é criado com flag exclusiva de escrita (`open(..., "x")`). Se o arquivo já existir, a execução é abortada imediatamente (`FileExistsError`).

2. **Leitura 2 (Auditoria de Determinismo via stdout):**
   ```bash
   .venv/bin/python scripts/eval_composite_residual_test.py \
     --candidate experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz
   ```
   - Emite o JSON formatado diretamente na saída padrão (stdout).
   - O hash SHA-256 e os bytes da saída padrão devem ser **idênticos bit-a-bit** ao arquivo `STAGE5_RELEASE_VERDICT.json` gravado na Leitura 1.

---

## 5. Instrumento de Avaliação (`scripts/eval_composite_residual_test.py`)

O instrumento foi projetado como o espelho rigoroso e invertido de `train_composite_residual.py`:

1. **Gate Inverso de Shards:**
   - Whitelist estrita: apenas `A_A_ON_dump.jsonl_VER.json` e `B_B_ON_dump.jsonl_SAI.json` são aceitos.
   - Qualquer tentativa de carregar shards de treino, de validação ou arquivos desconhecidos causa erro fatal imediato (`SealedTestWhitelistViolationError`).
2. **Checagem de Integridade do Candidato:**
   - O hash SHA-256 do arquivo `--candidate` é conferido contra o etalão `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60`. Divergência gera `CandidateWeightsIntegrityError`.
3. **Inferência Forward em NumPy Puro:**
   - Carrega as matrizes do NPZ (`res_d1_0`, `res_d1_1`, `res_d2_0`, `res_d2_1`, `res_out_0`, `res_out_1`).
   - Executa a propagação direta 16 → 128 (ReLU) → 128 (ReLU) → 2 (Linear) idêntica à de `NumpyCompositeActor._residual_forward`.
   - Zero código de otimização, zero retropropagação.
4. **Proteção de Saída e Prevenção de Colisão:**
   - Proibição absoluta de caminhos de produção (`v15_residual`, `v10_dagger`, etc.) ou subdiretórios de treino (`train-1`).
   - Obrigação de residência sob `experiments/`.
   - Gravação atômica em modo exclusivo `"x"` via `json.dump(sort_keys=True, indent=2)`.
5. **Auditoria Criptográfica Completa:**
   - O JSON de veredicto ancora: SHA do candidato, SHA dos dois shards test (revelados somente na leitura da Etapa B), SHA do próprio script e SHA do commit git HEAD.

---

## 6. Lista Exaustiva de PAREs (Gatilhos de Aborto Imediato)

Qualquer uma das seguintes ocorrências constitui violação contratual grave e encerra imediatamente a operação:

1. **Leitura pré-freeze:** qualquer acesso, abertura ou inspeção dos shards de teste antes do freeze assinado pelo dono.
2. **Acesso fora do instrumento:** uso de `cat`, `head`, `grep`, `jq`, `python -c` ou qualquer outro utilitário sobre os shards do bucket test.
3. **Treinamento:** qualquer tentativa de ajustar pesos ou treinar sobre os dados do split test.
4. **Edição de produção / PROFILES:** qualquer toque em `backend/model_train/v15_residual/` ou modificação do dicionário `PROFILES` em `run_race_10_cars.py`.
5. **Promoção antecipada:** cópia ou substituição de arquivos para produção nesta fase.
6. **Rerun pós-gate:** repetição de execuções ou reavaliação após obtenção de resultado.
7. **Instalação de pacotes (pip):** modificação do ambiente virtual (`.venv`).
8. **Alteração de ledgers / anexos:** edição de `PROJECT_STATE.md`, `worklog.md` ou `AUDITORIA_RL.md` durante a etapa A.
9. **Commits na Etapa A:** nenhum commit deve ser realizado pelo agente nesta etapa.
10. **Timeout / Exit 124:** travamento ou estouro de tempo do instrumento.
11. **JSON ausente ou inválido:** falha na geração ou corrupção do arquivo de veredicto.
12. **Divergência entre leituras:** diferença de bytes entre a Leitura 1 e a Leitura 2 (quebra de determinismo).
