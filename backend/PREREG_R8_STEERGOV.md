# PRÉ-REGISTO R8 — STEER-GOVERNOR (camada de corrida OPT-IN)
# REGRA NOVA (achado 9099235): medição sem commit não existe.
# Este arquivo + o código + os testes são commitados ANTES do primeiro run ON.

## CAUSA (R7b, fechada)
Física lateral SÃ (scripted: círculo estável até v_allow, misalign 0,3°;
understeer 1,45-1,6× calibrado no grip 0,788). Saídas: comando da política
~24× a necessidade cinemática → guinada+slip sem curvatura (a_lat 3,9-5 vs
10,4 m/s²; slip 16,8°). Bandas: κ<0,005 (weave reta) + 0,008-0,015 (entradas)
= 74%. DAgger REJEITADO como trilha primária (retreinos v14b/c/d: 2/3→1/5→0/3);
precedentes de camada: governor vplan (137→103s), rejoin bearing R3.

## PASSO 0 (dados R7a, zero runs) — FECHADO
- 0.2: 97% (894/924) das saídas pilots têm |δ| > cap(2,0×atan(L·κ@10m)) no
  cruzamento (δ/cap mediana 11,6×) → PORTA DE SAÍDA PASSOU.
- 0.3(a): CAP-ONLY. Só 14/924 (1,5%) têm herr>20° com δ≤cap (heading já
  torto antes do cruzamento) — minoria documentada; o rejoin bearing (R3)
  já cobre o estado pós-cruzamento. Banda de heading NÃO implementada.
- 0.3(b) PROPOSTA de critério wanderer p/ o gate de produto (fase de gate,
  aprovação própria): mediana de wanderers(>60 s) por seed = 0 e nenhum
  seed com >3 episódios (distribuição R7a: seeds 0-7 têm 0-1; 8-9 têm 4-15).
- 0.1: 2160 episódios = 2134 rápidos (bearing rejoin FUNCIONA) + 26
  wanderers + 1092 churn encadeado (sai-volta-sai ≤10 s) — o cap ataca a
  RAIZ (a saída inicial) e por consequência o churn.

## COMANDOS (UMA flag de diferença)
- OFF (baseline R7a, CSVs EXISTENTES — não re-rodar):
  `.venv/bin/python model_train/race_diagnostic.py --profile composite --ticks 6000 --laps 99 --track interlagos --seed {N} --gov vplan --variance grid,compound --out race_diag_r7a_disp_s{N}.csv`
- ON (idem + UMA flag):
  `.venv/bin/python model_train/race_diagnostic.py --profile composite --ticks 6000 --laps 99 --track interlagos --seed {N} --gov vplan --variance grid,compound --steer-gov cap --out race_diag_r8_on_s{N}.csv`
- NÃO-INVASÃO (1.3): idem OFF seed 0 → bit-idêntico a
  race_diag_r7a_disp_s0.csv (hash das colunas de métrica, CSV v3.2).

## CONSTANTES PINADAS (dos dados R7a/R7b; PROIBIDO ajustar contra seeds de confirmação)
- k_comp = 2,0 — cobre o understeer sistemático 1,45-1,6× com margem e
  bloqueia a cauda 5-24×; abaixo disso o cap normalizaria curvas legítimas.
- κ_preview = κ@10 m (canal obs10/25 — MESMO preview do governor vplan e do
  rejoin; precedente de lookahead da R3). L (wheelbase) = 3,4 m.
- CAP: |δ| ≤ cap = 2,0 × atan(3,4 × κ@10m). Hairpin κ=0,12 → cap = 0,77 rad
  ≈ STEER_MAX (0,785) → hairpins LEGÍTIMOS não são clipados (teste unitário).
- Autoridade: o cap atua SÓ no comando da POLÍTICA (neural/composite),
  ANTES da composição de controles. O rejoin bearing (R3) SOBRESCREVE o
  esterço depois e é ISENTO do cap; recovery/blocked não tocam esterço.
  Professor NÃO é afetado (seu esterço é geométrico pure-pursuit).
- Default: OFF (bit-reproduzível como R7a — prova 1.3).

## INSTRUMENTO (antes de interpretar — lição FASE 1)
- Coluna `steer_gov_active` por carro-tick (1 = clipado neste tick).
- Resumo por corrida: steer-gov% (ticks on-track clipados) e por banda de κ.
- VERIFICAR no piloto: o cap DISPARA nas bandas dominantes ANTES de ler fora%.

## PREDIÇÕES (registradas antes dos números)
1. Exits evitados: UPPER BOUND 97% dos pilots (contrafactual 0.2); esperado
   realista: as bandas dominantes (74% da massa) caem substancialmente.
2. fora% mediano pareado (N=3, seeds 0-2): OFF mediana ~29,7 → ON < 20%.
3. Teto de degradação de rolante: ON ≤ OFF_pareado + 10 s (racional: o cap
   só atua em comandos 5-24× — o custo é a perda de correções fortes em
   estados reais de recuperação, minoria).
4. DISCIPLINA: cap ativo em ≤0,5% dos ticks ON-TRACK de volta limpa nos runs
   ON. Se >0,5%: PARE — re-derivar constantes dos dados, sem piloto.
   (Análise nos CSVs do piloto — zero runs extras.)
5. Wanderers: sem mudança esperada (26/10 seeds; a causa deles é fling
   pós-contato — fora do escopo do cap).

## ÁRVORE DO PASSO 2 (piloto pareado N=3, seeds 0-2)
| resultado | ação |
|---|---|
| VERDE: fora% ON<OFF em 3/3 E rolante ON ≤ OFF+10 s E 10/10 voltas E disciplina ≤0,5% | → PASSO 3 (N=10) |
| MISTO: fora melhora mas pace degrada além do teto, ou seeds divididos | diagnóstico por banda; UMA revisão de constante SÓ contra seeds 0-2; re-piloto; confirmação com seeds NUNCA usados p/ ajuste |
| VERMELHO: fora não melhora | PARE com diagnóstico; DAgger volta à fila como proposta |
| disciplina >0,5% em solo limpo | PARE: re-derivar constantes, sem piloto |

## LIMITAÇÕES
- Contrafactual 0.2 é UPPER BOUND (não simulação) — a verdade só o piloto mede.
- Fronteira skidpad medida só ≤16 m/s; micro-mecanismo do understeer 1,45×
  aberto (fora de escopo).
- 14 saídas com herr>20° + δ≤cap não são endereçadas pelo cap-only.
