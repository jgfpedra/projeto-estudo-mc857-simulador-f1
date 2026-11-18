# GRIP PACING FEASIBILITY — pacing sensível ao grip nas 4 crônicas

**Data:** 2026-11-07 · **Método:** offline report-only (zero corrida/PyBullet) · **Instrumento:** `scripts/prof_grip_pacing_feasibility.py` (determinístico, `cmp=0` ×2) · **Guarda:** 123.05 s.

Piso base (v_plan histórico, sem mecanismo): **96.202 s** (piso teórico — ignora rastreio/transições; a mediana rolante OFF observada é 130,195 s).

| grip | fator direta | t_lap direta (s) | Δ vs base | guarda? | fator reserva | t_lap reserva (s) | Δ vs base | guarda? |
|---:|---:|---:|---:|---|---:|---:|---:|---|
| 0.85 | 1.0000 | 96.202 | +0.000 | cabe | 0.9535 | 97.06 | +0.858 | cabe |
| 0.84 | 0.9941 | 96.306 | +0.104 | cabe | 0.9478 | 97.169 | +0.968 | cabe |
| 0.82 | 0.9822 | 96.52 | +0.319 | cabe | 0.9365 | 97.394 | +1.193 | cabe |
| 0.80 | 0.9701 | 96.743 | +0.541 | cabe | 0.9250 | 97.627 | +1.426 | cabe |
| 0.78 | 0.9579 | 96.974 | +0.772 | cabe | 0.9134 | 97.87 | +1.668 | cabe |
| 0.75 | 0.9393 | 97.337 | +1.136 | cabe | 0.8956 | 98.251 | +2.049 | cabe |

## Custo por curva (s), variante DIRETA (Δ vs base)

| grip | C01 | C06 | C07 | C08 |
|---:|---:|---:|---:|---:|
| 0.85 | +0.000 | -0.000 | +0.000 | -0.000 |
| 0.84 | +0.030 | +0.023 | +0.026 | +0.026 |
| 0.82 | +0.091 | +0.070 | +0.079 | +0.079 |
| 0.80 | +0.154 | +0.119 | +0.135 | +0.134 |
| 0.78 | +0.219 | +0.170 | +0.192 | +0.191 |
| 0.75 | +0.322 | +0.250 | +0.282 | +0.281 |

## Leitura (report-only; veredito é do Dono)

- o mecanismo só toca as janelas das 4 crônicas — retas e demais curvas ficam com o v_plan histórico;
- o piso não inclui frenagens a montante nem perdas de rastreio: é limite INFERIOR do lap com o mecanismo (estouro no piso = quebra garantida; piso dentro da Guarda ainda pode estourar corrido);
- a variante com reserva 10% existe para não repetir o tangenciamento a centímetros da zebra visto no LAGO_APPROACH_FINDINGS (a Volta 1 passou com margem de +6 cm).
