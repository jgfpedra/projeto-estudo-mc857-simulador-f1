# FONTE-1 — probe_log.md (APPEND-ONLY; teto 30 chamadas; prereg 27ebff9 §3)
| # | probe | endpoint | timestamp UTC | status | latência_ms | tamanho_bytes | sha256(payload) | nota |
|---|---|---|---|---|---|---|---|---|
| 1 | A | https://api.jolpi.ca/ergast/f1/2024/circuits.json (via fastf1.ergast) | 2026-10-21T22:41:56Z | 200 | 1020 | 947 | - | 24 circuitos |
| 2 | A | https://api.jolpi.ca/ergast/f1/2024/races (via fastf1.ergast) | 2026-10-21T22:41:57Z | 200 | 709 | 1273 | - | 24 corridas |
| 3 | A | fastf1.ergast | 2026-10-21T22:41:58Z | ERR:TypeError | 0 | 0 | - | object of type 'ErgastMultiResponse' has no len() |
| 1 | A-retry | https://api.jolpi.ca/ergast/f1/2024/8/laps (via fastf1.ergast) | 2026-10-21T22:44:33Z | 200 | 7 | 70 | - | 30 linhas |
| 1 | B | https://api.jolpi.ca/ergast/f1/2024/circuits.json | 2026-10-21T22:46:49Z | 200 | 761 | 5322 | 6d5f19347a9a3422 | x-ratelimit-remaining=?, retry-after=?, ratelimit-reset=? |
| 2 | B | https://api.jolpi.ca/ergast/f1/2024/8/results.json | 2026-10-21T22:46:50Z | 200 | 819 | 11563 | 1cf2773e3f4efe1d | x-ratelimit-remaining=?, retry-after=?, ratelimit-reset=? |
| 3 | B | https://api.jolpi.ca/ergast/f1/2024/8/laps.json | 2026-10-21T22:46:51Z | 200 | 818 | 2331 | 8320548aa09d632f | x-ratelimit-remaining=?, retry-after=?, ratelimit-reset=? |
| 1 | C | https://api.openf1.org/v1/sessions?country_name=Monaco&year=2024 | 2026-10-21T22:46:57Z | 200 | 1160 | 1823 | 837572f3afba397c |  |
| 2 | C | https://api.openf1.org/v1/car_data?session_key=9516&driver_number=16 | 2026-10-21T22:47:05Z | 200 | 6759 | 2915244 | 85dd487f4064db40 | amostra histórica Monaco 2024 |
| 10 | C-manual | https://api.openf1.org/v1/car_data?session_key=9516&driver_number=16&max_duration=1s | 2026-10-21T22:47:44Z | 404 | ~300 | 130 | - | CHAMADA FORA DO SCRIPT (verificação manual de amostra pelo agente; param max_duration inválido → 404; DISCLOSE: conta no teto; total 10/30 |
