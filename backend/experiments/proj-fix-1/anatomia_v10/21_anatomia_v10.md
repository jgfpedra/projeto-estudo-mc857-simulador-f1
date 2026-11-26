# PROJ-FIX-5 — anatomia v1.0

Report-only; fonte limitada ao mapa NIT-2 e ao resumo v1.2.

## Saltos por classe

Valores assinados; p50/p95 usam interpolação linear. Máximo é o maior valor com sinal.

| Classe | n | Métrica | p50 | p95 | máximo |
|---|---:|---|---:|---:|---:|
| C3 | 46 | `delta_s_wrapped_m` | 206.399878 | 1127.55096 | 1624.81963 |
| C3 | 46 | `delta_cum_dist_m` | 1.7593118 | 1.87045677 | 6.61269053 |
| C3 | 46 | `d_ns_raw` | 53 | 416.25 | 810 |
| C5 | 66 | `delta_s_wrapped_m` | 19.1098878 | 25.3394363 | 30.6863781 |
| C5 | 66 | `delta_cum_dist_m` | 1.77342097 | 3.30776035 | 6.15820822 |
| C5 | 66 | `d_ns_raw` | 5 | 6.75 | 7 |

## Eventos por carro

| Carro | Eventos | Eventos/volta | Intervalo médio (s) | Intervalo médio (ticks) |
|---|---:|---:|---:|---:|
| ALO | 14 | n/a* | 38.6769231 | 386.769231 |
| GAS | 9 | n/a* | 60.25 | 602.5 |
| HAM | 14 | n/a* | 33.3692308 | 333.692308 |
| LEC | 15 | n/a* | 40.0285714 | 400.285714 |
| NOR | 13 | n/a* | 48.3166667 | 483.166667 |
| PER | 8 | n/a* | 59.6857143 | 596.857143 |
| PIA | 9 | n/a* | 66.125 | 661.25 |
| RUS | 9 | n/a* | 67.975 | 679.75 |
| SAI | 11 | n/a* | 36.96 | 369.6 |
| VER | 10 | n/a* | 54.3555556 | 543.555556 |

* Eventos/volta indisponível: as fontes autorizadas não trazem volta por evento nem total de voltas; `s` não foi usado como substituto porque é o ponteiro em análise.

## Coerência

- Mapa/resumo: 112/112 linhas; C3=46; C5=66.
- Autoridade: {'rejoin': 112}; offtrack: {'1': 112}; checkpoints únicos por `(drv,tick_prev,tick)`: 112.
- Hash mapa: `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f`.
- Hash resumo: `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05`.

## Limite

A tabela não estima voltas, não lê replay e não mede dXY físico. As contagens públicas de PROJ-FIX-4 não foram reavaliadas além da reconciliação de integridade pinada.
