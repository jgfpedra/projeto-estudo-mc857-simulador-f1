# PRÉ-REGISTO R11 — MECANISMO DAS PARADAS + PACE GAP + VIABILIDADE WEAVE/SLIDE + RE-ANCORAGEM
# Commitado ANTES de qualquer análise/run/treino (regra permanente).
# Corpus: R7a braço A (race_diag_r7a_disp_s{0..9}) + R10 braço B
# (race_diag_r10_blind_s{0..9}) + logs + events. ZERO runs nos PASSOS 0.*.

## 0.0 — FECHAMENTO DE RESSALVAS R10 (docs/commits only)
0.0.1 Dif ca6b827→4bb7993 do script de veredito: registrar shas, o diff
EXATO (pandas accessor str.startswith — implementação apenas) e o DESVIO DE
PROCESSO honesto: o fix ficou em working tree NA HORA em que o veredito
rodou (script crashou com AttributeError na 1ª execução; fix aplicado;
veredito rodou com o fix; fix+docs commitados juntos em 4bb7993). Checagem
de invariantes: constantes (10pp/15s/+3) e ordem lex D1∧D2∧D3 intocadas —
confirmar por diff.
0.0.2 Estatística usada: MEDIANAS POR BRAÇO (med(A) vs med(B) com
tolerâncias) — o script commitado calcula assim; o texto do prereg R10 dizia
"mediana pareada". DOCUMENTAR a discrepância e computar AMBAS (robustez do
veredito à escolha da estatística: sinais por seed para cada métrica).
0.0.3 Apêndice com unidades explícitas: disciplina = % ticks normais com
disparo; cobertura por TICK pré-saída (%) e cobertura por SAÍDA (fração de
saídas com ≥1 disparo na janela — o "8/100" era por GRUPO (seed,drv), não
por saída); lead médio. RAMO: números não recuperáveis → item INCONCLUSIVO.

## 0.1 — MECANISMO DAS 14 PARADAS do composite (s8: 6, s9: 8)
Tabela por episódio ≥3 s: t início, duração, classificação por regra PINADA:
- RECUP-OFF: episódio INTERSECA um episódio off-track (carro fora quando
  parou) OU começa ≤5 s depois do fim de um off-track (crawl de retorno);
- ENGARRAFO: ≥2 outros carros com v<2 m/s a <30 m de s no início;
- HESIT-CASCATA: nenhum dos anteriores (parada isolada em pista limpa).
Contraste s8 vs s9: onde o composite compra menos contatos com MAIS paradas
no s9 (8 vs 7 do cego)? Paradas são SUBPRODUTO das excursões (RECUP-OFF) ou
fenômeno próprio? Métrica de saída: fração RECUP-OFF vs outras por seed.
RAMO: classificação ambígua (>1 regra) → contar na primeira que casa e
registrar a ambiguidade.

## 0.2 — DECOMPOSIÇÃO DO GAP DE PACE (med 158−136 = 22 s)
Por seed (braço A): tempo total por carro em off-track (s), em hesitação
(v<0,5; s), parado ≥3 s (s); % da volta mediana. Gap = rolante_A − rolante_B
por seed. Explicado = (fora_s + hesit_s + parado_s)/n_voltas aprox; RAMO:
resíduo grande (>50% do gap não explicado) → pace intrínseco do envelope
(documentar: cortar fora% NÃO vira D3 sozinho); resíduo pequeno → cortar
fora% É a alavanca do D3.

## 0.3 — VIABILIDADE WEAVE/SLIDE (go/no-go PINADO antes de olhar)
Sobre as saídas root do corpus R7a (~91/seed × 10): para cada saída, o
comando que o PROFESSOR faria naquele estado — computável offline? O
professor é pure-pursuit com v_plan (parâmetros do reference_controller);
o estado pré-saída está no CSV (s, lat, v, heading err, κ). Simular
δ_prof = atan(2·L·sin(α)/ld) nos ticks da janela pré-saída [−30,0) e comparar
com o envelope do aluno (|δ| p95 da janela). MÉTRICA PINADA: fração de
saídas com ≥5 ticks em que |δ_prof − δ_aluno| > 0,15 rad (correção
substantiva fora do envelope) — **≥50% → GO; <50% → NO-GO** (PASSOS 1-2
não executados; PARE). RAMO: estado não simulável offline (ex.: professor
precisa de estado interno ausente do CSV) → declarar LIMITE DO CRITÉRIO e
tratar como NO-GO conservador (retreino à fila).

## 0.4 — DRAFT DE RE-ANCORAGEM (nada canônico; para a revisão)
Corpus 20 corridas (A+B). Propostas por QUANTI (pinar os quantis ANTES):
fora% p75 do corpus como teto de produto; rolante mediana +10 s como teto;
paradas = 0 em clima seco (w_trans=0), tolerância explícita T em clima
adverso (proposta: mediana do braço melhor); wanderers: mediana 0/seed e
nenhum seed > mediana+2. Tudo DRAFT — a revisão aprova/corta no prereg do
gate futuro.

## RAMOS GERAIS
- falha técnica em 0.1/0.2 → item INCONCLUSIVO documentado (não bloqueia).
- 0.3 NO-GO ou limite → PASSOS 1-2 NÃO executados; PARE com 0.4 + docs.
- 0.3 GO → prereg de RETREINO (PASSO 1) com hipótese pinada, canárias,
  best-por-VAL, commit de logs por iteração — ANTES de qualquer treino.

## LIMITAÇÕES herdadas
Fronteira skidpad ≤16 m/s; understeer 1,45× (backlog); slip=regime (R9);
critérios pré-canônicos = referência histórica até re-ancoragem aprovada.
