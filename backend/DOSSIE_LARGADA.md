# DOSSIÊ LARGADA — fecho canônico do CICLO LARGADA (2026-10-19)
> Local ÚNICO canônico da frente LARGADA; referenciado pelo PROJECT_STATE.md
> e pelo worklog. ZERO runs neste fecho; pools intatos (70-79 virgens).

## 1. A QUEIXA e a CADEIA CAUSAL (âncoras)
**Queixa original**: carros fora na 1ª curva de Interlagos (Senna S) na
largada. O CICLO LARGADA a decomps e fechou em três fases:

- **F0 — ANATOMIA** (prereg 071bc37; anatomia 056421c; decomposição 82b12c6):
  a queixa é uma cascata de **CONTATO**, não de tempo-fora: share_largada
  mediana **0,074** (< 0,20 pinado; P-C FAIL → PARE e alvo redefinido pela
  revisão). A 1ª excursão ocorre 20/20 em t 4,2-8,4 s na entrada do Senna S
  (s 2699,7-2814), **20/20 CONTATO-ADJ** (contato do dono em ±2 s); a massa
  de pares da janela W=[0,60 s] é **ENTRADA-S 228/348 (65%)** vs GRID 112
  (32%); os pares ADJACENTES à 1ª excursão são **20/20 em ENTRADA-S, 0 no
  grid**; contatos já no grid em t 1,2-1,4 s. 1ª excursão por posição de
  grid: P2 6× (não P1).
- **F1a — LAUNCH-CAP** (a falsificação; prereg a3b8ff0, impl d81b842,
  reparo 4b0d4eb, veredito 7f10fb0, fecho f1ebccd): o cap (teto 0,8×v_plan
  na janela t<30/s<2950) **engajou em 10/10 carros** (74-137 cap-ticks/run,
  fase 0 violações pós-reparo do flag-fantasma off-track) e **não reduziu
  nada** (pares_W med 18 ≈ âncora 17; 1ªs excursões idem CONTATO-ADJ 9/10)
  → **hipótese VELOCIDADE REFUTADA** (fator uniforme preserva a geometria
  relativa; o funil do v_plan recomprime no mesmo ápice). Efeito colateral
  decisivo: **fora% <15 em 0/10 → E1 (keying) CONFIRMADO POR MEDIÇÃO** — o
  efeito da era contaminada era o bug de keying, não pacing. Em úmido PIORA
  (s50 WET: par 22 vs 12; cc +31%).
- **F1b — LAUNCH-STAGGER** (a validação da densidade e o atrator; prereg
  cd3ca5e, impl+veredito 52fa020, reparo tick-exato ea1194a, fecho
  a614cb0): release escalonado (pos−1)×1,0 s frente→trás, hold th=0/brk=1
  com rec.clear() (pós-release canônico). Smoke pegou bug real de
  boundary (float +=0,1 → 0,99999<1,0; fix em TICKS com round; +t6).
  GATE (14 runs, 60-69, 1/10 DAMP s60): **PRIMÁRIO-1 (vinculante) PASS
  ESMAGADOR — pares_W mediana 2, máx 4 vs âncora 12-23/med 17: a
  DENSIDADE de grid É o mecanismo do storm de largada**. MAS: **PRIMÁRIO-2
  FAIL 5/10 — a 1ª excursão reaparece em 10/10 runs a t=32,8 s, s≈31-35 m
  (o FIM DA VOLTA 1 — o MESMO sítio/modo da era contaminada: 32,6 s @
  s≈37)**: o campo RE-EMPACOTA dentro de uma volta e a
  excursão-por-contato reemerge (CONTATO-ADJ em 5/10). s60 (DRY→CLOUDY→
  DAMP): cc 9.268 vs base 6.418 (+44%) — úmido piora com campo segurado
  (mesmo padrão do cap). **GATE FAIL → PARE; SEM re-pin, SEM re-run.**

## 2. ENUNCIADO DO TETO (canônico)
Com este stack — **perfis de velocidade idênticos por carro (v_plan
compartilhado) + zero coordenação inter-carros** — o empacotamento do campo
é **ESTRUTURAL**: intervenções de largada NÃO eliminam a 1ª
excursão-por-contato; **transferem-na** (deterministicamente para o fim da
volta 1, s≈31-35 m, quando o campo re-converge ao funil do v_plan). O
launch-storm como fenômeno de campo é o **teto documentado do produto**.

## 3. DISPOSIÇÃO DE PRODUTO
- **Mitigação canônica do sintoma**: alavanca rejoin-gap X=20 **opt-in**
  (−44% de taxa de perigosas no seco; C' 40-49 8/8; DISPOSIÇÃO FINAL
  canônica no PROJECT_STATE). Único flag VIVO do ciclo ALAVANCA.
- **--launch-cap e --launch-stagger: research-negativas, default OFF**
  (código e testes preservados; cap×stagger mutuamente exclusivos).
- **GRID-ERA CONTRA-INDICADA**: a evidência do atrator (a fortiori
  empírica: o stagger deu gaps ≥ aos que o espaçamento de grid daria e o
  campo re-empacotou dentro de UMA volta) + custo de re-pin total.
- Regra de template permanente: todo prereg futuro declara no orçamento
  "+1 re-smoke contingente (s0)" (errata LARGADA-FECHO-0).

## 4. LEAD FUTURO PRÉ-ANEXADO (com ressalva explícita)
- **19/20 pares residuais de largada envolvem um carro SOFT** (HARD/SOFT 8,
  MEDIUM/SOFT 9, SOFT/SOFT 2 — estratificação do veredito L-1b). Insumo
  para eventual ciclo de compostos/heterogeneidade.
- **RESSALVA (N2 do fecho)**: os CARROS da 1ª excursão não seguem o padrão
  SOFT (7 MEDIUM / 2 HARD / 1 SOFT — sem dominância): o lead SOFT aplica
  aos pares de contato residuais da janela de largada, NÃO ao evento de
  re-empacotamento. E o atrator (§2) limita o ganho de QUALQUER intervenção
  de largada: um ciclo de compostos atacaria os pares residuais, não o
  re-empacotamento estrutural.

## 5. DIAGNÓSTICOS DO FECHO (PASSO 1; script largada_fecho_diag.py)
- **N1 — GUARD-V (veredito L-1b, recomputada)**: `GUARD-V 10/10 voltas:
  PASS` (10 tratamentos, todos com 10/10 carros ≥1 volta).
- **N2 — 1ªs excursões (t≈32,8 s, s≈31-35 m) por carro/composto**:
  s60 VER/MEDIUM · s61 SAI/HARD · s62 VER/MEDIUM · s63 PIA/MEDIUM ·
  s64 RUS/HARD · s65 NOR/MEDIUM · s66 PER/MEDIUM · s67 HAM/MEDIUM ·
  s68 ALO/MEDIUM · s69 VER/SOFT → **SOFT 1/10: SEM padrão dominante**
  (anotada a ausência; ambos os desfechos dossiê-válidos; nenhum ciclo
  novo abre a partir disto).
- **N3 — runs→arquivos L-1b (14 runs → 13 CSVs principais)**: run 1
  base_s0 (flag-off) · run 2 stg_s0 v1 (release não-exato 6/10)
  **SOBRESCRITO** · run 3 stg_s0 re-smoke pós-ea1194a (arquivo re-usado;
  SELF 3/3) · run 4 base_s60 (pareio damp) · runs 5-14 tratamentos
  s60-s69. (No disco: 13 CSVs principais + 13 _events = 26 arquivos.)

## 6. INVENTÁRIO DO CICLO
- **Runs**: L-0 = ZERO (anatomia offline) · L-1a = 14 (2 smoke + 1
  re-smoke + base s50 + 10 trat 50-59) · L-1b = 14 (2 smoke + 1 re-smoke +
  base s60 + 10 trat 60-69) · scans de clima = ZERO runs (scanner offline
  validado 30/30). **Total do ciclo: 28 corridas.**
- **Pools**: 0-19 = âncoras cegas · 20-29 = queimados (instrumento
  contaminado) · 30-39 = consumidos (re-gate ALAVANCA C) · {2,8,9} =
  consumidos (D adverso) · 40-49 = consumidos (C') · 50-59 = consumidos
  (L-1a) · 60-69 = consumidos (L-1b) · **70-79 = INTACTOS (próximo
  virgem)**.
- **Flags**: `--rejoin-gap 20` OPT-IN VIVO (seco) · `--launch-cap` morta
  (default OFF) · `--launch-stagger` morta (default OFF).
- **Hashes âncora**: 82b12c6 (decomposição 0-c) · a3b8ff0 (prereg L-1a) ·
  cd3ca5e (prereg L-1b) · a614cb0 (fecho L-1b) · 071bc37 (prereg L-0) ·
  056421c (anatomia) · 7f10fb0 (veredito L-1a) · 52fa020 (veredito L-1b) ·
  362ec3a (scan 50-59) · 6551bac (scan 60-69) · 0268919 (probe Δt).
- **Instrumento**: weather_scan.py (teorema do prefixo, 30/30) ·
  largada_anatomy.py / largada_decompose.py / largada_dt_probe.py /
  largada_fecho_diag.py (leitura) · leak-checks (pair/self/exc/drift) ·
  doc-integrity (test_state_files.py).

## 7. RATIFICAÇÃO E RESOLUÇÕES (LARGADA-4, 2026-10-19)
- **Fecho RATIFICADO** pela revisão LARGADA-2 (ANEXO B, apendado VERBATIM ao
  worklog no commit **8bd728c**): R1-R5 ratificam o PARE do L-1b ("o FAIL
  mais produtivo do projeto"), o atrator (R2) e a regra de template do
  re-smoke (R3). **DECISÃO DE FILA da revisão: FECHAR O CICLO LARGADA** —
  grid-era contra-indicada com contra-evidência empírica direta (a fortiori
  medido); 19/20-SOFT = lead pré-anexado, não ciclo; mitigação canônica =
  rejoin-gap opt-in. *(Veto do dono registrado no ANEXO B.)*
- A pendência do ANEXO B registrada no fecho está RESOLVIDA (texto recebido
  nesta ordem e colado sem edição).
- AUDITORIA_RL.md: a referência fantasma foi resolvida por RESTAURAÇÃO do
  histórico (ver proveniência no topo do arquivo) — ver PROJECT_STATE.
