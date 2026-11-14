# PRÉ-REGISTO — ADOÇÃO-H-2: mirrors como canônico (dono aprovou: AMBOS)
# Commitado ANTES de qualquer mudança/medida. ZERO corridas · ZERO pool
# (70-79 intactos) · ZERO re-pin · ZERO edição em commits fechados ·
# loader INTOCADO. Evals determinísticos de gate PERMITIDOS.
# PARE adicional: QUALQUER número de ALUNO antes do professor = violação.

## 1. ESCOPO PINADO PELO DONO
**AMBOS**: Monaco_mirror2021_v1.json → **Monaco_v2.json**; Spa_mirror_v1.json
→ **Spa_v2.json**. A prioridade `{key}_v2.json` EXISTENTE do loader faz a
troca (mesma convenção do interlagos_v2 canônico). v1s → `archive/tracks_frozen_v1/`
com README de proveniência (NUNCA deletar). NENHUMA cópia duplicada com nome
inerte no diretório frozen.

## 2. SHAS DE CONTEÚDO (conferidos pós-mv)
- **Monaco_v2 = 67ca11dc211c8c78** (834 wp; G1 16,30 m; G2 0; G3 11,34 m;
  G5 0,05%).
- **Spa_v2 = 4b05f2c3bbc625fc** (1.751 wp; G1 24,83 m; G2 0; G3 14,66 m;
  G5 0,01%). [DISCLOSE: difere do 2637c8adf3c37939 citado no memo da review
  porque a errata R8 (nota aditiva `r8_hypothesis` de HIPÓTESE ABERTA,
  ordenada no PASSO 0, commit ce4e799) alterou o conteúdo — sha recomputado
  e conferido.]
- v1s arquivados: Monaco_v1.json = 07e7ef4dd6af4517; Spa_v1.json = sha do
  arquivo (conferido no arquivamento).

## 3. PROFESSOR-FIRST (árvore pinada, POR PISTA, ANTES de qualquer swap)
**Instrumento (ZERO mudanças de código)**: o RUNNER —
`race_diagnostic.py --controller professor --n-cars 1 --track <nome> --ticks 6000`
(a engine/grid/controlador do gate all-professor menos os outros 9 carros;
cadeia do professor SEM governor). POR NOME EXPLÍCITO nos mirrors ANTES do
swap: `--track Monaco_mirror2021` e `--track Spa_mirror`.
- **PASS por ep = ≥2 voltas completas** (cruzamentos de SF − 1 ≥ 2) nos 600 s
  (critério da canária ERRATA #2, instrumento frozen da era).
- **3 eps por mirror** (determinístico: os 3 devem ser idênticos — bit-check
  dos CSVs).
- **ÁRVORE POR PISTA**: professor 3/3 no mirror → pista adotada E re-ancora
  (B' aluno 3 eps pós-swap + Meta A se aplicável). Professor <3/3 → swap
  MANTIDO (geometria superior é fato medido; aprovação do dono), B' NÃO
  re-ancora naquela pista (número era-v1 anotado + nova limitação
  documentada por nome). Registro honesto em AMBOS os ramos.

## 4. HIPÓTESES MARCADAS (motivação, nunca dado)
- **H-Mon**: B' Monaco 0/3 era limitado pelo ARTEFATO (clearance ~1,6-1,7 m
  — rótulo N2; 45 riscos de hint; 56 pares <8 m). Falsificação: aluno 0/3
  com professor 3/3 sob o mirror ⇒ gargalo é pilotagem/física; B' Monaco
  permanece ✘ honesto.
- **H-Spa**: B' Spa 3/3 foi medido na TRUNCADA (4.352 m — R8); nos 7,004 m
  completos (Eau Rouge/Kemmel/Blanchimont) a sustentação é incerta.
  Falsificação: aluno <3/3 com professor 3/3 = degradação real de
  generalização, registrada.

## 5. VALIDADE EXTERNA (declarada)
R_min do mirror de Monaco (11,34 m) é MAIS SUAVE que o hairpin real (~7 m —
consequência do SVG+resample). B' passa a valer **"SOB MIRROR"** (tag na
tabela de metas). Números históricos Monaco/Spa permanecem registros
**"era v1"** anotados — NUNCA apagados.

## 6. RE-BASELINES ENUMERADOS (antes de rodar; só nas pistas com professor 3/3)
- **B' (aluno 3 eps por pista adotada, pós-swap)**: runner
  `--n-cars 1 --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode
  edge --gov vplan --ticks 6000 --track Monaco|Spa` (canária ERRATA #2 — o
  instrumento solo-frozen da era; era-v1 para comparar: Monaco 0/3, Spa 3/3).
  PASS por ep = ≥2 voltas completas; fora% reportado.
- **Meta A Monaco (professor)**: Monaco ESTAVA nas 8 pistas do professor
  (teacher_benchmark.py TRACKS.TESTE inclui Monaco; registro 40/40 = 5
  eps/pista × 8). MESMO protocolo (eps): **professor 5 eps** em Monaco_v2
  (pós-swap), runner, grip real (o instrumento do gate; a variante grip 1.0
  do benchmark fica report-only se rodada). PASS por ep = ≥2 voltas.
- **51-eps = annotation-only** (nenhuma run; registros v14/v10 anotados como
  era-v1).
- Outras linhas canônico-dependentes: NENHUMA identificada (produtos de
  corrida usam interlagos — não afetado pela adoção).

## 7. INSTRUMENTO DE TESTES (suite esperada: **25F/304P/2S** — exato)
- **t-inércia REESCRITO (flip)**: pós-swap, `load_track_frozen('Monaco')` →
  Monaco_v2 (conteúdo mirror; sha 67ca11dc211c8c78) e `'Spa'` → Spa_v2
  (sha 4b05f2c3bbc625fc).
- **t-novo (+1)**: v1s em `archive/tracks_frozen_v1/` permanecem artefatos
  VÁLIDOS — leitura direta do JSON + sha de conteúdo conferido
  (07e7ef4dd6af4517 e o da Spa_v1) + `Track.from_waypoints` constrói.
  [DISCLOSE: o loader NÃO consulta archive/ (INTOCADO por PARE) —
  "loadável" = via JSON direto; o runner por design não vê os v1s.]
- Delta além dos 2 declarados = justificar no prereg. Esperado: 303+1 = 304P.

## 8. ORÇAMENTO E PAREs
- Zero corridas; evals determinísticos: professor 3+3 (mirrors) + aluno
  3+3 (adotadas) + Meta A Monaco 5 = **17 evals solo de 600 s** (1 carro,
  determinísticos — os triplos/quíntuplos confirmam bit-identidade).
- PAREs: corridas; pool (70-79); clima no runner; re-pin; errata
  não-aditiva; edição em commits fechados; trocar canônico de novo sem
  dono; ALUNO antes do PROFESSOR; subir fastf1 neste ciclo.
