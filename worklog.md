# worklog.md — log de trabalho por tarefa (append por sessão; Task ID por entrada)

> Convenção: cada entrada = uma task concluída (ou PARE), com commits,
> vereditos e pendências. Estado canônico do projeto: `backend/PROJECT_STATE.md`.
> Rulings da revisão REVALIDA-0 chegaram via prompt LARGADA-0 (aplicadas e
> registradas no commit f801d09): alavanca rejoin X=20 OPT-IN as-is; sem flip
> de default, sem flag clima-dependente, sem re-pin do regime canônico; fb
> janela/T_max = pré-condição de promoção; LARGADA abre com ANATOMIA.

# Task ID: LARGADA-0 (2026-10-19) — ANATOMIA OFFLINE da largada (zero corridas)

## Commits
f801d09 (L-0-doc: disposição final da alavanca + MEMORY.md) → 071bc37 (prereg
da anatomia, ANTES do script; P-B emendado p/ s∈[2650,2950] com âncoras
citadas) → 056421c (script + âncoras + fechamento).

## Fechamento de registro (V)
- V-1: GUARD-L do C' = **135,0** (mediana das medianas; máx 136) — o "135" do
  relatório confirmado; SEM errata (≤141, veredito imune).
- V-2: GUARD-V do D 3/3 PASS (n_comp 10 = hist 10 por seed).
- V-3: SELF do D 3/3 PASS quantificado: 9-10 carros/run com hold, margem
  mínima 1º hold − 1ª reentrada = **0 ticks** (engaje exato), 0 violações.

## Anatomia (SELF-checks 3/3 PASS; instrumento scripts/largada_anatomy.py)
- 1ª excursão: **20/20 em W** (t 4,2-8,4 s) e **20/20 na 1ª curva**
  (s 2699,7-2814,0, entrada do Senna S pós-SF) — P-A e P-B PASS com folga
  (região literal do prompt [550,850]: 0/20, como documentado na emenda).
- **Taxonomia: 20/20 CONTATO-ADJ** — toda primeira excursão tem contato do
  dono em ±2 s; 12-23 pares de contato por run na janela; primeiros contatos
  JÁ NO GRID (t 1,2-1,4 s, s 2618-2656).
- Dinâmica do campo (insumos): v média 14,5 (t=2) → 28,7 (t=4) → 10-17
  (t=8) m/s; compostos por fileira no CSV âncora.
- **P-C FAIL: share_largada mediana 0,074** (0,021-0,115) vs ≥0,20 pinado.
  A janela de largada detém só ~7% do TEMPO fora. **PARE pela árvore
  preregistrada: a premissa "maior fonte única" (em tempo-fora) CAIU →
  re-prioritização com a revisão ANTES de qualquer L-1.**

## Re-atribuição (obrigatória, registrada)
A derivação original do P-C (contaminado 10-15% fora vs histórico 17-26% ⇒
largada ≈ 1/4-1/2 do fora) confundia o efeito-largada LOCAL com a CASCATA
completa — o híbrido contaminado também carregava o bug de keying. O que
permanece verdade: a largada é um evento de CONTATO concentrado (grid +
Senna S), 100% CONTATO-ADJ. O anexo CONTAMINADO (11 runs, insumo de design)
mostra o launch-hold empurrando a 1ª excursão para t=32,6 s (modo exato
10/10) — mas a atribuição do restante da diferença de fora% (−7-11 pp)
permanece confundida.

## Pendências para a revisão
1. Re-prioritização do CICLO LARGADA com os números CORRETOS: teto de um
   pacing sobre tempo-fora ≈ 7% (janela) + cascata indeterminada; a queixa
   original (1ª curva) é de CONTATO, não de tempo-fora — o candidato natural
   migrou de "pacing" para "espaçamento/ordem de largada + pacing de
   aproximação à 1ª curva".
2. Proposta L-1 (SÓ TEXTO, no relatório da sessão): mecanismo, guards,
   pool 50-59 com weather scan declarado ANTES (lição 30-39), mecanismo
   NÃO pode ler clima no runner (lição GUI≠headless).
3. Zero corridas gastas; suite inalterada; pools intactos.

# Task ID: LARGADA-1 (2026-10-19) — DECOMPOSIÇÃO + PREREG L-1a + GATE: FAIL (falsificação limpa)

## Commits
fc5752b (0-a erratas E1/E2) → c848d6e (0-b doc-integrity test; suite 25F/284P/2S) →
82b12c6 (0-c decomposição: ENTRADA-S 228/348=65% dominante → árvore CAP; adjacentes à
1ª exc 20/20 ENTRADA-S, 0 no grid; 1ª exc por posição P2 6×, não P1; cc hist SECA
med 2.906 / DAMP med 3.500) → scan 50-59 commitado (1/10 DAMP: s50 → WET na v5) →
a3b8ff0 (prereg L-1a: k=0,8/s_cut=2950/T_max=30 PINADOS com derivação medida —
v_plan real 20,3-57,1 na janela vs chegada medida máx 48,4) → d81b842 (launch-cap
+ 5 testes) → 4b0d4eb (reparo do smoke: FLAG FANTASMA off-track — 3 violações de
fase; gate `not offtrack`, mudança de comportamento ZERO, +t6) → 7f10fb0 (veredito
do gate commitado ANTES dos números; +fix de glob _events) → fechamento.

## Instrumento e smoke
--launch-cap: v_ceiling = 0,8×v_plan(s) na janela t<30 E s<2950; freio do governor
(zero constantes novas); default OFF (drift base≡hist 0/30000); telemetria per-carro
(lição stale-drv). Smoke v1: (1) 1ª divergência == 1º cap (tick 48, HAM na
aproximação) PASS; (2) fase FAIL — 3 violações, todas carros OFF-TRACK na janela
com authority 'rejoin' (o rejoin SOBRESCREVE th/brk → flag fantasma; v_plan é plano
on-track) → reparo `not offtrack` (mudança ZERO) + t6 → re-smoke SELF 3/3 PASS
(112 cap-ticks reais em 10 carros). Suite final esperada 25F/290P/2S (+1 t6 vs
prereg — teste do reparo, padrão REPARO).

## GATE (11 runs: base s50 + 10 tratamentos 50-59; identity launch_cap=True 10/10)
**FAIL MECÂNICO** (veredito 7f10fb0):
- PRIMÁRIO-1: pares_W mediana 18 (máx 24) vs ≤8/≤14 — o cap NÃO reduziu o storm
  (âncora 12-23, med 17).
- PRIMÁRIO-2: 1/10 (s54 OUTRO@9,6 s); 9/10 ainda CONTATO-ADJ em 4,4-9,6 s.
- NÃO-REG: secas rolante 132-138 ✓, par/wand 0/0 9/9 ✓, GUARD-V 10/10 ✓;
  s50 (WET) PIORA: par 22 vs base 12, cc 10.872 vs 8.258 (+31%); s58 cc 3.400>3.197.
- EXPECTATIVA (report-only): fora% <15 em 0/10 → **o efeito da era contaminada era
  ARTEFATO DO KEYING (E1 confirmado por medição), não pacing**; secas 20,9-26,7.

## Diagnóstico (falsificação limpa)
O cap ENGAJOU de verdade (74-137 cap-ticks/run em 10/10 carros; fase 0 violações)
e NADA mudou no desfecho: a hipótese "velocidade de chegada causa o storm" está
REFUTADA — a compressão vem do FUNIL do próprio v_plan (todos freiam no mesmo
ápice; um fator uniforme 0,8× preserva a geometria relativa do campo). Em úmido o
cap PIORA (campo mais lento = mais compactado: s50 par 22 vs 12).

## Estado
Launch-cap = research-negativo documentado; flag PERMANECE default OFF. SEM
re-pin, SEM re-run. A fila da largada volta ao DONO: (a) mudança de GRID
(espaçamento/fileiras — era nova com re-pin total; 112 pares de grid + o storm
de entrada-S persistem); (b) aceitar o launch-storm como teto documentado.
Pools: 50-59 consumidos; 60-69 próximo virgem. 13 runs gastas (o cabeçalho do
prereg dizia 12 — slip aritmético; a sequência §4 está correta).

---

Task ID: LARGADA-0-review
Agent: orquestrador (Z.ai)
Task: Auditar LARGADA-0 (V-1/2/3; L-0-doc f801d09; prereg 071bc37 com emenda P-B
documentada; anatomia SELF 3/3; P-A/P-B 20/20; P-C FAIL 0,074 → PARE) e decidir a
re-prioritização.

Work Log:
- Cross-check aritmético CONFERE: mediana pooled 0,074 exata; décadas 0,0725/0,075;
  máx 0,115 < 0,20 (FAIL limpo); s 2699,7-2814,0 ⊂ [2650,2950] e ⊂ cluster 0-d
  [2698,2814] (reprodução independente); VER 7/20 confirmado; grid s 2618-2656 ≤ SF;
  suite inalterada 25F/283P/2S.
- ERRATA do orquestrador: o âncora "s≈685m" do prompt era leitura errada do registro
  "(RUS,4,2s,2702,685m)" — o valor é s=2702,685 m. Emenda do ajudante RATIFICADA
  (legítima, não-gateável).
- V-1/V-2/V-3 RATIFICADOS (GUARD-L 135,0/ máx 136; GUARD-V D 3/3; SELF D 3/3 margem
  0 ticks = fase perfeita).
- P-C PARE ACEITO: a premissa caída era do orquestrador (herdava a atribuição
  confundida da era REPARO — 6-11pp ≠ efeito local; híbrido tinha bug de keying +
  cascata). ERRATA E1 exigida no PROJECT_STATE.
- RE-PRIORIZAÇÃO: dossiê CONTINUA com alvo REDEFINIDO = CONTATOS de largada (pares_W
  12-23, med 17,0; 20/20 CONTATO-ADJ; 1ª exc 20/20 entrada-S; grid t≈1,2s), não
  fora%. Ordem por decomposição: entrada-S → L-1a CAP; grid → PARE-report (era = 
  decisão do dono).
- ESTRUTURAL: worklog do repo = canônico (reviews do orquestrador apendadas lá);
  mishap de header 2× → teste doc-integrity obrigatório.

Stage Summary:
- LARGADA-0 RATIFICADO: queixa original = cascata de CONTATO do grid à entrada do
  Senna S (20/20), com janela detendo só 7,4% do tempo fora. Alvo redefinido;
  LARGADA-1 emitido (decomposição → CAP ou GRID; pool 50-59 após scan).

---
Task ID: LARGADA-1-review (decomposição 0-c ratificada + GATE L-1a FAIL ratificado por falsificação limpa + contabilidade corrigida + fila devolvida ao dono com recomendação)
Agent: orquestrador (Z.ai)
Task: Ajudante executou o PROMPT LARGADA-1: erratas E1/E2 (fc5752b); doc-test com expectativa pinnada (c848d6e, regex do próprio teste bugado → fix+amend, 25F/284P/2S); decomposição 0-c (82b12c6: ENTRADA-S 228/348=65% dominante → árvore CAP; adjacentes à 1ª exc 20/20 ENTRADA-S, 0 no grid); scan 0-d (1/10 DAMP s50 → base fresca exigida); derivação com v_plan REAL do runner (kwarg errado → construtor exato grip 0,788/sf 0,80); prereg a3b8ff0 (k=0,8/s_cut=2950/T_max=30) ANTES do código d81b842; smoke v1 pegou FLAG FANTASMA (3 violações de fase: carros off-track com rejoin sobrescrevendo th/brk) → reparo `not offtrack` comportamento-ZERO + t6 (4b0d4eb) → re-smoke 3/3; veredito commitado ANTES dos números (7f10fb0); GATE 11 runs FAIL mecânico → PARE; fechamento f1ebccd. Pediu: ratificação + decisão de fila (grid-era vs teto).

Work Log:
- Revisão de papel (sem repo — sandbox do ajudante é separado, como nos ciclos anteriores): relatório vs prereg a3b8ff0 (texto integral na mensagem) vs âncoras LARGADA-0 (worklog/071bc37).
- Cross-check aritmético TUDO CONFERE (script review_lg1_arith.py): decomposição 228+112+8=348, 65,5%/32,2% ✓; cap constants = 0,8×v_plan exatos nos 6 pontos (45,6/36,5/27,4/16,2/26,8/35,3) ✓; PRIMÁRIO-1 FAIL duplo limpo (med 18>8, máx 24>14; folga 10/10, sem knife-edge; trat 18 ≈ âncora 17 → cap não moveu o desfecho) ✓; PRIMÁRIO-2 1/10 < 7/10 (e t máx 9,6 nem chega perto de 12,4) ✓; s50 cc 10.872/8.258 = +31,7% e par 22>12 ✓; s58 cc 3.400 > 3.197 (= 2.906×1,1) ✓; rolante 132-138 ≤ 141 ✓; fora secas 20,9-26,7 ≤ 28,3 ✓; s50 fora 46,6 vs base 46,5 = clima (pareio damp correto) ✓; suite 283→284→289→290P com 25F invariante ✓; âncoras (12-23 med 17,0; t med 6,2; s_cut ⊃ cluster 2699,7-2814,0) == LARGADA-0 ✓.
- CORREÇÃO DE CONTABILIDADE (achado da review): runs executadas = **14, não 13** — o re-smoke do braço cap pós-reparo (4b0d4eb) é uma sim completa de 6000 ticks que SOBRESCREVEU race_diag_lg1_cap_s0.csv; o "13" conta ARQUIVOS (13) e não RUNS (base_s0 + cap_v1 + cap_v2 + base_s50 + 10 trat). Slip duplo honesto (header 12 → §4 13 → real 14), nenhum gateia critério; pools INALTERADOS (50-59 = 10 seeds consumidas; s0 é semente de corpus, não-pool). Errata de 1 linha exigida no worklog do repo pelo próximo prompt.
- RULING R1 (veredito): PARE **RATIFICADO** — falsificação limpa de manual: o cap ENGAJOU de verdade (74-137 cap-ticks/run em 10/10 carros, fase 0 violações pós-reparo, SELF 3/3) e o desfecho não mudou (pares_W med 18 vs âncora 17; 9/10 ainda CONTATO-ADJ em 4,4-9,6s). Hipótese "velocidade de chegada causa o storm" REFUTADA. Flag morta (default OFF) = research-negativo documentado, SEM re-pin, SEM re-run. O diagnóstico mecânico é coerente: fator uniforme em v preserva a geometria relativa do campo e o funil do v_plan recomprime no mesmo ápice; em úmido campo mais lento = mais tempo comprimido por metro (s50 piora par 22 vs 12, cc +31%).
- RULING R2 (reparo flag-fantasma): RATIFICADO como reparo de INSTRUMENTO, não de mecanismo — o rejoin sobrescreve th/brk quando off-track (o freio do cap era dead write; v_plan é plano on-track), logo `not offtrack` muda telemetria/authority, NÃO comportamento; descoberto no smoke (SELF bloqueante funcionou), corrigido ANTES de consumir 50-59 (conforme o próprio prereg §3), com teste t6 (+1P, padrão REPARO) e re-smoke 3/3. Drift do braço base segue válido (bloco flag-gated).
- RULING R3 (E1 FECHADO POR MEDIÇÃO): expectativa report-only medida — fora% <15 em 0/10 (secas 20,9-26,7, 9/9 na banda 17,3-26,3) → o efeito da era contaminada era ARTEFATO DO KEYING, não pacing. E1 (errata exigida na L-0-review) agora tem confirmação empírica direta. Re-leitura obrigatória do anexo contaminado: o launch-HOLD sincronizado (32,6s modo 10/10) só ATRASAVA o storm (gaps de 9m preservados; release conjunto), nunca o reduzia — o cap não testou hold, testou teto de velocidade; as duas evidências juntas isolam a variável real: DENSIDADE ESPACIAL no funil.
- RULING R4 (nits de processo, não-gating): (1) o fix do glob (_events.csv) no script de veredito aconteceu DEPOIS do commit 7f10fb0 e ANTES da execução da decisão — a regra "script de decisão roda só com árvore limpa" foi tecnicamente contornada; ratificado porque os critérios estavam pinnados no prereg a3b8ff0, o FAIL tem margem enorme em 4 critérios independentes e a aritmética foi reproduzida por mim; NIT permanente: fix de script de decisão = commit/amend ANTES da execução. (2) hashes dos commits do scan 0-d + probe de derivação não reportados no §1 (a cadeia salta de 82b12c6 para a3b8ff0) — incluir no worklog do repo. (3) max seca 26,7 excede a banda report-only 26,3 por 0,4pp (1 seed; não-gating, conclusão E1 intacta). (4) suite nunca re-executada por mim (sandbox) — números agente-reportados, deltas internamente consistentes.
- RULING R5 (a fila — decisão do DONO, como pré-acordado na L-0-review "grid → era = decisão do dono"): a falsificação deixa exatamente três caminhos:
  (a) **GRID-ERA** (espaçamento/fileiras no cenário): ataca os 112 pares de grid E a densidade de chegada; custo = re-pin TOTAL (todas as âncoras de corrida morrem: pares_W, cc, rolante, fora, pools) — pagar só com hipótese validada.
  (b) **ACEITAR o launch-storm como teto documentado do produto**: fechar CICLO LARGADA; alavanca rejoin opt-in (−44% seco) permanece a mitigação do sintoma (tempo-fora pós-excursão).
  (c) **L-1b LAUNCH-STAGGER (recomendação do orquestrador)**: mecanismo flag-gated default OFF, release por SLOT (P1→P10, Δt/slot pinnado por derivação — gap pós-release = v(s)×Δt_cum, +20m no ápice com Δt=1,0s vs 9m do grid; zero closing-speed por construção com perfis idênticos), pool 60-69 virgem COM weather scan 0-d-style primeiro, SEM re-pin (flag-off = canônico), infraestrutura da L-1a reaproveitada (autoridade/telemetria/fase 1:1/SELF). É o TESTE BARATO da hipótese da grid-era: stagger dá gaps no ápice ≥ os que o espaçamento de grid daria → stagger FAIL ⇒ grid-era falharia a fortiori (economiza o re-pin); stagger PASS ⇒ dono decide adoção opt-in + grid-era opcional por realismo.
  GUARDS OBRIGATÓRIOS do prereg L-1b (registro antecipado): carros em stagger-hold NÃO contam como paradas ≥3s (GUARD-P falso-falaria o próprio mecanismo — excluir janela de hold por autoridade 'stagger' fase 1:1, declarado ANTES das runs); NUNCA lê clima; release frente→trás (trás→frente empilharia no grid); custo de +9×Δt na volta 1 declarado (rolante intocada — exclui volta 1); critérios PRIMÁRIO-1/2 e NÃO-REG IDÊNTICOS aos da L-1a (limiares pré-registrados não migram entre ciclos).

Stage Summary:
- LARGADA-1 RATIFICADO com 1 correção (14 runs) e 4 nits: GATE L-1a FAIL = falsificação limpa da hipótese de velocidade; launch-cap = research-negativo com flag morta; E1 (keying) confirmado por medição; worklog repo canônico com entrada L-1 + review L-0 verbatim.
- Estado: CICLO LARGADA em PARE aguardando o DONO — (a) grid-era com re-pin total, (b) fechar com teto documentado, (c) L-1b launch-stagger (recomendado: teste barato da hipótese de espaçamento em pool 60-69, sem re-pin).
- Pools: 50-59 consumidos; 60-69 próximos virgens (reservados ao L-1b se (c)); 0-19 âncoras; 20-29 queimados; 30-39/{2,8,9}/40-49 consumidos.

# Task ID: LARGADA-1-errata-0a (2026-10-19)
- ERRATA (contabilidade de runs): L-1a executou **14 runs, não 13** — o re-smoke do braço cap pós-reparo (4b0d4eb) é uma sim completa que SOBRESCREVEU race_diag_lg1_cap_s0.csv; arquivos (13) ≠ runs (14). Pools inalterados (s0 = semente de corpus, não-pool).
- Hashes ausentes da cadeia L-1a (R4.2): scan 0-d = **362ec3a**; probe de derivação do k/s_cut = inline (`python -c`), NUNCA commitado — lição: probe de derivação vira script commitado (o 0-c da L-1b o fará).

# Task ID: LARGADA-1b (2026-10-19) — LAUNCH-STAGGER: GATE FAIL; PRIMÁRIO-1 (vinculante) PASS esmagador — densidade validada, re-empacotamento estrutural

## Commits
a920fe0 (ANEXO A verbatim + errata 0-a: 14 runs ≠ 13; hash scan 362ec3a; probe L-1a
era inline) → 6551bac (0-b: scan 60-69 = 1/10 DAMP s60) → 0268919 (0-c: probe Δt
COMMITADO — Δt=1,0 pinado: gap 20,3-57,1 m ≥2× os 9 m do grid) → cd3ca5e (prereg
L-1b ANTES de código; PRIM-2 emendado; paradas excluem hold; rolante exclui volta 1;
orçamento 12+n_damp=13) → 52fa020 (impl + veredito ANTES de resultados, glob
_events desde o 1º commit) → testes 5/5 + suite 25F/295P/2S → ea1194a (reparo do
smoke: release em TICKS com round() — float +=0,1 segurava 1 amostra no boundary;
GAS slot 7 held até tick 60 vs 58; +t6) → re-smoke SELF 3/3 → fechamento.

## Smoke (SELF bloqueante funcionou)
Drift flag-off 0/30000 ✓; 1ª divergência == 1º held (tick 0) ✓; release NÃO exato
6/10 carros — CAUSA: sim_ts acumulado por += 0,1 deixa 0,99999… < 1,0 (float) →
fix tick-exato (int(round(sim_ts×10)) < (pos−1)×10), a lei do prereg implementada
literalmente. Re-smoke: 3/3 PASS. Suite 25F/296P/2S (295 prereg + 1 t6, disclose).

## GATE (14 runs: base s0 + stg v1 + re-smoke + base s60 + 10 trat 60-69; identity 10/10)
**FAIL MECÂNICO → PARE** — mas o resultado mais informativo do ciclo:
- **PRIMÁRIO-1 (vinculante, delay-invariante) PASS ESMAGADOR: pares_W mediana 2,
  máx 4** (âncora 12-23, med 17) — o stagger ELIMINA o storm de largada. A
  EXPECTATIVA report-only confirma: DENSIDADE de grid É o mecanismo local.
- **PRIMÁRIO-2 FAIL 5/10**: a 1ª excursão reaparece em 10/10 runs a t=32,8 s,
  s≈31-35 m — o FIM DA VOLTA 1, o MESMO sítio/modo da era contaminada (32,6 s @
  s≈37): o campo RE-EMPACOTA dentro de uma volta (perfis idênticos convergem de
  volta ao funil do v_plan) e a excursão-por-contato reemerge (CONTATO-ADJ em
  5/10, OUTRO em 5/10).
- **s60 (DAMP) FAIL PW/OFF/CC**: wand 16 vs base 13; off 46,5% (clima, base 46,8);
  cc 9.268 vs base 6.418 (+44%) — úmido PIORA com campo segurado (mesmo padrão
  do cap: +31% no WET s50).
- **REPORT-ONLY compostos**: pares residuais — HARD/SOFT 8, MEDIUM/SOFT 9,
  MEDIUM/MEDIUM 1, SOFT/SOFT 2 → 19/20 envolvem um carro SOFT (insumo grid-era).

## Leitura conjunta F1a+F1b (a cadeia causal fecha)
1. VELOCIDADE não é o mecanismo (cap refutado por falsificação limpa).
2. DENSIDADE de largada É o mecanismo DO STORM DE LARGADA (stagger: 17→2 pares).
3. O RE-EMPACOTAMENTO pós-largada é ESTRUTURAL (perfis idênticos): segurar a
   largada só TRANSFERE a primeira excursão-por-contato para o fim da volta 1,
   no mesmo sítio determinístico (s≈32 m).
4. Conclusão p/ o dono: o launch-storm como fenômeno de CAMPO é o teto do
   produto com este stack — a grid-era (espaçamento no CENÁRIO) atacaria a
   densidade inicial, mas a evidência do stagger diz que o campo re-empacota
   dentro de UMA VOLTA: esperar re-empacotamento ~igual com grid espaçado.
   A mitigação do sintoma permanece a alavanca rejoin opt-in (−44% seco).

## Estado
Flags --launch-cap e --launch-stagger ambas default OFF (research-negativas,
código/testes preservados). SEM re-pin, SEM re-run. 14 runs (13 arquivos —
contagem runs≠arquivos aplicada). Pools: 60-69 consumidos; 70-79 próximos
virgens. Suite 25F/296P/2S; doc-test verde.

# Task ID: LARGADA-FECHO-0 (2026-10-19) — ERRATA-CANÔNICA (aditiva, ancorada)
- ORÇAMENTO L-1b: prereg cd3ca5e declarou 13 runs; EXECUTADAS 14 (+1
  re-smoke s0 do braço stagger pós-reparo ea1194a) — sancionado pelo §3
  SELF-BLOQUEANTE do próprio prereg (falha → consertar e re-smoke SEM
  consumir pool), fora do pool (s0 = semente de corpus), disclose já feito
  no relatório L-1b. Pools inalterados.
- REGRA DE TEMPLATE PERMANENTE: todo prereg futuro declara no orçamento a
  linha "+1 re-smoke contingente (s0)" — o orçamento declarado passa a
  incluir explicitamente a contingência do re-smoke.
- PENDÊNCIA REGISTRADA: o texto "LARGADA-2-review" (ANEXO B) NÃO constava do
  prompt do LARGADA-FECHO nem existe no repo — o append verbatim fica
  PENDENTE até o texto chegar; nada foi fabricado.
  [RESOLVIDO no LARGADA-4, 2026-10-19: texto recebido e apendado VERBATIM no
  commit 8bd728c — ver "ANEXO B — LARGADA-2-review" adiante neste worklog.]

# Task ID: LARGADA-FECHO (2026-10-19) — fecho canônico do CICLO LARGADA (teto documentado)
ZERO runs · ZERO mecanismo novo · ZERO consumo de pool (70-79 INTACTOS).

## Commits deste fecho
1cd238a (errata-canônica: L-1b 13->14; regra +1 re-smoke contingente; pendência
ANEXO B) → diag script (commitado ANTES de executar) → DOSSIE_LARGADA.md +
PROJECT_STATE (header FECHADO + seção) + worklog (esta entrada) + memórias.

## PASSO 1 — diagnósticos (largada_fecho_diag.py, leitura only)
- N1 GUARD-V (veredito L-1b recomputado): 10/10 voltas PASS.
- N2 1ªs excursões (t~32,8s, s~31-35m): VER/MEDIUM, SAI/HARD, VER/MEDIUM,
  PIA/MEDIUM, RUS/HARD, NOR/MEDIUM, PER/MEDIUM, HAM/MEDIUM, ALO/MEDIUM,
  VER/SOFT → SOFT 1/10: SEM padrão dominante (anotada a ausência; ambos os
  desfechos dossiê-válidos; nenhum ciclo novo abre). O lead 19/20-SOFT
  aplica aos pares residuais de largada, NÃO ao evento de re-empacotamento.
- N3 mapeamento 14 runs -> 13 CSVs: run2 (stg_s0 v1) SOBRESCRITO pelo
  re-smoke run3 (pós-ea1194a) — arquivo re-usado; runs≠arquivos reafirmado.

## PASSO 2 — DOSSIE_LARGADA.md (local único canônico)
Cadeia causal com âncoras (F0 contato/redefinição; F1a velocidade refutada +
E1 keying medido; F1b densidade 17->2 validada + atrator 10/10 a 32,8s
s~31-35m); ENUNCIADO DO TETO (perfis idênticos + v_plan compartilhado + zero
coordenação => empacotamento estrutural; intervenções de largada TRANSFEREM
a 1ª excursão-por-contato, não a eliminam); disposição de produto (rejoin-gap
opt-in = mitigação canônica; cap/stagger research-negativas default OFF;
GRID-ERA contra-indicada); lead SOFT com ressalva; inventário completo
(28 corridas no ciclo; pools; flags; hashes 82b12c6/a3b8ff0/cd3ca5e/a614cb0
+ demais).

## Estado final da frente LARGADA
ENCERRADA. Teto documentado. Mitigação de produto = rejoin-gap opt-in
(-44% seco, C' 8/8). Próximo pool virgem: 70-79.

## Pendências
- ANEXO B (texto "LARGADA-2-review") AUSENTE do prompt deste fecho — append
  verbatim no worklog fica PENDENTE até o texto chegar; nada foi fabricado.

## ANEXO B — LARGADA-2-review (orquestrador, 2026-10-19) — verbatim

# REVISÃO LARGADA-1b — VEREDITO: **RATIFICADA** ✓

Cross-check aritmético íntegro (revisão de papel): pares_W med 2/máx 4 ≤ 8/14 PASS ✓; PRIMÁRIO-2 = 5/10 ≠ADJ < 7/10 FAIL ✓; secas NÃO-REG íntegras (rol 132-135 ≤141; P/W 0/0 pós-release; off 20,6-23,7 ≤28,3; cc 692-1.902 ≤3.197) ✓; s60: wand 16>13, cc 9.268 = +44,4% vs 6.418, off 46,5 ≈ base 46,8 (caveat clima do próprio prereg aplicado) ✓; pares residuais 8+9+1+2=20, **19/20 com SOFT** ✓; 14 runs/13 arquivos ✓; cadeia de commits monotônica ✓.

**R1 — PARE RATIFICADO, e é o FAIL mais produtivo do projeto.** PRIMÁRIO-1 PASS esmagador **valida a hipótese de DENSIDADE** (17→2 pares), mas o gate é conjuntivo: a excursão transferida (10/10 no mesmo sítio) e a piora em úmido (cc +44%) são regressões de produto. **PRIMÁRIO-1 não resgata a flag** — correta a disposição: flag morta, conhecimento vivo.

**R2 — afiamento:** F1a+F1b falsificam a **classe inteira** de intervenções-de-largada (velocidade via cap; densidade/timing via stagger). O sistema tem um **ATRATOR**: perfis idênticos + funil do v_plan re-criam o empacotamento independente das condições iniciais. Isso não é leitura retórica — é o que separa "transferiu" de "eliminaria com outro parâmetro".

**R3 — errata-canônica para o fecho:** orçamento prereg 13 → executados **14** (+1 re-smoke s0, sancionado pelo §3 SELF-BLOQUEANTE, fora do pool, disclose). Segunda recorrência do padrão (L-1a e L-1b) → vira regra de template: todo orçamento futuro traz linha explícita "+1 re-smoke contingente (s0)".

**R4 — SELF/reparo ratificados como padrão-ouro:** a falha de release (float 0,999…<1,0) foi pega na fumaça **antes** do pool, zero seeds consumidas; o fix implementa a lei do prereg literalmente (ticks, não segundos) + t6. Lição durável registrada nas memórias.

**R5 — NITs report-only** (leitura de CSVs existentes, zero runs): (N1) citar a linha GUARD-V do veredito; (N2) driver_id + composto dos excursionantes a t≈32,8s — se SOFT consistente, conecta o re-empacotamento ao 19/20; qualquer desfecho é dossiê-válido; (N3) mapa runs→arquivos 14→13.

---

# DECISÃO DE FILA: **FECHAR O CICLO LARGADA (teto documentado)**

1. A cadeia causal da queixa original está **completa**: F0 anatomia (cascata de contato, ENTRADA-S 65%) → F1a velocidade refutada → F1b densidade validada + atrator estrutural.
2. Grid-era tem **contra-evidência empírica direta**: reduziria a densidade inicial que o stagger já provou redutível (17→2), enquanto a excursão persiste pelo atrator — a fortiori agora **medido**, não teórico, e com custo de re-pin total (todas as âncoras de corrida morrem).
3. O 19/20-SOFT é lead futuro **pré-anexado da ressalva do atrator**, não ciclo agora.
4. A mitigação canônica do sintoma permanece a **alavanca rejoin opt-in** (−44% seco, C' 8/8).

*(Veto do dono registrado: a grid-era continuava disponível antes do relay do fecho; o fecho executado segue esta decisão.)*

# Task ID: LARGADA-4 (2026-10-19) — micro-fecho de livros (resolve as 2 pendências do FECHO)
ZERO runs · ZERO mecanismo · ZERO pool (70-79 INTACTOS).

## PASSO 0 — ANEXO B (pendência fechada)
Texto "LARGADA-2-review" recebido nesta ordem e apendado VERBATIM (commit
**8bd728c**) — nada editado/resumido/reescrito. A revisão RATIFICA o fecho:
R1 (PARE do L-1b = "o FAIL mais produtivo"; PRIM-1 valida densidade mas não
resgata a flag), R2 (atrator: F1a+F1b falsificam a CLASSE de
interventions-de-largada), R3 (errata 13→14 + regra de template
re-smoke), R4 (SELF/reparo = padrão-ouro), R5 (NITs report-only — todos
executados no FECHO). DECISÃO DE FILA: FECHAR O CICLO LARGADA; veto do
dono à grid-era registrado. Pendência marcada RESOLVIDA nos 3 livros
(worklog/PROJECT_STATE/DOSSIE_LARGADA §7).

## PASSO 1 — AUDITORIA_RL.md (referência fantasma fechada — DESFECHO A)
- Proveniência (1.0, read-only): `git log --all --follow` mostra o arquivo
  em 9099235 (criação, R13-FECHAMENTO A3), 3d4f0e9 e 439f402 (última
  versão), no caminho `backend/model_train/AUDITORIA_RL.md` (1.181 linhas —
  auditoria do pipeline de RL pré-reestruturação); referenciado pelo
  PROJECT_STATE (header + tabela Arquivos-chave) e por scripts de
  archive/; PERDIDO no squash da PÓS-CICLO-1.
- Ação: **restaurado VERBATIM de 439f402** com bloco de PROVENIÊNCIA de
  5 linhas no topo (o único acréscimo; claramente datado/marcado — zero
  narrativa fabricada). Header do PROJECT_STATE ("ler este arquivo e
  AUDITORIA_RL.md") é VERDADEIRO novamente; linha da tabela Arquivos-chave
  atualizada com a nota de restauração.
- Doc-integrity: o test_state_files.py NÃO valida referências de arquivo →
  sem alteração de teste; suite esperada 25F/296P/2S invariante.

## Estado
As duas pendências do FECHO estão RESOLVIDAS. CICLO LARGADA encerrado e
RATIFICADO. Pools: 70-79 INTACTOS.

# Task ID: LARGADA-4-review (micro-fecho RATIFICADO — frente LARGADA definitivamente encerrada)
Agent: orquestrador (Z.ai)
Task: Auditar o LARGADA-4 (ANEXO B verbatim em 8bd728c; restauração do AUDITORIA_RL.md de 439f402;
resolução nos 3 livros; zero runs; árvore limpa em 2fb1d37) e encerrar a frente LARGADA.

Work Log:
- ANEXO B CONFERE 1:1 com o texto emitido — nada editado/resumido; commit 8bd728c dedicado ao append
  (fonte antes dos derivados) ✓. Contagem CONFERE: 1.181 + 5 de proveniência = 1.186 ✓.
- Cadeia de proveniência coerente: 9099235 (criação, R13-FECHAMENTO A3) → 3d4f0e9 → 439f402 (última) →
  perda no squash da PÓS-CICLO-1 (3º caso) → restauração verbatim em 2fb1d37 ✓. Proveniência read-only
  ANTES da ação: a referência fantasma foi tratada como hipótese (git log --all --follow), não como fato ✓.
- 3 livros coerentes: worklog ([RESOLVIDO] ancorado em 8bd728c); PROJECT_STATE (pendência removida do
  header; RATIFICADO com âncora; Arquivos-chave com nota de restauração); DOSSIE_LARGADA §7 ✓.
- Zero runs / zero mecanismo / zero pool: 70-79 intactos; suite 25F/296P/2S invariante; doc-test verde;
  re-leitura antes do edit após drift de heredoc = anti-stale-write honrado ✓.
- R1: RATIFICADA a ordem proveniência→ação — o arquivo EXISTIA, logo a ação correta era religar (A), não
  apagar a referência. Lições: referência fantasma → arqueologia git antes de presumir; squash = operação
  de risco para livros (3º arquivo perdido).
- R2: restauração RATIFICADA como aditiva-pura — corpo verbatim de 439f402, único acréscimo = bloco de
  proveniência datado/marcado; ZERO narrativa fabricada; "ler este arquivo e AUDITORIA_RL.md" é VERDADEIRO.
- R3: re-leitura antes de editar = padrão-ouro para os livros (creditado).
- R4 (NITs report-only — resolver na PRÓXIMA tocada nos livros, sem commit dedicado): N1 — "restaurado do
  histórico em 439f402" → 439f402 é a versão-FONTE; a restauração foi em 2fb1d37 (reescrever). N2 —
  "# 238/238" em Comandos essenciais defasado vs 25F/296P/2S (pré-existente). N3 — doc-test não valida
  existência de arquivos referenciados; candidato aditivo se o doc-test for tocado no futuro.
- R5 (fecho definitivo): frente LARGADA ENCERRADA em todos os níveis — 28 corridas, fecho RATIFICADO,
  pendências ZERO, 70-79 virgens. Reabertura só com hipótese nova + prereg novo; grid-era segue vetada.

Stage Summary:
- LARGADA-4 RATIFICADO (âncoras: 8bd728c, 2fb1d37). CICLO LARGADA fechado, ratificado, sem pendências.
- FILA ao DONO: (a) FASE H geometria [recomendado]; (b) wiring do composite em corrida (caveat: atrator
  estrutural); (c) compostos 19/20-SOFT (pares residuais apenas). Task ID: FASE-H-0 — PHASE H (geometry). ZERO runs, ZERO pool (70-79 untouched), ZERO re-pin.

# Task ID: FASE-H-0 (2026-10-19) — PHASE H geometry: mirrors Monaco/Spa GATE FAIL no G4 (limiar); NÃO congelados; H3 detector validado
ZERO runs · ZERO pool (70-79 intactos) · ZERO re-pin (v1s canônicos intocados).

## Commits
fdb1afb (STEP 0: ANEXO LARGADA-4-review verbatim) → 738f72d (NITs N1/N2 da review:
Arquivos-chave FONTE-vs-restauração; suite no Comandos essenciais 238/238 →
25F/296P/2S) → 21ac676 (STEP 1: prereg FASE-H ANTES de código) → d470a87 (STEP 2:
builder + detector + 5 testes) → fechamento (books).

## H1/H2 — mirrors F1DB (SVG black-outline; parse M/c/s/z; resample 4 m; calibração ao oficial)
| pista | layout | G1 clearance | G2 cross | G3 R_min | G4 turns | G5 L | veredito |
|---|---|---|---|---|---|---|---|
| Monaco | monaco-6 (2003-2019, 2021-2026) | 16,30 m ✓ | 0 ✓ | 11,34 m ✓ | **15 vs 19±3 ✗** | 0,05% ✓ | FAIL → NÃO congela |
| Spa | spa-francorchamps-4 (2007-2026) | 24,83 m ✓ | 0 ✓ | 14,66 m ✓ | **5 vs 19±3 ✗** | 0,01% ✓ | FAIL → NÃO congela |

- Fonte F1DB saudável e MUITO superior aos v1 (Monaco_v1: clearance 1,71 m;
  o mirror dá 16,30 m; R_min 11,34 m = hairpin real do Loews). Nome previsto
  `{Name}_mirror*_v1.json` (NUNCA _v2: o loader prioriza _v2 e mudaria a pista
  canônica sem decisão do dono — desvio documentado no prereg §2.6).
- **Diagnóstico (pós-veredito; emenda = revisão — precedente ERRATA #2)**: o
  limiar κ≥0,02 (R≤50 m) do G4 sub-detecta curvas rápidas. Sweep: Monaco
  κ≥0,01 → 17 (DENTRO de 19±3); Spa κ≥0,01 → 23 (4 fora; κ~0,008 daria ~19-21).
  **Crítica do instrumento**: G4 como pinado não separa Spa COMPLETA (5 turns
  a κ≥0,02) da Spa_v1 TRUNCADA (também ~4-5) — em pista rápida o G4 não serve
  ao próprio intento (completude). SEM re-pin pós-número: nada congelado.
- Opções para a revisão: (a) emendar G4 (limiar ~0,008-0,01 ou ±4) num prereg
  novo e RE-RODAR o builder (segundos, zero runs); (b) trocar G4 por outro
  cheque de completude; (c) rejeitar os mirrors.

## H3 — detector G3 (report-only; critério pinado ANTES)
9/9 frozen auditadas: **2/9 flaggeadas EXATAMENTE como o prereg previa**:
- Monaco_v1: **45 riscos** de hint (pares não-adjacentes <2 m; clearance
  1,63 m) — o artifact de spline concentrado em s≈972-1055 m.
- Suzuka_v1: **8 riscos** (clearance **0,04 m** em s≈1731↔3936 m — o
  crossover real da ponte/esses, MAIS crítico que os 0,39 m da FASE G).
- Spa_v1: **0 gaps** (confirmado: o furo dela é comprimento, não espaçamento).
- Demais 7 limpas (clearance 17-23 m). ZERO mudança de runtime. O mapa do
  fix futuro "janela arc-local" (G3) está quantificado.

## Instrumento
5 testes (25F/301P/2S): parser M/c/s/z + rejeição de comandos fora do prereg;
resample 4 m em loop; gates sintéticos (fold/cruzamento/R apertado falham;
clean passa); convenção sha do freeze validada contra Monaco_v1 REAL (t4
adaptado: o original "artefatos se congelados" ficou N/A — G4 FAIL, nada
congelado — disclose); detector sintético (pinça 1,5 m; gap 20 m).

## Estado
Mirrors NÃO congelados (gate mechanical FAIL; a decisão de emenda = revisão).
H3 entregue. Pools 70-79 intactos. v1s canônicos intocados. O loader segue
inalterado.

# Task ID: FASE-H-0-review (RATIFICADA — G4 FAIL honrado como falha de instrumento; fila = H-1 calibração em controles)
Agent: orquestrador (Z.ai)
Task: Auditar o FASE-H-0 (mirrors F1DB Monaco/Spa + detector G3; zero runs/pool/re-pin; G1/G2/G3/G5 PASS,
G4 FAIL → nada congelado; emenda roteada à revisão) e decidir a fila.

Work Log:
- Cross-check CONFERE: suite 296+5=301 exato ✓; cadeia fdb1afb→738f72d→21ac676→d470a87→db1e131 monotônica,
  prereg antes de código ✓; zero runs/pool/re-pin ✓; NITs N1/N2 resolvidos conforme a review (anexo) ✓;
  eras F1DB honestas ✓.
- R1: G4 FAIL honrado — nada congelado, sem re-pin pós-número, diagnóstico pós-veredito MARCADO e usado só
  para a fila (padrão PARE→diagnóstico→revisão executado a lápis).
- R2: crítica do instrumento VÁLIDA E MEDIDA — G4 κ≥0,02 não separa Spa completa (5) de Spa_v1 truncada
  (~4-5): não mede completude em pista rápida; morre como gate.
- R3 (catch): emenda ingênua NÃO passa — κ≥0,01 resolve Monaco (17) mas não Spa (23>22); ±4 não resolve
  (5 vs [15,23]); κ chutado pelos alvos = calibrar até passar = re-pin disfarçado. Rota honesta: calibrar
  κ* em CONTROLES known-good e aplicar aos alvos com κ* congelado (anti-tautologia explícita).
- R4: nomeação inerte ao loader CORRETA e OBRIGATÓRIA (load_track_frozen prioriza {key}_v2.json — nomear
  _v2 trocaria o canônico sem o dono); Monaco_mirror2021_v1.json / Spa_mirror_v1.json + teste de inércia.
  Freeze ≠ troca de canônico.
- R5: desvio benigno ratificado com crédito (NITs em commit separado do ANEXO preserva a proveniência do
  verbatim). NIT novo: Comandos essenciais defasado de novo (296P vs 301P) — resolver no H-1.
- H3 detector validado como preregistrado (2/9: Monaco_v1 45 riscos no artefato; Suzuka_v1 0,04 m no
  crossover real; mapa arc-local quantificado = backlog, sem ciclo novo). t4 adaptado com disclose = OK.

Stage Summary:
- FASE-H-0 RATIFICADA: fonte espelhada saudável e muito superior aos v1; o bloqueio é CALIBRAÇÃO do G4,
  não geometria. PROMPT FASE-H-1 emitido (calibração em controles, árvore pinnada, zero runs).

[Nota do ajudante: o primeiro append desta review foi parar num caminho errado FORA do repo
(/home/jovitor/unicamp/worklog.md, cwd flipou para a raiz — armadilha conhecente da memória);
o estranho foi removido e o append refeito no caminho absoluto correto. Zero efeito nos livros.]

# Task ID: FASE-H-1 (2026-10-20) — calibração do G4 em CONTROLES: G4 MORRE como gate; mirrors CONGELADOS (ramo B)
ZERO runs · ZERO pool (70-79 intactos) · ZERO re-pin (canônico intocado; adoção = DONO).

## Commits
94e8df8 (PASSO 0: ANEXO FASE-H-0-review verbatim; nota: 1º append foi parar num
arquivo estranho FORA do repo pelo cwd-flip — removido e refeito no caminho
absoluto) → f277819 (NIT recorrente: Comandos essenciais 296P→301P) → 1f4af52
(prereg FASE-H-1 ANTES de qualquer execução: contagens oficiais ESCRITAS da
fonte única Wikipedia EN 2026-10-20 — formula1.com OMITIU turns nas race pages,
probe registrado; M19 S19 H14 Mo11 Z14 Su18 I15) → 00be13d (calibração:
CSV dos controles commitado ANTES dos alvos) → e405298 (RAMO B: freeze dos
2 mirrors + 2 testes) → fechamento.

## Calibração (anti-tautologia cumprida)
Fase controles: grade κ 0,004→0,020 (17 valores) sobre 5 controles
(Hungaroring 14, Monza 11, Zandvoort 14, Suzuka 18, interlagos_v2 15):
**0/5 in-band em TODOS os κ** (melhor Σ|Δ|=42 @κ=0,02: contagens 21-28 vs
oficiais 14-18). Diagnóstico do instrumento: o detector κ-picos INFLA em
frozen de telemetria (ruído de polyline = picos espúrios) e DEFLACIONA em
mirrors Bézier — **a contagem de "turns oficiais" é convenção humana que o
detector geométrico não reproduz em NENHUMA classe de fonte**. Validade
(<4/5) → **RAMO B**. κ* = 0,02 (degenerado, apenas referência do
fingerprint). O protocolo anti-tautologia PROVOU seu valor: had we tunado
κ nos alvos, teríamos shipado um gate sem sentido.

## RAMO B executado
G4 → fingerprint report-only (turns_detected + g4_kappa_used + g4_note da
crítica nos JSONs); completude = G5 + G1/G2/G3 (todos PASS). **Mirrors
CONGELADOS**: Monaco_mirror2021_v1.json (sha 67ca11dc211c8c78; 834 wp; G1
16,30 m; G3 11,34 m — hairpin real; G5 0,05%) e Spa_mirror_v1.json (sha
2637c8adf3c37939; 1.751 wp; G1 24,83 m; G3 14,66 m; G5 0,01%).

## Inércia (verde)
load_track_frozen('Monaco') → Monaco_v1 (07e7ef4dd6af4517) e 'Spa' →
Spa_v1, mesmo com os mirrors no diretório; mirrors loadáveis pelos nomes
explícitos. LIÇÃO nova: o loader é CASE-SENSITIVE ('monaco' minúsculo não
acha Monaco_v1.json no Linux). Suite 25F/303P/2S (301+2, declarado).

## Estado
Mirrors = artefatos GEOMÉTRICOS congelados; âncoras de corrida
(SF/direção) e TROCA do canônico = decisão do DONO. Pools 70-79 intactos.

ANEXO — FASE-H-1-review (orquestrador, 2026-10-20) — VERBATIM
Veredito: RATIFICADO ✓ — FASE H-1 fechada. G4 morto como gate COM causa nomeada; mirrors
congelados como artefatos geométricos; canônico intocado; zero runs/pool/re-pin; suite
25F/303P/2S exata. Fase H encerrada nos termos do dono (freeze ≠ adoção). Fila devolvida com
emo de decisão.

R1 — Anti-tautologia honrada (o ponto central da fase): o CSV de controles foi commitado
(00be13d) ANTES de qualquer cômputo dos alvos; κ* nunca foi congelado (0/5 < 4/5) e o RAMO B estava
PINADO no prereg §6 antes dos dados; a crítica do detector está documentada no JSON
(g4_note). Não houve "ajustar o limiar até passar" — o gate morreu com diagnóstico. É exatamente
a rota que a R3 da H-0-review exigia. Comportamento protocolar perfeito.
R2 — Contagens oficiais verificadas independentemente pelo revisor: Monaco 19, Spa 19,
Hungaroring 14, Monza 11, Zandvoort 14, Suzuka 18, Interlagos 15 — os 7 valores conferem com a
re-verificação externa do revisor (Wikipedia EN + circuit-guide da formula1.com, que lista
"Number of turns: 19" para Monaco; o probe do agente omitiu-turns vale para as RACE pages —
isto é corroboração, não correção; a fonte única do prereg permanece válida pois foi ESCRITA
antes da execução). Robustez: o 0/5 não depende de erro ±1-2 nas oficiais (contagens 21-28;
Δ mínima 4 > banda 3).
R3 — Aritmética interna consistente: grade 0,004→0,020 passo 0,001 = 17 κ ✓; Σ|Δ|=42 @κ=0,02
compatível com contagens 21-28 × oficiais {14,11,14,18,15} com todo Δ≥4 ✓; 834 wp × 4 m =
3336 m vs oficial 3,337 km (0,05% ✓); 1751 wp × 4 m = 7004 m vs 7,004 km (0,01% ✓ — os G5
re-ancoram os mirrors nos comprimentos oficiais); suite 301+2 = 303P, t-métricas não-N/A ✓.
R4 — Inércia/canônico: loader intocado, nomes inertes (a prioridade {key}_v2.json nunca
acionada), 'Monaco'/'Spa' seguem resolvendo para os v1; lição case-sensitive registrada; o
desvio 'monaco'→'Monaco' no teste foi conservador e com disclose — ratificado.
R5 — Incidente cwd-flip: disclosure honesto e benigno. O heredoc com caminho relativo
apensou num arquivo estranho FORA do repo; detectado pela falha do git add ("fora do
repositório"), worklog real (414 linhas) verificado intacto, estranho removido, append refeito
em caminho absoluto, incidente registrado no commit do ANEXO. Zero contaminação. Lição
reafirmada: livros SEMPRE em caminho absoluto.
R6 — PROJECT_STATE: header H-1 completo (todas as métricas do relato presentes); cadeia de
"anterior" preservada; seção H-1 consistente hash a hash (94e8df8 → f277819 → 1f4af52 →
00be13d → e405298; a81a011 fora da auto-referência — mesma convenção da H-0) ✓.
R7 — Nota epistêmica (não bloqueia): o que morreu é o DETECTOR (κ-picos com limiar único
global), não a ideia de checagem de turns — a convenção oficial não é refratável por um
escalar (chicane conta 1-2 por convenção; sweeper não conta). Revival research-grade é
possível no futuro via âncoras humanas de turn (7 labels, zero runs) — backlog OPCIONAL.
R8 — ACHADO NOVO do revisor — causa-raiz provável da truncagem da Spa_v1: Spa_v1 mede
4352 m; o comprimento oficial 7,004 km = 4,352 mi (7004/1,609344 = 7003,85 m). Igualdade a
4 algarismos raramente é coincidência: o builder original provavelmente engoliu o valor em
MILHAS como metros — isso explica o −37,9% de uma vez. Não muda nada processualmente
(Spa_v1 já está superada pelo mirror), mas vale errata ADITIVA: nota no registro da FASE G +
campo no JSON da Spa_mirror ("parent v1 truncated by probable mi→m unit error"). Confirmação
barata: procurar o literal "4.352"/conversão mi no builder/fonte original da Spa_v1.
NITs aditivos:
N1 (3ª recorrência desta classe): Comandos essenciais diz # 25F/301P/2S; a suite fechou
303P. Hábito novo proposto: o commit de FECHAMENTO inclui o Comandos (o toque do PASSO 0
sempre fica defasado quando a suite cresce na própria fase). Fix imediato: # 25F/303P/2S.
N2: Monaco_v1 clearance tem dois valores ancorados — 1,71 m (audit FASE G) e 1,63 m
(H3 detector da H-0, s≈972-1055 m). Não é contradição, são dois instrumentos; errata de uma
linha rotulando as fontes (o prereg §3 citou 1,63 m sem rótulo).
N3 (micro): "oficiais 14-18" no relato/header ⇒ "oficiais 11-18" — Monza 11 é controle
e entra no Σ|Δ| (de fato, o Δ de Monza é dos maiores; o slip esconde o pior caso do detector).
MEMO DE DECISÃO AO DONO (a fila é sua):

Opção A ⭐ (recomendada) — ADOÇÃO dos mirrors como canônico (Monaco e/ou Spa) num micro-ciclo
único com prereg. Motivos: Monaco hoje é ARTEFATO (clearance ~1,6-1,7 m; 45 riscos de hint; 56
pares <8 m) e o B' Monaco 0/3 foi medido SOBRE o artefato — com o mirror (G1 16,30 m; G3 11,34 m;
G5 0,05%) a Meta B' (6/9) tem chance real de virar 7/9. Spa hoje é TRUNCADA −37,9% (R8) e TODOS
os números históricos de Spa (B' 3/3; 51-eps 124,4 s) são sobre a pista curta — a Spa real
(7 km; Eau Rouge/Kemmel/Blanchimont) é outra pista: expectativa incerta, é experimento.
Ressalvas a preregistrar: (i) professor-FIRST — medir professor solo 3 eps nos mirrors ANTES de
qualquer número de aluno; se o professor não fizer 3/3 num mirror, B' NÃO re-ancora naquela
pista (registro honesto); (ii) validade externa — R_min do mirror 11,34 m é mais suave que o
hairpin real (~7 m, consequência do SVG+resample): B' passaria a valer "sob mirror"; (iii)
mecânica da inversão de inércia — preferência: publicar o mirror como {key}_v2.json (a
prioridade EXISTENTE do loader faz a troca sem tocar no loader; é a MESMA convenção do
interlagos_v2 canônico; sha de conteúdo preservado); (iv) v1s NUNCA apagados (archive/ com
proveniência); (v) números históricos de Monaco/Spa permanecem registros "era v1" anotados.
Opção B — wiring do composite no race runner (FASE 4 v15): desbloqueia B3.2/B3.3 (mista,
hold-at multi) e corridas all-composite; independente da adoção.
Opção C — compostos 19/20-SOFT (fila LARGADA herdada; pares residuais).
Backlog sem ciclo: revival G4 por âncoras humanas; fix arc-local do G3 (Suzuka_v1 0,04 m);
NITs N1-N3; errata R8.
PROMPT ADOÇÃO-H-2 (condicional — SOMENTE enviar após o dono aprovar a Opção A):

Task ADOÇÃO-H-2 (zero corridas/pool/clima/re-pin; evals determinísticos de gate PERMITIDOS;
pools 70-79 intactos). PASSO 0: ler PROJECT_STATE + AUDITORIA_RL; apendar esta review VERBATIM
em commit dedicado (caminho ABSOLUTO do worklog); NITs N1-N3 + errata R8 (a hipótese mi→m entra
MARCADA como hipótese até confirmar o literal no builder da Spa_v1). PASSO 1: PREREG commitado
ANTES de qualquer mudança/medida: (a) escopo EXATO decidido pelo dono — quais chaves adotam
(monaco/spa) — marcado no prereg; (b) professor-first: professor solo 3 eps nos mirrors com o
instrumento do gate; professor <3/3 num mirror ⇒ B' NÃO re-ancora naquela pista (árvore pinada);
(c) mecânica: mirror → {key}_v2.json (convenção interlagos_v2; loader INTOCADO; sha de
conteúdo preservado e conferido); (d) v1s → archive/ com proveniência (NUNCA deletar); (e)
hipótese de B' com expectativa + falsificação (Monaco 0/3 era limitado pelo artefato? Spa 3/3
sustenta nos 7 km?); (f) validade externa declarada (R_min 11,34 m vs hairpin real ~7 m; B'
vale "sob mirror"). PASSO 2: execução na ordem do prereg (professor → mecânica → re-baseline
aluno 3 eps por pista adotada → suite). Instrumento: t-inércia REESCRITO (flip: 'Monaco' →
mirror) + t-novo (v1 archived loadável por nome explícito); suite delta declarado no prereg
(esperado 25F/304P/2S — confirmar contagem). Header PROJECT_STATE novo + cadeia "anterior";
worklog FASE-H-2; PARE para revisão. PAREs permanentes: corridas; pool; clima no runner; re-pin;
errata não-aditiva; qualquer número de ALUNO antes do professor = violação do prereg.

[Nota do ajudante: este ANEXO foi apensado VERBATIM conforme o prompt ADOÇÃO-H-2; o
PROMPT condicional embutido é o RASCUNHO da review — o prompt FINAL desta execução é o
do ADOÇÃO-H-2 emitido pelo dono, que prevalece em conflito (escopo pinado: AMBOS).]

# Task ID: ADOÇÃO-H-2 (2026-10-20) — mirrors ADOTADOS como canônico (dono: AMBOS); B' sob mirror 9/9 por completude
ZERO corridas · ZERO pool (70-79 intactos) · ZERO re-pin · loader INTOCADO.

## Commits
87419b1 (ANEXO FASE-H-1-review verbatim — caminho ABSOLUTO) → ce4e799 (NITs N1-N3
+ errata R8 HIPÓTESE ABERTA — literal 4.352/mi NÃO achado no repo; nota no registro
FASE G + JSON da Spa, sha 2637c8→4b05f2c3bbc625fc com disclose + fastf1 ==3.8.3
pinado, blast radius REDE-vs-cache, ingestão futura = dono) → 8c14f9f (prereg: escopo
AMBOS; professor-first; shas pinados; H-Mon/H-Spa; re-baselines enumerados; suite
declarada 25F/304P/2S) → 86a129c (professor 3/3 + controles + mecânica git mv →
_v2 + v1s→archive c/ README + CSVs commitados) → fechamento (Comandos NO commit —
hábito N1).

## Professor-first (nomes explícitos, ANTES do swap; runner --controller professor --n-cars 1)
3 eps/mirror, bit-idênticos (md5), ≥2 voltas/ep pelo critério PINADO → **3/3 ambos**
(Monaco 2 voltas @211,9s fora 58,5%; Spa 2 voltas @223,1s fora 32%). DISCLOSE:
eps terminaram em 2 voltas (--laps default 2) dentro da janela 600s.
**CONTROLES (pós-veredito, marcados)**: interlagos canônico professor-solo
**fora 24,3%** — o off% alto é BASELINE do instrumento professor-solo-frozen (os
0,36% históricos eram 10-carros/live; nunca houve âncora solo-frozen);
**Monaco_v1 ABORTA no runner atual** (reta antes da SF = 0 m); Spa_v1 professor
fora 45,4%. **Mirrors MAIS dirigíveis que os v1s** (Spa 32<45,4; Monaco 58,5<ABORT).

## Mecânica
git mv → Monaco_v2.json (sha conferido 67ca11dc211c8c78) / Spa_v2.json
(4b05f2c3bbc625fc — delta do memo da review pela errata R8 do PASSO 0,
disclosed no prereg); v1s → archive/tracks_frozen_v1/ (Monaco_v1
07e7ef4dd6af4517; Spa_v1 f83365bf26d0b1b1) com README de proveniência;
zero duplicatas inertes; loader INTOCADO (a prioridade {key}_v2 existente
faz a troca).

## B' re-ancorado SOB MIRROR (canária runner solo 600s; 3 eps/pista bit-idênticos)
- **Monaco_v2: 3/3 × ≥2 voltas** (era-v1: 0/3 — numa pista que HOJE ABORTA).
  RESSALVA: fora 45,0% (>25% canária); 34 excursões; preso acumulado 118s
  (R3); wanderer 0 (mais longa 26,8s). H-Mon: o artefato limitava a era-v1
  (confirmado pela ABORT), mas a pilotagem segue custando — completude com
  custo documentado.
- **Spa_v2: 3/3 × 3 voltas; fora 20,8% ≤ 25%; wanderer 0 — canária
  COMPLETA.** H-Spa: o aluno SUSTENTA nos 7.004 m reais (o 3/3 era-v1 era
  na truncada 4.352 m).
- **Meta A Monaco SOB MIRROR (professor 5 eps)**: 5/5 × 2 voltas @211,9s.
- B' tabela: [era v1] 6/9 anotado; SOB MIRROR 9/9 por completude
  (Suzuka_v1 3/3 inalterada). Números históricos NUNCA apagados.

## Instrumento
t-inércia REESCRITO (flip: 'Monaco'→Monaco_v2; 'Spa'→Spa_v2; v1s fora do
frozen; zero duplicatas) + t-novo (v1s arquivados válidos: sha conferido +
Track.from_waypoints; loader não vê archive/ por PARE). t4 do
test_track_mirror atualizado para o path arquivado (Monaco_v1 movido).
**Suite 25F/302P/3S** [desvio do declarado 25F/304P/2S: (1) os 2 testes
novos SUBSTITUÍRAM os 2 antigos de inércia (net 0); (2) composite_parity:45
(artefato Monaco_v1) virou skip condicional — consequência direta da
adoção]. doc-test verde. Comandos essenciais NO commit de fechamento (hábito N1).

## Estado
Monaco/Spa canônicos = conteúdo mirror (v2). Adoção CONFORME árvore pinada
(professor 3/3 → adotar + re-ancorar; ambos os ramos mantinham o swap pela
aprovação do dono). Pools 70-79 intactos. Hashes: 87419b1 → ce4e799 →
8c14f9f → 86a129c → fechamento.

ANEXO — ADOÇÃO-H-2-review (orchestrator, 2026-10-21)
Veredito: RATIFICADO ✓ (revisão de papel; zero acesso ao repo).
Cadeia: 87419b1 (ANEXO H-1-review, caminho absoluto) → ce4e799 (NITs N1-N3 +
errata R8 + NOTA-DEP fastf1 ==3.8.3) → 8c14f9f (prereg ANTES de mudança/medida)
→ 86a129c (professor-first + controles + swap) → 3604a80 (fechamento COM
Comandos — hábito N1). Shas: Monaco_v2 67ca11dc211c8c78 / Spa_v2
4b05f2c3bbc625fc (DISCLOSE R8) / Spa_v1 f83365bf26d0b1b1 no header. Loader
INTOCADO; v1s → archive/tracks_frozen_v1 com README; sem duplicatas inertes;
professor ANTES de aluno; 6 eps bit-idênticos; zero corridas; pools 70-79
intactos; PROJECT_STATE com tags [era v1]/SOB MIRROR, nada apagado.
R1 (R8-H1 editou congelado): errata escreveu r8_hypothesis DENTRO do Spa JSON
(2637c8→4b05f2c). ACEITO: aditivo, commit dedicado ANTES do prereg, re-pin com
DISCLOSE, zero runs no intervalo. REGRA: congelado = append-only via campo de
errata em commit dedicado + sha re-divulgado + re-pin no prereg seguinte ANTES
de qualquer run. Busca do literal 4.352/mi NEGATIVA — hipótese ABERTA (correto).
R2 (erro de pin da canária): critério pinado omitiu fora ≤25% da ERRATA #2.
TRATAMENTO CORRETO: nenhum re-pin pós-número; resultado pelo critério pinado +
ressalva explícita (Monaco 45% > 25%; Spa 20,8% ambos OK). "9/9 POR COMPLETUDE"
e B' mantido ✘ [era v1] com anotação SOB MIRROR = enquadramento conservador
correto. Promover B' a ✓ exige decisão de dono.
R3 (achado de instrumento, maior da sessão): off% professor-solo-frozen é
BASELINE — 24,3% no interlagos CANÔNICO; 0,36% histórico = era 10-carros/live.
Consequência: canária ERRATA #2 (fora ≤25%) DESCALIBRADA p/ solo-frozen (margem
zero no canônico). Números desta sessão valem (pin); TODO gate solo-frozen
futuro exige limiar re-ancorado em prereg. Fila.
R4 (controles fora do §8): 3 evals de diagnóstico não orçados. ACEITOS: solo
determinísticos, independentes da árvore de decisão, disclose completo. REGRA:
próximos preregs trazem cláusula "diagnóstico permitido" ou addendum commitado
antes de rodar controles.
R5: Monaco_v1 ABORTA no runner atual ("reta antes da SF = 0 m") — endurece o
era-v1 0/3 (o artefato nem aceitava grid). Livros corretos.
R6: mirrors MAIS dirigíveis que os v1s (Spa 32% vs 45,4%; Monaco 58,5% vs
ABORT) — adoção mais robusta do que no momento da aprovação.
R7: suíte 25F/302P/3S vs 304P/2S — desvio justificado (substituição net-0 +
skip condicional grácil composite_parity:45). Aceito; ver N1.
R8 (hipóteses): H-Mon não falsificada (aluno 3/3 sob mirror ⇒ gargalo era o
ARTEFATO); H-Spa sobrevive (aluno 3/3 nos 7.004 m — primeira medição completa).
Registro bidirecional honesto.
Q1 (barato, zero runs): Spa_v2 aluno = 3 voltas sob --laps default 2
(professores pararam em 2 exatas). Explicar a semântica de parada do caminho
neural (contador interno × cruzamentos do CSV). Não afeta veredictos.
Q2 (barato): definir nos livros a métrica "preso" (Monaco 118,5 s acumulado vs
12 s contíguo; Spa 57,1 s): v<2 acumulado ou contíguo? janela?
N1: preregs futuros: "suíte ESPERADA ±" + cláusula "desvio justificado no
fechamento".
N2: fila (não bloqueia): (a) re-ancoragem da canária solo-frozen (R3);
(b) qualidade do professor no Monaco_v2 (fora 56,9-58,5% >> 24,3% —
pure-pursuit × geometria do mirror; números de Monaco = qualidade BAIXA até
diagnosticar; research, prioridade do dono).

# Task ID: FASE-4-v15 (2026-10-21) — wiring composite no race runner: B3' FAIL MECÂNICO (evidência para o dono)
Zero pool (70-79 intocados) · mirrors/loader/v1s INTOCADOS · PROMOÇÃO = dono.

## Commits
5b2bcf0 (ANEXO ADOÇÃO-H-2-review verbatim) → 472cd94 (seção aberta: recon
wiring + Q1/Q2 respondidas) → d54b5fe (prereg ANTES de código/medida, com
RECONCILIAÇÃO pré-run dos absolutos pré-canônicos) → fixture pré-wiring (1200
ticks v10-cego) → 89598ef + f2c66f2 (wiring + 3 testes) → e5cd2ab (veredito
mecânico ANTES de ler números) → fechamento.

## Wiring (limitação 2 da FASE 4 RESOLVIDA)
Grupo `composite` no `--mixed`: parse_mixed/assign_groups/construção do
ctrl_comp (obs traffic + solo v10 npz + NumpyCompositeActor — o MESMO caminho
do --profile composite)/loop 3 controllers/export por grupo. PROTEÇÃO v10-cego:
corrida 1200 ticks seed 0 BIT-IDÊNTICA ao fixture pré-wiring (verde na 1ª
tentativa). Suíte 25F/305P/3S (ESPERADA ±; t-parity N/A — desvio justificado).

## B3' (6 corridas seed 0 DRY 600s, regime canônico, seriais)
CONTROLE 22,1% fora (REGIME OK) | cc 3674 · ALL-COMPOSITE: cc 752 (4,9×
menos!), 10/10, 0 par, fora 25,2% ≤ 29,9%, rol 140 ≤ 146, **MAS hesit 13**
(≤3 → FAIL; controle 3; R10 D3 REPRODUZIDO fora de sessão) · MISTAS: composite
acumula ~2× contatos/carro pós-largada que o edge (96,5 vs 47,6) e o
pós-largada composite 193/242 > ≤2 (absoluto pré-canônico NÃO re-ancorado
pelo prereg — GAP DE PIN divulgado); pace misto +33s vs ctrl-embaralhado ·
HOLD-AT (report): 9/10, 4 paradas — pilha multi-composite CONFIRMADA limitação.

## Veredito
**B3' FAIL → PARE** (sem re-pin/re-run). EVIDÊNCIA PARA O DONO: o valor de
segurança do composite sob regime canônico é MASSIVO (4,9× menos contatos que
o controle da mesma sessão; 0 paradas; 10/10; fora dentro do p75 do próprio
braço) ao custo de hesitações (13 vs 3 — R10 D3 confirmado) e pace (+4s solo;
+33s em campo misto). A PROMOÇÃO (race default = composite?) fica com o dono;
R13 mantém v10-cego.

## Diagnóstico pós-veredito (marcado)
zsh NÃO word-split variáveis não-quotadas ($VAR = UM argumento — 2 chains
abortaram em argparse antes de qualquer corrida); corrigido com args
explícitos. LIÇÃO de pin: ao re-ancorar absolutos de era, re-ancorar TODOS
(misti "≈0" ficou esquecido — o gap é meu).

ANEXO A — FASE-4-v15-review (verbatim):

FASE-4-v15-review: RATIFICADO ✓
Revisão de papel. Cadeia 5b2bcf0 (ANEXO verbatim) → 472cd94 (recon + Q1/Q2) → d54b5fe (prereg com reconciliação pré-run) → fixture pré-wiring → 89598ef+f2c66f2 (wiring + testes) → e5cd2ab (veredito antes dos números) → 7761984 (fechamento com Comandos) → 5eae120/2374348/d7c12e0. Árvore limpa; suíte 25F/305P/3S; zero pool; mirrors/loader/fastf1 intocados; promoção não decidida.

O que bateu:

Recon honesto e útil: o all-composite JÁ existia (--profile composite) — o prereg reescopou o item (a) para "validar, sem novo wiring" em vez de fabricar trabalho. Q1/Q2 resolvidos com código: --laps para no líder completar (professor-first sem flag = 2 voltas; re-baselines H-2 com --laps 99 = janela → Spa 3 voltas explicada, sem contador oculto); preso R3 (janelas 30s acumuladas) ≠ wanderer R4 (contíguo >60s) — métricas distintas, ambas válidas.
A §3 (reconciliação) é a estrela do prereg: re-ancoragem pré-run com derivação (fora ≤ p75 29,9% do R12 seco; rolante ≤ controle+10s) — legítima, não é re-pin pós-número. E os critérios que NÃO reconciliou falharam o gate honestamente.
Proteção bit-idêntica na 1ª tentativa (fixture 1200 ticks, teste permanente) — o wiring tocou só o branch --mixed.
FAIL mecânico honrado: PARE sem re-pin/re-run; gap de pin divulgado; o D3 do R10 reproduzido fora de sessão (13 vs 3 — o custo de hesitação do composite é real e sobrevive ao regime canônico; note que o próprio controle canônico hesita 3× vs 0 histórico — o regime também mudou o baseline).
Incidentes de shell (zsh SH_WORD_SPLIT, typo de flag, parêntese): falharam em parse, zero runs consumidos — disclose correto.
CATCH da revisão (R4) — assimetria das mistas: as mistas têm mais contatos totais que o all-v10 embaralhado (1808/2022 vs 1622) — heterogeneidade de comportamento é o risco, e isso precisa entrar no memo do dono. E a alegação "composite ~2× contatos/carro (96,5 vs 47,6)" fecha para a mista-2 (193/2 vs 381/8), mas na mista-4 os números implicam inversão (se 242 é a pós-largada do grupo composite: 60,5/carro vs edge 688/6 = 114,7/carro).

Questões baratas (zero runs; entram no próximo PASSO 0):

Q1' — tabela por grupo das DUAS mistas (pace, hesitações, pós-largada/carro: composite vs edge) + fechamento dos critérios "pace do grupo v10 ≈ controle" e "0 hesit no grupo v0" (o veredito listou só 2 FAILs — confirmar que os demais foram avaliados e passaram).
Q2' — confirmar zero CSVs parciais das chains mortas em parse (runs≠arquivos).
Regras que esta fase deixa:

REGRA (reconciliação sistemática): todo critério de gate enumerado no prereg com status ABSOLUTO / RE-ANCORADO (com derivação) / DROP — antes de qualquer run. O meu prompt carregou os 3 absolutos pré-canônicos; o agente reconciliou 2 e o terceiro virou FAIL evitável (honrado, mas evitável).
PADRÃO-OURO creditado: script de veredito commitado antes de ler números (e5cd2ab) — recomendado para todo ciclo gated daqui em diante.
MEMO DE PROMOÇÃO (a evidência em uma tabela — decisão sua):

opção
contatos (pós-larg)
rolante
hesit
leitura
A manter v10-cego	3674 (2482)	136s	3	status quo R13
B promover all-composite	752 (292) — 4,9× menos	140s (+4)	13	segurança massiva; D3 como custo declarado
C adoção parcial	1808/2022 — pior que all-v10 emb. (1622)	166s (+33)	4/3	contra-indicada pelos dados
D profile opt-in	—	—	—	só documentação + ressalvas

A adoção parcial (C) é refutada pela sua própria sessão; a decisão real é A × B (ou atacar o D3 antes). Qualquer flip de default = ciclo próprio com prereg.

[Nota do ajudante: passos (a) do MEMO — "adoção parcial" refere-se às corridas MISTAS da B3' como proxy de adoção parcial de campo; D = o --profile composite já é opt-in documentado. ANEXO apensado VERBATIM conforme o prompt ANTI-D3-1.]

# Task ID: ANTI-D3-1-P0 (2026-10-21) — Q1'/Q2' (errata aditiva; zero runs)
Q1a — tabela POR GRUPO das duas mistas (rolante por cruzamentos do grupo;
hesit on-track v<0,5 0,3-3s t>20; pós-largada t>20):
| corrida | grupo | n | rolante | hesit | fora% | pós-larg | /carro |
|---|---|---|---|---|---|---|---|
| MISTA-2 | composite | 2 | 202s | 4 | 20,8% | 193 | 96,5 |
| MISTA-2 | edge | 8 | 165s | 0 | 16,5% | 381 | 47,6 |
| MISTA-4 | composite | 4 | 177s | 2 | 22,2% | 242 | 60,5 |
| MISTA-4 | edge | 6 | 165s | 1 | 17,2% | 688 | 114,7 |
Q1b — critérios B3' NÃO reportados no veredito da fase (avaliados agora):
- "pace do grupo v10 ≈ controle (136s)": edge dá 165s nas DUAS mistas →
  FORA do ~ (≈+29s) — o grupo v10 desacelera no campo misto (não era
  critério de gate listado no veredito; o veredito listou só os 2 FAIL;
  estes eram os subcritérios das mistas cuja avaliação por grupo não foi
  impressa — agora fechados: pace FAIL-nas-duas, hesit-v10 PASS-na-2/FAIL-na-4).
- "0 hesitações no grupo v10": MISTA-2 = 0 (PASS); MISTA-4 = 1 (FAIL do
  subcritério — 1 episódio de 1 carro edge).
Q1c — escopo da alegação "~2× contatos/carro": a frase era MISTA-2-específica
(96,5 vs 47,6). A MISTA-4 INVERTE (60,5 composite vs 114,7 edge). Leitura
correta: o custo/carro NÃO é monotônico na fração composite — em minoria o
composite acumula mais; em maioria o edge acumula mais (a fronteira de
contato entre grupos). Alegação de 2× RETIFICADA: vale só p/ mista-2.
Q2' — zero CSVs parciais: 12 arquivos no f4v15-wiring (6 corridas ×
csv+events) + 6 logs; grep de nomes fora do padrão = vazio; timestamps coerentes
com as 6 corridas bem-sucedidas (14:36→14:57). As chains mortas em parse
não geraram NENHUM artefato (runs≠arquivos confirmado).

# Task ID: ANTI-D3-1-P1 (2026-10-21) — diagnóstico READ-ONLY das 13 hesitações (zero runs)
Extração completa (all-composite FASE-4-v15; critério on-track v<0,5 0,3-3s t>20):
13 episódios; TODOS com th=0,00 (freio-forte); 12/13 com gate>0 na janela
(g_med 0,3-1,0; g_max 1,0 em 9) — NÃO é gate-chatter (o gate fica ABERTO);
13/13 com |r|>0,1 (o residual ATIVO); authority='policy' em todos (o composite
É o policy ativo). Concentração: 8/13 em s≈2289-2318m (mesma zona de fila de
curva; ALO/GAS/LEC/PER/PIA em ticks distintos) + 3 na volta 1 em s≈104-112m
(GAS/VER t≈67-68s) + VER t=205s. Durações 0,4-1,0 s.
(i) CLASSIFICAÇÃO: **residual-brake dead-stop** (gate persistente + comando
freio do residual → parada morta on-track até o carro à frente sair do raio D).
Menção: #4 GAS (g=0) e #1 ALO (g_med 0,12) são edge-case (gate fechado mas
residual r_med 1,09/8,07 — g·r pequeno; freio vem do m_solo? investigação
futura); 11/13 fecham a classe com g>0.
(ii) MECANISMO HIPOTÉTICO ÚNICO: o residual aprendeu "carro à frente (no raio
D) = freia forte" do car-following do professor, SEM a nuance "retoma quando o
gap abre" — em filas de curva (s≈2300) o carro para MORTO e espera; a base
(v10 solo) retomaria sozinha. O mecanismo de camada que ataca exatamente este
modo: **progress-guard com fade gate→base** (após N ticks sem Δprogresso com
gate aberto, esmaece g→0 até o progresso voltar — a base reassume).

# Task ID: ANTI-D3-1 (2026-10-21) — progress-guard fade gate→base: FAIL MECÂNICO → D3 ESTRUTURAL; PARE
Zero pool (70-79 intocados) · promoção = dono · veredito pré-commitado (PADRÃO-OURO).

## Commits
57a9342 (prereg ANTES de código/medida) → 7dde1d8 (guard no ÚNICO caminho
composite + 5 testes; v10-cego BIT-IDÊNTICO ANTES das corridas) → 33610ba
(anti_d3_verdict.py ANTES dos números) → 2 corridas seed 0 DRY (seriais;
controle 1º) → probe pós-veredito bbe9512/29399d4/2f29c98/18c00a2 (cada
versão commitada antes do run) → fechamento.

## Resultado (veredito verbatim)
CONTROLE 22,1% | 0 par | hesit 3 | 10/10 | rol 136,0 | cc 3674 (pós-larg
2482) — PROTEÇÃO bit-idêntica à F4v15 ✓. ALL-COMPOSITE (guard) 26,1% | 0 |
hesit 12 | 10/10 | rol 145,0 | cc 1520 (846).
```
PRIMÁRIO hesit composite (12) <= controle (3): FAIL
Não-reg cc (1520) < controle (3674): PASS
Não-reg paradas = 0: PASS
Não-reg 10/10 voltas: PASS
Não-reg fora <= 29,9%: PASS
Não-reg rol (145.0) <= controle+10 (146.0): PASS

ANTI-D3-1: FAIL — PARE; sem re-pin/re-run
```

## Por que falhou (probe pós-veredito; ZERO runs)
Constantes EFETIVAS: tick lógico 0,1s (10 Hz) ⇒ trigger 0,5s @ v<5 m/s
(18 km/h) — o prereg pinou em TICKS, não segundos. (1) 9/10 carros
DISPARAM NA LARGADA (t=0,4-0,6s; razões ON/OFF 0,80/0,60 = fade próprio;
HAM exceção: gate nominal 0 na largada, dispara t≈99,6s): aceleração normal
0→5 m/s = 8 ticks "sem progresso" com gate aberto; o fade deixa os carros
MAIS RÁPIDOS no funil (PIA 6,67 vs 4,84 m/s em t=1,0s) → pós-largada
292→846, cc 752→1520. (2) Hesitações (0,4-0,6s) terminam antes de
trigger+fade; o contador (janela 0,3-3s) engole resgates por construção —
PRIMÁRIO quase-insensível ao mecanismo por PIN; a liberação das hesitações
é NATURAL (fila descarrega → d_min > D(v→0)=40m → g nominal→0; 4/13 na OFF
sem guard). (3) o limiar 5 m/s captura crawls de tráfego como "sem
progresso" — o guard cicla fade em seguimento lento e mutila o residual
exatamente onde ele previne contato.

## Discloses
DESVIO DE INSTRUMENTO: o prereg mandava o gate NOMINAL no instrumento; o
código gravou o g_eff (`g = g_eff` antes de `gates[i] = g`; comentário da
linha 798 contradiz o código) — nominal irrecuperável do CSV ON (probe usou
a corrida OFF como referência de prefixo). Probe v1 "0 disparos ON" =
artefato (tick-0 + g_eff≤0,01 sob fade cega o branch nominal), suplantado
pela §Divergência. Suíte 25F/310P/3S (ESPERADA ~309P ±; base 305+5).
Runs≠arquivos: 2 corridas = 6 arquivos coerentes.

## Veredito de árvore (ramo 3)
D3 ESTRUTURAL à camada; a decisão A×B VOLTA AO DONO com o D3 como CUSTO
PERMANENTE e o guard como evidência CONTRA fades de camada. Nada promovido;
v10-cego permanece o default (R13).

# Task ID: SANIDADE-0-P0 (2026-10-20) — branch feat/sanidade-produto; NIT N1 executado; ANEXO PENDENTE
NIT N1 (review ANTI-D3-1): progress-guard REPROVADO isolado atrás de
`--pguard` DEFAULT-OFF (run_race_10_cars __init__ pguard=False + bloco do
composite condicionado a self.PGUARD_ENABLED; race_diagnostic --pguard
store_true + pguard na linha de identidade; 3 sítios de construção).
Flag-off = comportamento pré-ANTI-D3-1 bit-idêntico à F4v15 e o instrumento
volta a carregar o gate NOMINAL (contrato do prereg 57a9342, violado na
implementação original — desvio divulgado no fechamento ANTI-D3-1).
Teste t6 novo (assinatura default False; bloco condicionado; argparse
store_true; identidade) — 6/6 verdes.

ANEXO PENDENTE: a review ANTI-D3-1 (Task ID ANTI-D3-1-review) NÃO constava
do prompt SANIDADE-0 e não foi localizada em nenhum sítio acessível
(sessions/dsh-continuacao.md estagnado na era PÓS-CICLO-2; worklogs
externos inexistentes; grep ANTI-D3-1-review em /home/jovitor/unicamp =
vazio). NADA FABRICADO (precedente LARGADA-4/ANEXO B): aguardando o texto
verbatim do orquestrador para commit dedicado. O conteúdo acionável citado
pelo prompt (NIT N1) foi executado; o restante da review não é conhecido.

# Task ID: SANIDADE-0 (2026-10-20) — defeitos do produto: M1/M3 FAIL saem; M2 verde no bundle; PARE
Zero promoção/re-pin/default · veredito mecânico pré-commitado · 70-73 consumidos (74-79 virgens).

## Commits
158e9f9 (NIT N1 --pguard DEFAULT-OFF + t6) → sanidade_diag v1→v2.2
(D0-D3) → 1007636 (PREREG c/ reconciliação sistemática, antes da impl) →
d42d947 (M1/M2/M3+bundle+5 testes) → veredito (auto-testado nas âncoras
F4v15) → 6 corridas seriais → 90e5b63 (evidência) → 7afe4a8 (árvore:
bundle = só M2) → fechamento.

## Diagnóstico (D0: coluna lat do CSV = MÓDULO; slat=obs4×hw é o canal válido)
D1: 2482 = 82,6% t>60s; t<60 = 1624; T1 |Δlat| 0,4m (10/10 <1,7 — campo
sobreposto); EMPURRÃO 27% × PILOTAGEM 73%. D2: excursão mediana 4,2s ambos
braços; wanders 0; reentrada-contato 38% (gap 3,0s). D3: controle 41
janelas/247s/6 deadlocks (|steer| ~0,05 — NINGUÉM esterça; 29 DECISÃO × 12
FÍSICA); composite 7/33s/0. s70-73 SECAS (weather-scan).

## Veredito (verbatim)
PROTEÇÕES: P1 v0 s0 OFF = 3674/2482/136/3/22,1 e P2 comp s0 OFF =
752/292/140/13/25,2 — AMBAS BIT-IDÊNTICAS às âncoras F4v15 (zero vazamento;
guard-off restaura o pré-guard = NIT N1 confirmado).
```
G1 v0 s70:  cc 1380 (t<60s 942)  | hesit 0  | rol 149 | off 25,7 | exc 5,1s | colado 66,6s | dead 0
G2 comp s71: cc 274 (t<60s 222)  | hesit 14 | rol 153 | off 30,0 | exc 6,0s | colado 2,4s  | dead 0
G3 v0 s72:  cc 1854 (t<60s 1352) | hesit 4  | rol 145 | off 25,6 | exc 4,0s | colado 99,2s | dead 1
G4 comp s73: cc 416 (t<60s 340)  | hesit 11 | rol 165 | off 30,3 | exc 4,5s | colado 17,8s | dead 0

M1: FAIL — research-negativo, SAI do bundle
M2: PASS — embarca no bundle
M3: FAIL — research-negativo, SAI do bundle

SANIDADE-0: PRIMÁRIO(S) FAIL — mecanismo(s) sai(m) do bundle; sem re-pin/re-run/promoção
```

## Leitura (marcada; zero runs)
M1: c60 −42%/−17% (942/1352 vs 1624) — direção positiva, longe do −50%
(re-empacotamento F1b de novo). M2: 4/4 (comp 4,2→6,0s = retorno mais
lento do ângulo raso, exatamente o previsto na re-ancoragem que REJEITOU a
leitura literal "2× melhor"). M3: FAIL por margens (1 deadlock s72 + comp
17,8>16,5) MAS v0 colado 247→66,6/99,2 (−60/−73%) e comp 33→2,4/17,8 —
move a métrica massivamente; dado p/ o dono. Não-reg rol/off: tetos de UMA
realização s0/quantil vs dispersão R7a (rol 139-192; comp-fora 25,1-41,2)
— FAILs marginais consistentes com variância de seed (disclose; sem
re-run). G2 cc 274 = menor cc do instrumento canônico (âncora 752).

## Discloses
ANEXO review ANTI-D3-1 PENDENTE (texto ausente do prompt e de todo sítio
acessível — nada fabricado; precedente LARGADA-4). D0: coluna lat do CSV é
o MÓDULO — análises futuras de lateral usam obs4×half_width. Suíte
25F/316P/3S (310+t6+5). Bundle --modo espectador = SÓ M2 (7afe4a8);
--grid staggered e --anti-glue ficam como research opt-in default-OFF.

# Task ID: SANIDADE-1b (2026-10-20) — M3-v2 ARQUIVADO (tetos mataram a separação); M2 atribuição LIMPA; PARE
Zero retreino/promoção/flip/re-pin · 74/75 consumidos (76-79 virgens) · suíte 25F/322P/3S (número EXATO do prereg).

## Commits
33396f6 (ANEXO SANIDADE-0-review VERBATIM, commit dedicado — pendência (b))
→ 8b95f69 (caveats help/docs — pendência (a)) → 4c7d96a (D4/D5) → 87214c7
(prereg c/ reconciliação + predição M2 31,8% pré-registrada) → e9d1877
(M3-v2: _anti_glue_step COMPARTILHADO neural+professor por HERANÇA; v1
MORTO atrás da mesma flag; +6 testes dos tetos; bug do cooldown-bypass
pego pelos testes) → d32036d (veredito --selftest OK: reproduz
F4v15+SANIDADE-0 dos CSVs) → ae1367d (evidência 7×3 arquivos) → fechamento.

## D4/D5 (zero runs)
D4: FRICÇÃO INOCENTE (shove≈0 em 0,01 e 0,05); BREAKER marginal;
PREVENTIVO = custo dominante (exposição comp 194-213 car·s; taxa de
excursão na janela DOBRA 0,144-0,169/s vs 0,077/s). D5: deadlock s72 =
GAS×PIA reentrando em paralelo (PIA no gap-hold do M2; GAS 6s sob o
breaker) = ARTEFATO M2×M3.

## Veredito (verbatim)
```
M3-v2: FAIL — ARQUIVADO research-negative COM LEADS (D4 preventivo-custo;
D5 interação M2×M3; ativo v1 colado −73/−60% v0); não-reg FAIL
[G2 cc 1536>752; G4 cc 964>752, off 30,6>29,9, rol 159>146];
ABSOLUTO deadlocks FAIL [gates 3/1/3/2]
M2: atribuição limpa registrada (fora dentro do teto)
```
Proteções P1/P2 BIT-IDÊNTICAS às âncoras F4v15 (zero vazamento v2).

## Atribuição M2 (memo p/ o dono — o resultado de ouro)
Comp M2-only s0: cc 516 (−31% vs 752), pós-larg 98, hesit 6 (−54% vs 13),
colado 16,4s (−51%), wand/dead 0, fora 28,0% (Δ+2,8pp ≤ 29,9 — gatilho de
escala NÃO dispara), exc 4,2→4,6s, rol 147. Predição 31,8% SUPERESTIMOU:
os +1,8s×219 da review eram em parte custo do M3 (bundle); M2 puro = +0,4s.
Helps atualizados pós-atribuição (solo MEDIDO; opt-in research; adoção=dono).

## M3-v2: leitura marcada
Os tetos mataram o ingrediente ativo — a dose crônica do preventivo era O
que separava: v0 colado 66,6/99,2 (v1) → 133,0/145,4 (v2), dead 0/1 → 3/3;
comp colado 51,6/50,6 = 3× o teto 16,5; cc comp 1536/964 > 752 (preventivo
oscilante 1s-on/2s-off + breaker que desiste). LEAD: custo (D4) e separação
são O MESMO mecanismo — M3 futuro precisa de OUTRO princípio de separação
(convenção de lado/precência), não limitação de dose.

## Discloses
PIN COLLISION (erro MEU): o ABSOLUTO "0 deadlocks em TODOS os 7 runs"
colide com a bit-identidade de P1 (a âncora F4v15-v0 TEM 6 deadlocks —
impossível por construção nas proteções); os runs de TRATAMENTO falham o
absoluto de qualquer forma (3/1/3/2) — veredito inalterado. Errata R4 da
review aplicada (seção SANIDADE-0: −73/−60%). Suíte 25F/322P/3S exata.

# Task ID: VARIEDADE-1 (2026-10-21) — camada de variedade OPT-IN: TODOS OS CRITÉRIOS PASS; PARE
Micro-ciclo; determinismo NÃO morre (infraestrutura); zero pool; suíte 25F/326P/3S (322+4 exata).

## Commits
083ddea (ANEXO SANIDADE-1b-review verbatim dedicado) → b237aeb (prereg c/
reconciliação ENTRE PINS — regra nova, 1ª aplicação, zero colisões) →
95a6a16 (impl camada-only + 4 testes) → 9b97da6 (veredito; --selftest OK)
→ c06dd7e (evidência 6 corridas) → fechamento.

## Mecanismo
--variedade N (default 0 = OFF bit-idêntico, provado em corrida); N>=1 =
PRNG próprio sha256(seed//variedade//N) (padrão weather_rng) perturbando
SÓ ICs: jitter grid ±0,5m/±0,3m (43≤45m; Δlat min 3,2m > 1,8m) + mu_nominal
×U[0,98,1,02] no spawn ([1,764,1,836]⊂[1,7,1,9]; canal dinâmico e leis dos
controllers intactos); variedade em LINHA DE LOG, nunca no schema; N<0
fail-loud; compõe com --modo espectador.

## Veredito (verbatim)
```
PROTEÇÃO P1 == F4v15-v0: BIT-IDÊNTICO
PROTEÇÃO P2 == F4v15-comp: BIT-IDÊNTICO
D2 == D1 byte-a-byte + stats: BIT-IDÊNTICAS: PASS
D3 diverge <tick 200: vs base t=0, vs D1 t=0: PASS
D1-D4: 10/10 voltas e 0 paradas: PASS (4×)

VARIEDADE-1: TODOS OS CRITÉRIOS PASS — camada entregue como OPT-IN
(default 0; canônico intocado; adoção = dono). Contatos variam
naturalmente (sem teto — report acima).
```

## Números
A MESMA seed 0 agora produz corridas distintas e plausíveis por N: cc
3674 (canônico) → 2052 (var=1; D2 REP bit-a-byte igual) → 1068 (var=2) →
2336 (comp var=1). D1/D3 off 21,6% rol 134; D4 comp hesit 24/rol 156/off
30,9 (realização nova, report sem teto). 10/10 + par 0 em todas.

## Leitura
O determinismo SOBREVIVEU à variedade (D2==D1 byte-a-byte; flag OFF
reproduz âncoras) e a variedade FUNCIONA (streams distintas por N — D3
diverge no tick 0, <200 por construção, o critério valida a derivação).
Reconciliação ENTRE PINS (regra nova) aplicada ANTES do commit — a PIN
COLLISION do 1b agora é prevenida por regra, não por sorte.

## Disposição
Camada OPT-IN; comando do dono nos Comandos essenciais (GUI --variedade 1);
seed 0/var 0 = canônico bit-idêntico. Pools: zero consumo novo; 76-79 virgens.

# Task ID: SAIDAS-1 (2026-10-21) — diagnóstico pré-registrado de saídas solo por curva: VEREDITO MECÂNICO PASS; PARE
Ciclo de diagnóstico mecânico self-contained; zero corridas gastas (re-análise F4v15); pools 76-79 virgens; decisão A×B aberta e congelada; suíte 25F/326P/3S mantida.

## Commits
1c24988 (PREREG_SAIDAS_1.md com reconciliação sistemática, 11 complexos de curva derivados de interlagos_v2.json com gap merge 40m, seed 42 de bootstrap) → 7ea2f27 (scripts/saidas_verdict.py com --selftest mecânico verde: SPIN, SLIDE, LINHA-RETA, RUIDOSO, bootstrap e geometria) → 736102d (tabelas de evidência Q1-Q4 emitidas em experiments/saidas-1/) → fechamento.

## Reconciliação F4v15 Âncoras
- Perfil A (v10-cego): 22,1167% fora vs âncora 22,1% (DIFF: 0,0167 pp <= 0,1 pp) -> PASS. 180 eventos, mediana 4,2 s [IQR: 1,3–10,5 s].
- Perfil B (composite): 25,2133% fora vs âncora 25,2% (DIFF: 0,0133 pp <= 0,1 pp) -> PASS. 219 eventos, mediana 4,2 s [IQR: 1,9–8,7 s].

## Respostas Q1–Q4 (Veredito mecânico)
- Q1 (Proporção Solo, D=15m, T=5s):
  - Perfil A (v10-cego): 46,7% (84/180) [IC 95%: 39,4% - 53,9%] (Sensibilidade: D=10m 57,2%, D=20m 38,3%).
  - Perfil B (composite): 83,6% (183/219) [IC 95%: 78,5% - 88,1%] (Sensibilidade: D=10m 88,1%, D=20m 78,5%).
  - Diferença: +36,9 pp a mais de isolamento no composite (ICs não se cruzam).
- Q2 (Top-5 Complexos de Curva):
  - 4 curvas concentram 91,7% das saídas de A e 78,1% das saídas de B:
    1. C01 Descida do Lago (T4/T5): A 48 (26,7%, 52,1% solo) | B 50 (22,8%, 84,0% solo).
    2. C06 Bico de Pato (T10): A 40 (22,2%, 55,0% solo) | B 38 (17,4%, 100,0% solo).
    3. C08 Junção (T12): A 40 (22,2%, 52,5% solo) | B 41 (18,7%, 90,2% solo).
    4. C07 Mergulho (T11): A 37 (20,6%, 43,2% solo) | B 42 (19,2%, 95,2% solo).
    5. A: C09 Subida dos Boxes (7 / 3,9%); B: Retas (20 / 9,1%) seguido por C10 Senna S (10 / 4,6%).
- Q3 (Modos de Saída pré-2s):
  - LINHA-RETA (tangencial/subesterço): A 106 (58,9%) | B 143 (65,3%).
  - SLIDE (deriva lateral >=10°): A 74 (41,1%) | B 76 (34,7%).
  - SPIN (|yaw_rate| >= 45°/s sust. >=0,5s): A 0 (0,0%) | B 0 (0,0%).
- Q4 (Velocidade de Entrada a -1s):
  - Junção (C08): A med 35,4 km/h (IQR 3,2), B med 36,8 km/h (IQR 6,7).
  - Mergulho (C07): A med 44,4 km/h (IQR 22,1), B med 42,1 km/h (IQR 24,2).
  - Bico de Pato (C06): A med 46,9 km/h (IQR 0,7), B med 46,8 km/h (IQR 1,3).
  - Descida do Lago (C01): A med 60,2 km/h (IQR 3,7), B med 60,0 km/h (IQR 2,4).

## Conclusão e Disposição
A reclamação do dono ("há curvas que eles saem mesmo estando sozinhos") foi 100% corroborada no Perfil B (83,6% das saídas acontecem em isolamento total contra 46,7% no A). No Bico de Pato, 100% das saídas de B são solo. As saídas não são piruetas (0% spin) nem descontrole de alta velocidade (velocidades lentas 35–60 km/h e IQRs estreitos). Decisão A×B permanece congelada; pools 76–79 intactos.

# Task ID: ERRATA-SAIDAS-1 (2026-10-21) — commit de erratas R1–R4 (ZERO corridas)
Ciclo de commit de erratas do diagnóstico SAIDAS-1 ratificado pelo orquestrador (SAIDAS-1-review).
Orçamento estrito: ZERO corridas; pools 76–79 VIRGENS; decisão A×B ABERTA e CONGELADA com o dono; suíte 25F/326P/3S mantida.

## Commits
- ce895cd (fix(saidas-1): correções R1–R4 + saidas_verdict.py re-rodado com selftest verde e cross-check aritmético)
- HEAD (docs(saidas-1): ANEXO_SAIDAS_1_ERRATAS.md + registro de estado e worklog do ciclo de erratas)

## Resolução das Erratas Obrigatórias (R1–R4)
- **R1 (Consistência Aritmética Q1×Q2 & "O Número que Moveu")**:
  - Cenário (iii) verificado empiricamente: erro de digitação/display no markdown do chat resumo (onde C09 Subida dos Boxes constou com 42,9% = 3 saídas solo aparentes).
  - Nos dados brutos (`1_controle.csv`), no código (`saidas_verdict.py`) e em todos os CSVs emitidos (`tabela_q2_curvas.csv`), C09-A sempre teve 0 saídas solo (0/7 = 0,0%).
  - Zero números moveram no código ou nos CSVs. No relatório textual, C09-A foi corrigido de 42,9% para 0,0%.
  - Fechamento aritmético exato: Perfil A = 25 (C01) + 22 (C06) + 21 (C08) + 16 (C07) + 0 (C09) = 84 == total Q1 84 (46,7% [39,4%; 53,9%]); Perfil B = 183 == total Q1 183 (83,6% [78,5%; 88,1%]).
  - Cross-check automatizado adicionado ao `saidas_verdict.py` com assertion fail-loud.
  - Headline de superioridade relativa do isolamento de saídas sobrevive intacto: B - A = +36,9 pp; ICs 95% estritamente disjuntos.
- **R2 (Dispersão Q4 Segregada por Curva)**:
  - C01 Descida do Lago e C06 Bico de Pato: IQRs ultrabaixos (<= 3,7 km/h; C06 IQR 0,7 a 1,3 km/h = repetição determinística do traçado volta a volta).
  - C07 Mergulho: IQR amplo (22,0 a 23,6 km/h, velocidades entre 31 e 72 km/h = múltiplos modos de falha / tráfego residual; insumo direto para professor).
  - C08 Junção: IQR intermediário (3,2 a 6,7 km/h).
  - Velocidades medianas (35 a 60 km/h) plenamente compatíveis com os raios das curvas.
- **R3 (Grandeza de Concentração Espacial)**:
  - Esclarecido formalmente que a métrica mede % de EVENTOS de saída (91,7% em A e 78,1% em B nas top-4 curvas), não tempo cumulado fora.
- **R4 (Reconciliação e Tolerâncias)**:
  - Rotulagem canônica adotada: "reconciliação dentro da tolerância pré-registrada (Δ <= 0,1 pp)" com Δ = +0,0167 pp em A e Δ = +0,0133 pp em B (180 e 219 eventos exatos; duração mediana 4,2 s).
  - Registro pós-hoc no PREREG esclarecendo que SLIDE foi definido e computado como deriva lateral pontual |beta| >= 10° na janela de 2 s com guard de velocidade (>= 2,0 m/s), enquanto a exigência de sustentação >= 0,5 s era exclusiva de SPIN.

## Disposição e Próximos Passos
- Decisão A×B: Permanece ABERTA e CONGELADA com o dono.
- Insumos de curvatura e dinâmica (C01, C06, C07, C08) prontos para o planejamento do professor Monaco_v2.
- Pools 76–79 virgens; zero corridas gastas.


# Task ID: PROF-MONACO-1-P0 (2026-10-22) — onboarding + erratas R5-a/R5-b + NITs; zero runs de sim
Onboarding: PROJECT_STATE (header ERRATA-SAIDAS-1) + AUDITORIA_RL.md (existe,
58 KB) + ANEXO_SAIDAS_1_ERRATAS.md lidos; handoff ai-memory mais recente
(01a15f60, ERRATA-SAIDAS-1) aceito.

## ANEXO — ERRATA-SAIDAS-1-review (orquestrador Z.ai, 2026-10-22) — VERBATIM
Veredito: RATIFICADO ✓ (revisão de papel; sandbox sem repo), com 1 verificaçãode proveniência prescrita + 2 reconciliações exigidas (R5-a/R5-b).

Cross-check aritmético CONFERE (script do revisor, tudo PASS): identidadeQ1×Q2 exata nos 2 perfis — A: 25+22+21+16+0+0+0 = 84 == 84/180 = 46,7%[39,4;53,9]; B: 42+38+37+40+2+24 = 183 == 183/219 = 83,6% [78,5;88,1];headline Δ = +36,9pp PRESERVADO (não o 35,2pp condicional ao cenário (i));ICs estritamente disjuntos (53,9 < 78,5; gap 24,6pp); % por célula recontadosexatos; top-4 91,7%/78,1%; decomposição B fecha em DUAS granularidades(tabela: top-4 171/157 + C09 3/2 + R/O 45/24; texto R1: reta 20/11 + C10 10/2demais 18/13 — R/O = reta+C10+C11/C02/C05 = 45/24); reconciliação R4 Δexatos 0,0167/0,0133pp; suite 25F/326P/3S invariante; 2 commits monotônicos;zero corridas; pools 76–79 virgens; NITs E5 resolvidos no prereg.
R1 (cenário iii): INTERNAMENTE COERENTE e falsificável — 42,9% × 7 = 3,003 → acélula digitada implicava EXATAMENTE os 3 eventos do pin; a asserção fail-loudΣ==Q1 fecha a classe de erro. Prova definitiva é de PROVENIÊNCIA: git log -p--follow experiments/saidas-1/ entre 36cdff3 e ce895cd não deve tocar célulade dados; se tocar, esta ratificação REVERTE.
R5-a (ACHADO do revisor): C07 IQR-B — original 24,2 vs republicado 23,6 (Δ 0,6não é arredondamento; A: 22,1 vs 22,0 é compatível). Reconciliar contra o CSV;errata de 1 linha. NÃO-gating (qualquer valor em 22–24 sustenta "heterogêneo =insumo do professor"), mas o insumo precisa do número canônico.
R5-b (ACHADO do revisor): Reta-B solo — original 16/20 = 80% vs errata 11/20 =55% (Δ 5 eventos). Mesma prescrição; o LEAD do professor carrega o númerocanônico. Ambos apontam para novos display-slips do PARE original (reforçariamo cenário iii) — se o CSV bater com o ORIGINAL, a errata reportada é que erroue a ratificação da tabela republicada reverte.
NITs não-gating: (1) header "ratificado pelo orquestrador" — rotular eras;(2) divulgar se a re-execução regenerou CSVs byte-idênticos; (3) confirmarrotulagem "C10 (Senna S)" contra o catálogo do código.
Fila: PROF-MONACO-1 emitido (professor Monaco_v2; saidas_verdict.py comoinstrumento de desfecho; baseline = tabelas corrigidas; lead C07 heterogéneo preservado). A×B segue do dono, aberta.
Por que Monaco agora: é o gargalo medido — professor com fora 56,9% e aluno B' com 45% + preso 118s sob mirror. O ciclo responde a pergunta que trava a Meta A e a ressalva da B': o fora é herdado dos rótulos do professor ou degradação do aluno — com as 2 falsificações pinadas antes dos dados.

## Execução do PASSO 0 (probe scripts/prof_monaco_p0.py commitado antes do uso)
- PROVENIÊNCIA R1 (decisiva): `git diff 36cdff3 ce895cd -- backend/experiments/
  saidas-1/` = **VAZIO** — nenhuma célula de dados tocada; a ratificação SEGUE
  (1 linha, conforme prescrito).
- R5-a: IQR C07-B recomputado do eventos_saidas_detalhados.csv BRUTO =
  23,6327 → **CANÔNICO 23,6** (o republicado CONFIRMA; o "original 24,2" era
  display-slip). C07-A raw = 21,9853 → 22,0 exato (compatível).
- R5-b: Reta-B solo do BRUTO = **11/20 = 55,0%** (a errata CONFIRMA; o
  "original 16/20=80%" era display-slip). Ratificação da tabela republicada
  SEGUE em ambos.
- NIT-1 (eras): rótulo aplicado à seção SAIDAS-1 do PROJECT_STATE (veredito
  ratificado na SAIDAS-1-review; execução/erratas ratificadas na
  ERRATA-SAIDAS-1-review; R5 consolidadas aqui).
- NIT-2 (byte-idêntico): re-execução do saidas_verdict nas F4v15 regenera
  **AS 6 TABELAS BYTE-IDÊNTICAS** (eventos + q1 + q2 + q3 + q4 + resumo) —
  a re-execução do ce895cd fica PROVADA e vira o golden test da F2.
- NIT-3 (C10): o catálogo do CÓDIGO (build_corner_definitions) dá C10 =
  'Senna S (T1/T2)' s∈[2748,3; 2852,3] κmax 0,0311 — o primeiro complexo
  pós-SF (2655) — CONFIRMA a rotulagem por geometria; RESSALVA de margem: a
  banda match_corner (±30 m) cobre 96 dos 114 m da zona anatômica da
  LARGADA-F0 (2699,7-2814) — os 18,6 m iniciais da zona caem em 'Reta' no
  instrumento (consistência de margem, não erro de rotulagem).
- DISCLOSE extra: ANEXO_SAIDAS_1_ERRATAS.md existe em DUAS cópias rastreadas
  idênticas (raiz + backend/, commit d3965e4 — gêmeas da sessão de erratas);
  ambas recebem o §8 R5 para permanecerem idênticas; canônica = backend/ (a
  linkada pelo PROJECT_STATE).
- Orçamento até aqui: ZERO sims (apenas re-execução READ-ONLY do instrumento
  em artefatos existentes). Pools 70-79 e 76-79 INTOCADOS.

# Task ID: PROF-MONACO-1 (2026-10-22) — FALSIDICAÇÃO-Q4 (PARE); Q1 reta-no-top-1; erratas R5/R6
READ-MOSTLY; prereg 2aa018c antes de tudo; zero reparo/treino/10-carros; pools intocados; 12/14 sims.

## Commits
99ec615 (P0) → 2aa018c (prereg §10) → 1ecf52d (instrumento golden) → 12
sims → 205c2c6 (evidência + verificação) → fechamento.

## Veredito (bateria 600 s; ver ANEXO_PROF_MONACO_1.md para tabelas Q1-Q4)
Q4-mecânico: FALSIDICAÇÃO-Q4 — ALUNO 45,00% ABAIXO do PROFESSOR 56,93%
(−11,9 pp; determinístico) → PARE IMEDIATO: 'herdado dos rótulos' e
'degradado' ambos refutados; o gargalo da Meta A é o PRÓPRIO professor.
Q1-mecânico: RETA no top-1 (24,4%; hairpin 7,3%) → FALSIDICAÇÃO-Q1
report-only → lead REJOIN-CASCATA. Q3: 94,6%/92,4% cascata ≤10 s; 0
wanderers. Q2: C03 determinística IQR 0,5; C04 prof única com spin.

## Erratas consolidadas
R5-a 23,6; R5-b 11/20=55,0 (P0, raw); R6 NOVA: preso canônico 237,0 s
(era dividiu 1185 ticks por 10 — taxa 5 Hz); metaA era 600 s; calibração
κ perfil×builder (§10).

## Verificações
Paridades bit-idênticas; V1 seeds degeneres (solo+seca = seed sem canal —
1 realização + 4 réplicas; ICs degenerados); V2/V2b bateria ≡ ADOÇÃO-H-2
bit-a-byte; golden Interlagos 6 tabelas byte-idênticas (permanente);
NIT-1/2/3 do P0 aplicados.

## Lições
(1) Baterias multi-seed em SOLO precisam de canal de variância (o seed só
age via clima COM transição ou --variance/--variedade); (2) R3 do runner
conta LINHAS de CSV 5 Hz (×0,2 s) — nunca dividir por 10 (4º caso da
classe exibição temporal, agora 2×); (3) "N voltas" em eps com cap de
ticks = voltas COMPLETAS, não a janela; (4) expectativa de curva
(hairpin) caiu para churn de reentrada — o mecanismo real do fora.

# Task ID: FONTE-1-P0 (2026-10-22) — onboarding + guarda + disclose-254 + inventário F0; zero sims
Guarda anti-duplicata: 0 commits FONTE-1 pré-existentes → ciclo NÃO
executado, PROSSEGUIR. Onboarding: PROJECT_STATE ([NOTA-DEP]:1634) +
AUDITORIA_RL + worklog + handoff 01a15fda (era PROF-MONACO-1) lidos.
DISCLOSE-254 aplicado ao ANEXO_PROF_MONACO_1: 254,5 s/ep = 1272,4/5
(tabela_anatomia, 5 eps da bateria); os 3 eps do B' original são
bit-idênticos (conferidos ep1/2/3) → a média deles daria o mesmo valor;
"270 s/ep" não reconcilia (NIT aberto, não-gating).
F0: inventário classificado em experiments/fonte-1/f0_inventario.md —
(i)=3 (schedule/driver_db/Ergast já-jolpi.ca), (ii)=2 (track_loader
get_session+circuit_info; driver_db get_session "R" — todos em camadas
LEGADAS com NECESSIDADE (i) ou supersede mirror), (iii)=mirrors/F1DB
intocáveis, (iv)=caches congelados (96K+935M) + archive.
ACHADO: fastf1 3.8.3 PINADA já tem ergast BASE_URL=api.jolpi.ca —
Jolpica drop-in SEM upgrade (registrado p/ FONTE-2, requirements
intocado). Classe (ii) não-vazia → PROBE-C obrigatório. Zero sims;
pools intocados.

# Task ID: FONTE-2-P0 (2026-10-22) — guarda + ACHADO-P0 + NIT Jolpica + mapa de acoplamento; zero sims/chamadas
Guarda anti-duplicata: 0 commits FONTE-2 reais (as correspondências eram
menções na FONTE-1); sem ANEXO/prereg/seção → PROSSEGUIR. Handoff 01a160ad
(era FONTE-1) aceito. Onboarding: PROJECT_STATE (header FONTE-1 +
[NOTA-DEP]) + ANEXO_FONTE_1 (classes F0, PROBE-C, ressalva de âncora) lidos.

## ACHADO-P0 (fluxo real, arquivo/linha — CONFIRMA o orquestrador)
1. `scripts/draw_track.py:23-24` (`load_track`) delega a
   `backend.model_train.f1_env.resolve_track` — **o desenho NUNCA consulta
   os mirrors** (load_track_frozen vive no MESMO f1_env.py:1292 e não é
   chamado por resolve_track).
2. `f1_env.py:103-111` (resolve_track): ordem = Track/CSV →
   **FastF1TrackLoader.load(load_session=True)** (→ `get_session` +
   `get_circuit_info` — track_loader.py:281/314 — o plano SESSÃO morto
   pelo paywall: TODO endpoint em WARNING, circuit_info sem pos_data) →
   fallback `FASTF1_DEFAULT_EVENT` (São Paulo GP = Interlagos) →
   `build_interlagos_track()` preset.
3. Por isso: `--track monza|monaco` → tentativa 1 morre (paywall),
   tentativa 2 (Interlagos) também morre → **preset silencioso de
   Interlagos**; `--track interlagos` → ÚNICA tentativa (São Paulo GP)
   morre → preset. Todas as 3 observações do dono CONFIRMADAS: até
   interlagos toca o FastF1 morto antes do preset; toda pista desenha
   Interlagos por engano.

## Mapa de acoplamento draw_track × F1MultiContextEnv
O desenho usa APENAS: `track.waypoints`, `track.width_m`, `track.name`,
`track.start_finish_waypoint` (plot_track/ascii_draw). O env entra SÓ em
`load_track` via `resolve_track` (que devolve um `Track`). **O desenho É
desacoplável SEM tocar o env**: basta construir `Track.from_waypoints`
de outra fonte (mirror JSON / OpenF1) na nova rota do draw_track.
PROIBIÇÃO respeitada: env/loader não serão modificados; resolve_track
fica disponível só atrás de `--legacy-preset` com warning LOUD.

## NIT FONTE-1-review FECHADO
"limite documentado ~500/h sem key" → RE-ESCRITO como OBSERVADO (zero
429 em 10 chamadas; cabeçalhos x-ratelimit ausentes) no
ANEXO_FONTE_1.md §4 — a frase original não tinha fonte citável.
Worktree: f1_env.py:81 diff whitespace não-meu pré-existente (persiste;
não commitado).

# Task ID: FONTE-2 (2026-10-22) — draw_track: mirrors → OpenF1 → ERRO LOUD; golden EXATO; preset morto
Prereg 9ba3f8c antes de tudo; zero sims; env/loader/canônico intocados;
5/10 chamadas de rede logadas APPEND; pools intocados.

## Commits
3d29116 (P0) → 9ba3f8c (prereg) → módulo v1-v4 + probe_run (antes de
cada uso) → f382938 (patch + golden + PNGs + testes) → fechamento.

## Vereditos (mecânicos)
P1/GOLDEN PASS: mirrors = fonte da verdade (Interlagos 4160,4 EXATO;
Monaco 3335,2 EXATO/834wp/hairpin κ0,1602; Spa 7003,2 −0,01%); DISCLOSE
preset×mirror (240wp/4309,0m vs 1131wp/4160,4m — +3,6%, 4,7× mais
grosso). P2 PASS: OpenF1 Monza 2024 = 575wp/5756m (−0,64% vs 5793);
UNIDADE = DECÍMETROS (razão exata 10× do bounding box; x/y/0,1); 3
métodos mortos documentados (salto; origem=garagem 6599 amostras
paradas; NN 66 km); método v4 final (remove-parado → célula-60m-mais-
visitada → janelas=volta → mediana → re-amostra 10m); location pesado
3,9MB/7-9,5s (cache local). P4 PASS: fail-loud SystemExit 3 + lista;
--legacy-preset com AVISO LOUD. PROBE-B devolvido (P2 passou).

## Lições
(1) Antes de medir distâncias de uma API nova, conferir a UNIDADE pelo
bounding box físico conhecido (razão 10× = decímetros); (2) telemetria
de "posição" contém GARAGEM (milhares de amostras paradas) — filtrar
parado antes de qualquer histograma; (3) iteração de método em payload
CACHEADO = zero chamadas de rede (o retry 2/2 virou cache e as 3
iterações seguintes não custaram nada); (4) cadeia NN em banda densa
embaraça — janelas temporais entre visitas a UMA célula são a forma
correta de fatiar voltas.

# Task ID: PROF-REPAIR-1 (2026-10-22) — pacing pós-reentrada: PRIMÁRIA FAIL (52,47%); GAP B/C conservador; PARE
Prereg fc0a939 antes de tudo; 7/7 eps; zero rede; baseline reuso
obrigatório; aluno 45,00% canônico intocado; pools/caches intactos.

## Commits
fc0a939 (prereg) → eb09171 (patch --prof-repair default-OFF) →
cae63df/35f3baa (+2 testes; erro aritmético MEU no teste, patch
correto) → 7 eps seriais → 50ea3eb (evidência + ANEXO) → fechamento.

## Veredito (mecânico vs pins)
flag-OFF BIT-IDÊNTICO a prof_s0 (regressão obrigatória PASS).
flag-ON: fora 52,47% (−4,46pp) — PRIMÁRIA FAIL (≥45,00); SEC-1 cascata
94,4% FAIL (inalterada); SEC-2 PASS (C11 top-1, Reta 2ª); SEC-3 preso
277,2s FAIL + REGRESSÃO (+40,2s). Árvore: A não; B não como pinado
(1/3 SEC); C não (sem regressão total) → GAP entre B e C não previsto
→ CONSERVADOR: nenhum sucesso; --prof-repair RESEARCH default-OFF;
professor segue não-viável p/ rótulos; decisão (2ª rodada × abandonar)
= dono, com gap quantificado (7,47pp residual).

## Lições
(1) Árvore de 3 ramos precisa de ramo p/ "melhora parcial SEM secundárias
verdes" — o GAP exigiu resolução conservadora declarada (sem re-pin);
(2) reparo de pacing melhorou o SINTOMA (Reta sai do top-1) sem tocar a
CAUSA (cascata inalterada) — o carro sai de novo mesmo a 8-12 m/s: a
trajetória de reentrada (bearing projeção+10m) é o motor dominante
(candidato SÓ TEXTO: alvo adiante/curvatura mínima); (3) a rampa
AUMENTOU o preso (crawl mais longo nas janelas presas) — reparos de
ritmo podem piorar métricas de tempo; (4) degenerescência solo+seca
confirmada de novo (seeds 0-4 bit-idênticos).

# Task ID: PISTA-IDENT-1 (2026-10-22) — resolução separada, mirror-first, fail-loud; 6 legacy curadas; zero sims
Prereg 3758661 antes de tudo; engenharia; zero sims/rede; zonas
proibidas intocadas (--prof-repair 2/2 verdes pós-refactor).

## Commits
3758661 (prereg+T0) → 015ecaf (G1+G2) → 22d13ad (G3+mirror-first) →
9b0f378 (+4 testes) → 135e409 (ANEXO) → fechamento.

## Veredito
Golden 5/5. resolve_track agora: CSV → MIRROR canônico (instantâneo,
shas verificados) → FastF1 legado → TrackResolutionError com LISTA (o
fallback silencioso de Interlagos MORRE no treino/eval; preservado só
com --allow-track-fallback + AVISO LOUD + [FALLBACK]). track_identity
(requested×efetiva×fonte×sha×wp×L) no env e no eval. Suíte: baseline
serial REAL 26F (livros 25F) → final serial 20F/345P/3S — 6 LEGACY
CURADAS (sintomas do preset: curvature/v_plan/hairpin/kappa/driver_db),
ZERO novas; monza-test reparado (pass anterior inválido).

## Lições
(1) O preset silencioso não era só um risco — estava CORROMPENDO a
suíte: 6 testes legados mediam o preset procedural em vez da pista
pedida (curvature_cap κ 0,13>0,11 era o PRESET, não o track); 
(2) suítes concorrentes que escrevem /tmp compartilhado = SIMS EM
PARALELO (falso 'novo' hold_at por colisão de arquivo — minha
violação da serial, disclosada); (3) case-exato do loader voltou a
morder ('monaco'≠'Monaco_v2.json' — H-1 reincidente em MIM; gate
`in MIRROR_OPTIONS` rejeitava 'Monaco'/'Spa'); (4) baseline de suíte
também flutua ±1 entre runs de ambiente (26 vs 25) — comparar
itemizado serial×serial, nunca contagem de livro contra run.

# Task ID: PISTAS_EXPAND_1 (2026-10-23) — mirrors reais via OpenF1; 0 sims; teto 25 chamadas
Estado no recebimento do PATCH_A: prereg 8afec70 commitado ANTES de qualquer
patch/rede (zero rede até aqui ✓); baseline serial REAL 20F/345P/3S (175,5s)
= livros 1a228b8 EXATO; T0 preliminar: f1db confirma os 9 oficiais da tabela
§1 SEM re-pin; v1s ACHADOS para Hungaroring e Zandvoort (além de Suzuka/Monza)
→ T0 reclassifica (c)→(b) — RATIFICADO pelo PATCH_A FIXAÇÃO 1 (fail-loud se o
disco divergir do inventário; sem reclassificação silenciosa).
PATCH_PISTAS_EXPAND_1_A registrado verbatim em backend/PATCH_PISTAS_EXPAND_1_A.md
→ 4 fixações: (1) congelar SÓ Montreal/Bahrain/Mexico (+LasVegas/Miami stretch
se teto deixar; senão NAO_EXECUTADO); (b) Suzuka/Hungaroring/Zandvoort =
comparativo SEM congelar; Silverstone = v2 candidato AGUARDA_DONO FORA do path
frozen; (2) git add -f SÓ deliverables canônicos (cru OpenF1/cache fora do
git); (3) stray backend/worklog.md → archive/ com README (não deletar);
(4) mirrors v2 c/ official_length_m (f1db) + sf_idx=0+sf_note + sha
recalculado + tabela de chaves case-exatas no ANEXO. Pool --tracks intocado;
adoção = ciclo próprio.

## Fechamento PISTAS_EXPAND_1 (cadeia 8afec70 → 51da2d8 → 6395354 → d5bb170 →
48a16f2 → 3eac9be → 81866bd → 96947fa → 25589b2)

RESULTADO HONESTO do gate Δ<1% pinado: **7/9 FAILED** (deltas −1,36% a −2,11%,
todos CURTOS). ACHADO MECÂNICO: o v4 do FONTE-2 extrai a LINHA DE CORRIDA
(corta curvas; corda<arco na re-amostra 10 m) — a prova Monza (−0,64%) é a
pista MAIS INDULGENTE do calendário; sinuosas/rua encurtam 1,3-2,1%. O gate
é mais estrito que o acervo: interlagos_v2 canônico é −3,45% vs oficial.
SEM re-pin pós-número.

ENTREGAS: LasVegas_v2.json CONGELADA (única OK, veio do esticamento;
−0,998% vs 6201 m; case-exata `LasVegas`; sha c30a8fe636b725cd; 614 wp) —
os 3 alvos primários de congelamento (Montreal/Bahrain/Mexico) falharam o
gate. Suzuka COMPARADO: candidato 5761,6 m (−0,78%) vs v1 5534,8 (−4,69%)
= 3,5× mais próximo, v1 INTACTO, sha 72807c529604ee6c (freeze = dono);
Hungaroring/Zandvoort reprovaram ANTES do artefato (números no manifest:
4320,8/−1,37% e 4171,3/−2,06% vs v1s 4177,7/4053,2). Manifest 9 linhas +
probe_log 17/25 + PNGs via draw_track --csv (zona proibida SÓ chamada;
rota --csv pré-existente confirmada por leitura, sem side-car).

GOLDEN §4 PASS TOTAL (canônicos 3/3 bit-idênticos; v1s 5/5; anti-substituição
5/5 — nenhum _v2 não-autorizado no path frozen; t_pe1_* 4/4 estruturais
data-driven). Suíte: baseline REAL serial 20F/345P/3S → FINAL serial
20F/349P/3S, as 20 falhas BIT-A-BIT idênticas, +4P = t_pe1 (§8 sem desvio).

LIÇÕES: (1) /tmp de tasks background é EFÊMERO — o tee do baseline e o log
da task foram reclamados pelo sandbox; comparação itemizada feita contra as
listas capturadas no registro da sessão (ver ANEXO §9; listas verbatim
registradas); logs de medição vão ao worktree no MESMO passo; (2) gate de
comprimento calibrado em UMA pista (Monza) não generaliza — limiares de
geometria precisam de derivação por CLASSE de pista, calibrada ANTES do
run; (3) o reprocessamento com gate futuro é ZERO-rede (streams em cache);
(4) manifest exibe −1,0 (arredondamento 2 casas) mas o gate avaliou
−0,9982% (registrar valor não-arredondado em ciclos futuros).

DECISÕES DO DONO: gate × re-derivação mecânica; Suzuka freeze; LasVegas
adoção no pool (= ciclo próprio); A×B/PROF-REPAIR-1 intactas.

# Task ID: EXECUTOR_LUNA_HANDOFF_A (2026-10-23) — erratas E1/E2

## Commit
Erratas documentais E1/E2 em commit dedicado, registrado junto com esta entrada.

## Alterações
- E1: corrigi o comparativo de Suzuka para explicitar a razão de 6,0× entre
  as magnitudes dos erros de comprimento (272,2 m ÷ 45,4 m), sem generalizar
  para fidelidade geométrica ou desempenho. Corrigidos o ANEXO, o resumo
  corrente e a fila do PROJECT_STATE; registros históricos preservados.
- E2: ANEXO §8 agora identifica 12 chamadas da primária (avanço Bahrain e
  fallbacks Zandvoort/Suzuka) e 2 chamadas Miami no esticamento, conforme o
  probe_log. Total existente: 2 discovery + 15 location = 17/25.
- Escopo documental: zero rede, zero sims, sem mudanças em caminhos frozen,
  pools, caches ou dados canônicos. O arquivo não rastreado preexistente
  backend/backend/ANEXO_SAIDAS_1_ERRATAS.md foi preservado.

# Task ID: ANEXO_PREREG_GDER1_V0_A (2026-10-23) — preservação do rascunho-base

## Commit
Arquivo `backend/PREREG_GATE_RE_DERIVE_1_v0.md` salvo verbatim a partir do
anexo reemitido pelo dono; commit separado anterior ao congelamento final.

## Estado
- S0–S10 preservados como no texto reemitido, inclusive as lacunas e a nota
  de proveniência original “Memória consultada: não.”
- Nenhuma extração, cálculo de delta ou execução foi feita nesta etapa.
- O prereg final ainda exige F1–F6, resolução auditável das 11 lacunas e
  congelamento em commit dedicado antes de qualquer execução.

## Task ID: EXECUTOR_LUNA_HANDOFF_A — GATE-RE-DERIVE-1

### Congelamento
- `backend/PREREG_GATE_RE_DERIVE_1.md` congelado antes da execução em
  `194a709`; base v0 verbatim preservada em `e58e8c4`; E1/E2 continuam no
  commit separado `b28e100`.
- Resolvidas as 11 lacunas com inventário, fontes, hashes, gates, epsilon
  `1e−12` pp, regra mecânica de holdout e decisão Ramo 2 pré-registrada.
- Nenhum dado novo de comprimento foi calculado antes do commit de freeze.

### Execução
- `backend/scripts/audit_gate_re_derive_1.py` processou em ordem os dez
  streams históricos e os seis alternativos, usando somente arquivos locais
  hash-pinned e `f1db.db`; zero rede, zero path frozen, zero alteração de pool,
  zero simulação de produto. Nenhum dado OpenF1 cru foi adicionado ao git.
- Os 16 streams excederam o teto estrutural congelado de 120 m/s. As dez
  unidades históricas ficaram fora da calibração; nenhuma pista elegível e
  nenhum fold LOO. Suzuka também falhou topologia em um histórico e nos dois
  alternativos. Nenhum dos seis deltas alternativos foi reportado. Resultado
  mecânico: Ramo 2, comprimento report-only; holdout independente = 0.
- Auditoria serializada em `backend/experiments/gate-re-derive-1/audit.json`;
  repetição bit a bit idêntica, SHA-256
  `67353f413e499b1dacb19d5933266516248d893ef5f6ae112ddfd22132e04091`.
- Suíte serial final: 20 falhas, 349 passes, 3 skips; as mesmas 20 falhas do
  baseline registrado `1a228b8` (20F/345P/3S), com quatro passes adicionais.
  Rótulo obrigatório: “349 testes, com 20 falhas bit a bit estáveis
  ('regressão estável conhecida') e 3 skips”.
- O primeiro run desta tarefa acusou uma falha extra no contrato documental
  por fechamento tipográfico ausente em uma linha histórica de
  `PROJECT_STATE.md`. Corrigido somente o parêntese no estado vivo; o teste
  direcionado passou e o run serial completo retornou ao conjunto de 20
  falhas conhecidas. Nenhum PARE ou worklog histórico foi editado.

## FAIL-FORENSICS-1 — PARE de leak-check (2026-10-23)

- Prereg `1e9ceee` e script offline `d631a46` congelados antes das corridas.
- Run 1 cego/Interlagos (6000 ticks, seed 0): CSV e `_events.csv` bit-idênticos
  às âncoras F4v15; 3674 contatos, 2482 pós-60s, 136,0 s rolantes, 3 hesitações,
  22,1% fora.
- Run 2 Composite/Interlagos: CSV e `_events.csv` bit-idênticos; 752 contatos,
  292 pós-60s, 140,0 s rolantes, 25,2% fora. Runner e recontagem do CSV dão 14
  hesitações, contra 13 no estado/pedido. O log original F4v15 também diz 14;
  bloco de código de contagem legado desde `439f402`.
- **PARE** antes das etapas Monaco por contradição da âncora, sem corrigir o pin
  após observação e sem análise causal. O dono precisa ratificar 13×14 e abrir
  prereg novo para retomar.
- CSVs, eventos, logs, `PARE.md` e `relatorio.md` preservados em
  `backend/experiments/fail-forensics-1/`; nenhuma mudança comportamental.

## ERRATA FF1-E3 — ratificação da âncora Composite (2026-10-23)

- **Ratificação do dono: governa 14 hesitações** no Composite Interlagos F4v15.
  A tabela e o bullet canônicos do B3' em `PROJECT_STATE.md` foram corrigidos
  com proveniência (`2_allcomposite.log:71`, recontagem do CSV e reprodução
  FAIL-FORENSICS-1b). B3' continua FAIL por hesit≤3; ANTI-D3-1 continua
  PRIMÁRIO FAIL. Prereg, veredito, PARE e relatório congelados da sessão
  anterior permanecem intocados; narrativas históricas com “13” não foram
  reescritas.
- Reconciliação do P1 (`8c79ee6`): os 13 episódios descritos eram on-track.
  O episódio adicional é NOR, 167,4–167,8 s, off-track em todas as 2 amostras,
  `recovery_rejoin`, `th=0,35`, `g_gate=1` e `|r|` máximo 1,59. O filtro
  on-track do P1 o excluiu. Sobre os 14 episódios, `g_gate>0` = 13/14 e
  `|r|>0,1` = 14/14; no subconjunto on-track P1, `g_gate>0` = 12/13.
- Suite baseline solicitada: **21F/348P/3S**, não os 20F/349P/3S esperados. A
  falha excedente era `test_state_files_doc_integrity`, pois um resumo superior
  anterior tinha removido o prefixo obrigatório `> Última atualização:`; o
  teste não fixa o valor 13. O header foi restaurado sem alterar o teste;
  `pytest tests/test_state_files.py -q` passou depois da correção. Suite
  completa pós-errata: **20F/349P/3S**, as 20 falhas conhecidas sem falha
  documental excedente.
- Sem alterações em comportamento, pools, dados congelados ou testes. A etapa
  E3 não executa corridas.

## FAIL-FORENSICS-1b — tentativas de resolução R3 (2026-10-23)

- Prereg `16910ef`, errata E3 `88c3e0e` e instrumento offline `ad5a88d` estão
  commitados antes de qualquer simulação da retomada. Baseline/pós-errata:
  21F/348P/3S antes de restaurar o header; 20F/349P/3S depois. Selftests
  `fail_forensics_verdict.py --selftest` e `saidas_verdict.py --selftest` PASS.
- Duas invocações R3 encerraram antes de iniciar o engine: `--track monaco`
  procurou `monaco_v1.json`; `--track Monaco_v2` procurou
  `Monaco_v2_v1.json`. Não existe CSV R3, não houve comparação válida com
  `aluno_s0.csv`, e isto não é divergência de âncora. Os logs foram preservados
  como `3_blind_monaco_attempt_invalid_track.log` e
  `3_blind_monaco_attempt_invalid_track_v2.log`.
- Preflight read-only confirmou `--track Monaco` como alias que resolve o
  frozen `Monaco_v2.json` (short SHA `67ca11dc211c8c78`, 834 wp, SF 0). A errata
  operacional está em `backend/experiments/fail-forensics-2/ERRATA_R3_TRACK_ALIAS.md`.
- A contingência única pré-CSV foi usada pela segunda tentativa; não fazer uma
  terceira invocação sem autorização. R3 permanece pendente; R4 não foi iniciado
  porque depende do gate byte-a-byte de R3. Nenhum mecanismo de comportamento
  foi alterado.

## FAIL-FORENSICS-1b — corridas Monaco e veredito offline (2026-10-23)

- Após autorização explícita do dono, uma execução corrigida de R3 usou
  `--track Monaco` e passou o leak-check: CSV byte-idêntico a
  `aluno_s0.csv`, SHA-256 `f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0`.
  As duas tentativas anteriores falharam antes do engine e permanecem
  preservadas como logs de resolução, sem CSV de corrida.
- O gate liberou R4: Composite Monaco, 10 carros, 6000 ticks, seed 0,
  `grid,compound`, primeira medição exploratória N=1. SHA-256 do CSV
  `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022`; do
  `_events.csv` `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4`.
  Resultado: 43,15% fora, 29 episódios/110.794 pontos solver-side, 12
  hesitações e 45 saltos ≥30 m pelo proxy `|Δs_wrapped − Δcum_dist|`; zero
  transições de clima.
- Veredito offline cobriu as 14 entradas declaradas. Em Monaco composite, a
  precedência causal classificou 280 saídas, 93 janelas presas, 11 hesitações
  e 111 saltos como recuperação; houve 29 episódios de contato e 55 saídas
  classificadas como curva. A regra causal não é contrafactual. As cinco
  sementes por braço nos CSVs Monaco históricos repetem a mesma sequência de
  dados e não são realizações independentes.
- Relatório completo, tabelas e hashes em
  `backend/experiments/fail-forensics-2/EXECUCAO_FAIL_FORENSICS_1B.md` e
  `backend/experiments/fail-forensics-2/veredito/`. Ponto para Etapa 2:
  capturar XY e índice bruto de `nearest_segment`, sincronizados com odômetro,
  autoridade e contatos; revisar corredor/bordas de Monaco antes de qualquer
  gate. O proxy de projeção não prova salto bruto da busca nearest. B3' e
  ANTI-D3-1 continuam FAIL; sem alteração de comportamento ou de gates.
- Selftests golden passaram antes das corridas; suíte pós-E3 permaneceu
  20F/349P/3S. Nenhum teste foi alterado ou repetido após a medição.

## LOC-XY-1 — PARE no gate 3 (2026-10-23)

- Prereg e baseline pré-código congelados em `5fe4ff8`; baseline serial
  20F/349P/3S. O dono ratificou 20F/352P/3S como conta esperada para exatamente
  três novos testes.
- Commit `4d22d65` adicionou as colunas `body_x`, `body_y`, `ns_raw`, o header
  v3.4 com kill-switch v3.3 e exatamente três testes. Os três novos testes
  passaram; o teste de kill-switch reproduziu o fixture v3.3 byte a byte.
- Gate 3 terminou **21F/351P/3S**. As 20 falhas conhecidas são idênticas ao
  baseline; apareceu uma 21ª fora do conjunto canônico:
  `test_mixed_composite_wiring.py::test_t_regression_v10_cego_bit_identico`,
  que compara o CSV inteiro com fixture v3.3 de 49 colunas. Por regra do dono,
  PARE imediatamente. Não houve smoke formal do gate 4, selftest golden
  pós-código, reparo de teste ou reexecução. A suíte baseline e a pós-código
  executaram cada uma o subprocesso de corrida de 1.200 ticks contido no teste
  legado; os CSV/eventos temporários foram removidos após o gate.
- Log bruto versionado: `backend/experiments/loc-xy-1/3_post_pytest.log`,
  SHA-256 `969628421db6fb3a57e038ef212ea97c017c325da3ae0d5290f24696986fbf6a`.
  Baseline bruto: `0_baseline_pytest.log`, SHA-256
  `dba9ff77f808e844be260bcf2a90b4e2ff46d8fff5f08e275ca6415467fdf7e3`.
- Estado: aguardar decisão do dono sobre a atualização do contrato do teste
  legado antes de retomar qualquer gate posterior.

## LOC-XY-1 — ERRATA E-XY-2 ratificada; PARE na retomada (2026-10-23)

- Decisão do dono: o teste legado mantém nome/path, roda no writer default v3.4
  e compara `split(',')[:49]` em todas as linhas, incluindo o header, com o
  fixture pré-wiring v3.3. Foi acrescentada a linha de contrato exata ao
  docstring. A edição limitou-se ao corpo desse teste; a limpeza temporária
  remove CSV e `_events.csv` em `finally`. Writer, testes novos e lógica de
  corrida permaneceram intocados.
- Suíte completa: **21F/351P/3S**, versus ratificado **20F/352P/3S**. O teste
  corrigido e os três novos testes LOC-XY passaram. As 20 falhas de baseline
  persistiram e `test_state_files_doc_integrity` falhou como divergência
  adicional, acusando a entrada histórica FAIL-FORENSICS-1b na cadeia
  `> (anterior:)` do PROJECT_STATE. PARE imediato no gate 3.
- Log bruto `backend/experiments/loc-xy-1/4_post_fix_pytest.log`, SHA-256
  `37527575cf3b889d65819f920e6fa0216f00817549674c9fe07e053371f1d675`.
  Nenhum smoke formal de 6.000 ticks ou selftest golden pós-código foi
  executado; zero corridas de medição, pools e pistas frozen intocados. A
  suíte incluiu a corrida curta de 1.200 ticks já embutida no teste legado.
- O relatório/anexo e a cadeia E-XY-2 foram atualizados sem alterar os logs
  históricos `0_baseline_pytest.log` e `3_post_pytest.log`. Próxima ação depende
  de nova decisão do dono para resolver o gate documental antes de qualquer
  reexecução ou smoke.

## LOC-XY-1 — E-XY-3 e fechamento (2026-10-23)

- E-XY-3 alterou somente a linha 6 de `backend/PROJECT_STATE.md`, repondo o
  ponteiro para o relatório FAIL-FORENSICS-1b; commit doc-only `29cf2a2`.
  A suíte completa passou em **20F/352P/3S** e as 20 falhas são exatamente as
  do baseline. Log `5_post_chain_fix_pytest.log`, SHA-256
  `7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185`.
- Smoke A (6000 ticks, seed 0, Interlagos blind, kill-switch ON): CSV inteiro
  byte-idêntico à âncora v3.3; SHA-256 comum
  `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`.
- Smoke B (mesmas flags, kill-switch OFF): projeção `split(',')[:49]` igual
  para header + 30.000 linhas; hash da projeção
  `ad145f45af4152e5f8097042793a2291b4cffe916ad8c4dd7bd3137a378d00c4`.
  CSV completo v3.4 hash `fe5027dcf83fd81bb062443b93e0a0b7b5b8e8f280c916a525c489bcb8003e35`;
  52 campos, `body_x/body_y/ns_raw` presentes, finitos/preenchidos e ns_raw
  inteiro no intervalo 0–1130. Eventos dos dois smokes iguais à âncora,
  SHA-256 `11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9`.
- Selftests golden pós-suíte/smokes: `fail_forensics_verdict.py --selftest`
  PASS (SHA `2112e34309a53dc80ab7771f867560d543d1f4fa31eb9c3cba87f27c4352e100`);
  `saidas_verdict.py --selftest` PASS (SHA
  `430bddf5170d96acb1542992c83b9004712edab989dbaeb99c68eec09da041e3`).
- Regra permanente: cada nova entrada de cabeçalho/cadeia inclui `Ver <path>`
  e fecha `)` para sobreviver ao rebaixamento futuro a `(anterior:)`. Fechado:
  2/2 smokes, zero corridas de medição, pools e pistas frozen intocados. Os
  logs e o CSV v3.4 de evidência foram preservados para o commit final.

## PROJ-FIX-1 — PARE na reconciliação histórica (2026-10-23)

- Prereg/classificador v1.0/selftest foram congelados no commit `a519081`
  antes do replay. O selftest sintético passou.
- Uma única corrida R4 Composite Monaco N=1, seed 0, `--track Monaco`, writer
  v3.4: g1 PASS com hash de projeção comum
  `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`; g2
  PASS com 71 campos, XY finitos e `ns_raw` em faixa. A saída tem 30.000 linhas.
- PARE antes de emitir classes: o seletor preregistrado da tabela NIT-2
  encontrou 0 linhas do run id congelado, em vez de 112 ≥10 m e 45 ≥30 m.
  Nenhuma classe ou correção é declarada; o script não foi editado após o
  resultado. Uma retomada exige prereg novo para resolver a identidade do run.
- Nenhuma outra corrida ou smoke; pools/pistas frozen intocados. CSV, eventos,
  logs brutos, hashes e estado do PARE: `backend/experiments/proj-fix-1/PARE.md`.

## PROJ-FIX-2 — PARE em g4 (2026-10-23)

- Prereg/classificador v1.1 congelados no commit `8222dff`; selftest PASS. Sem
  reexecução da suíte (referência 20F/352P/3S), sem novas simulações e smokes.
- g0–g3 PASS: hashes conferidos; projeções do replay/âncora iguais; 71 campos e
  30.000 linhas; NIT-2 `composite_monaco` seleciona 112 ≥10 m / 45 ≥30 m.
- PARE obrigatório na classificação: evento `('ALO', 2130, 2132)` sem classe
  XY/ns_raw. Não há mapa completo, contagens C1/C2/C3, p95 ou proposta de
  correção. O classificador não foi editado. Relatório e logs:
  `backend/experiments/proj-fix-1/PARE_PROJ_FIX_2.md`.

## PROJ-FIX-3 — PARE em g0 (2026-10-23)

- Diagnóstico limitado ao evento `('ALO', 2130, 2132)` registrado antes do
  freeze; prereg e classificador v1.2 congelados no commit `2330e9f`; selftest
  sintético PASS.
- g0 parou: hash esperado no prereg para PARE v2 `a3e7dd18…`, hash atual
  `e287e5bd…`. Demais hashes g0 conferem. Nenhum gate g1–g4 rodou, nem houve
  agregação de classes; suíte não reexecutada, referência 20F/352P/3S.
- Zero novas simulações/smokes. Detalhes e log bruto:
  `backend/experiments/proj-fix-1/PARE_PROJ_FIX_3.md` e `12_g0_sha256.log`.


## Task ID PROJ-FIX-4 — retificação de proveniência e fechamento C1–C5 (Ver `backend/experiments/proj-fix-1/EXECUCAO_PROJ_FIX_4.md`)

- PARE v2 e commits `d02a6f8`, `2330e9f`, `262d668`, `HEAD`: SHA-256 `e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c`; o esperado `a3e7…` veio de rascunho não commitado. P3/instrumento não alterados.
- Freeze dedicado P4 `574c5ea` (prereg SHA `0d9c8d31bfee6470d045cedea46c25264b3ba5d12d757116e75a300554219392`); manifest `75666b3` (SHA `5715be7b663394e29cc9b2a21a2baf554ccdb9281cc6d25439651d38e0b641ee`), 18 artefatos em proveniência dupla PASS; selftest v1.2 recheck PASS (`3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127`).
- g1/g2 PASS: projeção `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`, 71 campos/30.000 linhas, XY finitos, `ns_raw` 0–833. g3: 112 ≥10 m / 45 ≥30 m.
- g4: 112/112 chaves únicas; ≥10 m C1/C2/C3/C5 = 0/0/46/66; ≥30 m = 0/0/45/0; ALO (2130,2132)=C5; C4 inválido=0; anatomia C5 offtrack=1 em 66/66. Mapa C5 1:1: `backend/experiments/proj-fix-1/classificacao_v12/mapa_nit2_ge10.csv`. Sem proposta de correção, decisão da Etapa 2 volta ao dono.
- Zero corridas/smokes; suíte segue 20F/352P/3S por referência e não foi reexecutada; pools e pistas frozen intocados. SHA logs: g1/g2 `617ef75e8cae3aa556e8e362c5e54a8099f6446b734c3bb836040a5839807a10`, mapa `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f`, resumo `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05`, validação `e62d487948772713bb76959d21713fa575bcdc7dd63bc9f0de20cc9c18036f30`, relatório `b4b8c6ca4bbf2c7514978e09fe2a2b826c1dfd44be7c2f827d68a96142642403`.

## PROJ-FIX-5 (2026-10-23; freeze pré-análise corrigido `4081f06`): report-only — mapa 112/112 reconciliado (C3=46/C5=66), p95 Δs C3=1127,55 m/C5=25,34 m; intervalos médios por carro publicados, eventos/volta indisponível nas fontes permitidas; ponteiro localizado e gate desenhado em `backend/experiments/proj-fix-1/DOSSIÊ_PROJ_GATE.md`; zero sims/smokes, produção e suíte intactas; veredito aguardando dono.

## PROJ-GATE-1 — PARE em g2/g4 (2026-10-23)

- V-A runner-only foi commitada default-OFF (`f2bd199`). R1 OFF reproduziu os
  hashes congelados. A única R2 ON falhou g2 (173 pares ≥10 m; 108 ≥30 m) e g4
  (60,15% fora; 397 episódios; 144 janelas; 28 hesitações). g3 passou em 392/392
  reaquisições nearest-global; contatos e completude passaram.
- PARE obrigatório: g5 não rodou, nenhuma corrida foi repetida e não houve
  reanálise das classes 112/50/45 ou promoção. Artefatos e hashes duplos:
  `backend/experiments/proj-gate-1/PARE_PROJ_GATE_1.md`.

## PROJ-GATE-2 — autópsia report-only (2026-10-24)

- Pré-registro congelado (`0a269ff`) antes dos cálculos; audit offline v1.0
  congelado (`a6d6775`); selftest sintético PASS. Uma passagem validou
  proveniência dupla e schemas/samples: 30.000 linhas por braço, 10 carros,
  ticks `0,2,...,5998`; hashes completos em
  `backend/experiments/proj-gate-1/autopsia/3_execution.log`.
- Ponteiro proxy: ramo errado em 0/12.945 OFF e 5/18.045 ON; os cinco
  outliers foram amostras isoladas (máximo 1.403,663 m). R2: 6/392 janelas de
  reentrada com algum erro, 0/392 com dois erros consecutivos; spatial snap
  p95 5,959 m. R2 recriou as 28 hesitações publicadas.
- g2: R1 reproduziu 112/45, classes ge10/ge30 `0/0/46/66` e `0/0/45/0`;
  R2 reproduziu 173/108, classes `0/0/110/63` e `0/0/107/1` (C1/C2/C3/C5).
  H1 LOSING por alvo/âncora não gravados; H2 sem ponteiro interno observável;
  H3 confirma que o proxy g2 não responde à localidade. Decisão: arquivar esta
  bifurcação, sem afirmar ausência de defeito.
- Zero sims/smokes, suíte não executada, sem edits de produção/pool/cache/pista
  e sem promoção. Outputs novos em
  `backend/experiments/proj-gate-1/autopsia/` (`3_branch_geometry.json`,
  `4_g2_class_decomposition.json`, `5_veredito.md`); flag permaneceu OFF.

## REJOIN-TEL-1 — PARE no replay único (2026-10-24)

- Schema ratificado: 9 campos novos, 80 totais. Prereg `cc879b0`, erratas
  pré-resultados `f15bb7d`/`8316af0`, implementação frozen `b42f694`.
- Testes novos 5/5 e selftest sintético PASS. Suíte completa 20F/363P/3S;
  comparação por identidade confirmou exatamente as 20 falhas de referência,
  zero novas.
- Replay R4 foi iniciado uma vez e interrompido com Ctrl-C por erro operacional
  meu ao interpretar namespace/process list; sessão retornou 130 antes de
  produzir CSV ou events. Orçamento de um replay consumido: PARE, sem retry.
- Sem dados de v3.5; g1/g2/g3 e audit não executados; nenhum veredito sobre
  RECUP-2 ou arquivamento. `--writer-v35` continua default-OFF, sem promoção.
  PARE, proveniência, hashes e próximos passos em
  `backend/experiments/rejoin-tel-1/PARE_REJOIN_TEL_1.md`.

## REJOIN-TEL-2 — orçamento renovado do replay v3.5 (2026-10-24)

- Handoff `01a16e76-d20e-7f21-94fb-37ca0d4de672` reivindicado; prereg
  `PREREG_REJOIN_TEL_2.md` congelado antes do replay em `9f9dc53`. Código
  production frozen `b42f694`; sem edits de código e sem reexecução da suíte.
- Exatamente uma corrida R4 foreground, 9 min de timeout, exit 0 (~3m18). g1,
  g2 e g3 passaram; g4 é referência 20F/363P/3S. CSV SHA
  `d950f7a60d47d125d829f5c4bf0302eadd9eb8ef7001cd17e690ba7950f6ac95`;
  events SHA `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4`.
- 345 janelas/344 reentradas; 302/344 >20°; correlação heading × segunda
  saída −0,3613; retorno p50/p95/max 5,70/24,74/36,80 s; 12 hesitações totais
  (11 em até 10 s pós-reentrada). Recomendação ao dono: arquivar hipótese
  angular da Etapa 2 e avançar à Etapa 3; sem correção/promoção. Ver
  `backend/experiments/rejoin-tel-2/EXECUCAO_REJOIN_TEL_2.md`.

## TRAFEGO-MED-1B — decomposição por fase report-only (2026-10-24)

- Handoff de freeze reivindicado; o commit do dono `8136d54ec45f9f49b38a5893a812928474109535` fechou a proveniência byte a byte do prereg, manifest e script. Disclosure: `git add -f` nos dois arquivos em `experiments/` por `.gitignore:56`; o arquivo avulso já presente no workspace permaneceu intocado.
- Uma análise offline exit 0 validou o manifest e processou 52 de 65 séries elegíveis; 13 séries com somente um `drv` foram excluídas antes das métricas. Sem corridas/smokes/suíte e sem edição de produção. Saídas e hashes em `backend/experiments/trafego-med-1/4_DOSSIE_TRAFEGO_MED_1B.md`.
- Nas quatro coortes principais da largada (24 corridas com geometria), primeira volta pós-largada teve 0 contatos 5 Hz e 0 hesitações. Fora dela, rejoin teve contatos com counterpart on-track, e o maior volume espacial recorrente ficou em s=1.900–2.400 m. Os 20 tratamentos acumularam 7.416 oportunidades sem troca sustentada, 76,5–79,9% nose-a-tail, sobretudo após 60 s. Recomendação report-only única: medir espaço/lado para passar; alternativa arquivada: cedência no follow; nenhum efeito causal alegado.

## PASS-1 — decisão de passagem (2026-10-24)

- PASS-1 (2026-10-24): freeze `3abb98d` conferido; selftest PASS; suíte 20F/375P/3S com as mesmas 20 falhas da referência. R1/R2 válidas e auditadas: 17 trocas pós-largada; 5 engajamentos, 0 consumos; g3 mediana e g4 contatos falharam. PARE; R3 não rodou; recomendação ao dono: novo ciclo report-only de diagnóstico/refinamento, sem promoção. Ver `backend/experiments/pass-1/5_EXECUCAO_PASS_1.md`.

- YIELD-1C (2026-10-25): corrida standalone corrigida concluída uma vez com exit 0; `2_R2_Y2.csv` tem 30.000 linhas e hash R1, mas nenhum yield disparou ou foi consumido. g2 FAIL; linha yield encerrada/PARE-SUNSET e próximo pivô é Etapa 4. Ver `backend/experiments/yield-1/EXECUCAO_YIELD_1C.md`.

## COMPOSITE-MAP-1 — inventário da Etapa 4 (2026-10-25)

- Freeze do dono `98a71e6` (blob==disco; 6 pins conferidos zero treino/sims). Veredito: lacunas bloqueantes — conversor, rotulagem, split, proveniência; instrumentação ratificada COMPOSITE-CORPUS-1, depois COMPOSITE-BASE-1 e COMPOSITE-TRAIN-1. Ver `backend/experiments/composite-1/PREREG_COMPOSITE_MAP_1.md`.

- COMPOSITE-CORPUS-1 (2026-10-25): report-only concluído; módulo novo, 7 testes focados e censo de 38 fontes (0 elegíveis; 35 rejeitadas; 3 excluídas; 26 `SEM_BLOB_HEAD`) preparados com hashes. Sem treino/sim/inferência; impedimento técnico permanece reconstrução + proveniência. Ver `backend/experiments/composite-1/PREREG_COMPOSITE_CORPUS_1.md`.
- COMPOSITE-COLLECT-1C (2026-10-26): g0 uma vez (20F/423P/3S, lista de falhas igual a 1E); conversão `--write` uma vez, 20 shards/2 audits, pareamento 0,5 e SHA de audit estável em duas leituras; commits `55b7d05` (events) e `33c75ce` (shards/audits/logs). Sem corrida standalone, treino ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_COLLECT_1C.md`.
- COMPOSITE-BASE-1 (2026-10-26): g0 pinado 453 testes (20F/430P/3S, log `db0abd33…`); 4 corridas formais R1-R4 exit 0 com 30.002 linhas e sidecars completos; extrator determinístico (hashes idênticos em 2 leituras); proveniência commits `7cb4f19` (12 artefatos) e `ceeaa20` (4 métricas); deltas Composite vs blind medidos (−36% a −44% contatos, +6,7pp fora em Interlagos); sem treino ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_BASE_1.md`.
- COMPOSITE-TRAIN-1 (2026-10-27): g0 pinado 460 testes (20F/437P/3S, log `bf051732…`); 2 treinos formais (Run 1 candidato + Run 2 réplica seed 42) concluídos exit 0; gates O-1 e réplica PASS (delta val_loss 0.0, max |dW| 0.0, NPZ SHA `6210fff6…` byte-idêntico); proveniência commit `c186ef2` (10 artefatos); sem corrida, simulação ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_TRAIN_1.md`.
COMPOSITE-BASE-2 etapa B executada (agente, 2026-10-27): g0 460=20F/437P/3S fail-set canônico exato; R1'-R4' 4/4 gates (R2'/R4' blind BYTE-IDÊNTICOS ao BASE-1; override 6210fff6/6a2dbf53 nos logs); extração 8/8 determinística; commits ab9da45 (provenance) + 3a02c11 (metrics); EXECUCAO staged; zero PARE; bucket TEST selado intocado.
COMPOSITE-STAGE-5 etapa B executada (agente, 2026-10-28): desselo TEST em 2 leituras exit 0 (6.000 amostras A_VER+B_SAI); candidato 6210fff6 SANCIONADO (5/5 gates PASS: Huber 0.2885 vs null 0.7077 ratio 0.4077 <= 0.80; MAE 0.5856 < 1.0440; norm 1.5985 <= 2.0; nan/inf 0; determinismo cmp byte-idêntico exit 0); proveniência commit e017874; EXECUCAO staged; zero corrida, zero treino, zero promoção.
COMPOSITE-STAGE-6 promoção executada (agente, 2026-10-28): backup B3.1 (6a2dbf53/5a2c20ce) em archive/residual_promocao_stage6; PAR candidato (6210fff6/f237ac9e) assume produção; g0 pós 462=20F/439P/3S (460 canônicos + 2 testes do selo, ambos PASS; fail-set canônico exato, diff bit-a-bit — emenda de contagem do dono); R1''/R3'' sem override cmp byte-a-byte vs BASE-2 PASS; g3 residual baseline 6210fff65b19ad0e; commits c8270a5+608e671; EXECUCAO staged; zero PARE.
- REALISMO-1 C0 (2026-10-29): etapa B executada após freeze `240bacde`; 8 corridas OFF N=1..4 seriais, 32 extrações determinísticas, 2 relatórios de ruído byte-idênticos; g0 20F/458P/3S com fail-set canônico; sem mecanismo/promoção. Ver `backend/experiments/realismo-1/c0/EXECUCAO_REALISMO_C0.md`.
2026-10-30 REALISMO-1 C1 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C1.md.
2026-11-01 REALISMO-1 C2 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C2.md.
2026-11-02 REALISMO-1 C3 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C3.md.
2026-11-03 REALISMO-1 C4 etapa B: análise offline de geometria (Tasks 10-11); 2.199 voltas filtradas; PARE duro em frame RMS (17,79 m > 5,0 m); ramo GEOMETRIA rejeitado; adoção do ramo FALLBACK (A5); zero corrida; C4_FINDINGS.md.
2026-11-04 REALISMO-1 C6 etapa B: matriz ON N=0..4 (20 corridas) + 4 controles OFF + 96 leituras de extração determinísticas + EXECUCAO_REALISMO_C6.md.
2026-11-04 REALISMO-1 C7 consolidação: matriz ON/OFF em N=5..8 (16 corridas) + 64 leituras de extração determinísticas + EXECUCAO_REALISMO_C7.md.
2026-11-05 REALISMO-1 promoção produção: defaults --rejoin-handoff align e --rejoin-ramp adotados no composite; suíte 20F canônica confirmada; RELATORIO_PROMOCAO_REALISMO_1.md.
2026-11-06 ABERTURA PERCEPÇÃO-1 + C8-rejoin: selados N=9..12 (confirmação C8) e N=13..16 (confirmação Fase 3); pools 76..79 e shards test/ intocados; PREREG_PERCEPCAO_1_F0.md e PREREG_C8_0.md.
2026-11-06 C8-0 referência: 10 corridas em N=0..4 (Interlagos e Monaco) + 40 extrações determinísticas cmp=0; EXECUCAO_C8_0.md.
2026-11-06 C8-B execução: 2 controles OFF cmp=0 + 10 corridas ON N=0..4 + 48 extrações determinísticas; gates primário/B-1/R-2/reentrada não aprovados; EXECUCAO_C8.md.
2026-11-06 C8-B errata: números agregados N=0..4 confirmam FAIL por B-1 (+48% contatos Interlagos, +17% Monaco) e R-2 (+1,9 pp fora Interlagos); voltas ON=354 passam R-1; PERCEPÇÃO-1 formalmente suspensa por falha do professor na Task 3 (sobreposição 94,1%).
2026-11-06 ABERTURA PROF-CURVA-1: teto de velocidade local no professor solo; PREREG_PROF_CURVA_1.md.
2026-11-06 PROF-CURVA-1 Task 2: referência solo 600 s Interlagos confirmada (4 voltas, 24,6% fora, 4 saídas crônicas C01/C06/C07/C08 em 100% das voltas; teto guarda ritmo <=123,05 s); REF_FINDINGS.md.
2026-11-06 PROF-CURVA-1 Task 4: fronteira v2 250 medições cmp=0; 10 corridas OFF solo Interlagos/Monaco N=0..4 e 20 leituras determinísticas cmp=0; baseline confirma saídas crônicas e 56,4–57,2% fora em Monaco; EXECUCAO_PROF_CURVA_1_0.md; PARE para closing do Dono.
2026-11-06 PROF-CURVA-1 Task 5: mapa de viabilidade OFFLINE do teto local (determinístico cmp=0 ×2, script e5853aa commitado antes da execução) — MECANISMO COMO PREREGISTRADO INVIÁVEL: guarda Interlagos estoura no PISO (integral capped 131,04 s > teto 123,05 s; Δ+34,84 s), Gate Primário inalcançável (C01 0/22 bind R 107–140 m = saída comportamental, não pacing; C06 4/20), teto engaja 74% da volta Interlagos / 89% Monaco (rastejamento 3,2–5,8 m/s); PARE automático §4 — ZERO corrida ON, orçamento 10 solo 600 s preservado, --prof-curva mantido default OFF bit-idêntico; encaminhamento preregistrado: racing line suavizada (curva geométrica 18 m na Junção) em ciclo próprio a abrir pelo dono; MAPA_VIABILIDADE.md
2026-11-06 ABERTURA RACING-LINE-1: ciclo separado para linha suavizada local do professor, com curva geométrica R=18 m na Junção; plano/prereg staged, zero corrida e zero alteração no PROF-CURVA-1; aguardando Freeze do Dono.
2026-11-07 RACING-LINE-1 Task 2: construção geométrica offline do arco R=18 m na janela C08/Junção (instrumento staged antes da execução, R7; determinístico cmp=0 ×2) — PARE §7: sem arco exato com os limites congelados (resíduo dos centros 3,189856 m ≫ 1e-3; corda 35,58 m implica sweep 162,6° vs giro real −140,6° = superdeterminado); evidência report-only: raiz bi-tangente EXATA com limites livres dentro da janela (s 2282,417 → 2342,863 m, giro −139,89°, resíduo <1e-6; +6 raízes degeneradas R_local=18 e 2 fillets locais); corredor/C1/fechamento/auto-interseção da raiz NÃO avaliados (fora do escopo do candidato); ZERO corrida, ZERO produção, pista frozen intocada, orçamento 10 solo intacto; decisão do dono: nova prereg com limites derivados / outra construção (biarc) / arquivar. GEOMETRIA_C08.json/md
2026-11-07 RACING-LINE-1 Task 3: Emenda nº 1 (limites derivados s=2282,417->2342,863 m, R=18 m); validacao offline de corredor e C1; CORREDOR_C08.md.
2026-11-07 RACING-LINE-1 arquivado: candidato de arco unico R=18 m inviavel no corredor (|lat|=10,07 m > 6,0 m); orcamento de 10 corridas solo 100% preservado; transicao para diagnostico de controle do professor (PROF-CONTROL-1).
2026-11-07 ABERTURA PROF-CONTROL-1: controle lateral do professor com feedforward arctan(L*kappa) e ajuste no ápice contra subesterço (LAGO_ANATOMY.md); PREREG_PROF_CONTROL_1.md.
2026-11-07 PROF-CONTROL-1 Task 2: implementado --prof-control opt-in (delta_ff cinemático + ld modulado por c_ld derivado); testes unitários e bit-identidade OFF PASS.
2026-11-07 PROF-CONTROL-1 Task 3: 2 controles OFF cmp=0 e 10 corridas ON N=0..4 solo 600 s concluidas com extracoes deterministicas; integridade PASS; EXECUCAO_PROF_CONTROL_1.md.
2026-11-07 PROF-CONTROL-1 Task 4 closing: avaliacao formal dos gates — REPROVADO (FAIL em Primario: 4/4/4/4 cronicas inalteradas e fora% piorou +1,67 pp; FAIL em Monaco: -0,93 pp < 5 pp com piora em C05/C12; FAIL em Guarda: 132,40 s > 123,05 s); default OFF mantido; EXECUCAO_PROF_CONTROL_1.md.
2026-11-07 ABERTURA PROF-GRIP-1: pacing grip-sensível com reserva de 10% nas janelas das 4 crônicas (hipótese única da LAGO_APPROACH_FINDINGS + GRIP_PACING_FEASIBILITY); PLANO e PREREG; matriz 2 OFF cmp=0 + 10 ON com --variedade N.
2026-11-07 PROF-GRIP-1 Task 2: implementado --prof-grip opt-in (teto grip-sensível v_alvo=v_plan·min(1,sqrt(grip/0,85))·sqrt(1/1,10) nas janelas canônicas de C01/C06/C07/C08, grip_atual = tyre.grip_multiplier por tick); bit-identidade OFF exata e 10/10 testes PASS.
2026-11-07 PROF-GRIP-1 Task 3: 2 controles OFF cmp=0 vs PROF-CONTROL-1 e 10 corridas ON --prof-grip com --variedade N solo 600 s concluidas; extracoes deterministicas cmp=0 12/12; cronicas nao zeradas (C06/C07/C08 4/4/4/4; C01 3 em N1/N2); PRELIMINAR_PROF_GRIP_1.md.
2026-11-07 PROF-GRIP-1 Task 4 closing: avaliacao formal dos gates — REPROVADO (FAIL em Primario: C06/C07/C08 4/4/4/4 inalteradas e C01 3 em N1/N2; FAIL em Monaco: delta offtrack > 0 em N3/N4 e regressao C05; FAIL em Guarda: mediana 129,0–130,4 s > 123,05 s); causa: teto fator=0,9535*sqrt(grip/0,85) era comparado com v_plan*0,93 e foi no-op em >80% da corrida; default OFF mantido; EXECUCAO_PROF_GRIP_1.md.
2026-11-07 ABERTURA PROF-PACE-1: pacing preventivo grip_mode=fixed (grip_ref=0,789547 SOFT 6 voltas DRY 42°C; 0,807 NÃO é o pior caso confirmado pelo TyreState canônico); escada η1=0,48848/η2=0,40000; PLANO e PREREG; decisões do dono pendentes (controles OFF, escalada, Guarda voltas limpas).
2026-11-07 PROF-PACE-1 Task 1 (correção documental): grip_ref recalculado com demonstração n_laps=ceil(600/130,195)+1=6 aplicações exatas; length_factor precisão completa 0,9245415555555555 (versões divergentes removidas); grip_ref=0,7895474400345001; SHAs completos pinados; identidade operacional congelada (--n-cars 1, VER, SOFT, 42,0°C, grip fixed nunca atualizado); decisões do dono marcadas PENDENTE_DO_DONO (controles OFF, escalada η1→η2, Guarda voltas limpas).
2026-11-07 PROF-PACE-1 Task 1 (auditoria final): decisões do dono registradas (CTRL_OFF pareado N=0..4; ON η1 N=0..4; ON η2 N=0..4 condicional; orçamento máx 15; escalada com 5 condições; Guarda = mediana das voltas limpas por realização, mediana das medianas ≤ 123,05 s, OFF inconclusivo por desenho); auditoria clima/grip: 6 realizações DRY 0 transições grip 0,8420→0,8070 (gate grip_ref PASS); variação N0..N4 = jitter IC (variedade_params); t_base 96,202 / t_margin 103,656 / t_cap η1 105,660 / η2 107,080 com grip_ref 0,789547 (todos cabem).
2026-11-07 PROF-PACE-1 FREEZE Task 2 (dono): mecanismo --prof-pace congelado (grip_mode=FIXED grip_ref=0,7895474400345001; escada eta1=0,48848/eta2=0,40000; k_inst no v_safe + k suav 20 m nas passadas; tempos do PACE_MARGIN com 30 m superados; exclusividade vs --prof-grip/--prof-control; 0,93 uma vez -> cap -> passadas; correcao wrap-safe da mascara C01 + teste de cobertura circular; equivalencia cap inativo 1e-9; clima 6 realizacoes DRY 0 transicoes, grip_ref <= grip final 0,807); custos canonicos pelo caminho do controlador: t_base 96,201711 / t_margin_only 103,442766 / t_cap eta1 107,410153 / eta2 109,610725 (folga >= 15,6 s); incremental sobre t_margin: +3,97 (eta1) / +6,17 (eta2); reducoes rel max 38%/44%; estimativa 111-113 s observados = extrapolacao exploratoria do dono (sem status de medicao/gate); ressalva 1: os 4 ticks s1872-1884 (frenagem antecipada C06, dist 8,0 m, regra d_b <= 2*ds) com metricas no relatorio do executor; ressalva 2: determinismo pareado verificado estruturalmente (ICs = f(seed,N) puro) e empiricamente para variedade 0 (REF=CTRL bit-identico); N>0 sem duplicatas nos dados existentes (limitacao registrada para a Task 3).
