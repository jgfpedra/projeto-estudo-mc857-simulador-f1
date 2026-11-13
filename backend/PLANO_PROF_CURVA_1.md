# PLANO_PROF_CURVA_1 — teto de velocidade local no plano do professor

**Versão:** 1.0 · **Estado:** preregistração de abertura; aguardando Freeze do Dono ·
**Data:** 2026-11-06 (America/Sao_Paulo) · **Branch:** `feat/sanidade-produto`.

Este plano abre o Programa PROF-CURVA-1. O objetivo é eliminar as quatro
saídas crônicas de Interlagos — Descida do Lago (s≈31), Bico de Pato
(s≈1947), Mergulho (s≈2059) e Junção (s≈2318) — e a volta larga na grama,
atuando somente no `VelocityProfile` local do professor solo. Nenhuma tarefa
deste documento autoriza alteração do governor de produção, treino, promoção
ou matriz de 10 carros. Cada tarefa só começa após o prereg correspondente,
o Freeze do Dono e o orçamento explícito.

## 1. Escopo e estado inicial

A pré-condição da PERCEPÇÃO-1 (Task 3) reprovou o professor como oráculo:
sobreposição de saídas 94,1% contra o v10 cego. O C8-B (`--c8-rejoin`) foi
reprovado nos agregados N=0..4 (B-1 e R-2). Os defaults de produção do
REALISMO-1 (`--rejoin-handoff align --rejoin-ramp --gov vplan`) permanecem
canônicos e fora do escopo deste programa.

O defeito atacado é de **pacing local**: o plano de velocidade do professor
suaviza a curvatura em ~30 m e pede um `v_plan` acima do raio físico viável
nas quinas fechadas. O teto atua no professor isolado; o governor da
produção não é tocado.

## 2. Invariantes

1. **Zero código de produção nesta Task 1.** Só ledgers, plano, prereg,
   script de calibração isolado e testes sintéticos.
2. **Zero corrida do professor nesta Task 1.** A fronteira física é medida
   em skidpad (plano livre), não em Interlagos/Monaco.
3. **Fronteira isolada.** A calibração grava
   `backend/experiments/prof-curva-1/physics_frontier_current.json` e
   **não** sobrescreve `backend/model_train/physics_frontier.json`.
4. **Mecanismo isolado no professor.** A Task 3, quando autorizada, altera
   só o caminho do professor em `race_diagnostic.py`. Flag opt-in, default
   OFF, bit-idêntica com a flag desligada.
5. **Orçamento só solo 600 s.** Sem matrizes de 10 carros. Pools 76–79,
   N=9..16 e shards `test/` permanecem selados.

## 3. Tarefas do programa

1. **Task 1 — Abertura, errata C8, calibração física e prereg (esta etapa).**
   Registrar a errata do C8-B e a suspensão formal da PERCEPÇÃO-1 nos três
   ledgers; medir a fronteira física atual até 25 m/s nos grips 0,788 (real)
   e 0,842 (soft); redigir este plano e `PREREG_PROF_CURVA_1.md`. PARE para
   Freeze do Dono. Sem corrida do professor.
2. **Task 2 — Corrida de referência solo de 600 s do professor em Interlagos.**
   Somente após Freeze. Produz a baseline de saídas por curva (as quatro
   crônicas + demais setores) e o tempo de volta solo contra o qual a
   guarda de ritmo (Decisão 3=b) será medida. Sem patch de teto.
3. **Task 3 — Implementação do teto local de curvatura em `race_diagnostic.py`.**
   Isolado no professor. Curvatura local instantânea, sem a suavização
   excessiva de 30 m nas quinas. Teto de velocidade proporcional ao raio
   físico viável lido de `physics_frontier_current.json`. Governor de
   produção intocado. Testes de bit-identidade da flag OFF.
4. **Task 4 — Medição solo e avaliação dos gates em Interlagos e Monaco.**
   Corridas solo de 600 s do professor, ON contra a baseline da Task 2.
   Aplica Gate Primário (Interlagos), Gate Mônaco e Guarda de Ritmo.
   Qualquer estouro da guarda dispara PARE automático para adoção de
   racing line suavizada (curva geométrica de 18 m na Junção), em ciclo
   próprio — não nesta implementação.

## 4. Gates (pinados no prereg; avaliados só na Task 4)

- **Gate Primário (Interlagos):** ZERO saídas em Descida do Lago, Bico de
  Pato, Mergulho e Junção, e ZERO saídas novas em outros setores.
- **Gate Mônaco:** redução material de tempo fora de pista
  (Δfora% ≥ 5 pp) sem piora em nenhuma curva.
- **Guarda de Ritmo (Decisão 3=b):** perda máxima de tempo de volta solo
  limitada a 15% sobre a baseline histórica. Se estourar esse teto para
  ficar limpo, PARE automático e encaminhamento à linha suavizada de 18 m
  na Junção.

## 5. Governança

Ciclo de vida: prereg staged → Freeze do Dono (commit) → execução da
próxima task autorizada → uma linha idêntica de ledger nos três arquivos
canônicos → closing do dono.

Este documento não autoriza simulação de produto, treino, flip de default
nem promoção. A Task 1 pára no PARE FORMAL para Freeze do Dono.
