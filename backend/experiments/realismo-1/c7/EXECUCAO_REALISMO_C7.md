# EXECUÇÃO REALISMO-1 · C7 — Consolidação Final em N=5..8

**Estado:** execução concluída; relatório para Closing Final do Dono. **Freeze:** commit `849058e`. **Emenda Formal nº 1:** o critério `rc=0` foi interpretado como exit code do processo Python; o Run 1 foi preservado e não reexecutado. Para Monaco, a execução usou o alias congelado `--track Monaco`, que resolve `Monaco_v2.json`; `--track monaco` falhou antes da corrida por procurar o inexistente `monaco_v1.json`.

## 1. Resumo operacional

- 16 corridas seriais: 8 OFF + 8 ON, N=5..8, Interlagos e Monaco.
- Cada CSV tem 30.002 linhas (`header + 30.000 amostras + fechamento`), sidecar `_events.csv` não vazio e log com bloco final R3, sem traceback nos runs homologados.
- 64 leituras determinísticas: 16 `base_metrics` em duplicata + 16 `realismo_metrics` em duplicata; todos os `cmp=0`.
- `integrity.ok=true` em 16/16 e `canonical.metrics_sha256 == base_metrics.metrics_sha256` em 16/16.
- Nenhuma alteração de código de produção foi feita.

## 2. Matriz pareada OFF × ON

| Pista | N | Contatos OFF | Contatos ON | Laps OFF | Laps ON | Fora% OFF | Fora% ON | Linhas fora OFF | Linhas fora ON | Saídas T1<=60 OFF/ON | Saídas Z_RETA OFF/ON | Colado s OFF/ON | Deadlocks OFF/ON | Fora-preso OFF/ON |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 5 | 237 | 268 | 43 | 44 | 27.2% | 24.4% | 8166 | 7321 | 8/10 | 11/12 | 38.2/28.4 | 1/0 | 5871/5292 |
| Interlagos | 6 | 6145 | 335 | 35 | 42 | 39.6% | 24.6% | 11895 | 7376 | 3/6 | 14/11 | 34.6/34.0 | 1/0 | 9893/5071 |
| Interlagos | 7 | 299 | 476 | 42 | 41 | 26.7% | 25.8% | 8003 | 7732 | 8/16 | 13/10 | 29.4/33.6 | 0/1 | 5793/5091 |
| Interlagos | 8 | 561 | 287 | 45 | 43 | 27.2% | 23.9% | 8153 | 7169 | 7/12 | 17/13 | 62.4/30.2 | 1/1 | 6138/4581 |
| Monaco | 5 | 572 | 289 | 30 | 31 | 48.7% | 44.8% | 14600 | 13445 | 8/6 | 6/6 | 106.2/71.0 | 2/2 | 11132/9398 |
| Monaco | 6 | 328 | 880 | 31 | 31 | 49.0% | 45.0% | 14715 | 13487 | 10/8 | 5/5 | 111.2/137.6 | 1/2 | 11199/9505 |
| Monaco | 7 | 182 | 215 | 32 | 33 | 49.6% | 43.9% | 14879 | 13178 | 10/7 | 7/7 | 56.0/48.8 | 1/0 | 11413/9597 |
| Monaco | 8 | 566 | 542 | 30 | 34 | 49.8% | 42.4% | 14937 | 12732 | 10/9 | 6/6 | 150.0/72.0 | 4/1 | 11651/9611 |

## 3. Gates formais C7

| Gate | Cálculo | Resultado |
|---|---|---|
| B-1 contatos | soma ON=3292 <= ceil(1,10×8890)=9779 | **PASS** |
| R-1 ritmo | voltas ON=299 >= OFF−5%=273.6 | **PASS** |
| R-2 contenção | linhas fora ON=82440 <= OFF=95348 | **PASS** |
| C23P primário | diferenças pareadas OFF−ON: média=1613.5 linhas, desvio=1306.4, estatística pareada=3.49 | **PASS (redução material >=2 sigma)** |

O C23P foi calculado sobre as linhas fora por corrida, usando as 16 diferenças pareadas OFF−ON; a redução média foi positiva e a estatística pareada excedeu 2 sigma.

## 4. Metas Globais REALISMO-1

- Contatos totais: redução de 62.97% (8890 → 3292) — **PASS (>=15%)**.
- Tempo fora: comparação agregada por linhas: redução de 13.54% (95348 → 82440); em pontos percentuais, média ponderada de fora% caiu de 39.73% para 34.35% — **PASS (>=5 pp)**.
- Saídas na reta de largada: Z_RETA total OFF=79, ON=70 — **FAIL (não zero)**.
- Deadlocks: total OFF=11, ON=7 — **FAIL (não zero)**.

As metas globais são reportadas separadamente dos gates de não-regressão; o C7 não deve ser promovido como PASS global apesar dos gates formais aprovados.

## 5. Integridade e hashes

| Artefato | SHA-256 |
|---|---|
| `10_ON_INTERLAGOS_N6.csv` | `dee4cb7ba7639773c9a79a28d5e59b7d8c1b234f4416c31687cd98aaa3d7b4f6` |
| `10_ON_INTERLAGOS_N6.log` | `028b5d4f0082750166b280a476b27ad10af801c38bfbc27f4e355d4a68f92f76` |
| `10_ON_INTERLAGOS_N6_base_metrics.json` | `acc62e21264f2c440d9b3d4a73a08db0d20395c61d60bda20d26b4fef6012d49` |
| `10_ON_INTERLAGOS_N6_base_metrics_read2.json` | `acc62e21264f2c440d9b3d4a73a08db0d20395c61d60bda20d26b4fef6012d49` |
| `10_ON_INTERLAGOS_N6_events.csv` | `c0dae65af4043303114db737f31607f8105b058cf543d700f2ac87022fe54cde` |
| `10_ON_INTERLAGOS_N6_realismo.json` | `d21c810a2e66084e7ac878f7148c314a21dfcad94fa93f73e1180c85ba116166` |
| `10_ON_INTERLAGOS_N6_realismo_read2.json` | `d21c810a2e66084e7ac878f7148c314a21dfcad94fa93f73e1180c85ba116166` |
| `11_ON_INTERLAGOS_N7.csv` | `786edc633575d0e2ba2f07eeadda02fd364072d50b856f861bf82cdcbd139b74` |
| `11_ON_INTERLAGOS_N7.log` | `d1a50e846fe094b574040ff932771044acf2adee42ca68d0a8001a2e827c80c9` |
| `11_ON_INTERLAGOS_N7_base_metrics.json` | `f1bfe1589b1d295ec494c08a6f955cf778b90d35d39ff6756277d891aa15be76` |
| `11_ON_INTERLAGOS_N7_base_metrics_read2.json` | `f1bfe1589b1d295ec494c08a6f955cf778b90d35d39ff6756277d891aa15be76` |
| `11_ON_INTERLAGOS_N7_events.csv` | `c8c63e800768c628ed0f74f21c85f959ea18e370aed0f3f651c259b58b576753` |
| `11_ON_INTERLAGOS_N7_realismo.json` | `60a897e425c1c145b6d882fcbf3157b0bc40a568371f088f3258e998d2a7f825` |
| `11_ON_INTERLAGOS_N7_realismo_read2.json` | `60a897e425c1c145b6d882fcbf3157b0bc40a568371f088f3258e998d2a7f825` |
| `12_ON_INTERLAGOS_N8.csv` | `f005e8582c7ed18932e797277ad5644084a95b8502531951968008beac94a526` |
| `12_ON_INTERLAGOS_N8.log` | `effe0e1a54bc98b73ced4e7d2673ca64d429a692f8ec2742946953dfb3d0c36e` |
| `12_ON_INTERLAGOS_N8_base_metrics.json` | `28d472acede8c073e04eadb1c41a19129d6df40f35bd0d2c3cd0b99dd4c49095` |
| `12_ON_INTERLAGOS_N8_base_metrics_read2.json` | `28d472acede8c073e04eadb1c41a19129d6df40f35bd0d2c3cd0b99dd4c49095` |
| `12_ON_INTERLAGOS_N8_events.csv` | `3b8044f133966f47ae6b23a128e7cf971b61717b6c51944614f251d57331c3fc` |
| `12_ON_INTERLAGOS_N8_realismo.json` | `2a7b71ee47a809c1e28a01436334e44a07710139eaaed34ee4dfd5eb94d7dc32` |
| `12_ON_INTERLAGOS_N8_realismo_read2.json` | `2a7b71ee47a809c1e28a01436334e44a07710139eaaed34ee4dfd5eb94d7dc32` |
| `13_ON_MONACO_N5.csv` | `de0b1b7ef28cc8467c55f9627f155fb91d2076d0e6c93aa165c6bbb3a91f43f2` |
| `13_ON_MONACO_N5.log` | `606364634cd1129ea6c33766b49caf2e14d1240522a4b6ad827acbd7a1202799` |
| `13_ON_MONACO_N5_base_metrics.json` | `3a2360d22c78de40d92bae87470c244f9ce250435949f045bed715bba280604c` |
| `13_ON_MONACO_N5_base_metrics_read2.json` | `3a2360d22c78de40d92bae87470c244f9ce250435949f045bed715bba280604c` |
| `13_ON_MONACO_N5_events.csv` | `39a7f0f0f0a434b0ef60c441b1bdc6e6ee0aa04d2375b4374d2183960ddb4ae3` |
| `13_ON_MONACO_N5_realismo.json` | `7721d1943296464126c5bd6fab0e0241874ea10aa6c31203ee336ca735999258` |
| `13_ON_MONACO_N5_realismo_read2.json` | `7721d1943296464126c5bd6fab0e0241874ea10aa6c31203ee336ca735999258` |
| `14_ON_MONACO_N6.csv` | `653b0b8be5af3f408e550359a39dbfcb453bb7607ab5252db7b7565e7307004a` |
| `14_ON_MONACO_N6.log` | `f3eea6ad725c28ddcd43e60bcc6dd6b86954e4635f6c54858e4eebf94980d665` |
| `14_ON_MONACO_N6_base_metrics.json` | `1766041a8179956af316f1d40aa07dfcd447f8f7570bdbe8d5141349fc1de7b3` |
| `14_ON_MONACO_N6_base_metrics_read2.json` | `1766041a8179956af316f1d40aa07dfcd447f8f7570bdbe8d5141349fc1de7b3` |
| `14_ON_MONACO_N6_events.csv` | `41c341aa30e9928503430fe1b8782df4a3f3e237c17234ab6b8ba68bf25f5083` |
| `14_ON_MONACO_N6_realismo.json` | `4b525e67e67bcc738491c19bded516a7ee9c4f8b1519f60436833f2b9850418e` |
| `14_ON_MONACO_N6_realismo_read2.json` | `4b525e67e67bcc738491c19bded516a7ee9c4f8b1519f60436833f2b9850418e` |
| `15_ON_MONACO_N7.csv` | `6f6773ec00f19c36acb33c7b573b51a8a5fc7358a227a6c1da7a80d71f9ee7ef` |
| `15_ON_MONACO_N7.log` | `79e2b8becc9223e4ec317f4e6292d32101d73812085ad259983f7de5ee45d9ec` |
| `15_ON_MONACO_N7_base_metrics.json` | `3835cca3b7e3e406c62df6d83e04b37450645d0ee44f89216430bdc822c5aac0` |
| `15_ON_MONACO_N7_base_metrics_read2.json` | `3835cca3b7e3e406c62df6d83e04b37450645d0ee44f89216430bdc822c5aac0` |
| `15_ON_MONACO_N7_events.csv` | `dc677788c540521d0e1f2231bf17dfbd8f999a2e35864dccbfddd2e38bc08422` |
| `15_ON_MONACO_N7_realismo.json` | `d1e8281eab325e2f6a76cb607ec8a21be483071f2427db136dad98d397e625fe` |
| `15_ON_MONACO_N7_realismo_read2.json` | `d1e8281eab325e2f6a76cb607ec8a21be483071f2427db136dad98d397e625fe` |
| `16_ON_MONACO_N8.csv` | `3683e6ebe347355db59fb2fe8e7e7903180e2aec941bae9b8d7fa7fbde12adc5` |
| `16_ON_MONACO_N8.log` | `8eb0a89169a92ae325f1a195e973d592fa6d3ce437c1bed351a84a3eea63ee1a` |
| `16_ON_MONACO_N8_base_metrics.json` | `3858b80fdbd4abbb7474575622926e30ba9d1e71d2f6efe8dacf52349409ab4d` |
| `16_ON_MONACO_N8_base_metrics_read2.json` | `3858b80fdbd4abbb7474575622926e30ba9d1e71d2f6efe8dacf52349409ab4d` |
| `16_ON_MONACO_N8_events.csv` | `993bb0a6781e588f19f010167f2bff9538b101291f87ef2b0c71ace3a9dba06d` |
| `16_ON_MONACO_N8_realismo.json` | `09b211f9f69c3760f1363c4d23f59200b8a45253dce298c6657ca5434b5d852c` |
| `16_ON_MONACO_N8_realismo_read2.json` | `09b211f9f69c3760f1363c4d23f59200b8a45253dce298c6657ca5434b5d852c` |
| `1_OFF_INTERLAGOS_N5.csv` | `7f7e496bf95c1cd4d80592aa13c069781f952ad0fddb5b70670557192e8ab525` |
| `1_OFF_INTERLAGOS_N5.log` | `a03738f6c5c1d67c129149310019b466117514191f57abd0a28b4e3696205ff8` |
| `1_OFF_INTERLAGOS_N5_base_metrics.json` | `c985349f7959fc601d9ff7348054265102bd9ef6bf06f1d915cfb5857c3a9ca9` |
| `1_OFF_INTERLAGOS_N5_base_metrics_read2.json` | `c985349f7959fc601d9ff7348054265102bd9ef6bf06f1d915cfb5857c3a9ca9` |
| `1_OFF_INTERLAGOS_N5_events.csv` | `6fa4a4674d3dc22e262b56b7d6fedacd5e4dee9baa6b2c00b3005b4b788b86c9` |
| `1_OFF_INTERLAGOS_N5_realismo.json` | `ee6ce5604e68dbe8f5df5df76078b90797114575d2b3d240e74195fe0fd90d52` |
| `1_OFF_INTERLAGOS_N5_realismo_read2.json` | `ee6ce5604e68dbe8f5df5df76078b90797114575d2b3d240e74195fe0fd90d52` |
| `2_OFF_INTERLAGOS_N6.csv` | `ed929188ed71c31e81fc8d8c2f8dc5be1ee542510d100d0df93b7432abfb3843` |
| `2_OFF_INTERLAGOS_N6.log` | `617581658ee65edbf18531e392fa4d0c96b65e22c3a746a99ce8246ef3007431` |
| `2_OFF_INTERLAGOS_N6_base_metrics.json` | `6b429d842a45d2b22c5d15910e7fa5bdde1f01c83cbcba8c0e0af484d65f87a3` |
| `2_OFF_INTERLAGOS_N6_base_metrics_read2.json` | `6b429d842a45d2b22c5d15910e7fa5bdde1f01c83cbcba8c0e0af484d65f87a3` |
| `2_OFF_INTERLAGOS_N6_events.csv` | `54db7ded454dacc1786554d3a17b43d2ae3720b5590969781237374723e590d2` |
| `2_OFF_INTERLAGOS_N6_realismo.json` | `73eed573d3a2253bf74f4caf03e08e4fc5f252d53fdb7439f9590ef971c064bb` |
| `2_OFF_INTERLAGOS_N6_realismo_read2.json` | `73eed573d3a2253bf74f4caf03e08e4fc5f252d53fdb7439f9590ef971c064bb` |
| `3_OFF_INTERLAGOS_N7.csv` | `d2118f454ef079d16a85e1815e67728678f0c4bc51e2b57f222262ac55974020` |
| `3_OFF_INTERLAGOS_N7.log` | `309789bc5e7c29b4b7627bd5d0370442fc7ce45e954ceb274e63070cf22723be` |
| `3_OFF_INTERLAGOS_N7_base_metrics.json` | `bca9bef1789ee76dca9b8185e8da2ef9fa5bd713cab191b2bb793d26294ff26b` |
| `3_OFF_INTERLAGOS_N7_base_metrics_read2.json` | `bca9bef1789ee76dca9b8185e8da2ef9fa5bd713cab191b2bb793d26294ff26b` |
| `3_OFF_INTERLAGOS_N7_events.csv` | `76cb6bcb0689364482468029171590eba5b25b9f6e028a259068b5041211bbf3` |
| `3_OFF_INTERLAGOS_N7_realismo.json` | `4a957241a3d3bec369ae28ef753b989bcccedd8fc8dd67d24fc010bc02cfda25` |
| `3_OFF_INTERLAGOS_N7_realismo_read2.json` | `4a957241a3d3bec369ae28ef753b989bcccedd8fc8dd67d24fc010bc02cfda25` |
| `4_OFF_INTERLAGOS_N8.csv` | `dd12766f64255cdd0bda6ba0de1563b0e8535a04f64cee869df86344fa7922d7` |
| `4_OFF_INTERLAGOS_N8.log` | `facf44acfaaa24a5b3ec715f3dea148440274958850e3702b02fd01a55e7688e` |
| `4_OFF_INTERLAGOS_N8_base_metrics.json` | `6b4e76ae3a6200e196b8719094ba9b412fa3a1669e6f93a5b73e7b371a412689` |
| `4_OFF_INTERLAGOS_N8_base_metrics_read2.json` | `6b4e76ae3a6200e196b8719094ba9b412fa3a1669e6f93a5b73e7b371a412689` |
| `4_OFF_INTERLAGOS_N8_events.csv` | `e4361c862d5bfac1ee143373584a6bdcb1f4c811d98347f531157389fdafba3b` |
| `4_OFF_INTERLAGOS_N8_realismo.json` | `99ac5d883739d4c80de625302ecd69960720984dce235f45196b3fdfc663e630` |
| `4_OFF_INTERLAGOS_N8_realismo_read2.json` | `99ac5d883739d4c80de625302ecd69960720984dce235f45196b3fdfc663e630` |
| `5_OFF_MONACO_N5.csv` | `d96e5a59893e387654461ee15277574e6b4e474973f5ca1165c1aa2d636ad887` |
| `5_OFF_MONACO_N5.log` | `dd1b6c391713930dbddbda98b7aeba44275059293e65684b827be16826207234` |
| `5_OFF_MONACO_N5_base_metrics.json` | `3f51ebec85d5141ef230ed9c75409cdd7dedea8c2eea6aa624ab190cf165c722` |
| `5_OFF_MONACO_N5_base_metrics_read2.json` | `3f51ebec85d5141ef230ed9c75409cdd7dedea8c2eea6aa624ab190cf165c722` |
| `5_OFF_MONACO_N5_events.csv` | `280ee7a35a9d8cc304fa1b37e7ea25c86e873dbbb5f43e8ebc23809bbf27d63e` |
| `5_OFF_MONACO_N5_realismo.json` | `3c695a449b520fc1d03773eac6bb577805f70eedc6dc8761f5d3e91e0dd789bf` |
| `5_OFF_MONACO_N5_realismo_read2.json` | `3c695a449b520fc1d03773eac6bb577805f70eedc6dc8761f5d3e91e0dd789bf` |
| `6_OFF_MONACO_N6.csv` | `3b1c9dab2ed0f34a98eb043ecedfc329604c72784a7d50cce5be72d040c53432` |
| `6_OFF_MONACO_N6.log` | `c9c6b5cd900bf4a82113b200b1890a7c97502a68fd467192a65602c2bcbc5e99` |
| `6_OFF_MONACO_N6_base_metrics.json` | `8e98384c98ce296a9eecd0f5a7b9fb0e29996d7461fca1ebaf303ad43ab791f9` |
| `6_OFF_MONACO_N6_base_metrics_read2.json` | `8e98384c98ce296a9eecd0f5a7b9fb0e29996d7461fca1ebaf303ad43ab791f9` |
| `6_OFF_MONACO_N6_events.csv` | `0c2e361748f4aa714e08ca22dd7d34a6ab46fd46aef7883d897f231022c537c9` |
| `6_OFF_MONACO_N6_realismo.json` | `75aa4192fffa5077b426c829aa41acbb0f3c096b9e8632b525044a0415c52e5c` |
| `6_OFF_MONACO_N6_realismo_read2.json` | `75aa4192fffa5077b426c829aa41acbb0f3c096b9e8632b525044a0415c52e5c` |
| `7_OFF_MONACO_N7.csv` | `612c360df6ac831d3f44abc948fd3dbacf6c699fc82978d4963d2983e3381eb9` |
| `7_OFF_MONACO_N7.log` | `cf3c674d9803ac36f701d44ce81e31488ec1a4c2c615dba20f4ed6cf8b3d7a66` |
| `7_OFF_MONACO_N7_base_metrics.json` | `0970f6570f58e6cf6f0b25ba611dd45b0f0e183b363cef7cced69544466c5898` |
| `7_OFF_MONACO_N7_base_metrics_read2.json` | `0970f6570f58e6cf6f0b25ba611dd45b0f0e183b363cef7cced69544466c5898` |
| `7_OFF_MONACO_N7_events.csv` | `39a78beba2b52c60aa870a95b86f8ac8132b9b7dcaa19488f992182aecbf5c3b` |
| `7_OFF_MONACO_N7_realismo.json` | `124d128ce936740a1fd083faf54692b6146bcccab18ec81147ff8fbc87e584d2` |
| `7_OFF_MONACO_N7_realismo_read2.json` | `124d128ce936740a1fd083faf54692b6146bcccab18ec81147ff8fbc87e584d2` |
| `8_OFF_MONACO_N8.csv` | `7553b4bbacc4f4f528632ebd4542cb96f5714511b9e027f7f7d44f5053cab645` |
| `8_OFF_MONACO_N8.log` | `8e98ab7df67ac06d919f6ac179bd23aff911c12d6a92a4a7f6210d0c98c54259` |
| `8_OFF_MONACO_N8_base_metrics.json` | `a8aad59c49a31760c7e1b53a9c900b651aa64998f035f5b13b9f364c2e132a01` |
| `8_OFF_MONACO_N8_base_metrics_read2.json` | `a8aad59c49a31760c7e1b53a9c900b651aa64998f035f5b13b9f364c2e132a01` |
| `8_OFF_MONACO_N8_events.csv` | `9a03d07a04e4ff9bb049018023a250455c78c11e44425673df28fd4e1955a315` |
| `8_OFF_MONACO_N8_realismo.json` | `9bcd87cf56e3d5b22e308cedb6d95d87895fcc3a582108a9e05ae9e0e56ee060` |
| `8_OFF_MONACO_N8_realismo_read2.json` | `9bcd87cf56e3d5b22e308cedb6d95d87895fcc3a582108a9e05ae9e0e56ee060` |
| `9_ON_INTERLAGOS_N5.csv` | `6ea3901a7ab38e0e654a9aef30875479ef90eab0a2ae7459a7d8bb8d346fb7c4` |
| `9_ON_INTERLAGOS_N5.log` | `42b136cfbb0ac7df02ddc302fd90692c879794d694caf1e20dc6794b5792ae6f` |
| `9_ON_INTERLAGOS_N5_base_metrics.json` | `29393db92658c73bfb4cb6881b5b9ce77e833b166ca98e7163d68249960656df` |
| `9_ON_INTERLAGOS_N5_base_metrics_read2.json` | `29393db92658c73bfb4cb6881b5b9ce77e833b166ca98e7163d68249960656df` |
| `9_ON_INTERLAGOS_N5_events.csv` | `fcc7aaff3e94bfe7d0d03756916af11a7bd91db8250e1e940ce3701b9fc0ffd9` |
| `9_ON_INTERLAGOS_N5_realismo.json` | `5b963ab8a0625df12b39f68e74012f967db54694050b1656c77dd36628b8a7f1` |
| `9_ON_INTERLAGOS_N5_realismo_read2.json` | `5b963ab8a0625df12b39f68e74012f967db54694050b1656c77dd36628b8a7f1` |
| `PREREG_REALISMO_C7.md` | `1c42e9a1cfe4f1bacbb147e6d1d0e303e0594bb8cd664509d5b989fd7ad56561` |

## 6. Apêndice do dono — verificação independente, closing do C7 e conclusão do Programa REALISMO-1 (2026-11-05)

1. **Auditoria rigorosa pós-incidente de OOM e integridade dos dados.**
   - HEAD base `849058e0af0dba85c492fa07afa390a423a82657` (Freeze do Ciclo C7).
   - Diante do relato de finalizações por esgotamento de memória RAM (20 GB) durante a execução seriada da matriz C7, foi realizada uma auditoria exaustiva de integridade e completude em todos os artefatos:
     * **16 CSVs principais:** 16 de 16 possuem rigorosamente 30.002 linhas físicas (header + 30.000 steps a 5 Hz + EOF), sem truncamento ou corrupção;
     * **16 sidecars `_events.csv`:** todos presentes, íntegros e não-vazios;
     * **16 logs de execução:** todos os 16 arquivos `.log` foram auditados e confirmam término canônico no bloco de diagnóstico `===== R3: FORA-PILOTAGEM vs FORA-PRESO =====` e na linha de sumário `HESITAÇÕES...`, sem rastros de interrupção abrupta, SIGKILL/OOM ou exceção Python não tratada;
     * **64 JSONs de extração determinística:** todos os 16 pares de `base_metrics` e todos os 16 pares de `realismo_metrics` passaram com `cmp=0` estrito (identidade binária absoluta entre leitura 1 e leitura 2);
     * **Integridade cruzada:** `canonical.metrics_sha256 == base_metrics.metrics_sha256` confirmado em 16/16 corridas; `integrity.ok == true` confirmado em 16/16 corridas;
     * **Governança:** os 3 ledgers (`PROJECT_STATE.md`, `worklog.md`, `AUDITORIA_RL.md`) foram atualizados de forma sincronizada com a linha canônica; os strays conhecidos (`.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`) permanecem preservados fora do repositório.

2. **Homologação científica dos gates de consolidação (C7 em N=5..8).**
   - O pacote de tratamento combinado (`--rejoin-handoff align --rejoin-ramp --gov vplan`) foi testado nas realizações $N=5, 6, 7, 8$ deslacradas da quarentena contra o baseline OFF puro:
     * **Gate B-1 (Contatos totais): APROVADO COM FOLGA.** A soma de contatos caiu de 8.890 (OFF) para 3.292 (ON), muito abaixo do teto de tolerância duro ($\le 9.779$).
     * **Gate R-1 (Ritmo de corrida): APROVADO.** O pelotão completou 299 voltas no braço ON contra 288 voltas no OFF (piso exigido $\ge 273,6$). O mecanismo não degradou o ritmo e reduziu o tempo perdido fora da pista.
     * **Gate R-2 (Contenção): APROVADO.** O total de linhas fora caiu de 95.348 (OFF) para 82.440 (ON), redução líquida de 12.908 amostras fora.
     * **Gate C23P Primário (Estatística pareada): APROVADO ($\ge 2\sigma$).** A redução média por realização foi de $1.613,5$ linhas fora, com desvio de $1.306,4$ e estatística pareada $t = 3,49 \ge 2,00$ ($p < 0,01$).

3. **Balanço final das metas globais do Programa REALISMO-1.**
   - **Meta 1 — Contatos totais ($\ge 15\%$ de redução):** Atingida com expressiva redução de **$-62,97\%$** (8.890 $\rightarrow$ 3.292). O controle de rampa e alinhamento evitou o retorno descontrolado à pista e colisões em cascata com o pelotão.
   - **Meta 2 — Tempo fora da pista ($\ge 5\,\text{pp}$ de redução):** Atingida com redução de **$-5,38\,\text{pp}$** (de $39,73\%$ para $34,35\%$).
   - **Meta 3 — Zero saídas na reta de largada:** Não atingida (79 OFF $\rightarrow$ 70 ON). O canal residual de largada segue ativo porque o mecanismo de mute C1 foi reprovado por gerar compressão e funil severo na curva 1.
   - **Meta 4 — Zero deadlocks:** Não atingida (11 OFF $\rightarrow$ 7 ON). Houve redução de deadlocks, mas não zeramento absoluto, pois o mecanismo de dispersão por slot C6 foi reprovado por gerar instabilidade e colisões laterais.

4. **Decisão final de engenharia e encerramento do Programa REALISMO-1.**
   - **Veredito formal do Ciclo C7: PASS EM TODOS OS GATES DE NÃO-REGRESSÃO.**
   - **Veredito do Programa REALISMO-1: HOMOLOGADO PARCIAL COM SUCESSO DE COMPORTAMENTO.**
     * As flags `--rejoin-handoff align` (Ciclo C2) e `--rejoin-ramp` (Ciclo C3) demonstraram robustez estatística em variedades nunca antes vistas pelo modelo ($N=5..8$), trazendo melhoria dramática de segurança e contenção sem nenhum retreino ou alteração no espaço de observação.
     * Fica homologada para adoção em produção a combinação:
       `--rejoin-handoff align --rejoin-ramp --gov vplan`
     * Ficam arquivadas e descartadas de produção as propostas C1 (`--launch-steer-mute`), C4/C5 (`interlagos_v3`) e C6 (`--lat-offset-slots`), protegendo o simulador contra regressões silenciosas de física e geometria.
   - **Programa REALISMO-1 formalmente CONCLUÍDO e ENCERRADO.**
