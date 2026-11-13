# PRÉ-REGISTO — CICLO ALAVANCA: REVALIDAÇÃO (re-gate com premissa declarada + adverso pareado)
# Amenda commitada ANTES de qualquer run. NADA do código da alavanca muda nesta
# sessão — o smoke B (ead15a7) permanece a validação permanente do instrumento.
# Orçamento: 23 runs seriais (2 P1 + 1 base damp + 10 C' + 3 D + 7 E). PAREs em P1/C'/D.

## PASSO 0 — WEATHER SCAN (offline, ZERO runs): DECLARADO
Mecanismo exato (scripts/weather_scan.py, validado contra as 30 seeds conhecidas
do corpus — 28 EXATAS + 2 PREFIXOS (s9/s10: carros encravados truncam o stream
in-race) + 0 divergentes): rng = sha256 "<seed>//weather"; o race_diagnostic
dirige `_step_tick` diretamente (o draw de largada do engine.run() NÃO ocorre
no headless); transições avaliadas por VOLTA COMPLETADA POR CARRO (10 draws por
onda; ondas 2-5 numa corrida saudável de 600 s). **TEOREMA DO PREFIXO**: as
transições in-race são um PREFIXO do scan → seed declarada SECA nunca vira
úmida in-race; declarada DAMP pode autorreduzir-se (carros encravados).

**DÉCADA 40-49 DECLARADA** (weather_scan_s40_s49.csv, commitado como âncora —
convenção 120081e):
| seed | clima | transições |
|---|---|---|
| 40, 41, 44, 45, 47, 49 | SECA | nenhuma |
| 43, 46, 48 | SECA (CLOUDY-only, grip 0,98) | v3 CLOUDY / v3+v4 / v3 |
| **42** | **DAMP** | **v5: DRY→DAMP** |

**Damp: 1/10 — guardrail preregistrado (>5/10 → PARE) PASS.** A década INTEIRA
entra (nada selecionado). A seed 42 ativa a ramificação pareada do C'.

## PASSO 1 — DIAGNÓSTICO do gate falho (2 runs, report-only)
Base FRESCA SEM flag, seeds s30 e s37 (as DAMP do re-gate C), comando do
ead15a7 §C menos `--rejoin-gap`; out `experiments/diag-alv-seco/race_diag_alv2_base_s3{0|7}.csv`.
**PREDIÇÃO pré-registrada**: a base TAMBÉM apresenta paradas/wanderers na fase
úmida (o fenômeno é do CLIMA — presente no cego histórico: s10-WET 4/4, s8
14/17, s9 8/13; o tratamento C tinha s30 7/4, s37 4/6).
**PARE se AMBAS as bases derem par=0 E wand=0** (nenhuma parada úmida na base →
a atribução clima-vs-alavanca INVERTE: a alavanca teria causado as paradas —
diagnóstico antes de qualquer coisa). Qualquer par/wand > 0 na base confirma
clima → prossegue.

## PASSO 2 — RE-GATE SECO C' (seeds 40-49; comando idêntico ao ead15a7 §C)
- **s42 (DAMP): base FRESCA PRIMEIRO** (+1 run; out race_diag_alv2_base_s42.csv),
  depois o tratamento. Tratamentos: `race_diag_alv2_s4{N}.csv`.
- Critérios INALTERADOS: PASS-P mediana ≤ 0,307 | PASS-R máx ≤ 0,323 |
  GUARD-V 10/10 | GUARD-L ≤ 141 s | GUARD-F ≤ 33,6%.
- **GUARD-P/W (EMENDADOS, declarados)**: seeds SECAS → par=0 E wand=0 absolutos
  (espelho do histórico: 9/9 secas de 10-19 têm 0/0 — reproduzido em A.0 do
  ead15a7); seed DAMP (s42) → pareado contra a base FRESCA da mesma seed:
  par_trat ≤ par_base(s42) E wand_trat ≤ wand_base(s42).
- **FALLBACK: report-only** (restaurado ao §6 do 1883d6d; o limiar >10 fica
  REVOGADO como bloqueio — cobertura parcial por construção, teto 54%;
  >10/run = diagnóstico obrigatório no relatório, sem PARE).
- **SELF leak-check BLOQUEANTE em TODOS os CSVs de tratamento**: 1º hold por
  carro ≥ 1ª reentrada do carro. Violação → PARE (instrumento regrediu).
- Veredito por `scripts/lever_regate_c_verdict.py` (commitado junto).
- FAIL → PARE: research-grade FINAL (documentado, opt-in); dossiê LARGADA vira
  o próximo ciclo. SEM re-pin, SEM re-run.

## PASSO 3 — GATE ADVERSO D (seeds {2,8,9}; comando ead15a7 §D inalterado)
Critérios JÁ emendados (lever_adverse_gate_verdict.py, ead15a7): PASS-A
taxa ≤ hist (0,277/0,444/0,348) 3/3 | GUARD-V ≥ hist 3/3 | GUARD-L ≤ hist+5 s
(139/155/152) 3/3 | GUARD-F ≤ hist+2 pp (25,0/61,4/48,9) 3/3 | **GUARD-P/W
pareados ≤ hist** (par: 0/14/8; wand: 0/17/13) 3/3. **FALLBACK report-only**
(emenda desta sessão — >10/run = diagnóstico no relatório). **SELF leak-check
BLOQUEANTE** nos 3 tratamentos (emenda desta sessão).
FAIL → PARE por seed; SEM re-pin, SEM re-run.

## PASSO 4 — REPORT-ONLY E (SÓ se D TODOS-PASS; 7 runs {0,1,3,4,5,6,7})
Mesmo comando de D; out `race_diag_alv_adv_s{N}.csv`. Decomposição: fora% vs
hold-s por run; contatos DURANTE hold-ticks; rolante vs fora; 1ª excursão vs
histórica r10_blind_s{N} (a largada DEVE permanecer intocada).

## RAMOS
- P0 >5/10 damp → PARE pré-run (não ocorreu: 1/10).
- P1 base 0/0 em ambas → PARE (atribuição invertida).
- C' FAIL → PARE: research-grade final; dossiê LARGADA = próximo ciclo.
- D FAIL → PARE com diagnóstico por seed.
- TUDO PASS → PARE final: a revisão decide ADOÇÃO (flip default + re-pin do
  regime canônico com números reparados + identidade GUI↔headless com a flag +
  suite) e abre o dossiê LARGADA (prereg próprio, pool 50-59, baseline =
  config adotada).

## Notas de instrumento
- Guia de teste do scan (caveat documentado): o runner GUI (engine.run) consome
  1 draw a mais na largada → clima do GUI ≠ headless para a MESMA seed; os
  gates são headless-canônicos.
- Teorema do prefixo implica: a base fresca e o tratamento de uma seed damp
  podem, em tese, truncar o clima em pontos diferentes (carros encravados
  divergem entre os braços) — o pareamento por seed continua válido pois cada
  braço é medido na PRÓPRIA corrida (par/wand contados do CSV de cada braço).
