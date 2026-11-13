# PREREG REALISMO-1 · C2 — handoff do rejoin

**Versão:** 1.0 · **Estado:** pré-freeze; C2-A concluído report-only; ZERO edição de produção, ZERO corrida nesta etapa · **Data:** 2026-10-30 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `641b74bb4c134fb72010bb50131982c7fca355a5` (closing owner do C1, esperado). **Index:** C2-A e este prereg serão staged; commit somente após freeze do dono. Strays conhecidos, nunca stagear: `.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.

**Plano-mãe:** `backend/PLANO_REALISMO_BOTS_1.md` v1.1, Tasks 7–9. **C2-A:** `backend/experiments/realismo-1/c2/C2A_FINDINGS.md` e `C2A_ATTRIBUTION.json`, report-only, sem simulação.

## 1. Objetivo

Testar a flag `--rejoin-handoff align` para reduzir as saídas secundárias em cascata após o retorno à pista (P2), sem acelerar o pelotão e sem regressão de contatos, ritmo ou tempo fora da pista.

O ciclo usa somente camadas de controle. Não há retreino, alteração de física, alteração do espaço de observação ou mudança de default.

## 2. Resultado C2-A e parâmetros congelados

C2-A leu somente os CSVs N=0 commitados da promocao-1:

- Interlagos: 217 reentradas, 119 novas saídas em até 10 s;
- Monaco: 378 reentradas, 274 novas saídas em até 10 s.

Parâmetros aprovados pelo dono:

| Constante | Valor | Definição |
|---|---:|---|
| `theta_H` | `0,3490658504 rad` (20°) | limiar absoluto do erro de rumo na reentrada |
| `m_H` | `0,5 m` | margem mínima do centro do carro até a borda do asfalto |
| `T_H` | `24,0 s` | teto do handoff após a transição off→on |

`m_H` foi derivado como o maior degrau de 0,25 m abaixo do menor p75 de margem entre as pistas. `T_H` é `ceil(max(p95)` do tempo observado para satisfazer simultaneamente `theta_H` e `m_H`), limitado pelo Monaco.

## 3. Mecanismo C2-B pinado

### 3.1 Ativação e estado

O handoff ativa na transição observável `offtrack: 1 -> 0`, por carro. A transição usa a amostragem lógica do runner; o estado é keyed por `driver_id` e não pode vazar entre carros.

Enquanto ativo:

1. calcula o erro de rumo físico em relação ao rumo da pista:
   `heading_err = wrap(heading_car - heading_track)`;
2. calcula a margem lateral:
   `margin = half_width - abs(signed_lat)`;
3. comanda esterço por bearing ao mesmo alvo de rejoin existente: projeção do carro na linha central + `REJOIN_AHEAD_M = 10,0 m` na direção da pista;
4. limita o esterço a `±steer_limit_rad(v)`;
5. mantém o longitudinal da policy + governor. O handoff não substitui `th`, `brk` nem o `v_plan`.

A autoridade final fica explicitamente como `rejoin_handoff` em todos os ticks em que o handoff estiver ativo. O rótulo não fica grudado após o término.

### 3.2 Condição de término

O handoff termina no primeiro evento:

```text
(|heading_err| <= theta_H E margin >= m_H) OU (t_handoff >= T_H)
```

Para auditoria, o motivo de término por carro é registrado como:

- `aligned`: as duas condições de alinhamento foram satisfeitas;
- `timeout`: `t_handoff >= 24,0 s`;
- `offtrack`: o carro saiu novamente antes de alinhar ou atingir o teto.

Uma nova transição off→on inicia um novo episódio e um novo relógio. O estado de um episódio não é reutilizado no episódio seguinte.

### 3.3 Precedência sobre `rejoin_gap`

Durante `rejoin_handoff`, o handoff tem precedência explícita sobre `rejoin_gap`:

- `rejoin_handoff` controla o esterço;
- `rejoin_gap` não sobrescreve o esterço nem o longitudinal enquanto o handoff estiver ativo;
- quando o handoff termina, o comportamento normal de `rejoin_gap` volta a ser elegível para a transição off→on;
- a implementação do gap-check, seus limiares, crawl, fallback e estado existente permanecem intocados fora dessa precedência.

### 3.4 O que não muda

- O teto de 8 m/s na grama (`REJOIN_TARGET_MPS`) permanece intocado.
- O `rejoin_gap` permanece intocado fora da precedência acima.
- A lei de bearing fora do handoff permanece a lei atual.
- O espaço de observação, pesos, física e perfil de velocidade permanecem intocados.
- Default OFF = comportamento e CSV byte-idênticos.

## 4. Matriz de 12 corridas — orçamento exato

**Orçamento:** 12 corridas seriais: 2 controles OFF novos + 10 tratamentos ON. Não há re-smoke adicional. Falha de infraestrutura, aborto pré-launch, saída preexistente, timeout, reexecução ou corrida fora da matriz = PARE + emenda do dono.

Cada corrida parte de `backend/` e usa `set -o pipefail`, `timeout --signal=TERM 2400s`, `.venv/bin/python`, `--profile composite`, `--n-cars 10`, `--ticks 6000`, `--laps 99`, seed 0, `--weather seeded`, `--gov vplan`, `--variance off`, `--grid f1`, `--rejoin bearing`.

| Run | Pista | N | Braço | Flag | Saída principal |
|---:|---|---:|---|---|---|
| 1 | Interlagos | 0 | OFF controle novo | ausente | `1_CTRL_INTERLAGOS_N0.csv` |
| 2 | Monaco | 0 | OFF controle novo | ausente | `2_CTRL_MONACO_N0.csv` |
| 3 | Interlagos | 0 | ON | `--rejoin-handoff align` | `3_ON_INTERLAGOS_N0.csv` |
| 4 | Monaco | 0 | ON | `--rejoin-handoff align` | `4_ON_MONACO_N0.csv` |
| 5 | Interlagos | 1 | ON | `--rejoin-handoff align` | `5_ON_INTERLAGOS_N1.csv` |
| 6 | Monaco | 1 | ON | `--rejoin-handoff align` | `6_ON_MONACO_N1.csv` |
| 7 | Interlagos | 2 | ON | `--rejoin-handoff align` | `7_ON_INTERLAGOS_N2.csv` |
| 8 | Monaco | 2 | ON | `--rejoin-handoff align` | `8_ON_MONACO_N2.csv` |
| 9 | Interlagos | 3 | ON | `--rejoin-handoff align` | `9_ON_INTERLAGOS_N3.csv` |
| 10 | Monaco | 3 | ON | `--rejoin-handoff align` | `10_ON_MONACO_N3.csv` |
| 11 | Interlagos | 4 | ON | `--rejoin-handoff align` | `11_ON_INTERLAGOS_N4.csv` |
| 12 | Monaco | 4 | ON | `--rejoin-handoff align` | `12_ON_MONACO_N4.csv` |

### Controles OFF

Cada controle é uma corrida nova com a flag desligada, `--variedade 0`, e é comparado byte a byte contra os CSVs e sidecars canônicos da promocao-1. Divergência no CSV ou sidecar = PARE. Os valores de referência continuam sendo os bytes commitados; controles novos não redefinem o OFF canônico.

Se o header comentário do CSV mudar com a flag OFF, é PARE. Não ajustar header para fazer `cmp` passar.

### Selo de variedade

N=5..8 permanecem estritamente selados até C7. Nenhuma corrida desta etapa usa N>4.

## 5. Gates formais

Os ON N=0..4 são comparados ao OFF canônico da mesma pista e realização. A tabela ON × OFF por realização é disclosure obrigatório.

| Gate | Agregação | Regra | Limiar congelado |
|---|---|---|---:|
| **C23P primário** | soma por pista | `offtrack_rows_ON <= offtrack_rows_OFF + margem material` | Interlagos `<=39.347` linhas; Monaco `<=73.732` linhas |
| **B-1 contatos** | soma por pista | contatos totais ON não excedem OFF + 2σ | Interlagos `<=2655`; Monaco `<=3021` |
| **B-1 alerta** | soma por pista | registrar a banda de +10%, sem reprovação dura isolada | Interlagos `<=2007`; Monaco `<=2386` |
| **PARE outlier** | por realização | `ON >= 3 × OFF` em contatos totais | PARE + disclosure |
| **R-1 ritmo** | soma por pista | `laps_total_ON >= floor(0,95 × laps_total_OFF)` | Interlagos `>=209`; Monaco `>=144` |
| **R-2 fora** | soma por pista | `100·fora_ON <= 100·fora_OFF + linhas` | +1,0 pp |
| **Integridade D2** | por corrida | CSV 30.002 linhas, sidecar, identidade, N, duas leituras determinísticas | falha = PARE |

### Disclosures obrigatórios

Além dos gates formais, cada corrida registra:

- `rejoin_handoff` por tick e a distribuição de `aligned`, `timeout`, `offtrack`;
- cascatas e novas saídas em até 10 s;
- autoridade por camada;
- contatos totais e contatos `t<=60 s`;
- `offtrack_rows`, fora%, `laps_total`, hesitações, paradas e colado/deadlock;
- tabela por realização ON × OFF.

O objetivo específico de P2 é avaliado por `cascade_events`, `new_exit_le_5s` e autoridade `rejoin_handoff`; essas métricas são disclosure neste prereg, enquanto C23P é o gate primário formal.

## 6. Integridade e PAREs

- Controle OFF divergente byte a byte em CSV ou sidecar = PARE imediato; log não entra no `cmp`.
- Header OFF alterado = PARE; não editar header para contornar divergência.
- CSV ausente, sidecar ausente, menos/mais de 30.002 linhas, N incorreto, SHA de pista incorreto, `integrity.ok=false` ou extração não determinística = PARE.
- Qualquer corrida com `N>4`, seed diferente de 0, `--residual-override`, flags não previstas, timeout, traceback, rerun ou output preexistente = PARE.
- `theta_H`, `m_H`, `T_H` e a margem dos gates não podem ser ajustados depois de observar os ON.
- Nenhuma mudança de default, promoção ou alteração de produção ocorre neste ciclo automaticamente.

## 7. Implementação posterior ao freeze

Antes das corridas C2-B:

1. teste de flag OFF byte-idêntica;
2. teste de ativação somente na transição off→on;
3. teste de esterço limitado por `steer_limit_rad(v)`;
4. teste de longitudinal policy + governor intocado;
5. teste dos critérios `aligned`, `timeout` e `offtrack`;
6. teste de uso por episódio e chave por carro;
7. teste de precedência sobre `rejoin_gap`;
8. teste do rótulo `rejoin_handoff` sem persistência após o término;
9. suíte serial e comparação do fail-set conhecido.

A etapa C2-B só começa depois do freeze do dono deste prereg.

## 8. Freeze

Este arquivo é staged sem commit para revisão. O executor para aqui. O dono deve congelar o prereg C2 antes de qualquer edição de produção, implementação ou corrida.
