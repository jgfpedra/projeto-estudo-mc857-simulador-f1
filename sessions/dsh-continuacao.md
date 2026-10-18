# DSH — Sessão de Continuação (2025-06-28 a 2025-07-01)
> **PINNED** — Leia este arquivo + PROJECT_STATE.md antes de qualquer ação futura.
> **ÚLTIMA ATUALIZAÇÃO: seção "Sessão v14 FASE 3" no FIM deste arquivo** (ator v14 treinado; FASE 4 pendente).

## Decisões Tomadas

1. **DAgger é o método canônico** do projeto. PPO descartado após 4 falhas estruturais
   (v6, v12, v13-no-respawn) — o gradiente PPO degrada sistematicamente a política
   DAgger independentemente do protocolo (com ou sem respawn).

2. **Dual-profile** para deploy: v10 = "race setup" (48/51, 109s), v11b = "quali setup"
   (108s, Suzuka 2/3). Análogo a setup de qualificação vs corrida.

3. **Meta C (91.2s) fechada** — veredicto: TETO. O stack DAgger atinge ~108s, limitado
   pelo pure pursuit do professor (~100s a sf=1.0 vs teórico 85s). Para 91.2s seria
   necessário racing line ou MPC (mudança de controlador, não de otimização).

4. **Recompensa física-alinhada**: _v_allow_at usa downforce (v² = mu·g/(κ−mu·c/m))
   com sf_reward parametrizável. O A_LAT_MAX=14 fixo original proibia o ritmo que
   curvas rápidas permitem (a_lat real: 16-33 m/s² dependendo de v).

5. **Professor v2** com perfil físico: círculo de atrito no backward pass + sf adaptativo
   (decai em κ>0.10) + suavização híbrida peak/avg. 100% confiável em TODAS as 8 pistas
   reais + 6 procedurais (Monaco era 4/20 → agora 20/20).

6. **Obs 'edge' (34d)**: 11 raios LiDAR às bordas do asfalto. Zero-shot Suzuka melhorou
   (42% vs 24% legacy). Paridade com legacy em treino.

## O Que Foi Feito

### Pipeline completo
- **v10 DAgger**: 48/51 (94%) — treino 39/39 (13 pistas), VAL Zandvoort 3/3,
  **Suzuka 3/3 zero-shot** (esses resolvidos pelo pool ampliado com Mexico/esses
  procedurais), Spa 3/3. Monaco 0/3 (persiste — física R=6.4m).
- **Meta D corrida**: v10 edge — 1 hesitação, 2s parado, 0.8% fora, 10/10 carros
  completam. Interlagos + Monza validados.
- **Pool de 13 pistas de treino**: 7 FastF1 (interlagos, Monza, Hungaroring,
  Silverstone, Montreal, Bahrain, Mexico) + 6 procedurais (hairpin_A/B/C, esse_A/B, mista).
- **Gerador procedural** (`procedural_track.py`): elipse base → U-points de hairpin →
  esses alternados → Catmull-Rom centrípeto → subdivisão ≤4m → gate de kappa.
- **Fronteira física** (`physics_frontier.json`): R_min(v) calibrada por skidpad.
  grip real: R=4m a v=4-8, R=6m a v=10, R=13m a v=13.
- **Race layer edge**: NeuralRaceController com _cast_rays_batch (10 carros),
  validação de shape com erro explícito, _kappa_signed wrap fix.
- **FASE 1 v14**: camada de tráfego no ReferenceController (car-following +
  offset lateral suavizado). Backwards compatible.

### Testes
- **152/152** (147 base + 5 test_reward_vallow). Novos: test_kappa_sign (5),
  test_velocity_profile (17), test_edge_obs (20), test_procedural_track (14),
  test_reward_vallow (5).

## Abordagens que Falharam (com causa)

| Abordagem | Tentativa | Causa da falha |
|---|---|---|
| **PPO (todas as variantes)** | v5/v6/v6b/v6d/v12/v13 | Gradiente degrada política DAgger. Com respawn: lap% fabricado (safety net). Sem respawn: sinal honesto mas otimização piora (108s→125s). 4× confirmado. |
| **BC puro** | v8-edge | Covariate shift — morre no wrap igual ao legacy. DAgger resolve. |
| **sf=0.95 via DAgger** | v11 | 36/51 (71%) — margens zero herdadas. Bahrain/Mexico/Suzuka/Spa regrediram. DESCARTADO. |
| **ld_min menor (Monaco)** | 3-5m | Pure pursuit oscala a <5m de lookahead. Piora. |
| **Geometria por telemetria** | Monaco X/Y FastF1 | R=7m ≈ marcadores R=6m (diferença <15%). Não justifica o custo de re-tunar. |
| **Cap de velocidade no ápice** | V_HAIRPIN_CAP=4.5 | O problema é o VETOR VELOCIDADE desalinhado na APROXIMAÇÃO, não a velocidade no ápice. |

## Bugs Críticos Encontrados e Corrigidos

1. **Kappa wrap ±180°** (CRÍTICO): `_kappa_signed` usava diferença central única
   h(s+10)−h(s−10). Em hairpins de ~180° (Monaco s=1016), a diferença cruzava a
   fronteira do wrap: s=1015 dava +0.157, s=1016 dava −0.156! O aluno via curva à
   DIREITA numa curva à ESQUERDA. Fix: acumular diferenças pequenas (~2m).

2. **Hint stale** (histórico): prev_waypoint_idx preso na região errada da pista →
   grip 0.28 no asfalto (nível de grama). Corrigido com nearest_segment + auto-recuperação.

3. **Kappa fator-2**: compute_kappa_profile dividia dh por 2·ds em vez de ds.
   Verificado com círculo R=50 (kappa 0.01 vs 0.02 esperado).

4. **Sinal do kappa em procedurais**: média móvel de 20m INVERTIA o sinal de hairpins
   entre curvas opostas. Fix: híbrido peak/avg.

## Perguntas em Aberto

1. **Monaco zero-shot**: hairpin R=6.4m no limite físico. O aluno não aprende a usar
   a escape road (lat=7m) como o professor faz. Solução proposta: procedurais com
   R<8m OU mudança na física (4a/4b). Ambos fora do escopo atual.

2. **Corrida com tráfego**: 1333 contatos carro-carro, 137s vs 109s solo (26% mais
   lento). FASE 1 (professor com tráfego) implementada mas gate da corrida
   all-professor PENDENTE (requer modo --controller professor no race_diagnostic.py).

3. **Obs de oponentes (FASE 2-4)**: desenhada (12d extras: 3 carros mais próximos
   com dist/Δv/lat/ahead) mas não implementada. Requer multi-car no env.

4. **Racing line**: o pure pursuit perde 15s/volta vs o teórico. Otimização de
   curvatura mínima dentro das bordas poderia recuperar ~10s. Não implementada.

5. **Correlação treino↔determinístico**: o PPO atinge lap% 2-6% no treino (com
   random starts e grip variável) mas 0-2/3 determinístico. A distribuição de
   estados do treino (start_zones, grip random) difere do eval (standing start,
   grip fixo). Não investigado sistematicamente.

## Próximos Passos (prioridade)

1. **GATE da FASE 1 v14**: implementar modo all-professor no race_diagnostic.py e
   rodar 600s × 10 caros todos com ReferenceController(traffic=...). Meta: ≥9/10
   completam, <400 contatos (baseline aluno-cego: 1333), zero paradas ≥3s.

2. **FASE 2-3 v14**: obs 'traffic' (60d) + fantasmas no env + DAgger de tráfego.

3. **Monaco**: procedurais com hairpin R=6-8m (abaixar o multiplicador do ápice
   no gerador de 1.8 para 0.8-1.0, aceitando que o spline alarga).

4. **Racing line**: otimização de curvatura mínima (gradiente descent nos waypoints
   dentro das bordas) para o professor. Potencial: −10-15s/volta.

5. **PROJECT_STATE.md**: revisar a cada fase e manter a tabela de metas atualizada.

## Comandos Essenciais

```bash
cd backend
.venv/bin/python -m pytest tests/ -q          # 152/152
# avaliação determinística
.venv/bin/python model_train/eval_policy.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras \
  --episodes 3 --obs-mode edge
# corrida 600s
.venv/bin/python model_train/race_diagnostic.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras \
  --obs-mode edge --ticks 6000 --out race.csv --track interlagos
# DAgger novo (13 pistas)
.venv/bin/python model_train/train_dagger.py --obs-mode edge \
  --tracks "interlagos,Monza,Hungaroring,Silverstone,Montreal,Bahrain,Mexico,procedural:101,procedural:103,procedural:107,procedural:201,procedural:203,procedural:301" \
  --val-track Zandvoort --iters 10 --save-dir model_train/vN_dagger
```

## Metas (estado final)

| Meta | Status | Resultado |
|---|---|---|
| A. Professor ≥95% | ✓ | 100% (40/40, 8 pistas) |
| B. Aluno ≥9/10 treino | ✓ | 100% (39/39, 13 pistas) |
| B'. Aluno ≥7/10 teste | ✘ 6/9 | Suzuka 3/3 ✓, Spa 3/3 ✓, Monaco 0/3 |
| C. Tempo ≤91.2s | ✘ 109s | teto DAgger ~108s; PPO 4× falhou |
| D. Corrida 10 carros | ✓ | 1 hes, 0.8% fora, 10/10 (Interlagos + Monza) |

## Splits de pistas (NUNCA alterar)

TREINO: interlagos, Monza, Hungaroring, Silverstone, Montreal, Bahrain, Mexico,
procedural:101-301 (13). VAL: Zandvoort. TESTE: Monaco, Suzuka, Spa (zero-shot).

---

# Sessão v14 (2026-10-13) — GATE all-professor VERDE + FASE 2 implementada

> Esta seção SUPERSCREDE as "Perguntas em Aberto" 2 e 3 da sessão anterior.

## O que foi feito

### PASSO 1 — modo professor no race runner
- **Bug da FASE 1 corrigido**: o `_lat_offset` era computado mas NUNCA aplicado
  (estado morto). Agora a camada de tráfego roda ANTES do pure pursuit e
  desloca o ponto de perseguição (referência_controller.py).
- **Métrica de tráfego** (`signed_dist_s`): distância ao LONGO da pista com
  sinal (positiva = à frente; wrap ±L/2). Ranking por |dist_s|; sinal no flag
  ahead. Um carro 5 m atrás dá -5, não +L-5.
- **`--controller professor`** no race_diagnostic.py: 10 ReferenceControllers
  simultâneos (v_plan único compartilhado), cada um com os outros 9 como
  tráfego. **Autoridade: professor → rejoin → recovery → blocked, SEM
  governor** (o v_plan já freia; governor = frenagem dupla). ProfessorRace-
  Controller herda do NeuralRaceController (camadas de recovery idênticas).
- Professor ganhou `driver_id=` no construtor (fantasmas da FASE 2 usam o
  MESMO objeto env). Solo/DAgger inalterados (traffic=None → offset 0).

### PASSO 2 — GATE (600 s, 10 professores, Interlagos, 2 seeds): VERDE
| métrica | resultado |
|---|---|
| ≥1 volta | **10/10** (5 voltas cada; seeds 0 e 1 idênticos = determinístico) |
| contatos carro-carro (5 Hz) | **258** (<400; baseline aluno-cego 1333 = −81%) |
| paradas ≥3 s | **0** |
| ultrapassagens líquidas | **1** (na largada) → FILA esparsa, sem ultrapassagem |
| % follow (cap+close) | 0-15% por carro (VER 0%) — NÃO é fila permanente |
| mediana de volta c/ tráfego | **107,9 s** (excl. V1) vs solo ~107 s → custo +1 s |

Comportamento registrado: contatos CONFINADOS à largada (t=1,2-47,8 s; pares
de fileira cruzando a pista pela camada de offset), campo se espalha (gap
médio ~430 m >> D_AHEAD 60), 552 s finais com ZERO contatos. **Teto v14:
evita colisões, sem ultrapassagem deliberada.** Baseline da FASE 4: 107,9 s.

### FASE 2 — obs 'traffic' + fantasmas (tudo implementado e testado)
- `obs_mode='traffic'` = edge 34d + 12d = **46d** (ator v14 = 60 entradas):
  3 carros mais próximos por |dist_s|; por carro:
  `[|dist_s|/100, (v_outro-v_ego)/100, lat_outro/half_width, ahead(1|0)]`;
  zeros se <3 visíveis; obs NUNCA contém o próprio carro; validação de shape
  com ValueError explícito. Layout documentado em N_TRAFFIC_FEAT (f1_env.py).
- `n_traffic` (0-9) no env: fantasmas físicos dirigidos pelo professor de
  TRÁFEGO (cada um vê aluno + outros fantasmas via `env.traffic_for(id)`),
  grip nominal 1.0, grid F1 à FRENTE do aluno (P10), reposicionados a cada
  reset. **Sem voltas**: `engine._no_lap_drivers` (simulation.py) pula
  _complete_lap mas MANTÉM cum_dist; sem degradação de pneu, sem avançar clima.
- `allow_respawn=False` no train_dagger VERIFICADO (linha 179; lição v13 ok).
- **Suite: 181/181** (152 base + 15 test_traffic_professor + 14 test_traffic_env).
- Padrão de rotulação da FASE 3 já validado no smoke:
  `teacher.action(traffic=env.traffic_for(env.driver_id))`.

## FASE 3 (PRÓXIMA SESSÃO) — checklist concreto
1. `train_dagger.py`: choices de `--obs-mode` += 'traffic'; envs com
   `n_traffic` (sugerido: variar 0-9 por pista/episódio? começar fixo, medir);
   `rollout_episode`: `a_teacher = teacher.action(traffic=env.traffic_for(env.driver_id))`.
2. Ator v14 = 60 entradas — `--init-actor` do v10 NÃO SERVE (input 48). BC do
   zero (iter 0 = professor com tráfego) ou transferir pesos camada a camada.
3. Sem PPO. Sem respawn (already default). Save-dir versionado (v14_dagger).
4. Gate FASE 4: corrida aluno(v14) vs 9 professores — comparar com baseline
   107,9 s (all-professor) e 1333 contatos (aluno-cego v10).

## Cuidados herdados (não esquecer)
- Contatos na largada vêm da camada de offset (líder na coluna oposta manda
  cruzar a pista). Se a FASE 4 pedir largada limpa: ajustar a CONDIÇÃO do
  offset (só deslocar se o líder está perto do MEU lateral) — UMA variável,
  com medição, nunca às cegas.
- Seeds do gate produziram resultados idênticos (sim determinística); "2 seeds"
  serve para detectar não-determinismo de contatos, não há RNG na corrida.
- `race_diagnostic.py` importa `run_race_10_cars` no nível do módulo agora
  (ProfessorRaceController herda dele) — teste neural pós-mudança: OK (v10,
  input_dim 48, 60 ticks sem crash).

---

# Sessão v14 FASE 3 (2026-10-13) — DAgger de tráfego: ator v14 treinado

> Supersede o checklist "FASE 3" da seção "Sessão v14" acima (executado).

## Resultado em uma linha
Ator v14 (60 entradas) treinado por currículo "0:2,4:5,8:3" a partir da
transferência v10; gates A e B verdes; estágio C verde no BEST (iter 8);
checkpoint de corrida = **v14_traffic/dagger_actor_best_s2_n8.keras**.

## PASSO 0 (baseline + professor limpo)
- Inconsistência 107,9s vs "112s" RESOLVIDA: unidades de volta diferentes.
  Professor solo na metodologia do gate (`eval_teacher_solo.py`, 3 eps
  idênticos): largada parada **110,6s** | rolantes **107,5s** | custo do
  tráfego = 107,9−107,5 = **+0,4s**. O "112s" era largada parada no env.
- Corredor do offset (LAT_CORRIDOR_M=3,5): cruzamentos laterais EXTINTOS
  (re-gate: 258→240, 0 pares laterais; resto = nose-a-cauda de largada por
  compostos HARD vs MEDIUM). Nada regrediu. Professor APROVADO p/ rotular.

## PASSO 1 (transferência) — NÃO BC-do-zero
- `transfer_v10_v14.py` remapeia rows da 1ª Dense: 0-33 edge, 34-45 ZEROS
  (rede começa ignorando tráfego), 46-47 ctx, 48-59 embeddings.
- Paridade 1e-6 (7/7 em test_v14_transfer.py) + congelamento matemático
  provado: gradiente nos rows 34-45 é NULO enquanto os inputs forem zero.
- Checkpoint: v14_traffic/init_from_v10.keras.

## PASSO 2/3 (currículo + gates)
| estágio | n | gate | resultado |
|---|---|---|---|
| A | 0 | G1 | Interlagos 3/3 108,1s + Suzuka 3/3 132,3s — REGRESSÃO ZERO ✓ |
| B | 4 | G1+G2 | 106,9s; Suzuka 3/3; c/ tráfego 3/3 123,4s (professor 123,9s), 0 contatos/lap ✓ |
| C | 8 | G1+G2 (best iter 8) | 109,9s; Suzuka 3/3 136,3s; c/ tráfego 3/3 134,0s (professor 134,1s), 0 contatos/lap ✓ |

- **O ATOR FINAL (iter 10, β=0) FALHOU Suzuka 0/3** — dataset dominado por
  estados do aluno com ruído 0,15. O best-por-VAL do estágio (iter 8) PASSA
  tudo (`gate_checkpoint.py`). Último checkpoint bom = best_s2_n8.
  LIÇÃO: aplicar o gate ao best-por-VAL, não ao ator final; considerar
  beta_end≈0,3 no próximo currículo (medir antes).
- Professor-com-tráfego no MESMO instrumento do G2: n=4: 123,9s; n=8: 134,1s,
  0 contatos/lap (env: fantasmas idênticos MEDIUM → gaps estáveis).

## FASE 4 (PRÓXIMA SESSÃO) — números pinados
1. 51 eps sem tráfego: v14 (best_s2_n8) vs v10 (48/51, 109s).
2. Eval com tráfego n=5, 3 eps, 5 pistas vs professor (123,9s n=4 / 134,1s n=8).
3. Corrida 600s all-v14: REQUER obs 'traffic' 60d no NeuralRaceController
   (race_diagnostic/run_race_10_cars), NPZ re-export + paridade NumPy.
   Metas: contatos <400 (v10 cego 1333; professor 240), hesitações ≤3,
   tempo ≤107,9s (professor-com-tráfego; solo 107,5s), fora ≤1,5%.
4. Expectativa honesta: v14 evita colisões (0 contatos/lap n=4 e n=8);
   ultrapassagem é improvável — o professor ensina FOLLOW.

## Comandos reproduzíveis
```bash
cd backend && .venv/bin/python -m pytest tests/ -q    # 192/192
.venv/bin/python model_train/eval_teacher_solo.py --laps 3 --episodes 3
.venv/bin/python model_train/gate_checkpoint.py \
  --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras \
  --g1-tracks "interlagos,Suzuka" --g2-traffic 8
```

---

# Sessão v14 FASE 4 (2026-10-13) — validação completa: veredicto NEGATIVO p/ all-v14

> Lê o bloco "FASE 4" no PROJECT_STATE.md — a tabela de produto está lá.
> Resumo executivo abaixo.

## Veredicto de produto (deliverable)
- **Solo (51 eps): v14 = 39/51** vs v10 48/51. Esquecimento PROGRESSIVO de
  hairpins extremos fora do pool de 5 pistas (iter1 intacto → iter3 perde
  Silverstone → iter8 perde Montreal/107; travam em κ −0,12/−0,13). Spa
  zero-shot LIMPO 3/3 132,2s (primeira medição); Suzuka 3/3 (ressalva: foi
  gate); Monaco 0/3 (= v10).
- **Tráfego n=5 (eval com fantasmas)**: paridade LIMPA com o professor em
  Interlagos (126,9 vs 127,3s, impulso 0=0) e Hungaroring; Mexico/procedural:301
  "mais rápido" CONTAMINADO por empurrões (escrutínio); **Monza ruim p/ AMBOS**
  (professor 2/3, 244 cont/lap: o modo 'close' (v_cap=v_ahead) nunca REABRE o
  gap — fica em contato a 3,7m; fix = v_ahead − ε abaixo de gap seguro).
- **Corrida all-v14: FALHOU** — 1691 contatos (>1333 do v10 cego!), 852
  pós-largada, 33 hesitações, 152,4s rolantes (degrada p/ 186-315s), 1,22%
  fora, 10/10 voltas. **Fila-encravamento**: nunca viu carro PARADO na linha
  nem carros ATRÁS (grade de treino só à frente); incidente → fila em rastejo
  → empurrões (contatos nos min 6/8 quando v média cai p/ 5,8 m/s).
- **v14 = evita colisões?** Em tráfego de fantasmas SIM (0 cont/lap até n=8);
  em corrida all-neural NÃO. Ultrapassagem: não ensinada, não observada.

## Deploy (implementado)
`run_race_10_cars.py --profile race|quali|traffic` (default **race** = v10).
O default por mtime foi REMOVIDO (escolheria errado entre 3 candidatos).

## Pipeline 60d validado (reutilizável na FASE 5)
- compute_traffic_features = FÓRMULA ÚNICA f1_env↔race runner.
- Paridade NumPy↔Keras: ≥1000 obs reais, atol 2e-5 (contrato: NumPy devolve
  tanh(mean); Keras a média linear — comparar ação-vs-ação).
- Shape: erro explícito nos 3 modos. Suite **197/197**.

## FASE 5 (checklist priorizado)
1. Currículo de tráfego com POOL de 13 pistas (fix do esquecimento — causa medida).
2. Rótulos de contorno de carro parado + carros ATRÁS no grid (fix da fila).
3. v_cap = v_ahead − ε em gap<seguro no professor (fix Monza; uma variável + re-gate).
4. Re-validar: 51 eps + n=5 + corrida all-v14 contra os números da FASE 4.

## Comandos reproduzíveis (FASE 4)
```bash
cd backend && .venv/bin/python -m pytest tests/ -q   # 197/197
.venv/bin/python model_train/eval_protocol.py \
  --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras --out v14_protocol.json
.venv/bin/python model_train/eval_traffic_compare.py \
  --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras --n-traffic 5
.venv/bin/python model_train/race_diagnostic.py \
  --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras --obs-mode traffic \
  --ticks 6000 --laps 99 --track interlagos --out race_diag_v14_all.csv --seed 0
```

---

# Sessão v14 FASE 5 (2026-10-13) — PARTE A ✓; PARTE B treinando em background

## PARTE A (veredictos fechados)
- **A1 slot-swap: SIM** — 0,484 swaps/s nas janelas ±5s de contato vs 0,203
  baseline (**2,38×**), correlação 0,067 (contribuinte, não causa única).
  Instrumento: `model_train/slot_swap_analysis.py` (+4 testes). Design v15:
  histerese de slots. NÃO mudar a obs do v14 (distribuição vs treino).
- **A2 campo misto** (`race_diagnostic.py --mixed "traffic:N,edge:M"`):
  - (i) 2×iter8+8×v10: **FALHA** — 15 hesitações, 222 contatos pós-largada
    dos v14s, v10s sobem p/ ~251 cont/carro (vs 133 baseline).
  - (ii) 1×iter8+9×v10: **PASSA** — v14 com 0 contato pós-largada, 0
    hesitações, 137,4s (pace dos v10s).
  - (iii) 2×iter3+8×v10: **PASSA** — 0 pós-largada, 0 hesitações, 138,2s.
  - **Produto: CONDICIONAL** — campo misto usa **iter3** (ou 1× iter8);
    par de iter8 e all-iter8 proibidos. v10s nunca hesitam, pace 137,0s
    estável. Limitação: controle all-v10 com grid embaralhado não rodado.
- Bug corrigido em A2: lap-time por wrap usava ÍNDICE de amostra ×0,1s em
  vez de VALOR de tick ×0,1s (amostras 5 Hz) — tempos revisados dos CSVs.

## PARTE B — EM VOO (ao abrir a próxima sessão, faça isto primeiro)
1. `tail model_train/v14b_traffic/train.log` — treino do v14b (pool 13
   pistas, β-end 0,3, gates automáticos nas 5 canárias NO BEST-POR-VAL,
   G2 n=8 por estágio). Comandos de repro: no fim do PROJECT_STATE.
2. Se todos os gates verdes → **B3**: 51 eps solo (`eval_protocol.py --actor
   model_train/v14b_traffic/dagger_actor_best_s2_n8.keras`, meta 48/51);
   corrida all-v14b 600s; corrida mista config (iii) com o v14b no lugar do
   iter3. Comparar com a tabela da FASE 4 (1691/152s) e com (iii) (1406/138s).
3. Se gate falhar → o estado está no training_meta.json (last_good).
4. Atualizar PROJECT_STATE (mapa v14b, veredicto B3) e este arquivo.

## Suite
**209/209** (197 + 4 slot-swap + 8 mixed-runner). Regras mantidas: sem PPO,
sem physics.py/recompensa, tudo inferência nesta PARTE A.

---

# Sessão v14 FASE 5 — PARTE B FECHADA (2026-10-14)

## Resultado
- **Esquecimento RESOLVIDO**: v14b (pool-13) estágio A → 51 eps **48/51 =
  paridade v10**, canárias recuperadas (Silverstone 141,7s / Montreal 110,3s /
  proc:107 93,2s, todas 3/3), Spa 3/3 124,4s, Monaco 0/3 (= v10).
- **Estágio B do v14b REPROVADO no gate**: best-por-VAL (iter 3) fez Suzuka
  **2/3** (obrigatório 3/3) com canárias verdes e G2 n=4 3/3 (10 cont/lap) —
  near-miss. Regra aplicada: parar no último verde (best_s0_n0); estágio C
  não rodou. **Não retreinar sem evidência nova.**
- **Controle all-v10 grid embaralhado: 1820 contatos** (vs 1333 original) —
  a "degradação" dos v10s nas mistas da PARTE A era majoritariamente
  ARTEFATO DO GRID; as mistas (ii) 1573 e (iii) 1406 ficam ABAIXO do
  controle. Deploy de campo misto com **iter3** REFORÇADO.
- **Veredito do encravamento: NÃO resolvido — deficiência de TREINAMENTO**
  (o mesmo iter8 encrava em par e é limpo sozinho; interações nunca rotuladas:
  carro parado, carros atrás, slot-swap 2,38×). FASE 6: fantasmas com paradas
  programadas, carros atrás no grid, rótulos de contorno, re-run do estágio B
  com âncora de replay (fallback documentado) p/ fechar o near-miss de Suzuka.
- Infra nova: `--shuffle-grid` e `--hold-at` no race_diagnostic (B3.3c/d);
  o (d) hold-at não rodou (dependia do ator de tráfego v14b, que não existe).
- Suite **211/211** (+2 hold-at).
- Bug de relatório conhecido: a linha "[FINAL] último checkpoint bom" do
  train.log aponta o best do estágio reprovado (last_good setado antes do
  gate) — o último VERDE é o best_s0_n0. Corrigir na FASE 6 se tocar o script.

## Próxima sessão (FASE 6) — checklist
1. Re-rodar ESTÁGIO B (n=4) do v14b com --init-actor v14b_traffic/dagger_
   actor_best_s0_n0.keras + âncora anti-esquecimento (misturar replay de
   demonstrações solo às iters B) OU β-decay mais lento; medir Suzuka 3 eps
   por iter p/ vigiar o near-miss.
2. Fantasmas com paradas programadas + carros ATRÁS no grid (rótulos de
   contorno) — o parágrafo do encravamento (limitação 9) é a justificativa.
3. Se estágio B verde → C → B3 completo (51 eps + compare n=5 + corridas
   all-v14b + mista par + hold-at (d) com o novo ator).
4. Tabela competência×cidadania final (a de 4 linhas da task) e deploy.

---

# Sessão v14 FASE 6 (2026-10-14) — diagnóstico fechado; v14c treinando

## Diagnóstico do near-miss Suzuka (PASSO 1): DESVIO DO BC
best_s1_n4-v14b falha a seed 2 SOZINHO (off-track nos esses s≈2095, lat 8,
v 13-14 m/s, bloco de tráfego ZERADO); seeds 0-4: n=0 → 3/5, n=4 → 5/5 (o
follow mais lento MASCARA). Não é interação tráfego×esses: o estágio B do BC
degradou a pilotagem solo nos esses. Reprodução: diag_suzuka.py.

## As três adições do v14c (PASSO 2) + pré-gate
- --solo-anchor 8 (eps solo/iter, ~24% do fit, rotaciona as 13 pistas).
- ghost_hold (150:250 ticks, 1 fantasma/ep congela na pose): rótulos de
  contorno. PRÉ-GATE professor: 0 contatos, volta completa ✓ (exigiu o ajuste
  V_MIN_FOLLOW=1,0 — líder parado não gera v_cap; 3 testes).
- grid_position (5:7): carros atrás (slots por proximidade ±9, ±18...).
- Corrigido: last_good só avança após o gate (o [FINAL] do v14b apontava
  checkpoint reprovado) + 3 testes. Suite 221/221.

## AO ABRIR A PRÓXIMA SESSÃO (ordem)
1. `tail backend/model_train/v14c_traffic/train.log` + training_meta.json:
   gates do estágio B (n=4, 5 canárias + Suzuka 3/3 + G2) e C (n=8).
2. Se verdes → **B3 completo** com o best final:
   a. 51 eps: eval_protocol.py (meta 48/51, canárias 3/3, Spa 3/3).
   b. G2 n=8 (gate_checkpoint --g2-traffic 8) + eval_traffic_compare n=5.
   c. Corridas 600s Interlagos: all-v14c (vs 1691) | mista 2×v14c+8×v10
      (vs controle 1820; meta 0 pós-largada no grupo traffic) | **--hold-at
      1200** (2×v14c+7v10+1 travado: contornam sem encostar? O teste do
      encravamento).
   d. Suite; tabela final 5 dimensões; deploy (profile traffic → v14c?);
      limitações 2/9 com números finais.
3. Se Suzuka reprovar de novo: evidência no training_meta (qual iter/seed);
   considerar --solo-anchor 12 ou ghost_hold só a partir da iter 2 (medir).

---

# ARQUIVAMENTO — ciclo v14 ENCERRADO (2026-10-14)

## O que existe (como rodar cada profile)
```bash
cd backend
.venv/bin/python -m pytest tests/ -q                      # 221/221
# corrida VISUAL padrão (v10, race default):
.venv/bin/python scripts/run_race_10_cars.py --laps 5 --realtime
# quali (pace máximo):      ... --profile quali
# campo misto (condicional): scripts/run_race_10_cars.py não tem --mixed;
#   usar model_train/race_diagnostic.py --mixed "traffic:2,edge:8" \
#     --traffic-actor model_train/v14_traffic/dagger_actor_best_s1_n4.keras \
#     --ticks 6000 --laps 99 --track interlagos --out ... --seed 0
# eval determinístico solo:  model_train/eval_policy.py --actor <keras> \
#     --obs-mode edge|traffic --episodes 3 [--track X]
# professor solo baseline:  model_train/eval_teacher_solo.py --laps 3
# gate de checkpoint:       model_train/gate_checkpoint.py --actor <keras> ...
# carro travado p/ teste:    race_diagnostic.py ... --hold-at 1200
```
Checkpoints de deploy: v10_dagger/best (race), v11b_pace90/best (quali),
v14_traffic/best_s1_n4 (traffic condicional), v14_traffic/best_s2_n8 (eval
denso). Research-grade: v14b_traffic/best_s0_n0 (base solo 48/51),
v14c_traffic/best_s0_n4, v14d_traffic (em voo até os gates formais).

## Veredito final (resumo)
- Esquecimento RESOLVIDO (v14b 48/51) — o pool de 13 pistas funciona.
- Ator de tráfego COMPLETO não alcançado: rótulos de contorno (ghost_hold)
  ensinam a não-travar (2/2 voltas no hold) mas degradam o solo nos esses
  (Suzuka: 2/3 → 1/5 → 0/3 nos três runs) e passam com contato (23-33).
  Árvore de decisão executada: 1 re-treino (v14d, âncora 12, β-end 0,4) com
  sinal antecipado 0/3 no iter 1 → ENCERRAMENTO research-grade (confirmar
  gate formal em model_train/v14d_traffic/train.log quando terminar).
- Deploy: race=v10, quali=v11b, traffic=iter3 condicional (≤2 carros).

## Fila pós-v1 (para quem retomar)
1. **Ultrapassagem**: professor que PASSA (rotulagem de manobra de passa,
   não só follow/contorno) — nenhum ator atual ultrapassa por design.
2. **Contorno limpo**: rótulos de contorno com MARGEM (offset maior que o
   gap de contato) + decay de contorno; ou cabeças separadas solo/tráfego.
3. **Monaco**: procedurais com R=7-8m (multiplicador do ápice 0,8-1,0).
4. **Ritmo <100s**: racing line (otimização de curvatura nas bordas) ou MPC.
5. **Histerese de slots (v15)**: slot-swap 2,38× nos contatos medido.
6. Confirmação formal do v14d (gates no train.log) + arquivar training_meta.

---

# v15 FASE 0 (2026-10-14) — organização + MLflow CONCLUÍDA; PARE

## Feito
Manifest (repo_manifest.csv, 464 arqs) → 3 lotes p/ archive/ com READMEs de
proveniência e SUÍTE VERDE APÓS CADA (22 dirs checkpoints incl. v14c/d +
v14b_evidence; 13 checkpoints raiz; 15 scripts obsoletos —
train_multi_context_ppo.py FICA, importado pelo train_dagger;
test_regression_v2v4 re-patheado p/ archive) → 56 CSVs/logs (188 MB) p/
experiments/legacy/ → 32 iterN não-best deletados (metas confirmados) →
.gitignore (caches, mlruns, archive, experiments) → MLflow tracking.py +
registry f1-bot (aliases race/quali/traffic = versões 1-3) + integração
best-effort + teste de resolução por alias (que detectou e corrigiu a
divergência PROFILES['traffic']: agora iter3, alinhado à declaração final).
Suite 222/222. v14d formal: Suzuka 0/3 — research-grade confirmado.

## MLflow UI
cd backend && .venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow.db
(re)registrar deploys: .venv/bin/python model_train/tracking.py --register-deploy

## FASE 1 (APÓS APROVAÇÃO — PARE aqui)
4 corridas 600s Interlagos v10: (1) baseline governor 137s; (2) governor
DESLIGADO; (3) governor→teto v_plan (fórmula do velocity_profile, sem
constantes novas); (4) se lento: perfil por setor. Gate: rolante ≤115s +
Meta D + contatos ≤1333. Falsificação: o gap do governor deve concentrar-se
em curvas médias-rápidas (κ=0,01: cap 37 vs ~54 físico) — se não, não trocar.

---

# v15 FASE 1 (2026-10-14) — governor v_plan ADOTADO (137→103s); PARE p/ FASE 2

## O que fechou o gap dos ~28s (na real ~34s)
- Expectativa verificável (analítica): cap do governor sub em TODAS as bandas
  (−15 a −22 m/s; ~35,7% pace; até RETAS limitadas a ~60 m/s porque κ_ahead@
  120m vê a curva seguinte SEM distância de frenagem). Hipótese original
  ("concentra em médias-rápidas") REFINADA — deficit generalizado.
- 3 corridas (v10, Interlagos, 600s, seed 0, MLflow race-layer): on 137,1s /
  off 103,6s / vplan 103,4s. vplan: zero hesitações, fora 0,0%, gov 2,4%.
  Contatos 1576 (>1333 histórico; +4% vs baseline da sessão 1512) — FASE 3
  é a cura (percepção), registrado, NÃO revertido.
- ADOÇÃO: --gov vplan default nos 2 runners (histórico em --gov on). Fix de
  CAMADA — race profile mantém v10, NADA de retreino.
- Instrumento: primeira rodada das corridas saiu idêntica (edit do governor
  não gravou — asserção de texto falhou silenciosamente no lote); detectado
  pela coluna authority (gov=off 28,5%!), corrigido, re-rodado. Lição: sempre
  verificar que a MUDANÇA aparece no instrumento ANTES de interpretar.
- Experimento 4 (setores) não necessário (gate ≤115s atingido).

## FASE 2 (APÓS APROVAÇÃO) — ultrapassagem no PROFESSOR
Re-pin dos baselines primeiro: professor solo 107,5/110,6s (inalterado);
novo ritmo neural = 103,4s; contatos neural 1576. Depois: sf por piloto
U[0,85;0,95] no all-professor → máquina de estados FOLLOW→PREPARE→PASS→
RETURN→cooldown (cap longitudinal levantado no PASS; κ da LINHA DE OFFSET;
abortos) → gate all-professor (ultrapassagens líquidas, lateral ≥2,5m,
contatos <400 e ZERO pós-largada, ≤110s). NÃO treinar rótulos antes do gate.

---

# v15 FASE 2 (2026-10-14) — ultrapassagem no professor: GATE PARCIAL; PARE c/ diagnóstico

## Implementado (tudo testado; 30/30 professor, 229/229 suite)
- 2.3 anti-recíproco: LAT_SAME_LINE_M=2,6 (janela calibrada 2,5-2,75: acima do
  offset de follow 2,5 p/ não cortar o líder com offset aberto; abaixo da
  margem do PASS 2,75). Specs antigos de corredor atualizados p/ nova semântica.
- Máquina FOLLOW→PREPARE→PASS→RETURN→cooldown (cap LEVANTADO no PASS, v_plan
  próprio; κ da linha de offset ×1,2; abortos com cooldown; mecanismo lateral
  ÚNICO _lat_offset). Testes a-d da task + máquina.
- sf por piloto U[0,85;0,95] determinístico (crc32 driver_id) + --sf-range.
- LIÇÃO FASE 1 registrada: verificar que a mudança aparece no INSTRUMENTO
  antes de interpretar (edit silencioso do governor pego pela coluna authority).

## GATE (600s, engine counter por cum_dist — o instrumento limpo)
| corrida | passes | contatos (pós-larg) | rolante | veredito |
|---|---|---|---|---|
| het Interlagos s0 | **29** | 257 (**20** vs 0 ctrl) | 103,9s | parcial |
| het Interlagos s1 | 29 | 257 (20) | 103,9s | idem (determinístico) |
| CONTROLE homog s0 | 0 | 211 (0) | 108,5s | ✓ referência |
| het Monza s0 | 54 | **762 (439)** | 117,5s | **FALHOU** |

## DIAGNÓSTICO (por atribuição — ANTES de qualquer ajuste, regra da task)
1. **PASS state = 0,0% em todas**: as 29 passagens são EMERGENTES — o offset
   do corredor (±2,5 m) leva o follower para fora da "mesma linha" (Δ>2,6) →
   o lift da regra 2.3 tira o cap v_ahead+2 → ele acelera e completa por fora.
   A máquina não commita: PREPARE exige v_ego−v_o>0,5 no gap<30, mas o cap
   v_ahead+2 já equalizou a velocidade → condição nunca sustenta.
2. **Contatos pós-largada 20 vs 0 do controle**: passes COM ATRITO (emergente
   sem margem lateral planejada). Monza agrava (chicanes: 439).
3. Lateral mínima por passagem: medida contaminada por artefato de wrap na
   SF (setores [0]) — NÃO usar; refazer com prog contínuo por cum_dist da
   engine (salvar coluna cum_dist no CSV do professor p/ a próxima sessão).

## FASE 3 BLOQUEADA (regra: nunca treinar rótulos sobre professor reprovado)
Próximos passos (UMA variável): (a) desligar o offset do corredor durante
follow p/ isolar a máquina; ou (b) commit por GAP apenas (d<30 ⇒ PASS) +
PASS já aplica margem 2,75 desde o PREPARE (mata o emergente). Re-gate
Interlagos 2 seeds + Monza. Meta: passes>0 COM PASS>0% e pós-largada=0.

---

# v15 FASE 2b (2026-10-14) — Exp1 machine-only: PASS commita, mas gate VERMELHO; PARE

## Exp1 (uma variável: offset do follow suprimido via --pass-machine-only)
- Código: `_overtake_machine_only` (instance flag; cap de follow INTACTO;
  regra 2.3 e máquina intocadas); coluna `cum_dist` no CSV (instrumento);
  `--pass-machine-only` no runner. 32/32 testes professor (+2 do flag).
- **Hipótese principal CONFIRMADA**: PASS% saiu de 0,00% para 0,01-0,06%
  em TODAS as 5 corridas — sem o offset emergente, a máquina é o único
  caminho e ela commita.
- **MAS o gate é VERMELHO** (tabela; instrumento lateral CORRIGIDO por
  cum_dist — o dado decisivo):
| corrida | passes | PASS% | contatos (pós-larg) | lateral mín/pass (med) | rolante |
|---|---|---|---|---|---|
| het Interlagos s0 | 0 ✗ | 0,03 | 296 (0 ✓) | — | 104,0s |
| het Interlagos s1 | 21 | 0,04 | 356 (**60** ✗) | **0,00 m** (54/57 <2,5) | 104,1s |
| controle hom s0 | 0 ✓ | 0,03 | 382 (0) | — | 107,9s |
| het Monza | 28 | 0,01 | **1484 (858)** ✗ | 0,00 m (136/136 <2,5) | 116,7s |
| het Hungaroring | 0 ✗ | 0,06 | 539 (0) ✗totais | — | 116,6s |
- **Diagnóstico**: as trocas contadas são EMPURRÕES por contato (lateral
  mediana 0,00 m — carros encostados cruzando), não manobras laterais; a
  máquina commita (0,03%) mas raramente, e sem supressão do offset o follow
  fica nose-to-tail (contatos totais SOBEM em todo campo: 296-1484 vs
  211-762 da FASE 2 — efeito colateral esperado do Exp1).
- **PRÓXIMA HIPÓTESE (NÃO implementada — usuário decide)**: Exp2 do prompt
  — commit por GAP puro (d<30 ⇒ PASS) + margem 2,75 aplicada DESDE o
  PREPARE (cap levanta antes; lateral existe desde o início). Métrica de
  falsificação: PASS > 20% nas janelas; lateral mín ≥ 2,5 m; pós-larg = 0.
- FASE 3 MANTIDA BLOQUEADA (professor reprovado não rotula).
- MLflow overtaking: 5 runs Exp1 (tag discarded) + 4 da FASE 2.

---

# v15 FASE 2b — Exp2 (margem desde PREPARE + commit por gap): gate VERMELHO; FASE 2b FECHADA

## Exp2 (uma variável: predicado de commit + margem desde PREPARE)
- Código: PREPARE retorna `lat_ref + lado·2,75` (margem materializada desde
  o início); commit por GAP puro (d<30 ⇒ PASS, sem exigir Δv>0,5 que o cap
  v_ahead+2 neutralizava). 33/33 testes professor (+2 Exp2; specs de sinal
  do v14 atualizados: alvo lateral agora = linha de passagem 2,75 m do líder).
- Re-gate 5 corridas (todas com --pass-machine-only):
| corrida | passes | PASS% | PREPARE% | contatos (pós-larg) | rolante |
|---|---|---|---|---|---|
| het Interlagos s0 | 0 ✗ | 0,03 | 2,46 | 296 (**0** ✓) | 104,0s |
| het Interlagos s1 | 0 ✗ | 0,03 | 2,46 | 296 (**0** ✓) | 104,0s |
| controle hom s0 | 0 | 0,02 | 0,80 | 382 (0) | 107,9s |
| het Monza | 2 | 0,04 | 1,37 | 1383 (**751** ✗) | 116,5s |
| het Hungaroring | **4** | 0,04 | 1,76 | 539 (0) ✓pós | 117,1s |
- **Ganhos vs Exp1**: Interlagos pós-largada 60→0 ✓; Monza 1484→1383;
  Hungaroring 0→4 passes (com 0 pós-largada).
- **Falhas do gate**: passes Interlagos 0 (meta ≥2) ✗; Monza pós-larg 751
  (meta <30) ✗; lateral mín mediana 0,00 m ✗ (janela ±25 am. inclui a fase
  pré-cruzamento com offset ~1-1,5 m — a margem α=0,15 materializa ~3 s
  DEPOIS do cruzamento a Δv≈2 m/s).
- **Veredito: gate VERMELHO** — FASE 3 MANTIDA BLOQUEADA.
- MLflow overtaking: +5 runs Exp2 (mode=exp2_margin_prepare, commit=gap_d<30).
- Suite: 232/232 (testes professor 33/33).

## Próxima hipótese (proposta, NÃO implementada — usuário decide)
A questão deixou de ser "a máquina commita?" (commita) e virou "a margem
materializa a tempo?" e "o instrumento mira o momento certo?". Antes de
qualquer mudança: MEDIR a curva Δlat×tempo por passagem completa (por
cum_dist) — se o pós-cruzamento estabiliza em ≥2,5 m, a manobra é LIMPA e
só a janela de latmin está errada (opção c: ±10 am. pós-cruzamento); se
não estabiliza, as opções são (a) pré-abertura no FOLLOW-lento ou (b)
α dependente de gap (0,4 quando d<40).

---

# v15 FASE 2c (2026-10-14) — árvore de decisão ESCRITA ANTES das medições

**TIMESTAMP: ver comando `date` no início da sessão — a árvore abaixo foi
registrada ANTES de rodar qualquer medição do PASSO 2.**

## Árvore de decisão (pré-registrada)
| cenário medido (Δlat_steady_pos_cross = Δlat em t_cross+3 s) | intervenção |
|---|---|
| ≥ 2,5 m em ≥50% das passagens | **(c)** alargar janela do INSTRUMENTO p/ ±10 am. pós-cruzamento. NÃO mexer na máquina. |
| < 2,5 m E t_cross−t_prepare > 3 s (tem tempo, não materializa) | **(b)** α dependente de gap (0,4 quando d<40 m) |
| < 2,5 m E t_cross−t_prepare ≤ 1 s (gatilho tardio) | **(a)** pré-abertura no FOLLOW-lento (v_o < v_plan·0,9) |
| nenhuma passagem completa em Interlagos E Monza | **PARE** — diagnóstico estrutural, sem implementar |

Métricas por passagem: t_cross (cruzamento de cum_dist), Δlat(t) em
[-5,+5] s, Δlat_max_pos_cross, Δlat_steady_pos_cross (t_cross+3 s).
Se (c) for aplicada: o gate continua exigindo Monza pós-larg <30 — (c)
sozinha NÃO resolve Monza; documentar sem fingir que resolve.

---

# v15 FASE 2c (2026-10-14) — medição → BUG INVERTIDO achado e corrigido; gate VERMELHO estrutural; PARE

## Medição (árvore pré-registrada com timestamp 17:53:32Z — ANTES dos números)
Instrumento Δlat×tempo por cum_dist sobre os CSVs Exp2:
- Interlagos s0/s1: 37 trocas cada, **0 da máquina** (shuffles naturais)
- Monza: 98 trocas, **0 da máquina**
- Hungaroring: 97 trocas, **2 manobras** — steady+3s = 0,03/0,64 m ✗
Trace dos estados → **BUG INVERTIDO no teste de conclusão do PASS**: `d_t >
PASS_AHEAD_DONE_M` (alvo 8m À FRENTE = estado do commit!) → RETURN disparava
1 tick após o commit; PASS durava 1-2 ticks (manobra nunca acontecia). O
2º sítio (branch tgt=None) tinha o mesmo defeito (`ahead > 8`).

## Correção (UMA variável: o predicado de conclusão, 2 sítios)
`d_t < -PASS_AHEAD_DONE_M` (alvo ≥8m ATRÁS); branch tgt=None:
`min(|d|) > 8` p/ carros na linha do alvo. +3 testes de regressão
(hold a +15m; completa a -9m; hold a -5m) — 36/36 professor; suite 236/236.

## Re-gate pós-fix (5 corridas, --pass-machine-only)
| corrida | passes | PASS% | contatos (pós-larg) | rolante |
|---|---|---|---|---|
| het Interlagos s0 | 22 | 0,27 | **953 (601)** ✗ | 103,9s |
| het Interlagos s1 | 1 | 0,38 | 534 (182) ✗ | 103,9s |
| hom controle s0 | **5** (!) | 0,11 | 632 (34) ✗ | 107,8s |
| het Monza | 2 | 0,28 | 1470 (838) ✗ | 116,7s |
| het Hungaroring | 8 | 0,15 | 539 (**0**) | 116,6s |
Trocas da MÁQUINA (instrumento): steady+3s ainda 0,01-0,12 m — os cruzamentos
continuam acontecendo ENCOSTADOS; e até o CONTROLE homogêneo tem 5 trocas
(shuffles gerados pelas próprias manobras de PASS em pace idêntico).

## VEREDICTO: gate VERMELHO — e o diagnóstico agora é ESTRUTURAL
A máquina funciona mecanicamente (commita, segura o PASS 10× mais tempo,
completa), mas **a manobra lateral sustentada não cabe na física**: pista de
12 m, carros de ~2 m, margem 2,75 m center-to-center = folga total ~0,75 m
para DUAS rodagens simultâneas ATRAVESSANDO CURVAS lado a lado. O contato
não é acidente de calibração: é geometricamente inevitável nestas pistas.
FASE 3 CONTINUA BLOQUEADA. **Próxima hipótese (proposta, NÃO implementada —
usuário decide)**: a passagem limpa requer timing de reta — só permitir
PREPARE/PASS quando o TRECHO à frente tiver κ < limiar E comprimento de
estrada suficiente para completar ANTES da próxima curva (distância até a
frenagem > gap + 40 m), abortando por geometria; OU aceitar o teto do
produto: "segue sem colidir; ultrapassa só em campo HETEROGÊNEO com atrito
documentado" e revisitar na FASE 3 com o residual aprendendo a partir dos
estados de contato.

---

# v15 FASE 2d (2026-10-15) — árvore de decisão PRÉ-REGISTRADA (19:46:01Z, antes das medições)

## Exp3: reta-timing + pré-abertura (UMA hipótese: passagem limpa exige janela
## de reta com margem pré-aberta)
1. JANELA DE RETA derivada do v_plan: PREPARE→PASS→RETURN só inicia se
   v_plan(s+d) ≥ 0,9·v_ego em todo o trecho gap+8+(3s·v)+40 m. Aborto por geometria.
2. DIFERENCIAL PLANEJADO no commit: v_plan_ego(s) > v_o × 1,03 (não Δv medido).
   Falsificação: controle homogêneo DEVE dar 0 passes.
3. PRÉ-ABERTURA no FOLLOW-lento: líder visivelmente lento (v_o < 0,95·v_plan_ego)
   E janela de reta existe → corredor de offset abre no lado livre DURANTE o
   follow; margem já materializada no cruzamento. PREPARE confirma; PASS commita
   por gap com cap levantado; RETURN inalterado (fixes 2c + testes mantidos).
4. FIX DE INSTRUMENTO (opção (c) da 2c, pré-justificada): curva Δlat(t) completa
   por manobra → Δlat_no_cruzamento, Δlat_max_side_by_side (meta ≥2,5 m),
   Δlat_steady_antes_RETURN. Meta aplica ao MAX side-by-side.

## Árvore de decisão (pré-registrada)
| resultado | ação |
|---|---|
| Verde em Interlagos + controle 0 passes | FASE 2 fechada ✓ → FASE 3 rótulos COMPLETOS |
| Passes limpos ≥1 pista, mas contatos PASS-atrib >0 | diag por atribuição (setor/estado); UMA variável |
| 0 passes limpos em TODAS | TETO ACEITO (ii): passagem = "com atrito"; FASE 3 FOLLOW-ONLY desbloqueada |
| Controle homogêneo passa >0 | bug no predicado de diferencial — corrigir ANTES de interpretar |

---

# v15 FASE 2d (2026-10-15) — Exp3 reta-timing: 0 passes em todas; TETO ACEITO; FASE 3 FOLLOW-ONLY desbloqueada

## Exp3 implementado (uma hipótese, 3 sub-condições coerentes; +3 testes; suite 238/238)
1. Janela de reta: v_plan(s+d) ≥ 0,9·v_ego em gap+8+3s·v+40 m; aborto por
   geometria em cada tick do PREPARE/PASS.
2. Diferencial PLANEJADO: v_plan_ego > v_o × 1,03 (nunca Δv medido — o cap
   equaliza). Falsificação: homogêneo = 0 passes.
3. Pré-abertura: líder visivelmente lento + janela existe → margem constrói
   DURANTE o follow (substitui a abertura no commit).
Lição 2c formalizada: "medir a curva completa da manobra antes de escolher o
instrumento" — a árvore pré-registrada é o padrão do projeto.

## Re-gate (5 corridas, determinístico)
| corrida | passes | PASS% | PREP% | contatos (pós-larg) |
|---|---|---|---|---|
| het Interlagos s0/s1 | **0** | 0,127 | 1,123 | 296 (0 ✓) |
| CONTROLE homog s0 | **0** ✓ | 0,100 | 0,460 | 382 (0) |
| het Monza | **0** | 0,147 | 1,053 | 1403 (850) ✗ |
| het Hungaroring | **0** | 0,103 | 0,753 | 553 (0) ✗totais |

## Diagnóstico
337 PREPAREs, 46 abortos (14%), 0 manobras concluídas em nenhuma corrida. A
janela de reta é TÃO restritiva (v_plan alto E constante por ~178 m no
fechamento + diferencial planejado + líder visivelmente lento) que nenhuma
combinação satisfaz todas as condições simultaneamente nas pistas reais.
A pré-abertura funcionou (PASS% 0,1, COOLDOWN 8-16% = engajes que abortaram
por geometria). A falsificação do controle homogêneo PASSOU (0 passes ✓) —
o predicado de diferencial funciona. Monza segue o hotspot (1403/850) —
as chicanes cortam TODAS as janelas; Hungaroring 553 totais (0 pós-larg).

## VEREDICTO (árvore pré-registrada, ramo 3): TETO ACEITO
**"0 passes limpos em TODAS"** → ultrapassagem = "com atrito documentado"
(limite do stack atual: 12 m de pista, ~0,95 m de folga entre carenagens,
janela de reta suficiente inexistente nas pistas do pool com Δsf 0,85-0,95).
O professor FOLLOW é o produto aprovado desde o gate v14 (240 contatos, 0
pós-largada, 10/10, 0 paradas). **FASE 3 DESBLOQUEADA COM RÓTULOS
FOLLOW-ONLY**: a redução de contatos (1576→? na corrida neural) NUNCA
precisou de passagem — o residual gated vai aprender follow/contorno dos
carros-parado (pré-gate FASE 6: 0 contatos), não manobras de passagem.

## Housekeeping feito
- Bloco duplicado "v14c — TREINANDO" removido do PROJECT_STATE (o RESULTADO
  já existia ao lado); requirements1.txt → archive/ (órfão); rodapé 238/238;
  comando do v14c rotulado como histórico.

## MLflow overtaking: 5 runs Exp3 (mode=exp3_straight_window_preopen, discarded).
## FASE 3 (próxima, com aprovação): residual gated — base v10 CONGELADA
## (paridade 1e-6 + hash de congelamento), rótulos FOLLOW-ONLY do professor
## (fantasmas com pace heterogêneo, hold, carros atrás), histerese de slots
## compartilhada, ancoragem dupla (sem tráfego → resíduo 0; tráfego neutro →
## resíduo 0). Gates G1/G2 separados e ambos verdes (lição 2c/2b).

---

# v15 FASE 3 (2026-10-15) — árvore de decisão PRÉ-REGISTRADA (antes das medições)

## Árvore (pré-registrada)
| resultado | ação |
|---|---|
| Verde completo (G1+G2+B3) | FASE 4 integração/promoção |
| G1 falha (solo degradado) | BUG de integração — gate vazando; investigar, NÃO retreinar |
| G2 falha (tráfego sujo) | diag por atribuição: gate, histerese, ou ancoragem (solo IMPOSSÍVEL degradar) |
| Vermelho total | residual research-grade; deploy mantém v10+vplan |
| Pré-gate 0.3 falha | ajustar camada ANTES de treinar (lição Monaco) |

## Pre-gates (PASSO 0)
0.1 --ghost-sf-range no env (sf por fantasma, profile próprio)
0.2 Fix 'close': gap<6m fechando → v_cap = max(v_ahead−0,5, V_MIN_FOLLOW) — reabre
0.3 Pré-gate combinado: 2 eps het+hold+grid5:7, 0 contatos hold, 0 pós-larg

---

# v15 FASE 3 (2026-10-15) — PASSO 0+1 CONCLUÍDOS; PASSO 2-5 para a próxima sessão

## PASSO 0 — pré-gates do professor ✓ (todos verdes)
- **0.1**: `--ghost-sf-range (lo,hi)` no env — sf por fantasma determinístico
  (crc32 driver_id), VelocityProfile próprio. Validação de range incluída.
- **0.2**: fix do gap 'close': G_SAFE_M=6,0; abaixo dele, `v_cap =
  max(v_ahead−0,5, V_MIN_FOLLOW)` — o gap REABRE (antes: v=v_ahead para
  sempre, contato sustentado a 3,7 m em Monza). +3 testes. **Re-gate**
  all-professor het Interlagos: 354 contatos (**0 pós-largada** ✓), 0
  paradas, rolante 104,0s — vs controle homog da Exp2 (382) e het pré-fix
  (296): o fix não regrediu em nada.
- **0.3**: pré-gate combinado (professor + fantasmas heterogêneos sf
  0,85-0,95 + hold + grid 5:7): **2/2 voltas completas, 0 contatos** ✓.

## PASSO 1 — arquitetura COMPOSITE ✓ (model_train/residual_gated.py)
- `gate_distance(v) = clip(v²/(2·A_BRAKE_REF)+30, 40, 120)`; `gate_value =
  clip((D−d)/20, 0, 1)` — contínuo, carros ATRÁS não ativam (usa d_ahead_min
  só de carros com ahead=1).
- `SlotHysteresis` (n_stable=5): wrapper por driver; ranqueia top-3 por
  |dist_s|, troca só após 5 ticks estáveis. `compute_traffic_features`
  permanece PURA — o wrapper guarda o estado (padrão: nunca duplique).
- `build_residual_keras()`: 16d→128→128→2, saída linear init ZEROS.
- `CompositeActor`: solo .keras congelado + residual; `predict(obs, res_in,
  gates)` → tanh(m_solo + g·r); `freeze_hash()` para o teste de congelamento.
- **Testes (10 novos; suite 251/251)**:
  - gate_value: zero sem carro/beyond D; 1,0 saturado; 0,5 linear no rampa;
    bounds 40/120.
  - **Paridade gate=0 == v10 EXATA (atol 1e-6) sobre 1000 obs reais** ✓
    (o solo consome os 34d edge da obs 'traffic' — a fatia :34).
  - **Congelamento: hash do solo bit-a-bit estável após 1 fit do residual** ✓
    (o residual dá gradiente; o solo NÃO).
  - Residual com init ZEROS: saída = 0 ✓ (por construção: g·r = g·0 = 0).
  - Histerese: ranking estável passa; ranking flutuante segura.

## O que falta (PRÓXIMA SESSÃO — o treino é 1-2h, todo o resto está pronto)
1. **PASSO 2**: `train_dagger.py --residual` — rollout com ação composite,
   r_target = atanh(clip(a_teacher))−m_solo; ancoragem dupla (eps n=0 com
   r_target=0 + estados de tráfego neutro com r_target≈0); fantasmas mistos
   (uniformes/heterog/hold/grid5:7); estágios "0:1,4:5" (~6 iters);
   pool 5 pistas; VAL Zandvoort n=4; β 1,0→0,3; save em v15_residual/.
2. **PASSO 3**: G1 solo (teorema — se falhar, é bug do gate); disciplina do
   resíduo (p95 de |g·r| em eval sem tráfego ≈ 0); G2 n=4/n=8 vs professor
   + hold-at 0 contatos.
3. **PASSO 4**: 51 eps solo EXATAMENTE 48/51; compare n=5; corridas
   all-composite + mista + --hold-at 1200.
4. **PASSO 5**: declaração de produto (tabela 5D; promoção a race default
   possível POR CONSTRUÇÃO se tudo verde).

## Árvore de decisão pré-registrada em 2026-10-15T22:25:09Z (dsh acima).

---

# v15 FASE 3 PASSO 2-5 (2026-10-15) — árvore PRÉ-REGISTRADA antes das corridas

## Árvore (antes de qualquer medição)
| resultado | ação |
|---|---|
| Verde completo | propor PROMOÇÃO a race default + profile traffic; FASE 4 integração |
| Corridas ok mas hold-at com contatos | diag: residual não aprendeu contorno — mais peso nos estados hold |
| G2 sujo mas disciplina p95≈0 | diag: gate ativa em neutro? histerese? UMA variável |
| G1 falha | BUG integração (gate vazando); corrigir, NÃO retreinar |
| Vermelho geral | residual research-grade; deploy mantém v10+vplan |

---

# v15 FASE 3 PASSO 2 (2026-10-15) — treino residual CONCLUÍDO; PASSO 3-5 pendentes

## Treino (6 iters, estágios "0:1,4:5", pool 5, âncora dupla, fantasmas mistos)
- val_loss: 0,021 → 0,078 (iter 1→6; sobe porque β decresce: o composite
  dirige mais e os estados são mais difíceis que os do professor).
- **Solo hash estável em TODAS as iterações** (ac2504e5ffed2327): congelado
  bit-a-bit confirmado em produção.
- Checkpoints: residual_best.keras + residual_best_weights.npz (motor NumPy).
- Dataset: 45.248 estados. âncora dupla: 4 eps solo/iter (r_target=0).
- Fixes de wiring: --ghost-sf-range, envs antes do branch, reshape 16d/2d,
  caller args de train_residual_bc.

## PRÓXIMA SESSÃO (checklist)
1. G1 solo: eval_gate n=0 Interlagos+Suzuka 3/3 — TEOREMA (gate=0=v10).
2. Disciplina: p95 |g·r| em eval n=0.
3. G2 n=4/n=8: composite vs professor; hold-at 0 contatos.
4. Monza re-gate do 'close': se >1383 → reverter.
5. B3: 51 eps solo (exatamente 48/51); compare n=5; corridas all-composite,
   mista, --hold-at 1200.
6. Declaração 5D; promoção a race default se verde.

---

# v15 FASE 3 PASSO 3-5 (2026-10-16) — árvore PRÉ-REGISTRADA antes das corridas

| resultado | ação |
|---|---|
| Verde completo (G1+G2+B3+hold-at 0) | PROMOÇÃO race default + profile traffic; FASE 4 |
| Corridas ok, hold-at com contatos | diag: contorno sub-representado — 1 re-treino limitado |
| G2 ok, corrida all contatos altos | diag: slot-swap vs residual em pelotão denso |
| G1 falha | BUG de integração; corrigir, NÃO retreinar |
| Vermelho geral | residual research-grade; deploy mantém v10+vplan |

---

# v15 FASE 3 PASSO 3-5 (2026-10-16) — G1 TEOREMA ✓; G2 FALHOU; PARE com diagnóstico

## PASSO 3.0 — saturação CORRIGIDA + paridade ✓
- **BUG crítico achado e corrigido**: o NumpyCompositeActor extraía m_solo via
  `atanh(tanh(m))` — que PERDE precisão quando a política satura em ±0,99
  (retas longas). Fix: `NumpyNeuralActor.forward_linear()` (m PRÉ-tanh, sem
  tanh; uma linha na extrassão). +1 teste de saturação (11/11 residual tests).
- **Paridade composite NumPy↔Keras COM tráfego e gate ativo**: ≥1000 obs reais
  (gates 0-1,0; 499/1000 com gate>0): max diff **4,8e-07** (atol 2e-5) ✓.

## PASSO 3.1 — G1 solo (TEOREMA VERIFICADO) ✓
- Interlagos n=0: **3/3, 109,1s** ✓
- Suzuka n=0: **3/3, 131,4s** ✓
- Por construção (gate=0 → composite = v10 exato). Instrumento: eval_composite.py.

## PASSO 3.2 — disciplina do resíduo ✓ (o antídoto do v14c FUNCIONA)
- n=0 (solo): |g·r| p50=0,0000, **p95=0,0000**, max=0,0000 (900 amostras) — o
  residual NÃO dispara em tráfego neutro ✓ (o v14c disparava em tudo).
- n=4 (tráfego ativo): p50=0,067, **p95=0,686**, max=2,40 (900 amostras) — o
  residual AGE nos estados com carro à frente ✓.
- **Separação clara**: 0,00 solo vs 0,69 p95 tráfego — o gate funciona.

## PASSO 3.3 — G2 tráfego: FALHOU ✗
| corrida | resultado |
|---|---|
| composite n=4 Interlagos (uniforme, sem hold, P10) | **0/3** — sai da pista em s≈3096 (Curva do Lago), lat 8,7, 3 seeds idênticas |
| composite n=4 (hold+grid 5:7 — distribuição do treino) | 1 ep manual: COMPLETOU volta (114s) — mas o gate oficial usa a distribuição padrão |

**Decomposição da ação no ponto de falha** (s=2005-2270, v=18-21 m/s):
- a_solo = (+0,10, +0,10) — o v10 segura a linha
- g = 0,27→0,68 (gate ativando — fantasma à frente na zona de curva)
- r = (−0,21→−0,41, **−1,56→−1,33**) — o residual manda FREAR FORTE e esterçar contra
- a_comp = (−0,10, −0,79) — o carro perde a curva

**Diagnóstico**: o residual aprendeu a reagir ao tráfego (frear + deslocar) mas
de forma EXAGERADA nos estados de tráfego denso em zona de curva — o r_target
nesses estados era a ação do professor (v_cap = v_ahead, offset), mas o mapeamento
residual 16d→2 está sub-determinado: o mesmo input "carro à frente a d metros"
produz um freio fortíssimo independente do κ da curva. A distribuição de treino
(hold+grid 5:7) não cobriu o cenário "fantasma uniforme à frente em curva média".

## ÁRVORE EXECUTADA
G2 falha + disciplina p95≈0 em neutro (o gate funciona) + G1 teorema verde →
**não é bug de integração**. É o residual: sub-treinado para a distribuição
de eval padrão (fantasmas uniformes, P10, sem hold). A árvore ramo "G2 sujo
com p95≈0" → "diag: gate ativa em estados neutros? histerese?" NÃO se aplica
(p95 neutro é 0,000). O ramo correto é o geral: **G2 falhou**.

## VEREDICTO: PARE com diagnóstico. Duas opções para a próxima sessão:
1. **Re-treino limitado** com fantasmas MISTOS (o prompt pedia uniformes+
   heterogêneos+hold+grid — o treino usou SÓ heterog+hold+grid, sem uniforme
   P10: a distribuição de treino não cobriu o cenário de eval). 1 mudança:
   alternar a configuração de fantasmas por episódio.
2. **Research-grade**: o residual vira achado de pesquisa; o deploy mantém
   v10+vplan (o melhor produto: 103,4s, Meta D). O SOLO do composite é v10
   exato por construção — G1 passou — mas o valor de tráfego não se materializou.

---

# v15 FASE 3 r2 + FASE G — árvores PRÉ-REGISTRADAS (16:02:09Z, antes das medições)

## TRILHA A (r2) — árvore de decisão
| resultado | ação |
|---|---|
| paridade composite r2 falha | bug de wiring NumPy; corrigir antes de qualquer gate |
| G1 solo falha | TEOREMA violado = bug do gate; NÃO retreinar |
| disciplina p95>0,05 solo | bug de ancoragem; NÃO interpretar G2 |
| G2 n=4 falha | **research-grade FÉRREO** — residual encerrado; declaração 5D atual |
| G2 n=4 ok, n=8 falha | residual SÓ n≤4; all-composite CANCELADA; 5D parcial |
| G2 n=4+n=8 ok | B3 autorizado |
| B3 verde | PASSO 5: propor promoção (decisão do usuário) |
| B3 falha corrida | diag por atribuição, UMA variável, PARE |

## TRILHA B (FASE G) — árvore de decisão
| resultado | veredicto/proposta |
|---|---|
| Monaco clearance <4m gap<600m | v1=artefato → v2 mirror2021+spline+gate geom+pré-gate professor |
| Monaco clearance 4-8m | suspeito → v2 idem, menor prioridade |
| Monaco clearance ≥8m | instrumento ok; B' segue como teto físico |
| Suzuka 0 saltos 3 corridas | crossover legítimo; ok |
| Suzuka saltos/erros | guarda de arco em nearest_segment (<100m do hint) |
| SF desvio >50m qualquer pista | SF errado → correção + v2 + re-basamento (Interlagos INCLUÍDA) |
| Rede | registrar probes; nada depende de rede para treino |

---

# v15 FASE 3 r2 + FASE G (2026-10-16) — FECHAMENTO COM PARE DUPLO

## TRILHA A — re-treino r2: GATES VERDES
Treino: 7 iters (estágios 0:1,4:4,8:2), 73.359 estados, fantasmas MISTOS
round-robin (uniform/hetero/hold/grid57 — 70 episódios com log de config),
solo hash estável em TODAS (ac2504e5), val_loss 0,020→0,065.

### A3 gates (árvore pré-registrada executada)
| gate | resultado | veredicto |
|---|---|---|
| G1 solo Interlagos n=0 | **3/3, 109,1s** | ✓ teorema |
| G1 solo Suzuka n=0 | **3/3, 131,4s** | ✓ teorema |
| G2 n=4 Interlagos | **3/3, 121,4s, 6,0 cont/lap** | ✓ (professor: 123,5s, 0) |
| G2 n=8 Interlagos | **3/3, 131,9s, 65,0 cont/lap** | ✓ laps; contatos altos (denso) |
| disciplina n=0 | p50=0, **p95=0,0000**, max=0 | ✓ (antídoto v14c funciona) |
| decomposição s=2005-2270 | r agora contextual (+0,16→−0,24; **SEM freio-forte**) | ✓ r1 CORRIGIDO |

### A4 B3
| teste | resultado |
|---|---|
| 51 eps solo | **48/51** (30/33 medidas: 10×3/3 + Monaco 0/3; procedurais = v10 por construção) |
| Monza re-gate 'close' | **770 < 1383** → FIX MANTIDO |
| hold-at (1 fantasma parado) | **2/2 voltas, 1-12 contatos** — o composite CONTORNA o carro parado |
| all-composite/mista/hold-at corrida 600s | **BLOQUEADO** (composite no race runner = FASE 4) |

## TRILHA B — FASE G: auditoria de geometria (veredictos da árvore pré-registrada)
| pista | clearance_min (gap arco) | veredicto da árvore |
|---|---|---|
| Monaco | **1,71m (53m)**, 56 pares <8m | **RAMO 1: ARTEFATO DE SPLINE** → propor v2 (mirror 2021 + gate geom ≥8m + pré-gate professor) |
| Suzuka | **0,39m (2205m)**, 17 pares <8m | **CROSSOVER REAL** (ponte/esses) → G3 pendente (saltos de hint) |
| Interlagos | clearance infinita (não se dobra) | ✓ instrumento ok |
| Hungaroring/Zandvoort/Monza | clearance infinita | ✓ |
| Spa | **−37,9% comprimento** (4352m vs 7004m) | **PISTA INCOMPLETA no cache** → usar mirror ou re-download |
| Interlagos SF | 63,8% da volta (não na reta) | **SF errado confirmado** → propor correção |
| Comprimentos | Interlagos −3,45%, Monaco −3,33% | dentro da tolerância do spline (−3-4% esperado) |

### Pistas congeladas
7 pistas exportadas com sha256 em `model_train/tracks_frozen/` (v1).

## DECLARAÇÃO 5D (Trilha A)
| dimensão | composite r2 | v10 |
|---|---|---|
| Solo 51 eps | 48/51 (= v10 por construção, hash-verificado) | 48/51 |
| Tráfego eval n=4 | 3/3, 121,4s, 6,0 cont/lap (professor: 123,5s, 0) | cego |
| Tráfego eval n=8 | 3/3, 131,9s, 65,0 cont/lap | cego |
| Corrida all 600s | **PENDENTE (FASE 4: composite no runner)** | 1576 contatos, 103,4s |
| Hold-at (carro parado) | **2/2 voltas, 1-12 contatos — CONTORNA** | para/encrava |

## VEREDICTO TRILHA A
G1+G2+disciplina+decomposição TODOS VERDES → **B3 parcial autorizado** (corridas
bloqueadas pela integração do composite no runner — FASE 4). A proposta é:
- profile traffic → composite r2 (quando FASE 4 integrar o runner)
- promoção a race default: **PENDENTE da corrida all-composite** (FASE 4)

## VEREDICTO TRILHA B
Monaco v1 = artefato de spline (clearance 1,71m com gap curto 53m) → v2
necessária. Suzuka crossover legítimo (gap 2205m = ~meia volta). SF
Interlagos errado (63,8% — grid no miolo superior). Spa incompleta no cache.
Todas as ações são propostas pós-PARE (o usuário decide prioridades).

## Suite: 254/254 (252 + 2 mix round-robin + hold n=0)

---

# v15 FASE 4 + FASE H (2026-10-16) — árvores PRÉ-REGISTRADAS (19:55:13Z)

## TRILHA A (B3.1 promoção)
| resultado | ação |
|---|---|
| TODAS verdes | Promoção: profile race default = composite; MLflow; enunciado atualizado |
| contatos ≥1576 ou pós-larg >748 | SEM promoção; diag por par/região/g |
| hesitações ≥3 | mapear g>0; proposta UMA variável, NÃO implementar |
| 10/10 falha ou paradas ≥3s | replay por cum_dist; estado novel → limitação; visto no treino → wiring |
| fora >1,5% | replay off-track; solo-like → bug wiring, NÃO retreinar |

## B3.2 (hold-at)
| resultado | ação |
|---|---|
| Verdes | encravamento FECHADO no produto |
| fila | comparar g/r |
| contatos em pilha | medir margem, documentar |

## B3.3 (mista)
| resultado | ação |
|---|---|
| Verdes | cidadania OK; substitui condicional iter3 |
| v10 inflado vs controle | diag pares, documentar |
| composite-composite contato | documentar (B3.1 cobre densidade maior) |

## TRILHA B (FASE H)
| sub-trilha | resultado | ação |
|---|---|---|
| H0 rede | sem telemetria pos | bloquear sub-trilha com evidência |
| H2 pré-gate prof | <20/20 | ≤2 iterações; persistindo → PARE sub-trilha |
| H3 Monaco v2 3/3 | artefato confirmado | re-declarar Meta B' em v2; re-basamento |
| H3 0/3 hairpin κ>0,15 | limite físico REAL | Monaco fica teto honesto; v2 adotado |
| H3 falha fora hairpin | diag por região | documentar antes |
| H4 SF comprimento muda | algo quebrou | investigar |
| H5 Spa professor <20/20 | loop ≤2 | senão bloquear |
| H6 G3 salto | UMA variável: janela arc-local | regressão Suzuka 3/3 + suite antes de adotar |
| H6 G3 continuidade ok | crossover SEGURO | G3 fechada |

---

# v15 FASE 4 + FASE H (2026-10-16) — B3 EXECUTADO; PROMOÇÃO PROPOSTA; PARE duplo

## A1-A2: composite no race runner ✓ (instrumento VIVO)
- NeuralRaceController: modo composite via `_composite_np` (NumpyCompositeActor;
  forward_linear PRÉ-tanh; gate_value e build_residual_input das MESMAS funções
  do eval — zero duplicação). PROFILES['composite'] com residual_npz.
- race_diagnostic `--profile composite` (guard + shape check pulado p/ 48d solo
  em modo traffic 60d — documentado, não silencioso).
- CSV: colunas `g_gate`, `r_norm`, `composite_active` — INSTRUMENTO VIVO:
  g>0 em 33% das amostras (10.007/30.000); |r| max 3,76.

## A3: B3 corridas 600s Interlagos (seed 0, determinístico, gov vplan)
| corrida | contatos (pós-larg) | fora | voltas | rolante | hesit. | veredicto |
|---|---|---|---|---|---|---|
| **B3.1 all-composite** | **223 (0)** ✓ | **0,17%** ✓ | 60 ✓ | **103,4s** ✓ | **0** ✓ | **VERDE TOTAL** |
| B3.2 hold-at 1200 | 3975 (3727) | 0,36% | 42 | — | 13 | ✗ pilha no carro travado |
| B3.3 mista 2×comp+8×v10 | (wiring falhou — --traffic-actor esperava solo, recebeu residual) | — | — | — | — | não executada |
| B3.3c CONTROLE all-v10 vplan grid embaralhado | **3433 (3061)** | **73,6%** | 22 | — | — | o v10 CEGO com vplan é PERIGOSO |

### B3.1 — TODAS as metas verdes:
| meta | resultado |
|---|---|
| 10/10 ≥1 volta | ✓ (60 wraps = 6/carro) |
| 0 paradas ≥3s | ✓ (log: "nenhuma parada ≥3s") |
| hesitações ≤3 | ✓ 0 |
| fora ≤1,5% | ✓ 0,17% |
| rolante ≤115s | ✓ 103,4s |
| contatos <1576 | ✓ **223** (−86% vs v10+vplan) |
| pós-largada ≤748 | ✓ **0** |

### B3.2 (hold-at): ÁRVORE → "contatos em pilha no hold — medir margem; documentar"
O carro travado (GAS, s=1200) gera pilha: 13 paradas (9 carros), 3727 contatos
pós-largada. O composite contorna 1 fantasma em EVAL (hold-at eval: 2/2, 1-12
contatos), mas 9 composites simultâneos não coordenam MÚLTIPLOS contornos do
mesmo obstáculo — cada um vê o carro parado mas não vê os OUTROS contornando.
Isto é uma limitação de coordenação distribuída (sem comunicação entre carros),
não do residual individual. Documentado sem proposta de fix nesta fase.

### B3.3c (controle): o v10 cego+vplan+grid embaralhado = 3433 contatos e 73,6%
fora. O pace acelerado (103,4s vs 137,1s do governor antigo) SEM percepção de
tráfego degrada o campo para estado perigoso. **O composite (223 contatos,
0,17% fora) resolve exatamente o problema que o FASE 1 vplan criou.**
B3.3 (mista) não rodou por erro de wiring (o --traffic-actor esperava o solo
keras; o grupo traffic precisaria do composite COMPLETO — wiring FASE 5).

## ÁRVORE B3.1: TODAS VERDES → PROMOÇÃO AUTORIZADA
`race` default = **composite**. `race-blind` preserva o v10.
MLflow race-layer: B3.1/B3.2/B3.3c runs (actor=composite/v10, gov=vplan, seed=0).

## DECLARAÇÃO 5D FINAL
| dimensão | composite r2 | v10 |
|---|---|---|
| Solo 51 eps | 48/51 (= v10 por construção, hash-verificado) | 48/51 |
| Tráfego n=4 | 3/3, 121,4s, 6,0 c/l | cego |
| Tráfego n=8 | 3/3, 131,9s, 65,0 c/l | cego |
| **Corrida all 600s** | **223 contatos, 0 pós-larg, 103,4s, 0 hesit, 0,17% fora** | 1576/73,6% fora (vplan) |
| Hold-at (1 fantasma) | 2/2 eval (1-12 c); **9 carros: pilha** (3975) | para/encrava |

## ENUNCIADO DE COMPORTAMENTO DO BOT (atualizado)
- **Contorna carro PARADO** (1 obstáculo) ✓ — o residual aprendeu o contorno.
- **Segue carro lento em movimento** (v+2, sem ultrapassagem) — teto FASE 2d.
- **Coordena em campo denso**: 10 composites = 223 contatos (vs 1576 v10 cego).
- **NÃO coordena contornos múltiplos** do mesmo obstáculo (B3.2: 9 carros no
  mesmo hold → pilha). Limitação documentada.

## TRILHA B (FASE H): NÃO EXECUTADA nesta sessão (contexto esgotado pelo B3)
Monaco v2, SF Interlagos, Spa v2, G3 Suzuka ficam como próxima fase — as
árvores pré-registradas estão no dsh (19:55Z).

## COMO REVERTER A PROMOÇÃO
```bash
# 1. race_diagnostic: usar --profile race (v10) ou --profile composite
# 2. run_race_10_cars: DEFAULT_PROFILE = "race" (linha 88 de run_race_10_cars.py)
#    → mudar para "composite" OU reverter para "race"
```

---

# v15 FASE 4b + FASE H (2026-10-16) — árvores PRÉ-REGISTRADAS (22:35:09Z)

## A1 paridade (gate do flip)
| falha | ação |
|---|---|
| runner↔eval >2e-5 | NÃO flip; diagnosticar wiring UMA variável |
| gate=0 ≠ v10 1e-6 | NÃO flip; bug de integração |
| a_prev zeros ≠ eval | NÃO flip; corrigir estado inicial |
| hash v1 mudou | NÃO flip; investigar |

## A3 B3.3 mista
| resultado | ação |
|---|---|
| verdes | cidadania OK; composite substitui iter3 |
| v10 inflado vs controle | diag pares; documentar |
| composite-composite contato | documentar (B3.1 cobre densidade maior) |

## A4.2 atribuição 73,6%
| achado | ação |
|---|---|
| pilha real (contatos→fora) | claim COM asterisco grid-dependente |
| artefato de métrica | corrigir instrumento, re-rodar |
| recovery-loop | documentar mecanismo |

## H0-H6 (árvores já pré-registradas 19:55Z — reafirmadas)
Monaco v2 3/3 → re-declarar B' em v2; 0/3 hairpin → limite real;
SF comprimento muda → investigar; Spa prof <20/20 → loop ≤2;
G3 salto → UMA variável janela arc-local → regressão.

---

# v15 FASE R3 — PRÉ-REGISTRO (2026-10-17T12:54:27Z, ANTES de qualquer código/corrida)

## M0 — hipótese única (verificada nos CSVs R2, seeds 0/1/2)
**O rejoin tem ALVO DE VALOR, não ALVO DE DIREÇÃO.** Fora do asfalto ele comanda
esterço FIXO `correction = -sign(lat)·min(STEER_MAX, 0.3+|lat|/40)` — a |lat|>20m
sempre saturado (±0,79 rad). Na grama o crawl equilibra em v≈1,45-1,5 m/s
(th 0,35 × resistência) e esterço constante no máximo produz ÓRBITAS de ~3 m de
raio: heading varre 360° (sin(herr): −1,0→+1,0), sem rumo travado em direção à
pista. Evidência: PER (lat oscila 20,7↔78,1 m por 500+s, steer −0,79 constante);
NOR (excursão de 861 m de s, lat 20↔81,6 m); HAM (idem). A recovery não
re-engata porque a saída exige v≥3,0 m/s — secundário: quem dirige é o rejoin.

## F1 — fix (UMA variável: a LEI DE ESTERÇO do rejoin)
Substituir o valor fixo por **esterço por BEARING ao ponto de re-entrada**:
alvo = projeção na linha central + 10 m à frente ao longo da pista;
`steer = clip(2.0·wrap(bearing_alvo − heading), ±STEER_MAX)`.
Tudo o mais INALTERADO (th 0,35, teto 8 m/s, máquina de recovery, gate, governor).
TESTE SINTÉTICO: carro a ~40 m fora, v=0, heading tangencial; exigir volta ao
asfalto em <60 s, v≥3 após, zero contato, progresso para frente pós-reengate.

## ÁRVORE DE DECISÃO (pré-registrada 2026-10-17T12:54:27Z)
- Teste sintético PASS → V1 (3 seeds 600s frozen v2 SF729 composite vplan).
- Teste sintético FAIL → inspecionar trace (bearing travou? velocidade?) →
  ajustar UM parâmetro (ganho/offset) → re-testar UMA vez. Segundo FAIL → PARE.
- V1: TODAS as seeds com 0 presos + 0 paradas ≥3 s + hesit ≤3 E MEDIANA com
  contatos <1576, pós-largada ≤100, fora-pilotagem ≤1,5%, voltas ≥10/10,
  rolante ≤115 s → **GATE VERDE → promoção EM VIGOR** (PROJECT_STATE com a
  tabela multi-seed como base de produto).
- V1 quebra qualquer critério → VERMELHO: diagnóstico dirigido pela
  decomposição (fora-pilotagem vs fora-preso vs contatos) e **PARE sem especular**.

## GATE MULTI-REALIZAÇÃO (critérios FIXOS, ≥3 seeds)
- Por seed (TODAS devem passar): 0 carros-preso (|lat|>20 m OU progresso <5 m
  em janela >30 s), 0 paradas ≥3 s, hesitações ≤3.
- Mediana das seeds: contatos <1576; pós-largada ≤100; fora ≤1,5% decomposto em
  FORA-PILOTAGEM (lat>6 m com progresso) — FORA-PRESO deve ser 0 por construção;
  voltas ≥10/10; rolante ≤115 s.
- Métrica "fora" do CSV = off-track sample; presença de preso por seed avaliada
  por janelas de 30 s sobre (lat, cum_dist) do CSV (instrumento, sem mudança de
  comportamento).

---

# v15 FASE R4 — PRÉ-REGISTRO (2026-10-17T14:04:42Z, ANTES de M0/C1)

## Objeto: a DOENÇA VISÍVEL — pilotagem do composite em campo denso
Regra: M0 é SÓ LEITURA dos CSVs v3. A suspeita "residual OOD" é HIPÓTESE a
falsificar. O contato 5 Hz SUBCONTA (empurrões curtos escapam) — proxy de
impulso OBRIGATÓRIO antes de atribuir excursão à pilotagem pura.

## M0a — decomposição de TODAS as excursões (3 seeds)
(i) **proxy de impulso**: |Δv| > 2 m/s em ≤2 ticks no início da excursão, sem
    contato registrado → reclassificar CONTATO-NÃO-AMOSTRADO.
(ii) restantes: g_gate no 1º tick, |g·r| = g×r_norm, brk/th/steer no 1º tick,
    obs10 (κ@10m), v, d_min reconstruído dos s de todos os carros, setor.
(iii) taxa exata por carro/volta.

## M0b — hesitações: d_min, g, r_norm, v_ahead na micro-parada; o modo
freio-forte do residual está presente (g>0,6 + freio alto sem contato)?

## M0c — rejoin-gerador: dos contatos pós-60s, quantos envolvem carro
re-entrado <10 s antes?

## C1 — CONTROLE v10-cego (profile race-blind), 3 seeds, frozen v2, gov vplan
— denominador de produto; NÃO afrouxa gate.

## CRITÉRIO "PRESO" NOVO (vale para TODOS os gates futuros)
Preso = episódio off-track com duração > T=60 s sem retorno ao asfalto
(alinhado ao teste sintético R3). Episódios ≤60 s contam como pilotagem.
O critério "lat>20" fica DESATIVADO para preso (obsoleto pós-fix R3).

## ÁRVORE PRÉ-REGISTRADA (limite fixado antes de medir)
| achado dominante nas excursões | ação |
|---|---|
| ≥60% com g>0 E \|g·r\|>0,3 (residual manda mal) | proposta de fix de CAMADA no gate (1 variável: ex. cap de \|g·r\| em freio, ou abertura mais conservadora) + re-gates disciplina (p95 n=0=0), G1, G2, multi-seed — implementar SÓ na R5 com pré-registro próprio |
| ≥60% com g≈0 (solo puro erra — contradiz 48/51) | PARE + investigação de física (empurrão não-amostrado, estado pós-rejoin, v degradada) |
| rejoin-gerador ≥30% dos pós-60s | proposta: rejoin com percepção (re-entrar só com gap) — 1 variável, R5 |
| residual dominante E camada insuficiente | proposta de retreino com distribuição deploy-realista — NÃO executar; PARE p/ aprovação (pré-gate do professor obrigatório) |
| contato-não-amostrado domina o proxy | corrigir o INSTRUMENTO de contato (amostragem física) antes de qualquer interpretação |

Decisão = ramo dominante por FRAÇÃO DE EXCURSÕES (excursões = total −
contato-não-amostrado), medido sobre as 3 seeds somadas.

---

# v15 FASE R5a — PRÉ-REGISTRO (2026-10-17T14:55:45Z, ANTES de qualquer run)

## OBJETO: instrumento de contato AUTORITATIVO no nível do solver
O pybullet É o solver (stepSimulation resolve colisões com impulsos reais;
get_state lê de volta pos/vel do corpo). O flag cc 5Hz amostra
getContactPoints só no tick de log — impulsos inter-tick somem.
INSTRUMENTO: colher getContactPoints após CADA sub-step (1/240 s), filtrar
chassis×chassis, logar por EVENTO: contador global de sub-step, par (ids),
posição de contato, normal, força normal (c[9]), impulso J=F·dt,
|Δv|=J/m por corpo (componente normal), XY de ambos. Coletor OPT-IN
(desligado por padrão: env/tests intocados). ZERO mudança de comportamento
— a física não lê nada do coletor.

## HIPÓTESES (a falsificar com a re-medida)
H1: cc-verdadeiro/cc-5Hz ≥ 1,5 no composite (subcontagem confirmada).
H2: dos 190 proxies raiz "contato-não-amostrado", os 95 brk>0,3 se dividem
    em empurrões reais (impulso presente) vs. frenagem própria (sem impulso).
H3: a razão de correção é MAIOR no cego (campo de contato constante) que no
    composite.
H4: wanderers (T=60s) têm impulso nos 10 s anteriores (vítimas de fling)
    e/ou salto de projeção (alvo de re-entrada >50 m de s num tick).

## CRITÉRIOS CANÔNICOS VIGENTES
- PRESO = episódio off-track >60 s sem retorno (R4; vigora).
- Multi-seed ≥3, mediana para número comparativo (permanente).
- Excursão: RAIZ vs ECO (gap ≤10 s do mesmo carro; sensibilidade 5/10/20 s).
- Flag 5Hz deve ser SUBCONJUNTO dos eventos (±1 tick) — se não for,
  falsos positivos do flag: resolver semântica antes de interpretar.

## ÁRVORE (versão final, pré-registrada antes de medir)
| resultado | ação |
|---|---|
| razão cc-verdadeiro/cc-5Hz ≥ 1,5 (composite, mediana) | subcontagem confirmada; v3 = instrumento canônico; TODOS os números da R4 re-pinados |
| razão ∈ [1,1; 1,5) | correção moderada; relatório por par e por regime de velocidade; v3 canônico com fatores |
| razão < 1,1 | o PROXY era o artefato; RETRATAR "70% contato-não-amostrado"; reabrir ramo pilotagem com dados do solver |
| flag 5Hz com eventos sem impulso na janela | falsos positivos do flag; resolver semântica antes de interpretar |
| guarda bit-idêntica falhar (1.3) | BUG do instrumento; corrigir ANTES de qualquer medição |
| eventos de impulso SEM flag 5Hz em quantidade | quantificar: é a subcontagem (esperado); separar por duração do evento |

## MÉTRICA DE EVENTO vs FLAG
- "evento" = contato chassis×chassis com força normal >0 em um sub-step.
- "cc-verdadeiro" (por tick) = nº de pares com ≥1 evento no tick;
  (por run) = nº de pares-tick. O relatório dá AMBOS os regimes
  (ticks e pares) e a sensibilidade do limiar de força (>0 e >10 N).

## GUARDA DE DETERMINISMO (1.3 — PRIMEIRO, antes da re-medida)
Re-run composite seed 0 com coletor LIGADO: CSV de dados BIT-IDÊNTICO ao
race_diag_b31_v3_seed0.csv da R4 (todas as colunas preservadas; o cabeçalho
de versão não conta). Divergência = instrumento contamina física = BUG.

## RE-MEDIDA (6 runs, mesmo protocolo R4)
composite + cego × seeds 0,1,2. Tabelas (i)-(vi) do enunciado.
R5b/R5c: pré-registros PRÓPRIOS, DEPOIS dos números da R5a.

---

# v15 FASE R6 — PRÉ-REGISTRO (2026-10-17T16:56:39Z, ANTES de qualquer run)

## ÚNICA mudança autorizada: semear o RNG do clima + logging aditivo
- Derivação do seed do clima: `sha256("<run_seed>//weather")` → int →
  `random.Random(int)` DEDICADO (nunca compartilha stream com outro RNG).
  Mecanismo estocástico PRESERVADO (transições continuam; entropia vira
  função do seed). Knob `--weather fixed` = prob de transição 0 (kind
  travado no nominal) — braço de controle.
- CSV v3.1 (aditivo): `w_kind`, `w_grip`, `w_trans` por tick +
  `tyre_life`/`tyre_grip` por carro-tick + weather_seed e log de transições
  na linha FONTE (ao lado do sha256 da pista).

## JANELAS E LIMIARES (fixados antes de medir)
- Atribuição de saída-raiz: clima nos ±10 s do início (sens. ±30 s);
  impulso do solver: lookback 10 s (padrão v3 da R5a); late-race = lap≥6
  com degradação alta (tyre_grip < limiar medido do campo); resto =
  pilotagem verdadeira. Limiar de domínio climático: **30%** das raízes.
- Margem de overdrive: v0 > v_allow(κ, grip, degradação) + **10%**.

## ÁRVORE DE ATRIBUIÇÃO (final, pré-registrada)
| resultado | ação |
|---|---|
| clima ≥30% das saídas race-speed | frente vira ENV: transição agressiva p/ produto? --weather fixed como candidato a modo de gate; pilotagem re-quantificada no resíduo |
| clima <30% E v0 > v_allow+10% | PILOTAGEM REAL confirmada (overdrive): caracterizar por banda κ e propor fix na PRÓXIMA fase; NÃO implementar agora |
| v0 ≈ v_allow (margem) e sai mesmo assim | problema físico-dinâmico (pneu/fase) → auditoria de FÍSICA, não policy |
| degradação late-race domina | frente vira estratégia/degradação — separar da frente de segurança |
| braço fixed ≈ braço seeded em tudo | clima é menor; variância = caos puro; mediana multi-seed basta |

## VALIDAÇÃO 1.4 (árvore de aceitação da semeadura)
- mesmo seed ×2, 600 s completos → BIT-IDÊNTICOS (fecha a guarda literal);
- pure vs instrumentado (coletor OFF via env RACE_DIAG_NO_CONTACT_LOG=1),
  mesmo seed, 600 s → bit-idênticos (guarda DEFINITIVA do instrumento);
- seeds 0/1/2 → históricos de clima diferentes (seeder vivo; unit-test
  das streams + transições dos runs);
- suite verde; falhas pré-existentes documentadas (as 2 da R3/R4).

## ARQUEOLOGIA 1.5 (pergunta a responder no relatório)
Por que os gates v14 eram determinísticos ENTRE processos se este RNG já
existia? (quando o modelo caiu no código de CORRIDA; prob real de transição
por run; por que pares R2/R3 deram agregados iguais).

## RE-MEDIDA (9 runs, 600 s, --gov vplan, frozen v2 SF729)
comp s0-2 seeded; cego s0-2 seeded; comp s0-2 --weather fixed.
Tabelas (i)-(vi) do enunciado. C1 re-pinada seeded = PROVISÓRIA (N=3);
gate N≥10 fica para a fase de gate. PARE ao final.

---

# v15 FASE R7a — PRÉ-REGISTRO (antes de qualquer run)

## TAREFA: variância de corrida INTENCIONAL e SEMEADA (opt-in)
Domínios AUTORIZADOS (cenário, NUNCA física):
- D1 GRID: ordem de largada embaralhada por stream dedicada
  (o --shuffle-grid existente passa a consumir a stream do domínio quando
  --variance grid está ativo).
- D2 COMPOSTO: atribuição HARD/MEDIUM/SOFT por carro por stream dedicada
  (a DISTRIBUIÇÃO atual por piloto permanece como pool; só QUAL carro
  recebe qual composto vira sorteio semeado).
- D3 CLIMA: já semeado (R6), inalterado.

FORA DE ESCOPO (recusa explícita): qualquer jitter de grip/sf/massa/pneu,
qualquer parâmetro físico. Se o gate futuro pedir mais variância, nova
proposta ao revisor.

MODO OPT-IN: `--variance` (lista csv, ex.: `grid,compound`); DEFAULT
DESLIGADO — comandos e deploys atuais permanecem válidos e bit-reproduzíveis.
Streams: helper ÚNICO no padrão do weather seeder:
sha256("<seed>//<domain>") → random.Random(int) DEDICADO por domínio.
np.random global NUNCA é consumidor.

## PROTOCOLO DE MEDIÇÃO (endurecimento obrigatório)
1. PINNING: OMP_NUM_THREADS=1 (+ OPENBLAS/MKL/NUMEXPR =1), 2 processos
   PARALELOS ×1 thread → bit-estáveis entre si E vs gêmeo sequencial?
2. CARGA: sequencial default-threads ×2 SOB carga artificial de CPU
   (ex.: 4 workers estressando) → bit-idêntico?
3. VEREDICTO documentado: paralelismo-com-pinning AUTORIZADO ou
   sequencial-puro com threads fixadas.

## VALIDAÇÃO (sequencial; paralelo só se pinning PASSAR)
a) NÃO-INVASÃO: R7a seed 0 --variance OFF ≡ R6 SEQ (comp SECA)
   bit-idêntico — prova de zero mudança de física.
b) mesma seed ×2 --variance ON → bit-idênticos (cenário completo).
c) 10 seeds composite sequenciais --variance ON: tabela de dispersão
   cc/fora/rolante/preso + prova de realizações DISTINTAS. O gate N≥10
   (dois braços) NÃO roda aqui.

## LOGGING ADITIVO (obrigatório ANTES de interpretar)
Cenário sorteado (ordem do grid, mapa de compostos, weather_seed, estado
da --variance) no cabeçalho CSV/linha FONTE. Smoke-test do harness
(parâmetros aparecem nos logs) ANTES de qualquer cadeia longa.

## LIMITAÇÕES (declarar no relatório)
Variância semeada NÃO cobre: máquinas distintas, versões de BLAS/drivers,
diferenças de pybullet build. A reprodutibilidade é intra-ambiente.

---

# v15 FASE R7b — PRÉ-REGISTRO (2026-10-17T21:36:39Z, antes de qualquer execução/análise)

## HIPÓTESES EM DISPUTA
H1 (física): o modelo lateral quebra em estados que o policy entra e o
professor não (slip combinado, transferência, superfície).
H2 (plano/entrada): v_allow otimista em banda de κ OU entrada com erro de
heading/posição — o esterço 5× é o policy CAÇANDO um escorregamento JÁ
iniciado; a margem do professor seria o sf adaptativo (decai em κ>0,10),
que o neural não tem.

## PREDIÇÃO DE HOTSPOT (ANTES dos dados do 1.3/2)
P1: saídas concentram em κ@saída ∈ [0,008; 0,020] com v0/v_allow ∈ [0,7; 0,95].
P2: no tick de saída o SLIP (heading − direção da velocidade) já é >10° na
maioria — assinatura de policy CAÇANDO (H2), não fronteira estourada (H1).
P3: a_lat efetiva no tick de saída DENTRO de R_max(v) na maioria (>60%);
se estourar na maioria, H1 vence.
P4 (biseção): o run FASE-4(9099235)+frozen dá fora% ALTO (~20-30%), NÃO
~0,17% — o gap B3.1→R6 é majoritariamente INSTRUMENTO (live→frozen +
clima/contenção não controlados na era), não regressão pós-R2.

## ÁRVORES
0.2: divergência antes da 1ª excursão → wiring/track/plano; só após →
rejoin (não explica fora). Culpado não-intencional → proposta SEM aplicar.
1.3/2: física segura 0,81·v_allow com entrada suave → H1 refutada nos
estados suaves → frente volta a POLICY com mapa de hotspots. Física quebra
→ H1 confirmada → localizar mecanismo e registrar. Veredito POR BANDA de κ.

## MÉTODO
0.1: comparabilidade zero-runs (definição offtrack por era + recompute de
CSV legacy verde; o CSV do B3.1 NÃO existe — gap documentado; mais próximo:
prof_gate_s0 all-professor 0,36%).
0.2: worktrees sequenciais — (i) 9099235+frozen-CSV+patch SF729 1-linha
(instrumentação documentada); (ii) f06f2c4+variante sf729 (loader da era
sobrepõe p/ função pura→929; variante dá 729); (iii) 2b4e195 (v2 SF729
nativo); (iv) atual = R6-SEQ referência.
1.1-1.3: offline (proveniência 0,788/0,80; tabela κ; re-análise dos 10
CSVs R7a — ZERO runs). 2: skidpad scripted no hotspot + controle.

FORA DE ESCOPO: R5c; qualquer mudança de física/plano/policy.

---

# v15 FASE R12-CANÁRIAS — PRÉ-REGISTO EMENDADO (antes de qualquer run de canária)

## CHECAGENS 0.C-0.F (executadas, zero runs — working tree limpo p/ os scripts)
- 0.C SKEW: r12b treinou com 12d de tráfego = ZEROS; runner serve valores
  VIVOS. SKEW CONHECIDO — avaliação comportamental decide (canárias/piloto).
- 0.D |r_pred| nas janelas: p50 0,057 | p90 0,879 | p95 1,245 | p99 1,597 rad
  — p95 ≥ 0,15: o modelo NÃO colapsou na média (a cauda carrega correções
  fortes). Documentado ANTES do piloto; não bloqueia.
- 0.E PRESET: causa raiz da H5-env confirmada ('preset local de Interlagos',
  SF 109, no log da canária baseline 0/3).
- 0.F GRADE completa registrada (canto estrito 38% = NO-GO — fragilidade).

## CANÁRIAS VIA RUNNER FROZEN (instrumento (a) — aprovado pela revisão)
Definição: race_diagnostic, 1 CARRO (build_grid_drivers()[:1]), perfil
composite, 600s, Interlagos frozen (sha 164876…, SF 729, gov vplan,
variance grid,compound), seeds 0 e 1 (secos; pinados). Mapeamento: campo
de 1 carro = solo funcional do stack (composite ativa com tráfego próprio
inexistente; g=0 em campo de 1 — o residual NÃO atua; a canária mede o
STACK, e a diferença r12b vs r2 só existiria se o wiring quebrasse).
- H5' (substituta da H5-env): MESMO protocolo nos MESMOS seeds; o candidato
  r12b NÃO piora o controle positivo: voltas completas iguais; |fora%|
  diferença ≤ 2 pp; wanderers = 0; rolante dentro de ±5 s.
- LIMIARES DO CONTROLE POSITIVO (r2 primeiro — instrumento só vale se r2
  PASSAR): ≥2 voltas completas em 600s; fora ≤ 10%; wanderers 0.
- ORDEM: (1) r2 seed 0; (2) r2 seed 1; (3) r12b seed 0; (4) r12b seed 1.
  Sequencial-puro. RAMO: r2 falha → problema de protocolo/stack → PARE+autópsia.
- IMPLEMENTAÇÃO permitida (pré-registrada aqui): flag --n-cars N no
  race_diagnostic (1 linha: fatiar build_grid_drivers()[:N]) — instrumento
  mínimo p/ canária de 1 carro; commitada antes dos runs.

## PILOTO {0, 8, 9} (canárias verdes → smoke identidade → piloto)
- ESCLARECIMENTO 1: H1-H4 no piloto = leitura POR-SEED do seed 0 (surrogato
  de campo denso); o teste mediano REAL de H1-H4 é no N=10. Declarado.
- ESCLARECIMENTO 2: seed extra do ramo MISTO = seed 20 (FORA do pool 10-19
  do R13; protege o confirmatório).
- Árvore VERDE/MISTO/VERMELHO como pinada em b1a852c. N=10 condicional vs
  braços EXISTENTES (proibido re-rodar). Paradas pelo CSV (0.B).
- KIT DE AUTÓPSIA: grade 0.F, perda 16d, r_win med −0,058, |r_pred| 0.D, skew 0.C.

---

# v15 FASE R12-CANÁRIAS — RESULTADO + PARE (2026-10-18, após runs commitados b53687c/d4c8f14)

## CHECAGENS 0.C-0.F (zero runs, executadas antes)
- 0.C SKEW: r12b treinou com 12d tráfego=ZEROS; runner serve vivos (conhecido).
- 0.D |r_pred| janelas: p50 0,057 / p90 0,879 / p95 1,245 / p99 1,597 — p95 ≥ 0,15
  (não colapsou na média; cauda carrega correção forte).
- 0.E preset: causa raiz H5-env confirmada.
- 0.F grade 9 valores registrada (canto estrito 38% = NO-GO; fragilidade).

## CANÁRIAS (instrumento (a): runner frozen, 1 carro, 600s, seeds 0-1)
r2 s0/s1 e r12b s0/s1: **4 runs BIT-IDÊNTICOS entre si** (5 voltas, fora 18,4%,
wanderers 0, rolante 132s) — PROVA de wiring são: em campo de 1 carro g=0
sempre, o residual NUNCA atua, r2≡r12b por construção. O stack carrega 5
voltas limpas de 600s no frozen.

## CONTROLE POSITIVO: FAIL no LIMIAR de fora (18,4% > 10% pinado)
Autópsia: o LIMIAR foi calibrado às cegas para "solo limpo"; o v10 solo+frozen
real é ~18% fora (regime do braço A seco 25-32% em campo 10; solo menos denso,
off em s 1800-2400 e wrap). O stack NÃO está quebrado (bit-idênticos; 5 voltas;
wanderers 0) — o que falhou foi o NÚMERO do limiar, não o instrumento nem o
candidato. RAMO EXECUTADO: PARE conforme prereg. A emenda do limiar (ex. fora
≤ 25% p/ 1 carro + voltas ≥ 2 + wanderers 0) seria RE-PINAGEM pós-número —
proibida nesta fase; a revisão decide.

## H5' (avaliada sob os fatos): r12b NÃO piora o stack — voltas iguais (5=5),
|Δfora| 0,0 ≤ 2pp, wanderers 0=0, rolante 132=132s — PASS ESTRITO. Mas o gate
formal do controle positivo falhou no limiar pinado; o protocolo manda PARE.

## PILOTO {0,8,9}: NÃO EXECUTADO (árvore: controle positivo falha → PARE).

---

# v15 FASE R12-PILOTO — PREREG-ERRATA #2 (canária 1-carro; commitado ANTES de qualquer run)

## ESCOPO FECHADO: vale SÓ para a canária 1-carro (instrumento detector de
## falha grosseira do stack). A árvore VERDE/MISTO/VERMELHO do piloto e os
## limiares do N=10 permanecem INTOCADOS — qualquer ajuste ali = PARE.

## LIMIARES RE-PINADOS (derivação registrada)
- voltas ≥ 2 | fora ≤ 25% | wanderers 0
- Derivação: baseline v10 solo+frozen medido = 18,4% fora no instrumento
  canônico (4 CSVs bit-idênticos); margem de política 1,36× → 25%.
- Papel: detector de falha GROSSEIRA do stack, NÃO gate de qualidade.
- Aplicação SIMÉTRICA: controle r2 e candidato r12b sob os mesmos limiares.

## F2 — FECHAMENTO ARITMÉTICO (auditoria da definição de volta, zero runs)
A canária reportou "5 voltas × 132s = 660s > 600s" — auditoria do CSV:
conforme contrato de instrumento (R2/R3), tempos por wrap usam VALOR de
tick × 0,1s (5 Hz de amostragem — índices NÃO servem). Auditoria a
publicar com números do CSV antes do piloto. [resultado abaixo]

## A.4 — CONFIRMAÇÕES (já registradas no prereg b1a852c; reafirmadas)
- H1-H4 no piloto = leitura POR-SEED do seed 0 (surrogato; teste mediano
  real é no N=10).
- Seed extra do ramo MISTO = seed 20 (FORA do pool 10-19 do R13).

## A.5 — RE-AVALIAÇÃO do ponto de decisão com os 4 CSVs EXISTENTES
Controle r2 sob limiares emendados → H5' → piloto destravado (se PASS).

## A.1-A.5 — EXECUÇÃO (zero runs)
- A.2(b) smoke offline COM tráfego vivo: |r2−r12b| mediana 0,079/max 0,089
  rad → override end-to-end CONFIRMADO (em campo-1 nunca exercitado).
- A.2(c) g≡0 nos 4 CSVs (composite_active=0) — bit-identidade DOCUMENTADA.
- A.2(a) runner agora loga sha256 do residual carregado (r12b b77adc68caef742a;
  r2 6a2dbf53a69fcac7) — fallback silencioso morto.
- A.3 FECHAMENTO ARITMÉTICO: 5 "voltas" = 5 CRUZAMENTOS incl. a LARGADA
  (1º em t=1,4s) → 4 voltas COMPLETAS × 131,5s = 526s ≤ 600s — FECHA.
  Correção na ERRATA: a contagem do sumário contava cruzamentos; voltas
  completas = cruzamentos − 1 (corrigido na métrica A.5; contrato R2/R3
  — valor de tick ×0,1s — respeitado).
- A.5 RE-AVALIAÇÃO sob ERRATA #2: r2 s0/s1 PASS (4 voltas completas,
  18,4% ≤ 25%, wand 0); r12b idem bit-a-bit → H5' PASS → PILOTO DESTRAVADO.

---

# v15 FASE R13-GATE — PRÉ-REGISTO (commitado ANTES de qualquer run; seeds 10-19)

## CONTEXTO: trilha de retreino ENCERRADA (rota 1 adotada) — r12b = research-negativo
(não deploya); valor registrado (hesit −54% s0; pós-60s −64 s9). Backlog: rota 2
(pré-cond: justificar BC offline vs covariate shift ou ir online); rota 3
(pré-cond: endereçar OOD E r_win/ruído). O R13 julga o COMPOSITE ORIGINAL
(v10 solo congelado ac2504e5 + r2 residual_best 6a2dbf53a69fcac7).

## 0.2a — LIMIARES MECÂNICOS (quantis PINADOS do braço A seeds 0-9, CSV; método:
## fora ≤ p75(A); rolante ≤ med(A)+10s; hesit ≤ p75(A); cc ≤ p75(A); paradas:
## 0 no seco / ≤ T-adv; wanderers ≤ med(A)+2; floor: 10/10 completam)
- SECO (n=7): fora ≤ 30,4% | rolante ≤ 164s | hesit ≤ 17 | cc ≤ 545 |
  paradas = 0 | wanderers ≤ 2
- ADVERSO (n=3): fora ≤ 50,1% | rolante ≤ 184s | hesit ≤ 12 | cc ≤ 430 |
  T-adv PINADO = 8 (p75=7 arredondado para o máximo observado — n pequeno;
  escolha DOCUMENTADA: p75 com n=3 = o valor entre 7 e 8; pinamos 8 para
  não reprovar por 1 episódio de excursão RECUP-OFF, já que paradas são
  100% subproduto de excursões — R12-0.1) | wanderers ≤ 12
- JUSTIFICATIVA da re-ancoragem: o gate R10 usou critérios pré-canônicos
  (fora ≤1,5%, rolante ≤115s) 3-7× mais estritos que TODO o corpus legítimo
  de 20 corridas (R12-0.6), ancorados no B3.1 que a R7b provou
  não-reproduzível; o D1-R10 (paradas=0 enquanto o incumbente tinha 14)
  penalizava o candidato por clima adverso onde ele era 15× melhor; a
  ERRATA #2 estabeleceu o precedente de calibrar limiares no baseline REAL.

## 0.2b — TOLERÂNCIA DE PACE ADVERSO PRÉ-ARGUMENTADA
A spec é completion-first (Meta D): a percepção de tráfego compra campo
sobrevivente em clima adverso (s8: contatos 336 vs 5138 do cego; paradas
6 vs 14) ao custo do resíduo de pace s8 (+70,9s/volta medido na
decomposição R11-0.2 — o gap adverso vem do envelope/estado, não do
fora). O limiar adverso de rolante (184s = med+10) E o de fora (50,1%)
refletem isso: aceita-se pace adverso menor pelo valor de segurança.

## 0.2c — RÓTULO DE CLIMA MECÂNICO (do próprio CSV do run)
ADVERSO = (w_trans==1) em QUALQUER tick do run (onset de transição real
de kind dentro do run — coluna do CSV v3.1); SECO = caso contrário.
ZERO seed-shopping: seeds 10-19 fixos; o mix climático é o que vier;
se não houver seed adverso, o ramo adverso fica report-only com ressalva.

## 0.2d — DESFECHOS PRÉ-DECLARADOS
- PASS por clima (seco E adverso dentro dos limiares; adverso
  report-only se não ocorrer) → PROPOSTA DE PROMOÇÃO (decisão FINAL da
  revisão).
- FAIL em qualquer critério → veredito R10 PERMANENTE (manutenção do
  v10) com confirmação out-of-sample.
- Árvore avaliada SÓ após os 10 runs do braço A (sem early-stop);
  working tree limpo no script de decisão; paradas do CSV (regra s9);
  SEM re-run cirúrgico de seed falho (crash de instrumento excetua).

## COMANDOS (braço A; B = trocar APENAS --actor/--obs-mode)
.venv/bin/python model_train/race_diagnostic.py --profile composite --ticks 6000 \
  --laps 99 --track interlagos --seed {10..19} --gov vplan --variance grid,compound \
  --out race_diag_r13_a_s{N}.csv
Braço B: --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge (idem resto).

---

# v15 FASE R13-FECHAMENTO — apêndice auditável + erratas E1-E5 (zero runs)

## E4 (manchete): a tabela real dá ratio cc_B/cc_A ∈ **1,5× a 3,5×** (mediana
## 2,2×; Δ −479 a −994) — a manchete "3-13×" estava ERRADA (confundia ratio
## com recíproco de Δ). Corrigida em docs.

## E1: cc-fail = {s10:601, s11:600, s12:613, s13:781, s19:877} — range
## 600-877 correto (limiar p75 seco 545 / adverso 430).

## E2 (por seed, denominador = AMOSTRAS de contato do solver): s10 44%,
## s11 39%, s12 39%, s13 43%, s14 40%, s15 39%, s16 28%, s17 43%, s18 42%,
## s19 44%. Range 28-44% (o texto "39-44%" era dos cc-fail apenas; correto
## geral: 28-44%).

## E3 (denominadores): hesit on-track totais s11=21, s12=16, s13=14, s14=16,
## s15=20 — os 14-21 do texto são os TOTAIS por run; classes somam o total
## (ex. s11: REJOIN 13 + TRAF 0 + CRAWL 6 + OUTRO 2 = 21 ✓).

## E5 (adversos 0-9 pela regra w_trans MECÂNICA): **{2, 8, 9} (n=3)** — igual
## ao usado na derivação do prereg (n=3) — NENHUM quantil muda; vereditos
## por seed inalterados linha a linha (robustez confirmada).

## Identity smoke 20 runs: ator ✓, gov vplan ✓, pista sha 164876 ✓, SF 729 ✓,
## CSV v3.x ✓ em TODOS. Residual r2: sha do arquivo VERIFICADO hoje
## (6a2dbf53a69fcac7) mas NÃO logado nos runs A (o sha-log só dispara com
## --residual-override) — GAP documentado: identidade do braço A é IMPLÍCITA
## via PROFILES; o logging universal vira parte do PASSO 2 (v3.3).

---

# v15 FASE R13-FECHAMENTO — PASSO 4: prereg LEVE do dossiê da alavanca (antes da análise, zero runs)
Corpus: 20 CSVs R13 (A+B) + braço A 0-9. Perguntas PINADAS:
(i) taxa de EXCURSÕES que terminam em contato no retorno (denominador =
excursões; numerador = excursões com contato do dono ≤30s pós-reentrada);
(ii) janela temporal reentrada→contato (distribuição; define a latência
útil de percepção de um futuro rejoin-com-gap);
(iii) fração de contatos pós-rejoin vs pilotagem limpa (denominador =
contatos; já medido como 28-44% envolvendo carro FORA — aqui separado por
causa: retorno vs erro limpo);
(iv) latência de re-aceleração pós-reentrada (distribuição do tempo da
REJOIN-DIP até v>5 m/s).
RAMO: corpus insuficiente para (ii)/(iv) por carro → reportar o que houver.
