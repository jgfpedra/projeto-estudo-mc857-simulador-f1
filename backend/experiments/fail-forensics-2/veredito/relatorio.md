# FAIL-FORENSICS-1b — relatório de medição

**Rótulo:** diagnóstico report-only; uma realização por célula (`N=1`).
**Escopo:** Etapa 1. Nenhuma promoção, mudança de comportamento, retreino, re-pin ou inferência estatística.

## Integridade e condições

- `blind_interlagos` / interlagos: pista SHA-256 `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613`, SF 729, 1131 waypoints, 10 carros, 3000 ticks, transições de clima 0.
- `composite_interlagos` / interlagos: pista SHA-256 `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613`, SF 729, 1131 waypoints, 10 carros, 3000 ticks, transições de clima 0.
- `professor_monaco_s0` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `professor_monaco_s1` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `professor_monaco_s2` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `professor_monaco_s3` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `professor_monaco_s4` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `aluno_monaco_s0` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `aluno_monaco_s1` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `aluno_monaco_s2` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `aluno_monaco_s3` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `aluno_monaco_s4` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `blind_monaco` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 1 carros, 3000 ticks, transições de clima 0.
- `composite_monaco` / monaco: pista SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`, SF 0, 834 waypoints, 10 carros, 3000 ticks, transições de clima 0.

CSV composite: `res_0..res_15` presentes (checado pelo leitor); autoridade, clima, pneu e odômetro foram preservados.
Os CSVs não têm x/y nem índice cru do `nearest_segment`: os saltos são medidos pelo `s` persistido contra `cum_dist`; os segmentos anterior/seguinte são derivados do `s` e da geometria frozen.

## Resumo por corrida

| Pista | Braço | N carros | Fora (%) | Saídas | contatos solver (episódios/pontos) | preso R3 | hesitações | saltos ≥10/20/30 m | erro p95 (m) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| interlagos | blind | 10 | 22.12 | 180 | 90/53658 | 61 | 3 | 0/0/0 | 0.00 |
| interlagos | composite | 10 | 25.21 | 219 | 30/12691 | 75 | 14 | 3/1/1 | 801.24 |
| monaco | professor | 1 | 56.93 | 41 | 0/0 | 15 | 0 | 21/16/14 | 365.31 |
| monaco | professor | 1 | 56.93 | 41 | 0/0 | 15 | 0 | 21/16/14 | 365.31 |
| monaco | professor | 1 | 56.93 | 41 | 0/0 | 15 | 0 | 21/16/14 | 365.31 |
| monaco | professor | 1 | 56.93 | 41 | 0/0 | 15 | 0 | 21/16/14 | 365.31 |
| monaco | professor | 1 | 56.93 | 41 | 0/0 | 15 | 0 | 21/16/14 | 365.31 |
| monaco | aluno | 1 | 45.00 | 34 | 0/0 | 15 | 1 | 9/4/4 | 325.66 |
| monaco | aluno | 1 | 45.00 | 34 | 0/0 | 15 | 1 | 9/4/4 | 325.66 |
| monaco | aluno | 1 | 45.00 | 34 | 0/0 | 15 | 1 | 9/4/4 | 325.66 |
| monaco | aluno | 1 | 45.00 | 34 | 0/0 | 15 | 1 | 9/4/4 | 325.66 |
| monaco | aluno | 1 | 45.00 | 34 | 0/0 | 15 | 1 | 9/4/4 | 325.66 |
| monaco | blind | 1 | 45.00 | 34 | 0/0 | 15 | 1 | 9/4/4 | 325.66 |
| monaco | composite | 10 | 43.15 | 346 | 29/110794 | 120 | 12 | 112/50/45 | 1122.90 |

## Pista × braço × causa-raiz

| Pista | Braço | Causa | Off-track | Contato | Preso | Hesitação | Salto projeção | Total |
|---|---|---|---:|---:|---:|---:|---:|---:|
| interlagos | blind | COLISÃO | 23 | 90 | 6 | 0 | 0 | 119 |
| interlagos | blind | CURVA | 51 | 0 | 4 | 0 | 0 | 55 |
| interlagos | blind | RECUPERAÇÃO | 106 | 0 | 51 | 3 | 0 | 160 |
| interlagos | blind | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| interlagos | composite | COLISÃO | 5 | 30 | 2 | 0 | 0 | 37 |
| interlagos | composite | CURVA | 56 | 0 | 5 | 1 | 0 | 62 |
| interlagos | composite | RECUPERAÇÃO | 154 | 0 | 68 | 13 | 3 | 238 |
| interlagos | composite | TRAJETÓRIA | 4 | 0 | 0 | 0 | 0 | 4 |
| monaco | professor | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | CURVA | 4 | 0 | 2 | 0 | 0 | 6 |
| monaco | professor | RECUPERAÇÃO | 37 | 0 | 13 | 0 | 21 | 71 |
| monaco | professor | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | CURVA | 4 | 0 | 2 | 0 | 0 | 6 |
| monaco | professor | RECUPERAÇÃO | 37 | 0 | 13 | 0 | 21 | 71 |
| monaco | professor | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | CURVA | 4 | 0 | 2 | 0 | 0 | 6 |
| monaco | professor | RECUPERAÇÃO | 37 | 0 | 13 | 0 | 21 | 71 |
| monaco | professor | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | CURVA | 4 | 0 | 2 | 0 | 0 | 6 |
| monaco | professor | RECUPERAÇÃO | 37 | 0 | 13 | 0 | 21 | 71 |
| monaco | professor | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | professor | CURVA | 4 | 0 | 2 | 0 | 0 | 6 |
| monaco | professor | RECUPERAÇÃO | 37 | 0 | 13 | 0 | 21 | 71 |
| monaco | professor | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | CURVA | 6 | 0 | 3 | 0 | 0 | 9 |
| monaco | aluno | RECUPERAÇÃO | 28 | 0 | 12 | 1 | 9 | 50 |
| monaco | aluno | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | CURVA | 6 | 0 | 3 | 0 | 0 | 9 |
| monaco | aluno | RECUPERAÇÃO | 28 | 0 | 12 | 1 | 9 | 50 |
| monaco | aluno | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | CURVA | 6 | 0 | 3 | 0 | 0 | 9 |
| monaco | aluno | RECUPERAÇÃO | 28 | 0 | 12 | 1 | 9 | 50 |
| monaco | aluno | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | CURVA | 6 | 0 | 3 | 0 | 0 | 9 |
| monaco | aluno | RECUPERAÇÃO | 28 | 0 | 12 | 1 | 9 | 50 |
| monaco | aluno | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | aluno | CURVA | 6 | 0 | 3 | 0 | 0 | 9 |
| monaco | aluno | RECUPERAÇÃO | 28 | 0 | 12 | 1 | 9 | 50 |
| monaco | aluno | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | blind | COLISÃO | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | blind | CURVA | 6 | 0 | 3 | 0 | 0 | 9 |
| monaco | blind | RECUPERAÇÃO | 28 | 0 | 12 | 1 | 9 | 50 |
| monaco | blind | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |
| monaco | composite | COLISÃO | 11 | 29 | 4 | 0 | 1 | 45 |
| monaco | composite | CURVA | 55 | 0 | 23 | 1 | 0 | 79 |
| monaco | composite | RECUPERAÇÃO | 280 | 0 | 93 | 11 | 111 | 495 |
| monaco | composite | TRAJETÓRIA | 0 | 0 | 0 | 0 | 0 | 0 |

## Casos exemplares

1. **SALTO_PROJECAO / RECUPERAÇÃO — composite_monaco, HAM, tick 2024 (202.4s), s=1446.6m, lat=18.7m, v=9.2m/s.** Maior descontinuidade primária da projeção.
   Authority `rejoin`; th/brk/steer = 0.35/0.00/0.785; Reta Reta / Outro, modo LINHA-RETA; impulso anterior nan N·s / Δv nan m/s; salto antecedente nan m.
2. **CONTATO / COLISÃO — composite_monaco, HAM, tick 4854 (485.4s), s=1328.1m, lat=0.4m, v=1.8m/s.** Maior impulso solver-side agregado no episódio.
   Authority `policy`; th/brk/steer = 0.95/0.00/0.038; Reta Reta / Outro, modo LINHA-RETA; impulso anterior 339703.75027285476 N·s / Δv 10.2281612977522 m/s; salto antecedente nan m.
3. **OFF_TRACK / RECUPERAÇÃO — composite_monaco, PIA, tick 3020 (302.0s), s=560.8m, lat=6.0m, v=3.6m/s.** Maior episódio contíguo de saída.
   Authority `policy`; th/brk/steer = 0.00/0.23/0.762; C05 Complexo de curva 05, modo SLIDE; impulso anterior nan N·s / Δv nan m/s; salto antecedente nan m.
4. **PRESO_R3_30S / RECUPERAÇÃO — composite_monaco, NOR, tick 3908 (390.8s), s=561.0m, lat=6.0m, v=5.2m/s.** Janela presa R3 com mais ticks off-track.
   Authority `policy`; th/brk/steer = 0.00/0.34/0.742; C05 Complexo de curva 05, modo LINHA-RETA; impulso anterior nan N·s / Δv nan m/s; salto antecedente nan m.
5. **HESITACAO / RECUPERAÇÃO — composite_interlagos, GAS, tick 682 (68.2s), s=104.2m, lat=4.3m, v=0.0m/s.** Hesitação de maior duração dentro da definição congelada.
   Authority `policy`; th/brk/steer = 0.00/1.00/-0.722; C01 Descida do Lago (T4/T5), modo SLIDE; impulso anterior nan N·s / Δv nan m/s; salto antecedente nan m.

## Leitura e limites

Interlagos cego/composite e Monaco cego são reconciliações de âncoras; Monaco Composite é exploração `N=1`. R3 solo replica o âncora `aluno_s0`; R4 tem 10 carros e não é pareado por grid com R3. Os arquivos Monaco prof/aluno s0–s4 têm linhas de dados repetidas por braço, com seed diferente só no cabeçalho: cinco arquivos, uma realização de dados por braço. A tabela mantém cada arquivo visível; não some esses registros como realizações independentes.
Classificação causal é uma regra mecânica de precedência, não uma estimativa contrafactual. O contacto solver-side é a fonte de impulso; a amostragem a 5 Hz não é usada como substituto.
Saltos primários exigem erro `|Δs_wrapped − Δcum_dist| ≥ 30 m`; contagens a 10/20 m são sensibilidade descritiva. Nenhum limiar altera execução ou exclui dados.

## Dados recomendados para a Etapa 2

Usar esses locais/ticks para coletar posição XY do corpo e índice/segmento de `nearest_segment` diretamente, sincronizados com `s`, `lat`, odômetro e authority; guardar pontos de contato do solver. Para Monaco, construir e revisar as bordas permitidas antes de qualquer gate de respeito à pista. Este relatório não deriva bordas a partir da linha central.
