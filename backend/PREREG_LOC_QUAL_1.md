# PREREG LOC-QUAL-1 — rascunho v0

**Status:** rascunho para revisão; não canônico e não autorizado para execução.  
**Memória consultada:** não.

## S0. Escopo e não objetivos

Este ciclo medirá, de forma offline, a qualidade temporal dos 16 streams `/location` já pinados no `PREREG_GATE_RE_DERIVE_1.md`: dez históricos e seis alternativos. O resultado será uma classificação por stream entre **utilizável como está**, **utilizável com pré-limpeza** e **só geometria**, acompanhada dos dados necessários para decisões posteriores do dono.

O ciclo também informará se os problemas temporais observados são isoláveis por uma pré-limpeza determinística e se há dados locais suficientes para fundamentar um futuro `GATE-RE-DERIVE-2` com holdout real. As decisões sobre implementar pré-limpeza e autorizar chamadas de rede pertencem ao dono, em ciclos próprios.

Este ciclo **não** cria nem altera gates de geometria ou de comprimento; não implementa pré-limpeza; não chama APIs; não muda geometria congelada, pools, loaders, checkpoints, bots ou física; não promove pistas; e não executa simulações. A classificação vale para a qualidade temporal destes streams e não certifica o uso de seus dados em treino ou avaliação.

O resultado anterior de velocidades implícitas acima de 120 m/s motivou este ciclo, mas não predetermina seus resultados. Nenhuma conclusão abaixo antecipa as medições LOC-QUAL-1.

## S1. Objeto e inventário

O objeto é exatamente o inventário congelado no ciclo anterior. Os caminhos, hashes e tamanhos abaixo foram conferidos em modo somente leitura; os hashes atuais correspondem aos pins. Os extremos de `date` são metadados de inventário, não uma análise de intervalos.

Os 16 arquivos têm o mesmo conjunto de chaves: `date`, `session_key`, `driver_number`, `meeting_key`, `x`, `y`, `z`. A ordem das chaves varia entre arquivos. Os valores de `x/y` são decímetros, com conversão para metros por fator `0,1`, conforme o ciclo anterior; `z` permanece sem uso na medição.

| Ordem | Pista | Tipo | Sessão / piloto | Caminho em cache | Tamanho | SHA-256 pinado | `date` mínimo → máximo (UTC) |
|---:|---|---|---:|---|---:|---|---|
| 1 | Monza | Histórico | 9590 / 44 | `backend/experiments/fonte-2/location_9590_d44.json` | 4.338.361 B | `19c61905ba527d9114aeb54dc38df33f587c244215898e6af9f87427e090fc45` | 2024-09-01T12:08:13.787000+00:00 → 2024-09-01T14:20:34.369000+00:00 |
| 2 | Hungaroring | Histórico | 9566 / 81 | `backend/cache/openf1_pistas_expand_1/location_9566_81.json` | 5.055.421 B | `16572644c117cd3085c1fb193de65363daf7446713514d4c82acf860c052cf03` | 2024-07-21T12:08:52.180000+00:00 → 2024-07-21T14:43:37.717000+00:00 |
| 3 | Silverstone | Histórico | 9558 / 44 | `backend/cache/openf1_pistas_expand_1/location_9558_44.json` | 4.793.907 B | `3a9ff9f8c5631557937de0dcb87abc19dbbe696c16c3f50fe2d235efcfd0806f` | 2024-07-07T13:04:59.390000+00:00 → 2024-07-07T15:31:29.972000+00:00 |
| 4 | Montreal | Histórico | 9531 / 1 | `backend/cache/openf1_pistas_expand_1/location_9531_1.json` | 3.644.352 B | `12e0ae6a3b36b19da28ab41bca0e6f0462e22b3ddda35f93ab9d8821e3f5bbf4` | 2024-06-09T17:59:04.556000+00:00 → 2024-06-09T19:51:14.457000+00:00 |
| 5 | Bahrain | Histórico | 9472 / 11 | `backend/cache/openf1_pistas_expand_1/location_9472_11.json` | 5.063.347 B | `03e70429ce0cfa6554388ee4d1acf50ed52e48039f26fbc3ba2657445c220092` | 2024-03-02T14:03:43.899000+00:00 → 2024-03-02T16:39:16.378000+00:00 |
| 6 | Mexico | Histórico | 9625 / 55 | `backend/cache/openf1_pistas_expand_1/location_9625_55.json` | 5.225.558 B | `a139c6f272b41510115479ec3a7055c593a1018e9a396b287afb9bbc86c01af4` | 2024-10-27T19:07:35.353000+00:00 → 2024-10-27T21:46:47.141000+00:00 |
| 7 | Zandvoort | Histórico | 9582 / 4 | `backend/cache/openf1_pistas_expand_1/location_9582_4.json` | 4.832.394 B | `d5a88777e21924c68254a00c952511826a91a2394ef1b3bfdc2fd79c99c77332` | 2024-08-25T12:07:23.654000+00:00 → 2024-08-25T14:38:22.496000+00:00 |
| 8 | Suzuka | Histórico | 9496 / 1 | `backend/cache/openf1_pistas_expand_1/location_9496_1.json` | 5.853.936 B | `7b3f00ecbbd7c54c44831b4e7699bb9b61b08fcba42fb2384bbd6a7c0280cb10` | 2024-04-07T04:01:02.928000+00:00 → 2024-04-07T07:02:23.056000+00:00 |
| 9 | LasVegas | Histórico | 9644 / 63 | `backend/cache/openf1_pistas_expand_1/location_9644_63.json` | 4.702.363 B | `782bd62606a964c33c4896ac34e70f95e01bf8263429acacf2bfa40fce120b48` | 2024-11-24T05:07:13.967000+00:00 → 2024-11-24T07:30:25.121000+00:00 |
| 10 | Miami | Histórico | 9507 / 1 | `backend/cache/openf1_pistas_expand_1/location_9507_1.json` | 4.795.031 B | `fcb7235f8154b544b727f12038922a42e75296d89f092026bceb265d3399bd89` | 2024-05-05T19:07:43.944000+00:00 → 2024-05-05T21:37:22.172000+00:00 |
| 11 | Bahrain | Alternativo | 9472 / 1 | `backend/cache/openf1_pistas_expand_1/location_9472_1.json` | 5.028.285 B | `0acc7c3776dbffdc8636cca2b12c65467dcde7614f67df274287ac63261711c4` | 2024-03-02T14:03:43.899000+00:00 → 2024-03-02T16:39:16.378000+00:00 |
| 12 | Miami | Alternativo | 9507 / 4 | `backend/cache/openf1_pistas_expand_1/location_9507_4.json` | 4.794.049 B | `b230968a62fefb5bcc7158d3b3d908cebebfabe74989676226076e97cafdf57d` | 2024-05-05T19:07:43.944000+00:00 → 2024-05-05T21:37:22.172000+00:00 |
| 13 | Suzuka | Alternativo | 9496 / 11 | `backend/cache/openf1_pistas_expand_1/location_9496_11.json` | 5.893.840 B | `bf58f1a3b450c7bec4d994396096be62ee2c33a2a3a1b945c329f6a3280d2ff7` | 2024-04-07T04:01:02.928000+00:00 → 2024-04-07T07:02:23.056000+00:00 |
| 14 | Suzuka | Alternativo | 9496 / 55 | `backend/cache/openf1_pistas_expand_1/location_9496_55.json` | 5.890.089 B | `bb9947035b223763901839d723a67bbb87030687254b4c5eaea47465d7b5f7fc` | 2024-04-07T04:01:02.928000+00:00 → 2024-04-07T07:02:23.056000+00:00 |
| 15 | Zandvoort | Alternativo | 9582 / 1 | `backend/cache/openf1_pistas_expand_1/location_9582_1.json` | 4.834.156 B | `4b9798cf288e688f72987fffba6f64be108489c22c98a5a8d3e5b68545ad5721` | 2024-08-25T12:07:23.654000+00:00 → 2024-08-25T14:38:22.496000+00:00 |
| 16 | Zandvoort | Alternativo | 9582 / 16 | `backend/cache/openf1_pistas_expand_1/location_9582_16.json` | 4.868.284 B | `9829fc170b9012339b3a9fed6c15002432908b299a1dafcb88d4b2e1b827e50a` | 2024-08-25T12:07:23.654000+00:00 → 2024-08-25T14:38:22.496000+00:00 |

A ausência de qualquer arquivo, divergência de hash ou incompatibilidade com os pins torna esse item `FALTA_DADO(repo)`. Não se substitui nem se adiciona stream durante o ciclo.

## S2. Definições operacionais e métricas

A unidade de análise é o stream completo, sem misturar pilotos como réplicas de pista. Cada execução reportará medidas da ordem original do JSON e, quando aplicável, da visualização pré-limpa definida em S3. A medição não modifica os arquivos de origem.

Para cada amostra, `date` será interpretado como instante com fuso explícito e convertido para UTC. Datas sem fuso, ausentes ou não parseáveis não serão presumidas locais. A diferença temporal entre amostras adjacentes na ordem original será `Δtᵢ = tᵢ − tᵢ₋₁`, em segundos. `Δt < 0` conta como inversão; `Δt = 0` conta como timestamp duplicado; somente `Δt > 0` entra em cadência e velocidade implícita.

A distribuição de intervalos positivos será reportada com contagem, mínimo, máximo e quantis P50, P90, P95 e P99. Quantis usarão nearest-rank: ordenar os `n` valores e escolher o índice `ceil(p × n) − 1`, com `p` entre 0 e 1. Os resultados serão apresentados sem arredondamento na decisão; arredondamento será apenas de exibição.

Um gap é um intervalo positivo que ultrapassa o limiar congelado em S3. Serão reportadas contagem e fração de pares acima dos limiares de sensibilidade fixos. Duplicatas serão contadas como número de grupos de timestamps repetidos e número de linhas excedentes; grupos com coordenadas `x/y` diferentes serão identificados separadamente. A ordenação será reportada como contagem de inversões na ordem original, sem reordenar antes dessa contagem.

Para cada par cronológico válido, a distância será `dᵢ = sqrt(((xᵢ − xᵢ₋₁)/10)² + ((yᵢ − yᵢ₋₁)/10)²)` metros. A velocidade implícita será `vᵢ = dᵢ / Δtᵢ`, definida somente para `Δtᵢ > 0`. A magnitude dos saltos será resumida com quantis da distância; sua frequência será reportada por faixas pré-fixadas em S3. `z` não participa do cálculo porque o método v4 e o ciclo anterior usam apenas `x/y`.

A cobertura observável será reportada como extremos UTC e duração entre o menor e o maior timestamp. Também será calculada a fração temporal válida dentro dessa janela: soma dos intervalos retidos e contíguos dividida pela duração observada. Isso não equivale à fração de uma sessão oficial. A cobertura percentual da sessão só poderá ser calculada se início e fim oficiais estiverem registrados em fonte local versionada; sem esses limites, o PARE deve escrever `FALTA_DADO(repo)` e não inferir a cobertura da sessão.

Campos ausentes ou malformados serão contados por stream e por tipo. Não se imputam coordenadas ou timestamps. Um registro sem `date`, `x` ou `y` utilizável impede classificar o stream como temporalmente utilizável; o evento será divulgado sem substituição manual.

## S3. Limiares e critérios reproduzíveis

Os valores desta seção são **PROPOSTOS** para revisão e fixação antes do congelamento. Nenhum será escolhido ou ajustado depois da medição.

- **Gap principal: `Δt > 3 s` (PROPOSTO).** A 120 m/s, três segundos permitem até 360 m sem observação; isso impede tratar o intervalo como continuidade local para um gate temporal. Serão reportadas, em paralelo, as bandas fixas `Δt > 1 s`, `> 3 s` e `> 10 s`. Elas são uma análise de sensibilidade pré-registrada, não garantias de cadência do OpenF1.
- **Velocidade implícita principal: `v > 120 m/s` (limite previamente congelado no GATE-RE-DERIVE-1).** Para sensibilidade serão reportadas também `v > 60 m/s` e `v > 90 m/s`. Essas bandas inferiores não substituem nem recalibram o limite anterior.
- **Magnitude de salto (PROPOSTO, descritivo):** contar distâncias `d > 10 m`, `> 30 m` e `> 100 m`, além dos quantis de `d`. São faixas report-only; 10 m corresponde à escala de reamostragem do v4 e as demais são múltiplos fixos dessa escala. Não são gates independentes.
- **Duplicata (PROPOSTO):** igualdade do instante UTC após parsing, sem tolerância adicional. Timestamps repetidos com `x/y` idênticos podem ser coalescidos na visualização pré-limpa; coordenadas conflitantes no mesmo instante não serão resolvidas por escolha manual.
- **Ordenação (PROPOSTO):** qualquer inversão na ordem original conta como quebra de monotonicidade. Na visualização pré-limpa, ordenar de forma estável por instante UTC e desempatar pelo índice original.
- **Cobertura de janela (PROPOSTO):** exigir ao menos 90% da duração observada em intervalos válidos após eventual segmentação. Esse limiar limita a 10% a perda temporal por cortes determinísticos; não declara que os 16 streams ou qualquer fração específica serão aprovados.
- **Cadência de origem:** `FALTA_DADO(repo)` para uma frequência nominal oficialmente declarada e versionada. Os limiares acima não presumem que o serviço garanta uma cadência específica.

Uma quebra por gap ou velocidade acima do limite será tratada como fronteira entre segmentos. Não se interpola nem se cria ligação entre os dois lados da quebra. A regra não remove seletivamente uma coordenada para reduzir uma velocidade.

## S4. Classificação mecânica em três baldes

Antes de classificar, verificar identidade do arquivo, correspondência ao hash pinado, campos obrigatórios, consistência de `session_key` e `driver_number` com o pin e parsing UTC. Falha de arquivo ou de hash é `FALTA_DADO(repo)`, não um quarto balde de qualidade.

Aplicar a seguinte precedência fixa:

1. **Utilizável como está:** todos os registros têm `date/x/y` utilizáveis; timestamps na ordem original são estritamente crescentes; não há duplicatas; todo par tem `0 < Δt ≤ 3 s` e `v ≤ 120 m/s`. A cobertura dentro da janela observada é integral. Essa classificação não afirma cobertura integral da sessão oficial.
2. **Utilizável com pré-limpeza:** não há campos obrigatórios irrecuperáveis nem conflito de coordenadas para o mesmo timestamp; a ordenação estável e a coalescência de duplicatas com `x/y` idênticos produzem uma sequência determinística; intervalos com `Δt > 3 s` ou `v > 120 m/s` são cortados sem interpolação; a cobertura temporal válida restante é pelo menos 90% da janela observada. O PARE deve descrever as operações que seriam necessárias, mas não as implementará.
3. **Só geometria:** qualquer campo obrigatório é irrecuperável, há timestamps iguais com `x/y` conflitantes, nenhum intervalo temporal válido permanece ou a cobertura após cortes fica abaixo de 90%. A classificação não atesta a qualidade geométrica; indica apenas que este ciclo não considera o stream apto ao uso temporal segundo as regras acima.

Se o limite oficial da sessão não estiver disponível, a classificação permanece restrita à janela observada e a cobertura percentual oficial recebe `FALTA_DADO(repo)`. Nenhum resultado será promovido de categoria com julgamento humano.

## S5. Árvore de decisão completa

**Ramo 1 — inventário íntegro e classificação calculável.** Se os 16 arquivos estiverem presentes, seus hashes coincidirem com os pins, o schema necessário estiver disponível e as regras de S2–S4 forem calculáveis, produzir o relatório por stream, agregados e classificação mecânica. Registrar separadamente qualquer `FALTA_DADO(repo)` de cobertura oficial da sessão ou de cadência nominal. O resultado fornece insumos ao dono; não decide limpeza, rede, gate novo ou promoção.

**Ramo 2 — inventário ou classificação insuficiente.** Se um arquivo estiver ausente, ilegível, divergente do pin ou sem campos necessários, registrar o item afetado como `FALTA_DADO(repo)`, explicar a causa e apresentar somente resultados parciais que sejam calculáveis sob as regras congeladas. Não substituir o arquivo, não buscar dados pela rede e não concluir que os streams não inspecionados têm a mesma qualidade. Se uma regra se mostrar ambígua, não ajustar a regra: marcar o resultado afetado como não classificável e levar a lacuna ao PARE.

Nenhum ramo autoriza alterar limiares após observar resultados.

## S6. Regras da casa aplicáveis

- Execução 100% offline e cache-only; teto de chamadas OpenF1 = **0**.
- Usar somente os 16 arquivos e hashes da S1; qualquer outro stream está fora de escopo.
- Nenhuma escrita nos caches de origem ou em paths frozen; nenhum dado cru novo será commitado.
- Nenhuma mudança em geometria, gates existentes, pools, loaders, checkpoints, bots, simulador ou suíte.
- Sem pré-limpeza implementada nesta fase; o tratamento será uma visualização determinística definido neste prereg.
- Ordem fixa: dez históricos na ordem de S1; depois alternativos em `Bahrain`, `Miami`, `Suzuka` (pilotos 11, 55), `Zandvoort` (pilotos 1, 16).
- Reprodutibilidade: registrar commit do instrumento e versões do runtime/dependências; executar a medição duas vezes com os mesmos hashes de entrada e comparar byte a byte os artefatos de saída. Saídas não incluirão timestamps de geração variáveis.
- Política de commits proposta: após revisão, congelar este prereg em commit dedicado; só então criar o instrumento em commit próprio; armazenar resultados em `backend/experiments/loc-qual-1/`; concluir com PARE em commit dedicado. Nenhuma dessas etapas ocorre nesta fase de redação.
- A suíte fica intocada. Rótulo de referência do projeto: **“349 testes, com 20 falhas bit a bit estáveis (‘regressão estável conhecida’) e 3 skips”**. Não chamar de “suíte verde” ou “validação completa”.

## S7. Formato do relatório esperado (PARE)

O PARE deverá conter:

1. Identidade deste prereg congelado, commit do instrumento e identidade/hash de cada entrada.
2. Inventário completo da S1 e confirmação do cache-only.
3. Métricas por stream: intervalos, bandas de gap, duplicatas, inversões, magnitude/frequência de saltos, velocidade implícita, extremos temporais e cobertura.
4. Comparação entre ordem original e visualização pré-limpa, sem substituir a evidência bruta.
5. Balde de cada stream ou `FALTA_DADO(repo)`, aplicado pela árvore da S4.
6. Tabelas agregadas separadas por histórico/alternativo, sem tratar pilotos alternativos como pistas independentes.
7. Sensibilidades com todos os limiares congelados, sem escolher um deles após observar os dados.
8. As duas decisões que cabem ao dono: se vale desenhar um ciclo para pré-limpeza do v4 e se há base para considerar um `GATE-RE-DERIVE-2` com rede e holdout. O PARE não as apresenta como tomadas.
9. Declaração de saída reproduzida byte a byte ou descrição fail-loud da divergência.
10. A expressão **“diagnóstico exploratório”** e uma seção explícita **“O que estes resultados não provam”**.

## S8. Limitações a divulgar

- Os 16 streams já foram expostos ao ciclo anterior; nenhum é holdout independente.
- A amostra não é aleatória: dez streams históricos e seis pilotos alternativos de quatro pistas já presentes.
- Um limiar congelado antes da medição melhora a reprodutibilidade, mas não o transforma em verdade de referência ou garantia oficial do OpenF1.
- A classificação vale apenas para estes arquivos e para a janela observada. Generalização a novos streams exigiria novo prereg e dados independentes.
- Sem limites oficiais de início/fim da sessão em fonte local versionada, não se pode afirmar uma cobertura percentual da sessão.
- A ausência de uma cadência nominal local impede tratar qualquer intervalo como garantia contratual do serviço.
- Cortar ligações problemáticas não reconstrói a trajetória ausente; não interpolar evita inventar pontos, mas pode reduzir cobertura.
- O resultado não prova qualidade geométrica, fidelidade à linha central, largura, segurança, desempenho de piloto ou adequação a treino/avaliação.

## S9. Auto-checagem

| Requisito | Cobertura no rascunho |
|---|---|
| Escopo fixo de 16 streams e cache-only | S0, S1 e S6; caminhos, tamanho, hashes, schema e extremos temporais inventariados |
| Métricas temporais definidas sem julgamento manual | S2 |
| Limiares fixos antes dos dados e sensibilidade pré-registrada | S3; valores ainda **PROPOSTOS** |
| Três baldes mecânicos e precedência | S4 |
| Dois ramos definidos antes dos resultados | S5 |
| Zero rede, zero sim, zero escrita frozen e nenhuma alteração nos bots | S0 e S6 |
| Ordem determinística e reprodução bit a bit | S6 e S7 |
| Relatório, decisões reservadas ao dono e limitações | S7 e S8 |
| Sem LOO/holdout neste ciclo | S0 e S8: nenhum será usado para calibrar ou validar |
| Rotulagem correta da suíte | S6 |

**`FALTA_DADO(repo)` pendente antes do congelamento:**

- Limites oficiais de início/fim dos session keys `9472`, `9496`, `9507`, `9531`, `9558`, `9566`, `9582`, `9590`, `9625` e `9644`, caso se exija cobertura percentual da sessão.
- Uma cadência nominal `/location` oficialmente declarada e versionada no repositório; os critérios propostos não a presumem.
- Versões exatas de runtime e dependências a registrar para a reprodução bit a bit no ciclo de execução.

**Valores `PROPOSTOS` pendentes de revisão e congelamento:** gaps de 1/3/10 s, limiar principal de 3 s, bandas de velocidade 60/90/120 m/s, faixas descritivas de salto 10/30/100 m, igualdade de timestamp em UTC sem tolerância adicional, cobertura mínima de 90% da janela observada e regras determinísticas de ordenação, coalescência e segmentação.

## Congelamento do PREREG LOC-QUAL-1

Status: **CONGELADO antes de qualquer medição**. O conteúdo integral das seções S0–S9 acima é a BASE IMUTÁVEL, preservada do arquivo v0. O adendo F1–F5 prevalece somente nos campos que resolve; não altera os demais termos nem seus valores. Os valores PROPOSTOS estão fixados: gaps de 1/3/10 s (principal 3 s); bandas de velocidade 60/90/120 m/s (principal 120 m/s); saltos de 10/30/100 m; duplicata por igualdade exata de timestamp UTC; cobertura mínima de 90%; ordenação, coalescência e segmentação conforme abaixo.

## Adendo obrigatório F1–F5

### F1. Precisão de pareamento

(i) **ORDEM ORIGINAL** — calcular Δt e velocidade entre pares consecutivos no arquivo; velocidade somente para Δt > 0 nessa mesma adjacência. (ii) **VISUALIZAÇÃO PRÉ-LIMPA** — ordenar de forma estável por UTC ascendente, desempate pelo índice original; calcular Δt e velocidade entre consecutivos dessa sequência. A classificação S4 usa as duas visões: condições de ordem original no balde 1; gaps, velocidade e cobertura na pré-limpa. As métricas da ordem original são evidência bruta reportada.

### F2. Campo obrigatório irrecuperável

Basta um registro com `date`, `x` ou `y` não utilizável para classificar o stream no balde 3 (só geometria), divulgando a contagem por tipo. A pré-limpeza permitida é fechada: ordenação estável, coalescência de duplicatas com `x/y` idênticos e corte de intervalos em quebras. Não inclui descarte de registros nem imputação.

### F3. Cobertura com identidade telescópica

A janela observada é `t_max − t_min` sobre registros com `date` utilizável, na sequência pré-limpa. A soma de todos os Δt positivos consecutivos dessa sequência é a própria janela observada. Cobertura válida = `1 − Σ(Δt dos pares cortados) / janela`. Duplicatas coalescidas contribuem zero. Esta é a definição mecânica única, sem julgamento.

### F4. Parsing por chave

Os JSONs são lidos por nome de chave, sem depender da ordem das chaves. Chaves extras são ignoradas. Ausência de qualquer uma das sete chaves (`date`, `session_key`, `driver_number`, `meeting_key`, `x`, `y`, `z`) torna o campo irrecuperável nos termos de F2.

### F5. Fronteiras de corte e resolução de FALTA_DADO

Cortar segmentos **somente** quando Δt > 3 s ou velocidade > 120 m/s. As bandas de sensibilidade — Δt > 1 s e > 10 s; velocidade > 60 m/s e > 90 m/s; saltos de 10/30/100 m — são exclusivamente reportadas e nunca cortam nem classificam. FALTA_DADO de limites de sessão e cadência só pode ser resolvido por fonte local versionada; rede proibida. O que não for encontrado permanece declarado no PARE.
