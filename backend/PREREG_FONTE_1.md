# PREREG_FONTE_1 — Migração da aquisição externa (plano pago → gratuito): diagnóstico READ-MOSTLY

Branch `feat/sanidade-produto` · 2026-10-22 · Commitado ANTES de qualquer
probe/chamada. Decisão do dono (pinada): **sem assinatura F1TV**; migrar o
que for migrável para fonte gratuita; mapear o que ficar órfão.
NENHUMA adoção neste ciclo (FONTE-2 = ciclo próprio).

## §1 Escopo e proibições
ZERO treino; **ZERO sims** (teto 0 — nem race_diagnostic nem GUI); ZERO
corridas 10-carros; ZERO mudança de canônico/loader/schema/requirements;
ZERO login/serviço pago; ZERO scraping de endpoint não-público.
`--variedade`/`--modo espectador` proibidos (moot: zero sims).
Pools 70-79/76-79 INTOCADOS. Caches fastf1 (96K + 935M) = ATIVOS
CONGELADOS: não limpar/mover/reescrever. Bit-idêntico NÃO se aplica a
respostas de rede — o probe REGISTRA a variabilidade, não esconde;
re-runs APPENDEM no log, nunca sobrescrevem.

## §2 Perguntas P1–P3 (expectativa + falsificação pinadas ANTES dos dados)
- **P1 — A migração Jolpica é drop-in?** (classe (i) do F0 cobre as
  necessidades ativas?) EXPECTATIVA: SIM — o F0 achou que o `fastf1.ergast`
  da versão 3.8.3 PINADA já aponta para `api.jolpi.ca` e que nenhum código
  ativo consome telemetria de verdade. **FALSIDICAÇÃO-P1**: PROBE-A falhar
  (erro/rede/limite após ≤2 retries) → drop-in NÃO provado; registrar e
  seguir com PROBE-B como teste independente.
- **P2 — Os números-âncora externos citados nos livros são obtíveis via
  Jolpica?** Âncora de teste: **a volta mais rápida da corrida de Monaco
  2024** (round via schedule). EXPECTATIVA: SIM (lap times são plano
  metadado). **FALSIDICAÇÃO-P2 (pinada)**: se NÃO obtível → registrar o gap
  e seguir (âncora pode congelar via dataset estático; decisão de dono).
- **P3 — OpenF1 cobre o gap de telemetria?** (obrigatório: F0 classe (ii)
  não-vazia): cobertura de campos (speed/throttle/brake/gear/position),
  latência, sem-login OK, sessão histórica Monaco 2024. EXPECTATIVA:
  campos completos sem login. **FALSIDICAÇÃO-P3**: sem login exigido →
  marcar e seguir; campos ausentes → registrar cobertura parcial.

## §3 Orçamento de chamadas (teto 30, TODAS logadas)
- PROBE-A (via `fastf1.ergast`, módulo instalado): `get_circuits(2024)`,
  `get_race_schedule(2024)` (localizar round de Monaco; NOTA: nome do
  método conferido na interface instalada — `get_race_schedule`, não
  `get_schedule`), `get_lap_times(2024, round)` — **~3 chamadas**.
- PROBE-B (REST direto via `requests`, SEM fastf1): 2 chamadas ao
  endpoint Ergast-compatível da Jolpica (circuits 2024 + lap times do
  round de Monaco) — **2 chamadas**; medir rate limit OBSERVADO
  (cabeçalhos/erros; sem pressionar o limite).
- PROBE-C (OpenF1, classe (ii) não-vazia): 1-2 chamadas `car_data`
  histórica (Monaco 2024) — **≤2 chamadas**.
- Margem p/ retries: **máx 2 retries por probe** (contam no teto; o
  contador do log é a verdade). Total previsto ≈ 7-9; teto 30.
- **Formato do log** (`experiments/fonte-1/probe_log.md`, APPEND-only):
  `| # | probe | endpoint | timestamp UTC | status HTTP | latência_ms |
  tamanho_bytes | sha256(payload) | nota |` + bloco de resultado por
  chamada (com a variabilidade registrada: re-runs APPENDEM).

## §4 Árvore de decisão (antes dos números)
1. Probes A+B OK e classe (ii) coberta por supersede (mirrors) →
   **recomendação FONTE-2: adoção drop-in via fastf1.ergast e/ou REST
   direto** (SÓ TEXTO; nada adotado aqui).
2. Classe (ii) com necessidade REAL de telemetria → PARE com os pontos
   exatos + resultado do PROBE-C + 3 opções (OpenF1 / dataset congelado /
   eliminar a necessidade) — decisão de dono.
3. Probe falhar por rede/limite após ≤2 retries → **PARE com o estado**
   (fail-loud, sem esconder; re-runs registrados por APPEND).
4. Qualquer necessidade de tocar canônico/loader/schema/requirements →
   **PROIBIDO aqui**; side-car para aprovação do orquestrador.

## §5 Suíte
Sem mudança de código de produção → **ESPERADA INVARIANTE 25F/332P/3S**
(±: se houver testes de probe, declarar no fechamento; não há previstos —
probes são scripts de diagnóstico, não código de produção).

## §6 Reconciliação ENTRE pins
- Teto 30 chamadas × ~9 previstas: folga p/ retries ✓.
- Zero sims × orçamento do ciclo: o simulador NÃO roda ✓.
- APPEND-only × reprodutibilidade: chamadas de rede variam por natureza —
  o log é o registro da VARIABILIDADE (não existe bit-identidade aqui;
  a âncora é o hash por chamada) ✓.
- PROBE-A usa a versão PINADA 3.8.3 (ergast→jolpi.ca confirmado no F0)
  × "exige versão recente": o achado do F0 diz que NÃO exige — o probe
  TESTA essa hipótese (se falhar por versão, o F0 fica refutado e vira
  insumo p/ FONTE-2) ✓.
