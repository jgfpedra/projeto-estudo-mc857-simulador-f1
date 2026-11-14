# PREREG REALISMO-1 · C6 — trenzinho e deadlock

**Versão:** 1.0 · **Estado:** pré-freeze; C6-A report-only concluído; ZERO simulação, ZERO edição de produção nesta etapa · **Data:** 2026-11-02.

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `c5ade414eb10e177e5caeb9d3ef7f4019d992de4`. **Index:** C6-A e este prereg serão staged; nenhum commit será feito antes do Freeze do Dono. Strays conhecidos, nunca stagear: `.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.

**Plano-mãe:** `backend/PLANO_REALISMO_BOTS_1.md` v1.1, Tasks 13–14. **C4:** encerrado pelo Dono com PARE de RMS e FALLBACK; C6-A é análise offline do P5.

## 1. Objetivo

Medir, sem simulação, a ocorrência de pelotão colado, perda de fluidez de ultrapassagem e deadlock nos bytes OFF disponíveis dos perfis composite e cego. Derivar um padrão de offset lateral por slot de grid para a futura flag opt-in `--lat-offset-slots`, sem alterar produção nesta etapa.

O mecanismo C6-B será avaliado somente depois de um preregistration congelado e da aquisição dos oito OFF cegos N=1..4 que ainda não existem no cache. C6-A não homologa a flag, não escolhe um novo default e não lê shards de treino.

## 2. Proveniência e hashes

| Item | Caminho | SHA-256 |
|---|---|---|
| Runner de medição | `backend/model_train/race_diagnostic.py` | `12976b93c8100c4f95506bea7cec396df37b6e95cf6387595ae971e8d819e852` |
| Instrumento canônico | `backend/scripts/realismo_metrics.py` | `e5a7ecb42fd9bfd3297935d974a53174b51eb822a877b33e4ed4a208a590ac7b` |
| Auditoria de geometria | `backend/scripts/saidas_verdict.py` | `e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c` |
| Ambiente/obs | `backend/model_train/f1_env.py` | `e488967f3d7dee5f79bf80bc07724be4f075b9f8e48c59f19ca5e8ee112755a2` |
| Geometria Interlagos v2 | `backend/model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| Geometria Monaco v2 | `backend/model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| C6-A analyzer | `backend/scripts/c6a_train_analysis.py` | `58374435ba2abafb62da2c0f589242793fd2b3527b3affd5c68de2926b20f320` |
| C0 golden Interlagos N0 | `backend/experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.csv` | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` |
| C0 golden Monaco N0 | `backend/experiments/composite-1/promocao-1/3_R3_MONACO_RACE.csv` | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` |
| Cego Interlagos N0 | `backend/experiments/composite-1/base-2/2_R2_INTERLAGOS_RACE_BLIND.csv` | `9d2a08427d4c5bdad0d6611df2caa7b4d7f02c5a5584c71a49d412c763c67e12` |
| Cego Monaco N0 | `backend/experiments/composite-1/base-2/4_R4_MONACO_RACE_BLIND.csv` | `15fb3da069adb7369741e90fdffca00f12cbe2abd75481b217c9c962bfacdd11` |

Cada corrida usada também tem sidecar e JSON canônico/extraído nos diretórios de origem. Os quatro arquivos cegos N=1..4 por pista **não existem**; não são substituídos pelos OFF composite N=1..4.

## 3. Definições congeladas de C6-A

### 3.1 Campo físico e sinal lateral

- `signed_lat_m = obs4 * 6,0 m`;
- `obs4` é o erro lateral normalizado da observação, não a coluna física `lat`;
- positivo significa à esquerda da linha central, conforme o produto vetorial da projeção da pista;
- `s` é circular, com comprimento 4160,4 m em Interlagos e 3335,2 m em Monaco;
- um par está colado no tick se `|Δlat| < 2,0 m` e `|Δs_circular| < 5,5 m`;
- episódio contíguo exige amostras consecutivas de 5 Hz;
- colado é episódio com mais de 2,0 s, equivalente a pelo menos 10 linhas de 0,2 s;
- deadlock é episódio colado com mais de 10,0 s, equivalente a mais de 50 linhas;
- gaps, wrap e restauração do comprimento da pista seguem a métrica D3 de `realismo_metrics.py`, sem usar o `L_TRACK` de Interlagos para Monaco.

### 3.2 Fluidez de ultrapassagem

Para cada episódio e cada carro, o relatório registra:

- par de carros;
- início, fim e duração;
- `Δs` assinado no início e no fim;
- se houve inversão do sinal de `Δs` durante o episódio;
- crossings totais e crossings que ocorreram enquanto o carro estava em um episódio colado.

A proporção de tempo de trenzinho é `train_rows / sample_rows`, onde `train_rows` é a união, por carro, das linhas pertencentes a episódios colados. A proporção de voltas é `train_lap_crossings / laps_total`. Essas métricas são disclosure de C6-A, não substituem os gates do C6-B.

### 3.3 Slot de grid e offset

O slot é recuperado pela ordem dos drivers na primeira linha de tick do CSV, de 0 a 9. O instrumento registra a tabela `driver -> slot` por corrida; não usa índice incidental após ordenar por nome.

Para cada corrida, no intervalo `1,0 s <= t_s <= 20,0 s` e com `offtrack == 0`, calcula-se a mediana de `signed_lat_m` por slot. O centro da corrida é a mediana dos slots observados. O offset candidato é:

```text
off_i = clip(median_signed_lat(slot_i) - median_signed_lat(all_slots), -1,0 m, +1,0 m)
```

O relatório divulga os vetores por corrida e o vetor mediano por perfil entre as corridas disponíveis. `|off_i| <= 1,0 m` é obrigatório e preserva margem de pelo menos 5,0 m até a borda de meia-largura 6,0 m.

O resultado C6-A não escolhe silenciosamente um vetor final para C6-B: o Dono deve congelar um vetor por perfil ou um vetor comum depois de observar a matriz cega N=1..4.

## 4. Dados disponíveis e resultado C6-A

### Composite OFF

Disponíveis N=0..4 em Interlagos e Monaco:

- N=0: bytes canônicos da promocao-1;
- N=1..4: corridas OFF do C0, uma vez cada.

### Cego/race-blind OFF

Disponível somente N=0:

- Interlagos: `2_R2_INTERLAGOS_RACE_BLIND.csv`;
- Monaco: `4_R4_MONACO_RACE_BLIND.csv`.

N=1..4 não existem. O relatório C6-A registra essa lacuna e não trata o painel como matriz completa dos dois perfis.

Resumo observado:

| Perfil | Pista | N | colado s | deadlocks | tempo trem | voltas | fração de voltas trem |
|---|---|---:|---:|---:|---:|---:|---:|
| composite | Interlagos | 0 | 34,6 | 0 | 1,14% | 44 | 0,00% |
| composite | Interlagos | 1 | 43,2 | 1 | 1,44% | 45 | 0,00% |
| composite | Interlagos | 2 | 88,0 | 3 | 2,88% | 44 | 0,00% |
| composite | Interlagos | 3 | 47,4 | 1 | 1,55% | 44 | 0,00% |
| composite | Interlagos | 4 | 33,8 | 1 | 1,13% | 43 | 0,00% |
| composite | Monaco | 0 | 82,2 | 1 | 2,10% | 31 | 0,00% |
| composite | Monaco | 1 | 111,4 | 1 | 3,27% | 31 | 12,90% |
| composite | Monaco | 2 | 97,4 | 2 | 3,25% | 32 | 6,25% |
| composite | Monaco | 3 | 93,4 | 1 | 2,46% | 29 | 13,79% |
| composite | Monaco | 4 | 101,2 | 2 | 3,34% | 29 | 6,90% |
| blind | Interlagos | 0 | 178,2 | 6 | 5,04% | 49 | 0,00% |
| blind | Monaco | 0 | 108,6 | 3 | 3,45% | 32 | 18,75% |

O composite apresenta padrão mensurável, embora pequeno em tempo total e variável por realização. O cego N=0 apresenta mais colado/deadlock que o composite, mas não há dados cegos N=1..4 para estimar ruído do perfil.

Offsets medianos candidatos derivados:

| Slot | Composite m | Blind N0 m |
|---:|---:|---:|
| 0 | +0,273 | +0,251 |
| 1 | -1,000 | -0,003 |
| 2 | -0,693 | -0,549 |
| 3 | +0,590 | -0,042 |
| 4 | +1,000 | -0,879 |
| 5 | -0,784 | -0,518 |
| 6 | +0,018 | +0,896 |
| 7 | -0,902 | +0,142 |
| 8 | +0,064 | +0,694 |
| 9 | +1,000 | +0,180 |

## 5. Mecanismo C6-B a congelar

A flag opt-in `--lat-offset-slots` altera exclusivamente a observação lateral policy-facing:

```text
tels[i, 4] = (signed - off_i) / hw
```

O mecanismo não altera:

- `drv_signed`;
- `drv_lat`;
- posição física, `s`, heading ou raios;
- CSV físico;
- física, pesos, residual, longitudinal ou demais observações;
- comportamento OFF e seus bytes.

A chave é o slot de grid congelado do run. O runner visual e o runner de medição devem receber o mesmo mapeamento driver-slot. O mecanismo deve falhar alto se a ordem de grid não estiver disponível, se houver slot fora de 0..9 ou se algum `|off_i| > 1,0 m`.

## 6. Orçamento do C6-B

O orçamento exato, a executar somente após novo Freeze do Dono, é:

- **8 OFF cegos:** N=1..4 × Interlagos/Monaco, executados uma única vez;
- **4 controles canônicos:** composite OFF e blind OFF, duas pistas, com `cmp` contra os bytes canônicos;
- **20 ON:** N=0..4 × dois perfis × duas pistas;
- total: **32 corridas C6-B**, serialmente, salvo redução formal de escopo pelo Dono.

N=5..8 permanecem selados até C7.

## 7. Gates formais do C6-B

Cada perfil é comparado ao próprio baseline OFF e às mesmas realizações N.

| Gate | Regra congelada | Agregação |
|---|---|---|
| C6 primário colado | `Σ glued_rows_ON < Σ glued_rows_OFF` | soma por pista/perfil |
| C6 primário deadlock | `deadlocks_ON(N) <= deadlocks_OFF(N)` para todo N | por realização |
| B-1 | `Σ contacts_ON <= (11*Σ contacts_OFF + 9)//10` | soma por pista/perfil |
| R-1 | `Σ laps_ON >= (95*Σ laps_OFF)//100` | soma por pista/perfil |
| R-2 | `100*fora_ON <= 100*fora_OFF + linhas` | taxa agregada |

O relatório deve divulgar contatos t<=60, fora%, offtrack rows, excursões, glue, deadlock, laps, crossings, alertas `ON >= 3×OFF` e os pares de ultrapassagem. O gate C6 primário não é inferido da fração de tempo isolada; usa `glued_rows` conforme D3.

## 8. Testes pré-corrida obrigatórios

Antes de qualquer corrida C6-B:

1. default OFF byte-idêntico nos dois runners;
2. fórmula de `obs4` e sinal lateral em teste sintético;
3. vetor por slot validado em `[-1,0,+1] m` e margem física mínima;
4. slot keyed por driver e sem estado compartilhado;
5. `drv_signed`, `drv_lat`, raios, CSV e física preservados;
6. flag rejeitada se a tabela de slots estiver ausente ou inválida;
7. controles OFF com `cmp` CSV e sidecar;
8. suíte serial com fail-set conhecido;
9. leitura dupla dos extratores, hashes e integridade D2;
10. prova de que nenhum shard TEST, treino, rede, geometria v3 ou outra flag experimental entra no ciclo.

## 9. Freeze do Dono

**Decisão do Dono:** HOMOLOGADO E CONGELADO.
1. O padrão de trenzinho e deadlocks é mensurável no perfil composite (28 a 109 s de pelotão colado, 1 a 3 deadlocks por corrida) e expressivo no perfil cego N=0 (108 a 178 s, 3 a 6 deadlocks). O escopo do mecanismo é mantido integralmente em ambos os perfis.
2. Congelados os vetores de offset por slot `off_i` em `[-1,0, +1,0] m` derivados na etapa C6-A.
3. Autorizada a divisão do orçamento em duas fases:
   - **C6-B1:** Aquisição da baseline OFF do perfil cego em N=1..4 (8 corridas seriais sem mecanismo);
   - **C6-B2:** Execução dos 4 controles canônicos (com prova `cmp`) e dos 20 tratamentos ON (--lat-offset-slots).
4. Nenhuma corrida ON, teste de integração ou edição de produção autorizada antes da baseline C6-B1.

**Data:** 2026-11-03    **Status:** FREEZE EFETUADO
