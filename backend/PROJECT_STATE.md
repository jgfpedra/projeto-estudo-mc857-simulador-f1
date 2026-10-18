# PROJECT_STATE.md — F1 RL Bot: estado do projeto

> **Toda sessão futura começa por: ler este arquivo e AUDITORIA_RL.md.**
> Última atualização: **FASE R13-FECHAMENTO (housekeeping, zero runs): erratas E1-E5 auditáveis (manchete corrigida: 1,5-3,5× menos contatos; contato×carro-fora 28-44%; adversos 0-9 = {2,8,9} confirmado n=3 — vereditos inalterados); CSV v3.3 ADITIVO commitado com bit-identidade PASS (res_16d por tick p/ rota 2; sha universal do residual); DECLARAÇÃO FINAL DE PRODUTO colada como seção canônica: v10-cego = race default; composite research-grade com vantagem de segurança consistente; alavanca = percepção no retorno. Ver FASE R13-FECHAMENTO.**
> (anterior: FASE R3 (fix do absorvedor + gate multi-realização): branch hotfix/instrument-repair. ABSORVEDOR MORTO — rejoin por BEARING: excursão de 40 m recupera em 15,7 s (vs 500+s/never em R2); teste sintético PASS; contatos/pós-largada/voltas melhoraram em TODAS as seeds (pós-largada ≤100 pela primeira vez). GATE MULTI-REALIZAÇÃO VERMELHO por OUTRA causa: pilotagem — 96% das 253 excursões de s0 começam SEM contato (v med 14 m/s, todos os setores): o composite sai da pista 2-3×/carro/volta em tráfego denso; fora-pilotagem 6% > 1,5%, rolante 190 s > 115. Promoção PERMANECE SUSPENSA. — Ver seção FASE R3.)**

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
| v15_residual/residual_best (r2) | Residual gated 16d (FASE 3 r2) | **COMPOSITE = braço A** (research-grade; gate R10: mantido, ver R13) | contatos 3-4× menores que v10-cego; fora 29-54% |
| v15_residual/residual_weave_r12b | BC janelas weave/slide 16d | **RESEARCH-NEGATIVO — ENCERRADO (R12-PILOTO)**: piloto VERMELHO (fora +6,6pp, cc +114% no s0); autópsia: skew 12d (treino zeros/serve vivos), mudança de estilo nos ticks g>0; valor: hesit −54% s0, pós-60s −64 s9 | NÃO deploya; rotas 2/3 no backlog com pré-condições |
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
- **SF Interlagos = 63,8% da volta** — ~~não na reta!~~ **CORREÇÃO R2/R3: o
  veredicto "errado" foi REFUTADO.** SF 729 é a linha FIA real (heading 55°,
  reta de 45 m antes); toda a base de evidência verde (B3.1/B3.2/B3.3c/v14)
  foi medida com ela. O "não está na reta" vinha do detector de retas do
  audit, que não separa curva suave de reta em polilinha real (a pista
  frozen não tem reta >280 m em critério algum); a função pura
  find_best_start_waypoint herda esse defeito e escolheu um SWEEPER (929) —
  refutado em B3.1-v2 (1352 contatos, 68% fora). SF canônico = **729**.
- **Spa INCOMPLETA no cache**: 4352m vs 7004m oficial (−37,9%).
- 7 pistas congeladas com sha256 em `model_train/tracks_frozen/`.

### Pistas congeladas (tracks_frozen/)
| pista | wp | sha256 | observação |
|---|---|---|---|
| interlagos_v1 | 1131 | (ver JSON) | SF 729 = linha FIA (verdade canônica) |
| **interlagos_v2** | 1131 | 164876196eb12174 | **CANÔNICO: SF 729** (json autoritativo no loader) |
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

## v15 FASE R2 (2026-10-17) — unificação do SF + re-medida B3.1-v2: VERMELHO; caos + rejoin são as causas

### S1–S4 (unificação)
- **S1**: `find_best_start_waypoint(waypoints)` extraída como função PURA (geometria, sem estado de env).
- **S2**: validação cruzada IMPOSSIBILITADA — FastF1 offline (circuit_info 401; cache existe mas não carrega). Env standalone cai no preset 240wp (SF 109). A pista frozen (1131wp, 4160,4m) é a ÚNICA via para a geometria real.
- **S3**: `interlagos_v2.json` criado com SF 729→929 (função pura, 81,4% da volta).
- **S4**: loader prefere v2; env usa a função pura. Testes de contrato verdes (48+1 skip).
- **BUG DO S4 ENCONTRADO NA RE-MEDIDA**: `load_track_frozen` fazia OVERRIDE do sf_idx do json com a função pura em runtime (herança do FASE R) — o json era peso morto. B3.1-v2 (json SF929) e o run FASE R (json v1 SF729) rodaram IDÊNTICOS (1352 contatos bit-a-bit) porque ambos usaram SF 929 por override. **CORRIGIDO: o sf_idx do json é AUTORITATIVO** (a função pura é a ferramenta que GEROU o valor, não um reajuste em runtime).

### S5 — re-medida (gate B3.1: 10/10 voltas, 0 paradas≥3s, hesit≤3, fora≤1,5%, rolante≤115s, contatos<1576, pós-larg≈0)
| realização | cc | pós-60s | fora | voltas | veredicto |
|---|---|---|---|---|---|
| B3.1 verde (live, seed 0) — registro histórico | 223 | 0 | 0,17% | 10/10 | VERDE (realização ÚNICA) |
| frozen SF929 (v2 original, seed 0) | 1352 | 1260 | 68,2% | 7/10 | ✗ largada no sweeper |
| frozen SF729 seed 0 | 309 | 128 | 60,3% | 7/10 | ✗ |
| frozen SF729 seed 1 | 211 | 82 | 45,9% | 9/10 | ✗ |
| frozen SF729 seed 2 | 271 | 120 | 49,5% | 10/10 | ✗ |

- **SF 929 REFUTADO**: o "best straight" da função pura é um sweeper com quebras de 2,3-2,6°/wp a cada ~35m (o detector de reta não separa curva suave de reta em polilinha real); a pista frozen não tem reta >280m em nenhum critério. A âncora empírica de TODA a base verde (B3.1/B3.2/B3.3c/v14) é SF 729 (reta de 45m, heading 55° — linha FIA real). **interlagos_v2.json RECONSTRUÍDO com sf_idx=729** (sha256 164876196eb12174), sf_method documentando a refutação.
- **Diagnóstico dirigido (árvore pré-registrada)**:
  - *g active%*: instrumento composite VIVO (g>0 25-27% vs 33% verde; r_norm ≤~3 na largada em ar limpo). r_norm 20-40 observado é SINTOMA OOD (carros fora de pista projetam s/lat lixo que envenenam as features de tráfego de TODOS), não causa.
  - *fora por setor*: colapso é na LARGADA (t=4-46s, s 2655-2820/0-80) — pares de colunas colidem em cadeia (PIA↔RUS, SAI↔PER, ALO↔GAS), carros lançados a 45-100m da pista.
  - *hint resync*: projeção EXONERADA — a divergência de sinal lat_s×obs4 (~43-50% dos ticks) é ARTEFATO DE CONVENÇÃO do CSV diagnóstico, presente também em todos os runs verdes (v14_all: 43%). O grid físico é correto (±1,9m alternados, confirmado por obs4; a coluna `lat` do CSV tem convenção invertida — CAVEAT de instrumento).
- **CAOS A/B (decisivo)**: v14-actor live (verde: 1691cc, 1,2% fora, lat_max 16m) vs v14-actor frozen (1871cc, ~66% fora): trajetórias IDÊNTICAS por 13-21 ticks (diferença ≤cm), depois UM flip de threshold (VER t=2,1s: v≈21,0 → verde acelera, frozen freia) e a cascata acoplada por contatos diverge o fim completamente. Fonte da perturbação: nível float (json é float64 exato; candidatas: atributos do Track live [length_m explícito 4309 vs computado 4160 — sem efeito pré-volta-1 identificado], ordem de soma, estado pybullet). **Conclusão: a largada de 10 carros a 3,8m de separação lateral é um sistema caótico; o gate de 1 realização/600s não é instrumento sombro para ele.**
- **MODO DE FALHA REAL (novo, produto)**: carro lançado >20m fora NUNCA recupera — rejoin (th 0,35, teto 8 m/s) + recovery (saída só com progresso físico) não vencem o grip da grama a 50-100m; carros encravam a v≈1,5 m/s por 500+s (seed 0: 6 carros; seeds 1-2: parcial — reentraram e laparam a 136-205s). Este modo NUNCA foi exercitado na era verde (nada saiu >16m).

### S6 — VEREDICTO
**B3.1-v2 = VERMELHO (3/3 seeds). Promoção do composite PERMANECE SUSPENSA.** Contatos passam (211-309 < 1576) e os sobreviventes correm a pace (VER 136s c/ tráfego), mas fora-de-pista (46-68%) e pós-largada (82-128) falham consistentemente. Os números verdes do B3.1 (223/0/0,17%) são uma realização única, não reproduzível — NÃO são fraude nem regressão do composite: são sorte de realização num sistema caótico + um modo de falha (grama profunda) que a realização verde não visitou.

### Artefatos R2
- `model_train/tracks_frozen/interlagos_v2.json` — CANÔNICO, sf_idx=729, sha256 164876196eb12174.
- `model_train/tracks_frozen/interlagos_sf729_v2.json` — variante de diagnóstico dos runs S5d (idêntica em sf_idx; manter por proveniência dos CSVs).
- CSVs: `race_diag_b31_v2.csv` (SF929 s0), `race_diag_b31_v2b_sf729.csv` (s0), `race_diag_b31_v2b_seed1.csv`, `race_diag_b31_v2b_seed2.csv`, `race_diag_v14all_frozen_sf729.csv` (gov vplan — confundido), `race_diag_v14all_frozen_gvon.csv` (A/B do caos).
- Loader: `load_track_frozen` json-autoritativo; `_env_adjust_sf`/`_F1EnvSFAdjust` removidos (mortos).

## v15 FASE R3 (2026-10-17) — fix do ABSORVEDOR (rejoin por BEARING): absorvedor MORTO; gate multi-realização VERMELHO por pilotagem

### M0 — hipótese única (verificada, CSVs R2): o rejoin tinha ALVO DE VALOR, não de DIREÇÃO
Fora do asfalto comandava esterço FIXO saturado (±0,79 rad); na grama o crawl
equilibra a v≈1,45-1,5 m/s e esterço constante = ÓRBITAS de ~3 m (heading varre
360°: sin(herr) −1,0→+1,0). PER oscilou lat 20,7-78,1 m por 500+s; NOR 861 m
de excursão. Recovery nunca re-engata (saída exige v≥3,0, inalcançável na grama).

### M1 — pré-registro 2026-10-17T12:54:27Z (dsh): árvore do fix + gate multi-seed

### F1 — fix (UMA variável: a LEI DE ESTERÇO do rejoin)
`steer = clip(REJOIN_BEARING_GAIN·wrap(bearing−heading), ±STEER_MAX)` ao ponto
de re-entrada (projeção + REJOIN_AHEAD_M=10 m na linha central). Quadro físico
(x, y, heading do mundo) — imune às convenções de sinal da obs. th 0,35, teto
8 m/s, recovery, gate e governor INALTERADOS.
**Teste sintético PASS** (tests/test_deep_rejoin.py): carro a 40 m, v=0, heading
tangencial → asfalto em **15,7 s** (v 8,8 ao re-entrar), v_max 31,9 m/s pós,
progresso 1808 m — vs. absorvedor R2 (500+s, nunca).

### V1/V2 — B3.1-v3 (3 seeds, frozen v2 SF729, composite, gov vplan, 600 s)
| seed | cc | pós-60s | fora | pilot/preso (ticks) | voltas | rolante | hesit | paradas |
|---|---|---|---|---|---|---|---|---|
| 0 | 251 | 68 | 43,3% | 1758 / 11244 | 10/10 | 322 s | 14 | 0 |
| 1 | 158 | 58 | 49,4% | 1812 / 13009 | 10/10 | 186 s | 36 | 0 |
| 2 | 267 | 64 | 52,8% | 2007 / 13818 | 10/10 | 191 s | 46 | 0 |

**Efeito ISOLADO do fix (mesma seed, R2→R3)**: absorvedor MORTO — excursões
profundas agora duram 6-33 s e o carro VOLTA (R2: 500+s e nunca; 22-30
episódios/carro, todos resolvidos). Contatos 309→251 / 211→158 / 271→267;
pós-largada 128→68 / 82→58 / 120→64 (todas ≤100 pela primeira vez);
voltas 7/10→10/10 (s0). Off% s0 melhora (60,3→43,3) mas s1/s2 pioram
(45,9→49,4; 49,5→52,8): carros que R2 absorvia agora VOLTAM ao tráfego.

**GATE (pré-registrado): VERMELHO.** PASS: contatos (mediana 251 < 1576),
pós-largada (64 ≤ 100), paradas (0), voltas (10/10). **FAIL: fora-pilotagem
(mediana 6,04% > 1,5%), rolante (190 s > 115), hesitações (14-46 > 3),
preso-por-janela (critério lat>20 atingido)**.

### Decomposição dirigida (árvore: vermelho → decompor → PARE)
- **Pilotagem REAL**: 243/253 (96%) das excursões começam SEM contato,
  v mediana 14 m/s, em TODOS os setores — o composite sai da pista ~2-3×/
  carro/volta em tráfego denso (R2 filtrava isso: os carros errantes eram
  absorvidos e os limpos corriam soltos). NÃO é pinball de contato (4%).
- **Hesitações**: paradas de v<0,5 m/s, duração mediana 0,6 s, 8/14 sob
  authority=policy — micro-freagens em tráfego, não encraves.
- **Preso-por-janela**: artefato do critério — janela 30 s com lat>20 conta
  excursões RECUPERADAS; o absorvedor R2 (permanente) tem 0 ocorrências em
  30 carro-seeds. **O critério "lat>20" como proxy de preso ficou obsoleto
  com o fix** — a próxima revisão do gate deve medir preso por "não-retorno
  em T s", não por profundidade.
- **Modo residual novo (1/30 car-seeds)**: VER s0 t 566-600 — após impacto
  42→0 m/s sem contato carro-carro, heading ≈90° à pista, o carro crawl para
  FORA a 1,7 m/s com bearing saturado correto e rotação ~30× mais lenta que
  a cinemática (v_x≈0 degenera o modelo lateral); estava RECUPERANDO no
  horizonte (lat 38,8→33,9 caindo, sin(herr) passando a negativo). Modo
  lento pós-spin, não permanente — caracterizar na próxima fase.

### Protocolo padrão (vigor a partir de R3)
- **Multi-realização**: gate de corrida = mediana de ≥3 seeds + critérios
  por-seed; NUNCA 1 realização (R2 provou: 0,17% vs 46-68% entre realizações
  do mesmo sistema).
- **Fonte da pista em todo log**: runners imprimem "[diag] pista FROZEN:
  <nome> | <n> wp | SF wp <idx>" (vigorante); evals de ENV não valem como
  gate (FastF1 offline = preset 240wp silencioso).
- Gates de ENV não colher (regra R2/R3); solo se avalia só por registro.

## v15 FASE R4 (2026-10-17) — A DOENÇA VISÍVEL decomposta: NÃO é pilotagem do residual; é contato sub-amostrado + ping-pong de re-entrada

### Pré-registro: 2026-10-17T14:04:42Z (árvore + critério PRESO NOVO: episódio
### off-track >60 s sem retorno — vale para TODOS os gates futuros).

### M0a — 755 excursões (3 seeds v3) = 272 RAÍZES + 483 ECOS (64%)
Eco = excursão ≤10 s após a anterior do mesmo carro (ping-pong de re-entrada).
**76% do TEMPO off-track são ecos** (6.601 s de 8.730); raízes duram mediana 6 s.
- **Raízes (272): 70% PROXY contato-não-amostrado** (|Δv|>2 m/s em ≤2 ticks s/
  contato registrado — 95 c/ brk≤0,3 = impulso puro; 95 c/ brk>0,3 = freio
  próprio forte). Pilots raiz: só 82 (30%) — residual manda 42 (51%),
  solo 39 (48%), nenhum ramo ≥60%.
- O "96% sem contato" do R3 era ARTEFATO: o contato 5 Hz perde empurrões
  curtos (regra 2 do R4 acertou). Excursão ≠ incidente: o R3 media ecos.
- Perfil dos ecos: v med 10 m/s (cap do rejoin), esterço saturado, reta
  (κ≈0), dur med 9 s, lat med 19 m — re-entra desalinhado, o solo corrige
  bruto, sai do outro lado.

### M0b — hesitações (96): modo freio-forte do residual em SÓ 12%
g med=0,00 e brk med=0,00 nelas; 66% ocorrem OFF-TRACK (crawl de re-entrada).
**Suspeita "residual OOD freio-forte": FALSIFICADA como dominante.**

### M0c — REJOIN-GERADOR: 68% dos contatos pós-60s envolvem carro
### re-entrado <10 s antes (limite da árvore: 30% — DISPARA)
O rejoin do R3 (bearing) traz o carro de volta SEM PERCEPÇÃO — re-entra
na frente/ao lado de carros a caminho → novo contato → novo fling → ecos.

### C1 — denominador de produto (mesmo instrumento, 3 seeds)
| run | cc | pós-60s | fora | voltas | rolante | preso>60s (carros) | hesit on-track |
|---|---|---|---|---|---|---|---|
| cego s0 | 904 | 370 | 33,8% | 10/10 | 148 s | 0 | 4 |
| cego s1 | 588 | 130 | 35,5% | 10/10 | 166 s | 0 | 6 |
| cego s2 | 946 | 406 | 38,1% | 10/10 | 164 s | 0 | 6 |
| comp s0 | 251 | 68 | 43,3% | 10/10 | 322 s | 0 | 12 |
| comp s1 | 158 | 58 | 49,4% | 10/10 | 186 s | 5 | 13 |
| comp s2 | 267 | 64 | 52,8% | 10/10 | 191 s | 4 | 8 |
**O composite tem 3-4× MENOS contatos que o v10-cego** (med 251 vs 904) e
pós-largada 5-6× menor (64 vs 370) — a percepção de tráfego FUNCIONA e é o
valor de produto. Mas paga com mais off-track (ping-pong) e pace pior.

### Modo WANDERER (novo, preso>60s no critério novo): 9/30 carro-seeds
Episódios 60-102 s, lat até 300 m, v 0,2-9 m/s, heading 25-90° errado,
esterço saturado, g=0. Mecanismo candidato (a caracterizar na R5): a
projeção global-argmin salta de BRAÇO da pista a >100 m → alvo de re-entrada
instável → carro vagueia; + rotação lenta a v_x≈0 (modo pós-spin do R3).

### ÁRVORE EXECUTADA (pré-registrada 14:04:42Z)
> **RETRATAÇÃO R5a**: o ramo 1 ("70% contato-não-amostrado") abaixo era
> baseado no PROXY |Δv|>2 m/s — o instrumento solver-side refutou: só 12-20%
> das raízes têm impulso 10 s antes. O proxy capturava frenagem própria +
> entrada na grama. Os ramos rejoin-gerador (68%) e o claim C1 também foram
> re-pinados na R5a (mediana 23%; sem vantagem em contatos). Ver FASE R5a.
1. **"contato-não-amostrado domina o proxy" (70% das raízes) → corrigir o
   INSTRUMENTO de contato antes de qualquer interpretação** — pré-requisito
   de R5: log de impulso/Δv por sub-step físico (o gate atual SUBCONTA).
2. **"rejoin-gerador ≥30%" (68%) → proposta: REJOIN COM PERCEPÇÃO (re-entrar
   só com gap) — 1 variável, R5 com pré-registro próprio.**
3. Ramos residual/solo/retreino: NÃO dispararam (51%/48% dos pilots raiz,
   minoria; freio-forte 12% das hesitações). Retreino NÃO proposto.

## v15 FASE R7a (2026-10-17) — VARIÂNCIA DE CORRIDA SEMEADA (opt-in) + veredicto do protocolo de execução

### Pré-registro 18:07:04Z: domínios D1 GRID / D2 COMPOSTO (cenário, nunca
### física — jitter físico RECUSADO por escopo); D3 clima inalterado.

### Implementação (opt-in, default OFF)
- `domain/racevar.py`: `variance_rng_from_seed(seed, domain)` no padrão do
  weather seeder (sha256 "<seed>//<domínio>", instância DEDICADA); parse;
  shuffled_order; assign_compounds (DISTRIBUIÇÃO preservada, só a atribuição
  muda). np.random global NUNCA consumidor.
- `--variance grid,compound` nos 2 runners (race_diagnostic + run_race);
  default off = corridas bit-reproduzíveis como antes.
- CSV v3.2/FONTE: variance, grid_order, compounds, weather_seed — cenário
  sorteado VISÍVEL no instrumento (lição FASE 1). Smoke-test do harness
  PASS antes de qualquer cadeia. Testes 4/4 (tests/test_racevar.py).

### VEREDICTO DE PROTOCOLO (endurecimento 1c)
- **PINNING FALHA**: 2 processos paralelos com OMP/OPENBLAS/MKL/NUMEXPR=1
  divergem ENTRE SI (linha 712, t=14,2 s) e do gêmeo sequencial — a
  contagem de threads NÃO é a causa; é a CONCORRÊNCIA de sims.
- Teste de carga e pinado-sequencial (bateria concluída):
  - **pinado-SEQUENCIAL ≡ R6-SEQ bit-idêntico** — env de threads é inócuo;
    e é também a prova de NÃO-INVASÃO (a): código R7a com --variance OFF é
    bit-idêntico ao R6 (zero mudança de física);
  - **sequencial SOB CARGA FP (4 burners numpy) ≡ R6-SEQ bit-idêntico** —
    carga de CPU NÃO perturba; o gatilho é especificamente SIMS PYBULLET
    CONCORRENTES (2 processos de simulação ativos), não threads nem load;
  - **variância ON, mesma seed ×2 → bit-idênticos** (cenário reproduzível).
- **VEREDICTO: SEQUENCIAL-PURO para sims** (um processo de simulação por
  vez; análise leve/IO em paralelo é seguro — provado). Pinning não
  autoriza paralelismo. Env OMP/BLAS opcional (inócuo).

### (c) DISPERSÃO — 10 seeds sequenciais, --variance grid,compound (PASS)
| seed | cc-v | pós-60s | fora% | rolante | preso>60s |
|---|---|---|---|---|---|
| 0 | 334 | 83 | 25,2 | 140 s | 0 |
| 1 | 323 | 69 | 30,5 | 154 s | 0 |
| 2 | 523 | 362 | 31,9 | 174 s | 0 |
| 3 | 946 | 184 | 30,4 | 154 s | 1 |
| 4 | 268 | 106 | 29,7 | 165 s | 0 |
| 5 | 272 | 16 | 25,8 | 139 s | 0 |
| 6 | 190 | 100 | 31,5 | 162 s | 0 |
| 7 | 756 | 234 | 29,5 | 164 s | 0 |
| 8 | 336 | 136 | 53,6 | 192 s | 15 |
| 9 | 203 | 96 | 46,6 | 154 s | 10 |
**Cenários de grid distintos: 10/10 — VARIÂNCIA MATERIAL ✓** (a variância
existe, é semeada e reproduzível por seed). Dispersão honesta: cc 190-946
(5×), fora 25-54%, pace 139-192 s. Medianas (baseline p/ o futuro gate
N≥10): cc 328, pós-60s 103, fora 30,4%, rolante 158 s, preso 0.
WANDERERS: seeds 8-9 sortearam 15/10 episódios >60 s — o modo PRECISA de
variância de cenário para aparecer (grids diferentes criam padrões de
contato diferentes); episódios disponíveis p/ a análise de persistência R5c.

### PROTOCOLO DE VARIÂNCIA v1 (vigora)
1. Domínios de CENÁRIO, semeados por sha256("<seed>//<domínio>"): grid,
   compound (distribuição preservada), clima (R6). Jitter físico: RECUSADO.
2. `--variance grid,compound` (opt-in; default OFF = bit-reproduzível).
3. Cenário sorteado VISÍVEL: linha FONTE + cabeçalho CSV v3.2.
4. Medição: SEQUENCIAL-PURO (1 sim por vez; análise leve paralela ok;
   threads inócuas). Bit-reprodutível por seed dentro do mesmo ambiente.
5. Gate N≥10: duas amostras por seed não valem — cada seed É uma
   realização completa (clima + cenário); N seeds = N realizações.

### LIMITAÇÕES
- Reprodutibilidade INTRA-ambiente: máquinas distintas, versões de
  BLAS/pybullet/drivers não são cobertas pela semeadura.
- A variância cobre CENÁRIO (grid/composto/clima); a dinâmica da largada
  permanece caótica (sensível ao cenário — é o que a dispersão mede).

### CHANGELOG (mudança de comportamento)
Com `--variance ON`, os MESMOS comandos produzem CENÁRIOS semeados por
seed (ordem de largada + compostos). Sem a flag: nada muda (bit-reproduzível
como R6 — prova de não-invasão).

## v15 FASE R7b (2026-10-17) — auditoria de física + BISEÇÃO B3.1: gap EXPLICADO; H2 CONFIRMADA (política de esterço, não fronteira física)

### Pré-registro 21:36:39Z (H1/H2 + predições P1-P4 + árvores antes dos dados)

### 0.1 — métrica COMPARÁVEL (zero runs)
Definição de fora idêntica em todas as eras (`|lat|>half_width`); recompute do
CSV legacy all-professor com classificador atual reproduz 0,03% exato → o gap
B3.1→R6 é DINÂMICA, não definição.

### 0.2 — BISEÇÃO DECISIVA (P4 confirmada): gap EXPLICADO
- **O commit 9099235 (FASE 4) NÃO RODA**: place_grid chama track.nearest_segment
  que não existia (crash registrado como um dos 4 do 9099235) — o working tree
  que mediu o B3.1 NUNCA FOI COMMITADO. Reconstrução mínima documentada (método
  portado verbatim da FASE R + frozen exportado como CSV + SF729 1-linha).
- **Código FASE-4 no instrumento canônico (frozen 1131wp, SF729, 600s): 40,55%
  FORA** (vs R6 atual: 29,3% — o código atual é MELHOR; o rejoin bearing da R3
  melhorou o campo). O 0,17% do B3.1 é inalcançável pela própria era no
  instrumento canônico.
- **VEREDICTO (árvore: culpado canônico pretendido): B3.1 rotulado REGIME
  PRÉ-CANÔNICO.** O gap 223→511/0,17%→29,3% = instrumento live→frozen + clima
  não semeado + contenção não controlada na era; NÃO há regressão pós-R2.
  Nenhuma correção proposta (não há culpado não-intencional).

### 1.1/1.2 — proveniência e tabela κ
- Professor usa o MESMO VelocityProfile (grip 0,788 / sf 0,80, sf adaptativo
  interno) — mas alveja 0,93×v_plan (speed_margin) e é PURE-PURSUIT (esterço
  por geometria de perseguição — feedback que absorve o understeer do físico).
- Fronteira skidpad (physics_frontier.json, real): a 16 m/s NENHUM raio testado
  segura; v_allow nas bandas quentes (26-54 m/s) está FORA do domínio medido —
  o perfil só é honesto porque o grip_mult 0,788 foi CALIBRADO contra o
  entregável do físico (understeer sistemático medido: R_eff/R_target =
  1,45-1,6× em círculo suave).

### 1.3 — 907 saídas pilots (10 CSVs R7a, zero runs novos)
- **P2 CONFIRMADA**: slip no tick de saída mediana 16,8°; 65% >10° — o carro
  JÁ está deslizando quando sai (assinatura de CAÇA, não de estouro).
- **P3 CONFIRMADA (H2)**: só 18% (27/150 computáveis) excedem a fronteira;
  a_lat atingida mediana 3,9-5 m/s² vs ~10,4 disponíveis.
- P1 PARCIAL: picos em κ<0,005 (322 — weave em reta, slip +16°, 0,72×v_allow)
  E 0,008-0,015 (353 — entradas de curva, slip −8°) — 74% das saídas.
- **Comando de esterço mediano nas saídas: 0,72 rad vs necessidade cinemática
  0,030 rad = 24×** — guinada sem curvatura de caminho (a_lat baixa + slip alto).

### 2 — SCRIPTED (sem policy/tráfego; protocolo do calibration script)
Hotspot κ=0,010 (R=100) e controle κ=0,005 (R=200), v = {v_allow, 0,81×,
0,93×prof, 0,72×}: **A FÍSICA SEGURA O CÍRCULO EM TODAS** — misalign 0,3°,
lat_proxy ≈0, inclusive a v_allow cheio. **H1 REFUTADA nos estados suaves.**
(R_eff/R_target = 1,41-1,61: understeer sistemático estável — propriedade de
calibração, não instabilidade.)

### 3 — VEREDITO POR BANDA (H1/H2/misto)
| banda κ | n | veredito |
|---|---|---|
| <0,005 (weave reta) | 322 | H2 — política oscila/caça (slip 16°, a_lat 4,9) |
| 0,008-0,015 (entrada curva) | 353 | H2 — comando insuficiente/saturado p/ understeer 1,45× |
| 0,015-0,03 | 87 | H2 majoritária (slip baixo, dentro da fronteira) |
| 0,03-0,05 | 76 | misto (0,91×v_allow, slip 8°) |
| ≥0,05 / excedentes | ~37 | minoria; estouro de fronteira real (18% dos computáveis) |
**H2 CONFIRMADA no agregado**: a física entrega círculos estáveis com entrada
suave; as saídas vêm de COMANDOS de esterço da política ~24× a necessidade
cinemática, gerando guinada+slip sem curvatura de caminho, a 0,72-0,9×v_allow.

### PROPOSTAS (NÃO implementadas — aprovação)
1. **STEER-GOVERNOR (race-layer, 1 variável)**: cap do esterço comandado em
   k_comp×atan(L·κ_preview) (+ banda p/ correção de heading), espelhando o
   padrão do governor de velocidade e do rejoin bearing (R3). Alvo: as 74% das
   saídas das bandas dominantes. Pré-registro próprio + skidpad sintético
   (comando exagerado → cap → segura?) + re-gate multi-seed.
2. Alternativa a retreino (só com aprovação): DAgger de estados de
   weave/slide — o policy nunca viu dados de RECUPERAÇÃO de deslize.
3. Documentação: understeer 1,45-1,6× como propriedade do físico (o professor
   absorve por feedback; imitador não absorve) — nota de auditoria.

## v15 FASE R12-PASSO1-2 (2026-10-17) — retreino executado; canárias INCONCLUSIVAS por INSTRUMENTO; PARE no ponto de decisão

### PASSO 0 (fechamentos, commitados no prereg b1a852c)
0.A Grade de sensibilidade COMPLETA (ld 0,48/0,60/0,72 × limiar 0,10/0,15/0,20):
83% (ld−20%, 0,10) → 38% (ld+20%, 0,20); ponto pinado (0,60/0,15) = 51% —
vizinhança NÃO inverte; GO de pé. 0.B Recount CSV: A s8=6/s9=8 confirmam;
B s9=8 (episódio NOR RECUP-OFF termina com a corrida; stoplog só registra
LIBERADO) — instrumento canônico de paradas = CSV; 100% RECUP-OFF nos 36.

### PASSO 1 — retreino (log commitado a385c18 + a seguir)
Dataset: 13.581 estados das 471 janelas GO + 20.000 replay 2:1 (r_target=
δ_prof−|δ|; TRÁFEGO-YIELD fora; motor pure-pursuit validado corr 0,863).
r12 (6d): corr 0,957 — mas INCOMPATÍVEL com a interface 16d do runner
(12 tráfego + 4 aux). r12b (16d, mesmas janelas com 10 zeros nos slots de
tráfego + v/κ/prev_st): **corr 0,936, replay |pred| 0,021** (disciplina em
pilotagem normal melhor que o r2). PERDA DE INFO documentada: |slip| e
sin/cos(herr) não existem na interface 16d — só v, κ, prev_st entram.
Solo congelado por construção (BC no residual; g=0 em solo).

### PASSO 2 — canárias H5: INCONCLUSIVAS POR INSTRUMENTO (lição R6 re-capturada)
A canária baseline (r2 — o residual VIVO do braço A, 223-contato-ex-VD)
também dá **0/3** no env. Causa: FastF1 offline → env cai no PRESET 240wp
(SF 109) — pista em que o v10 NUNCA foi treinado; o carro anda (76 m/s,
848 m em 160 steps) mas SAI da pista do preset no hairpin dele (t=341 s,
lat 8,1). O mesmo PROJECT_STATE já dizia desde R6: "gates de ENV não
colher agora — preset 240wp silencioso". As canárias de ENV não são
viáveis até FastF1 voltar ou o env aceitar a pista frozen.
**PONTO DE DECISÃO EXECUTADO (árvore do prereg: canárias quebram → não
prosseguir): o PILOTO {0,8,9} NÃO foi rodado.** Sem canárias, sem corrida —
o prereg manda parar. A alternativa honesta (canárias via race_diagnostic
solo no frozen) NÃO existe como comando e criá-la seria instrumento novo
não-preregistrado. PARE registrado.

### FASE R13-FECHAMENTO (2026-10-18) — apêndice auditável, erratas E1-E5, CSV v3.3, docs finais

**ERRATAS (auditáveis, zero runs):**
- E4 (manchete): ratio cc_B/cc_A real = **1,5× a 3,5×** (mediana 2,2×; Δ −479
  a −994) — a manchete "3-13×" confundia razão com recíproco; CORRIGIDA.
- E1: cc-fail por seed = {s10:601, s11:600, s12:613, s13:781, s19:877}
  (range 600-877 confirmado).
- E2: contato×carro-fora POR SEED (denominador = amostras de contato):
  28-44% (s16 é o menor com 28%; o texto "39-44%" era só dos cc-fail).
- E3: denominadores de hesit on-track: s11=21, s12=16, s13=14, s14=16,
  s15=20 — as classes somam o total (REJOIN+TRAF+CRAWL+OUTRO = total ✓).
- E5: adversos do braço A 0-9 pela regra w_trans MECÂNICA = **{2, 8, 9}
  (n=3)** — IGUAL ao n usado na derivação do prereg; nenhum quantil muda;
  vereditos por seed inalterados linha a linha.
- Identity smoke dos 20 runs: ator/gov/pista-sha/SF/CSV ✓ em todos; GAP
  documentado: sha do residual só logava com --residual-override (braço A
  implícito) — CORRIGIDO no v3.3 (sha universal).

**PASSO 2 — CSV v3.3 ADITIVO (commits 0c5892c + 97f3ad9):** colunas
res_0..res_15 por carro-tick (o 16d EXATO que o residual consome — rota 2
do backlog agora tem tráfego VIVO offline), sha do residual baseline logado
SEMPRE, kill-switch RACE_DIAG_NO_RES16. **Bit-identidade PASS: 0 divergências
em 52 colunas canônicas × 600 ticks (mesma seed, logging on vs off).** Suite
33+1 skip verde. ZERO mudança de comportamento.

## PASSO 4 — DOSSIÊ DA ALAVANCA (zero runs; 20 corridas braço A; prereg leve commitado)
- **(i)** 4.356 excursões; **18%** terminam com contato do dono ≤30s pós-reentrada.
- **(ii)** reentrada→primeiro contato: **mediana 8,7s** (p25 2,5s; p75 19,4s;
  35% dentro de 5s) — a LATÊNCIA ÚTIL de percepção de um rejoin-com-gap é
  ~2-9s (mediana): um gap-checker precisa olhar ~10s à frente.
- **(iii)** já medido (E2): 28-44% das amostras de contato com carro fora —
  retorno é a causa dominante dos cc-fail.
- **(iv)** reentrada ocorre a ~8 m/s (teto do rejoin); voltar a 15 m/s leva
  mediana 1,2s — o carro recupera pace RÁPIDO, mas o contato chega em ~8,7s:
  o retorno ao fluxo ANTES do pace é a janela de risco, não a lentidão.
- **CONCLUSÃO do dossiê**: a alavanca "rejoin com percepção" tem alvo
  quantificado: 18% das excursões geram o contato; a janela de decisão é
  ~10s; o carro reentra rápido demais para o gap que encontra. Um
  gap-checker que adie a reentrada até um buraco ≥X m (medir X da
  distribuição de gaps no corpus) atacaria ~35% dos contatos-pós-rejoin
  (os que chegam em ≤5s) e parte dos de 5-19s.

## DECLARAÇÃO FINAL DE PRODUTO (canônica — texto da revisão, colado verbatim)
> **Race default = v10-cego (dagger_actor_best.keras, obs edge, gov vplan).**
> O composite (v10 solo congelado + residual r2) NÃO é promovido: falhou o
> gate re-ancorado out-of-sample (R13: 3/10; adverso 0/4) nas dimensões
> contato (39-44% das amostras de contato com carro fora — retorno de
> excursões) e hesitação (classe REJOIN-DIP dominante), apesar de o critério
> de pista (fora) passar em TODAS as seeds. Permanece research-grade com
> vantagem de segurança CONSISTENTE e documentada: 1,5-3,5× menos contatos
> que o v10-cego em 10/10 seeds out-of-sample (Δcc −479 a −994), pós-60s
> sempre menor, e clima adverso sobrevivível (s8: 336 vs 5138 contatos).
> A cadeia causal única do produto: excursões race-speed da política →
> contatos no retorno → hesitação REJOIN-DIP → paradas RECUP-OFF. A alavanca
> futura é percepção de tráfego no RETORNO (rejoin com gap) ou weave/slide
> com tráfego VIVO (rota 2 — pré-condição de dados agora disponível via
> CSV v3.3).

## (registro anterior) FASE R13-GATE (2026-10-18) — 20 runs out-of-sample (seeds 10-19): VEREDITO R10 PERMANENTE
Prereg 2882a37 (limiares MECÂNICOS pinados do braço A 0-9; tolerância
adversa pré-argumentada; rótulo de clima do CSV w_trans; desfechos pré-
declarados). Braço A = composite (10 runs seriais); braço B = v10-cego
(10 runs seriais pareados). Working tree limpo no script de veredito
(scripts/r13_gate_verdict.py, commitado). Clima REAL que veio nos seeds:
adversos = {10 (DRY→CLOUDY→WET, 3 transições), 12, 13, 14}; secos = 6.
**GATE: FAIL — 3/10 seeds A passam (16, 17, 18); adverso 0/4; seco 3/6.**
Falhas por atribuição:
- cc > p75: s10 (601), s11 (600), s12 (613), s13 (781), s19 (877) —
  ~40-44% dos contatos envolvem carro FORA da pista (o fora e o cc são a
  MESMA frente: excursões RECUP-OFF gerando contatos no retorno).
- hesit > p75: s11 (21), s12 (16), s13 (14), s14 (16), s15 (20) — classe
  REJOIN-DIP domina em todos (7-13 de ~16-21) = a mesma frente única.
- paradas: SÓ s10 (10 > T-adv 8, clima WET real); floor 10/10 em TODAS.
- fora: TODAS dentro do limiar por clima (25,1-41,2 ≤ p75) — o critério
  re-ancorado de pista NÃO é o gargalo; o gargalo é CONTATO ligado à
  excursão, e hesitação pós-rejoin.
**COMPARAÇÃO PAREADA A×B (reporte cru — decisão INDEPENDENTE do gate):**
Δcc mediana ≈ −600 (composite 3-13× MENOS contatos em TODAS as 10 seeds);
Δpós-60s sempre negativo (−35 a −668); Δfora +2,2 a +9,6 pp (composite
sai MAIS); Δrol −34 a +23 s (adversos: composite mais lento em 3/4);
Δparadas: só s10 (+6); Δwand: só s10 (+4). O composite mantém a vantagem
de segurança em TODAS as seeds out-of-sample.
**VEREDITO (mecânico, pré-declarado): o composite ORIGINAL NÃO passa o
gate re-ancorado como política de produto. O veredito R10 (manutenção do
v10 como race default; composite research-grade) fica PERMANENTE com
confirmação out-of-sample de 20 corridas novas. A vantagem de contatos
é consistente (10/10 seeds) mas o custo em excursões/hesitações pós-
rejoin excede os quantis do próprio braço.**
FRENTE DOMINANTE unificada (todas as fases convergem): excursões de
pilotagem race-speed (R7b) → contatos no retorno (44%) → hesitação
REJOIN-DIP (57%) → paradas RECUP-OFF (100%). UMA frente, endereçada por
percepção de tráfego no RETORNO ou dados de weave com tráfego VIVO
(rota 2 do backlog — pré-condição documentada).

## (registro anterior) FASE R12-PILOTO (2026-10-18) — ERRATA #2 aceita; PASSO A fechado; PILOTO VERMELHO; autópsia completa
**PASSO A (zero runs; commit 85616af)**: ERRATA #2 (canária 1-carro: fora ≤25%
pela derivação 1,36× do baseline real 18,4%; papel = detector de falha
grosseira; aplicação simétrica). A.2(a) runner loga sha256 do residual
carregado (r12b b77adc68caef742a; r2 6a2dbf53a69fcac7) — fallback silencioso
morto. A.2(b) smoke offline COM TRÁFEGO VIVO: |r2−r12b| med 0,079 rad —
override end-to-end CONFIRMADO (campo-1 nunca exercita). A.2(c) g≡0 nos 4
CSVs — bit-identidade documentada. **A.3 FECHAMENTO ARITMÉTICO**: "5 voltas ×
132s" eram 5 CRUZAMENTOS incl. a LARGADA (t=1,4s) → **4 voltas COMPLETAS ×
131,5s = 526s ≤ 600s** — a contagem do sumário confundia cruzamento com
volta (corrigido na métrica). A.5 re-avaliação: r2 s0/s1 PASS sob ERRATA #2
(18,4 ≤ 25); H5' PASS → piloto destravado.

**PASSO B — PILOTO {0, 8, 9} (seriais; identity smoke por run; sha b77adc68)**:
| seed | métrica | A | r12b | Δ |
|---|---|---|---|---|
| 0 (seco) | cc | 334 | 716 | +382 (+114%) |
| 0 | fora% | 25,2 | 31,8 | +6,6 pp |
| 0 | hesit | 13 | 6 | −54% ✓ |
| 0 | rolante | 140 | 153 | +13 s |
| 8 (adv) | cc | 336 | 1061 | +725; wand 15→19 |
| 9 (adv) | pos60 | 96 | 32 | −64 ✓; wand −1 |
ÁRVORE (b1a852c): **H1 FALHA (fora +6,6pp), H3 FALHA (+13s), H4 FALHA
(cc +114%) — 3 de 4 no seed 0; VERMELHO. N=10 NÃO executado.**

**AUTÓPSIA (ordem pré-registrada)**:
(1) SKEW 0.C: r12b em campo denso = |r_norm| p95 1,91-2,26 << r2 (5,83-8,15)
— MAIS conservador, NÃO cauda explosiva; g ativo 22-31% (r2: 18-37%).
(2) SATURAÇÃO: refutada como mecanismo (p95 baixo).
(3) MECANISMO RESTANTE: nos ticks g>0 do s0, o r12b corre com th 0,24 vs A
0,36 e v_med 25 vs 19 (freia/corrige MENOS, anda MAIS RÁPIDO) — mudança de
estilo em 22% dos ticks com entradas de tráfego VIVO que ele nunca viu no
treino (skew). A hesit caiu (−54%) mas contatos dobraram: menos micro-
paradas, mais proximidade.
FALBACKS confirmados: GO 51% frágil (canto estrito 38% = NO-GO); r_win med
−0,058 (correção-alvo PEQUENA, dominada pelo ruído de interface 16d).
**CONCLUSÃO da frente weave/slide: retreino BC offline com interface 16d
incompleta NÃO transfere para o campo denso. Nenhum retreino adicional sem
aprovação.**

## FASE R12-CANÁRIAS (2026-10-18) —(registro anterior) — instrumento (a) executado; 4 runs bit-idênticos; controle falhou no LIMIAR (não no stack); PARE
Checagens 0.C-0.F executadas (skew 12d conhecido; |r_pred| p95 1,245 ≥ 0,15
— não colapsou; preset confirmado; grade 9 valores). Flags --n-cars e
--residual-override commitadas ANTES dos runs (b53687c, d4c8f14).
**Canárias (1 carro, frozen, 600s, seeds 0-1): r2≡r12b BIT-IDÊNTICOS nos 4
runs** (5 voltas, fora 18,4%, wanderers 0, rolante 132s) — wiring são por
construção (g=0 em campo de 1; o residual nunca atua; o stack carrega 5
voltas limpas). H5' ESTRITO: PASS (todas as diferenças zero).
**Controle positivo FAIL no limiar pinado (fora 18,4% > 10%)** — autópsia:
o NÚMERO foi calibrado às cegas p/ "solo limpo"; o v10 solo+frozen REAL é
~18% fora (off em s 1800-2400 e wrap; mediana on/off 34/8 m/s). O stack
não está quebrado (bit-idênticos provam); re-pinagar o limiar pós-número é
proibido → **PARE conforme o ramo pré-registrado; a revisão decide a
emenda do limiar** (proposta honesta p/ 1 carro: voltas ≥2, fora ≤25%,
wanderers 0 — calibrada no valor REAL do baseline). Piloto {0,8,9} NÃO
executado (árvore).

### ESTADO DO ATOR r12b (para a próxima sessão)
- residual_weave_r12b.keras/.npz salvos; dataset r12_dataset_weave.npz
commitado. Interface 16d OK com o runner (trocar --profile composite para
apontar o novo npz = 1 flag de diferença — via PROFILES ou flag nova).
- PRÓXIMA SESSÃO: (a) canárias honestas: rodar o v10 solo NO RUNNER frozen
(1 carro, 600 s, --profile composite) — o instrumento que o gate usa; OU
(b) se a revisão preferir, canárias de ENV com a pista frozen carregada
( requer instrumento novo pré-registrado).
- A fragilidade 0.A (GO limítrofe) + a perda de info 16d (|slip|, herr fora)
entram na autópsia se o piloto falhar.

## v15 FASE R12 (2026-10-17) — fechamentos + hesitações=REJOIN-DIP/CORNER-CRAWL (treinável); retreino autorizado

### Prereg 9ca161e (sha 65bc5048) commitado antes; REGRA NOVA registrada:
### script de veredito/decisão só roda com working tree limpo.

### 0.1 — ERRATA s9 (paradas do braço B): log dizia 7; recontagem CSV = 8
O stoplog do runner só registra episódio LIBERADO (contato/autonomia) — o
episódio do NOR (t0=593 s, dur 6,6 s) TERMINA COM A CORRIDA e escapa do log.
Verdade: B s9 = 8 (não 7); A s9 = 8. A tabela R10 corrigida: s9 paradas
A/B = 8/8 (não 8/7). IMPACTO NO VEREDITO R10: ZERO (D1 olha só o candidato;
o candidato tinha 6/8 e falha de qualquer forma). Instrumento: stoplog do
runner perde episódios no fim da corrida — métricas de parada contadas do
CSV daqui em diante.

### 0.2 — decomposição COMPLETA: identidade fecha 10/10 seeds
Δrolante = Δfora + Δhesit + Δparado + resíduo fecha (tol. 0,15 s) em todas
as seeds. ERRATA da frase R11: **"em clima adverso o composite é mais
rápido" era ERRADA** — s8: A=192,5 vs B=149,9 (A 42 s MAIS LENTO); s9:
153,7 vs 147,2 (+7 s). O correto: nos adversos o ΔFORA é negativo (o
composite passa MENOS tempo fora por volta) mas o RESÍDUO INTRÍNSECO
explode (s8: +70,9 s/volta) — o gap vem do envelope/estado, não do fora.
Leitura seca: gap 22,8 s = 11,1 fora + 8,3 intrínseco + ~3 hesit.

### 0.3 — MECANISMO DAS HESITAÇÕES (regra PINADA; braço A, 10 seeds)
Com o critério DO GATE (on-track): 132 episódios = **REJOIN-DIP 75 (57%) +
CORNER-CRAWL 33 (25%) + OUTRO 24 (18%); TRÁFEGO-YIELD ≈ 0.**
(Nota de critério: a primeira passada sem filtro on-track achou 1.881 eps,
98% dos "OUTRO" DURANTE off-track — micro-paradas dentro de excursões,
custo do fora, não da métrica hesitação; o gate sempre contou on-track.)
**RESPOSTA: hesitações ENTRAM na frente única das excursões** (57% são o
dip de reentrada pós-excursão; 25% corner-crawl treinável; o yield de
tráfego é marginal) → o retreino PODE ajudar; NÃO é preço estrutural.

### 0.4 — sensibilidade do GO 51% (report-only; regra R11 fica de pé)
Bairro estreito na dimensão ticks: ≥3 → 58%; ≥5 (pinado) → 51%; ≥8 → 19%.
subst/saída: mediana 5, p75 6, p25 0 — a massa está EXATAMENTE no limiar.
Variação ld/limiar rad não recomputada (exige re-rodar janelas); o GO
permanece pela regra pinada, com a fragilidade documentada.

### 0.5 — validação da reconstrução de pose: CONSISTENTE
κ alvo@10m reconstruído vs obs10 em 1000 ticks on-track: correlação 0,863;
erro mediano 0,0026 (2,5% da escala) — abaixo do ramo de 25%. O motor do
r11_03 é válido na trajetória dada (condição necessária, como registrado).

### 0.6 — quantis por CONDIÇÃO CLIMÁTICA (20 corridas; DRAFT p/ R13)
SECO (n=16): fora p50 25,5% / p75 29,9% | rolante med 138 s.
ADVERSO (n=4): fora p50 **50,25%** | rolante med 151,8 s.
DRAFT de re-ancoragem por clima (nada canônico; para o prereg R13):
- SECO: fora teto p75 ≈ 30% | rolante ≤ 148 (med+10) | paradas = 0 |
  hesit ≤ 10 (mediana comp seca + tolerância) | cc ≤ 800 (p75 seco)
- ADVERSO: fora teto p75 próprio (~55%) | paradas ≤ 6 (mediana do melhor
  braço) | rolante ≤ 160 | cc ≤ 1.500
- wanderers: mediana 0/seed; nenhum seed >3 (backlog, não bloqueador).

### DECISÃO 0.3 → PASSO 1 (retreino) LIBERADO: REJOIN-DIP+CORNER-CRAWL
### são treináveis (a frente é UMA); TRÁFEGO-YIELD não treinar contra (marginal).
### Execução do retreino + piloto {0,8,9} fica para a próxima sessão
### (dataset agregado + iterações DAgger com canárias — pesado; prereg
### próprio antes de qualquer treino, como registrado no prereg R12).

## v15 FASE R11 (2026-10-17) — trilha pós-gate: paradas=RECUP-OFF 100%; gap de pace 49% explicado; weave/slide GO (51%); re-ancoragem draft

### 0.0 — FECHAMENTO DE RESSALVAS R10 (prereg 98c8fd8, sha dee6aa19)
0.0.1 Dif ca6b827→4bb7993 do script de veredito: UMA mudança
(`T.arm.startswith` → `T.arm.str.startswith` — accessor pandas). Constantes
(10pp/15s/+3) e ordem lex intocadas (diff completo acima). DESVIO DE
PROCESSO documentado honesto: o fix ficou em working tree na hora do
veredito (script crashou AttributeError na 1ª execução; veredito rodou com
o fix; fix+docs commitados juntos em 4bb7993).
0.0.2 Estatística: o script usa MEDIANAS POR BRAÇO; o prereg R10 dizia
"mediana pareada". Computadas AMBAS: sinais unânimes em cc/pós60/rolante/
hesit (10/10 seeds); fora misto (8+/2−). VEREDITO ROBUSTO à escolha —
D1 falha (paradas≠0) e D3 falha (rolante Δmed +22,5>15; hesit +10>3) nas
DUAS estatísticas.
0.0.3 Apêndice com unidades: disciplina 0,01% dos ~183k ticks normais;
cobertura por TICK pré-saída 0,1% (13.547 ticks); o "8/100" era por GRUPO
(seed,drv) — GRUPO≠SAÍDA (não computado por saída); lead "3.700 ticks" é
artefato de agregação (janela=30). VEREDITO NÃO SEPARA permanece (0,1% vs
50% por tick — 3 ordens de magnitude).

### 0.1 — MECANISMO DAS 14 PARADAS: 100% RECUP-OFF (subproduto das excursões)
Todas as 14 paradas do composite (s8: 6, s9: 8) começam COM o carro
off-track ou ≤5 s após o fim de um episódio off — nenhuma engarrafamento,
nenhuma hesit-cascata isolada. **Paradas = SUBPRODUTO das excursões** (o
crawl de retorno a 8 m/s com recovery às vezes demora ≥3 s). Contraste
s8×s9: cego s8=14 paradas (vs comp 6); s9=8 (vs 8 — empate). CONCLUSÃO:
cortar excursões corta paradas — a frente é UMA (pilotagem), não duas.

### 0.2 — GAP DE PACE (mediana +22,8 s): 49% explicado por Δ(fora+hesit+parado)/volta
Decomposição DIFERENCIAL por seed (Δcusto A−B por volta): mediana
11,1 s do gap de 22,8 s vem de fora/hesit/parado (quase tudo fora);
resíduo mediano 8,3 s. Em clima adverso (s8-9) o composite é até MAIS
rápido (Δ fora negativo). CONCLUSÃO: cortar fora% É a alavanca principal
do D3 (metade do gap), com componente intrínseco de envelope ~8 s.

### 0.3 — VIABILIDADE WEAVE/SLIDE: **GO** (51% — apertado)
924 saídas avaliadas; o PROFESSOR (pure-pursuit simulado offline) comandaria
correção substantiva (>0,15 rad de diferença) em ≥5 ticks da janela pré-saída
em **471/924 = 51%** (mediana de ticks substanciais: 5; p90: 12). Limiar
pinado ≥50%: GO. Nota honesta: apertado — o envelope do aluno em metade das
saídas JÁ contém o comando do professor (limite do retreino: ganho máximo
~metade das saídas).

### 0.4 — DRAFT DE RE-ANCORAGEM (nada canônico; para a revisão)
Corpus 20 corridas (A+B). SECO (16): fora p50 25,2 / p75 29,7 / p90 30,5% |
rolante med 139 s | cc p50 756. ADVERSO (4): fora 46,6% | rolante 150 s.
PROPOSTA: fora teto p75-seco 30% | rolante med+10 = 149+10=159 s... (valores
exatos no relatório; a revisão aprova/corta). Os critérios PRÉ-CANÔNICOS
(fora ≤1,5%, rolante ≤115 s) são 3-7× mais estritos que TODO o corpus
legítimo — referência histórica de um regime não-reproduzível (R7b).

### DECISÃO DA FASE: 0.3 = GO → PASSO 1 (retreino) autorizado pelo prereg;
### execução fica para a próxima sessão (escopo + orçamento: o dataset weave/
### slide precisa de extração dedicada + iterações DAgger com canárias por
### iteração — pesado). Fila: PASSO 1 (retreino dirigido) → piloto {0,8,9} → N=10.

## v15 FASE R10 (2026-10-17) — GATE DE PRODUTO N=10 pareado: MANUTENÇÃO do v10; composite research-grade

### Prereg + script de veredito MECÂNICO commitados ANTES dos runs B (ca6b827).
Braço A = CSVs R7a (não re-rodar — não-invasão provada R8); braço B = 10 runs
sequenciais novos, UMA diferença (ator v10/edge). Smoke B PASS (ator conferido).
Apêndice 2ª ordem (zero runs): NÃO SEPARA (cobertura 0,1% vs 50%).

### TABELA POR SEED (medianas no pé)
| seed | cc A/B | pós60 A/B | fora% A/B | rolante A/B | hesit A/B | paradas A/B |
|---|---|---|---|---|---|---|
| 0 | 334/1427 | 83/797 | 25,2/22,1 | 140/136 | 13/3 | 0/0 |
| 1 | 323/1401 | 69/753 | 30,5/22,8 | 154/136 | 12/3 | 0/0 |
| 2 | 523/1213 | 362/850 | 31,9/23,0 | 174/134 | 18/1 | 0/0 |
| 3 | 946/1003 | 184/347 | 30,4/23,3 | 154/136 | 12/2 | 0/0 |
| 4 | 268/1072 | 106/341 | 29,7/26,1 | 165/137 | 21/2 | 0/0 |
| 5 | 272/711 | 16/264 | 25,8/21,2 | 139/135 | 10/1 | 0/0 |
| 6 | 190/1072 | 100/392 | 31,5/22,2 | 162/135 | 14/3 | 0/0 |
| 7 | 756/1232 | 234/731 | 29,5/22,8 | 164/136 | 20/5 | 0/0 |
| 8 (clima adv) | 336/5138 | 136/4602 | 53,6/59,4 | 192/150 | 7/0 | 6/14 |
| 9 (clima adv) | 203/2925 | 96/1942 | 46,6/46,9 | 154/147 | 4/0 | 8/7 |
**Medianas**: cc 328,5 vs 1222,5 | pós60 103 vs 742 | fora 30,45 vs 22,9 |
rolante 158 vs 136 | hesit 12,5 vs 2,0 | wand 0/0 | preso 0/0.

### VEREDITO MECÂNICO (script commitado, regra pinada antes dos números)
- **D1 SEGURANÇA: FAIL** — cc e pós60 do composite são ESMAGADORAMENTE
  melhores (328 vs 1222; 103 vs 742), MAS paradas do candidato ≠ 0
  (seeds de clima adverso 8/9: 6 e 8 paradas; o cego: 14 e 7).
- **D2 PISTA: PASS** — fora 30,45 ≤ 22,9+10; wanderers 0≤0; preso 0≤0+5.
- **D3 PACE: FAIL** — rolante 158 > 136+15=151; hesit 12,5 > 2+3=5.
→ **MANUTENÇÃO DO v10 como race default; composite PERMANECE research-grade**
com D1/D3 documentados como limitações de produto.

### DECLARAÇÃO DE PRODUTO (o que o usuário ganha/perde em cada cenário)
Com o **v10-cego (default mantido)**: pace previsível (136 s), quase zero
hesitações, menos fora-de-pista no seco (22,9%) — ao custo de 3-4× mais
colisões (mediana 1222) e, em clima adverso, quase-destruição do campo
(semente 8: 5138 contatos, 14 paradas). Com o **composite (research-grade)**:
3-4× menos colisões SEMPRE (328) e clima adverso sobrevivível (336 vs 5138
— a percepção de tráfego é a diferença entre corrida e demolição), ao custo
de +7,5 pp de fora, +22 s de volta e +10 hesitações. A regra pinada
priorizou zero-paradas e pace do incumbente: o composite ainda não passa.

### Fila pós-gate (aprovação da revisão)
1. DAgger weave/slide (trilha de melhoria principal; risco v14b/c/d) — os
   estados-alvo (saída a 0,81×v_allow, weave, slip-regime) estão
   caracterizados; a assinatura de 2ª ordem NÃO separa (apêndice: cobertura
   0,1%) — o retreino deve mirar o PADRÃO completo, não um gatilho simples.
2. Paradas em clima adverso (D1): os wanderers/paradas dos seeds 8-9 existem
   nos DOIS braços (composite MENOS: 6/8 vs 14/7) — a causa comum é o clima
   adverso + post-spin (R6); candidato a correção de camada de RECUPERAÇÃO
   (não de comando — família encerrada).
3. Re-ancoragem absoluta dos critérios (fora ≤1,5%/rolante ≤115 são
   pré-canônicos): proposta de novos limiares à distribuição honesta na
   próxima fase de gate.

## v15 FASE R9 (2026-10-17) — falsificação OFFLINE: AMBOS os candidatos MORTOS; família camada ENCERRADA; zero runs

### Prereg de análise commitado ANTES (2e5159d, sha bd6d279b): limiares pinados
(disciplina ≤0,5%; lead med ≥5 ticks; cobertura ≥50%; morte do B se <30%).

### 0.1 — calibração do motor: REPROVADA no critério pinado (80-91%), causa
diagnosticada e é um defeito ADICIONAL da R8: o κ@10m é ASSINADO — com curva
à direita à frente o canal fica negativo, max(0,·) colapsa o cap a 0 e o
clip ZERA o esterço (linhas steer=0,0 com log ativo). O veredito R8 (refutado)
vinha do RUN (fora 2,4× pior, clip 88-92%) e fica MAIS sólido. Os candidatos
A/B morrem por DISTRIBUIÇÕES DIRETAS (motor-independentes) — a limitação da
calibração não afeta o veredito (honestidade do prereg: condição necessária).

### 0.2 — candidato A (slip-cap): MORTO por DISCIPLINA — 43,9-47,1% (limiar 0,5%)
slip>θ em ticks NORMAIS: 91-97,7% (θ=5-15°) — a política dirige em slip alto
PERPETUAMENTE (estado normal de compensação do understeer 1,45×); a janela
pré-saída tem a condição ativa em 35,2% vs 45,8% nos normais — SEM separação
(a janela é ativa MENOS que o normal). O sintoma "16,8° nas saídas" não é
sintoma: é o regime de operação.
### 0.3 — candidato B (rate-limiter ρ): MORTO por SEPARAÇÃO — 0,2% (morte <30%)
ρ(p99,5)=2,73 rad/s (disciplina inerente 0,5%); rate-spike pré-cruzamento em
0,2% das saídas (ρ p99,9: 0,0%) — o comando gerador é OFFSET SUSTENTADO, não
yank. A taxa não separa. Número registrado.
### 0.4 — círculo-de-atrito: descartado por construção (a_lat das saídas
3,9-5 m/s² ABAIXO do limite; o comando impossível é absorvido pelo understeer).

### ÁRVORE EXECUTADA: AMBOS MORTOS → PARE — FAMÍLIA CAMADA ENCERRADA
Nenhum mecanismo de CAMADA sobre o comando de esterço separa normal de saída:
- valor absoluto (κ-cap): refutado no piloto R8 (disciplina 88-92%);
- valor condicionado a slip: morto offline (slip alto é o regime NORMAL);
- taxa: morto offline (offset sustentado, não yank);
- círculo-de-atrito: morto por construção (a_lat sub-limite nas saídas).
O diagnóstico estrutural fecha: as saídas vêm do PADRÃO de comando da política
(imitação do professor sem o feedback pursuit), não de eventos separáveis no
comando. ESCOLHA DA REVISÃO (pré-registrada):
  (a) DAgger weave/slide — retreino com pré-gate do professor + âncora solo
      (risco documentado: v14b 2/3 → v14c 1/5 → v14d 0/3); OU
  (b) GATE-FIRST — re-ancoragem dos critérios à distribuição R7a e promoção
      com a limitação de fora% documentada (29-54% pela pilotagem atual).
Custos: R9 gastou ZERO runs (a R8 gastou 10 para o mesmo tipo de veredito —
a regra offline-first pagou-se imediatamente).

## v15 FASE R8 (2026-10-17) — steer-governor: MECANISMO REFUTADO pelo piloto (disciplina 88-92% vs gate 0,5%); PARE sem adoção

### PASSO 0 (R5c, zero runs) — porta PASSOU, mas com a lição do viés
97% (894/924) das saídas pilots têm |δ| > cap(2×atan(L·κ@10m)) no cruzamento
(δ/cap 11,6×) → porta de saída PASSOU. Cap-only (14/924 com herr>20° e δ≤cap).
Inventário: 2160 eps = 2134 rápidos (rejoin bearing FUNCIONA) + 26 wanderers
(concentrados s8-9) + 1092 churn encadeado. PROPOSTA wanderer p/ gate (fase de
gate): mediana 0/seed e nenhum seed >3 episódios.

### REGRA NOVA CUMPRIDA (achado 9099235): prereg (PREREG_R8_STEERGOV.md,
sha 9519d157) + código + 5 testes COMMITADOS (cf04f88) ANTES do 1º run ON.
Não-invasão PASS: OFF bit-idêntico ao baseline R7a (0 diverg em 52×30000).

### PASSO 2/3 (piloto N=10 sequencial) — DISCIPLINA FALHA, VERMELHO TOTAL
| seed | fora% ON (OFF) | steer-gov% ativo (gate ≤0,5%) |
|---|---|---|
| 0-9 | 65,4-75,7 (OFF: 25,2-53,6) | 87,7-92,1 |
**O cap clipa 88-92% dos ticks ON-TRACK e o fora PIOROU ~2,4×** — a política
usa esterço alto COM κ baixo em direção NORMAL (pursuit/correção): até
k_comp=25 clipa 30% dos ticks normais. RE-DERIVAÇÃO (sem piloto): NENHUM
k_comp satisfaz a disciplina 0,5% — mediana normal 2,7× vs saídas 23,1×
separa MEDIÂNICAS mas as caudas se sobrepõem por construção (κ≈0 na reta).
O contrafactual 97% do 0.2 era VIÉS DE SELEÇÃO (upper bound registrado como
tal; a verdade só o piloto mediu — e mediu o contrário).

### VEREDICTO R8 (árvore: disciplina falha → PARE — re-derivar → inviável)
**Steer-governor como CAP κ-CINEMÁTICO é MECANISMO ERRADO — refutado.**
Default permanece OFF (nunceu se tratou de adoção). DAgger de estados
weave/slide VOLTA À FILA como proposta primária (a rejeição era condicionada
ao diagnóstico do governor mostrar que o cap expressa a correção — mostrou
que NÃO expressa). Candidatos de MECANISMO p/ proposta futura (não
implementados): (a) cap condicionado a slip (clipar só com |slip|>10°, o
sintoma das saídas); (b) limitador de TAXA de esterço (derivada, não valor
absoluto); (c) DAgger weave/slide (retreino — risco documentado v14b/c/d).

### LIÇÕES R8
1. Contrafactual em eventos (amostragem só nas saídas) SUPERESTIMA o efeito
   de um cap — a distribuição NORMAL do comando é o denominador que falta.
2. Regra nova funciona: commit-antes-de-run + disciplina-gate no resumo
   pegaram a falha no 1º seed (o gate do runner imprime o PARE).
3. Redirecionamento de shell cria .log VAZIOS na raiz (restos da tentativa
   127) — sempre confirmar cwd/ls antes de ler outputs.

## v15 FASE R6 (2026-10-17) — SEMEADURA DO CLIMA + descoberta do NÃO-DETERMINISMO PARALELO (corrige a leitura da R5a)

### A ÚNICA mudança (aprovada): semear o RNG do clima
`weather_rng_from_seed(run_seed)` (domain/weather.py): sha256("<seed>//weather")
→ random.Random DEDICADO; `--weather seeded|fixed` (fixed = prob transição 0,
kind travado — braço de controle). CSV v3.1 aditivo: w_kind/w_grip/w_trans por
tick + tyre_life/tyre_grip por carro-tick + weather_seed e transições na
FONTE. Testes 3/3 (tests/test_weather_seed.py: reproduzível por seed, diverge
entre seeds, instância dedicada).

### ARQUEOLOGIA 1.5 — por que os gates v14 "eram determinísticos"?
O WeatherModel com rng NÃO semeado existe desde 6a63758 (18/set, commit
fundacional do domínio) e o engine sorteia transições POR VOLTA desde
ff49b39 (commit do engine) — TODA corrida desde sempre foi bilhete de
loteria: P(transição real em 600 s) ≈ 45-50% (≈50 sorteios de 5% × 25% de
mudança de kind). Os pares v14/R2 que "bateram" (1352×2, 309×2) eram os runs
sem transição — seleção sobrevivente, nunca determinismo. O B3.1-verde (223)
é UMA extração dessa loteria.

### VALIDAÇÃO 1.4 — TODA PASS (sequencial)
- mesma seed ×2, 600 s COMPLETOS: BIT-IDÊNTICOS (30000×52) — a guarda
  literal da R5a fecha.
- puro vs instrumentado (RACE_DIAG_NO_CONTACT_LOG=1), 600 s: 0 divergências
  em colunas físicas — guarda DEFINITIVA do instrumento.
- seeder vivo: seed 2 sortou DRY→CLOUDY na volta 2; seeds 0/1 sem transição
  (streams distintas); testes 3/3 (tests/test_weather_seed.py).

### DESCOBERTA DE PROTOCOLO: o SEED é knob DE CLIMA (e nada mais)
Sem --mixed/--shuffle, np.random.seed NÃO é consumido pela corrida; o único
consumidor do seed é o rng do clima (que só altera a física QUANDO há
transição). Verificado BIT-IDÊNTICOS: comp s1≡s0; blind s1≡s0; fixed ×3 ≡
comp-seca. **As "3 seeds" de cada grupo são 1-2 realizações, não 3.** TODA
a "variância multi-seed" das fases R2-R5 era (a) loteria do clima NÃO semeada
e (b) ruído de contenção paralela — o seed NUNCA amostrou variância da
corrida. Um gate multi-realização HONESTO precisa de um mecanismo semeado
de variância de corrida (ex.: jitter de grid com rng dedicado) — proposta R7,
1 variável, aprovação.

### PASSO 2 — re-medida SEQUENCIAL (realizações distintas, não "medianas de 3")
| realização | cc-verdade | pós-60s | fora% | voltas | rolante | preso>60s |
|---|---|---|---|---|---|---|
| comp SECA (s0≡s1) | 511 | 308 | 29,3% | 10/10 | 144 s | 0 |
| comp CLIMA s2 (DRY→CLOUDY@2) | 813 | 610 | 31,0% | 10/10 | 166 s | 0 |
| cego SECO (s0≡s1) | 892 | 250 | 22,6% | 10/10 | 136 s | 0 |
| cego s2 (clima próprio) | 1112 | 470 | 22,2% | 10/10 | 133 s | 0 |
| comp FIXED | ≡ comp SECA bit-idêntico | | | | | 0 |

### DESCORBERTA R6 (validação 1.4): NÃO-DETERMINISMO POR EXECUÇÃO PARALELA
- mesma seed ×2 em LOTE PARALELO (3 sims simultâneos): DIVERGEM em t≈2,6-4,6 s
  (fase de largada, contatos); mesmos runs SOZINHOS: BIT-IDÊNTICOS.
- SEQ (R6, sozinho) ≡ R5a-guard (R5a, sozinho) BIT-IDÊNTICOS — as mudanças
  R5a/R6 não tocam a física; weather seeding + logging v3.1 limpos.
- **CORREÇÃO RETROATIVA DA R5a**: as 6 re-medidas R5a eram lotes paralelos —
  o "derby" do comp s0 (cc 6103) era uma realização de CONTENÇÃO, não uma
  realização legítima do seed 0 (diverge do SEQ em t=4,6 s). As tabelas
  R5a (i)-(vi) caracterizam realizações válidas de corrida, mas o RÓTULO
  "seed N" não era chave reproduzível. As medianas R6 SEQUENCIAIS as
  substituem.
- PROTOCOLO PERMANENTE: corridas de medição/guarda são SEQUENCIAIS (sem
  sims concorrentes na máquina); execução paralela de sims = variância
  não semeada extra.

### TABELAS (i)-(vi) e ÁRVORE DE ATRIBUIÇÃO EXECUTADA
(i) Acima (realização-rotulada; medianas de 3 "seeds" seriam degeneradas).
(ii) Atribuição das raízes (comp seco): PILOTAGEM 77 (74%), CONTATO(imp10s)
     17 (16%), PNEU late-race 10 (10%), CLIMA 0% (s2: 3% perto da transição
     — sens. ±30 s não muda). Histograma por minuto: uniforme (6-15), SEM
     spike pós-transição.
(iii) **DISCRIMINADOR (comp seco, 77 pilotagens): mediana v0/v_allow = 0,81;
     OVERDRIVE (>1,10×v_allow) só 13% (10/77); 87% SAEM ABAIXO DA VELOCIDADE
     PERMITIDA**, com esterço mediano 0,72 rad (cinemática ~5× o círculo de
     atrito a 18 m/s) e freio forte em 43. Bandas κ: reta 28 / média 32 /
     curva 17. → **RAMO EXECUTADO: "v0 ≈ v_allow e sai mesmo assim" =
     PROBLEMA FÍSICO-DINÂMICO — auditoria de FÍSICA (modelo lateral em
     saída de curva / understeer a comando), NÃO policy.**
(iv) Derby s0 (cc 6103 na R5a): realização de CONTENÇÃO PARALELA — diverge
     do SEQ legítimo em t=4,6 s; sem transição de clima. Didático: loteria.
(v) C1 REALIZAÇÃO-MATCHED (sequencial): **a vantagem de contatos do
     composite VOLTOU**: comp 511 vs cego 892 (seca; −43%) e 813 vs 1112
     (clima; −27%) — a tabela R5a "sem vantagem" era ruído paralelo. Fora%:
     comp PIOR (29-31 vs 22-23) — o composite evita CONTATO e sai MAIS da
     pista (comportamento consistente em todas as fases). PROVISÓRIO (N=1
     por condição); gate N≥10 exige antes o mecanismo de variância (R7).
(vi) Wanderers: **0 episódios >60 s em TODAS as realizações sequenciais**
     — o modo das R3/R5a (9/30) não sorteou sem contenção; a persistência
     (salto de braço) fica pendente de episódios para analisar.

### VEREDICTO R6
1. Clima: causa MENOR de saídas (0-3%) — mas o custo por transição é real
   (+302 cc, +22 s de pace no s2). --weather fixed NÃO vira modo de gate
   (o clima é parte do produto); o gate amostra tickets de clima por seed.
2. Pilotagem: 74% das raízes, mas o discriminador manda o fix para a
   FÍSICA: carros saem a 0,81×v_allow com comando ~5× o orçamento de
   atrito. **PRÓXIMA FRENTE: auditoria do modelo lateral (fase 4 do
   apply_control) em saída de curva + a relação comando-vs-fricção do
   _action_to_controls** — NÃO policy, NÃO residual, NÃO retreino.
3. Produto: composite reduz contatos 27-43% vs cego (matched), ao custo de
   +7-8 p.p. de fora%. Gate de corrida segue VERMELHO (fora 29-31% > 1,5%).
4. R7 propostas (aprovação): (a) mecanismo semeado de variância de corrida
   (jitter de grid c/ rng dedicado) para o gate multi-realização; (b)
   auditoria de física do lateral; (c) R5c wanderer-persistência (aguardar
   episódios).

## v15 FASE R5a (2026-10-17) — INSTRUMENTO DE CONTATO AUTORITATIVO: proxy da R4 RETRATADO; pilotagem RE-CONFIRMADA; realização domina

### Pré-registro 2026-10-17T14:55:45Z (hipóteses H1-H4 + árvore + preso T=60s).

### PASSO 1 — instrumento (ZERO mudança de comportamento; física intocada)
- Coletor OPT-IN em `PyBulletPhysics` (engine/physics.py): colhe `getContactPoints`
  por SUB-STEP (1/240 s) após cada stepSimulation; por PONTO de contato
  chassis×chassis: par, posição, normal, força c[9], impulso J=F·dt,
  |Δv|=J/m por corpo (3ª lei), XY de ambos. Desligado = zero custo (env/tests).
- CSV v3: TODAS as colunas preservadas + `imp_events/imp_dv/imp_dv_max` por
  carro-tick + eventos crus em `<out>_events.csv` + cabeçalho de versão +
  sha256 da pista na linha FONTE (`load_track_frozen` expõe `frozen_sha256`).
- Testes 3/3 (tests/test_contact_instrument.py): colisão central scriptada
  (log do solver explica Δv observado; 3ª lei; |Δv|≈closing/2); solo = 0
  eventos; mapeamento sub→tick EXATO. NOTA do solver: também faz SEPARAÇÃO
  POSICIONAL (resolve sobreposição em <24 sub-steps).

### GUARDA 1.3 — a história completa (árvore: guarda falhou → debugou → instrumento EXONERADO)
- Literal (re-run s0 vs CSV R4): FALHOU. A/B com código R4 PURO (worktree
  a5abb8e) FALHOU IGUAL → não é o instrumento.
- **CAUSA-RAIZ (não-determinismo entre processos): `WeatherModel.rng =
  random.Random()` NÃO SEMEADO** (domain/weather.py:159) — transições reais
  de clima (5%/volta/carro) mudam o grip e divergem a realização daquele
  instante (medido: ontem t=97,2s; hoje t=137,2s; 5 processos sem transição
  ≤160s). PRE-EXISTENTE desde o recurso de clima — explica por que B3.1
  nunca foi re-mensurável bit-a-bit entre sessões (refina a hipótese "float"
  da R2: a fonte é o RNG do clima, não ruído numérico).
- GUARDA REAL PASS: puro ≡ instrumentado BIT-IDÊNTICOS por 160 s (janela que
  cobre largada + fase densa + ambos os onsets de clima observados);
  prefixo do run completo ≡ segmento; PYTHONHASHSEED irrelevante (A≡B).
- **Proposta R5 (comportamento, 1 variável, aprovação): semear
  `WeatherModel.rng` por seed da corrida** — reprodutibilidade bit-a-bit
  entre sessões; NÃO implementado nesta fase (regra READ-ONLY).

### PASSO 2 — re-medida (6 runs de hoje; composite 0 transições, cego s0/s1 1)
(i) **Fator flag→verdade (composite): 1,01 / 1,08 / 1,40 (mediana 1,08)** —
    o flag 5Hz era quase honesto como CONTAGEM de ticks; cobertura flag⊆eventos
    173/173…6103/6103 (falsos positivos ~0). Árvore: **razão ∈ [1,1; 1,5)**.
(ii) **RETRATADO o "70% contato-não-amostrado" da R4**: com o solver, raízes
    com impulso 10 s antes = 17/20/12% (mediana ~17%). O proxy |Δv|>2 m/s
    capturava FREIO PRÓPRIO + entrada na grama, não empurrão. Ambiguidade
    brk>0,3 RESOLVIDA: frenagem própria. **PILOTAGEM RE-CONFIRMADA dominante:
    76/81/97 pilots por seed (80-88% das raízes), ~50/50 residual/solo,
    v0 mediana 18-22 m/s, esterço 0,55-0,79 — saídas em VELOCIDADE DE CORRIDA
    (o perfil v≈10 do R4 era dos ECOS pós-rejoin).** O ramo pilotage da R3
    volta a ser a frente dominante — agora com dados do solver.
(iii) rejoin-gerador: 1% / 23% / 95% (mediana 23% < 30% da árvore) — o claim
    de 68% da R4 era de 190 flag-ticks de UMA realização. R5b (rejoin com
    gap) DESCLASSIFICADO de "a frente" para "uma frente" (real em s2).
(iv) Tempo fora: s1/s2 dominado por ECOS (72-75%); s0 por raízes+preso
    (61%+38%; 2 wanderers, ambos vítimas de fling c/ impulso 10 s antes —
    H4 confirmada p/ wanderers).
(v) Eco: gap 5/10/20 s → raízes 146-175 / 92-110 / 48-58 (padrão estável).
(vi) Wanderers: entrada por impulso+spin (R5c: estabilizar braço da projeção
    segue como candidato, agora com evidência de entrada).

### C1 RE-PINADA — o claim de produto "3-4× menos contatos" RETRATADO
| run | cc_flag | cc_VERDADE | pos60_v | fora | pace | preso>60s |
|---|---|---|---|---|---|---|
| cego s0-s2 | 806/439/608 | 1003/521/709 | 434/154/142 | 45,9-48,7% | 192-210s | 0/2/0 |
| comp s0-s2 | 6103/595/116 | 6156/641/162 | 5508/410/40 | 44,5-51,2% | 179-217s | 2/0/0 |
Medianas: cego 709 vs comp 641 pares-tick — **SEM vantagem do composite em
contatos nas realizações de hoje**; pós-60s comp PIOR na mediana (410 vs 154,
puxado pelo derby s0: 2 carros em contato contínuo por centenas de s).
**VARIÂNCIA DE REALIZAÇÃO DOMINA: cc do comp s0 = 251 (ontem) → 6103 (hoje,
mesmo seed/código) = 24×.** Qualquer A/B a 3 seeds é frágil demais para
claim de produto.

### ÁRVORE EXECUTADA + VEREDICTO
1. Razão ∈ [1,1; 1,5): **v3 = instrumento canônico**, fatores por run;
   números R4 re-pinados onde o instrumento importa.
2. Ramo "proxy era o artefato" (mediana 1,08 < 1,1): **RETRATAÇÃO formal do
   "70% contato-não-amostrado"**; ramo pilotage RE-ABERTO e CONFIRMADO.
3. R5b rejoin-com-gap: abaixo do threshold na mediana — mantém como proposta
   secundária. R5c wanderer: entrada confirmada (fling), proposta mantida.
4. **Nova frente #1 (evidência): pilotagem race-speed (80-88% das raízes,
   ~50/50 residual/solo)** — caracterização M0-style (onde na pista, o que a
   obs via, g/kappa/r por saída) antes de qualquer fix.
5. **Protocolo**: A/B de produto exige N≥10 seeds (ou variância reduzida pós
   RNG do clima); mediana de 3 é insuficiente para claims de produto.

### Artefatos R3
- Fix: `scripts/run_race_10_cars.py` (bearing law + REJOIN_AHEAD_M/REJOIN_BEARING_GAIN).
- Testes: `tests/test_deep_rejoin.py` (sintético PASS 15,7 s);
  `tests/test_race_layer.py::test_rejoin_gains_authority_off_track` atualizado
  p/ lei de bearing; suite 61 pass + 1 skip (2 falhas PRÉ-EXISTENTES registradas:
  import `_resample_closed_polyline` inexistente; curvature-cap no preset 240wp).
- Instrumentação: `race_diagnostic` imprime FORA-PILOTAGEM vs FORA-PRESO
  (janelas 30 s), CARROS-PRESO/sessão e HESITAÇÕES; `scripts/gate_multi_seed.py`.
- CSVs/logs: `race_diag_b31_v3_seed{0,1,2}.{csv,log}`. Mudanças NÃO commitadas.

## Próximos passos recomendados

0. **v15 PÓS-R5a (prioridade — re-pós da re-medida com instrumento canônico)**:
   - **Frente #1: PILOTAGEM race-speed** (80-88% das raízes; ~50/50
     residual/solo; v0 18-22 m/s, esterço forte): caracterização M0-style
     SÓ LEITURA (onde na pista, o que a obs via nos ticks de saída: g_gate,
     kappa por preview, d_min, r_norm) ANTES de qualquer fix. A hipótese
     "residual manda mal" e "solo erra" ficam EMPATADAS — a caracterização
     decide.
   - **Semear o RNG do clima por seed** (1 variável, comportamento — precisa
     aprovação): elimina a componente entre-sessões do não-determinismo;
     A/B intra-dia vira bit-reproduzível; prerequisite para A/B de produto
     confiável.
   - **A/B de produto exige N≥10 seeds** (mediana): 3 seeds mostrou-se
     frágil (cc comp s0: 251→6103 entre dias). Alternativa: métrica por
     VOLTA (taxa), não total de 600 s.
   - R5b rejoin-com-gap: DESCLASSIFICADO p/ secundário (mediana 23% < 30%);
     manter proposta p/ realizações onde domina.
   - R5c wanderer: entrada por fling CONFIRMADA (impulso 10s antes);
     estabilizar braço da projeção segue candidato.
   - CONCLUÍDO em R5a: instrumento solver-side canônico (v3, testes 3/3);
     guarda com causa-raiz nomeada (RNG do clima); retrações R4 registradas.
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
