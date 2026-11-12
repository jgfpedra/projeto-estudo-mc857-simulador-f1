# EXECUÇÃO REALISMO-1 · C1 — largada: mute direcional do residual

**Data:** 2026-10-30 (America/Sao_Paulo)

**Prereg congelado:** `backend/experiments/realismo-1/c1/PREREG_REALISMO_C1.md`, SHA `71a2c8157ffe9f44c3a0490f6b118c1997bbd310b6d5969059271c2a4097b400`, freeze do dono `5ff99f5f5b0d5aa8118214e89bdff1022f788c94`.

**Fix C1-B:** commit `36efcbb328de1c3fb346d5c424454bdb24f01999`; crash do commit anterior `fb6ba378` preservado em `1_CTRL_INTERLAGOS_N0_attempt1_crash.log` (SHA `9f9ae8768cd3c4ad7544a309ce30c9eb3d725dfc6f3017749cecb9c6b541196a`).

## 1. Veredito operacional

- Teste focal C1-B: **11 passed**.
- Suíte completa serial: **20 failed / 469 passed / 3 skipped**, fail-set idêntico ao C0. Log `0_full_suite_c1_fix.log`, SHA `987baf0c6d7a384dd13ccc6fbcea136375d2459e78bd51990e04e3833e322e23`.
- O run 1 Interlagos OFF foi repetido após o fix e passou `rc=0`, `cmp_main=0`, `cmp_events=0`.
- O run 2 Monaco OFF foi executado só depois do cmp do run 1 e passou `rc=0`, `cmp_main=0`, `cmp_events=0`.
- Os runs ON 3–12 foram executados serialmente, em ordem, com `--launch-steer-mute`, N=0..4 e seed 0. O shell terminou com `ON_RUNS_COMPLETE`.
- As 48 leituras de extração passaram: cada par de JSONs passou `cmp`, `canonical.metrics_sha256` bateu com o JSON correspondente de `base_metrics`, e `integrity.ok=true` em todas.
- Nenhum N>4 foi usado. Nenhum código adicional foi alterado depois do commit `36efcbb`. Nenhum commit foi feito nesta etapa.

### Controles OFF

| Controle | rc | cmp main | cmp events | CSV linhas | SHA main | SHA events |
|---|---:|---:|---:|---:|---|---|
| Interlagos | 0 | 0 | 0 | 30002 | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` |
| Monaco | 0 | 0 | 0 | 30002 | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` |

Os quatro hashes dos controles são iguais aos CSVs e sidecars canônicos da promocao-1. Os logs divergem apenas como esperado pela configuração/timestamps.

## 2. Janela D_L

Todas as dez corridas ON possuem as colunas `launch_steer_mute` e `launch_steer_mute_end_reason`. Não houve `deadline`.

A distribuição final por carro é:

| Run | Pista/N | crossed | offtrack | deadline |
|---|---|---:|---:|---:|
| 3 | Interlagos N0 | 10 | 0 | 0 |
| 4 | Monaco N0 | 10 | 0 | 0 |
| 5 | Interlagos N1 | 10 | 0 | 0 |
| 6 | Monaco N1 | 10 | 0 | 0 |
| 7 | Interlagos N2 | 10 | 0 | 0 |
| 8 | Monaco N2 | 10 | 0 | 0 |
| 9 | Interlagos N3 | 8 | 2 | 0 |
| 10 | Monaco N3 | 10 | 0 | 0 |
| 11 | Interlagos N4 | 10 | 0 | 0 |
| 12 | Monaco N4 | 10 | 0 | 0 |

O Run 9 teve `offtrack` para PER e PIA. Todos os demais carros ON terminaram D_L por `crossed`.

## 3. Métricas ON × OFF por realização

Formato das células: `OFF -> ON`. `fora%` é percentual por realização; as somas formais usam linhas `offtrack_rows`, não percentuais arredondados.

| Run | pista/N | contatos | t<=60 | laps | fora% | excursões t<=60 | Z_RETA | T1<=60 | Junção | colado s | deadlocks |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | I/N0 | 107→653 | 95→523 | 44→43 | 26,4→26,5 | 35→35 | 12→0 | 12→15 | 51→40 | 32,6→53,2 | 0→0 |
| 4 | M/N0 | 210→403 | 96→203 | 31→32 | 49,9→49,1 | 67→60 | 6→0 | 9→7 | n/a | 80,2→131,6 | 1→4 |
| 5 | I/N1 | 340→971 | 178→903 | 45→43 | 26,3→26,5 | 42→26 | 18→0 | 10→9 | 40→43 | 41,2→99,8 | 1→1 |
| 6 | M/N1 | 487→964 | 285→466 | 31→29 | 49,2→50,8 | 70→55 | 7→0 | 7→3 | n/a | 109,4→229,2 | 1→7 |
| 7 | I/N2 | 627→544 | 483→512 | 44→46 | 26,6→24,1 | 42→28 | 16→0 | 11→9 | 40→43 | 88,0→63,4 | 3→1 |
| 8 | M/N2 | 373→842 | 91→480 | 32→30 | 49,2→50,1 | 61→50 | 6→0 | 11→3 | n/a | 97,4→118,0 | 2→2 |
| 9 | I/N3 | 406→743 | 296→615 | 44→44 | 26,2→26,6 | 34→33 | 12→2 | 10→14 | 43→43 | 45,4→76,0 | 1→1 |
| 10 | M/N3 | 374→424 | 194→342 | 29→31 | 49,5→48,7 | 72→66 | 7→0 | 10→4 | n/a | 91,4→80,2 | 1→3 |
| 11 | I/N4 | 344→622 | 296→322 | 43→44 | 26,4→26,5 | 33→37 | 13→0 | 9→11 | 47→43 | 33,8→94,6 | 1→2 |
| 12 | M/N4 | 725→441 | 347→241 | 29→31 | 50,7→48,8 | 72→44 | 7→0 | 11→6 | n/a | 97,2→141,2 | 2→3 |

### Somas por pista

| Pista | contatos OFF→ON | t<=60 OFF→ON | laps OFF→ON | linhas fora OFF→ON | excursões t<=60 OFF→ON | Z_RETA OFF→ON | T1 OFF→ON | Junção OFF→ON | colado rows OFF→ON | deadlocks OFF→ON |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 1824→3533 | 1348→2875 | 220→220 | 39566→39041 | 186→159 | 71→2 | 52→58 | 221→212 | 1205→1935 | 6→5 |
| Monaco | 2169→3074 | 1013→1732 | 152→153 | 74546→74237 | 342→275 | 33→0 | 48→23 | n/a | 2378→3501 | 7→19 |

## 4. Veredito dos gates

| Gate | Pista | Observado | Limiar | Status |
|---|---|---:|---:|---|
| C1P1a | Interlagos | 0 expostas em 5/5 | 0 por realização | **PASS** |
| C1P1a | Monaco | 0 expostas em 5/5 | 0 por realização | **PASS** |
| C1P1b | Interlagos | 2 Z_RETA | <=59 | **PASS** |
| C1P1b | Monaco | 0 Z_RETA | <=30 | **PASS** |
| C1P2 | Interlagos | 159 excursões t<=60 | <=166 | **PASS** |
| C1P2 | Monaco | 275 excursões t<=60 | <=321 | **PASS** |
| B-1 duro | Interlagos | 3533 contatos | <=2655 | **FAIL** |
| B-1 duro | Monaco | 3074 contatos | <=3021 | **FAIL** |
| B-1 alerta +10% | Interlagos | 3533 | <=2007 | **ALERTA** |
| B-1 alerta +10% | Monaco | 3074 | <=2386 | **ALERTA** |
| B-1 outlier >=3x | Interlagos N0 | 653 vs OFF 107 | <321 | **PARE/outlier** |
| B-1 outlier >=3x | demais realizações | nenhum | 3x OFF | **DISCLOSURE** |
| R-2-T1 | Interlagos | 58 | <=46 | **FAIL** |
| R-2-T1 | Monaco | 23 | <=40 | **PASS** |
| R-1 ritmo | Interlagos | 220 | >=209 | **PASS** |
| R-1 ritmo | Monaco | 153 | >=144 | **PASS** |
| R-2 fora | Interlagos | 39041 linhas | <=39566 + 150000 | **PASS** |
| R-2 fora | Monaco | 74237 linhas | <=74546 + 150000 | **PASS** |
| S-1 contatos t<=60 | Interlagos | 2875 vs OFF 1348 | disclosure | **DISCLOSURE** |
| S-1 contatos t<=60 | Monaco | 1732 vs OFF 1013 | disclosure | **DISCLOSURE** |

**Veredito C1:** **FAIL**, por B-1 duro nas duas pistas, PARE de outlier no Interlagos N0 e R-2-T1 de Interlagos. O C1P1a, C1P1b, C1P2, R-1 e R-2 passaram, mas não anulam os gates de segurança falhos.

## 5. Mecanismo C1P1a e C1-A

As duas saídas Z_RETA do ON ocorreram somente no Run 9 (`9_ON_INTERLAGOS_N3`): PER e PIA, ambas em `t=4,6 s`, tick 46. Nenhuma foi exposta porque houve contato no segundo anterior.

### PER, Run 9

| tick | t_s | car_car | speed | s | lat |
|---:|---:|---:|---:|---:|---:|
| 36 | 3,6 | 2 | 26,83 | 2670,32 | 0,96 |
| 38 | 3,8 | 4 | 28,30 | 2675,84 | 0,93 |
| 40 | 4,0 | 2 | 29,67 | 2681,63 | 1,34 |
| 42 | 4,2 | 1 | 30,89 | 2687,41 | 2,59 |
| 44 | 4,4 | 0 | 32,05 | 2693,22 | 5,01 |

Soma `car_car` no intervalo: 9.

### PIA, Run 9

| tick | t_s | car_car | speed | s | lat |
|---:|---:|---:|---:|---:|---:|
| 36 | 3,6 | 0 | 24,40 | 2674,93 | 1,01 |
| 38 | 3,8 | 2 | 25,92 | 2679,95 | 0,61 |
| 40 | 4,0 | 2 | 27,18 | 2685,20 | 0,20 |
| 42 | 4,2 | 1 | 28,35 | 2690,45 | 1,87 |
| 44 | 4,4 | 0 | 29,59 | 2695,79 | 4,12 |

Soma `car_car` no intervalo: 5.

O C1-A mostrou residual direcionado para a saída em 16/18 janelas e solo direcionado para longe em 18/18, mas as corridas ON mostram que silenciar esse canal não protegeu os contatos: o B-1 piorou, principalmente no Interlagos N0 (653 vs 107 contatos). A hipótese compatível com os dados é retenção/reespraiamento do pelotão: o longitudinal do residual continua ativo, enquanto a remoção do esterço lateral muda a geometria relativa do campo. A exposição zero não significa largada segura quando as saídas acontecem com contato.

## 6. Hashes e proveniência

### 24 arquivos de corrida

| Arquivo | SHA-256 |
|---|---|
| `1_CTRL_INTERLAGOS_N0.csv` | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` |
| `1_CTRL_INTERLAGOS_N0_events.csv` | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` |
| `1_CTRL_INTERLAGOS_N0.log` | `2a464fb574534d627c4cda7df548a297eff725f35fe1754d481c600b93235a19` |
| `2_CTRL_MONACO_N0.csv` | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` |
| `2_CTRL_MONACO_N0_events.csv` | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` |
| `2_CTRL_MONACO_N0.log` | `021fcaf1d6c7729161a807bf7059453907cfff2707e0f6b5c8cb49825953abf7` |
| `3_ON_INTERLAGOS_N0.csv` | `c105e426e2834643175f1a63375560fd7ea9431ad65adadcade5c1f8a87e8aa0` |
| `3_ON_INTERLAGOS_N0_events.csv` | `ac1d9e5921bcd6d6c4225e76f6989a2e840af26512c99a4b96ca464f73366a97` |
| `3_ON_INTERLAGOS_N0.log` | `665d4dcd10b29502210ad35ba408bbfff6e72bf0bc1e4c4b41959c8853c9c44a` |
| `4_ON_MONACO_N0.csv` | `eff7436a4cd024240c60e535ac6e0ff512ef9677bb9ed581966b334a4ce81c47` |
| `4_ON_MONACO_N0_events.csv` | `4bfe04ce03292516e4987ae85fa56559b40812f9324c3d9c49fc55feab45ab1e` |
| `4_ON_MONACO_N0.log` | `50ed1c76eacd678b0006372c8ccec65c0f2b33185ecd040fcebbda2aff42f897` |
| `5_ON_INTERLAGOS_N1.csv` | `57996070dc271d7d08d2f296f1635ea2046132cc97cbe005aaa02ba03fb1ce79` |
| `5_ON_INTERLAGOS_N1_events.csv` | `fd95ddaeef4ec18ad46ebad462e79683ad159ec48302ce6a0990b444878e9338` |
| `5_ON_INTERLAGOS_N1.log` | `ad80d35eaf103d5f7c4611025bf506edf10ce3de6f5ec384192d5aa0f4b039ca` |
| `6_ON_MONACO_N1.csv` | `9527f965d37f268fd0d72cd80339f3621c6b86cd193ac36d3e1cf19beb1a95b5` |
| `6_ON_MONACO_N1_events.csv` | `fb95ab06ed0222136572a4eb222905dd03f9f942b7548d2211bdfc96920027e2` |
| `6_ON_MONACO_N1.log` | `50dedcf8623cf20ed01f4880bc151151ec7de15cf4577512a3af363219568150` |
| `7_ON_INTERLAGOS_N2.csv` | `a63391de8863ebb6486a5e55d3b3aee4cb53ddd95511fce1cc2e5a9dc300fd44` |
| `7_ON_INTERLAGOS_N2_events.csv` | `28aedae6be89a1849a2cf9996c5d1885ab024fc02a4cad3f2644d8803ed6eaf4` |
| `7_ON_INTERLAGOS_N2.log` | `5670e980bf7cb1f8aa53879c285fa3baf165eaa05077a6f9e57055be9af63884` |
| `8_ON_MONACO_N2.csv` | `0db08e01cf4b658c2722f1ce2fa2d8f66c37f054b2628c5134bc5d8daeb4a192` |
| `8_ON_MONACO_N2_events.csv` | `995dadb9c15dbde08d1acd6c6114acf88c4904cd764e86742540d02609c7eb2f` |
| `8_ON_MONACO_N2.log` | `f939594bb856bc6cd973449ede4f4b3ae3d1b762edc524fa57f8f91527898635` |
| `9_ON_INTERLAGOS_N3.csv` | `ff7f738ffad90b8f037936885aadc1f867082a642e6e852bd4c05c9b05fce91d` |
| `9_ON_INTERLAGOS_N3_events.csv` | `7ee4c2f86349f6a95385b1fc665ca80ee4f79613fca869ad75d8d7d8f274a227` |
| `9_ON_INTERLAGOS_N3.log` | `5aa00082a4856c7da455db28b7f2f2ddb05e7486b38de07ac86b0a70d7abce68` |
| `10_ON_MONACO_N3.csv` | `8ba4517e136a8e05c760e61c15fd8571b6ce02f816b06d34c4c4d80202dd6734` |
| `10_ON_MONACO_N3_events.csv` | `bde9106531d8a83508b5dae211f6148b2cfce9e8d26b0fec3c314ca1f7eac1f4` |
| `10_ON_MONACO_N3.log` | `a571fcf16476d1bf77e3f07069b4e0d13c65f843909573103e1175fdcf8b9d05` |
| `11_ON_INTERLAGOS_N4.csv` | `c50379b9e674e91c7acaec4272d893b28ec7472ebe02bb24459662fdebef1083` |
| `11_ON_INTERLAGOS_N4_events.csv` | `92b23625d9e819a5f545b37ce640ed07e6a33b09c991bada856df654f787ee49` |
| `11_ON_INTERLAGOS_N4.log` | `39859879dc33c39810ffd5d960b6baef8a0cc347751f2f2c99bf387eb536cc5d` |
| `12_ON_MONACO_N4.csv` | `5817e720edd07051afd92717dc6357ebc83707f52acd3e5229e58379c35a6b13` |
| `12_ON_MONACO_N4_events.csv` | `6167c656de4ad1b3836589e8a61e481f4b546aa5f9a8bd07f62363f848bb000b` |
| `12_ON_MONACO_N4.log` | `ad13dec5bfc5d34aa2cae38cef87c16ab3aa2d80b768e8356ae158953182e808` |

### 48 arquivos de extração

Todos os pares `base_metrics` e `realismo_metrics` têm hashes iguais entre as duas leituras. Os hashes completos estão abaixo:

| Arquivo | SHA-256 |
|---|---|
| `1_CTRL_INTERLAGOS_N0_base_metrics.json` | `3880de1e24a2a77cc32761087a46ecf5dcd78e08b75409dc6bf67c4145c1178d` |
| `1_CTRL_INTERLAGOS_N0_base_metrics_read2.json` | `3880de1e24a2a77cc32761087a46ecf5dcd78e08b75409dc6bf67c4145c1178d` |
| `1_CTRL_INTERLAGOS_N0_realismo.json` | `eeec2600cdd30c289023500a13578d6c79baf92e2c9df7b19675c090cbbbd1f9` |
| `1_CTRL_INTERLAGOS_N0_realismo_read2.json` | `eeec2600cdd30c289023500a13578d6c79baf92e2c9df7b19675c090cbbbd1f9` |
| `2_CTRL_MONACO_N0_base_metrics.json` | `25c1fdbbe93fecff5ff4df4288119347befb138b8d7b06172b8b5fa8d938cae0` |
| `2_CTRL_MONACO_N0_base_metrics_read2.json` | `25c1fdbbe93fecff5ff4df4288119347befb138b8d7b06172b8b5fa8d938cae0` |
| `2_CTRL_MONACO_N0_realismo.json` | `093bb943326e80e5456fb47da1d58138e603e4527d29a82576c8f0d79dfcf686` |
| `2_CTRL_MONACO_N0_realismo_read2.json` | `093bb943326e80e5456fb47da1d58138e603e4527d29a82576c8f0d79dfcf686` |
| `3_ON_INTERLAGOS_N0_base_metrics.json` | `5b72d29e6798661425372e96da9fa93c57dbc2a815ef22d6cd6e66e698d020c1` |
| `3_ON_INTERLAGOS_N0_base_metrics_read2.json` | `5b72d29e6798661425372e96da9fa93c57dbc2a815ef22d6cd6e66e698d020c1` |
| `3_ON_INTERLAGOS_N0_realismo.json` | `0b3754310f8d3b1ea53de974d3c0c957a8b7feec1ea46f1dc9b3642cf2ff42c0` |
| `3_ON_INTERLAGOS_N0_realismo_read2.json` | `0b3754310f8d3b1ea53de974d3c0c957a8b7feec1ea46f1dc9b3642cf2ff42c0` |
| `4_ON_MONACO_N0_base_metrics.json` | `4d4a7bda3c0ae7c1b6031b2d58be82c35f36ad0da747e1aedf8937ad8aa1c743` |
| `4_ON_MONACO_N0_base_metrics_read2.json` | `4d4a7bda3c0ae7c1b6031b2d58be82c35f36ad0da747e1aedf8937ad8aa1c743` |
| `4_ON_MONACO_N0_realismo.json` | `f9b2153977c5fb328dc4c312f19e6d8b06662d62efb9028f877db5aa530294b0` |
| `4_ON_MONACO_N0_realismo_read2.json` | `f9b2153977c5fb328dc4c312f19e6d8b06662d62efb9028f877db5aa530294b0` |
| `5_ON_INTERLAGOS_N1_base_metrics.json` | `70472002fe96c343caa0fb3322a04dbf5bf5d4ae947b7b46fc4f1e60733b584b` |
| `5_ON_INTERLAGOS_N1_base_metrics_read2.json` | `70472002fe96c343caa0fb3322a04dbf5bf5d4ae947b7b46fc4f1e60733b584b` |
| `5_ON_INTERLAGOS_N1_realismo.json` | `0b1589e4f0209540111206597759e9393d3c957607f5ed624ce95d57caeb3c01` |
| `5_ON_INTERLAGOS_N1_realismo_read2.json` | `0b1589e4f0209540111206597759e9393d3c957607f5ed624ce95d57caeb3c01` |
| `6_ON_MONACO_N1_base_metrics.json` | `d3902285c3c0a3be1eebbec58a03f76e8fb81b63bc101ea86ec558216d996972` |
| `6_ON_MONACO_N1_base_metrics_read2.json` | `d3902285c3c0a3be1eebbec58a03f76e8fb81b63bc101ea86ec558216d996972` |
| `6_ON_MONACO_N1_realismo.json` | `1caf936bf3405e6125cfdcc615370d454633d2709f50ed5d4a3feab23cafdce3` |
| `6_ON_MONACO_N1_realismo_read2.json` | `1caf936bf3405e6125cfdcc615370d454633d2709f50ed5d4a3feab23cafdce3` |
| `7_ON_INTERLAGOS_N2_base_metrics.json` | `48e73d88be52a89dc136b24dcb50e608d9391edf44207178fb295503f12c8c3c` |
| `7_ON_INTERLAGOS_N2_base_metrics_read2.json` | `48e73d88be52a89dc136b24dcb50e608d9391edf44207178fb295503f12c8c3c` |
| `7_ON_INTERLAGOS_N2_realismo.json` | `beecc86c838bcb1d8dcd4f017c472dca27a88b666093efda49ae2a8f17cadb00` |
| `7_ON_INTERLAGOS_N2_realismo_read2.json` | `beecc86c838bcb1d8dcd4f017c472dca27a88b666093efda49ae2a8f17cadb00` |
| `8_ON_MONACO_N2_base_metrics.json` | `4e6e8c71dca018b59a9d43bad5be83f5ae661038c7b1155ffc6a53eb3dc85ab4` |
| `8_ON_MONACO_N2_base_metrics_read2.json` | `4e6e8c71dca018b59a9d43bad5be83f5ae661038c7b1155ffc6a53eb3dc85ab4` |
| `8_ON_MONACO_N2_realismo.json` | `704ce512cbc0a57ecafc20e1b4df8ac524ef9a15a6772126b647efe487ddbc7a` |
| `8_ON_MONACO_N2_realismo_read2.json` | `704ce512cbc0a57ecafc20e1b4df8ac524ef9a15a6772126b647efe487ddbc7a` |
| `9_ON_INTERLAGOS_N3_base_metrics.json` | `c9bd4e27e7f2c30d3dd2f0b1a4cc55c152fc43b3ff0bfc9dc0f4bb1100a97443` |
| `9_ON_INTERLAGOS_N3_base_metrics_read2.json` | `c9bd4e27e7f2c30d3dd2f0b1a4cc55c152fc43b3ff0bfc9dc0f4bb1100a97443` |
| `9_ON_INTERLAGOS_N3_realismo.json` | `daffd1aa9dbbc37f6b342a1b9d92d2fd216bc00b37889ce1817bb4a0c87a666f` |
| `9_ON_INTERLAGOS_N3_realismo_read2.json` | `daffd1aa9dbbc37f6b342a1b9d92d2fd216bc00b37889ce1817bb4a0c87a666f` |
| `10_ON_MONACO_N3_base_metrics.json` | `e9f827f1e23788789a4e78e5387833e00579413a2d11d41080d392a978e8d4ef` |
| `10_ON_MONACO_N3_base_metrics_read2.json` | `e9f827f1e23788789a4e78e5387833e00579413a2d11d41080d392a978e8d4ef` |
| `10_ON_MONACO_N3_realismo.json` | `826331c8f86a10630c5f5134bcc105d685737a96bbf2f6221fdc760a0eac3b6a` |
| `10_ON_MONACO_N3_realismo_read2.json` | `826331c8f86a10630c5f5134bcc105d685737a96bbf2f6221fdc760a0eac3b6a` |
| `11_ON_INTERLAGOS_N4_base_metrics.json` | `f08bcc243b03b36223fbd80248f2ad07e422468cc2b9d7a847542017a60bd707` |
| `11_ON_INTERLAGOS_N4_base_metrics_read2.json` | `f08bcc243b03b36223fbd80248f2ad07e422468cc2b9d7a847542017a60bd707` |
| `11_ON_INTERLAGOS_N4_realismo.json` | `402102f43b39f94c2ffd36e189f1ee5bd2856c163bcda8e0d9951554e872abed` |
| `11_ON_INTERLAGOS_N4_realismo_read2.json` | `402102f43b39f94c2ffd36e189f1ee5bd2856c163bcda8e0d9951554e872abed` |
| `12_ON_MONACO_N4_base_metrics.json` | `4d124418d6641d5bd1155d45055751f92716252fd10630b84d89c7467c7fbf91` |
| `12_ON_MONACO_N4_base_metrics_read2.json` | `4d124418d6641d5bd1155d45055751f92716252fd10630b84d89c7467c7fbf91` |
| `12_ON_MONACO_N4_realismo.json` | `ec63b039208fa03e3b1b7044195c1a7f2624fdf686a5528a70f6c426efa97c8f` |
| `12_ON_MONACO_N4_realismo_read2.json` | `ec63b039208fa03e3b1b7044195c1a7f2624fdf686a5528a70f6c426efa97c8f` |

## 7. Encerramento

O C1 foi executado conforme o orçamento. Este relatório é staged sem commit para o veredito do dono. Não houve alteração de default. Não foi feita promoção do mecanismo. O C1-B deve ser considerado **FAIL** até decisão explícita do dono sobre a regressão de contatos e o R-2-T1 de Interlagos.

## 8. Apêndice do dono — verificação independente e closing (2026-10-30)

1. **Verificação de integridade.**

   - HEAD `36efcbb`.

   - 88 arquivos staged: 24 de corrida (12 CSVs, 12 sidecars, 12 logs), 48 JSONs de extração (dupla leitura determinística cmp=0), 3 ledgers atualizados, e o relatório de execução.

   - Zero código de produção alterado além da flag opt-in do C1-B; strays conhecidos preservados fora do stage.

   - Controles OFF 1 e 2 confirmaram identidade byte a byte contra promocao-1.

2. **Leitura científica e física do resultado.**

   - O mecanismo C1-B cumpriu com perfeição o objetivo de diagnóstico: 0 saídas expostas em 5/5 realizações ON nas duas pistas (C1P1a PASS), e colapso das saídas em reta Z_RETA (71->2 em Interlagos, 33->0 em Monaco; C1P1b PASS).

   - Contudo, a eliminação das saídas na reta manteve todos os 10 carros no asfalto em alta velocidade, provocando compressão severa do pelotão na Curva 1 (efeito funil).

   - Essa densidade causou explosão de colisões entre carros nos primeiros 60 s (S-1 mais que dobrou), estourando o limite duro de B-1 (Interlagos 3533 > 2655; Monaco 3074 > 3021), acionando o PARE de outlier em Interlagos N0 (653 vs 107) e falhando o R-2-T1 em Interlagos (58 > 46).

3. **Decisão de engenharia.**

   - **Veredito formal: FAIL.**

   - O mecanismo `--launch-steer-mute` **NÃO** é promovido para produção e permanece estritamente como opção de diagnóstico (default OFF mantido).

   - Não há alteração de baseline nem promoção de constantes.

4. **Próximo passo autorizado.**

   - Ciclo C1 encerrado.

   - Autorizada a abertura do ciclo **C2-A** (handoff do rejoin: alinhamento na volta à pista, sem simulação, usando os bytes commitados da promocao-1), conforme o PLANO_REALISMO_BOTS_1.md.
