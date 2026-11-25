# PRÉ-REGISTO — CICLO LARGADA, FASE 1b: LAUNCH-STAGGER (commitado ANTES de qualquer código de mecanismo)
# Orçamento (aritmética explícita): 2 smoke (s0) + 1 base s60 (única DAMP do scan 6551bac)
#   + 10 tratamentos 60-69 = **13 runs** (runs ≠ arquivos — lição 12→13→14).
# PAREs transversais: prereg ausente antes de código/run; scan >5/10 DAMP (PASSOU: 1/10);
# SELF falho pós-fix; FAIL por seed; suite 25F invariante; leitura de clima no runner;
# combinação cap×stagger aceita.

## 0. DADOS PRÉ-COMITADOS (citados)
- Scan 60-69 (6551bac): **1/10 DAMP — s60 (v2 DRY→CLOUDY; v3 CLOUDY→DAMP)**;
  s66/s68 CLOUDY-only; resto seco. s60 exige base fresca (pareio, padrão s50).
- Probe Δt (0268919): v_plan REAL (construtor exato grip 0,788/sf 0,80):
  s2725=45,7 | s2800=20,3 | s2850=33,5 | s2700=57,1. Gap pós-release = v(s)×Δt:
  **Δt=1,0 s → 1º par 20,3-57,1 m (≥2× os 9 m do grid na zona da queixa)**;
  Δt=0,5 → 10-29 m (marginal); Δt=1,5 → +13,5 s de atraso com ganho decrescente.
  **Δt PINADO = 1,0 s/slot.**

## 1. MECANISMO — UMA variável: flag `--launch-stagger` (store_true, DEFAULT OFF)
- **Lei**: enquanto `sim_ts < release(slot)`: ações forçadas `th=0, brk=1`
  (pose mantida — carro nasce parado com freio; zero creep verificado no t2);
  `release(slot) = (grid_position − 1) × Δt`, **Δt = 1,0 s** (P1→0 s;
  P10→9,0 s). Ordem frente→trás (trás→frente empilharia no grid). Com
  `--variance grid`, grid_position = slot REAL do run (o runner passa a ordem
  de largada efetiva ao controller — única fonte da verdade; **flag on sem
  ordem = erro explícito**, nunca no-op silencioso).
- **Pós-release canônico PURO (zero resíduo)**: o hold LIMPA o estado da
  recovery (`rec.clear()`) a cada tick held — sem isso, a recovery veria o
  carro "encravado" por até 9 s e governaria a largada do pós-release
  (declarado ANTES das runs). Governor/gap-check/blocked: sem estado ou
  transitório; a obs prev_action carrega o histórico REAL (o carro estava
  freando) — isso é o passado físico, não interação.
- **ZERO constantes novas além de Δt=1,0** (LAUNCH_STAGGER_DT = 1,0).
  **NUNCA lê clima** (lição GUI≠headless). `--launch-cap` × `--launch-stagger`
  **mutuamente exclusivos** (erro no argparse; combinação não definida).
- **Telemetria (CSV aditivo, flag on)**: `stagger_held` (1 = held neste tick),
  keyed POR CARRO via drivers[i] (lição stale-drv); **authority 'stagger'
  ⟺ held=1 linha a linha**. identity por run (`launch_stagger=True/False`).
- **Cadeia de autoridade**: stagger (hold no grid) > segurança
  (rejoin/recovery/blocked) > governor > policy — o stagger é a ÚLTIMA
  escrita em th/brk enquanto held e rotula; esterço segue o computado
  (carro parado — irrelevante).

## 2. CRITÉRIOS DO GATE (âncoras: 82b12c6 + worklog L-0; instrumento idêntico)
- **PRIMÁRIO-1 (vinculante, delay-invariante)**: pares_W med ≤ 8 E máx ≤ 14
  (pares distintos com ≥1 evento solver em t ≤ 60 s; W cobre o storm
  deslocado ≤ +9 s).
- **PRIMÁRIO-2 (EMENDA pré-registrada, justificada)**: ≥ 7/10 runs com
  taxonomia ≠ CONTATO-ADJ (dono em ±2 s) OU run sem excursão. O ramo
  `t > 12,4 s` da L-1a é RETIRADO: o mecanismo POR CONSTRUÇÃO desloca t
  (até +9 s), tornando o ramo sensível a atraso puro — o hold sincronizado
  da era contaminada já mostrou 32,6 s sem reduzir nada. O critério de
  higiene vinculante é o PRIMÁRIO-1.
- **NÃO-REGRESSÃO**:
  - rolante SECAS ≤ 141 s; s60 ≤ rol base fresca s60 + 5 s. **Rolante da
    L-1b EXCLUI a volta 1 de cada carro** (custo declarado +9×Δt; exclusão
    declarada AQUI, implementada no veredito).
  - GUARD-V: 10/10 carros ≥ 1 volta.
  - **paradas/wanderers SECAS 0/0 APÓS o release de cada carro — a janela
    de hold NÃO conta como parada** (exclusão por `authority='stagger'`
    fase 1:1, implementada no veredito/métrica: episódio de parada = trecho
    contíguo v<0,5 em ticks NÃO-held do carro, ≥3 s; wanderers idem —
    carros held estão on-track, sem efeito). s60: pareio ≤ base fresca.
  - fora% ≤ 28,3 (caveat clima: s60 damp pode refletir clima — diagnóstico
    por seed usa a base). cc (soma car_car): SECA ≤ 3.197 | DAMP ≤ 3.850.
- **Expectativa REPORT-ONLY pré-registrada (não-gating)**: pares_W med ≤ 8 →
  hipótese de DENSIDADE validada (adoção opt-in + grid-era opcional ao
  dono); pares_W ≈ âncora (12-23) → densidade inicial NÃO é o mecanismo →
  grid-era falharia a fortiori → fechar CICLO LARGADA com (b).
- **Custo declarado**: volta 1 +9×Δt no pior caso (P10) — rolante exclui a
  volta 1 (acima).

## 3. SELF BLOQUEANTE (padrão ADVERSO; smoke PRIMEIRO, seed 0 seco, par fresco)
1. flag-off bit-idêntico ao base E base ≡ histórico `r10_blind_s0`
   (drift 0/30000);
2. fase 0 violações: authority 'stagger' ⟺ held=1; release EXATO por carro:
   held=1 em [0, release) e 1º tick pós-release == (grid_position−1)×10
   ticks (P1 nunca held);
3. 1ª divergência base-vs-stagger == 1º tick com ALGUM stagger_held=1
   (tick 0 — P2..P10 held enquanto o base larga todos), nenhum outro canal.
Falha → PARE (consertar ANTES do pool; SEM consumir 60-69).
Fix de mecanismo/teste = commit antes do re-smoke; **fix de script de
decisão = commit/amend ANTES da execução (NIT permanente da L-1-review)**.

## 4. TESTES DE UNIDADE (5; suite esperada 25F/295P/2S)
t1 schedule exato (P1 t0; Pk (k−1)×Δt — held só antes do release);
t2 hold de pose (v=0, s constante, zero creep no hold);
t3 exclusão de paradas na janela de hold (held NÃO conta; pós-release
conta — helper do veredito testado);
t4 telemetria per-carro (chave própria, lição stale-drv);
t5 flag-off default no-op + REJEIÇÃO cap×stagger (argparse error).
Reparos = +1 teste com disclose (padrão REPARO).

## 5. GATE (runs SERIAIS; identity por run; árvore limpa p/ decisão)
- Comando tratamento (cwd=backend): idem canônico + `--launch-stagger`,
  out `experiments/diag-largada/race_diag_lg1b_s{N}.csv`; base s60: idem
  sem a flag, `race_diag_lg1b_base_s60.csv`.
- Veredito mecânico por `scripts/largada_lg1b_verdict.py` — commitado ANTES
  de ler QUALQUER resultado, com glob filtrando `_events` DESDE O 1º COMMIT
  (NIT R4.1). Verifica identity launch_stagger=True 10/10 + fase.
- FAIL → PARE por seed com diagnóstico; SEM re-pin, SEM re-run.
  TUDO-PASS → PARE final p/ revisão.
- Fechamento: PROJECT_STATE (header F1b) + worklog (LARGADA-1b) + memória;
  doc-test verde; suite reportada. Report-only: pares_W estratificado por
  PAR DE COMPOSTOS (insumo grid-era/ruído; zero runs extras).
