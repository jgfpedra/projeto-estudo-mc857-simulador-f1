# PREREG REALISMO-1 · C3 — rampa P2 pós-reentrada

**Versão:** 1.0 · **Estado:** pré-freeze; C3-A homologado pelo dono como `C3_MORDE`; ZERO edição de produção, ZERO corrida nesta etapa · **Data:** 2026-10-29 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `a623575aaa52ca45f193445a0d54d1a244c577e0` (closing do dono do C2). **Index na redação:** C3-A e este prereg serão staged; não haverá commit antes do freeze do dono. Strays conhecidos, nunca stagear: `.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.

**Plano-mãe:** `backend/PLANO_REALISMO_BOTS_1.md` v1.1, Task 9. **C3-A:** `backend/experiments/realismo-1/c3/C3_RAMP_CHECK.json` e `C3_FINDINGS.md`, report-only, sem simulação. **C3-A homologado:** `C3_MORDE`, com mordida em 115/119 reentradas críticas de Interlagos (96,6%) e 263/274 de Monaco (96,0%).

## 1. Objetivo

Testar a flag opt-in isolada `--rejoin-ramp` para limitar a velocidade pós-reentrada e conter novas saídas em cascata (P2), sem retreino, sem alteração de física, sem alteração do espaço de observação, sem acelerar o pelotão e sem regressão de contatos, ritmo ou tempo fora da pista.

O ciclo testa somente a rampa P2 contra o baseline canônico. A interação entre esta flag e outras mudanças homologadas fica reservada ao C7. O default continua OFF.

## 2. Proveniência e pins

Os pins abaixo são registrados antes da implementação C3-B. Divergência em qualquer pin de código, geometria ou instrumento é PARE e exige decisão do dono antes de prosseguir.

| Item | Caminho | SHA-256 |
|---|---|---|
| Runner de medição | `backend/model_train/race_diagnostic.py` | `21b44267dcf3e6a92291c667f78e18082d9cbb9d1f3eaea3bd4579f374fde7e2` |
| Runner visual/controller | `backend/scripts/run_race_10_cars.py` | `638f6cd25b11c4f06c18dda2b94c97e5d57d86bc88a73a3e7d78e1c9bbb5c5d0` |
| Perfil de velocidade frozen | `backend/model_train/velocity_profile.py` | `a2953bac36064e3a531df7e43bd840efeb0a9b29a823096fa01341651024f5dc` |
| Extrator canônico | `backend/scripts/base_metrics.py` | `9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728` |
| Instrumento REALISMO-1 | `backend/scripts/realismo_metrics.py` | `e5a7ecb42fd9bfd3297935d974a53174b51eb822a877b33e4ed4a208a590ac7b` |
| Geometria/interpretação | `backend/scripts/saidas_verdict.py` | `e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c` |
| Interlagos v2 | `backend/model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| Monaco v2 | `backend/model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| C3-A instrumento | `backend/scripts/c3_ramp_test.py` | `d94f6f3608c641ee83ba01ccd8e39571bc2eaf3bbb59633104c02cb698b2ee5b` |
| C3-A resultado | `backend/experiments/realismo-1/c3/C3_RAMP_CHECK.json` | `cf2ebe12dd20e258651aaf048b38cf6fa928db210b27e49645bf70f5065ebd29` |

Os CSVs N=0 canônicos de comparação permanecem os bytes commitados em `backend/experiments/composite-1/promocao-1/`. Os hashes dos seis arquivos usados como OFF canônico foram congelados nas etapas anteriores e devem ser registrados novamente no relatório de execução antes de qualquer veredito.

## 3. Mecanismo C3-B pinado

### 3.1 Ativação e estado

A flag `--rejoin-ramp` é uma opção opt-in de governor. Ela ativa na transição observável, para o mesmo carro, de `offtrack: 1 -> 0`. O estado é keyed por `driver_id`, tem um relógio próprio por episódio e dura uma janela máxima de **5,0 s** após a reentrada.

Uma nova transição `offtrack: 1 -> 0` inicia um novo episódio e um novo relógio. O estado de um episódio não vaza para outro carro nem é reutilizado depois de uma nova excursão.

A flag é testada isoladamente contra o baseline canônico. Os tratamentos ON não usam `--rejoin-handoff align`, `--launch-steer-mute`, `--pguard`, `--launch-cap`, `--launch-stagger`, `--lat-offset-slots`, override de residual ou qualquer outra flag experimental. Interações entre flags ficam reservadas ao C7.

### 3.2 Teto de velocidade

Durante a janela de C3-B, em cada tick do episódio, o runner calcula o teto usando o `v_plan` do perfil frozen na posição corrente `s`:

```text
v_cap(t) = min(
    0,8 * v_plan(s),
    8,0 + max(0,8 * v_plan(s) - 8,0) * (t - t_reentry) / 5,0
)
```

Constantes congeladas:

| Constante | Valor |
|---|---:|
| Fração do `v_plan` | `0,8` |
| Velocidade inicial `v0` | `8,0 m/s` |
| Janela `T_R` | `5,0 s` |

Se `v > v_cap`, o governor comanda freio pela lei padrão já usada pelo governor de velocidade. A rampa não cria uma lei de freio nova e não altera a política longitudinal fora da intervenção normal do governor.

A flag atua somente como teto longitudinal pós-reentrada. Ela não altera esterço, bearing, handoff, gap-check, observações, pesos, residual, física, geometria ou default.

### 3.3 Pré-condição e erro explícito

`--rejoin-ramp` só é válido com `--gov vplan`. Se a flag for passada sem `--gov vplan`, o parser/configuração deve produzir erro explícito antes da corrida.

A implementação deve existir nos caminhos de medição e demonstração previstos pelo plano, sem mudar o comportamento do runner quando a flag estiver ausente.

### 3.4 Default OFF e saída

Com `--rejoin-ramp` ausente:

- a ação, o governor, a ordem das operações e o estado do runner devem permanecer byte-idênticos ao baseline;
- o CSV principal, o sidecar de eventos e os headers devem permanecer byte-idênticos;
- nenhuma coluna ou metadado de C3-B pode aparecer no OFF de modo a quebrar o `cmp`;
- o comportamento OFF é comparado byte a byte contra os arquivos canônicos da promocao-1.

Qualquer alteração do output OFF, ainda que apenas no header, é PARE. Não se ajusta o header para fazer o `cmp` passar.

## 4. Matriz de 12 corridas — orçamento exato

O orçamento é fixo em 12 corridas seriais: 2 controles OFF novos e 10 tratamentos ON. Não há smoke run, re-smoke, corrida de demonstração, rerun silencioso ou corrida adicional dentro deste ciclo.

Cada corrida parte de `backend/` e usa a configuração canônica:

```text
set -o pipefail
.venv/bin/python model_train/race_diagnostic.py
  --profile composite --n-cars 10 --ticks 6000 --laps 99
  --weather seeded --gov vplan --variance off --grid f1
  --rejoin bearing --seed 0
```

A implementação deve preservar o mesmo seed, número de carros, duração, clima, perfil, governor, grid e modo de rejoin entre OFF e ON. A única diferença entre o tratamento ON e o OFF correspondente é `--rejoin-ramp` e, no tratamento ON, `--variedade N`.

| Run | Pista | N | Braço | Flag | Saída principal |
|---:|---|---:|---|---|---|
| 1 | Interlagos | 0 | OFF controle novo | ausente | `1_CTRL_INTERLAGOS_N0.csv` |
| 2 | Monaco | 0 | OFF controle novo | ausente | `2_CTRL_MONACO_N0.csv` |
| 3 | Interlagos | 0 | ON | `--rejoin-ramp` | `3_ON_INTERLAGOS_N0.csv` |
| 4 | Monaco | 0 | ON | `--rejoin-ramp` | `4_ON_MONACO_N0.csv` |
| 5 | Interlagos | 1 | ON | `--rejoin-ramp` | `5_ON_INTERLAGOS_N1.csv` |
| 6 | Monaco | 1 | ON | `--rejoin-ramp` | `6_ON_MONACO_N1.csv` |
| 7 | Interlagos | 2 | ON | `--rejoin-ramp` | `7_ON_INTERLAGOS_N2.csv` |
| 8 | Monaco | 2 | ON | `--rejoin-ramp` | `8_ON_MONACO_N2.csv` |
| 9 | Interlagos | 3 | ON | `--rejoin-ramp` | `9_ON_INTERLAGOS_N3.csv` |
| 10 | Monaco | 3 | ON | `--rejoin-ramp` | `10_ON_MONACO_N3.csv` |
| 11 | Interlagos | 4 | ON | `--rejoin-ramp` | `11_ON_INTERLAGOS_N4.csv` |
| 12 | Monaco | 4 | ON | `--rejoin-ramp` | `12_ON_MONACO_N4.csv` |

### 4.1 Controles OFF

Cada controle OFF é uma corrida nova com `--variedade 0` e sem `--rejoin-ramp`. O CSV principal e o sidecar devem ser comparados com `cmp` contra:

- Interlagos: `backend/experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.csv` e `_events.csv`;
- Monaco: `backend/experiments/composite-1/promocao-1/3_R3_MONACO_RACE.csv` e `_events.csv`.

Divergência em qualquer byte, inclusive no header, é PARE imediato. Os controles novos não redefinem o OFF canônico.

### 4.2 Tratamentos ON e selo de variedade

Os dez tratamentos ON usam `--rejoin-ramp`, seed 0 e `--variedade N=0..4`, duas corridas por valor de N, uma por pista. Os tratamentos são executados em série, na ordem da tabela, sem paralelização.

**N=5..8 permanecem estritamente selados até C7.** Qualquer corrida com N>4 nesta etapa é PARE e não pode ser substituída por uma nova execução sem emenda formal do dono.

## 5. Gates formais — limiares congelados

Os ON N=0..4 são comparados ao OFF canônico da mesma pista e realização. O relatório deve apresentar a tabela ON × OFF por realização, mesmo quando o gate é agregado por soma. Todas as comparações abaixo ficam congeladas antes das corridas.

| Gate | Agregação | Regra | Limiar congelado |
|---|---|---|---:|
| **C23P primário: fora da pista** | soma por pista | melhora material de pelo menos 2σ: `Σ offtrack_rows_ON <= limite` | Interlagos `<= 39.347` linhas; Monaco `<= 73.732` linhas |
| **B-1 contatos totais** | soma por pista | contatos ON não excedem OFF + 2σ | Interlagos `<= 2655`; Monaco `<= 3021` |
| **B-1 alerta** | soma por pista | registrar a banda antiga de +10%, sem reprovação dura isolada | Interlagos `2007`; Monaco `2386` |
| **PARE outlier de contatos** | por realização | `contacts_ON >= 3 * contacts_OFF` | PARE + disclosure |
| **R-1 ritmo** | soma por pista | `Σ laps_total_ON >= floor(0,95 * Σ laps_total_OFF)` | Interlagos `>= 209`; Monaco `>= 144` |
| **R-2 fora da pista** | soma por pista | taxa ON `<=` taxa OFF + 1,0 ponto percentual | `+1,0 pp` |
| **Integridade D2** | por corrida | 30.002 linhas, sidecar, identidade, variedade correta e duas leituras determinísticas | falha = PARE |

`C23P` é o gate primário do ciclo. A comparação formal usa as somas das cinco realizações ON contra as somas OFF da mesma pista, com os limites acima congelados. O limite de B-1 é também uma comparação por soma; o alerta +10% deve ser informado mesmo sem reprovar isoladamente.

O objetivo mecanístico de P2 será divulgado com `excursions`, `cascade_events`, `new_exit_le_5s`, reentradas, autoridade do governor e estado/tempo da rampa. Essas métricas não substituem os gates formais.

## 6. Integridade D2, extração e PAREs

Cada corrida deve satisfazer, antes de entrar no agregado:

- CSV principal com exatamente 30.002 linhas físicas e 30.000 linhas de telemetria;
- sidecar `_events.csv` presente e legível;
- identidade da pista frozen correta no CSV e no log;
- `variedade` coerente com a linha da matriz;
- seed 0, `--weather seeded`, `--variance off`, `--grid f1`, `--gov vplan` e parâmetros canônicos preservados;
- residual de produção e pins do instrumento conforme o baseline;
- extração por `base_metrics`/`realismo_metrics` realizada duas vezes, em leituras independentes, com o mesmo resultado/hash;
- nenhum output preexistente antes da execução;
- nenhum timeout, traceback, aborto pré-launch ou reexecução silenciosa.

Os seguintes eventos são PARE imediato:

- controle OFF divergente byte a byte do CSV ou sidecar canônico;
- flag passada sem `--gov vplan` sem erro explícito;
- corrida com N=5..8, seed diferente de 0 ou qualquer flag experimental adicional;
- alteração do default, do espaço de observação, da física, da geometria v2, dos pesos, do `base_metrics` ou do extrator canônico;
- CSV/sidecar ausente, linha incorreta, identidade incorreta, integridade falsa ou extração não determinística;
- corrida fora das 12 entradas, rerun, output sobrescrito ou orçamento excedido.

Qualquer PARE interrompe a etapa. Não há rerun silencioso. Uma repetição só ocorre depois de emenda explícita do dono, preservando o artefato da falha.

## 7. Testes pré-corrida obrigatórios

Nenhuma corrida C3-B pode começar antes de todos os testes abaixo passarem e do fail-set ser comparado ao baseline conhecido:

1. **Flag OFF byte-idêntica:** demonstrar nos caminhos de medição e demonstração que a flag ausente preserva a ação, o caminho OFF, o CSV, o sidecar e o header; executar os controles e exigir `cmp` contra a promocao-1.
2. **Pré-condição do governor:** `--rejoin-ramp` sem `--gov vplan` produz erro explícito antes de iniciar a corrida.
3. **Cálculo correto da rampa:** testar a fórmula nos limites `t=t_reentry`, `t=t_reentry+5 s`, `v_plan <= 10 m/s` e `v_plan > 10 m/s`, incluindo `min(0,8*v_plan, ...)` e ausência de teto acima do valor calculado.
4. **Janela de 5 s:** testar ativação somente na transição `offtrack 1 -> 0`, relógio por carro/episódio, duração de 5,0 s, fronteiras inclusivas pinadas e reinício após nova reentrada.
5. **Intervenção longitudinal:** testar que `v > v_cap` chama a lei padrão de freio do governor e que a flag não altera esterço, observação ou política fora dessa intervenção.
6. **Isolamento do ciclo:** testar que C3-B não ativa nem depende de `--rejoin-handoff`, `--launch-steer-mute`, `--pguard`, `--launch-cap`, `--launch-stagger` ou `--lat-offset-slots`.
7. **Suíte serial:** executar a suíte completa em modo serial e comparar o conjunto de linhas `^FAILED` com o fail-set conhecido, sem aceitar falhas novas e sem remover falhas conhecidas por alteração do teste.

Os testes devem ser escritos e executados depois do freeze, antes de qualquer uma das 12 corridas. Falha em qualquer item é PARE.

## 8. Registro D3 / C3b

Este registro não é um gate de C3-B. Depois do fechamento de C2/C3, calcular por pista `FORA-PRESO` e `fora` no melhor estado aprovado, usando a definição D3/A9 já congelada. O melhor estado aprovado é o estado aprovado com menor `offtrack_rows` na pista; em caso de C3 sem aprovação, permanece como referência o melhor estado aprovado anterior do C2.

Se:

```text
2 * preso > fora
```

no melhor estado aprovado, registrar que o próximo ciclo prevê **perfil de velocidade na grama com gap-check**, em ciclo próprio, sem combinar esse mecanismo com outra mudança. O perfil na grama não será implementado como parte do C3-B e não entra na interpretação dos gates deste ciclo.

Se a condição não ocorrer, registrar explicitamente `C3b não acionado` e preservar a decisão para o próximo ciclo conforme o plano-mãe.

## 9. Relatório de execução

O relatório C3-B deve conter:

- comandos completos e ordem serial das 12 corridas;
- hashes de todos os outputs e pins efetivamente usados;
- prova `cmp` dos dois controles OFF;
- duas leituras determinísticas por corrida e hashes dos extratores;
- tabela ON × OFF por realização;
- agregados dos gates C23P, B-1, alerta, R-1 e R-2;
- contagem e tempo de reentradas, novas saídas, cascatas, autoridade do governor e ativações da rampa;
- disclosure de `FORA-PRESO`, `fora`, colado/deadlock e registro C3b;
- PAREs, censuras, falhas de infraestrutura ou divergências, sem ocultar qualquer corrida inválida;
- veredito por gate e veredito formal do ciclo.

Nenhum limiar, constante, regra de agregação ou definição de episódio pode ser ajustado depois da observação dos tratamentos ON.

## 10. Freeze

Este arquivo deve ser staged sem commit para revisão do dono. O executor para aqui. O dono deve congelar este prereg antes de qualquer edição de produção, implementação da flag, teste de integração ou corrida C3-B.
