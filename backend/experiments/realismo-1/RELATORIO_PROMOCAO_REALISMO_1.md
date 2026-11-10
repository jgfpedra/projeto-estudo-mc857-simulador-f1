# Relatório de promoção REALISMO-1

**Base de autorização:** commit `8423a1f` — Programa REALISMO-1 encerrado e homologado pelo Dono.
**Branch:** `feat/sanidade-produto`.
**Estado:** promoção preparada, validada e aguardando Freeze/Commit do Dono; nenhum commit foi feito nesta etapa.

## 1. Alterações controladas de produção

Os dois runners de produção foram atualizados:

- `backend/model_train/race_diagnostic.py`
  - `--profile composite` assume `--rejoin-handoff align`;
  - `--profile composite` assume `--rejoin-ramp`;
  - `--no-rejoin-ramp` permite opt-out explícito;
  - perfis sem residual permanecem com handoff `off` e rampa desligada;
  - `--gov vplan` continua obrigatório quando a rampa está ativa.
- `backend/scripts/run_race_10_cars.py`
  - perfis `race` e `composite` assumem `--rejoin-handoff align`;
  - perfis `race` e `composite` assumem `--rejoin-ramp`;
  - `--no-rejoin-ramp` permite opt-out explícito;
  - perfis sem residual permanecem com handoff `off` e rampa desligada;
  - `--gov vplan` continua sendo o default.

Os mecanismos rejeitados `--launch-steer-mute` e `--lat-offset-slots` não foram alterados e continuam estritamente OFF por default.

## 2. Conformidade e não-regressão

Testes focados:

```text
tests/test_rejoin_handoff.py tests/test_rejoin_ramp.py
16 passed in 1.92s
```

Suíte completa registrada em `full_suite_pos_promocao.log`:

```text
520 collected
20 failed, 497 passed, 3 skipped
```

O conjunto de 20 falhas coincide com o fail-set histórico canônico: `test_kappa_sign.py` (2), `test_mixed_race.py` (1), `test_procedural_track.py` (13), `test_race_layer.py` (1), `test_race_neural_60d.py` (1) e `test_rl_v2.py` (2). Não houve falha nova.

## 3. Demonstração dos novos defaults

Execução:

```text
cd /home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend && \
.venv/bin/python model_train/race_diagnostic.py \
  --profile composite --track interlagos --n-cars 10 --ticks 1000 \
  --out experiments/realismo-1/demo_promocao_interlagos.csv
```

O log confirma:

```text
rejoin_handoff=align
[rejoin-ramp] {'enabled': True, ...}
```

A corrida terminou com exit code 0, gerou CSV, sidecar `_events.csv` e log. A demonstração usou 5.000 linhas de telemetria e 13.482 eventos do solver.

## 4. Evidências e hashes SHA-256

| Artefato | SHA-256 |
|---|---|
| `backend/experiments/realismo-1/full_suite_pos_promocao.log` | `91aefbff9ccf070bf6648fef49af4054da8d50eb95e98cfd7923bb2f5d19de54` |
| `backend/experiments/realismo-1/demo_promocao_interlagos.csv` | `fb3cb96f6201cd516b2d5e732d571590e130ff7006872d78da38ac075f8f2757` |
| `backend/experiments/realismo-1/demo_promocao_interlagos_events.csv` | `9b0b09a23e627f04e7f63aa93230f1dc1acea614e2e384253d4bcf4cb8b38173` |
| `backend/experiments/realismo-1/demo_promocao_interlagos.log` | `be67b67b8d2925a8ab6aa82a08485a2980d715661e3ef3e161cd1c8043531eef` |

## 5. Conclusão

Os mecanismos homologados em C2 e C3 foram promovidos como defaults do perfil de produção composite/race, com opt-out explícito da rampa. A conformidade focada passou integralmente e a suíte completa preservou exatamente o fail-set histórico de 20 falhas. A transição de pesquisa para produção está tecnicamente concluída e aguarda somente o Freeze/Commit de Promoção do Dono.
