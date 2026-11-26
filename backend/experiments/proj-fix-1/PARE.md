# PROJ-FIX-1 — PARE na reconciliação histórica

**Data:** 2026-10-23
**Estado:** encerrado por PARE obrigatório antes de emitir a decomposição C1/C2/C3.
**Orçamento:** 1/1 replay; zero corridas de medição novas; zero smokes.

## Replay e gates

R4 Composite Monaco foi reexecutado uma vez, N=1, com a configuração FF1b congelada, alias `--track Monaco`, seed 0 e writer v3.4 default. A pista frozen manteve SHA curto `67ca11dc211c8c78`; o clima teve zero transições. Saíram 30.000 linhas de dados.

- **g1 PASS:** projeção `split(',')[:49]`, incluindo header e excluindo linhas `#`, byte-idêntica à âncora R4. Hash de ambas as projeções: `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`.
- **g2 PASS:** 71 campos por linha; XY finitos; `ns_raw` inteiro em `[0,833]`.
- A suíte pós-LOC-XY referenciada permanece em 20 FAILED canônicos, 352 passed e 3 skipped; o ciclo atual só adicionou um classificador offline e não alterou runner/testes.

## PARE

O classificador v1.0 congelado selecionou zero linhas da tabela histórica para o identificador preregistrado `composite_monaco_s0`; portanto, a reconciliação ficou em 0 entradas ≥10 m e 0 ≥30 m, contra os esperados 112 e 45. Nenhum mapeamento 1:1 foi produzido e nenhum resultado C1/C2/C3 é declarado. O classificador não foi editado depois dessa leitura. PARE acionado; não foram abertas outras identidades da tabela e não houve nova simulação.

Este estado não demonstra divergência física dos saltos: o seletor histórico congelado não encontrou as linhas que deveria mapear. Qualquer retomada requer um novo prereg que resolva a identidade do run na fonte NIT-2, seguido de nova versão/selftest do classificador antes de acessar números. Nenhuma correção de comportamento é proposta.

## Artefatos e hashes

| Artefato | SHA-256 |
|---|---|
| `PREREG_PROJ_FIX_1.md` | `fcfc012656ef1645eb8d984f412368f892d807abc1b4d85e7a20a8d2017e692c` |
| `scripts/proj_fix_1_classify.py` v1.0 | `a8d6b3202c80aa84e7b2af7a522801bf33ff6896e310873400b2d55608d6a73f` |
| replay v3.4 CSV | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| replay `_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| log bruto do replay | `d88f14030e729716a730228fdca5e4dc8ac99d6dddeeab320a16e593496eb0a1` |
| log g1/g2 | `b982ca2f1561128176945084f2d4839288008ed628a52859bf70de5753ac6d81` |
| log PARE do classificador | `8553a4dac2458aba3ef38119e8f88f952fb991339b78bdbd8ada977a0d30debb` |
| selftest sintético | `edfd299c9e9d364efb837fc41ac47b61df6717302034dd2817a798a0892ebb1f` |

Prereg/classificador/selftest congelados antes do replay no commit `a519081`. Pistas frozen e pools permaneceram intocados.
