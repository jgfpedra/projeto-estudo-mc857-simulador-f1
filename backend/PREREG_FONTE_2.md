# PREREG_FONTE_2 — Desenho de pista: mirrors → OpenF1 → ERRO LOUD (diagnóstico + 1 módulo novo)

Branch `feat/sanidade-produto` · 2026-10-22 · Commitado ANTES de qualquer
chamada/código. ACHADO-P0 confirmado (3d29116): o draw_track NUNCA usou os
mirrors — vai sempre por resolve_track → FastF1 (morto) → preset.

## §1 Escopo e proibições
ZERO treino/sims/10-carros (teto 0); ZERO mudança de
canônico/loader/schema/track_loader/F1MultiContextEnv/requirements
(IMPORTAR/CHAMAR read-only do track_loader É permitido; MODIFICAR,
não); ZERO login/pago. Pools 70-79/76-79 INTOCADOS; caches fastf1
INTACTOS. Código novo: `scripts/track_geometry_free.py` (módulo
diagnóstico) + patch cirúrgico em `scripts/draw_track.py`. MAIS NADA.
`--variedade`/`--modo espectador` proibidos (moot: zero sims).
Chamadas de rede: **teto 10**, TODAS logadas por APPEND em
`experiments/fonte-2/probe_log.md` (formato FONTE-1: endpoint, UTC,
status, latência, tamanho, sha256, nota). Bit-idêntico N/A para rede.

## §2 Perguntas P1–P4 (expectativa + falsificação, ANTES dos números)
- **P1 (mirrors)**: `--track interlagos|monaco|spa` desenha DOS MIRRORS
  (JSONs congelados, read-only), instantâneo, ZERO rede? EXPECTATIVA:
  SIM (load_track_frozen do f1_env é read-only e o desenho só consome
  waypoints/width/name/SF). **FALSIDICAÇÃO-P1**: impossível ler o mirror
  sem modificar loader/env → PARE com mapa de acoplamento (já provado
  desacoplável no P0 — a falsificação é improvável; se o import revelar
  dependência escondida de rede, PARE).
- **P2 (OpenF1 location)**: `/location` de 1 driver (sessão Race) entrega
  x/y/z suficiente para o contorno de Monza 2024? EXPECTATIVA: SIM
  (PROBE-C da FONTE-1 provou o host sem login). **FALSIDICAÇÃO-P2**:
  payload vazio/indisponível após ≤2 retries → fallback GPX/OSM estático
  (dataset comunitário, licença a verificar no probe; ≤2 chamadas).
- **P3 (GOLDEN contra a verdade do espelho)**: as 3 canônicas desenhadas
  DEVEM conferir com os números-pinados: **Monaco_v2: L=3335,2 m, 834
  wp, hairpin C06 κmax 0,1602; Spa_v2: volta ~7.004 m; Interlagos_v2:
  L=4160,4 m (TRACK_LEN canônico)**. O filtro de outliers NÃO pode
  distorcer a geometria (teste unitário com contorno sintético).
  Baseline NÃO são PNGs antigos (nunca existiram p/ Monaco/Spa).
  DISCLOSE preset×mirror no Interlagos (o preset legado difere? por quê?).
- **P4 (fail-loud)**: `--track inexistente` → ERRO com lista de pistas
  disponíveis (canônicas + "qualquer pista F1 2023+ via OpenF1") — NUNCA
  desenha outra pista silenciosamente. Preset antigo só atrás de
  `--legacy-preset` com warning LOUD.

## §3 Árvore (antes dos números)
- Mirrors OK + OpenF1 OK → wiring completo (canônicas = zero rede;
  não-canônicas = OpenF1).
- OpenF1 falha → GPX/OSM estático (licença verificada) p/ Monza.
- Ambos falham → PARE com estado (fail-loud; ≤2 retries/probe contando
  no teto).
- Qualquer necessidade de tocar env/loader/canônico → **PARE + side-car**
  (PROIBIDO neste ciclo).

## §4 Orçamento de chamadas
- PROBE-A (OpenF1): `/sessions?country_name=Italy&year=2024&session_name=Race`
  → session_key de Monza; `/location?session_key=...&driver_number=44` →
  x/y/z. **≤3 chamadas** (+ retries contam).
- PROBE-B (GPX/OSM): SÓ se P2 falhar; ≤2 chamadas.
- Total previsto 2-3; teto 10. Re-runs APPENDEM no log.

## §5 Golden executável
Desenhar as 3 canônicas DEPOIS do patch e conferir contra os
números-pinados dos mirrors (P3): perímetro dos waypoints ≈ L do
espelho (tolerância de discretização declarada: o perímetro do polígono
de N wp aproxima L com erro O(h²·κ) — declarar o desvio por pista);
Monaca κmax do hairpin re-derivável via build_corner_definitions
(saidas_verdict). PNGs salvos em `experiments/fonte-2/`.
DISCLOSE preset×mirror Interlagos: desenhar o preset legado
(--legacy-preset) e comparar com o mirror (L, nº wp, forma).

## §6 Suíte
Base 25F/332P/3S **+ 2 testes unitários recomendados** (filtro de
outliers não distorce geometria sintética; fail-loud levanta erro com
lista de pistas) → **ESPERADA 25F/334P/3S** (desvio justificado no
fechamento se diferente).

## §7 Reconciliação ENTRE pins
- Teto 0 sims × golden "desenhar as 3 canônicas": desenhar NÃO é sim
  (matplotlib Agg, sem engine/pybullet) ✓.
- PROIBIDO modificar env × rota nova no draw_track: o patch usa
  `Track.from_waypoints` + `load_track_frozen` (import read-only) ✓.
- Zero rede p/ canônicas × OpenF1 p/ não-canônicas: rota decide por
  nome ANTES de qualquer chamada ✓.
- P3 golden contra números-pinados × baseline PNG inexistente: os
  números do espelho (L/wp/κ) são a verdade canônica ✓.
