# PRELIMINAR_PROF_GRIP_1 — Task 3 (matriz 12 corridas solo 600 s)

**Data:** 2026-11-07 · **Report-only:** a avaliação formal dos gates é da
Task 4 · **Extrações:** `prof_curva_metrics.py`, 2 leituras por corrida,
`cmp=0` em 12/12 · **Modo:** `off` (o `--mode on` do extrator exige config
sha do TETO do PROF-CURVA-1 — inaplicável; integridade ON atestada pelo
banner `prof_grip=True` + `--variedade` no log).

## Desvio do mandato, disclosado

O comando do mandato passava `--rejoin-handoff align --rejoin-ramp` nos
controles — o runner **rejeita** (`error: --rejoin-handoff align requer
--profile composite`) e, de qualquer forma, alinhar o handoff mudaria a
trajetória e inviabilizaria o `cmp=0` contra os controles históricos que o
próprio mandato exige. A matriz rodou com os **defaults do runner**
(handoff off, ramp off) — a única configuração self-consistente com a
validação de bit-identidade. Evidência no log
`corridas/CTRL_interlagos_OFF.log` (leva descartada).

## Integridade

12/12 exit=0; 3.002 linhas; banners `prof_grip=False` ×2 / `True` ×10;
`--variedade` 0..4 nos logs ON; sidecars vazios (convenção solo);
**bit-identidade de corrida OFF: `cmp=0` vs os controles do
PROF-CONTROL-1 nas duas pistas** (com `--track Interlagos` capital — alias
resolve para a mesma pista frozen).

## Interlagos (5 realizações independentes, `--variedade N`)

| corrida | fora % | exc | C01 | C06 | C07 | C08 | Reta | mediana volta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CTRL_OFF | 24,567 | 20 | 4 | 4 | 4 | 4 | 4 | 130,195 s |
| ON N0 | 24,533 | 20 | 4 | 4 | 4 | 4 | 4 | 130,195 s |
| ON N1 | 24,367 | 19 | **3** | 4 | 4 | 4 | 4 | 129,639 s |
| ON N2 | 24,067 | 19 | **3** | 4 | 4 | 4 | 4 | 129,005 s |
| ON N3 | 24,667 | 20 | 4 | 4 | 4 | 4 | 4 | 130,428 s |
| ON N4 | 24,433 | 20 | 4 | 4 | 4 | 4 | 4 | 130,069 s |

## Monaco

| corrida | fora % | exc | C05 | C12 | mediana volta |
|---|---:|---:|---:|---:|---:|
| CTRL_OFF | 56,933 | 41 | 3 | 4 | 211,786 s |
| ON N0 | 56,933 | 41 | 3 | 4 | 211,786 s |
| ON N1 | 56,167 | 41 | 3 | 4 | 208,258 s |
| ON N2 | 56,633 | 41 | 3 | 4 | 212,844 s |
| ON N3 | 57,000 | 42 | **4** | 4 | 213,340 s |
| ON N4 | 57,300 | 42 | **5** | **3** | 215,816 s |

## Observações report-only (para a Task 4)

1. **As crônicas não zeraram:** C06/C07/C08 = 4/4/4/4 em TODAS as
   realizações; C01 = 3 em N1/N2 (uma saída a menos) e 4 nas demais. Pela
   letra do prereg ("qualquer saída crônica em qualquer ON falsifica a
   hipótese"), a hipótese única está **falsificada** — avaliação formal na
   Task 4.
2. **Autoridade estrutural limitada do teto:** o cap é
   `min(alvo_hist = 0,93·v_plan, v_plan·fator)` — o mecanismo só binda
   quando `fator < 0,93`, i.e. `tyre_grip < ~0,809` (grip de fim de vida; o
   passe 1 roda com 0,842 → no-op por construção, como testado). O trim
   efetivo em fim de vida é de ~1-2% do alvo — pequeno demais para zerar
   saídas que consomem 24 cm de margem.
3. **Custo de ritmo ≈ nulo:** medianas ON dentro de ±0,6 s da OFF
   (Interlagos) — consistente com o piso do estudo de viabilidade (≤ +2,05
   s); a Guarda não é o problema aqui.
4. **Monaco:** Δofftrack ≤ 0 em N1/N2, > 0 em N3/N4 (+0,07/+0,37 pp), com
   regressão localizada em C05 (3→4→5) em N3/N4 e melhora em C12 no N4.
5. A direção do efeito em C01 (N1/N2: 3 crônicas vs 4) é consistente com o
   cliff de pneu, mas a autoridade do teto (item 2) limita o alcance —
   qualquer mecanismo com autoridade real precisaria de reserva ≥ margin
   ou substituir o margin dentro das janelas (mudança de prereg, não pós-hoc).
