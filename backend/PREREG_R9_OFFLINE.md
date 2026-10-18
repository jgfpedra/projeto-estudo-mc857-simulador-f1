# PRÉ-REGISTO R9 — FALSIDICAÇÃO OFFLINE dos candidatos de camada (PASSO 0)
# Commitado ANTES da análise (regra R8: medição sem commit não existe).
# Corpus: 10 CSVs R7a OFF (race_diag_r7a_disp_s{0..9}.csv) + 10 CSVs R8 ON
# (race_diag_r8_on_s{0..9}.csv) + tabelas r7b_exits_analysis/r8_passo02.
# LIÇÃO R8 ELEVADA A REGRA: contrafactual de evento é NECESSÁRIO mas
# INSUFICIENTE — toda alegação "evitaria X%" vem com (i) denominador de
# distribuição COMPLETA (ticks on-track normais clipados) e (ii) lead time
# (lição do absorvedor R3: reagir depois é não reagir). Viabilidade decide
# NO OFFLINE; o piloto só confirma o que o offline prediz.

## DEFINIÇÕES COMUNS
- slip por tick: ângulo entre heading do carro e direção da velocidade,
  derivado de (s, lat) consecutivos + obs5/obs6 + heading da pista
  (mesma fórmula da análise R7b 1.3; 5 Hz).
- "ticks normais" = on-track (offtrack==0) que NÃO precedem saída
  (excluída a janela de 30 ticks antes de cada cruzamento).
- "janela pré-saída" = 30 ticks (3 s) antes do cruzamento (tick0 da saída).

## 0.1 — CALIBRAÇÃO DO MOTOR (obrigatória, antes dos candidatos)
Reproduzir a coluna steer_gov_active dos CSVs R8 ON a partir dos canais do
próprio CSV (cap = 2,0×atan(3,4×obs10/25); ativo se |steer_rad| ≥ cap−1e-6,
pois o valor logado é PÓS-clip). Critério pinado: concordância por tick
≥99% em CADA seed (esperado ~100% — o cap é determinístico nos canais).
NOTA DE HONESTIDADE: isto valida o MOTOR NA TRAJETÓRIA DADA; a suficiência
dinâmica (clipar muda a trajetória seguinte) só o piloto mede — a análise
offline é CONDIÇÃO NECESSÁRIA, não suficiente.

## 0.2 — CANDIDATO A: cap condicionado a slip (clipar |δ| só com |slip|>θ)
Forma: se |slip|>θ, clipar |δ| ≤ cap_A = k_A × atan(L × κ@10m).
- θ candidatos PINADOS: {5°, 10°, 15°} (sintoma real: slip 16,8° mediano
  nas saídas, 65% >10°).
- k_A PINADO: 3,0 (gerosa que 2,0 da R8 — o slip-condiciona restringe a
  população; se nem 3,0 passa, valores maiores perdem o sentido de cap).
- DISCIPLINA (limiar pinado): fração de ticks NORMAIS clipados ≤ 0,5%.
- LEAD TIME (limiar pinado): para cada saída, o PRIMEIRO tick na janela
  pré-saída com (|slip|>θ E |δ|>cap_A); lead = nº de ticks antes do
  cruzamento. MORTO SE: mediana do lead < 5 ticks (0,5 s) — tarde demais.
- COBERTURA (limiar pinado): ≥50% das saídas com janela acionável
  (≥1 tick de lead com a condição ativa).

## 0.3 — CANDIDATO B: limitador de taxa |δ̇| ≤ ρ
- δ̇ por tick = Δδ/Δt (5 Hz) por carro.
- ρ candidatos PINADOS: quantis {99,5%, 99,9%} de |δ̇| nos ticks NORMAIS
  (o próprio ρ nasce do denominador completo, não de eventos).
- DISCIPLINA (pinado): por construção ρ no quantil q clipa (100−q)% dos
  ticks normais — usar ρ(p99,9) ⇒ disciplina 0,1% inerente; ρ(p99,5)
  ⇒ 0,5% (no limiar).
- SEPARAÇÃO (critério de morte pinado): na janela pré-saída, fração de
  saídas com |δ̇| > ρ ANTES do cruzamento. Se o comando gerador é OFFSET
  SUSTENTADO (não yank), a taxa não separa → MORTO com o número:
  declare-se morto se <30% das saídas têm rate-spike pré-cruzamento.
- Lead time idem A (primeiro tick com |δ̇|>ρ; mediana ≥5 ticks).

## 0.4 — CONSIDERADO E DESCARTADO (sem análise de pormenor)
Cap forma círculo-de-atrito (δ ≤ L·a_max/v²): sem poder de separação POR
CONSTRUÇÃO — as saídas acontecem com a_lat 3,9-5 m/s² ABAIXO do limite
(R7b: só 18% estouram a fronteira); o comando impossível é absorvido pelo
understeer sistemático (1,45-1,6×). Clipar por círculo-de-atrito não
alcança o mecanismo (guinada sem curvatura a a_lat sub-limite).

## 0.5 — ÁRVORE (pinada antes dos números)
| resultado | ação |
|---|---|
| ≥1 candidato viável (disciplina ≤0,5% E lead med ≥5 ticks E cobertura ≥50%) | PASSO 1 com o(s) viável(is) — piloto condicional |
| ambos mortos | PARE: família camada ENCERRADA formalmente; revisão decide DAgger weave/slide (pré-gate professor + âncora solo; risco v14b/c/d) vs gate-first (re-ancoragem + promoção com limitação documentada) |
| viável mas lead curto | morto por atraso (lição R3) — tratar como morto |

## LIMITAÇÕES PRÉ-DECLARADAS
- Slip derivado de projeção 5 Hz (não é estado do solver); ruído em baixa
  velocidade — ticks com v<3 m/s excluídos do slip (declarado na análise).
- Contrafactual = condição NECESSÁRIA (motor na trajetória dada); a
  suficiência dinâmica é do piloto.
- Fronteira skidpad ≤16 m/s; micro-mecanismo do understeer 1,45×: abertos.
