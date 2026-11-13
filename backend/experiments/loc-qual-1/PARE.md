# PARE — LOC-QUAL-1

**Status:** medição concluída sob prereg congelado; submetida à revisão do orquestrador. **Rótulo:** diagnóstico exploratório. Nenhuma promoção, alteração de gate, limpeza implementada, chamada de rede ou mudança de pool foi decidida neste ciclo.

## 1. Identidade, proveniência e reprodução

| Item | Identidade |
|---|---|
| Rascunho v0 verbatim | backend/PREREG_LOC_QUAL_1_v0.md — commit dbb28a1032d953af9248a589047daeb7131c04ca; SHA-256 7e0a0fc76270af935f05485f2153523fb1aad1436f43f68af1a9732be573323e |
| Prereg congelado | backend/PREREG_LOC_QUAL_1.md — commit 902097e33a34a7d158e33a3222a45e18307221df; SHA-256 a04cacc452f2231a5f105b10c21bd1086343903ebbb7471ca3d484609de8937e |
| Instrumento | backend/scripts/audit_loc_qual_1.py — commit cc3edbe17a2b20b2918143e9b136284cb766ef83; SHA-256 90e32baa187a23c9d9a3bc0a716bb89331382efba56f13483c07eb110b674eaf |
| Runtime e dependências | backend/experiments/loc-qual-1/runtime_manifest.json — CPython 3.12.12; somente biblioteca padrão; nenhuma dependência de terceiros |
| Artefatos da medição | commit 432a3fe; duas saídas em backend/experiments/loc-qual-1/run1/results.json e run2/results.json |

As duas saídas foram comparadas byte a byte; ambas têm SHA-256 **7590f90eea71eaf352fc9a4697805c0968c3547341bfa429d4cbe48df1a0210b**. A comparação passou. Não há timestamp de geração variável no JSON. As duas execuções usaram o mesmo prereg, instrumento, runtime e conjunto de entradas.

O instrumento conferiu tamanho e SHA-256 de cada entrada contra o pin da S1 antes de processá-la. **16/16 arquivos coincidiram** em tamanho e hash; os hashes completos esperados e observados estão nos resultados JSON e os pins completos, com paths, estão em S1 do prereg congelado. A tabela seguinte identifica cada entrada por chave e prefixo de hash.

| # | Pista / tipo | Sessão / piloto | Bytes | Prefixo SHA-256 | Pin conferido |
|---:|---|---:|---:|---|---|
| 1 | Monza / histórico | 9590 / 44 | 4.338.361 | 19c61905ba52 | sim |
| 2 | Hungaroring / histórico | 9566 / 81 | 5.055.421 | 16572644c117 | sim |
| 3 | Silverstone / histórico | 9558 / 44 | 4.793.907 | 3a9ff9f8c563 | sim |
| 4 | Montreal / histórico | 9531 / 1 | 3.644.352 | 12e0ae6a3b36 | sim |
| 5 | Bahrain / histórico | 9472 / 11 | 5.063.347 | 03e70429ce0c | sim |
| 6 | Mexico / histórico | 9625 / 55 | 5.225.558 | a139c6f272b4 | sim |
| 7 | Zandvoort / histórico | 9582 / 4 | 4.832.394 | d5a88777e219 | sim |
| 8 | Suzuka / histórico | 9496 / 1 | 5.853.936 | 7b3f00ecbbd7 | sim |
| 9 | LasVegas / histórico | 9644 / 63 | 4.702.363 | 782bd62606a9 | sim |
| 10 | Miami / histórico | 9507 / 1 | 4.795.031 | fcb7235f8154 | sim |
| 11 | Bahrain / alternativo | 9472 / 1 | 5.028.285 | 0acc7c3776db | sim |
| 12 | Miami / alternativo | 9507 / 4 | 4.794.049 | b230968a62fe | sim |
| 13 | Suzuka / alternativo | 9496 / 11 | 5.893.840 | bf58f1a3b450 | sim |
| 14 | Suzuka / alternativo | 9496 / 55 | 5.890.089 | bb9947035b22 | sim |
| 15 | Zandvoort / alternativo | 9582 / 1 | 4.834.156 | 4b9798cf288e | sim |
| 16 | Zandvoort / alternativo | 9582 / 16 | 4.868.284 | 9829fc170b90 | sim |

## 2. Regime e decisão da árvore

Execução 100% offline, cache-only e na ordem fixada em S1/S6: dez históricos, depois Bahrain, Miami, Suzuka 11, Suzuka 55, Zandvoort 1 e Zandvoort 16. **network_calls=0; simulations=0; frozen_path_writes=0; source_cache_writes=0.** O instrumento só leu as entradas pinadas e escreveu os resultados no diretório LOC-QUAL-1.

Todos os arquivos estavam presentes, legíveis, com hash e tamanho pinados; as sete chaves obrigatórias estavam presentes em todos os registros; não houve valor inválido em date/x/y nem inconsistência de session_key/driver_number. Assim, aplica-se o **Ramo 1 da S5**: relatório integral e classificação calculável. A falta de limites oficiais de sessão e de cadência nominal fica destacada separadamente; não impede a classificação na janela observada conforme S4. Nenhum parâmetro foi alterado após o congelamento.

## 3. Resultado por stream — ordem original e pré-limpa

Os extremos da janela UTC foram recalculados e estão abaixo. Δt é apresentado como mínimo/P50/P90/P95/P99/máximo em segundos, pela ordem original. As bandas de gaps mostram contagem e percentual dos intervalos positivos. A coluna de ordem/duplicatas significa inversões / grupos de timestamps duplicados / linhas excedentes / grupos com x/y conflitante.

Contagens por stream (registros / intervalos Δt positivos): Monza 30.637/30.636; Hungaroring 35.724/35.723; Silverstone 33.899/33.898; Montreal 25.940/25.939; Bahrain histórico 35.994/35.993; Mexico 36.741/36.740; Zandvoort histórico 34.781/34.780; Suzuka histórico 41.801/41.800; LasVegas 33.175/33.174; Miami histórico 34.375/34.374; Bahrain alternativo 35.994/35.993; Miami alternativo 34.375/34.374; Suzuka 11 41.801/41.800; Suzuka 55 41.801/41.800; Zandvoort 1 34.781/34.780; Zandvoort 16 34.781/34.780.

| # | Stream | Sessão/piloto | Janela UTC observada | Δt min/P50/P90/P95/P99/máx (s) | Gap >1 / >3 / >10 s | Inv./grupos/excedentes/conflitos | Cortes principais / cobertura válida | Classificação S4 |
|---:|---|---:|---|---|---|---|---|---|
| 1 | Monza (hist.) | 9590/44 | 2024-09-01 12:08:13.787 → 2024-09-01 14:20:34.369 | 0.020/0.240/0.380/0.420/0.480/1.800 | 40 (0.131%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 934 / 97.377% | utilizável com pré-limpeza |
| 2 | Hungaroring (hist.) | 9566/81 | 2024-07-21 12:08:52.180 → 2024-07-21 14:43:37.717 | 0.019/0.240/0.380/0.420/0.480/1.421 | 42 (0.118%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 226 / 99.547% | utilizável com pré-limpeza |
| 3 | Silverstone (hist.) | 9558/44 | 2024-07-07 13:04:59.390 → 2024-07-07 15:31:29.972 | 0.019/0.241/0.380/0.420/0.481/3.400 | 43 (0.127%) / 1 (0.003%) / 0 (0.000%) | 0/0/0/0 | 585 / 98.635% | utilizável com pré-limpeza |
| 4 | Montreal (hist.) | 9531/1 | 2024-06-09 17:59:04.556 → 2024-06-09 19:51:14.457 | 0.020/0.240/0.380/0.420/0.480/1.860 | 30 (0.116%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 291 / 99.181% | utilizável com pré-limpeza |
| 5 | Bahrain (hist.) | 9472/11 | 2024-03-02 14:03:43.899 → 2024-03-02 16:39:16.378 | 0.020/0.240/0.380/0.420/0.480/1.301 | 39 (0.108%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 361 / 99.236% | utilizável com pré-limpeza |
| 6 | Mexico (hist.) | 9625/55 | 2024-10-27 19:07:35.353 → 2024-10-27 21:46:47.141 | 0.019/0.240/0.380/0.420/0.481/3.380 | 43 (0.117%) / 1 (0.003%) / 0 (0.000%) | 0/0/0/0 | 474 / 98.883% | utilizável com pré-limpeza |
| 7 | Zandvoort (hist.) | 9582/4 | 2024-08-25 12:07:23.654 → 2024-08-25 14:38:22.496 | 0.020/0.240/0.380/0.420/0.480/1.360 | 47 (0.135%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 355 / 99.214% | utilizável com pré-limpeza |
| 8 | Suzuka (hist.) | 9496/1 | 2024-04-07 04:01:02.928 → 2024-04-07 07:02:23.056 | 0.019/0.240/0.381/0.420/0.481/3.100 | 57 (0.136%) / 1 (0.002%) / 0 (0.000%) | 0/0/0/0 | 454 / 99.150% | utilizável com pré-limpeza |
| 9 | LasVegas (hist.) | 9644/63 | 2024-11-24 05:07:13.967 → 2024-11-24 07:30:25.121 | 0.019/0.240/0.380/0.420/0.480/1.599 | 41 (0.124%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 902 / 97.674% | utilizável com pré-limpeza |
| 10 | Miami (hist.) | 9507/1 | 2024-05-05 19:07:43.944 → 2024-05-05 21:37:22.172 | 0.019/0.241/0.380/0.420/0.480/1.999 | 40 (0.116%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 628 / 98.526% | utilizável com pré-limpeza |
| 11 | Bahrain (alt.) | 9472/1 | 2024-03-02 14:03:43.899 → 2024-03-02 16:39:16.378 | 0.020/0.240/0.380/0.420/0.480/1.301 | 39 (0.108%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 349 / 99.272% | utilizável com pré-limpeza |
| 12 | Miami (alt.) | 9507/4 | 2024-05-05 19:07:43.944 → 2024-05-05 21:37:22.172 | 0.019/0.241/0.380/0.420/0.480/1.999 | 40 (0.116%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 591 / 98.603% | utilizável com pré-limpeza |
| 13 | Suzuka (alt.) | 9496/11 | 2024-04-07 04:01:02.928 → 2024-04-07 07:02:23.056 | 0.019/0.240/0.381/0.420/0.481/3.100 | 57 (0.136%) / 1 (0.002%) / 0 (0.000%) | 0/0/0/0 | 488 / 99.067% | utilizável com pré-limpeza |
| 14 | Suzuka (alt.) | 9496/55 | 2024-04-07 04:01:02.928 → 2024-04-07 07:02:23.056 | 0.019/0.240/0.381/0.420/0.481/3.100 | 57 (0.136%) / 1 (0.002%) / 0 (0.000%) | 0/0/0/0 | 453 / 99.134% | utilizável com pré-limpeza |
| 15 | Zandvoort (alt.) | 9582/1 | 2024-08-25 12:07:23.654 → 2024-08-25 14:38:22.496 | 0.020/0.240/0.380/0.420/0.480/1.360 | 47 (0.135%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 302 / 99.363% | utilizável com pré-limpeza |
| 16 | Zandvoort (alt.) | 9582/16 | 2024-08-25 12:07:23.654 → 2024-08-25 14:38:22.496 | 0.020/0.240/0.380/0.420/0.480/1.360 | 47 (0.135%) / 0 (0.000%) / 0 (0.000%) | 0/0/0/0 | 396 / 99.113% | utilizável com pré-limpeza |

Frações de gap usam como denominador os intervalos positivos do respectivo stream. A visualização pré-limpa ordenou por UTC e desempate por índice original; não houve inversões nem duplicatas, portanto ordenação e coalescência não alteraram estes streams. A coluna de cortes usa a regra principal congelada (Δt > 3 s ou velocidade > 120 m/s). A cobertura é exclusivamente da janela observada, calculada pela identidade telescópica de F3; não é cobertura da sessão oficial.

## 4. Saltos espaciais e velocidade implícita por stream

Quantis de distância em metros seguem P50/P90/P95/P99. Bandas mostram contagem e fração dos pares espaciais válidos. Como todos os registros tinham date/x/y utilizáveis, o denominador coincide com o número de intervalos positivos indicado na seção anterior.

| # | Stream | d P50/P90/P95/P99 (m) | d >10 / >30 / >100 m | v >60 / >90 / >120 m/s |
|---:|---|---|---|---|
| 1 | Monza (hist.) | 10.012/25.794/30.104/38.768 | 15327 (50.029%) / 1564 (5.105%) / 6 (0.020%) | 11407 (37.234%) / 3297 (10.762%) / 934 (3.049%) |
| 2 | Hungaroring (hist.) | 8.615/20.038/23.903/31.191 | 15480 (43.333%) / 473 (1.324%) / 3 (0.008%) | 8075 (22.604%) / 1308 (3.662%) / 226 (0.633%) |
| 3 | Silverstone (hist.) | 8.349/23.389/27.921/35.415 | 15279 (45.073%) / 1162 (3.428%) / 4 (0.012%) | 10919 (32.211%) / 2228 (6.573%) / 584 (1.723%) |
| 4 | Montreal (hist.) | 10.404/22.314/26.369/33.970 | 13559 (52.273%) / 600 (2.313%) / 1 (0.004%) | 7783 (30.005%) / 1365 (5.262%) / 291 (1.122%) |
| 5 | Bahrain (hist.) | 8.110/21.574/25.652/33.394 | 15519 (43.117%) / 768 (2.134%) / 1 (0.003%) | 9783 (27.180%) / 1769 (4.915%) / 361 (1.003%) |
| 6 | Mexico (hist.) | 6.964/20.938/25.951/35.228 | 13644 (37.137%) / 988 (2.689%) / 2 (0.005%) | 8129 (22.126%) / 2184 (5.944%) / 473 (1.287%) |
| 7 | Zandvoort (hist.) | 8.490/21.506/25.516/33.380 | 15390 (44.250%) / 705 (2.027%) / 2 (0.006%) | 9245 (26.581%) / 1720 (4.945%) / 355 (1.021%) |
| 8 | Suzuka (hist.) | 4.974/21.243/25.503/33.317 | 15908 (38.057%) / 872 (2.086%) / 3 (0.007%) | 10131 (24.237%) / 1940 (4.641%) / 453 (1.084%) |
| 9 | LasVegas (hist.) | 8.500/24.752/29.702/38.651 | 14980 (45.156%) / 1593 (4.802%) / 3 (0.009%) | 10948 (33.002%) / 3481 (10.493%) / 902 (2.719%) |
| 10 | Miami (hist.) | 8.026/23.363/28.014/36.161 | 14805 (43.070%) / 1227 (3.570%) / 2 (0.006%) | 10025 (29.164%) / 2250 (6.546%) / 628 (1.827%) |
| 11 | Bahrain (alt.) | 8.101/21.519/25.564/33.415 | 15645 (43.467%) / 755 (2.098%) / 6 (0.017%) | 9891 (27.480%) / 1773 (4.926%) / 349 (0.970%) |
| 12 | Miami (alt.) | 7.658/23.214/27.918/36.208 | 14426 (41.968%) / 1224 (3.561%) / 5 (0.015%) | 9850 (28.655%) / 2394 (6.965%) / 591 (1.719%) |
| 13 | Suzuka (alt.) | 4.880/21.246/25.730/33.746 | 15782 (37.756%) / 953 (2.280%) / 2 (0.005%) | 9880 (23.636%) / 2034 (4.866%) / 487 (1.165%) |
| 14 | Suzuka (alt.) | 4.880/21.293/25.668/33.701 | 15801 (37.801%) / 917 (2.194%) / 3 (0.007%) | 10126 (24.225%) / 1951 (4.667%) / 452 (1.081%) |
| 15 | Zandvoort (alt.) | 8.782/21.233/25.294/33.093 | 15718 (45.193%) / 680 (1.955%) / 2 (0.006%) | 9373 (26.949%) / 1673 (4.810%) / 302 (0.868%) |
| 16 | Zandvoort (alt.) | 8.631/21.513/25.608/33.610 | 15466 (44.468%) / 782 (2.248%) / 2 (0.006%) | 9218 (26.504%) / 1810 (5.204%) / 396 (1.139%) |

## 5. Agregados descritivos por grupo

Agregados de distribuição juntam observações do grupo e são descritivos; os seis pilotos alternativos não são tratados como seis pistas independentes. Percentuais usam o denominador indicado em cada banda.

| Medida | 10 históricos | 6 alternativos |
|---|---:|---:|
| Classificação S4 | 0 como está; 10 com pré-limpeza; 0 só geometria | 0 como está; 6 com pré-limpeza; 0 só geometria |
| Registros / intervalos positivos | 343.067 / 343.057 | 223.533 / 223.527 |
| Δt min; P50/P90/P95/P99; máximo (s) | 0.019; 0.240/0.380/0.420/0.480; 3.400 | 0.019; 0.240/0.380/0.420/0.480; 3.100 |
| Inversões; grupos duplicados; excedentes; conflitos | 0; 0; 0; 0 | 0; 0; 0; 0 |
| Gaps >1 / >3 / >10 s | 422/343057 (0.123%); 3/343057 (0.001%); 0 | 287/223527 (0.128%); 2/223527 (0.001%); 0 |
| Distância P50/P90/P95/P99 (m) | 8.276/22.472/26.926/35.346 | 7.443/21.630/25.938/34.100 |
| Saltos >10 / >30 / >100 m | 149.891 (43.693%); 9.952 (2.901%); 27 (0.008%) | 92.838 (41.533%); 5.311 (2.376%); 20 (0.009%) |
| Velocidade >60 / >90 / >120 m/s | 96.445 (28.113%); 21.542 (6.279%); 5.207 (1.518%) | 58.338 (26.099%); 11.635 (5.205%); 2.577 (1.153%) |
| Cortes pela regra principal | 5.210 intervalos; 1.099.386 s cortados | 2.579 intervalos; 527.025 s cortados |
| Janela observada somada | 89.139.221 s | 58.188.647 s |
| Cobertura válida ponderada pela duração observada | 98.767% | 99.094% |

A cobertura individual após cortes variou de **97.377% a 99.547%** nos históricos e de **98.603% a 99.363%** nos alternativos. Todas superam o mínimo congelado de 90% da janela observada. A cadência observada tem mediana agregada de 0,240 s e P95 de 0,420 s, mas isso não estabelece uma cadência nominal ou garantia de serviço.

## 6. Campos, limites de sessão e cadência

As 16 entradas tinham as sete chaves exigidas. Contagens agregadas de chave ausente: 0 para date, session_key, driver_number, meeting_key, x, y e z. Valores date/x/y não utilizáveis: 0. Registros irrecuperáveis: 0. Inconsistências de session_key/driver_number com o pin: 0.

**Limites oficiais de sessão — FALTA_DADO(repo).** Os keys 9472, 9496, 9507, 9531, 9558, 9566, 9582, 9590, 9625 e 9644 aparecem nas fontes versionadas como identificadores e estão associados a pistas/pilotos, mas não foi encontrada fonte versionada com os horários oficiais de início e fim. A busca de texto consultou arquivos versionados de documentação e código, excluindo backend/cache/**, backend/experiments/**, testes e dados. A leitura somente de esquema do banco versionado data/processed/f1.db encontrou races.Date, sem colunas de limites de sessão. Por isso a cobertura oficial da sessão permanece FALTA_DADO(repo) nos 16 streams; somente a janela observada é informada.

**Cadência nominal /location — FALTA_DADO(repo).** Não foi encontrada declaração local versionada de uma taxa nominal. O prereg anterior registra “Cadência não presumida”; as taxas observadas acima são medidas destes arquivos, não uma promessa da API.

O terceiro FALTA_DADO do rascunho foi resolvido: runtime e dependências estão fixados no manifesto commitado (CPython 3.12.12, biblioteca padrão, sem dependências externas).

## 7. Desvio de busca prévio e rastreabilidade dos limiares

Na etapa anterior de inventário ocorreu uma busca textual ampla que exibiu conteúdo bruto de JSON em cache. **Não foi calculada estatística LOC-QUAL-1 nesse desvio.** A avaliação do dono/orquestrador foi de que o desvio era imaterial: nenhum limiar PROPOSTO tem rastreabilidade às linhas exibidas; as justificativas são de princípio e foram congeladas antes desta medição (120 m/s herdado do GATE-RE-DERIVE-1; 3 s = 360 m a 120 m/s; 10/30/100 m como escala do v4 e múltiplos fixos; 60/90 m/s como frações fixas de 120; 90% como teto de 10% de perda temporal). A medição atual seguiu os limiares congelados sem ajuste nem re-pin.

## 8. Limitações e o que estes resultados não provam

- Os 16 streams já eram conhecidos e foram expostos no ciclo anterior; nenhum constitui holdout independente.
- A amostra não é aleatória: são dez streams históricos e seis pilotos alternativos de quatro pistas. Agregados são descritivos.
- Os resultados caracterizam estes arquivos e suas janelas observadas. Não estabelecem generalização a outros pilotos, sessões ou pistas.
- Sem horários oficiais locais, não há percentual de cobertura da sessão; sem cadência nominal versionada, a distribuição observada não define garantia do OpenF1.
- Cortar pares por Δt >3 s ou v >120 m/s cria intervalos não conectados; não reconstrói a trajetória ausente.
- A classificação é temporal. Ela não prova qualidade da geometria, linha central, bordas ou largura, segurança do piloto, desempenho do modelo, nem adequação a treino ou avaliação.
- Não houve alteração nos gates, pools, loaders, pistas congeladas, bots ou simulador. Nenhuma chamada de rede ou simulação foi executada.
- A suíte não foi executada neste ciclo. Sua referência permanece: **349 testes, com 20 falhas bit a bit estáveis ('regressão estável conhecida') e 3 skips**. Isso não é “suíte verde” nem “validação completa”.

## 9. Insumos às decisões reservadas ao dono

1. **Pré-limpeza do v4:** todos os streams entram no balde “utilizável com pré-limpeza” por precisarem cortar pares acima dos limites primários; a perda medida da janela observada ficou entre 0,453% e 2,623% por stream. O relatório não implementa nem recomenda, por si só, a mudança.
2. **GATE-RE-DERIVE-2 e rede:** estes dados não oferecem holdout independente, e permanecem faltando os limites oficiais de sessão e a cadência nominal. Nenhuma chamada foi autorizada ou feita neste ciclo. Um novo ciclo e a decisão sobre rede/holdout pertencem ao dono.

## 10. Memória e encaminhamento

O v0 preserva a declaração histórica “Memória consultada: não”, verdadeira na fase em que foi redigido. Nesta execução consultei ai-memory em modo somente leitura para verificar contexto/handoff, conforme o AGENTS.md fornecido nesta tarefa; não usei memória como fonte de entradas, métricas ou parâmetros. O v0 foi recuperado literalmente do histórico da conversa e sua igualdade foi verificada por SHA-256.

Este PARE encerra a execução do executor e aguarda revisão do orquestrador antes de qualquer ratificação ou ciclo subsequente.

