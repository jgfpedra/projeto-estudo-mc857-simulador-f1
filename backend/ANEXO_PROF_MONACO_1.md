# ANEXO_PROF_MONACO_1 — Diagnóstico READ-MOSTLY do professor-solo em Monaco_v2 (2026-10-22)

> Ciclo PROF-MONACO-1 · Branch `feat/sanidade-produto` · Prereg
> `backend/PREREG_PROF_MONACO_1.md` (2aa018c, ANTES de qualquer coleta).
> Instrumento de desfecho: `scripts/saidas_verdict.py` generalizado
> (`--track`; GOLDEN Interlagos provado byte-idêntico). NENHUM reparo.
> ZERO treino. ZERO corridas 10-carros. Pools 70-79/76-79 INTOCADOS.

## 1. Cadeia
99ec615 (P0: ANEXO ERRATA-SAIDAS-1-review verbatim + R5-a/R5-b consolidadas
— canônicos 23,6 e 11/20=55,0 + proveniência R1 VAZIA + NITs 1/2/3) →
2aa018c (prereg F1 + errata de calibração §10 pré-coleta) → 1ecf52d
(instrumento F2: `--track`/bateria multi-ep/Σ fail-loud; +6 testes; golden
AS 6 TABELAS BYTE-IDÊNTICAS) → 12 sims seriais (5 prof s0-4 + paridade;
5 aluno s0-4 + paridade; 600 s; re-smoke contingente NÃO consumado: 12/14)
→ 205c2c6 (evidência + bateria Q1-Q4 + verificação V1-V3b) → fechamento.

## 2. Verificação instrumental (probe prof_monaco_f4.py, commitado)
- **V1 — DEGENERESCÊNCIA DE SEED**: TODOS os seeds 0-4 BIT-IDÊNTICOS por
  braço (linhas de dados). Em modo solo + clima SECA sem transição + sem
  `--variance`, o seed NÃO TEM canal estocástico: a "bateria 5-seeds" é
  **1 realização determinística + 4 réplicas** (as paridades s0×2
  fecharam bit-a-bit). Os ICs cluster degeneram em ponto — o Q4
  mecânico por ICs é, na prática, uma comparação DETERMINÍSTICA entre
  duas corridas. LIÇÃO: baterias multi-seed em solo exigem um canal de
  variância (`--variedade` no runner GUI seria o canal; no
  race_diagnostic solo o seed só atua via clima com transições).
- **V2/V2b — cross-era BIT-IDÊNTICA**: aluno_s0 == aluno_Monaco_ep1 e
  prof_s0 == metaA_mon_1 da ADOÇÃO-H-2, byte a byte (3001 linhas). A
  bateria REPRODUZ a era exatamente; os números herdados (45,0%/34
  excursões; 56,9%) são a MESMA realização. NOTA: os eps metaA eram
  janela **600 s** ("2 voltas" = voltas COMPLETAS no cap, ~212 s/volta)
  — o F0 desta sessão corrigiu a leitura "2-voltas de janela".
- **V3 — ERRATA DE TAXA (era ADOÇÃO-H-2)**: o "preso acumulado 118 s"
  herdado era **1185 ticks ÷ 10** — erro aritmético de taxa: o R3 do
  runner opera sobre LINHAS do CSV a 5 Hz ⇒ **CANÔNICO = 1185 × 0,2 s =
  237,0 s** (o log da era confere: `preso=1185 ticks`). Classe da NIT
  "exibição temporal" da ERRATA-SAIDAS-1-review, agora com erro 2×. O
  preso do aluno vive DENTRO do churn de cascata (237,0 ≤ 254,5 s/ep).

## 3. Bateria Q1–Q4 (verbatim do instrumento; experiments/prof-monaco-1/)

### Reconciliação por ep (todas idênticas — ver V1)
- PROFESSOR (solo-frozen): **fora 56,9% | 41 eventos | dur_med 6,8 s** (×5)
- ALUNO (v10-cego): **fora 45,0% | 34 eventos | dur_med 6,1 s** (×5)
- [PASS] Σ solo por curva == total em ambos (fail-loud).

### Q1 — Ranking (top-5; EXPECTATIVA FALSIDIFICADA — report-only)
| # | Professor | exc | % | | Aluno | exc | % |
|---|---|---|---|---|---|---|---|
| 1 | **Reta / Outro** | 50 | 24,4% | | C03 | 30 | 17,6% |
| 2 | C11 | 45 | 22,0% | | C04 | 30 | 17,6% |
| 3 | C04 | 30 | 14,6% | | C11 | 30 | 17,6% |
| 4 | C12 | 20 | 9,8% | | C10 | 20 | 11,8% |
| 5 | C06 (hairpin) | 15 | 7,3% | | C12 | 20 | 11,8% |

**FALSIDICAÇÃO-Q1 (report-only, conforme prereg): RETA no top-1 do
professor** → lead de REJOIN-CASCATA. O hairpin geométrico (C06, κmax
0,1602, R 6,2 m do perfil) NÃO domina — a expectativa "hairpin/Loews no
top-1" caiu.

### Q2 — Assinatura cinemática (top-5 professor)
Reta n=50 v_med 37,2 IQR 8,6 [LR:50] | C11 n=45 34,9 IQR 8,1
[LR:25/SL:20] | C04 n=30 42,0 IQR 10,4 [LR:15/SL:10/**SP:5**] | C12 n=20
33,1 IQR 5,9 | C03 n=15 53,1 **IQR 0,5** (determinística, template
C01/C06 do Interlagos). Aluno: C11 IQR 43,8 [SP:10] e C10 IQR 42,7
(heterogêneas, template C07).

### Q3 — Anatomia (cascata ≤10 s × limpa × wanderer >60 s)
| Perfil | classe | eventos | % | tempo acum (5 eps) |
|---|---|---|---|---|
| PROFESSOR | REJOIN-CASCATA | 194 | **94,6%** | 1653,4 s |
| PROFESSOR | SAIDA_LIMPA | 11 | 5,4% | 54,6 s |
| PROFESSOR | WANDERER | 0 | 0% | 0 |
| ALUNO | REJOIN-CASCATA | 157 | **92,4%** | 1272,4 s |
| ALUNO | SAIDA_LIMPA | 13 | 7,6% | 77,6 s |
| ALUNO | WANDERER | 0 | 0% | 0 |

O "preso" herdado decomposto: o fora de ambos os braços é **CHURN de
reentrada** (sai → volta → sai ≤10 s), não 34/41 saídas independentes;
zero wanderers. As 34 excursões do aluno ≈ 31,4 cascata + 2,6 limpa por ep.

### Q4 — Herdado ou degradado (VEREDITO MECÂNICO = PARE)
- PROFESSOR: fora 56,93% [IC degenerado 56,93–56,93]
- ALUNO: fora 45,00% [IC degenerado 45,00–45,00]
- **FALSIDICAÇÃO-Q4: aluno ABAIXO do professor (45,0 < 56,9; −11,9 pp)
  com ICs disjuntos** (determinístico — V1) → **PARE IMEDIATO pelo
  prereg §6**: a premissa "o fora do aluno é herdado dos rótulos do
  professor" está FALSIFICADA — o aluno é MELHOR que o professor na
  pista-gargalo; "herdado" E "degradado" estão refutados de uma vez.

## 4. Erratas consolidadas por este ciclo
- **R5-a** (SAIDAS-1): C07 IQR-B **canônico 23,6** (raw 23,6327) —
  republicado confirma; "original 24,2" era display-slip.
- **R5-b** (SAIDAS-1): Reta-B solo **canônico 11/20 = 55,0%** — errata
  confirma; "original 16/20" era display-slip.
- **R6 (NOVA — era ADOÇÃO-H-2)**: preso acumulado do aluno_B' Monaco_v2
  **canônico 237,0 s** (1185 ticks × 0,2 s; o herdado "118 s" dividira
  por 10 — erro de taxa; classe da NIT de exibição temporal, 4º caso).
- **Calibração κ** (pré-coleta, §10 do prereg): o κmax do perfil (0,1602;
  R 6,2 m) é métrica distinta do r_min 11,34 do builder; identificação do
  hairpin por κmax máximo inalterada.
- **Leitura de era**: eps metaA/aluno da ADOÇÃO-H-2 eram janela 600 s
  (as "2 voltas" eram completas no cap) — F0 desta sessão.

## 5. Leitura conjunta (marcada; zero coleta adicional)
1. O fora do professor em Monaco_v2 é **auto-infligido por churn de
   reentrada** (94,6% cascata; reta 24,4% top-1): o carro sai, retorna e
   volta a sair em ≤10 s — o problema é o RETORNO/pós-reentrada, não a
   geometria do hairpin (que responde por só 7,3%).
2. O aluno NÃO herdou o pior do professor: 45,0 < 56,9 (−11,9 pp
   determinístico). A ressalva da B' (fora 45%) é MELHOR que a Meta A do
   professor — o gargalo da Meta A é o PRÓPRIO professor, não o aluno.
3. Zero wanderers e zero spins relevantes em solo (SP:5 só em C04-prof;
   SP:10 em C11-aluno); os modos dominantes são LINHA-RETA/SLIDE — o
   mesmo padrão do SAIDAS-1 no Interlagos.
4. **Proposta de ciclo de reparo (SÓ TEXTO — nenhum reparo foi feito)**:
   um ciclo futuro do PROFESSOR em Monaco_v2 deveria mirar o
   **re-entry/pacing pós-excursão** (a cascata de ≤10 s), não a
   geometria das curvas: ex. perfil de re-entrada com teto de curvatura
   progressivo na faixa de retorno (a banda s das "retas" de churn) —
   requer prereg próprio e autorização do dono. A Meta A (professor
   5/5×2 voltas) segue válida: o professor COMPLETA voltas; o custo é
   o tempo-fora, não a sobrevivência.

## 6. Disposição
- **PARE IMEDIATO pela FALSIDICAÇÃO-Q4** (prereg §6): o resto do quadro
  interpretativo do ciclo ("herdado × degradado") não se sustenta; escala
  ao orquestrador SEM coleta adicional (re-smoke contingente poupado).
- A×B segue ABERTA e CONGELADA com o dono. Pools 70-79 e 76-79 VIRGENS
  (seeds de eval = corpus 0-4 fora do pool; consumo = 12 sims solo).
- Suíte: ver fechamento (esperada 25F/332P/3S ±).

> **DISCLOSE-254 (FONTE-1 P0, 1 linha)**: o "254,5 s/ep" do §2-V3 é
> 1272,4 s de tempo-cascata acumulado nas **5 eps da bateria** ÷ 5
> (tabela_anatomia.csv); os 3 eps do B' original são BIT-IDÊNTICOS aos da
> bateria (ep1/ep2/ep3 conferidos), logo a "média dos 3 eps do B'"
> daria o MESMO 254,5 — o "270 s/ep" não reconcilia com nenhum artefato
> (NIT aberto, não-gating).
