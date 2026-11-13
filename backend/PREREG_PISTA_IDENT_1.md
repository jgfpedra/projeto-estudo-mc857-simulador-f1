# PREREG_PISTA_IDENT_1 — Identidade de pista verificável + resolução separada (engenharia; 0 sims)

Branch `feat/sanidade-produto` · 2026-10-22 · Commitado ANTES de qualquer
patch. Ciclo de ENGENHARIA: separa a RESOLUÇÃO DE DADOS da adaptação
Gymnasium, mata o fallback silencioso de Interlagos no treino/eval e
registra IDENTIDADE verificável (solicitada × efetiva × fonte × hash).
O MESMO fluxo do ACHADO-P0/FONTE-2, agora no caminho de treino.

## §1 T0 — inventário de call-sites (arquivo:linha; classificação)
| call-site | uso hoje | fallback silencioso? |
|---|---|---|
| `f1_env.py:391` (F1MultiContextEnv.__init__ → resolve_track) | TREINO/eval via env (train_dagger etc.) | **SIM** — resolve_track cai FastF1→São Paulo GP→preset Interlagos sem aviso |
| `f1_env.py:69-130` (resolve_track + _fastf1_event_name + _FASTF1_EVENT_ALIASES + FASTF1_*) | o próprio resolvedor | é a FONTE do fallback (steps 3-5) |
| `eval_teacher_solo.py:80` (R.resolve_track session='R') | baseline professor | **SIM** (mesma cadeia) |
| `draw_track.py:66-67` (--legacy-preset) | pós-FONTE-2, JÁ fail-loud na rota nova; legacy atrás de flag | NÃO (preso) |
| `audit_track_geometry.py:132,138` | diagnóstico (investigação) | SIM, mas script de investigação (fora do runtime de produto) — report-only |
| `track_geometry_free.py:46` (load_track_frozen read-only) | mirrors FONTE-2 | NÃO (mirror direto) |
| r9/r10/r11/r7b/largada_dt_probe (load_track_frozen 'interlagos') | scripts de investigação hardcoded | NÃO (não usam resolve_track) |

Zonas proibidas verificadas: o patch toca SÓ f1_env.py (move código
para o módulo novo + wrapper), o módulo NOVO
`backend/domain/track_resolution.py`, eval_teacher_solo.py (identidade
+ erro), train_dagger.py (só se tiver UI de pista — ver T2) e testes.
mirrors/caches/schema/pools/draw_track/--prof-repair/--variedade/
perfis-default INTOCADOS. `--prof-repair` (5beb1da) NÃO pode quebrar:
testes existentes continuam verdes.

## §2 G1 — separação (nenhuma mudança de comportamento)
- Mover de `f1_env.py` para `backend/domain/track_resolution.py`:
  `resolve_track`, `_fastf1_event_name`, `_FASTF1_EVENT_ALIASES`,
  `FASTF1_DEFAULT_*`, `FASTF1_CACHE_DIR`, `build_interlagos_track`,
  `load_track_frozen` (e o que for exclusivo deles).
- `f1_env.py` importa do módulo novo (`from backend.domain.
  track_resolution import resolve_track, load_track_frozen`) — TODOS os
  imports existentes (`from backend.model_train.f1_env import
  resolve_track/load_track_frozen`, inclusive os de investigation
  scripts e track_geometry_free) continuam funcionando via re-export.
- GOLDEN: nenhum caminho muda comportamento — a suíte inteira
  (25F/336P/3S, incluindo o golden Interlagos de 6 tabelas e os testes
  --prof-repair bit-identidade) é a prova primária; zero sims.

## §3 G2 — fail-loud no treino/eval (fallback só com flag)
- `resolve_track(..., allow_fallback=False)` (default) → se a pista
  pedida não carregar (nem CSV, nem FastF1, nem mirror), levanta
  `TrackResolutionError` com a LISTA de opções (mirrors canônicos
  interlagos/monaco/spa; CSV; pista F1 2023+ via OpenF1; preset legado
  atrás de --allow-track-fallback).
- `allow_fallback=True` (flag `--allow-track-fallback` no race_diagnostic
  e no eval_teacher_solo; env F1MultiContextEnv herda default False)
  preserva o comportamento antigo COM warning LOUD + registro
  `FALLBACK` na identidade.
- NOTA de compatibilidade: `load_track_frozen` (mirrors) é lookup
  DIRETO e nunca cai no preset — não é afetado. O fallback que morre é
  o do PLANO FASTF1→preset (steps 3-5 de resolve_track). O
  `audit_track_geometry.py` (script de investigação) passa a usar
  allow_fallback=True com aviso (mantém funcionamento; fora do runtime).

## §4 G3 — identidade verificável
- Função `track_identity(track) -> dict` no módulo novo: name, n_wp,
  length_m, sha256 da geometria (hash dos waypoints — o mecanismo do
  frozen sha 67ca11dc211c8c78 é o modelo), fonte (csv/mirror/fastf1/
  openf1/preset), requested (nome pedido).
- `race_diagnostic.py`: a linha `[diag] pista FROZEN` JÁ registra
  nome/wp/SF/sha (canônico) — ESTENDER com `requested=X fonte=Y` quando
  o caminho NÃO é o frozen do runner (o runner usa load_track_frozen
  direto; a identidade nova cobre os caminhos de ENV/eval).
- `eval_teacher_solo.py`: imprime e registra identidade (requested ×
  efetiva × fonte × hash × wp × L); divergência → warning LOUD.
- `F1MultiContextEnv`: expõe `self.track_identity` (dict) para
  consumidores de treino.

## §5 Golden (tabela de casos; T3)
| caso | esperado |
|---|---|
| CSV existente (--csv em draw_track / reference_csv) | inalterado; fonte=csv |
| mirror canônico (interlagos/Monaco/Spa via load_track_frozen) | inalterado; fonte=mirror |
| resolve_track('Monaco', 2024) SEM rede e SEM cache fastf1 | **TrackResolutionError com lista** (antes: preset Interlagos silencioso) |
| resolve_track('Monaco', 2024, allow_fallback=True) | preset Interlagos + WARNING LOUD + registro FALLBACK |
| suíte completa | 25F/336P/3S + testes novos (abaixo), zero FAIL novo |

## §6 Plano de testes (+3-4 declarados; suíte esperada 25F/339P/3S ±)
1. t_g1_reexport: `from backend.model_train.f1_env import
   resolve_track, load_track_frozen` funciona (compat); módulo novo
   existe e é a fonte.
2. t_g2_fail_loud: resolve_track pista inexistente (sem CSV/cache)
   levanta TrackResolutionError com a lista; allow_fallback=True devolve
   Track de Interlagos (preset) + registra FALLBACK.
3. t_g3_identity: track_identity devolve os campos; hash estável
   (determinístico entre chamadas); requested vs efetiva.
4. t_g3_g2_wiring: f1_env expõe track_identity; eval_teacher_solo tem
   o import/uso (source-check).

## §7 Orçamento e proibições
- **0 sims**; zero rede esperada (nenhuma chamada; se ocorrer, log +
  disclose imediato). Zero corridas de produto; pools 70-79/76-79
  VIRGENS; caches fastf1 INTACTOS.
- Proibido: expandir pistas, telemetria OpenF1 (o import read-only de
  track_geometry_free é permitido, mas NÃO é necessário — mirrors já
  resolvem as canônicas), A×B, flip de default (o default muda para
  FAIL-LOUD no caminho de ENV/eval por DESIGN deste ciclo — o produto
  race-runner segue frozen intocado), retreino.

## §8 Reconciliação ENTRE pins
- G1 "nenhuma mudança de comportamento" × G2 "fallback morre": G2 é
  opt-in por flag na ASSINATURA (default allow_fallback=False muda o
  caminho de env/eval — pinado AQUI como o objetivo declarado do
  ciclo, com o produto race-runner (frozen) intocado) ✓.
- Bit-identidade --prof-repair × refactor do f1_env: o patch PROF-REPAIR
  vive em race_diagnostic.py (ProfessorRaceController) e não importa
  resolve_track; testes existentes são a prova ✓.
- f1_env.py:81 whitespace não-meu: preservado (não commitado) ✓.
