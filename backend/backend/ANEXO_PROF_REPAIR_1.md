# ANEXO_PROF_REPAIR_1 — Reparo do professor: pacing pós-reentrada (opt-in) — 2026-10-22

> Ciclo PROF-REPAIR-1 · Branch `feat/sanidade-produto` · Prereg
> `backend/PREREG_PROF_REPAIR_1.md` (fc0a939, ANTES de qualquer patch/dado).
> PRIMEIRO ciclo que MODIFICA o professor. Baseline = PROF-MONACO-1
> (reuso obrigatório; aluno 45,00% canônico NÃO re-coletado).
> Orçamento cumprido: 7/7 eps (1 flag-OFF identidade + 1 flag-ON smoke +
> 5 bateria seeds 0-4); ZERO rede; ZERO corridas de produto; pools
> 70-79/76-79 VIRGENS; caches fastf1 intactos; f1_env.py:81 whitespace
> não-commitado (ruling vigente).

## 1. Cadeia
fc0a939 (prereg) → eb09171 (patch `--prof-repair` default-OFF:
ProfessorRaceController + argparse; UM fator) → cae63df/35f3baa (+2
testes; erro aritmético MEU no teste corrigido — patch correto) → 7 eps
seriais → bateria (saidas_verdict) → fechamento.

## 2. Mecanismo (R0; arquivo:linha)
- Re-entry: `race_diagnostic.py:327-364` — off-track = esterço p/
  projeção+10 m, teto 8 m/s; a transição off→on devolve o controle ao
  professor INSTANTANEAMENTE (sem settling).
- Pacing: `reference_controller.py:448-453` — `v_tgt = v_plan(s) ×
  0,93` (frozen) já no tick seguinte ao reentry → pulso de pace com o
  carro a 8 m/s na borda = mecanismo da cascata 94,6%.
- Patch: janela 5,0 s pós-reentrada; alvo = min(v_plan·0,93,
  8 + (v_plan·0,93 − 8)·elapsed/5); long_cmd com a MESMA fórmula do
  professor; esterço intocado; authority=prof_repair; UM fator.

## 3. Resultado (bateria 5 eps seeds 0-4 vs baseline canônico)
| métrica | baseline | repair | veredito pinado |
|---|---|---|---|
| **PRIMÁRIA** fora% | 56,93% | **52,47%** (−4,46pp) | **FAIL** (≥ 45,00%) |
| SEC-1 rejoin-cascata | 94,6% | **94,4%** | **FAIL** (≥ 50%) |
| SEC-2 top-1 ranking | Reta 24,4% | **C11 22,0%** (Reta 2ª, 17,1%) | **PASS** |
| SEC-3 preso acumulado | 237,0 s | **277,2 s** (+40,2) | **FAIL** (≥ 118,5; REGREDIU) |
| Bit-identidade flag-OFF | — | smoke-OFF ≡ prof_s0 BYTE | **PASS** |
| Eventos/ep | 41 | 39 | report |
| Determinismo | — | smoke-ON ≡ bateria s0; seeds 0-4 idênticos (degenerescência solo+seca) | report |

## 4. Veredito da árvore (§5 do prereg) — GAP HONESTO
- **A** (PRIMÁRIA + SEC-1..3): NÃO — PRIMÁRIA FAIL.
- **B** (SECs verdes mas fora% ≥ 45): NÃO — apenas 1/3 SEC verde.
- **C** (fora% ≥ 56,93 ou abort/instabilidade): NÃO — fora% melhorou
  e não houve abort.
O resultado cai num **GAP ENTRE B E C não previsto pela árvore** (um
melhora parcial sem SECs verdes nem regressão total). Resolução
CONSERVADORA (fail-loud; sem re-pin): **nenhum sucesso reivindicado;
o reparo NÃO é promovido; `--prof-repair` fica RESEARCH default-OFF;
o professor PERMANECE não-viável como fonte de rótulos no estado
atual; a decisão (2ª rodada de reparo × abandonar o professor) volta
ao dono com o gap quantificado: 52,47% vs 45,00% = 7,47pp residual,
cascata inalterada (94,4%), preso REGREDIU (+40,2 s)**.

## 5. Leitura mecânica (marcada; zero sims adicionais)
- **O ramp funciona como desenhado e melhora pouco**: fora −4,46pp e a
  Reta sai do top-1 (SEC-2) — mas a cascata é INALTERADA (94,4%) e o
  preso PIORA: o authority mostra o carro 97,9% do tempo entre rejoin
  (52,3%) e a janela prof_repair (45,6%), com só 2,0% de ticks em
  'professor' pleno. O carro cicla sai→volta-rampa→sai mesmo a 8-12 m/s.
- **Conclusão estrutural**: o pulso de pace NÃO é o único motor da
  cascata — a trajetória de reentrada em si (bearing à projeção+10 m,
  que em Monaco deposita o carro em ângulo incompatível com C11/C04) é
  a causa dominante. O próximo candidato natural (SÓ TEXTO; ciclo
  próprio): esterço de reentrada com alvo MAIS ADIANTE (projecão + 30-40
  m ou o ponto de curvatura mínima mais próximo) — lição FONTE-2/M2:
  ângulo raso. NÃO iteramos aqui (árvore: PARE; orçamento 7/7).

## 6. Suíte
25F/334P/3S + 2 testes novos (t_pr1_1 wiring default-OFF; t_pr1_2
rampa) → esperada 25F/336P/3S ± (ver fechamento).

## 7. Disposição
- `--prof-repair` = RESEARCH default-OFF; produto intocado; professor
  histórico bit-idêntico no default (provado).
- Zonas proibidas intocadas; A×B intocada; proposta de retreino (SÓ
  TEXTO) PREMATURA — o professor ainda não supera o aluno.
