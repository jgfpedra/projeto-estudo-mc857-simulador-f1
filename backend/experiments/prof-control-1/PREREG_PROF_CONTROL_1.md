# PREREG_PROF_CONTROL_1 — feedforward de curvatura e lookahead no professor solo

**Data:** 2026-11-07 (America/Sao_Paulo)
**Branch:** `feat/sanidade-produto`
**Estado:** preregistro da Task 1; aguardando Freeze do Dono.
**Programas de origem:** PROF-CURVA-1 (encerrado, `a0e9139`) e
RACING-LINE-1 (arquivado; anatomia C01 em `e1a9c25`).

## 1. Hipótese e escopo

A anatomia da Descida do Lago falsificou a saturação mecânica (4/4 passagens
com saída a ≤ 74% do volante, ZERO ticks ≥ 98%, esterço caindo no ápice) e
a geometria da Junção mostrou ápice de raio instantâneo ≈ 7,9 m. A hipótese
deste ciclo: o subesterço crônico do professor é **defeito do controlador** —
pure pursuit geométrico puro, sem termo de curvatura, com lookahead que salta
o ápice — e um **feedforward cinemático + lookahead modulado por curvatura**,
isolados no professor solo, eliminam as saídas crônicas dentro da Guarda de
Ritmo.

Não há corrida, treino ou alteração de produção nesta Task 1. O mecanismo é
opt-in (`--prof-control`, default OFF) e OFF byte-idêntico.

## 2. Fontes e constantes congeladas

| fonte | identidade pinada |
|---|---|
| `experiments/prof-control-1/LAGO_ANATOMY.json` | SHA-256 `81d3393f9c01fec8…` |
| `experiments/racing-line-1/c2/GEOMETRIA_C08.json` | SHA-256 `fe79e69ef6e91af7…` |
| `model_train/tracks_frozen/interlagos_v2.json` | `164876196eb12174` |
| `model_train/tracks_frozen/Monaco_v2.json` | `67ca11dc211c8c78` |
| `model_train/reference_controller.py` (abertura) | SHA-256 `95633403f25bc148…` |
| `model_train/f1_env.py` (teto de esterço) | SHA-256 `e488967f3d7dee5f…` |

Constantes canônicas do mecanismo (lidas em runtime, sem hardcode ad hoc):

- `L = 3,4 m` — wheelbase canônica do `ReferenceController` (`wheelbase_m`);
- `k_ld = 0,6`, `ld_min = 5,0 m`, `ld_max = 45,0 m` — canônicos do
  lookahead do `ReferenceController`;
- `steer_limit_rad(v)` — teto canônico do env
  (`max(0,04, rad(45°)/(1+(v/25)²))`, `f1_env.py:530`);
- `κ_local(s)` — curvatura local instantânea da pista frozen com janela
  mínima (função canônica `prof_curva._instantaneous_kappa_profile`),
  SINAL completo (`env._kappa_signed`), nunca o perfil suavizado de 30 m;
- pista e `v_plan` do professor: intocados (o pacing permanece o histórico).

## 3. Mecanismo pinado (implementação da Task 2, após Freeze)

1. **Feedforward cinemático:** `δ_ff(s) = arctan(L · κ_local(s))`;
2. **Lookahead modulado:** `ld_eff = clip(k_ld·v, ld_min, ld_max) · g(κ)`,
   com `g(κ) = 1/(1 + c_ld·|κ_local(s)|)`;
3. **Esterço comandado:** `steer_cmd = clip((δ_ff + δ_pp)/steer_limit_rad(v),
   −1, 1)`, onde `δ_pp` é o pure pursuit existente com `ld_eff` no lugar de
   `ld` — o pursuit vira termo residual de correção lateral; nenhum outro
   caminho (trafego, pass_layer, rejoin, governor) é alterado;
4. **Derivação de `c_ld` (regra fixada ANTES da implementação):** a partir
   do segmento 3 de `LAGO_ANATOMY.json` —
   `c_ld = (ld_base/ld_alvo − 1)/κ_w`, com
   `ld_base = k_ld·v_exit` (v_exit = velocidade no instante da saída do
   segmento 3, em m/s), `ld_alvo = s_exit − s_ratio_max` (arco da razão
   máxima ao instante da saída, em m) e `κ_w = κ máx da janela do segmento 3`
   — o valor que mantém o ponto de perseguição dentro do arco nas condições
   exatas em que a C01 sai. O número derivado e a conta são registrados no
   log da corrida ON e no relatório da Task 4;
5. **Guarda de escopo:** `--prof-control` só engaja no caminho professor
   (mesmo padrão de guarda de `--prof-curva`); OFF mantém arrays e CSV
   byte-idênticos; ON fora do professor = erro loud.

Nenhum resultado ON pode alterar constantes post hoc (§7).

## 4. Gates formais (avaliados só na Task 4)

### Gate Primário — Interlagos

Em cada realização ON: **ZERO** saídas em C01 (Lago), C06 (Bico de Pato),
C07 (Mergulho) e C08 (Junção), e **ZERO** saídas novas nas demais curvas.
Tabela por realização obrigatória; melhora agregada não compensa regressão
localizada.

### Gate Mônaco

Redução de tempo fora de pista com **Δfora% ≥ 5 pp** (agregado definido pelo
instrumento), sem aumento de excursões, |lat| máximo ou tempo fora em
nenhuma curva.

### Guarda de Ritmo — Decisão 3=b

**Mediana de volta solo ON ≤ 123,05 s** (baseline limpa histórica 107,0 s ×
1,15, pinada no PROF-CURVA-1). Estouro = **PARE automático**: não se amplia
o teto nem se promove o mecanismo.

### Gates de integridade

Exit 0, CSV de 3.002 linhas, sidecar presente, SHA da pista no cabeçalho,
variedade no log, flag/config no log das corridas ON, duas leituras
determinísticas com `cmp=0` por extração, testes de bit-identidade OFF
verdes.

## 5. Orçamento e ordem de execução

Estritamente corridas solo de 600 s do professor: controles OFF (bit-idênticos
contra o estágio 0 do PROF-CURVA-1) e corridas ON N=0..4 em Interlagos e
Monaco, em série, mais leituras determinísticas. Sem 10 carros, treino, rede
ou alteração de cache. N=9..12, N=13..16 e pools 76..79 selados.

Emenda documental da auditoria da Task 1: `backend/scripts/run_race_10_cars.py`
permanece intocado neste programa; o mecanismo `--prof-control` é exclusivo do
caminho professor em `backend/model_train/race_diagnostic.py` — nenhum
comportamento neural ou composite é alterado (o runner visual não é tocado).

Ordem obrigatória:

1. Freeze do presente plano/prereg;
2. Task 2 — implementação isolada + testes OFF/ON (sem corrida);
3. PARE → Freeze do Dono da implementação;
4. Task 3 — corridas solo e extrações determinísticas;
5. Task 4 — gates, relatório, linha nos três ledgers, PARE para closing.

## 6. Critérios de PARE

PARE imediato se houver: quebra de bit-identidade OFF; engajamento fora do
professor; falha de qualquer gate formal; violação da Guarda de Ritmo;
`cmp≠0`; ausência de sidecar/integridade; ou necessidade de alterar
constantes pós-resultado. Nenhum desses casos autoriza ajuste post hoc.

**Estado desta abertura:** zero corrida, zero código de produção, zero
alteração de pista frozen; aguardando Freeze do Dono.
