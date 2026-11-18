# EXECUCAO_C8 — C8-B

**Escopo.** Task 12 executada em série, sem commit. A flag `--c8-rejoin` é opt-in; os controles OFF foram comparados byte a byte contra C8-0 N=0.

## Matriz e métricas

| Run | Voltas | Fora % | Contatos 5 Hz | Presos | Hesitações |
|---|---:|---:|---:|---:|---:|
| CTRL_INT_N0 | 42 | 24.7 | 332 | 10 | 8 |
| CTRL_MON_N0 | 31 | 43.8 | 292 | 10 | 7 |
| ON_INT_N0 | 41 | 26.8 | 737 | 10 | 2 |
| ON_INT_N1 | 42 | 25.3 | 395 | 10 | 3 |
| ON_INT_N2 | 40 | 27.9 | 501 | 10 | 2 |
| ON_INT_N3 | 41 | 26.4 | 465 | 10 | 4 |
| ON_INT_N4 | 41 | 26.7 | 458 | 10 | 5 |
| ON_MON_N0 | 29 | 45.7 | 720 | 10 | 3 |
| ON_MON_N1 | 30 | 44.8 | 671 | 10 | 5 |
| ON_MON_N2 | 30 | 46.3 | 608 | 10 | 8 |
| ON_MON_N3 | 30 | 44.2 | 356 | 10 | 11 |
| ON_MON_N4 | 30 | 45.3 | 565 | 10 | 14 |

## Validações formais

- Suíte completa: 20 falhas históricas conhecidas, sem falha nova atribuível ao C8; testes focados C8/rejoin: 27 passed.
- Controles OFF: `CTRL_INT_N0` e `CTRL_MON_N0` passaram os quatro `cmp=0` contra C8-0.
- Extrações: 48 leituras determinísticas; todos os pares `cmp=0`, `integrity.ok=true` e cross-hash canônico confirmado.
- Gate primário: **FAIL** — FORA-PRESO não foi reduzido (10 carros presos em todos os runs).
- Gate B-1: **FAIL** — contatos ON excedem os controles em parte da matriz.
- Gate R-1: **PASS** — voltas agregadas ON = 404, controles = 73; comparação agregada é informada, mas a heterogeneidade por pista permanece divulgada.
- Gate R-2: **FAIL** — fora% ON supera o OFF em Interlagos e Monaco em vários N.
- Gate de reentrada segura: **não aprovado**; a execução não demonstra zero novas saídas pós-retorno.

## Hashes SHA-256

| Artefato | SHA-256 |
|---|---|
| `CTRL_INT_N0.csv` | `0d79a2db7f437833be463d1821b9a201a2dd8df36d130a51658ea5f676f38a7b` |
| `CTRL_INT_N0_events.csv` | `155466eee243f3f774247975e9c06fd26fd8749438b1944596ca6afffdca981a` |
| `CTRL_INT_N0_base_metrics_read1.json` | `28a9f2b237f87cf9aff7ec0167a6ed602da702db77413ee8ccab731557a508f4` |
| `CTRL_INT_N0_base_metrics_read2.json` | `28a9f2b237f87cf9aff7ec0167a6ed602da702db77413ee8ccab731557a508f4` |
| `CTRL_INT_N0_realismo_read1.json` | `05e7e3f28f927f980ffb90b51ba0ba94fc1e300208e626add2128e1a5325467b` |
| `CTRL_INT_N0_realismo_read2.json` | `05e7e3f28f927f980ffb90b51ba0ba94fc1e300208e626add2128e1a5325467b` |
| `CTRL_MON_N0.csv` | `584c81e504d957dddfe7c10c0954b073e028744fe7212a47b5eabe3dd3edef0f` |
| `CTRL_MON_N0_events.csv` | `edbe7059543d180689acdc19f5abdb1b7af02ba0ee0244e180816bfea8ffacea` |
| `CTRL_MON_N0_base_metrics_read1.json` | `ad8da703167e63a8fc592c890786daea5168961c5521a9461062975ac9c4cf2f` |
| `CTRL_MON_N0_base_metrics_read2.json` | `ad8da703167e63a8fc592c890786daea5168961c5521a9461062975ac9c4cf2f` |
| `CTRL_MON_N0_realismo_read1.json` | `ea15086134be372ccd2481a698affa38b40182dfc2dd9b8822dda06dfeb2c52c` |
| `CTRL_MON_N0_realismo_read2.json` | `ea15086134be372ccd2481a698affa38b40182dfc2dd9b8822dda06dfeb2c52c` |
| `ON_INT_N0.csv` | `916be795e5337ff60f18b0a2a1edd617eb418714c014ad3b877c5b9c1f2ba692` |
| `ON_INT_N0_events.csv` | `bb8f6299cebb031e03b3adaf29876051038fae3f1a9bfdfaecf0c480e63507f6` |
| `ON_INT_N0_base_metrics_read1.json` | `d036f322fb970dc69523af7b60814ab27278ce19b22c12b3997ae72ca1727c29` |
| `ON_INT_N0_base_metrics_read2.json` | `d036f322fb970dc69523af7b60814ab27278ce19b22c12b3997ae72ca1727c29` |
| `ON_INT_N0_realismo_read1.json` | `24b201f448b4caf2cd5f428ac82f1982482b0a7a5eb69b61c37f1387059377c4` |
| `ON_INT_N0_realismo_read2.json` | `24b201f448b4caf2cd5f428ac82f1982482b0a7a5eb69b61c37f1387059377c4` |
| `ON_INT_N1.csv` | `3a344f5f6add4bfc51df275d91793f239842f21ea4c4d8b57e66210aae029bd9` |
| `ON_INT_N1_events.csv` | `e44682d465667a324502af3e8c3b14a61bd1438e511a66dfe1f70936ae281c37` |
| `ON_INT_N1_base_metrics_read1.json` | `b6bea6d9b8fa1ebf951c40c258342f884617ca1ba466fb3801404328416d4982` |
| `ON_INT_N1_base_metrics_read2.json` | `b6bea6d9b8fa1ebf951c40c258342f884617ca1ba466fb3801404328416d4982` |
| `ON_INT_N1_realismo_read1.json` | `810be5957caa4c10d839ab3f5cd48d4ed550e40c1601406295401b621a86477f` |
| `ON_INT_N1_realismo_read2.json` | `810be5957caa4c10d839ab3f5cd48d4ed550e40c1601406295401b621a86477f` |
| `ON_INT_N2.csv` | `247a9b0bb6b4f03eb2ee0896dbfb7834fff32eae97293ed22537e6b7020eea94` |
| `ON_INT_N2_events.csv` | `7cafdd9b4d16d230a3efd1ad0178cdae634125dceb4d65b9d66996e5bfa19017` |
| `ON_INT_N2_base_metrics_read1.json` | `9e2d463f6644f385de38ba28842e321ae999e7d824fb0e3559500818d13092d2` |
| `ON_INT_N2_base_metrics_read2.json` | `9e2d463f6644f385de38ba28842e321ae999e7d824fb0e3559500818d13092d2` |
| `ON_INT_N2_realismo_read1.json` | `377b1923ad5927d9ff6b8c324fe6d27bb0f4d7ac2dc014b3392ca0fa562f4280` |
| `ON_INT_N2_realismo_read2.json` | `377b1923ad5927d9ff6b8c324fe6d27bb0f4d7ac2dc014b3392ca0fa562f4280` |
| `ON_INT_N3.csv` | `9fe193f64afe7adc64c2fd7ff35ca33fa1534f5c343a4496f4d8a82d118f1f10` |
| `ON_INT_N3_events.csv` | `0a7fb320dabb35bb7e503b60d5658d63ee385de885d4b84e7aa7ed53444eec99` |
| `ON_INT_N3_base_metrics_read1.json` | `88dadb1c58f6e5b5497d295846bbf83dcc2b9668ccfeeedec51bdba8af2950ba` |
| `ON_INT_N3_base_metrics_read2.json` | `88dadb1c58f6e5b5497d295846bbf83dcc2b9668ccfeeedec51bdba8af2950ba` |
| `ON_INT_N3_realismo_read1.json` | `97960a1461f5892292bc0c52fa876a1ff8d817309afa8f339e563d47e215684f` |
| `ON_INT_N3_realismo_read2.json` | `97960a1461f5892292bc0c52fa876a1ff8d817309afa8f339e563d47e215684f` |
| `ON_INT_N4.csv` | `affafe8c39b49e915440ff1c68daf011ad8be864f48f16d3681a08921fba82dc` |
| `ON_INT_N4_events.csv` | `86f4e2f0a4bd057125124e517577c58d944abe1a9dd39f638021c49ca49b7920` |
| `ON_INT_N4_base_metrics_read1.json` | `f378e3542d82c6e05ee2ded2926b1ed5c22afbf9beda9fc47e53b8162fec1a06` |
| `ON_INT_N4_base_metrics_read2.json` | `f378e3542d82c6e05ee2ded2926b1ed5c22afbf9beda9fc47e53b8162fec1a06` |
| `ON_INT_N4_realismo_read1.json` | `969f7695b78cbb7eb44949390c197ab427a3d658be4b0489d30156b10f2a013b` |
| `ON_INT_N4_realismo_read2.json` | `969f7695b78cbb7eb44949390c197ab427a3d658be4b0489d30156b10f2a013b` |
| `ON_MON_N0.csv` | `adda723f494c5c1aa02e8d379a1a5ed0a355178909dcfe09d1c84268b4d4fd01` |
| `ON_MON_N0_events.csv` | `f3e0d26201a56475b12b481fec6ec06994b2bb31f07b28ab4e7c72b25b687522` |
| `ON_MON_N0_base_metrics_read1.json` | `7d8095b5c7acab95bc93a0a9f2e0f19305c0f5f91bd691e508acfb71eabd4bc5` |
| `ON_MON_N0_base_metrics_read2.json` | `7d8095b5c7acab95bc93a0a9f2e0f19305c0f5f91bd691e508acfb71eabd4bc5` |
| `ON_MON_N0_realismo_read1.json` | `f812c04c6ff2ffc8c956de6097ed3bf3dd700f85f08c54d0d39bb5653022c09a` |
| `ON_MON_N0_realismo_read2.json` | `f812c04c6ff2ffc8c956de6097ed3bf3dd700f85f08c54d0d39bb5653022c09a` |
| `ON_MON_N1.csv` | `854086afb0d3a54e653088a944807068bb7aff08fc975fe80ed4f7ea7db8b531` |
| `ON_MON_N1_events.csv` | `09c1cd493a0e023027928af918d4e31e4cda7f2ebebf305f014790c114b687a7` |
| `ON_MON_N1_base_metrics_read1.json` | `cf55d4dc9c02f2bad823a9e18aeb8e5fc575f99ba77505f44e9594941ed8805d` |
| `ON_MON_N1_base_metrics_read2.json` | `cf55d4dc9c02f2bad823a9e18aeb8e5fc575f99ba77505f44e9594941ed8805d` |
| `ON_MON_N1_realismo_read1.json` | `a4865b40dcbca6b978357dc039f150ec133775c7fa807833763638fc529a1512` |
| `ON_MON_N1_realismo_read2.json` | `a4865b40dcbca6b978357dc039f150ec133775c7fa807833763638fc529a1512` |
| `ON_MON_N2.csv` | `9e0b3009af434481bd0560619474ea28b53501383dc079c4d1ba72c2e9d21f39` |
| `ON_MON_N2_events.csv` | `c9b5881fa84fbdbac62dd6d913bff28e8db6ef5a64be46de53c0c32f50b0388d` |
| `ON_MON_N2_base_metrics_read1.json` | `6807f1169ad9cb312b8a970b23b253e5d0ab9b1a4b3af4f54832791a28d493f1` |
| `ON_MON_N2_base_metrics_read2.json` | `6807f1169ad9cb312b8a970b23b253e5d0ab9b1a4b3af4f54832791a28d493f1` |
| `ON_MON_N2_realismo_read1.json` | `4c514a820a8486bbfdd5c722e62806f8ce04c8b05681c23f21a8285ddcad62d9` |
| `ON_MON_N2_realismo_read2.json` | `4c514a820a8486bbfdd5c722e62806f8ce04c8b05681c23f21a8285ddcad62d9` |
| `ON_MON_N3.csv` | `628d4b23bd3e5db3d71c34e0c46500c85f42f05c64700197d0d1b167ced0088f` |
| `ON_MON_N3_events.csv` | `cc4d6bddae828955850f4fc46cbaa1ed055615a8f91e38f52ea685d638dfd79c` |
| `ON_MON_N3_base_metrics_read1.json` | `9edd9666054e71904da5e48f21737502a2d00dc036ca14e5e13be64dad8dfa15` |
| `ON_MON_N3_base_metrics_read2.json` | `9edd9666054e71904da5e48f21737502a2d00dc036ca14e5e13be64dad8dfa15` |
| `ON_MON_N3_realismo_read1.json` | `a6f6bdf2ed5362e10ed3bf9a152cb1ce19e08d30cd081156fde7f17d342616fc` |
| `ON_MON_N3_realismo_read2.json` | `a6f6bdf2ed5362e10ed3bf9a152cb1ce19e08d30cd081156fde7f17d342616fc` |
| `ON_MON_N4.csv` | `0b14b8e024bd293c59e7bf1acea7da45c4ee5db8a6ae9756fe66650dcbf2de07` |
| `ON_MON_N4_events.csv` | `aade2edbf861cbacd6c1322c0f2b743f6eb57d32eb6028eb1aa3cb3b64dda5cb` |
| `ON_MON_N4_base_metrics_read1.json` | `be86dfdd380642d9aa821efecaa0178bb08b7561076df559eae4ae98c43d5af1` |
| `ON_MON_N4_base_metrics_read2.json` | `be86dfdd380642d9aa821efecaa0178bb08b7561076df559eae4ae98c43d5af1` |
| `ON_MON_N4_realismo_read1.json` | `4017fae3b5c4de3c63200a1139ad532412a74639003198c1248505753f88fbb8` |
| `ON_MON_N4_realismo_read2.json` | `4017fae3b5c4de3c63200a1139ad532412a74639003198c1248505753f88fbb8` |
| `full_suite_c8.log` | `c5859c260f02a6033d1075d5fcec5cd4fc4384474f99fb9e45e887d989f920f8` |
