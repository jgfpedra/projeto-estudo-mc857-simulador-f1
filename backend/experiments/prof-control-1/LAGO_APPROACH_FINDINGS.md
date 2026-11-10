# LAGO APPROACH FINDINGS — aproximação e entrada da C01 (Descida do Lago)

**Data:** 2026-11-07 · **Método:** report-only sobre a telemetria existente (zero corrida nova) · **Instrumento:** `scripts/prof_lago_approach_audit.py` (determinístico, `cmp=0` ×2) · **Fonte:** `REF_INTERLAGOS_600S.csv` (SHA `c00391ab…`) · **Pista:** `164876196eb12174`.

## Passe por passe (5 cruzamentos de linha; janela C01 s ∈ [0, 80] m)

| passe | t_s do lat_max | lat_max (m) | margem (m) | saiu | tyre_life | tyre_grip | v_min ápice (km/h) | demanda/capacidade |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | 34.0 | 5.9399 | +0.0601 | não | 100.0% | 0.842 | 52.679 | 0.394 |
| 2 | 172.6 | 6.0495 | -0.0495 | SIM | 93.07% | 0.833 | 46.495 | 0.239 |
| 3 | 311.6 | 6.0685 | -0.0685 | SIM | 86.13% | 0.825 | 52.462 | 0.229 |
| 4 | 452.2 | 6.2426 | -0.2426 | SIM | 79.2% | 0.816 | 33.938 | 0.259 |
| 5 | 594.2 | 6.2613 | -0.2613 | SIM | 72.26% | 0.807 | 34.014 | 0.279 |

**Correlação tyre_grip ↔ lat_max:** Pearson r = **-0.9686** em 5 passes; deltas de lat_max por passe (m): [0.1096, 0.019, 0.1741, 0.0187].
Passes com saída: 4/5.

## Aproximação (reta principal, últimos 150 m)

| passe | v_max (km/h) | início frenagem s (m) | dist até linha (m) | v na frenagem (km/h) | lat final (m) |
|---|---:|---:|---:|---:|---:|
| 1 | 284.282 | 4013.292 | 147.145 | 284.282 | 0.0054 |
| 2 | 282.795 | 4014.447 | 145.99 | 282.795 | 0.0386 |
| 3 | 277.877 | 4018.048 | 142.389 | 277.877 | 0.1398 |
| 4 | 286.143 | 4011.797 | 148.64 | 286.143 | 0.0426 |
| 5 | 266.647 | 4024.968 | 135.468 | 266.647 | 0.0918 |

## Leitura (report-only; veredito é do Dono)

- A aproximação é consistente entre passes (mesma frenagem, mesma entrada centralizada); a variável que separa o passe limpo das saídas é o **tyre_grip degradado** (0,842 → 0,807) sobre uma trajetória que já tangencia a borda no passe 1 (margem de centímetros);
- a demanda lateral v²·κ na janela excede a capacidade μ_eff·g (demanda/capacidade > 1) — o carro desliza largo com o pneu gasto;
- relatório instrumental: sem promoção, sem ajuste de constante, sem corrida nova.
