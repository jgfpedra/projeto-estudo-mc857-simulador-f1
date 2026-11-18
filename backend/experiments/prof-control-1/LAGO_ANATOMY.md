# PROF-CONTROL-1 — Anatomia da Descida do Lago (C01)

**Data:** 2026-11-07 · **Método:** OFFLINE report-only sobre a telemetria
EXISTENTE (zero corrida nova, zero rede, zero código de produção) ·
**Instrumento:** `scripts/prof_lago_anatomy.py` (staged ANTES da execução, R7;
determinístico, `cmp=0` em duas execuções seriais) · **Testes:** 9 passed
(`test_prof_lago_anatomy.py` ×8 + `test_state_files.py`) · **Saída canônica:**
`prof-control-1/LAGO_ANATOMY.json` · **Veredito: HIPÓTESE B — subesterço de
controle (4/4 passagens com saída; zero saturação mecânica).**

## Proveniência e método

- Referência: `experiments/prof-curva-1/REF_INTERLAGOS_600S.csv`
  (SHA-256 `c00391ab…78e9b3a` conferido; 3.000 linhas, 600 s a 5 Hz, professor
  solo seed 0);
- Pista frozen Interlagos (`164876196eb12174`, 4.160,437 m);
- Teto de esterço: `F1MultiContextEnv.steer_limit_rad` canônico
  (f1_env sha `e488967f…`) = `max(0,04 rad, rad(45°)/(1+(v/25)²))`;
- Janela pinada: s ∈ [0, 80] m; saída = |lat| > 6,0 m;
- κ(s): perfil canônico suavizado 30 m (`compute_kappa_profile`, ds 4 m);
- Hipóteses: **A** se razão máxima pré-saída ≥ 98%; **B** se < 90%;
  entre 90-98% = CINZA.

## Estrutura temporal da referência (relevante para rotulagem)

O REF **largas em s ≈ 2649 m** (t=0, v≈0,75 m/s) — não na linha de largada.
Cruzamentos de linha em **t = 31,8 / 170,4 / 309,4 / 450,0 / 592,0 s** (5
cruzamentos). Portanto: segmento 1 = parcial de largada (sem passagem pela
C01); segmentos 2-5 = **4 voltas completas**; segmento 6 = parcial final.

## Anatomia por segmento (janela s ∈ [0, 80] m)

| seg | tipo | saída (t, s, \|lat\|, v) | ratio máx pré | ratio 1 s antes | ratio no instante | ticks ≥98% | veredito |
|---|---|---|---:|---:|---:|---:|---|
| 1 | parcial-largada | — (janela não atravessada) | — | — | — | — | SEM-SAIDA |
| 2 | completa | **nenhuma** (v 52,7-106,9 km/h) | 0,726 | — | — | 0 | SEM-SAIDA |
| 3 | completa | t 172,4 s · s 32,82 · \|lat\| 6,02 · 76,0 km/h | **0,734** | 0,705 | 0,636 | 0 | **B** |
| 4 | completa | t 311,4 s · s 33,65 · \|lat\| 6,06 · 76,7 km/h | **0,736** | 0,710 | 0,623 | 0 | **B** |
| 5 | completa | t 452,0 s · s 31,91 · \|lat\| 6,13 · 75,2 km/h | **0,738** | 0,704 | 0,668 | 0 | **B** |
| 6 | parcial-fim | t 594,0 s · s 31,29 · \|lat\| 6,08 · 74,7 km/h | **0,742** | 0,695 | 0,679 | 0 | **B** |

a_lat demanda nas janelas com saída: 9,24-10,13 m/s² (v²·κ suavizada);
κ máx na janela ≈ 0,041 1/m (R ≈ 24 m).

## Veredito: HIPÓTESE B — subesterço de controle / falta de feedforward

- Em **todas** as 4 passagens com saída, o esterço comandado ficou a
  **26-27% de folga** do teto mecânico (razão máxima pré-saída 0,734-0,742) e
  **ZERO ticks** atingiram 98% do limite — a Hipótese A (saturação mecânica)
  está **falsificada** nesta referência;
- no instante da saída o ratio está em **0,62-0,68** — o pure pursuit está
  **REDUZINDO** o esterço enquanto o carro espalha (comportamento típico de
  perseguição de ponto adiante sem antecipação de deriva);
- a demanda lateral (9,2-10,1 m/s²) excede o μg nominal do grip real
  (0,788 × 9,81 ≈ 7,7 m/s²) — o carro desliza largo (subesterço plástico)
  **com esterço mecânico de sobra disponível**;
- leitura mecânica: a ~75 km/h o teto é ≈ 0,460 rad (26,4°) e o controlador
  pede no máximo ≈ 0,34 rad (19,5°) — **faltou ~6,9° de volante** para vencer
  o raio efetivo da curva com a deriva dos pneus.

## Observação estrutural (para o PROF-CONTROL-1 investigar — não conclui aqui)

A passagem da volta completa pós-largada (segmento 2) foi **LIMPA** — mesma
folga de esterço (ratio máx 0,726) e velocidade MAIOR na janela (até
106,9 km/h). O gatilho da saída crônica **não é a velocidade pontual nem a
razão de esterço**: é o **estado de entrada na curva** (linha/tangente
herdada do trecho anterior — a Reta dos Boxes — e/ou história de deriva).
Isto orienta o reparo para **feedforward de curvatura/antecipação de linha**
no controlador, não para teto mecânico ou governador.

## Escopo e limitações

Report-only sobre **uma** corrida (seed 0, variedade 0 — realização única;
baterias multi-seed do professor solo exigem `--variedade`, lição
PROF-MONACO-1 V1). κ suavizada 30 m (não instantânea). Janela e limiares
exatamente os pinados no prompt executivo.

## Estado e decisão pendente do Dono

- RACING-LINE-1 **arquivado** (linha nos três ledgers; orçamento de 10
  corridas solo 100% preservado; N=9..12, N=13..16, pools 76..79 selados);
- ZERO corrida nova neste diagnóstico;
- próximo passo autorizável: **prereg do PROF-CONTROL-1** (feedforward de
  curvatura / antecipação de linha no professor solo), Freeze do Dono antes
  de qualquer implementação.
