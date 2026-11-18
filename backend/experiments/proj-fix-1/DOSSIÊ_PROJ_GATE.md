# PROJ-FIX-5 — anatomia dos ponteiros e desenho do gate

**Estado:** report-only; nenhuma mudança de produção, comportamento ou observação.
**Ratificação:** aguardando o dono.
**Orçamento:** nenhuma simulação ou smoke; pools e pistas frozen intocados; suíte de referência 20F/352P/3S não reexecutada.

## 1. Freeze, fontes e reconciliação

A anatomia foi executada uma vez pelo instrumento v1.0, depois do freeze
corrigido. O primeiro preflight parou antes de publicar métricas porque o mapa
usa `t_s` e a primeira revisão do instrumento procurava `tick_s`; a errata
pré-análise e um novo selftest/freeze registraram a correção. Nenhum número de
anatomia foi emitido antes do freeze final.

| Artefato | SHA-256 |
|---|---|
| Preregistro | `5848ecdbaf79103bde079e6e1a8aa2f2f2e054d4711cdedc847b35027c7041a6` |
| Instrumento v1.0 corrigido | `2e89915a0dfa241f3d156c21cd2db677249aae23d0f11527a477003347695e9d` |
| Selftest sintético final | `5a6346a573260bde36e55564a924f313dcb2ca107a5fad0fcea63bdd8c929595` |
| Mapa de entrada | `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f` |
| Resumo de entrada | `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05` |
| JSON da anatomia | `703dc034313ff4f1f5a62cdbf6532d22be85833600feed09ab21d612286e49c6` |
| Tabelas Markdown | `0bfa71893a2234ac5043db1f2a33ceb263a86093295481cdc667579554d339ac` |
| Manifesto de saídas | `f2b7acdc45a43a6e1ae2b0d5d90b20b1572535059d004456f5f66d9c322d9b49` |

O commit `58ccb77` congelou o primeiro preregistro/instrumento/selftest;
`d042203` fixou seu manifesto. A errata pré-análise, o instrumento corrigido e
o novo selftest foram congelados em `c0dd552`; o manifesto corrigido foi
commitado em `4081f06`, antes da única execução com métricas. As duas fontes de
entrada conferiram com os SHAs esperados e com o mapa publicado.

Reconciliação do mapa: 112/112 linhas; C3=46, C5=66; 112/112 `authority=rejoin`;
112/112 `offtrack=1`; 112 checkpoints únicos por `(drv,tick_prev,tick)`. O
resumo congelado confirma headline ≥30 m = 45/45 C3. Qualquer divergência teria
parado a emissão das tabelas.

## 2. Anatomia dos saltos

Quantis usam interpolação linear; valores mantêm o sinal e “à frente” é
positivo. `delta_cum_dist_m` é o incremento físico do odômetro entre as duas
amostras do evento; não é o dXY público de PROJ-FIX-4.

| Classe | n | Métrica | p50 | p95 | máximo |
|---|---:|---|---:|---:|---:|
| C3 | 46 | `delta_s_wrapped_m` | 206.399878 | 1127.55096 | 1624.81963 |
| C3 | 46 | `delta_cum_dist_m` | 1.7593118 | 1.87045677 | 6.61269053 |
| C3 | 46 | `d_ns_raw` | 53 | 416.25 | 810 |
| C5 | 66 | `delta_s_wrapped_m` | 19.1098878 | 25.3394363 | 30.6863781 |
| C5 | 66 | `delta_cum_dist_m` | 1.77342097 | 3.30776035 | 6.15820822 |
| C5 | 66 | `d_ns_raw` | 5 | 6.75 | 7 |

Os valores de C3 para `delta_s_wrapped_m` e `d_ns_raw` mostram saltos largos no
ponteiro/índice enquanto o incremento de odômetro por par segue na escala de
metros baixos. Em C5, o p95 de Δs é 25.34 m, contra p95 de 3.31 m no incremento
de odômetro. Isso quantifica associação com o evento classificado; não prova
causa nem diz que os demais segmentos de Mônaco são proibidos.

### Cadência observável por carro

| Carro | Eventos | Eventos/volta | Intervalo médio (s) | Intervalo médio (ticks) |
|---|---:|---:|---:|---:|
| ALO | 14 | n/a | 38.6769231 | 386.769231 |
| GAS | 9 | n/a | 60.25 | 602.5 |
| HAM | 14 | n/a | 33.3692308 | 333.692308 |
| LEC | 15 | n/a | 40.0285714 | 400.285714 |
| NOR | 13 | n/a | 48.3166667 | 483.166667 |
| PER | 8 | n/a | 59.6857143 | 596.857143 |
| PIA | 9 | n/a | 66.125 | 661.25 |
| RUS | 9 | n/a | 67.975 | 679.75 |
| SAI | 11 | n/a | 36.96 | 369.6 |
| VER | 10 | n/a | 54.3555556 | 543.555556 |

“Intervalo médio” é a média entre timestamps de eventos consecutivos, ordenados
por carro. Eventos/volta fica n/a: o mapa não tem número da volta por evento,
e o resumo não fornece voltas completadas. Como `s` é a variável em investigação,
não o usamos para inventar voltas a partir dos próprios saltos. Para obter
eventos/volta será necessário um arquivo de eventos com odômetro/volta por
amostra, fora da allowlist deste ciclo.

## 3. Localização read-only no checkout atual

O ponteiro de progresso é calculado em mais de um caminho; o índice local de
waypoint usado pelo grip é outro estado e não deve ser confundido com `s`.

| Papel | Localização atual | O que faz |
|---|---|---|
| Projeção do runner neural | `backend/scripts/run_race_10_cars.py:446-453, 717-740` | Monta arcos dos segmentos; projeta XY em todos os segmentos, escolhe o `argmin` de distância e preenche `drv_s`/ponto projetado. |
| Rejoin | `backend/scripts/run_race_10_cars.py:544-547, 919-920, 1073-1105` | Off-track deriva da distância lateral; o modo padrão aponta para bearing até a projeção + 10 m; o modo perceptive pode ampliar esse avanço. A autoridade final registra `rejoin` em `1162`. |
| Consumidor do `s` no professor | `backend/model_train/reference_controller.py:389-395, 428-445` | Recebe `s` de `_project_on_path`, escolhe velocidade/lookahead e constrói o alvo de pure pursuit. |
| Projeção do ambiente | `backend/model_train/f1_env.py:607-627` | Mesmo tipo de busca global por segmento mais próximo; retorna distância lateral, `s`, índice e lateral assinada. |
| Observação edge/traffic | `backend/model_train/f1_env.py:439-449, 723-749, 904-948`; runner em `backend/scripts/run_race_10_cars.py:454-463, 659-695, 772-781` | Preview e raios usam geometria da pista; o runner escolhe a janela de raios pelo `drv_s`. As bordas são polilinhas paramétricas geradas com meia-largura, não uma medição/ratificação de borda física. |
| Hint de waypoint para grip | `backend/engine/simulation.py:477-482`; `backend/domain/track.py:243-281, 283-309` | Mantém `prev_waypoint_idx` e faz busca local na vizinhança para distância à linha e grip de superfície; busca global é caminho de retarget após largada/teleporte. É distinto da projeção global de `s`. |
| Contador de volta e odômetro | `backend/engine/simulation.py:575-626` | Soma deslocamento XY físico em `cum_dist_m` e completa volta ao cruzar múltiplos do comprimento da pista; lap time é atualizado nessa máquina. O gate proposto não altera essa cadeia. |
| Escrita diagnóstica | `backend/model_train/race_diagnostic.py:911-912, 938-946, 981-1005, 1281-1289` | Recalcula `s` pelo controlador/fallback e grava estado/autoridade/odômetro; quando XY está ativo, grava `body_x`, `body_y` e `ns_raw` por busca global no frozen. |
| Proxy de saltos publicado | `backend/scripts/fail_forensics_verdict.py:58-93` | Compara Δs circular com Δcum_dist; o erro absoluto seleciona eventos, enquanto segmentos/hops são derivados de `s` e geometria. Não é uma leitura direta do nearest segment físico. |

Os apontadores do R0 foram verificados, mas as linhas mudaram: `race_diagnostic.py:327-364`
hoje cobre o laço do professor/tráfego e anti-glue; `_project_signed` do
professor está em `301-313`. `reference_controller.py:448-453` hoje cobre alvo de
velocidade/comando longitudinal; a leitura atual de projeção é `394`, e o alvo
lookahead usa `s` em `432-445`. Portanto, R0 serviu como pista de leitura, não
como referência de linha atual.

## 4. Desenho de um fator para PROJ-GATE-1

### Gate do ponteiro com âncora pegadora

- **On-track:** aceitar avanço somente por segmentos/waypoints vizinhos e
  contínuos. O orçamento por atualização é a janela física `v·dt`; o limite de
  tolerância deve ser calibrado antes do braço ON, usando p50/p95 do
  `delta_cum_dist_m` e os percentis de `delta_s_wrapped_m`/`d_ns_raw` acima. Os
  percentis enormes de C3 medem o salto a conter; não devem virar autorização
  de avanço. Este mapa tem apenas eventos off-track, então o próximo ciclo
  também precisa confirmar a margem em amostras on-track antes de fixar ON.
- **Off-track:** congelar o ponteiro na última âncora on-track; readquirir só
  mediante evento explícito da autoridade de rejoin.
- **Exceções previstas:** permitir o lap-wrap benigno em `s=0` e a primeira
  aquisição de RAS sem permitir saltos por segmentos adjacentes.
- **Carve-outs:** contador de volta, lap time e `cum_dist` ficam inalterados. O
  corredor de readmissão vem da geometria frozen (waypoints e meia-largura
  paramétrica); não é uma afirmação de borda física. A superfície dirigível de
  Mônaco segue sem ratificação.

### Variantes para decisão do dono

- **V-A — runner/rotulação:** restringe telemetria escrita pelo runner e alvo de
  rejoin, sem alimentar o `s` ajustado à observação do agente nem mudar o modelo
  físico. É o candidato primário para destravar a cascata PROF-REPAIR e manter o
  perfil padrão v10-cego.
- **V-B — nível do ambiente:** muda comportamento e observação. Exige sinal
  NEURAL bit-off idêntico ao replay e gates mais fortes. Riscos explícitos:
  alteração da observação de tráfego de 46d e promessas FR0 ainda não fatiadas.

### Matriz de gates pinada

| Estado | Gate de PROJ-GATE-1 |
|---|---|
| OFF | Saída/sinal bit-idêntico ao replay/âncora. |
| ON — pares ≥10 m | p95 de Δs off-track tende a zero em Mônaco repetido. |
| ON — evento conhecido | ALO `(2130,2132)` deixa de ser salto do ponteiro. |
| Segurança/controle | Contatos e hesitações não pioram. |
| Geometria | Zero atalhos por trechos adjacentes, verificado explicitamente em Mônaco. |
| Regressão | Referência de suíte 20F/352P/3S permanece intacta. |

### Hipótese sobre o alvo de rejoin

Hipótese a medir, não achado causal: o alvo atual “bearing da projeção + 10 m”
pode herdar a contaminação quando o ponteiro corre à frente em off-track. No
braço ON, medir deslocamento lateral/erro de reentrada com probe `nhist`.

## 5. Veredicto reservado ao dono

Nenhuma variante foi escolhida. Ratificação pendente entre: (a) V-A com a matriz
acima; (b) V-B com gates bit-off; (c) ocultar apenas no instrumento/writer, sem
alterar comportamento; (d) mover o problema para outro ciclo. O WORKLOG e o
PROJECT_STATE apontam para este dossiê e registram “aguardando decisão do dono”.
