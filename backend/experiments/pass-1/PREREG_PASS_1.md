# PREREG PASS-1 — decisão de passagem no follow

**Versão:** 1.0  
**Base do freeze:** `8136d54ec45f9f49b38a5893a812928474109535` (`feat/sanidade-produto`)  
**Estado:** preregistro congelado antes de suíte, corrida ou métrica nova.

## Objetivo e decisão de escopo

Testar, sem promoção, se uma decisão opt-in de lado e liberação do `v_cap` faz o
`ReferenceController` converter oportunidades de passagem em trocas sustentadas.
`--pass-decision` ausente permanece default-OFF e chama a camada `_pass_layer`
legada. Com ON, a decisão PASS-1 **substitui** `_pass_layer`; não compõe com ela.
O campo neural/v10 não recebe a decisão.

### Reespecificação ratificada pelo dono

O fixture inicialmente proposto para R1,
`backend/experiments/diag-largada/race_diag_lg1_cap_s0.csv`, é um braço neural
com `launch_cap=True` e variância `grid,compound`; ele não mede
`ReferenceController`. É Tier B no manifest TRAFEGO-MED-1B: SHA-256
`9c16cc29daf19ff52e78159b3c81237dbf8c7ef70a3021dc00a96ceaced14969`,
14.936.231 bytes, 30.000 linhas de dados, 50 colunas. Logo, não pode ser o
replay OFF pareado.

R1 será uma **nova medição OFF** do professor sobre a geometria congelada
Interlagos v2. Seu CSV completo e seu SHA-256, registrados após exit 0, passam a
ser o novo pino de baseline de R2. R2 repete a mesma configuração e muda apenas
a flag. Não se reivindica identidade de bytes com o fixture neural antigo.

O antigo R3 `traffic:2,edge:8` também não testa o fator no professor. R3 passa
a ser `professor:2,edge:8`; só esses dois carros recebem a decisão. O guardrail
R3 congela os números publicados no pedido PASS-1 do dono para a mista (iii):
84 contatos no total, zero contatos pós-largada, zero hesitações, 138,2 s no
campo e 138,2 s para os v10. Os gates usam contatos totais ≤84 e pace rolante
edge ≤140,96 s (`138,2 × 1,02`). Como a composição do grupo de dois carros
mudou, são referências absolutas, não uma comparação pareada. Composição e
limitação serão divulgadas no veredito.

O CSV/eventos histórico de largada e o CSV misto antigo continuam apenas como
referências de elegibilidade/proveniência; não serão abertos para métricas neste
ciclo. O CSV misto antigo não tem geometria frozen identificada no manifest.

## Proveniência congelada antes das corridas

### Nível A — disco igual a blob Git em `8136d54`

| Artefato | SHA-256 | Uso |
|---|---|---|
| `backend/model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` | Geometria R1/R2/R3; 61.791 bytes |
| `backend/model_train/v10_dagger/dagger_actor_best.keras` | `b75ab0e56d64457589a7f2a869c4d4140dafb6ad7c6a6a03560dbfe6c0e94b2e` | Ator edge de R3; 733.863 bytes |
| `backend/model_train/v10_dagger/dagger_actor_best_weights.npz` | `bc5ea6e288a4f0c36eb9257a1ac5d478c6cf51549a9b492ac0b89b90951b93e3` | Pesos NumPy carregados por R3; 227.134 bytes |
| `backend/experiments/rejoin-tel-1/2_full_suite.log` | `8755ea47a6de565eacdd132dbd89effcf4863de4720b773d74788ba1796eb8ae` | Referência da suíte; 20F/363P/3S |
| `backend/experiments/trafego-med-1/1_MANIFEST_TRAFEGO_MED_1B.json` | `895ab61a6531b44ed18407c3e927ad24f6fa230997d9df6cc2305c928a5fb9a3` | Manifest Tier A que congela as fontes Tier B abaixo |

SHA-256 de cada blob acima foi conferido por `git show 8136d54:<path>` e
coincide com o disco.

### Nível B — histórico não rastreado, pino no manifest congelado

O inventário metadata-only `backend/experiments/trafego-med-1/0_INVENTARIO_METADATA.md`
(SHA-256 `cfae366a07d3d75ef45b61d6892a91caf4b098091d7cf70f1011048baeb8c02b`)
é Tier B histórico, sem blob em `8136d54`; o hash está pinado aqui e no manifest
Tier A acima. As fontes de corrida listadas no manifest permanecem Tier B. O
fixture de largada citado acima está classificado como Tier B. O CSV da mista (iii),
`backend/experiments/legacy/race_diag_mixed_2iter3_8v10.csv`, está pino Tier B
`11d4b956b6bc1c077a27b60fc3527eed16337461d735d413de3ae3a5c642a93c`,
13.551.372 bytes, 30.000 linhas, 41 colunas. Ele só contextualiza o braço; as
métricas-limite vêm do Tier A `PROJECT_STATE.md` acima. Nenhum Tier B será
re-hidratado ou analisado como série neste ciclo.

## Freeze de arquivos

O dono commita e informa o hash antes de qualquer suíte ou corrida. Depois,
verificar com `git show <hash>:<path>` que os cinco blobs abaixo são byte
idênticos ao disco:

1. `backend/experiments/pass-1/PREREG_PASS_1.md`;
2. `backend/model_train/reference_controller.py`;
3. `backend/model_train/race_diagnostic.py`;
4. `backend/tests/test_pass_decision.py`;
5. `backend/scripts/pass_decision_audit.py`.

`experiments/` é ignorada para arquivos novos; o prereg precisa entrar com
`git add -f`. Não incluir no commit deste freeze os edits anteriores de
`backend/PROJECT_STATE.md`, `backend/model_train/AUDITORIA_RL.md`, `worklog.md`
nem o arquivo não relacionado `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.
Esses caminhos permanecem fora do stage. Nenhum outro caminho de produção está
autorizado.

Depois de verificar os cinco blobs, executar uma vez a suíte completa, solo e
serial, em `backend/`:

```sh
set -o pipefail
.venv/bin/python -m pytest -q tests 2>&1 | tee experiments/pass-1/2_full_suite.log
```

Antes da suíte, executar uma vez o selftest sintético do audit, sem abrir CSVs
de corrida: `.venv/bin/python scripts/pass_decision_audit.py --selftest`.
Resultado esperado: `PASS`; qualquer outro resultado é PARE, sem suíte ou run.

A referência contém exatamente estas 20 falhas conhecidas:

```text
tests/test_kappa_sign.py::TestKappaSignProcedural::test_local_sign_correct
tests/test_kappa_sign.py::TestKappaSignProcedural::test_no_spurious_flip
tests/test_mixed_race.py::TestHoldAt::test_hold_car_stays_at_s
tests/test_procedural_track.py::TestDeterminism::test_same_seed_same_track
tests/test_procedural_track.py::TestDeterminism::test_different_seed_different_track
tests/test_procedural_track.py::TestGeometry::test_closure
tests/test_procedural_track.py::TestGeometry::test_spacing_le_4m
tests/test_procedural_track.py::TestGeometry::test_length_range
tests/test_procedural_track.py::TestGeometry::test_kappa_in_range
tests/test_procedural_track.py::TestWidth::test_custom_width
tests/test_procedural_track.py::TestWidth::test_width_range
tests/test_procedural_track.py::TestEnvIntegration::test_env_with_procedural
tests/test_procedural_track.py::TestEnvIntegration::test_start_zones_auto
tests/test_procedural_track.py::TestEnvIntegration::test_race_layer_compatible
tests/test_procedural_track.py::TestFeatures::test_hairpin_produces_tight_corner
tests/test_procedural_track.py::TestFeatures::test_esse_track_variety
tests/test_race_layer.py::TestSplineGeometry::test_subdivision_preserves_length_exactly
tests/test_race_neural_60d.py::TestDeployProfiles::test_profiles_exist_default_race_obs_correct
tests/test_rl_v2.py::test_reference_controller_completes_lap
tests/test_rl_v2.py::test_skidpad_radius_close_to_bicycle
```

Gate da suíte: as 20 falhas acima permanecem as únicas falhas; nenhuma falha
nova; os 12 testes PASS-1 passam. Esperado: 20F/375P/3S. Qualquer diferença
encerra o ciclo antes de R1. Não rodar smokes/testes individuais.

## Comportamento PASS-1 congelado

1. O candidato é o carro mais próximo à frente reconhecido pela camada de
   follow existente: `0 < gap < D_AHEAD_M` (60 m) e
   `abs(Δlat) < LAT_SAME_LINE_M` (2,6 m). Isso mantém a decisão na superfície
   que atualmente produz o follow/cap.
2. O mesmo candidato deve satisfazer `gap >= 15 m` e `abs(Δv) >= 1 m/s` em 15
   amostras consecutivas de 5 Hz (3,0 s). As amostras são as mesmas do CSV.
3. Ao engajar: escolher o lado com maior clearance lateral livre contra os
   demais carros em ±25 m de arco; empates usam clearance da borda e depois
   esquerda (+lat). Alvo de offset é `lat_ego ± 2,5 m`, limitado a 0,5 m da
   borda. O offset passa pelo filtro lateral já existente e o `v_cap` de follow
   é liberado enquanto a tentativa está ativa.
4. Carve-outs: `t < 60 s`; carro fora da pista (`abs(lat) > half_width ×
   OFFTRACK_FACTOR`); e 10 s depois do fim de cada intervalo fora/rejoin.
   Tentativa ativa que entrar num carve-out aborta de volta para follow.
5. Aborto: `gap < 8 m` sem progresso lateral ≥0,5 m; duração >8 s sem troca;
   contato solver no par em tentativa. Troca consumida quando o ego está ≥10 m
   à frente do alvo em distância acumulada. O contato solver entra no controle
   no próximo tick lógico; R3 também será conferido no sidecar de eventos cru
   contra os intervalos de tentativa registrados no log.
6. Os contadores e intervalos de tentativa são apenas stdout (`[pass-decision]`);
   nenhuma coluna, writer ou telemetry CSV é alterada. OFF chama a camada
   legada sem alteração funcional.

## Corridas congeladas e orçamento

Diretório de saída: `backend/experiments/pass-1/`. Os arquivos de saída abaixo
estavam ausentes no preflight; não sobrescrever. Os 3 comandos são sequenciais,
em foreground com `tee`; zero jobs paralelos/background. Fazer novo preflight de
processo órfão e de ausência dos caminhos imediatamente antes de cada run.
Executar cada linha da tabela num shell foreground, sem `&`; `set -o pipefail`
preserva falhas do processo de corrida apesar do `tee`.

Todas as corridas usam o runner em `backend/`, seed 0, 10 carros, 6.000 ticks
lógicos a 10 Hz, `--laps 99` (o limite de ticks encerra a gravação), geometria
`interlagos_v2`, grid F1, `--weather seeded`, `--variance off`, `--rejoin
bearing`; nenhum flag de launch-cap/stagger, anti-glue, prof-repair, pguard,
proj-gate ou machine-only. Professor usa seu `VelocityProfile` frozen (vplan);
`--gov` não muda esse controller. No modo mixed, o grupo edge mantém o
controller default do baseline A2; o caminho misto não consome o flag `--gov`.

| Run | Comando (executar do diretório `backend/`) | Condição |
|---|---|---|
| R1 OFF | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --controller professor --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --variance off --grid f1 --rejoin bearing --out experiments/pass-1/1_R1_OFF.csv 2>&1 | tee experiments/pass-1/1_R1_OFF.log` | obrigatório; flag ausente; após exit 0, schema completo e hash, seu CSV vira o pino baseline de R2 |
| R2 ON | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --controller professor --pass-decision --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --variance off --grid f1 --rejoin bearing --out experiments/pass-1/2_R2_ON.csv 2>&1 | tee experiments/pass-1/2_R2_ON.log` | obrigatório somente após R1 válido; qualquer falha de R1 = PARE |
| R3 mixed | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --mixed professor:2,edge:8 --actor model_train/v10_dagger/dagger_actor_best.keras --pass-decision --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --variance off --grid f1 --rejoin bearing --out experiments/pass-1/3_R3_MIXED.csv 2>&1 | tee experiments/pass-1/3_R3_MIXED.log` | pré-declarado; executar apenas se todos os gates R2 forem verdes |

O baseline histórico de tempo não registra duração de run nos logs adjacentes.
Estimativa conservadora congelada: 20 min por corrida; timeout de cada run =
40 min (2×). Um timeout, sinal ou exit code diferente de 0 é PARE imediato, sem
retry e sem substituir arquivos. Conclusão só é reconhecida por exit 0 + 30.000
linhas de dados completas + SHA-256 registrado. Sinal/process list não substitui
esses critérios. Se qualquer saída existir após interrupção, preservar como
`*_interrupted*` e não reexecutar neste orçamento.

As variáveis relevantes do processo estavam unset no freeze:
`RACE_DIAG_NO_CONTACT_LOG`, `RACE_DIAG_NO_XY`, `RACE_DIAG_NO_RES16`,
`PYTHONHASHSEED`, `TF_CPP_MIN_LOG_LEVEL`. Não as alterar entre suíte/corridas;
registrar novamente no log de execução. Se alguma condição de coleta tornar o
run inválido, PARE.

## Gates congelados

### Schema comum — g1

Cada corrida precisa ter 30.000 linhas de dados, 10 pilotos e 3.000 amostras
por piloto, ticks 0,2,…,5998, intervalo temporal de 0,2 s (tolerância 0,01 s),
com `tick,t_s,drv,speed,s,lat,car_car,offtrack,cum_dist,authority`. R1/R2
também exigem `p_state` e header idêntico byte a byte. Schema/linhas são
verificados fail-loud pelo audit antes de qualquer métrica. A decisão pode
registrar colunas existentes além do conjunto requerido; nenhuma coluna nova
será escrita.

### R2

- **g2 — primário:** pelo menos 5 inversões líquidas de ordem pós-largada
  (`t_s > 60 s`) usando o instrumento atual: `cum_dist` e histerese 10 m,
  amostragem 5 Hz. Reportar também oportunidades/engajamentos/abortos/consumos
  e intervalos de tentativa dos logs.
- **g3 — não piora contra o R1 recém-medido:** contatos 5 Hz `car_car>0` ≤
  `floor(R1 × 1,15)`; hesitações pela regra frozen do runner ≤R1; fora de pista
  ≤R1; cruzamentos de volta ≥R1; mediana de voltas completas (distância
  acumulada/geometry frozen) ≤ `R1 + 2%`.
- **g4 — transferência:** contatos carro-carro e hesitações na primeira volta
  iguais a zero; contatos e hesitações na janela de 10 s pós-reentrada ≤R1.
  Janelas começam no fim de offtrack/rejoin (`offtrack=1` ou authority
  `rejoin`/`recovery_rejoin`) e terminam 10 s depois.
- **g5 — carve-outs:** zero amostras `p_state=DECISION_ACTIVE` em `t<60 s`,
  durante offtrack/rejoin ou nos 10 s pós-reentrada.

### R3 — apenas após todos os gates R2 passarem

- **g6 — campo:** 2 carros professor + 8 edge no CSV; contatos totais 5 Hz
  ≤84; mediana do pace rolante edge ≤140,964 s (`138,2 × 1,02`).
- **g7 — aplicação:** os 2 professores engajam ao menos uma vez cada; zero
  contato solver entre um alvo e um professor durante qualquer tentativa; zero
  hesitações no grupo professor. Verificar tentativas por log e sidecar solver
  `_events.csv`; ausência do sidecar significa zero eventos, conforme writer do
  runner.

## PARE obrigatório

Hash/proveniência divergente; saída preexistente não preservada; processo órfão;
blob do freeze diferente do disco; falha da suíte fora das 20 conhecidas;
schema divergente; qualquer corrida com exit diferente de 0, sinal, timeout,
run parcial ou SHA ausente; falha de qualquer gate; R3 sem aprovação integral
de R2; env/config/pista/pool/cache alterados; edição de código, teste, audit ou
prereg depois do primeiro número; corrida além do orçamento. Qualquer PARE
encerra a execução, sem reparo/retry neste ciclo.

## Saídas e fechamento previstos

- `experiments/pass-1/2_full_suite.log` — única execução da suíte.
- `experiments/pass-1/1_R1_OFF.csv` + log — baseline fresco e novo pino R1.
- `experiments/pass-1/2_R2_ON.csv` + log — tratamento ON.
- `experiments/pass-1/3_R3_MIXED.csv` + log e sidecar de eventos se houver.
- `experiments/pass-1/4_AUDIT_PASS_1.json` — tabelas, gates e hashes pelo
  `scripts/pass_decision_audit.py` v1.0; `--selftest` é sintético e não abre
  corridas.
- `experiments/pass-1/5_EXECUCAO_PASS_1.md` — resultado ponto-a-ponto e
  veredito ao dono.

Após a análise, atualizar uma linha em `PROJECT_STATE.md`,
`model_train/AUDITORIA_RL.md` e `worklog.md`, e registrar handoff de encerramento.
Veredito sem promoção: (a) avaliação mais ampla em mais seeds/pistas, com novo
orçamento; (b) refinar limiares em novo ciclo; ou (c) arquivar. Nenhuma opção é
selecionada/promovida automaticamente.
