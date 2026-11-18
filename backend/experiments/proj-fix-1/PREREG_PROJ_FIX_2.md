# PREREG — PROJ-FIX-2: identidade NIT-2 e decomposição C1/C2/C3 (Monaco)

**Status:** congelado antes do classify. Retomada do PROJ-FIX-1, interrompido por PARE após o seletor v1.0 usar `composite_monaco_s0` e encontrar zero linhas. A fonte NIT-2 identifica o braço como `composite_monaco`; replay v3.4 já existente permanece validado e será reutilizado. Nenhuma nova corrida, nenhuma correção ou promoção.

## 1. Objetivo, orçamento e limites

Decompor offline as entradas históricas de salto do FF1b R4 Composite Monaco, mapeando 1:1 as classes C1/C2/C3 por `(drv,tick_prev,tick)`. A decisão entre RECUP-1 para C1/C2 e correção de projeção/gate para C3 volta ao dono após o relatório. Monaco mantém cautela sobre a superfície dirigível antes de qualquer exigência de bordas.

- Zero corridas de medição novas e zero smokes; apenas leitura dos CSVs congelados.
- Pools, pistas frozen, runner, testes, controle e física intocados.
- Suíte pós-código: referência existente 20F/352P/3S; não reexecutar nesta etapa. Qualquer nova falha reportada é PARE.
- Script `proj_fix_1_classify.py` v1.0 permanece imutável, SHA-256 `a8d6b3202c80aa84e7b2af7a522801bf33ff6896e310873400b2d55608d6a73f`.

## 2. Fase 0 — identidade da fonte NIT-2 já confirmada

Fonte `experiments/fail-forensics-2/veredito/saltos_projecao.csv`, SHA-256 `b9bcb14d9bb38dceabcbfddc9f90cb3b5bd2cc25fa6719a90ded52eb2b9bb739`. Evidência versionada em `experiments/proj-fix-1/5_identidade_run_nit2.log`.

| Run | Linhas |
|---|---:|
| `aluno_monaco_s0` … `aluno_monaco_s4` | 9 cada |
| `blind_monaco` | 9 |
| `composite_interlagos` | 3 |
| `composite_monaco` | 112 |
| `professor_monaco_s0` … `professor_monaco_s4` | 21 cada |

Para `composite_monaco`: 112/112 linhas têm erro de projeção ≥10 m; 45/112 têm ≥30 m; carros `ALO,GAS,HAM,LEC,NOR,PER,PIA,RUS,SAI,VER`; ticks em `[0,6000)` (observado min 76, max 5910); `track=monaco`. Esse rótulo é a identidade de FF1b R4 `experiments/fail-forensics-2/4_composite_monaco_s0.csv`, SHA-256 `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022`: é o único braço Composite Monaco; a tabela usa sufixo de seed nos braços professor/aluno. O fechamento 112/45 coincide com o headline R4.

## 3. Fase 1 — congelamento do classificador e da análise

1. O prereg e os artefatos abaixo serão commitados antes de qualquer classify.
2. Criar `scripts/proj_fix_2_classify.py` v1.1 como cópia de v1.0. Diff permitido estritamente: docstring para PROJ-FIX-2/version 1.1, `VERSION = "1.1"`, `PROJECTION_RUN = "composite_monaco"`. Nenhuma outra linha muda.
3. Rodar o selftest sintético da v1.1 e registrar hashes do prereg, script e log do selftest em `6_freeze_manifest.log`; congelar por commit antes de abrir qualquer número de decomposição.

O selftest v1.1 usa os mesmos casos sintéticos C1/C2/C3/C4, chaves 1:1 e p95 do v1.0. SHA-256 do script v1.1: `9d73a890964974b3f04d2261fe0806a21ec6b162b111aa89c28c7919c3704d8d`; SHA-256 de `6_classifier_selftest_v11.log`: `f9f6a84ed8538b1ded286aa0ba65afef17bef166c9c5e73e75285de893b5f521` (PASS). SHA-256 de `5_identidade_run_nit2.log`: `23f499357abb80d30c4ee17db3bed12e289e059dc5bea4057503c2ebc0e4c179`.

### Regra congelada de classes

Para cada par de amostras consecutivas do mesmo carro, em ordem de tick, `dXY = hypot(body_x_t-body_x_prev, body_y_t-body_y_prev)` e `d_ns = abs(ns_raw_t-ns_raw_prev)`. Classificar estritamente na prioridade:

1. **C1 — descontinuidade composta:** `dXY >= 30 m` e `d_ns >= 8`.
2. **C2 — divergência física local:** `dXY >= 30 m` e `d_ns < 8`.
3. **C3 — reapontamento na vizinhança:** `dXY < 30 m` e `d_ns >= 8`.
4. **C4-diagnóstico:** linha inválida, contada à parte; pares que a usam não recebem C1/C2/C3.

Relatar contagens C1–C4 e p95 linear de dXY e d_ns por classe nos cortes NIT-2 ≥10 m e headline ≥30 m, usando somente o mapa 1:1 validado. Reportar também os pares classificados gerais. O método do p95 é o mesmo da função congelada `_linear_percentile` do classificador.

## 4. Fase 2 — execução somente offline sobre artefatos existentes

### g0 — hashes, antes de ler CSVs

Conferir `sha256sum`; qualquer divergência é PARE.

| Artefato | SHA-256 esperado |
|---|---|
| Replay v3.4 `1_replay_composite_monaco_s0_v34.csv` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| Replay `_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| Log do replay | `d88f14030e729716a730228fdca5e4dc8ac99d6dddeeab320a16e593496eb0a1` |
| Âncora FF1b R4 `4_composite_monaco_s0.csv` | `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022` |
| `saltos_projecao.csv` | `b9bcb14d9bb38dceabcbfddc9f90cb3b5bd2cc25fa6719a90ded52eb2b9bb739` |

### g1/g2 — replay já existente

Executar apenas `proj_fix_2_classify.py --gate` sobre o replay existente, sem rerun. g1 deve reproduzir o hash comum `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`; g2 deve confirmar 71 campos/linha, X/Y finitos e `ns_raw` em `[0,833]`.

### g3 — seleção NIT-2

Selecionar `run=composite_monaco`; confirmar 112 linhas ≥10 m, 45 ≥30 m e os metadados da Fase 0. Divergência = PARE.

### g4 — classify v1.1

Usar o script frozen com `--historical-jumps experiments/fail-forensics-2/veredito/saltos_projecao.csv --outdir experiments/proj-fix-1/classificacao_v11`. Ele deve produzir `pares_classificados.csv`, `mapa_nit2_ge10.csv`, `resumo_classes.json` e um mapeamento único de todos os 112 eventos. Qualquer evento sem classe, chave duplicada/ausente ou contagem que não feche nos cortes é PARE. Produzir o resumo p95 por classe/corte a partir do mapa v1.1 com o método linear congelado acima; registrar log e hashes sem alterar o classificador.

## 5. Fase 3 — relatório e decisão

Reportar contagens e p95 por classe nos dois cortes (headline ≥30 m e NIT-2 ≥10 m), mais o mapa classe-por-evento 1:1. Atualizar `PROJECT_STATE.md`, `AUDITORIA_RL.md` e `worklog.md`, preservando o histórico PARE do PROJ-FIX-1 e incluindo ponteiros `Ver <path>` fechados por `)`. Nenhuma correção é proposta: RECUP-1 (C1/C2) versus projeção/gate (C3) é decisão do dono para a próxima etapa.

## 6. PARE obrigatório

Qualquer hash g0 ou gate g1/g2 divergente; g3 diferente de 112/45; evento NIT-2 sem C1/C2/C3; chave `(drv,tick_prev,tick)` duplicada ou ausente; contagens não fecharem; qualquer linha inválida além do C4-diagnóstico; ou edição do script/prereg após revelar números. Em PARE, não rerodar simulação, não re-pin e não editar o instrumento congelado.
