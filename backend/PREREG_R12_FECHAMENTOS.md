# PRÉ-REGISTO R12 — FECHAMENTOS R11 + MECANISMO DAS HESITAÇÕES + RETREINO DIRIGIDO
# Commitado ANTES de qualquer análise/treino/run. REGRA NOVA: script de
# veredito/decisão roda só com working tree limpo (fix commitado ANTES).

## PASSO 0 — fechamentos zero-runs (regras PINADAS)
0.1 ERRATA s9: recontar paradas do braço B seed 9 por CSV (v<0,5 por ≥3 s)
   vs log. Hipótese de discrepância a verificar: o stoplog do runner só
   registra episódio LIBERADO (contato/autonomia) — episódio que termina
   com a corrida escapa do log. ERRATA no PROJECT_STATE; impacto no
   veredito R10 = zero (D1 olha só as paradas do CANDIDATO).
0.2 DECOMPOSIÇÃO COMPLETA: tabela por seed com Δfora + Δhesit + Δparado +
   resíduo = Δrolante (identidade a verificar). CORRIGIR a frase R11
   "adversos o composite é mais rápido": a tabela R10 mostra A MAIS LENTO
   em s8/s9 (192 vs 150; 154 vs 147) — a leitura correta é "Δfora NEGATIVO
   (menos tempo fora) com resíduo INTRÍNSECO maior". RAMO: identidade não
   fecha (>±2 s) → declarar e usar componentes como estimativas.
0.3 MECANISMO DAS HESITAÇÕES (regra PINADA, primeira que casa + registrar
   ambiguidade), sobre episódios v<0,5 de 0,3-3 s, t>20 s, do braço A:
   - REJOIN-DIP: início ≤5 s do fim de um episódio off-track do carro;
   - TRÁFEGO-YIELD: outro carro a <30 m (Δs) com v<ego no início;
   - CORNER-CRAWL: |κ@10m| > 0,02 sem carro a <30 m;
   - OUTRO: resto.
   PERGUNTA: hesitações = frente única das excursões (REJOIN-DIP dominante
   → retreino pode ajudar) ou preço estrutural da percepção (TRÁFEGO-YIELD
   dominante → tolerância própria no gate futuro, NÃO treinar contra)?
0.4 SENSIBILIDADE DO GO 51% (report-only; o GO FICA DE PÉ pela regra pinada
   R11 — NÃO re-decide): recomputar fração com ld ±20% e limiar 0,10/0,20.
0.5 VALIDAÇÃO DA RECONSTRUÇÃO DE POSE (do script r11_03): consistência
   κ reconstruído vs obs10 em N=1000 ticks on-track (correlação + erro
   mediano). RAMO: erro mediano > 25% da escala → limite declarado.
0.6 QUANTIS ADVERSOS: mediana dos 4 runs adversos (2×s8 + 2×s9, braços
   A e B) recomputada; draft de re-ancoragem por CONDIÇÃO CLIMÁTICA.

## PASSO 1 — RETREINO DIRIGIDO (condicional ao 0.3; prereg PRÓPRIO antes)
- Dataset: janelas das 471 saídas GO (padrão completo) AGREGADO com replay
  de pilotagem normal — proporção declarada no prereg de treino (anti-
  esquecimento v14c/d).
- SE 0.3 CORNER-CRAWL dominante → incorporar ao spec; SE TRÁFEGO-YIELD
  dominante → NÃO treinar contra (preço da segurança; registrar).
- Init: ator do braço A; MESMO stack obs/gov — única diferença = pesos.
- Hipótese REALISTA pinada: teto aritmético do D3 ~5,7 s recuperáveis
  (fora 11,1 − resíduo...); fora% desce SEM perder contatos (cc ≤ +10% A).
- Gates/iteração: canárias solo 3/3; best-por-VAL; no-respawn; log commitado.

## PASSO 2 — AVALIAÇÃO: smoke identidade; piloto {0,8,9} canárias-primeiro;
## N=10 condicional vs braços EXISTENTES (proibido re-rodar); PARE sem adoção.
## Se candidato vivo → R13 = gate por clima, seeds NOVOS 10-19.
