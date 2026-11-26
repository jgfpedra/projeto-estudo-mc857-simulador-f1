# PREREG_VARIEDADE_1 — camada de variedade opt-in (micro-ciclo; self-contained)

Branch `feat/sanidade-produto` · 2026-10-21 · commitado ANTES de qualquer
código/run. **O determinismo é infraestrutura de medição e NÃO morre**:
mesma seed + mesmo profile sem a flag = corrida bit-idêntica ao hoje.
Zero promoção/flip/retreino; mirrors/loader/fastf1 intocados; nada de
pool (demos = seed 0 + variedade; 76-79 seguem VIRGENS).

## §0 Contexto
SANIDADE-1b RATIFICADO (ANEXO_SANIDADE_1B_REVIEW.md, commit 083ddea).
REGRA NOVA da review — **reconciliação de pins ENTRE SI (absolutos ×
bit-identidade × âncoras, ANTES do commit)**: 1ª aplicação aqui (§3).
Âncoras F4v15 (bit-identidade da flag OFF): v0 3674/2482/136,0/3/22,1;
comp 752/292/140/13/25,2. Suíte base 25F/322P/3S. NITs da review: mostrar
tempo com a MESMA precisão do instrumento (246,8, não 247); sign do
breaker −0,4 (spec errada — v1 preservado).

## §1 Mecanismo pinado (camada-only; flag `--variedade N`, default 0 = OFF)
- **PRNG PRÓPRIO derivado de (seed, N)**: `random.Random(int(sha256(
  "<seed>//variedade//<N>"), 16))` — o padrão da casa (weather_rng_from_seed);
  NUNCA o RNG global da sim (o clima/loteria continua vivendo na seed
  principal — intocado).
- **Perturba SÓ condições iniciais, ANTES do tick 0** (por carro, na ordem
  do grid):
  (a) **jitter de grid**: d_long ~ U(−0,5, +0,5) m; d_lat ~ U(−0,3, +0,3) m
      — dentro da folga física real do grid (derivação §2);
  (b) **offset de pace**: fator f_mu ~ U(0,98, 1,02) aplicado ao
      `mu_nominal` do carro NO SPAWN (`handle.mu_nominal = 1,8 × f_mu` ∈
      [1,764, 1,836] ⊂ banda slick documentada [1,7, 1,9] — o knob é a
      condição inicial "carro/piloto", NUNCA o canal dinâmico
      `grip_multiplier` de pneu/clima/superfície, NUNCA as leis dos
      controllers (vplan/governor grip_mult 0,788 intocado)).
- **Proibido** (pinado): ruído DURANTE a corrida; clima; física de contato
  (chassis-chassis/solver); leis dos controllers (M2/governor/anti-glue);
  colunas novas de CSV — **o valor de variedade vai em LINHA DE LOG**
  (identidade `[diag]`), não no schema.
- **Reprodutibilidade**: mesma (seed, N) → bit-idêntico; N diferente →
  corrida diferente (streams sha256 distintas por construção).
- **Validação de faixa**: N < 0 → ERRO fail-loud no argparse; N = 0 = OFF
  (nenhum código roda — inércia por construção).

## §2 Derivação dos limites (justificativa dos pins)
- **Grid**: reta disponível 45 m; grid ocupa 4×9+6 = 42 m; +2×0,5 m de
  jitter = 43 m ≤ 45 m ✓. Fileiras ficam ≥ 8,0 m apart (9 − 2×0,5) ✓.
  Colunas: ±(1,9+0,3) = ±2,2 m ⇒ Δlat mínimo entre file-mates 3,2 m >
  largura do carro 1,8 m ✓ (sem sobreposição física no tick 0).
- **Pace**: mu_nominal 1,8 (slick seco; dataclass physics.py:62) × [0,98,
  1,02] = [1,764, 1,836] ⊂ [1,7, 1,9] (banda documentada) — efeito
  qualitativo: ±2% de grip ≈ ±2% de pace de volta, dentro da dispersão
  natural entre seeds (R7a rol 139-192 s).
- **Divergência precoce**: o jitter muda POSIÇÕES ⇒ as colunas de estado
  divergem do PRIMEIRO tick exportado (t=0,2 s = tick 2 < 200) — o pin
  "1ª divergência < tick 200" é satisfeito POR CONSTRUÇÃO e serve de
  detector de vazamento/colisão de streams (se N=2 por acaso reproduzisse
  o jitter de N=1, a checagem falharia).

## §3 Critérios — reconciliação sistemática E ENTRE PINS (regra nova, 1ª vez)
| critério | status | pin |
|---|---|---|
| P1 (v0 flags-off s0) | **ABSOLUTO** | BIT-IDÊNTICO à âncora F4v15-v0 (cc 3674, pós 2482, rol 136,0, hesit 3, fora 22,1). FAIL = PARE (vazamento). |
| P2 (comp flags-off s0) | **ABSOLUTO** | BIT-IDÊNTICO à âncora F4v15-comp (cc 752, pós 292, rol 140, hesit 13, fora 25,2). |
| D2 == D1 (mesma (seed,N) 2×) | **ABSOLUTO** | BIT-IDÊNTICO — comparação BYTE-A-BYTE das linhas de dados (excl. `#`) + stats idênticas. FAIL = PARE (não-determinismo). |
| D3 (N=2) diverge cedo | **ABSOLUTO** | 1ª divergência vs base (P1) E vs D1 < tick 200 (derivação §2). |
| D1–D4 sanidade | **ABSOLUTO** | 10/10 voltas E 0 paradas ≥3 s em TODAS as corridas com variedade (a variedade não pode quebrar a corrida). |
| Contatos das D | **REPORT** | Variam naturalmente — SEM teto (pin do dono). |
| D4 (comp var=1) | **REPORT** | Sanidade cross-profile: stats impressas; sem teto além de 10/10/par 0. |
| MISTAS/OUTROS | **DROP** | Fora do escopo do micro-ciclo. |

**Reconciliação ENTRE PINS (a regra nova, aplicada)**: (i) P1/P2 bit-ídentica
OFF × D2==D1 bit-ídentica ON: COMPATÍVEIS — o RNG da variedade é derivado
(sha256), não global; corridas sequenciais são bit-idênticas (R6/R7a
estabelecido); (ii) nenhum absoluto colide com âncora nesta vez (P1/P2
exigem REPRODUZIR as âncoras — as âncoras satisfazem 10/10 e par 0 ✓ —
checado ANTES do commit, lição da PIN COLLISION do SANIDADE-1b); (iii) D3
diverge < tick 200 × D2==D1: compatíveis (runs distintos, streams
distintas); (iv) o ABSOLUTO 10/10-par-0 aplica-se às D-races SEM colidir
com bit-identidade (P1/P2 não são D-races). **Zero colisões remanescentes.**

## §4 Veredito mecânico
`scripts/variedade_verdict.py` commitado ANTES das corridas, com
`--selftest` contra as âncoras F4v15 (reusa o `stats` do
sanidade1b_verdict — mesma aritmética, 3ª aplicação do padrão-ouro).

    .venv/bin/python scripts/variedade_verdict.py --selftest
    .venv/bin/python scripts/variedade_verdict.py \
      experiments/variedade-1/1_prot_v0.csv experiments/variedade-1/2_prot_comp.csv \
      experiments/variedade-1/3_var1_v0.csv experiments/variedade-1/4_var1_v0_rep.csv \
      experiments/variedade-1/5_var2_v0.csv experiments/variedade-1/6_var1_comp.csv

## §5 Orçamento — 6 corridas SERIAIS (seed 0; ordem pinada; args explícitos;
runs≠arquivos; corridas nunca em paralelo)
1. **P1** v10-cego flags-off s0 (bit-idêntica à âncora).
2. **P2** comp flags-off s0 (bit-idêntica).
3. **D1** v0 `--variedade 1` s0.
4. **D2** v0 `--variedade 1` s0 (REPETE — bit-idêntica a D1 ou PARE).
5. **D3** v0 `--variedade 2` s0 (≠ base e ≠ D1).
6. **D4** comp `--variedade 1` s0 (sanidade cross-profile).

## §6 Árvore (antes dos números)
- P1 ou P2 FAIL → **PARE imediato** (vazamento de RNG/caminho compartilhado).
- D2 ≠ D1 → **PARE imediato** (não-determinismo — o determinismo é
  infraestrutura e não pode morrer).
- D3 sem divergência precoce → **PARE** (streams colidindo — bug de derivação).
- D1-D4 sem 10/10 ou com paradas ≥3 s → **PARE** com trade-off documentado
  (a variedade quebra a corrida — limites revisados em ciclo próprio; SEM
  re-pin neste).
- Tudo verde → variedade **entregue como opt-in** (default 0; canônico
  intocado); adoção = dono.

## §7 Suíte
Base 25F/322P/3S + **4 testes novos** (derivação PRNG; jitter no place_grid;
escala mu_nominal; inércia OFF + validação de faixa) → **ESPERADA
25F/326P/3S** (exata; cláusula ±: desvio justificado no fechamento).

## §8 Regras herdadas
Veredito-antes-dos-números com selftest; probes commitados (nunca inline);
args explícitos; pins com unidade+taxa; serial estrito; tempo exibido na
precisão do instrumento (NIT da review); zero variedade de RUNTIME (só IC);
nada de pool; doc-test.
