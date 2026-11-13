# PREREG_PROF_PACE_1 — pacing preventivo com razão alvo fixa (η) nas 4 crônicas

**Data:** 2026-11-07 (America/Sao_Paulo)
**Branch:** `feat/sanidade-produto`
**Estado:** preregistro da Task 1; aguardando Freeze do Dono.
**Origem:** PROF-GRIP-1 seq. (calibração + OOS + Kamm + PACE_MARGIN v2),
homologados pelo Dono até `f35bc51`-linha.

## 1. Declaração formal e falsificável

**Hipótese:** com o cap preventivo `v_target_cap` ativo (η1 = 0,48848; forma
fechada com downforce; janelas canônicas de C01/C06/C07/C08), **as quatro
crônicas caem para zero em cada realização ON do estágio final**.

**Falsificação:** qualquer saída em C01/C06/C07/C08 no estágio final; ou
saída de C06/C07/C08 **com o cap ativo** (PARE por insuficiência do
mecanismo); ou saída com o cap inativo (falha de engajamento/cobertura).

**Escalada pré-declarada:** se o estágio η1 falhar nos gates, o estágio
seguinte executa **η2 = 0,40000** (constante pré-definida — não é ajuste
pós-fato; nenhum novo valor pode ser criado após observar resultados).

## 2. Fórmulas exatas (ordem congelada)

```
c_m   = PhysicsParams.c_downforce() / PhysicsParams.mass
A     = (1,8 · grip_ref) · 9,81
denom = kappa_inst(s) − η · (1,8 · grip_ref) · c_m
v_safe(s) = sqrt(η · A / denom)   se denom > 0; senão v_plan(s)

v_ctrl        = 0,93 · v_plan(s)
v_seed(s)     = min(v_ctrl(s), v_safe(s))      [somente nas janelas;
                fora delas v_safe ≡ v_plan → v_seed = v_ctrl]
v_target_cap  = passadas backward/forward de prof_curva.py sobre v_seed
                (frenagem com círculo de atrito + drag, fecho circular
                200 m, tração; clip 0..200)
```

Aplicação **somente dentro das janelas canônicas** de C01/C06/C07/C08
(`build_corner_definitions`; janelas registradas no log ON). Pacing-only:
esterço, rejoin, governor, física, pista frozen e `run_race_10_cars.py`
intocados.

## 3. Grip: modo fixo, pool e grip_ref calculado

- **`grip_mode = fixed`**: o cap usa um `grip_ref` CONSTANTE durante toda a
  corrida (sem leitura por tick, sem atualização por volta);
- **cadência de atualização: constante durante toda a corrida**;
  `grip_mode = per_lap` está FORA deste ciclo;
- **pool de compostos seco efetivamente permitido (professor solo):**
  `{SOFT}` — o pool da `--variedade` é
  `[d.starting_tyre_compound for d in drivers]` com `--n-cars 1` = o
  primeiro piloto do grid (VER, SOFT); o shuffle de 1 elemento é no-op —
  **o composto é invariante ao N**;
- **evidência do modelo vs telemetria:** o `TyreState` canônico reproduz o
  REF byte a byte (SOFT, DRY 42,0 °C: grip 0,8421 → 0,8071 nos 5 passes);
- **clima:** `--weather seeded` com DRY e zero transições observadas em
  N0..N4 (600 s × 5 corridas); `track_temp = 42,0 °C` (pinado em
  `domain/weather.py`).

**`grip_ref` recalculado (Correção da Task 1 — demonstração da regra):**

- `t_lap_ref = 130,195 s` — mediana de volta OBSERVADA do controle
  `CTRL_Interlagos_OFF` (4 voltas: 138,572/130,498/127,441/129,891);
- `n_laps = ceil(600 / 130,195) + 1 = ceil(4,608) + 1 = 5 + 1 = 6` — a
  corrida de 600 s completa 5 voltas (cruzamentos em t =
  31,8/170,4/309,4/450,0/592,0 s) e a folga de 1 volta adiciona a 6ª
  aplicação de `TyreState.apply_lap` — **6 aplicações exatas do modelo
  canônico** (convenção discreta: `apply_lap` é chamado a cada cruzamento
  de linha);
- `length_factor = 4,160437 km / 4,5 = 0,9245415555555555` (precisão
  completa; as versões 0,9256/0,9245 divergentes estão REMOVIDAS);
- `decay/lap = 7,5 × 0,9245415555555555 = 6,934061666666667 %/volta`
  (SOFT, `weather_wear_penalty = 1,0` em DRY, `aggressive = 1,0`);
- `life(6) = 100 − 6 × 6,934061666666667 = 58,39563000000001 %`;
- `wear_factor = 0,85 + 0,15 × 0,5839563 = 0,937593445`;
- `temp_factor = max(0,5, 1 − |42,0 − 75,0| × 0,006) = 0,802` (exato);
- **`grip_ref = 0,7895474400345001`** (precisão completa; arredondado:
  0,789547).

**`grip_ref = 0,789547`** (SOFT, 6 aplicações exatas). **0,807 era o grip a
5 voltas SEM a folga — confirmado NÃO-ser o pior caso** (verificado pelo
modelo canônico: SOFT life 72,26% → grip 0,8071 ✓). HARD/MEDIUM
registrados como contexto (o pool atual não os permite; mudar o pool =
mudança de prereg).

## 3a. Auditoria de clima e grip (N=0..4, telemetrias existentes)

| realização | clima (1º/últ) | transições | grip 1º | grip últ | grip mín | grip máx | composto | driver | n-cars | variedade |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|
| CTRL_OFF (N0-equiv) | DRY/DRY | 0 | 0,8420 | 0,8070 | 0,8070 | 0,8420 | SOFT | VER | 1 | 0 |
| ON N0 | DRY/DRY | 0 | 0,8420 | 0,8070 | 0,8070 | 0,8420 | SOFT | VER | 1 | 0 |
| ON N1 | DRY/DRY | 0 | 0,8420 | 0,8070 | 0,8070 | 0,8420 | SOFT | VER | 1 | 1 |
| ON N2 | DRY/DRY | 0 | 0,8420 | 0,8070 | 0,8070 | 0,8420 | SOFT | VER | 1 | 2 |
| ON N3 | DRY/DRY | 0 | 0,8420 | 0,8070 | 0,8070 | 0,8420 | SOFT | VER | 1 | 3 |
| ON N4 | DRY/DRY | 0 | 0,8420 | 0,8070 | 0,8070 | 0,8420 | SOFT | VER | 1 | 4 |

- clima pela coluna canônica `w_kind` (a mesma da telemetria; não inferido
  pelo grip); transições = soma de `w_trans`;
- **mecanismo de variação N0..N4 identificado:** `variedade_params(seed, N)`
  = PRNG `sha256("<seed>//variedade//<N>")` → por carro
  `(d_long U[−0,5;0,5] m, d_lat U[−0,3;0,3] m, fator mu U[0,98;1,02])`
  aplicado às CONDIÇÕES INICIAIS (jitter de grid + `scale_mu_nominal`);
- **domínios invariantes:** clima (DRY, seed 0, zero transições), compound
  (`--variance off` → domínio compound inerte; pool {SOFT}), grid-order
  (inerte), driver (VER), track_temp (42,0 °C);
- **limitação registrada:** N0..N4 são realizações independentes SOMENTE no
  espaço de condições iniciais (jitter de posição + μ_nominal); mesmo
  regime climático, composto, pista e driver — não são realizações de
  regime;
- o `tyre_grip` telemetrado é invariante a N (o jitter de μ_nominal atua no
  μ_eff da física, abaixo da coluna do pneu) — consistente com o
  observado.

## 4. Fontes e hashes pinados (SHA-256 completos)

| fonte | SHA-256 completo |
|---|---|
| `tracks_frozen/interlagos_v2.json` (arquivo; pin interno do JSON: `164876196eb12174`) | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| `model_train/prof_curva.py` | `dd7d638799632efe687997922b6409cdd1c2d70b0fd17fc2180aa07bfbf66017` |
| `model_train/velocity_profile.py` | `a2953bac36064e3a531df7e43bd840efeb0a9b29a823096fa01341651024f5dc` |
| `model_train/reference_controller.py` | `26879873b3babc5ee72201afd41a1d0dadb13ee552a120d64a31f00bf3ec9038` |
| `model_train/f1_env.py` | `e488967f3d7dee5f79bf80bc07724be4f075b9f8e48c59f19ca5e8ee112755a2` |
| `scripts/prof_pace_margin_derivation.py` | `d76c9b5e381d03a5dcb67bce5db432d1e729019e2abc490fbdb8c29ea7322f21` |
| `scripts/prof_demand_out_of_sample.py` | `2ce8c4d0724bd07c2600faa712678c90db3f751a5404a0388d7069a789a0b147` |
| `corridas/CTRL_Interlagos_OFF.csv` (controle OFF histórico) | `c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a` |

(Monaco `67ca11dc211c8c78`/arquivo `af3125959ade1f82…` entra apenas no
Secundário — pinados no §5.)

## 4a. Identidade operacional congelada

```
--n-cars 1
driver inicial: VER
compound: SOFT
track_temp: 42,0 °C
grip_mode: fixed
grip atualizado: nunca durante a corrida
grip_ref: 0,7895474400345001 (recalculado nesta Task 1)
```

Qualquer mudança de número de carros, piloto inicial, pool de compostos,
clima ou cadência do grip é **mudança de preregistro** (reabertura deste
documento, não ajuste silencioso).

## 5. Gates formais (inalteráveis pós-observação)

### Primário — Interlagos

**ZERO saídas em C01, C06, C07 e C08 no estágio final** (baseline 4/4/4/4),
e zero saídas novas nas demais curvas.

### Regra de PARE por localização da falha

- **C06/C07/C08 saem com o cap ativo** (cap binding no trecho da saída) →
  **PARE e rejeição da hipótese de suficiência do mecanismo**;
- saída com o **cap inativo** (fora da janela ou cap não binding) →
  **falha de engajamento/cobertura** — não falha física do limiar;
- C01 sai com o cap ativo → avaliar a autoridade (o cliff de pneu da C01
  pode exigir o grip real por tick — `per_lap` é fora deste ciclo).

### Secundário — Monaco

`Δofftrack ≤ 0` e zero regressões locais em C05/C12 (comparadores OFF do
mesmo ciclo, variedade correspondente).

### Guarda de Ritmo (definição final registrada pelo Dono)

Para cada realização ON:

- considerar **somente voltas completas**;
- **volta limpa = zero cruzamentos de 6,0 m**;
- calcular a **mediana das voltas limpas** da realização.

**Gate: mediana das medianas por realização ≤ 123,05 s.**

- Se uma realização ON não tiver nenhuma volta limpa, a Guarda é
  **inconclusiva, nunca aprovada**;
- publicar também, apenas para transparência, a **mediana de todas as
  voltas completas**;
- a Guarda do controle OFF **não entra no julgamento** (a ausência de
  voltas limpas no OFF é esperada e registrada como "inconclusiva por
  desenho").

### Escalada η1 → η2 (condições registradas pelo Dono)

η2 só pode ser executado se, no estágio η1:

- o Gate Primário **falhar**;
- a integridade estiver **íntegra**;
- não houver **divergência de parâmetros**;
- não houver **quebra de bit-identidade**;
- a Guarda de η1 for **avaliável** e sua mediana de medianas for
  **≤ 123,05 s**.

Se a Guarda de η1 for inconclusiva, **não escalar**: encerrar como
inconclusivo.

Em η2:

- saída em C06, C07 ou C08 com cap ativo = **PARE definitivo**;
- saída em C01 com cap ativo = **Gate Primário reprovado e encerramento do
  ciclo**;
- **não existe η3**.

### Integridade

Exit 0; CSV 3.002 linhas; sidecar presente (vazio por convenção solo); SHA
da pista no cabeçalho; `prof_pace=True` + `--variedade` no log ON; janelas e
η registrados no log; extrações 2 leituras `cmp=0` por corrida.

## 6. Orçamento e ordem

**Orçamento máximo: 15 corridas solo de 600 s** (decisão do Dono
registrada): `CTRL_OFF N=0..4` (5) + `ON η1 N=0..4` (5) + `ON η2 N=0..4`
(5, SOMENTE se a escalada for acionada), série, mais leituras
determinísticas. Sem 10 carros, treino, rede. N=9..12, N=13..16, pools
76..79 selados.

Ordem: 1. Freeze deste prereg → 2. Task 2 implementação + testes OFF/ON
(sem corrida) → 3. PARE → Freeze da implementação → 4. Task 3 corridas +
extrações → 5. Task 4 gates/relatório/ledgers → PARE para closing.

## 7. Decisões do Dono (registradas nesta Task 1)

1. **Controles OFF: RESOLVIDO — pareados N=0..4** (`CTRL_OFF N=0..4`, com o
   N0 adicionalmente `cmp=0` vs o histórico `c00391ab…`);
2. **Regra de escalada η1→η2: RESOLVIDA** — η2 só executa com o Gate
   Primário de η1 falhado, integridade íntegra, sem divergência de
   parâmetros, sem quebra de bit-identidade e Guarda de η1 avaliável com
   mediana de medianas ≤ 123,05 s (§5); Guarda inconclusiva = não escalar;
3. **Guarda sobre voltas limpas: RESOLVIDA** — mediana das voltas limpas
   por realização, gate = mediana das medianas ≤ 123,05 s (definição
   completa no §5).

Estas decisões NÃO foram preenchidas por inferência pelo executor; a Task 2
NÃO se inicia enquanto impedirem o Freeze.

## 8. Critérios de PARE

PARE imediato se: bit-identidade OFF quebrada; engajamento fora do
professor; qualquer saída crônica no estágio final; C06/C07/C08 saírem com
o cap ativo (insuficiência); Guarda estourada no tempo observado; `cmp≠0`;
violação de integridade; ou alteração de η/grip_ref/janelas pós-resultado.
Nenhum caso autoriza ajuste post hoc.

**Estado desta abertura:** zero corrida, zero código de produção, zero
alteração de pista frozen; aguardando Freeze do Dono.
