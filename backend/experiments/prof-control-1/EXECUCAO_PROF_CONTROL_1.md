# EXECUCAO_PROF_CONTROL_1 — Task 3 (corridas solo 600 s e extrações)

**Data:** 2026-11-07 · **Branch:** `feat/sanidade-produto` · **HEAD do freeze
da implementação:** `bb9ea5b` · **Método:** corridas solo de 600 s (6.000
ticks a 5 Hz), série estrita, professor, ZERO treino / ZERO matriz de 10
carros · **Estado:** PARE — avaliação dos gates na Task 4 pelo Dono.

## 1. Matriz executada (comandos do mandato, defaults do runner:
`--rejoin bearing --variedade 0 --gov vplan`)

| corrida | comando diferencial | exit | linhas | banner | sha pista |
|---|---|---|---:|---|---|
| CTRL_interlagos_OFF | seed 0 | 0 | 3.002 | prof_control=False | 164876196eb12174 ✓ |
| CTRL_Monaco_OFF | seed 0 | 0 | 3.002 | prof_control=False | 67ca11dc211c8c78 ✓ |
| ON_interlagos_N0..N4 | seed N + `--prof-control` | 0 ×5 | 3.002 ×5 | prof_control=True ×5 | ✓ |
| ON_Monaco_N0..N4 | seed N + `--prof-control` | 0 ×5 | 3.002 ×5 | prof_control=True ×5 | ✓ |

**Bit-identidade de corrida OFF: `cmp=0`** de
`CTRL_interlagos_OFF.csv` vs `c0/INT_N0.csv` e `CTRL_Monaco_OFF.csv` vs
`c0/MON_N0.csv` (a flag OFF reproduz o professor histórico byte a byte em
corrida, nas duas pistas).

**Sidecars:** `<out>_events.csv` vazios (0 bytes) — o runner só grava o
sidecar com eventos de contato; corrida solo sem contato = sidecar vazio por
convenção do extrator ("podendo estar vazio numa corrida solo"), como no
estágio 0.

**Extrações:** instrumento canônico `prof_curva_metrics.py`, 2 leituras por
corrida (24 leituras), **`cmp=0` em 12/12 pares**. Desvio documentado:
`--mode off` em TODAS as leituras — o `--mode on` do extrator exige
"config sha" do TETO do PROF-CURVA-1 no log (regra do ciclo anterior,
inaplicável ao `--prof-control`); a integridade ON é atestada pelo banner
`prof_control=True` (verificado por corrida) + exit 0 + 3.002 linhas.

**Correção de wiring durante a Task 3 (regressão testada):** a primeira leva
das 10 corridas ON falhou na inicialização (`_RaceEnvView` não expõe
`.track`); correção: perfil κ instantânea construído UMA vez no
`ProfessorRaceController` (a partir de `track.waypoints`) e emprestado via
`prof_control_kappa` ao `ReferenceController` — testes 9 passed (incl. novo
teste de regressão do caminho do runner). A matriz abaixo é do código final.

## 2. Resultados por realização

**Degenerescência da matriz (reportada, não decidida):** com clima seco sem
transições e `--variedade 0` (o comando do mandato omitiu `--variedade N`,
diferindo do estágio 0), as 5 sementes por pista são **idênticas nos dados**
(`cmp` dos corpos = 0; N0≡N1≡…≡N4) — a matriz efetiva é **1 realização por
pista**. O estágio 0 do PROF-CURVA-1 usava `--variedade N`; diferença de
matriz registrada para a leitura dos gates.

### Interlagos (vs controle OFF)

| corrida | fora % | excursões | C01 | C06 | C07 | C08 | Reta | mediana volta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CTRL_OFF (≡ INT_N0 histórico) | 24,567 | 20 | 4 | 4 | 4 | 4 | 4 | 130,195 s |
| ON_N0..N4 (réplicas) | **26,233** | 20 | 4 | 4 | 4 | 4 | 4 | **132,402 s** |

Voltas ON: 140,998 / 133,857 / 130,848 / 130,947 s.

### Monaco (vs controle OFF)

| corrida | fora % | excursões | C05 | C12 | demais | mediana volta |
|---|---:|---:|---:|---:|---|---:|
| CTRL_OFF (≡ MON_N0 histórico) | 56,933 | 41 | 3 | 4 | C03 3 · C04 6 · C06 3 · C07 3 · C11 9 · Reta 10 | 211,786 s |
| ON_N0..N4 (réplicas) | **56,000** | 46 | **7** | **5** | C03 3 · C04 6 · C06 3 · C07 3 · C11 9 · Reta 10 | **223,246 s** |

## 3. Leitura report-only (o veredito formal é da Task 4)

- **Gate Primário (Interlagos): as quatro crônicas continuam 4/4 voltas**
  (idênticas ao OFF) e o tempo fora **PIOROU** (+1,666 pp: 24,567 → 26,233);
- **Gate Mônaco:** Δfora% = **−0,933 pp** (< 5 pp) **com regressão
  localizada** (C05 3→7, C12 4→5) — as duas condições do gate falham;
- **Guarda de Ritmo:** mediana Interlagos ON **132,402 s > 123,05 s** —
  estoura pela letra do prereg (a baseline OFF rolante também está acima do
  teto por carregar o tempo fora de pista: 130,195 s; o custo PRÓPRIO do
  mecanismo é +2,207 s/volta ≈ +1,7% sobre a baseline ON×OFF);
- **Monaco:** +11,460 s de mediana (+5,4%) por −0,93 pp de fora — perda de
  ritmo substantiva;
- consistente com a própria anatomia: o gatilho das crônicas é o **estado de
  entrada na curva**, não o esterço no ápice — o feedforward+lookahead não
  endereçou a causa.

## 4. Integridade e proveniência

- 12/12 corridas exit 0; 3.002 linhas; sidecar presente (vazio); SHA da
  pista no cabeçalho; variedade=0 no log; banner com todas as flags;
- extrações determinísticas `cmp=0` ×2 por corrida; `metrics_sha256` em
  todos os JSONs;
- `_status.txt` registra os exit codes de cada corrida.

## 5. Próximo passo

**PARE para avaliação dos gates na Task 4 pelo Dono** (tabelas por curva e
por realização acima; nenhuma promoção, nenhum ajuste post hoc de constante).
