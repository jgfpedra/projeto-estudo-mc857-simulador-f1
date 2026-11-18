# PRÉ-REGISTO — ANTI-D3-1: progress-guard com fade gate→base (hesitações do composite)
# Commitado DEPOIS do diagnóstico (P1) e ANTES da implementação. ZERO retreino,
# ZERO dataset, ZERO re-pin de pesos, ZERO mudança de default (promoção = dono).
# Pool 70-79 INTOCADO; mirrors/loader/v1s/fastf1 ==3.8.3 INTOCADOS.

## §Mecanismo (UM, pinnado pelo diagnóstico P1)
**PROGRESS-GUARD COM FADE GATE→BASE**: no caminho composite do
predict_batch, por carro — se o gate g estiver aberto (>g_min) e o carro não
progredir (Δcum_dist < 0,5 m) por **N=5 ticks** consecutivos, o g EFETIVO
esmaece linearmente até 0 em **F=5 ticks** adicionais (o gate nominal segue
como instrumento; o g_eff é o que multiplica r). Retoma (g_eff volta a 1)
quando Δcum_dist ≥ 0,5 m em um tick. Estado por driver no próprio
controller. Justificativa (P1): 13/13 hesitações são residual-brake
dead-stop com gate PERSISTENTE — o fade devolve o comando à base (v10 solo)
que retoma sozinha; ataca exatamente o modo medido, não o gate em si.
- Fallback de IMPLEMENTAÇÃO apenas: se o cum_dist do CSV não estiver
  disponível no predict_batch, usar Δs (wrap corrigido) — documentado.
- RISCOS: se o carro à frente estiver PARADO e a base retomar, pode gerar
  aproximação → os critérios de contatos pegam.
- NÃO-mecanismos (descartados pelo diagnóstico): EMA no g (gate não é
  chattering); histerese (idem); V_MIN floor (maior-risco de contato — só se
  o guard falhar, ciclo futuro).

## §Escopo do toque
ÚNICO arquivo: `scripts/run_race_10_cars.py` — bloco composite do
predict_batch (linhas ~750-790: onde g é calculado; adicionar o quench +
g_eff). O caminho v10-cego NÃO passa pelo bloco (exige `_composite_np` set)
— mas compartilha o ARQUIVO: a proteção dupla pega qualquer vazamento.

## §Critérios (RECONCILIAÇÃO SISTEMÁTICA — status por critério, ANTES dos runs)
| critério | status | derivação/valor |
|---|---|---|
| PRIMÁRIO: hesit composite ≤ controle da MESMA sessão | RE-ANCORADO | B3' mediu controle=3 sob canônico (não o 0 pré-canônico); a barra honesta é igualar o controle da mesma sessão |
| Não-reg: contatos < controle da mesma sessão | RE-ANCORADO | 752 é referência, não limiar; barra relativa |
| Não-reg: 0 paradas ≥3s (v<0,5) | ABSOLUTO | parada nunca é aceitável no seco |
| Não-reg: 10/10 ≥1 volta | ABSOLUTO | idem |
| Não-reg: fora ≤ 29,9% | RE-ANCORADO | mesma derivação B3' (p75 seco braço A, R12 0.6) |
| Não-reg: rolante ≤ controle mesma sessão +10s | RE-ANCORADO | idem B3' |
| Critérios de MISTAS | **DROP** | fora do escopo; voltam no ciclo de re-decisão de promoção |

## §Proteção dupla
1. **Bit-identidade v10-cego vs fixture 1200 ticks** (teste permanente)
   DEVE ficar verde (o caminho canônico não passa pelo bloco).
2. **CONTROLE re-run BIT-IDÊNTICO à FASE-4-v15**: cc=3674, pós-larg=2482,
   rol=136s, hesit=3, fora=22,1% — se NÃO reproduzir bit-a-bit → algo vazou
   no caminho compartilhado → PARE imediato, sem ler mais nada.

## §Veredito mecânico
`scripts/anti_d3_verdict.py` — commitado ANTES das corridas (PADRÃO-OURO
OBRIGATÓRIO); lê os CSVs, emite PASS/FAIL por critério + veredito global;
números humanos não entram.

## §Orçamento (2 corridas seriais, seed 0 DRY, 600s, args EXPLÍCITOS)
1. CONTROLE (v10-cego, flags canônicos) — PRIMEIRO.
2. ALL-COMPOSITE (`--profile composite`) com o mecanismo.
Nenhuma outra corrida gated. Diagnóstico pós-veredito só MARCADO.

## §Árvore de decisão (ambos os ramos ANTES dos dados)
- PRIMÁRIO PASS + não-regressão verde → ciclo fecha BEM; fila =
  re-decisão de promoção (dono) com re-cheque de mistas.
- PRIMÁRIO PASS + não-regressão FAIL → PARE com trade-off divulgado (dono).
- PRIMÁRIO FAIL → D3 é estrutural à camada → PARE; re-decisão A×B com D3
  como custo permanente.
- Em NENHUM ramo este ciclo promove default.

## §Suíte ESPERADA ± (N1)
Base 25F/305P/3S + testes do mecanismo (~4: quench dispara após N ticks sem
progresso; g_eff esmaece linearmente; retoma com progresso; v10-cego não
afetado pelo estado) → **ESPERADA ~25F/309P/3S ±**; desvio justificado no
fechamento. Diagnóstico PERMITIDO (R4): corridas curtas determinísticas com
disclosure.

## §PAREs
Re-pin/re-run pós-número; retreino; pool 70-79; fastf1; mirrors/loader/v1s;
corrida antes da proteção verde; mudança de default (promoção = dono);
chains com variável não-quotada (args explícitos).
