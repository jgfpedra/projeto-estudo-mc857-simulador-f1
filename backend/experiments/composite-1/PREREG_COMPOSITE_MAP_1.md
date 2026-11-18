# PREREG COMPOSITE-MAP-1 — inventário frozen da Etapa 4

## Escopo e proibições

Este ciclo é report-only. Não houve treino, fine-tune, inferência, corrida,
smoke, suíte ou alteração de produção/flags default. O estado PASS/YIELD
permanece no repositório como pesquisa arquivada/defeito conhecido; `race`
default e `--leader-yield` não foram alterados.

O inventário foi lido no worktree principal, com `HEAD=7f1b68d5c2d54dd7c40c4366e3b684ba5bf46a46`.
Os registros pendentes `PROJECT_STATE.md`, `model_train/AUDITORIA_RL.md`,
`worklog.md` e o anexo não relacionado ficaram intocados.

## (a) Candidatos a Composite e wiring atual

### Composição efetivamente ligada

O perfil de deploy está em `backend/scripts/run_race_10_cars.py:71-104`:

- `race`/default: `model_train/v10_dagger/dagger_actor_best.keras`
  (solo, obs `traffic`) + `model_train/v15_residual/residual_best_weights.npz`;
- `composite`: alias do mesmo par;
- `race-blind`: solo v10 puro, obs `edge`, sem residual;
- `traffic`: `v14_traffic/dagger_actor_best_s1_n4.keras`, obs `traffic`;
- `quali`: `v11b_pace90/dagger_actor_best.keras`, obs `edge`.

O runner converte o solo Keras para o sidecar NPZ quando necessário e executa
`NumpyCompositeActor` (`model_train/residual_gated.py:142-188`):
`a=tanh(m_solo+g*r)`, com residual 16→128→128→2 e último layer inicializado
em zero. O solo é congelado no treino residual. O wiring de
`--profile composite`, `--mixed composite:N,edge:M` e `professor` está em
`model_train/race_diagnostic.py:45-74,1184-1221`; o caminho misto aceita os
grupos `traffic`, `edge`, `composite` e `professor`.

### Artefatos de política e hashes SHA-256

| Componente | Caminho | Versão/papel | SHA-256 |
|---|---|---|---|
| Solo | `backend/model_train/v10_dagger/dagger_actor_best.keras` | v10 DAgger, base vigente | `b75ab0e56d64457589a7f2a869c4d4140dafb6ad7c6a6a03560dbfe6c0e94b2e` |
| Solo sidecar | `backend/model_train/v10_dagger/dagger_actor_best_weights.npz` | forward NumPy do runner | `bc5ea6e288a4f0c36eb9257a1ac5d478c6cf51549a9b492ac0b89b90951b93e3` |
| Solo metadata | `backend/model_train/v10_dagger/training_meta.json` | histórico v10 | `d94a296ecde0489b3c0d1e379d47b65aa1414ad226fb358b127943f7f63cef96` |
| Residual | `backend/model_train/v15_residual/residual_best.keras` | v15 residual gated | `5a2c20cedf90b6cccfd5551c3e2e7e5fd9d99f767a12ea284b75b0299349ee3a` |
| Residual sidecar | `backend/model_train/v15_residual/residual_best_weights.npz` | forward NumPy do runner | `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` |
| Traffic candidato | `backend/model_train/v14_traffic/dagger_actor_best_s1_n4.keras` | v14 estágio 1, n=4 | `ac9cedf7afc5bb2f1449d0801d4bffd4e5d461c8afabe9822be1fe30bfc8f11d` |
| Traffic sidecar | `backend/model_train/v14_traffic/dagger_actor_best_s1_n4_weights.npz` | sidecar n=4 | `c4d3129bf0cb554291bcbb86d5b22be70ba4e31233d64134f86152f1f8fb8217` |
| Traffic candidato | `backend/model_train/v14_traffic/dagger_actor_best_s2_n8.keras` | v14 estágio 2, n=8 | `0c6257f7c105c7092c763367e14b7b24c3cf3317d524ac186df051fc5b4fc932` |
| Traffic sidecar | `backend/model_train/v14_traffic/dagger_actor_best_s2_n8_weights.npz` | sidecar n=8 | `4daf8a2ab5bb8c76fcd9caad67d8ed3e3a2825408f421317ca0cfc067a257809` |
| Traffic metadata | `backend/model_train/v14_traffic/training_meta.json` | currículo 0:2, 4:5, 8:3 | `d4ac3360c815fb43507bc332641a2db7290a3b69472e396cd6b20957a141438c` |
| Pace candidato | `backend/model_train/v11b_pace90/dagger_actor_best.keras` | v11b quali | `44e2fa632a2132e2da125521dd2f049bc82a4daa1d42b804322183c3df6dce32` |
| Pace sidecar | `backend/model_train/v11b_pace90/dagger_actor_best_weights.npz` | sidecar quali | `d3065ff62cfba2ba784bca5e307fb2812d8c1917e927f334894a08d3399d85b7` |
| Mappings | `backend/model_train/mappings.pkl` | mapeamento do forward NumPy | `e7d1c4b9efc1d59a06ee341e351a173fdbc7bb0afb9b51d01b5cde3c5f7447e3` |
| Runner | `backend/scripts/run_race_10_cars.py` | profiles e actor NumPy | `6f13b59cfb7e709081483be85e2ad14d7295f65981dc8705ca8bcc9a9b8b03b3` |
| Wiring | `backend/model_train/race_diagnostic.py` | profile/mixed runner | `63fc1527455fc552caf9b15a1fcff3e797f5c91d2aeca13d231a057866af2216` |
| Residual code | `backend/model_train/residual_gated.py` | gate/composição/export | `955085c029f0c72cb1c0bb1faa57f4266084ceca22f694369f51267ecf9a73a9` |

Também foram catalogados, sem promoção, `v14b_traffic/s0_n0`,
`v14_traffic/s0_n0`, `v14_traffic/init_from_v10`,
`v15_residual/residual_weave_r12` e `residual_weave_r12b`; são históricos ou
alternativos e não entram no candidato Composite deste prereg.

### Formatos de observação

`backend/model_train/f1_env.py:88-114,394-395,942-960` define:

- `legacy`: telemetria 23-D;
- `edge`: 34-D (23 + 11 raios);
- `traffic`: 46-D (34-D edge + 12-D tráfego).

O Composite vigente usa o solo com entrada edge e acrescenta os 12 sinais de
tráfego no `build_residual_input`, mais velocidade, curvatura e duas ações
anteriores, totalizando 16-D para o residual.

## (b) Pontos de treino e dataset consumido

### DAgger/BC

`backend/model_train/train_dagger.py` é o entry point principal. O loop
`rollout_episode` (`:60-85`) gera estados como dicionários
`{telemetry, ctx, track_id, compound_id}` e rótulos de ação do professor
`float32[2]`; `train_bc` (`:88-116`) empilha cada chave, aplica clipping
`[-0,98,0,98]`, transforma o alvo para `atanh` e treina Keras com Huber.
O dataset é mantido em memória e agregado entre iterações; não existe leitor
de CSV medido para alimentar esse entry point.

No modo residual (`train_dagger.py:123-205,489-570`), o solo v10 é carregado
congelado. O dataset consumido é `res_inputs float32[N,16]`, `r_targets
float32[N,2]`, com gate calculado durante o rollout; o alvo é
`atanh(a_teacher)-m_solo`. O exportador produz o NPZ usado pelo runner.

### PPO

`backend/model_train/train_multi_context_ppo.py:42-44,265-318,515-626` é um
entry point separado de PPO. Ele usa `F1MultiContextEnv`, rollout online,
observações do ambiente e referência opcional `reference_path.csv`; salva
ator, crítico, `log_std` e metadata. Não há adaptador para o corpus CSV
medido, nem base Composite offline neste entry point.

### O que é treinável hoje

Treinável sem instrumento novo: um novo DAgger/BC ou residual pode consumir
rollouts gerados pelo próprio ambiente/teacher, com obs `legacy`/`edge`/
`traffic`, ou arrays já convertidos para os formatos acima. O residual
preserva o solo congelado por construção.

Não é treinável diretamente hoje: os CSVs medidos de corrida, seus sidecars
de solver e os agregados de fase. Eles têm `tick,t_s,drv,speed,s,lat,th,brk,
steer_rad,...` e observações gravadas (`obs0...`), mas não carregam em geral
o dicionário `ctx/track_id/compound_id` nem os alvos do professor ou
`res_inputs/r_targets`. A conversão e a política de rotulagem ainda não
existem.

## (c) Adesão do corpus representativo

### Corpus elegível/pinado

| Subcorpus | Artefatos | Hashes principais | Uso proposto | Estado |
|---|---|---|---|---|
| Rejoin cycles | `backend/experiments/rejoin-tel-2/2_replay_rejoin_tel2_monaco_s0_v35.csv` | `d950f7a60d47d125d829f5c4bf0302eadd9eb8ef7001cd17e690ba7950f6ac95` | estados/telemetria de reentrada | bruto; conversor pendente |
| Rejoin windows | `backend/experiments/rejoin-tel-2/autopsia/3_rejoin_windows.csv` | `1df9fdcff1082dffc0e9571b53e6cdc26d7f2daf1af59495e024a032f140e129` | janelas para seleção | agregado; não é dataset de ação |
| Rejoin hesitations | `backend/experiments/rejoin-tel-2/autopsia/4_hesitations.csv` | `0a479deaf34b5ba4bdba92e384d4497c01cdefbac533cf43d28cc83d9ee3c89e` | casos ≤10 s pós-reentrada | agregado; conversor/rotulagem pendente |
| Rejoin summary | `backend/experiments/rejoin-tel-2/autopsia/5_summary.json` | `74fccba9e9c5bafed52a9b150877f0598c4fb87da4e5fc31a8cf46cf60c08cf3` | proveniência e cobertura | report-only |
| Tráfego manifest | `backend/experiments/trafego-med-1/1_MANIFEST_TRAFEGO_MED_1B.json` | `895ab61a6531b44ed18407c3e927ad24f6fa230997d9df6cc2305c928a5fb9a3` | pin de 110 caminhos e schemas | frozen; raw sources heterogêneos |
| Tráfego inventory | `backend/experiments/trafego-med-1/0_INVENTARIO_METADATA.md` | `cfae366a07d3d75ef45b61d6892a91caf4b098091d7cf70f1011048baeb8c02b` | censo de fontes | frozen |
| Nose-to-tail/phase | `backend/experiments/trafego-med-1/1_phase_pair_arm.csv` | `2800a648e8fe853eb325582d3d973215bad8fc4250b8ef06756258c425c24beb` | oportunidades por fase/par | agregado; sem alvo de ação |
| Pair aggregate | `backend/experiments/trafego-med-1/1b_phase_pair_aggregate.csv` | `47e1c11a13be1b29c9bac6ab28195bba6e59d9af295bd07bac8a8991c50d0802` | agregação para seleção | agregado |
| Top segments | `backend/experiments/trafego-med-1/2_top_segments_car.csv` | `ba4ab48e53c6beac4b3bbcd2a7e35e90de6dccbfe5fbca7801a85b8ca089ca3c` | segmentos nose-to-tail | agregado |
| Start/rejoin transfer | `backend/experiments/trafego-med-1/3_reentry_launch_transfer.csv` | `9aa82a54ebc460af49bb7585f97b8f4a3b99569d63c8d641c84a1c365e444e4a` | pacote de largada/reentrada | agregado |
| Per-arm transfer | `backend/experiments/trafego-med-1/3b_transfer_by_arm.csv` | `c394c96fb73440613d892621d5e24494b6f7985b98b8eb5132ee55cbabbecd4a` | transferência por braço | agregado |
| Run coverage | `backend/experiments/trafego-med-1/3c_run_coverage.csv` | `bb505c75b4022e8f3dbcba5be54ec2fb69c11c5b1afd5869adeeebe6e25b9be2` | cobertura/proveniência | agregado |
| Dossiê | `backend/experiments/trafego-med-1/4_DOSSIE_TRAFEGO_MED_1B.md` | `23a2dac7ad7c7c6d3d39a28a556338ef454dbd18dca8cca36d0b1d504861a04a` | decisão report-only | report-only |

As geometrias usadas nos pinos são `interlagos_v2`
(`c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613`) e
`Monaco_v2` (`af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`).
O pacote de largada do manifest contém fontes raw sem blob Git (`SEM_BLOB_HEAD`);
portanto não é corpus treinável frozen até uma etapa posterior de proveniência.

### Adesão proposta

O corpus futuro deve selecionar, sem misturar labels ainda, quatro famílias:

1. janelas de rejoin;
2. largada/primeira volta;
3. filas nose-to-tail após 60 s;
4. hesitações até 10 s após reentrada.

Os artefatos agregados acima servem para seleção e auditoria, não para treino
direto. Os CSVs brutos elegíveis precisam ser reconfirmados pelo manifest,
convertidos para observação `traffic`/residual e rotulados com professor
compatível antes do primeiro número de treino.

## (d) Protocolo de avaliação futuro

O berço do gate futuro fica congelado, sem número de runs nesta etapa:

- baseline: policy vigente `race` (solo v10 + residual) e `race-blind` como
  controle de ablação;
- condições: Composite candidato, professor e mixed
  `composite:N,edge:M` conforme o próximo prereg;
- seeds/pistas/config: usar o conjunto canônico de PASS-1/YIELD-1C:
  Interlagos, seed 0, weather `seeded`, variance `off`, grid `f1`, rejoin
  `bearing`, 6000 ticks/99 laps, mantendo ambiente, física, observação,
  pool, cache e pista frozen;
- incluir também o berço de rejoin Monaco_v2 somente se o próximo prereg
  explicitar a condição e o número de runs;
- número exato de execuções por condição, seeds adicionais, critérios de
  promoção e orçamento ficam deliberadamente para `COMPOSITE-BASE-1`.

## (e) Riscos e lacunas bloqueantes

1. **Conversão:** não existe leitor/conversor que transforme os CSVs medidos
   em `{telemetry,ctx,track_id,compound_id}` + labels do professor, ou em
   `res_inputs/r_targets`.
2. **Rotulagem:** os CSVs registram ações observadas, mas a origem teacher/
   student e a semântica de ação não são uniformes entre versões de
   instrumento; não se deve tratá-las como alvos sem protocolo.
3. **Schema/versionamento:** há séries `res16d`, `xyraw`, tráfego e rejoin com
   headers diferentes; compatibilidade `23/34/46-D` precisa ser validada por
   arquivo, não inferida por nome.
4. **Proveniência:** parte do pacote de largada é untracked/`SEM_BLOB_HEAD`;
   o manifest congela hashes de disco, mas não cria uma cadeia Git para essas
   fontes.
5. **Geometria:** métricas espaciais dependem de geometry_id e versão exacta;
   qualquer conversor deve rejeitar geometria ausente ou divergente.
6. **Balanceamento:** os agregados medem oportunidades e fases, não fornecem
   distribuição de estados/ações nem split por episódio; ainda não há regra
   de train/validation/test.
7. **Paridade:** o residual exige solo v10 e sidecar/mappings exatos; uma
   conversão que use o ator traffic v14 ou outro sidecar muda o contrato.
8. **Auditoria:** ainda não há schema de dataset nem checksum de cada shard
   convertido; qualquer treino futuro deve congelar ambos antes da primeira
   época.

## Veredito da etapa

**Lacunas bloqueantes.** O Composite é treinável em princípio pelo entry point
residual/DAgger existente, mas o corpus medido não é treinável hoje sem
instrumentação nova de conversão, rotulagem e proveniência. Este prereg não
autoriza resolver as lacunas, treinar, inferir ou simular. O próximo passo
possível é `COMPOSITE-BASE-1` somente após o dono ratificar um conversor,
schema de dataset, regra de labels, split e cadeia de hashes.
