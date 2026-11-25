# PRÉ-REGISTO — FASE H-0 (geometria): Monaco mirror-2021 + Spa mirror + detector G3
# Commitado ANTES de qualquer código de implementação. ZERO runs · ZERO pool
# (70-79 intactos) · ZERO re-pin (v1s canônicos intocados; trocar pista
# canônica = decisão do DONO, fora de escopo).
# Fonte da fila: LARGADA-4-review (a) FASE H geometria [recomendado].
# Histórico-âncora (FASE G/Trilha B, dsh-continuacao): Monaco_v1 clearance
# 1,71 m com 56 pares <8 m (ARTEFATO de spline); Spa_v1 4.352 m vs 7.004 m
# oficiais (−37,9%, INCOMPLETA no cache; spacing uniforme 3,8-4 m — o furo
# NÃO é gap, é comprimento); Suzuka_v1 crossover REAL 0,39 m (ponte/esses);
# G3 (saltos de hint de projeção) pendente.

## 1. FONTE ESPELHADA (probes registrados)
- `data/circuit_layouts_evolution.json` (F1DB, commitado) dá os SVGs oficiais
  por era, hospedados em raw.githubusercontent.com — probes HTTP 200 OK.
- **Monaco "mirror 2021" = layout `monaco-6`** (effective; anos
  ['2003-2019', '2021-2026']; metadata 19 turns; 3,34 km).
- **Spa atual = layout `spa-francorchamps-4`** (effective; ['2007-2026'];
  metadata 19 turns; 7,00 km).
- Estrutura medida (probe de parse, M/c/s/z apenas): fechamento gap
  **0,00 u** nas duas fontes (o `z` fecha exato); L_svg 1.616,4 u (Monaco) /
  1.606,7 u (Spa); escalas de calibração esperadas 2,0644 / 4,3591 m/u;
  n_wp@4 m ≈ 834 (Monaco) / 1.751 (Spa).

## 2. PIPELINE H1/H2 (mecânica pinada)
1. Download do SVG (black-outline; URL do JSON commitado).
2. Parse do `d`: comandos **M, c, s, z** (exatamente os que as fontes usam;
   qualquer outro comando → PARE documentado). Béziers amostradas a
   24 pontos/curva; loop fechado pelo `z`.
3. Gate de fechamento: gap |end−start| ≤ 1% de L (medido: 0,00% nas duas).
4. Reamostragem em arco a **ds = 4,0 m** (convenção das frozen: 3,7-4 m).
5. **Calibração de escala = comprimento oficial / L_svg** — Monaco
   **3.337 m** (tabela do audit_track_geometry) e Spa **7.004 m** (pinado
   pela task). Declaração: o mirror é calibrado AO OFICIAL por construção;
   a validação de completude vem do GATE (G4 turns + G2/G1 + G5), não do
   comprimento.
6. **NOME dos artefatos (desvio documentado com razão)**: NÃO
   `Monaco_v2.json`/`Spa_v2.json` — o `load_track_frozen` dá PRIORIDADE a
   `{key}_v2.json` sobre v1 (R2 S4): nomear assim MUDARIA a pista canônica
   sem decisão do dono (PARE de escopo). Nomes: **`Monaco_mirror2021_v1.json`**
   e **`Spa_mirror_v1.json`** — carregáveis apenas via `--track` explícito
   com esses nomes; **Monaco_v1/Spa_v1 permanecem as canônicas intactas**;
   adoção/rename = dono.
7. Campos: mesmos do formato v1 (`name, waypoints, width_m=12,0, sf_idx,
   n_wp, sha256` hex[:16] do JSON menos o campo sha — convenção do loader) +
   **chaves aditivas de proveniência** (source_svg, era, official_length_m,
   scale_m_per_unit, gate_clearance_min_m, gate_crossovers, r_min_m,
   sf_note). `sf_idx = 0` com **limitação documentada**: a fonte SVG não
   marca SF nem direção de percurso — âncoras de CORRIDA (SF/direção) são
   decisão da era de adoção; H-0 congela GEOMETRIA.

## 3. GEOM GATE (pinado; definições idênticas ao audit_track_geometry.py)
- **G1 clearance ≥ 8,0 m**: distância mínima centro↔centro entre segmentos
  NÃO-adjacentes (gap de arco > 40 m) ≥ 8,0 m. [Monaco_v1 falharia: 1,71 m]
- **G2 zero crossover**: nenhuma interseção entre segmentos não-adjacentes.
- **G3 R mínimo ≥ 8,0 m**: κ por 3 pontos consecutivos; reportar a
  distribuição de R por curva (hairpins/esses DOCUMENTADOS no relatório;
  Monaco real: hairpin do Loews ≈ 10-11 m — floor de 8 m afasta artefatos
  de parse sem reprovar geometria real).
- **G4 turns detectados = metadata ± 3**: picos de κ (limiar κ ≥ 0,02 1/m,
  separação mínima 30 m de arco) — Monaco 19±3; Spa 19±3. É o detector de
  COMPLETUDE (uma fonte truncada tipo Spa_v1 teria ~10 turns).
- **G5 comprimento calibrado**: |L − oficial| ≤ 0,1% (sanity da calibração).
- **Gate FAIL → NÃO congela + PARE documentado com as métricas** (achado
  sobre a FONTE, registrado; zero artefato).
- H2: download/parse/fonte incompleta → PARE documentado; **ZERO spline
  fabricado para "completar"**.

## 4. H3 — DETECTOR G3 de saltos de hint (critério pinado; REPORT-ONLY)
Sobre TODAS as frozen (9 v1/v2 existentes) + os 2 mirrors (se congelados):
- **(a) gaps de espaçamento**: |Δs| entre waypoints adjacentes > 12,0 m
  (3× ds) = buraco de dados.
- **(b) risco de salto de hint**: pares de segmentos NÃO-adjacentes (gap de
  arco > 40 m) com distância mútua < 2,0 m = AMBIGUIDADE da projeção
  nearest-segment (onde o hint pode saltar de braço — o caso Suzuka 0,39 m).
- Relatório por pista: n_gaps, n_riscos, clearance mín, localizações (s).
  **Validação esperada (declaração prévia)**: Suzuka_v1 DEVE flaggear riscos
  (crossover real); Monaco_v1 DEVE flaggear (artifact 1,71 m); Spa_v1 NÃO
  deve flaggear gaps (spacing uniforme medido — o furo dela é comprimento).
  ZERO mudança de runtime.

## 5. TESTES ADITIVOS (5; suite esperada 25F/301P/2S — 296 + 5)
t1 parser de path (d sintético M/c/s → pontos Bézier esperados);
t2 resample+fechamento (ds≈4 m; loop fechado; n_wp);
t3 gates sintéticos (clean PASSA; fold <8 m falha G1; cruzamento falha G2;
R apertado falha G3);
t4 artefatos (se congelados): load_track_frozen(strict) carrega os mirrors
+ métricas de gate nos JSONs batem com o recomputado;
t5 detector sintético (near-touch <2 m flaggeado; gap 20 m flaggeado).
Reparos = +1 teste com disclose (padrão REPARO).

## 6. RAMOS / PAREs transversais
- Prereg ausente antes de código; qualquer run de corrida; consumo de pool;
- re-pin de pista canônica (os v1s são INTOCÁVEIS; o loader permanece
  inalterado — zero mudança em f1_env);
- edição em commits fechados; fabricação de geometria (spline para
  "completar"); download falha/parse falha/gate FAIL sem PARE documentado.

## 7. Orçamento
ZERO corridas. Downloads SVG = probes de build registrados (monaco-6,
spa-francorchamps-4; nada de runtime depende de rede — os artefatos
congelados são commitados).
