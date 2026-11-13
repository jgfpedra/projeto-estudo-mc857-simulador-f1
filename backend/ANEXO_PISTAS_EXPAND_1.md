# ANEXO_PISTAS_EXPAND_1 — Biblioteca de mirrors reais via OpenF1 (aquisição; 0 sims)

Ciclo de AQUISIÇÃO na `feat/sanidade-produto` (2026-10-23). Cadeia de documentos:
PREREG_PISTAS_EXPAND_1 (8afec70) → PATCH_PISTAS_EXPAND_1_A (51da2d8) → pipeline
script (6395354) → T0 dados (d5bb170) → pins (48a16f2) → fixação-3 (3eac9be) →
aquisição dados (81866bd) → testes (96947fa) → ANEXO + fechamento (este).

**Resumo executivo**: 17/25 chamadas OpenF1; 9 pistas processadas SERIAIS;
resultado HONESTO do gate Δ<1% pinado: **7/9 FAILED** (deltas −1,36% a
−2,11%, todos no sentido CURTO — mecanismo: o v4 mede a LINHA DE CORRIDA);
**1 mirror congelado** (LasVegas_v2, −0,998%, veio do esticamento); **1
comparativo entregue** (Suzuka: candidato −0,78% vs v1 −4,69%; a razão
entre as magnitudes dos erros de comprimento é 6,0× — 272,2 m ÷ 45,4 m;
v1 intacto). ZERO sims; pool `--tracks` intocado;
canônicos/v1s bit-idênticos; suíte 20F/349P/3S com ZERO FAIL novo.

---

## 1. Tabela de chaves case-exatas (anti-H-1 — FIXAÇÃO 4; T0 commit d5bb170)

O loader é CASE-EXATO (track_resolution.py:212-216: alias minúsculo SÓ para
interlagos; senão key VERBATIM; prioridade `{key}_v2.json` > `{key}_v1.json`).

| arquivo (tracks_frozen/) | chave `load_track_frozen(<chave>)` | sha embutido | wp | L (m) | resolução |
|---|---|---|---|---|---|
| interlagos_v1.json | `interlagos` | e1857ffda5fe617f | 1131 | 4160,4 | interlagos_v2.json |
| interlagos_v2.json | `interlagos` | 164876196eb12174 | 1131 | 4160,4 | interlagos_v2.json |
| interlagos_sf729_v2.json | `interlagos_sf729` | e836910429769c27 | 1131 | 4160,4 | interlagos_sf729_v2.json |
| Monaco_v2.json | `Monaco` | 67ca11dc211c8c78 | 834 | 3335,2 | Monaco_v2.json |
| Spa_v2.json | `Spa` | 4b05f2c3bbc625fc | 1751 | 7003,2 | Spa_v2.json |
| Monza_v1.json | `Monza` | 6ed5fac92bc2fb17 | 1477 | 5641,9 | Monza_v1.json |
| Suzuka_v1.json | `Suzuka` | 4323ecb67e12d18e | 1485 | 5534,8 | Suzuka_v1.json |
| Hungaroring_v1.json | `Hungaroring` | 24c7cd7f33653781 | 1138 | 4177,7 | Hungaroring_v1.json |
| Zandvoort_v1.json | `Zandvoort` | 0fb026c95f674eab | 1099 | 4053,2 | Zandvoort_v1.json |
| **LasVegas_v2.json (NOVO)** | `LasVegas` | c30a8fe636b725cd | 614 | 6139,1 | LasVegas_v2.json |

- T0: 9/9 arquivos pré-existentes ÍNTEGROS (sha embutido == recalculado).
- RECLASSIFICAÇÃO ratificada (PATCH_A FIX 1): Hungaroring/Zandvoort eram
  "(c)" no prereg; o disco tem v1s → **(b)** (comparativo, sem congelar).
- Oficiais §1: **9/9 CONFIRMADOS** pelo f1db (`race.course_length` 2024) —
  §7 satisfeito SEM re-pin.

## 2. Descoberta + pins (§2.1; commit dedicado 48a16f2)

2 chamadas (`/sessions?year=2024|2023&session_name=Race`). Session_keys 2024
pinados com verificação por location contra o cache de descoberta (EUA
discriminados: Miami ≠ Austin ≠ Las Vegas):

| pista | session_key | location OpenF1 | P1 f1db (RACE_RESULT) |
|---|---|---|---|
| Hungaroring | 9566 | Budapest | #81 PIA |
| Silverstone | 9558 | Silverstone | #44 HAM |
| Montreal | 9531 | Montréal | #1 VER |
| Bahrain | 9472 | Sakhir | #1 VER |
| Mexico | 9625 | Mexico City | #55 SAI |
| Zandvoort | 9582 | Zandvoort | #4 NOR |
| Suzuka | 9496 | Suzuka | #1 VER |
| LasVegas | 9644 | Las Vegas | #63 RUS |
| Miami | 9507 | Miami | #4 NOR |

## 3. Aquisição por pista (§2; manifest = verdade do ciclo)

| pista | classe | driver usado | n_amostras | wp | L (m) | oficial (m) | Δ | status |
|---|---|---|---|---|---|---|---|---|
| Hungaroring | (b) | P1 #81 PIA (0 saltos) | 35724 | 432 | 4320,8 | 4381,0 | −1,37% | FAILED |
| Silverstone | (c) | P1 #44 HAM (0 saltos) | 33899 | 581 | 5810,8 | 5891,0 | −1,36% | FAILED |
| Montreal | (c) | P1 #1 VER (0 saltos) | 25940 | 430 | 4295,9 | 4361,0 | −1,49% | FAILED |
| Bahrain | (c) | P2 #11 PER (P1 salto 784 m → avanço §2.2) | 35994 | 530 | 5298,0 | 5412,0 | −2,11% | FAILED |
| Mexico | (c) | P1 #55 SAI (0 saltos) | 36741 | 423 | 4236,4 | 4304,0 | −1,57% | FAILED |
| Zandvoort | (b) | P1 #4 NOR (top-3 com 1 salto → fallback documentado) | 34781 | 417 | 4171,3 | 4259,0 | −2,06% | FAILED |
| Suzuka | (b) | P1 #1 VER (top-3 com 1 salto → fallback documentado) | 41801 | 576 | 5761,6 | 5807,0 | −0,78% | **COMPARADO** |
| LasVegas | (c) str | P1 #63 RUS (0 saltos) | 33175 | 614 | 6139,1 | 6201,0 | −0,998% | **OK CONGELADO** |
| Miami | (c) str | P2 #1 VER (P1 salto 320 m → avanço §2.2) | 34375 | 533 | 5330,5 | 5412,0 | −1,51% | FAILED |

Vocabulário do PATCH_A: `AGUARDA_DONO` (Silverstone) e `NAO_EXECUTADO`
(stretch sem teto) ficaram **não-usados** nesta rodada — Silverstone
reprovou nos gates (FAILED honesto) antes de atingir o estágio de
candidato, e o esticamento EXECUTOU (teto 15/25 no momento do gate de
stretch). Ironia reportada fielmente: os 3 alvos de congelamento da
primária (Montreal/Bahrain/Mexico) falharam o gate; o esticamento LasVegas
passou (no limite, −0,998%).

## 4. ACHADO MECÂNICO — o gate Δ<1% e a LINHA DE CORRIDA

- TODOS os 9 deltas são NEGATIVOS (contorno mais CURTO que o oficial), na
  faixa −0,78% a −2,11%. Zero saltos na maioria dos P1s e bbox plausível
  (unidade ÷10 confirmada) excluem erro de unidade/janela.
- Mecanismo: o v4 extrai a **linha de corrida** (o carro corta curvas), e
  a re-amostra em 10 m mede cordas (< arco). A prova do FONTE-2 (Monza
  −0,64%) é a pista mais indulgente do calendário (11 curvas, majoritária-
  mente retas + chicanes); pistas sinuosas (Bahrain/Zandvoort −2,1%) e de
  rua (Miami −1,5%) encurtam mais; Vegas (retão de 2 km) ficou no limite.
- Contexto do acervo: o mirror canônico **interlagos** também não passaria
  no gate (4160,4 m vs 4.309 oficiais = **−3,45%**); Monaco_v2 (−0,05%) e
  Spa_v2 (−0,01%) passam. Ou seja: o gate Δ<1% é mais estrito do que a
  própria biblioteca canônica satisfaz em 1 de 3 espelhos.
- Sem re-pin pós-número (regra da casa): o veredito é o pinado — 7 FAILED
  honestos. **DECISÃO DO DONO**: aceitar o resultado negativo × abrir novo
  ciclo com gate RE-DERIVADO mecanicamente ANTES de qualquer run (ex.:
  teto por classe de pista; mediana multi-driver; ou comparação contra a
  mediana de voltas da própria telemetria em vez do comprimento oficial).

## 5. Comparativo v1 × candidato OpenF1 (§3 — pistas (b))

| pista | v1 L (m) | v1 Δ vs oficial | OpenF1 L (m) | OpenF1 Δ | OpenF1 vs v1 |
|---|---|---|---|---|---|
| Suzuka | 5534,8 | −4,69% | 5761,6 | −0,78% | **erro de comprimento 6,0× menor em magnitude** (272,2 m ÷ 45,4 m; candidato GRAVADO: `candidatos/Suzuka_candidato_openf1.json`, sha 72807c529604ee6c, 576 wp vs 1485; v1 INTACTO) |
| Hungaroring | 4177,7 | −4,64% | 4320,8 | −1,37% | 3,4× mais próximo (candidato NÃO gravado — gate reprovou antes do artefato; ordem pinada §2.5; números do manifest) |
| Zandvoort | 4053,2 | −4,83% | 4171,3 | −2,06% | 2,3× mais próximo (idem) |

Decisão de substituição (congelar `{key}_v2.json`, o que faz o loader
preferir v2) = **dono**. Os v1s estão intactos (golden 5/5).

## 6. Identidade (§3; track_identity; fonte=openf1)

```
LasVegas (mirror congelado): {'requested': 'LasVegas',
  'efetiva': 'LasVegas (mirror OpenF1 2024)', 'fonte': 'openf1',
  'sha256': 'd18de1bef98e20d1', 'n_wp': 614, 'length_m': 6139.1}
  (sha de ARQUIVO embutido: c30a8fe636b725cd; delta vs 6201,0 m: −0,9982%)
Suzuka (candidato, fora do frozen): 576 wp, 5761,6 m (−0,78%),
  sha de arquivo embutido: 72807c529604ee6c (track_identity sobre o
  Track carregado do candidato daria a mesma geometria; fonte=openf1)
```

## 7. Golden (§4): PASS TOTAL

- Canônicos bit-idênticos NÃO tocados: interlagos/Monaco/Spa 3/3.
- v1s intactos 5/5 (Monza/Suzuka/Hungaroring/Zandvoort/interlagos).
- Anti-substitução 5/5: NENHUM `_v2.json` no path frozen para
  Suzuka/Hungaroring/Zandvoort/Monza/Silverstone.
- LasVegas carrega pela case-exata `LasVegas`; wp/L == manifest; fonte
  openf1; |ΔL| < 1% (re-confirmação independente no t_pe1_identidade).
- Manifest × arquivos: shas recalculados == embutidos == manifest (2/2).
- Orçamento: 17/25 PASS.

## 8. Orçamento de rede (§6)

**17/25 chamadas**, todas logadas APPEND em
`experiments/pistas-expand-1/probe_log.csv` (2 descoberta + 15 location:
12 na primária — incl. avanço de driver Bahrain e fallbacks Zandvoort/Suzuka
— + 1 LasVegas + 2 Miami no esticamento). Cache local
`backend/cache/openf1_pistas_expand_1/` evitou 2º download (re-execuções
e o golden consumiram ZERO chamadas). Respostas cruas FORA do git
(FIXAÇÃO 2); caches fastf1 intocados.

## 9. Suíte (§8) — comparação itemizada serial × serial

- Baseline (pré-mudanças, worktree = 1a228b8): **20F/345P/3S** (175,53 s).
- Final (pós mirrors+testes): **20F/349P/3S** (177,89 s).
- Δ = +4 passes = exatamente os 4 `t_pe1_*` (§5) — 4/4 verdes.
- **As 20 falhas são as MESMAS bit-a-bit** (0 novas, 0 curadas):
  `test_kappa_sign::test_local_sign_correct`, `test_no_spurious_flip`,
  `test_mixed_race::test_hold_car_stays_at_s`,
  `test_procedural_track` ×13 (TestDeterminism×2, TestGeometry×5,
  TestWidth×2, TestEnvIntegration×3, TestFeatures×2),
  `test_race_layer::test_subdivision_preserves_length_exactly`,
  `test_race_neural_60d::test_profiles_exist_default_race_obs_correct`,
  `test_rl_v2::test_reference_controller_completes_lap`,
  `test_rl_v2::test_skidpad_radius_close_to_bicycle`.
- §8 satisfeito SEM desvio: 20F/345P/3S + 4 testes novos, zero FAIL novo
  (a nota fail-loud do PATCH_A sobre deslocamento de contagem não se
  materializou — os testes são data-driven do manifest).

## 10. Disclosures (totais)

1. **cwd-flip 2× durante o ciclo** (git add do T0 a partir de backend/ →
   "backend/backend/..."; pytest isolado com `./.venv` a partir da raiz) —
   ambos corrigidos com caminhos absolutos; ZERO efeito em dados.
2. **/tmp de tasks background é EFÊMERO** (sandbox por task): o tee do
   baseline (`/tmp/pe1_baseline.txt`) e o log da task antiga foram
   reclamados — a comparação itemizada foi feita contra as listas de
   falhas capturadas NO REGISTRO DA SESSÃO quando produzidas (ambas
   verbatim na seção 9). LIÇÃO: logs de medição vão para o worktree no
   MESMO passo, nunca só em /tmp.
3. **Manifest exibe −1,0 para LasVegas** (arredondamento 2 casas); o gate
   avaliou o valor NÃO-arredondado **−0,9982%** (pass); t_pe1_identidade
   reconfirma |ΔL|<1% mecanicamente a partir da geometria carregada.
4. **1 salto ~320-784 m por stream** em Bahrain/Miami (P1 — regra de
   avanço §2.2 aplicada) e Zandvoort/Suzuka (top-3 com 1 salto cada —
   fallback documentado: menor contagem, empate = ordem de classificação;
   o v4 tolera o salto — a janela mediana descarta janelas parciais).
5. **Hungaroring/Zandvoort sem candidato gravado**: a ordem pinada do
   pipeline (§2.5 gates antes do artefato) reprovou-os antes de escrever
   JSON; os números do comparativo vêm do manifest (seção 5).
6. Stray antigo `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` (cwd-flip de
   ciclo passado, divulgado no PROF-MONACO-1) permanece — fora do escopo
   da FIXAÇÃO 3 (que tratou SÓ de backend/worklog.md → archive/, 3eac9be).
7. ZERO sims de treino/corrida (suíte de regressão serial é o único
   executor de corridas, como §6 manda); PNGs = PLOT de geometria via
   draw_track `--csv` (zona proibida SÓ chamada; rota pré-existente
   confirmada por leitura de código, não houve side-car).

## 11. Decisões do dono (fila)

1. **Gate Δ<1%**: resultado negativo 7/9 por mecanismo de racing-line.
   Aceitar × novo ciclo com gate re-derivado mecanicamente (prereg antes
   de qualquer run). Nota: TODOS os contornos OpenF1 são melhores que os
   v1s do acervo (e melhores que o interlagos canônico, −3,45%).
2. **Suzuka**: congelar `Suzuka_v2.json` (loader passaria a preferir v2)?
   Erro de comprimento do candidato com módulo 6,0× menor (272,2 m ÷
   45,4 m); v1 intacto; 1 linha de aprovação.
3. **LasVegas_v2** congelada está pronta (`load_track_frozen('LasVegas')`);
   adoção no pool `--tracks` = ciclo próprio.
4. Silverstone/Montreal/Bahrain/Mexico/Miami/Hungaroring/Zandvoort:
   reprocessar sob novo gate (os streams estão EM CACHE — zero novas
   chamadas de rede para re-derivar) = decisão de ciclo futuro.
