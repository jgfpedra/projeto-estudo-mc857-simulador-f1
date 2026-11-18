# PRÉ-REGISTO — FASE 4 v15 (wiring): composite no race runner — B3' sob regime canônico
# Commitado ANTES de qualquer código/medida. A PROMOÇÃO (race default =
# composite?) NÃO é desta fase — a fase produz evidência; decisão = dono.
# R13 mantém v10-cego como default. Mirrors/loader/v1s INTOCADOS.

## 1. ESCOPO (SÓ inferência; residual_best r2 e v10_best CONGELADOS)
- (a) all-composite N=10: JÁ EXISTE via `--profile composite` (recon §PASSO 0)
  — validar no B3.1', sem novo wiring.
- (b) `--mixed` estendido: grupo `composite` ("composite:N,edge:M"):
  parse_mixed + branch de construção (ctrl_comp = obs traffic + solo v10 npz +
  NumpyCompositeActor) + loop de 3 controllers + export CSV por grupo
  (g_gate/r_norm/composite_active para o grupo composite).
- PAREs: retreino; pool; fastf1; mirrors/loader; mudar race default/promoção
  sem dono; editar commits fechados; iterar código contra gate que falhou.

## 2. INSTRUMENTO CANÔNICO (R13 — o regime de TODA a B3'; recon §PASSO 0)
`.venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras
--obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed {N} --gov vplan
--variance grid,compound --out ...`
Regime canônico: v10-cego fora 21-32%; clima semeado por seed; seed 0 = DRY
sem transições (probe registrado). TODAS as corridas da B3' na MESMA sessão
(seed 0, determinístico).

## 3. RECONCILIAÇÃO DE LIMIARES (PRÉ-run; derivação — NÃO é re-pin pós-número)
O prompt carrega os limiares ABSOLUTOS da era pré-canônica do B3.1
(fora ≤1,5%; rolante ≤115s) — medidos com clima-loteria/live-track, marcados
PRÉ-CANÔNICOS pelo próprio contexto pinado. Sob o regime canônico R13 esses
absolutos são SABIDAMENTE inatingíveis (R13: composite fora 25,1-41,2%; rolante
~136-158s; PROJECT_STATE FASE R13-GATE). Re-ancoragem PRÉ-run com derivação:
- fora ≤ 29,9% = p75 SECO do braço A composite (R12 0.6, quantis por
  condição; corrida é seed 0 = SECO).
- rolante ≤ controle da MESMA sessão + 10 s (R10 D3: gap de pace do
  composite ~7 s; a âncora correta é o controle coletâneo, não o absoluto
  pré-canônico).
- 10/10 ≥1 volta; 0 paradas ≥3s; hesitações ≤3 — mantidos ABSOLUTOS
  (eram asseguráveis no seco na era: B3.1 10/10/0/0).
- **CONTATOS carro-carro < controle da mesma sessão = GATE OPERACIONAL
  PRIMÁRIO** (o valor de segurança do composite; âncoras históricas
  1576/1333 NÃO valem — só o controle coletâneo).

## 4. CORRIDAS (orçamento ENUMERADO: 6 corridas 600s seriais, seed 0, DRY)
1. **CONTROLE all-v10-cego vplan** (âncora de tudo): deve cair no regime
   canônico (fora 21-32%). Fora disso → PARE e investigar o instrumento.
2. **B3.1' all-composite** (`--profile composite`): critérios §3.
3. **B3.3'-a MISTA {composite:2, edge:8}** com `--shuffle-grid`:
   contatos pós-largada ≈0 no grupo composite; 0 hesitações no grupo v10;
   pace do grupo v10 ≈ controle da sessão; comparação contra o
   CONTROLE-EMBARALHADO (corrida 5).
4. **B3.3'-b MISTA {composite:4, edge:6}** idem.
5. **CONTROLE-EMBARALHADO all-v10-cego + --shuffle-grid** (a âncora que
   faltou na FASE 5 A2: all-v10 com o MESMO embaralhamento das mistas —
   6ª corrida ENUMERADA por este prereg).
6. **B3.2' hold-at REPORT-ONLY** (`--hold-at 1200`, braço mista
   {composite:2,edge:8} + hold): pilha multi-composite é LIMITAÇÃO DECLARADA
   (FASE 4); medir sem gate de aprovação.
- CSVs = fonte da verdade; runs seriais; zero pool (70-79 intocado).

## 5. PROTEÇÃO v10-cego (bit-identidade)
O wiring toca SÓ o branch `--mixed` + parse_mixed (o caminho v10-cego
canônico não passa por eles). Verificação: corrida curta (1200 ticks, seed 0,
v10-cego flags canônicos) PRÉ-wiring commitada como fixture;
pós-wiring, MESMO comando → CSV bit-idêntico (teste permanente). Se
bit-idêntico impossível → paridade obs/ações ≥1000 ticks + disclose.

## 6. TESTES (suíte ESPERADA ± [N1]; base 25F/302P/3S)
+ t-mixed-parse (composite:N,edge:M parseia; soma=10; chave desconhecida rejeita)
+ t-composite-controller (ctrl_comp do --mixed: obs traffic, _composite_np
  NumpyCompositeActor com os npz do PROFILES, predict_batch produz ações
  composite com g_gate>0 em tráfego sintético)
+ t-regression-v10-cego (bit-identidade contra fixture §5)
+ t-parity-race-path (paridade NumPy↔Keras do composite sobre obs REAIS de
  corrida ≥1000 ticks — corrida curta coletando obs, comparando atores)
**ESPERADA: 25F/306P/3S ±** — desvio justificado no fechamento (cláusula N1).

## 7. ÁRVORE (ordem pinada; controle primeiro)
wiring+testes verdes → [proteção bit-idêntica] → corrida 1 (controle: regime
canônico OK? senão PARE) → 2 (B3.1') → 3-4 (mistas) → 5 (controle-embaralhado)
→ 6 (hold-at report-only) → fechamento. Qualquer FAIL → PARE (diagnóstico
marcado pós-veredito, padrão H-0). Diagnóstico permitido (R4 da
ADOÇÃO-H-2-review): evals determinísticos curtos, disclosure completo.
