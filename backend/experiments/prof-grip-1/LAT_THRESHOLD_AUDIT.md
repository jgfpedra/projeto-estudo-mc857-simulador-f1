# LAT THRESHOLD AUDIT — limiares de margem lateral e custo de desaceleração

**Data:** 2026-11-07 · **Método:** report-only sobre os controles OFF existentes (zero corrida nova) · **Instrumento:** `scripts/prof_lat_threshold_audit.py` (determinístico, `cmp=0` ×2) · **a_brake:** 15.0 m/s² (pinado no mandato).

## Interlagos (CTRL_OFF, 4 voltas)

| limiar (m) | ticks | % tempo | eventos | dur média (s) | crônicas | outras | reta | v média (m/s) | v máx (m/s) | custo 10% por volta (s) | custo 20% por volta (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.5 | 840 | 28.0 | 24 | 7.0 | 17 | 5 | 2 | 9.669 | 27.741 | 0.335 | 0.67 |
| 4.0 | 819 | 27.3 | 21 | 7.8 | 17 | 4 | 0 | 9.501 | 24.234 | 0.262 | 0.525 |
| 4.5 | 802 | 26.7333 | 21 | 7.638 | 17 | 4 | 0 | 9.42 | 24.234 | 0.263 | 0.525 |
| 5.0 | 786 | 26.2 | 21 | 7.486 | 17 | 4 | 0 | 9.324 | 23.082 | 0.262 | 0.523 |

## Monaco (CTRL_OFF, 2 voltas)

| limiar (m) | ticks | % tempo | eventos | dur média (s) | crônicas | outras | reta | v média (m/s) | v máx (m/s) | custo 10% por volta (s) | custo 20% por volta (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.5 | 1901 | 63.3667 | 53 | 7.174 | 6 | 32 | 15 | 9.352 | 21.317 | 0.995 | 1.99 |
| 4.0 | 1856 | 61.8667 | 52 | 7.138 | 6 | 31 | 15 | 9.266 | 21.26 | 0.965 | 1.93 |
| 4.5 | 1813 | 60.4333 | 48 | 7.554 | 6 | 27 | 15 | 9.14 | 19.889 | 0.837 | 1.674 |
| 5.0 | 1773 | 59.1 | 44 | 8.059 | 6 | 26 | 12 | 9.041 | 17.185 | 0.707 | 1.414 |

## Leitura (report-only; veredito é do Dono)

- limiares mais baixos contêm ≥ ticks (nesting) e revelam a fração do tempo que o carro já passa fora da MEIA margem antes de cruzar 6,0 m;
- o custo de desaceleração projeta quanto tempo uma intervenção de pacing pagaria por corrida/volta para desacelerar 10%/20% a cada evento de violação (estimativa cinemática linear, não simulação);
- o mapeamento por setor mostra se a violação de margem se concentra nas 4 crônicas ou se é difusa (Reta/outras).
