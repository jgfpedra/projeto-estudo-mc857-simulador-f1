# PLANO_PROF_GRIP_1 — pacing sensível ao grip nas 4 crônicas de Interlagos

**Versão:** 1.0 · **Estado:** abertura; aguardando Freeze do Dono ·
**Data:** 2026-11-07 (America/Sao_Paulo) · **Branch:** `feat/sanidade-produto`.

## 1. Motivação (evidência congelada)

1. **LAGO_APPROACH_FINDINGS** (`0175e662…`): a causa da saída crônica da C01
   é o **cliff de degradação de pneu** — o passe 1 tangencia a borda com
   margem de **+6 cm** (grip 0,842) e os passes 2-5 cruzam os 6,0 m conforme
   o `tyre_grip` degrada linearmente (0,842 → 0,807); correlação Pearson
   grip↔lat_max = **−0,9686**; aproximação/frenagem idênticas em todos os
   passes. O carro anda no ~99% do corredor com demanda lateral no limite do
   μ remanescente — qualquer perda de aderência empurra para fora.
2. **GRIP_PACING_FEASIBILITY** (`ecb4d842…`): um teto de pacing
   `v_plan · sqrt(grip/0,85)` **com reserva de 10% da capacidade lateral**,
   aplicado SOMENTE nas janelas canônicas das 4 crônicas, custa no piso
   teórico **+0,86 a +2,05 s** na grade de grip 0,85→0,75 — **todos os
   pontos cabem na Guarda de Ritmo (123,05 s) com folga ≥ 24,8 s**. O piso
   base (96,202 s) bate com o mapa de viabilidade do PROF-CURVA-1.
3. **Contexto dos ciclos mortos:** o teto global do PROF-CURVA-1 custava
   +34,8 s no piso (capava a volta inteira); o feedforward/lookahead do
   PROF-CONTROL-1 (REPROVADO nos gates) não atacou o pacing no limite — a
   causa está no `v_plan` que consome a margem de μ que o desgaste do pneu
   vem comendo.

## 2. Hipótese única (falsificável)

Modulação dinâmica do plano de velocidade **nas janelas das 4 curvas
crônicas de Interlagos (C01, C06, C07, C08)** em função do grip instantâneo
do pneu:

```
v_target(s, t) = v_plan(s) · min(1, sqrt(grip_atual(t) / 0,85)) · sqrt(1 / 1,10)
```

com `f_reserva = sqrt(1/1,10)` (10% de margem física contra o
tangenciamento a centímetros da zebra). Se estiver ativa, **as quatro
crônicas caem para zero em cada realização ON**; se qualquer crônica
sobreviver em qualquer realização, a hipótese é falsificada.

## 3. Arquitetura isolada

- Flag opt-in `--prof-grip` em `race_diagnostic.py` (**default OFF;
  OFF byte-idêntico** ao professor histórico — o caminho OFF não executa
  nenhuma função nova), engajando **somente no caminho professor** (mesma
  guarda de `--prof-curva`/`--prof-control`; neural/composite nunca);
- aplicação: `min` entre o `v_plan` canônico e o `v_target` escalado,
  **apenas dentro das janelas canônicas** de C01/C06/C07/C08
  (`build_corner_definitions`, registradas no log ON); **nunca escala para
  cima**; fora das janelas, intocado;
- `grip_atual(t)` = `tyre_grip` instantâneo do estado físico do tick (a
  MESMA coluna telemetrada; nunca média por volta);
- **pacing-only:** esterço, rejoin, governor, física, pista frozen,
  `run_race_10_cars.py` intocados.

## 4. Tarefas do programa

1. **Task 1 — abertura e preregistro (esta etapa).** Este plano +
   `PREREG_PROF_GRIP_1.md` + linha nos três ledgers. ZERO código, ZERO
   corrida. PARE para Freeze do Dono.
2. **Task 2 — implementação isolada** (`--prof-grip` no `race_diagnostic.py`
   + caminho professor; janelas e `grip_ref`/reserva conforme o prereg;
   testes de bit-identidade OFF e de rejeição fora do professor). Depois de
   Freeze. ZERO corrida.
3. **Task 3 — corridas e extrações.** Depois de novo Freeze. Matriz abaixo,
   em série, com sidecar e duas leituras determinísticas `cmp=0` por corrida.
4. **Task 4 — gates, relatório e closing.** Tabelas por curva e por
   realização ON × OFF; PARE para closing do Dono. Promoção não faz parte.

## 5. Matriz de testes

- **2 controles OFF** (Interlagos N=0, Monaco N=0; variedade 0): `cmp=0`
  contra o CSV histórico (bit-identidade de corrida), como no PROF-CURVA-1
  estágio 0 e no PROF-CONTROL-1 Task 3;
- **10 corridas ON** com `--prof-grip` e **`--variedade N` (N=0..4) em
  Interlagos e Monaco** — realizações independentes (lição da degenerescência
  do PROF-CONTROL-1 Task 3, onde a matriz sem variedade colapsou em réplicas);
- execução estritamente serial; 600 s (6.000 ticks a 5 Hz); sidecar
  (vazio por convenção em corrida solo sem contato); extração com 2 leituras
  `cmp=0`.

## 6. Gates formais (avaliados só na Task 4)

- **Primário Interlagos:** ZERO saídas em C01, C06, C07 e C08 em cada
  realização ON (baseline OFF do estágio 0: 4/4/4/4), e ZERO saídas novas
  nas demais curvas. Melhora agregada não compensa regressão localizada.
- **Secundário Monaco:** `Δofftrack ≤ 0` (tempo fora ON ≤ OFF) e **zero
  regressões locais** em C05 e C12 (as curvas que regrediram no
  PROF-CONTROL-1 Task 3: C05 3→7, C12 4→5).
- **Guarda de Ritmo:** mediana de volta solo Interlagos ON **≤ 123,05 s**
  (107,0 × 1,15). Estouro = **PARE automático**.
- **Integridade:** exit 0, CSV 3.002 linhas, sidecar presente, SHA da pista
  no cabeçalho, banner com `prof_grip=True` nas ON, `--variedade` no log,
  extrações `cmp=0` ×2.

## 7. Orçamento

Estritamente **12 corridas solo de 600 s** (2 OFF + 10 ON) mais leituras
determinísticas. Sem matriz de 10 carros, sem treino, sem rede. N=9..12,
N=13..16 e pools 76..79 selados.

## 8. Governança

Ciclo de vida: prereg staged → Freeze do Dono (commit) → execução da próxima
task autorizada → linha idêntica de ledger nos três arquivos canônicos →
closing do dono. Este documento não autoriza Tasks 2-4. O estado atual é
**PARE para Freeze do Dono**.
