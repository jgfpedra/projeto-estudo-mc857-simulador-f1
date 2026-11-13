# PREREG_PROF_CURVA_1 — teto de curvatura local no professor

**Data:** 2026-11-06 (America/Sao_Paulo)
**Branch:** `feat/sanidade-produto`
**Estado:** preregistro da Task 1; aguardando Freeze do Dono.

## 1. Hipótese e escopo

O professor solo apresenta quatro saídas crônicas em Interlagos — Descida do
Lago (s≈31), Bico de Pato (s≈1947), Mergulho (s≈2059) e Junção (s≈2318) —
além de uma volta larga na grama. A hipótese PROF-CURVA-1 é que o
`VelocityProfile` suaviza excessivamente a curvatura em uma janela de cerca de
30 m e, nas quinas, entrega um `v_plan` acima do raio fisicamente viável.

Esta etapa mede a fronteira física atual e fixa o experimento. Não há corrida
do professor, treino, alteração de código de produção, alteração do governor
ou matriz de 10 carros autorizada nesta Task 1.

## 2. Origem das constantes e instrumento

Todas as constantes numéricas da intervenção devem ser derivadas somente de
`backend/experiments/prof-curva-1/physics_frontier_current.json`, produzido
por `backend/scripts/calibrate_physics_frontier.py` a partir de
`backend/archive/scripts/physics_radius_calibration.py`. O arquivo
`backend/model_train/physics_frontier.json` é legado de produção e permanece
intocado; ele não é fonte desta preregistração.

O arquivo atual registra a grade medida de velocidades até 25 m/s, os raios
testados e os dois grips nominais (`real` 0,788 e `soft` 0,842), além dos
critérios de classificação `LIMPO`, `MARGINAL` e `QUEBRA`. A Task 3 deve ler
essa saída em runtime; não é permitido copiar a fronteira para constantes
hardcoded em `race_diagnostic.py`.

## 3. Mecanismo pinado

O candidato é um teto local aplicado apenas ao professor solo:

1. calcular a curvatura local instantânea, sem a suavização excessiva de 30 m
   nas quinas;
2. consultar a fronteira física medida para o grip vigente;
3. limitar a velocidade local proporcionalmente ao raio físico viável;
4. manter o governor de produção e os caminhos não-professor intocados.

A implementação da Task 3 deverá ser opt-in, default OFF e bit-idêntica ao
professor histórico quando desligada. Nenhum resultado de uma execução ON
será promovido sem avaliação formal dos gates abaixo.

## 4. Gates formais

### Gate Primário — Interlagos

- ZERO saídas em Descida do Lago, Bico de Pato, Mergulho e Junção;
- ZERO saídas novas em qualquer outro setor da pista.

### Gate Mônaco

Redução material de tempo fora de pista, com `Δfora% >= 5 pp`, sem piora em
nenhuma curva. Uma melhora agregada não compensa regressão localizada.

### Guarda de Ritmo — Decisão 3=b

A perda máxima de tempo de volta solo fica limitada a 15% sobre a baseline
histórica. Se o teto for ultrapassado para manter o carro limpo, o resultado é
PARE automático: não se amplia o teto nem se promove o mecanismo. O próximo
ciclo autorizado deverá avaliar racing line suavizada, com curva geométrica de
18 m na Junção.

## 5. Execução e orçamento

- Task 1: calibração de skidpad até 25 m/s, sem corrida do professor;
- Task 2: depois do Freeze do Dono, uma referência solo de 600 s do professor
  em Interlagos;
- Task 3: depois de nova autorização, implementação isolada no professor em
  `race_diagnostic.py`;
- Task 4: depois de nova autorização, corridas solo de 600 s em Interlagos e
  Monaco para os gates.

O orçamento é exclusivamente de corridas solo de 600 s do professor. Não há
matriz de 10 carros nesta linha. Pools 76–79, N=9..16 e shards `test/`
permanecem selados.

## 6. PARE formal

Task 1 termina após a validação dos ledgers, dos testes, da saída isolada e do
stage. O próximo passo é o **Freeze do Dono**. Sem esse Freeze, não executar a
Task 2, não alterar `race_diagnostic.py` e não correr o professor.
