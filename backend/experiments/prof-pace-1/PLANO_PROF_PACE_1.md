# PLANO_PROF_PACE_1 — pacing preventivo com razão alvo fixa (η) nas 4 crônicas

**Versão:** 1.0 · **Estado:** abertura; aguardando Freeze do Dono ·
**Data:** 2026-11-07 (America/Sao_Paulo) · **Branch:** `feat/sanidade-produto`.

## 1. Motivação (evidência homologada)

- **LATERAL_DEMAND_CALIBRATION** (PROF-GRIP-1 seq.): com a capacidade REAL
  (`PhysicsParams.a_lat`, μ=1,8 + downforce), a razão
  `v²·κ_INSTANTÂNEA/a_lat` **separa LIMPA de SAÍDA** nas 3 fontes
  (máx LIMPA 0,6106 < min SAÍDA 0,6205). A convenção suavizada 30 m não
  separa; a convenção path prova que o carro **corta a curva** — o erro é a
  suavização, não a trajetória.
- **OUT_OF_SAMPLE_VALIDATION**: o limiar η=0,615 testado CEGO em ON_N1..N4:
  **TP 62, FN 0, FP 5, TN 1, acurácia 0,9265** — zero falsos negativos
  (toda saída prevista); C06/C07/C08 perfeitos (16/16); os 5 FP concentram-se
  em C01 (passagens limpas com razão > 0,615).
- **WARNING_TIME_FEASIBILITY v2 Kamm**: a autoridade de frenagem no arco é
  **zero** (`a_brake_rem = 0` em C01/C06/C07) — frear no ápice não
  desacelera; a autoridade física pertence ao **pacing de entrada**.
- **PACE_MARGIN_DERIVATION v2**: escada fixa η1=0,48848/η2=0,40000
  (constantes de engenharia pré-declaradas); o cap **engaja de verdade**
  contra 0,93·v_plan (Δ ápice 12,1-15,3 km/h) — ao contrário do PROF-GRIP-1;
  t_lap piso com margin ≤ 108,8 s (folga ≥ 14,3 s da Guarda).

## 2. Hipótese única (falsificável)

Com o cap preventivo `v_target_cap` (η da escada, forma fechada com
downforce, janelas canônicas das 4 crônicas) ativo, **as quatro crônicas
caem para zero no estágio final**; se C06/C07/C08 saírem com o cap ativo, a
hipótese de suficiência do mecanismo é rejeitada (PARE).

## 3. Arquitetura isolada

- Flag opt-in `--prof-pace` em `race_diagnostic.py` (**default OFF;
  OFF byte-idêntico**), engajando **somente no caminho professor**;
- mecanismo: `v_ctrl = 0,93·v_plan`; `v_seed = min(v_ctrl, v_safe(s))`
  com a forma fechada **grip_mode = fixed** (grip_ref constante, §2 do
  prereg); `v_target_cap = passadas backward/forward de prof_curva.py
  sobre v_seed` (ordem congelada: cap depois do 0,93, antes das passadas);
- pacing-only: esterço, rejoin, governor, física, pista frozen,
  `run_race_10_cars.py` intocados.

## 4. Tarefas

1. **Task 1 — abertura, calibração do grip_ref e preregistro (esta).** ZERO
   código, ZERO corrida. PARE para Freeze.
2. **Task 2 — implementação isolada** (`--prof-pace`) + testes de
   bit-identidade OFF. Depois de Freeze. ZERO corrida.
3. **Task 3 — matriz de corridas e extrações** (após novo Freeze).
4. **Task 4 — gates, relatório e closing** (após novo Freeze).

## 5. Matriz de testes (decisão do Dono registrada)

- **Controles OFF pareados: `CTRL_OFF N=0..4`** (5 corridas; o N0
  adicionalmente `cmp=0` vs o histórico `c00391ab…`);
- **10 corridas ON** com `--prof-pace` e `--variedade N` (N=0..4) em
  Interlagos e Monaco, em série;
- **estágio único com η1; escalada pré-declarada para η2** somente sob as
  condições do §5 do prereg (Gate Primário de η1 falhado + integridade
  íntegra + sem divergência de parâmetros + sem quebra de bit-identidade +
  Guarda de η1 avaliável com mediana de medianas ≤ 123,05 s);
- extrações com 2 leituras `cmp=0` por corrida.

## 6. Gates pré-declarados (inalteráveis pós-observação)

1. **C01, C06, C07 e C08: zero saídas no estágio final**;
2. **C06, C07 e C08: qualquer saída com o cap ativo no estágio final →
   PARE e rejeição da hipótese de suficiência**;
3. saída com o cap inativo → **falha de engajamento/cobertura** (não falha
   física do limiar);
4. **Guarda de Ritmo pelo tempo observado no ciclo real** (não pelo piso
   offline) — definição final: mediana das **voltas limpas** (zero
   cruzamentos de 6,0 m) por realização, gate = **mediana das medianas
   ≤ 123,05 s**; realização sem volta limpa = inconclusiva, nunca aprovada;
   mediana de todas as voltas completas publicada para transparência; a
   Guarda do controle OFF não entra no julgamento ("inconclusiva por
   desenho");
5. nenhum gate pode ser alterado após observar os resultados.

## 7. Orçamento

**Orçamento máximo: 15 corridas** (decisão do Dono): 5 controles OFF
pareados + 5 ON η1 + 5 ON η2 (somente com a escalada acionada), todas solo
de 600 s. Sem 10 carros, treino, rede. N=9..12, N=13..16, pools 76..79
selados.

## 8. Governança

prereg staged → Freeze do Dono → execução → linha nos três ledgers →
closing. Este documento não autoriza Tasks 2-4. Estado atual: **PARE para
Freeze do Dono**.
