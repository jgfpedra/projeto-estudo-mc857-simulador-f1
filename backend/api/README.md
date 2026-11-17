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

Quando o desgaste ou o combustível exige uma parada, o carro segue a via fisicamente, respeita o limite simplificado e troca os pneus instantaneamente durante a passagem. O tick informa `pitting`, e o evento `pit_stop` ocorre na troca. A perda de tempo e posições resulta do percurso e da velocidade reduzida; não se soma a penalidade contábil antiga.
