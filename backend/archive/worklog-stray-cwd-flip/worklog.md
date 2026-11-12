
# Task ID: FONTE-1 (2026-10-22) — Jolpica drop-in PROVADO; âncora 1:14.165; OpenF1 sem-login; recomendação FONTE-2 (SÓ TEXTO)
READ-MOSTLY; prereg 27ebff9 antes dos probes; ZERO sims (teto 0);
caches fastf1 congelados INTACTOS; pools intocados; 10/30 chamadas logadas.

## Commits
02ea59b (P0/F0) → 27ebff9 (prereg) → probes v1-v3 (commitados antes do
uso; bug ErgastMultiResponse corrigido no v2 — era bug do PROBE, não da
rede; retry 1/2 do prereg logado) → fechamento.

## Vereditos (mecânicos)
P1 PASS: fastf1.ergast da 3.8.3 PINADA já fala api.jolpi.ca — provado em
execução (circuits 200/24; schedule 200/24; Monaco=round 8; lap_times
200 com paging 30/pág). P2 PASS: âncora externa OBTÍVEL — volta mais
rápida Monaco 2024 = 1:14.165 (FastestLap rank=1 via results REST;
os mínimos das laps 2:01/2:57 são ARTEFATO DE PAGING). P3 PASS: OpenF1
sem login — car_data Monaco 2024 (session 9516): 10 campos
(speed/throttle/brake/n_gear/rpm/drs…); position é endpoint SEPARADO;
2,9 MB/6,8 s por sessão×driver. Rate limit: nenhum header observado na
Jolpica; zero 429.

## Inventário F0
(i)=3 Jolpica (schedule/driver_db/Ergast já-jolpi.ca); (ii)=2 órfãos
LEGADOS (track_loader get_session+circuit_info — dado=geometria superseded
pelos mirrors; driver_db get_session R — necessidade=metadado);
(iii) mirrors/f1db intocáveis; (iv) caches 96K+935M congelados.
Telemetria de verdade: NENHUM código ativo consome.

## Discloses
DISCLOSE-254 fechado (254,5 = 1272,4/5 da tabela_anatomia; eps B'
bit-idênticos ep1/2/3; '270 s/ep' não reconcilia — NIT aberto). 1 chamada
manual 404 (param inválido) LOGADA e contada no teto (10/30). Bug de
probe v1 corrigido e logado (TypeError ErgastMultiResponse).

## Recomendação (SÓ TEXTO)
FONTE-2: adoção drop-in do plano metadado via fastf1.ergast e/ou REST
direto (SEM upgrade — a 3.8.3 já fala jolpi.ca); OpenF1 documentada
como candidata gratuita p/ telemetria histórica. Decisão de dono.
Suíte INVARIANTE 25F/332P/3S (zero código de produção).

# Task ID: PROF-REPAIR-1 (2026-10-22) — pacing pós-reentrada: PRIMÁRIA FAIL (52,47%); GAP B/C conservador; PARE
Prereg fc0a939 antes de tudo; 7/7 eps; zero rede; baseline reuso
obrigatório; aluno 45,00% canônico intocado; pools/caches intactos.

## Commits
fc0a939 (prereg) → eb09171 (patch --prof-repair default-OFF) →
cae63df/35f3baa (+2 testes; erro aritmético MEU no teste, patch
correto) → 7 eps seriais → 50ea3eb (evidência + ANEXO) → fechamento.

## Veredito (mecânico vs pins)
flag-OFF BIT-IDÊNTICO a prof_s0 (regressão obrigatória PASS).
flag-ON: fora 52,47% (−4,46pp) — PRIMÁRIA FAIL (≥45,00); SEC-1 cascata
94,4% FAIL (inalterada); SEC-2 PASS (C11 top-1, Reta 2ª); SEC-3 preso
277,2s FAIL + REGRESSÃO (+40,2s). Árvore: A não; B não como pinado
(1/3 SEC); C não (sem regressão total) → GAP entre B e C não previsto
→ CONSERVADOR: nenhum sucesso; --prof-repair RESEARCH default-OFF;
professor segue não-viável p/ rótulos; decisão (2ª rodada × abandonar)
= dono, com gap quantificado (7,47pp residual).

## Lições
(1) Árvore de 3 ramos precisa de ramo p/ "melhora parcial SEM secundárias
verdes" — o GAP exigiu resolução conservadora declarada (sem re-pin);
(2) reparo de pacing melhorou o SINTOMA (Reta sai do top-1) sem tocar a
CAUSA (cascata inalterada) — o carro sai de novo mesmo a 8-12 m/s: a
trajetória de reentrada (bearing projeção+10m) é o motor dominante
(candidato SÓ TEXTO: alvo adiante/curvatura mínima); (3) a rampa
AUMENTOU o preso (crawl mais longo nas janelas presas) — reparos de
ritmo podem piorar métricas de tempo; (4) degenerescência solo+seca
confirmada de novo (seeds 0-4 bit-idênticos).
