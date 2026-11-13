# PREREG_PROF_GRIP_1 — pacing sensível ao grip nas 4 crônicas de Interlagos

**Data:** 2026-11-07 (America/Sao_Paulo)
**Branch:** `feat/sanidade-produto`
**Estado:** preregistro da Task 1; aguardando Freeze do Dono.
**Programas de origem:** PROF-CURVA-1 (`a0e9139`), RACING-LINE-1 (arquivado),
PROF-CONTROL-1 (REPROVADO, `41f7968`), estudos LAGO_APPROACH_FINDINGS e
GRIP_PACING_FEASIBILITY (homologados em `f35bc51`).

## 1. Declaração formal e falsificável

**Hipótese:** com o teto de pacing grip-sensível ativo nas janelas das 4
crônicas, as saídas crônicas de Interlagos caem para **zero em cada
realização ON** (N=0..4, com `--variedade N`).

**Teste falsificável:** 10 corridas ON solo de 600 s (Interlagos e Monaco,
N=0..4, `--variedade N`, série). **Falsificação = qualquer saída em C01,
C06, C07 ou C08 em qualquer realização ON**, ou qualquer saída nova nas
demais curvas de Interlagos, ou regressão localizada em C05/C12 de Monaco.

**Previsão quantitativa prévia (do estudo de viabilidade, não é gate):**
custo no piso teórico ≤ +2,05 s para todo o intervalo de grip — o piso com
o mecanismo fica ≤ 98,25 s, ≪ Guarda 123,05 s.

## 2. Fórmulas exatas e janelas

Aplicação por tick, **apenas dentro das janelas canônicas** de C01, C06,
C07 e C08 (`build_corner_definitions`, κ>0,006, fusão 40 m — janelas
efetivas registradas no log da primeira corrida ON):

```
fator(t)    = min(1, sqrt(grip_atual(t) / 0,85))        # nunca escala p/ cima
f_reserva   = sqrt(1 / 1,10)                            # 10% de margem física
v_target(s,t) = v_plan(s) · fator(t) · f_reserva
v_exec(t)   = min(v_plan(s), v_target(s,t))             # fora das janelas: v_plan
```

- `grip_atual(t)` = **`tyre_grip` instantâneo do estado físico do tick** (a
  coluna telemetrada; proibido usar média por volta ou valor fixo);
- `v_plan(s)` = perfil canônico do professor (grip 0,788, sf 0,80, ds 4 m,
  suavização 20 m) — **intocado fora das janelas**;
- pacing-only: nenhum termo de esterço; rejoin/governor/física intocados;
- janelas sobrepostas por arco de frenagem a montante: **não** existem
  transições dinâmicas — o teto é aplicado por tick dentro da janela e o
  controlador faz a frenagem natural dele (comportamento idêntico ao OFF
  fora das janelas).

## 3. Fontes e hashes pinados

| fonte | identidade |
|---|---|
| `experiments/prof-control-1/LAGO_APPROACH_FINDINGS.json` | SHA-256 `0175e662e61d5a5b…` |
| `experiments/prof-control-1/GRIP_PACING_FEASIBILITY.json` | SHA-256 `ecb4d842ba197172…` |
| `tracks_frozen/interlagos_v2.json` | `164876196eb12174` |
| `tracks_frozen/Monaco_v2.json` | `67ca11dc211c8c78` |
| `model_train/reference_controller.py` (abertura) | SHA-256 `7b35de70dacda31b…` |
| `model_train/race_diagnostic.py` (abertura) | SHA-256 `ddbcfe74733885b1…` |
| `model_train/f1_env.py` (tyre/steer limit) | SHA-256 `e488967f3d7dee5f…` |
| `scripts/saidas_verdict.py` (regiões/eventos) | SHA-256 `e1ac9f699e6d1339…` |

Constantes congeladas: `grip_ref = 0,85`; `f_reserva = sqrt(1/1,10)`; grade
de estudo 0,85→0,75 (a degradação observada no REF cobre 0,842→0,807);
Guarda **123,05 s**; janelas por `build_corner_definitions` canônico.

## 4. Integridade e isolamento

- `--prof-grip` default OFF; **OFF byte-idêntico** (arrays e CSV) — testes
  de bit-identidade obrigatórios na Task 2;
- engajamento **só no caminho professor** (mesma guarda de
  `--prof-curva`/`--prof-control`); ON fora do professor = erro loud;
- banner do runner registra `prof_grip=`; janelas efetivas e `c_ld`-análogo
  (aqui: `grip_ref`/reserva) registrados no log ON;
- `run_race_10_cars.py` permanece intocado.

## 5. Gates formais (avaliados só na Task 4)

### Primário — Interlagos

ZERO saídas em C01, C06, C07 e C08 em **cada** realização ON (baseline do
estágio 0: 4/4/4/4), e ZERO saídas novas nas demais curvas. Tabela por
realização obrigatória; melhora agregada não compensa regressão localizada.

### Secundário — Monaco

`Δofftrack ≤ 0` (tempo fora ON ≤ OFF, agregado do instrumento) **e** zero
regressões locais em C05 e C12 (comparadores OFF do mesmo ciclo, com
`--variedade` correspondente).

### Guarda de Ritmo

Mediana de volta solo Interlagos ON **≤ 123,05 s**. Estouro = **PARE
automático** (não se amplia o teto nem se promove o mecanismo).

### Integridade

Exit 0; CSV 3.002 linhas; sidecar presente (vazio por convenção solo);
SHA da pista no cabeçalho; `prof_grip=True` + `--variedade` no log ON;
extrações 2 leituras `cmp=0` por corrida.

## 6. Orçamento e ordem

**12 corridas solo de 600 s** (2 OFF controles com `cmp=0` contra o CSV
histórico + 10 ON N=0..4 com `--variedade N`), série, mais leituras
determinísticas. Sem 10 carros, treino, rede. N=9..12, N=13..16, pools
76..79 selados.

Ordem: 1. Freeze deste prereg → 2. Task 2 implementação + testes OFF/ON
(sem corrida) → 3. PARE → Freeze da implementação → 4. Task 3 corridas +
extrações → 5. Task 4 gates/relatório/ledgers → PARE para closing.

## 7. Critérios de PARE

PARE imediato se: bit-identidade OFF quebrada; engajamento fora do
professor; qualquer saída crônica em qualquer ON (falsificação); saída nova
em Interlagos; regressão em C05/C12; `Δofftrack > 0` em Monaco; Guarda
estourada; `cmp≠0`; ausência de integridade; ou necessidade de alterar
`grip_ref`/reserva/janelas pós-resultado. Nenhum caso autoriza ajuste post
hoc.

**Estado desta abertura:** zero corrida, zero código de produção, zero
alteração de pista frozen; aguardando Freeze do Dono.
