# PRÉ-REGISTO — CICLO ALAVANCA PASSO 1 (commitado ANTES de qualquer código/run)

Branch: feat/rejoin-gap-check (base a6ae0f6 ← cf6529f/v15.0). Pool confirmatório: seeds 20-29.

## 1. DEFINIÇÕES (reconciliadas, única interpretação)
- **Excursão**: trecho contíguo de ticks off-track (uma por trecho). 4.356 = braço
  A composite (R7a 0-9: 2.160 + R13 10-19: 2.196 — dossiê cab38ed). 1.820 = braço B
  cego (R13 10-19). Denominadores do PASSO 0-c (1.808 reentradas do cego) e do dossiê
  (4.356 excursões do composite) diferem por BRAÇO e por CONDIÇÃO (reentrada-real vs
  excursão) — reconciliado e confirmado por recontagem.
- **Reentrada**: primeiro tick on-track após excursão QUE TERMINA antes do fim da
  corrida (excursão cortada pelo fim não gera reentrada; 98-99% geram).
- **Reentrada PERIGOSA**: contato do DONO em ≤30 s (300 ticks) após a reentrada
  (contato pelo instrumento solver-side, events CSV). Única definição.
- **MÉTRICA PRIMÁRIA POR RUN**: taxa = perigosas / reentradas do run.
- Distribuição HISTÓRICA (braço B cego, R13 seeds 10-19, computada do corpus):
  taxa por run = [0,306; 0,328; 0,317; 0,441; 0,333; 0,406; 0,267; 0,310; 0,300; 0,350].
  **mediana 0,323 | p25 0,307 | p75 0,346 | máx 0,441**. Rolante histórico: mediana 136 s.

## 2. CRITÉRIO DE X (mecânico, declarado; tabela 0-c é a justificativa)
X = min{X ∈ {10,15,20,25,30} m : %perigosas bloqueadas ≥ 50% E espera mediana ≤ 1,0 s}.
Tabela 0-c: 10m→36%; 15m→46%; **20m→54% (≥50%, espera 0,6 s ≤ 1,0)** → **X = 20 m**.

## 3. SPEC do gap-checker (UMA variável: hold por gap à frente)
- Aplica-se DENTRO do estado rejoin (após o bearing trazer o carro À BORDA do asfalto:
  quando o carro está on-track MAS ainda em modo rejoin por histerese, e |lat| <
  meia-largura×1,5 — perto da borda interior).
- Gap à FRENTE apenas (menor Δs>0 a qualquer outro carro, ao longo da linha central).
- Janela útil: 10 s (100 ticks) a partir do momento em que o carro CHEGA à borda.
- **HOLD mecanicamente definido**: velocidade de crawl 4 m/s (teto do rejoin é 8; crawl
  pela metade — sem deadlock na borda, carro sempre em movimento), th proporcional ao
  gap (como o rejoin faz), esterço = bearing ao ponto de reentrada (inalterado).
- **FALLBACK T_max = 10 s**: se nenhum gap ≥ X aparecer em T_max, SOLTA (retorna ao
  policy) e registra evento `rejoin_gap_fallback` (sem deadlock na borda).
- **Parada ≥3 s: ISENÇÃO DOCUMENTADA**: hold em crawl 4 m/s NÃO é parada (v ≥ 1 m/s;
  a regra de paradas conta v<0,5). O tempo em hold entra em report-only (tempo de hold
  total por run), NÃO na métrica de paradas — decidido ANTES, mecanicamente.
- Autoridade: `rejoin_gap` (nova) enquanto em hold; destrói ao soltar.

## 4. TETO declarado
X=20m bloqueia ~54% das perigosas; ~46% passam POR CONSTRUÇÃO (gap grande à frente,
ou sem carro). O gate compara com a DISTRIBUIÇÃO HISTÓRICA (taxa mediana 0,323), não
com zero. Redução esperada mecânica: taxa ≈ 0,323 × (1−0,54) ≈ 0,149 (teto teórico;
o real depende de dinâmica — o gap-check muda a própria formação dos gaps).

## 5. GATE (N=10, seeds 20-29, secos, 600s, Interlagos frozen v2, braço CEGO v10+vplan)
Comando (idêntico ao histórico R13-B + UMA flag):
`.venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed {N} --gov vplan --variance grid,compound --rejoin-gap 20 --out race_diag_alv_gap_s{N}.csv`
- **Veredito mecânico por script commitado** (junto com este prereg):
  - PASS-P: mediana(taxa_tratamento) ≤ p25 histórico = **0,307**; E
  - PASS-R: nenhuma run com taxa > mediana histórica = **0,323**; E
  - GUARD-V: 10/10 carros completam ≥1 volta (por cruzamento de SF − 1); E
  - GUARD-P: paradas ≥3 s (v<0,5) = 0 em todas as runs; E
  - GUARD-W: wanderers (>60 s) = 0 em todas as runs; E
  - GUARD-L: rolante mediana ≤ histórico 136 s + 5 s = **≤ 141 s**; E
  - GUARD-F: fora% por run dentro do range histórico [21,0; 31,6] (tolerância +2 pp
    para o custo de hold na borda: ≤ 33,6%).
- Report-only (não bloqueia): excursões/run, tempo total de hold, eventos T_max fallback.
- FAIL em qualquer critério → PARE com diagnóstico; SEM re-pin, SEM re-run.
- Adversos: NÃO entram neste gate (sessão própria se o seco passar).

## 6. INSTRUMENTO
- Flag `--rejoin-gap X` (m; default 0 = off) no race_diagnostic; no identity log.
- CSV v3.3 aditivo: colunas `rejoin_gap_hold` (1 se em hold neste tick),
  `rejoin_gap_fb` (1 no tick do fallback T_max).
- **SMOKE seed 0 ANTES do pool (lição FASE 1)**: com `--rejoin-gap 20` o CSV DEVE
  diferir do sem-checker (authority `rejoin_gap` ≠ 0, colunas hold > 0). Se o CSV
  for bit-idêntico, o wiring está morto → PARE, conserte instrumento, re-smoke.
- Veredito por script `scripts/lever_gate_verdict.py` (commitado com este prereg).

## RAMOS
- Smoke bit-idêntico → wiring morto → PARE (instrumento antes de interpretação).
- Qualquer guard FAIL → PARE com diagnóstico por seed.
- Todos PASS → alavanca VIVA no seco; adversos = sessão própria; adoção = revisão.
