# PREREG REALISMO-1 · C4-A — engenharia de geometria da Junção

**Versão:** 1.0 · **Estado:** pré-freeze; ZERO processamento da linha real, ZERO simulação, ZERO edição de produção nesta etapa · **Data:** 2026-11-02 (America/Sao_Paulo).

**Branch:** `feat/sanidade-produto`. **HEAD na redação:** `3c9af2b6782328ed86de475ec81fb2608b0d2e53`. **Index na redação:** este prereg será staged; nenhum commit será feito antes do Freeze do Dono. Strays conhecidos, nunca stagear: `.cursor/`, `.kiro/`, `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.

**Plano-mãe:** `backend/PLANO_REALISMO_BOTS_1.md` v1.1, Task 10. **C3 encerrado:** `backend/experiments/realismo-1/c3/EXECUCAO_REALISMO_C3.md`, com C3b acionado em Interlagos e Monaco. Este documento congela o procedimento de C4-A; a leitura dos pickles e a engenharia C4-B/Task 11 só começam depois do Freeze do Dono.

## 1. Objetivo e escopo

Avaliar, exclusivamente offline, se a linha de corrida real observada no cache local sai do corredor de `±6,0 m` da geometria frozen `interlagos_v2` no setor da Junção, C08 `±30 m`.

A análise decide entre:

- **GEOMETRIA:** a linha real sai do corredor no setor focal. A decisão autoriza a Task 11 a construir o protótipo de avaliação `interlagos_v3.json`, trocando somente o setor C08;
- **FALLBACK:** a linha real permanece contida no corredor no setor focal. Não há alteração geométrica e deve ser redigido um relatório da aritmética do governor A5 para deliberação do Dono.

C4-A não edita `interlagos_v2.json`, não cria `interlagos_v3.json`, não altera `track_resolution.py`, não altera runners, controllers, física, pesos ou métricas de produção e não executa corrida.

## 2. Proveniência e pins

A tabela registra os hashes antes da leitura de qualquer conteúdo dos pickles. A inspeção feita nesta etapa limita-se à existência dos arquivos e ao SHA-256; nenhum pickle foi carregado com `pickle.load` antes do Freeze.

| Item | Caminho | SHA-256 |
|---|---|---|
| Geometria base frozen | `backend/model_train/tracks_frozen/interlagos_v2.json` | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| Resolução de pista | `backend/domain/track_resolution.py` | `f3fc6b2bd254bc3c00b9f353c6d199eb82383140d18a9756f3e3ddc1c4a51018` |
| Auditoria/geometria | `backend/scripts/saidas_verdict.py` | `e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c` |
| Position 2022 | `backend/cache/2022/2022-11-13_São_Paulo_Grand_Prix/2022-11-13_Race/position_data.ff1pkl` | `b254a8ea76e235603bde7128931ffa9965245cbd0c367e36cc9c67e0624c2431a` |
| Track status 2022 | `backend/cache/2022/2022-11-13_São_Paulo_Grand_Prix/2022-11-13_Race/track_status_data.ff1pkl` | `9ec7f8299218aaa28b9d0c12a4bf3f3df054cbd0c367e36cc9c67e0624c2431a` |
| Weather 2022 | `backend/cache/2022/2022-11-13_São_Paulo_Grand_Prix/2022-11-13_Race/weather_data.ff1pkl` | `2fa6a19afe389dacf47bb2cfc7b74b52a1a33393403a0245e00da30cf3cc6ac2` |
| Lap count 2022 | `backend/cache/2022/2022-11-13_São_Paulo_Grand_Prix/2022-11-13_Race/lap_count.ff1pkl` | `8597b465126cda56c32c331ce8d6b8d4b05da3b7fb048a111a29eaa558d0a922` |
| Position 2023 | `backend/cache/2023/2023-11-05_São_Paulo_Grand_Prix/2023-11-05_Race/position_data.ff1pkl` | `26e12de29988dfefe790cb4f17b56d4e78934e6ba090bd4c32c5d3177fb59b33` |
| Track status 2023 | `backend/cache/2023/2023-11-05_São_Paulo_Grand_Prix/2023-11-05_Race/track_status_data.ff1pkl` | `fbbaf596ceadefa9b6f865167802148d513cffd00d527ba4fcac25e8ccf52d6c` |
| Weather 2023 | `backend/cache/2023/2023-11-05_São_Paulo_Grand_Prix/2023-11-05_Race/weather_data.ff1pkl` | `326ab172affc4836951367efe9ac3ac24e146c79973f0ab93baf68c6fe7962d7` |
| Lap count 2023 | `backend/cache/2023/2023-11-05_São_Paulo_Grand_Prix/2023-11-05_Race/lap_count.ff1pkl` | `d76eee0944b4d9445fb730aca3a7a9efe5bbda12b5f1fe4c4ed306308cab15a2` |
| Position 2024 | `backend/cache/2024/2024-11-03_São_Paulo_Grand_Prix/2024-11-03_Race/position_data.ff1pkl` | `2b1667600c9f4afce8fa4e18295fcece90b04d182eb8017b51a5b79b82303897` |
| Track status 2024 | `backend/cache/2024/2024-11-03_São_Paulo_Grand_Prix/2024-11-03_Race/track_status_data.ff1pkl` | `1ad22c3fcd9c4621ce8f481c786c93eb53679952d3528311f8b93db62970d179` |
| Weather 2024 | `backend/cache/2024/2024-11-03_São_Paulo_Grand_Prix/2024-11-03_Race/weather_data.ff1pkl` | `2c409ddb7195b1f2c7981e86c7402443e5445d3601280c50a68d9e9ff3357e6f` |
| Lap count 2024 | `backend/cache/2024/2024-11-03_São_Paulo_Grand_Prix/2024-11-03_Race/lap_count.ff1pkl` | `1db85364a69bdd4ec6b52752012d7ec7f25084eae53ce436f32f160755a20e70` |

Pins geométricos adicionais da v2:

- SHA embutido da geometria frozen: `164876196eb12174`;
- identidade dos waypoints v1/v2 registrada pelo plano: `24461ba0b6c38983`;
- `width_m = 12,0 m`, meia-largura `HW = 6,0 m`;
- `n_wp = 1131`;
- `sf_idx = 729`;
- comprimento da pista: `4160,4 m`;
- `SF_S = 2655,0 m`.

As coordenadas de `position_data.ff1pkl` serão interpretadas como decímetros e convertidas uma única vez para metros por `unit_scale = 0,1`. A fonte será lida diretamente por `pickle.load`. FastF1 não será importado nem usado para resolver a sessão ou a telemetria.

## 3. Critérios de seleção de voltas válidas

Os critérios abaixo são aplicados antes de qualquer agregação de linha de corrida e não podem ser ajustados depois da inspeção dos dados:

1. `Rainfall == False` para a volta inteira;
2. `TrackStatus == '1'` em toda a extensão temporal da volta;
3. voltas com `InLap == True` ou `OutLap == True` são descartadas;
4. a Volta 1 é sempre descartada, pois contém largada e formação do grid;
5. a volta precisa ter posição `X` e `Y` utilizável para a volta inteira, sem conversão parcial ou preenchimento silencioso;
6. são aceitas somente voltas da sessão Race das edições 2022, 2023 e 2024 nos pickles congelados acima;
7. o mínimo é **N = 15 voltas válidas por setor no conjunto pooled das três edições**. O relatório deve divulgar N por edição e por setor. Se qualquer setor analisado tiver menos de 15 voltas válidas pooled, a etapa entra em **PARE por insuficiência amostral** antes da regra GEOMETRIA/FALLBACK.

A agregação pooled dá o mesmo peso a cada volta, não a cada amostra bruta. Uma volta válida será reamostrada no procedimento definido abaixo antes de entrar na mediana por bin.

A edição de 2024 continua elegível somente se passar os filtros congelados. O prereg não substitui chuva por pista seca, não relaxa `TrackStatus` e não transforma volta inválida em observação válida.

## 4. Registro de frame de coordenadas

O registro será feito separadamente por edição/sessão, antes da projeção final:

1. interpretar `X` e `Y` como metros após multiplicar por `0,1`;
2. construir a linha de referência da sessão a partir das voltas válidas reamostradas;
3. testar primeiro a identidade direta com o referencial XY da `interlagos_v2`, sem rotação, translação ou escala;
4. se a identidade direta não for aceitável, estimar uma transformação de Procrustes rígido, com rotação própria e translação, sem escala e sem reflexão (`det(R)=+1`);
5. registrar RMS, rotação, translação, método escolhido e número de pontos usados por edição;
6. usar a transformação escolhida para todos os pontos daquela edição, sem escolher transformação por setor ou por volta.

A correspondência entre a polilinha da sessão e a v2 será resolvida por amostragem uniforme, fechamento circular e busca do deslocamento cíclico que minimiza o RMS antes da avaliação do Procrustes. O procedimento não pode usar a linha real para escolher entre identidade e Procrustes depois de olhar a contenção no C08.

**PARE duro:** se o RMS do alinhamento final for `> 5,0 m` em qualquer uma das três edições, interromper e não produzir decisão GEOMETRIA/FALLBACK.

## 5. Projeção, bins e contenção

Para cada volta válida, depois do registro de frame:

1. converter a sequência XY para metros;
2. projetar cada ponto na polilinha fechada da `interlagos_v2`;
3. obter `s_v2` pela posição de arco do segmento mais próximo;
4. obter o desvio lateral signed pela orientação do segmento v2, preservando o sinal para auditoria;
5. reamostrar cada volta em bins de `2,0 m` de `s_v2`, com uma observação por bin e interpolação linear somente dentro do intervalo coberto pela própria volta;
6. em cada bin, calcular a mediana e o IQR dos desvios laterais entre as voltas válidas, com cada volta tendo peso igual;
7. não preencher bins sem observações e não usar esses bins para formar um trecho contíguo;
8. registrar também o número de voltas contribuintes por bin.

O corredor de contenção é `|desvio mediano| <= 6,0 m`. A saída do corredor exige:

```text
abs(desvio_mediano) > 6,0 m
```

em trecho contíguo de pelo menos `X = 10,0 m`. Como os bins têm 2,0 m, o trecho precisa conter pelo menos cinco bins consecutivos completos, medidos pelo intervalo coberto dos bins. A desigualdade é estrita; exatamente `6,0 m` não sai do corredor.

O IQR é disclosure obrigatório e não altera o gate primário. A linha mediana será reportada por bin junto com IQR, N de voltas, método de frame e hashes das fontes.

### Setor focal da Junção

O C08 nominal da v2 é `[2276,2; 2344,2] m`. A janela decisória C08 `±30 m` é congelada como intervalo inclusivo:

```text
[2246,2; 2374,2] m
```

A decisão GEOMETRIA só pode ser acionada por um trecho qualificado de saída do corredor formado por bins completamente contidos nessa janela focal. Trechos fora da janela são reportados, mas não acionam a decisão C4.

A tabela de κ/raio exigida pela Task 11 será apenas um disclosure posterior. Ela não pode substituir o teste de desvio lateral nem alterar a regra de decisão.

## 6. Regra de decisão pinada a priori

A regra é congelada antes de carregar os pontos XY das voltas válidas:

### GEOMETRIA

Acionada **se e somente se** existir, na janela C08 `±30 m`, um trecho contíguo de pelo menos `10,0 m` em que o desvio lateral mediano satisfaça `abs(mediana) > 6,0 m`.

Nesse caso, a Task 11 fica autorizada a construir, em ciclo próprio e ainda sem promoção:

- `interlagos_v3.json` como v2 com somente o setor C08 trocado pela linha mediana real;
- emendas geométricas suavizadas em `±20 m` ao redor do setor trocado;
- `sf_idx` recalculado e registrado;
- campos de proveniência com sessões, voltas válidas, método, RMS, transformação, fonte e SHA da v2 base;
- SHA embutido recalculado;
- carregamento somente por seletor explícito `_v3`, estrito e sem fallback em `track_resolution.py`.

A decisão GEOMETRIA não autoriza corrida, promoção, treino ou edição do runner. Ela autoriza apenas a abertura da Task 11 conforme prereg próprio ou seção subsequente congelada.

### FALLBACK

Acionado se a linha real estiver inteiramente contida no corredor `±6,0 m` dentro da janela C08 `±30 m`, isto é, se não existir trecho qualificado de saída do corredor.

Nesse caso:

- nenhuma geometria será alterada;
- `interlagos_v3.json` não será criado;
- será redigido um relatório da aritmética do governor A5 para deliberação do Dono;
- a decisão sobre abrir ciclo posterior ficará com o Dono.

### PARE

O resultado é PARE, sem GEOMETRIA/FALLBACK, se ocorrer qualquer uma destas condições:

- RMS final de frame `> 5,0 m` em qualquer edição;
- menos de 15 voltas válidas pooled em qualquer setor analisado;
- arquivo, hash ou schema de fonte divergente dos pins;
- pickle ilegível, estrutura incompatível ou coordenadas não finitas;
- ausência de `Rainfall`, `TrackStatus`, `_extended_timing_data.ff1pkl` com `NumberOfLaps`, `PitInTime`, `PitOutTime`, `Time` e `LapTime`, ou `lap_count` necessários para aplicar os filtros;
- tentativa de usar FastF1, rede, API remota ou preset de geometria;
- qualquer leitura da linha real antes do Freeze deste prereg.

## 7. Trava de segurança da janela de largada

A janela da largada nunca será remendada por C4. A geometria v2 e qualquer eventual v3 devem preservar integralmente:

- fundo do grid e reta de largada;
- `Z_RETA` Interlagos `[2608,2; 2718,3)`;
- `Z_T1` Interlagos `[2718,3; 2882,3]`;
- `sf_idx = 729` até que um ciclo próprio autorize alteração;
- todos os constantes e gates de C1/C2/C3 em coordenadas `s` da v2.

A suavização da eventual Task 11 é limitada ao entorno do C08 e não pode alcançar ou alterar a janela de largada. A v3 será sempre avaliação-only; qualquer promoção futura exige rederivação própria de todas as constantes em coordenadas `s` da v2.

## 8. Entregáveis da Task 11, se GEOMETRIA for acionada

Somente após decisão GEOMETRIA e autorização do Dono, a Task 11 deverá produzir:

- instrumento offline com leitura direta dos pickles;
- teste sintético com círculo e transformação conhecida;
- teste de preservação dos pins v1/v2 e dos golden existentes;
- relatório de frame por edição, RMS e transformação;
- tabela de mediana/IQR por bin de 2 m;
- teste de contenção por trecho e C08;
- tabela de κ/raio v2 versus linha real, com reamostragem de 4 m e suavizações de 20 m e 30 m;
- protótipo v3 somente se o Dono abrir a etapa correspondente.

Nenhum desses artefatos será criado na C4-A além deste preregistration.

## Emenda Formal do Dono nº 1 — timing estendido

A Emenda Formal do Dono nº 1 substitui a exigência de colunas explícitas `InLap`/`OutLap` no cache base pelo payload local `_extended_timing_data.ff1pkl`, sem alterar os demais limiares ou a regra GEOMETRIA/FALLBACK. Os três arquivos adicionais e seus hashes congelados são:

| Ano | Caminho | SHA-256 |
|---:|---|---|
| 2022 | `backend/cache/2022/2022-11-13_São_Paulo_Grand_Prix/2022-11-13_Race/_extended_timing_data.ff1pkl` | `92be7e1d21e1ada858e5eb4e1fc5e796e2918afc3130b82118ad848799356074` |
| 2023 | `backend/cache/2023/2023-11-05_São_Paulo_Grand_Prix/2023-11-05_Race/_extended_timing_data.ff1pkl` | `7b0bb638be91ffd63569dd1ffde28ed76a5eb967a37f27becfba1363a4b6761f` |
| 2024 | `backend/cache/2024/2024-11-03_São_Paulo_Grand_Prix/2024-11-03_Race/_extended_timing_data.ff1pkl` | `adea1c4499a099247e491616c821eb6e6775a19757af2701c9fd05e888fe12f8` |

O instrumento deve carregar `payload['data'][0]` como DataFrame, verificar o SHA antes do uso e usar os campos `NumberOfLaps`, `PitInTime`, `PitOutTime`, `Time` e `LapTime` para formar as janelas de volta:

```text
NumberOfLaps > 1
pd.isna(PitInTime)
pd.isna(PitOutTime)
t_end = Time
t_start = Time - LapTime
```

A janela só é válida se não houver `Rainfall == True` no `weather_data` entre `t_start` e `t_end` e se o status vigente em todo `[t_start, t_end]` for `Status == '1'`. A posição do piloto é fatiada na mesma janela temporal e convertida de decímetros para metros com `unit_scale = 0,1`. A emenda não autoriza inferência de box pela posição, velocidade ou lacunas.

A emenda mantém `N_min=15` pooled por setor, identidade/Procrustes rígido, PARE RMS `>5,0 m`, bins de 2 m, corredor `±6,0 m`, trecho mínimo `10,0 m`, C08 `[2246,2;2374,2] m` e a trava da janela de largada. O resultado pode ser `PARE` por schema, amostra, RMS ou insuficiência; a decisão GEOMETRIA/FALLBACK só existe depois de todas as três edições passarem os filtros.

## 9. Freeze do Dono

**Validação do Dono:**

- [x] versão, HEAD e branch conferidos;
- [x] hashes da geometria, módulos e cache conferidos;
- [x] filtros de volta, `N_min = 15`, bins de 2 m e `X = 10,0 m` congelados;
- [x] RMS máximo de 5,0 m e regra PARE aprovados;
- [x] janela C08 `[2246,2; 2374,2] m` aprovada;
- [x] regra GEOMETRIA/FALLBACK aprovada antes da leitura da linha real;
- [x] trava da janela de largada aprovada;
- [x] nenhuma simulação ou edição de produção autorizada nesta etapa.

**Decisão do Dono:** CONGELADO E HOMOLOGADO. Autorizada a execução da Task 11 (análise estritamente offline, leitura direta dos pickles locais, sem simulação).

**Data:** 2026-11-03    **Status:** FREEZE EFETUADO
