# EXECUÇÃO REALISMO-1 · C2 — handoff do rejoin

**Data:** 2026-11-01 (America/Sao_Paulo)

**Prereg congelado:** `backend/experiments/realismo-1/c2/PREREG_REALISMO_C2.md`.

**HEAD antes da implementação:** `641b74bb4c134fb72010bb50131982c7fca355a5`.

## 1. Veredito operacional

- A flag `--rejoin-handoff align` foi implementada nos dois runners.
- Testes focados C2: **9 passed**.
- Suíte completa serial: **20 failed / 478 passed / 3 skipped**, com fail-set idêntico ao C1. O aumento de passes em relação ao C1 corresponde aos 9 testes novos de C2.
- Os controles OFF 1 e 2 terminaram com `rc=0`, 30.002 linhas e `cmp=0` no CSV principal e no sidecar de eventos.
- Os 10 tratamentos ON terminaram serialmente; todos produziram 30.002 linhas e sidecar de eventos.
- As 48 leituras de extração foram concluídas após as corridas: cada par passou `cmp`, `canonical.metrics_sha256` conferiu com `base_metrics` e `integrity.ok=true`.

O C2-B passou todos os gates formais do prereg. Nenhum default foi promovido nesta etapa; este relatório é staged sem commit para o closing do dono.

## 2. Estatísticas do mecanismo

| Run | Pista/N | aligned | timeout | offtrack | ticks ativos |
|---:|---|---:|---:|---:|---:|
| 3 | Interlagos N0 | 10 | 0 | 0 | 687 |
| 4 | Monaco N0 | 10 | 0 | 0 | 2316 |
| 5 | Interlagos N1 | 10 | 0 | 0 | 631 |
| 6 | Monaco N1 | 10 | 0 | 0 | 2256 |
| 7 | Interlagos N2 | 10 | 0 | 0 | 682 |
| 8 | Monaco N2 | 9 | 0 | 1 | 2224 |
| 9 | Interlagos N3 | 10 | 0 | 0 | 672 |
| 10 | Monaco N3 | 10 | 0 | 0 | 2334 |
| 11 | Interlagos N4 | 10 | 0 | 0 | 817 |
| 12 | Monaco N4 | 10 | 0 | 0 | 2326 |

Total: **99 aligned, 0 timeout, 1 offtrack** em 100 carros/episódios.

## 3. Métricas ON × OFF por realização

Formato: `OFF -> ON`. `fora%` é percentual por realização; os gates de fora usam `offtrack_rows`.

| Run | Pista/N | contatos | t<=60 | laps | fora% | offtrack rows | excursões t<=60 | Z_RETA | T1<=60 | Junção | colado s | deadlocks |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | I/N0 | 107→300 | 95→148 | 44→45 | 26,4→25,1 | 7905→7529 | 35→37 | 12→12 | 12→10 | 51→44 | 32,6→40,4 | 0→0 |
| 4 | M/N0 | 210→460 | 96→240 | 31→31 | 49,9→48,3 | 14963→14478 | 67→59 | 6→6 | 9→9 | n/a | 80,2→143,0 | 1→3 |
| 5 | I/N1 | 340→388 | 178→350 | 45→45 | 26,3→25,6 | 7884→7694 | 42→32 | 18→9 | 10→10 | 40→41 | 41,2→57,6 | 1→1 |
| 6 | M/N1 | 487→386 | 285→104 | 31→30 | 49,2→47,6 | 14769→14270 | 70→68 | 7→7 | 7→8 | n/a | 109,4→149,8 | 1→3 |
| 7 | I/N2 | 627→427 | 483→383 | 44→46 | 26,6→25,6 | 7989→7666 | 42→38 | 16→13 | 11→12 | 40→46 | 88,0→50,4 | 3→2 |
| 8 | M/N2 | 373→858 | 91→184 | 32→29 | 49,2→48,4 | 14764→14508 | 61→61 | 6→6 | 11→9 | n/a | 97,4→143,6 | 2→3 |
| 9 | I/N3 | 406→206 | 296→196 | 44→45 | 26,2→25,9 | 7861→7761 | 34→39 | 12→10 | 10→12 | 43→42 | 45,4→33,4 | 1→0 |
| 10 | M/N3 | 374→357 | 194→163 | 29→30 | 49,5→48,5 | 14849→14537 | 72→68 | 7→7 | 10→9 | n/a | 91,4→77,4 | 1→0 |
| 11 | I/N4 | 344→582 | 296→370 | 43→41 | 26,4→26,5 | 7927→7961 | 33→34 | 13→12 | 9→12 | 47→41 | 33,8→67,6 | 1→2 |
| 12 | M/N4 | 725→859 | 347→376 | 29→31 | 50,7→48,5 | 15201→14536 | 72→64 | 7→7 | 11→11 | n/a | 97,2→204,4 | 2→6 |

### Somas formais por pista

| Pista | contatos OFF→ON | t<=60 OFF→ON | laps OFF→ON | offtrack rows OFF→ON | excursões t<=60 OFF→ON | Z_RETA OFF→ON | T1 OFF→ON | colado rows OFF→ON | deadlocks OFF→ON |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 1824→1903 | 1348→1447 | 220→222 | 39566→38611 | 186→180 | 71→56 | 52→58 | 1205→1247 | 6→5 |
| Monaco | 2169→2920 | 1013→1067 | 152→151 | 74546→72329 | 342→320 | 33→33 | 48→46 | 2378→3591 | 7→15 |

Disclosures de cascata/nova saída em até 10 s por corrida ON:

| Run | Pista/N | cascatas | nova saída <=5 s | reentradas |
|---:|---|---:|---:|---:|
| 3 | I/N0 | 119 | 37 | 220 |
| 4 | M/N0 | 274 | 145 | 372 |
| 5 | I/N1 | 97 | 31 | 197 |
| 6 | M/N1 | 275 | 137 | 374 |
| 7 | I/N2 | 110 | 42 | 210 |
| 8 | M/N2 | 259 | 153 | 367 |
| 9 | I/N3 | 114 | 40 | 219 |
| 10 | M/N3 | 263 | 142 | 364 |
| 11 | I/N4 | 127 | 50 | 231 |
| 12 | M/N4 | 284 | 155 | 383 |

## 4. Veredito formal dos gates

| Gate | Observado | Limiar | Status |
|---|---:|---:|---|
| C23P Interlagos | 38611 offtrack rows | <=39347 | **PASS** |
| C23P Monaco | 72329 offtrack rows | <=73732 | **PASS** |
| B-1 Interlagos | 1903 contatos | <=2655 | **PASS** |
| B-1 Monaco | 2920 contatos | <=3021 | **PASS** |
| B-1 alerta Interlagos | 1903 | <=2007 | **PASS limpo** |
| B-1 alerta Monaco | 2920 | <=2386 | **ALERTA** |
| B-1 outlier | nenhum ON >=3× OFF correspondente | nenhum | **PASS** |
| R-1 Interlagos | 222 laps_total | >=209 | **PASS** |
| R-1 Monaco | 151 laps_total | >=144 | **PASS** |
| R-2 Interlagos | 38611 <= 39566 + 150000 | +1,0 pp | **PASS** |
| R-2 Monaco | 72329 <= 74546 + 150000 | +1,0 pp | **PASS** |
| Integridade D2 | 12/12 corridas e 48/48 leituras | contrato D2 | **PASS** |

O C2-B passou todos os gates formais. O alerta Monaco permanece como disclosure porque contatos 2920 excedem a banda histórica de +10% (2386), mas permanecem abaixo do limite duro OFF+2σ (3021).

## 5. Autoridade e leitura do mecanismo

O handoff terminou alinhado em 99/100 episódios, sem timeout. Um episódio Monaco N2 terminou por `offtrack`. O handoff reduziu `offtrack_rows` em ambas as pistas e manteve os contatos abaixo dos limites duros. A redução de cascatas é divulgada por corrida acima; não há inferência causal além do desenho opt-in e dos gates pré-registrados.

A implementação não alterou os controles OFF: ambos reproduziram byte a byte os CSVs e sidecars canônicos. Não houve extração de produção, mudança de default ou promoção nesta etapa.

## 6. Hashes e proveniência

### 24 arquivos de corrida

| Arquivo | SHA-256 |
|---|---|
| `1_CTRL_INTERLAGOS_N0.csv` | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` |
| `1_CTRL_INTERLAGOS_N0_events.csv` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` |
| `1_CTRL_INTERLAGOS_N0.log` | `1a27ac8bbaafa6a99c78a1c7c66f4382d1c369fdec097667a69b98ba7fa5adec` |
| `2_CTRL_MONACO_N0.csv` | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9fadf2c9c9ba2c3b2ccc74669b5` |
| `2_CTRL_MONACO_N0_events.csv` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` |
| `2_CTRL_MONACO_N0.log` | `72c8cadfa375e782bb5646ac78244239156cd84115814b194ef5303c4f0ec0c3` |
| `3_ON_INTERLAGOS_N0.csv` | `014e3bdbe2596cf685930b0572016316548b114742cecd109135a86f37e254b2` |
| `3_ON_INTERLAGOS_N0_events.csv` | `d1243cf3178e36222c1b35f13331d5d73539d09a0135636d9f439790ffed32c5` |
| `3_ON_INTERLAGOS_N0.log` | `2a8d357379918bc1989940cf2eb3cf5d5c6f3271f8bba38f99ed16f8761371bd` |
| `4_ON_MONACO_N0.csv` | `18b067fc93efb4b15091c15ea398b1526fa3ef7c6c6c86a6ee3c64b5b774e423` |
| `4_ON_MONACO_N0_events.csv` | `3894ac1802e46e4158986cd06d5447f4c566f02429288f044901810d301b3533` |
| `4_ON_MONACO_N0.log` | `e07055f721b1ee8fae46920834bf7d06360a196a0064b5042feec5b0f835cefd` |
| `5_ON_INTERLAGOS_N1.csv` | `ae38ed9639b0cb7efbff8accc6058686cb78e546e199f2181b3c526e31e298d9` |
| `5_ON_INTERLAGOS_N1_events.csv` | `82ee8fc3cc02e5402540288a9ad6d1421c58fe37dd94b8b50b2ea67ab56e6fb3` |
| `5_ON_INTERLAGOS_N1.log` | `d5788890b775101f8b2d9cbafdd4f43371773a61079afe1100b12595dd67e50a` |
| `6_ON_MONACO_N1.csv` | `8ec7ed38eca29a50dcb03b436f191475ab0b7bc57c6c1c7067af04a004505611` |
| `6_ON_MONACO_N1_events.csv` | `bcfa3ead287dd5b502729f79f5ed6a44a749ed2cf1088a7fd38af511796bd5dd` |
| `6_ON_MONACO_N1.log` | `60aa34fceab29083628271051d65196193fcecfa56729408fe85733d35c42101` |
| `7_ON_INTERLAGOS_N2.csv` | `7477fb348d0cd37653bcdbdd63add6b8c890ffe8c11b30accc8072706febff6d` |
| `7_ON_INTERLAGOS_N2_events.csv` | `82a78c05e30cdf31316d062ebea155d0e18f4e253d6b4c02ad44418621d9667a` |
| `7_ON_INTERLAGOS_N2.log` | `494f034b5f3e97f063e08c8bf464eadd67b47590c21d8b393bfec1efa7c6a462` |
| `8_ON_MONACO_N2.csv` | `56e5954b4aa750dddd8e37abc4c66c05477c3ff3c87f68188c220ecba0f63614` |
| `8_ON_MONACO_N2_events.csv` | `2a8449a8b45c8e2b64480a4f6699f07fee19f5d2f6fee0eeb12252fbb0ac7c27` |
| `8_ON_MONACO_N2.log` | `0b277b914187dddff1891c358b531c56875592a77c19a24b067f2ba94a9b75fa` |
| `9_ON_INTERLAGOS_N3.csv` | `a010cc07da597c9510ecee2292167aabb0361b7f59a6df507fd253f6c4d8bca8` |
| `9_ON_INTERLAGOS_N3_events.csv` | `fa91555d85d958fff7bc149bf1d1ade8ffd1bb6bfc702d5d084ba7306ced07de` |
| `9_ON_INTERLAGOS_N3.log` | `ca3f56e682384bf901d0da120aec20f13eb1d046fcdcfa2dfe42d5e949f1420b` |
| `10_ON_MONACO_N3.csv` | `6ebb3c2cbc915d2b10d9eeda6567571d7d754dff6484bcde9bfee2005d68130b` |
| `10_ON_MONACO_N3_events.csv` | `da93ea982092be4e2cf0902fb7fa84537548f91f5e4194c48e818d7c5bb9533d` |
| `10_ON_MONACO_N3.log` | `83a5e6469f3b21e06e0225a2d570baa5e429c874575a7168d88ba71ad9911f0e` |
| `11_ON_INTERLAGOS_N4.csv` | `8c225458ef0d5d5e62e512b8f99315a980cbdddd7b26360f2cd0f6147084d049` |
| `11_ON_INTERLAGOS_N4_events.csv` | `7b99a9f940d99e0006c3bae97b58db7e9c3e4b82725aa1a76e09604d3e60fc86` |
| `11_ON_INTERLAGOS_N4.log` | `274e0cfa31aa0fa3760c8fa5128cfbbf477f701e25b992f807b235872718a244` |
| `12_ON_MONACO_N4.csv` | `1abbe27f6952d1a322646b02aacebcff0d317783a506bd3139b94a9295021396` |
| `12_ON_MONACO_N4_events.csv` | `3e7d6aa124ec8c87a159a5630e8841eab664c186d759537f90edc7f95d2b8ca8` |
| `12_ON_MONACO_N4.log` | `3912f5904559718d9de738f8f9cca37c7517d3e979fce26c9d05f59b522500c9` |

### 48 arquivos de extração

Os pares de leitura são byte-idênticos. Os hashes completos estão nos artefatos JSON staged; o padrão de cada par é `read2 == leitura1`.

| Grupo | Hash da leitura 1 | Hash da leitura 2 |
|---|---|---|
| `1_CTRL_INTERLAGOS_N0_base_metrics` | `17b44aff51a0084082421371c803cb2c03274987924254dd564287d42f065b02` | igual |
| `1_CTRL_INTERLAGOS_N0_realismo` | `9e43d36b253ac523094b739cdb6120290387497e913e006897875f3bde8ce87c` | igual |
| `2_CTRL_MONACO_N0_base_metrics` | `6ad9e9de5a195beea2a8b65e5646827f8735f3bf50597e7169d087fa0a00610f` | igual |
| `2_CTRL_MONACO_N0_realismo` | `b08e137c730d91a56bd6d74ebefd13bad52b8a4749c6afe31a9e217eb88a788e` | igual |
| `3_ON_INTERLAGOS_N0_base_metrics` | `106f35d2231eca40f2c5d481d7e5c213de4c19f4b6544b271ae97fb5e9192d0a` | igual |
| `3_ON_INTERLAGOS_N0_realismo` | `f7fa701c52b28ef8d7ab8aa8b2d5f5165d526703c4a8bf84091c61ab441e3125` | igual |
| `4_ON_MONACO_N0_base_metrics` | `450048eb60db6548c9d729b2271ae63945a52aac171621b1a04aa168e2f6511d` | igual |
| `4_ON_MONACO_N0_realismo` | `6b3ba16f5295106a0966f4a743aa89d6885b1701d1ab817511702829bdb069f2` | igual |
| `5_ON_INTERLAGOS_N1_base_metrics` | `1a4cc33830f3dd36b7340f54d40bf36adc02e90e49c918eb95cb82b229213dfc` | igual |
| `5_ON_INTERLAGOS_N1_realismo` | `a69e265647ca7f63ea839f27dc548c773febea71fc50cdf81560a4ea3147b77c` | igual |
| `6_ON_MONACO_N1_base_metrics` | `c377d83204a5a111be7a99b1e3f5de31fa81e6e0e2b22275484ab4b430ce7443` | igual |
| `6_ON_MONACO_N1_realismo` | `9d9a68e204e435081cdb11731fc759adb0de390bf20abe569e45885e7044c820` | igual |
| `7_ON_INTERLAGOS_N2_base_metrics` | `28549d3be9153ba0caad66824e26a9a16d416795e413c8c37c035cd405c9d2dd` | igual |
| `7_ON_INTERLAGOS_N2_realismo` | `1e40b16a5196de5f988f91dfa5403ac72f052ecd7118ed63ed0729136897cf8c` | igual |
| `8_ON_MONACO_N2_base_metrics` | `9bbcdfda29a2ede6b1337a0814cf56a00beb446ab70f9cf98692b6f6e94f4a39` | igual |
| `8_ON_MONACO_N2_realismo` | `83aaa700ce6cfdfde3f1925cc0cf65c43b5dc37c43723f43ea74ebb04e288718` | igual |
| `9_ON_INTERLAGOS_N3_base_metrics` | `c136bd2f1c4e697caa060667db94285d3ec75d26c4ddd85ae06e336b50cc1b71` | igual |
| `9_ON_INTERLAGOS_N3_realismo` | `e2a84a904ef73b6bd2819cf6652b26b89187de401fb505fa2fb1c9a7982c2bbb` | igual |
| `10_ON_MONACO_N3_base_metrics` | `c6fb2bfa0182106d88f043f70470d25389df095e69faca5d36a7aeff51453c93` | igual |
| `10_ON_MONACO_N3_realismo` | `5ff33fe298d058f5c79661cbfe6f2347909340c5c71ed46b7e6486dc4593ed54` | igual |
| `11_ON_INTERLAGOS_N4_base_metrics` | `6fc38a29cf23fcdc61e690c41b3439b8af2d3be934d4a7bc7ef986d8332aa2d7` | igual |
| `11_ON_INTERLAGOS_N4_realismo` | `6f2caef6e31b26466fc0c49bcc97e6adc2d2038f8e8af1ea569e9eda9c96aaa0` | igual |
| `12_ON_MONACO_N4_base_metrics` | `04799422ab6acf18794be9c1149f549c3658c95bfb78f6f5b7ade664393a0ed1` | igual |
| `12_ON_MONACO_N4_realismo` | `c03be1b23bd6fc6689aaa30af53ff9c6bae1db7f8284caad108880a0747440c5` | igual |

## 7. Encerramento

C2-B passou os gates formais do prereg. Nenhum default foi promovido nesta etapa. O relatório fica staged sem commit para o closing do dono.

### Nomes completos das leituras `read2`

Cada arquivo abaixo tem o mesmo SHA da leitura 1 correspondente, conforme `cmp=0`:

```text
1_CTRL_INTERLAGOS_N0_base_metrics_read2.json = 17b44aff51a0084082421371c803cb2c03274987924254dd564287d42f065b02
1_CTRL_INTERLAGOS_N0_realismo_read2.json = 9e43d36b253ac523094b739cdb6120290387497e913e006897875f3bde8ce87c
2_CTRL_MONACO_N0_base_metrics_read2.json = 6ad9e9de5a195beea2a8b65e5646827f8735f3bf50597e7169d087fa0a00610f
2_CTRL_MONACO_N0_realismo_read2.json = b08e137c730d91a56bd6d74ebefd13bad52b8a4749c6afe31a9e217eb88a788e
3_ON_INTERLAGOS_N0_base_metrics_read2.json = 106f35d2231eca40f2c5d481d7e5c213de4c19f4b6544b271ae97fb5e9192d0a
3_ON_INTERLAGOS_N0_realismo_read2.json = f7fa701c52b28ef8d7ab8aa8b2d5f5165d526703c4a8bf84091c61ab441e3125
4_ON_MONACO_N0_base_metrics_read2.json = 450048eb60db6548c9d729b2271ae63945a52aac171621b1a04aa168e2f6511d
4_ON_MONACO_N0_realismo_read2.json = 6b3ba16f5295106a0966f4a743aa89d6885b1701d1ab817511702829bdb069f2
5_ON_INTERLAGOS_N1_base_metrics_read2.json = 1a4cc33830f3dd36b7340f54d40bf36adc02e90e49c918eb95cb82b229213dfc
5_ON_INTERLAGOS_N1_realismo_read2.json = a69e265647ca7f63ea839f27dc548c773febea71fc50cdf81560a4ea3147b77c
6_ON_MONACO_N1_base_metrics_read2.json = c377d83204a5a111be7a99b1e3f5de31fa81e6e0e2b22275484ab4b430ce7443
6_ON_MONACO_N1_realismo_read2.json = 9d9a68e204e435081cdb11731fc759adb0de390bf20abe569e45885e7044c820
7_ON_INTERLAGOS_N2_base_metrics_read2.json = 28549d3be9153ba0caad66824e26a9a16d416795e413c8c37c035cd405c9d2dd
7_ON_INTERLAGOS_N2_realismo_read2.json = 1e40b16a5196de5f988f91dfa5403ac72f052ecd7118ed63ed0729136897cf8c
8_ON_MONACO_N2_base_metrics_read2.json = 9bbcdfda29a2ede6b1337a0814cf56a00beb446ab70f9cf98692b6f6e94f4a39
8_ON_MONACO_N2_realismo_read2.json = 83aaa700ce6cfdfde3f1925cc0cf65c43b5dc37c43723f43ea74ebb04e288718
9_ON_INTERLAGOS_N3_base_metrics_read2.json = c136bd2f1c4e697caa060667db94285d3ec75d26c4ddd85ae06e336b50cc1b71
9_ON_INTERLAGOS_N3_realismo_read2.json = e2a84a904ef73b6bd2819cf6652b26b89187de401fb505fa2fb1c9a7982c2bbb
10_ON_MONACO_N3_base_metrics_read2.json = c6fb2bfa0182106d88f043f70470d25389df095e69faca5d36a7aeff51453c93
10_ON_MONACO_N3_realismo_read2.json = 5ff33fe298d058f5c79661cbfe6f2347909340c5c71ed46b7e6486dc4593ed54
11_ON_INTERLAGOS_N4_base_metrics_read2.json = 6fc38a29cf23fcdc61e690c41b3439b8af2d3be934d4a7bc7ef986d8332aa2d7
11_ON_INTERLAGOS_N4_realismo_read2.json = 6f2caef6e31b26466fc0c49bcc97e6adc2d2038f8e8af1ea569e9eda9c96aaa0
12_ON_MONACO_N4_base_metrics_read2.json = 04799422ab6acf18794be9c1149f549c3658c95bfb78f6f5b7ade664393a0ed1
12_ON_MONACO_N4_realismo_read2.json = c03be1b23bd6fc6689aaa30af53ff9c6bae1db7f8284caad108880a0747440c5
```

## 8. Apêndice do dono — verificação independente e closing (2026-11-01)

1. **Verificação de integridade.**

   - HEAD base `641b74b`.

   - 96 arquivos staged com proveniência completa: código C2-B nos dois runners, novo teste de conformidade (9/9 passed), suíte com fail-set idêntico (20F/478P/3S), C2-A, prereg C2, 12 corridas completas (30.002 linhas e sidecars), 48 extrações determinísticas (cmp=0 em todas as duplas), 3 ledgers idênticos e o relatório de execução.

   - Strays conhecidos preservados fora do repositório.

   - Controles OFF 1 e 2 confirmaram identidade byte a byte contra promocao-1.

2. **Homologação científica do mecanismo.**

   - O mecanismo `--rejoin-handoff align` (bearing para projeção + 10 m, θ_H=20°, m_H=0,5 m, T_H=24 s) atingiu 99% de alinhamento com zero timeouts.

   - **C23P primário aprovado com melhora material >= 2σ nas duas pistas:** redução de 955 linhas fora em Interlagos (38611 <= 39347) e de 2217 linhas em Monaco (72329 <= 73732).

   - **B-1 aprovado:** Interlagos 1903 <= 2655 (abaixo da banda de 10%); Monaco 2920 <= 3021 (dentro de 2σ; alerta amarelo mantido como disclosure). Zero outliers >= 3x OFF.

   - **R-1 e R-2 aprovados:** ritmo preservado (222 e 151 voltas) e redução líquida da taxa de offtrack.

3. **Decisão de engenharia.**

   - **Veredito formal: PASS (APROVADO).**

   - O mecanismo `--rejoin-handoff align` está homologado como o primeiro componente aprovado do programa REALISMO-1.

   - A flag segue como opt-in aprovado para consolidação final no Ciclo C7.

4. **Próximo passo autorizado.**

   - Ciclo C2 formalmente encerrado.

   - Autorizada a abertura do **Ciclo C3** (Task 9 do PLANO_REALISMO_BOTS_1.md: teste offline sem simulação para verificar se a rampa morde >= 30% das reentradas).
