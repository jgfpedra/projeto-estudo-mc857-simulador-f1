# PREREG_SANIDADE_1B — M3-v2 (anti-colagem com tetos por-realização) + atribuição limpa do M2

Branch `feat/sanidade-produto` · 2026-10-20 · commitado ANTES de qualquer
código/run. SEM retreino, SEM promoção, SEM flip de default, SEM re-pin
pós-número. NÃO implementar variedade/aleatoriedade neste ciclo (pedido
registrado do dono; micro-ciclo próprio depois deste).

## §0 Contexto congelado (não re-derivar)
SANIDADE-0 RATIFICADO (ANEXO_SANIDADE_0_REVIEW.md, commit 33396f6): M2
(`--rejoin perceptive`) PASS 4/4, único no `--modo espectador` (opt-in
research, não-gaitado — caveat nos helps, commit 8b95f69); M1 FAIL; M3 v1
FAIL por margens (comp 17,8 > 16,5 s; 1 deadlock s72) com ativo grande
(v0 colado −73/−60%). Âncoras F4v15 (proteção bit-idêntica): v0
3674/2482/136,0/3/22,1; comp 752/292/140/13/25,2. D0: coluna `lat` =
MÓDULO; lateral SEMPRE por slat = obs4 × half_width (hw 6,00). Pools:
70-73 consumidos; **este ciclo usa 74-75**; 76-79 intocados (76/77 só com
shift divulgado — desnecessário: scan seco). Suíte base 25F/316P/3S.

## §1 Diagnóstico D4/D5 (commit 4c7d96a; legitima os tetos)
- **D4**: FRICÇÃO INOCENTE (shove ≈ 0 em todos os braços, 0,01 e 0,05);
  BREAKER marginal (0-11 eps, 0-17,6 car·s, 0-5 excursões pós);
  **PREVENTIVO é o custo dominante** — exposição comp 194-213 car·s e a
  taxa de excursão DURANTE janela de exposição DOBRA com o preventivo
  ativo (0,144-0,169/s vs 0,077/s da ref 0,05): o offset +0,25 rad
  crônico empurra carros pra fora.
- **D5**: deadlock s72 = GAS×PIA reentrando em PARALELO — PIA seguro
  pelo gap-hold do M2 (rejoin_gap, crawl 4 m/s) e GAS 6,0 s sob o
  breaker (60 ticks anti_glue) sem separar (crawl + parceiro na borda);
  artefato da INTERAÇÃO M2×M3; breaker v1 incompetente no regime
  crawl/borda.
- Weather-scan s74/s75 (instrumento validado): **AMBAS SECAS** (s75 com
  transição v2 DRY→CLOUDY); 0/2 damp.

## §2 Mecanismo M3-v2 (substitui o v1 ATRÁS DA MESMA FLAG --anti-glue;
v1 documentado como MORTO) — TETOS POR-REALIZAÇÃO PINADOS (unidade+taxa:
tick lógico 0,1 s)
Herda do v1: fricção chassis 0,05→0,01 (mantida — inocente por D4, pin do
dono); preventivo escopado a composite/professor (race-blind preserva o
v10); breaker para todos; authority='anti_glue'; SEM colunas novas de CSV.
- **Preventivo (ii) com tetos**: offset +0,25 rad PARA FORA + th≤0,6
  quando |Δlat|<2,5 m ∧ Δs wrap<10 m, E:
  (a) **duração máx por episódio contíguo = 1,0 s** (10 ticks); após o
      teto, cooldown até |Δlat|>3 m OU 2,0 s;
  (b) **máx 10 episódios por par por corrida** (depois: hands-off);
  (c) **só com velocidade relativa |Δv| < 8,0 m/s** (parceiro em
      passagem rápida não recebe offset);
  (d) **REVERT**: preventivo inerte se o PRÓPRIO carro OU o PARCEIRO
      estiver off-track (não empurrar quem está na grama — lição D5).
- **Breaker (iii) com competência por regime** (>3 s colado,
  |Δlat|<2,5 ∧ Δs<5,5; de trás cede, empate o de fora, desempate
  driver_id):
  (a) **teto de duração 4,0 s por episódio** — sem separar, DESISTE e
      registra (não persegue separação eterna no regime crawl/borda);
  (b) **competência por velocidade**: abaixo de 25,0 m/s → lift (th=0) +
      offset 0,4 rad (v1); ACIMA → ação suave: th≤0,5 + offset 0,15 rad
      (a 60+ m/s o yank 0,4 lança pra fora);
  (c) **máx 8 episódios por par por corrida**;
  (d) **REVERT**: solta o breaking se o alvo ficar off-track.
- Professor espelha TUDO (init não chama super — espelho manual).
- Estado `_glue_state[drv]`: prev_ticks, prev_eps{par}, prev_cool,
  brk_ticks, brk_eps{par}, brk_giveup — zerado a cada corrida pelo
  construtor; INERTE com flag OFF (bit-identidade).

## §3 Critérios — RECONCILIAÇÃO SISTEMÁTICA
| critério | status | pin |
|---|---|---|
| PRIMÁRIO M3-v2 (gate) | **RE-ANCORADO** | Tempo colado (fórmula D3 exata: slat; \|Δlat\|<2,0 ∧ Δs wrap<5,5; janela contígua >2 s) de CADA corrida **comp** do gate (s74 e s75) **≤ 16,5 s** (½ × 33 s do comp seed 0 F4v15 — mesma derivação do SANIDADE-0; o "G4" do prompt = a corrida comp do gate, generalizada para as duas por honestidade de janela). |
| ABSOLUTO (todos os 7 runs) | **ABSOLUTO** | **0 deadlocks** (>10 s) em TODAS as corridas do ciclo. |
| NÃO-REG 5/5 (cada corrida de gate) | misto | contatos **< proteção da sessão** (v0 < 3674; comp < 752 — as proteções 1/2 re-medidas nesta sessão) **ABSOLUTO**; 0 paradas ≥3 s **ABSOLUTO**; 10/10 voltas **ABSOLUTO**; fora ≤ 29,9% **RE-ANCORADO** (p75 seco R12; s74/s75 SECAS pelo scan); rol ≤ 146,0 s **RE-ANCORADO** (ctrl s0 136+10). |
| hesit | **DROP (report-only)** | D3 estrutural documentado (ANTI-D3-1); coletado para o memo, sem teto. |
| colado v0 | **REPORT** | O prompt não pina teto para o braço v0 (o FAIL v1 no v0 foi o deadlock, coberto pelo ABSOLUTO); reportado com contexto v1 (66,6/99,2 vs 247). |
| SECUNDÁRIO | **disclosure-only** | Redução de contato total vs referência flags-off seed 0 — **caveat cross-seed declarado** (s74/s75 são realizações novas; comparação indicativa, não-gate). |
| ATRIBUIÇÃO M2 (não-gaitado) | **diagnóstico** | fora(M2-only comp seed 0) vs 25,2%, com **PREDIÇÃO RE-ANCORADA pré-registrada**: nº de excursões do comp flags-off seed 0 = **219** (derivado do CSV F4v15 2_allcomposite pelo sanidade_diag D2; commitado) ⇒ fora_esperado ≈ 25,2% + (1,8 s × 219)/(600 s × 10 carros) = 25,2% + 6,57 pp ≈ **31,8%**. Contatos/hesit/rol coletados p/ o memo. **Gatilho: fora(M2-only) > 29,9% → ESCALA AO DONO** (M2 pode sair do bundle — decisão do dono, não deste ciclo). |
| MISTAS | **DROP** | Fora do escopo (o prompt não as orça). |

## §4 Veredito mecânico
`scripts/sanidade1b_verdict.py` commitado **ANTES de qualquer corrida** E
**auto-validado** reproduzindo, a partir dos CSVs existentes: F4v15
(3674/2482/136/3/22,1; 752/292/140/13/25,2; excursões 180/219; colado
247/33; deadlocks 6/0) e SANIDADE-0 gates (G1-G4: cc 1380/274/1854/416;
colado 66,6/2,4/99,2/17,8; dead 0/0/1/0; exc 5,1/6,0/4,0/4,5) —
PADRÃO-OURO da review. Modo `--selftest` roda as asserções acima.

    .venv/bin/python scripts/sanidade1b_verdict.py \
      experiments/sanidade-1b/1_prot_v0.csv experiments/sanidade-1b/2_prot_comp.csv \
      experiments/sanidade-1b/3_m2only_comp_s0.csv \
      experiments/sanidade-1b/4_gate_v0_s74.csv experiments/sanidade-1b/5_gate_comp_s74.csv \
      experiments/sanidade-1b/6_gate_v0_s75.csv experiments/sanidade-1b/7_gate_comp_s75.csv

## §5 Orçamento — 7 corridas SERIAIS, ordem pinada (sequencial-puro;
args explícitos; runs≠arquivos)
1. **Prot 1**: v10-cego flags-off seed 0 → BIT-IDÊNTICO a F4v15-v0
   (3674/2482/136,0/3/22,1). FAIL = PARE, zero re-pin.
2. **Prot 2**: comp flags-off seed 0 → BIT-IDÊNTICO a F4v15-comp
   (752/292/140/13/25,2). Dupla-função: base OFF da atribuição M2.
3. **Atribuição**: comp **M2-only** seed 0 (`--rejoin perceptive`,
   `--grid f1`, sem `--anti-glue`).
4-7. **Gates M3-v2 ON com M1/M2 OFF** (isolamento do mecanismo):
   s74 v0 / s74 comp / s75 v0 / s75 comp (só `--anti-glue`).

## §6 Árvore (TODOS os ramos antes dos números)
- Proteção 1 ou 2 FAIL → **PARE imediato** (vazamento no caminho
  compartilhado); zero re-pin, zero gate.
- M3-v2: PRIMÁRIO (comp colado ≤ 16,5 nas duas corridas comp) FAIL **OU**
  deadlocks > 0 **OU** não-reg FAIL → **M3 ARQUIVADO como
  research-negative COM LEADS** (D4: preventivo como custo; D5: interação
  M2×M3; ativo v1: colado −73/−60% no v0) — `--anti-glue` volta a ser
  research default-OFF documentado; **nenhuma re-tentativa neste ciclo**.
- M3-v2 PASS → **documentado como CANDIDATO A BUNDLE** (promoção =
  decisão do dono em ciclo próprio; nada promovido aqui).
- Atribuição: fora(M2-only) > 29,9% → **ESCALA AO DONO** (M2 pode SAIR
  do bundle; decisão do dono); ≤ 29,9% → M2 permanece com dado limpo no
  memo (predição 31,8% vs teto 29,9: a predição DIZ que a escala é o
  desfecho provável — registrar e escalar honestamente).
- **Sem re-pin pós-número; sem re-run orçamentário; zero promoção.**

## §7 Suíte
Base 25F/316P/3S + testes novos dos tetos: **ESPERADA 25F/322P/3S ±**
(6 testes novos: preventivo teto-1s+cooldown; contagem 10/par; gate
|Δv|<8; revert offtrack; breaker 4s+desistência+competência-v; contagem
8/par + espelho professor). Cláusula ±: desvio justificado no fechamento.

## §8 Regras herdadas
Probes commitados antes de cada uso (nunca inline); veredito-antes-dos-
números; shell args explícitos; pins com unidade+taxa; corridas NUNCA em
paralelo; diagnóstico read-only permitido pós-veredito (marcado); zero
variedade/aleatoriedade; mirrors/loader/fastf1 intocados; canônico R13
(v10-cego default) intacto; 76-79 intocados.
