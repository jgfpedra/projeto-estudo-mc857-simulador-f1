# Auditoria do pipeline de RL (antes da reestruturação)

## Problemas confirmados em código

### Críticos
1. **Espaço de ação redundante**: `[throttle, brake, steer]` com exclusão mútua aplicada *depois* da amostragem
   (`action_to_controls`). A rede precisa aprender duas ações para uma decisão (velocidade), e em metade
   do espaço de ação o gradiente é zero (qualquer ação com throttle≥brake zera o brake).
2. **Inconsistência policy ↔ env no PPO**: `_act()` amostra de Gaussiana **sem squash/clip**
   (train_multi_context_ppo.py `_act`), o logp é calculado na amostra crua, mas o ambiente clipa.
   Resultado: as ações aplicadas à física diferem das ações cuja probabilidade foi otimizada;
   o ratio do PPO é calculado sobre uma ação que não é a executada.
3. **Recompensa sem penalidade de overspeed**: `P_SLOW` só pune andar devagar; nada pune entrar
   rápido demais numa curva. A política ótima local vira "acelerar sempre e aceitar o crash na
   penúltima curva" — exatamente o observado nos logs (morte consistente ~450-800m).
4. **GAE trata truncamento como terminal** (`1 - done_arr[t]`), sem bootstrap do valor em `trunc`.
   Raro com max_steps alto, mas errado.

### Altos
5. **Previews insuficientes**: só 3 distâncias (30/60/120m) e só mudança de heading. Sem curvatura
   assinada por ponto, a rede não distingue "reta que entra em hairpin" de "curva suave".
6. **Memorização posicional**: `s_frac` (posição absoluta na pista) permite decorar o mapa em vez de
   reagir à geometria local — ruim para robustez e para pistas novas.
7. **Colapso de exploração no esterço**: std do esterço convergiu para ~0.05 (logs), com
   `log_std` clipado em [-3, 0.5] — o clip superior permite, mas o aprendizado do std não foi limitado
   por baixo cedo o suficiente.
8. **Melhor checkpoint por retorno médio**, não por taxa de conclusão de volta.

### Médios
9. Curvatura da observação derivada de waypoints vizinhos é ruidosa com espaçamento desigual
   (FastF1 dá ~180 pontos não-uniformes por volta).
10. `initial_position(0)` usava o grid do FastF1 (colado na curva 4) — corrigido na sessão anterior
    com detecção automática da melhor reta.

## Achado dominante (descoberto durante a validação): física

0. **Subesterço estrutural do modelo lateral** (physics.py): em skidpad controlado
   (velocidade alvo 20 m/s, esterço fixo 15°, grip_override=1.0), o raio da trajetória
   era 3–6x o do modelo bicicleta (raio ~40–50 m vs 12,7 m), porque (a) a rigidez de
   deriva `c_alpha=12` exigia slip de ~7° para liberar 80% da força lateral — o vetor
   velocidade não acompanhava o corpo — e (b) nada restringia a trajetória ao bicicleta.
   Com a curva mais fechada da pista real em raio ~27 m, **fazer a curva era
   fisicamente impossível** para qualquer política — é por isso que todos os treinos
   morriam nas curvas. Correções:
   - `c_alpha` 12 → 40 (slip típico de F1: 2–4°);
   - nova "fase 4b": curvatura cinemática do vetor velocidade ancorada no bicicleta
     (`omega = v·tan(δ)/L`), com teto por aderência real (mu_eff × Fz/massa, inclui
     downforce) — implementado via `resetBaseVelocity` por sub-step;
   - descoberta extra: `grip_multiplier` real nos treinos era ~0.5–0.79 (pista a 42 °C
     vs pneu ótimo 95 °C + fator de superfície). O ambiente de treino agora usa
     `grip_override=1.0` (aprende pilotagem, não química de pneu); a avaliação roda
     com grip realista (`grip_override=None`).
   Baseline clássico pós-correção: **completa a volta em ~108 s** (a_lat 12), sem
   respawn. Antes da correção: impossível em qualquer velocidade.

## Fase A — reprodução instrumentada da falha (pós-v2)

Avaliação do checkpoint v2 corrigida (eval_policy agora aplica tanh e roda SEM respawn,
grip realista). Resultado: 10/10 episódios, deterministicamente, "saiu da pista" em
**s ≈ 1158–1163** a ~150 km/h, lat ≈ 8–9 m.

Trace por passo (`--dump-csv`) mostrou:
- **Percepção OK**: o preview carrega `kappa=0.037` (hairpin) já a 150 m de distância;
  o esterço vai a +1.0 no lugar certo. Não é problema de observação nem de direção.
- **A política nunca freia**: `a_long` ≥ −0.04 no trecho inteiro e `brake=0.00` a
  224 km/h. É uma falha de aprendizado da decisão longitudinal — ir rápido pagava
  progresso integral até o crash descontado por γ; P_FAST antigo (curvatura só na
  posição atual) não contrabalançava.
- Grip de treino (1.0) vs real (0.79) NÃO explica: com grip 1.0 a avaliação falha
  até mais cedo/rápido (193 km/h). Domain randomization de aderência ficou
  implementada (`grip_random`) como currículo, não como causa raiz.
- O baseline clássico passa a mesma curva a ~20 m/s porque planeja velocidade por
  DISTÂNCIA DE FRENAGEM. A recompensa agora usa a mesma regra: `_v_allow_at` =
  min_d sqrt(v_curve(d)² + 2·a_brake·d), e o prêmio de progresso é multiplicado por
  min(1, v_allow/v). Andar rápido demais deixou de pagar.

## Fase 12 — incompatibilidade NPX da corrida de 10 carros

Causa exata: `NumpyNeuralActor` casava pesos por shape e exigia camada de saída
(32,3)/(3,) — arquitetura v1 `[throttle, brake, steer]`. O checkpoint v2 exporta
(32,2)/(2,) (`[steer, longitudinal]`), então a validação falhava com `['w5','b5']`.
A primeira densa (37,256) é compatível com a obs v2 (23+2+8+4=37 ✓) — a matriz NÃO
era o problema. Correções:
- Loader aceita (32,2)/(2,) e registra act_dim; valida a dimensão de entrada com erro
  explícito em caso de obs incompatível.
- run_race_10_cars: `--actor` para escolher o checkpoint; padrão prefere v2/; o NPZ
  é reexportado a partir do .keras escolhido (com st_mtime check).
- Paridade Keras↔NumPy coberta por teste (test_npz_parity_keras_vs_numpy).

## Decisões (referência F1TENTH Gym)
- **Observação**: estado local compacto + preview geométrico em 7 distâncias (heading_change e curvatura
  assinada por ponto). Remove `s_frac` e slip angles da cabeça da política (mantidos só como log).
  heading_err vira (sin, cos) para evitar descontinuidade em ±π.
- **Ação**: 2D `[steer, long]` em [-1,1]²; long>0=throttle, long<0=brake. Conversão num único ponto.
- **PPO**: política tanh-squashed com correção de log-prob (inversão atanh no update). GAE com
  bootstrap em truncamento. `log_std` com piso explícito para não colapsar exploração.
- **Recompensa**: progresso denso + gates + penalidade de overspeed vs velocidade segura da curvatura
  futura + componentes logados individualmente.
- **Avaliação**: métrica principal = taxa de conclusão de volta SEM respawn.

---

# Investigação da regressão v2 → v4 (corrida visual, carros a 0 km/h)

## Fase A — artefatos (hashes sha256/16)
| Modelo | sha | arch |
|---|---|---|
| multi_context_bc_v2.keras | 57bb984569e3f89d | 23→2 |
| multi_context_bc_v2b.keras | 1d1c134d0f827f9a | 23→2 |
| v2/rl_actor_best.keras | bea02606a9b31bfc | 23→2 |
| v3/rl_actor_best.keras | 8e984b5a1dd9d57c | 23→2 |
| v4/rl_actor_best.keras | cacdd464af10c64d | 23→2 |
| v4/rl_actor.keras (final) | 244516abf2932674 | 23→2 |
Todos compatíveis entre si (mesma obs 23, mesma ação 2). v4 inicializado do
BC v2b (o BC pai NÃO freia no ponto crítico → o freio persistente veio do PPO).

## Fase B/C — corrida reproduzida headless (race_diagnostic.py, 150 s, 10 carros)
- **v4**: 10/10 carros travados a 0,00–0,04 m/s em s≈5–31 (~1580 m de progresso),
  dentro da "curva-monstro" s∈[4210,50] (kappa 0.129, R≈7.7 m — 3.5× mais fechada
  que a pior curva vista no treino, s≈1158/kappa 0.037). VER: brake 0.94–0.99
  contínuo por 100+ s A 0 m/s (comando da POLÍTICA; governador inativo a v=0;
  recovery exige lat>12).
- **v2**: carros param em s≈2027–2391 (~3900 m) — quase uma volta. Regressão
  confirmada e quantificada: v4 para 2.5× antes.

## Fase D — mesmo estado, ações opostas (observações REAIS do deadlock)
No deadlock de VER (v≈0, dentro da curva-monstro, previews kappa_obs +2.15/+1.88):
- v2: long +0.23…+0.31 (ACELERA — por isso avança)
- v3: long +0.98…+1.00
- BC v2b: long −0.03…+0.20
- **v4: long −0.94…−0.99 (FREIO QUASE TOTAL — bate com o brake 0.94–0.99 da corrida)**
Causa: PPO com o gate v_allow ensinou "kappa alto → freio forte"; a rede
EXTRAPOLA para kappa 3.5× fora da distribuição e mantém freio a v=0 (estado
que o treino nunca visita — o STUCK encerra o episódio em 4 s; a corrida não
tem término).

## Causa do 0 km/h PERMANENTE (dois bugs compostos)
1. **Política v4**: freio persistente fora de distribuição (acima).
2. **Anti-stall da corrida**: condição `speed < 2.0 and brk == 0.0` — QUALQUER
   freio da política (0.06 basta) bloqueia a recuperação para sempre, e o
   `else` reseta o timer a cada tick com freio. Reproduzido com v2 TAMBÉM
   (para mais tarde, s≈2381, freio residual 0.05–0.13). O bug estrutural é da
   corrida; v4 apenas o encontra 2.5× mais cedo.
3. Agravante: `MODEL_DIR` hardcoded em `model_train/v2` fazia o DEFAULT da
   corrida carregar SEMPRE o ator v2 (v3/v4 nunca candidatos) e quebrava
   mappings.pkl/scaler_*.pkl (que vivem na raiz de model_train).

## Correções (conjunto mínimo)
1. `run_race_10_cars.py` — `_anti_stall` autoritário e testável: parado/lento
   > 1 s → th=0.8, brk=0 SEJA QUAL FOR o comando da política; timer só reseta
   com v ≥ 5 m/s.
2. `run_race_10_cars.py` — `MODEL_DIR = model_train` (raiz) + default do ator =
   checkpoint mais recente por mtime entre v2/v3/v4/raiz (proveniência impressa).
3. `train_multi_context_ppo.py` — `training_meta{,_best}.json` com iteração,
   lap%, retorno e std a cada salvamento (rastreabilidade da Fase F).

## Validação
- Race diag v4 pós-fix: 10/10 carros a 12–40 m/s em s≈2370–2886 (~3900–4400 m),
  ZERO travados (amostras v<2: 15–59, só largada/transitórias vs 509–526 antes).
- Corrida real headless (default=v4): a 105 s, todos a 48–105 km/h, 3.2–3.5 km.
- Testes: 73/73 (5 novos em tests/test_regression_v2v4.py).
- Nenhuma mudança em física/recompensa/política/currículo — só camada de corrida.

---

# Corrida multi-carros: paradas involuntárias + cortes de curva na grama

## Reprodução (250 s headless, 10 carros, v4 — ANTES dos fixes)
- 7,4% das amostras com centro fora do asfalto; lat máximo 39,4 m.
- Carros PERDIDOS na grama com anti-stall forçando th=1.00 (ex-LEC a 39 m,
  ex-VER a 35 m com esterço em lock): a política nunca treinou além de 7,8 m
  de erro lateral (o env termina o episódio lá) e o anti-stall anterior
  acelerava às cegas. São os "carros parados que só voltam a andar quando
  são atingidos": perdidos, em ciclos de parada, recuperando por impulso.
- Trechos críticos coincidem com kinks da spline (s 0-50, 2050, 2430).

## Causa raiz dos CORTES (Problema B)
Spline Catmull-Rom UNIFORME sobre 15 marcadores FastF1 espaçados de forma
desigual → overshoot: micro-segmentos de 6-10 m com giros de 30-50°, pico
kappa=0.129 (R=7,7 m; Ferradura real ≈ R 20 m). Segmentos medidos: 6,4-37,6 m
(amostragem por segmento-de-controle, não por arco). Curvas impossíveis +
threshold de recovery a 2× a meia-largura (12 m) = carros atravessando grama.

## Causa raiz das PARADAS (Problema A)
Composição: (1) carros jogados fora nos kinks; (2) política sem competência
off-track; (3) anti-stall forçando torque na grama; (4) recovery antigo
só reagindo a 12 m e só freando acima de 20 m/s. Carros vagavam até 39 m,
paravam em ciclos e recuperavam (visualmente) quando atingidos.

## Correções
1. `domain/track.py`: Catmull-Rom CENTRÍPETA (Barry-Goldman, α=0.5) — elimina
   overshoot por construção; `_resample_closed_polyline` por SUBDIVISÃO
   (≤4 m, preserva comprimento exato — o resample uniforme por passo de arco
   cortava a corda de fechamento e alterava o comprimento oficial).
2. `track_loader.py`: subdivisão aplicada SEMPRE após toda escala/correção de
   unidades (fazer antes reamostrava em unidades cruas e estourava o cap).
   Pista real: 1131 wps, segmentos 2,68-4,00 m, kappa máx 0.102 (era 0.129),
   sem REGIÕES de kinks (ponto único no ápice da hairpin — limite da
   interpolação com 15 marcadores).
3. `run_race_10_cars.py`: MODO REJOIN — autoridade total fora do asfalto:
   gatilho a 1× meia-largura (era 2×), esterço p/ linha central, velocidade
   alvo 8 m/s (freia acima, torque 0.35 abaixo), política perde autoridade
   longitudinal na grama. Bloqueio por contato: carro parado em contato com
   outro → torque limitado a 0.25 (sem arremetida). `last_authority` registra
   quem manda em cada tick (policy/governor/anti_stall/rejoin/blocked).

## Validação (250 s headless, MESMO v4 — DEPOIS)
| Métrica | Antes | Depois |
|---|---|---|
| Amostras fora do asfalto | 7,4% | **1,9%** |
| lat máximo | 39,4 m | **7,7 m** |
| Paradas ≥ 3 s | (ciclos na grama) | **0** |
| Autoridade | policy cega na grama | policy 75% / gov 21% / rejoin 1,8% / anti_stall 1,7% |

Testes: 90/90 (17 novos em tests/test_race_layer.py: curvatura sintética —
reta/R conhecido esq/dir/hairpin/espaçamento desigual/fechamento; subdivisão
exata; cap de kappa real ≤0,11; cenários anti-stall 3,6,7,8; recuperação
física headless com verificação de velocidade E progresso; guarda de cusps).

## Limitações
- A política RL em si (v2/v3/v4) continua sem completar a prova do env
  (déficit longitudinal documentado na investigação anterior). Re-treinar
  sobre a geometria corrigida é o próximo passo — a observação é local
  (sem posição absoluta), então os checkpoints atuais continuam carregáveis,
  mas o kappa dos previews muda de distribuição (picos 3,2→2,6 em obs units).
- A fonte FastF1 só tem 15 marcadores: o ápice da hairpin fica R≈10 m
  (real ≈ 15-20 m). Melhorar exige telemetria de volta real como fonte.

---

# Investigação definitiva — "carros parados até serem empurrados" (persistente)

## Divergência headless × visual (Fase A) — CAMINHOS SÃO IDÊNTICOS
Linha a linha: `run_race()` e `race_diagnostic.py` chamam o MESMO
`predict_batch` → `set_driver_input` → `_step_tick` → `step_with_control`.
O código exclusivo do GUI é inócuo: `_poll_gui_keyboard` não publica nada com
o piloto ocioso (teclas w/a/s/d/espaço/r; as teclas de câmera o/f/l não o
atingem), `draw_track_surface` é corpo SEM colisão (`baseCollisionShapeIndex=-1`),
`realtime` só space o wall-clock. A física GUI↔DIRECT é a mesma.
**A divergência era do INSTRUMENTO, não do caminho**: 3 detectores de contato
estavam mortos (abaixo) e o threshold de "parada ≥3 s" não via o padrão real.

## Instrumentação morta (3 bugs)
1. `p.getContactData` NÃO EXISTE neste pybullet (AttributeError silenciado
   por try/except → "0 contatos" em todos os relatórios anteriores).
2. `getContactPoints` retorna TUPLAS de 14 campos (c[1]=bodyA, c[2]=bodyB,
   c[9]=força normal) — `getattr(c,'bodyUniqueIdB')` devolvia None →
   `_contact_with_other_car` sempre False (o cap de bloqueio nunca atuou).
3. No diagnóstico, `getattr(c,'appliedImpulse')` em tupla → 0.0.
Corrigidos: diagnóstico agora separa contato solo × carro-carro; o controlador
lê c[1]/c[2]/c[9] com limiar de força > 1 N.

## Causa raiz da parada persistente (com dados)
O anti-stall anterior liberava ao cruzar 5 m/s. A política v4, nas curvas
fora da sua distribuição de treino (kappa_obs ~2,6 vs ~2,25), re-freava no
tick seguinte → CICLO-LIMITE parar/andar: 96 episódios de 0,3–1,0 s numa
corrida de 600 s, concentrados nas curvas fechadas (s≈0, 2000–2400, 4000),
v média no hairpin 11,5 m/s com mínimos de 0. Na corrida visual (com tráfego),
carros de trás chegavam durante as fases paradas eempurravam — impulsos
reais (contatos carro-carro: 1589 amostras, picos ~3,5× o peso do carro) que
coincidiam com os bursts do anti-stall → percepção correta do usuário:
"parado até alguém empurrar".

## Correção (Fase C/D): composição com precedência + RECUPERAÇÃO com progresso
Precedência explícita em `predict_batch` (o rótulo `last_authority` registra
quem definiu th/brk FINAIS em cada tick):
  5. policy → 4. governor → 3. rejoin (fora do asfalto) → 2. recovery →
  1. blocked (segurança, cap 0.25 por último).
`_recovery_step` (máquina de estado por piloto, testável):
  - engate: v<2 m/s por >1 s (0,15 s se re-estolou <5 s após liberar);
  - ativa: torque progressivo até 9 m/s (abaixo de todo v_safe da pista),
    freio ZERO — o freio da política não cancela a recuperação;
  - saída: SOMENTE com ≥25 m de progresso físico (cum_dist) e v≥3 —
    oscilações de velocidade não rearmam o freio da política;
  - fora da pista: só zera o freio (o rejoin comanda velocidade/esterço);
  - timer reseta SÓ com v ≥ 5 m/s (freio residual nunca resetou nada).
O anti-stall antigo foi REMOVIDO (subsumido); testes migrados.

## Validação headless 10 carros (600 s, mesma v4)
| Métrica | Antes | Depois |
|---|---|---|
| Episódios de parada ≥0,3 s | 96 | 31 (−68%) |
| Tempo total parado (v<0,5) | 34 s (3,4 s/carro) | 12 s (1,2 s/carro) |
| Parada máxima | 1,0 s | 1,0 s — ZERO ≥3 s |
| v média no hairpin | 11,5 m/s | 13,2 m/s |
| Fora do asfalto | 2,5% | 2,3% (lat máx 8,5 m) |
| Autoridade | policy cega | recovery 4,4%, blocked 0,7% atuantes |

Testes: 91/91 (9 novos em tests/test_recovery_state.py — cenários 1-8 do
enunciado + progresso real + anti-chatter + off-track; os testes de _anti_stall
foram migrados, não duplicados).

## Limitações
- As 31 hesitações restantes (média 0,74 s) são os stalls de PRIMEIRA
  engatação (timeout 1 s) quando a política trava o carro vindo em alta —
  inerente ao comportamento da política v4 fora de distribuição; a recuperação
  assume em ≤1 s e atravessa com autoridade. Eliminá-las por completo exige
  re-treino na geometria nova (fora do escopo desta etapa, conforme instruído).
- Teste visual (Teste 5) a ser confirmado pelo usuário: o caminho de controle
  é idêntico ao headless (demonstrado acima); comando na seção de reprodução.

---

# v5 — currículo de curvas + BC + PPO (eliminação das hesitações)

## Fase A — os dois pontos (mecs. distintos, mesma assinatura)
- **Curva aberta s≈2026–2044** (R=18,4): 14 hesitações; v4 chega a 2–5 m/s e
  AINDA freia (brk 0,30–0,66) até v≈10⁻⁶ — autoridade "policy".
- **Hairpin s≈2274–2301** (R=9,8): 19 hesitações; freio 0,40–0,95, idem.
- (Wrap s≈4143–4158: 10, misto policy/blocked_contact — tráfego.)
Mecanismo comum: **a própria política freia até quase-zero** chegando devagar —
não é recoverable-sozinho; é pilotagem.

## Fase B — baseline na geometria atual: VÁLIDO
Volta completa em 106 s; curva aberta v_min 15,2 m/s; hairpin v_min 13,1 m/s;
wrap v_min 19,2 m/s; lat máx 4,4 m — tudo dentro do asfalto, zero paradas.
O professor serve de gerador de demonstrações.

## Fase C — divergência v4 vs professor (mesmos estados)
v4 freia forte em 22–57% dos estados onde o professor freia 0–7%
(por faixa de kappa 0,01–0,12). 74/1060 estados com "v4 freia, professor
acelera" (kappa médio 0,021, v 35 m/s). Confirma OOD herdado da geometria
antiga (onde frear em kinks era racional).

## Fase D — currículo de aproximação (start_zones)
`f1_env.py`: `start_zones=[(s_lo,s_hi)...]` + `zone_frac`. Nasce 100–300 m
antes de cada curva crítica com v0 ~ U(0,5,1,15)×v_allow(distância de
frenagem) + jitter lateral/heading. Trainer: `--start-zones "1748:1948,..."`.

## Fase E — BC v5 (geometria nova, split por EPISÓDIO)
10 voltas + 30 aproximações às zonas; split por episódio (sem vazamento).
val_loss 0,0125 | err steer 0,012 | err long 0,049 | err em frenagem 0,126
(n=51). BC puro em closed-loop: 0/10 — morre aos 3996 m a 152 km/h sem frear
(covariate shift; o frenar proporcional do professor é sub-representado).

## Fase F — PPO v5/v5b (BC init + zonas)
80 + 800 + 1600 iters, grip-random 0,75–1,0, random-start 0,6–0,7.
**Primeiras voltas válidas em TREINO do projeto (lap% 0,5 nas iters 506–509
e v5b/64)** — episódios com prog até 2055 m (passando os 2 pontos críticos).

## Fase H — avaliação comparativa (determinístico 10 eps + corrida)
Determinístico (sem respawn, grip real): TODOS 0/10.
Parede universal: **wrap corner** (R 47→27 decrescente, ~775 m após a
largada) — morre a 27,8–41,1 m/s onde a curva exige 19,5–22.
| corrida 600 s | v4 | v5 | v5b |
| hesitações ≥0,3s | 38 | 58 | 45 |
| tempo total parado | 32 s | 41 s | **28 s** |
| parada máxima | 1,4 s | 2,0 s | **1,0 s** |
| v hairpin / aberta | 9,2/12,2 | 7,9/8,6 | 8,3/10,8 |

## Conclusão honesta (NÃO validado)
- Meta 8/10 voltas: NÃO atingida (0/10). Meta "sem parada >0,5 s": parcial
  (v5b max 1,0 s). As hesitações nos 2 pontos não foram eliminadas pela
  política — a camada de recuperação continua necessária.
- Bloqueio dominante: o wrap corner (raio decrescente) mata TODO episódio
  determinístico antes dos 2 pontos; exige trail-brake de ~45→20 m/s em ~90 m.
- v5b checkpoint preservado como EXPERIMENTAL (model_train/v5b/). A corrida
  visual deve usar --actor para escolher entre v4 (mais rápido nas curvas) e
  v5b (menos tempo total parado); nenhum dos dois é validado.

## Próximos passos com maior retorno
1. DAgger: rodar v5b autorregressivo, coletar estados onde sai da pista e
   re-rotular com o professor (ataca o covariate shift do BC onde dói).
2. Demonstrações dedicadas do wrap: aproximações a 1,0–1,4× v_safe com o
   professor executando o trail-brake (o trecho mais sub-representado).
3. Mais iterações com o currículo de zonas — lap% 0,5% é a primeira evidência
   de que o gradiente existe; 8/10 precisa de 1–5M passos concentrados.

---

# v6 — pace: o bug do hint, a margem de frenagem e o colapso de exploração

## FASE 0 — v5c validado
- sha 75b19b671d7769b8 | 23→2 | paridade NumPy 1,2e-07 ✓
- Determinístico: 0/10 — TODOS na curva do wrap (s 7–19, a 89–112 km/h).

## CAUSA RAIZ HISTÓRICA (bug do hint) — resolvido nesta fase
`prev_waypoint_idx` da engine era inicializado no `setup()` com o start/finish
PRÉ-ajuste (wp 729) e nunca ressincronizado quando o env teleportava o carro
no reset (wp 929). A busca em janela de `_compute_grip` rastreava uma região
espacialmente próxima mas ERRADA da pista; no wrap essa região divergia ->
distância "450 m" com o carro NO asfalto -> surface factor 0.35 (grama) ->
**grip 0.28 no meio do asfalto** -> subesterço -> morte. Instrumentado:
g_mult=0.280 logado tick a tick. Efeitos: TODAS as avaliacoes determinísticas
morriam no wrap (v2..v5c E o professor!); o treino tinha grip corrupto no
início de todo episódio; a corrida visual só funcionava porque rejoin/recovery
mascaravam. Correções: (1) `nearest_segment()` busca completa com índice;
(2) auto-recuperação em `distance_to_centerline_near` (dist>30 m -> busca
completa); (3) ressincronização explícita em env.reset() e place_grid().
**Pós-fix: o professor completa a volta no grip REAL (114 s) — a "parede do
wrap" era 100% o bug.**

## v6 (margem de frenagem) e v6b
- v6 (A_BRAKE_REF=12, 1600 iters, zonas no wrap): treino lap% 7,5; determinístico
  ainda 0/10 no wrap (entra a 95–128 km/h; o v_allow planejava frenagem no
  LIMITE físico — sem margem para erro de execução).
- v6b (A_BRAKE_REF 12→10 = margem 83%, evidência: 17/17 falhas por sub-frenagem;
  professor passa freando a ~7,3 m/s²): **wrap PASSOU** — determinístico
  800→2712 m (3,4×). Nova parede: curva s≈1936 após 1,8 km de reta.

## v6c (3200 iters, zonas duplicadas) — parede de 1936 persiste
Trace da falha: a política a 181–256 km/h com a_long=+0.99 (acelerador cheio),
v_allow caindo 127→56; DOIS blips de freio (-0.42, -0.45) e retorno ao
acelerador. Diagnóstico: **colapso de exploração** — média saturada tanh(+0.99)
com std 0.23 ⇒ P(amostrar freio)≈0; a política não consegue explorar frenagem
sustentada nas retas. (A física permite: de 69→17.8 m/s em ~190 m de freio.)

## v6d (em curso)
min_std 0.15→0.30 (piso de exploração) + --init-std 0.5 na continuação.

## Infraestrutura v7 (multitrack) pronta
- Auditoria FastF1: Monza/Monaco/Silverstone/Suzuka/Zandvoort/Hungaroring/
  Catalunya carregam com geometria plausível.
- Split: TREINO=Interlagos,Monza,Hungaroring,Silverstone | VAL=Zandvoort |
  TESTE=Monaco,Suzuka,Catalunya.
- `--tracks "A,B,..."` distribui round-robin nos workers; `--start-zones auto`
  detecta as 3 curvas mais fechadas POR GEOMETRIA (sem coordenadas hardcoded);
  `--track-id-embed 0` força a política a usar só a geometria local.
- Benchmark de setores (`sector_benchmark.py`) e profilador de curvas prontos.

## v6d (init-std 0.5) + v7 multitrack — resultados finais

### v6d: o piso de exploração não quebrou o muro de 1936
Determinístico: misto (algumas regressões ao wrap 803 m, outras no mesmo
1936). A média saturada tanh(+0.99) precisa de ~5σ para amostrar freio —
mesmo std 0.5 não gera frenagem sustentada por amostragem. OBSERVAÇÃO
adicional: `v_allow` oscila ±60 km/h entre steps na região de 1936 (janela
de curvatura em segmentos ruidosos) — sinal de recompensa inconsistente no
ponto exato da falha.

### Corrida de 10 carros (600 s, assistida) — leaderboard honesto
| política | hesitações ≥0,3s | t parado | máx | fora asfalto |
|---|---|---|---|---|
| **v5c pós-fix** | **21** | **18 s** | 1,6 s | 4,6% |
| v4 | 38 | 32 s | 1,4 s | 2,3% |
| v6c | 76 | 62 s | 5,4 s | 6,6% |
O v5c pós-fix é a MELHOR política de corrida medida; o fix do hint melhorou
a que o usuário já havia validado visualmente. As v6 (treinadas com margem
de frenagem) ficaram super-conservadoras na corrida assistida.

### Determinístico (autônomo) — leaderboard
| política | progresso | parede |
|---|---|---|
| v6b/v6c | **2712–2720 m (65%)** | curva s≈1936 (frenagem de 250 km/h) |
| v5c/v6d | 803 m | wrap |
Critério 9/10: NÃO atingido (0/10 todos). Causa remanescente documentada:
exploração de frenagem sob saturação tanh + v_allow oscilante em 1936.

### v7 multitrack (800 iters, pool 4 pistas, treino lap% 7.0)
| conjunto | pista | v7 prog% | v5c zero-shot prog% |
|---|---|---|---|
| TREINO | Interlagos/Monza/Hunga/Silver | 19/13/18/32 | — |
| VAL | Zandvoort | 19 | 19 |
| TESTE | Monaco | **38** | 26 |
| TESTE | Suzuka | 24 | 25 |
| TESTE | Spa(Catalunya) | 21 | 21 |
Generalização NÃO declarada: ganho modesto em Monaco, paridade nos demais,
0 voltas em todas. Pipeline validado (7 circuitos, zonas por geometria,
obs local — a representação se mostrou adequada: mesmas faixas de kappa/vel
em todas as pistas).

### Limitações e próximos passos (ordenados por retorno)
1. Suavizar `v_allow` (média móvel sobre s) — o sinal oscilante em 1936 é a
   causa imediata identificável do não-aprendizado daquele trecho.
2. DAgger nos estados de falha (250 km/h pré-1936 + wrap): re-rotular com o
   professor (que passa de 114 s) e misturar ao buffer PPO.
3. Se necessário: recompensa de frenagem antecipada específica (crédito
   denso por iniciar frenagem antes do ponto físico) — só após 1-2.

---

# v8 — Edge-Aware Observation (LiDAR virtual) + avaliação

## Percepção de bordas implementada (Fase C/D)
11 raios virtuais a partir do heading do carro (±90° a cada 18°), alcance 40 m,
medindo a distância às POLILINHAS DE BORDA do asfalto (não à linha central,
não à grama). Correção importante: a fórmula inicial de interseção
raio-segmento tinha sinal invertido — reescrita com a fórmula padrão
(cross(D,B-A) etc., caso-teste P=(0,0) D=(1,0) A=(5,-1) B=(5,1) → t=5 ✓).

**Leituras fisicamente corretas** (Interlagos):
| posição | raio frontal | ±90° |
|---|---|---|
| reta (s=450) | 40m (max) | 6.0/6.0m |
| hairpin ápice (s=2309) | **10.6m** | 5.3/6.0m |
| wrap ápice (s=0) | **19.0m** | 6.0/6.0m |
| curva aberta (s=2048) | **10.2m** | 5.5/7.3m |

O sinal de "a pista fechou na minha frente" é DIRETO: no hairpin, o raio
frontal mostra 10m de asfalto restante mesmo com lat_err=0 — informação que
os previews de curvatura não dão da mesma forma.

**obs_mode**: 'legacy'=23d (compatível v2-v7) | 'edge'=34d (v8+).
111/111 testes passando (20 novos em test_edge_obs.py).

## BC edge (Fase E)
Professor na geometria corrigida, obs edge, split por episódio.
val_loss=0.0166 | err_steer≈0.01 | err_long=0.057 | err_brake=0.143.
BC-edge puro em closed-loop: 0/3 (morre no wrap a 190 km/h — covariate
shift do BC, igual ao legacy). O ator edge tem 48 entradas (vs 37 do
legacy) — checkpoints antigos são INCOMPATÍVEIS por design (versionamento).

## PPO v8 edge (1600 iters, zonas, grip-random, A_BRAKE_REF=10)
Treino lap%: 4.0 (best iter 1372). Determinístico 10 eps: **810m** (wrap).

## COMPARAÇÃO: edge vs legacy (mesmo protocolo, grip real, sem respawn)
| modelo | obs | voltas | prog | obs de morte |
|---|---|---|---|---|
| v5c | 23d legacy | 0/10 | 795m | wrap (125 km/h) |
| **v8_edge** | **34d edge** | **0/10** | **810m** | **wrap (125 km/h)** |
| v6b | 23d legacy | 0/10 | 2703m | curva 1936 (246 km/h) |
| professor | — | ✓ | 4173m | — (114 s) |

**Conclusão honesta**: a observação edge alcança PARIDADE com a legacy no
mesmo orçamento de treino (1600 iters do BC). NÃO supera a v6b — cuja
vantagem vem do ACÚMULO de iterações na linhagem (v5c→v6→v6b≈8000 total),
não da representação. Os raios de borda são infraestrutura válida e
fisicamente correta, mas o PPO precisa de mais dados para explorar o
sinal. O gargalo permanece a frenagem sustentada (exploração sob
saturação tanh).

## Zero-shot cross-track (v8 edge, treinada SÓ em Interlagos)
| pista | v8 edge (34d) | v7 multi-track (23d) |
|---|---|---|
| Monaco | 28% | 38% |
| Suzuka | **42%** | 24% |
| Spa | 21% | 21% |
| Zandvoort | 25% | 19% |

O v8 edge SUPERA o v7 em Suzuka (42% vs 24%) e Zandvoort (25% vs 19%) —
sugestão de que os raios de borda generalizam melhor que os previews de
curvatura (medem a geometria física local, independente do circuito).
Sem voltas válidas em qualquer pista — inconclusivo.

## Limitações e próximos passos
1. Mais iteração de PPO v8 (3200-5000) para dar tempo ao sinal edge.
2. DAgger: coletar estados de falha (wrap a 190 km/h), re-rotular com o
   professor, injetar a frenagem sustentada diretamente.
3. v9 edge multitrack: o zero-shot de Suzuka sugere transferência melhor;
   validar com treino multi-pista na obs edge.
4. Adaptar NeuralRaceController (run_race_10_cars.py) para obs_mode='edge'
   quando um modelo edge for selecionado para a corrida.

---

# Professor v2 — perfil de velocidade físico (Fase 0/1)

## H1 CONFIRMADA: A_LAT_MAX=14 desperdiça downforce
Medido no skidpad: a_lat real = 16.0 m/s² (v=20), 22.3 (v=40), 32.7 (v=60).
A constante 14 ignorava o downforce (~2,94·v² N). O planejador antigo perdia
~15-44% de velocidade em curvas médias/rápidas.

## H2 CONFIRMADA: V_TGT_MIN=15 quebra pistas apertadas
Interlagos hairpin v_física=13.4 m/s; Monaco=9.5 m/s. V_TGT_MIN=15 era 12-58%
acima do físico. O professor antigo FALHAVA em 6 de 8 pistas (só passava
Interlagos com a_lat=10).

## H3 CONFIRMADA: freio satura em |long|≈0,30
decel(long): -0.05→4.9 | -0.10→7.2 | -0.20→11.8 | -0.30→16.5 | -0.50→16.5
| -1.00→16.7 m/s². Faixa útil de frenagem: [-0.30, 0] — TUDO acima satura.
A ação PPO/BC desperdiça 70% do range.

## H4 CONFIRMADA: grip_override pula superfície
_compute_grip com override retorna DIRETO (bypassa fator de grama). Treino
nunca vê perda de grip fora do asfalto; avaliação sim (0.788×0.35=0.28 na grama).

## Correção do kappa (fator 2)
compute_kappa_profile tinha `kappa = dh / (2·ds)` — o central difference
`heading[i+1]-heading[i]` cobre 1 intervalo (ds), não 2. Corrigido para
`dh / ds`. Verificado: círculo R=50 → kappa=0.02 (antes 0.01). Teste
test_circle_kappa falhava com o valor antigo, passa com o correto.

## Janela de suavização: 20m (linha de corrida)
Janela 10m: k_max(hairpin)=0.111 (R=9m) — real demais para o pure pursuit.
Janela 20m: k_max≈0.078 (R=13m) — representa a linha efetiva. Igual ao
_kappa_signed do env. A janela 20m foi escolhida por dar o melhor tradeoff
entre completude (16/16) e tempo de volta.

## RESULTADO: professor v2 passa TODAS as 8 pistas (Meta A: 100%)
Parâmetros: sf=0.80, smooth_window=20m, ld_min=5, k_ld=0.6, grip real.

| pista | voltas | tempo | vs original |
|---|---|---|---|
| Interlagos | 2/2 | **107s** | 114s → **−6,1%** |
| Monza | 2/2 | 117s | (original falhava) |
| Hungaroring | 2/2 | 117s | (original falhava) |
| Silverstone | 2/2 | 136s | (original falhava) |
| Zandvoort (val) | 2/2 | 115s | (original falhava) |
| Monaco | 2/2 | 101s | (original falhava) |
| Suzuka | 2/2 | 131s | (original falhava) |
| Spa | 2/2 | 117s | (original falhava) |

**16/16 voltas válidas (100%)** — primeira vez na história do projeto.
128/128 testes passando (17 novos: test_velocity_profile.py).

## Próximo: DAgger multi-pista (Fase 2)
O professor v2 agora pode rotular QUALQUER estado (inclusive fora da linha).

---

# DAgger multi-pista (Fase 2) — a primeira volta neural válida da história

## O que mudou
1. Professor v2 com perfil físico (Fase 1): passes 16/16 em TODAS as 8 pistas.
2. DAgger (train_dagger.py): substitui o PPO-do-zero. Loop:
   - β=1.0 → demonstrações do professor v2 (com ruído σ=0.15)
   - β decai 1.0→0.0 ao longo de 10 iterações
   - A cada iter: rollout com mistura β, rotula TODOS os estados com o
     professor, agrega ao dataset (96k amostras finais), retreina BC
   - Obs: 'edge' (34d, com os 11 raios LiDAR)
   - Pistas de treino: Interlagos, Monza, Hungaroring, Silverstone
   - Validação (seleção de checkpoint): Zandvoort

## RESULTADO FINAL (determinístico, grip real, SEM respawn, 3 eps/pista)

### dagger_actor_iter10.keras (β=0, aluno puro)
| conjunto | pista | voltas | tempo |
|---|---|---|---|
| TREINO | Interlagos | **3/3** | **104s** |
| TREINO | Monza | **3/3** | 115s |
| TREINO | Hungaroring | **3/3** | 113s |
| TREINO | Silverstone | **3/3** | 133s |
| VALIDAÇÃO | Zandvoort | **3/3** | 109s |
| TESTE | Spa/Catalunya (zero-shot!) | **3/3** | 114s |
| TESTE | Suzuka (zero-shot) | 0/3 | 3322m (58%) |
| TESTE | Monaco (zero-shot) | 0/3 | 1306m (40%) |
| **TOTAL** | | **18/24 (75%)** | |

### dagger_actor_iter8.keras (best por val_loss)
Treino 12/12, Val 2/3, Spa 3/3, Suzuka 0/3, Monaco 0/3 → 17/24 (71%)
Interlagos: 102s.

## Metas (critério do usuário)
- **A. Professor ≥95% em todas as pistas: ✓** (16/16 = 100%, Fase 1)
- **B. Aluno ≥9/10 em treino: ✓** (12/12 = 100% — EXCEDE)
- **B'. Aluno ≥7/10 em teste: ✘** (3/9 = 33% — Spa passa, Monaco/Suzuka não)
- **C. Tempo ≥20% menor que 114s: ✘** (104s = −8.8%; iter8=102s = −10.5%)

## Análise
1. O DAgger resolveu o problema da frenagem sustentada que 8000+ iterações
   de PPO não resolveram. Causa: o professor v2 com v_plan físico produz
   rótulos CORRETOS em estados de alta velocidade (PPO não conseguia
   explorá-los por saturação tanh).
2. Spa/Catalunya zero-shot 3/3 a 114s = GENERALIZAÇÃO REAL validada. A obs
   'edge' (raios) provavelmente contribuiu (zero-shot Suzuka 42% na v8-edge
   vs 24% na legacy).
3. Monaco/Suzuka falham: hairpins R=8m (Monaco) e esses de direção trocando
   (Suzuka) estão fora da distribuição das 4 pistas de treino. Solução
   futura: pistas procedurais ou mais pistas FastF1 no pool.
4. O checkpoint iter10 (β=0) é o melhor geral; iter8 é melhor em
   Interlagos (102s). A seleção por val_laps+val_loss escolheu iter8;
   iter10 é melhor no critério do usuário (mais voltas totais).

## Próximos passos
1. Mais pistas no pool de treino (Bahrain, Cidade do México, etc.) para
   cobrir hairpins e esses.
2. Aumento: pistas procedurais (splines fechadas aleatórias).
3. PPO residual do aluno DAgger (Fase 5) para reduzir o tempo além do
   professor.
4. Corrida de 10 carros com o aluno DAgger (Fase 6) — objetivo D.

---

# Monaco: confiabilidade do professor v2 — análise completa

## Resultado: 20/20 voltas (100%) — Meta de CONCLUSÃO atingida

| Critério | Meta | Resultado | Status |
|---|---|---|---|
| Voltas válidas | ≥19/20 | **20/20** [Wilson 0,84-1,00] | ✓ |
| lat_max | ≤5,5m | **7,0m** mediana | ✗ |
| v_min (durante volta) | ≥3 m/s | **2,3 m/s** mediana | ✗ |

## Diagnóstico físico (testes controlados)

1. **Cap de velocidade no ápice** (V_HAIRPIN_CAP=4.5): lat PIOROU (7,25m).
2. **Zona de aproximação** (10m a 3 m/s²): lat igual (6,97m).
3. **Teste DEFINITIVO**: carro no ápice, v=4 m/s, heading alinhado,
   esterço MÁXIMO → **lat_max = 6,98m**. O carro faz R_path=4,2m (MAIS
   apertado que o centro de 6,4m!) mas AINDA desliza lateralmente para
   fora. O vetor velocidade desalinha do heading (slip) e o carro
   atravessa a pista.
   
   **Conclusão**: a física do simulador (fase 4a+4b combinadas) não
   consegue manter o vetor velocidade alinhado em curvatura extrema
   (kappa>0,15), mesmo a 4 m/s com esterço máximo. NÃO é limitação do
   pure pursuit — é característica da interação das fases na física.

## O que FOI corrigido (e valida as outras pistas)

| Fix | Efeito |
|---|---|
| Círculo de atrito na passada backward | Freia antes em zonas de curva+frenagem |
| sf adaptativo (kappa>0,10 decai) | Mais conservador em hairpins |
| Zona de aproximação (10m) | Entra alinhado (reduz mas não elimina o drift) |

## Regressão: TODAS as 8 pistas 5/5 (100%)

| Pista | Voltas | Tempo | lat_max |
|---|---|---|---|
| Interlagos | 5/5 | 109s | 1,0m |
| Monza | 5/5 | 118s | 6,4m |
| Hungaroring | 5/5 | 119s | 4,0m |
| Silverstone | 5/5 | 138s | 3,6m |
| Zandvoort | 5/5 | 117s | 4,0m |
| Monaco | **5/5** | 104s | **7,0m** |
| Suzuka | 5/5 | 133s | 1,9m |
| Spa | 5/5 | 120s | 3,7m |

128/128 testes passando.

## Limitação honesta

lat_max ≤ 5,5m em Monaco NÃO é atingível com a física atual. O hairpin
R=6,4m (dos 15 marcadores FastF1) está no limite do modelo de curva
cinemática. O carro completa a volta (20/20) mas usa ~1m da área de
escape na saída — comportamento realista de Monaco, mas não ideal.

**Possíveis caminhos futuros**:
1. Geometria por telemetria (R=7m em vez de 6,4m) — pode reduzir o drift
2. Ajustar a interação 4a/4b na physics.py (versionado, com medição)
3. Aceitar o critério de conclusão (20/20) como suficiente para o DAgger

---

# Pool de treino ampliado — fronteira física, FastF1 novas, procedurais

## Parte 0 — Fronteira física R_min(v)
Calibrada em plano livre (esterço fixo, velocidade constante, ≥2 voltas).
Critério PRÁTICO: LIMPO = |R_eff−R_alvo| ≤ 2m e misalign < 12°.

| grip | v=4 | v=6 | v=8 | v=10 | v=13 | v=16 |
|---|---|---|---|---|---|---|
| real | **4m** | **4m** | **4m** | **6m** | **13m** | — |
| treino | **4m** | **4m** | **4m** | **4m** | **8m** | — |

Salva em `physics_frontier.json`. O gerador LÊ este arquivo (nunca hardcode).
Verificação: Monaco hairpin R=6m a v=4-6 → LIMPO na física pura (o lat_max=7m
vem do pure pursuit, não da física — documentado na fase anterior).

## Parte 1 — FastF1 adicionais (só TREINO)
3 pistas novas validadas com professor 5/5:

| pista | R_ápice | esses/100m | professor | tempo |
|---|---|---|---|---|
| Montreal | 8,5m | 0,1 | 5/5 | 108s |
| Bahrain | 12,9m | 0,1 | 5/5 | 132s |
| Mexico | 14,5m | 0,3 | 5/5 | 111s |

## Parte 2 — Gerador procedural (`procedural_track.py`)
Pipeline: elipse base → U-points de hairpin (entrada/ápice/saída em
Cartesiano) → esses (alternância perpendicular) → Catmull-Rom centrípeto
(reutiliza track.py) → subdivisão ≤4m → gate de kappa.

**BUG ENCONTRADO E CORRIGIDO**: a média móvel de 20m no kappa INVERTIA O
SINAL de hairpins procedurais (k_avg=−0,013 [DIREITA] onde k_raw=+0,042
[ESQUERDA]). O professor esterçava para o lado errado e saia — 0/20 voltas.
**Fix**: suavização HÍBRIDA — usa a MÉDIA quando os sinais concordam
(pistas reais: comportamento idêntico ao anterior) e o PICO quando
discordam OU o pico é >3× a média (hairpin procedural: ratio 3-7).

### Pool procedural validado (professor ≥19/20):
| tag | seed | features | professor | tempo |
|---|---|---|---|---|
| hairpin_A | 101 | 2 hairpins | **10/10** | 81s |
| hairpin_B | 103 | 2 hairpins | **10/10** | 85s |
| hairpin_C | 107 | 3 hairpins | **10/10** | 100s |
| esse_A | 201 | 3 esses | **10/10** | 53s |
| esse_B | 203 | 4 esses | **10/10** | 55s |
| mista_A | 301 | 2 hp + 2 esses | **10/10** | 81s |

### Regressão em pistas REAIS (com o híbrido):
| pista | antes | depois | delta |
|---|---|---|---|
| Interlagos | 109s | 112s | +2,8% |
| Montreal | 108s | 115s | +6,5% |
| Monaco | 104s | 111s | +6,7% |
| Suzuka | 133s | 138s | +3,8% |

Todas 5/5 — custo do híbrido: 3-7% de tempo. Aceitável.

## Parte 3 — Sanidade
6/6 (3 procedurais + 3 FastF1 novas): professor completa, obs edge finita.

## Pool FINAL para DAgger (13 pistas de treino):
- FastF1 reais (7): interlagos, Monza, Hungaroring, Silverstone, Montreal, Bahrain, Mexico
- Procedurais (6): hairpin_A(101), hairpin_B(103), hairpin_C(107), esse_A(201), esse_B(203), mista_A(301)
- VALIDAÇÃO: Zandvoort (intocada)
- TESTE (nunca no treino): Monaco, Suzuka, Spa

142/142 testes (14 novos: test_procedural_track.py).

---

# DAgger v10 — pool ampliado (13 pistas) + kappa wrap fix

## PRÉ-CHECK 0: BUG DO KAPPA NA OBSERVAÇÃO (crítico, corrigido)
`_kappa_signed` usava diferença central h(s+10)−h(s−10) numa janela de 20m.
Num hairpin de ~180° (Monaco s=1016), a diferença cruza EXATAMENTE a fronteira
do wrap ±π: s=1015 dá +0,157; s=1016 dá **−0,156**! O aluno via curva à DIREITA
numa curva à ESQUERDA. Correção: acumular diferenças pequenas (~2m cada, sempre
<90°) ao longo da janela — a soma preserva o sinal. 5 testes novos
(test_kappa_sign.py), Monaco agora +0,156 ✓.

## PRÉ-CHECK 1: procedurais no DAgger
`_resolve("procedural:101")` → generate_track(seed=101, n_hairpins=2, n_esses=0).
Pool de 13 carrega com grip_random 0.70-1.0, obs edge 34d ✓.

## GATE β=1.0: professor 39/39 (100%) nas 13 pistas
Professor com grip_random 0.70-1.0: 3/3 em TODAS as 13 (incluindo procedurais).

## DAgger v10 (10 iters, 13 pistas, 270k amostras)
- β 1.0→0.0, 2 eps/pista/iter, 50 epochs BC/iter
- Seleção: (voltas VAL, tempo mediano, val_loss) — corrigida do viés da v9
- MELHOR: iter 10 (β=0, VAL 3/3 a 113,8s)

## AVALIAÇÃO FINAL (determinístico, grip real, sem respawn, 3 eps/pista)

| conjunto | pista | voltas | tempo |
|---|---|---|---|
| TREINO | interlagos | **3/3** | 109s |
| TREINO | Monza | **3/3** | 120s |
| TREINO | Hungaroring | **3/3** | 118s |
| TREINO | Silverstone | **3/3** | 141s |
| TREINO | Montreal | **3/3** | 108s |
| TREINO | Bahrain | **3/3** | 132s |
| TREINO | Mexico | **3/3** | 110s |
| TREINO | procedural:101 | **3/3** | 76s |
| TREINO | procedural:103 | **3/3** | 82s |
| TREINO | procedural:107 | **3/3** | 92s |
| TREINO | procedural:201 | **3/3** | 52s |
| TREINO | procedural:203 | **3/3** | 51s |
| TREINO | procedural:301 | **3/3** | 77s |
| VALIDAÇÃO | Zandvoort | **3/3** | 116s |
| TESTE | Monaco | 0/3 | 41% prog |
| **TESTE** | **Suzuka** | **3/3** | **131s** |
| TESTE | Spa | **3/3** | 121s |
| **TOTAL** | | **48/51 (94%)** | |

## COMPARAÇÃO v9 → v10
| métrica | v9 | v10 | delta |
|---|---|---|---|
| treino | 12/12 (4 pistas) | **39/39 (13 pistas)** | +3× escopo |
| VAL | 3/3 | 3/3 | = |
| **Suzuka zero-shot** | **0/3 (58%)** | **3/3 (100%)** | **RESOLVIDO** |
| Spa zero-shot | 3/3 | 3/3 | = |
| Monaco zero-shot | 0/3 | 0/3 | persiste |
| **total** | 18/24 (75%) | **48/51 (94%)** | **+19pp** |

## Monaco: mesma falha, causa documentada
v10 morre em s≈1022 (MESMO PONTO da v9: s≈1024). A intervenção (pool ampliado)
NÃO moveu o ponto de falha em Monaco. Causa: hairpin R=6.4m está no limite
físico (o carro desliza a >4 m/s mesmo com esterço máximo — ver fase Monaco).
O professor completa 20/20 mas usa lat=7m (escape road). O aluno não aprendeu
esta manobra específica. **Solução futura**: DAgger com demonstrações ESPECÍFICAS
do professor em Monaco (estados do hairpin com rótulos corretos) — mas isso
exporia dados de TESTE ao treino, violando o protocolo.

## Metas
- **B (treino ≥36/39): ✓ 39/39 (100%) — EXCEDE**
- **VAL 3/3: ✓**
- **B' (teste ≥7/9): ✘ 6/9** (Monaco 0/3, Suzuka 3/3, Spa 3/3)

147/147 testes.

---

# Meta D — Corrida de 10 carros com v10 (edge, 34d)

## PASSO 1: NeuralRaceController adaptado para edge
- `--obs-mode edge|legacy` no run_race_10_cars.py e race_diagnostic.py
- `_cast_rays_batch`: 11 raios LiDAR vetorializados para 10 carros/tick
- **Validação de shape com ERRO EXPLÍCITO**: "INCOMPATÍVEL: o ator espera 48
  entradas mas obs_mode='legacy' produz 37" — não crash numérico
- `_kappa_signed` do race controller: MESMO BUG DE WRAP corrigido (acumulação
  de diferenças pequenas, igual ao f1_env)
- NPZ exportado: primeira camada (48, 256) ✓
- 147/147 testes

## PASSO 3: Corrida 600s (10 caros, Interlagos, headless)

| métrica | v5c (baseline) | **v10** | delta |
|---|---|---|---|
| hesitações ≥0.3s | 21 | **1** | **−95%** |
| tempo total parado | 18s | **2s** | **−89%** |
| fora do asfalto | 4.6% | **0.8%** | **−3.8pp** |
| carros ≥1 volta | ? | **10/10 (2 voltas cada)** | ✓ |
| tempo de volta mediano | ? | **88s** | — |
| autoridade policy | ? | **66%** | — |
| autoridade governor | ? | 27% | — |
| autoridade rejoin/recovery | ? | 0.9% | — |

**TODOS OS CRITÉRIOS DE ACEITE PASSAM:**
- ✓ Zero paradas ≥3s (máx = 1.6s, RUS em s=3000)
- ✓ 10/10 carros completam ≥1 volta (todos fazem 2)
- ✓ Fora do asfalto 0.8% ≤ 4.6% (baseline)

## Análise do tempo de volta (88s race vs 109s eval)
O tempo de 88s na corrida é ~19% mais rápido que o eval determinístico (109s).
Causa: o GOVERNOR (27% da autoridade) assiste com frenagem/coronagem em
velocidades onde a política raw seria mais conservadora. A avaliação
determinística usa a política raw (sem assistência) — por isso é mais lenta.
Isto é BY DESIGN: a corrida tem camadas de assistência; o eval mede autonomia.

## Limitações
- Monza race (EXTRA) não executada (tempo de sessão)
- Contatos carro-carro: 1333 amostras (empurrões em s=2800-3000, 3 carros
  afetados, todos recuperados via rejoin)
- O aluno não vê adversários (obs sem oponentes): contatos são resolvidos
  pela física + cap blocked, como esperado

---

# Meta C — ritmo: PASSO 0 (verificação) + Caminho B (sf=0.95, FALHOU)

## PASSO 0.1: 88s = ARTIFATO
As "voltas de 88s" eram a MEDIANA MISTA de voltas parciais (grid→linha,
26-41s) e reais (136-138s). Voltas REAIS na corrida: **137s** (com tráfego
de 10 carros). O raw eval é 109s. O professor é 112s.

| o que | tempo |
|---|---|
| "88s" (artefato) | mediana de [26-41s parciais + 136-138s reais] |
| corrida real (tráfego) | 137s |
| raw eval (autonomia) | 109s |
| professor v2 (sf=0.80) | 112s |

## PASSO 0.2: headroom medido
1. **Governor**: concentrado em frenagens (s=700-1400, 3900-4000; share 60-89%)
2. **sf sweep (Interlagos, professor)**:

| sf | v_plan teórico | professor | 13 pistas |
|---|---|---|---|
| 0.80 | 96.4s | 111s | 26/26 ✓ |
| 0.90 | 90.1s | 105s | **26/26 ✓** |
| 0.95 | 87.5s | 102s | **26/26 ✓** |
| 1.00 | 85.0s | 100s | (não medido) |

## PASSO 0.3: decisão
Governor em frenagens → **CAMINHO B** (relabel sf=0.90/0.95).
88s era artefato → CAMINHO C descartado.

## CAMINHO B executado (sf=0.95, 5 iters, partindo do v10): FALHOU

### Ganho de velocidade (real):
| modelo | Interlagos | delta |
|---|---|---|
| v10 (sf=0.80) | 109s 3/3 | — |
| v11 (sf=0.95) | **99s** 2/3 | **−10s** |

### Custo de confiabilidade (inaceitável):
| métrica | v10 | v11 | regressão |
|---|---|---|---|
| treino | 39/39 | **33/39** | Bahrain 0/3, Mexico 0/3, Interlagos 2/3 |
| VAL | 3/3 | 3/3 104s | = |
| **Suzuka** | **3/3** | **0/3** | **PERDEU** |
| Spa | 3/3 | 1/3 | **PERDEU** |
| **total** | **48/51 (94%)** | **36/51 (71%)** | **−12pp** |

### Veredito: v11 DESCARTADO
O sf=0.95 é o LIMITE do professor — o aluno que o imita herda margens
praticamente zero. Qualquer erro em Bahrain/Mexico/Suzuka/Spa resultou em
saída de pista. O critério "REGRESSÃO ZERO em treino/VAL/Suzuka/Spa" FALHA.

## Escada de sucesso (onde paramos):
| degrau | resultado | status |
|---|---|---|
| <105s | v11: 99s | ✓ mas com regressão inaceitável |
| <100s | v11: 99s | ✓ mas DESCARTADO |
| 91.2s (Meta C) | **não atingido** | ✗ |

**Melhor resultado VÁLIDO: v10 a 109s (48/51, 94%)**

## O teto realista (o que o PASSO 0 diz):
- Professor sf=0.80: 112s | Professor sf=0.95: 102s | Professor sf=1.00: 100s
- Teórico (v_plan sf=1.00): 85s (o pure pursuit perde 15s/volta)
- O ALUNO imitando o professor não passa do professor (por construção)
- Para chegar a 91.2s seria necessário: PPO residual (CAMINHO A) ou um
  controlador melhor que pure pursuit (fora de escopo)
- **O gap 109→91.2s (18%) exige RL além da imitação — o Caminho A é o
  único caminho não testado, mas o histórico do projeto mostra que o PPO
  não consegue explorar frenagem sustentada (8000+ iters sem sucesso)**

## Próximos passos honestos:
1. PPO residual ancorado no v10 (Caminho A): risco alto, histórico desfavorável
2. Melhor pure pursuit → racing line (mudança estrutural no professor)
3. Aceitar 109s como o resultado com 94% de confiabilidade

---

# Meta C — FASE 0-2: recompensa física, sonda sf=0.90, PPO residual (FALHOU)

## FASE 0: _v_allow_at com downforce — CORRIGIDO
- A_LAT_MAX=14 fixo substituído por: v² = mu_s·g/(kappa − mu_s·c/m)
  onde mu_s = sf_reward · mu · grip_do_episódio
- 5 testes novos (test_reward_vallow.py): downforce aumenta v_allow ✓,
  monotonicidade em grip ✓, calibração v_allow(sf_r=1.0) ≥ v_plan(sf=0.80) ✓,
  sf_r=0.80 ≈ legado ✓, obs inalterada ✓
- 152/152 testes (147 + 5 novos)

## FASE 1: sonda sf=0.90 (v11b)
| modelo | Interlagos | Zandvoort | Suzuka |
|---|---|---|---|
| v10 (sf=0.80) | 109s 3/3 | 116s | 3/3 |
| v11b (sf=0.90) | **108s 3/3** | 111s 3/3 | **2/3** |
| v11 (sf=0.95) | 99s 2/3 | 102s | 0/3 (DESCARTADO) |

**Conclusão da sonda**: o aluno absorve ~1s por passo de 0.05 em sf. O joelho
está ENTRE 0.90 e 0.95 (v11b mantém quase tudo; v11 desaba). O ganho por
imitação é marginal — 108s é o teto do DAgger.

## FASE 2: PPO residual (v12) — FALHOU
- Init: v11b (sf=0.90 DAgger), sf_reward=0.90, 250 iters, 5 pistas
- Treino: lap%=6.5 (best iter 139) — APARENTEMENTE bom
- **Determinístico: 0/3 em Interlagos** — MESMO PADRÃO de todos os PPOs

| modelo | treino lap% | determinístico |
|---|---|---|
| v12 PPO | 6.5% | **0/3** |
| v6b PPO (histórico) | 5.0% | 0/10 |
| v6d PPO (histórico) | 4.5% | 0/5 |

**O PPO encontra voltas estocasticamente no treino (random starts, respawn,
grip variável) mas a política determinística (tanh da média) não mantém
controle por uma volta completa. Este é o TERCEIRO PPO que falha do mesmo
modo — o padrão é estrutural, não de hiperparâmetros.**

## CRITÉRIO DE PARADA ATINGIDO
"melhor checkpoint válido > 103s → PARE"

## ESCADA FINAL (onde paramos):
| degrau | resultado | válido? |
|---|---|---|
| 109s | v10 (sf=0.80) | ✓ 48/51 94% |
| 108s | v11b (sf=0.90) | ✓ (Suzuka 2/3 — ver regressão) |
| 99s | v11 (sf=0.95) | ✗ 36/51 71% DESCARTADO |
| 91.2s | Meta C | **✗ NÃO ATINGIDO** |

**Melhor resultado VÁLIDO: v10 a 109s (48/51, 94%)**

## O QUE O PASSO 0 DIZ SOBRE O TETO REALISTA:
| nível | tempo | método |
|---|---|---|
| teórico v_plan sf=1.0 | 85s | integração (nunca atingido) |
| professor sf=1.0 | 100s | pure pursuit perde 15s/volta |
| professor sf=0.80 | 112s | segurança operacional |
| **v10 (aluno)** | **109s** | **DAgger — 3% melhor que o professor** |
| Meta C | 91.2s | **exige superar o pure pursuit no sf máximo** |

Para 91.2s seria necessário um controlador MELHOR que o pure pursuit
(racing line, MPC) — possível mas é uma mudança estrutural, não um ajuste.
O PPO não resolve (3 tentativas, 3 falhas do mesmo modo).

## DECISÃO APRESENTADA AO USUÁRIO:
(a) aceitar 108-109s com 94% de confiabilidade (v10/v11b)
(b) investir em racing line / MPC no professor (mudança estrutural, novo projeto)
(c) renegociar a meta com os dados: o teto teórico é 85s mas o pure pursuit
    atinge apenas 100s; o aluno DAgger herda o teto do professor

---

# Meta C — VEREDICTO FINAL (3 testes, zero treino novo)

## TESTE 1: inferência estocástica — ARQUITETURA FALHOU
| sigma | v10 | v11b | v12 |
|---|---|---|---|
| 0.00 | 3/3 | 3/3 | **0/3** |
| 0.05 | — | — | **0/3** |
| 0.10 | 3/3 | 3/3 | **0/3** |
| 0.20 | — | — | **0/3** |

O v12 falha em TODOS os sigmas: o PPO DEGRADOU a política (v11b 3/3 → v12 0/3).
Não é modo de inferência — é a otimização PPO que destrói o comportamento do
actor DAgger. Greedy-V descartado (Teste 3 não aplicável).

## TESTE 2: respawn no treino PPO — CONFIRMADO CONTAMINADO
- PPO: `allow_respawn=True` por default → lap% de treino media SOBREVIVÊNCIA
  COM RESPAWN, não autonomia. Todos os PPOs v5-v12 têm lap% inflado.
- DAgger: `allow_respawn=False` → dados limpos, teacher completa sem respawn.
- **Isto explica a discrepância treino↔eval de TODOS os PPOs**: o PPO otimiza
  "sobreviver com safety net", o DAgger otimiza "completar sem".

## DECISÃO FINAL
| protocolo | v10 | v11b | v12 | melhor VÁLIDO |
|---|---|---|---|---|
| tanh(mu) | 109s 48/51 | 108s ~47/51 | 0/3 | **109s** |
| sigma=0.10 | 3/3 ✓ | 3/3 ✓ | 0/3 | — |
| greedy_v | n/a | n/a | n/a | — |

## RECOMENDAÇÃO DE PRODUTO: DUAL-PROFILE
- **v10 = race setup**: 48/51 (94%), 109s — máxima confiabilidade
- **v11b = quali setup**: 108s, Suzuka 2/3 — pace máximo aceitável

## EXTRA: corrida Monza 600s com v10 (validação multi-pista)
| métrica | Interlagos | Monza |
|---|---|---|
| hesitações ≥0.3s | 1 | 13 |
| fora do asfalto | 0.8% | 0.5% |
| carros ≥1 volta | 10/10 | **10/10** |
| tempo real mediano | 137s | **140s** |
| autoridade policy | 66% | 72% |

Monza 10/10 carros completam ✓. A camada de corrida funciona multi-pista.

---

# Meta C — VEREDICTO DEFINITIVO: v13 PPO no-respawn (TETO)

## O experimento que faltava
PPO com allow_respawn=False (sinal honesto), init do v11b (3/3 a 108s),
sf_reward=0.90 (física-alinhada), 400 iters, steps_per_roll=1024.

## Curva lap% honesta vs fabricada (a evidência definitiva)
| modelo | respawn | lap% treino | eval determinístico |
|---|---|---|---|
| v12 PPO | **True** | 6.5% (FABRICADO) | 0/3 |
| **v13 PPO** | **False** | **2.0% (HONESTO)** | **2/3 a 125s** |
| v11b DAgger | False | — | 3/3 a 108s |

O lap% honesto do v13 (2.0%) é 3× MENOR que o fabricado do v12 (6.5%) —
confirmando que o respawn inflava o sinal em ~3×. Mas mesmo com o sinal
correto, o PPO DEGRADOU a política: 108s→125s (+17s) e 3/3→2/3.

## Resultado: TETO
"≥108s ou lap% degradou → veredicto FINAL"

**v13: 125s (PIOR que 108s) e 2/3 (PIOR que 3/3). TETO CONFIRMADO.**

## VEREDICTO FINAL DA META C (base completa — 4 PPOs testados)
| PPO | respawn | resultado |
|---|---|---|
| v6/v6b/v6d (histórico) | True | 0/10 determinístico |
| v12 residual | True | 0/3 determinístico |
| **v13 no-respawn** | **False** | **2/3 a 125s (degradou)** |

**O PPO não melhora a política DAgger em NENHUM protocolo.** Com respawn:
sinal fabricado, otimização errada. Sem respawn: sinal honesto, mas a
otimização ainda degrada (o gradiente empurra para longe do comportamento
limpo do DAgger). O teto do stack é o DAgger: **~108s**.

## O teto realista (resumo final):
- v_plan teórico sf=1.0: **85s** (nunca atingido)
- professor pure-pursuit sf=1.0: **100s** (path-following perde 15s/volta)
- **aluno DAgger (v11b)**: **108s** (herda o teto do professor sf=0.90)
- Meta C 91.2s: exigiria **racing line ou MPC** no professor (fora do
  escopo do PPO/DAgger — é uma mudança de controlador, não de otimização)
