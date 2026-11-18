# PREREG REALISMO-1 · C1 — largada: mute direcional do residual

**Versão:** 1.1 · **Estado:** pré-freeze; C1-A report-only concluído; ZERO corrida C1, ZERO mudança de produção nesta etapa · **Data:** 2026-10-30 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `e3846fe115fbb9ae09a264ce5eaf6b9451baa09d` (closing do C0, esperado). **Index:** C1-A staged, este prereg ainda será staged e aguarda freeze do dono. Strays conhecidos, nunca stagear: `.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.

**Plano-mãe:** `backend/PLANO_REALISMO_BOTS_1.md` v1.1. **C0:** `backend/experiments/realismo-1/c0/PREREG_REALISMO_C0.md` + `EXECUCAO_REALISMO_C0.md`, closing do dono `e3846fe`.

## 1. Objetivo

Testar, sem retreino, se silenciar **somente o canal de esterço** do residual gated durante a largada elimina as saídas atribuíveis ao residual sem acelerar o campo a ponto de produzir regressão de contatos. O canal longitudinal do residual permanece ativo.

C1-A já verificou, nos bytes N=0:

- residual para o lado da saída em **16/18** janelas (89%);
- solo para longe do lado da saída em **18/18** janelas (100%);
- `|g·r|/(|m_solo|+|g·r|)` mediana **0,473 Interlagos / 0,540 Monaco**;
- o teste não trata as 18 janelas como ensaios independentes: 12 provêm de 9 carros e aproximadamente 66% têm contato no entorno. Esses números são evidência de mecanismo, não a principal decisão do ciclo.

O mecanismo C1-B será medido em 2 controles OFF (corridas novas, flag desligada, cmp contra a promocao-1) + 10 corridas ON, todas com seed 0 e `--variedade N=0..4`.

## 2. Proveniência e pins

| Item | Caminho | SHA-256 |
|---|---|---|
| Runner de medição | `model_train/race_diagnostic.py` | `ccf9bb2c247e7bf30257cdc81e120ecc742f4d4f1129a3d11eb3445b8dfdf14e` |
| Runner visual/controller | `scripts/run_race_10_cars.py` | `6f13b59cfb7e709081483be85e2ad14d7295f65981dc8705ca8bcc9a9b8b03b3` |
| Composite | `model_train/residual_gated.py` | `955085c029f0c72cb1c0bb1faa57f4266084ceca22f694369f51267ecf9a9` |
| Extrator canônico | `scripts/base_metrics.py` | `9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728` |
| Instrumento C0 | `scripts/realismo_metrics.py` | `e5a7ecb42fd9bfd3297935d974a53174b51eb822a877b33e4ed4a208a590ac7b` |
| Análise C1-A | `scripts/c1a_attribution.py` | `e2ddbd7ad7ceab9773399fd6519f0ee80d53d288274422815ed4075f65ae57a8` |
| Achados C1-A | `experiments/realismo-1/c1/C1A_FINDINGS.md` | `932d699cf4a4b025d662b53fcb888df31e401a4d71b4bdcfc6c43379d6585db7` |
| Saída C1-A | `experiments/realismo-1/c1/C1A_ATTRIBUTION.json` | `299307cfbdca0c550d75afc1193a305c12a274335ba4d24925fb0308e3b4d47f` |
| Residual produção | `model_train/v15_residual/residual_best_weights.npz` | `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` |
| Interlagos v2 | `model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` / sha16 `164876196eb12174` |
| Monaco v2 | `model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` / sha16 `67ca11dc211c8c78` |

OFF N=0 são os CSVs commitados em `experiments/composite-1/promocao-1/`; OFF N=1..4 são os CSVs commitados em `experiments/realismo-1/c0/`. Nenhuma corrida OFF será reexecutada.

## 3. Matriz EXATA e forma canônica

**Orçamento:** **12 corridas**: 2 controles OFF (corridas novas, flag desligada, cmp contra a promocao-1) + 10 tratamentos ON N=0..4, duas pistas. Não há re-smoke adicional. Qualquer falha de infraestrutura, aborto pré-launch, saída existente, timeout ou reexecução = PARE + emenda do dono; nunca rerun silencioso.

Cada corrida parte de `backend/` e usa `set -o pipefail`, `timeout --signal=TERM 2400s`, `.venv/bin/python`, `--ticks 6000`, `--laps 99`, seed 0, `--weather seeded`, `--gov vplan`, `--variance off`, `--grid f1`, `--rejoin bearing`.

### Matriz completa

| Run | Pista | N | Braço | Saída principal |
|---|---|---:|---|---|
| 1 | Interlagos | 0 | OFF controle novo | `1_CTRL_INTERLAGOS_N0.csv` |
| 2 | Monaco | 0 | OFF controle novo | `2_CTRL_MONACO_N0.csv` |
| 3 | Interlagos | 0 | ON | `3_ON_INTERLAGOS_N0.csv` |
| 4 | Monaco | 0 | ON | `4_ON_MONACO_N0.csv` |
| 5 | Interlagos | 1 | ON | `5_ON_INTERLAGOS_N1.csv` |
| 6 | Monaco | 1 | ON | `6_ON_MONACO_N1.csv` |
| 7 | Interlagos | 2 | ON | `7_ON_INTERLAGOS_N2.csv` |
| 8 | Monaco | 2 | ON | `8_ON_MONACO_N2.csv` |
| 9 | Interlagos | 3 | ON | `9_ON_INTERLAGOS_N3.csv` |
| 10 | Monaco | 3 | ON | `10_ON_MONACO_N3.csv` |
| 11 | Interlagos | 4 | ON | `11_ON_INTERLAGOS_N4.csv` |
| 12 | Monaco | 4 | ON | `12_ON_MONACO_N4.csv` |

### Controles OFF

- Interlagos: **1 corrida nova** com o comando canônico e **sem** `--launch-steer-mute`, `--variedade 0`; `cmp` byte a byte contra `experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.csv` e seu sidecar. Divergência = PARE. Este controle não redefine o OFF canônico: os valores de referência continuam sendo os bytes commitados.
- Monaco: **1 corrida nova** com o comando canônico e **sem** `--launch-steer-mute`, `--variedade 0`; `cmp` byte a byte contra `experiments/composite-1/promocao-1/3_R3_MONACO_RACE.csv` e seu sidecar. Divergência = PARE. Este controle não redefine o OFF canônico: os valores de referência continuam sendo os bytes commitados.

Se o header comentário do CSV mudar quando a flag está OFF, por exemplo por uma lista de flags no cabeçalho, é PARE. O header não será ajustado para fazer `cmp` passar; a saída OFF tem de ser byte-idêntica por construção.

### Tratamentos ON

A única diferença entre ON e o OFF correspondente é `--launch-steer-mute` e, para N=1..4, a realização `--variedade N`. Não usar `--residual-override`, `--pguard`, `--launch-cap` ou `--launch-stagger`.

**Selo de variedade:** N=5..8 permanecem selados até o C7; nenhuma corrida deste ciclo usa N>4.

## 4. Mecanismo C1-B pinado

### 4.1 Ação

No caminho composite, antes do `tanh` final:

- fora de D_L: `a = tanh(m_solo + g·r)`;
- dentro de D_L: `a_steer = tanh(m_solo_steer)` e `a_long = tanh(m_solo_long + g·r_long)`.

O longitudinal não muda. O residual é calculado e instrumentado normalmente. `g_gate`, `res_0..15`, `r_norm` e as observações mantêm o schema existente; a flag não muda o espaço de observação nem treina modelo.

### 4.2 Janela D_L

D_L é estado por carro, uso único, indexado pela identidade SHA da pista:

| SHA16 da pista | `S_L_END` |
|---|---:|
| `164876196eb12174` Interlagos v2 | 2718,3 m |
| `67ca11dc211c8c78` Monaco v2 | 3331,2 m |

A cada tick, enquanto o estado ainda está ativo, a flag aplica o mute somente se:

- carro está on-track;
- `s <= S_L_END` no frame da pista;
- `t_s <= T_L_MAX_S`, com `T_L_MAX_S = 10,0 s`.

A condição `v >= V_L` foi descartada. C1-A mostrou que ela não fecha na largada de Monaco e só fecha em 6/10 carros antes de 10 s em Interlagos; três saídas N=0 ocorrem a 14,2–14,9 m/s, acima do teto exploratório 12,6.

O estado termina uma única vez pelo primeiro motivo verdadeiro, registrado por carro:

- `crossed`: cruzou `S_L_END`;
- `offtrack`: ficou fora do asfalto antes de cruzar;
- `deadline`: `t_s > 10,0 s` enquanto ainda não terminou.

Depois de terminado, nunca reativa, mesmo se o carro voltar para `s <= S_L_END`. SHA desconhecido, incluindo futura v3, = erro explícito antes da corrida. Sem composite ativo = erro explícito com a flag ON.

A coluna `launch_steer_mute` é aditiva e só aparece com a flag ON. O runner registra também `launch_steer_mute_end_reason` por linha; a primeira razão final por carro é a tabela de disclosure. OFF permanece sem essas colunas e deve ser byte-idêntico.

### 4.3 Wiring obrigatório

A flag `--launch-steer-mute` existe nos dois runners e nos construtores correspondentes:

- `backend/model_train/race_diagnostic.py` para medição;
- `backend/scripts/run_race_10_cars.py` para demonstração visual.

No `race_diagnostic.py`, a flag é válida apenas com `--profile composite` e é mutuamente exclusiva com `--pguard`, `--launch-cap` e `--launch-stagger`. Default OFF = código/saída byte-idênticos.

## 5. C1-A: trava de falsificação e classe steer-atribuível

A trava é direcional, não a razão instável `g·r/pre`:

- residual para o lado da saída em **>=75%** das janelas `authority=policy`;
- solo para longe em **>=75%** das janelas;
- mediana, sobre as janelas, de `|g·r|/(|m_solo|+|g·r|)` **>=0,40**.

Os números C1-A observados são 16/18, 18/18, 0,473/0,540. Disclosure obrigatório: as 18 janelas não são independentes (12 vêm de 9 carros) e cerca de 66% têm contato no entorno. A trava é só mecanismo de entrada; C1P1 é o gate do efeito.

**Definição ratificada de `Z_RETA exposta` para C1P1a:** uma saída da lista já emitida pelo instrumento em `events.z_reta` (`t <= 10,0 s` e `s ∈ [z_reta[0], z_reta[1])`) cujo carro tem `car_car == 0` em **todas** as linhas com `start - 10 <= tick < start`, onde `start` é o tick do próprio evento. São 10 ticks lógicos = 1,0 s = 5 amostras a 5 Hz; o tick da saída não entra.

O C1P1a não classifica por independência estatística nem por canal. Ele mede se a saída aconteceu com pista livre no segundo anterior. Qualquer ocorrência ON de `Z_RETA exposta` exige, antes do veredito, atribuição por carro: motivo de término de D_L, timeline de contato em `t_s ∈ [t_exit−1, t_exit]`, `g`, `m_solo_steer`, `g·r_steer`, `exit_dir` e estado físico correspondente.

Baseline congelado, calculado dos 10 CSVs OFF já existentes:

| Pista | N0 | N1 | N2 | N3 | N4 | total |
|---|---:|---:|---:|---:|---:|---:|
| Interlagos | 4 | 3 | 4 | 4 | 3 | **18** |
| Monaco | 3 | 3 | 3 | 3 | 3 | **15** |
| Total | 7 | 6 | 7 | 7 | 6 | **33 expostas em 77 saídas Z_RETA** |

**Gate C1P1a:** `Z_RETA exposta = 0` em cada uma das cinco realizações ON de cada pista. O baseline é disclosure; o gate é estrutural e não soma exposições entre realizações.

C1-A permanece report-only e não emite gate de comportamento. A trava direcional C1-A continua registrada como evidência de mecanismo, separada do C1P1a de efeito.

## 6. Gates do C1

As comparações de contagem são por soma de N=0..4 por pista, salvo onde a regra diz por realização. O ON é comparado ao OFF da mesma pista e N. A tabela por realização ON × OFF é disclosure obrigatório e alerta se qualquer ON >=3× o OFF correspondente.

| Gate | Agregação | Regra | Limite/papel |
|---|---|---|---|
| **C1P1a mecanismo** | por realização | 0 `Z_RETA exposta` em cada N=0..4 ON; exposta = `car_car==0` em todas as linhas do carro com `start−10 <= tick < start` | estrutural; qualquer ocorrência exige atribuição antes do veredito |
| **C1P1b efeito** | soma por pista | `Σ ON Z_RETA <= Σ OFF Z_RETA − 2σ` | Interlagos `<=59`; Monaco `<=30` |
| **C1P2** | soma por pista | excursões em `t<=60 s` (`excursions_t_le_60s`) com melhora material | Interlagos `<=166`; Monaco `<=321` |
| **B-1 contatos** | soma por pista | contatos totais ON não excedem OFF+2σ | Interlagos `<=2655`; Monaco `<=3021` |
| **Alerta B-1** | soma por pista | registrar a banda antiga +10% | Interlagos `<=2007`; Monaco `<=2386`; alerta, não gate duro |
| **PARE outlier** | por realização | ON >=3× OFF em contatos totais | PARE e disclosure |
| **R-2-T1** | soma por pista | Z_T1 `t<=60` ON não excede OFF+2σ | Interlagos `<=46`; Monaco `<=40` |
| **R-1 ritmo** | soma por pista | `Σ laps_total ON >= floor(0,95 × Σ laps_total OFF)` | Interlagos `>=209`; Monaco `>=144` |
| **R-2 fora** | soma por pista | `100·Σfora_ON <= 100·Σfora_OFF + Σlinhas` | +1 pp; gate |
| **S-1** | disclosure | contatos `t<=60` ON vs OFF | sem gate formal neste ciclo |
| **Integridade** | por corrida | D2: linhas, identidade, sidecar, variedade, 2 leituras e hashes | falha = PARE |

**C1P1b:** a margem OFF−2σ foi congelada pelo C0 closing como `<=59` Interlagos e `<=30` Monaco, aplicada ao total bruto de saídas Z_RETA. A leitura de mecanismo da C1-A continua disclosure separado: o mute deve remover as saídas atribuíveis ao canal de esterço sem aumentar o total bruto; o total bruto é que entra neste gate.

**S-1:** permanece fora do gate formal por causa da variância; aparece na tabela e no relatório de ruído. O risco de acelerar o pelotão é coberto por B-1, R-1, R-2, C1P1a e C1P1b.

## 7. Integridade e PAREs

- Controle OFF com a flag desligada deve ser byte-idêntico ao CSV/eventos da promocao-1. Divergência = PARE imediato.
- Qualquer saída ON sem sidecar, sem coluna de motivo, sem 30.002 linhas, sem identidade da pista, sem residual `6210fff6`, ou sem `variedade=N` = PARE.
- Qualquer reexecução, timeout, corrida fora das 12, seed diferente de 0, N diferente de 0..4, `--residual-override`, leitura de shard TEST, alteração de v1/v2/base_metrics ou mudança de default = PARE.
- Não usar o C1 para ajustar `S_L_END`, `T_L_MAX`, os limiares direcionais, o limite 0,40 ou as margens 2σ depois de observar ON.

## 8. Implementação e orçamento da etapa

Antes das corridas:

1. testes de flag OFF byte-idêntica;
2. teste de mute só no eixo de esterço;
3. testes da máquina D_L: crossed/offtrack/deadline, uso único, SHA desconhecido;
4. teste da coluna condicional e do motivo por carro;
5. teste de exclusividade das flags;
6. suíte serial e diff do fail-set conhecido.

Depois: 2 controles OFF (corridas novas, flag desligada, cmp contra a promocao-1) e 10 ON seriais conforme §3. Extrair `base_metrics` e `realismo_metrics` duas vezes por corrida. Gerar a tabela C1P1a por carro, C1P1b, disclosure por realização, timeline de contatos e o veredito mecânico.

## 9. Correções desta versão e decisão do dono

Versão 1.1 incorpora as correções ratificadas antes do freeze:

1. **Orçamento e controles:** 12 corridas totais; 2 controles OFF são corridas novas com flag desligada e `cmp` contra os CSVs/sidecars da promocao-1; os 10 ON foram renumerados de 3 a 12.
2. **C1P1b:** existe um único limite formal por pista, `<=59` Interlagos e `<=30` Monaco; não há limite alternativo.
3. **C1P2:** usa `excursions_t_le_60s`, não o número de saídas Z_RETA em `t<=60`.
4. **R-1:** limites congelados em `>=209` Interlagos e `>=144` Monaco.
5. **Selo:** N=5..8 permanecem selados até C7; nenhuma corrida desta etapa usa N>4.
6. **Header OFF:** se o header comentário mudar com a flag desligada, é PARE; não se corrige o header para fazer o `cmp` passar.

**Decisão do dono:** opção (a), com 2 controles reais OFF e orçamento de 12 corridas.

## 10. Freeze

Este arquivo é staged sem commit para revisão do dono. O executor para aqui. O dono deve congelar este prereg antes de qualquer edição de produção ou corrida C1-B.
