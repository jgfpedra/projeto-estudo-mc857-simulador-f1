# EXECUÇÃO REALISMO-1 · C3 — rampa P2 pós-reentrada

**Data:** 2026-11-02 (America/Sao_Paulo)

**Prereg congelado:** `backend/experiments/realismo-1/c3/PREREG_REALISMO_C3.md`.
**Freeze do Dono:** `f0a416aec30e95141d25d58855426c76aa796c3d`.

## 1. Veredito operacional

- Controles OFF: Runs 1 e 2 com `rc=0`, 30.002 linhas, sidecars e `cmp=0` no CSV e sidecar contra promocao-1.
- Suíte serial: **20F/485P/3S**, com fail-set idêntico ao baseline conhecido.
- Runs ON 3–12: **10/10** concluídos serialmente com `rc=0`, 30.002 linhas e sidecar.
- Extração: **48/48 leituras** concluídas; todos os pares passaram `cmp`, o `canonical.metrics_sha256` conferiu com `base_metrics.metrics_sha256` e `integrity.ok=true`.
- Emenda Formal do Dono nº 1 aceita: o aborto pré-launch de cwd do Run 1 fica registrado no disclosure abaixo.
- **Veredito formal dos gates C3: PASS.** C23P, B-1 duro, R-1, R-2 e integridade D2 passaram.

## 2. Estatísticas do mecanismo

| Run | Pista/N | ativações | linhas ativas 5 Hz | linhas com freio 5 Hz |
|---:|---|---:|---:|---:|
| 3 | I/N0 | 224 | 4934 | 863 |
| 4 | M/N0 | 349 | 7278 | 573 |
| 5 | I/N1 | 217 | 4906 | 915 |
| 6 | M/N1 | 356 | 7532 | 543 |
| 7 | I/N2 | 216 | 4761 | 897 |
| 8 | M/N2 | 354 | 7178 | 547 |
| 9 | I/N3 | 211 | 4678 | 919 |
| 10 | M/N3 | 365 | 7622 | 708 |
| 11 | I/N4 | 214 | 4813 | 862 |
| 12 | M/N4 | 367 | 7617 | 713 |

Totais ON: **2.873 ativações**, **61.319 linhas ativas** e **7.540 linhas com freio**, contados no CSV amostrado a 5 Hz. Os controles OFF têm zero ativação por definição.

## 3. ON × OFF por realização

Formato: `OFF → ON`. `fora%` é por realização; C23P e R-2 usam `offtrack_rows`.

### Interlagos

| N | contatos | t<=60 | laps | fora% | offtrack rows | exc<=60 | Z_RETA | T1<=60 | colado s | deadlocks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 107 → 303 | 95 → 243 | 44 → 43 | 26.4 → 25.1 | 7905 → 7539 | 35 → 48 | 12 → 16 | 12 → 17 | 32.6 → 28.0 | 0 → 1 |
| 1 | 340 → 273 | 178 → 259 | 45 → 42 | 26.3 → 24.6 | 7884 → 7380 | 42 → 45 | 18 → 16 | 10 → 12 | 41.2 → 20.8 | 1 → 1 |
| 2 | 627 → 742 | 483 → 555 | 44 → 41 | 26.6 → 26.3 | 7989 → 7888 | 42 → 41 | 16 → 16 | 11 → 13 | 88.0 → 120.2 | 3 → 2 |
| 3 | 406 → 231 | 296 → 221 | 44 → 43 | 26.2 → 25.1 | 7861 → 7533 | 34 → 34 | 12 → 12 | 10 → 10 | 45.4 → 30.6 | 1 → 0 |
| 4 | 344 → 604 | 296 → 356 | 43 → 42 | 26.4 → 25.2 | 7927 → 7556 | 33 → 36 | 13 → 12 | 9 → 11 | 33.8 → 62.0 | 1 → 2 |

**Somas Interlagos:** contatos 1824 → 2153; t<=60 1348 → 1634; laps 220 → 211; offtrack rows 39566 → 37896; exc<=60 186 → 204; Z_RETA 71 → 72; T1 52 → 63; colado s 241.0 → 261.6; deadlocks 6 → 6.

FORA-PRESO rows: 30336 → 26599; fora agregado: 26.377% → 25.264%.

### Monaco

| N | contatos | t<=60 | laps | fora% | offtrack rows | exc<=60 | Z_RETA | T1<=60 | colado s | deadlocks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 210 → 428 | 96 → 366 | 31 → 30 | 49.9 → 47.6 | 14963 → 14283 | 67 → 54 | 6 → 6 | 9 → 9 | 80.2 → 75.4 | 1 → 1 |
| 1 | 487 → 488 | 285 → 178 | 31 → 30 | 49.2 → 47.5 | 14769 → 14259 | 70 → 56 | 7 → 7 | 7 → 5 | 109.4 → 188.0 | 1 → 5 |
| 2 | 373 → 453 | 91 → 218 | 32 → 31 | 49.2 → 47.1 | 14764 → 14130 | 61 → 67 | 6 → 6 | 11 → 11 | 97.4 → 81.2 | 2 → 0 |
| 3 | 374 → 558 | 194 → 346 | 29 → 31 | 49.5 → 46.7 | 14849 → 14015 | 72 → 56 | 7 → 7 | 10 → 7 | 91.4 → 97.2 | 1 → 3 |
| 4 | 725 → 559 | 347 → 281 | 29 → 29 | 50.7 → 48.4 | 15201 → 14519 | 72 → 60 | 7 → 7 | 11 → 9 | 97.2 → 133.4 | 2 → 3 |

**Somas Monaco:** contatos 2169 → 2486; t<=60 1013 → 1389; laps 152 → 151; offtrack rows 74546 → 71206; exc<=60 342 → 293; Z_RETA 33 → 33; T1 48 → 41; colado s 475.6 → 575.2; deadlocks 7 → 12.

FORA-PRESO rows: 56911 → 49746; fora agregado: 49.697% → 47.471%.

### Somas formais por pista

| Pista | contatos OFF→ON | t<=60 OFF→ON | laps OFF→ON | offtrack rows OFF→ON | exc<=60 OFF→ON | Z_RETA OFF→ON | T1 OFF→ON | colado s OFF→ON | deadlocks OFF→ON |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 1824→2153 | 1348→1634 | 220→211 | 39566→37896 | 186→204 | 71→72 | 52→63 | 241.0→261.6 | 6→6 |
| Monaco | 2169→2486 | 1013→1389 | 152→151 | 74546→71206 | 342→293 | 33→33 | 48→41 | 475.6→575.2 | 7→12 |

## 4. Veredito formal dos gates

| Gate | Observado | Limiar congelado | Status |
|---|---:|---:|---|
| C23P Interlagos | 37.896 offtrack rows | <=39.347 | **PASS** |
| C23P Monaco | 71.206 offtrack rows | <=73.732 | **PASS** |
| B-1 contatos Interlagos | 2.153 | <=2.655 | **PASS**; alerta +10% (2.007) acionado |
| B-1 contatos Monaco | 2.486 | <=3.021 | **PASS**; alerta +10% (2.386) acionado |
| B-1 outlier | nenhum ON >=3× OFF | nenhum | **PASS** |
| R-1 Interlagos | 211 laps | >=209 | **PASS** |
| R-1 Monaco | 151 laps | >=144 | **PASS** |
| R-2 Interlagos | 25,264% vs 26,377% OFF | OFF +1,0 pp | **PASS** |
| R-2 Monaco | 47,471% vs 49,697% OFF | OFF +1,0 pp | **PASS** |
| Integridade D2 | 12/12 corridas; 48/48 leituras | contrato D2 | **PASS** |

Nenhuma realização ON atingiu três vezes o contato OFF correspondente. Os dois alertas de +10% são disclosures, não falhas dos gates duros.

## 5. Registro D3 / C3b

No melhor estado aprovado, o estado ON C3-B, os valores são:

| Pista | fora ON | FORA-PRESO ON | 2×preso | Condição `2×preso > fora` | Decisão futura |
|---|---:|---:|---:|---|---|
| Interlagos | 37.896 | 26.599 | 53.198 | **ACIONADA** | perfil de velocidade na grama com gap-check em ciclo próprio |
| Monaco | 71.206 | 49.746 | 99.492 | **ACIONADA** | perfil de velocidade na grama com gap-check em ciclo próprio |

O mecanismo C3b não foi implementado neste ciclo e não foi combinado com a rampa.

## 6. Disclosures de infraestrutura

- **Emenda Formal do Dono nº 1:** aceita o aborto pré-launch inicial do Run 1 causado por cwd incorreto (`.venv/bin/python` não encontrado na raiz do workspace).
- Após a emenda, houve uma segunda tentativa de invocação na raiz, encerrada antes do início do simulador e sem artefato; a matriz efetiva foi então executada a partir de `backend/`.
- Durante a execução efetiva, os CSVs e sidecars foram persistidos. O stdout dos runs não foi redirecionado para logs permanentes; os 12 `.log` usados na extração foram reconstruídos a partir dos CSVs persistidos e dos resumos capturados do terminal, contendo os campos exigidos pelos extratores. Essa limitação de proveniência deve permanecer explícita no closing do dono.

## 7. Hashes e proveniência

Os 24 hashes de corrida são listados por linha (`CSV`, `events` e `log`); os 48 hashes JSON são listados por grupo, com `read2` byte-idêntico à leitura 1.

### Arquivos de corrida

| Run | CSV SHA-256 | events SHA-256 | log SHA-256 |
|---:|---|---|---|
| 1_CTRL_INTERLAGOS_N0 | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` | `fa632b9db7ef188ce56da805b23f571116ff34ad474b8e5c8dd8e4866af05451` |
| 2_CTRL_MONACO_N0 | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` | `b8ebd182441b66b7c9a43661f8d1a2f95e61e33ab8e7431e19362a3d10426e5e` |
| 3_ON_INTERLAGOS_N0 | `bb78b936b54ab0005a444429f10ad0c258d7fb2d4988d7324e5488a07d8cea93` | `35826be5203c7730bf7da9be407fd01c19d4c5a8315357a996bfc2778eb7686b` | `6cd74b2c91b3c322d45671789e3560064adde181348282cc3a95b62a95aa4b44` |
| 4_ON_MONACO_N0 | `7f1f12a89bce03ea53e3f54e038023c338a3e43f4bf373d917b4e898645f94a5` | `c28a752c2314b16383206e3c189ebbdb5c462fabc6f029d6cfad73da946b952d` | `55043ecdc4d01381aa73897093e9114736c4f18dc1a11c9374499ea7bda712ba` |
| 5_ON_INTERLAGOS_N1 | `f1dadffc4fb84ab30fcf9141838e3f1581b00d621bb9c6530e138e2c8b60d928` | `ed5e7554287617cd624839e79cf84bdce0832845aa2a32d34485fa3d9127375f` | `c414942177d9a8d7658099015d06fe90c0cdd39fd9213d0a2c3ce0b1d354ce8c` |
| 6_ON_MONACO_N1 | `7ac280d08d523befdaa1cc60e19c0b20cd3b26040e8ad3eb32ce44dc8ead230b` | `59448f4fcf266ed01c656f86f5498a72004006fb5e7bb4e64fd1cfd556549794f` | `0963bd5eba20970e699b878630c336190f48329d37a47f10a0c388cb60cba8cf` |
| 7_ON_INTERLAGOS_N2 | `c6a23db47db68367089890375095eb372c8930dc97a7734ad211ac216faefb31` | `adcd51888c9e4c989e2242f19189a5ccee771a7b1224557f7079a27f9ca2f7a6` | `179ac30df800cb66f349342fde44769db45a5615fe4d056756b3df7fa4cea97c` |
| 8_ON_MONACO_N2 | `6f7b43e43490a755c2520fbc356442d775538ed31e5d194a2062dc9e9326d533` | `29d47c42196030e25522c7f561d20e190d8d970304089a4fc498fd8a4559428c` | `8a7c899effc285387fa3cf559014b3fbf0dd34a440827a496af40b8860b912d9` |
| 9_ON_INTERLAGOS_N3 | `c5c0a9fd1617ac640547fdec82a5ce84bd42a66a8e728f8cb1a7bd071deb5351` | `0afa1d9609f8fc1a8c0e7762e67faeb736ba019d6532abc67bf423dd43ad6c05` | `e9cf4a89ab342e1785e53fb5d6aff233404b79de4bedc174e855bb39dc0f000c` |
| 10_ON_MONACO_N3 | `8dd6bc49b3b18f706c26e54e82f8282b001ca22c58d74fe2f9106f1ae43dd938` | `1fd54c1dedba9ac34d2613bed63aa2374e6054858a79b5ccd6c2e9b1490dcb0d` | `312c1cd84464a802526a29b4c70cfd9562df6a586935742d18439bf9097ae543` |
| 11_ON_INTERLAGOS_N4 | `68d53106e5caea3e977f9a6c42376bb98b32d3f5bd69fb2fe8e1a62a2deb323e` | `ebcc0f5d9c87bc30869940f522c6a5c3509100deb6f358b923251b52c34c5b78` | `de34f38bbb882183c230a47d50593896e578ec010128bde5c6d7269c4d97ad32` |
| 12_ON_MONACO_N4 | `221bebc1bc3bfa4f93b1ade54373a1a9f0f37cbb64d8222c808b6992d57221cd` | `649bebe29ce9642e0435035c4979a69ba88dc6f5d607f688930d9e17d5a378d2` | `e6e91b0063e61bec79c861f0b229a92dc7fe3aa3a9dc847c49a2fd13882cc072` |

### JSONs de extração

| Run | base_metrics SHA-256 (read1=read2) | realismo SHA-256 (read1=read2) |
|---|---|---|
| 1_CTRL_INTERLAGOS_N0 | `44d54038fd5708681a3c5002a949d0f626fa729bdd2727227d637cd37b2e7737` | `91c3f668cb31dded36036f3ce021d22d8d333614466e2e895166b9dd9a81265a` |
| 2_CTRL_MONACO_N0 | `76c36f9560b2328e85c5e9ca0b326ba2ac627d36ea0dd81446dfce91c9ce4bab` | `ee68809ba19c52c9b19d1fefd67e4a5b7b5f36b7a3f1b01ddfa7c8c3abe7247d` |
| 3_ON_INTERLAGOS_N0 | `56e0159400cb56a374701332ac018790cd0e9ea0709f2d7b2daecf84a3cdb29b` | `157f4afb88c9ad5ba431c93fae5d0157b5792e3de1a364073428aebe63641135` |
| 4_ON_MONACO_N0 | `5cfdfca8db1ffd1e61e5569cbd9b74b594c9ebb757159b0d3efc668dbf305689` | `0a7c1df9ed073f329f6be74026ef8c7f8681ab9980cd97b5c9897b52a63849cf` |
| 5_ON_INTERLAGOS_N1 | `5b016419926644fde87cdffc423c1ce6dc2751de1e5709c83f1bf680368c4b3e` | `9143455be14c068c41602bfdb0d1c60b5460e5f1f5c576e1f73330346715b451` |
| 6_ON_MONACO_N1 | `27fa9d4ba60cfc43c619b8c8a403618424e7f2f85a02377099c81b40c8de5705` | `9f3e8d0adddf7fff892fa1bc7f56bf59fbca1e8922895b8503e8e6438d9d489f` |
| 7_ON_INTERLAGOS_N2 | `b76df38a2bda0e9afa4ab4bc800737f53956d357f86bfbce004bcf1a901603c6` | `2093b9638ff499f0bddc6220b9423429f72accd07a9ec0f27189324b0bbea14a` |
| 8_ON_MONACO_N2 | `27e7717acaa78e8661f360e4dc821f74e7835e7cb98d2a849bf63a45b99d3599` | `bf77d9eef5ecb75594ee71eef97d754355317b321b7be5c1e5e3ef17528cc9dc` |
| 9_ON_INTERLAGOS_N3 | `aac1cc52f6318f22ef15072468f405c775409b2650841090b4545cf39cc90ceb` | `4bb1236da4b43fe9c5dc1df5b46f5e53061b471bb840e37421a6ce8ce7f82f57` |
| 10_ON_MONACO_N3 | `97a49b695b16b9e93fe7dc669a80f05ec16c22da611fe4758777f9ff8189cdfe` | `af53ff3be89c4d8ee0b93efa8c3da5dcf453af9a8ea9ce9996e87a941e18c94b` |
| 11_ON_INTERLAGOS_N4 | `076262f072fe850a0a9c02019951de06931daac04a444f8f48cd9abc8c80078b` | `0d3f85ed00b93875262412ef94a67aae5cc393158921bdb5c45892760f1ce093` |
| 12_ON_MONACO_N4 | `6bd34f489730a8c0bd995f44aa3e2511a361bb665c09344cfb2b136692c73f8d` | `dba03c1123a30466ecec586f2ba9334dc660ceaa6ad015dbf6a2be1eebb6eb74` |

## 8. Apêndice do dono — verificação independente e closing (2026-11-02)

1. **Verificação de integridade.**
   - HEAD base `f0a416a`.
   - 91 arquivos staged com proveniência completa: código C3-B nos dois runners (`race_diagnostic.py` e `run_race_10_cars.py`), novo teste de conformidade (`backend/tests/test_rejoin_ramp.py`, 24/24 passed), suíte com fail-set idêntico (20F/485P/3S), 12 corridas completas (30.002 linhas e sidecars), 48 extrações determinísticas (cmp=0 em todas as duplas), 3 ledgers idênticos e o relatório de execução.
   - Strays conhecidos (`.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`) preservados estritamente fora do stage/repositório.
   - Controles OFF 1 e 2 confirmaram identidade byte a byte contra `promocao-1`.
   - **Disclosures aceitos:** (a) Emenda Formal do Dono nº 1 aceita para o aborto pré-launch com cwd incorreto; (b) Reconstrução dos 12 arquivos `.log` a partir de CSVs persistidos e resumos de terminal aceita com disclosure explícito, mantendo integridade dos dados de telemetria e extração canônica.

2. **Homologação científica do mecanismo.**
   - O mecanismo `--rejoin-ramp` (teto linear de velocidade pós-reentrada de $v_{exit}$ a $v_{plan}(s)$ ao longo de $\Delta T_{ramp}=5\,\text{s}$ via freio longitudinal acionado por `_v_plan_cap`) atingiu 2.873 ativações, 61.319 linhas ativas e 7.540 ticks com freio nos 10 runs de tratamento.
   - **C23P primário aprovado com melhora material $\ge 2\sigma$ nas duas pistas:** redução de 1.451 linhas fora do limiar em Interlagos (37.896 $\le$ 39.347; melhora líquida de $-1.670$ linhas vs OFF) e de 2.526 linhas em Monaco (71.206 $\le$ 73.732; melhora líquida de $-3.340$ linhas vs OFF).
   - **B-1 aprovado:** Interlagos 2.153 $\le$ 2.655; Monaco 2.486 $\le$ 3.021. Ambos abaixo do teto duro de $+2\sigma$. Alertas amarelos de $+10\%$ mantidos como disclosure. Zero outliers $\ge 3\times\text{OFF}$.
   - **R-1 e R-2 aprovados:** ritmo preservado (211 e 151 voltas) e redução líquida da taxa de offtrack (25,264% vs 26,377% OFF em Interlagos; 47,471% vs 49,697% OFF em Monaco).
   - **Registro D3 / C3b acionado:** condição $2 \times \text{preso} > \text{fora}$ confirmada nas duas pistas ($2 \times 26.599 = 53.198 > 37.896$ em Interlagos; $2 \times 49.746 = 99.492 > 71.206$ em Monaco). Aprovado para ciclo próprio futuro (perfil de velocidade na grama com gap-check).

3. **Decisão de engenharia.**
   - **Veredito formal: PASS (APROVADO EM TODOS OS GATES).**
   - O mecanismo `--rejoin-ramp` está homologado como o segundo componente aprovado do programa REALISMO-1.
   - A flag segue como opt-in aprovado para consolidação final no Ciclo C7.

4. **Próximo passo autorizado.**
   - Ciclo C3 formalmente encerrado.
   - Autorizada a abertura do **Ciclo C4** (Engenharia de Geometria da Junção — Tasks 10 e 11 do PLANO_REALISMO_BOTS_1.md: análise offline com cache local do FastF1 sem qualquer simulação).
