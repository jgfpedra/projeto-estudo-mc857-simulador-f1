# REALISMO-1 · C1-A — atribuição por canal (report-only, N=0)

**Data:** 2026-10-30 · **Estado:** análise pré-freeze; ZERO simulação, ZERO código de produção tocado; alimenta o prereg do C1.

**Entradas (bytes commitados):** `experiments/composite-1/promocao-1/1_R1_INTERLAGOS_RACE.{csv,log,_events.csv}` e `3_R3_MONACO_RACE.*`; pesos de produção `model_train/v15_residual/residual_best_weights.npz` (sha16 `6210fff6`) e solo `v10_dagger/dagger_actor_best_weights.npz`.

**Instrumento:** `scripts/c1a_attribution.py` (reusa `realismo_metrics.analyze_run` para os eventos Z_RETA, `NumpyCompositeActor.residual_forward_only` para o `r` exato, e `F1MultiContextEnv.steer_limit_rad`). Saída: `C1A_ATTRIBUTION.json`.

## Validação de exatidão

- `r` recomputado de `res_0..15` + NPZ de produção reproduz a coluna `r_norm` do CSV com erro máximo **2,7e-6 / 3,97e-6** (float32). O residual atribuído é exatamente o que a corrida usou.
- `tanh(m_solo + g·r)` reconstrói `a_steer` com erro máximo **2,2e-16**. A decomposição `pre = atanh(a_steer) = m_solo_steer + g·r_steer` é exata.

## Resultado 1 — direção do esterço (SUPORTA o C1-B)

Janela: 1 s (5 amostras) antes de cada saída na Z_RETA, linhas `authority=policy`. `exit_dir` = sinal de `obs4` na 1ª linha off-track. Projeção "no sentido da saída" = `× exit_dir` (positivo = empurra para o lado da saída).

| Pista | janelas | `m_solo_steer` p/ saída | `g·r_steer` p/ saída | `|g·r|/(|m_solo|+|g·r|)` |
|---|---|---|---|---|
| Interlagos | 12 | média **−1,414** (<0 em **12/12**) | média **+1,149** (>0 em **10/12**) | mediana 0,473 |
| Monaco | 6 | média **−1,298** (<0 em **6/6**) | média **+1,462** (>0 em **6/6**) | mediana 0,540 |

Leitura: **o solo esterça para LONGE do lado da saída em 18/18 janelas (corretivo); o residual empurra PARA o lado da saída em 16/18 (89%).** O residual é a componente que leva o carro para fora na reta de largada; o solo resiste. Por magnitude, o residual é ~47–54% do comando de esterço. As 2 exceções em Interlagos: uma janela com `g=0` (saída por subesterço/inércia, não residual) e uma em que o residual se opôs.

**A trava literal do plano (mediana de `g·r / pre ≥ 0,5`) é instável e deve ser substituída.** Como o solo domina a magnitude e aponta para longe, `pre` (denominador) é pequeno e muda de sinal, então a razão explode (Monaco pooled +8,9) ou fica negativa (Interlagos Σgr/Σpre −4,35); a mediana pooled 1,38 "passa" por artefato numérico, não por sinal limpo. A estatística robusta é direcional: **residual p/ saída em 16/18; solo contra em 18/18** → premissa do C1-B sustentada.

## Resultado 2 — a janela D_L do plano NÃO fecha (precisa redesenho)

A terminação pinada no plano — "cruzou `S_L_END` **E** `v ≥ V_L`" com `V_L = min(12,6; max vel. de saída)` — não é alcançável na fase de largada:

- `V_L_raw` (maior vel. no início de saída) = 14,93 m/s → `V_L = 12,6`.
- Condição conjunta `S_L_END ∧ v≥12,6`: Interlagos **6/10** carros antes de 10 s (último em **42 s**); Monaco **0/10** na largada (mediana **238 s** — perto do start os carros não chegam a 12,6 m/s).
- Posição-só (cruzar `S_L_END`): Interlagos mediana 8,9 s (máx 11,6); Monaco mediana 3,4 s (máx 6,0). `S_L_END` de Monaco (3331,2) fica a ~2 m da frente do grid (3329,2); o de Interlagos a ~69 m.

Ou seja, a condição conjunta roda até o teto `T_L_MAX=10 s` para ~40% do grid em Interlagos e para todo o grid em Monaco. Isso é intervenção muito mais longa que o alvo (as saídas agrupam em **t=2,2–3,8 s**, com cauda Interlagos até 7,8 s), e mutaria o esterço do residual (a defesa de contato) por ~10 s em todo carro.

**Recomendação:** redefinir `D_L` por POSIÇÃO — mutar o canal de esterço do residual enquanto o carro está on-track e ainda **não cruzou `S_L_END`** (fim da Z_RETA = entrada da T1), com `T_L_MAX` só como teto de segurança; **descartar a condição `v≥V_L`** (inalcançável em Monaco, não agrega). Isso cobre 100% das saídas Z_RETA por construção (todas em `s ≤ S_L_END`) e termina naturalmente quando o carro deixa a reta.

## Fatos para o prereg

- `S_L_END` = fim da Z_RETA por SHA de pista: Interlagos `164876196eb12174` → 2718,3; Monaco `67ca11dc211c8c78` → 3331,2.
- Saídas Z_RETA N=0: Interlagos t_s {2,2 2,4 2,4 2,4 3,0 3,2 3,4 3,8 5,4 7,6 7,6 7,8}; Monaco {2,2 2,4 2,4 3,0 3,0 3,0}.
- Vel. no início da saída (min/med/máx): Interlagos 9,17/10,96/14,93; Monaco 7,88/9,63/12,65.

## Decisões abertas (para o freeze do C1)

1. **Trava de falsificação:** adotar a estatística direcional (residual p/ saída em maioria forte; 16/18) no lugar da razão `g·r/pre` instável. **PASSA** → seguir para C1-B.
2. **Janela D_L:** adotar posição (`on-track ∧ s ≤ S_L_END`) + `T_L_MAX` de segurança, descartando `v≥V_L`. Definir `T_L_MAX` (proposta: 10 s) e se há guarda temporal adicional.
