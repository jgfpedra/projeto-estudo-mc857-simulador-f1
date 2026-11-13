# PROJ-GATE-2 — autópsia do PARE PROJ-GATE-1

**Modo:** report-only; Monaco; zero simulações/smokes; suíte não executada.
**Flag:** permanece default-OFF; nenhuma promoção.

## Resultado de proveniência e método

Todos os artefatos autorizados passaram hash de disco = `git show` = pino preregistrado; headers CSV/eventos e amostras passaram validação fechada. Ver `3_execution.log` e `3_branch_geometry.json` para os hashes completos.
A comparação de ramo é o proxy registrado `ns_raw` contra `wp*` (waypoint Euclidiano mais próximo; empate no menor índice), local se gap circular × `3335.2/834 <= 32 m`. Ela não observa um campo de ponteiro interno do env.
A soma da polyline frozen é 3335.234577 m (3335.2 m a uma casa decimal); a métrica usa o pino preregistrado 3335.2/834 m por waypoint. `official_length_m` é metadado separado.
Os metadados de R1 e R2 confirmam a mesma variância `grid,compound`, seed de clima 0 e a mesma ordem de grid/compostos.

## Scorecard H1/H2/H3

| Hipótese | Resultado | Evidência e limite |
|---|---|---|
| H1 — alvo congelado escolhe ramo errado | **LOSING / não identificável** | O estado da âncora/alvo não é gravado; âncora atualiza a cada tick lógico (runner `:794-800`) e CSV registra 5 Hz após o passo (`race_diagnostic.py:904,918-923`). Distância alvo→reentrada não estimável (`run_race_10_cars.py:327-351,477-495`). |
| H2 — ponteiro vivo do env salta >32 m | **não diretamente observável** | Proxy `ns_raw` errado em R2 off-track: 5/18045 (0,0277%); os cinco outliers são amostras isoladas, com pico de 1.403,663 m. `ns_raw` vem de busca global `nearest_segment` sobre XY (`race_diagnostic.py:1010-1015`), não de estado interno do env. |
| H3 — g2 mede o ponteiro interno para esse diagnóstico | **apoia a mis-especificação** | g2 é `|wrap(Δs,L)−Δcum_dist|` (`proj_gate_1_audit.py:57-76`): `s` é arco recalculado no runner (`race_diagnostic.py:921-923,1291-1299`), `cum_dist` é odômetro; `ns_raw` é outro cálculo global de XY. O corte histórico segue válido como proxy, mas não identifica ponteiro/ramo. |

## Localidade de ramo do proxy

| Braço | Estado | Amostras | Ramo errado | Fração | p95 gap (m) |
|---|---:|---:|---:|---:|---:|
| R1 OFF | all | 30000 | 0 | 0.00% | 3.999 |
| R1 OFF | ontrack | 17055 | 0 | 0.00% | 3.999 |
| R1 OFF | offtrack | 12945 | 0 | 0.00% | 3.999 |
| R2 ON | all | 30000 | 5 | 0.02% | 3.999 |
| R2 ON | ontrack | 11955 | 0 | 0.00% | 3.999 |
| R2 ON | offtrack | 18045 | 5 | 0.03% | 3.999 |

## Janela de 10 s após reentrada observada

| Braço | Reentradas | Linhas pooled (sobreposição conta) | Fração ramo errado | p95 gap (m) | Janelas com erro | 2+ erros seguidos |
|---|---:|---:|---:|---:|---:|---:|
| R1 OFF | 345 | 17160 | 0.00% | 3.999 | 0/345 | 0/345 |
| R2 ON | 392 | 19464 | 0.03% | 3.999 | 6/392 | 0/392 |

Na R2, a distância do spatial snap disponível é `abs(lat)` na amostra de reentrada: 392 reentradas, p95 5.959 m, máximo 5.999 m. A distância alvo congelado→descoberta não é estimável; não foi substituída por esse snap.

## g2 e decomposição v1.2

| Braço | Off-track samples | Pares off-track | ≥10 m | /1000 amostras | ≥30 m | /1000 amostras |
|---|---:|---:|---:|---:|---:|---:|
| R1 OFF | 12945 | 12945 | 112 | 8.652 | 45 | 3.476 |
| R2 ON | 18045 | 18045 | 173 | 9.587 | 108 | 5.985 |

Decomposição por classe (contagem; p95 de dxy / |Δns_raw|):

**R1 OFF:**
- ge10: 112 pares; C1 0 (p95 n/a m / n/a wp); C2 0 (p95 n/a m / n/a wp); C3 46 (p95 1.8704425708164663 m / 416.25 wp); C5 66 (p95 3.307436586085905 m / 6.75 wp).
- ge30: 45 pares; C1 0 (p95 n/a m / n/a wp); C2 0 (p95 n/a m / n/a wp); C3 45 (p95 1.8713291979009652 m / 418.59999999999985 wp); C5 0 (p95 n/a m / n/a wp).

**R2 ON:**
- ge10: 173 pares; C1 0 (p95 n/a m / n/a wp); C2 0 (p95 n/a m / n/a wp); C3 110 (p95 1.8719973641963352 m / 433.6999999999997 wp); C5 63 (p95 7.140475873375 m / 7.0 wp).
- ge30: 108 pares; C1 0 (p95 n/a m / n/a wp); C2 0 (p95 n/a m / n/a wp); C3 107 (p95 1.8696826761377625 m / 447.8000000000003 wp); C5 1 (p95 1.618571712145485 m / 7 wp).

## Hesitações e decisão

R2 recriou 28 hesitações pela regra frozen do runner (28 publicadas). A interseção temporal por reentrada, carro e amostra está em `3_branch_geometry.json`; distância alvo/âncora é não estimável.

**Encaminhamento único: arquivar esta bifurcação causal.** H1 não pode ser identificada com o writer congelado; H2 não tem leitura direta do ponteiro interno; H3 confirma que g2 responde a uma pergunta de divergência arco/odômetro, não à localidade do ponteiro. Os dados de `ns_raw` são reportados como geometria do proxy e não bastam para escolher V-A2 ou V-B. Arquivar aqui encerra somente essa bifurcação, sem afirmar que não exista defeito.

### Artefatos e hashes

- `3_branch_geometry.json` SHA-256 `b6596c15d05b15d1989846548b90ef422d525d9da6d899e6d79c430ff6b8c21f`
- `4_g2_class_decomposition.json` SHA-256 `b558715bc1c6e46ac87d06b855094e5577e3f04f587b50d40007f4a8e9fe9128`
- script v1.0 SHA-256 `4f86cd9996041cddc0fd742c603ae1e89f381513bb54264d8b66c5bd39278ea7`
