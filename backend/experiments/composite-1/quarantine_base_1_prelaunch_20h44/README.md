# Quarentena — lançamento pré-formal abortado (COMPOSITE-BASE-1, R1)

Lançamento: 2026-10-26 20:44:28 → 20:47:44 (-03). Autorização: emenda
operacional B.1 do dono em `PREREG_COMPOSITE_BASE_1.md` (freeze `d1e811e`
+ emenda, commitada antes da execução formal).

Estes bytes NUNCA serão lidos para métricas e NUNCA constituem proveniência
de corrida formal. Preservados exclusivamente como evidência do lançamento
abortado: o `tee` quebrou na largada e o log ficou com exatos 42 bytes
(apenas o banner `pybullet build time: Sep 11 2026 21:22:29`) — sem sumário
do runner e sem prova de exit code, o gate frozen não é certificável. A
física completou o session (main com 30.002 linhas físicas, última linha
tick 5998 / t_s 599,8; events sidecar completo), mas a cadeia de
proveniência exige o log — executar sobre estes bytes violaria o prereg.

| Arquivo | SHA-256 |
| --- | --- |
| 1_R1_INTERLAGOS_RACE.csv | `8872feb3e9a7c62963423f3c9fe5b7c5f2dfa91cad6f1d18cac0489a369844bd` |
| 1_R1_INTERLAGOS_RACE_events.csv | `0fb20fc74d84d5809c96e756d8a801bf6aecc98a25927c74d8e7fef27e69a32d` |
| 1_R1_INTERLAGOS_RACE.log | `8e95cc79f36d6fd99667f69e2d49cddb14745460e8e7e52c8a1bf5b91ba38134` |

Verificação estrutural realizada pelo dono (declarada, nenhuma métrica de
corrida calculada ou consultada): `wc -l` (30.002), última linha de dados,
linha de metadados canônica (`race_diag_v3_4_xyraw`,
`track_frozen_sha256=164876196eb12174`, `weather_transitions=[]`,
`variance=off`), header do events. O g0 executado no mesmo intervalo
(20:40:53–20:44:09, SHA `db0abd330786cbfcae605fe3b19c9e5d78c74506da2849f1118a08b537e67561`,
20F/430P/3S, fail-set idêntico ao g0 1G) foi validado pelo dono e
commitado como g0 de registro — não pertence a esta quarentena.
