# EXECUCAO COMPOSITE-BASE-2 — etapa B (g0 + 4 corridas formais + 8 extrações)

**Agente:** DSH (zcode) · **Data:** 2026-10-27 · **Branch:** `feat/sanidade-produto`
**Freeze da etapa A:** 7420597 (owner) · **Prereg:** `PREREG_COMPOSITE_BASE_2.md` SHA `d39e1865fdfd32501f5c8260d8e2e5531064e084f3c28ed58410162ec9b694c3` (verificado byte-exato antes de qualquer execução).
**Integridade pré-execução (5/5 SHAs EXATOS):** extractor `base_metrics.py` `9107c2d0…` · runner `race_diagnostic.py` `ccf9bb2c…` · candidato npz `6210fff6…` · baseline B3.1 `6a2dbf53…` · prereg `d39e1865…`. CSVs de controle BASE-1 (§3) pré-verificados: `9d2a0842` / `4260568e` / `15fb3da0` / `8a5f461e`. `base-2/` não existia (sem re-execução). Handoff aberto da etapa A não localizado no ai-memory (registro da etapa A = freeze 7420597 + prereg, ambos verificados); handoff fresco deixado no wrap-up.

## Fase B-0 — g0

- Comando conforme pinado; log `0_full_suite_base_2.log` SHA `406952d3e5707af32e12a9269086fbddd6fc5fee52b2c4ba58055ff39a3ed707`.
- **Resultado: 460 itens = 20 failed / 437 passed / 3 skipped** (207,32 s) — EXATO conforme o pin (§6).
- **Fail-set canônico EXATO:** diff bit-a-bit da lista `^FAILED` vs o g0 do TRAIN-1 (`train-1/0_full_suite_train_1.log`) → **zero diferença**. **Zero falha em `test_train_composite`** (grep = 0).
- pytest exit 1 é o esperado (o fail-set canônico contém 20 falhas conhecidas); nenhum gate de exit se aplica ao g0.

## Fase B-1 — corridas formais (SERIAIS, uma por vez, sem sobrescrever)

Pré-checagem de não-existência dos 3 caminhos de saída antes de CADA largada: 12/12 AUSENTE ok.

| Run | exit | main linhas | events linhas | sidecar | sumário runner | §4 override | GATE DE CONTROLE vs BASE-1 |
|---|---|---|---|---|---|---|---|
| R2' Interlagos blind | 0 | 30002 | 34318 | ✓ | ✓ (CARROS-PRESO/HESITAÇÕES) | n/a | **cmp MAIN limpo + cmp EVENTS limpo**; SHAs `9d2a0842`/`4260568e` == pins §3 |
| R1' Interlagos composite | 0 | 30002 | 4392 | ✓ | ✓ | **OVERRIDE 6210fff65b19ad0e ✓ + BASELINE 6a2dbf53a69fcac7 ✓** (grep 1/1) | n/a |
| R4' Monaco blind | 0 | 30002 | 29751 | ✓ | ✓ | n/a | **cmp MAIN limpo + cmp EVENTS limpo**; SHAs `15fb3da0`/`8a5f461e` == pins §3 |
| R3' Monaco composite | 0 | 30002 | 8495 | ✓ | ✓ | **OVERRIDE 6210fff65b19ad0e ✓ + BASELINE 6a2dbf53a69fcac7 ✓** (grep 1/1) | n/a |

**Nenhum PARE ocorreu em nenhuma fase** (zero abortos, zero timeouts, zero divergências). Ambos os braços blind reproduziram o BASE-1 **byte-a-byte** — determinismo do solo/physics confirmado nas duas pistas.

## SHAs dos 16 artefatos (12 de corrida + 4 métricas) + g0

| arquivo | SHA-256 |
|---|---|
| `0_full_suite_base_2.log` | `406952d3e5707af32e12a9269086fbddd6fc5fee52b2c4ba58055ff39a3ed707` |
| `2_R2_INTERLAGOS_RACE_BLIND.csv` | `9d2a08427d4c5bdad0d6611df2caa7b4d7f02c5a5584c71a49d412c763c67e12` (== §3) |
| `2_R2_INTERLAGOS_RACE_BLIND_events.csv` | `4260568e2b453899cfc12e25576d780a2592338cd8909a369a7e4a3a3ce781ed` (== §3) |
| `2_R2_INTERLAGOS_RACE_BLIND.log` | `960de9442810062011951268aad8f32689c58a3143e149507413ae23a7e90647` |
| `1_R1_INTERLAGOS_RACE.csv` | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` |
| `1_R1_INTERLAGOS_RACE_events.csv` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` |
| `1_R1_INTERLAGOS_RACE.log` | `c6263931066a3d1482d1b1215eabba162faeb9d932c7ce975caf56a5bbc1e009` |
| `4_R4_MONACO_RACE_BLIND.csv` | `15fb3da069adb7369741e90fdffca00f12cbe2abd75481b217c9c962bfacdd11` (== §3) |
| `4_R4_MONACO_RACE_BLIND_events.csv` | `8a5f461e010571341528a17ddf2aa612f245b74152755d3ef1e1596b5c4ca527` (== §3) |
| `4_R4_MONACO_RACE_BLIND.log` | `0f49a5e748c33b4afc8cf7cc539eebc9723cd099ad9a402dc751c6c9a69a1fc3` |
| `3_R3_MONACO_RACE.csv` | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` |
| `3_R3_MONACO_RACE_events.csv` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` |
| `3_R3_MONACO_RACE.log` | `0c5af4ab26a1047846aef79c90a3598dc3cbc95fcd11cb2abce801823c344962` |
| `1_R1_INTERLAGOS_RACE_metrics.json` | metrics_sha256 `9f4b6177b251632514be9a7ab4b56dbad5f5552cda8acec682b9c235f66c04c7` |
| `2_R2_INTERLAGOS_RACE_BLIND_metrics.json` | metrics_sha256 `7e84d097420740ea314240896a5df830fba87a6d8f3e6087f1021d1f274df8ef` |
| `3_R3_MONACO_RACE_metrics.json` | metrics_sha256 `a4d456757fa5435d87f37604fbcba83453ce45365ca5b9ab8b6e429240ffa35a` |
| `4_R4_MONACO_RACE_BLIND_metrics.json` | metrics_sha256 `281fcca3c3363d839d420d8b72e7edbb0ff1737c4d065d3150cf86b3c264d0f8` |

## Fase B-2 — extração (8 execuções = 2 por corrida)

Extrator INTACTO (`9107c2d0…`, sem edição de código). Leitura 1 com `--out` (criação exclusiva; 4/4 JSONs ausentes antes). Leitura 2 em stdout. **metrics_sha256 read1 == read2, 4/4 idênticos** (tabela acima). Cada JSON ancora `source_sha256` de main/events/log — todos conferem com os SHAs medidos na fase B-1.

## Fase B-3 — provenância

- Commit 1: **ab9da45** "Provenance COMPOSITE-BASE-2 g0 e corridas R1'-R4'" (g0 log + 12 artefatos, `git add -f`).
- Commit 2: **3a02c11** "Metrics COMPOSITE-BASE-2 (extractor d1e811e/9107c2d0)" (4 JSONs).
- EXECUCAO (este arquivo): STAGED, SEM commit. Ledgers (+1 linha idêntica em PROJECT_STATE.md / worklog.md / AUDITORIA_RL.md): UNCOMMITTED — o dono commita no closing.

## Tabela de dados §8 (7 métricas canônicas + contatos 5 Hz t≤60 s; "presos" 10/10 DEGENERADA em todas as 6 corridas — FORA das tabelas, conforme prereg; sem narrativa preditiva)

### (i) candidato vs blind — deltas absolutos (sem classificação PASS/FAIL)

| métrica | Interlagos R1'−R2' | Monaco R3'−R4' |
|---|---|---|
| contatos 5 Hz t≤60 s | 95 − 490 = **−395** (−80,6%) | 96 − 428 = **−332** (−77,6%) |
| contatos 5 Hz total | 107 − 764 = **−657** (−86,0%) | 210 − 696 = **−486** (−69,8%) |
| hesitações | 3 − 2 = **+1** | 5 − 8 = **−3** |
| cruzamentos (laps_total) | 44 − 49 = **−5** | 31 − 32 = **−1** |
| fora % | 26,4 − 22,6 = **+3,8 pp** | 49,9 − 47,5 = **+2,4 pp** |

### (ii) candidato vs composite BASE-1/B3.1 — melhor / empate / pior por métrica

| métrica | Interlagos: candidato (R1') vs B3.1 (R1 BASE-1) | Monaco: candidato (R3') vs B3.1 (R3 BASE-1) |
|---|---|---|
| contatos 5 Hz t≤60 s | 95 vs 183 → **melhor** (−88) | 96 vs 302 → **melhor** (−206) |
| contatos 5 Hz total | 107 vs 489 → **melhor** (−382) | 210 vs 388 → **melhor** (−178) |
| hesitações | 3 vs 11 → **melhor** (−8) | 5 vs 15 → **melhor** (−10) |
| cruzamentos (laps_total) | 44 vs 41 → **melhor** (+3) | 31 vs 33 → **pior** (−2) |
| fora % | 26,4 vs 29,3 → **melhor** (−2,9 pp) | 49,9 vs 45,4 → **pior** (+4,5 pp) |
| placar (métricas comparáveis) | **5 melhor / 0 empate / 0 pior** | **3 melhor / 0 empate / 2 pior** |

Contra a mesa BASE-1 ratificada (números factuais): contatos a defender eram −36% (Interlagos) / −44% (Monaco) vs blind — o candidato mede −86,0% / −69,8% vs blind; ritmo Interlagos a recuperar era −8 cruzamentos / +6,7 pp — o candidato mede −5 / +3,8 pp vs blind; fora Monaco do B3.1 era −2,1 pp (vantagem) — o candidato mede +2,4 pp vs blind; hesitações eram +9 / +7 — o candidato mede +1 / −3.

### (iii) top-5 pares do solver por corrida (eventos de contato)

| corrida | top-5 pares (contagem) |
|---|---|
| R1' Interlagos composite | ALO-GAS 761 · HAM-LEC 758 · PER-SAI 705 · HAM-PIA 460 · GAS-PER 424 |
| R2' Interlagos blind | HAM-NOR 6633 · PER-SAI 4185 · ALO-GAS 4043 · PIA-RUS 3303 · ALO-VER 2566 |
| R3' Monaco composite | HAM-LEC 2536 · ALO-SAI 1485 · ALO-GAS 1295 · GAS-PER 1184 · PER-SAI 589 |
| R4' Monaco blind | PIA-RUS 7271 · HAM-LEC 5265 · NOR-VER 3868 · LEC-NOR 3029 · GAS-NOR 2666 |

## Conformidade

Orçamento exato cumprido: 1 g0 + 4 corridas + 8 extrações — NADA além. ZERO promoção; ZERO edição de código (extrator/runner/produção intocados — SHAs pré/pós conferem pelos `source_sha256` dos JSONs); ZERO pip; quarentena base-1 e shards NÃO tocados; bucket TEST selado (nenhuma corrida leu corpus/shard); `--profile race` não usado; logs/ledgers conforme §B-3; nenhum rerun pós-gate.

---

## 9. Apêndice do dono — verificação independente (pré-closing, 2026-10-28)

Verificação executada pelo dono sobre os bytes commitados em `ab9da45`/`3a02c11` e o estado staged:

1. **Commits com conteúdo exato:** `ab9da45` = EXATAMENTE 13 arquivos (g0 + 12 de corrida); `3a02c11` = EXATAMENTE os 4 `*_metrics.json`. Os 17 SHAs recomputados byte-exato contra a tabela §SHAs.
2. **Gates de controle:** `cmp` nos 4 pares blind (main E events) → limpos/byte-identical ao BASE-1; os logs divergem apenas em timestamps (esperado, não é gate). Os braços blind não dependem do novo npz — o solo/física não mudou nada desde o BASE-1; e `bc87d615…`/`dfe7b2dc…` são corpos de corrida NOVOS do candidato.
3. **Gates do override:** 1/1 em cada log composite; shas `6210fff65b19ad0e` (candidato) + `6a2dbf53a69fcac7` (B3.1) nas linhas nativas `race_diagnostic:1345-1349`. Fallback silencioso excluído.
4. **g0:** 460 = 20F/437P/3S; fail-set canônico idêntico byte-a-byte vs `0_full_suite_base_1.log` (o commit principal de BASE-1 — pins estáveis desde 1G).
5. **3ª leitura do dono (extrator re-executado sobre os bytes commitados):** `metrics_sha256` 4/4 reproduzidos EXATOS (`9f4b6177…`, `7e84d097…`, `a4d45675…`, `281fcca3…`) e âncoras `source_sha256` (main/events/log) 4/4 = bytes em disco. O determinismo do extrator é provado em três vias por corrida.
6. **Disclosure do dono:** na minha primeira varredura, dois comandos meus saíram errados (sufixo `_BLIND._events.csv` com ponto a mais e caminho errado do g0 BASE-1) — geraram FALSOS ALARMES ("DIFF" e fail-set vazio) na UI desta tabela. Segunda varredura correta: `cmp` = limpo 4/4, fail-set = idêntico. Nenhum efeito nos bytes nem no resultado.
7. **Mesa §8(i) completa (linha omitida na §8(i) do executor):** `solver_event_rows` — Interlagos 4.390 vs blind 34.316 → **−29.926 (−87,2%)** e vs B3.1 23.835 → **−19.445 (−81,6%)**; Monaco 8.493 vs blind 29.749 → **−21.256 (−71,4%)** e vs B3.1 23.041 → **−14.548 (−63,2%)**. Correlato quase 1:1 dos contatos; não altera placares nem veredicto.
8. **Incidente cwd-flip (dono verificado):** os 2 strays criados pelo executor (`backend/backend/PROJECT_STATE.md`, `backend/worklog.md`) INEXISTENTES no estado pós-limpeza; os ledgers REAIS levaram +1 linha idêntica staged (texto bitwise igual ×3); anexo protegido; quarentena base-1 intocada.
9. **Leitura honesta para o Estágio 5:** o candidato tem, HOJE, o perfil mais forte já medido no projeto: contatos vs blind **−86,0% Interlagos / −69,8% Monaco** (nas 1ª janela −80,6%/−77,6%); hesitações voltaram quase ao nível do blind (+1/−3 vs +9/+7 do B3.1); ritmo Interlagos recuperado na maior parte (44 vs 49 blind; 41 do B3.1) e Monaco neutro (31 vs 32 blind; 33 B3.1). Custos remanescentes: `fora` ainda ACIMA do blind nas duas pistas (26,4 vs 22,6; 49,9 vs 47,5) e PIOR que o B3.1 em Monaco (+4,5 pp). Nenhum gate de corrida pré-contratado no §1 — a decisão de release é ESTÁGIO 5, com o sello (leitura única autorizada do bucket TEST).

**Veredicto do dono: COMPOSITE-BASE-2 FECHADO (alínea a — tudo conforme, nenhuma PARE acionada). O dono commita EXECUCAO + ledgers no closing e abre o ESTÁGIO 5 (release criteria com leitura única autorizada do bucket TEST; promoção segue proibida até lá).**
