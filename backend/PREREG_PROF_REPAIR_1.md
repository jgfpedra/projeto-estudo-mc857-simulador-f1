# PREREG_PROF_REPAIR_1 — Reparo do professor em Monaco_v2: pacing pós-reentrada (opt-in)

Branch `feat/sanidade-produto` · 2026-10-22 · Commitado ANTES de qualquer
patch/dado. **PRIMEIRO ciclo que MODIFICA o professor** (ciclos anteriores
read-only). Baseline = PROF-MONACO-1 (RATIFICADO; reuso OBRIGATÓRIO —
anti-duplicata: baseline NÃO se re-coleta; aluno 45,00% canônico).

## §1 Mecanismo alvo (R0 — arquivo:linha; GATE aprovado: nenhuma zona proibida)
- **Re-entry**: `race_diagnostic.py:327-364` (ProfessorRaceController.
  predict_batch): off-track = esterço p/ projeção+10 m; teto 8 m/s; th 0,35.
  A transição off→on devolve o controle ao professor INSTANTANEAMENTE —
  **não existe settling**: o carro reentra a ~8 m/s na borda, muitas
  vezes dentro/antes de um complexo (C11/C04/C12 = 46% dos eventos-base).
- **Pacing**: `reference_controller.py:448-453`: `v_tgt = _v_target(s,v)
  × margin(0,93)`; `_v_target` (linha 145-153) = `v_profile.at(s)` =
  **v_plan FROZEN** — no tick seguinte ao reentry o alvo já é o v_plan
  pleno (Monaco: 15-50 km/h) → `long_cmd=(v_tgt−v)/8` = aceleração total
  com o carro ainda a ~8 m/s na borda, heading raso.
- **Por que cascata (94,6%)**: reentra → v_plan exige ritmo pleno
  IMEDIATAMENTE → subesterço/overshoot lateral na borda do mesmo complexo
  → sai de novo ≤10 s (o padrão Q1-RETA 24,4% = as reentradas caem na
  banda entre complexos). O mecanismo é o PULSO DE PACE, não a geometria
  (hairpin só 7,3%) e não o esterço de reentrada (o bearing leva ao centro).
- **Zonas proibidas verificadas**: o patch toca SÓ
  `ProfessorRaceController` (race_diagnostic.py) + argparse —
  track_loader/F1MultiContextEnv/reference_controller/canônicos/schema/
  pools/caches/draw_track/perfis-default INTOCADOS.

## §2 Desenho do patch (flag `--prof-repair`, default OFF)
Em `ProfessorRaceController.predict_batch`, após o bloco rejoin (~365),
gated por `if self.PROF_REPAIR_ENABLED:`:
- Estado por driver `_repair_state[drv] = dict(active, t0, was_off)`.
- Transição off→on detectada por `_repair_state[drv]['was_off']` → janela
  `PROF_REPAIR_HOLD_S = 5,0 s` (50 ticks de 0,1 s — unidade+taxa).
- Durante a janela: **PACING RAMP** — alvo de velocidade =
  `min(v_plan(s)·margin, V0 + (v_plan(s)·margin − V0)·elapsed/HOLD_S)` com
  `V0 = 8,0 m/s` (= REJOIN_TARGET_MPS); `long_cmd = clip((alvo−v)/8, −1,
  1)` → th/brk recomputados com a MESMA fórmula do professor (é como se
  o v_plan fosse temporariamente menor). **Esterço do professor intocado**
  (pursuit já busca a linha). Janela também encerra se re-excusar
  (reinicia na próxima reentrada) ou se elapsed ≥ HOLD_S.
- UM fator (pacing pós-reentrada). Variedade semeada (VARIEDADE-1) =
  proposta SÓ-TEXTO p/ ciclo futuro.
- Default OFF = **caminho bit-idêntico** (estado só é tocado sob a flag).
- Seeds explícitas: já no cabeçalho (weather_seed); `prof_repair=True`
  entra na linha de identidade `[diag]`.

## §3 Falsificações pinadas (ANTES dos dados; baseline canônico)
| métrica | baseline | PASS se |
|---|---|---|
| **PRIMÁRIA** fora% professor pós-reparo | 56,93% | **< 45,00%** (supera o aluno; condição p/ rótulos úteis) |
| SEC-1 share rejoin-cascata | 94,6% | **< 50,0%** |
| SEC-2 top-1 do ranking | Reta (24,4%) | **Reta NÃO é top-1** |
| SEC-3 preso acumulado | 237,0 s | **< 118,5 s** (metade) |
| Estabilidade IQR/curva | C03 0,5 (alvo) | REPORT-ONLY (padrão C03 documentado; sem gate) |
| Bit-identidade flag-OFF | — | episódio flag-OFF BYTE-IDENTIDADE a prof_s0 (regressão obrigatória; falha = PARE por vazamento) |

## §4 Orçamento (teto N+2 = 7 eps; seriais; zero rede; zero corridas de produto)
- Smoke 1: episódio **flag-OFF** seed 0 → BYTE-IDENTIDADE a
  `experiments/prof-monaco-1/prof_s0.csv` (regressão; fail-loud).
- Smoke 2: episódio **flag-ON** seed 0 (sanidade: não aborta; a janela
  engaja — verificado por log).
- Bateria: **5 eps flag-ON seeds 0-4**, Monaco_v2, `--controller
  professor --n-cars 1 --ticks 6000 --laps 99 --track Monaco --seed N
  --prof-repair` (mesma pista/N/seeds/instrumento/formato do
  PROF-MONACO-1; N/seeds lidos de PREREG_PROF_MONACO_1.md §4 ✓).
- Análise: `saidas_verdict.py --track monaco --files-a <5 eps novos>
  --files-b <5 eps aluno baseline>` (aluno NÃO re-coletado; 45,00%
  canônico). Baseline professor = tabelas PROF-MONACO-1 (reuso).
- Estatística: descritiva + cluster bootstrap seed 42 (herdado; a
  bateria solo+seca é determinística — degenerescência V1 do
  PROF-MONACO-1: comparação determinística).
- Pools 70-79/76-79 VIRGENS; caches fastf1 intactos; f1_env.py:81
  whitespace não-commitado (ruling vigente).

## §5 Árvore de decisão (pinada)
- **A — Sucesso** (PRIMÁRIA + SEC-1..3): professor apto como fonte de
  rótulos → PARE + proposta SÓ-TEXTO de ciclo de RETREINO do aluno com
  rótulos novos (orçamento próprio; proibido aqui).
- **B — Parcial** (melhora substancial — SECs verdes mas fora% ≥ 45,00):
  PARE honesto; gap residual quantificado; decisão do dono (2ª rodada de
  reparo × abandonar o professor).
- **C — Falha/regressão** (fora% ≥ 56,93% ou abort/instabilidade): PARE
  imediato; flag default-OFF protege o produto; professor declarado
  não-viável no estado atual; alternativas documentadas.
- Bit-identidade flag-OFF FALHA → PARE por vazamento (independe da árvore).

## §6 Suíte
Base 25F/334P/3S + 2 testes novos (wiring flag default-OFF + rampa
linear unitária) → **ESPERADA 25F/336P/3S ±** (cláusula: desvio
justificado no fechamento).

## §7 Reconciliação ENTRE pins
- Teto 7 eps × (1 flag-OFF + 1 flag-ON + 5 bateria) = 7 ✓.
- Bit-identidade flag-OFF × patch no mesmo arquivo: gate `if` único,
  estado lazy — zero execução default ✓.
- Degenerescência de seeds (V1) × estatística bootstrap: a bateria é
  determinística; CIs degeneram; a comparação é DETERMINÍSTICA (lição
  registrada — não é defeito) ✓.
- Baseline reuso × anti-duplicata: professor antigo e aluno NÃO se
  re-coletam; tabelas canônicas PROF-MONACO-1 são a referência ✓.
- PRIMÁRIA < 45,00% (aluno) × SECs vs professor: consistentes (o aluno é
  o alvo do produto; o professor é o insumo de rótulos) ✓.
