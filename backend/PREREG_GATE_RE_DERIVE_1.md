# PREREG GATE-RE-DERIVE-1 — adendo vinculante e resoluções finais

**Status:** prereg candidato a congelamento. A execução só fica autorizada depois de um commit dedicado deste arquivo, anterior a qualquer extração v4, patch de execução ou chamada de rede.

**Base imutável:** [`PREREG_GATE_RE_DERIVE_1_v0.md`](PREREG_GATE_RE_DERIVE_1_v0.md), preservado verbatim em commit anterior. O prereg efetivo deste ciclo é a base v0 **mais este adendo**. Os valores e resoluções abaixo substituem os `FALTA_DADO(repo)` e parâmetros marcados como `PROPOSTO` na base; todo o restante de S0–S10 continua aplicável sem alteração. Se a base e este adendo divergirem nesses campos, prevalece este adendo.

Este documento é parte do micro-ciclo exploratório descrito em S0–S10. Não promove pistas, não altera loader ou pools, não grava em paths frozen e não executa simulações. Nenhum parâmetro será revisto após a revelação dos seis novos resultados v4.

## 1. Resolução dos dados pendentes e inventário fechado

O inventário abaixo cobre os resultados reais v4 persistidos nos artefatos versionados deste projeto até este congelamento: a demonstração Monza do FONTE-2 e as nove pistas do PISTAS-EXPAND-1. A revisão de manifests, anexos, worklog, código e caches não identificou outro resultado v4 de pista real persistido. Testes sintéticos não são unidades de pista. Uso externo ao repositório ou não registrado não pode ser afirmado nem excluído por esta evidência.

| Lacuna do v0 | Resolução vinculante |
|---|---|
| 1. Inventário v4 completo | Dez medições históricas reais listadas nesta seção; seis streams alternativos identificados separadamente. Escopo: resultados e caches persistidos no repositório. |
| 2. Chave, fonte, método e revisão | Chaves/sessões/pilotos nas tabelas; OpenF1 `/location`; método `filter_race_line` v4 do commit `ffe0c59`, reusado pelo pipeline `6395354`. |
| 3. Comprimento oficial e proveniência | `backend/f1db.db`, `race.course_length`, 2024; SHA-256 declarado abaixo. |
| 4. Comprimento v4, delta e status | Tabela histórica abaixo, com valores publicados e status anterior. |
| 5. Uso anterior por pista | Uso de método/gate e divulgação listados por linha; o PISTAS-EXPAND-1 declarou pools `--tracks` e caches FastF1 intocados. Não há registro de adoção desses resultados em treino/avaliação; uso externo ou não registrado não é inferível. |
| 6. Holdout independente/cache completo | Nenhum circuito elegível; seleção mecânica e ausência documentadas abaixo. |
| 7. Conversão de unidade/metadados | `x/y` em decímetros, escala `0,1` para metros, `z` não usado; seção 2. |
| 8. Espaçamento nominal `Δ*` | `10 m`, `resample_m=10.0`; seção 2. |
| 9. Datas/cadência/completude | Regras congeladas de campos, parsing, ordenação e velocidade; seção 2. Cadência não presumida. |
| 10. Classes de pistas | Não há taxonomia morfológica existente; categorias administrativas excluídas; seção 3. |
| 11. Compatibilidade dos limites | Comparação com os parâmetros e a implementação v4; seção 2. |

O método é `filter_race_line` de `backend/scripts/track_geometry_free.py`, v4 do FONTE-2 (implementação congelada no commit `ffe0c59`), reusado sem alteração pelo pipeline PISTAS-EXPAND-1 (`backend/scripts/pistas_expand_1.py`, commit `6395354`). Para o lote de 2024, a chave da pista, sessão, piloto e stream são os registrados no manifest e nos pins do ciclo anterior. Os comprimentos oficiais são `race.course_length` da base local `backend/f1db.db`, temporada 2024; SHA-256 da base consultada: `4ab5fcab6f75a16f3548e226c8959d89f7af97805adfce165ec10fff909c845d`. Os comprimentos e deltas abaixo são os valores publicados no FONTE-2/manifest (L arredondado a 0,1 m; delta a 0,01 ponto percentual, exceto o valor exato LasVegas reportado no dossiê).

| Pista / chave exata | Sessão / piloto | Comprimento v4 (m) | Oficial f1db 2024 (m) | Δ publicado | Status anterior e uso conhecido |
|---|---:|---:|---:|---:|---|
| Monza / `Monza` | 9590 / 44 HAM | 5756,0 | 5793,0 | −0,64% | Demonstração e desenvolvimento/seleção do método FONTE-2; resultado público. |
| Hungaroring / `Hungaroring` | 9566 / 81 PIA | 4320,8 | 4381,0 | −1,37% | FAILED no gate anterior; publicado. |
| Silverstone / `Silverstone` | 9558 / 44 HAM | 5810,8 | 5891,0 | −1,36% | FAILED no gate anterior; publicado. |
| Montreal / `Montreal` | 9531 / 1 VER | 4295,9 | 4361,0 | −1,49% | FAILED no gate anterior; publicado. |
| Bahrain / `Bahrain` | 9472 / 11 PER | 5298,0 | 5412,0 | −2,11% | FAILED no gate anterior; publicado. |
| Mexico / `Mexico` | 9625 / 55 SAI | 4236,4 | 4304,0 | −1,57% | FAILED no gate anterior; publicado. |
| Zandvoort / `Zandvoort` | 9582 / 4 NOR | 4171,3 | 4259,0 | −2,06% | FAILED no gate anterior; publicado. |
| Suzuka / `Suzuka` | 9496 / 1 VER | 5761,6 | 5807,0 | −0,78% | COMPARADO; candidato e delta públicos, sem promoção. |
| LasVegas / `LasVegas` | 9644 / 63 RUS | 6139,1 | 6201,0 | −0,9982% | OK/congelada no ciclo anterior; delta público. |
| Miami / `Miami` | 9507 / 1 VER | 5330,5 | 5412,0 | −1,51% | FAILED no gate anterior; publicado. |

Essas dez linhas são **dez unidades por pista**, não dez resultados independentes de validação: todas tiveram deltas divulgados antes deste ciclo. Nenhuma pode ser holdout. Os nove resultados do PISTAS-EXPAND-1 foram avaliados pelo gate anterior; Monza participou do desenvolvimento do método. A seleção histórica não é amostra aleatória. O LOO com essas linhas é exclusivamente diagnóstico exploratório.

Os limiares de `3 × escala robusta`, mínimo de cinco pistas e os checks geométricos foram propostos no rascunho v0 por um redator que já conhecia resultados históricos. Essa escolha não é cega aos deltas. Por isso, mesmo folds LOO aprovados não seriam evidência independente; o único caminho ao Ramo 1 exigiria um holdout de pista nunca visto, que este inventário não contém.

| Pista | Stream de entrada | SHA-256 do stream | Amostras brutas |
|---|---|---|---:|
| Monza | `backend/experiments/fonte-2/location_9590_d44.json` | `19c61905ba527d9114aeb54dc38df33f587c244215898e6af9f87427e090fc45` | 30637 |
| Hungaroring | `backend/cache/openf1_pistas_expand_1/location_9566_81.json` | `16572644c117cd3085c1fb193de65363daf7446713514d4c82acf860c052cf03` | 35724 |
| Silverstone | `backend/cache/openf1_pistas_expand_1/location_9558_44.json` | `3a9ff9f8c5631557937de0dcb87abc19dbbe696c16c3f50fe2d235efcfd0806f` | 33899 |
| Montreal | `backend/cache/openf1_pistas_expand_1/location_9531_1.json` | `12e0ae6a3b36b19da28ab41bca0e6f0462e22b3ddda35f93ab9d8821e3f5bbf4` | 25940 |
| Bahrain | `backend/cache/openf1_pistas_expand_1/location_9472_11.json` | `03e70429ce0cfa6554388ee4d1acf50ed52e48039f26fbc3ba2657445c220092` | 35994 |
| Mexico | `backend/cache/openf1_pistas_expand_1/location_9625_55.json` | `a139c6f272b41510115479ec3a7055c593a1018e9a396b287afb9bbc86c01af4` | 36741 |
| Zandvoort | `backend/cache/openf1_pistas_expand_1/location_9582_4.json` | `d5a88777e21924c68254a00c952511826a91a2394ef1b3bfdc2fd79c99c77332` | 34781 |
| Suzuka | `backend/cache/openf1_pistas_expand_1/location_9496_1.json` | `7b3f00ecbbd7c54c44831b4e7699bb9b61b08fcba42fb2384bbd6a7c0280cb10` | 41801 |
| LasVegas | `backend/cache/openf1_pistas_expand_1/location_9644_63.json` | `782bd62606a964c33c4896ac34e70f95e01bf8263429acacf2bfa40fce120b48` | 33175 |
| Miami | `backend/cache/openf1_pistas_expand_1/location_9507_1.json` | `fcb7235f8154b544b727f12038922a42e75296d89f092026bceb265d3399bd89` | 34375 |

### Streams em cache ainda não processados pelo v4

Os seis arquivos abaixo já estão no cache local, não foram previamente processados pelo v4 e serão considerados **somente diagnósticos de piloto alternativo**. São quatro circuitos já expostos publicamente; não constituem quatro ou seis pistas independentes, não entram na calibração por pista e não suprem o holdout de S5. A ordem é fixa: chave de pista em ordem alfabética sensível a maiúsculas/minúsculas; dentro da chave, session_key e número do piloto em ordem numérica.

| Ordem | Pista | Arquivo de cache | Session / piloto | Amostras | SHA-256 |
|---:|---|---|---:|---:|---|
| 1 | Bahrain | `backend/cache/openf1_pistas_expand_1/location_9472_1.json` | 9472 / 1 | 35994 | `0acc7c3776dbffdc8636cca2b12c65467dcde7614f67df274287ac63261711c4` |
| 2 | Miami | `backend/cache/openf1_pistas_expand_1/location_9507_4.json` | 9507 / 4 | 34375 | `b230968a62fefb5bcc7158d3b3d908cebebfabe74989676226076e97cafdf57d` |
| 3 | Suzuka | `backend/cache/openf1_pistas_expand_1/location_9496_11.json` | 9496 / 11 | 41801 | `bf58f1a3b450c7bec4d994396096be62ee2c33a2a3a1b945c329f6a3280d2ff7` |
| 4 | Suzuka | `backend/cache/openf1_pistas_expand_1/location_9496_55.json` | 9496 / 55 | 41801 | `bb9947035b223763901839d723a67bbb87030687254b4c5eaea47465d7b5f7fc` |
| 5 | Zandvoort | `backend/cache/openf1_pistas_expand_1/location_9582_1.json` | 9582 / 1 | 34781 | `4b9798cf288e688f72987fffba6f64be108489c22c98a5a8d3e5b68545ad5721` |
| 6 | Zandvoort | `backend/cache/openf1_pistas_expand_1/location_9582_16.json` | 9582 / 16 | 34781 | `9829fc170b9012339b3a9fed6c15002432908b299a1dafcb88d4b2e1b827e50a` |

Os seis JSONs já foram verificados antes do congelamento apenas quanto à identidade do arquivo, parse, quantidade de amostras e presença/parse/uniquidade de `date`: os seis têm as quantidades da tabela, zero datas ausentes, inválidas ou duplicadas. Os streams alternativos já tinham sido inspecionados pelo ciclo anterior para contagens de saltos na seleção de pilotos; nenhum deles foi passado pelo filtro v4 e nenhum delta novo foi calculado nessa inspeção. Essa seleção prévia é mais um motivo para tratá-los apenas como diagnóstico não independente.

**Holdout:** não existe holdout independente disponível no inventário/cache deste prereg. Todos os dez circuitos com resultado histórico tiveram seu delta divulgado; os seis streams restantes pertencem a quatro desses circuitos. A regra mecânica para qualquer stream já presente no escopo é: considerar somente chaves exatas de circuito ausentes da tabela histórica, com stream completo em cache, sem delta v4 anterior divulgado e sem uso na escolha do método; ordenar as chaves por ordem lexical sensível a caixa e escolher a primeira. Com zero chaves elegíveis, registrar ausência de holdout e não procurar dados pela rede. Resultado desta checagem: zero elegíveis; S5 não pode ser satisfeito.

## 2. Resoluções vinculantes de S1–S3

**Alvo downstream (S1):** os mirrors podem ser resolvidos pelo loader e consumidos pela geometria do ambiente F1 (`backend/domain/track_resolution.py` e `backend/model_train/f1_env.py`). O PISTAS-EXPAND-1 congelou LasVegas, mas declarou o pool `--tracks` intocado; congelamento não equivale a adoção. Este ciclo só avalia plausibilidade da racing line v4 em relação ao comprimento oficial. Não certifica adequação para treino, avaliação, segurança ou fidelidade física.

**Unidade e escala (F3):** são duas verificações separadas. (a) Verificação de unidade: `x` e `y` de `/location` são decímetros e o fator do v4 é exatamente `unit_scale=0.1` para metros; `z` não é usado. A transformação está documentada em `backend/ANEXO_FONTE_2.md` e no v4. Ausência ou divergência de unidade/fator reprova. (b) Plausibilidade de escala: depois da conversão, `diagonal_bbox / comprimento_oficial` deve pertencer a `[0,05; 0,50]`. Esse é um teste de escala, não prova da unidade nem substitui sua verificação.

**Reamostragem:** `Δ* = 10 m`, conforme `resample_m=10.0` em `filter_race_line`. Os parâmetros v4 congelados são `min_step_m=0.5 m`, `cell_m=60 m`, `resample_m=10 m` e `unit_scale=0.1`.

**Gates estruturais congelados:** aplicam-se mecanicamente a cada geometria de pista antes de sua inclusão na calibração. Qualquer falha exclui a unidade do ajuste; não se corrige ou remove ponto manualmente.

| Gate | Regra congelada |
|---|---|
| Unidade | `x/y` em decímetros; conversão `×0,1` para metros; falha se contradito ou não verificável. `z` é irrelevante para este filtro. |
| Plausibilidade de escala | `diag(bbox_xy_m) / L_oficial_m ∈ [0,05; 0,50]`. |
| Dados de entrada | JSON parseável; ao menos 100 amostras brutas; `x`, `y` e `date` presentes; `x/y` finitos; `date` ISO parseável com fuso, único e crescente. Converter `date` a UTC, ordenar por `date` e exigir que essa ordem coincida com a ordenação lexical usada pelo v4. Falha se qualquer condição não for calculável. |
| Saltos temporais | Para amostras consecutivas ordenadas por `date`, distância em metros dividida pelo intervalo de tempo UTC positivo; falha se velocidade exceder `120 m/s`. Não se infere cadência nem se completa stream. O teto de 120 m/s é aceito e congelado como limite amplo de plausibilidade, não como velocidade máxima validada de F1. |
| Saída/continuidade | Saída v4 com ao menos 50 pontos; todas as coordenadas finitas; cada segmento entre pontos consecutivos mede `[5; 15] m`. Pontos repetidos consecutivos falham por comprimento de segmento abaixo de 5 m. |
| Fechamento | Segmento entre último e primeiro ponto mede `≤15 m`; também deve satisfazer o intervalo de continuidade `[5;15] m`. |
| Espaçamento | Todos os segmentos, inclusive o de fechamento, em `[5;15] m`; nenhuma exclusão de pontos para melhorar resultado. |
| Topologia | Um único ciclo, sem auto-interseção de segmentos não adjacentes; vértices compartilhados por segmentos adjacentes são permitidos. Para todo par não adjacente (incluindo o par primeiro/último como adjacente cíclico), calcular a distância euclidiana mínima entre os segmentos em float64; reprovar se a distância for `≤0,1 m` (`0,01 × Δ*`). Resultado não calculável reprova. |

A compatibilidade dos espaçamentos foi conferida com o código v4: ele fecha a linha, calcula `n=max(int(L/10),32)` e reamostra em `n` pontos uniformes com `endpoint=False`. Para o inventário de pistas com comprimentos de aproximadamente 4,2–7,0 km, o espaçamento nominal resultante fica na faixa congelada; a checagem final por pista continua obrigatória. Nenhuma alteração será feita ao filtro v4.

## 3. Resoluções vinculantes de S4–S6

**Unidade estatística:** circuito/pista (chave exata), nunca piloto, amostra, volta ou ponto. Para o LOO, usa-se no máximo um delta histórico por pista: as dez linhas da tabela da seção 1, sem excluir uma pista por seu status anterior. Só prosseguem as pistas cujos dados e gates estruturais passem. Os seis pilotos alternativos não são adicionados como linhas independentes nem substituem a medição histórica da pista.

**Fórmula e decisão estatística:** preservam-se a mediana, `MAD`, escala robusta `1,4826 × MAD`, intervalo bilateral mediana `± 3 × escala robusta`, limiar global e mínimo de cinco pistas de ajuste por fold propostos no v0; ficam aceitos e congelados. Os deltas históricos de entrada são os valores publicados na tabela, em pontos percentuais com precisão declarada. Não haverá ajuste por classe. A taxonomia `(a)/(b)/(c)` preexistente significa presença de mirror v2/v1 ou ausência de mirror no ciclo anterior; “primária/esticamento” é prioridade de aquisição. Nenhuma é classe morfológica de pista. Não existe taxonomia de forma de pista elegível para este ajuste.

**Dispersão nula (F4):** em cada fold, se `1,4826 × MAD ≤ 1e−12` ponto percentual, o fold é inválido. Fold inválido por amostra de ajuste menor que cinco, dispersão nula, dado ausente, gate estrutural reprovado ou cálculo não finito também é inválido. Se todos os folds forem inválidos, aplica-se explicitamente o Ramo 2 do S6: report-only. Se qualquer fold for inválido ou falhar, o critério conjunto LOO não passa.

**Holdout (F5):** aplica-se a seleção mecânica definida na seção 1 antes de revelar qualquer delta novo. Como não há circuito elegível inédito em cache, o holdout está ausente. Não há chamada de rede para procurar um. O LOO pode ser executado uma única vez como diagnóstico exploratório; não será chamado de validação independente.

**Árvore de decisão:** Ramo 1 requer, simultaneamente, inventário fechado, gates calculáveis, todos os folds válidos e aprovados, holdout independente aprovado e parâmetros intactos. A ausência conhecida de holdout impede o Ramo 1 neste ciclo, independentemente dos resultados LOO ou dos pilotos alternativos. Assim, a decisão pré-registrada deste ciclo é o Ramo 2: comprimento report-only, sem gate global proposto para uso futuro, sem re-pin e sem mudar o gate anterior. Os folds e os seis diagnósticos podem ser reportados para documentar o diagnóstico exploratório, mas não alteram essa decisão.

## 4. Execução e limites (F1, F2, D3/D4, S7)

1. Congelar este prereg por commit dedicado antes de qualquer extração v4 ou script de execução. O v0 permanece intocado.
2. Não fazer chamadas OpenF1, FastF1 ou outras chamadas de rede. Não usar funções com fallback de rede, como `openf1_track` em cache miss. Ler diretamente apenas os arquivos locais listados neste prereg e os streams históricos rastreados no inventário; cache ausente/incompleto = `FALTA_DADO(repo)` e abortar o item.
3. Aplicar os gates estruturais às dez geometrias históricas necessárias ao LOO, reprocessando apenas os streams correspondentes em cache, e executar em seguida os folds LOO uma única vez. Processar os seis streams alternativos na ordem congelada da tabela e aplicar os mesmos gates; somente se passarem, calcular e reportar seus comprimentos/deltas como descritores não independentes. Não agrupar pilotos como pistas.
4. O total histórico de nove deltas públicos permanece intacto e sem reclassificação. Os novos resultados não podem substituir, reclassificar ou promover pistas, nem entrar no loader, nos pools de treino/avaliação, nos checkpoints ou em métricas de modelo.
5. LasVegas já congelada permanece no estado anterior; ser carregável não implica inclusão em pool. Suzuka permanece candidata comparativa sem flip de default. Nenhum path frozen canônico pode ser escrito.
6. Nenhuma simulação de treino/corrida. Nenhuma edição em cache FastF1 ou pools 70–79/76–79. Nenhum dado cru OpenF1 será adicionado ao git.
7. Prioridade D4: os dez circuitos históricos entram no inventário/LOO e, por isso, recebem os checks necessários. Os seis streams alternativos são incluídos apenas porque F2 os autorizou e estão em cache; não se reprocessa nenhum outro stream por conveniência. A existência de cache, por si só, não justifica processamento.
8. Preservar os resultados anteriores sem post-hoc re-pin. Qualquer uso do limiar ou inclusão de pista em pool/gate exige decisão do dono e ciclo/prereg próprio (F6).

## 5. Formato obrigatório do PARE e auto-checagem

O PARE final deve registrar: commit deste prereg; hash e identidade de cada stream processado; ordem de extração; contagem de streams extraídos com sucesso/falha; resultado individual dos gates estruturais; LOO por pista e decisão mecânica; ausência de holdout; valores novos de pilotos alternativos apenas como diagnóstico não independente; conclusão report-only; zero rede, zero escrita em caminhos frozen e zero simulações; qualquer dado ausente ou divergência.

O PARE usará a expressão **“diagnóstico exploratório”** e explicitará que este ciclo não prova generalização para outras pistas, correspondência da racing line à linha central, qualidade de bordas/largura, segurança do piloto, desempenho do modelo ou adequação para treino/avaliação.

A suíte deve ser descrita exatamente como: **“349 testes, com 20 falhas bit a bit estáveis ('regressão estável conhecida') e 3 skips”**. Essa frase não equivale a “suíte verde” nem a “validação completa”. A comparação de execução deve ser serial contra o baseline serial `1a228b8`, itemizada pelas falhas conhecidas, conforme a solicitação do executor.

| Requisito | Resolução congelada |
|---|---|
| Inventário completo antes da calibração | Dez resultados históricos reais v4 listados; seis streams alternativos identificados e com hashes, deltas ainda não calculados. |
| Elegibilidade e histórico | Status e uso prévio explicitados; resultados históricos divulgados não são holdout. |
| Holdout independente | Seleção lexical por chave exata, definida antes de novos resultados; nenhum elegível; Ramo 2 esperado. |
| Unidade/fator de conversão | x/y em decímetros, `×0,1`; z não usado. |
| `Δ*` | 10 m, conforme `resample_m` v4. |
| Timestamps/cadência | `date` ISO único e parseável; velocidades derivadas de intervalos reais; teto `120 m/s`; sem completar dados. |
| Classes | Nenhuma classe morfológica existente; classes administrativas não entram no limiar. |
| Compatibilidade | Regras ligadas aos parâmetros e ao reamostrador v4; gates mecânicos e sem exceções manuais. |
| LOO e epsilon | Global; mediana ±3×escala robusta; mínimo de cinco ajustes; epsilon `1e−12` pp; fold/all-fold invalidade leva ao Ramo 2. |
| Separação de uso | Nenhuma promoção, pool, treino, avaliação, loader, checkpoint ou simulação. |
| Rotulagem da suíte | Texto obrigatório reproduzido acima; regressão estável conhecida ≠ validação completa. |

## 6. Proveniência desta resolução

As resoluções factuais vieram do repositório e dos caches locais identificados nas tabelas, incluindo `backend/ANEXO_FONTE_2.md`, `backend/ANEXO_PISTAS_EXPAND_1.md`, `backend/experiments/pistas-expand-1/manifest_pistas_expand_1.csv`, `backend/scripts/track_geometry_free.py`, `backend/scripts/pistas_expand_1.py` e `backend/f1db.db`. O uso de ai-memory foi consultado conforme `AGENTS.md`; a busca não forneceu fato relevante para este ciclo e não foi usada como fonte de dados. A nota `Memória consultada: não.` no v0 é preservada como proveniência do texto-base, não como declaração desta execução.
