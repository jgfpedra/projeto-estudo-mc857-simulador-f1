# RACING-LINE-1 Task 3 — Gates geométricos do candidato (Emenda nº 1)

**Data:** 2026-11-07 · **Método:** OFFLINE report-only (zero corrida, zero
rede, pista frozen intocada) · **Instrumento:**
`scripts/racing_line_1_corredor.py` (staged ANTES da execução, R7;
determinístico, `cmp=0` em duas execuções seriais, exit 4 = PARE) ·
**Testes:** 9 passed (`test_racing_line_corredor.py` ×8 + `test_state_files.py`)
· **Saída canônica:** `c3/CORREDOR_C08.json` · **Veredito: PARE §7 — arco FORA
DO CORREDOR.**

## Emenda nº 1 (registrada no PREREG_RACING_LINE_1.md)

Limites derivados por bi-tangência ratificados: **s_a = 2282,417 m**,
**s_b = 2342,863 m**, **R = 18,0 m** inalterado. Re-derivação do instrumento a
partir da geometria frozen: **Δ = 0,0 m** contra os limites ratificados
(proveniência exata; giro −139,89°).

## Construção do candidato

| grandezas | valor |
|---|---:|
| centro O | (−290,025189, 1,69475) m |
| sweep do arco | 139,8638° (horário, curva à direita) |
| comprimento do arco | 43,9395 m |
| discretização | 44 amostras, ds = 0,998625 m ≤ 1,0 m |
| linha virtual | 1.159 vértices (SHA-256 `71ff2563…`) |
| vértices frozen substituídos | somente s ∈ (s_a, s_b); externos byte-idênticos |

## Gates

| gate | limite | medido | resultado |
|---|---|---:|---|
| **Corredor** (|lat| máx vs linha central frozen) | ≤ 6,0 m | **10,0667 m** (±cota 0,025; sonda 0,05 m, 2.039 pontos) | **FAIL por 4,07 m** |
| **C1** nas emendas (tangente analítica do arco vs campo suave centrado) | < 1,0° | 0,0163° / 0,0124° | PASS |
| C1 vs direção de segmento frozen (informação) | — | 0,0163° / 1,7136° | artefato do campo descontínuo, documentado |
| **Fechamento** (tangência + segmento de fecho) | < 1e-4 m | 0,0 / 0,0 / Δ 0,0 | PASS |
| **Auto-interseção** | zero | nenhuma | PASS |
| **Externo invariante** | byte-idêntico | ✓ | PASS |

Nota de instrumento: a malha ds ≤ 1,0 m **erra o pico** do desvio (o máximo
contínuo fica entre amostras) — o gate de corredor mede a curva contínua via
sondagem densa do arco (0,05 m, cota de erro 0,025 m registrada). O gate C1
usa o campo de tangente centrada interpolado (o mesmo em que a raiz
bi-tangente é exata); a comparação contra a direção de segmento frozen
(descontínua por construção, saltos de até ~15°/vértice no ápice) fica
registrada como informação, não como gate.

## Leitura — por que o corredor falha

A distância mínima do centro O à linha central é **18 − 10,07 ≈ 7,93 m**, ou
seja, o **raio instantâneo da linha central no ápice da Junção é ≈ 7,9 m**
(muito mais fechado que os 13,5 m do perfil suavizado de 30 m usado pela
definição canônica de curva). Um arco único de R=18 m esterça portanto
~10 m para fora da linha central no ápice — **4,1 m além da meia-largura
(6,0 m)**. A estimativa de origem do PROF-CURVA-1 ("os ~129° cabem num raio
de ~18 m usando a largura da pista") valida-se no **sweep** (o arco existe e
é tangente, C1, sem auto-interseção) mas **não na contenção**: o arco não
cabe na pista frozen.

## Veredito

**PARE §7** (arco fora do corredor é critério explícito de PARE; sem ajuste
post hoc do candidato). Nenhum candidato alternativo (R menor, biarc,
transições) foi avaliado — mudar R ou a construção exige nova
preregistração. ZERO corrida; orçamento de 10 solo 600 s intacto; N=9..12,
N=13..16 e pools 76..79 selados.

## Decisão pendente do Dono

1. **Nova preregistração com candidato que caiba no corredor** — ex.: o
   maior raio bi-tangente contido em ±6,0 m (a derivar em instrumento
   próprio; o teto físico grosseiro é R ≈ 7,9 + 6,0 ≈ 13,9 m no ápice);
2. **Outra construção** (biarc, transições clothoid-like, ou linha com
   deslocamento lateral limitado);
3. **Arquivar** RACING-LINE-1 (a linha suavizada de raio único não cabe na
   geometria da Junção).
