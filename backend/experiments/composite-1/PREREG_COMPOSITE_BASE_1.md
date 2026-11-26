# PREREG COMPOSITE-BASE-1 — primeira medição quantitativa da linha Composite

**Versão:** 1.0 · **Estado:** pré-freeze; sem corridas nesta etapa · **Base de código:** `4273e01716c0cc57d063454b4f704acebccf9bb2` (`feat/sanidade-produto`).

## Objetivo e escopo

Medir, pela primeira vez de forma quantitativa e pareada por configuração, a linha Composite (`race`: v10 + residual gated) contra `race-blind` (v10 sem residual), em Interlagos. Monaco é uma comparação secundária, report-only. BASE-1 mede e reporta diferenças; não contém thresholds, promoção, retreino ou decisão de produto.

Esta etapa entrega o prereg, o extrator report-only, seus testes e um registro de `pytest --collect-only`. Não executa corrida, smoke, treino ou inferência do estudante; não altera produção, ledgers, anexo ou cache e não cria commit.

## Proveniência das condições e resolução de perfis

O berço `PREREG_COMPOSITE_MAP_1.md` §(d) fixa `race` vs `race-blind` e as condições canônicas Interlagos/seed 0/weather seeded/variance off/grid f1/rejoin bearing/6000 ticks/99 laps. Os comandos do runner canônico e suas opções estão em `PREREG_PASS_1.md` §§165–177 e `EXECUCAO_YIELD_1C.md` §§19–30.

Há uma particularidade de interface que fica explícita antes dos números: `race_diagnostic.py` é o runner com CSV e sidecar de eventos, mas seu `--profile` não resolve o alias de produto `race-blind`; o caminho `--profile composite` implementa `race`, enquanto `race-blind` é o mesmo ator v10 com `obs_mode=edge`. Isso é confirmado por `race_diagnostic.py` linhas 943–955, 1318–1350 e por `run_race_10_cars.py` linhas 71–87. Os comandos abaixo usam essas duas resoluções equivalentes congeladas; os únicos fatores do contraste são a política/perfil (Composite vs v10 cego). Não usar `--profile race` no diagnóstico: o branch de construção de controller não resolve esse alias corretamente.

## Matriz congelada — quatro corridas, a executar somente após freeze do dono

Todos os comandos partem de `backend/`. Cada corrida será foreground, sem job paralelo, com `set -o pipefail`, `timeout --signal=TERM 2400s` e `tee`. Conclusão válida exige exit code 0, main CSV com exatamente 30.002 linhas físicas (metadado + header + 30.000 amostras de 10 carros a 5 Hz) e SHA-256 registrado para log, main e events. Nenhum dump de treino é solicitado ou gravado. O runner gera o sidecar de eventos como `<main sem .csv>_events.csv`.

Antes de cada comando, confirmar que os três caminhos de saída ainda não existem; não sobrescrever artefatos. Usar os valores de ambiente canônicos sem flags experimentais adicionais.

| Run | Condição | Comando frozen (shell foreground) | Papel |
|---|---|---|---|
| R1 | Interlagos, `race` (Composite) | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-1/1_R1_INTERLAGOS_RACE.csv 2>&1 | tee experiments/composite-1/base-1/1_R1_INTERLAGOS_RACE.log` | primário |
| R2 | Interlagos, `race-blind` (v10 edge) | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-1/2_R2_INTERLAGOS_RACE_BLIND.csv 2>&1 | tee experiments/composite-1/base-1/2_R2_INTERLAGOS_RACE_BLIND.log` | controle primário |
| R3 | Monaco, `race` (Composite) | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --profile composite --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-1/3_R3_MONACO_RACE.csv 2>&1 | tee experiments/composite-1/base-1/3_R3_MONACO_RACE.log` | secundário, report-only |
| R4 | Monaco, `race-blind` (v10 edge) | `set -o pipefail; timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --n-cars 10 --ticks 6000 --laps 99 --track Monaco --seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --out experiments/composite-1/base-1/4_R4_MONACO_RACE_BLIND.csv 2>&1 | tee experiments/composite-1/base-1/4_R4_MONACO_RACE_BLIND.log` | secundário, report-only |

As comparações são deltas absolutos `Composite − race-blind`, sem classificação PASS/FAIL:

| Pista/par | Presos (carros) | Fora (%) | Hesitações | Contatos 5 Hz total | Contatos 5 Hz, t≤60 s | Eventos solver, linhas | Voltas (cruzamentos) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Interlagos: R1 − R2 | a preencher após freeze | | | | | | |
| Monaco: R3 − R4 | a preencher após freeze | | | | | | |

## Métricas congeladas e definições

Entrada de cada corrida: log, main CSV e events CSV. O extrator registra SHA-256 de cada fonte e produz JSON determinístico (`sort_keys=True`), com um hash próprio calculado sobre o JSON canônico sem o campo `metrics_sha256`.

1. **Presos:** reproduzir a fórmula do runner, `race_diagnostic.py` linhas 1762–1801. Para cada carro, janelas `[w0,w0+30)` s com `w0` em passos de 30 s; só considerar janela que contém ao menos uma amostra `offtrack=1`; é preso se `max(abs(lat)) > 20 m` OU `max(cum_dist)-min(cum_dist) < 5 m`. Reportar IDs e contagem de carros presos.
2. **Fora:** `100 × mean(offtrack)` sobre as amostras do main CSV, arredondado a uma casa decimal, como o resumo do runner (linhas 1796–1799).
3. **Hesitações:** reproduzir literalmente o resumo do runner (linhas 1803–1822): por piloto, ordenar por `t_s`, reter `t_s > 20 s`, contar sequências contíguas `speed < 0,5 m/s` com duração `(t_s do primeiro sample não-lento − t_s do primeiro sample lento)` em `[0,3, 3,0)` s; se a sequência chega ao fim, usar o último `t_s` disponível.
4. **Contatos por par:** no sidecar, contar linhas de ponto de contato do solver por par não ordenado `(drv_a, drv_b)` (normalizar a ordem lexical); são pontos/substeps do solver, não contatos físicos deduplicados. Reportar também número total de linhas de eventos.
5. **Contatos 5 Hz e janela inicial:** no main, `car_car > 0` é uma amostra carro-tick, conforme `race_diagnostic.py` linhas 1755–1760 e `mixed_summary` linhas 385–401. Reportar o total dessas amostras e o subconjunto com `t_s <= 60 s`, exatamente como solicitado. O rótulo `t≤60 s` significa a janela inicial até 60 s; não é a convenção histórica `post_launch` do runner, que usa `t_s > 60 s`.
6. **Voltas:** por piloto, contar cruzamentos de volta quando `s[k] < s[k−1] − 2000 m`, reprodução da definição em `mixed_summary`, linhas 406–414; reportar dicionário por piloto e total.

Schema mínimo do main: `tick,t_s,drv,s,lat,cum_dist,speed,offtrack,car_car`; do events: `sub,drv_a,drv_b` (arquivo sem eventos pode ser representado como zero linhas com header, mas o gate operacional ainda exige que o sidecar exista); do log: resumos históricos de fora/presos/hesitações e conclusão/saída. Schema ausente/incompatível deve falhar antes de produzir métricas. Métrica repetida em duas leituras dos mesmos bytes deve ser idêntica.

## Calibração histórica A-OFF (não é um braço novo)

Fontes frozen já publicadas: `A_OFF.log` SHA-256 `af7bcb67e09d2486fa295519b84fcf9f5776eee6d9de105819b4d373cbd472db`; `A_OFF_main.csv` `38607bf1154abf5c149cb4b33a85e3bb9fffd96b1eb5134eb7f5051673c70965`; `A_OFF_main_events.csv` `1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54`. Summary publicado: presos `10/10`, fora `25,2%`, hesitações `14`.

O gerador histórico foi localizado: `model_train/race_diagnostic.py` linhas 1762–1822; as definições 1–3 acima replicam o código publicado. Os testes confrontarão célula a célula `stuck_cars=10/10`, `offtrack_pct=25.2`, `hesitations=14` tanto com o summary registrado quanto com os valores recomputados do CSV. Isso calibra a reprodução das fórmulas; não transforma o A-OFF (`variance grid,compound`) em comparação pareada com os quatro runs (`variance off`). Eventos e métricas adicionais são descrições novas, não parte do summary histórico.

## Testes e registro da coleta

`tests/test_base_metrics.py` cobre as fórmulas com fixtures sintéticos e valida a calibração nos bytes A-OFF após o prereg ser salvo. `scripts/base_metrics.py` é report-only; não importa engine/controller nem modifica fontes. Reexecutar duas leituras apenas para provar determinismo do extrator.

Executar apenas compilação Python, testes focados do instrumento e `pytest --collect-only -q` da suíte; não executar a suíte completa nesta etapa. Registrar a saída da coleta em `experiments/composite-1/0_base_metrics_collect_only.log`, com total coletado e pin de referência `20 failed / 423 passed / 3 skipped` do último log da suíte. Qualquer mudança de produção, corrida, treino, extração de corpus ou edição após começar a ler os números de A-OFF encerra a etapa.

## Etapa A2 — emenda dono (índice findall + pin)

Causa raiz do PARE da etapa A: `re.findall` com padrão de grupo único devolve lista de strings (`'10'`), não tuplas; `int(matches[...][0][0])` lia o primeiro caractere (`10`→`1`, `14`→`1`). As regexes `\d+` e os bytes A-OFF (`A_OFF.log` `af7bcb67…` / `A_OFF_main.csv` `38607bf1…` / `A_OFF_main_events.csv` `1f79529e…`) estavam corretos. A emenda normaliza o resultado do `findall` antes de indexar; o offtrack (dois grupos, unpacking direto) permanece intacto.

Varredura de classe no leitor: o indexing `[0][0]`/`[0][1]` sobre `findall` existia só nas duas células de grupo único (presos/hesitações) e foi substituído pelo helper `_findall_capture`; zero ocorrência restante dessa classe. O offtrack continua com unpacking de tupla de dois grupos.

Esta é o 6º PARE da linha no leitor (1B, 1C, 1D, 1E, 1H, A2) — nunca nos dados. Emenda pré-freeze autorizada pelo dono no leitor. A regra «não editar após abrir A-OFF» volta a valer a partir do freeze assinado pelo dono.

Referência de pin da suíte: g0 1G, `0_full_suite_collect_1g.log` SHA `369874d3490956c53e651c9456590fb594121a2b552792f79c422a6b4a6d2357` → `20 failed / 423 passed / 3 skipped`.

## PARE obrigatório

Parar diante de corrida divergente; resultado métrico não determinístico entre leituras dos mesmos bytes; schema incompatível; treino ou inferência do estudante; qualquer corrida além das quatro declaradas; commit; alteração de ledger/anexo; instalação de pacote (`pip`); ou tentativa de promoção/threshold. Artefatos desta etapa permanecem sem commit para o freeze do dono.

## Etapa B.1 — emenda operacional do dono (lançamento pré-formal abortado e quarentena)

Entre 20:40 e 20:47 de 2026-10-26, antes do turno formal, ocorreu um g0
completo e um lançamento R1 com proveniência quebrada. Bytes verificados
pelo dono: `1_R1_INTERLAGOS_RACE.log` com exatos 42 bytes (apenas o banner
`pybullet build time: Sep 11 2026 21:22:29`; o `tee` quebrou na largada —
sem sumário do runner e sem prova de exit code), `1_R1_INTERLAGOS_RACE.csv`
com 30.002 linhas físicas completas (última linha tick 5998, t_s 599,8;
metadado canônico `race_diag_v3_4_xyraw`,
`track_frozen_sha256=164876196eb12174`, `weather_transitions=[]`,
`variance=off`) e events sidecar completo. A física correu até o fim; a
cadeia de proveniência está quebrada, logo o gate frozen não pode ser
certificado para este lançamento.

Decisão do dono, registrada antes de qualquer número formal:

1. O g0 de registro é o log existente SHA
   `db0abd330786cbfcae605fe3b19c9e5d78c74506da2849f1118a08b537e67561`
   (20 failed / 430 passed / 3 skipped, 453 testes, fail-set idêntico ao
   g0 1G `369874d3…`), validado e commitado pelo dono; não é re-executado.
2. Os três bytes R1 do lançamento abortado vão para quarentena em
   `experiments/composite-1/quarantine_base_1_prelaunch_20h44/` com SHAs
   registrados (main `8872feb3e9a7c62963423f3c9fe5b7c5f2dfa91cad6f1d18cac0489a369844bd`,
   events `0fb20fc74d84d5809c96e756d8a801bf6aecc98a25927c74d8e7fef27e69a32d`,
   log `8e95cc79f36d6fd99667f69e2d49cddb14745460e8e7e52c8a1bf5b91ba38134`),
   NUNCA lidos para métricas e NUNCA usados como proveniência de corrida.
   A verificação estrutural do dono (contagem de linhas, última linha,
   metadado, header do events) é declarada e não constitui leitura de
   métrica.
3. A corrida R1 formal executa UMA vez, com o comando frozen da matriz e
   caminhos novos; se o gate falhar, PARE sem nova repetição. R2–R4 seguem
   o protocolo frozen. Total de execuções R1 neste ciclo: 2 (1 abortada +
   1 formal); o orçamento formal continua sendo 4 corridas com gate
   aprovado, executadas uma de cada vez, nunca em paralelo.
