# REALISMO-1 C6-B1 — baseline OFF do perfil cego

**Estado:** concluído, report-only; zero alteração de produção, zero flag C6-B, sem commit.

**Freeze:** `cb0ebe856c0dd93709e3bd8128b2f4206a80a2ce`.
**Emendas:** Formal nº 1 aceita para o aborto pré-launch inicial por cwd; Formal nº 2 aceita para retomar a partir do Run 3.

## 1. Execução e integridade

Os oito runs foram executados serialmente a partir de `backend/`, com o comando canônico do C6-B1, seed 0, clima `seeded`, `--gov vplan`, `--variance off`, `--grid f1`, `--rejoin bearing`, perfil solo DAgger v10 e `--obs-mode edge`.

| Run | Pista | N | CSV | Sidecar | Log | Linhas |
|---:|---|---:|---|---|---|---:|
| 1 | Interlagos | 1 | presente | presente | presente | 30.002 |
| 2 | Interlagos | 2 | presente | presente | presente | 30.002 |
| 3 | Interlagos | 3 | presente | presente | presente | 30.002 |
| 4 | Interlagos | 4 | presente | presente | presente | 30.002 |
| 5 | Monaco | 1 | presente | presente | presente | 30.002 |
| 6 | Monaco | 2 | presente | presente | presente | 30.002 |
| 7 | Monaco | 3 | presente | presente | presente | 30.002 |
| 8 | Monaco | 4 | presente | presente | presente | 30.002 |

As 32 leituras de extração passaram determinismo por `cmp`. Em todas as oito corridas:

- `canonical.metrics_sha256 == base_metrics.metrics_sha256`;
- `integrity.ok == true`;
- CSV com exatamente 30.002 linhas físicas;
- sidecar `_events.csv` presente.

## 2. Métricas cegas OFF N=0..4

N=0 é o controle canônico do BASE-2. N=1..4 são os oito runs adquiridos nesta fase. `colado s` e `deadlocks` usam a convenção D3 corrigida por comprimento da pista.

| Perfil | Pista | N | Contatos | Laps | Fora% | Colado s | Deadlocks |
|---|---|---:|---:|---:|---:|---:|---:|
| blind | Interlagos | 0 | 764 | 49 | 22,6 | 178,2 | 6 |
| blind | Interlagos | 1 | 955 | 48 | 22,8 | 220,2 | 10 |
| blind | Interlagos | 2 | 1.351 | 46 | 23,7 | 204,4 | 6 |
| blind | Interlagos | 3 | 1.047 | 48 | 21,4 | 194,4 | 3 |
| blind | Interlagos | 4 | 1.194 | 50 | 20,8 | 156,2 | 5 |
| blind | Monaco | 0 | 696 | 32 | 47,5 | 108,6 | 3 |
| blind | Monaco | 1 | 1.346 | 31 | 47,2 | 293,4 | 11 |
| blind | Monaco | 2 | 854 | 28 | 48,5 | 122,0 | 4 |
| blind | Monaco | 3 | 1.345 | 30 | 48,1 | 159,6 | 4 |
| blind | Monaco | 4 | 822 | 33 | 46,8 | 102,2 | 1 |

O padrão cego é mensurável. Em particular, o baseline cego mostra colado e deadlock suficientes para manter o escopo integral do C6-B nos dois perfis.

## 3. Disclosures de infraestrutura

- **Emenda Formal nº 1:** aceita o aborto pré-launch inicial ocorrido quando o Run 1 foi invocado fora de `backend/`.
- **Emenda Formal nº 2:** aceita o segundo aborto pré-launch ocorrido quando o Run 3 foi invocado fora de `backend/`. O Run 3 foi retomado a partir de `backend/`, sem CSV ou log parcial reaproveitado.
- As duas emendas foram aplicadas antes da matriz efetiva continuar. Nenhum run foi sobrescrito ou repetido depois de produzir saída válida.
- O supervisor não expõe o código de saída numérico individual do shell. A integridade foi confirmada por saída completa, 30.002 linhas, sidecar, log e extração D2; essa limitação permanece divulgada.

## 4. Extração

Para cada run foram produzidos:

- `<RUN_ID>_base_metrics.json`;
- `<RUN_ID>_base_metrics_read2.json`;
- `<RUN_ID>_realismo.json`;
- `<RUN_ID>_realismo_read2.json`.

Os pares passaram `cmp=0`. A extração não alterou CSVs, sidecars, produção ou os artefatos do C6-A.

## 5. Encerramento da Fase C6-B1

A baseline cega OFF N=1..4 está adquirida para as duas pistas. C6-B1 termina aqui. Não implementar `--lat-offset-slots`, não executar controles C6-B2 e não iniciar tratamentos ON antes da homologação do Dono.
