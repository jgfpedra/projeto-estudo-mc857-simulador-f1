# OUT OF SAMPLE VALIDATION — limiar η=0,615 e forma fechada com downforce

**Data:** 2026-11-07 · **Método:** report-only sobre telemetria existente (zero corrida nova) · **Instrumento:** `scripts/prof_demand_out_of_sample.py` (determinístico, `cmp=0` ×2).

**Proveniência:** η=0,615 calibrado EM AMOSTRA (REF + CTRL_OFF + ON_N0); teste cego sobre **ON N1..N4 (--variedade 1..4)** — realizações fora da calibração.

## Matriz de confusão global (positivo = SAÍDA)

| | real SAÍDA | real LIMPA |
|---|---:|---:|
| **prev SAÍDA** | TP 62 | FP 5 |
| **prev LIMPA** | FN 0 | TN 1 |

**Acurácia de separação: 0.9265** sobre 68 passes fora da amostra.

**Pergunta especial — C01 em N1/N2:** as passagens que ficaram LIMPAS foram corretamente classificadas? **1/4** ✓.

## Matriz por crônica

| crônica | TP | FP | TN | FN | acurácia |
|---|---:|---:|---:|---:|---:|
| C01 | 14 | 5 | 1 | 0 | 0.75 |
| C06 | 16 | 0 | 0 | 0 | 1.0 |
| C07 | 16 | 0 | 0 | 0 | 1.0 |
| C08 | 16 | 0 | 0 | 0 | 1.0 |

## Varredura das demais curvas (máx razão inst nas N1..N4)

| curva | janela (m) | razão máx | risco > 0,615? | lat máx | fontes c/ saída |
|---|---|---:|---|---:|---:|
| C02 | 220.023–336.035 | 1.118 | SIM | 1.0444 | 0/4 |
| C03 | 988.104–1124.118 | 1.7168 | SIM | 1.0852 | 0/4 |
| C04 | 1176.124–1240.13 | 1.642 | SIM | 1.3193 | 0/4 |
| C05 | 1596.168–1804.189 | 0.9494 | SIM | 1.4078 | 0/4 |
| C09 | 2468.259–2564.269 | 1.0151 | SIM | 23.4413 | 4/4 |
| C10 | 2748.289–2852.3 | 0.956 | SIM | 2.7974 | 0/4 |
| C11 | 3128.329–3156.331 | 1.5572 | SIM | 2.3215 | 0/4 |

## t_lap forma fechada (η = 0,60, janelas das 4 crônicas)

Piso base (v_plan histórico): **96.202 s** · Guarda: **123.05 s** · c_m = 0.00368421 1/m.

| tyre_grip | t_lap piso (s) | Δ vs base | guarda? |
|---:|---:|---:|---|
| 0.807 | 97.653 | +1.451 | cabe |
| 0.842 | 97.457 | +1.255 | cabe |

## Leitura (report-only; veredito é do Dono)

- a acurácia global é o teste do limiar fora da amostra; FN é o erro caro (prev LIMPA, saiu);
- a varredura mostra se o alvo η=0,60 cria risco de saída nova nas demais curvas sob o pacing histórico;
- o t_lap de forma fechada usa a capacidade REAL (downforce) — substitui as estimativas com μ_eff·g ≈ 8 m/s².
