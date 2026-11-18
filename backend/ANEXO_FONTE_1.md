# ANEXO_FONTE_1 — Diagnóstico READ-MOSTLY da aquisição externa (fastf1 → fonte gratuita) — 2026-10-22

> Ciclo FONTE-1 · Branch `feat/sanidade-produto` · Prereg
> `backend/PREREG_FONTE_1.md` (27ebff9, ANTES de qualquer probe).
> Decisão do dono (pinada): **sem assinatura F1TV**; migrar o que for
> migrável para fonte gratuita; mapear o que ficar órfão.
> ZERO sims (teto 0 cumprido); ZERO treino; ZERO mudança de
> canônico/loader/schema/requirements; caches fastf1 (96K + 935M)
> INTACTOS; pools 70-79/76-79 INTOCADOS. NENHUMA adoção aqui (FONTE-2 =
> ciclo próprio).

## 1. Cadeia
02ea59b (P0/F0: guarda anti-duplicata + disclose-254 + inventário
classificado) → 27ebff9 (prereg) → probe v1→v3 (commits antes de cada
uso; bug de probe corrigido no v2 — ErgastMultiResponse.content) →
probes A/B/C executados (10/30 chamadas; log APPEND-only) → fechamento.

## 2. Inventário F0 (resumo; tabela completa em experiments/fonte-1/f0_inventario.md)
- **(i) substituível por Jolpica = 3** (schedule/driver_db/Ergast).
- **(ii) órfão na Jolpica = 2** — track_loader `get_session`+
  `get_circuit_info` (fallback LEGADO; o DADO pedido é geometria, já
  suprido pelos mirrors F1DB) e driver_db `get_session("R")` (a chamada é
  do plano sessão; a NECESSIDADE é metadado = Jolpica).
- **(iii) intocar** = mirrors F1DB (geometria canônica) + f1db.db.
- **(iv) congelado/arquivado** = caches (PROIBIDO limpar) + archive.
- **Telemetria de verdade NÃO é consumida por nenhum código ativo** (a
  era R2 registrou "pista frozen é a única via").
- **ACHADO p/ FONTE-2**: o `fastf1.ergast` da versão **3.8.3 PINADA**
  já usa `BASE_URL = https://api.jolpi.ca/ergast/f1`
  (`fastf1/ergast/interface.py:35`) — a Jolpica é drop-in **SEM upgrade**.

## 3. Vereditos P1–P3 (mecânicos, dos probes)
- **P1 — drop-in Jolpica: PROVADO (PASS).** PROBE-A via `fastf1.ergast`
  (3.8.3 pinada): circuits 2024 → 200 (24 circuitos, 1020 ms); race
  schedule 2024 → 200 (24 corridas, 709 ms; Monaco = **round 8**);
  lap_times → 200 (paging padrão de 30 linhas/página; 7 ms — servido do
  cache fastf1 após a 1ª chamada de rede). **A versão pinada JÁ fala com
  a Jolpica — a hipótese do F0 foi CONFIRMADA em execução.**
  (1 TypeError no v1 do probe = bug do MEU script sobre
  ErgastMultiResponse — corrigido v2; retry 1/2 do prereg consumido e
  logado.)
- **P2 — âncora externa obtível: OBTIDA (PASS).** **Volta mais rápida da
  corrida de Monaco 2024 = 1:14.165** (FastestLap rank=1 do endpoint
  `results`, via PROBE-B REST direto). RESSALVA de instrumento: os
  mínimos das chamadas `laps` (2:01.235 / 2:57.857) são ARTEFATOS DE
  PAGING (30 linhas/página default) — a âncora correta vem do
  `FastestLap` do `results`, não do min() de uma página. Reconciliação
  A×B: os dois caminhos (módulo × REST) acertam o MESMO round 8 e os
  mesmos dados.
- **P3 — OpenF1 cobre o gap de telemetria: SIM, sem login (PASS).**
  PROBE-C: sessions `country_name=Monaco&year=2024` → 200 (session_key
  9516); `car_data` driver 16 → 200 (2.915.244 B, 6759 ms, 17.485
  amostras). **Campos: brake, date, drs, driver_number, meeting_key,
  n_gear, rpm, session_key, speed, throttle** — speed/throttle/brake/gear
  ✓; **position NÃO está em car_data (endpoint separado `/position` —
  documentado, não consumido no orçamento)**. Sem login ✓ (200 direto).
  Latência: 1,2 s (sessions) / 6,8 s (car_data 2,9 MB — payload grande
  por sessão×driver).

## 4. Rate limit observado
- **Jolpica**: NENHUM cabeçalho `x-ratelimit-*`/`retry-after` nas
  respostas observadas; zero 429 em 6 chamadas rápidas. NIT
  FONTE-1-review FECHADO (re-escrito): **limite OBSERVADO: zero 429 em
  10 chamadas; cabeçalhos x-ratelimit ausentes nas amostras** — a frase
  anterior "limite documentado ~500/h sem key" não tinha fonte/URL
  citável e é RETIRADA (o fastf1 cacheia localmente, o que reduz a
  exposição por padrão).
- **OpenF1**: 200 sem login; sem cabeçalhos de limite nas amostras.

## 5. Log de chamadas (experiments/fonte-1/probe_log.md — APPEND-only)
10/30 chamadas (A=3+1retry, B=3, C=2, +1 manual 404 DISCLOSED — chamada
de verificação de amostra fora do script, param inválido, logada
honestamente e contada no teto). Hashes sha256 por payload registrados.

## 6. DISCLOSE-254 (pendência herdada do PROF-MONACO-1 — fechada no P0)
O "254,5 s/ep" do ANEXO_PROF_MONACO_1 §2-V3 = **1272,4 s ÷ 5 eps**
(tabela_anatomia, tempo-cascata do ALUNO na bateria). Os 3 eps do B'
original são BIT-IDÊNTICOS aos da bateria (ep1/2/3 conferidos) → a
"média dos 3 eps" daria o MESMO 254,5. O "270 s/ep" do orquestrador
não reconcilia com nenhum artefato — **NIT aberto, não-gating**.

## 7. Árvore executada (ramo convergente)
A classe (ii) é não-vazia (2 camadas LEGADAS), mas nenhuma NECESSIDADE
ativa de telemetria existe: os dados pedidos pelos (ii) são geometria
(superseded pelos mirrors) ou metadado (coberto pela Jolpica). PROBE-C
provou que a candidata gratuita (OpenF1) cobre telemetria histórica sem
login caso ela volte a ser necessária. **Recomendação FONTE-2 (SÓ
TEXTO)**: adoção drop-in do plano metadado via `fastf1.ergast` (já
aponta jolpi.ca — NENHUM upgrade necessário) e/ou REST direto; OpenF1
documentada como candidata gratuita para telemetria histórica; decisão
de dono.

## 8. Suíte
Sem mudança de código de produção → **INVARIANTE 25F/332P/3S** (nenhum
teste de probe adicionado — probes são diagnóstico, não produção; o
script de probe fica versionado em scripts/ para re-runs APPEND).
