# PREREG COMPOSITE-CORPUS-1 — instrumentação do corpus medido

## Escopo congelado

Este ciclo é report-only. O contrato único é o v15 residual gated:
solo v10 congelado, `res_inputs[N,16]` e `r_targets[N,2]`. A linha v14 traffic
fica fora. Não foram executados treino, épocas, inferência de modelo,
simulação, corrida, smoke ou suíte completa; o teste focado abaixo valida
somente funções puras do instrumento.

As ações observadas `th`, `brk` e `steer_rad` dos CSVs são ações do estudante.
O conversor não as lê para formar alvos. O alvo é exclusivamente:

`r_target = atanh(clip(a_professor, -0.98, 0.98)) - m_solo`

onde `a_professor` é produzido por replay determinístico sobre estado
reconstruído e `m_solo` é o forward NumPy previamente produzido pelos artefatos
v10 pinados. O módulo novo não carrega Keras/NPZ, não executa o forward e não
reconstrói estado por aproximação silenciosa.

## Fase 0 — censo frozen por arquivo

O instrumento leu cada fonte pelo conteúdo do arquivo, não pelo nome:

`backend/experiments/composite-1/1_CENSO_COMPOSITE_CORPUS_1.json`

- SHA-256 do censo: `fcd29503d41bd3ae90c9589e591af10fde5d23d68817bfba9299428850474df8`;
- versão do instrumento: `composite-corpus-v1`;
- manifest de referência: `backend/experiments/trafego-med-1/1_MANIFEST_TRAFEGO_MED_1B.json`;
- fontes censadas: 38;
- elegíveis para conversão direta: 0;
- rejeitadas: 35;
- excluídas como agregados/relatórios: 3.

O censo confere SHA de disco contra o manifest quando a fonte é classificada
no manifest, exige os campos race-timeseries, e compara `geometry_id` e o
fingerprint de geometria embutido no comentário inicial com os pins do
manifest. Os arquivos `diag-largada` são reportados explicitamente como
`source_sem_blob_head`; não foram misturados com fontes tracked.

Resultado substantivo: o raw rejoin e as fontes de largada possuem telemetria
`res16d`/legada e observações `obs0..obs22`, mas não possuem o estado
reconstruído edge+traffic, `geometry_id` por linha nem os sinais 12-D
necessários. Agregados de fase, janelas, hesitações e relatórios não são
fontes de ação e foram excluídos, não convertidos.

## Fase 1 — contrato de saída

### Estado por linha

Uma linha só entra depois de uma reconstrução externa fornecer, explicitamente:

```text
run, drv, tick, t_s
geometry_id, geometry_sha256
track_id, compound_id
telemetry_edge_34[34]
ctx[2]
traffic_features_12[12]
speed_mps, curvature_ahead
previous_steer, previous_longitudinal
```

O layout residual é exatamente:

| Índices | Campo | Escala |
|---|---|---|
| 0–11 | três slots × quatro sinais de tráfego | fórmula `compute_traffic_features` |
| 12 | velocidade ego | `speed_mps / 100` |
| 13 | curvatura à frente | `curvature_ahead * 25` |
| 14 | esterço anterior | `previous_steer` |
| 15 | ação longitudinal anterior | `previous_longitudinal` |

O módulo preserva também a telemetria edge 34-D, `ctx`, IDs de pista e
composto, run, driver, tick, tempo, geometria e split. Não há fallback para
23-D, 46-D incompleto, zero-fill de tráfego, ou reconstrução por nome de
arquivo.

### Replay do professor

`scripts/composite_corpus.py:professor_replay` recebe uma função pura de
estado reconstruído e executa cada estado duas vezes, rejeitando qualquer
diferença. A função de replay deve depender somente de `s`, velocidade,
lateralidade, tráfego e `v_profile` congelado; um estado ausente, fora de
ordem ou não determinístico rejeita a fonte. Nenhuma ação gravada no CSV é
usada como label.

### Split e proveniência

O split é por episódio `(run, drv)`, nunca por linha. A regra congelada,
aplicada por SHA-256 do identificador do episódio, é 80% train, 10%
validation e 10% test. O conversor rejeita tick duplicado ou fora de ordem
dentro do episódio.

Cada dataset/shard deve carregar `run`, `drv`, o SHA Git da fonte quando
existir, `geometry_id`, `geometry_sha256`, a versão do instrumento e seu
checksum. O schema JSON é `composite-corpus-v1`, com dimensões 34/16/2,
regra de split e registros. O audit JSON registra contagens por split e
SHA-256 canônico do dataset. A escrita é determinística (`sort_keys` e
separadores fixos).

Fontes `SEM_BLOB_HEAD` exigem, em ciclo separado, force-add da fonte original
em commit próprio antes da conversão, ou exclusão explícita do subcorpus.
Este ciclo escolhe exclusão: nenhuma fonte sem blob entra no dataset.

## Fase 2 — implementação e selftest

Arquivos novos deste freeze:

- `backend/scripts/composite_corpus.py` — censo, contrato de 16-D, replay
  determinístico, split por episódio, conversão e audit/checksum;
- `backend/tests/test_composite_corpus.py` — sete testes focados;
- `backend/experiments/composite-1/1_CENSO_COMPOSITE_CORPUS_1.json` — censo
  produzido pelo módulo.

Selftest pré-declarado: duas linhas sintéticas do episódio
`synthetic-run/ALO`, ticks 1 e 2, telemetria 34-D zero, tráfego 12-D zero,
geometria `interlagos_v2` pinada e ações professorais `[0.4,-0.2]` e
`[0,0]`. O teste verifica largura 16-D, replay determinístico, rejeição de
ordem e de hash de geometria, split estável, checksum e a não utilização das
ações CSV `th/brk/steer_rad`.

Execução permitida e realizada, no venv nativo:

```text
cd /home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend
.venv/bin/python -m pytest -q tests/test_composite_corpus.py
7 passed in 0.04s
```

Não houve execução de produção, ambiente, modelo ou simulação.

## Fase 3 — veredito

**Impedimento técnico confirmado.** O contrato de instrumentação está
implementado e testado, mas nenhuma fonte medida é elegível para conversão
direta: falta reconstruir edge+traffic, IDs/geometry por linha e replay
professoral determinístico; as fontes de largada também não têm blob Git.

O próximo ciclo só pode ser `COMPOSITE-BASE-1` depois de uma decisão do dono
sobre reconstrução/proveniência e de um prereg que congele os shards gerados.
Não há autorização neste ciclo para resolver essas lacunas, treinar ou rodar
qualquer baseline.
