# PREREG_PROF_MONACO_1 — Diagnóstico READ-MOSTLY do professor-solo em Monaco_v2

Branch `feat/sanidade-produto` · 2026-10-22 · Commitado ANTES de qualquer
coleta/mudança. Ciclo de DIAGNÓSTICO: **nenhum reparo nesta fase**.
Instrumento de desfecho: `scripts/saidas_verdict.py` generalizado (`--track`)
— régua de regressão oficial (lead E6 da ERRATA-SAIDAS-1-review). Baseline =
tabelas SAIDAS-1 corrigidas (R1-R4 + R5-a/R5-b consolidadas no P0).

## 1. Escopo e proibições (inegociáveis)
ZERO treino/retreino; ZERO corridas 10-carros; ZERO mudança de
canônico/loader/schema. PROIBIDO: `--variedade`, `--modo espectador`,
alterar QUALQUER parâmetro do professor, decidir A×B, side-car de schema
sem aprovação do orquestrador. Pools 70-79 e 76-79 INTOCADOS (seeds de eval
= corpus 0-4, fora dos pools). Livros em caminho ABSOLUTO. Suite declarada
(§8). Comandos essenciais no commit de fechamento.

## 2. Definições herdadas do SAIDAS-1 (PREREG_SAIDAS_1.md §3 — EXATAS)
- **Evento de saída**: transição `offtrack` 0→1 (episódio contíguo);
  `offtrack = |slat| > half_width`; **slat = obs4 × hw** (Monaco_v2
  `width_m = 12,0` ⇒ hw = 6,00 — IGUAL ao Interlagos; fórmula D0 carrega).
- **Modos** (janela 2 s pré-evento; 10 ticks a 5 Hz): SPIN = |ψ̇| ≥ 45°/s
  sustentado ≥ 0,5 s; SLIDE = |β| ≥ 10° (heading do chassi via obs5/obs6 +
  ψ_track; guarda v < 1,0 m/s); LINHA-RETA caso contrário.
- **v_1s**: velocidade 1,0 s antes do evento (mediana + IQR por curva).
- **Solo** (D=15 m, T=5 s): nas eps 1-carro é 100% por construção —
  report-only (o alvo deste ciclo é o RANKING por curva).
- **Curvas**: mesma derivação do SAIDAS-1 sobre os 834 wp do
  Monaco_v2.json — κ > 0,006 m⁻¹ (R < 166,7 m), fusão de blocos com gap
  < 40 m, `compute_kappa_profile(ds_target=4,0; smooth=30,0)`. **Nomes
  GENÉRICOS por geometria** (C01..CN em ordem de s, com κmax reportado) —
  SEM atribuição oficial de turns (lição FASE-H-1: convenção oficial não
  mapeia mecanicamente em geometria; o HAIRPIN = o complexo de κmax
  máximo, R ≈ 11,34 m ⇒ κmax ≈ 0,088 — identificação GEOMÉTRICA).
  Justificativa do limiar: 19 turns oficiais de Monaco têm R de ~7 m
  (hairpin real; 11,34 no mirror) até ~∞ — κ > 0,006 isola complexos
  contra o ruído de spline; o merge 40 m unifica multi-ápices contíguos.

## 3. Perguntas com expectativa + falsificação (pinadas ANTES dos dados)
- **Q1 — Ranking**: top-5 de curvas por excursões do professor
  (bateria 5 eps seeds 0-4). EXPECTATIVA: o hairpin (κmax máximo) domina
  o top-1. **FALSIDICAÇÃO (report-only)**: RETA dominar o top-1 → lead de
  rejoin-cascata (não-PARE; registrado como lead).
- **Q2 — Assinatura cinemática por curva**: v_med, IQR, modo (definições
  exatas §2). Comparabilidade Interlagos×Monaco: mesmas definições e
  limiares; classificação determinística (IQR ≤ 3,7 km/h, template C01/C06)
  vs heterogênea (IQR > 20 km/h, template C07) — QUALITATIVA entre pistas
  (curvas diferentes; sem teto cruzado).
- **Q3 — Anatomia do preso**: decompor preso acumulado 118 s e as 34
  excursões (números herdados do B' aluno 3×s0/2-voltas da ADOÇÃO-H-2) em:
  **rejoin-cascata** (excursão iniciando ≤ 10 s após o FIM da anterior —
  convenção raiz/eco da FASE R4, separação VALIDADA na review),
  **saída limpa** (não-cascata), **wanderer** (episódio contíguo > 60 s).
  Métricas: contagem por classe + tempo acumulado por classe. Fontes: os
  artefatos EXISTENTES (aluno_Monaco_ep1-3) para os 118 s/34 exatos + a
  bateria fresca do aluno (report).
- **Q4 — Herdado ou degradado**: v10-cego na MESMA bateria (5 eps seeds
  0-4, janela idêntica). MECÂNICO por ICs bootstrap 95% (seed 42, 10000
  rounds, herdado) do fora% de cada braço:
  (a) ICs DISJUNTOS com aluno > professor (**Δ ≥ +15 pp** degradado em
      termo absoluto OU disjunção de ICs) → **DEGRADAÇÃO do aluno**;
  (b) ICs DISJUNTOS com aluno < professor → **FALSIDICAÇÃO-Q4 = PARE
      imediato** (rótulos inconsistentes — aluno melhor que o professor
      que o treinou em pista onde o professor é o gargalo);
  (c) ICs SOBREPOSTOS → **HERDADO dos rótulos** (fora ≈ professor: o
      fora é baseline do instrumento+rótulos, não degradação do aluno).

## 4. Orçamento (teto 14 sims; SERIAIS; nunca paralelo; bit-idêntico por seed)
Janela das eps: `--ticks 6000 --laps 99` (600 s ≈ 5-6 voltas de Monaco a
~106 s/volta — máx eventos/ep dentro do teto). Clima seeds 0-4: **TODAS
SECAS pelo weather-scan** (s2/s4 com transição DRY→CLOUDY; 0/5 damp —
declarado ANTES da coleta).
1-5. **Professor** seeds 0-4: `race_diagnostic --controller professor
      --n-cars 1 --ticks 6000 --laps 99 --track Monaco --seed N`
6. **Paridade professor s0** (repete o 1) → BIT-IDÊNTICO ao eps 1 (ou
    PARE por não-determinismo).
7-11. **Aluno (v10-cego)** seeds 0-4: `race_diagnostic --actor
      model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge
      --n-cars 1 --ticks 6000 --laps 99 --track Monaco --seed N`
12. **Paridade aluno s0** → BIT-IDÊNTICO ao eps 7.
13-14. **+1 re-smoke contingente (s0)** — regra de template do
      LARGADA-FECHO-0; só se um smoke falhar em parse/abort.
ZERO corridas 10-carros. A telemetria EXISTENTE (metaA 5×s0 2-voltas;
aluno 3×s0 2-voltas) fica como CROSS-CHECK de era (fora% comparável), não
como bateria (janela/seeds insuficientes — F0).

## 5. Instrumento (F2) — critérios de aceitação ANTES da coleta
- `--track {interlagos,monaco}`; o caminho Interlagos NÃO muda (constantes
  e nomes idênticos aos de hoje).
- **Golden test OBRIGATÓRIO**: output Interlagos (F4v15 CSVs) BYTE-IDÊNTICO
  às tabelas corrigidas de `experiments/saidas-1/` (o P0/NIT-2 PROVOU que
  fecha byte a byte — as 6 tabelas).
- **Selftest estendido**: 4 casos sintéticos herdados + geometria Monaco
  (N complexos ≥ 8; κmax máximo ≈ 1/11,34 m ± 15%; curvas em ordem de s;
  fail-loud se o catálogo der 0 curvas).
- **Asserção fail-loud Σ solo por curva == total OBRIGATÓRIA em TODO
  output** (fecha a classe de erro R1 da review).

## 6. Árvore de decisão (completa, antes dos números)
- Paridade (prof ou aluno) NÃO bit-idêntica → **PARE** (não-determinismo;
  determinismo é infraestrutura).
- **Falsificação Q4 (aluno ≪ professor, ICs disjuntos)** → **PARE
  imediato**: rótulos inconsistentes; o resto do ciclo não se sustenta;
  escala ao orquestrador SEM coleta adicional.
- Q1 reta no top-1 → report-only (lead rejoin-cascata; o ranking por
  curva segue válido).
- Q4 degradado → diagnóstico completo + **proposta (SÓ TEXTO) de ciclo de
  reparo do professor** (nenhum reparo AQUI).
- Q4 herdado → o fora% é baseline dos rótulos do professor sob mirror
  (Meta A trava por rótulos); documento para o dono.
- Tudo verde → PARE padrão com tabelas Q1-Q4 + veredito das 2
  falsificações + hashes + confirmação de pools + proposta de reparo (texto).

## 7. Reconciliação ENTRE pins (regra da casa)
- Bit-identidade das paridades × bateria seeds 0-4: compatíveis (serial;
  clima semeado por seed — scan declarou secas; zero variedade/espectador).
- Golden Interlagos byte-idêntico × generalização --track: compatíveis
  (branch monaco separado; constantes Interlagos intocadas).
- Q4 mecânico por ICs (sem margem arbitrária) × report qualitativo Q2:
  compatíveis (Q2 sem teto cruzado entre pistas — declarado).
- Teto 14 sims × paridades 2 + re-smoke contingente 1: 12 + 2 = 14 ✓
  (re-smoke só se smoke falhar — não conta se não rodar).

## 8. Suíte
Base 25F/326P/3S + testes novos do instrumento generalizado (golden
Interlagos; selftest estendido; geometria Monaco; fail-loud Σ==total) —
**ESPERADA 25F/330P/3S ±** (cláusula ±: desvio justificado no fechamento).

## 9. Estatística
Descritiva (mediana, IQR, contagens) + bootstrap 95% (seed 42, 10000
rounds — herdado) para fora% por braço e proporções por curva. Tempo
exibido na precisão do instrumento (NIT da ERRATA-SAIDAS-1-review).

## 10. Errata de calibração (PRÉ-COLETA — additive; instrumento F2)
O §2 anotava "hairpin ... R ≈ 11,34 m ⇒ κmax ≈ 0,088": o r_min 11,34 do
JSON é a métrica do BUILDER (circle-fit grosso do mirror); o κmax do
PERFIL do instrumento (κ > 0,006; ds=4,0; smooth=30,0) no hairpin de
Monaco_v2 = **0,1602 (R ≈ 6,2 m do perfil) — métrica DISTINTA e mais
apertada**. O MÉTODO de identificação do hairpin (complexo de κmax
MÁXIMO — geometria) é INALTERADO; o selftest pinou o valor do perfil como
PISO (κmax ≥ 1/11,34) em vez da igualdade. Nenhum dado coletado antes
desta errata; a generalização do limiar κ > 0,006 segue válida (o hairpin
real do mirror é capturado com folga).
