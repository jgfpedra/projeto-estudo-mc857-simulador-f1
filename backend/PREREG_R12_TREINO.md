# PRÉ-REGISTO R12-PASSO1 — RETREINO DIRIGIDO WEAVE/SLIDE (commitado antes de qualquer treino)
# Base: PREREG_R12_FECHAMENTOS (9ca161e) + decisões 0.3/0.4/0.B. Corpus: braços R7a-A/R10-B.

## PASSO 0 — fechamentos executados (zero runs)
0.A Sensibilidade COMPLETA do GO (grade 3×3: ld_k ∈ {0,48; 0,60; 0,72} × limiar ∈
{0,10; 0,15; 0,20} rad, ≥5 ticks): 83% (ld−20, 0,10) → 38% (ld+20, 0,20).
O ponto pinado (0,60/0,15) = 51%; a vizinhança NÃO inverte a decisão em
faixa razoável (limiar mais frouxo + lookahead menor → mais GO; mais
estrito → menos). O GO fica de pé pela regra R11; grade documentada.
0.B RECOUNT CSV de paradas (20 runs): A s8=6/s9=8 confirmam os logs; B s9
= **8** (não 7) — episódio NOR (t0=593 s, dura 6,6 s) TERMINA COM A CORRIDA
e o stoplog só registra LIBERADO. Reclassificado: RECUP-OFF (dentro de
off-track 582,4-599,8). Tabela canônica de paradas do gate R13 = CSV.
Todos os 14 episódios A e 22 B (6/8 + 14/8) = RECUP-OFF (100%).

## PASSO 1 — RETREINO (hipótese ESCOPADA AO SECO)
- **HIPÓTESE PINADA** (braço A seco seeds 0-7: fora med 30,0% / pior 31,9;
  rolante 158 s; cc med 328; hesit/seed med 14):
  H1: fora% seco −3 pp ou mais (mediana ≤ 27,0%);
  H2: hesit/seed seco −30% ou mais (mediana ≤ 10);
  H3: rolante seco NÃO piora (≤ 158 s);
  H4: cc mediana ≤ +10% do braço A (≤ 361);
  H5: canárias solo 3/3 (Interlagos, Suzuka, Zandvoort; 51 eps ~48/51).
- Dataset: janelas [−30, 0) ticks das 471 saídas GO (R11 0.3) — padrão
  COMPLETO de 2ª ordem (slip, a_lat, δ, κ, v, heading err), r_target =
  δ_prof do pure-pursuit offline (o MESMO motor validado 0.5) — AGREGADO
  com REPLAY de pilotagem normal (amostra aleatória de ticks on-track do
  braço A em proporção 2:1 replay:janelas — anti-esquecimento v14c/d
  1/5→0/3). CORNER-CRAWL no spec (25% das hesitações); TRÁFEGO-YIELD FORA.
- Init: ator do braço A (dagger_actor_best.keras + residual r2) — MESMO
  stack obs(traffic 60d)/gov(vplan); única diferença = pesos do residual
  (BC sobre r_target nas janelas; solo congelado por construção).
- Gates/iteração: canárias solo 3/3; best-por-VAL; no-respawn; log de
  iterações commitado por iteração.
- RAMO: canárias quebram 2 iterações seguidas → PARE do treino, ator
  descartado, autópsia com a grade 0.A na mão. RAMO: dataset < 5k estados
  úteis → declarar e seguir (BC em janelas é pequeno por natureza).

## PASSO 2 — AVALIAÇÃO (árvore do piloto {0, 8, 9})
- Smoke identidade + cabeçalho (ator novo, stack braço A, sha 164876…, SF 729).
- Ordem: canárias PRIMEIRO (H5) → se falha, PARE (não rodar corrida).
- Piloto: seed 0 (seco) e {8, 9} (adverso) com o MESMO comando do braço A
  + --variance grid,compound, trocando SÓ o ator/residual:
  VERDE: seco passa H1-H4 e adverso não colapsa (fora ≤ A+5pp, cc ≤ A×1,5)
       → N=10 (seeds 0-9) vs braços EXISTENTES.
  MISTO: seco parcial (H1-H4 divididos) → UMA revisão de hiper (lr/epochs)
       contra {0,8,9} e re-piloto; confirmação com seed NOVO (ex.: 12).
  VERMELHO: fora seco não desce → PARE; autópsia; DAgger volta à fila.
- N=10 condicional: tabela por seed com 8 métricas R10 + hesit POR CLASSE
  (0.3) + separação das janelas pré-saída + paradas pelo CSV (0.B).
- PARE sem adoção. Candidato vivo → R13 gate por clima (seeds 10-19).

## Comandos base (braço A, referência):
# .venv/bin/python model_train/race_diagnostic.py --profile composite --ticks 6000
#   --laps 99 --track interlagos --seed {N} --gov vplan --variance grid,compound
# Braço candidato: idem + --residual <novo npz> (flag a adicionar, única diferença).
