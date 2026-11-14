# PREREG YIELD-1C — reexecução standalone do yield

## Estado e exposição

YIELD-1B foi interrompido porque a única corrida usou
`--pass-decision --leader-yield`, embora o prereg congelasse a configuração
canônica mais `--leader-yield`. A execução contaminada rearmou o defeito
residual da linha PASS (`started_s=68,0` após aborto) e falhou em `t_s=76,2`,
com payload preservado em `2_R2_Y.log` (SHA-256
`38aa106552fb3ab46bda308ac7361188ee33094e654bce0ec070dac863494096`).
Nenhum comportamento de yield foi medido.

Esta exceção única renova uma corrida limpa para medir somente o mecanismo
standalone de cedência. O código permanece congelado em
`d4b4eb067f3205d6a9e33062a461a1380bd50495` (`d4b4eb0`), já validado pela
suíte de referência em 20 falhas conhecidas / 380 passes / 3 skips
(`1_full_suite.log`, SHA-256
`8c5bccd58d484d122c70b09c1ae0cdb95d46c0b9dc02ea5d088e2d9aeee5dcf9`).
Não haverá nova execução da suíte.

## Pré-condição de imutabilidade

Antes do commit deste prereg, conferir:

```text
git diff d4b4eb0 -- backend/model_train/race_diagnostic.py \
  backend/model_train/reference_controller.py \
  backend/tests/test_pass_decision.py
```

O resultado esperado é vazio; essa checagem foi realizada e passou. A
checagem ampla `git diff d4b4eb0 -- backend/model_train/ backend/tests/`
também deve ser interpretada sem incluir o registro de fechamento pendente
`backend/model_train/AUDITORIA_RL.md`, que é intocável e permanece fora deste
ciclo. Qualquer diferença em código ou testes é PARE.

## Comando congelado e conferência flag a flag

O comando único, foreground, com `tee`, é:

```bash
cd /home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend
unset RACE_DIAG_NO_CONTACT_LOG RACE_DIAG_NO_XY RACE_DIAG_NO_RES16 PYTHONHASHSEED TF_CPP_MIN_LOG_LEVEL
set -o pipefail
timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py \
  --controller professor \
  --leader-yield \
  --ticks 6000 \
  --laps 99 \
  --track interlagos \
  --seed 0 \
  --weather seeded \
  --variance off \
  --grid f1 \
  --rejoin bearing \
  --out experiments/yield-1/2_R2_Y2.csv \
  2>&1 | tee experiments/yield-1/2_R2_Y2.log
```

Conferência antes de executar:

| Item | Congelado |
|---|---|
| Controller | `professor` |
| Yield | `--leader-yield` |
| PASS | ausente; modo standalone obrigatório |
| Ticks / voltas | `6000` / `99` |
| Pista / seed | `interlagos` / `0` |
| Clima / variância | `seeded` / `off` |
| Grid / rejoin | `f1` / `bearing` |
| Timeout | `2400s`, `TERM` |
| Saída | `2_R2_Y2.csv` e `2_R2_Y2.log` |

Qualquer divergência flag a flag é PARE. Conclusão da corrida exige exit 0,
linhas no CSV e hashes registrados.

## Gates

O orçamento é exatamente uma corrida standalone. Os gates permanecem os de
YIELD-1B:

- **g2 — consumo:** pelo menos um seguidor-gatilho completa a passagem e fica
  pelo menos 10 m à frente dentro da janela de yield; reportar yields iniciados,
  consumidos e abortados por par-alvo;
- **g3 — não-piora contra R1**
  (`5cb49097fea9bb066e9bef5ae62f4ee7c6f9ceb70485448792d33b533ce5cdaa`):
  contatos 5 Hz `<= R1 x 1,15`, hesitações `<= R1`, fora `<= R1`, voltas
  `>= R1` e tempo mediano `<= R1 + 2%`;
- **g4 — transferência:** primeira volta `<= R1`, janela pós-rejoin `<= R1` e
  zero engajamento em carve-out;
- **g5 — paridade:** R2-Y2 byte-idêntica a R1 para todo `t < t*`, com primeiro
  gatilho `t* >= 60 s` anotado.

## Fluxo e encerramento

O dono commita este prereg com `git add -f`, verifica o blob e só então a
corrida pode começar. A execução é seguida por auditoria g2-g5 e tabela por
par. O fechamento deve incluir `EXECUCAO_YIELD_1C.md`, os logs/audits, o
`2_R2_Y.log` contaminado como evidência, e as linhas pendentes de
`PROJECT_STATE.md`, `AUDITORIA_RL.md` e `worklog.md`.

Qualquer falha própria, gate, crash, divergência pré-`t*`, `t* < 60 s`,
carve-out, corrida além do orçamento ou edição pós-números arquiva
definitivamente a linha yield, encerra a sublinha de passagem da Etapa 3 e
pivota para a Etapa 4. Não há promoção e o race default v10 permanece
intocado.
