# `data/processed/f1.db`

Banco SQLite gerado por `scripts/run_pipeline.py <ano>`. Uma linha por ano/piloto/corrida, conforme tabela.

## `drivers`
Pilotos (sem corte por ano — reaproveitado entre temporadas).

| coluna | tipo | obs |
|---|---|---|
| driverId | INTEGER | PK, origem: Ergast |
| code | TEXT | sigla 3 letras (Ergast) |
| Abbreviation | TEXT | sigla 3 letras (telemetria) — igual a `code` |
| DriverNumber | INTEGER | número do carro |
| forename | TEXT | primeiro nome |
| surname | TEXT | sobrenome |

## `races`
| coluna | tipo | obs |
|---|---|---|
| raceId | INTEGER | PK, origem: Ergast |
| round | INTEGER | rodada da temporada |
| name | TEXT | nome da corrida (sem ano/patrocinador) |
| date | TEXT | formato `YYYY-MM-DD` |
| gp_id | INTEGER | FK opcional p/ `telemetry/GP.csv` — pode ser nulo (3 corridas de 2024 sem match) |
| gp_location | TEXT | nulo se `gp_id` nulo |
| gp_country | TEXT | nulo se `gp_id` nulo |
| year | INTEGER | temporada |

## `laps`
Volta por piloto por corrida. Fonte: `final_merged_{year}_data.csv`.

| coluna | tipo | obs |
|---|---|---|
| raceId | INTEGER | FK → `races.raceId` |
| driverId | INTEGER | FK → `drivers.driverId` |
| LapNumber | INTEGER | número da volta |
| LapTime | REAL | segundos |
| Sector1Time / Sector2Time / Sector3Time | REAL | segundos |
| Compound | TEXT | `SOFT` / `MEDIUM` / `HARD` / `INTERMEDIATE` / `WET` |
| TyreLife | INTEGER | voltas rodadas com o pneu atual — reset para `1` indica pit stop |
| FreshTyre | INTEGER (bool) | 1 = pneu novo no início do stint |
| Stint | INTEGER | número do stint |
| Team | TEXT | equipe |
| Position | INTEGER | posição na volta |
| AirTemp / TrackTemp | REAL | °C |
| Rainfall | INTEGER (bool) | 1 = chovendo |
| Humidity | REAL | % |
| WindSpeed | REAL | m/s |
| RoundNumber | INTEGER | round (fonte pneus, redundante com `races.round` via `raceId`) |
| year | INTEGER | temporada |

Índices: `raceId`, `driverId`.

## `safety_cars`
| coluna | tipo | obs |
|---|---|---|
| Race | TEXT | string original `"{ano} {nome}"` |
| Cause | TEXT | motivo do acionamento |
| Deployed | TEXT | volta/momento do acionamento |
| Retreated | TEXT | volta/momento da retirada |
| FullLaps | INTEGER | voltas completas sob safety car |
| raceId | INTEGER | FK → `races.raceId` |
| year | INTEGER | temporada |

Índice: `raceId`.

## `red_flags`
| coluna | tipo | obs |
|---|---|---|
| Race | TEXT | string original `"{ano} {nome}"` |
| Lap | INTEGER | volta da interrupção |
| Resumed | TEXT | se a corrida foi retomada |
| Incident | TEXT | descrição do incidente |
| Excluded | TEXT | piloto(s) envolvido(s) |
| raceId | INTEGER | FK → `races.raceId` |
| year | INTEGER | temporada |

Índice: `raceId`.

## `fatal_accidents_drivers`
Histórico geral, sem filtro de ano, sem FK para `races`/`drivers` (dado textual solto).

| coluna | tipo |
|---|---|
| Driver | TEXT |
| Age | INTEGER |
| Date Of Accident | TEXT |
| Event | TEXT |
| Car | TEXT |
| Session | TEXT |

## `fatal_accidents_marshalls`
Mesmo caráter da tabela acima.

| coluna | tipo |
|---|---|
| Name | TEXT |
| Age | INTEGER |
| Date Of Accident | TEXT |
| Event | TEXT |

---

**Notas gerais:**
- Pipeline idempotente: re-rodar para o mesmo ano faz `DELETE` + reinsere (exceto `drivers`, que é upsert por `driverId`).
- `gp_id`/`gp_location`/`gp_country` podem vir nulos — telemetria (`GP.csv`) está incompleta para 3 corridas de 2024.
- `fatal_accidents_*` não têm chave de junção com o resto do banco — consumir como referência solta, não via `JOIN`.
