# PREREG REJOIN-TEL-2 — renovação do orçamento do replay v3.5

**Data:** 2026-10-24 (America/Sao_Paulo)
**Status:** congelar e commitar antes do único replay.
**Código:** writer v3.5 opt-in congelado em `b42f694`; este ciclo não altera
código, não repete a suíte e não promove comportamento.
**Handoff reivindicado:** `01a16e76-d20e-7f21-94fb-37ca0d4de672`.

## Decisão e orçamento

Renovar exclusivamente o orçamento consumido pela interrupção operacional do
REJOIN-TEL-1 (`8c0be3b`, exit 130 antes de CSV ou sidecar completos). Será feita
**exatamente uma** corrida de medição: R4 canônica, perfil `composite`, 10
carros, 6000 ticks, Monaco frozen, seed 0, clima seeded, governança `vplan`,
variância `grid,compound`, `--laps 99` e `--writer-v35`. Não haverá smoke,
comparação adicional ou outra simulação. A suíte não será reexecutada: o
writer `b42f694` já foi validado; o log de referência registra 20 falhas, 363
passes e 3 skips, com as mesmas 20 falhas canônicas.

O replay será executado uma vez em foreground, ligado a `tee`. Nenhum trabalho
paralelo/background será iniciado durante a corrida. A conclusão exige em
conjunto exit code 0, CSV completo conforme g1 e SHA-256 registrado. Listas de
processos não determinam conclusão. Interrupção, sinal, código diferente de
zero ou timeout encerram o ciclo em PARE, sem nova tentativa.

### Timeout congelado

O log R1 OFF (`proj-gate-1/1_repro_off_monaco_s0.log`) não registra duração
explícita. Seu arquivo foi criado às 23:06:25.310 e teve a última gravação às
23:10:48.809 de 2026-10-23, intervalo aproximado de 4m24s. Como estimativa
conservadora do tempo observado, o timeout fica em **9 minutos** (2× o
intervalo, arredondado para cima). Exceder esse limite é PARE e não autoriza
retry.

## Pré-condições congeladas

Verificação concluída antes deste freeze:

1. `git diff b42f694..HEAD` é vazio nos arquivos de produção deste ciclo:
   `backend/model_train/race_diagnostic.py`,
   `backend/scripts/run_race_10_cars.py` e
   `backend/scripts/rejoin_tel_1_audit.py`.
2. Nenhum processo `race_diagnostic.py`/`run_race_10_cars.py` estava ativo na
   checagem pré-run. Os caminhos novos abaixo não existem e nunca serão
   sobrescritos. O log incompleto anterior de 42 bytes permanece preservado em
   `backend/experiments/rejoin-tel-1/3_replay_rejoin_tel_monaco_s0_v35.log`;
   ele não é saída deste orçamento.
3. Cada pin abaixo foi conferido por SHA-256 em disco e com `git show`; ambos
   coincidem com o valor esperado.

| Fonte | Caminho | SHA-256 esperado = disco = Git |
|---|---|---|
| Âncora R4 | `backend/experiments/fail-forensics-2/4_composite_monaco_s0.csv` | `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022` |
| Replay R4 v3.4 | `backend/experiments/proj-fix-1/1_replay_composite_monaco_s0_v34.csv` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| Events R4 v3.4 | `backend/experiments/proj-fix-1/1_replay_composite_monaco_s0_v34_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| Monaco frozen | `backend/model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| Suíte de referência (20F/363P/3S) | `backend/experiments/rejoin-tel-1/2_full_suite.log` | `8755ea47a6de565eacdd132dbd89effcf4863de4720b773d74788ba1796eb8ae` |
| Audit v1.0 frozen em `b42f694` | `backend/scripts/rejoin_tel_1_audit.py` | `e106db7882edb58d603358855e86c5776373e0ddba28f676ee3ee7e6560f1d25` |

## Comando único

Executar de `backend/`, em foreground, gravando a saída integral em arquivo
novo com `tee` e limite externo de 9 minutos:

```bash
set -o pipefail
timeout --signal=TERM 9m env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track Monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound --writer-v35 \
  --out experiments/rejoin-tel-2/2_replay_rejoin_tel2_monaco_s0_v35.csv \
  2>&1 | tee experiments/rejoin-tel-2/2_replay_rejoin_tel2_monaco_s0_v35.log
```

Não alterar ambiente, física, observações, pista, pool/cache, `--proj-gate`,
configuração R4 ou comando durante o ciclo. O writer v3.5 permanece opt-in e
default-OFF.

## Gates congelados

- **g1 — completude/schema:** exatamente 80 campos por linha, cabeçalho
  incluído; 30.000 linhas de dados; 10 carros e 3.000 amostras por carro nos
  ticks `0,2,...,5998`; sem linha duplicada ou ausente.
- **g2 — passividade:** no cabeçalho e em cada linha, os primeiros 71 campos
  (`split(',')[:71]`) são byte-idênticos ao replay R4 v3.4 pinado. Divergência
  é PARE.
- **g3 — 9 campos novos:** validar integralmente tipos, finitude, janelas,
  idade, âncora, alvo, rumo e curvatura segundo schema e semântica frozen em
  `PREREG_REJOIN_TEL_1.md` (commit `cc879b0`), incluindo zeros/blank conforme
  regra. A execução do audit não pode reconstruir um alvo diferente daquele
  capturado pass-through. Divergência ou impossibilidade de validar é PARE.
- **g4 — suíte:** referência, sem reexecução: SHA acima, 20F/363P/3S e mesmas
  20 identidades canônicas documentadas em
  `PARE_REJOIN_TEL_1.md`.

Somente após exit 0, completude e hash do CSV serão executados g1–g3. Qualquer
falha interrompe as fases dependentes e fecha em PARE.

## Audit report-only e regra de encaminhamento

Com g1–g3 aprovados, executar `rejoin_tel_1_audit.py` v1.0 exclusivamente
sobre o CSV novo e a geometria Monaco frozen, salvando arquivos novos em
`backend/experiments/rejoin-tel-2/autopsia/`. Preservar as definições do
REJOIN-TEL-1 sem editar o script frozen:

- tabela de até ~345 janelas: saída, duração observada, reentrada,
  `heading_err_deg`, κ e lead do alvo;
- H-ÂNGULO com `abs(heading_err_deg)>20°`, limiar descritivo frozen por C11/C04;
- Pearson entre erro angular assinado e segunda excursão em até 10 s, com `n`
  e `null` quando não identificável;
- tempo de retorno p50/p95/máximo por janela, censuradas separadas;
- hesitações em até 10 s pós-reentrada, pelo detector frozen, confrontadas com
  os números publicados **12 OFF / 28 ON**.

Uma única recomendação para o dono: (a) RECUP-2, ângulo raso/alvo mais adiante,
opt-in e kit de 2 simulações futuras; (b) arquivar Etapa 2 com critérios
evidenciados e avançar à Etapa 3; ou (c) outra hipótese com barreira explícita.
Associação não será descrita como causalidade. Nenhuma correção ou promoção
neste ciclo.

## PARE obrigatório e fechamento

PARE diante de divergência de hash/proveniência, drift em produção, caminho
parcial não preservado, falha g1/g2/g3, interrupção/sinal/exit code diferente
de zero, timeout, edição de código ou prereg após observar números, corrida
além da única autorizada, ou mudança proibida de ambiente/física/observações/
`--proj-gate`/pool/cache/pista frozen.

Depois do resultado, registrar gates ponto a ponto, hashes e veredito em
`EXECUCAO_REJOIN_TEL_2.md`; adicionar uma linha `Ver <path>` em
`backend/PROJECT_STATE.md`, atualizar `backend/model_train/AUDITORIA_RL.md` e
`worklog.md`, e criar handoff de encerramento. Não alterar este prereg após o
freeze.
