# PREREG_C8_0 — confirmação de rejoin após a promoção

**Data:** 2026-11-06 · **Branch:** `feat/sanidade-produto` · **Estado:**
aguardando Freeze do Dono. Esta preregistração não autoriza execução antes do
Freeze.

## 1. Comando canônico

Cada corrida deve ser disparada a partir de `backend/` com os defaults
promovidos:

```text
cd /home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend && \
.venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --weather seeded --gov vplan --variance off --grid f1 \
  --rejoin bearing --rejoin-handoff align --rejoin-ramp \
  --seed 0 --track <interlagos|Monaco> --out <saida.csv>
```

Não usar `--launch-steer-mute`, `--lat-offset-slots`, `--residual-override` ou
qualquer outra flag fora desta preregistração. O comando deve ser serial e o
log deve preservar a linha completa executada.

## 2. Matriz de referência

| pista | variedades |
|---|---|
| Interlagos | N=0, 1, 2, 3, 4 |
| Monaco | N=0, 1, 2, 3, 4 |

São **10 corridas** de referência. A variedade N é declarada no comando e no
log; cada saída tem CSV principal, sidecar `_events.csv` e `.log`.

## 3. D2 — integridade e extrações

Uma corrida só é íntegra se:

- terminar com exit code 0;
- produzir CSV de 30.002 linhas físicas e o sidecar de eventos;
- registrar a pista frozen e o hash canônico esperado;
- não houver arquivo de saída antes da largada;
- o log registrar `rejoin_handoff=align` e a rampa ativa com `gov=vplan`;
- a extração por `base_metrics` e `realismo_metrics` puder ser repetida;
- as duas leituras do extrator forem byte-idênticas (`cmp=0`) e produzirem o
  mesmo `metrics_sha256`.

O orçamento de extração é de **40 leituras determinísticas**: duas leituras
por extrator em cada uma das 10 corridas (2 extratores × 2 leituras × 10).
Qualquer falha de integridade é PARE, sem reexecução seletiva ou substituição
do artefato.

O cross-hash canônico é o hash SHA-256 do conjunto ordenado de resultados
canônicos das 40 leituras, após normalização declarada pelo extrator. O
relatório deve publicar os 40 hashes individuais, o hash agregado, os comandos,
as versões e a tabela por corrida. Um cross-hash divergente, mesmo com métricas
numericamente iguais, reprova a integridade.

## 4. Governança

O prereg deve estar staged antes do Freeze. Até o Freeze são proibidos corrida,
treino, alteração de código, consumo de pools selados e qualquer ajuste de
default. Após a execução, os artefatos e uma linha de ledger idêntica só podem
ser staged com autorização do Dono. Nenhum commit é realizado pelo executor.
