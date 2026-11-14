# ANEXO_FONTE_2 — Desenho de pista: mirrors → OpenF1 → ERRO LOUD (2026-10-22)

> Ciclo FONTE-2 · Branch `feat/sanidade-produto` · Prereg
> `backend/PREREG_FONTE_2.md` (9ba3f8c, ANTES de qualquer chamada/código).
> Código novo permitido: `scripts/track_geometry_free.py` + patch cirúrgico
> em `scripts/draw_track.py`. env/loader/canônico/schema/requirements
> INTOCADOS. ZERO sims (teto 0); pools 70-79/76-79 INTOCADOS; caches fastf1
> INTACTOS. Rede: teto 10 — **5 chamadas consumidas**, logadas APPEND em
> `experiments/fonte-2/probe_log.md`.

## 1. Cadeia
3d29116 (P0: guarda 0-commits + ACHADO-P0 c/ arquivo:linha + mapa de
acoplamento + NIT Jolpica fechado) → 9ba3f8c (prereg) → módulo v1-v4 +
probe_run (commitados antes de cada uso) → f382938 (patch draw_track +
golden + PNGs + testes) → fechamento.

## 2. ACHADO-P0 (fluxo real confirmado; worklog Task FONTE-2-P0)
- `draw_track.py:23-24` delegava a `f1_env.resolve_track`; os mirrors
  NUNCA eram consultados (`load_track_frozen` vive no mesmo f1_env.py:1292
  sem ser chamado por resolve_track).
- `f1_env.py:103-111`: a ordem era FastF1 (`get_session`+`get_circuit_info`
  — track_loader.py:281/314, plano SESSÃO morto por paywall) → fallback
  São Paulo GP → preset `build_interlagos_track()`. As 3 observações do
  dono CONFIRMADAS (inclusive interlagos passava pelo FastF1 morto; toda
  pista desenhava Interlagos).
- Acoplamento: o desenho usa SÓ waypoints/width/name/SF → desacoplável
  sem tocar o env (Track.from_waypoints de outra fonte).

## 3. Vereditos P1–P4
- **P1 (mirrors) PASS**: `load_mirror` lê os JSONs congelados via
  `load_track_frozen` importado READ-ONLY (loader intocado); instantâneo,
  ZERO rede. GOLDEN: Interlagos **L=4160,4 m EXATO** (1131 wp); Monaco
  **L=3335,2 m EXATO** (834 wp); Spa **L=7003,2 m** vs pinado ~7004
  (−0,01%; 1751 wp); hairpin Monaco **C06 κmax 0,1602** = medido no
  PROF-MONACO-1. DISCLOSE preset×mirror Interlagos: preset legado
  240 wp/4309,0 m (polyline da era de telemetria; +3,6% e 4,7× mais
  grosso que o mirror) — o desenho agora usa a MESMA geometria do
  simulador.
- **P2 (OpenF1 location) PASS (após 2 retries metodológicos)**: Monza
  2024 (session_key 9590, driver 44): contorno de **575 wp, arco
  5.756 m vs 5.793 m oficiais (−0,64%)**. ACHADO DE UNIDADE: **x/y da
  /location são DECÍMETROS** (bounding box 12.568×21.684 unidades ≡
  footprint real de Monza 1.257×2.168 m — razão EXATA 10×); unit_scale
  0,1 documentado no módulo. Métodos mortos no caminho (v1 salto>300 m:
  cruzar a linha não gera salto — 18,3 km/3 voltas; v2 origem: a 1ª
  amostra é GARAGEM, não a linha — 6.599 amostras paradas numa célula;
  v3 cadeia NN: embaraça a banda da linha — 66 km): todos registrados.
  Método final v4: remove parado → célula 60 m mais visitada = linha de
  corrida → janelas entre visitas consecutivas = voltas → arco mais
  próximo da mediana → re-amostra 10 m.
- **P3 (GOLDEN contra os números-pinados) PASS**: ver P1 (4/4
  conferências) + teste unitário do círculo sintético (filtro não
  distorce: arco −5%, raio médio −2% com garagem parada no início).
- **P4 (fail-loud) PASS**: `--track pista-inexistente` → SystemExit 3 +
  lista no stderr (mirrors canônicos; qualquer país F1 2023+ via OpenF1;
  --legacy-preset documentado como "desenhará Interlagos"). O preset
  silencioso MORREU.

## 4. Probes (teto 10; 5 consumidas; log APPEND-only)
| # | endpoint | status | latência | tamanho | nota |
|---|---|---|---|---|---|
| 1-2 | sessions Italy 2024 + location 9590 d44 | 200/200 | 1083 ms / 9522 ms | 694 B / 3.909.444 B | v1 (golden falhou: método) |
| 3-4 | sessions + location (retry 1) | 200/200 | 1287/7062 ms | idem | v2 (origem = garagem) |
| 5 | location 9590 (retry 2 + cache em disco) | 200 | 8298 ms | idem | v3 (NN) → iterações seguintes OFFLINE no cache (v4 PASS; zero chamadas) |

- Rate/latência OpenF1: sessions ~0,7-1,3 KB sub-segundo; **location é
  PESADO: 3,9 MB / 7-9,5 s por sessão×driver** — o módulo faz cache
  local do payload para reuso offline.
- PROBE-B (GPX/OSM): NÃO necessário (P2 passou no retry 2; orçamento
  devolvido).

## 5. Patch draw_track.py (rota nova)
`CSV → MIRROR canônico (zero rede) → OpenF1 location (sem login) →
ERRO LOUD com lista`. `--legacy-preset` preserva o caminho antigo com
AVISO LOUD. Proibições respeitadas: env/loader/track_loader/f1_env
NÃO modificados (import read-only); canônico/schema/requirements
intocados.

## 6. Entregáveis
- PNGs em `experiments/fonte-2/png/`: `interlagos_mirror.png`,
  `monaco_mirror.png`,  `spa_mirror.png`, `monza_openf1.png`.
- Módulo `scripts/track_geometry_free.py` (v4 final, documentado).
- Testes: `tests/test_track_geometry_free.py` (2/2 verdes).
- Suíte: ver fechamento (esperada 25F/334P/3S).

## 7. Disposição
- Comandos do dono (Comandos essenciais): `draw_track --track monaco`
  (mirror, instantâneo), `--track Italy` (OpenF1, sem login),
  `--track xyz` (erro com lista).
- Nenhuma adoção de default de corrida; A×B intocada; zero sims.
