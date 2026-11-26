# EXECUÇÃO REALISMO-1 · C0 — matriz OFF N=1..4 e ruído

**Data:** 2026-10-29 (America/Sao_Paulo)

**Prereg congelado:** `backend/experiments/realismo-1/c0/PREREG_REALISMO_C0.md`, freeze do dono `240bacde17b0301da6d5f0db30d52fb5cad03397`.

**Código/instrumento frozen:** `realismo_metrics.py` `e5a7ecb42fd9bfd3297935d974a53174b51eb822a877b33e4ed4a208a590ac7b`; `base_metrics.py` `9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728`; `race_diagnostic.py` `ccf9bb2c247e7bf30257cdc81e120ecc742f4d4f1129a3d11eb3445b8dfdf14e`.

## 1. Veredito operacional

- A primeira tentativa do g0 foi um PARE de infraestrutura: cwd incorreto, falha antes de iniciar pytest, sem saída criada. O dono autorizou uma única nova tentativa por emenda explícita no chat.
- A nova tentativa do g0 foi executada com cwd `backend/`; terminou com **20 failed / 458 passed / 3 skipped**, 210,76 s, e o conjunto de linhas `^FAILED` foi byte-idêntico ao g0 canônico da promocao-1. SHA do log: `eadd9db4849ce2d3ad693a3f2b5955e8966ccc5dceab0cd3bdb742863d0ffc93`.
- As 8 corridas OFF N=1..4 foram executadas uma por vez, sem rerun. Todas produziram 30.002 linhas no CSV principal, sidecar de eventos e logs completos com identidade da pista, variedade, residual e sumários do runner.
- As 32 leituras de extração foram executadas: 2 leituras de `base_metrics` e 2 leituras de `realismo_metrics` por corrida. Cada par passou `cmp`; o `canonical.metrics_sha256` do instrumento novo bateu com o JSON do `base_metrics` correspondente.
- Os 2 relatórios de ruído foram lidos duas vezes e passaram `cmp`.
- Nenhum código de produção, modelo, pista ou arquivo v1/v2 foi editado. Não houve seed diferente de 0, `--variedade` >= 5, leitura de shard TEST, treino ou promoção.

**Nota de instrumentação:** `control_bash_process` não expõe o código de saída individual do shell. O processo de cada corrida terminou com saída completa do runner, 30.000 amostras, sidecar e sem traceback/timeout; o código de saída numérico não foi capturado separadamente. Isso fica divulgado para o closing do dono, em vez de ser inferido silenciosamente como `exit 0`.

## 2. Matriz OFF e métricas

N=0 é o golden commitado da promocao-1. N=1..4 são as novas corridas desta etapa. Contato mantém a definição única do plano: linha 5 Hz com `car_car > 0`. `glue/deadlock` usa a métrica D3 corrigida; em Monaco os números são novos e não são comparáveis aos números legados que usavam o comprimento de Interlagos.

### Interlagos

| N | contatos | t<=60 | laps | fora% | fora rows | FORA-PRESO | excursões | Z_RETA | T1<=60 | Junção | colado s | deadlocks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 107 | 95 | 44 | 26,4 | 7905 | 6281 | 219 | 12 | 12 | 51 | 32,6 | 0 |
| 1 | 340 | 178 | 45 | 26,3 | 7884 | 5836 | 227 | 18 | 10 | 40 | 41,2 | 1 |
| 2 | 627 | 483 | 44 | 26,6 | 7989 | 5911 | 227 | 16 | 11 | 40 | 88,0 | 3 |
| 3 | 406 | 296 | 44 | 26,2 | 7861 | 6098 | 213 | 12 | 10 | 43 | 45,4 | 1 |
| 4 | 344 | 296 | 43 | 26,4 | 7927 | 6210 | 222 | 13 | 9 | 47 | 33,8 | 1 |

### Monaco

| N | contatos | t<=60 | laps | fora% | fora rows | FORA-PRESO | excursões | Z_RETA | T1<=60 | Junção | colado s | deadlocks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 210 | 96 | 31 | 49,9 | 14963 | 11294 | 384 | 6 | 9 | n/a | **80,2** | 1 |
| 1 | 487 | 285 | 31 | 49,2 | 14769 | 11487 | 386 | 7 | 7 | n/a | 109,4 | 1 |
| 2 | 373 | 91 | 32 | 49,2 | 14764 | 11281 | 367 | 6 | 11 | n/a | 97,4 | 2 |
| 3 | 374 | 194 | 29 | 49,5 | 14849 | 11525 | 373 | 7 | 10 | n/a | 91,4 | 1 |
| 4 | 725 | 347 | 29 | 50,7 | 15201 | 11324 | 396 | 7 | 11 | n/a | 97,2 | 2 |

**Disclosure Monaco:** `80,2 s / 1 deadlock` em N=0 e os valores N=1..4 são métricas novas sob o comprimento de Monaco corrigido durante a chamada de `sanidade1b_verdict.stats`. Não há comparabilidade legítima com os números legados calculados com `L_TRACK=4160,4`.

### Hesitações e nova saída

| Pista | N=0 | N=1 | N=2 | N=3 | N=4 |
|---|---:|---:|---:|---:|---:|
| Interlagos hesitações | 3 | 3 | 3 | 5 | 4 |
| Monaco hesitações | 5 | 4 | 3 | 7 | 4 |
| Interlagos nova saída <=5 s / reentrada | 22,1% | — | — | — | — |
| Monaco nova saída <=5 s / reentrada | 42,6% | — | — | — | — |

A tabela de N=1..4 não acrescenta a métrica `new_exit_le_5s` acima porque o instrumento a registra no JSON individual; os valores N=0 permanecem o golden exigido. O disclosure da convenção estrita `<5 s` é o do prereg: 20,3% Interlagos e 42,1% Monaco.

## 3. Relatório de ruído

Relatórios:

- `9_NOISE_INTERLAGOS.json` — SHA `5db292d2009ad38a58095fe9e3e1c7651bc2ca093216bcaadfc6c847eb1b1df2`.
- `10_NOISE_MONACO.json` — SHA `19ecc6eeab29c3ac9391ce9793b4c5a793ed4d46bbbdc95ebc76470e1f6dfe08`.

Os relatórios `_read2.json` são byte-idênticos aos respectivos arquivos com `--out`.

### Média e desvio-padrão amostral sobre N=0..4

| Métrica | Interlagos média | Interlagos sd | Monaco média | Monaco sd |
|---|---:|---:|---:|---:|
| contatos totais | 364,8 | 185,711 | 433,8 | 190,386 |
| contatos t<=60 | 269,6 | 146,466 | 202,6 | 113,505 |
| laps_total | 44,0 | 0,707 | 30,4 | 1,342 |
| fora rows | 7913,2 | 48,941 | 14909,2 | 181,937 |
| excursões t<=60 | 37,2 | 4,438 | 68,4 | 4,615 |
| Z_RETA | 14,2 | 2,683 | 6,6 | 0,548 |
| T1 t<=60 | 10,4 | 1,140 | 9,6 | 1,673 |
| Junção | 44,2 | 4,764 | n/a | n/a |
| colado rows | 241,0 | 114,335 | 475,6 | 53,026 |
| deadlocks | 1,2 | 1,095 | 1,4 | 0,548 |

### Probabilidades sob a nula caótica

`pair_fail_frac` é a fração dos 20 pares ordenados OFF(N') × OFF(N), N' != N, que reprovariam. Para gates por soma/taxa, `p_fail_normal` usa a aproximação normal pinada no prereg. Gates estruturais por realização não recebem aproximação normal.

| Pista | Gate | pair fail | p_fail normal | p_pass normal |
|---|---|---:|---:|---:|
| Interlagos | B1 | 0,4500 | 0,3293 | 0,6707 |
| Interlagos | S1 | 0,4500 | 0,4994 | 0,5006 |
| Interlagos | R1 | 0,0000 | 0,0000 | 1,0000 |
| Interlagos | R2 | 0,0000 | 0,0000 | 1,0000 |
| Interlagos | C1P1 | 1,0000 | estrutural | estrutural |
| Interlagos | C1P2 | 0,5500 | 0,5201 | 0,4799 |
| Interlagos | R2T1 | 0,4500 | estrutural | estrutural |
| Interlagos | C23P | 0,5000 | 0,5018 | 0,4982 |
| Interlagos | C5P | 0,5500 | 0,5187 | 0,4813 |
| Interlagos | C6G | 0,5000 | 0,5008 | 0,4992 |
| Interlagos | C6D | 0,3500 | estrutural | estrutural |
| Monaco | B1 | 0,4500 | 0,3047 | 0,6953 |
| Monaco | S1 | 0,5000 | 0,4992 | 0,5008 |
| Monaco | R1 | 0,1000 | 0,0023 | 0,9977 |
| Monaco | R2 | 0,1500 | 0,0001 | 0,9999 |
| Monaco | C1P1 | 1,0000 | estrutural | estrutural |
| Monaco | C1P2 | 0,5500 | 0,5193 | 0,4807 |
| Monaco | R2T1 | 0,4500 | estrutural | estrutural |
| Monaco | C23P | 0,5000 | 0,5005 | 0,4995 |
| Monaco | C6G | 0,5000 | 0,5017 | 0,4983 |
| Monaco | C6D | 0,3000 | estrutural | estrutural |

C0 não emite PASS/FAIL de comportamento. Os números mostram que a realização única N=0 é inadequada como referência de desenvolvimento para gates de contagem: por exemplo, os contatos Interlagos variaram de 107 a 627 e Monaco de 210 a 725. A agregação final e a leitura desses falsos FAIL ficam para o freeze do C1, conforme o prereg.

## 4. Disclosure por realização e observações

A tabela completa OFF × N=0..4 está na §2. Em particular:

- Interlagos N=2 tem 627 contatos, 88,0 s colado e 3 deadlocks; Monaco N=4 tem 725 contatos e 50,7% fora. Esses valores não são descartados nem mascarados por soma.
- Não houve realização ON neste C0; o alerta `ON >= 3 x OFF` não se aplica.
- N=1..4 produziram CSVs distintos; os oito hashes estão nos JSONs e na tabela de hashes deste relatório. N=5..8 não foram usados e continuam selados.
- Nenhuma métrica de comportamento foi promovida, comparada contra um gate de mecanismo ou usada para escolher constantes.

## 5. Artefatos e proveniência

Todos os artefatos abaixo estão em `backend/experiments/realismo-1/c0/`; os CSVs, sidecars, logs, JSONs e o EXECUCAO são staged com `git add -f` por causa do `.gitignore` de `experiments/`.

| Grupo | Conteúdo | Estado |
|---|---|---|
| g0 | `0_full_suite_c0.log` | criado; fail-set idêntico |
| corridas | `1_OFF_...` até `8_OFF_...` (`csv`, `_events.csv`, `log`) | 8/8 completas |
| extração | 2 JSONs `base_metrics` + 2 JSONs `realismo_metrics` por corrida | 32/32 leituras determinísticas |
| ruído | `9_NOISE_INTERLAGOS*`, `10_NOISE_MONACO*` | 4/4 leituras determinísticas |
| relatório | este `EXECUCAO_REALISMO_C0.md` | staged, sem commit do executor |

Mensagens aprovadas pelo dono no freeze, a usar nos dois commits de proveniência:

1. `REALISMO-1 C0 etapa B: matriz OFF N=1..4 — 8 corridas (provenance)`
2. `REALISMO-1 C0 etapa B: extração (2 leituras) + relatório de ruído (provenance)`

## 6. Ledger e fechamento

Esta execução appendou uma linha idêntica no fim de:

- `backend/PROJECT_STATE.md`;
- `worklog.md`;
- `backend/model_train/AUDITORIA_RL.md`.

O dono deve conferir os hashes, especialmente a métrica corrigida de Monaco, e fazer os dois commits de proveniência autorizados pelo prereg. Nenhuma promoção ou alteração de default ocorreu.

## REPORT

- Freeze: `240bacde17b0301da6d5f0db30d52fb5cad03397`.
- g0: **20F/458P/3S**, 210,76 s; fail-set idêntico ao `promocao-1`.
- Corridas: **8/8** completas, uma por vez; 0 reruns.
- Extrações: **32/32** determinísticas; ruído: **4/4** leituras idênticas.
- Mecanismos: nenhum; C0 é matriz OFF e medição de ruído.
- Commits: nenhum feito pelo executor nesta etapa.

---

## 7. Apêndice do dono — verificação independente e closing (2026-10-30)

1. **Verificação de bytes.** HEAD `240bacd`; 65 arquivos staged (24 de corrida, 32 de extração, 4 de ruído, g0, este EXECUCAO, 3 ledgers); **zero `.py`**, zero edição de v1/v2 ou de modelo; strays intocados. 8/8 CSVs com 30.002 linhas; 8/8 sidecars; 8/8 logs com `residual baseline sha256=6210fff65b19ad0e` 1×, `VARIEDADE-1` 1×, sem traceback e com os 3 blocos de sumário; 8 hashes de CSV distintos (g3); `integrity.ok=true` (com `csv_track_sha`, `log_track_sha`, `expected_variedade`, `main_physical_lines`, `residual_baseline`, `no_residual_override`) nos 8 JSONs; 32/32 leituras de extração e 4/4 de ruído `cmp` byte-idênticas; ledgers ×3 idênticas (md5 `e1b8a520…`).

2. **Emenda do g0 (aceita).** A 1ª tentativa do g0 foi PARE de infraestrutura (cwd incorreto; falha antes do pytest; nenhuma saída criada). O dono autorizou UMA nova tentativa por emenda no chat. O g0 não é corrida; nenhuma corrida foi reexecutada. g0 final: 481 = 20F/458P/3S em 210,76 s, fail-set byte-idêntico ao canônico (`eadd9db4…`).

3. **Caveat de exit-code (aceito).** O supervisor não expôs o código numérico. Evidência compensatória verificada: logs completos com sumários, 30.000 amostras, sidecars, ausência de traceback/timeout e `integrity.ok` nos 8 JSONs — nenhum modo de falha plausível (crash/timeout) deixaria esse conjunto completo. Disclosure mantido; nenhuma re-execução autorizada.

4. **EMENDA DE HASH (correção de registro).** O hash deste EXECUCAO reportado ao dono (`7f0d3d24…`) não corresponde aos bytes staged (`2104a6010cdfae89396fda0db670eac408d456edcf97ae18aa2558a65ea944f0`, disco = index): o arquivo evoluiu após o hash. O conteúdo staged é completo (inclui a §1 e o caveat). O hash final, após este apêndice, é reportado no commit de closing. Nenhum outro artefato tem divergência: g0, 8 corridas, 32 extrações e 4 ruído conferidos byte a byte.

5. **Leitura do ruído (dado novo que o C1 usa).** Contatos são caóticos entre realizações: Interlagos 107/340/627/406/344 (soma 1.824, sd 415); Monaco 210/487/373/374/725 (soma 2.169, sd 426). N=0 NÃO é referência de desenvolvimento para contagem. Métricas estruturais são estáveis: fora% 26,2–26,7 / 49,2–50,7; excursões t≤60 s 33–41 / 64–73; Z_RETA 12–18 / 6–7; T1 9–11 / 7–11; Junção 40–51.
   **Agenda de ratificação no freeze do C1** (nada muda agora):
   - Agregação por soma mantida; tabela por realização como disclosure.
   - Gates primários exigem melhora MATERIAL ≥ 2σ da soma OFF (sob a nula, `ON < OFF` estrito dá falso PASS ≈ 0,48–0,52): C1P2 Interlagos ≤166 / Monaco ≤321; C5P ≤199; C23P Interlagos ≤39.347 / Monaco ≤73.732; C6G decidido no freeze do C6 (2σ de Interlagos = −42%, exigente demais; 1σ = −21% como alternativa; C6D estrutural como primário). S-1 vira disclosure (margem 2σ ≈ −50%).
   - C1P1 mantém "zero saídas na reta em 5/5 realizações" (pair_fail = 1,0 sob a nula — gate discriminativo).
   - R-2-T1: proposta de virar soma com margem 2σ (Interlagos ≤46 / Monaco ≤40) em vez de por realização (45% de falso FAIL sob a nula).
   - B-1: a banda +10% tem falso FAIL 33%/30% (somas OFF 1.824/2.169, sd 415/426; limiares 2.007/2.386). Proposta: duro em OFF+2σ (2.655/3.021; falso FAIL ≈2,3%) com alerta amarelo em +10% e PARE em outlier (≥3× o OFF da realização).
   - R-1/R-2 estáveis (falso FAIL 0,0–0,2%) — mantidos como estão.

6. **Estado.** N=5..8 selados; nenhum mecanismo, constante ou promoção; nenhum PASS/FAIL de comportamento emitido. Próximo passo autorizado: **C1-A** (atribuição por canal, sem simulação) + prereg do C1 com a agenda do item 5, com **PARE** no congelamento do dono.
