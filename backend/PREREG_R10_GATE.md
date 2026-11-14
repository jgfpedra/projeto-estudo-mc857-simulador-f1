# PRÉ-REGISTO R10 — GATE DE PRODUTO COMPARATIVO (composite × v10-cego, N=10 pareado)
# REGRA: medição sem commit não existe — este prereg + o script de veredito
# são commitados ANTES de qualquer run do braço B. Regra R9: toda checagem
# que pode falhar tem ramo próprio abaixo.

## 0.1 — BRAÇOS (UMA diferença: ator/perfil; todo o resto idêntico)
- **Braço A (CANDIDATO, composite)**: os 10 CSVs R7a EXISTENTES
  (`race_diag_r7a_disp_s{0..9}.csv`, + `_events.csv` + `.log`) — NÃO re-rodar
  (não-invasão OFF≡R7a provada na R8, bit-idêntica).
- **Braço B (INCUMBENTE, v10-cego)**: 10 runs NOVOS, SEQUENCIAL-PURO
  (proibido paralelo), seeds 0-9, mesmos flags trocando APENAS o ator:
  `.venv/bin/python model_train/race_diagnostic.py --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed {N} --gov vplan --variance grid,compound --out race_diag_r10_blind_s{N}.csv`
- SMOKE antes da cadeia (30 ticks, seed 0): MARCADOR DE SUCESSO ("linhas ->")
  + cabeçalho FONTE conferido (ator dagger_actor_best/edge, gov=vplan,
  variance=grid,compound, sha256 pista 164876196eb12174, SF 729).
  RAMO: smoke falha → corrigir ANTES da cadeia (não prosseguir).

## 0.2 — MÉTRICAS por braço/seed (tabela POR SEED; deltas pareados + mediana; SEM pooling)
- cc = pares-tick únicos c/ impulso do solver (events CSV; instrumento v3).
- pós-60s = pares-tick c/ impulso em t>60 s.
- paradas ≥3 s = do log da corrida ("TOTAL: N paradas"; "nenhuma" = 0).
- fora% = 100×média(offtrack).
- wanderers = nº de CARROS com ≥1 episódio off-track >60 s na corrida.
- preso = nº TOTAL de episódios off-track >60 s.
- rolante = mediana dos tempos de volta (cruzamentos de SF s=2655, 5 Hz).
- hesitações = episódios v<0,5 m/s de 0,3-3 s, t>20 s (definição R3).

## 0.3 — REGRA DE DECISÃO (lexicográfica, MECÂNICA, pinada antes dos números;
##        calculada pelo script commitado `scripts/r10_gate_verdict.py`;
##        PROIBIDO veredito à mão). Deltas PAREADOS por seed (A−B), mediana dos deltas.
- **D1 SEGURANÇA (bloqueante)**: mediana(cc_A) < mediana(cc_B) E
  mediana(pos60_A) ≤ mediana(pos60_B) E paradas_A (todas as seeds) = 0.
- **D2 PISTA (bloqueante)**: mediana(fora_A) ≤ mediana(fora_B) + **10 pp**
  (tolerância MÁXIMA; racional de produto: o composite compra segurança
  com pilotagem — a revisão autorizou até 10 pp de fora adicional) E
  mediana(wanderers_A) ≤ mediana(wanderers_B) E mediana(preso_A) ≤ mediana(preso_B) + 5.
  (O critério wanderer ABSOLUTO — mediana 0/seed, nenhum seed >3 — é meta do
  backlog PÓS-gate, NÃO bloqueador deste gate.)
- **D3 PACE (bloqueante)**: mediana(rolante_A) ≤ mediana(rolante_B) + **15 s**
  (tolerância máxima; racional: o valor de produto do composite é a redução
  de contatos; o pace já é 158 s vs 115 s do regime pré-canônico — a
  comparação é RELATIVA ao incumbente no MESMO instrumento) E
  mediana(hesit_A) ≤ mediana(hesit_B) + 3.
- **VEREDITO**: D1 ∧ D2 ∧ D3 → PROMOÇÃO PROPOSTA (alias race → composite;
  executada SÓ após aprovação da revisão). Qualquer D falhando →
  MANUTENÇÃO do v10 + composite research-grade, com a dimensão falha
  documentada como limitação de produto.

## RAMOS PARA CHECAGENS QUE PODEM FALHAR (regra R9)
| checagem | ramo |
|---|---|
| smoke B sem marcador/cabeçalho errado | corrigir antes da cadeia |
| CSV B sem colunas v3.2 (w_kind/tyre/imp) | veredito PROIBIDO até entender; reportar |
| colunas dos braços incompatíveis | veredito PROIBIDO; reportar |
| algum run B crasha | re-rodar o seed isolado 1×; segunda falha → PARE |
| eventos CSV ausente em B | o coletor é default-on desde R5a — ausência = bug; PARE |
| mediana empatada em D1 (cc) | trata-se de "não estritamente melhor" → D1 FALHA (regra estrita) |

## 0.4 — LIMITAÇÕES pré-declaradas
- Slip é regime de operação, não sintoma (R9); fronteira skidpad medida ≤16 m/s;
  micro-mecanismo do understeer 1,45× aberto.
- O braço A não inclui --steer-gov (default OFF; nada adotado) — idem B.
- Métricas de contato pelo instrumento v3 (solver, sub-step) nos DOIS braços.

## PASSO 3 — APÊNDICE (zero runs, SEM impacto no gate)
Assinatura de 2ª ordem (janela deslizante): features = offset sustentado
(mediana |δ| da janela), yaw crescente (Δheading/Δt), curvatura de caminho
baixa (|Δdireção-vel|/Δt) — separa ticks normais de janela pré-saída sob a
metodologia R9 (denominador completo + lead)? Veredito: separa/não separa.
Alimenta a fila pós-gate (DAgger weave/slide). RAMO: se o script do
apêndice falhar tecnicamente → apêndice declarado INCONCLUSIVO (não bloqueia
o gate; reportado).
