# PLANO_PROF_CONTROL_1 — feedforward de curvatura e lookahead no professor solo

**Versão:** 1.0 · **Estado:** abertura; aguardando Freeze do Dono ·
**Data:** 2026-11-07 (America/Sao_Paulo) · **Branch:** `feat/sanidade-produto`.

Este plano abre o Programa PROF-CONTROL-1: o reparo do controle lateral do
professor solo apontado pela anatomia da Descida do Lago. O objetivo é zerar
as quatro saídas crônicas de Interlagos (C01/Lago, C06/Bico, C07/Mergulho,
C08/Junção) agindo no **controlador** — não em teto de velocidade (morto no
PROF-CURVA-1), nem em linha virtual (arquivada no RACING-LINE-1), nem no
governador de produção. Nenhuma tarefa altera treino, física, pista frozen,
matriz de 10 carros ou os caminhos não-professor. Cada tarefa só começa após
o prereg correspondente, o Freeze do Dono e o orçamento explícito.

## 1. Diagnóstico (evidência congelada)

1. **C01/Descida do Lago — Hipótese B confirmada** (`LAGO_ANATOMY.md`): em
   4/4 passagens com saída, o pure pursuit usa no máximo **74% do volante
   disponível** (0 ticks ≥ 98%), e **reduz** o esterço no ápice/saída
   (ratio 0,74 → 0,62-0,68) enquanto o carro espalha; demanda lateral
   9,2-10,1 m/s² > μg nominal 7,7 m/s² (subesterço plástico com folga de
   ~6,9° de volante a 75 km/h). A passagem pós-largada da volta 1 foi limpa
   a até 107 km/h com a mesma folga — o gatilho é o **estado de entrada** na
   curva, não a velocidade pontual.
2. **C08/Junção — geometria pinada** (`GEOMETRIA_C08.md`): raio instantâneo
   da linha central no ápice ≈ **7,9 m** (13,5 m no perfil suavizado 30 m);
   arco único R=18 m sai do corredor (10,07 m > 6,0 m).
3. **Causa estrutural no código** (`reference_controller.py`, sha
   `95633403…` na abertura): o esterço é pure pursuit geométrico puro,
   `δ_pp = atan2(2·L·sin α, ld)` com `ld = clip(0,6·v, 5, 45)` e **nenhum
   termo de curvatura**. A ~75 km/h, `ld ≈ 12,6 m` salta o ápice da C01 —
   o ponto perseguido já está na saída e o ângulo α colapsa antes de a
   curva terminar: é o corte prematuro de volante medido.

## 2. Mecanismo (duas frentes, isolado no professor solo)

Flag opt-in `--prof-control` em `race_diagnostic.py` (default OFF;
OFF byte-idêntico ao professor histórico; engaja só no caminho professor —
mesma guarda de `--prof-curva`; nunca em carros neurais):

a) **Feedforward cinemático de esterço**: `δ_ff(s) = arctan(L · κ_local(s))`,
   com `L = 3,4 m` (wheelbase canônica do `ReferenceController`) e
   `κ_local` = curvatura local instantânea da pista frozen (janela mínima —
   a suavização de 30 m esconde quinas, lição PROF-CURVA-1), sinal completo.
   O esterço comandado passa a ser `clip((δ_ff + δ_pp)/steer_limit_rad(v),
   −1, 1)`: o feedforward dá a base proporcional à curvatura e o pure
   pursuit vira o termo residual de correção lateral.
b) **Lookahead modulado pela curvatura**: `ld_eff = clip(k_ld·v, ld_min,
   ld_max) · g(κ)`, com `g(κ) = 1/(1 + c_ld·|κ_local(s)|)` — mantém o ponto
   de perseguição dentro do arco no ápice/saída de curvas rápidas (C01) e
   aperta o lookahead nas quinas (C08), eliminando o corte prematuro.
   `c_ld` é derivado por regra fixada no prereg SÓ de `LAGO_ANATOMY.json` e
   dos canônicos do env, registrado no log da corrida ON.

Não toca: `VelocityProfile`/`v_plan` (o pacing do professor permanece o
histórico), governor de produção, física, pista frozen, rejoin, grid.

## 3. Tarefas do programa

1. **Task 1 — Abertura, diagnóstico e preregistro (esta etapa).** Registrar
   o diagnóstico, redigir este plano e `PREREG_PROF_CONTROL_1.md`, linha nos
   três ledgers. ZERO código de produção e ZERO corrida. PARE para Freeze
   do Dono.
2. **Task 2 — Implementação isolada em `race_diagnostic.py`/
   `reference_controller.py`.** Só após Freeze: as duas frentes atrás da
   flag, constantes derivadas pelas regras do prereg e registradas no log;
   testes de bit-identidade da flag OFF (v_plan e CSV histórico idênticos)
   e de rejeição ON fora do professor.
3. **Task 3 — Medição solo e extrações.** Só após novo Freeze: corridas
   solo de 600 s do professor em Interlagos e Monaco, N=0..4, em série,
   sidecar, duas leituras determinísticas `cmp=0` por extração; controles
   OFF contra o estágio 0 do PROF-CURVA-1.
4. **Task 4 — Gates, relatório e closing.** Tabelas por curva e por
   realização ON × OFF, avaliação dos gates formais, linha nos três
   ledgers, PARE para closing do Dono. Promoção não faz parte deste
   programa.

## 4. Gates (pinados no prereg; avaliados só na Task 4)

- **Gate Primário (Interlagos):** ZERO saídas em C01, C06, C07 e C08 em cada
  realização ON, e ZERO saídas novas nas demais curvas. Melhora agregada não
  compensa regressão localizada.
- **Gate Mônaco:** redução de tempo fora de pista com Δfora% ≥ 5 pp, sem
  piora em nenhuma curva.
- **Guarda de Ritmo (Decisão 3=b):** mediana de volta solo ON ≤ 123,05 s
  (baseline limpa histórica 107,0 s × 1,15). Estouro = PARE automático; não
  se amplia o teto.

## 5. Orçamento

Estritamente corridas solo de 600 s do professor (Interlagos e Monaco,
N=0..4) mais leituras determinísticas dos instrumentos. Sem matriz de 10
carros, sem treino, sem rede. N=9..12, N=13..16 e pools 76..79 permanecem
selados.

## 6. Governança

Ciclo de vida: prereg staged → Freeze do Dono (commit) → execução da próxima
task autorizada → linha idêntica de ledger nos três arquivos canônicos →
closing do dono. Este documento não autoriza Task 2-4. O estado atual é
**PARE para Freeze do Dono**.
