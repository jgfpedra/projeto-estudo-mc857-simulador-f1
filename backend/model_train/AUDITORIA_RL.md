> [PROVENIÊNCIA — LARGADA-4, 2026-10-19] Restaurado VERBATIM do histórico
> (git show 439f402:backend/model_train/AUDITORIA_RL.md — última versão do
> arquivo; criado em 9099235, atualizado em 3d4f0e9/439f402; perdido no squash
> da PÓS-CICLO-1). Este bloco é o ÚNICO acréscimo pós-histórico; todo o resto
> é conteúdo histórico intocado. Referência: worklog LARGADA-4.
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


---

## R7b→R13 — CADEIA CAUSAL ÚNICA FECHADA (out/2026, ciclo v15 completo)

Diagnóstico por fases, cada uma fechando um elo com instrumento canônico
(frozen v2 SF729, clima semeado, variância semeada, sequencial-puro, contato
solver-side v3):

1. **R7b**: física lateral SÃ (scripted: círculo estável até v_allow;
   understeer 1,45× calibrado). Saídas = comando da política ~24× a
   necessidade cinemática (slip 16,8° mediano; a_lat 3,9-5 vs 10,4 m/s²).
   B3.1 histórico rotulado pré-canônico (commit FASE-4 não roda).
2. **R8**: cap κ-cinemático REFUTADO no piloto (clipa 88-92% dos ticks
   normais; nenhum k_comp viável).
3. **R9**: slip-cap MORTO (slip alto = regime NORMAL, 91-98% dos ticks);
   rate-limiter MORTO (offset sustentado, 0,2% yank). Família camada
   ENCERRADA.
4. **R11/R12**: paradas = 100% RECUP-OFF (subproduto de excursões);
   hesitações = 57% REJOIN-DIP + 25% CORNER-CRAWL; retreino BC offline
   16d (r12b) VERMELHO no piloto (skew: tráfego vivo nunca visto) —
   research-negativo, trilha encerrada.
5. **R13 (gate out-of-sample, 20 corridas seeds 10-19)**: composite FAIL
   (3/10; adverso 0/4) por CONTATO no retorno (28-44% das amostras com
   carro fora) e hesitação REJOIN-DIP — o critério de pista (fora)
   passou em TODAS. Vantagem de segurança consistente (1,5-3,5× menos
   contatos em 10/10). Veredito R10 PERMANENTE.

**Conclusão**: uma única frente — excursões da política → contatos no
retorno → hesitação pós-rejoin → paradas. Alavancas futuras: percepção de
tráfego no rejoin; weave/slide com tráfego VIVO (dados agora logados no
CSV v3.3). Instrumentos deixados prontos: contato solver-side, clima
semeado, variância semeada, protocolo sequencial, gate mecânico por
clima com re-ancoragem por quantis.

## LOC-XY-1 — PARE no gate 3 (2026-10-23)

- Prereg `5fe4ff8` e baseline bruto 20F/349P/3S congelados antes do código.
  Referência blind Interlagos v3.3: 49 colunas, SHA-256
  `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`.
- A implementação `4d22d65` acrescenta `body_x,body_y,ns_raw` ao CSV; foram
  adicionados exatamente três testes, todos aprovados na execução da suíte.
  O teste v3.3 do kill-switch reproduziu o fixture pré-mudança byte a byte.
- Suíte pós-código: **21F/351P/3S**. As 20 falhas do baseline permanecem; a
  falha adicional não-canônica foi
  `test_mixed_composite_wiring.py::test_t_regression_v10_cego_bit_identico`,
  que compara a saída inteira com o header v3.3 de 49 colunas e falha com a
  expansão de schema.
- Gate 3 acionou o **PARE** previsto. O smoke formal do gate 4 não foi
  iniciado; os selftests golden não foram executados após o PARE. Cada suíte
  (baseline e pós-código) executou o subprocesso de 1.200 ticks incluído no
  teste de regressão; os CSV/eventos temporários foram removidos após a falha.
  A instrumentação não foi validada em saída completa de corrida de 6.000
  ticks. O log bruto pós-suíte tem SHA-256
  `969628421db6fb3a57e038ef212ea97c017c325da3ae0d5290f24696986fbf6a`.
- `ns_dist` foi omitido para manter exatamente as três colunas especificadas.
  Próxima ação requer decisão do dono sobre a expectativa do teste legado;
  nenhum teste existente foi alterado e nenhuma execução ocorreu após o gate 3.

Ver `experiments/loc-xy-1/relatorio.md` e `experiments/loc-xy-1/3_post_pytest.log`.

## ANEXO LOC-XY-1 — ERRATA E-XY-2 e retomada interrompida (2026-10-23)

**E-XY-2 (aditiva, ratificada pelo dono).** O contrato de
`test_t_regression_v10_cego_bit_identico` passa a ser: executar no caminho
default v3.4 e comparar, por linha, os campos `split(',')[:49]` contra o
fixture pré-wiring v3.3, sem biblioteca CSV. A projeção inclui o header
(campos 0–48, iguais ao header v3.3). Nome/path do teste permanecem iguais;
seu docstring ganha a linha: “v3.4: 49 legadas proj. bit-idênticas ao
pré-wiring; restauração v3.3 provada pelo teste (c) e pelo smoke do gate 4”.
A restauração de arquivo v3.3 completo continua disponível via
`RACE_DIAG_NO_XY=1`.

A edição permitida foi aplicada somente ao corpo desse teste. Na suíte
completa seguinte, o teste legado corrigido e os três testes LOC-XY passaram,
mas a contagem resultou em **21F/351P/3S**, divergente do ratificado
**20F/352P/3S**. As 20 falhas canônicas do baseline permaneceram e surgiu
`test_state_files.py::test_state_files_doc_integrity`; o traceback identifica
uma linha histórica da cadeia `> (anterior:)` do PROJECT_STATE sem o sufixo
de referência esperado. O gate 3 acionou PARE. Nenhum smoke formal de 6.000
ticks nem selftest golden pós-código foi iniciado; pools e pistas frozen
permanecem intocados.

Log bruto versionado: `experiments/loc-xy-1/4_post_fix_pytest.log`, SHA-256
`37527575cf3b889d65819f920e6fa0216f00817549674c9fe07e053371f1d675`. O
relatório completo conserva o PARE anterior e registra a retomada E-XY-2.

## ANEXO LOC-XY-1 — fechamento E-XY-3 (2026-10-23)

E-XY-3 fez a correção doc-only da linha 6 em `PROJECT_STATE.md` e foi
commitada em `29cf2a2`. A suíte completa então passou: **20F/352P/3S**, com
exatamente a mesma lista de 20 falhas do baseline. Log
`experiments/loc-xy-1/5_post_chain_fix_pytest.log`, SHA-256
`7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185`.

Os dois smokes formais de 6000 ticks, seed 0, Interlagos blind foram seriais.
Smoke A com `RACE_DIAG_NO_XY=1`: CSV completo byte-idêntico à âncora v3.3,
SHA-256 `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`.
Smoke B com o kill-switch OFF: as 49 colunas legadas são byte-idênticas por
projeção dumb (`split(',')[:49]`) sobre header e linhas de dados; hash da
projeção `ad145f45af4152e5f8097042793a2291b4cffe916ad8c4dd7bd3137a378d00c4`.
O CSV completo v3.4 tem SHA-256
`fe5027dcf83fd81bb062443b93e0a0b7b5b8e8f280c916a525c489bcb8003e35`, 52
colunas, 30.000 linhas e três campos finais `body_x,body_y,ns_raw`; X/Y são
floats finitos preenchidos e ns_raw inteiro de 0 a 1130 em todas as linhas.
O sidecar `_events.csv` dos dois smokes é byte-idêntico entre eles e à âncora
(SHA-256 `11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9`).

Selftests golden pós-código: `fail_forensics_verdict.py --selftest` PASS
(SHA-256 `2112e34309a53dc80ab7771f867560d543d1f4fa31eb9c3cba87f27c4352e100`)
e `saidas_verdict.py --selftest` PASS (SHA-256
`430bddf5170d96acb1542992c83b9004712edab989dbaeb99c68eec09da041e3`).
Orçamento: 2/2 smokes formais, zero corridas de medição, pools e pistas
frozen intocados. Para novas entradas de cabeçalho/cadeia, incluir `Ver
<path>` e fechar com `)` antes do próximo ciclo rebaixá-las a `(anterior:)`.
Relatório consolidado: `experiments/loc-xy-1/relatorio.md`.)

## PROJ-FIX-1 — PARE na reconciliação NIT-2 (Ver `backend/experiments/proj-fix-1/PARE.md`)

Prereg e classificador offline v1.0 foram congelados antes do único replay
R4 Composite Monaco (commit `a519081`; selftest sintético PASS). O alias
`--track Monaco` resolveu Monaco_v2, seed 0, writer v3.4 default.

g1 PASS: projeção byte a byte das 49 colunas, incluindo header, igual à âncora
R4. g2 PASS: 71 campos por linha, XY finitos e `ns_raw` inteiro válido. A
saída tem 30.000 linhas; clima sem transições. A reconciliação histórica
falhou antes de produzir classes: o seletor preregistrado encontrou 0 eventos
NIT-2, contra 112 entradas ≥10 m e 45 ≥30 m esperadas. PARE obrigatório; o
script não foi editado depois desse resultado, nenhuma classe ou correção é
declarada. Retomada requer novo prereg para resolver o identificador de run
histórico e uma nova versão/selftest do instrumento.

Orçamento encerrado em 1/1 replay, zero medições e zero smokes. Runner,
controles, física, pools e pistas frozen intocados. CSV, sidecar, logs e hashes
estão preservados em `experiments/proj-fix-1/`.

## PROJ-FIX-2 — PARE em g4 (Ver `backend/experiments/proj-fix-1/PARE_PROJ_FIX_2.md`)

O prereg e o classificador v1.1 foram congelados antes da classificação no commit
`8222dff`; selftest sintético PASS. g0–g3 passaram, incluindo a projeção
byte-idêntica do replay e âncora e a seleção de 112 eventos NIT-2 ≥10 m / 45
≥30 m para `composite_monaco`. A classificação v1.1 parou no evento
`('ALO', 2130, 2132)`, sem classe XY/ns_raw. PARE obrigatório: não foi produzido
mapa 1:1 nem resumo de classes/p95, e não há conclusão C1/C2/C3 ou proposta de
correção. A suíte ficou na referência 20F/352P/3S, sem reexecução; zero corridas
de medição e zero smokes.

## PROJ-FIX-3 — PARE em g0 (Ver `backend/experiments/proj-fix-1/PARE_PROJ_FIX_3.md`)

O prereg e o classificador v1.2 foram congelados no commit `2330e9f`, após o
diagnóstico limitado à chave ALO e antes de qualquer agregado por classe. O
selftest sintético passou. g0 encontrou divergência no hash do relatório PARE
v2: prereg `a3e7dd18…`, arquivo preservado `e287e5bd…`. PARE obrigatório; g1–g4
não foram executados, nenhuma classificação C1–C5 foi produzida, e a suíte
permanece na referência 20F/352P/3S sem reexecução. Sem novas corridas ou smokes.

## ANEXO PROJ-FIX-4 — fechamento offline C1–C5 (2026-10-23) (Ver `backend/experiments/proj-fix-1/EXECUCAO_PROJ_FIX_4.md`)

O novo freeze P4 corrigiu a proveniência do PARE v2: o hash commitado é `e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c`; `a3e7…` foi transcrito de rascunho não commitado. P3 e o classificador v1.2 permaneceram intocados. Freeze P4 `574c5ea` (prereg SHA `0d9c8d31bfee6470d045cedea46c25264b3ba5d12d757116e75a300554219392`), manifest `75666b3` (SHA `5715be7b663394e29cc9b2a21a2baf554ccdb9281cc6d25439651d38e0b641ee`, 18/18 PASS), selftest v1.2 recheck PASS (SHA `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127`).

g0–g3 passaram. g1/g2: projeção legada SHA-256 `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`, 71 campos em 30.000 linhas, XY finitos e `ns_raw` inteiro `[0,833]`; g3: 112 eventos ≥10 m e 45 ≥30 m. A classificação v1.2 mapeou 112 chaves únicas: corte ≥10 m C1=0, C2=0, C3=46, C5=66; headline ≥30 m C1=0, C2=0, C3=45, C5=0. O mapa C5 1:1 está em `experiments/proj-fix-1/classificacao_v12/mapa_nit2_ge10.csv`. p95 de dXY/|d_ns_raw|: ≥10 m C3=1,8704425708164663 m/416,25 e C5=3,307436586085905 m/6,75; ≥30 m C3=1,8713291979009652 m/418,59999999999985. C4 inválido=0; ALO (2130,2132)=C5; entre C5, `offtrack=1` em 66/66 e `offtrack=0` em 0/66.

Nenhuma correção proposta; a escolha RECUP-1 vs projeção/gate retorna ao dono. Zero corridas, zero smokes e nenhuma reexecução da suíte (referência 20F/352P/3S); pools e pistas frozen intocados. Mapa SHA `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f`, resumo SHA `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05`, log g1/g2 SHA `617ef75e8cae3aa556e8e362c5e54a8099f6446b734c3bb836040a5839807a10`, verificação pós-classificação SHA `e62d487948772713bb76959d21713fa575bcdc7dd63bc9f0de20cc9c18036f30`. Hashes e logs brutos estão no relatório e em `experiments/proj-fix-1/`.

## PROJ-GATE-1 — PARE em g2/g4 (2026-10-23)

V-A foi congelada e implementada com `--proj-gate` default-OFF. g1 passou com
R1 byte-idêntica. g2 parou: R2 teve 173 pares ≥10 m e 108 ≥30 m. g3 passou nas
392 reentradas nearest-global. g4 parou com 60,15% fora, 397 episódios, 144
janelas presas e 28 hesitações; contatos e completude passaram. g5 não foi
executado por PARE obrigatório. Sem promoção, nova corrida ou reanálise de
classes; evidências e hashes estão em
`backend/experiments/proj-gate-1/PARE_PROJ_GATE_1.md`.

## PROJ-GATE-2 (2026-10-24) — autópsia report-only do PARE

- Freeze em dois commits: pré-registro `0a269ff`, script offline v1.0
  `a6d6775`; selftest sintético PASS, sem abrir dados de corrida. R1/R2 usam
  a mesma variância `grid,compound`. SHA-256 de disco e `git show` passou para
  CSVs/events, Monaco frozen, runner, diagnostic writer, classificador v1.2,
  audit anterior, PARE e DOSSIÊ; headers 71/17 colunas e cada braço com
  30.000 linhas, dez carros e ticks `0,2,...,5998` válidos.
- Localidade do proxy `ns_raw` contra o waypoint Euclidiano mais próximo:
  R1 OFF 0/12.945 amostras off-track erradas; R2 ON 5/18.045 (0,0277%), em
  cinco amostras isoladas, pico 1.403,663 m. Os outliers pertencem a ALO, PIA,
  HAM, PER e RUS. R2 teve erro em 6/392 janelas pós-reaquisição de 10 s e
  nenhum erro em duas amostras consecutivas. Spatial snap (`abs(lat)`) p95
  5,959 m nas 392 reentradas; distância alvo→descoberta não estimável.
- g2 reproduzido: R1 112/45 ≥10/≥30 m, normalizado 8,652/3,476 por mil
  amostras off-track; R2 173/108, normalizado 9,587/5,985. Taxonomia frozen
  v1.2 C1/C2/C3/C5: R1 ge10 `0/0/46/66`, ge30 `0/0/45/0`; R2 ge10
  `0/0/110/63`, ge30 `0/0/107/1`. P95s e mapeamento par-level constam em
  `backend/experiments/proj-gate-1/autopsia/4_g2_class_decomposition.json`.
- Scorecard: H1 **LOSING** porque a âncora e o alvo não são escritos e a
  atualização a cada tick lógico não pode ser reconstruída do writer 5 Hz;
  H2 não é observável diretamente pelo CSV, cujo `ns_raw` é proxy XY/global;
  H3 confirma que g2 mede discrepância arco/odômetro, não localidade do
  ponteiro interno. Hesitações R2 recriadas: 28, com cruzamento temporal por
  reentrada em `backend/experiments/proj-gate-1/autopsia/3_branch_geometry.json`.
  Encaminhamento único: arquivar esta bifurcação sem afirmar ausência de defeito.
- Nenhuma simulação/smoke, nenhuma suíte, nenhum ajuste de produção/pool/cache/
  pista e nenhuma promoção; flag permaneceu default-OFF. Hashes completos de
  inputs e outputs em `backend/experiments/proj-gate-1/autopsia/3_execution.log`;
  veredito em `backend/experiments/proj-gate-1/autopsia/5_veredito.md`.

## REJOIN-TEL-1 — PARE antes dos dados (2026-10-24)

- Preregistro de writer v3.5 aditivo congelado em `cc879b0`, com 9 campos
  (80 colunas); regra de encaminhamento em `f15bb7d`; correção de provenance
  pré-resultados em `8316af0`. Writer, 5 testes sintéticos e audit v1.0
  congelados em `b42f694`. A flag `--writer-v35` segue opt-in/default-OFF e
  `--proj-gate` permanece OFF.
- Suíte completa: 20F/363P/3S, mesmas 20 identidades da referência 20F/352P/3S;
  gate sem novas falhas PASS. Log em
  `backend/experiments/rejoin-tel-1/2_full_suite.log`.
- A única corrida R4 v3.5 foi interrompida com SIGINT (exit 130) antes de
  escrever CSV/events. PARE obrigatório pelo orçamento; g1–g3 e audit não
  foram avaliados. Sem estatísticas de rejoin, ângulo, hesitações, retorno ou
  encaminhamento RECUP-2/arquivar. Não repetir sem novo preregistro do dono.
- Instrumentação não muda escolha de ação por construção (alvo capturado em
  pass-through); contudo, sem o prefixo CSV não há prova de passividade neste
  replay. Nenhuma promoção ou alteração de env/física/observações/runner/pista/
  pools/caches ocorreu. Detalhes, comando, logs e hashes em
  `backend/experiments/rejoin-tel-1/PARE_REJOIN_TEL_1.md`.

## REJOIN-TEL-2 — replay v3.5 report-only (2026-10-24)

- Prereg de renovação congelado antes da única corrida (`9f9dc53`; SHA
  `7ff5863263b381ca244452ec03ea62c0cbfc0efdc4650827abd308023e023820`). Código
  frozen `b42f694`, sem diff de produção. Proveniência dupla PASS para R4
  âncora/CSV/events, Monaco, suíte 20F/363P/3S e audit v1.0.
- Uma corrida foreground, timeout 9 min, exit 0 em ~3m18; CSV 30.000 × 80,
  SHA `d950f7a60d47d125d829f5c4bf0302eadd9eb8ef7001cd17e690ba7950f6ac95`.
  Events SHA `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4`,
  idêntico ao sidecar v3.4. g1/g2/g3 PASS; g2 comparou 30.001 linhas com
  cabeçalho e prefixo legado `[:71]` idêntico. g4 usou a referência sem
  reexecução.
- Audit: 345 janelas, 344 reentradas e uma censurada; 302/344 (87,79%) com
  `|heading_err|>20°`; Pearson erro angular × segunda saída em 10 s = −0,3613
  (n=344); retorno p50/p95/máximo = 5,70/24,74/36,80 s; hesitações 12 total,
  11 até 10 s após reentrada (referências publicadas: 12 OFF/28 ON).
- Recomendação report-only ao dono: arquivar a hipótese angular da Etapa 2 e
  avançar Etapa 3; o critério combinado frozen para RECUP-2 falhou por
  correlação não positiva. Isso não demonstra ausência de defeito. Nenhum
  código, flag, suite, pool, cache ou pista foi promovido/alterado. Ver
  `backend/experiments/rejoin-tel-2/EXECUCAO_REJOIN_TEL_2.md` e hashes dos
  outputs em seu diretório `autopsia/`.

## TRAFEGO-MED-1B — Etapa 3 report-only (2026-10-24)

- Freeze assinado pelo dono no commit `8136d54ec45f9f49b38a5893a812928474109535`; prereg, manifest e script tiveram blobs byte-idênticos ao disco. O commit usou `git add -f` nos dois arquivos de `experiments/` por causa de `.gitignore:56`. Censo congelado: 47 Tier A + 63 Tier B; hash/schema e blob Git foram conferidos em A, com tamanho/linhas também revalidados em B. Uma análise offline exit 0 processou 52/65 séries; 13 foram excluídas antes de carregar métricas porque cada arquivo tinha um único `drv`.
- Matriz por corrida/fase/par/braço, agregados, segmentos, transferência e cobertura estão em `backend/experiments/trafego-med-1/{1_phase_pair_arm.csv,1b_phase_pair_aggregate.csv,2_top_segments_car.csv,3_reentry_launch_transfer.csv,3b_transfer_by_arm.csv,3c_run_coverage.csv}`; hashes completos em `4_DOSSIE_TRAFEGO_MED_1B.md`.
- Nas coortes principais de largada (2 controles por braço, 10 tratamentos por braço), não houve contato 5 Hz ou hesitação na primeira volta identificável (24/24 corridas com geometria). Em REJOIN houve pares com counterpart on-track: 553/460 nos controles e 1.597/1.366 nos dois tratamentos; solver events são subpassos separados. Hesitações agregadas são muito assimétricas, com um run respondendo por 629/632, 924/927, 465/489 e 779/797 eventos por braço.
- Os tratamentos acumularam 7.416 oportunidades congeladas sem troca sustentada; 76,5–79,9% foram classificadas nose-a-tail e a maioria ocorreu após os primeiros 60 s. Recomendação report-only: medir lado/espaço para passar com gates opt-in, OFF byte-idêntico, segurança não pior e sem transferir eventos da largada para a primeira volta. Alternativa arquivada: protocolo de cedência no follow. Sem inferência causal, edição de produção, simulação, smoke, suíte ou promoção.

## PASS-1 — decisão de passagem (2026-10-24)

- PASS-1 (2026-10-24): audit congelado terminou `all_gates_pass=false`; g3 mediana (+2,22%) e g4 contatos (171 na 1ª volta; 29 pós-rejoin vs 17 OFF) falharam; g4 da largada é PARE informativo dado R1=4.140 contatos. R3 não executada; recomendação ao dono: novo ciclo de diagnóstico/refinamento, sem promoção. Evidências e hashes: `backend/experiments/pass-1/5_EXECUCAO_PASS_1.md`.

- YIELD-1C (2026-10-25): freeze `b9f9061` e código `d4b4eb0` conferidos; R2-Y2 standalone exit 0, 30.000 linhas e CSV byte-idêntico a R1, porém `engaged=0`, `consumed=0`, `aborted=0` em todos os carros. g2 FAIL; YIELD arquivado definitivamente, sem promoção, com pivô para Etapa 4. Ver `backend/experiments/yield-1/EXECUCAO_YIELD_1C.md` e `4_AUDIT_YIELD_1C.json`.

## COMPOSITE-MAP-1 — inventário frozen da Etapa 4 (2026-10-25)

- Inventário report-only congelado em `98a71e672f5241ff0e9f3cfea9481b71322fa23f`; 6 pins críticos conferidos pelo dono (solo/residual/código/runner + corpus rejoin/manifest). Conclusão: Composite treinável pelo residual gating existente (solo v10 congelado, entry residual de `train_dagger.py`), mas os CSVs medidos não são treináveis hoje — conversão, rotulagem (professor-replay), split por episódio e proveniência (fontes SEM_BLOB_HEAD) pendentes. Rumos do dono: contrato residual v15; rotulagem por professor-replay; ordem COMPOSITE-CORPUS-1 → COMPOSITE-BASE-1 → COMPOSITE-TRAIN-1. Ver `backend/experiments/composite-1/PREREG_COMPOSITE_MAP_1.md`.

- COMPOSITE-CORPUS-1 (2026-10-25): instrumento report-only congelado; 7/7 testes focados passaram, censo SHA `fcd29503…` com 0/38 fontes elegíveis e 26 `SEM_BLOB_HEAD`; sem treino, inferência, simulação ou edição de produção. Ver `backend/experiments/composite-1/PREREG_COMPOSITE_CORPUS_1.md`.
- COMPOSITE-COLLECT-1C (2026-10-26): conversão offline A/B com splits rank-80/10/10, famílias e hashes conferidos; g0 preservou exatamente as 20 falhas canônicas. Dois commits autorizados registram events e shards/audits/logs; recomenda-se ao dono ratificar COMPOSITE-BASE-1 após revisar a ressalva do denominador `monaco_rejoin`. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_COLLECT_1C.md`.
- COMPOSITE-BASE-1 (2026-10-26): g0 pinado 453 testes (20F/430P/3S, log `db0abd33…`); 4 corridas formais R1-R4 exit 0 com 30.002 linhas e sidecars completos; extrator determinístico (hashes idênticos em 2 leituras); proveniência commits `7cb4f19` (12 artefatos) e `ceeaa20` (4 métricas); deltas Composite vs blind medidos (−36% a −44% contatos, +6,7pp fora em Interlagos); sem treino ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_BASE_1.md`.
- COMPOSITE-TRAIN-1 (2026-10-27): g0 pinado 460 testes (20F/437P/3S, log `bf051732…`); 2 treinos formais (Run 1 candidato + Run 2 réplica seed 42) concluídos exit 0; gates O-1 e réplica PASS (delta val_loss 0.0, max |dW| 0.0, NPZ SHA `6210fff6…` byte-idêntico); proveniência commit `c186ef2` (10 artefatos); sem corrida, simulação ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_TRAIN_1.md`.
COMPOSITE-BASE-2 etapa B executada (agente, 2026-10-27): g0 460=20F/437P/3S fail-set canônico exato; R1'-R4' 4/4 gates (R2'/R4' blind BYTE-IDÊNTICOS ao BASE-1; override 6210fff6/6a2dbf53 nos logs); extração 8/8 determinística; commits ab9da45 (provenance) + 3a02c11 (metrics); EXECUCAO staged; zero PARE; bucket TEST selado intocado.
COMPOSITE-STAGE-5 etapa B executada (agente, 2026-10-28): desselo TEST em 2 leituras exit 0 (6.000 amostras A_VER+B_SAI); candidato 6210fff6 SANCIONADO (5/5 gates PASS: Huber 0.2885 vs null 0.7077 ratio 0.4077 <= 0.80; MAE 0.5856 < 1.0440; norm 1.5985 <= 2.0; nan/inf 0; determinismo cmp byte-idêntico exit 0); proveniência commit e017874; EXECUCAO staged; zero corrida, zero treino, zero promoção.
COMPOSITE-STAGE-6 promoção executada (agente, 2026-10-28): backup B3.1 (6a2dbf53/5a2c20ce) em archive/residual_promocao_stage6; PAR candidato (6210fff6/f237ac9e) assume produção; g0 pós 462=20F/439P/3S (460 canônicos + 2 testes do selo, ambos PASS; fail-set canônico exato, diff bit-a-bit — emenda de contagem do dono); R1''/R3'' sem override cmp byte-a-byte vs BASE-2 PASS; g3 residual baseline 6210fff65b19ad0e; commits c8270a5+608e671; EXECUCAO staged; zero PARE.
- REALISMO-1 C0 (2026-10-29): etapa B executada após freeze `240bacde`; 8 corridas OFF N=1..4 seriais, 32 extrações determinísticas, 2 relatórios de ruído byte-idênticos; g0 20F/458P/3S com fail-set canônico; sem mecanismo/promoção. Ver `backend/experiments/realismo-1/c0/EXECUCAO_REALISMO_C0.md`.
2026-10-30 REALISMO-1 C1 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C1.md.
2026-11-01 REALISMO-1 C2 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C2.md.
2026-11-02 REALISMO-1 C3 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C3.md.
2026-11-03 REALISMO-1 C4 etapa B: análise offline de geometria (Tasks 10-11); 2.199 voltas filtradas; PARE duro em frame RMS (17,79 m > 5,0 m); ramo GEOMETRIA rejeitado; adoção do ramo FALLBACK (A5); zero corrida; C4_FINDINGS.md.
2026-11-04 REALISMO-1 C6 etapa B: matriz ON N=0..4 (20 corridas) + 4 controles OFF + 96 leituras de extração determinísticas + EXECUCAO_REALISMO_C6.md.
2026-11-04 REALISMO-1 C7 consolidação: matriz ON/OFF em N=5..8 (16 corridas) + 64 leituras de extração determinísticas + EXECUCAO_REALISMO_C7.md.
2026-11-05 REALISMO-1 promoção produção: defaults --rejoin-handoff align e --rejoin-ramp adotados no composite; suíte 20F canônica confirmada; RELATORIO_PROMOCAO_REALISMO_1.md.
2026-11-06 ABERTURA PERCEPÇÃO-1 + C8-rejoin: selados N=9..12 (confirmação C8) e N=13..16 (confirmação Fase 3); pools 76..79 e shards test/ intocados; PREREG_PERCEPCAO_1_F0.md e PREREG_C8_0.md.
2026-11-06 C8-0 referência: 10 corridas em N=0..4 (Interlagos e Monaco) + 40 extrações determinísticas cmp=0; EXECUCAO_C8_0.md.
2026-11-06 C8-B execução: 2 controles OFF cmp=0 + 10 corridas ON N=0..4 + 48 extrações determinísticas; gates primário/B-1/R-2/reentrada não aprovados; EXECUCAO_C8.md.
2026-11-06 C8-B errata: números agregados N=0..4 confirmam FAIL por B-1 (+48% contatos Interlagos, +17% Monaco) e R-2 (+1,9 pp fora Interlagos); voltas ON=354 passam R-1; PERCEPÇÃO-1 formalmente suspensa por falha do professor na Task 3 (sobreposição 94,1%).
2026-11-06 ABERTURA PROF-CURVA-1: teto de velocidade local no professor solo; PREREG_PROF_CURVA_1.md.
2026-11-06 PROF-CURVA-1 Task 2: referência solo 600 s Interlagos confirmada (4 voltas, 24,6% fora, 4 saídas crônicas C01/C06/C07/C08 em 100% das voltas; teto guarda ritmo <=123,05 s); REF_FINDINGS.md.
2026-11-06 PROF-CURVA-1 Task 4: fronteira v2 250 medições cmp=0; 10 corridas OFF solo Interlagos/Monaco N=0..4 e 20 leituras determinísticas cmp=0; baseline confirma saídas crônicas e 56,4–57,2% fora em Monaco; EXECUCAO_PROF_CURVA_1_0.md; PARE para closing do Dono.
2026-11-06 PROF-CURVA-1 Task 5: mapa de viabilidade OFFLINE do teto local (determinístico cmp=0 ×2, script e5853aa commitado antes da execução) — MECANISMO COMO PREREGISTRADO INVIÁVEL: guarda Interlagos estoura no PISO (integral capped 131,04 s > teto 123,05 s; Δ+34,84 s), Gate Primário inalcançável (C01 0/22 bind R 107–140 m = saída comportamental, não pacing; C06 4/20), teto engaja 74% da volta Interlagos / 89% Monaco (rastejamento 3,2–5,8 m/s); PARE automático §4 — ZERO corrida ON, orçamento 10 solo 600 s preservado, --prof-curva mantido default OFF bit-idêntico; encaminhamento preregistrado: racing line suavizada (curva geométrica 18 m na Junção) em ciclo próprio a abrir pelo dono; MAPA_VIABILIDADE.md
2026-11-06 ABERTURA RACING-LINE-1: ciclo separado para linha suavizada local do professor, com curva geométrica R=18 m na Junção; plano/prereg staged, zero corrida e zero alteração no PROF-CURVA-1; aguardando Freeze do Dono.
2026-11-07 RACING-LINE-1 Task 2: construção geométrica offline do arco R=18 m na janela C08/Junção (instrumento staged antes da execução, R7; determinístico cmp=0 ×2) — PARE §7: sem arco exato com os limites congelados (resíduo dos centros 3,189856 m ≫ 1e-3; corda 35,58 m implica sweep 162,6° vs giro real −140,6° = superdeterminado); evidência report-only: raiz bi-tangente EXATA com limites livres dentro da janela (s 2282,417 → 2342,863 m, giro −139,89°, resíduo <1e-6; +6 raízes degeneradas R_local=18 e 2 fillets locais); corredor/C1/fechamento/auto-interseção da raiz NÃO avaliados (fora do escopo do candidato); ZERO corrida, ZERO produção, pista frozen intocada, orçamento 10 solo intacto; decisão do dono: nova prereg com limites derivados / outra construção (biarc) / arquivar. GEOMETRIA_C08.json/md
2026-11-07 RACING-LINE-1 Task 3: Emenda nº 1 (limites derivados s=2282,417->2342,863 m, R=18 m); validacao offline de corredor e C1; CORREDOR_C08.md.
2026-11-07 RACING-LINE-1 arquivado: candidato de arco unico R=18 m inviavel no corredor (|lat|=10,07 m > 6,0 m); orcamento de 10 corridas solo 100% preservado; transicao para diagnostico de controle do professor (PROF-CONTROL-1).
2026-11-07 ABERTURA PROF-CONTROL-1: controle lateral do professor com feedforward arctan(L*kappa) e ajuste no ápice contra subesterço (LAGO_ANATOMY.md); PREREG_PROF_CONTROL_1.md.
2026-11-07 PROF-CONTROL-1 Task 2: implementado --prof-control opt-in (delta_ff cinemático + ld modulado por c_ld derivado); testes unitários e bit-identidade OFF PASS.
2026-11-07 PROF-CONTROL-1 Task 3: 2 controles OFF cmp=0 e 10 corridas ON N=0..4 solo 600 s concluidas com extracoes deterministicas; integridade PASS; EXECUCAO_PROF_CONTROL_1.md.
2026-11-07 PROF-CONTROL-1 Task 4 closing: avaliacao formal dos gates — REPROVADO (FAIL em Primario: 4/4/4/4 cronicas inalteradas e fora% piorou +1,67 pp; FAIL em Monaco: -0,93 pp < 5 pp com piora em C05/C12; FAIL em Guarda: 132,40 s > 123,05 s); default OFF mantido; EXECUCAO_PROF_CONTROL_1.md.
2026-11-07 ABERTURA PROF-GRIP-1: pacing grip-sensível com reserva de 10% nas janelas das 4 crônicas (hipótese única da LAGO_APPROACH_FINDINGS + GRIP_PACING_FEASIBILITY); PLANO e PREREG; matriz 2 OFF cmp=0 + 10 ON com --variedade N.
2026-11-07 PROF-GRIP-1 Task 2: implementado --prof-grip opt-in (teto grip-sensível v_alvo=v_plan·min(1,sqrt(grip/0,85))·sqrt(1/1,10) nas janelas canônicas de C01/C06/C07/C08, grip_atual = tyre.grip_multiplier por tick); bit-identidade OFF exata e 10/10 testes PASS.
2026-11-07 PROF-GRIP-1 Task 3: 2 controles OFF cmp=0 vs PROF-CONTROL-1 e 10 corridas ON --prof-grip com --variedade N solo 600 s concluidas; extracoes deterministicas cmp=0 12/12; cronicas nao zeradas (C06/C07/C08 4/4/4/4; C01 3 em N1/N2); PRELIMINAR_PROF_GRIP_1.md.
2026-11-07 PROF-GRIP-1 Task 4 closing: avaliacao formal dos gates — REPROVADO (FAIL em Primario: C06/C07/C08 4/4/4/4 inalteradas e C01 3 em N1/N2; FAIL em Monaco: delta offtrack > 0 em N3/N4 e regressao C05; FAIL em Guarda: mediana 129,0–130,4 s > 123,05 s); causa: teto fator=0,9535*sqrt(grip/0,85) era comparado com v_plan*0,93 e foi no-op em >80% da corrida; default OFF mantido; EXECUCAO_PROF_GRIP_1.md.
2026-11-07 ABERTURA PROF-PACE-1: pacing preventivo grip_mode=fixed (grip_ref=0,789547 SOFT 6 voltas DRY 42°C; 0,807 NÃO é o pior caso confirmado pelo TyreState canônico); escada η1=0,48848/η2=0,40000; PLANO e PREREG; decisões do dono pendentes (controles OFF, escalada, Guarda voltas limpas).
2026-11-07 PROF-PACE-1 Task 1 (correção documental): grip_ref recalculado com demonstração n_laps=ceil(600/130,195)+1=6 aplicações exatas; length_factor precisão completa 0,9245415555555555 (versões divergentes removidas); grip_ref=0,7895474400345001; SHAs completos pinados; identidade operacional congelada (--n-cars 1, VER, SOFT, 42,0°C, grip fixed nunca atualizado); decisões do dono marcadas PENDENTE_DO_DONO (controles OFF, escalada η1→η2, Guarda voltas limpas).
2026-11-07 PROF-PACE-1 Task 1 (auditoria final): decisões do dono registradas (CTRL_OFF pareado N=0..4; ON η1 N=0..4; ON η2 N=0..4 condicional; orçamento máx 15; escalada com 5 condições; Guarda = mediana das voltas limpas por realização, mediana das medianas ≤ 123,05 s, OFF inconclusivo por desenho); auditoria clima/grip: 6 realizações DRY 0 transições grip 0,8420→0,8070 (gate grip_ref PASS); variação N0..N4 = jitter IC (variedade_params); t_base 96,202 / t_margin 103,656 / t_cap η1 105,660 / η2 107,080 com grip_ref 0,789547 (todos cabem).
2026-11-07 PROF-PACE-1 FREEZE Task 2 (dono): mecanismo --prof-pace congelado (grip_mode=FIXED grip_ref=0,7895474400345001; escada eta1=0,48848/eta2=0,40000; k_inst no v_safe + k suav 20 m nas passadas; tempos do PACE_MARGIN com 30 m superados; exclusividade vs --prof-grip/--prof-control; 0,93 uma vez -> cap -> passadas; correcao wrap-safe da mascara C01 + teste de cobertura circular; equivalencia cap inativo 1e-9; clima 6 realizacoes DRY 0 transicoes, grip_ref <= grip final 0,807); custos canonicos pelo caminho do controlador: t_base 96,201711 / t_margin_only 103,442766 / t_cap eta1 107,410153 / eta2 109,610725 (folga >= 15,6 s); incremental sobre t_margin: +3,97 (eta1) / +6,17 (eta2); reducoes rel max 38%/44%; estimativa 111-113 s observados = extrapolacao exploratoria do dono (sem status de medicao/gate); ressalva 1: os 4 ticks s1872-1884 (frenagem antecipada C06, dist 8,0 m, regra d_b <= 2*ds) com metricas no relatorio do executor; ressalva 2: determinismo pareado verificado estruturalmente (ICs = f(seed,N) puro) e empiricamente para variedade 0 (REF=CTRL bit-identico); N>0 sem duplicatas nos dados existentes (limitacao registrada para a Task 3).
