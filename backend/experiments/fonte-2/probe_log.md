# FONTE-2 — probe_log.md (APPEND-ONLY; teto 10; prereg 9ba3f8c §4)
| # | probe | endpoint | timestamp UTC | status | latência_ms | tamanho_bytes | sha256(payload) | nota |
|---|---|---|---|---|---|---|---|---|
| 1 | A | https://api.openf1.org/v1/sessions?country_name=Italy&year=2024&session_name=Race | 2026-10-21T23:25:33Z | 200 | 1083 | 694 | 6f29f8e64e77916b | country=Italy year=2024 |
| 2 | A | https://api.openf1.org/v1/location?session_key=9590&driver_number=44 | 2026-10-21T23:25:42Z | 200 | 9522 | 3909444 | 2f619e46a145f87b | session=9590 driver=44 |
| 1 | A | https://api.openf1.org/v1/sessions?country_name=Italy&year=2024&session_name=Race | 2026-10-21T23:31:19Z | 200 | 1287 | 694 | 6f29f8e64e77916b | country=Italy year=2024 |
| 2 | A | https://api.openf1.org/v1/location?session_key=9590&driver_number=44 | 2026-10-21T23:31:26Z | 200 | 7062 | 3909444 | 2f619e46a145f87b | session=9590 driver=44 |
| 1 | A | https://api.openf1.org/v1/location?session_key=9590&driver_number=44 | 2026-10-21T23:33:29Z | 200 | 8298 | 3909444 | 2f619e46a145f87b | session=9590 driver=44 |
| 6 | teste-t_f2_2 | https://api.openf1.org/v1/sessions?country_name=Pista-inexistente-xyz&year=2024&session_name=Race | 2026-10-21T23:30:00Z (aprox — na execução da suíte) | 200 (lista vazia) | ~1900 | ~90 | - | DISCLOSE: chamada NÃO-LOGADA no momento (feito pelo teste t_f2_2 antes do monkeypatch; país fictício; resposta vazia); teste corrigido p/ SEM rede (monkeypatch) — contada no teto: 6/10 |
