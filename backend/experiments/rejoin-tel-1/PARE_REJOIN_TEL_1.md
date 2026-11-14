# REJOIN-TEL-1 — PARE no replay único

**Data:** 2026-10-24 (America/Sao_Paulo)  
**Status:** PARE; sem dados de telemetria, sem recomendação RECUP-2/arquivar e
sem promoção.  
**Preregistro:** `cc879b0`; erratas pré-resultados `f15bb7d` e `8316af0`.  
**Implementação frozen:** `b42f694` (writer v3.5 opt-in, testes e audit v1.0).

## Motivo

O único replay R4 foi iniciado com a configuração canônica mais `--writer-v35`
e caminho de saída novo. Durante a espera, a lista de processos não mostrou o
processo do replay; interpretei isso incorretamente como encerramento e enviei
Ctrl-C à sessão. A sessão retornou código 130. O log capturou somente a linha
de inicialização do PyBullet; não há CSV nem sidecar de eventos completos.

Este ciclo autorizava exatamente uma corrida. A tentativa interrompida
consumiu esse orçamento; não houve segunda execução. A telemetria não pode ser
auditada e não existe base para recomendar RECUP-2 ou arquivar a hipótese
angular. Um novo replay exige novo preregistro e orçamento ratificado pelo
dono.

## Evidência e gates

| Item | Resultado |
|---|---|
| Pré-pinos corrigidos | PASS — proveniência disco/Git conferida para R1/R2/R4, Monaco, runner, PARE, DOSSIÊ e baseline. Log SHA-256 `7fb06100a04280dc223078cef7cbbf27e055b29a93c559ffea4cd158c09eea0e`. |
| Audit sintético | PASS — não abriu CSV/track/replay. Log SHA-256 `e77cda301ada2a7d7af239c07d4716633eefd402f715e3b836f23cb0ea1cdded`. |
| Suíte completa serial | PASS no gate de identidade: `20 failed, 363 passed, 3 skipped`; as 20 identidades são exatamente as mesmas da referência `20F/352P/3S`. SHA-256 do log novo `8755ea47a6de565eacdd132dbd89effcf4863de4720b773d74788ba1796eb8ae`; SHA da referência `7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185`. |
| Replay único | PARE, interrupção com código 130; sem CSV e sem events. O log parcial tem 42 bytes, SHA-256 `8e95cc79f36d6fd99667f69e2d49cddb14745460e8e7e52c8a1bf5b91ba38134`. |
| g1 schema / g2 prefixo / g3 telemetria | NÃO AVALIADOS — arquivos de dados não foram concluídos. |
| Audit das janelas / scorecard | NÃO EXECUTADO — sem CSV v3.5 válido. |

As 20 identidades conhecidas permaneceram inalteradas: dois testes
`test_kappa_sign`, `TestHoldAt.test_hold_car_stays_at_s`, treze testes
`test_procedural_track`, `TestSplineGeometry.test_subdivision_preserves_length_exactly`,
`TestDeployProfiles.test_profiles_exist_default_race_obs_correct` e os dois
testes de `test_rl_v2` (`test_reference_controller_completes_lap` e
`test_skidpad_radius_close_to_bicycle`). O log completo tem traceback e resumo.

## Reprodutibilidade e disposição

Comando iniciado (sem outra alteração da configuração R4):

```bash
env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track Monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound --writer-v35 \
  --out experiments/rejoin-tel-1/3_replay_rejoin_tel_monaco_s0_v35.csv
```

O writer v3.5 continua default-OFF; `--proj-gate` não foi ligado nem alterado.
Nenhuma alteração ocorreu no runner, env, física, observações, pista frozen,
pools ou caches. Nenhum número do replay foi obtido; o audit de dados e a
decisão experimental ficam pendentes de novo ciclo explicitamente congelado.

Os dois registros de preparação estão preservados. `0_prepins.log` contém a
tentativa que fez somente hashes dos pinos antigos, mas comparou o writer já
implementado ao hash histórico e tinha um dígito transcrito incorretamente no
SHA do PARE; nenhum valor de corrida foi aberto/decomposto nessa tentativa. A
primeira chamada com paths relativos à raiz enquanto estava em `backend/`
parou antes de ler uma fonte e foi sobrescrita pelo registro seguinte. A
`ERRATA_2` corrigiu o dígito e distinguiu o writer histórico do implementado;
`0_prepins_corrected.log` passou integralmente.
