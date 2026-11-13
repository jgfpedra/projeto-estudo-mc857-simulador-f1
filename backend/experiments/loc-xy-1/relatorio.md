# LOC-XY-1 — fechamento após E-XY-3 (2026-10-23)

## Fechamento autorizado por E-XY-3

**Status: gates 3, 4 e selftests golden concluídos.** A correção documental
E-XY-3 alterou somente a linha 6 de `PROJECT_STATE.md`, acrescentando o
ponteiro de FAIL-FORENSICS-1b e fechando a entrada com `)`. Commit doc-only:
`29cf2a2`. Regra permanente de autoria: novas entradas de cabeçalho/cadeia já
incluem `Ver <path>` e fecham `)` antes de eventual rebaixamento para
`(anterior:)` no ciclo seguinte.

### Gate 3 — suíte completa

Resultado **20F/352P/3S**, exatamente o ratificado. A lista dos 20 testes
FAILED é idêntica ao baseline: 20 nomes em comum, zero novos e zero ausentes.
O teste legado alterado e os três testes LOC-XY passaram. Log bruto
`5_post_chain_fix_pytest.log`, SHA-256
`7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185`.

### Gate 4 — dois smokes formais, seed 0, Interlagos blind, 6000 ticks

| Prova | Resultado | SHA-256 / evidência |
|---|---|---|
| Smoke A, `RACE_DIAG_NO_XY=1` | CSV inteiro byte-idêntico à âncora v3.3; 30.000 linhas de dados, 49 colunas | Âncora e saída: `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733` |
| Smoke B, kill-switch OFF | Projeção das 49 colunas legadas igual à âncora em header + 30.000 linhas; schema total 52 | CSV completo: `fe5027dcf83fd81bb062443b93e0a0b7b5b8e8f280c916a525c489bcb8003e35`; projeção legada: `ad145f45af4152e5f8097042793a2291b4cffe916ad8c4dd7bd3137a378d00c4` |

A projeção usou `split(',')[:49]` sem biblioteca CSV, incluindo a linha de
nomes das colunas e excluindo somente a linha de comentário de metadados. No
Smoke B, o header termina exatamente em `body_x,body_y,ns_raw`; as 30.000
linhas têm 52 campos, X/Y são floats finitos preenchidos, e `ns_raw` é token
inteiro em `[0,1130]`. O CSV v3.4 completo do Smoke B está versionado. Os
eventos dos dois smokes têm o mesmo SHA-256 da âncora de eventos:
`11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9`.
Logs brutos dos smokes: A `6_smokeA.log` SHA-256
`7807744af36bd5f98544e24cc747bf71bd01b3581ba2fe45c02e9f7843e73906`; B
`7_smokeB.log` SHA-256
`82cc7b07210ef47d6835e1df85bfe5fa3910e7aae39b9692603dc69c1fdca5bc`.

### Selftests golden

Executados após a suíte e os dois smokes. `fail_forensics_verdict.py
--selftest`: PASS, SHA-256 do log
`2112e34309a53dc80ab7771f867560d543d1f4fa31eb9c3cba87f27c4352e100`.
`saidas_verdict.py --selftest`: PASS (4/4 sintéticos, bootstrap e geometrias
Interlagos/Monaco), SHA-256
`430bddf5170d96acb1542992c83b9004712edab989dbaeb99c68eec09da041e3`.

### Escopo, decisão e orçamento final

O diff de produção permanece o de `4d22d65`: leitura read-only de XY do getter
existente e índice da busca global `nearest_segment`; nenhum controle,
governor, física, ordenação, contador ou objeto de simulação foi alterado.
`ns_dist` continua omitido para manter exatamente três colunas novas. E-XY-2
alterou somente o corpo do teste legado; E-XY-3 foi doc-only. Foram consumidos
**2/2 smokes formais**, **zero corridas de medição**, nenhum seed de pool e
nenhuma pista frozen foi modificada. A suíte inclui a corrida curta de 1200
ticks embutida no teste legado, não contada como smoke formal nem medição.

## Retomada sob a errata E-XY-2 (2026-10-23)

O dono ratificou que o teste legado
`tests/test_mixed_composite_wiring.py::test_t_regression_v10_cego_bit_identico`
deve rodar no caminho default v3.4 e comparar a projeção dumb das primeiras
49 colunas (`split(',')[:49]`) por linha, inclusive o header, contra o fixture
pré-wiring v3.3. O mesmo nome e caminho foram preservados; o docstring recebeu
a linha de contrato ratificada. A comparação e a limpeza de CSV/_events
temporários estão no corpo do teste. Os três testes novos, o writer e o loop da
corrida não foram alterados nesta retomada.

**PARE imediato no gate 3:** a suíte completa executada após a edição terminou
em **21F/351P/3S**, não no ratificado **20F/352P/3S**. O teste legado corrigido
e os três testes LOC-XY passaram, mas `tests/test_state_files.py::test_state_files_doc_integrity`
falhou fora do conjunto de 20 falhas canônicas. O traceback aponta a cadeia
`> (anterior:)` do `PROJECT_STATE.md` (linha histórica de FAIL-FORENSICS-1b sem
o sufixo de referência esperado pelo validador). As 20 falhas do baseline
continuam presentes. Como a contagem divergiu, o gate 4 e os selftests golden
pós-código não foram iniciados.

- Log bruto: `4_post_fix_pytest.log` — SHA-256
  `37527575cf3b889d65819f920e6fa0216f00817549674c9fe07e053371f1d675`.
- Resultado do orçamento nesta retomada: zero smokes formais de 6.000 ticks;
  zero corridas de medição; pools intocados; pistas frozen intocadas. A suíte
  incluiu somente a corrida curta de 1.200 ticks já embutida no teste legado.
- **E-XY-2 (aditiva, ratificada):** o caminho default v3.4 exige projeção
  bit-idêntica das 49 colunas legadas; restauração do arquivo completo v3.3
  continua disponível com `RACE_DIAG_NO_XY=1`. A prova do kill-switch segue
  coberta pelo teste (c) e pelo smoke ON do gate 4, ainda pendente.

## PARE original anterior à E-XY-2

**Status: PARE no gate 3.** O CSV v3.4 e os três testes novos foram
implementados, mas a suíte completa revelou uma falha além das 20 falhas
canônicas. O smoke formal de 6.000 ticks do gate 4 e os selftests golden
pós-código não foram iniciados.

## Gatilho do PARE

| Etapa | Resultado |
|---|---|
| Baseline antes do código | 20F/349P/3S |
| Esperado após exatamente +3 testes | 20F/352P/3S, ratificado pelo dono |
| Pós-código | **21F/351P/3S** |
| Diferença | 20 falhas antigas idênticas + 1 falha nova fora do conjunto canônico |

A falha nova é `tests/test_mixed_composite_wiring.py::test_t_regression_v10_cego_bit_identico`.
O teste compara todas as linhas do CSV exportado com um fixture v3.3 de 49
colunas; o exportador agora emite o header v3.4 com as três colunas no fim.
Como a regra do ciclo manda parar diante de qualquer falha fora das 20
canônicas, nenhum gate posterior foi iniciado. O teste legado não foi alterado.

Nota de execução: as suítes completas exigidas pelos gates 1 e 3 executaram
cada uma o subprocesso de corrida de 1.200 ticks do teste legado de
bit-identidade (seed 0, Interlagos blind). O subprocesso pós-código escreveu
temporariamente o CSV e `_events.csv` da regressão; ambos foram removidos ao
encerrar o gate. Isto não é a corrida formal de 6.000 ticks do gate 4 nem uma
corrida de medição.

Os três testes adicionados passaram na suíte:

1. header v3.4 com `body_x,body_y,ns_raw` nessa ordem;
2. `ns_raw` do fixture congelado de Interlagos igual ao argmin auxiliar global;
3. serialização com `RACE_DIAG_NO_XY=1` byte-idêntica ao fixture v3.3.

## Artefatos e hashes

- Baseline de teste: `0_baseline_pytest.log` — SHA-256
  `dba9ff77f808e844be260bcf2a90b4e2ff46d8fff5f08e275ca6415467fdf7e3`.
- Suíte pós-código: `3_post_pytest.log` — SHA-256
  `969628421db6fb3a57e038ef212ea97c017c325da3ae0d5290f24696986fbf6a`.
- Referência blind v3.3: `../fail-forensics-1/1_blind_interlagos_s0.csv` —
  SHA-256 `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`,
  30.000 linhas, 49 colunas.
- Fixture auxiliar frozen LOC-XY-1: `tests/fixtures/loc_xy_interlagos_s377.csv` —
  SHA-256 `6745f371f059a51ad5cf261b73ceee72c682ce3f79279f2becd3fca3236da09d`.
- Prereg + baseline commitados em `5fe4ff8`; código + três testes em
  `4d22d65`.

## Escopo do diff e contrato pretendido

O diff altera somente `model_train/race_diagnostic.py` para anexar
`body_x`, `body_y`, `ns_raw`, usando `phys['x']`/`phys['y']` do getter
read-only já existente e `Track.nearest_segment` em busca global. Não toca
controles, governor, física, ordenação, contadores ou estado da simulação. Os
campos planejados são coordenadas X/Y mundiais do chassi em metros e o índice
inteiro do waypoint inicial do segmento vencedor. A matemática e as convenções
de eixos estão congeladas no preregistro.

`ns_dist` foi omitido: não é necessário para o objetivo de capturar o índice
bruto e adicionaria uma quarta coluna fora do trio pedido. O smoke completo
não ocorreu, portanto valores/tipos em linhas reais de corrida e a paridade de
todos os campos legados ainda não foram medidos.

## Próximo passo pendente

Aguardar decisão do dono sobre o contrato de
`test_t_regression_v10_cego_bit_identico` (usar o kill-switch v3.3 ou comparar
somente a projeção das colunas legadas). Não editar o teste nem retomar o ciclo
antes dessa decisão. O PARE impede afirmar a validação final do instrumento.
