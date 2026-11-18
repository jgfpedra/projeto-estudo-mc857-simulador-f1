# PREREG — PROJ-FIX-4: retificação de proveniência e fechamento C1–C5 (Monaco)

**Status:** retomada após PARE em g0 de PROJ-FIX-3; nenhum agregado por classe
foi produzido. P4 corrige somente a proveniência de um hash e reutiliza o
classificador v1.2 já congelado, sem simulações ou mudanças de comportamento.

## Causa raiz e retificação de proveniência

O PROJ-FIX-3 congelado registrou `a3e7dd187f96116f5edf3c34a6e613af7357105b6fe454c4217a9b64cbb502ac` para `PARE_PROJ_FIX_2.md`. O arquivo foi criado no commit `d02a6f8`; `git show` nos estados commitados `d02a6f8`, `2330e9f`, `262d668` e `HEAD`, assim como o disco, dá `e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c`. O hash `a3e7…` veio de um rascunho não commitado da revisão final do PARE v2 e foi transcrito ao P3; nenhum estado commitado do relatório teve esse hash. A causa é erro de proveniência, não mutação. P3 e o instrumento v1.2 permanecem intocados.

Aplicação desta retomada: o §3 registra o histórico do freeze v1.2 já concluído em `2330e9f`; não recriar nem editar o classificador. Reexecutar seu `--selftest` uma vez antes do freeze P4, salvar `13_selftest_v12_recheck.log` (SHA-256 esperado `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127`) e confirmar que o hash do script no disco e em `git show 2330e9f` é `bc0a7ba9a5a9e4194d6195f3bc830a7626133939b465829f8ee1225e30414bdd`. O diretório `experiments/proj-fix-1/classificacao_v12/` deve estar ausente ou vazio antes do freeze; qualquer conteúdo aciona PARE.

O commit dedicado de P4 congela este preregistro e o selftest reexecutado antes de qualquer contagem. Em seguida, `14_freeze_manifest_v4.log` registra para cada fonte o hash esperado, `sha256sum` do disco e hash de `git show <commit pinado>:<path>`; os três precisam coincidir. A proveniência do próprio P4 é conferida contra seu commit de freeze e registrada no manifest subsequente. Se qualquer fluxo divergir, PARE antes de g1/g2 ou de abrir qualquer classe.
## 1. Objetivo, orçamento e limites

Fechar o mapeamento 1:1 dos 112 eventos NIT-2 `composite_monaco` (112 ≥10 m,
45 ≥30 m) sobre C1/C2/C3/C5, preservando C4-diagnóstico para linhas inválidas.
C5 é somente uma classe residual **de evento mapeado**: o par válido existe no
replay, mas não satisfaz nenhum limiar C1/C2/C3. A taxonomia anterior C1/C2/C3
permanece inalterada. Nenhuma correção de comportamento é proposta.

- Zero corridas novas e zero smokes; usar somente o replay e as fontes congeladas.
- Pools, pistas frozen, runner, testes, controles e física intocados.
- A suíte permanece na referência 20F/352P/3S; não reexecutar.
- PROJ-FIX-2 e seu PARE permanecem imutáveis: commits `8222dff` e `d02a6f8`;
  `proj_fix_2_classify.py` v1.1 SHA-256
  `9d73a890964974b3f04d2261fe0806a21ec6b162b111aa89c28c7919c3704d8d`.

## 2. Fase 0 — diagnóstico permitido de uma única chave

Somente a chave que acionou o PARE anterior foi examinada:
`('ALO', 2130, 2132)`, run `composite_monaco`. Evidência em
`experiments/proj-fix-1/10_diagnostico_chave_alo.log`, SHA-256
`0efe1bc82568d39a92076539d5cf5e708b38926a03bdc5d19abe0d519de40990`.

- Replay: `dXY=1.8617987807296796 m`; `ns_raw=766→772`, `d_ns=6`.
- Fonte histórica: `delta_s_wrapped_m=20.175834396520713`,
  `abs_projection_error_m=18.313956217828036`, `offtrack=1`,
  `authority=rejoin`, `lat=11.39793668372648→12.23462726140812`,
  `speed_mps=9.293553754712804`.
- `delta_cum_dist_m=1.8618781786926775`; difere do dXY exportado por
  `0.0000793979629978292 m` (≈79.4 μm), portanto os valores são próximos, não
  exatamente iguais.
- Monaco frozen: waypoints 766→772, arco direto `23.860952390323 m`, corda
  `20.738853198767 m`; o loader passa os waypoints diretamente a
  `Track.from_waypoints`. Track identity interna `67ca11dc211c8c78`.
- Única atribuição permitida antes do freeze: esse evento satisfaz
  `dXY<30` e `d_ns<8`, portanto receberá C5 se os gates e o fechamento geral
  passarem. Nenhuma contagem de classe ou par semelhante foi examinada.

## 3. Fase 1 — instrumento v1.2 e freeze

Criar `scripts/proj_fix_3_classify.py` como cópia de
`proj_fix_2_classify.py` v1.1. Diff autorizado estritamente:

1. Docstring para PROJ-FIX-3/version 1.2 e `VERSION="1.2"`.
2. `_classify_samples` retorna também `par_metricas`, indexado pela chave
   `(drv,tick_prev,tick)`, com `dxy_m` e `d_ns_raw` de **todo** par válido
   adjacente em ordem de tick crescente.
3. No mapeamento de cada evento histórico ≥10 m: usar classe C1/C2/C3 quando
   presente; se não, atribuir C5 somente quando a chave existir em
   `par_metricas`; se a chave não existir, PARE. Pares inválidos continuam fora
   de `par_metricas` e C4-diagnóstico permanece separado.
4. O resumo terá blocos C1–C5 de `count`, `p95_dxy_m` e
   `p95_abs_d_ns_raw` para o conjunto mapeado NIT-2 ≥10 m, além dos mesmos
   campos por classe para o subconjunto headline ≥30 m. Os blocos de
   `nit2_ge10_mapping` e `headline_ge30_mapping` terão contagens C1–C5. C4
   mantém contagem e linhas inválidas da v1.1.
5. Estender o selftest sem mudar os casos/asserts existentes de C1/C2/C3,
   fronteiras, C4, chaves e p95; adicionar par sintético válido sub-limiar
   que só pode ser mapeado como C5.

Executar o selftest sintético v1.2 uma vez para o P4 e registrar seu resultado
em `13_selftest_v12_recheck.log`; os hashes e duas proveniências são registrados
em `14_freeze_manifest_v4.log`. Congelar o prereg P4 e o log do selftest em
commit dedicado antes de qualquer agregação por classe. Depois do freeze, não
editar prereg nem instrumento.

## 4. Fase 2 — gates sobre artefatos existentes

### g0 — integridade

Conferir SHA-256 antes de ler CSVs. Divergência = PARE.

| Artefato | SHA-256 esperado |
|---|---|
| Replay `1_replay_composite_monaco_s0_v34.csv` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| Replay `_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| Log do replay | `d88f14030e729716a730228fdca5e4dc8ac99d6dddeeab320a16e593496eb0a1` |
| Âncora FF1b R4 `4_composite_monaco_s0.csv` | `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022` |
| Tabela NIT-2 `saltos_projecao.csv` | `b9bcb14d9bb38dceabcbfddc9f90cb3b5bd2cc25fa6719a90ded52eb2b9bb739` |
| v1.1 `proj_fix_2_classify.py` | `9d73a890964974b3f04d2261fe0806a21ec6b162b111aa89c28c7919c3704d8d` |
| PARE g4 v1.1 `9_classify_v11.log` | `3fe29ebed88da8bb67ea39cb4c14be500eb4131b75b8afebfd063e3d0a84e9ee` |
| PARE PROJ-FIX-2 `PARE_PROJ_FIX_2.md` — hash corrigido | `e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c` |
| v1.2 `proj_fix_3_classify.py` | `bc0a7ba9a5a9e4194d6195f3bc830a7626133939b465829f8ee1225e30414bdd` |
| Selftest v1.2 original `11_classifier_selftest_v12.log` | `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127` |
| Selftest v1.2 recheck `13_selftest_v12_recheck.log` | `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127` |
| PARE PROJ-FIX-3 `PARE_PROJ_FIX_3.md` | `b8e6b3793e89d681c5feedd1290de9aa22b0878b250a41a07345fc70a3ace6a3` |
| g0 histórico P3 `12_g0_sha256.log` | `a3321d81148c421437ca4168ca29a80444ec41c6ea4e14f9314d61073f130486` |
| Prereg PROJ-FIX-3 `PREREG_PROJ_FIX_3.md` | `d1bd9190183e50ff841e008ee5e4610d135765bfe5e449e056bbe33c8d13b1b2` |
| Diagnóstico único ALO `10_diagnostico_chave_alo.log` | `0efe1bc82568d39a92076539d5cf5e708b38926a03bdc5d19abe0d519de40990` |
| Identidade g3 `8_g3_identity_selector.log` | `aa1e37ba7c7d8a6bfa19e475abb35f97df18f00a2db81bf0451487e0b4a17212` |
| Identidade NIT-2 `5_identidade_run_nit2.log` | `23f499357abb80d30c4ee17db3bed12e289e059dc5bea4057503c2ebc0e4c179` |

Confirmar também que os commits v1.1/PARE e seus arquivos permanecem intactos.

### g1/g2 — replay congelado

Executar somente `proj_fix_3_classify.py --gate` sobre o replay existente e
salvar o log em `experiments/proj-fix-1/15_gate_g1_g2_v12.log`.
Esperados: projeção de 49 colunas do replay/âncora igual a
`a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`; 71
campos por linha; `ns_raw` inteiro em `[0,833]`; X/Y finitos. Não reexecutar o
replay.

### g3 — identidade NIT-2

Usar como referência o log prévio `8_g3_identity_selector.log`, SHA-256
`aa1e37ba7c7d8a6bfa19e475abb35f97df18f00a2db81bf0451487e0b4a17212`:
`run=composite_monaco`, 112 ≥10 m e 45 ≥30 m. Não abrir outras identidades.

### g4 — classify v1.2

Executar offline sobre replay/tabela congelados e gravar em novo diretório
`experiments/proj-fix-1/classificacao_v12/`, capturando stdout/stderr em
`16_classify_v12.log`. Exigir:

- Cada um dos 112 eventos ≥10 m resolve exatamente uma classe C1/C2/C3/C5;
  chaves únicas e sem ausentes.
- Mapeamentos fecham `112 = Σ(C1..C5)` para ≥10 m e
  `45 = Σ(C1..C5)` para headline ≥30 m. C4 continua diagnóstico separado.
- Os resumos/p95 por classe para os dois cortes e todos os artefatos têm hashes.
- Emitir novos `pares_classificados.csv`, `mapa_nit2_ge10.csv` e
  `resumo_classes.json`; o mapa conserva os campos históricos, incluindo
  `authority` e `offtrack`.

## 5. Fase 3 — veredito

Reportar contagem e p95 de dXY/d_ns por classe nos cortes ≥10 m e ≥30 m, mapa
1:1 classe-por-evento, e uma linha de anatomia C5 com a fração `offtrack=1`
versus `offtrack=0` entre os eventos C5 (somente da tabela histórica). Atualizar
`PROJECT_STATE.md`, `AUDITORIA_RL.md` e `worklog.md` com ponteiros `Ver <path>`
fechados por `)`, mais hashes e commits. Nenhuma correção é proposta nesta fase;
a escolha RECUP-1 (C1/C2) versus projeção/gate (C3/C5) retorna ao dono.

## 6. PARE obrigatório

PARE em qualquer divergência g0–g3; chave histórica sem classe exata única,
inclusive chave ausente no replay; duplicidade; cortes diferentes de 112/45;
diff v1.1→v1.2 fora da lista autorizada; agregado por classe antes do freeze;
edição de prereg/instrumento após revelar números; ou nova falha de teste
reportada contra a referência 20F/352P/3S. Não rodar simulação nem alterar o
instrumento congelado em caso de PARE.
