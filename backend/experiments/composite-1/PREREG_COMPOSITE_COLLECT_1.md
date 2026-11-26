# PREREG COMPOSITE-COLLECT-1

## Escopo e congelamento

Este ciclo coleta, de forma opt-in, duas corridas para o corpus do Composite
v15 residual-gated. Não há treino, fine-tune, inferência offline ou alteração
de física, ambiente, observação principal, pool, cache, pista ou decisão. O
gravador usa somente a API já carregada pelo runner e permanece desligado sem
`--corpus-dump`.

O código de referência é o commit que o dono congelar antes da execução. O
instrumento é `scripts/composite_corpus_dump.py`, integrado somente em
`model_train/race_diagnostic.py`; a saída é JSONL gzip determinístico usando
apenas a biblioteca padrão. O reparo 1B altera somente a resolução do
`compound_id` no caminho de captura e sobe o instrumento para
`composite-corpus-dump-v3` no ciclo 1C.

## Contrato do dump

Cada arquivo começa com um registro `_schema=composite-corpus-dump-v3` e então
uma linha por piloto por tick lógico, antes da ação daquele tick:

`run`, `drv`, `tick`, `t_s`, `geometry_id`, `geometry_sha256`,
`instrument_version`, `track_id`, `compound_id`, `telemetry_edge_34[34]`,
`ctx[2]`, `traffic_features_12[12]`, `speed_mps`, `curvature_ahead`,
`previous_steer`, `previous_longitudinal`.

As 34 dimensões são as 23 dimensões de telemetria mais os 11 raios do mesmo
builder edge usado pelo controller neural. As 12 dimensões de tráfego vêm
exclusivamente de `compute_traffic_features`. As ações anteriores pertencem
ao gravador e são atualizadas depois da ação do tick; elas não retornam ao
simulador. Vetores com largura errada, valores não finitos, ticks duplicados ou
fora de ordem abortam a execução.

Pinos de geometria:

| geometry_id | SHA-256 |
|---|---|
| `interlagos_v2` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| `monaco_v2` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |

## Fase 0: pino de Monaco e pré-condições

O replay Monaco arquivado em
`experiments/rejoin-tel-2/2_replay_rejoin_tel2_monaco_s0_v35.csv` foi gerado
por comando congelado e terminou com exit 0. O gate g1b é estrutural (emenda do dono): cada dump responde pela própria
config — 10 pilotos × 6000 ticks = 60000 linhas de dados, sem duplicação ou
lacuna por piloto, e geometria/sha conformes. A comparação byte-a-byte com o CSV Monaco arquivado não é usada
porque o novo dump é um artefato lateral e a configuração histórica não
reproduz o arquivo principal como parte deste ciclo.

Antes das corridas, o dono deve verificar o blob deste prereg e do código,
além de conferir o comando flag a flag. Nenhuma corrida ocorre antes desse
freeze.

### Mapping de compostos congelado (1C)

`model_train/mappings.pkl` contém as chaves de topo `drivers`, `tracks` e
`compounds`. A chave `compounds` é um dicionário `str -> int` e recebe o
suplemento congelado abaixo:

```text
{"SOFT": 0, "INTERMEDIATE": 1, "MEDIUM": 2, "HARD": 3}
```

O mapping efetivo é `mappings.pkl["compounds"] ∪ {"HARD": 3}`. A união falha
se houver colisão com outro id; os ids existentes não são renumerados. O
gravador carrega esse mapping uma vez por corrida e resolve
`state.tyre.model.compound` pelo valor do enum. Composto `None`, objeto sem
valor, `WET` ou qualquer nome ausente no mapping gera `ValueError` fail-loud;
não existe fallback para `0`. O mapping 1B permanece como backup de pureza de
rótulo: a suplementação instrumental não altera labels nem o contrato do
professor-replay.

## Fase 1: gates

**g0 — suíte.** Uma execução solo da suíte no estado commitado. Base
conhecida: 20F/380P/3S, mais os 7 testes de CORPUS-1, os 11 do gravador/JOIN
anteriores e os testes 1B com tipos reais de pneu e falha louda. Os totais
EXATOS pinados por `--collect-only` após a emenda 1E são **430 testes**; a
execução g0 deve reproduzir 20F / 407P / 3S (a emenda 1E soma 7 testes ao
berço 1D: ordem por grid, retrocesso de tick, duplicidade, três formas
inválidas de metadata e piloto fora da lista). Divergência ou FAILED canônico
novo é PARE.

**g1a — Interlagos: paridade do gravador contra pino NOVO (EMENDA DO DONO).**
O R1 `5cb49097…` é controller professor — uma corrida
`--controller neural --profile composite` nunca pode casar com ele; o gate
antigo era impossível. Nova cadeia: (run 1, A-OFF) a MESMA config neural/
composite SEM `--corpus-dump` — nasce o pino neural/composite que o acervo
não tinha, commitado como baseline; (run 2, A-ON) mesma linha + `--corpus-dump`
— main CSV BYTE-IDÊNTICO ao pino A-OFF (gravador inerto; determinismo do env
já provado pela R2-Y2) + dump completo: grid da config × 6000 ticks, contagem
exata declarada na abertura (grid g1 = 10 pilotos → 60000 linhas) + cabeçalho.
`--pass-decision`, `--leader-yield` e flags experimentais adicionais ficam
ausentes nas duas corridas.

**g1b — Monaco (gate estrutural normalizado pela EMENDA DO DONO).** Uma
corrida foreground, solo, com a config Monaco congelada na abertura
(controller neural, profile composite, `--corpus-dump`). Contagem estrutural
declarada ANTES do run a partir da própria config (grid × 6000 ticks; grid
g1 = 10 pilotos → 60000 linhas); a frase "20 pilotos no conjunto dos dois
runs" sai — cada dump responde pela própria config. Geometria Monaco pinada.
Sem pino arquivado de neural em Monaco: o CSV main + log DESTE run entram no
commit ciclo como NOVO pino (âncora de reprodução futura fora do Interlagos).
Contagem de família rejoin no audit é DISCLOSURE, não PARE (só schema/
conversão são PARE).

Cada corrida tem orçamento unitário: sem jobs paralelos, sem retry, e conclusão
somente por exit 0, contagem exata de linhas e SHA-256 do CSV, log e dump.
Timeout, sinal, exit diferente de zero, dump parcial ou hash ausente é PARE.

## Comandos congelados

Todos os comandos são executados a partir de `backend/`, em foreground, uma
por vez, com `set -o pipefail`, `timeout --signal=TERM 2400s` e `tee`. A-OFF e
A-ON são flag-a-flag idênticos, exceto pelo `--corpus-dump` e pelos caminhos
de saída. B-ON troca somente a pista e os caminhos para a configuração Monaco.

```bash
set -o pipefail
unset RACE_DIAG_NO_CONTACT_LOG RACE_DIAG_NO_RES16 PYTHONHASHSEED TF_CPP_MIN_LOG_LEVEL
timeout --signal=TERM 2400s env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track interlagos --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --out experiments/composite-1/A_OFF_main.csv \
  2>&1 | tee experiments/composite-1/A_OFF.log
```

```bash
set -o pipefail
unset RACE_DIAG_NO_CONTACT_LOG RACE_DIAG_NO_RES16 PYTHONHASHSEED TF_CPP_MIN_LOG_LEVEL
timeout --signal=TERM 2400s env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track interlagos --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --corpus-dump experiments/composite-1/A_ON_dump.jsonl.gz \
  --out experiments/composite-1/A_ON_main.csv \
  2>&1 | tee experiments/composite-1/A_ON.log
```

```bash
set -o pipefail
unset RACE_DIAG_NO_CONTACT_LOG RACE_DIAG_NO_RES16 PYTHONHASHSEED TF_CPP_MIN_LOG_LEVEL
timeout --signal=TERM 2400s env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track Monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --corpus-dump experiments/composite-1/B_ON_dump.jsonl.gz \
  --out experiments/composite-1/B_ON_main.csv \
  2>&1 | tee experiments/composite-1/B_ON.log
```

Cada comando declara 10 pilotos × 6000 ticks lógicos = 60000 linhas de dump,
mais um registro de schema. O A-ON deve ter o mesmo CSV principal byte a byte
que A-OFF; B-ON não tem pino neural prévio e seu CSV/log serão o novo pino.

**g2 — conversão.** Após os dois dumps, `scripts/composite_corpus.py` deve
validar schema, geometria, ordem e checksums, e gerar shards
train/validation/test com split por `(run, drv)` hash, sem vazamento de
episódio. O audit registra hashes dos dumps, origem, versão do instrumento e
contagens POR FAMÍLIA via JOIN (EMENDA DO DONO): classificação RESOLVIDA por
JOIN determinístico (tick, drv) entre o dump e o CSV main da MESMA corrida —
s/lat/speed/offtrack/authority vêm do main CSV (pares commitados na mesma
ordem; hash conjunto registrado); divergência de join (tick/drv ausente ou
desalinhado) rejeita o par (PARE). Função nova no conversor (join +
classificação de famílias + contagens) e testes focados correspondentes
ENTRAM NO MESMO FREEZE, antes de qualquer corrida. O main CSV é a amostra
autoritativa de 5 Hz; ticks extras do dump lógico permanecem no dataset, mas
são registrados como não emparelhados e não recebem rótulo de família. Para
nose-to-tail, o vizinho à frente é o menor gap circular positivo até 40 m,
com diferença lateral absoluta até 2 m, velocidade do seguidor não mais que
2 m/s abaixo da líder e sustentação por 5 amostras JOIN consecutivas. Rejoin
é a transição offtrack→ontrack ou autoridade contendo `rejoin`; hesitação é
velocidade abaixo de 0,5 m/s até 10 s após a reentrada. `unavailable` só é aceito
com causa arquivo:linha de coluna ausente; nada é preenchido por aproximação.
Professor-replay e a geração de `r_targets` exigem duas passadas determinísticas
idênticas; ações gravadas são sempre ações do estudante e nunca alvos.

### Emenda 1D — loader do CSV de produção e stride de pareamento

A causa do PARE 1C foi o header de produção: cada CSV main começa
obrigatoriamente com uma linha `#` de metadados, seguida pelo primeiro header
não-comentado. Os segmentos de metadata são separados por ` | ` e cada
segmento usa somente o primeiro `=`; valores permanecem strings brutas. A
ausência da primeira linha `#` gera `CorpusError` na linha 1, e erros de
colunas/linhas usam o número físico real do arquivo.

O JOIN 1D pareia somente ticks pares (`tick % 2 == 0`), preservando a cadência
stride 2 do CSV de produção. Ticks ímpares do dump são extras e entram na
auditoria, não recebem rótulo. O audit registra `main_csv_metadata` e
`paired_by_drv` com `paired`, `total` e fração por piloto; espera-se 50% por
piloto. As regras, janelas, chaves `(tick, drv)` e totais de famílias não
mudam.

### Emenda 1E — ordem de produção por `grid_order`

O PARE 1D revelou que o CSV de produção é ordenado por `(tick, posição no
grid)`, não por `(tick, drv)` lexicográfico; a ordem observada é determinística
e igual nos dois raws commitados. A metadata deve conter `grid_order` no formato
estrito `['A', 'B', ...]`: colchetes, aspas simples e separador `', '`.
Qualquer ausência ou forma divergente gera `CorpusError: unparseable grid_order`.

A validação de ordem usa `(tick, índice em grid_order)` estritamente crescente.
Duplicatas e retrocessos continuam rejeitados. Todo `drv` presente nas linhas
deve estar na lista; um piloto ausente gera erro explícito. Números de linha
físicos, chaves de duplicidade do dump, metadata, pareamento em ticks pares,
regras de família, janelas e schema v3 permanecem inalterados.

Esta emenda documenta o terceiro caso sintético versus produção: 1B corrigiu
tipos domain, 1D corrigiu o header de metadata, e 1E corrige a ordem do grid.
A conversão posterior consumirá exclusivamente os bytes commitados em
`7ef87c8`, com SHAs pinados; o risco de divergência do writer é zero neste
ciclo. Após os testes, o total da coleta deve ser re-pinada por
`--collect-only`; o pin 1G anterior era 441 testes, após os testes adicionais
de composição do estado e provider frozen. Este ciclo não executa a suíte
completa, portanto não atualiza o histórico de resultados F/P/S.

### Emenda 1F — replay puro do professor e forward solo pinado

O labeler 1F é report-only e não usa ações gravadas do estudante. O professor
recebe estado reconstruído (`s`, `speed`, `lat`, pose/heading, tráfego e
`VelocityProfile` da geometria frozen) e não mantém estado entre amostras.
As linhas de código congeladas que definem a matemática são:

```text
model_train/reference_controller.py:803-810
v_tgt = self._v_target(s, v) * self.margin
if v_cap is not None: v_tgt = min(v_tgt, v_cap)
long_cmd = clip((v_tgt - v) / 8.0, -1.0, 1.0)
steer_rad = atan2(2.0 * self.wheelbase * sin(alpha), ld)
steer_cmd = clip(steer_rad / env.steer_limit_rad(v), -1.0, 1.0)
```

O replay puro usa `VelocityProfile.at(s)`, `margin=0.93`, `GAIN_REF=8.0`,
`wheelbase=3.4`, `lookahead_gain=0.6`, limites de lookahead `[5,45]` m e
as constantes de tráfego da classe `ReferenceController`: `D_AHEAD=60`,
`D_FOLLOW=25`, `V_MARGIN=2`, `V_MIN_FOLLOW=1`, `G_SAFE=6`,
`LAT_SAME_LINE=2.6`, `LAT_CORRIDOR=3.5` e `LAT_OFFSET_MAX=2.5`. O cap é
aplicado somente ao vizinho à frente na mesma linha; o deslocamento lateral
é aplicado diretamente ao ponto de perseguição, sem `_lat_offset`,
`_pass_layer` ou qualquer máquina de passagem.

A conversão física é a inversa exata do método congelado:

```text
model_train/f1_env.py:534-558
throttle = max(long_cmd, 0.0)
brake = max(-long_cmd, 0.0)
steer_rad = steer * steer_limit_rad(speed_mps)
```

O solo é produzido exclusivamente pelo forward linear NumPy do ator v10
`dagger_actor_best.keras`, exportado por `ensure_npz_weights_exist`; para cada
linha são usados `telemetry_edge_34`, `ctx`, `track_ids=zeros` e
`compound_ids=zeros`, conforme o deploy congelado. Professor e solo executam
duas passadas idênticas e qualquer divergência byte-a-byte gera
`CorpusError`. Treino, fine-tune, fitting, inferência do estudante/Composite
e uso de `th/brk/steer` gravados como label permanecem proibidos.

#### Composition do rótulo 1F

Para cada par `(tick, drv)` do JOIN entre os bytes commitados do dump e do
main CSV, `s`, `lat` e `speed` vêm exclusivamente da projeção congelada do
main. A pose é reconstruída pela inversão exata da projeção do ambiente:
`(px,py,ph)=point_at(s)`; `nx,ny=(-sin(ph),cos(ph))`; `x=px+nx*lat`,
`y=py+ny*lat` e `heading=ph`. A convenção é `+lat=ESQUERDA`; a meia-largura
vem de `f1_env.py:414` (`track.width_m/2.0`) e a implementação de projeção é
a de `F1MultiContextEnv._project_on_path`.

O snapshot de tráfego é formado pelas dez linhas completas do mesmo tick do
mesmo main CSV, removendo o ego: `[(s_j, lat_j, speed_j)]`. Essa é a cópia
exata da fonte `f1_env.py:803-808` (`_all_cars_snapshot` e
`traffic_for`), sem leitura do dump para a geometria do estado. O provider
congelado de cada pista fornece `track_len_s`, `half_width`, `point_at`,
`VelocityProfile` e a geometria; o perfil é construído como em
`race_diagnostic.py:542-544`, com `np.array(track.waypoints,float64)`,
`grip_mult=0.788`, `sf=0.80`, `ds_target=4.0` e `smooth_window_m=20.0`.
Os valores verificados são `4160.436950117386` (Interlagos) e
`3335.2345774147834` (Monaco), declarados no audit e nunca substituídos por
constantes locais.

O labeler chama `professor_replay(states, pure_professor_action)` e
`pinned_solo_forward(rows, load_pinned_solo_actor("model_train/v10_dagger/
dagger_actor_best.keras", "model_train/v10_dagger/
dagger_actor_best_weights.npz"))`; o steering usa
`F1MultiContextEnv.steer_limit_rad` (`f1_env.py:530-531`) e o ponto é o
provider usado pelo ambiente. O fluxo final é `convert_reconstructed(...)`,
com split hash por episódio 80/10/10; esta etapa não treina, não executa
inferência do estudante e não escreve shards.

O audit adicional `state_builder` registra a fórmula da pose, a fonte do
tráfego, `sf`, `grip_mult`, `half_width`, `track_len_s` por caso, SHAs dos
arquivos Keras/NPZ e as linhas-fonte citadas, além do `pair_sha256` do JOIN.
Qualquer tick sem exatamente dez drivers, driver duplicado ou driver fora do
snapshot é erro explícito.

#### Composition 1F — provider e CLI

O caller usa exclusivamente `FrozenTrackProvider`, construído por
`domain/track_resolution.py:219-240` via `load_track_frozen(name, strict=True)`
(reexportado em `model_train/f1_env.py:50`); ausência ou corrupção é
fail-loud. As tabelas são copiadas verbatim de `f1_env.py:405-414`:
`_wps_arr`, `_seg_B`, `_seg_AB`, `_seg_len`, `_seg_cum`, `_seg_heading`,
`_track_len_s` e `_half_width=track.width_m/2.0`, sem valores geométricos
hardcoded. `point_at` reproduz `f1_env.py:638-646` (módulo, `searchsorted`
`right-1`, clamp e interpolação); `project_on_path`, usado apenas no
roundtrip de teste/audit, reproduz `f1_env.py:607-625`. A conversão nunca
projeta o estado: `s/lat/speed` continuam vindo do main.

O provider expõe `track_len_s`, `half_width`, `point_at`, `project_on_path`,
`waypoints`, `velocity_profile`, nome, `geometry_id`, SHA de geometria e SHA
do arquivo frozen. Os valores verificados pelas tabelas são
`4160.436950117386` (Interlagos) e `3335.2345774147834` (Monaco), com
tolerância de `1e-6` somente no teste, nunca substituídos por constantes.

`scripts/composite_corpus.py convert-1f` fixa os casos: A usa
`A_ON_dump_interrupted3.jsonl.gz` + `A_ON_main_interrupted3.csv` +
`interlagos`; B usa `B_ON_dump.jsonl.gz` + `B_ON_main.csv` + `Monaco`.
`--source-git-sha256` defaulta para
`7ef87c8f4e880b979c6dc8c77915a8f57356dd03`; `--out-dir` defaulta para
`experiments/composite-1/shards`. Sem `--write`, o comando é dry-run e
imprime somente COUNTS em stdout, sem criar arquivos. Com `--write`, grava
um shard JSON por episódio, com schema `composite-corpus-v1`, ordenação
determinística por `sort_keys`, e um audit JSON por caso contendo metadata
do main, pareamento, famílias, geometria, provenance do state builder e do
provider. O CLI chama `run_teacher_labeling` sem duplicar o labeler; não há
treino, inferência do estudante ou estatísticas distributivas.

**g3 — proveniência.** O commit dos dumps precede o commit dos shards. Cada
shard carrega o run, o blob Git da fonte, geometry_id, geometry_sha256, versão
do instrumento e checksum próprio. Fonte sem blob é rejeitada.

**g4 — zero treino.** Nenhuma época, fine-tune, inferência de treino ou métrica
de treino pode ocorrer neste ciclo.

## Fase 2: fechamento

O fechamento será `EXECUCAO_COMPOSITE_COLLECT_1.md`, contendo comandos
executados, gates, contagens, tamanhos e SHA-256 dos CSVs, logs, dumps,
shards e audit. `PROJECT_STATE.md`, `model_train/AUDITORIA_RL.md` e
`worklog.md` recebem somente a linha de fechamento e permanecem uncommitted;
`backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` permanece intocado.

Veredito:

* dumps conformes e dataset auditado: próximo ciclo `COMPOSITE-BASE-1`;
* qualquer falha de paridade, contagem, conversão, proveniência ou execução:
  PARE, preserve o payload e não repita a coleta neste ciclo.

## Emenda 1H — alocação de split rank-based por corrida

Esta emenda substitui, para a alocação efetiva do labeler, o split por
threshold do hash descrito acima. A causa é que o threshold
`digest[0] % 100 < 80/<90/else` só aproxima as proporções para populações
grandes: nas duas corridas com dez episódios, A produziu 8/2/0 e B 9/1/0,
deixando `test` vazio em ambas. O 80/10/10 do CORPUS-1 é uma proporção.
Esta é a quarta divergência entre caso sintético e produção (1B: tipos de
domínio; 1D: header metadata; 1E: ordem da grade; 1H: população de episódios
versus threshold).

Contrato congelado:

1. `assign_episode_splits(run, episode_ids)` retorna `Mapping[drv, split]`.
   Ordena os episódios por `(sha256 hex completo de "{run}::{drv}", drv)`;
   atribui os primeiros `floor(0.8*n)` a `train`, os próximos
   `floor(0.1*n)` a `validation` e o restante a `test`.
2. Para `n >= 3`, bucket `validation` ou `test` vazio recebe o último item de
   `train` na ordem de rank. Para `n < 3`, lança `CorpusError` com a mensagem
   `cannot split fewer than 3 episodes`. Assim, `n=3` resulta em 1/1/1.
3. O rank é determinístico e estável por corrida: a população de cada corrida
   é independente; adicionar uma corrida futura não muda os buckets existentes.
   O hash usa somente o identificador do episódio, sem valores de amostra.
4. `convert_reconstructed` exige `episode_splits`, com chaves `(run, drv)` e
   split como valor. Ausência do argumento ou de episódio no mapa é
   `CorpusError`; não há fallback para threshold.
5. `split_episode` legado é renomeado para
   `_legacy_threshold_split_episode`, com corpo intacto e sem uso pelo labeler.
6. `run_teacher_labeling` constrói o mapa uma vez com a população de episódios
   do JOIN por corrida e o injeta na conversão.
7. O audit registra `split_rule: "rank-80/10/10-per-run-v1"` e as contagens
   de `train`, `validation` e `test`.

Membership real congelada, a conferir pelos testes (não calcular manualmente):

| Corrida | train | validation | test |
| --- | --- | --- | --- |
| A | PIA, NOR, LEC, HAM, PER, RUS, GAS, ALO | SAI | VER |
| B | PIA, RUS, GAS, LEC, HAM, NOR, PER, ALO | VER | SAI |

Cada caso tem exatamente 30.000 registros, 10 episódios e split_counts
`{train: 24000, validation: 3000, test: 3000}`. O dry-run validado nesta
emenda não grava shards; o relatório registra somente registros, episódios
e contagens dos splits, sem estatísticas adicionais.

Roundtrip de geometria: o teste usa a malha `stableSampler` com ao menos
200 pontos seguros em 4.000. O projetor nearest-segment congelado não é
inversível nos cantos para `lat=±3`; a conversão nunca projeta o estado
(`s/lat -> pose` é forward-only). Esse caveat limita-se ao escopo do teste de
roundtrip e não altera a conversão.

Testes frozen da emenda: dez IDs sintéticos dão exatamente 8/1/1 e são
idempotentes; três IDs dão 1/1/1; dois IDs falham com a mensagem congelada.
Conversão rejeita mapa ausente ou episódio não mapeado e usa o split do mapa.
Regressão do helper legado preserva A em 8/2/0. Os testes A/B conferem a
membership literal acima e os split_counts exatos. Após os testes focados,
executar collect-only para re-pinar a contagem exata da suíte; não executar
suíte completa, treinar, escrever shards ou iniciar corridas neste ciclo.
O resultado `--collect-only` desta emenda é 446 testes coletáveis; os testes
focados report-only passaram 35/35.

## EMENDA DO DONO (2026-10-26, pré-freeze)

Motivo: (1) o g1a original pedia byte-idêntico ao R1 `5cb49097…`, que é
controller professor — impossível com perfil neural/composite. A paridade do
gravador passa a ser provada contra o pino NOVO A-OFF (prova de inertez do
`--corpus-dump`). (2) As famílias de seleção não exigem colunas extras no
dump: o CSV main da mesma corrida fornece a topologia e os marcadores de
rejoin via JOIN (tick, drv). (3) A contagem "20 pilotos no conjunto dos dois
runs" era ambígua; cada dump responde pela própria config. ORÇAMENTO
RENOVADO da linha: até 3 corridas singles (A-OFF pino novo, A-ON
paridade+dump, B-ON Monaco), uma por vez, zero retry; a FASE 0 só reduz o
orçamento para 2 se um pino TRACKED de neural/composite reproduzível no env
atual for citado com hash. Ordem exigida: implementação do JOIN + testes →
o dono commita o freeze ÚNICO → suíte g0 com totais pinados → corridas.
Restrições inalteradas: treino proibido; preenchimento por aproximação é
proibido; nenhum número de treino antes do freeze; mudança em env/física/
obs/pool/cache/pista frozen é PARE.
