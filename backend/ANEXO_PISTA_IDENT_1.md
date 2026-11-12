# ANEXO_PISTA_IDENT_1 — Identidade de pista verificável + resolução separada (2026-10-22)

> Ciclo de ENGENHARIA (prereg 3758661; ZERO sims por design — a prova
> de bit-identidade do --prof-repair veio dos TESTES existentes, sem
> corrida). Nenhuma rede. Pools 70-79/76-79 VIRGENS; caches fastf1
> INTACTOS; mirrors/canônicos/schema/draw_track/--prof-repair/--variedade
> INTOCADOS (testes --prof-repair 2/2 verdes pós-refactor).

## 1. Cadeia
3758661 (prereg c/ inventário T0) → 015ecaf (G1: backend/domain/
track_resolution.py = resolução de dados MOVIDA de f1_env (verbatim) +
re-export de TODOS os nomes; G2: resolve_track(allow_fallback=False
default) levanta TrackResolutionError c/ lista; fallback legado atrás
de flag + WARNING LOUD; track_identity()) → 22d13ad (G3 wiring +
MIRROR-FIRST no resolve_track + case-exato do loader) → 9b0f378 (+4
testes) → fechamento.

## 2. T0 — inventário de call-sites (arquivo:linha)
| call-site | fallback silencioso antes? | agora |
|---|---|---|
| `f1_env.py:391` (F1MultiContextEnv → resolve_track) — TREINO | SIM (FastF1→São Paulo→preset Interlagos) | **mirror-first → fail-loud** (allow_track_fallback kwarg default False) |
| `eval_teacher_solo.py:80` (R.resolve_track) | SIM | fail-loud + `--allow-track-fallback` + IDENTIDADE impressa |
| `draw_track.py:66-67` (legacy) | já flagado (FONTE-2) | preso |
| `audit_track_geometry.py:132,138` | SIM (script de investigação) | report-only (fora do runtime) |
| `track_geometry_free.py:46` (load_track_frozen) | NÃO (mirror direto) | referência |
| r9/r10/r11/r7b/largada_dt_probe (frozen hardcoded) | NÃO | NÃO-afetados |
Imports de compat: r10/r9/r11/track_geometry_free/etc. importam
`from backend.model_train.f1_env import resolve_track/load_track_frozen`
→ re-export preserva TODOS.

## 3. Entregas G1-G3
- **G1**: `backend/domain/track_resolution.py` — resolve_track,
  _fastf1_event_name, _FASTF1_EVENT_ALIASES, FASTF1_*,
  load_track_frozen, TrackResolutionError, track_identity, MIRROR_
  OPTIONS. f1_env re-exporta (compat total). A separação: f1_env fica
  com a lógica de AMBIENTE; resolução reutilizável sem importar o Gym.
- **G2**: `resolve_track(..., allow_fallback=False)` — pista pedida
  não carregou = **TrackResolutionError com a LISTA** (mirrors
  interlagos/Monaco/Spa; CSV; OpenF1 p/ 2023+; preset legado via
  flag). O fallback silencioso **MORRE** no default do treino/eval;
  `--allow-track-fallback` (+ kwarg env) preserva o antigo com
  WARNING LOUD + [FALLBACK] na identidade. load_track_frozen intocado
  (nunca caiu no preset).
- **G3**: `track_identity(track)` → requested/efetiva/fonte/sha256/
  n_wp/length_m (hash SHA-256 dos waypoints — mecanismo do frozen sha
  67ca11dc211c8c78 é o modelo). Env: `self.track_identity` + warning
  LOUD solicitada×efetiva; eval_teacher_solo imprime IDENTIDADE.
- **MIRROR-FIRST** (o padrão do draw_track pós-FONTE-2, agora no
  treino/eval): as 3 canônicas resolvem instantâneo/zero-rede/sha
  verificado ANTES do FastF1 legado. BUGS MEUS corrigidos no caminho:
  (1) case-exato do loader ('monaco' ≠ 'Monaco_v2.json' — lição H-1
  reincidente); (2) gate `in MIRROR_OPTIONS` rejeitava 'Monaco'/'Spa'.

## 4. Golden (§5 do prereg — 5/5)
| caso | resultado |
|---|---|
| CSV existente | inalterado (fonte=csv) |
| mirrors interlagos/Monaco/Spa | BIT-IDÊNTICOS (shas 164876196eb12174 / 67ca11dc211c8c78 / 4b05f2c3bbc625fc) |
| pista inexistente (offline) | **TrackResolutionError com lista** (era: preset Interlagos silencioso) |
| allow_fallback=True | preset Interlagos (240wp) + AVISO LOUD + [FALLBACK] |
| suíte completa | **20F/345P/3S** (baseline REAL serial: 26F/335P/3S) |

## 5. Suíte — o ACHADO de produto
- **Baseline REAL (serial, worktree em 5beb1da com dados): 26F/335P/3S**
  (os livros registravam 25F — o run do fechamento PROF-REPAIR deve ter
  tido 1 flutuação de ambiente; ±1 declarado).
- **Final serial: 20F/345P/3S** (+4 testes novos: test_track_resolution).
- **6 LEGACY CURADAS** (todas sintomas do fallback silencioso — passavam
  ou falhavam contra o PRESET procedural 240wp em vez da pista pedida):
  test_race_layer::real_track_curvature_cap (κ 0,13>0,11 era o preset);
  test_velocity_profile::interlagos_v_plan; test_edge_obs::hairpin_
  frontal_curto + wrap_fechamento_circular; test_kappa_sign::interlagos_
  hairpin_sign; test_driver_service::fastf1_driver_database_2024.
- **ZERO falhas novas** (comparação itemizada serial-baseline × serial-final).
- Reparo de teste legado: test_monza_retas_longas 'passava' no preset
  Interlagos (pista ERRADA) — agora passa o frozen Monza_v1
  EXPLICITAMENTE (intenção preservada; o pass anterior era inválido).
- **DISCLOSE de incidente**: rodei 2 suítes CONCORRENTES (violando a
  regra de serial) durante a comparação — o falso "novo" hold_at era
  colisão em /tmp/hold_smoke.csv (caminho compartilhado entre suites);
  o run serial limpo o eliminou. Teste permanece passando isolado e em
  suíte serial. **LIÇÃO: suítes que geram sims em /tmp compartilhado
  também são "sims em paralelo"** — disciplina serial aplica a TESTES
  que rodam corridas, não só a corridas de medição.

## 6. Disposição
- Comandos do dono (Comandos essenciais): o --allow-track-fallback é
  opt-in; treino/eval sem a flag = fail-loud com lista; identidade
  impressa em toda execução de eval (env expõe self.track_identity).
- Produto race-runner: INTOCADO (frozen direto, sha no log — já era
  fail-loud). Zonas proibidas nenhuma tocada.
