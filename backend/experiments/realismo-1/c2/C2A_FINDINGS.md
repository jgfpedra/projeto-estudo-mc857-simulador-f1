# REALISMO-1 · C2-A — handoff do rejoin: atribuição e parâmetros

**Data:** 2026-10-30 · **Estado:** report-only concluído; zero simulação, zero edição de produção, zero promoção.

**Entradas:** somente os CSVs N=0 commitados da promocao-1 e as geometrias frozen Interlagos v2 / Monaco v2. O script é `backend/scripts/c2a_attribution.py`; a saída detalhada é `C2A_ATTRIBUTION.json`.

## 1. Método congelado

- Reentrada observável: uma linha 5 Hz `offtrack=0` imediatamente precedida, para o mesmo carro, por linha `offtrack=1`.
- Lateral signed: `obs4 × 6,0 m`. A coluna histórica `lat` não é usada como lateral signed.
- Erro de rumo: `atan2(obs5, obs6)`, em radianos. `obs5/obs6` são o seno/cosseno do heading error usado pela observação frozen.
- Atitude/posição: `body_x`, `body_y`, `s`, heading error, lateral signed, margem lateral `6 − |signed_lat|` e velocidade são registrados por reentrada.
- Nova saída: primeira linha `offtrack=1` do mesmo carro em `(t_reentry, t_reentry + 10 s]`.
- Alinhamento: primeira linha on-track com `|heading_error| <= θ_H` e margem lateral `>= m_H`.
- Nenhum simulador, controller, peso ou CSV foi alterado.

## 2. Resultado por pista

| Pista | Reentradas | Nova saída <=10 s | Taxa | |heading error| mediana / p75 / p95 | Margem mediana / p75 / p95 | Vel. mediana / p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Interlagos | 217 | 119 | 54,8% | 22,52° / 36,21° / 40,50° | 0,299 / 0,514 / 0,914 m | 9,13 / 12,54 m/s |
| Monaco | 378 | 274 | 72,5% | 37,37° / 41,53° / 60,10° | 0,465 / 0,726 / 1,123 m | 9,18 / 10,05 m/s |

As correlações ponto-bisserial entre o valor na reentrada e uma nova saída em 10 s foram fracas:

| Pista | |heading error| × nova saída | margem lateral × nova saída | velocidade × nova saída |
|---|---:|---:|---:|---:|
| Interlagos | +0,028 | −0,017 | −0,016 |
| Monaco | +0,151 | +0,057 | +0,098 |

A correlação fraca não identifica causalidade. Ela só descreve a associação nos estados frozen e não substitui o gate do futuro C2-B.

## 3. Derivação recomendada

### θ_H

**Recomendação:** `θ_H = 20° = 0,3490658504 rad`.

Esse é o limiar angular frozen do protocolo de reentrada já usado na telemetria anterior e fornece um corte explícito para alinhamento, sem ajustar o valor às corridas ON. A análise N0 mostra que a maior parte dos retornos chega com erro relevante, sobretudo em Monaco; o parâmetro deve ser tratado como hipótese de handoff, não como prova causal.

### m_H

**Recomendação:** `m_H = 0,5 m`.

Regra de derivação: escolher o maior degrau de 0,25 m que não excede o menor p75 de margem entre as duas pistas. Os p75 são aproximadamente 0,514 m em Interlagos e 0,726 m em Monaco, portanto o degrau comum é 0,5 m.

### T_H

**Recomendação:** `T_H = 24,0 s`.

Com `θ_H=20°` e `m_H=0,5 m`, o tempo observado até a primeira linha que satisfaz ambos os critérios tem:

| Pista | p50 | p95 | máximo |
|---|---:|---:|---:|
| Interlagos | 0,8 s | 11,8 s | 30,0 s |
| Monaco | 1,4 s | 23,25 s | 57,8 s |

O teto comum é `ceil(max(p95)) = 24,0 s`, limitado pelo Monaco. O futuro handoff deve liberar o controle ao policy ao atingir os critérios ou ao expirar `T_H`; este C2-A não aplica esse comportamento.

## 4. Leitura de engenharia

A maior taxa de nova saída em Monaco coincide com maiores erros angulares e tempos de alinhamento mais longos, mas as correlações lineares são pequenas. A causa não está identificada por este relatório. O achado útil para o C2-B é operacional: o handoff imediato atual ocorre antes de uma fração relevante dos carros satisfazer simultaneamente rumo e margem; um handoff condicionado a `θ_H`, `m_H` e `T_H` é uma hipótese testável.

A saída do C2-B precisa preservar o longitudinal da policy + governor e alterar somente a autoridade de esterço durante o handoff. O teto de 8 m/s na grama e o gap-check não são tocados nesta etapa.

## 5. Proveniência

| Item | SHA-256 |
|---|---|
| `scripts/c2a_attribution.py` | `eca7e4bfc020ec7131dcb89135bdb6147636b75ded0225dba2a32c980a66280c` |
| `experiments/realismo-1/c2/C2A_ATTRIBUTION.json` | `b48ea6c613a0b108d5c8dbd718555f34a123149c853edcc1d1a94070a87c1bb6` |
| Interlagos N0 CSV | `bc87d61509290e852393534b5f343e18a2158cbf85b0d62ce4d91c8031ce4c76` |
| Interlagos N0 events | `7351454f35c690694e11d80c442e6b46855ee4a3d57ecfad171e52d04d7ced9a` |
| Interlagos N0 log | `1f587edee46335735f85ced6673cb733028046116858ed4cd6a36a0f232324b1` |
| Monaco N0 CSV | `dfe7b2dc05e5d8c0db95e351e0c8af6bad9af9fadf2c9c9ba2c3b2ccc74669b5` |
| Monaco N0 events | `fa49a252fd1b0801d0f84bdb9ad49dca40f894c750600aeb053c9b27d2b59a40` |
| Monaco N0 log | `0fb7dc6c0a827b6444f7887e978ec11494b7328d9c7abda602b8260c8928bf86` |
| Interlagos v2 | `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| Monaco v2 | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |

The complete per-reentry records, including body XY and heading/margin values, are in `C2A_ATTRIBUTION.json`.

## 6. Disposição

C2-A está concluído como atribuição offline. Nenhum parâmetro foi aplicado à produção. O próximo passo é o dono revisar estes parâmetros e congelar um prereg próprio do C2-B antes de qualquer implementação ou corrida.
