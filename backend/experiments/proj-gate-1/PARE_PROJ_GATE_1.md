# PROJ-GATE-1 — PARE em g2 e g4

**Data:** 2026-10-23 (America/Sao_Paulo)
**Variante:** V-A ratificada, runner-only, opt-in `--proj-gate`, default OFF.
**Veredito:** PARE após a única R2. Sem promoção. A flag permanece desligada.

## Freeze e orçamento

- Preregistro: `ab0a0734ee41496d4ada9e0fe3f9abb353d6cf18`.
- Errata pré-R1 de amostragem: `cab9efaa2c9d54c472b117008729bb50fe0518c6`.
- Implementação, testes e audit: `f2bd1991947410f32be2929579d5ebbd11348a5a`.
- Evidências das duas corridas e do audit: `5c4bf9c32e6574412e510f08f2c0731eb6cc22c2`.
- Exatamente duas corridas formais foram executadas em série: R1 OFF e R2 ON.
  Não houve smoke, repetição, análise de classes ou alteração de código após o
  freeze da implementação.

## Gates

| Gate | Resultado | Evidência |
|---|---|---|
| g1 — R1 OFF byte-idêntica | PASS | CSV SHA-256 `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7`; events SHA-256 `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4`, ambos iguais aos pinos. |
| g2 — salto proxy R2 | **PARE** | 18.045 pares observados; `|Δs_wrapped − Δcum_dist|`: ≥10 m = 173 (limite 2), ≥20 m = 132, ≥30 m = 108 (limite 0). |
| g3 — reaquisição nearest-global | PASS | 392 transições off→on; 392 nearest-global, 0 não-nearest. |
| g4 — não-piora R2 | **PARE** | Fora 60,15% (limite 43,15%); 397 episódios (≤346); 144 janelas presas de 30 s (≤120); 28 hesitações (≤12). Contatos 22.084 (≤110.795) e completude 30.000 linhas / 3.000 ticks / 10 carros passaram. |
| g5 — suíte completa | NÃO EXECUTADO | PARE obrigatório em g2/g4; suíte não executada. A referência continua 20F/352P/3S e não foi revalidada neste ciclo. |

O CSV ON v3.4 tem 71 colunas, 30.000 linhas, 3.000 ticks amostrados e
sequência completa `0,2,...,5998` para cada um dos 10 carros. O sidecar tem
22.083 registros CSV; a métrica literal congelada de linhas menos um cabeçalho
é 22.084.

## Proveniência dos artefatos

Os hashes de disco e de `git show HEAD:<path>` foram conferidos após o commit
`5c4bf9c32e6574412e510f08f2c0731eb6cc22c2`; todos coincidem.

| Arquivo | SHA-256 |
|---|---|
| `1_repro_off_monaco_s0.csv` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| `1_repro_off_monaco_s0_events.csv` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| `1_repro_off_monaco_s0.log` | `64115b49ec1fe848c2b6effe33ef0108af05c109584adede261bd4e21794d1f7` |
| `2_on_monaco_s0.csv` | `b9ea18f28a26f2035fe61c9370eec7a70eb2bcaa342897d08a71baaf686a4edc` |
| `2_on_monaco_s0_events.csv` | `88fa98130b73b881750dab5f54a1fae02d07ce2a2162e1586332afec0660ac6a` |
| `2_on_monaco_s0.log` | `a421ae8b7fa3b6f13a9ce0d39f1f54ee29ce263728cc685d1d97f5d48a0d38e7` |
| `4_gate_audit.json` | `e7f088cba3a9a9372a2d17675e42aba0a9d0fb9ee5316660479402633eaaa3ed` |
| `4_gate_audit.log` | `33e8d86574a894b66274cc45a498e412630d65b94741c3513993eaa3edb1929e` |

## Encerramento

O audit sintético pré-corrida passou sem ler arquivos de corrida. A ajuda do CLI
e `git diff --check` passaram. g2/g4 acionam PARE; não houve suíte completa,
nova corrida, reanálise dos números públicos 112/50/45 ou promoção. Física,
ambiente, observações, clima, fitness, odômetro, writer, pools, caches e pista
frozen permaneceram fora da implementação.

Próxima decisão retorna ao dono. Uma continuação experimental exige novo
preregistro; nenhuma correção foi aplicada após observar R2.
