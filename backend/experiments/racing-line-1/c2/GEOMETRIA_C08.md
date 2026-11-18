# RACING-LINE-1 Task 2 — Construção geométrica C08 (arco R=18 m)

**Data:** 2026-11-07 · **Método:** OFFLINE report-only (zero corrida, zero rede,
pista frozen intocada) · **Instrumento:** `scripts/racing_line_1_geometria.py`
(staged ANTES da execução, R7; determinístico, `cmp=0` em duas execuções seriais,
exit 4 = PARE) · **Saída canônica:** `c2/GEOMETRIA_C08.json` ·
**Veredito: PARE §7 do PREREG_RACING_LINE_1.md.**

## Janela canônica

`build_corner_definitions` canônico (κ>0,006, fusão 40 m, rótulos Interlagos):

| grandezas | valor |
|---|---|
| C08 | Junção (T12) — curva à **direita** (σ=−1) |
| janela canônica | s 2276,239 → 2344,246 m (68,0 m) |
| vértices frozen na janela | 20 (emenda efetiva: s 2278,664 / 2343,919; 18 internos) |
| κmax suavizado 30 m | 0,0739 → R_local mín 13,5 m |

## Modo literal do prereg (limites congelados) — SEM solução

O §3 do prereg exige um arco único de R=18,0 m tangente às direções da linha
**nos limites da janela** (posição + tangente congeladas). Com posição e
tangente fixas nos dois extremos e raio fixo, a construção é
superdeterminada — o resíduo mede a coincidência exigida:

| grandezas | valor |
|---|---:|
| **resíduo dos centros \|O(s_a) − O(s_b)\|** | **3,189856 m** (tol 1e-3 m) |
| corda entre os limites | 35,58 m |
| sweep que a corda implica a R=18 | 162,6° |
| giro líquido real da linha na janela | −140,6° |
| combinação σ=+1 (ambos, lado oposto) | 69,43 m |

A incompatibilidade é de **22°**: nenhum arco único de R=18 m fecha a corda e
as tangentes nos dois limites congelados. Pelo §7, isso é **PARE** — sem
ajuste post hoc do candidato.

## Evidência report-only — raízes bi-tangentes com limites LIVRES

Varredura determinística (Newton 2D sobre O(s)=P(s)+σR·N(s), sementes da
grade, dedupe 1 m) de onde um círculo de R=18 m é tangente à linha em DOIS
pontos dentro da janela. **Não é candidato** — é a evidência para a decisão
do dono:

| raiz | s_a → s_b (m) | giro líquido | leitura |
|---|---|---:|---|
| **dominante** | **2282,417 → 2342,863** | **−139,89°** | fillet único tangente à linha cobrindo TODO o giro da Junção; resíduo < 1e-6 m |
| 6 degeneradas | s_a = s_b | 0,0° | pontos onde o raio local da linha vale exatamente 18 m (cusps do offset) — não são arcos |
| secundária | 2299,814 → 2309,929 | −32,08° | fillet local de feição interna |
| secundária | 2304,039 → 2310,193 | +20,08° | fillet local de sinal oposto |

A raiz dominante confirma, na geometria frozen, a estimativa do plano de
origem do PROF-CURVA-1 ("usando a largura da pista, os ~129° cabem num raio
de ~18 m" — o giro real mediu −139,9°).

## O que NÃO foi avaliado (fora do escopo do instrumento congelado)

Corredor (±6,0 m da linha frozen), C1 na emenda, fechamento e
auto-interseção da linha virtual da raiz dominante. São gates de geometria do
prereg, mas para o CANDIDATO — que sob os limites congelados não existe.
Avaliá-los para a raiz de limites livres é trabalho de uma nova
preregistração.

## Decisão pendente do Dono

1. **Nova preregistração legalizando limites DERIVADOS** (pontos de tangência
   bi-tangente, registrados no JSON): o raio 18 m e todas as demais
   constantes do §2 permanecem; muda apenas a regra dos limites
   ("congelados nos extremos da janela" → "derivados dentro da janela").
   O instrumento atual já fornece a raiz exata como ponto de partida;
2. **Outra construção preregistrada** (ex.: biarc nos limites congelados, que
   fecha posição+tangente com dois arcos);
3. **Arquivar** a linha RACING-LINE-1.

Qualquer caminho consome ZERO corridas — o orçamento de 10 solo 600 s segue
intacto e N=9..12, N=13..16 e pools 76..79 seguem selados.
