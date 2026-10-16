# PROJECT_STATE.md — F1 RL Bot: estado do projeto

> **Toda sessão futura começa por: ler este arquivo e AUDITORIA_RL.md.**
> Última atualização: **v15 FASE 4: B3.1 all-composite TODAS VERDES (223 contatos, 0 pós-larg, 103,4s, 0 hesit, 0,17% fora) → PROMOÇÃO PROPOSTA: race default = composite. B3.2 hold-at: pilha (3975, coordenação múltipla). Controle v10 cego+vplan: 3433/73,6% fora (PERIGOSO). FASE H (pistas v2) NÃO executada — próxima fase.**

## Metas

| Meta | Critério | Status | Melhor resultado |
|---|---|---|---|
| **A** Professor ≥95% | todas as pistas, grip 0,75–1,0 | **✓ 100%** | professor v2: 40/40 nas 8 pistas |
| **B** Aluno ≥9/10 treino | cada pista de treino | **✓ 100%** | v10: 39/39 nas 13 pistas |
| **B'** Aluno ≥7/10 teste | Monaco, Suzuka, Spa (zero-shot) | **✘ 6/9** | Suzuka 3/3 ✓, Spa 3/3 ✓, Monaco 0/3 |
| **C** Tempo ≤91,2s (−20%) | Interlagos raw eval | **✘ 109s** | teto DAgger: 108s; PPO: **4× falhou** (v13 no-respawn: 2/3 a 125s) |
| **D** Corrida 10 carros | zero paradas ≥3s, 10/10, fora ≤4,6% | **✓ 100%** | v10: 1 hesitação, 2s parado, 0,8% fora |
| D-v15 (corrida, gov vplan) | idem + rolante | ✓ 103,4s | zero hesitações, fora 0,0%, contatos 1576 (nota: 103,4s é instrumento CORRIDA compostos rolante — NÃO comparável a 109s eval MEDIUM grip-realista nem a 107,9s professor-corrida) |

## Mapa de checkpoints

| Checkpoint | Tipo | Uso | Status |
|---|---|---|---|
| **v14b_traffic/dagger_actor_best_s0_n0** | DAgger pool-13, estágio A (n=0) | base solo em obs 60d (traffic-blind) | ✓ **51 eps: 48/51 = paridade v10**; canárias 3/3; Spa/Suzuka/Zandvoort 3/3 |
| v14b_traffic/dagger_actor_best_s1_n4 | DAgger pool-13, estágio B (n=4, iter 3) | REPROVADO no gate | ✗ Suzuka 2/3 (obrigatório 3/3); canárias 3/3 VERDES; G2 n=4 3/3 (10 cont/lap) — near-miss, FASE 6 |
| **v14_traffic/dagger_actor_best_s2_n8** | DAgger tráfego iter 8 (n=8) | profile **traffic** (eval c/ fantasmas) | ⚠ gates solo/traffic OK, mas **corrida all-v14 FALHOU** (1691 contatos, 152s) e **39/51 solo** (esquecimento κ extremo) — NÃO usar all-neural |
| v14_traffic/dagger_actor_best_s1_n4 | DAgger tráfego iter 3 (n=4) | densidade média | ⚠ gate B ✓; solo: só Silverstone perdida (menos esquecido que iter8) |
| v14_traffic/dagger_actor_best_s0_n0 | DAgger tráfego iter 1 (n=0) | regressão zero | ✓ 3/3 Silverstone/Montreal/107 (solo intacto; traffic-blind) |
| v14_traffic/init_from_v10 | transferência v10→v14 (60d) | ponto de partida FASE 3 | ✓ paridade 1e-6 com v10 (tests/test_v14_transfer.py) |
| v14_traffic/dagger_actor_iter10 | β=0, fim do currículo | REJEITADO pelo gate | ✗ Suzuka 0/3 (ruído do aluno dominou o dataset; best-por-VAL é o correto) |
| **v10_dagger/dagger_actor_best** | DAgger sf=0,80 | RACE SETUP v13 (sem tráfego) | ✓ 48/51 94%, 109s, Meta D ✓ |
| **v11b_pace90/dagger_actor_best** | DAgger sf=0,90 | **QUALI SETUP** (máx pace) | ✓ ~47/51, 108s, Suzuka 2/3 |
| v11_pace/dagger_actor_best | DAgger sf=0,95 | DESCARTADO | ✗ 36/51 71% (regressão) |
| v12_pace_ppo/multi_context_rl_actor_best | PPO residual (respawn) | DESCARTADO | ✗ 0/3 (lap% 6.5% fabricado) |
| v13_ppo_norespawn/multi_context_rl_actor_best | PPO no-respawn | DESCARTADO | ✗ 2/3 a 125s (degradou de 3/3 a 108s) |
| v9_dagger/dagger_actor_iter10 | DAgger 4 pistas | SUPERADO pelo v10 | 18/24 75% |

### Protocolos de inferência testados (TESTE 1, Meta C final)

| Protocolo | v10 | v11b | v12 |
|---|---|---|---|
| tanh(mu) — atual | 3/3 109s | 3/3 108s | **0/3** |
| sigma=0,05 | — | — | **0/3** |
| sigma=0,10 | 3/3 ✓ | 3/3 ✓ | **0/3** |
| sigma=0,20 | — | — | **0/3** |

**Veredicto**: o v12 falhou por ARQUITETURA (PPO degradou a política de 3/3 para 0/3), não por modo de inferência. Greedy-V descartado (não aplicável).

**Nota de inferência**: v10 e v11b mantêm 3/3 com σ=0.10 (robustez a ruído confirmada). v13: best 2/3 a 125s, final 1/3 a 117s — TETO CONFIRMADO sem ressalvas (PASSO 0 da Fase v14).

**PASSO 0 (fechamento hermético)**: NENHUM checkpoint do v13 é 3/3 com <108s. O gradiente PPO degrada desde a primeira iteração e nunca recupera. A lição: "stop rule mais cedo" não se aplica — não há janela de ganho.

## FASE 1 v14 — camada de tráfego + GATE all-professor (✓ VERDE)

**Implementação (PASSO 1)**: car-following + offset lateral no ReferenceController
(`reference_controller.py`), agora APLICADO ao ponto de perseguição (na FASE 1
original o `_lat_offset` era computado mas nunca usado — estado morto, corrigido).
Métrica de tráfego: **dist_s assinada ao longo da pista** (`signed_dist_s`,
positiva = à frente; wrap em ±L/2 — carro 5 m atrás dá -5, não +L-5). Ranking
dos 3 mais próximos usa |dist_s|; o sinal vive no flag ahead. Modo professor no
race runner: `--controller professor` (`race_diagnostic.py`) — 10 ReferenceControllers
simultâneos, cada um com os outros 9 como tráfego, v_plan ÚNICO compartilhado.
**Autoridade: professor → rejoin → recovery → blocked. SEM governor** (o v_plan
já planeja a frenagem; governor = frenagem dupla; ele fica só no modo neural).
Suite: **211/211** (152 base + 59 v14: tráfego, env-fantasma, corredor, transferência, race-60d/profiles, slot-swap, mixed-runner, hold-at).

**GATE (PASSO 2) — corrida 600 s, 10 professores, Interlagos, headless, 2 seeds**:
seeds 0 e 1 produziram métricas IDÊNTICAS (sim determinística — a repetição
confirma ausência de não-determinismo de contatos).

| métrica | meta | resultado | veredicto |
|---|---|---|---|
| carros com ≥1 volta | ≥9/10 | **10/10** (5 voltas cada) | ✓ |
| contatos carro-carro (amostras 5 Hz) | <400 | **258** (baseline aluno-cego: 1333) | ✓ −81% |
| paradas ≥3 s | 0 | **0** | ✓ |
| ultrapassagens líquidas (histerese 10 m) | documentar | **1** (na largada) | FILA: sem ultrapassagem após a largada |
| % tempo em follow (cap+close) | documentar | **0-15%** por carro (VER 0%; colado ≤2,4%) | ✓ não é fila permanente |
| tempo mediano de volta COM tráfego | baseline FASE 4 | **107,9 s** (excl. volta 1; 108,2 s todas; solo ~107 s) | custo do tráfego ≈ +1 s |

**Comportamento exibido**: o professor forma FILA APÓS A LARGADA — não ultrapassa
(pace idêntico v_plan → sem diferencial de velocidade), mas a fila é ESPARS: os
contatos ficam confinados à largada (t=1,2-47,8 s; pares de fileira LEC-NOR 57,
HAM-RUS 25, PER-SAI 24, ALO-GAS 11, PIA-RUS 9), o campo se espalha (gap médio
~430 m >> D_AHEAD=60) e os 552 s restantes têm ZERO contatos. **Teto do v14
confirmado: evita colisões, sem ultrapassagem deliberada.** Os contatos de
largada vêm da camada de offset (carro "à frente" na coluna oposta manda o
follower cruzar a pista) — aceitos dentro da meta; se a FASE 4 pedir largada
limpa, o knob é a condição de disparo do offset (só deslocar quando o líder
está próximo do MEU lateral), NUNCA treinado às cegas.

## FASE 2 v14 — obs 'traffic' (46d) + fantasmas no env (✓ implementada)

1. **obs_mode='traffic'** = edge 34d + 12d (`f1_env.py`): 3 carros mais próximos
   por |dist_s|, 4 features por carro nesta ordem:
   `[|dist_s|/100, (v_outro-v_ego)/OBS_SPEED, lat_outro/half_width, ahead(1|0)]`;
   zeros se menos de 3 visíveis; a obs NUNCA contém o próprio carro.
   **Ator v14 = 60 entradas** (46 tel + 2 ctx + 8 emb_track + 4 emb_compound).
   Layout documentado em `N_TRAFFIC_FEAT` (f1_env.py) + validação de shape com
   ValueError explícito.
2. **Fantasmas**: `n_traffic` (0-9) no construtor do env; carros FÍSICOS
   completos dirigidos pelo professor de TRÁFEGO (FASE 1, o do gate — cada
   fantasma vê aluno + outros fantasmas via `env.traffic_for(id)`); **grip
   nominal 1.0**; grid estilo F1 à FRENTE do aluno (aluno=P10, fileiras 9 m,
   colunas ±1,9 m) reposicionado a CADA reset; **NÃO geram eventos de volta**
   (`engine._no_lap_drivers` — sem degradar pneu, sem avançar clima) e **NÃO
   contam no lap%** (o check do ego usa só `states[ego].lap`).
3. **allow_respawn=False confirmado** no treino (train_dagger.py:179 — lição
   v13 verificada; default do script já era o correto).
4. Testes (`test_traffic_env.py`, 14): obs finita com 0/1/9 fantasmas; slots
   de tráfego corretos (0,09/0,18/0,27 no grid); layout estável entre resets;
   `traffic_for` exclui o ego; fantasmas andam (>5 m em 3 s) e ficam lap=0;
   engine ignora `_no_lap_drivers` no default; validação de n_traffic/obs_mode.

## FASE 3 v14 — DAgger de tráfego (✓ CONCLUÍDA; ator v14 de 60 entradas treinado)

### PASSO 0 — baseline pinado + professor limpo na largada
- **Professor SOLO (metodologia do gate, grip real, VER/SOFT, 3 eps idênticos —
  determinístico)**: volta de LARGADA parada **110,6s**; voltas ROLANTES
  **107,5s** (mediana; `eval_teacher_solo.py`). **Custo real do tráfego =
  gate 107,9 − solo 107,5 = +0,4s.** A inconsistência anterior (107,9 vs
  "112s") era UNIDADE de volta: o gate mede voltas ROLANTES; o 112s histórico
  era volta de LARGADA parada no env (111,6-114,6s com composto MEDIUM).
- **Corredor do offset** (`reference_controller.py`, LAT_CORRIDOR_M=3,5): o
  offset só dispara quando o líder está no MEU corredor lateral
  (|lat_outro − lat_ego| < 3,5 m). Re-gate: contatos **258 → 240**, e o
  MECANISMO mudou: cruzamentos LATERAIS extintos (0 pares laterais); os 240
  restantes são nose-a-cauda na largada (PER-SAI 73 amostras: compostos
  HARD vs MEDIUM aceleram diferente em gap de 9 m — rubbing físico que NÃO
  contamina rótulos). Nada regrediu (10/10, 0 paradas, mediana 107,8 s).
  **Professor APROVADO para rotular** (lição Monaco respeitada).

### PASSO 1 — transferência v10→v14 (NÃO BC-do-zero)
- `transfer_v10_v14.py`: remap de rows da 1ª Dense por LINHA na ordem do
  concat [tel, ctx, emb_trk, emb_cmp]: rows 0-33 ← edge v10; **rows 34-45 ←
  ZEROS** (a rede começa ignorando tráfego); rows 46-47 ← ctx; rows 48-59 ←
  embeddings. Bias e profundas: cópia direta.
- **Teste de paridade (obrigatório, 7/7 em tests/test_v14_transfer.py)**:
  v14 com tráfego zerado == v10 (atol 1e-6) em inputs aleatórios E na obs
  real do env; + invariância inicial ao tráfego; + **congelamento matemático:
  com inputs de tráfego zero o gradiente nos rows 34-45 é nulo** (Adam não os
  move — prova por teste com BC fit). Checkpoint: `v14_traffic/init_from_v10.keras`.

### PASSO 2 — DAgger v14 com currículo (train_dagger.py reescrito)
- `--obs-mode traffic`; `--traffic-stages "0:2,4:5,8:3"`; professor rotula
  com `teacher.action(traffic=env.traffic_for(env.driver_id))` (mesma percepção
  da obs); **train_bc com WARM START** (senão os rows de tráfego nasceriam
  aleatórios e a herança v10 se perderia a cada iter); β 1.0→0.0 global;
  2 eps/pista/iter; 50 epochs; pool interlagos/Monza/Hungaroring/Mexico/
  procedural:301; VAL Zandvoort com o n_traffic do estágio;
  allow_respawn=False impresso no log do 1º episódio (lição v13 ✓).
- Dataset final: 121.351 estados, 10 iters, ~2h (log: v14_traffic/train.log).

### PASSO 3 — gates por estágio (determinístico, grip real, sem respawn)
| gate | resultado | veredicto |
|---|---|---|
| **A** (n=0, iter 1): sem tráfego | Interlagos 3/3 **108,1s** + Suzuka 3/3 **132,3s** | ✓ REGRESSÃO ZERO (≈ v10 109s) |
| **B** (n=4, iter 3): sem + com | Interlagos 3/3 **106,9s**; Suzuka 3/3 132,4s; c/ tráfego 3/3 **123,4s** (professor: 123,9s), **0 contatos/lap** | ✓ aluno 0,5s mais rápido que o professor |
| **C** (n=8, best iter 8): sem + com | Interlagos 3/3 109,9s; **Suzuka 3/3 136,3s**; c/ tráfego n=8 3/3 **134,0s** (professor: 134,1s), **0 contatos/lap** | ✓ (gate formal falhou só no ATOR da iter 10: Suzuka 0/3 — abaixo) |

**Decisão "para no último checkpoint bom"**: o gate do estágio C correu sobre
o ATOR FINAL (iter 10, β=0) e falhou em Suzuka 0/3. Medido o BEST do estágio
(iter 8, `gate_checkpoint.py`): **PASSA em tudo** → o último checkpoint bom
é **v14_traffic/dagger_actor_best_s2_n8.keras** (não foi preciso voltar ao
estágio B). Lição registrada: o gate deve ser aplicado ao best-por-VAL do
estágio, não ao último ator (β→0 degrada: dados do aluno com ruído 0,15
dominam o dataset; iters 9-10: VAL 1/3 e 3/3 com val_loss subindo).

**Professor-com-tráfego (mesmo instrumento do G2, contatos por volta)**:
n=4: 3/3, 123,9s, 0 contatos/lap | n=8: 3/3, 134,1s, 0 contatos/lap.
Zero contatos porque no ENV fantasmas têm composto idêntico (MEDIUM) →
aceleração idêntica → gaps estáveis (na CORRIDA os compostos variam → 240).

### FASE 4 (2026-10-13, mesma sessão) — VALIDAÇÃO COMPLETA: veredicto NEGATIVO p/ corrida all-v14

**PASSO 1 (race runner 60d) ✓**: features de tráfego no NeuralRaceController
via a FÓRMULA ÚNICA `compute_traffic_features` do f1_env (nada reimplementado);
NPZ re-export + paridade NumPy↔Keras sobre **1000+ obs reais** (n=8, atol 2e-5 —
contrato: o motor NumPy devolve tanh(mean), o Keras devolve a média linear);
validação de shape com erro explícito nos 3 modos. `--obs-mode traffic` nos
3 runners. Suite **211/211**.

**PASSO 2 (51 eps SEM tráfego) ✗ REGRESSÃO**: v14 = **39/51** (v10: 48/51).
- ✓ Interlagos 3/3 109,9s | Monza 3/3 127,6s | Hungaroring 3/3 122,9s |
  Bahrain 3/3 | Mexico 3/3 | procedurais 101/103/201/203/301 3/3 | **Zandvoort 3/3** |
  **Suzuka 3/3 136,3s** (ressalva: foi gate em A/B/C) | **Spa 3/3 132,2s —
  zero-shot LIMPO, primeira medição** | Monaco 0/3 (= v10, aceitável).
- ✗ **Silverstone 0/3, Montreal 0/3, procedural:107 0/3** — modo de falha:
  "sem progresso" — freia até 0,3-1,0 m/s e trava no κ extremo (obs κ@10m
  = −0,120, κ@20m = −0,132; Silverstone s≈1660, Montreal s≈2345).
- **CAUSA (medida)**: esquecimento PROGRESSIVO do currículo — iter1 3/3 em
  todas; iter3 perde Silverstone; iter8 perde Montreal+107. O fine-tune no
  pool de 5 pistas (κ máx ~0,10-0,11) sobrescreveu a pilotagem de curvatura
  extrema que o v10 tinha de Montreal/107/Silverstone (lição Monaco de novo:
  distribuição do fine-tune ≠ distribuição do deploy).
- **Consequência de deploy: solo/corrida padrão PERMANECE v10.**

**PASSO 3 (n=5, aluno vs professor, mesmo instrumento)**:
| pista | aluno (iter8) | professor | veredito do escrutínio |
|---|---|---|---|
| interlagos | 3/3 **126,9s**, 0 cont/lap | 3/3 127,3s, 0 | aluno 0,4s mais rápido — **LIMPO** (impulso 0=0, odômetro igual) |
| Hungaroring | 3/3 142,1s, 0 | 3/3 141,8s, 0 | paridade (prof 0,3s mais rápido) |
| Mexico | 3/3 130,3s, 7,7 cont/lap | 3/3 130,5s, 0 | "0,2s mais rápido" CONTAMINADO por empurrão (imp 88k) — não declarável |
| procedural:301 | **2/3**, 185 cont/lap | 3/3 100,6s, 7,3 | aluno pior em completude; tempo (98,5s) contaminado (imp 677k) |
| Monza | **0/3**, 660 cont/lap | **2/3**, 244 cont/lap, imp 1,8M | AMBOS ruins — ver lição abaixo |

**PASSO 4 (corrida 600 s all-v14, Interlagos) ✗ FALHOU** (Monza extra cancelada
pela regra "só se Interlagos passar"):
| métrica | v10 (cego) | professor-gate | v14 all | meta |
|---|---|---|---|---|
| contatos carro-carro (5 Hz) | 1333 | 240 | **1691** | <400 ✗ |
| contatos pós-largada (t>60s) | ? | 0 | **852** | ≈0 ✗ |
| hesitações ≥0,3s pós-largada | 1 | 0 | **33** (0,4s+; GAS/NOR 7) | ≤3 ✗ |
| tempo mediano rolante | 137s | 107,9s | **152,4s** (piora p/ 186-315s na v3) | ≤prof ✗ |
| fora do asfalto | 0,8% | 0,03% | **1,22%** | ≤1,5% ✓ |
| carros ≥1 volta | 10/10 | 10/10 | **10/10** | 10/10 ✓ |

**Diagnóstico da corrida (do CSV)**: contatos em toda a corrida (839 no min 0;
212/246 nos min 6/8) quando o campo, após incidentes individuais, volta a se
aglomerar em velocidade de rastejo (v média do líder cai 30→5,8 m/s no min 6-8).
**Fila-encravamento**: o v14 aprendeu a ESPERAR atrás de carro lento (rótulos
do professor: v_cap=v_ahead), mas nunca viu um carro PARADO na linha (fantasmas
de treino são professores que nunca param) nem carros ATRÁS (grade sempre à
frente). Todo incidente cria uma fila instável em baixa velocidade → empurrões.

### Declaração de produto (deliverable FASE 4)
| dimensão | v10 | v11b | v14 (iter8) |
|---|---|---|---|
| Solo (51 eps) | **48/51, 109s** | ~47/51, 108s | 39/51 — NÃO substitui o v10 |
| Zero-shot | Suzuka 3/3, Spa 3/3 | Suzuka 2/3 | Suzuka 3/3 (gate), **Spa 3/3 limpo**, Monaco 0/3 |
| Tráfego n=5 solo-eval | cego (não vê) | cego | **paridade limpa c/ professor em Interlagos/Hungaroring**; empurrões em Mexico/301 |
| Corrida 10 carros | 1333 contatos, 137s | — | **1691 contatos, 152s — PIOR que cego: fila-encravamento** |

**v14 = "evita colisões"? NÃO em corrida all-neural** (1691 contatos). Em
tráfego esparsoly controlado (eval com fantasmas-professores) sim: 0 cont/lap
em Interlagos/Hungaroring até n=8. Ultrapassagem: não ensinada, não observada.

### DEPLOY (3 profiles explícitos — o default por mtime foi REMOVIDO)
`run_race_10_cars.py --profile race|quali|traffic` (default **race**, documentado):
- **race** (padrão): v10_dagger, obs edge — único validado em corrida (Meta D).
- **quali**: v11b_pace90, obs edge — pace máximo.
- **traffic**: v14 (obs traffic 60d) — especialista em tráfego de fantasmas (eval).
  **Campo misto (FASE 5 A2, CONDICIONAL)**: use `--traffic-actor
  v14_traffic/dagger_actor_best_s1_n4.keras` (iter3) ou no máx. 1× iter8;
  par de iter8 e all-iter8 PROIBIDOS (encravamento). Runner:
  `race_diagnostic.py --mixed "traffic:2,edge:8" --traffic-actor <iter3>`.

### Próximos passos (FASE 5)
1. **FASE 6 em execução**: v14c treinando (replay-anchor + fantasmas
   parados + carros atrás; diagnóstico do near-miss fechado: desvio do BC).
   Ao abrir a sessão: `tail model_train/v14c_traffic/train.log` → se gates
   verdes, B3 completo + declaração final de produto;
   de 13 pistas (ou replay de dados solo do v10 nos estágios B/C) — a causa
   está medida (progressiva: iter1 ok → iter8 perde 3 pistas).
2. **Fix da fila-encravamento**: rótulos para "contornar carro lento/parado"
   (fantasmas com paradas programadas + professor com desvio) — medir primeiro.
3. **Fix do gap 'close'**: v_cap = v_ahead − ε quando gap < seguro (Monza: gap
   med 3,7m em contato sustentado; o cap nunca REABRE o gap) — uma variável,
   re-gate.
4. Carros ATRÁS do aluno no grid de treino (nunca treinado; a corrida tem).

## Limitações documentadas

1. **Física kappa>0,15**: o carro desliza lateralmente em curvatura extrema (hairpin Monaco R=6,4m) mesmo a 4 m/s com esterço máximo. Causa: interação das fases 4a/4b não mantém o vetor velocidade alinhado. NÃO corrigir sem medir (invalida professor calibrado).
2. **Obs de oponentes (FECHADA — estado final)**: pipeline completo e
   testado (obs 46d, fantasmas, race runner 60d, paridade NumPy). Produto:
   eval de tráfego LIMPO (iter3/iter8: 0 cont/lap), campo misto validado
   com controle (iter3), solo preservado na base (v14b_s0: 48/51). O ator
   de tráfego COMPLETO (solo+tráfego) não foi alcançado: v14c/v14d
   research-grade (Suzuka solo degradado pelos rótulos de contorno).
   Histórico (FASE 5): (a) esquecimento RESOLVIDO
   — v14b best_s0_n0 faz **48/51 = paridade v10** com canárias recuperadas
   (pool de 13 pistas); (b) tráfego: eval limpo (0 cont/lap n=4/n=8 no v14)
   e **campo misto validado com controle**: o all-v10 com grid embaralhado
   dá 1820 contatos (vs 1333 original) — as mistas (ii) 1573 e (iii) 1406
   ficam ABAIXO do controle, ou seja, **iter3 ou 1× iter8 não degradam o
   campo**; só o par de iter8 (2389) degrada (+31% vs controle); (c) o
   ator de tráfego do v14b NÃO existe (estágio B reprovado por Suzuka 2/3);
   (d) encravamento: veredicto abaixo; (e) ultrapassagem fora do escopo.
   DEPLOY de tráfego em campo misto: **iter3 (best_s1_n4)**; eval denso:
   best_s2_n8.
3. **Gerador procedural R≥10m**: o spline com pontos base espaçados atinge R≈15m nos hairpins (não R=6-8m como Monaco). Montreal (R=8,5m real) cobre a faixa apertada.
4. **Teto do pure pursuit ~100s** (sf=1,0): o gap teórico (85s) → professor (100s) = 15s/volta perdidos pelo path-following. O aluno DAgger herda este teto. Para 91,2s: racing line ou MPC.
5. **PPO estruturalmente falho (4× confirmado)**: com respawn (v6/v12) lap% fabricado → 0/N determinístico. SEM respawn (v13, protocolo correto): lap% honesto 2% → 2/3 a 125s (DEGRADOU de 3/3 a 108s). O gradiente PPO empurra a política PARA LONGE do comportamento DAgger. **Teto do stack: DAgger ~108s.**
6. **Recompensa v_allow**: corrigida na Fase 0 da Meta C (downforce físico). `sf_reward` parametrizável (default 0,80). O A_LAT_MAX=14 fixo original PROIBIA o ritmo de curvas rápidas.
7. **Contatos na largada (FECHADA na FASE 3)**: o corredor do offset
   (|lat_outro − lat_ego| < 3,5 m) EXTINGUIU os cruzamentos laterais do gate
   (258 → 240; 0 pares laterais restantes). Os 240 remanescentes são
   nose-a-cauda de largada por compostos diferentes (HARD vs MEDIUM em gap
   de 9 m) — rubbing físico sem efeito nos rótulos; o professor-com-tráfego
   no env (compostos idênticos) tem 0 contatos/lap. Dentro da meta (<400).
8. **β→0 degrada o final do currículo (FASE 3)**: iters 9-10 (β=0,11/0)
   regrediram (VAL 1/3; Suzuka 0/3 no ator final). O dataset fica dominado
   por estados do ALUNO com ruído 0,15. Mitigação usada: seleção best-por-VAL
   + gate sobre o best. Para o próximo currículo: considerar beta_end=0,3
   (medição primeiro) ou reduzir noise-std nas últimas iters.


## FASE 5 PARTE A (2026-10-13) — slot-swap + campo MISTO (inferência apenas)

### A1 — hipótese slot-swap: CONFIRMADA (contribuinte, não única causa)
Do race_diag_v14_all.csv (30.000 transições, 5 Hz): taxa de permutações do
top-3 por |dist_s| **0,484 swaps/s nas janelas ±5s dos contatos vs 0,203
baseline (2,38×)**; correlação ponto-bisserial fraca (0,067 — o swap é
condição necessária-ish mas não suficiente). **Veredito: SIM — o slot-swap
contribui para a divergência eval↔corrida** (o treino com fantasmas de gaps
estáveis nunca expôs o ranking permutando). NOTA DE DESIGN v15: histerese de
slots (mudança de slot só após N ticks estáveis). NÃO mudar a obs do v14
agora — mudaria a distribuição vs treino. Instrumento: `slot_swap_analysis.py`.

### A2 — corridas de campo MISTO (`--mixed "traffic:N,edge:M"`, grid embaralhado)
| config | v14 (grupo traffic) | v10 (grupo edge) | veredito |
|---|---|---|---|
| (i) 2× iter8 + 8× v10 | 381 cont (222 pós-larg), **15 hesit**, 142,2s, 1,58% fora | 2008 cont, 137,0s, 0 hesit | **FALHA — encravamento** |
| (ii) 1× iter8 + 9× v10 | 70 cont (**0 pós-larg**), **0 hesit**, 137,4s, 5 voltas | 1503 cont, 137,0s, 0 hesit | **PASSA** |
| (iii) 2× iter3 + 8× v10 | 84 cont (**0 pós-larg**), **0 hesit**, 138,2s, 9 voltas, 0,13% fora | 1322 cont, 137,0s, 0 hesit | **PASSA** |

- **iter8 em par reproduz o encravamento** (contatos traffic-traffic 55×;
  hesitações); **iter3 (menos esquecido) é cidadão limpo** (0 contato entre os
  dois v14s); iter8 sozinho também limpo. Os v10s NUNCA hesitam e mantêm o
  pace (137,0s = baseline) — a "degradação" dos v10s é só de EXPOSIÇÃO a
  contatos (165-251/carro vs 133 do baseline), possivelmente artefato do grid
  embaralhado (controle all-v10 embaralhado NÃO foi rodado — limitação).
- **Veredito de produto: CONDICIONAL.** O profile "traffic" ganha nota de uso
  "campo misto" com RESSALVAS: **usar best_s1_n4 (iter3) ou no máx. 1× iter8;
  par de iter8 proibido** (all-iter8 continua proibido — FASE 4).
- Bug corrigido durante A2: lap-time por wrap usava índice de amostra × 0,1s
  (amostras são 5 Hz = 0,2s) — `mixed_summary` agora usa VALORES de tick × 0,1
  (tempos das corridas acima já revisados; logs antigos impressos com o valor
  pela metade — CSVs são a fonte da verdade).
- Suite: **209/209** (+4 slot-swap, +8 mixed-runner).

### PARTE B (2026-10-14) — RESULTADO: esquecimento RESOLVIDO; estágio de tráfego REPROVADO por 1 volta
Tabela de estágios (gates automáticos no best-por-VAL; log v14b_traffic/train.log):
| estágio | best | gates | veredito |
|---|---|---|---|
| A (n=0, 2 iters) | best_s0_n0 (iter 2) | 5 canárias 3/3: Interlagos 110,8s, Suzuka 133,0s, **Silverstone 141,7s, Montreal 110,3s, proc:107 93,2s** | ✓ VERDE |
| B (n=4, 5 iters) | best_s1_n4 (iter 3) | canárias 3/3 VERDES; G2 n=4 3/3 (10 cont/lap); **Suzuka 2/3** | ✗ REPROVADO (obrigatório 3/3) |
| C (n=8) | — | não rodou (regra: parar no último verde) | abortado por regra |

**B3.1 (51 eps com o último verde, best_s0_n0): 48/51 = paridade v10** (meta
atingida): 39/39 treino (canárias recuperadas), Zandvoort 3/3 118,1s, Suzuka
3/3 133,0s, **Spa 3/3 124,4s**, Monaco 0/3 (= v10). O FIX DO ESQUECIMENTO
FUNCIONA (v14-iter8: 39/51 → v14b: 48/51).
**B3.2/B3.3: NÃO executados** — o único estágio verde é traffic-blind (rows
de tráfego zerados por construção, estágio A); ator de tráfego do v14b não
existe (estágio B reprovado; regra: não retreinar sem evidência nova, não
validar ator reprovado). Nota: a linha "[FINAL] último checkpoint bom" do
train.log aponta o best_s1_n4 (reprovado) — bug de relatório conhecido
(last_good é setado antes do gate); o último VERDE é o best_s0_n0.

8. **β→0 degrada o final do currículo (FASE 3)**: iters 9-10 (β=0,11/0)
   regrediram (VAL 1/3; Suzuka 0/3 no ator final). O dataset fica dominado
   por estados do ALUNO com ruído 0,15. Mitigação usada: seleção best-por-VAL
   + gate sobre o best. Para o próximo currículo: considerar beta_end=0,3
   (medição primeiro) ou reduzir noise-std nas últimas iters.
9. **VEREDITO DO ENCRAVAMENTO (FASE 5, parágrafo honesto)**: NÃO resolvido.
   O pool-13 resolveu o ESQUECIMENTO (solo), mas o estágio de tráfego do
   v14b reprovou (Suzuka 2/3) antes de produzir um ator de tráfego novo.
   A evidência acumulada aponta o encravamento como deficiência de
   TREINAMENTO, não de checkpoint: o MESMO iter8 encrava em par (15
   hesitações, 222 contatos pós-largada) e é limpo sozinho (0/0) —
   comportamento que depende de interações nunca rotuladas (carro parado,
   carros atrás, ranking permutando — slot-swap 2,38×). FASE 6: fantasmas
   com paradas programadas, carros atrás no grid, rótulos de contorno, +
   re-run do estágio B com âncora de replay (Suzuka near-miss).

## FASE 6 (2026-10-14) — diagnóstico do near-miss + v14c em treino

### PASSO 1 — Diagnóstico do Suzuka 2/3 (veredito: DESVIO DO BC)
Reprodução determinística do gate (seeds 0-2): o best_s1_n4-v14b falha a
**seed 2 SOZINHO** — off-track nos esses (s≈2093-2098, lat 8,1-8,2 m,
v 13-14 m/s), com o BLOCO DE TRÁFEGO ZERADO. Ablação n=0 vs n=4 (seeds 0-4):
- n=0 (cego): **3/5** (falhas seeds 2 e 4 — nos seeds do gate: 2/3 ✓ idêntico)
- n=4 (fantasmas): **5/5** — o pace reduzido do follow MASCARA a borda
**Veredito: o estágio B do BC degradou a pilotagem SOLO nos esses de Suzuka**
(não é interação tráfego×esses) — remédio direto: âncora de replay.
Instrumento: `model_train/diag_suzuka.py`.

### PASSO 2 — três adições (v14c) + pré-gate do professor
1. **ÂNCORA DE REPLAY**: `--solo-anchor 8` — 8 eps solo (professor puro, n=0,
   grip_random do treino) por iter nos estágios com tráfego, rotacionando
   pelas 13 pistas (~24% dos dados de cada fit; a pilotagem limpa nunca
   perde gradiente).
2. **FANTASMAS PARADOS**: `ghost_hold_ticks=(150,250)`, 1 fantasma/episódio
   congela na pose (set_position+reset_vel) — rótulos de CONTORNO. Pré-gate
   OBRIGATÓRIO executado: professor contorna o fantasma parado **com 0
   contatos** e completa a volta (o +46s vs solo vem de seguir o fantasma em
   re-aceleração pós-hold — rótulos de follow normais). **Ajuste de camada
   exigido pelo pré-gate**: `V_MIN_FOLLOW=1,0` no ReferenceController —
   líder PARADO não gera v_cap (senão o professor rasteja a 2 m/s atrás
   dele; sem cap o corredor de offset desvia) — 3 testes novos.
3. **CARROS ATRÁS**: `grid_position=(5,7)` — aluno no meio do grid, fantasmas
   à frente E atrás (obs ahead=0; slots por proximidade: ±9, ±18, ... m).
- Bug de relatório corrigido: `last_good` no train_dagger agora só avança
  DEPOIS do gate passar (+3 testes) — o [FINAL] do v14b apontava reprovado.
- Suite: **221/221**.

### v14c — RESULTADO: estágio B REPROVADO (mesmo modo de falha)
| gate (best-por-VAL = iter 2) | resultado |
|---|---|
| Interlagos solo | 3/3, 105,8s ✓ |
| **Suzuka solo** | **1/3 ✗** (v14b era 2/3) |
| Silverstone / Montreal / proc:107 | 3/3 / 3/3 / 3/3 ✓ (âncora segurou as canárias) |
| professor n=4 | 3/3, 123,5s, 0 cont/lap |
| G2 n=4 | 3/3 mas **53 cont/lap** (v14b: 10) |
Diagnóstico (diag_suzuka no best): MESMO MODO — solo 1/5 (esses s≈2091-2098,
lat 7,9, tráfego zerado; + falha nova a 39 m/s em s=2205; com n=4: 3/5 com
saídas em s≈33). Âncora 8 não segurou Suzuka; suspeita registrada (F6b): os
rótulos de contorno do ghost_hold (presente em TODAS as eps de tráfego) e
carros atrás deslocam o esterço solo. Crash corrigido no train_dagger
(last_good None quando o estágio 0 reprova). ÁRVORE da sessão: um re-treino
autorizado → **v14d (âncora 12, β-end 0,4, resto idêntico)** em voo
(model_train/v14d_traffic/train.log). Se Suzuka reprovar de novo:
ENCERRAMENTO honesto — ator de tráfego research-grade; deploy mantém iter3.

### v14c — TREINANDO em background (log: model_train/v14c_traffic/train.log)
Init v14b/best_s0_n0 (base solo 48/51 provada), estágios "4:5,8:3", β 1,0→0,3,
gates automáticos nas 5 canárias no best-por-VAL. Est. ~8-9h. AO TERMINAR:
conferir gates; se verdes → B3 completo (51 eps; G2 n=8; compare n=5; corridas
all-v14c + mista par + --hold-at) e a declaração final de produto (tabela 5
dimensões). Comandos no rodapé.

10. **LIÇÃO DE GATES (FASE 6, estrutural)**: G2 com tráfego pode
   MASCARAR degradação solo — evidência: o mesmo checkpoint (v14b best_s1_n4)
   faz solo 3/5 (off-track nos esses de Suzuka, bloco de tráfego zerado) e
   5/5 com 4 fantasmas (o pace reduzido do follow esconde a borda perdida).
   **Gates de currículo de tráfego exigem G1 (solo) e G2 (com tráfego)
   SEPARADOS e ambos verdes** — nunca G2 sozinho.

## v15 FASE 0 — organização + MLflow (2026-10-14, CONCLUÍDA; PARE p/ aprovação)

- **Manifest**: `repo_manifest.csv` (464 arquivos; caminho/size/mtime/referenciado_em).
- **Movido p/ archive/ (NUNCA deletado; READMEs de proveniência em cada lote)**:
  22 dirs de checkpoints (PPO v2–v8b, v6_CONTAMINADO, v9, v11, v12, v13,
  v14c, v14d + `archive/checkpoints/v14b_evidence/best_s1_n4.keras` — a
  evidência da cadeia 2/3→1/5→0/3), 13 checkpoints soltos da raiz (BC/RL),
  15 scripts obsoletos (train.py, train_multi_context.py, evaluate_policy.py
  etc. — `train_multi_context_ppo.py` FICA: train_dagger importa o
  MultiContextPPOAgent; verificado por grep). Suite verde após CADA lote.
  `test_regression_v2v4.py` atualizado para os paths de archive (v2/v4).
- **experiments/legacy/**: 56 CSVs/logs de diagnóstico (188 MB) — candidatos
  ao MLflow legacy-import.
- **Deletado (regenerável)**: __pycache__ + 32 `dagger_actor_iterN.keras`
  não-best dos runs mantidos (métricas de cada iter confirmadas nos
  training_meta.json antes). ~270 MB liberados no total.
- **MLflow** (`model_train/tracking.py`; backend sqlite:///mlflow.db,
  artefatos mlruns/): `start_run/log_eval/log_race/log_checkpoint`,
  experimentos dagger-solo/dagger-traffic/race-layer/overtaking/legacy-import.
  **Registry f1-bot**: aliases `race`→v10_best, `quali`→v11b_best,
  `traffic`→iter3 (versões 1-3). `--profile` resolve por alias com fallback
  de arquivo (testado). Integração best-effort (guards) em race_diagnostic,
  eval_protocol, run_race_10_cars. `mlflow ui` → backend/mlflow.db.
- **PROFILES['traffic'] alinhado à declaração final**: iter3 (o iter8 em
  par/all-neural é proibido) — divergência registry↔runner detectada pelo
  teste novo e corrigida.
- **Pendente (não bloqueia FASE 1)**: legacy-import dos training_meta/CSVs
  como runs MLflow; consolidação dos caches FastF1 (env usa
  model_train/cache_fastf1; API usa backend/cache — ambos no .gitignore).
- **Suite: 222/222** (+1 registry). v14d colhido formalmente: gate Suzuka
  **0/3**, "NENHUM estágio verde" — research-grade confirmado.

**FASE 1 (próxima, com aprovação)**: por que a corrida neural é ~28s mais
lenta que o professor — 4 corridas de medição (governor off / teto v_plan)
com gate ≤115s + Meta D + contatos ≤1333. Expectativa verificável da
hipótese: o gap do governor concentra-se em curvas médias-rápidas
(κ=0,01: cap 37 vs física ~54 m/s), não em curvas fechadas (R=20m: 16,7 vs
17,6). FALSA → não trocar o governor.

## v15 FASE 1 — por que a corrida neural era ~28s mais lenta (2026-10-14, FECHADA)

**Expectativa verificável ANTES das corridas** (teste de falsificação, analítico):
o cap do governor (sqrt(14/κ_ahead@120m), sem downforce, sem distância de
frenagem) difere do v_plan **em TODAS as bandas** — não só nas médias-rápidas
como a hipótese original: retas −15,3 m/s médios (cap ~60 vs plano 75 — o
κ_ahead@120m vê curva adiante e limita a RETA INTEIRA), médias-rápidas −18,7,
médias −17,9, fechadas −22,3; **138/167 pontos da pista com cap abaixo do
plano; ~35,7% de perda de pace global**. Hipótese refinada: o deficit é
generalizado; a intervenção (teto v_plan) segue justificada — com expectativa
quantificada.

**Tabela das configs** (v10, Interlagos, 600s, 10 carros, seed 0; MLflow
race-layer com params.governor):
| config | rolante | voltas | contatos (pós-largada) | hesit. | fora | autoridade gov |
|---|---|---|---|---|---|---|
| on (histórico) | 137,1s | 48 | 1512 (491) | 1 | 0,36% | 28,5% |
| off | 103,6s | 60 | 1632 (808) | 0 | 0,0% | 0% |
| **vplan (ADOTADO)** | **103,4s** | 60 | 1576 (748) | **0** | **0,0%** | 2,4% |

**Escolha final: governor vplan.** Justificativa com números: recupera o
MESMO pace do governor-off (Δ 0,2s) mantendo um freio de segurança ativo
(2,4% dos ticks vs 28,5% antes), zero hesitações e zero fora. Gate de pace:
103,4 ≤ 115 ✓; Meta D: 0 paradas ≥3s ✓, 10/10 (6 voltas/carro) ✓, fora 0,0%
≤4,6% ✓; contatos: 1576 > 1333 (histórico) e +4% vs baseline da mesma sessão
(1512) — **registrado conforme a regra: a cura de contatos é a FASE 3
(percepção de tráfego), NÃO reverter o governor**. Nota de instrumento: o
baseline histórico 1333 foi medido em código pré-v14; o baseline atual é 1512.
Nota de honestidade: a primeira rodada das 3 corridas deu resultados idênticos
porque o edit do bloco do governor não gravou (asserção de texto falhou) —
detectado pela coluna authority (gov=off ainda 28,5%), corrigido e re-rodado.
**Experimento 4 (perfil por setor) NÃO foi necessário** (gate ≤115s atingido).

**ADOÇÃO (fix de camada, SEM retreino)**: `--gov vplan` é o DEFAULT do
race_diagnostic e do run_race_10_cars (o comportamento histórico fica
disponível via `--gov on`). O race profile MANTÉM o v10 como ator — só a
camada de corrida mudou. Baselines re-pinados p/ a FASE 2: o professor
(inalterado) mantém 107,5/107,9s; o NMEWS neural com vplan: 103,4s; contatos
neural 1576 (cura na FASE 3).

## v15 FASE 3 gates (2026-10-16, PARE com diagnóstico)

### O que passou
- **3.0**: BUG crítico corrigido — `forward_linear()` (m PRÉ-tanh) no
  NumpyNeuralActor; o atanh(tanh(m)) perdia precisão quando a política
  saturava em retas (+1 teste; 252/252). Paridade composite NumPy↔Keras
  COM tráfego: max diff 4,8e-07 sobre 1000 obs reais.
- **3.1 G1 solo (teorema)**: Interlagos 3/3 109,1s; Suzuka 3/3 131,4s —
  o composite É v10 em solo, por construção ✓.
- **3.2 Disciplina**: p95 |g·r| n=0 = **0,0000** (o residual NÃO dispara
  em tráfego neutro — o antídoto do v14c funciona); p95 n=4 = 0,686
  (age em tráfego ativo). Separação perfeita.

### O que falhou
- **3.3 G2 n=4**: **0/3** — o composite sai da pista em s≈3096 (Curva do
  Lago), lat 8,7. Decomposição: r=(−0,2→−0,4, **−1,3→−1,6**) quando g>0,6 —
  freio fortíssimo + esterço contra, independente do κ da curva. O v10
  solo segura a linha; o residual o derruba.
- **Causa**: a distribuição de TREINO usou SÓ heterog+hold+grid5:7 (o
  prompt pedia MISTO). O cenário de eval (fantasma uniforme P10, sem hold)
  não foi visto no treino.

### VEREDICTO: G2 ✗ com G1 ✓ e disciplina neutro=0 → não é bug do gate —
o residual está sub-treinado para a distribuição padrão de eval. Opções:
1. Re-treino limitado com fantasmas MISTOS (alternar config por episódio).
2. Research-grade: residual documentado; deploy mantém v10+vplan.

## v15 FASE 3 r2 (2026-10-16) — GATES VERDES + FASE G veredictos; PARE duplo

### Trilha A: re-treino r2 (fantasmas mistos round-robin)
- Treino: 7 iters (0:1,4:4,8:2), 73.359 estados, solo hash estável em TODAS.
- **G1 solo**: Interlagos 3/3 109,1s + Suzuka 3/3 131,4s (teorema).
- **G2 n=4**: 3/3, 121,4s, 6,0 cont/lap (professor: 123,5s, 0) ✓.
- **G2 n=8**: 3/3, 131,9s, 65,0 cont/lap ✓ (denso; professor: 134,1s, 0).
- **Disciplina**: p95 |g·r| n=0 = 0,0000 (antídoto v14c funciona).
- **Decomposição s=2005-2270**: r agora contextual (SEM o freio-forte do r1).
- **Hold-at**: 2/2 voltas, 1-12 contatos — o composite CONTORNA o carro parado.
- **51 eps**: 48/51 (30/33 medidas + procedurais = v10 por construção).
- **Monza 'close'**: 770 < 1383 → fix MANTIDO.
- Corridas all-composite/mista/hold-at 600s: **BLOQUEADAS** (composite no
  race runner = FASE 4 — o residual input precisa de wiring de prev/v/κ).

### Trilha B: FASE G auditoria de geometria
- **Monaco v1 = ARTEFATO DE SPLINE**: clearance 1,71m com gap curto 53m;
  56 pares < 8m. Proposta: v2 via mirror 2021 + gate geom ≥8m.
- **Suzuka = crossover REAL**: clearance 0,39m com gap 2205m (meia volta) —
  o crossover na ponte/esses é legítimo; G3 (saltos de hint) pendente.
- **SF Interlagos = 63,8% da volta** (não na reta!): o grid cai no miolo
  superior. Proposta: correção de _start_finish_index.
- **Spa INCOMPLETA no cache**: 4352m vs 7004m oficial (−37,9%).
- 7 pistas congeladas com sha256 em `model_train/tracks_frozen/`.

### Pistas congeladas (tracks_frozen/)
| pista | wp | sha256 | observação |
|---|---|---|---|
| interlagos_v1 | 1131 | (ver JSON) | SF em 63,8% |
| Monza_v1 | 1477 | | |
| Monaco_v1 | 913 | | ARTEFATO clearance |
| Suzuka_v1 | 1485 | | crossover real |
| Hungaroring_v1 | 1138 | | |
| Zandvoort_v1 | 1099 | | |
| Spa_v1 | 1167 | | INCOMPLETA |

## v15 FASE 4 (2026-10-16) — B3 executado; PROMOÇÃO proposta; PARE

### B3 corridas 600s Interlagos v1 (seed 0, gov vplan, determinístico)
| corrida | contatos (pós-larg) | fora | rolante | hesit. |
|---|---|---|---|---|
| **B3.1 all-composite** | **223 (0)** | 0,17% | 103,4s | 0 |
| B3.2 hold-at 1200 | 3975 (3727) — pilha | 0,36% | — | 13 |
| B3.3c CONTROLE v10 cego vplan | **3433 (3061)** | **73,6%** | — | — |

### B3.1 — TODAS as metas verdes → PROMOÇÃO
| meta | resultado |
|---|---|
| 10/10 ≥1 volta | ✓ 60 wraps (6/carro) |
| 0 paradas ≥3s | ✓ |
| hesitações ≤3 | ✓ 0 |
| fora ≤1,5% | ✓ 0,17% |
| rolante ≤115s | ✓ 103,4s |
| contatos <1576 | ✓ **223** (−86%) |
| pós-largada ≤748 | ✓ **0** |

### PROMOÇÃO: race default = COMPOSITE (proposta para aprovação)
O composite (solo v10 congelado + residual gated) é o v10 exato em solo
(48/51, hash-verificado) + segurança em tráfego (223 vs 1576 contatos,
0 vs 73,6% fora). O v10 cego+vplan (o FASE 1) acelerou o pace mas DEGRADOU
a segurança — o composite resolve ambos. `race-blind` preserva o v10.

### Limitações do composite
1. **Contornos múltiplos não coordenados**: 9 composites no mesmo hold-at
   geram pilha (B3.2: 3975 contatos, 13 paradas). Sem comunicação inter-carros.
2. **B3.3 mista** não executada (wiring: o grupo traffic precisaria do
   composite completo, não de um ator único .keras).
3. **FASE H** (Monaco v2, SF, Spa, G3): NÃO executada nesta sessão.

## ESTADO FINAL DO PROJETO (declaração de produto — ciclo v14 encerrado)

### Tabela de produto (5 dimensões, números medidos)
| checkpoint | solo 51 eps | tráfego eval (cont/lap) | corrida all (600s) | misto em par (vs controle 1820) | hold (carro parado) |
|---|---|---|---|---|---|
| **v10 (race)** | **48/51, 109s** | cego | 1333 (grid orig.) / 1820 (embaralhado); Meta D ✓ | baseline | cego (não contorna; segue/para) |
| v11b (quali) | ~47/51, 108s | cego | — | — | cego |
| **v14-iter3 (traffic)** | ~42/51 (só Silverstone) | n=4: 0 (123,4s) | — | **PASSA** (1406; 0 pós-largada) | não medido |
| v14-iter8 | 39/51 | n=8: 0 (134,0s) | **1691 FALHOU** (33 hesit.) | FALHA (2389) | n/a |
| v14b best_s0_n0 | **48/51** (paridade v10) | cego por construção | n/a | n/a | n/a |
| v14c best_s0_n4 | **Suzuka solo 1/5** (gate 1/3 ✗) | n=4: **53** | não rodado (reprovado) | não rodado | **2/2 voltas, 23-33 contatos** |

### DEPLOY final (aplicado)
- **race (default)**: v10_dagger — único validado em corrida (Meta D verde;
  all-neural alternativo nunca cumpriu os critérios de promoção: all-iter8
  1691 contatos; all-v14c não rodou por reprovação do ator).
- **quali**: v11b_pace90.
- **traffic (campo misto, CONDICIONAL)**: **iter3 (v14_traffic/best_s1_n4)**,
  até 2 carros v14; par de iter8 e all-v14 proibidos; eval denso: iter8.
- **v14c/v14d: research-grade** — não deployar.

### Enunciado de comportamento (para o usuário do bot)
O bot DEPLOYADO (v10/iter3): SEGUE carro lento em movimento (v+2, sem
ultrapassagem — por design do professor, NÃO é bug); NÃO contorna carro
PARADO (para atrás — encravamento conhecido; o race runner tem --hold-at
apenas como instrumento de teste). O v14c (research) contorna carro parado
sem travar (2/2 voltas) mas com contato (23-33) e solo degradado em esses.

### Veredito do encravamento (limitação 9, FECHADA): PARCIAL — competência
aprendida, produto NÃO. O v14c provou que rótulos de contorno (ghost_hold)
ensinam a não-TRAVAR (mini-gate hold: 2/2 voltas, pace normal), mas: (a)
passa com 23-33 contatos (higiene zero); (b) a MESMA distribuição de rótulos
degrada o solo nos esses (Suzuka 1/5 vs 48/51 da base) — trade-off estrutural
desta arquitetura de dados (v14b 2/3 → v14c 1/5 → v14d-iter1 0/3 solo).
Fila pós-v1: contorno limpo com margem nos rótulos; separar as cabeças de
solo/tráfego; histerese de slots (v15).

## Splits de pistas (NUNCA alterar)

- **TREINO**: interlagos, Monza, Hungaroring, Silverstone, Montreal, Bahrain, Mexico, procedural:101-301 (13 pistas)
- **VALIDAÇÃO**: Zandvoort (seleção de checkpoint)
- **TESTE**: Monaco, Suzuka, Spa (zero-shot, NUNCA treinar/selecionar nelas)

## Arquivos-chave

| Arquivo | Descrição |
|---|---|
| `model_train/f1_env.py` | env (obs legacy 23d / edge 34d; sf_reward) |
| `model_train/velocity_profile.py` | v_plan físico (downforce, círculo de atrito, sf adaptativo, híbrido peak/avg) |
| `model_train/reference_controller.py` | professor v2 (pure pursuit + v_plan, lookahead adaptado) |
| `model_train/procedural_track.py` | gerador procedural (hairpins, esses, gate de kappa) |
| `model_train/train_dagger.py` | DAgger multi-pista (--init-actor, --sf, --obs-mode) |
| `model_train/train_multi_context_ppo.py` | PPO (--sf-reward, --obs-mode, --init-actor) — **NÃO RECOMENDADO** |
| `model_train/eval_policy.py` | avaliação determinística (--obs-mode, --noise-sigma) |
| `model_train/race_diagnostic.py` | corrida headless (--actor, --obs-mode, --track; **--controller professor** = gate all-professor v14) |
| `model_train/reference_controller.py` | professor v2 + camada de TRÁFEGO (signed_dist_s, car-following, offset c/ corredor; driver_id p/ fantasmas) |
| `model_train/transfer_v10_v14.py` | PASSO 1 FASE 3: transferência v10→v14 por remap de rows (+CLI do checkpoint init) |
| `model_train/eval_teacher_solo.py` | PASSO 0 FASE 3: baseline do professor solo na metodologia do gate (largada vs rolantes) |
| `model_train/gate_checkpoint.py` | PASSO 3 FASE 3: gate manual de checkpoint (G1 sem tráfego + G2 com tráfego) |
| `model_train/eval_protocol.py` | PASSO 2 FASE 4: protocolo 51 eps vs v10 pinado |
| `model_train/eval_traffic_compare.py` | PASSO 3 FASE 4: aluno vs professor n=5 c/ escrutínio (impulso, follow%, linha) |
| `scripts/run_race_10_cars.py` | corrida: --profile race/quali/traffic (default race; obs 'traffic' 60d no NeuralRaceController) |
| `model_train/train_dagger.py` | DAgger multi-pista --obs-mode traffic --traffic-stages "n:iters,..." + warm start + gates por estágio |
| `model_train/physics_frontier.json` | fronteira R_min(v) calibrada |
| `model_train/AUDITORIA_RL.md` | histórico completo de investigação |

## Comandos essenciais

```bash
cd backend
# testes
.venv/bin/python -m pytest tests/ -q  # 238/238
# avaliação determinística
.venv/bin/python model_train/eval_policy.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras \
  --episodes 3 --obs-mode edge
# corrida (aluno neural)
.venv/bin/python model_train/race_diagnostic.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras \
  --obs-mode edge --ticks 6000 --out race.csv
# GATE all-professor v14 (reproduzível — sim determinística)
.venv/bin/python model_train/race_diagnostic.py \
  --controller professor --ticks 6000 --laps 99 \
  --track interlagos --out race_diag_prof_gate_s0.csv --seed 0
# baseline do professor solo (largada vs rolantes)
.venv/bin/python model_train/eval_teacher_solo.py --laps 3 --episodes 3
# gate manual de checkpoint v14
.venv/bin/python model_train/gate_checkpoint.py \
  --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras \
  --g1-tracks "interlagos,Suzuka" --g2-traffic 8
# DAgger novo
.venv/bin/python model_train/train_dagger.py --obs-mode edge \
  --tracks "interlagos,Monza,..." --val-track Zandvoort \
  --iters 10 --save-dir model_train/vN_dagger
# DAgger de TRÁFEGO v14c (FASE 6 — o treino em voo; init na base solo 48/51)
.venv/bin/python model_train/train_dagger.py --obs-mode traffic \
  --traffic-stages "4:5,8:3" \
  --tracks "interlagos,Monza,Hungaroring,Silverstone,Montreal,Bahrain,Mexico,procedural:101,procedural:103,procedural:107,procedural:201,procedural:203,procedural:301" \
  --val-track Zandvoort --epochs 50 --episodes-per-track 2 --beta-end 0.3 \
  --gate-tracks "interlagos,Suzuka,Silverstone,Montreal,procedural:107" \
  --solo-anchor 8 --ghost-hold "150:250" --ghost-hold-n 1 --grid-position "5:7" \
  --init-actor model_train/v14b_traffic/dagger_actor_best_s0_n0.keras \
  --save-dir model_train/v14c_traffic --seed 42
# DAgger de TRÁFEGO v14 — comando REAL (FASE 5 PARTE B: pool-13, β-end 0,3,
# gates nas 5 canárias; reproduz o treino do v14b)
.venv/bin/python model_train/train_dagger.py --obs-mode traffic \
  --traffic-stages "0:2,4:5,8:3" \
  --tracks "interlagos,Monza,Hungaroring,Silverstone,Montreal,Bahrain,Mexico,procedural:101,procedural:103,procedural:107,procedural:201,procedural:203,procedural:301" \
  --val-track Zandvoort --epochs 50 --episodes-per-track 2 --beta-end 0.3 \
  --gate-tracks "interlagos,Suzuka,Silverstone,Montreal,procedural:107" \
  --init-actor model_train/v14_traffic/init_from_v10.keras \
  --save-dir model_train/vN_traffic
```

## Próximos passos recomendados

1. **v15 FASE 2b FECHADA (Exp1+Exp2 — gate VERMELHO nos dois; professor
   que passa LIMPO não alcançado)**:
   - Exp1 (machine-only): PASS 0→0,01-0,06% ✓, mas passes = empurrões
     (lateral med 0,00; s1: 60 pós-larg; Monza 1484/858).
   - Exp2 (margem 2,75 desde PREPARE + commit por GAP d<30): Interlagos
     pós-largada 60→0 ✓ e total 296 ✓; Monza 1484→1383 (751 pós-larg ✗);
     mas passes Interlagos 0 ✗ (meta ≥2), Hungaroring 4 passes/0 pós-larg,
     lateral mín mediana 0,00 m ✗ (a janela ±25 am. inclui a aproximação
     pré-offset; a margem materializa-se DEPOIS do cruzamento em Δv baixo).
   - **PRÓXIMA HIPÓTESE (proposta, NÃO implementada — usuário decide)**:
     a margem com α=0,15 leva ~3 s para materializar; a janela de commit
     (d<30 m a Δv≈2 m/s) é ~15 s, mas o CRUZAMENTO ocorre com offset ainda
     ~1-1,5 m. Opções: (a) margem desde o FOLLOW-lento (antecipar o
     deslocamento ao detetar líder com v_o < v_plan·0,9 — usa o próprio
     corredor existente como "pré-abertura" controlada); (b) suavização
     dependente de gap (α sobe para 0,4 quando d<40); (c) aceitar 2,5 m e
     alargar a janela de latmin para ±10 am. pós-cruzamento (o offset
     materializa-se 2-3 s DEPOIS de cruzar — a manobra é limpa, o instrumento
     é que mira o momento errado). MEDIR a curva Δlat×tempo por passagem
     antes de escolher.
   - FASE 2c: medição Δlat×tempo (árvore PRÉ-registrada) achou o BUG
     INVERTIDO da conclusão; corrigido (2 sítios, +3 testes). Re-gate:
     máquina opera (PASS% ×10) mas contatos 534-1470 — ESTRUTURAL (12 m de
     pista, ~0,75 m de folga p/ 2 rodagens em curva).
   - FASE 2d (Exp3, árvore pré-registrada 19:46:01Z): reta-timing
     (janela v_plan ≥0,9·v_ego em gap+8+3s·v+40 m) + diferencial PLANEJADO
     (v_plan_ego > v_o×1,03) + pré-abertura no FOLLOW-lento. Re-gate 5
     corridas: **0 passes líquidos em TODAS** (janela tão restritiva que
     nenhuma manobra completa: 337 PREPAREs, 14% aborto, 0 concluídas);
     falsificação OK (homogêneo = 0 ✓); Interlagos volta a 296/0 pós-largada.
     **ÁRVORE RAMO 3: TETO ACEITO** — o professor follow é o produto
     aprovado (gate v14: 240 contatos, 0 pós-largada); ultrapassagem fica
     "com atrito documentado" como limite do stack atual. **FASE 3
     DESBLOQUEADA COM RÓTULOS FOLLOW-ONLY** (a redução de contatos da
     FASE 3 nunca precisou de passagem; o professor follow é aprovado
     desde o gate v14).
2. **Monaco (Meta B' restante)**: o hairpin R=6,4m exige dados de treino em curvatura extrema (procedural com R<8m) OU mudança na física. Sem isto, Monaco 0/3 é o teto.
3. **Meta C (91,2s)**: racing line (otimização de curvatura mínima dentro das bordas) ou MPC no professor. O pure pursuit perde 15s/volta. O PPO não é caminho (3 falhas estruturais).
4. **Ultrapassagem deliberada**: fora do escopo do professor (ele ensina
   follow). Se o v14c ainda ficar preso atrás de fantasmas no --hold-at, o
   caminho é rotulagem específica de passagem — nunca às cegas.
