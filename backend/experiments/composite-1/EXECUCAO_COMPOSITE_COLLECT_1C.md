# EXECUCAO_COMPOSITE_COLLECT_1C

Data: 2026-10-26. Execução do freeze `fa73de6943b751514c64d19b1c265d27b0850fcb`, branch `feat/sanidade-produto`. Nenhuma corrida standalone ou treino foi iniciado; a única escrita de dados foi a conversão `--write` autorizada nesta fase.

## Fase A — g0 1G

Comando executado uma vez, em foreground, com `set -o pipefail` e `tee`:

```bash
set -o pipefail
.venv/bin/python -m pytest -q tests 2>&1 | tee experiments/composite-1/0_full_suite_collect_1g.log
```

Resultado: exit 1 esperado; 446 testes coletados, **20 failed / 423 passed / 3 skipped**, 99 warnings. A lista dos 20 IDs `FAILED` é idêntica à lista congelada no log 1E; zero falhas novas. SHA-256 de `0_full_suite_collect_1g.log`: `369874d3490956c53e651c9456590fb594121a2b552792f79c422a6b4a6d2357`.

Os logs anteriores disponíveis no worktree e o g0 1G:

| G0 | Resultado | SHA-256 do log |
| --- | --- | --- |
| 1B | 20F / 395P / 3S | `b6db756970b4865db6b4f90bd9795ff323ea32137af0c59f9405425e595d0971` |
| 1C | 20F / 397P / 3S | `eab4098a4f48b8d4463cae054ceb86afb61e75790f4b3564621ad3efedd7e5c6` |
| 1D | 20F / 400P / 3S | `5de11a470045d2f217de5d128fd97479ae9bba0da141edb5b5c10be14b407d99` |
| 1E | 20F / 407P / 3S | `4369364a5c7050fd345ce63d86a47cd161890b0879dd572149d7fa4754bb68b5` |
| 1G | 20F / 423P / 3S | `369874d3490956c53e651c9456590fb594121a2b552792f79c422a6b4a6d2357` |

O conjunto completo de testes inclui o teste canônico `TestHoldAt.test_hold_car_stays_at_s`, que inicia sua chamada interna de 30 ticks e falha depois ao ler a coluna `drv`; esse ID já consta na lista congelada. Nenhuma execução standalone de corrida foi feita.

## Fase B — conversão `--write`

Comando executado uma vez, em foreground:

```bash
set -o pipefail
.venv/bin/python scripts/composite_corpus.py convert-1f --case all --write 2>&1 | tee experiments/composite-1/0_convert_1f_write.log
```

Exit 0. O stdout registrou:

| Caso | Registros | Episódios | train / validation / test | launch | nose-to-tail | rejoin | hesitações |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| A | 30.000 | 10 | 24.000 / 3.000 / 3.000 | 3.000 | 178 | 16.088 | 42 |
| B | 30.000 | 10 | 24.000 / 3.000 / 3.000 | 3.000 | 273 | 23.946 | 44 |

Foram escritos 20 shards por episódio (10 por caso) e dois audits. Cada shard contém 3.000 registros. Os audits foram lidos duas vezes sem reescrita; os hashes coincidiram:

| Audit | SHA-256 em ambas as leituras |
| --- | --- |
| `A_audit.json` | `3631168758e5531b194352ff94004a9f90d8d6423fa7ace9a95a27d6d7586cf3` |
| `B_audit.json` | `e9066ab8bba40858c50b702b14135a9b277d990415fedf93a73c4136cc43c9e5` |

SHA-256 do log de conversão `0_convert_1f_write.log`: `6f6bee0a3611d18d6a1ac3ddacde87a32ade6c093e520ebbc037c659ca2fb180`.

### Regras e interpretação das famílias

* `launch_t_lt_60s`: conta amostras JOIN por carro com `t_s < 60`.
* `nose_to_tail_gt_60s`: em cada tick, escolhe o carro à frente com menor gap circular positivo até 40 m e diferença lateral absoluta até 2 m; exige `v_ego - v_líder >= -2 m/s` por cinco amostras JOIN consecutivas e `t_s > 60`. Conta amostras classificadas, não ultrapassagens.
* `monaco_rejoin`: para cada piloto, marca reentrada quando a amostra anterior JOIN estava off-track e a atual está on-track, ou quando `authority` contém `rejoin`. Cada amostra entre 0 e 10 s inclusive após uma reentrada recebe o rótulo; o contador é de amostras, não de episódios/eventos únicos. A implementação aplica essa regra aos dois casos, embora o nome do campo contenha “monaco”.
* `hesitations_post_reentry_le_10s`: amostras já marcadas na janela de reentrada com velocidade abaixo de 0,5 m/s.

O denominador JOIN é 30.000 amostras por caso; o dump lógico contém 60.000 linhas por caso. Assim, `monaco_rejoin` corresponde a 53,63% (A) e 79,82% (B) das amostras JOIN, ou 26,81% e 39,91% das linhas lógicas do dump. A formulação resumida “40–53% dos ticks” não usa um denominador comum e não é reproduzida por estes dados; ficam registrados os counts, a regra e ambos os denominadores para leitura crítica.

### Pareamento, splits e geometria

Em cada caso, os dez pilotos têm `paired=3000`, `total=6000`, `fraction=0.5`; no agregado, são 30.000/60.000. `split_rule` é `rank-80/10/10-per-run-v1`. Membership verificada pelos testes e registrada nos audits:

| Caso | train | validation | test |
| --- | --- | --- | --- |
| A | PIA, NOR, LEC, HAM, PER, RUS, GAS, ALO | SAI | VER |
| B | PIA, RUS, GAS, LEC, HAM, NOR, PER, ALO | VER | SAI |

`track_len_s`: Interlagos `4160.436950117386`; Monaco `3335.2345774147834`. Os geometry SHA-256 são, respectivamente, `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` e `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`.

## Proveniência e hashes

### Artefatos brutos usados

Os seis blobs A-ON final/B-ON (dump, main CSV e log) foram comparados disco↔Git e conferem com `7ef87c8f4e880b979c6dc8c77915a8f57356dd03`. O CSV principal A-OFF é byte-idêntico ao main CSV A-ON final. Os dois events CSVs adicionados no primeiro commit são A-ON final e B-ON.

| Artefato | SHA-256 |
| --- | --- |
| A-OFF `A_OFF.log` | `af7bcb67e09d2486fa295519b84fcf9f5776eee6d9de105819b4d373cbd472db` |
| A-OFF `A_OFF_main.csv` | `38607bf1154abf5c149cb4b33a85e3bb9fffd96b1eb5134eb7f5051673c70965` |
| A-OFF `A_OFF_main_events.csv` (mesmos bytes do events A-ON final) | `1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54` |
| A-ON final `A_ON_dump_interrupted3.jsonl.gz` | `904121eeabebecd2924c66f82b0cd493a7499d1875fbed7969d51f7016e2a2b5` |
| A-ON final `A_ON_main_interrupted3.csv` | `38607bf1154abf5c149cb4b33a85e3bb9fffd96b1eb5134eb7f5051673c70965` |
| A-ON final `A_ON_interrupted3.log` | `1837d35741c4df1737ea7807e435b52e459bc7ffbcc6e7e40ea8e59a5d6c3d52` |
| A-ON final `A_ON_main_events_interrupted3.csv` | `1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54` |
| B-ON `B_ON_dump.jsonl.gz` | `7e65405a0bb839f9f32609df285516c416f6adc45075d18a11e9a15cc6296bd3` |
| B-ON `B_ON_main.csv` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| B-ON `B_ON.log` | `f5d3c82dfb2bfbe5539317d51ca0015deea9710a54b7ca7db7ee17129846fd34` |
| B-ON `B_ON_main_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| Fonte Git para os dumps | `7ef87c8f4e880b979c6dc8c77915a8f57356dd03` |

Os dois dumps A-ON de tentativas anteriores foram preservados e não foram lidos pela conversão: `A_ON_dump_interrupted.jsonl.gz` SHA-256 `c2c708e69d54e1159f04ff18c04caf740565be6e54e595a415aeb16f96e682c4`; `A_ON_dump_interrupted2.jsonl.gz` SHA-256 `300753d458fe34fa7258ae9f47d4761ef6e950db46dd02b029f8ad52599f56b8`. Seus logs têm hashes `9a5d6eee5cc3d2379947e0c5cc3e2ccb33132d0c2ac3c86f02bc30a746d47c9e` e `205239d0e8ae3cd4457627ded5c8cf045f6e667d3ff6f217da24d02ca05913fb`.

Nota de inventário: a árvore de `7ef87c8` contém os dois dumps finais, dois main CSVs e dois logs A-ON/B-ON; o diretório local também contém o main A-OFF e dois dumps A-ON antigos preservados. A descrição abreviada “5 dumps + 4 mains” não corresponde a esses caminhos/à árvore consultada. Nenhum desses arquivos antigos entrou na conversão; as fontes efetivas são as duas linhas A-ON final e B-ON da tabela acima, mais o CSV A-OFF como referência de paridade.

### Hashes dos audits e proveniência interna

| Campo | A | B |
| --- | --- | --- |
| dump SHA-256 | `904121eeabebecd2924c66f82b0cd493a7499d1875fbed7969d51f7016e2a2b5` | `7e65405a0bb839f9f32609df285516c416f6adc45075d18a11e9a15cc6296bd3` |
| main CSV SHA-256 | `38607bf1154abf5c149cb4b33a85e3bb9fffd96b1eb5134eb7f5051673c70965` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| JOIN pair SHA-256 | `828d39e9226b958bd17ae1f3f8a387ab44a29d7b40f81ccc2146ef17055350af` | `45ceb2f4b6d2cd8422efac84a104aa75c11b414205d5db6d8e84151dbb22726d` |
| dataset SHA-256 | `5d29d1808695528c7a8bfc8e03cb335d95d5fab35ef16076b708dd3fca6b215b` | `2089d289c0f3b2adc01b0431c6af7bedb1a5522362101d4e9a39ab3ab3a593bc` |
| audit JSON SHA-256, duas leituras | `3631168758e5531b194352ff94004a9f90d8d6423fa7ace9a95a27d6d7586cf3` | `e9066ab8bba40858c50b702b14135a9b277d990415fedf93a73c4136cc43c9e5` |
| Geometry SHA-256 | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| arquivo de pista frozen (pin do runner) | `164876196eb12174` | `67ca11dc211c8c78` |

O forward solo obrigatório da Emenda 1F usou os mesmos artefatos frozen em ambos os casos: Keras SHA-256 `b75ab0e56d64457589a7f2a869c4d4140dafb6ad7c6a6a03560dbfe6c0e94b2e`; NPZ SHA-256 `bc5ea6e288a4f0c36eb9257a1ac5d478c6cf51549a9b492ac0b89b90951b93e3`.

### Shards (SHA-256)

| Caso / piloto | SHA-256 |
| --- | --- |
| A / ALO | `35ab7946039392711896c69bc02b7ea5ea376aaff52910c5d68432c3f622a871` |
| A / GAS | `0de1a87d27e19df3dcb8e39c4389d3d4cce79321e3833d03f60632857df200cf` |
| A / HAM | `df2976a7c8a39035c51e50836b19fe6677783d98f3606e88e331ccad515b824d` |
| A / LEC | `61a58dbf637ce6648356a3ad4604dd88977d753f314eb7a4bc929c2d0923600d` |
| A / NOR | `c6b73fcbf3366d85b1ebca5fabf079229a4ed0a0fb07702d00870ece8542941e` |
| A / PER | `996cede93a2c4671d6ebec8044c618e81fdf34acf631164f305663658eaa494a` |
| A / PIA | `940fa8ae536bae721d3062c00fc7c4ae8c08e18e3ac9621de00c52617497f884` |
| A / RUS | `78b486b2b21d9f28bcb345585e4b3e26e50963598383420484be677d2c5685c3` |
| A / SAI | `6a763dd1395f51e30badd3efc44b16d8e5298b090c99d23d25f42f42214a0cb2` |
| A / VER | `5ff4a203792eb4f47d94c403c83cb1a6fc94a6e0440b1ebff1b636a0915111c8` |
| A / audit | `3631168758e5531b194352ff94004a9f90d8d6423fa7ace9a95a27d6d7586cf3` |
| B / ALO | `9efb08af7faf83c106b42f1f5ac120483885976c72afe84375c8e6ca116c7514` |
| B / GAS | `9d0dff73bca279d54ce34b2132e7f625aa0885eed59f58cc75830aad5a11291c` |
| B / HAM | `377b60a9ac2a6eba063b9f279930853d6decdc0de53508651954e5bd79cfef8d` |
| B / LEC | `1601c1bd0857b386fa0f0590d3467f9e550612b26ed296f684b2301828e7ba54` |
| B / NOR | `36c3de4edac6717de68ff851d4e57f53963ec9caf08ee6e5831959435db967fa` |
| B / PER | `0573501dee120973b56a9e5206aee5df01d95eaa99d285ee04d142bf1fbb9338` |
| B / PIA | `adc8201b9c137b3cd9f6e46c5a5acd613a9d44370136b7a0f50d371a225bf800` |
| B / RUS | `ec88abb060886355f5d9a2278944e8fcea46b9c15ef8c7024bddcd48892a1152` |
| B / SAI | `4db7f236c8bc40d75dd479bb496b92bb0278c2b88ce8b6a89cd260462a4bef74` |
| B / VER | `dd3a1fbacb390af273b518d311a7e2ca46bbc523b41a1f01cf00fa6e6c2a180a` |
| B / audit | `e9066ab8bba40858c50b702b14135a9b277d990415fedf93a73c4136cc43c9e5` |

## Fase C — commits de proveniência

1. `55b7d053415441322094f1f1fd7c52004d9b0d94` — **Provenance COMPOSITE-COLLECT-1C addendum: events CSVs**. Contém somente `A_ON_main_events_interrupted3.csv` e `B_ON_main_events.csv`; hashes disco/blob conferem com `1f79529e…` e `b99007d0…`.
2. `33c75ce7cec7ef5dddb6ee86fcb474943e7849a4` — **Shards COMPOSITE-COLLECT-1C (converted from dumps fa73de6)**. Contém exatamente os 20 shards, dois audits e os logs g0/conversão; 24 arquivos. Nenhuma terceira commit foi criado.

## Disclosures e veredito

1. Registramos mea culpa pelos quatro casos em que testes sintéticos não representaram o formato de produção: 1B (tipos de domínio), 1D (header de metadata), 1E (ordem do grid) e 1H (população de episódios versus threshold).
2. A restrição genérica “inferência proibida” e o forward frozen obrigatório foram reconciliados na Emenda 1F: esta conversão executou somente o forward NumPy do solo v10 pinado para calcular o residual; não treinou nem avaliou o modelo Composite.
3. O sufixo `interrupted3` é housekeeping: o payload A-ON é válido e completo (dump com 60.000 linhas, main CSV com 30.000 amostras JOIN), está pinado em `7ef87c8` e foi convertido. A igualdade de hash A-OFF/A-ON confirma a paridade do main CSV.
4. Ambos os logs registram estado inicial DRY e `weather_transitions=[]` (zero transições); WET não ocorreu nesses dois runs. O comportamento fail-loud para estado fora do suporte continua intacto.
5. O A-OFF de referência registra 10/10 carros presos, 25,2% fora e 14 hesitações; fica como contexto de risco para o teste quantitativo do BASE-1.
6. Os counts `monaco_rejoin` são altos (16.088/23.946), mas repetem a janela pós-reentrada por amostra. A porcentagem “40–53%” não se sustenta com um único denominador: ver as duas normalizações na seção de famílias.

Todos os gates de g0, conversão, contagem, membership, hashes e leitura determinística dos audits passaram. Encaminhamento ao dono: ratificar COMPOSITE-BASE-1 com os critérios quantitativos próprios; nenhuma etapa BASE-1, promoção ou treinamento começou neste ciclo.

Freeze chain integral consultada: `229e6574bd0f421a5ca2b9443ce46ce9431e0165` → `debadf4f7143bdd2a8499b6d7b3ba08378792e26` → `2cbdeb48499003ec17ed50fc75d55822637ecde8` → `7ef87c8f4e880b979c6dc8c77915a8f57356dd03` → `b0998289bf60bba740a8515fb771246a17601834` → `678091a15b4ecdb9a30e8780a9649b4e748f2f7d` → `79b56809a81af231953e897ea3dbbaa1e9cf87bb` → `fa73de6943b751514c64d19b1c265d27b0850fcb`.
