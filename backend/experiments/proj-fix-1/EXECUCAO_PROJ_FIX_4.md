# PROJ-FIX-4 — retificação de proveniência e fechamento C1–C5 (Monaco)

**Data:** 2026-10-23  
**Resultado:** fechamento offline completo; nenhuma correção de comportamento proposta.  
**Orçamento:** zero corridas, zero smokes; suíte mantida como referência 20F/352P/3S, sem reexecução; pools e pistas frozen intocados.

## Proveniência e freeze

O P3 esperava `a3e7dd187f96116f5edf3c34a6e613af7357105b6fe454c4217a9b64cbb502ac` para `PARE_PROJ_FIX_2.md`. A cópia commitada em `d02a6f8` e os snapshots `2330e9f`, `262d668`, `HEAD` e disco têm todos SHA-256 `e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c`. O valor `a3e7…` veio de um rascunho não commitado da revisão final e foi transcrito ao P3. A evidência indica erro de proveniência, não mutação; P3 e o classificador v1.2 não foram editados.

- Freeze P4: commit `574c5eac266779d46c20c9f30d4fd76a69726834`; `PREREG_PROJ_FIX_4.md` SHA-256 `0d9c8d31bfee6470d045cedea46c25264b3ba5d12d757116e75a300554219392`.
- Selftest v1.2 executado uma vez antes do freeze: PASS; log `13_selftest_v12_recheck.log` SHA-256 `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127`. Script v1.2 disco e `git show 2330e9f` coincidem em `bc0a7ba9a5a9e4194d6195f3bc830a7626133939b465829f8ee1225e30414bdd`.
- Manifest de proveniência: commit `75666b3`; SHA-256 `5715be7b663394e29cc9b2a21a2baf554ccdb9281cc6d25439651d38e0b641ee`. Os 18 artefatos congelados passaram com `SHA esperado = sha256sum(disco) = sha256sum(git show commit pinado:path)`. O próprio manifest também foi conferido contra o commit `75666b3` e seu hash de disco coincide.
- O diretório de classificação estava ausente no freeze e foi criado somente após a aprovação do manifest.

## Gates

| Gate | Resultado |
|---|---|
| g0 | PASS — 18/18 proveniências duplas; PARE v2 corrigido para `e287e5…`; P3 e v1.2 íntegros. |
| g1 | PASS — projeção das 49 colunas do replay e âncora com SHA-256 comum `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`. |
| g2 | PASS — 71 campos por linha, 30.000 linhas; X/Y finitos em 30.000/30.000; `ns_raw` inteiro em `[0,833]` em 30.000/30.000 (mín. 0, máx. 833). |
| g3 | PASS — referência congelada `8_g3_identity_selector.log` SHA-256 `aa1e37ba7c7d8a6bfa19e475abb35f97df18f00a2db81bf0451487e0b4a17212`: `composite_monaco`, 112 eventos ≥10 m e 45 ≥30 m. Identidade NIT-2 histórica `5_identidade_run_nit2.log` SHA-256 `23f499357abb80d30c4ee17db3bed12e289e059dc5bea4057503c2ebc0e4c179`. |
| g4 | PASS — 112 eventos mapeados 1:1, 112 chaves únicas; cortes fechados em 112 e 45; ALO (2130,2132) é C5. |

Os cortes NIT-2 são definidos pelo campo congelado `abs_projection_error_m`: ≥10 m e headline ≥30 m. C4 permanece diagnóstico separado; foram zero linhas inválidas.

### Classes e p95

| Corte | Classe | N | p95 dXY (m) | p95 abs(d_ns_raw) |
|---|---:|---:|---:|---:|
| ≥10 m | C1 | 0 | — | — |
| ≥10 m | C2 | 0 | — | — |
| ≥10 m | C3 | 46 | 1.8704425708164663 | 416.25 |
| ≥10 m | C5 | 66 | 3.307436586085905 | 6.75 |
| **≥10 m** | **total** | **112** |  |  |
| ≥30 m | C1 | 0 | — | — |
| ≥30 m | C2 | 0 | — | — |
| ≥30 m | C3 | 45 | 1.8713291979009652 | 418.59999999999985 |
| ≥30 m | C5 | 0 | — | — |
| **≥30 m** | **total** | **45** |  |  |

Logo, `112 = 0 + 0 + 46 + 66` e `45 = 0 + 0 + 45 + 0` para C1/C2/C3/C5. Entre os 66 eventos C5, `offtrack=1` em 66/66 (1,000000) e `offtrack=0` em 0/66 (0,000000), conforme a tabela histórica. Isso descreve o subconjunto, sem atribuir causalidade.

## Artefatos e hashes

- g1/g2: `15_gate_g1_g2_v12.log` — `617ef75e8cae3aa556e8e362c5e54a8099f6446b734c3bb836040a5839807a10`.
- g4 stdout: `classificacao_v12/16_classify_v12.log` — `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05`.
- Pares classificados: `classificacao_v12/pares_classificados.csv` — `750319117b7f2f9c43a92543a8754a36a14021dbfd483c8bc3366f25c6b8c3c5`.
- Mapa 1:1: `classificacao_v12/mapa_nit2_ge10.csv` — `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f`.
- Resumo/p95: `classificacao_v12/resumo_classes.json` — `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05`.
- Validação de fechamentos/anatomia C5: `17_post_classify_validation.log` — `e62d487948772713bb76959d21713fa575bcdc7dd63bc9f0de20cc9c18036f30`.

Não se propõe RECUP-1 nem correção de projeção/gate nesta fase. A escolha entre RECUP-1 para C1/C2 e projeção/gate para C3/C5 volta ao dono para a Etapa 2.
