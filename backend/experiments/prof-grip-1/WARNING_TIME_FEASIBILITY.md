# WARNING TIME FEASIBILITY (v2 Kamm) — gatilho preditivo, autoridade e t_lap

**Data:** 2026-11-07 · **Método:** report-only (zero corrida nova) · **Instrumento:** `scripts/prof_warning_time_feasibility.py` (determinístico, `cmp=0` ×2) · **Fonte:** `CTRL_Interlagos_OFF.csv` (SHA `c00391ab…`).

**Agrupamento:** 20 cruzamentos brutos de 6,0 m → **20 excursões** após agrupar encadeadas (0 cascatas absorvidas — retorno nunca < 3.0 m).

## Tabela por crônica (excursões atribuídas ao ápice)

| crônica | excursões | gatilho real | já-fora/cascata | sem gatilho | Δt aviso médio (s) | Δt aviso mín (s) | a_brake_rem mín (m/s²) |
|---|---:|---:|---:|---:|---:|---:|---:|
| C01 | 4 | 32 | 0 | 0 | 1.081 | 0.4 | 0.0 |
| C06 | 4 | 32 | 0 | 0 | 0.844 | 0.2 | 0.0 |
| C07 | 4 | 32 | 0 | 0 | 9.475 | 9.0 | 0.0 |
| C08 | 4 | 32 | 0 | 0 | 0.613 | 0.2 | 2.257 |
| outras/reta | 4 | — | — | — | — | — | — |

## v_safe no ápice por crônica (dupla convenção, grip mín da janela)

| crônica | grip | R instantâneo (m) | v_safe inst (km/h) | R suavizado (m) | v_safe suav (km/h) |
|---|---:|---:|---:|---:|---:|
| C01 | 0.807 | 20.57 | 45.9 | 23.8 | 49.4 |
| C06 | 0.816 | 13.86 | 37.9 | 22.04 | 47.8 |
| C07 | 0.816 | 12.45 | 35.9 | 18.75 | 44.1 |
| C08 | 0.807 | 7.13 | 27.0 | 13.53 | 37.3 |

## Agregados por configuração (T, limiar) — excursões com GATILHO real

| config | gatilho | já-fora | sem gatilho | Δt médio (s) | Δt mín (s) | Kamm APROVADO (inst) | Kamm APROVADO (suav) |
|---|---:|---:|---:|---:|---:|---:|---:|
| T0.0_lim3.5 | 20 | 0 | 0 | 5.51 | 0.2 | 20 | 20 |
| T0.0_lim4.0 | 20 | 0 | 0 | 5.39 | 0.2 | 20 | 20 |
| T0.4_lim3.5 | 20 | 0 | 0 | 5.76 | 0.6 | 20 | 20 |
| T0.4_lim4.0 | 20 | 0 | 0 | 5.75 | 0.6 | 20 | 20 |
| T0.8_lim3.5 | 20 | 0 | 0 | 6.0 | 0.6 | 20 | 20 |
| T0.8_lim4.0 | 20 | 0 | 0 | 5.92 | 0.6 | 20 | 20 |
| T1.2_lim3.5 | 20 | 0 | 0 | 6.07 | 0.8 | 20 | 20 |
| T1.2_lim4.0 | 20 | 0 | 0 | 6.04 | 0.8 | 20 | 20 |

## Custo de ritmo integrado (v_safe nas janelas das 4 crônicas)

Piso base (v_plan histórico): **96.202 s** · Guarda: **123.05 s**.

| convenção | grip | t_lap piso (s) | Δ vs base | guarda? |
|---|---:|---:|---:|---|
| suavizada | 0.842 | 97.756 | +1.554 | cabe |
| suavizada | 0.807 | 98.037 | +1.835 | cabe |
| instantanea | 0.842 | 98.365 | +2.163 | cabe |
| instantanea | 0.807 | 98.602 | +2.400 | cabe |

## Leitura (report-only; veredito é do Dono)

- excursões encadeadas agrupam-se (cascata); os Δt de aviso são medidos DENTRO da janela de aproximação da própria crônica (≤ 150 m de arco antes do ápice); entradas já ≥ limiar são JÁ-FORA/CASCATA;
- a autoridade usa o Círculo de Kamm: no ápice a demanda lateral consome a aderência e a frenagem remanescente ≈ 0 — a autoridade física pertence ao pacing de entrada;
- o custo de ritmo integrado quantifica o piso da intervenção preventiva (v_safe no ápice) contra a Guarda.
