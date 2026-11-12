# v15_residual_r1 — arquivado antes do re-treino r2 (2026-10-16)

## A falha (evidência)
G2 n=4 Interlagos: 0/3 — o composite sai da pista em s≈3096 (Curva do
Lago), lat 8,7, 3 seeds idênticas.

## Decomposição da ação no ponto de falha (s=2005-2270, v=18-21 m/s)
- a_solo = (+0,10, +0,10) — o v10 solo segura a linha
- g = 0,27→0,68 (gate ativando — fantasma uniforme à frente em curva)
- r = (−0,21→−0,41, **−1,56→−1,33**) — freio fortíssimo + esterço contra
- a_comp = (−0,10, −0,79) — o carro perde a curva e sai

## Causa raiz
A distribuição de TREINO usou SÓ heterog+hold+grid5:7 — o cenário de
eval (fantasma uniforme P10, sem hold) não foi visto. O residual mapeou
"carro à frente no D" → "frear forte", sem módulo contextual do κ.

## Parâmetros do treino r1
- Estágios "0:1,4:5", pool 5 pistas, β 1,0→0,3, epochs 50, âncora 4 eps/iter
- Fantasmas: ghost_sf_range=(0,85,0,95), hold 150:250, grid_position=(5,7)
- val_loss: 0,021→0,078; solo hash estável em todas as iterações
- Dataset: 45.248 estados (16d res_in + 2d r_target)
