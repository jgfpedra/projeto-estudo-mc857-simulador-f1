# PRÉ-REGISTO — CICLO LARGADA, FASE 0: ANATOMIA OFFLINE (zero corridas)
# Commitado ANTES do script de análise. Orçamento: ZERO corridas — tudo é
# leitura de CSVs existentes + 1 script (scripts/largada_anatomy.py).
# Qualquer run → PARE + novo prereg.

## 1. CORPUS (inventário read-only, executado)
- **Braços CEGOS (a anatomia usa SÓ estes — 20 runs)**:
  `experiments/diag-r2-r13/race_diag_r10_blind_s{0..9}.csv` (geraram
  recontagem_cego_s0_9.csv) e `experiments/diag-r2-r13/race_diag_r13_b_s{1}0..19.csv`
  (geraram as 10 taxas [0,306;0,328;0,317;0,441;0,333;0,406;0,267;0,310;0,300;0,350]).
  Todos com `_events.csv` (instrumento solver-side) e 30.000 linhas/carros-run.
- **ANEXO CONTAMINADO (insumo de design, NUNCA evidência)**: os CSVs do
  instrumento contaminado 30-39 pré-reparo EXISTEM —
  `experiments/diag-alv-seco/race_diag_alv_gap_s{20..29}.csv` (10) +
  `race_diag_alv_smoke_gap_s0.csv` (1). Rotulados CONTAMINADO em toda saída.

## 2. DEFINIÇÕES (declaradas ANTES do script)
- **Janela de largada W = t ∈ [0, 60 s]**. Ancoragem: 1ª excursão histórica
  4,2 s; contrafactual do pacing contaminado 32,6 s — ambos < 60 s; 1ª volta
  real ~110 s+.
- **1ª excursão** = primeiro evento offtrack do run: a PRIMEIRA linha (por
  t_s) com `offtrack=1` do CSV. Coluna/critério IDÊNTICOS aos gates
  (`offtrack` = abs(lat) > meia-largura, escrita pelo race_diagnostic;
  amostragem 5 Hz — 30.000 linhas/run, 3.000/carro).
- **share_largada** = fora(W)/fora(total) do run = nº de amostras offtrack
  com t_s ≤ 60 dividido pelo total de amostras offtrack do run.

## 3. MÉTRICAS POR RUN (20)
t/s/driver da 1ª excursão; contatos em W (pares distintos (drv_a,drv_b) com
≥1 evento solver em t≤60 s; t do 1º evento do par; s = s do drv_a no tick);
v média do campo em t ∈ {2,4,8,15} s (média das 10 linhas do tick exato);
gap médio do campo em t=10 s (por carro: min Δs>0 aos demais módulo
L=4160,4 m — comprimento do polígono frozen, contrato de instrumento;
irrelevante no pelotão de largada); compostos por fileira (grid_order P1-P10
do cabeçalho, fileiras (P1,P2)...(P9,P10), composto de cada carro do mapa
`compounds`); share_largada; taxonomia da 1ª excursão.

**Taxonomia da 1ª excursão (mecânica)**: CONTATO-ADJ = evento solver do DONO
com |t − t_exc| ≤ 2 s; OUTRO = evento do dono em (2, 10] s; PILOTAGEM =
nenhum evento do dono em ±10 s.

## 4. PREDIÇÕES PRÉ-REGISTRADAS (falsificáveis)
- **P-A**: ≥ 14/20 runs com 1ª excursão em W (t ≤ 60 s). FAIL → prossegue com
  re-atribuição obrigatória no relatório (NÃO é PARE).
- **P-B**: ≥ 12/20 runs com 1ª excursão na região da 1ª curva.
  **EMENDA ANTES DO COMMIT (âncoras documentadas citadas)**: o prompt ancora
  "s ∈ [550, 850] (âncora: RUS 4,2 s @ s≈685 m)". As âncoras REGISTRADAS
  dizem: RUS 4,2 s @ **s=2702,685 m** (exc-check do smoke B, registro do
  ead15a7/9553105 — o "≈685" é a mantissa de 2702,685) e o cluster da
  largada 10/10 em **s 2698-2814, mediana 2757** (ALAVANCA P0 0-d, commit
  115e0b6) — pós-SF (SF=2655), a entrada do Senna S no s-coordenada do
  frozen. **Região EMENDADA: s ∈ [2650, 2950]** (cobre o cluster registrado
  com margens). A região literal [550, 850] também é reportada no relatório
  (esperado 0/20 — transparência). FAIL → prossegue com re-atribuição de
  escopo.
- **P-C (premissa do dossiê)**: share_largada MEDIANO ≥ 0,20.
  Derivação citada (antes do script): efeito-largada documentado por
  diferença de instrumentos — contaminado 10,4-14,8% fora vs histórico
  17,3-26,3% (mín 21,0 na década 10-19) ⇒ diferença ~6-11 pp sobre 17-26 pp
  ⇒ largada ≈ 1/4 a 1/2 do tempo fora. **FAIL (< 0,20) → PARE: premissa
  "maior fonte única" cai → re-prioritização com a revisão antes de
  qualquer L-1.**
- **SELF-checks do script (divergência → PARE: instrumento de análise
  regrediu)**:
  (i) as 10 taxas exatas da década 10-19 (via `lever_gate_verdict.stats`) ==
  [0,306; 0,328; 0,317; 0,441; 0,333; 0,406; 0,267; 0,310; 0,300; 0,350] E
  mediana == 0,323;
  (ii) valores da década 0-9 == `recontagem_cego_s0_9.csv` commitado
  (120081e), campo a campo (exc/reent/perigosas/taxa/off/rol/n_comp/par/wand);
  (iii) 1ª excursão de `race_diag_r10_blind_s0.csv` == **('RUS', 4,2,
  2702,685)** (arquivo citado pelo smoke B do ead15a7).

## 5. VEREDITO
- Mecânico por `scripts/largada_anatomy.py` (commitado JUNTO a este prereg):
  SELF-checks → tabela por run → P-A/P-B/P-C com os limiares pinados acima.
- Saídas: `experiments/largada_anatomia_cego_s0_19.csv` (âncora commitada —
  convenção 120081e: único artefato de dados no git) +
  `experiments/largada_anexo_CONTAMINADO.csv` (11 runs, rotulado, insumo de
  design: distribuição da 1ª excursão com o hold de largada — modo esperado
  ~32,6 s — e fora%).
- RAMOS: SELF-check falho → PARE. P-C < 0,20 → PARE (re-prioritização).
  P-A/P-B FAIL → prossegue com re-atribuição no relatório. Ao fim: append no
  worklog.md (Task ID: LARGADA-0).

## 6. NOTA L-1 (para o relatório, SÓ TEXTO)
Nada de código de alavanca nesta sessão. A proposta L-1 (pacing: o quê
exatamente — hold/cap de v/por quanto tempo/por composto; dinâmica-alvo;
guards preliminares; pool 50-59 com weather scan declarado ANTES do gate —
lição 30-39; mecanismo NÃO pode ler clima no runner — lição GUI≠headless)
vem da anatomia medida.
