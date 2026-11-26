# PREREG PASS-PARITY-1 — paridade pré-engajamento do `--pass-decision`

**Status:** freeze preparado; números de R2' ainda não abertos.  
**Tipo:** fix opt-in, um fator; uma corrida ON; sem promoção.  
**Decisão anterior:** PASS-DIAG-2, Q1 apontou divergência de trajetória em
13,6 s, antes da primeira tentativa a 78,4 s. O ramo (c) foi ratificado: a
paridade pré-engajamento é pré-requisito; R1 OFF permanece o baseline pinado.

## Fase 0 — localização read-only

A leitura de `git show 3abb98d` localizou a diferença de wiring em
`backend/model_train/reference_controller.py:605-613`, no `action()`: com a
flag ligada, o ramo chama `_pass_decision_layer` a cada tick desde o começo da
corrida; com a flag desligada, chama `_pass_layer`. O parser de
`_pass_decision_layer` ainda acumula `candidate_samples` antes de iniciar uma
tentativa. Isso torna a troca global da máquina a hipótese causal primária
para a divergência pré-engajamento.

No runner `backend/model_train/race_diagnostic.py:437-492`,
`ProfessorRaceController.predict_batch()` também lê o cursor de contatos,
atualiza a trava de rejoin e passa contexto sob a flag ON. Essa telemetria não
alimenta a física diretamente; será preservada e não será usada para alterar o
caminho de ação antes do engajamento. Não foi encontrado draw de RNG da decisão
de passagem. O cursor de contatos e a trava de rejoin são bookkeeping já
existente do gate; a decisão nova não altera o caminho físico até receber o
alvo de engajamento.
Mesmo se a causa anterior não for única, o fix é por construção: a chamada de
ação pré-engajamento volta ao legado.

## Fix congelado — lazy-legacy

1. Até o primeiro engajamento da decisão nova, `ReferenceController.action()`
   chama `_pass_layer(s, v, lat_signed, traffic, v_plan)` com os mesmos
   argumentos e mantém a sequência de atualização de offset já existente.
   Nenhum draw, escrita nova no estado de controle ou mudança de ordem da ação
   é permitido nesse trecho.
2. O runner avalia o predicado em amostras 5 Hz somente por leitura: 15 amostras
   consecutivas, mesmo alvo mais próximo à frente dentro de `D_AHEAD` e na
   mesma linha (`|Δlat_assinado| < LAT_SAME_LINE_M`), gap `>=15 m`,
   `|Δv|>=1 m/s`, tempo `>=60 s` e `allowed=True`. Os 14 snapshots anteriores
   vêm da lista `rows` já usada pelo writer; o snapshot corrente vem da leitura
   que o runner já faz para construir o tráfego. Como `lat` no CSV é magnitude
   sem sinal (`race_diagnostic.py:1599-1607` no código base), a janela recompõe
   `(s, lat_assinado)` com `body_x/body_y/ns_raw` e a geometria congelada, sem
   alterar o writer nem criar buffer de estado. A projeção reconstruída precisa
   reproduzir `s` e `|lat|` do registro dentro de `1e-6`; divergência aborta o
   run (checagem de integridade, não métrica).
3. No primeiro tick que satisfaz o predicado, o runner entrega
   `decision_engage_target`. O controller confirma o mesmo candidato, engaja
   naquele tick e mantém a máquina nova permanentemente, inclusive após abortos.
   Se a confirmação divergir, lança erro e a corrida é inválida.
4. OFF mantém a chamada legada sem alteração. Writer, CSV, eventos, ambiente,
   física, observações, pools, caches e geometria não são modificados.

Arquivos autorizados neste freeze: `backend/model_train/reference_controller.py`,
`backend/model_train/race_diagnostic.py`, `backend/tests/test_pass_decision.py`,
`backend/scripts/pass_parity_1_audit.py`, este prereg e o manifesto. Qualquer
outro diff de produção é PARE; documentos locais já alterados antes do ciclo
permanecem fora do freeze.

## Fontes congeladas e proveniência

O manifesto `1_MANIFEST_PASS_PARITY_1.json` é a fonte dos pins de entrada do
audit. R1 é Tier B: SHA-256 do arquivo histórico em disco, conferido antes do
run e novamente na abertura do audit. A geometria e o código de base são Tier A:
geometria conferida com `git show 3abb98d`; o código de produção de referência é
o commit `3abb98de95fa08b2b06b2ae922bb98d693cb9e5e`. O log da suíte é Tier B,
pinado pelo SHA no manifesto. Os documentos PASS-1 listados no manifesto fixam
configuração e interpretação do baseline.

Antes do run, verificar que o código/prereg/testes congelados estão no commit do
dono e que `git show <commit>:<path>` é byte-idêntico ao disco. Verificar também
os hashes Tier B/Tier A do manifesto. O instrumento `pass_parity_1_audit.py`
obtém o pin R1 do manifesto; nenhum hash de corrida é digitado no script.
Os arquivos em `experiments/` são ignorados para arquivos novos por
`.gitignore:56`; o dono deve incluí-los explicitamente no commit de freeze.

## Suíte pré-run — g1

Executar uma vez, serialmente, em foreground, de `backend/` após a verificação
do commit e antes da corrida:

```sh
set -o pipefail
.venv/bin/python -m pytest tests/ -q 2>&1 | tee experiments/pass-parity-1/0_full_suite.log
```

Referência congelada: `experiments/pass-1/2_full_suite.log`, SHA-256
`89b37f27680092414c7480052b98dc74338ac9fc0c6dc0319ab0d8f6d770905b`, com
20 falhas conhecidas, 375 passes e 3 skips. O gate aceita apenas os mesmos 20
node IDs de falha; os três testes novos devem passar. Contagem esperada se nada
mais mudar: 20F/378P/3S. Qualquer falha nova, node ID novo, ou falha em teste
novo é PARE antes da corrida. A suíte não é repetida neste ciclo.

Um teste unitário bloqueia o predicado por N ticks e compara hashes do estado
mutável OFF/ON após cada chamada; a configuração ON/OFF fica fora do hash. Os
testes da máquina já existentes continuam cobrindo os gates de limiar, lado,
abortos e carve-outs. Um selftest sintético do audit também roda como teste,
sem abrir CSVs de corrida.

## Corrida única

O orçamento é exatamente uma corrida: R2' ON com a configuração congelada de
R2 do PASS-1; R1 OFF é reutilizada, não reexecutada. Comando de `backend/`, em
foreground, sem job paralelo/background:

```sh
set -o pipefail
timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py --controller professor --pass-decision --ticks 6000 --laps 99 --track interlagos --seed 0 --weather seeded --variance off --grid f1 --rejoin bearing --out experiments/pass-parity-1/1_R2_PRIME.csv 2>&1 | tee experiments/pass-parity-1/1_R2_PRIME.log
```

A duração conservadora usada no PASS-1 foi 20 min; timeout pré-declarado 40
min. Preservar o ambiente do PASS-1; em particular, não alterar
`RACE_DIAG_NO_CONTACT_LOG`, `RACE_DIAG_NO_XY`, `RACE_DIAG_NO_RES16`,
`PYTHONHASHSEED` e `TF_CPP_MIN_LOG_LEVEL`; todos estavam unset na referência.
Se algum estiver set no preflight, PARE. Antes da corrida, confirmar ausência
de processo órfão e ausência dos caminhos de saída. Saídas frescas esperadas:
`1_R2_PRIME.csv`,
`1_R2_PRIME.log` e `1_R2_PRIME_events.csv`. Qualquer interrupção, código de
saída diferente de zero, timeout ou saída parcial encerra o orçamento; preservar
qualquer parcial como evidência e não repetir. Suíte, corrida e audit são
sequenciais, sem paralelismo. Preservar as variáveis de ambiente do PASS-1.

## Gates da corrida — g2/g3

Executar o audit offline, apenas após exit 0 e CSV completo:

```sh
.venv/bin/python scripts/pass_parity_1_audit.py \
  --r1 experiments/pass-1/1_R1_OFF.csv \
  --r2 experiments/pass-parity-1/1_R2_PRIME.csv \
  --log experiments/pass-parity-1/1_R2_PRIME.log \
  --manifest experiments/pass-parity-1/1_MANIFEST_PASS_PARITY_1.json \
  --output experiments/pass-parity-1/2_AUDIT_PASS_PARITY_1.json
```

- **g2 — prova real:** R1 deve corresponder ao pin Tier B do manifesto; os
  headers e as chaves `(tick, drv)` devem ser completos e idênticos. Para todo
  registro com `t_s < t*`, a linha de dados integral, byte a byte, deve ser
  idêntica entre R1 e R2'. `t*` é a primeira amostra 5 Hz `p_state=DECISION_ACTIVE`
  e deve ser `>=60 s`. A primeira linha divergente deve estar em `t*`; nessa
  amostra deve haver `DECISION_ACTIVE`. Qualquer divergência antes de `t*`,
  divergência ausente em `t*`, ou ausência de `t*` é FAIL/PARE.
- **g3 — operação e carve-outs:** log registra pelo menos um engajamento e uma
  tentativa (fechada ou ainda ativa); soma de tentativas registradas coincide
  com o contador `engaged`; todo início é `>=60 s`; início do primeiro registro
  coincide com `t*`. Nenhuma amostra `DECISION_ACTIVE` pode ocorrer em `t<60 s`, off-track,
  authority `rejoin/recovery_rejoin` ou até 10 s após a janela de off-track/
  rejoin. Ausência de tentativa ou violação é FAIL/PARE.
- A R2 original do PASS-1 pode ser mencionada somente como contexto histórico;
  não participa do gate pareado nem altera o veredito.

## PARE e fechamento

PARE obrigatório: pin divergente; commit/blob diferente do disco; diff fora da
lista autorizada; suíte com falha nova; R2' divergente de R1 antes de `t*`;
`t*<60 s`; primeira divergência fora da amostra `t*`; g3 sem tentativa ou com
carve-out; falha/interrupção/timeout; saída parcial; segunda corrida; ou mudança
em ambiente/física/observações/pools/caches/geometria.

Após a medição, registrar gates e hashes em
`EXECUCAO_PASS_PARITY_1.md`, produzir o veredito para o dono e adicionar uma
linha em `PROJECT_STATE.md`, `AUDITORIA_RL.md` e `worklog.md`; encerrar o
handoff. Decisão esperada ao dono: (a) paridade provada → PASS-2 no ciclo
seguinte (timeout 8→10 s, g2 consumo do par-alvo, uma corrida ON reutilizando
R1); (b) paridade não provada → PARE com causa. Sem promoção.
