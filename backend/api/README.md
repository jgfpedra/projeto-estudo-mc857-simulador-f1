# Contrato de corrida ao vivo

`POST /races` aceita `laps`, `track`, `year` (ou `season`), `num_drivers` (1 a 24) e `layout_id` opcional. Quando informado, o layout deve corresponder à temporada no catálogo F1DB. A fonte primária é a OpenF1: sessão, pilotos e amostras de uma volta histórica completa. A posição original das amostras é convertida empiricamente para metros e a linha de cronometragem é aproximada pelo início da volta; os pontos descrevem a trajetória de um carro, não as bordas oficiais da pista. A geometria passa por validações de extensão, fechamento e amostragem. Quando indisponível ou inválida, o adaptador local usa a pista congelada compatível. A origem de pilotos e pista é informada em `sources`; a lista local de emergência é de 2023. As fontes são injetáveis por `RaceDataProvider` e `ProviderChain`. A telemetria histórica `car_data` é acessível pelo adaptador OpenF1; o estado da corrida simulada sempre vem da engine.

`GET /races/{id}` retorna os metadados imutáveis e exatamente os waypoints/linha/largura usados pela engine. `layout_id` é o identificador F1DB associado à temporada quando há correspondência inequívoca; caso contrário é `null`. É uma referência histórica, não uma certificação de que a trajetória obtida coincide geometricamente com o desenho oficial. `geometry_sha256` identifica os pontos efetivamente usados. `GET /races/{id}/snapshot` retorna `starting`, `running`, `finished` ou `failed`, último tick e classificação final. O Redis mantém o evento `race_start`, o último tick, snapshot e resultado durante 24 horas. O WebSocket reenvia `race_start` e o último tick na reconexão.

Cada tick inclui `schema_version`, `leader_lap`, posição, `s_m` relativo à linha de chegada, `d_m` assinado em relação à geometria (positivo à direita), `progress_m`, orientação, velocidade, pneus, cor e classificação. O gap em segundos é calculado pela passagem anterior do líder na posição do seguidor, com interpolação; é `null` quando não existe histórico suficiente, quando o líder mudou ou quando o piloto está uma ou mais voltas atrás. `laps_behind` é calculado pela diferença de progresso sobre o comprimento do circuito.

Contatos crus do solver são agregados por par e por episódio, com os limiares de força/penetração do detector de colisão da branch do Caio. O tick traz apenas os novos contatos agregados para compatibilidade com o visualizador atual e publica um evento `collision` por novo episódio. `impact_force_n` é o pico da soma das forças em um subpasso; `penetration_m` é a maior penetração capturada. O evento não altera a física. O ajuste fino da linha de corrida segue restrito ao hash da geometria para o qual foi calibrado.

## Histórico de layouts e pistas antigas

`GET /circuits` lista os circuitos do catálogo; `GET /circuits/{id}/layouts` mostra cada layout F1DB, seus intervalos de anos com GPs registrados e a proveniência do catálogo. Os intervalos não comprovam a data exata de obras nem preenchem anos sem corrida. O snapshot incluído foi gerado em 2026-11-13 a partir do SQLite local cujo SHA-256 está registrado no arquivo; a versão exata da release F1DB de origem não foi registrada. O catálogo não se atualiza sozinho. Para atualizá-lo com um SQLite oficial do [F1DB](https://github.com/f1db/f1db) (CC BY 4.0), execute na raiz:

```bash
python backend/scripts/tracks/refresh_f1db_layouts.py --db-path caminho/para/f1db.db --f1db-release vVERSAO
```

Para conferir mudanças sem sobrescrever o snapshot, acrescente `--check`: o comando lista layouts adicionados, removidos ou com anos/extensão/curvas alterados e retorna código 1 quando encontra diferenças. O hash SHA-256 do SQLite e a release informada ficam no catálogo gerado. Reinicie a API para carregar o novo snapshot. O F1DB fornece metadados e imagens de layouts, não waypoints validados para a simulação. A OpenF1 histórica começa em 2023; para 2018–2022 tenta-se FastF1, que pode não ter uma geometria utilizável para toda sessão. Se não houver telemetria ou pista congelada, o provedor F1 Results Database tenta uma geometria aproximada extraída de SVG histórico para o circuito e ano. O catálogo cobre apenas mapas cuja conversão, largada e sentido passaram nas verificações automáticas; demais solicitações continuam indisponíveis.


## Pistas históricas aproximadas

A fonte `f1results_svg` funciona offline e é consultada após OpenF1, FastF1 e pistas locais. `sources.track_provenance` informa ano, GP, layout da fonte, comprimento, largura assumida, método de largada, sentido, licença e hash da base. O GET da corrida contém os mesmos waypoints usados pela engine. O grid segue a tangente do traçado e cada carro recebe sua orientação inicial. O limite `max_safe_grid_cars` evita posicionar carros fora da pista. Os mapas e suas limitações, atribuições, licenças e instruções de atualização estão em [`config/historical_tracks/README.md`](../config/historical_tracks/README.md).


### Consultas históricas de temporadas e pilotos

`GET /seasons` lista os anos do catálogo local. `GET /seasons/1973/drivers` lista os inscritos da temporada, incluindo a origem do último GP em que cada um aparece. Para circuitos e eventos de um ano, use `GET /circuits?season=1973` ou `GET /seasons/1973/events`; eventos sem associação segura com o F1DB são indicados separadamente. `geometry_available` indica disponibilidade de geometria SVG aproximada para aquele GP, não de telemetria.

`GET /seasons/1973/circuits/interlagos/drivers` retorna o grid real desse GP. Caso haja mais de um GP no mesmo circuito e ano, a consulta retorna 409; é possível informar `grand_prix` como parâmetro para selecionar o evento. Atualmente, a criação de corrida não oferece essa seleção e rejeita o caso ambíguo. A API usa OpenF1 primeiro quando disponível; no histórico usa o grid do F1 Results Database e geometria de outra fonte quando necessário. Solicitar mais carros que os registrados no grid histórico é um erro. Cores de equipe não disponíveis são cinza e siglas geradas são identificadas na resposta. Detalhes, cobertura e licenças: [`config/historical_tracks/README.md`](../config/historical_tracks/README.md).


### Via de boxes simplificada

`GET /races/{race_id}` inclui `track.pit_lane` com `waypoints` abertos no mesmo referencial da pista, `width_m`, `speed_limit_kmh` e `source`. Quando a fonte não fornece pontos válidos, o backend constrói uma via estimada junto à linha de chegada e informa `source: estimated`; ela não representa necessariamente a posição real dos boxes. A GUI PyBullet desenha essa via. Os clientes visuais precisam desenhá-la a partir do payload.

Para os bots, quando o desgaste ou o combustível exige uma parada, o carro segue a via fisicamente, respeita o limite simplificado e troca os pneus instantaneamente durante a passagem. O tick informa `pitting`, e o evento `pit_stop` ocorre na troca. A perda de tempo e posições resulta do percurso e da velocidade reduzida; não se soma a penalidade contábil antiga.


A configuração 2D também pode enviar `circuit: {id, layout_id}`, `year`, `grid` (IDs de pilotos em ordem), `weather`, `initial_tyre` e `weather_change`. `GET /seasons` e `GET /seasons/{year}/drivers` fornecem os pilotos usados nessa seleção; `GET /circuits` inclui os layouts no campo `circuits` preservando os metadados do catálogo. Os valores `light_rain`, `rain` e `heavy_rain` usam o estado molhado da engine, com intensidades iniciais diferentes. Quando `weather_change` não é enviado, o clima inicial permanece constante nessa configuração. As alterações de clima escolhidas são aproximadas pelos estados suportados pela engine. Estratégias de `stints` ainda não são aplicadas: a resposta de criação inclui um aviso para o frontend.

### Piloto do usuário

Na criação da corrida, envie `user_driver_id` com o ID de um piloto do `grid`, por exemplo `{"grid":["max-verstappen","lando-norris"],"user_driver_id":"lando-norris"}` junto aos demais campos do POST. O mesmo ID aparece no `GET /races/{race_id}`. O piloto indicado não agenda paradas automáticas por desgaste ou combustível; os outros pilotos continuam com a estratégia automática. Se o campo for omitido, todos os pilotos continuam automáticos. O piloto deve pertencer ao grid efetivo.

O front deve solicitar a parada pelo endpoint abaixo e pode cancelá-la antes da entrada. Após o pedido, o controlador dirige até os boxes e faz a troca. A configuração de stints ainda não agenda paradas.

### Solicitar boxes durante uma corrida

`POST /races/{race_id}/drivers/{driver_id}/pit-stop` com `{"tyre_compound":"medium"}` solicita a troca para `soft`, `medium`, `hard`, `intermediate` ou `wet` (maiúsculas também são aceitas). Resposta `202` indica que o pedido foi enfileirado para a thread da corrida, não que a troca já aconteceu. `404` indica corrida ou piloto inexistente; `409` indica corrida inativa, solicitação manual já pendente ou carro já entrando/nos boxes; `422` indica composto inválido. Uma solicitação manual substitui o composto de uma parada automática que ainda não começou. Se a corrida acabar antes de o pedido ser processado, a parada não acontece.

Ao processar o pedido, a engine publica `pit_requested` pelo mesmo WebSocket, com `race_id`, `driver_id`, `tyre_compound` em maiúsculas e `source: user`. O tick e o snapshot incluem `pit_request` por piloto com composto, origem e situação (`scheduled`, `approaching` ou `in_pit_lane`), ou `null` sem pedido; a entrada também é observada com `pitting: true`. A troca efetiva continua sendo informada pelo evento `pit_stop`. A via e a decisão de executar a troca continuam sob controle da engine. Na configuração atual de um único processo Uvicorn, o gerenciador mantém as engines ativas em memória; com múltiplos workers, seria necessário rotear o comando para o processo dono da corrida ou usar uma fila compartilhada.


`DELETE /races/{race_id}/drivers/{driver_id}/pit-stop` solicita o cancelamento sem corpo. A resposta `202` confirma que o comando foi enfileirado; o evento `pit_cancelled` confirma que a engine realmente o cancelou. Se a confirmação não for possível porque o carro cruzou a entrada entre o HTTP e o próximo tick, o evento é `pit_cancel_rejected` com `reason: already_in_pit_lane`, e a parada continua. `409` também é retornado quando já se sabe que o carro entrou, não há pedido pendente, a corrida está inativa ou o cancelamento já foi solicitado; `404` indica corrida ou piloto inexistente.

O cancelamento vale também para uma parada automática agendada. Depois de confirmado, a primeira avaliação automática de pit seguinte é ignorada para evitar reagendamento imediato; as avaliações posteriores voltam a funcionar normalmente. O carro pode estar em `approaching` com `pitting: true` e ainda pode cancelar: a entrada só é considerada cruzada quando o centro do carro passa o primeiro waypoint da via. O mesmo vale para uma via estimada; seu ponto de entrada também é aproximado.


### Temporada dos pilotos e variação da pista

A tela pode escolher um layout antes de escolher a temporada dos pilotos. Quando o pedido contém `grid` e `circuit.layout_id`, a API aceita uma temporada de pilotos diferente dos anos de uso daquele layout. Ela escolhe um ano de referência confirmado pelo F1DB para o **mesmo layout**, priorizando traçados locais congelados e anos com snapshot histórico; se necessário, tenta as fontes configuradas. Não mistura pilotos do ano de referência com o grid enviado. Por exemplo, um grid de 1968 pode correr no `austin-1` com geometria de referência de 2025.

A resposta de criação traz um aviso em `warnings`; `GET /races/{id}` mantém `season` como a temporada dos pilotos e informa `layout_reference.track_year`, `layout_reference.basis` e `sources.track_reference` quando a referência for diferente. A referência não declara que o GP existiu naquele ano dos pilotos. Sem grid explícito, a API continua exigindo que o layout corresponda à temporada, evitando inventar um grid histórico. Se nenhuma geometria do layout escolhido puder ser obtida, a criação é recusada com erro; outro layout não é substituído automaticamente.

Os anos em `layouts[].years` indicam os períodos com GPs registrados no catálogo, não uma variação por período contínuo. A ausência de um GP em 2020, por exemplo, pode dividir a lista de anos de um mesmo layout. As variações sem geometria disponível permanecem sinalizadas com `simulable: false`.

### Ritmo da simulação e calibração de Monza

A simulação ao vivo mantém passos físicos de 1/240 s e usa prazos baseados em relógio monotônico para compensar atrasos pontuais sem pular passos. Se o processamento permanecer mais lento que o tempo real, a corrida também ficará mais lenta; reduzir a quantidade de carros diminui a carga.

O controlador possui ajustes de ritmo para as duas geometrias de Monza 2024 testadas: a pista congelada e o snapshot OpenF1 da sessão 9590, piloto 1, volta 43. O ajuste exige hash e largura correspondentes; outras amostras OpenF1, variantes e geometrias continuam com os parâmetros gerais. A calibração é uma aproximação do simulador e não garante os tempos de pilotos reais. A geometria OpenF1 usada no teste offline está em `tests/fixtures/monza_openf1_2024.json`.
