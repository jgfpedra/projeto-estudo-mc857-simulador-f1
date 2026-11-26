# PREREG REJOIN-TEL-1 — telemetria do ciclo de rejoin

**Data:** 2026-10-24 (America/Sao_Paulo)  
**Status:** congelado antes de implementar writer/audit e antes de executar a
suíte ou abrir resultados novos.  
**Escopo:** writer v3.5 aditivo, um replay R4, análise report-only. Nenhuma
mudança de comportamento, promoção ou alteração de `--proj-gate`; essa flag
continua default-OFF. A referência da suíte permanece intacta.

## Decisões ratificadas pelo dono

- As **9** colunas enumeradas abaixo prevalecem: 71 legadas + 9 novas = **80
  colunas**.
- Executar a **suíte completa** depois de congelar implementação, testes e
  audit e antes do único replay. Comparar identidades de falhas contra a
  referência publicada; qualquer falha nova é PARE.

## Pergunta e hipóteses

Instrumentar somente a trajetória canônica R4 para medir ciclo de rejoin,
orientação na reentrada, curvatura e alvo legado efetivamente consumido. Os
resultados poderão recomendar RECUP-2 opt-in, encerrar a hipótese de alvo ou
registrar uma limitação/outro mecanismo. Não será aplicada correção de alvo ou
comportamento neste ciclo.

- **H-ÂNGULO:** a orientação no retorno tem discrepância material em relação à
  tangente local e se associa a uma segunda saída em até 10 s. Limiar
  descritivo frozen: `abs(heading_err_deg) > 20°`; é uma triagem de
  desalinhamento grosseiro, não um gate causal. A motivação é o lead publicado
  de incompatibilidade geométrica em C11/C04, responsáveis juntos por 36,6%
  das excursões baseline (22,0% + 14,6%).
- **CONTINUIDADE:** comparar o alvo legado, âncora, curvatura, lead e tempos de
  retorno por janela; associação temporal não prova causalidade.
- **HESITAÇÃO:** recriar literalmente o detector frozen abaixo e comparar com
  a referência publicada 28 (R2 ON) / 12 (limite OFF publicado).

## Fontes e pinos frozen

Antes de calcular ou abrir qualquer resultado novo, conferir SHA-256 completo
em disco e em `git show` para as fontes aplicáveis. Os valores abaixo são os
hashes completos já verificados no checkout HEAD `6745cd909f5df5e2557fcc31acda080b205b8e9e`;
hashes curtos mencionados em documentos não substituem estes.

| Fonte | Caminho | SHA-256 |
|---|---|---|
| R4 replay v3.4 (referência de prefixo) | `backend/experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.csv` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| R4 âncora de configuração | `backend/experiments/fail-forensics-2/4_composite_monaco_s0.csv` | `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022` |
| R1 events (referência publicada) | `backend/experiments/proj-gate-1/1_repro_off_monaco_s0_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| R2 ON CSV (referência publicada) | `backend/experiments/proj-gate-1/2_on_monaco_s0.csv` | `b9ea18f28a26f2035fe61c9370eec7a70eb2bcaa342897d08a71baaf686a4edc` |
| R2 ON events (referência publicada) | `backend/experiments/proj-gate-1/2_on_monaco_s0_events.csv` | `88fa98130b73b881750dab5f54a1fae02d07ce2a2162e1586332afec0660ac6a` |
| Monaco frozen | `backend/model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| Runner frozen em `f2bd199` | `backend/scripts/run_race_10_cars.py` | `6f13b59cfb7e709081483be85e2ad14d7295f65981dc8705ca8bcc9a9b8b03b3` |
| Diagnostic/writer frozen em `f2bd199` | `backend/model_train/race_diagnostic.py` | `69f87d163a56fe310212158ff527f58bd891828ffd0e8c5f91c3f5d7d41a0491` |
| PARE PROJ-GATE-1 | `backend/experiments/proj-gate-1/PARE_PROJ_GATE_1.md` | `6b89f7b03a2313b76c73117e795d0b9089da309fb4cccc6527edb3396673acb9` |
| Referência da suíte completa | `backend/experiments/loc-xy-1/5_post_chain_fix_pytest.log` | `7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185` |

Os dois CSVs de R1 (R1 e R4) têm SHA idêntico. A referência congelada de
prefixo contém cabeçalho e 30.000 linhas de dados, 71 colunas, 10 carros e
ticks amostrados `0,2,...,5998`. O runner frozen só atualiza âncora quando
on-track (`run_race_10_cars.py:794-800`); o alvo live é calculado em
`_rejoin_target_point` (`:477-495`) e consumido pelo ramo de rejoin (`:1158-1160`).
O writer v3.4 está em `race_diagnostic.py:75-96` e sua chamada em `:1057`.
Esses pontos de código e os SHAs devem ser verificados novamente contra
`git show f2bd199:<path>` antes da implementação. O evento de gap-check não
entra no R4 (`rejoin_gap=0`).

## Schema e semântica frozen

As 71 colunas anteriores, na ordem e representação existentes, permanecem
inalteradas. Anexar exatamente estas 9, nesta ordem, por linha amostrada:

| # | Campo | Tipo e definição |
|---|---|---|
| 72 | `off_window_id` | inteiro; ID crescente por carro da janela off-track ativa; `0` em estado on-track. ID começa em 1. Janela e estado são observados em cada tick lógico antes da ação; o CSV persiste snapshots na cadência legada de 5 Hz. |
| 73 | `off_age_ticks` | inteiro; ticks lógicos desde o primeiro estado off-track consecutivo, começando em 0; `0` on-track. |
| 74–75 | `anchor_x`, `anchor_y` | floats; pose XY do corpo no tick lógico mais recente cujo `abs(lat) <= half_width * OFFTRACK_FACTOR`; atualizada em todo tick on-track e congelada durante off-track. Inicialização precisa ocorrer antes da primeira ação. |
| 76 | `anchor_s` | float; arco `s` da mesma projeção do tick da âncora, calculada pelo algoritmo frozen do controller. |
| 77–78 | `target_x`, `target_y` | floats; retorno literal de `_rejoin_target_point` consumido pela ação deste tick, capturado por wrapper pass-through em memória. `0,0` quando não houve chamada/alvo. O wrapper retorna o mesmo par sem alteração. |
| 79 | `reentry_heading_err_deg` | float; somente na primeira linha amostrada após a transição lógica off→on: `degrees(wrap(course_xy - heading_at_s))`. `course_xy=atan2(y_i-y_prev,x_i-x_prev)` usa duas linhas CSV consecutivas do mesmo carro; `heading_at_s` usa a tangente segmentar frozen do controller em `s` da linha corrente. `wrap` é `((a+π) mod 2π)-π`. Zero fora da linha de reentrada; pode também ser zero no retorno se alinhado exatamente ou se `hypot(Δx,Δy) <= 1e-9` (caso marcado não identificável no audit). Não consultar estado novo do env para curso/rumo. |
| 80 | `target_kappa` | float; `_kappa_signed(s_live + ahead_m)` com janela default do método frozen, do mesmo alvo legado capturado; `0` sem alvo. |

Janela e âncora são atualizadas em resolução lógica de 10 Hz antes de
`predict_batch`; o registro emitido a cada dois ticks representa o estado
controller desse tick e a ação correspondente. `body_x/body_y` e `s` legados
continuam sendo o estado pós-step já definido pelo v3.4. Essa diferença de
fase será mantida explícita no audit. O valor alvo é o retorno anterior ao
step que escolheu a ação da linha, nunca um alvo reconstituído depois.

O cabeçalho metadata poderá identificar `race_diag_v3_5_rejoin_tel`; não muda
o comparador de passividade. `--writer-v35` é opt-in, default-OFF, válido para
controller neural único (incluindo o perfil composite), exige XY habilitado e
rejeita `--proj-gate`; sem a flag, o writer mantém o v3.4. Não editar
`run_race_10_cars.py`, env, física, observações, pista, pools ou caches.

### Fórmulas e gates de análise frozen

- Geometria: `L=3335.2 m`, 834 segmentos, `waypoint_s=L/834`. Para cada pose
  CSV, `wp* = argmin_j Euclid(body_xy, wp_j)`, empate no menor índice. Ângulo
  usa `atan2` em radianos e o wrap acima.
- Janelas auditáveis: grupo por `(drv,off_window_id)` com ID não zero nas
  linhas amostradas; até **345 janelas** são esperadas. Saída é a primeira
  linha amostrada off do grupo; retorno é a primeira linha amostrada posterior
  on-track; duração reportada em ticks pela diferença dos ticks observados,
  sem imputar ticks intermediários. Janelas sem linha de retorno observável
  são censuradas à direita. Lead é `hypot(target_x-exit_body_x,
  target_y-exit_body_y)` na linha amostrada de saída. Alvo zero é ausência,
  não coordenada válida.
- H-ÂNGULO: fração das reentradas observáveis com `abs(err)>20°`; associação
  com nova saída é Pearson entre erro assinado em graus e indicador 0/1 de
  segunda janela off-track iniciada em `[reentry_tick,reentry_tick+100]` do
  mesmo carro. Reportar `n`; se variância ausente, correlação `null`.
- Retorno: p50, p95 e máximo de ticks/tenths de segundo por janela visível,
  censuradas contadas e separadas; comparar com R2 somente quando métrica e
  origem publicados forem idênticos. R2 publicado sem retorno por janela não
  será inferido de outra métrica.
- Hesitação: reproduzir regra de `PREREG_PROJ_GATE_2.md`, §5: por carro,
  cortar `t_s>20`; sequência contígua `speed<0.5`; episódio quando
  `0.3 <= t_s[min(j,n-1)]-t_s[i] < 3.0`, com `j` primeiro índice não lento
  (ou `n`) e `n` tamanho após corte. Confirmar R2=28 por referência já
  publicada; a comparação 12 permanece o limite publicado, não baseline R4.
  Para R4 reportar total e hesitações em até 10 s pós-reentrada observável.
- A segunda saída é a próxima janela off-track observada do mesmo carro após
  retorno; janela `<=100` ticks. Não atribuir causalidade a erro de ângulo,
  κ, lead ou hesitação.

## Implementação e congelamento

1. Este arquivo é commitado sozinho antes de qualquer alteração em código.
2. Implementar `--writer-v35` opt-in em `backend/model_train/race_diagnostic.py`
   com captura pass-through do alvo e colunas anexadas sem editar o runner
   frozen; nenhum cálculo de telemetria participa da escolha de ação.
3. Criar `backend/tests/test_rejoin_tel.py` para: prefixo de 71 colunas,
   janela/id/idade com transições sintéticas, semântica de zeros, captura
   pass-through, rumo/tangente sintéticos e default-OFF. Nenhum teste lança
   simulação.
4. Criar `backend/scripts/rejoin_tel_1_audit.py` v1.0 com `--selftest` usando
   exclusivamente dados sintéticos; antes de executar selftest/audit, exibir
   schemas esperados. O audit de resultados novos lê somente CSV v3.5 e
   Monaco frozen; não abre R1/R2/R4 para computar métricas. Comparação de
   prefixo é um gate separado sobre CSV novo e R4 v3.4.
5. Congelar writer, testes e audit em commit dedicado. Depois desse commit,
   nenhuma edição de código, teste ou prereg após observar números do replay.

## Orçamento e execução

- Exatamente **um** replay: R4 canônico v3.4 com `--writer-v35` explicitamente
  ligado, 10 carros, 6000 ticks, `--laps 99`, Monaco, seed 0, clima seeded,
  gov vplan, variance `grid,compound`, rejoin gap 0 e prof-repair OFF. Zero
  smokes, nenhum replay de comparação ou simulação adicional.
- Configuração/command line será copiada literalmente do log da referência R4
  v3.4, acrescentando somente `--writer-v35` e novo caminho de saída. Um
  arquivo output pré-existente causa PARE; não sobrescrever.
- Depois do commit da implementação, executar a suíte completa serialmente
  de `backend/`: `.venv/bin/python -m pytest tests/ -q`. Baseline publicado:
  **20 falhas, 352 passes, 3 skips**, log SHA acima. Gate: zero novas falhas
  (comparar identidades de teste, não apenas contagens). Uma nova falha PARE
  antes da única corrida.

## Gates da corrida

1. **g1 schema/completude:** header exatamente 80 campos, 30.000 linhas,
   10 carros, 3.000 ticks amostrados por carro (`0,2,...,5998`), sem
   duplicatas/lacunas.
2. **g2 passividade:** para o cabeçalho CSV e cada linha de dados, comparar
   `split(',')[:71]` byte a byte com R4 v3.4 (SHA no quadro de pinos). Ignorar
   apenas a linha metadata `#`. Qualquer divergência é PARE.
3. **g3 telemetria:** valores finitos; IDs inteiros coerentes por carro,
   idades não negativas e contíguas em ticks lógicos; âncora finita e congelada
   durante off; alvo zeros quando ausente e igual ao retorno pass-through
   capturado quando presente; κ finita e zero sem alvo; erro de rumo zero
   fora da primeira amostra de reentrada. Reproduzir até 345 janelas esperadas;
   qualquer divergência de schema/semântica ou impossibilidade de validar é
   PARE.
4. **g4 suíte:** suíte completa conforme gate acima, antes do replay; nenhuma
   falha nova.

## PARE obrigatório

Qualquer divergência de pino disco/Git; fonte frozen/code drift; schema ou
prefixo inválido; valores ou transições inválidos; passividade não provada;
impossibilidade de capturar o alvo efetivamente consumido; falha nova na suíte;
configuração diferente; output preexistente; segunda corrida/smoke; ou mudança
em runner, ambiente, física, observações, `--proj-gate`, pista, pools ou
caches. Ao PARE, registrar evidência e interromper as fases dependentes sem
corrigir código/dados após números.

## Saídas e decisão

Congelar antes dos números novos o audit, incluindo selftest sintético; depois
do replay gravar em `backend/experiments/rejoin-tel-1/` os CSV/log e em
`autopsia/` as tabelas por janela, scorecard e logs com hashes/proveniência.
O veredito único ao dono poderá recomendar RECUP-2 (novo prereg e kit de gates,
duas simulações futuras), arquivar/avançar Etapa 3, ou registrar outra causa
com barreira explícita. Nenhuma promoção, correção, exibição ou suíte de
referência alterada neste ciclo. Ao fechar, atualizar `backend/PROJECT_STATE.md`,
`backend/model_train/AUDITORIA_RL.md`, `worklog.md` e handoff de encerramento.
