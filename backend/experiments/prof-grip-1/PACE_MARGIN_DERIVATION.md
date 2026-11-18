# PACE MARGIN DERIVATION (v2 horizonte) — escada fixa de η e perfil completo

**Data:** 2026-11-07 · **Método:** report-only (zero corrida nova) · **Instrumento:** `scripts/prof_pace_margin_derivation.py` (determinístico, `cmp=0` ×2).

## Correção metodológica (obrigatória)

- SEM regressão de lat_max contra razão para derivar η: lat_max é censurada e descontínua (grama/rejoin/dinâmica pós-saída); excursões de até 39,7 m não estimam fronteira de segurança;
- nenhum η < ~0,55 é "identificado pelos dados" (extrapolação);
- a escada η1/η2 é constante de engenharia pré-declarada.

## Escada fixa de η

- **η1 = 0.48848** (0,8 × 0,6106 — maior razão LIMPA da calibração; precisão completa no JSON: 0.48848)
- **η2 = 0.40000**
- regra: iniciar com η1; falha nos gates → escalada pré-declarada para η2; nenhum valor novo pós-observação.

## Diagnóstico descritivo (ON_N1..N4, por crônica)

| crônica | passes | LIMPA | SAÍDA | razão máx LIMPA | razão máx geral | lat_max (m) |
|---|---:|---:|---:|---:|---:|---|
| C01 | 20 | 6 | 14 | 0.6583 | 0.6715 | 5.8324–6.4174 |
| C06 | 16 | 0 | 16 | 0.0 | 0.8656 | 8.707–9.5213 |
| C07 | 16 | 0 | 16 | 0.0 | 0.9356 | 14.1151–15.5564 |
| C08 | 16 | 0 | 16 | 0.0 | 0.9663 | 35.1468–36.4057 |

Ajuste indicativo nas LIMPAS de C01 (n=6): lat_max = 6.7091 + -1.283349·razao — **diagnóstico indicativo, n pequeno, uma única crônica, sem poder de derivar ou validar η**.

## Perfil completo e custo de ritmo (η1 e η2 × grip)

Piso base (v_plan histórico): **96.202 s** · Guarda: **123.05 s**.

| estágio | η | grip | t_lap v_target_cap (s) | Δ vs base | folga Guarda | distância afetada (m) | piso otimista (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| eta1 | 0.48848 | 0.807 | 107.322 | +11.120 | 15.728 | 332.035 | 105.418 |
| eta1 | 0.48848 | 0.842 | 106.698 | +10.497 | 16.352 | 296.031 | 105.174 |
| eta2 | 0.40000 | 0.807 | 109.437 | +13.235 | 13.613 | 360.037 | 106.731 |
| eta2 | 0.40000 | 0.842 | 108.653 | +12.451 | 14.397 | 344.036 | 106.422 |

## Engajamento por estágio e crônica (η1, grip 0,842)

| crônica | engajou? | extensão (m) | % janela | maior trecho (m) | v hist mín (km/h) | v cap mín (km/h) | saídas c/ cap | sem cap |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| C01 | SIM | 132.014 | 100.0 | 132.014 | 53.643 | 38.196 | 4 | 0 |
| C06 | SIM | 76.008 | 95.0 | 52.005 | 51.054 | 36.022 | 4 | 0 |
| C07 | SIM | 64.007 | 76.19 | 64.007 | 46.86 | 30.955 | 4 | 0 |
| C08 | SIM | 60.006 | 83.33 | 32.003 | 38.305 | 25.602 | 4 | 0 |

## Δ no ápice por crônica (η1, grip 0,842)

| crônica | v hist ápice (km/h) | v cap ápice (km/h) | Δ (km/h) | Δ % |
|---|---:|---:|---:|---:|
| C01 | 56.403 | 44.287 | 12.115 | 21.48 |
| C06 | 51.371 | 36.022 | 15.348 | 29.878 |
| C07 | 48.889 | 34.071 | 14.818 | 30.309 |
| C08 | 38.606 | 25.602 | 13.004 | 33.684 |

## Gates pré-declarados para o ciclo ON

1. **C01, C06, C07 e C08: zero saídas no estágio final**;
2. **C06, C07 e C08: se qualquer uma sair com o cap ativo no estágio final, declarar PARE e rejeitar a hipótese de suficiência do mecanismo**;
3. se houver saída com o cap inativo, declarar **falha de engajamento/cobertura**, não falha física do limiar;
4. a **Guarda de Ritmo** deve ser avaliada pelo tempo observado no ciclo real, **não** pelo piso offline;
5. **nenhum gate pode ser alterado após observar os resultados**;
a escalada η1→η2 é pré-declarada (não é ajuste pós-fato).

"Cap binda" é apenas evidência de atuação — não autoridade suficiente, não eficácia, não prova de eliminação de saídas.

## Custo de ritmo — premissas

- frenagem: círculo de atrito com downforce (a_lat·sf − a_lat_demanda) + drag, piso 0,3 m/s², 4 iterações, fecho circular 200 m;
- aceleração: a_accel·sf (tração 55% + potência − drag − rolling);
- o piso otimista (1/min(0,93·v_plan, v_safe)) é referência inferior, rotulado — a estimativa final usa o perfil completo.

**Compatível no modelo offline; não prova que o controlador fechado respeitará a Guarda.**

## Conclusão

**PREPARADO PARA CICLO ON**

Sem "η seguro", "garantia de margem" ou "proteção comprovada" antes da validação ON.
