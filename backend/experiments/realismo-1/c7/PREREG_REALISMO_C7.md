# PREREG REALISMO-1 · C7 — consolidação final em N=5..8

**Versão:** 1.0 · **Estado:** pré-freeze; ZERO simulação e ZERO alteração de código nesta etapa.

**Branch:** `feat/sanidade-produto`. **HEAD base:** `3b5d80a263d4e5a39d35d8ee73566bec6da6a4a0`.

**Task:** 15 do `backend/PLANO_REALISMO_BOTS_1.md`. O Ciclo C6 foi encerrado pelo Dono no commit `3b5d80a` com veredito FAIL para `--lat-offset-slots`; o default OFF permanece mantido. Este documento registra a preregistração formal do Ciclo C7 e aguarda o Freeze do Dono antes de qualquer corrida.

## 1. Objetivo e escopo

Consolidar o Programa REALISMO-1 em N=5, 6, 7 e 8, comparando oito corridas OFF com oito corridas ON seriais, nas pistas Interlagos e Monaco. O C7 avalia exclusivamente a combinação de mecanismos já homologados; não reabre mecanismos reprovados ou rejeitados, não altera produção e não inicia simulação antes do Freeze formal do Dono.

## 2. Status dos mecanismos do Programa REALISMO-1

| Ciclo/mecanismo | Status congelado |
|---|---|
| C1 (`--launch-steer-mute`) | **REPROVADO** — default OFF mantido |
| C2 (`--rejoin-handoff align`) | **APROVADO / HOMOLOGADO** |
| C3 (`--rejoin-ramp`) | **APROVADO / HOMOLOGADO** — com `--gov vplan` |
| C4/C5 (`interlagos_v3`) | **REJEITADO / FALLBACK adotado** — geometria v2 inalterada |
| C6 (`--lat-offset-slots`) | **REPROVADO** — default OFF mantido |

### 2.1 Combinação C7 ON

A única combinação ON autorizada para o C7 é:

```text
--rejoin-handoff align --rejoin-ramp --gov vplan
```

Nenhuma flag de C1, C4/C5 ou C6 será incluída nas corridas C7.

## 3. Deslacramento formal das variedades de teste

As variedades de teste **N=5, N=6, N=7 e N=8** são formalmente deslacradas para o planejamento do C7, permanecendo em **quarentena estrita até este momento**. A retirada efetiva da quarentena, a execução de qualquer comando e a produção de qualquer saída dependem do Freeze explícito do Dono.

## 4. Pins e hashes SHA-256

| Item | Caminho | SHA-256 |
|---|---|---|
| Diagnóstico de corrida | `backend/model_train/race_diagnostic.py` | `ba884e9894dc6b5a8ea6cd5d6a607fd7ff3656fc8aa08910f1d433ff7fc17fcf` |
| Runner de 10 carros | `backend/scripts/run_race_10_cars.py` | `e426919aade4d8f83ec2c8bcf176e620bf64ca1eee1c79304d168ce2f4dfe23e` |
| Perfil de velocidade | `backend/model_train/velocity_profile.py` | `a2953bac36064e3a531df7e43bd840efeb0a9b29a823096fa01341651024f5dc` |
| Métricas base | `backend/scripts/base_metrics.py` | `9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728` |
| Métricas de realismo | `backend/scripts/realismo_metrics.py` | `e5a7ecb42fd9bfd3297935d974a53174b51eb822a877b33e4ed4a208a590ac7b` |
| Veredito de saídas | `backend/scripts/saidas_verdict.py` | `e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c` |
| Geometria congelada Interlagos v2 | `backend/model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| Geometria congelada Monaco v2 | `backend/model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |

## 5. Orçamento e matriz de 16 corridas

O orçamento total é de **16 corridas seriais**: 8 OFF e 8 ON.

| Grupo | Pista | Variedades | Quantidade | Tratamento |
|---|---|---:|---:|---|
| OFF | Interlagos | N=5..8 | 4 | Sem flags de tratamento |
| OFF | Monaco | N=5..8 | 4 | Sem flags de tratamento |
| ON | Interlagos | N=5..8 | 4 | `--rejoin-handoff align --rejoin-ramp --gov vplan` |
| ON | Monaco | N=5..8 | 4 | `--rejoin-handoff align --rejoin-ramp --gov vplan` |

### 5.1 Configuração padrão canônica

```text
--profile composite --n-cars 10 --ticks 6000 --laps 99 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing --seed 0
```

As corridas ON acrescentam somente:

```text
--rejoin-handoff align --rejoin-ramp
```

Cada corrida deve gerar:

- um CSV com **30.002 linhas**;
- um sidecar `_events.csv`;
- um arquivo `.log`.

Cada corrida deve passar por dupla leitura de extração determinística com `base_metrics` e `realismo_metrics`, com `cmp=0` e cross-hash canônico conferido. Qualquer divergência, falha de integridade ou ausência de artefato aciona PARE antes da continuação da matriz.

## 6. Metas Globais do Programa REALISMO-1

Conforme o relatório final, seção 1 do plano:

- **Contatos totais:** redução `>= 15%`;
- **Tempo fora da pista:** redução `>= 5` pontos percentuais;
- **Saídas na reta de largada:** `0` saídas;
- **Deadlocks:** `0` deadlocks.

Estas metas globais serão reportadas no fechamento do programa; os gates específicos do C7 permanecem obrigatórios e independentes.

## 7. Gates formais de não-regressão do C7

| Gate | Regra congelada |
|---|---|
| B-1 — contatos totais | `soma ON <= ceil(1.10 * soma OFF)` em N=5..8 |
| R-1 — ritmo | `total de voltas ON >= total OFF - 5%` |
| R-2 — contenção | `linhas fora ON <= linhas fora OFF` |
| C23P primário | Redução material `>= 2 sigma` nas linhas fora do limiar |

Os gates devem ser avaliados com agregação pareada por pista e variedade, preservando a comparabilidade OFF/ON e divulgando os valores individuais, somas, diferenças e incertezas usadas no C23P.

## 8. Regras de infraestrutura e governança

Todo comando de execução, extração, validação ou inspeção operacional deverá usar o prefixo explícito composto:

```text
cd /home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend && .venv/bin/python ...
```

Aplicam-se ainda as seguintes travas:

1. Os arquivos não rastreados `.cursor/`, `.kiro/` e `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` permanecem estritamente fora do stage.
2. Nenhuma simulação pode ser iniciada antes do Freeze do Dono.
3. Nenhum mecanismo reprovado, rejeitado ou fora da combinação C7 ON pode ser ativado.
4. A geometria `interlagos_v3` não será criada, lida ou usada; a geometria congelada permanece em v2.
5. Não haverá commit, alteração de código ou modificação de produção como parte desta preregistração.

## 9. PARE e Freeze do Dono

**PARE FORMAL:** preregistro avaliado e auditado pelo Dono.

**Validação do Dono:**
- [x] Versão 1.0, HEAD `3b5d80a263d4e5a39d35d8ee73566bec6da6a4a0` e branch `feat/sanidade-produto` conferidos;
- [x] Hashes dos 8 artefatos canônicos conferidos e coincidentes com o codebase congelado;
- [x] Status dos mecanismos de C1 a C6 ratificados;
- [x] Combinação C7 ON congelada exclusivamente em `--rejoin-handoff align --rejoin-ramp --gov vplan`;
- [x] Proibição estrita de qualquer flag de C1, C4/C5 ou C6 ratificada;
- [x] Geometria congelada v2 inalterada (`interlagos_v2.json` e `Monaco_v2.json`);
- [x] Deslacramento formal e unfreeze das variedades de teste N=5, 6, 7 e 8 aprovados para execução;
- [x] Orçamento estrito de 16 corridas seriais (8 OFF + 8 ON) homologado;
- [x] Gates B-1, R-1, R-2, C23P e protocolo de integridade determinística aprovados;
- [x] Travas de governança e isolamento de strays (`.cursor/`, `.kiro/`, `ANEXO_SAIDAS_1_ERRATAS.md`) confirmadas;
- [x] ZERO edição de código de produção autorizada no C7.

**Decisão do Dono:** CONGELADO E HOMOLOGADO.
Autorizada a execução das 16 corridas do Ciclo C7 (Task 15):
1. 8 corridas baseline OFF em N=5..8 (4 Interlagos + 4 Monaco);
2. 8 corridas tratamento ON em N=5..8 (4 Interlagos + 4 Monaco com `--rejoin-handoff align --rejoin-ramp --gov vplan`);
3. 32 extrações determinísticas duplas (`cmp=0`);
4. Relatório final de execução e consolidação das metas globais do programa REALISMO-1.

**Data:** 2026-11-04    **Status:** FREEZE EFETUADO
