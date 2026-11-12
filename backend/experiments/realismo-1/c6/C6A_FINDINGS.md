# REALISMO-1 C6-A — análise offline de trenzinho

**Estado:** report-only, zero simulação, zero alteração de produção.

## Escopo

Foram analisados composite OFF N=0..4 e blind N=0. Blind N=1..4 não existe no cache e permanece orçamento do C6-B.

## Métricas

| Perfil | Pista | N | colado s | deadlocks | fração tempo trem | voltas | fração voltas trem |
|---|---|---:|---:|---:|---:|---:|---:|
| composite | interlagos | 0 | 28.0 | 1 | 0.0114 | 44 | 0.0 |
| composite | interlagos | 1 | 41.2 | 1 | 0.0144 | 45 | 0.0 |
| composite | interlagos | 2 | 88.0 | 3 | 0.0288 | 44 | 0.0 |
| composite | interlagos | 3 | 45.4 | 1 | 0.0155 | 44 | 0.0 |
| composite | interlagos | 4 | 33.8 | 1 | 0.0113 | 43 | 0.0 |
| composite | monaco | 0 | 75.4 | 1 | 0.0210 | 31 | 0.0 |
| composite | monaco | 1 | 109.4 | 1 | 0.0327 | 31 | 0.12903225806451613 |
| composite | monaco | 2 | 97.4 | 2 | 0.0325 | 32 | 0.0625 |
| composite | monaco | 3 | 91.4 | 1 | 0.0246 | 29 | 0.13793103448275862 |
| composite | monaco | 4 | 97.2 | 2 | 0.0334 | 29 | 0.06896551724137931 |
| blind | interlagos | 0 | 178.2 | 6 | 0.0504 | 49 | 0.0 |
| blind | monaco | 0 | 108.6 | 3 | 0.0345 | 32 | 0.1875 |

## Derivação dos offsets

Os offsets são a mediana entre corridas disponíveis de `median_signed_lat_by_slot - pooled_median`, limitada a ±1,0 m. A aplicação C6-B deverá alterar somente `obs4` por `tels[i,4] = (signed - off_i)/hw`; a física e o CSV continuam físicos.

| Slot | Composite m | Blind m |
|---:|---:|---:|
| 0 | 0.2727731564999999 | 0.2505963375 |
| 1 | -1.0 | -0.002860336499999991 |
| 2 | -0.69266154 | -0.5486948054999999 |
| 3 | 0.589630985 | -0.04238477249999997 |
| 4 | 1.0 | -0.8786235379999999 |
| 5 | -0.784486685 | -0.5183083518 |
| 6 | 0.018426517500000072 | 0.8961343024999999 |
| 7 | -0.901684875 | 0.142456875 |
| 8 | 0.06410126100000002 | 0.6935913675000001 |
| 9 | 1.0 | 0.17962442849999996 |

## Dados ausentes e decisão

- Não há corridas blind N=1..4; portanto a matriz completa C6-A dos dois perfis não existe ainda.
- A análise não promove a flag nem autoriza C6-B.
- O Dono deve decidir se o padrão composite é mensurável e congelar o prereg C6 antes das corridas cegas N=1..4.

## Encerramento

C6-A termina aqui para revisão e Freeze do Dono.
