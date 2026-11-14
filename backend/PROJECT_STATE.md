# PROJECT_STATE.md — F1 RL Bot: estado do projeto

> **Toda sessão futura começa por: ler este arquivo e AUDITORIA_RL.md.**
> Última atualização: **REJOIN-TEL-2 (2026-10-24; corrida v3.5 concluída com exit 0, g1–g4 PASS; 302/344 reentradas >20°, Pearson com segunda saída −0,361; recomendação ao dono: arquivar hipótese angular da Etapa 2 e avançar Etapa 3, sem promoção. Ver `backend/experiments/rejoin-tel-2/EXECUCAO_REJOIN_TEL_2.md`.)**
> (anterior: **PROJ-FIX-5 (2026-10-23; freeze corrigido pré-análise `4081f06`; report-only — C3 p95 Δs=1127.55 m, C5=25.34 m; 112/112 reconciliados; eventos/volta indisponível nas fontes permitidas; zero sims/smokes, nenhuma mudança de produção; veredito do dono pendente. Ver `backend/experiments/proj-fix-1/DOSSIÊ_PROJ_GATE.md`.)**
> (anterior: **PROJ-FIX-3 (2026-10-23): PARE em g0 por erro de proveniência — P3 esperava `a3e7dd18…`, enquanto o PARE v2 commitado/disco é `e287e5bd…`; g1–g4 ainda não executados nesse ciclo. Ver `backend/experiments/proj-fix-1/PARE_PROJ_FIX_3.md`.)**
> (anterior: **LOC-XY-1 / ERRATA E-XY-3 (2026-10-23): ponteiro da linha 6 restaurado doc-only; gate 3/4 e selftests concluídos após retomada. Entradas futuras de cabeçalho/cadeia já devem conter `Ver <path>` e fechar `)`. Ver `backend/experiments/loc-xy-1/relatorio.md`.)**
> (anterior: **ERRATA E-XY-2 ratificada: o teste legado compara `split(',')[:49]` incluindo o header; kill-switch v3.3 permanece para restauração de arquivos. Gate 3 retomado terminou 21F/351P/3S e parou por `test_state_files_doc_integrity`. Ver `backend/experiments/loc-xy-1/relatorio.md`.)**
> (anterior: **FAIL-FORENSICS-1b concluído (2026-10-23): R3 `--track Monaco` passou byte a byte contra `aluno_s0.csv`; R4 Composite Monaco N=1, 43,15% fora, 12 hesitações e 45 saltos ≥30 m pelo proxy de projeção. Veredito offline das 14 entradas concluído; B3' e ANTI-D3-1 seguem FAIL; nenhuma mudança de comportamento. Suite pós-E3: 20F/349P/3S. Ver `backend/experiments/fail-forensics-2/EXECUCAO_FAIL_FORENSICS_1B.md`.)**
> (anterior: FAIL-FORENSICS-1 (2026-10-23): PARE após duas corridas Interlagos; Ver `backend/experiments/fail-forensics-1/PARE.md`.)
> Estado anterior: **GATE-RE-DERIVE-1 (2026-10-23; feat/sanidade-produto; prereg congelado 194a709): report-only — 0/10 históricos elegíveis no gate temporal de velocidade; 6 streams alternativos extraídos, 0 aprovados e 0 deltas reportados; nenhum holdout independente; zero rede, promoção ou simulação de produto; suíte serial 20F/349P/3S, mesmas 20 falhas conhecidas. Ver seção GATE-RE-DERIVE-1 e backend/experiments/gate-re-derive-1/PARE.md.**
> (anterior: PISTAS_EXPAND_1 (2026-10-23; feat/sanidade-produto; ciclo de AQUISIÇÃO — mirrors reais via OpenF1 /location método v4 FONTE-2; prereg 8afec70 + PATCH_PISTAS_EXPAND_1_A 51da2d8; ZERO sims; pool --tracks intocado; caches fastf1 intocados; 17/25 chamadas logadas APPEND): CONCLUÍDO — T0 (d5bb170) reclassificou Hungaroring/Zandvoort (c)→(b) por v1s no disco (RATIFICADO pelo PATCH_A; fail-loud codificado) e CONFIRMOU os 9 oficiais da §1 pelo f1db (sem re-pin). ACHADO MECÂNICO: o gate Δ<1% pinado REPROVOU 7/9 pistas (deltas −1,36% a −2,11%, TODOS no sentido CURTO — o v4 mede a LINHA DE CORRIDA, que corta curvas; a prova Monza −0,64% do FONTE-2 é a pista mais indulgente do calendário; o interlagos canônico é −3,45% vs oficial, ou seja, o gate é mais estrito que o acervo). CONGELADA 1: LasVegas_v2.json (sha c30a8fe636b725cd; case-exata `LasVegas`; 614 wp; −0,998% vs 6201 m) — a única OK veio do ESTICAMENTO; os 3 alvos de congelamento da primária (Montreal/Bahrain/Mexico) falharam o gate (FAILED honesto, sem re-pin pós-número). COMPARADO: Suzuka candidato 5761,6 m (−0,78%) vs v1 5534,8 (−4,69%) = razão entre as magnitudes dos erros de comprimento: 6,0× (272,2 m ÷ 45,4 m), v1 INTACTO (freeze = dono); Hungaroring/Zandvoort reprovaram antes do artefato (números no manifest). GOLDEN PASS TOTAL (canônicos 3/3 bit-idênticos; v1s 5/5; anti-substituição 5/5 — nenhum _v2 não-autorizado no path frozen). Suíte FINAL serial 20F/349P/3S = baseline REAL 20F/345P/3S + 4 t_pe1 com as 20 falhas BIT-A-BIT idênticas (ZERO novo FAIL). LIÇÕES: /tmp de tasks background é EFÊMERO (logs de medição vão ao worktree no MESMO passo); manifest exibe −1,0 (2 casas) mas o gate avaliou −0,9982%. Decisões do dono: gate × re-derivação mecânica (streams TODOS em cache = reprocessar SEM rede); Suzuka freeze (1 linha de aprovação); LasVegas pronta (adoção no pool = ciclo próprio). Ver ANEXO_PISTAS_EXPAND_1.md e seção PISTAS_EXPAND_1.)
> (anterior: PISTA-IDENT-1 (2026-10-22; feat/sanidade-produto; ciclo de ENGENHARIA; prereg 3758661; ZERO sims; zero rede; pools/caches/mirrors/schema/draw_track/--prof-repair/--variedade INTOCADOS): CONCLUÍDO — resolução de dados SEPARADA do ambiente (G1: backend/domain/track_resolution.py = resolve_track/aliases/FASTF1_*/load_track_frozen MOVIDOS de f1_env c/ re-export de compat total), FAIL-LOUD no treino/eval (G2: resolve_track allow_fallback=False default levanta TrackResolutionError c/ LISTA; o fallback silencioso Interlagos MORRE; --allow-track-fallback preserva o antigo c/ AVISO LOUD + [FALLBACK]) e MIRROR-FIRST (o padrão FONTE-2 agora no TREINO: interlagos/Monaco/Spa resolvem instantâneo/zero-rede/sha-verificado ANTES do FastF1 legado; bugs meus: case-exato do loader H-1 reincidente + gate MIRROR_OPTIONS) + IDENTIDADE verificável (G3: track_identity = requested×efetiva×fonte×sha256×wp×L; env expõe self.track_identity + warning LOUD; eval_teacher_solo imprime IDENTIDADE). GOLDEN 5/5 (CSV/mirrors bit-idênticos/fail-loud/fallback-flag/suíte). ACHADO DE PRODUTO: baseline REAL serial 26F/335P/3S (livros: 25F — ±1 flutuação); FINAL SERIAL 20F/345P/3S — 6 LEGACY CURADAS (curvature_cap/v_plan/hairpin×2/kappa/driver_db: todas eram sintomas do preset procedural 240wp no lugar da pista pedida) e ZERO novas; test_monza_retas_longas reparado (o pass anterior era INVALIDO — corria no preset Interlagos); DISCLOSE: 2 suítes concorrentes minhas causaram falso 'novo' hold_at (colisão /tmp/hold_smoke.csv) — LIÇÃO: suítes que rodam sims em /tmp compartilhado também são 'sims em paralelo'. +4 testes (test_track_resolution 4/4). Ver ANEXO_PISTA_IDENT_1.md e seção PISTA-IDENT-1)**
> (anterior: PROF-REPAIR-1 (2026-10-22; feat/sanidade-produto; PRIMEIRO ciclo que MODIFICA o professor — pacing pós-reentrada opt-in; prereg fc0a939; 7/7 eps do orçamento; zero rede; pools 70-79/76-79 VIRGENS; caches fastf1 intactos): VEREDITO — GAP ENTRE B E C NÃO PREVISTO PELA ÁRVORE → RESOLUÇÃO CONSERVADORA: nenhum sucesso reivindicado; --prof-repair fica RESEARCH default-OFF; o professor PERMANECE NÃO-VIÁVEL como fonte de rótulos; decisão (2ª rodada de reparo × abandonar o professor) VOLTA AO DONO com gap quantificado. Mecanismo R0 (arquivo:linha): rejoin race_diagnostic.py:327-364 devolve o controle ao professor INSTANTANEAMENTE na transição off→on (sem settling) e reference_controller.py:448-453 comanda o v_plan FROZEN pleno já no tick seguinte ao reentry a 8 m/s na borda = PULSO DE PACE (motor hipotético da cascata 94,6%). Patch UM FATOR: janela 5,0s pós-reentrada com rampa alvo = min(v_plan·0,93, 8+(v_plan·0,93−8)·elapsed/5) e MESMA fórmula long_cmd do professor; esterço intocado. RESULTADO: flag-OFF BIT-IDÊNTICO a prof_s0 (regressão OBRIGATÓRIA PASS); flag-ON: fora 52,47% (−4,46pp vs 56,93 baseline) MAS PRIMÁRIA FAIL (≥45,00 — aluno canônico); SEC-1 cascata 94,4% FAIL (INALTERADA — o pace NÃO é o motor dominante); SEC-2 PASS (C11 22,0% top-1, Reta 2ª 17,1%); SEC-3 preso 277,2s FAIL + REGRESSÃO (+40,2s — a rampa segura o carro MAIS tempo nas janelas presas); authority: rejoin 52,3% + prof_repair 45,6% + professor 2,0% (o carro cicla sai→volta-rampa→sai mesmo a 8-12 m/s). LEITURA (marcada): a TRAJETÓRIA de reentrada (bearing projeção+10m deposita o carro em ângulo incompatível com C11/C04) é a causa dominante — próximo candidato SÓ TEXTO: alvo de reentrada mais adiante/curvatura mínima (ângulo raso, lição M2). Árvore: A não (PRIMÁRIA FAIL); B não como pinado (1/3 SEC verde); C não (sem regressão total/abort) → GAP documentado fail-loud, sem re-pin. Suíte 25F/336P/3S. Ver ANEXO_PROF_REPAIR_1.md e seção PROF-REPAIR-1 [Rótulo de era: PRIMÁRIA FAIL 52,47%; --prof-repair RESEARCH default-OFF; decisão 2ª-rodada×abandonar = dono.])**
> (anterior: FONTE-2 (2026-10-22; feat/sanidade-produto; desenho de pista: mirrors canônicos → OpenF1 location → ERRO LOUD; prereg 9ba3f8c; ZERO sims — teto 0; env/loader/canônico/schema/requirements INTOCADOS; pools intocados; caches fastf1 intactos; rede 5/10 chamadas logadas APPEND): P1 PASS — as 3 canônicas desenham DOS MIRRORS instantâneo/zero-rede com GOLDEN EXATO (Interlagos 4160,4 m/1131 wp; Monaco 3335,2 m/834 wp + hairpin C06 κ0,1602 = PROF-MONACO-1; Spa 7003,2 vs 7004 −0,01%); DISCLOSE preset×mirror Interlagos: preset legado 240 wp/4309,0 m (era telemetria, +3,6%, 4,7× mais grosso) — o desenho agora usa a MESMA geometria do simulador. P2 PASS — OpenF1 /location entrega contorno de Monza 2024 (session 9590 d44): 575 wp/5756 m vs 5793 oficiais (−0,64%); ACHADO DE UNIDADE: x/y da /location são DECÍMETROS (bounding box 12.568×21.684 ≡ Monza real 1.257×2.168 m, razão exata 10×); 3 métodos mortos documentados (salto>300m; origem=garagem c/ 6.599 amostras paradas; cadeia NN 66 km); método final v4: remove-parado → célula-60m-mais-visitada → janelas-entre-visitas=volta → mediana → re-amostra 10 m; location é PESADO (3,9 MB/7-9,5 s por sessão×driver — cache local). P4 PASS — preset silencioso MORTO: --track inexistente = SystemExit 3 + lista (mirrors + OpenF1 + --legacy-preset c/ AVISO LOUD 'desenhará Interlagos'). ACHADO-P0: o draw_track NUNCA usou mirrors (draw_track.py:23-24 → resolve_track → FastF1 morto → preset; load_track_frozen no mesmo f1_env.py:1292 sem ser chamado). PATCH: CSV → MIRROR → OpenF1 → ERRO LOUD. +2 testes (círculo sintético multi-volta c/ garagem: filtro não distorce; fail-loud exit 3). PNGs: 3 mirrors + monza_openf1. Suíte esperada 25F/334P/3S. Ver ANEXO_FONTE_2.md e seção FONTE-2 [Rótulo de era: P1-P4 provados; ACHADO unidade decímetros; preset morto.])**
> (anterior: FONTE-1 (2026-10-22; feat/sanidade-produto; migração da aquisição externa plano pago→gratuito; READ-MOSTLY; prereg 27ebff9; ZERO sims — teto 0 cumprido; caches fastf1 96K+935M INTACTOS; pools 70-79/76-79 INTOCADOS): P1 PASS — a JOLPICA É DROP-IN NA VERSÃO 3.8.3 PINADA (fastf1.ergast BASE_URL=api.jolpi.ca confirmado no F0 e PROVADO em execução: circuits 2024 200/24, schedule 200/24 com Monaco=round 8, lap_times 200 com paging 30/pág); P2 PASS — âncora externa OBTÍVEL: volta mais rápida Monaco 2024 = 1:14.165 (FastestLap rank=1 via results; os 2:01/2:57 das laps eram ARTEFATO DE PAGING, não a âncora); P3 PASS — OpenF1 cobre telemetria histórica SEM LOGIN (session 9516 Monaco 2024; car_data 17.485 amostras; campos speed/throttle/brake/gear/rpm/drs; position é endpoint SEPARADO /position; latência 6,8s/2,9MB). F0: (i)=3 Jolpica, (ii)=2 órfãos em camadas LEGADAS (track_loader get_session+circuit_info — dado=geometria JÁ superseded pelos mirrors F1DB; driver_db get_session R — necessidade=metadado coberto pela Jolpica), (iii) mirrors/f1db intocáveis, (iv) caches congelados PROIBIDO limpar — telemetria de verdade NÃO é consumida por código ativo. Orçamento 10/30 chamadas logadas APPEND-only (A=3+1retry c/ bug-de-probe corrigido v2; B=3 REST direto SEM fastf1; C=2; +1 manual 404 DISCLOSED contada no teto). DISCLOSE-254 fechado: 254,5=1272,4/5 (tabela_anatomia); eps do B' bit-idênticos conferidos; '270 s/ep' não reconcilia — NIT aberto não-gating. RECOMENDAÇÃO FONTE-2 (SÓ TEXTO): adoção drop-in do plano metadado via fastf1.ergast e/ou REST direto (SEM upgrade — a 3.8.3 já fala jolpi.ca); OpenF1 documentada como candidata gratuita p/ telemetria histórica; decisão de dono. Suíte INVARIANTE 25F/332P/3S (zero código de produção). Ver ANEXO_FONTE_1.md e seção FONTE-1 [Rótulo de era: recomendação FONTE-2 emitida ao orquestrador; P1/P2/P3 da FONTE-1 provados.])**
> (anterior: PROF-MONACO-1 (2026-10-22; feat/sanidade-produto; diagnóstico READ-MOSTLY do professor-solo em Monaco_v2; prereg 2aa018c; NENHUM reparo; zero treino; pools 70-79/76-79 INTOCADOS): PARE IMEDIATO PELA FALSIDICAÇÃO-Q4 — o ALUNO (v10-cego, fora 45,00%) é MELHOR que o PROFESSOR (56,93%) na pista-gargalo (−11,9 pp, determinístico): a premissa 'o fora do aluno é herdado dos rótulos do professor' está FALSIFICADA — nem 'herdado' nem 'degradado' sobrevivem; o gargalo da Meta A é o PRÓPRIO professor. Q1 FALSIDICADA (report-only): RETA no top-1 do professor (50 excursões 24,4%; hairpin C06 só 7,3%) → lead REJOIN-CASCATA; Q3 ANATOMIA: 94,6% (prof) / 92,4% (aluno) das excursões são REJOIN-CASCATA ≤10 s pós-fim (churn de reentrada; 0 wanderers; 0 spins relevantes) — o fora é auto-infligido no RETORNO, não geometria do hairpin. VERIFICAÇÕES: paridades bit-idênticas; V1 DEGENERESCÊNCIA — TODOS os seeds 0-4 bit-idênticos por braço (solo+seca+sem variance = seed SEM canal: bateria = 1 realização + 4 réplicas; ICs cluster degenerados; lição: bateria multi-seed solo precisa de canal de variância); V2/V2b bateria ≡ artefatos ADOÇÃO-H-2 BIT-IDÊNTICOS (metaA era janela 600 s — '2 voltas' = completas no cap; leitura de era corrigida); ERRATA R6 (era ADOÇÃO-H-2): preso herdado '118 s' era 1185 ticks÷10 — CANÔNICO 237,0 s (R3 opera sobre LINHAS 5 Hz ×0,2 s; classe da NIT de exibição temporal, 4º caso, agora erro 2×). Erratas R5-a (C07 IQR-B canônico 23,6) e R5-b (Reta-B solo 11/20=55,0%) consolidadas no P0 com proveniência R1 VAZIA (ratificação SAIDAS-1 ÍNTEGRA); NIT-2: re-execução do veredito regenera as 6 tabelas BYTE-IDÊNTICAS (golden permanente); NIT-3: C10='Senna S (T1/T2)' s∈[2748,2852] κ0,0311 CONFIRMA por geometria (ressalva de margem ±30 m: 96/114 m da zona F0). Instrumento: saidas_verdict --track (golden Interlagos provado; bateria multi-ep com Σ solo==total fail-loud; +6 testes). Orçamento: 12/14 sims (re-smoke poupado); A×B ABERTA e CONGELADA. Proposta de reparo do professor (SÓ TEXTO): mirar re-entry/pacing pós-excursão, não a geometria — ciclo próprio com prereg, autorização = dono. Ver ANEXO_PROF_MONACO_1.md e seção PROF-MONACO-1 [Rótulo de era: veredito mecânico do PROF-MONACO-1 emitido ao orquestrador; erratas R5-a/R5-b/R6 consolidadas.])**
> (anterior: ERRATA-SAIDAS-1 (2026-10-21; feat/sanidade-produto; ciclo de erratas R1–R4 ratificado pelo orquestrador): VEREDITO MECÂNICO CONCLUÍDO — RECONCILIAÇÃO COM ÂNCORAS F4v15 DENTRO DA TOLERÂNCIA PRÉ-REGISTRADA (A fora 22,1167% vs 22,1% Δ=0,0167pp; B 25,2133% vs 25,2% Δ=0,0133pp; 180 e 219 eventos; dur med 4,2s). Perguntas respondidas: Q1 PROPORÇÃO SOLO = 46,7% no v10-cego [IC 95%: 39,4%-53,9%] vs 83,6% no composite [IC 95%: 78,5%-88,1%] (quase o dobro; confirmação estatística inequívoca da queixa do dono); Q2 TOP CURVAS = 4 curvas concentram 91,7% (A) e 78,1% (B) de todos os eventos de saída (T4/T5 Descida do Lago 23-27%, T10 Bico de Pato 17-22%, T11 Mergulho 19-21%, T12 Junção 19-22%); Q3 MODOS = 59-65% LINHA-RETA / subesterço tangencial, 35-41% SLIDE (deriva >=10° pontual), 0,0% SPIN (zero piruetas descontroladas); Q4 VELOCIDADE = IQR <=3,7 km/h em C01/C06 (repetição determinística), C07 largo 22,0-23,6 km/h (heterogeneidade 31-72 km/h insumo do professor), C08 intermediário 3,2-6,7 km/h (todas com v_med 35-60 km/h plausíveis de hairpin). Erratas R1-R4 incorporadas: R1 pin collision sanada (C09-A solo=0 nos dados/código; o 87 foi artefato de display; soma das curvas 25+22+21+16+0=84 == total Q1 84 exato; B fecha 183 exato); R2 IQR segregado; R3 % de eventos corrigido; R4 rotulagem canônica ajustada. Decisão A×B ABERTA e CONGELADA (zero promoção/flip/retreino). Orçamento: ZERO corridas (re-análise de artefatos existentes; pools 76-79 virgens). Ver seção SAIDAS-1 e ANEXO_SAIDAS_1_ERRATAS.md [Rótulo de era: veredito ratificado na SAIDAS-1-review; execução/erratas ratificadas na ERRATA-SAIDAS-1-review.])**
> (anterior: VARIEDADE-1 (2026-10-21): camada de variedade opt-in; determinismo sobreviveu; D2==D1 byte-a-byte; 76-79 virgens. Ver seção VARIEDADE-1.)
> (anterior: SANIDADE-1b (2026-10-20): M3-v2 (tetos) FAIL ARQUIVADO com leads; M2 rejoin-perceptive atribuição LIMPA solo (cc 516 −31%, hesit 6, fora 28,0 ≤ 29,9 — escala não dispara); PIN COLLISION divulgada. Ver seção SANIDADE-1b.)
> (anterior: SANIDADE-0 (2026-10-20; feat/sanidade-produto; ciclo de DEFEITOS DO PRODUTO): M1/M3 v1 FAIL saem do bundle; M2 rejoin-perceptive PASS 4/4 único no --modo espectador; proteções duplas bit-idênticas; D0 coluna lat=MÓDULO (slat=obs4×hw patrimônio). Ver seção SANIDADE-0.)
> (anterior: ANTI-D3-1 (2026-10-21; ataque de mecanismo-ÚNICO ao D3, pinnado pelo dono antes da decisão A×B): FAIL MECÂNICO — PARE; D3 DECLARADO ESTRUTURAL à camada. Progress-guard fade gate→base (prereg 57a9342; N=5 ticks/F=5/Δcum<0,5m; tick lógico 10 Hz ⇒ EFETIVO 0,5s @ v<5 m/s) no caminho composite (7dde1d8); PRIMÁRIO hesit 12 ≤ 3 FAIL (sem guard 13); não-reg 5/5 PASS mas cc 752→1520 (+102%) e pós-largada 292→846: o guard DEGRADA o valor primário; 9/10 disparos NA LARGADA (probe 1ª-divergência); D3 como custo permanente; A×B volta ao dono. Ver seção ANTI-D3-1.)
> (anterior: FASE 4 v15 (2026-10-21; wiring): grupo composite no --mixed (limitação 2 resolvida; 3 controllers; PROTEÇÃO v10-cego bit-idêntica ao fixture); B3' FAIL MECÂNICO sob regime canônico — hesit 13 vs ≤3 (R10 D3 reproduzido fora de sessão) + mistas pós-largada 193/242 > ≤2 (absoluto pré-canônico NÃO re-ancorado — gap de pin divulgado); PASSA: cc 752 vs 3674 (4,9× menos), 10/10, 0 par, fora 25,2 ≤ 29,9, rol 140 ≤ 146; mistas +33s vs ctrl-embaralhado; HOLD-AT 9/10 com 4 paradas (pilha multi-composite = limitação confirmada). Promoção = dono. Ver seção FASE 4 v15.)
> (anterior:  Última atualização: **ADOÇÃO-H-2 (2026-10-20; dono aprovou: AMBOS): mirrors F1DB ADOTADOS como canônico — Monaco_v2.json (sha 67ca11dc211c8c78) e Spa_v2.json (sha 4b05f2c3bbc625fc) via git mv + prioridade {key}_v2 EXISTENTE do loader (loader INTOCADO); v1s → archive/tracks_frozen_v1 (NUNCA deletar; Monaco_v1 07e7ef4dd6af4517 ABORTA no runner atual; Spa_v1 f83365bf26d0b1b1 truncada). PROFESSOR-FIRST 3/3 em ambos (6 eps bit-idênticos, ≥2 voltas pelo critério pinado); CONTROLES: professor-solo-frozen off% é BASELINE do instrumento (interlagos canônico 24,3%; os 0,36% históricos eram 10-carros/live); mirrors MAIS dirigíveis que os v1s (Monaco v1 aborta; Spa 45,4% vs 32%). B' SOB MIRROR 9/9 por completude (Monaco 3/3 — era 0/3 — com ressalva fora 45%; Spa 3/3 canária COMPLETA fora 20,8%); Meta A Monaco 5/5 professor. t-inércia flipado + t-novo archive (verdes); suite 25F/302P/3S [desvio do declarado 304P/2S justificado: os 2 testes novos SUBSTITUÍRAM os 2 antigos; composite_parity:45 (artefato Monaco_v1) virou skip condicional]. Zero corridas/pool/re-pin; 70-79 intactos. Ver seção ADOÇÃO-H-2.)**
> (anterior: FASE H-1 (2026-10-20): G4 morto como gate por calibração em controles (0/5 in-band em toda a grade; detector não reproduz turns oficiais); mirrors congelados via G1/G2/G3/G5. Ver seção FASE H-1.)
> (anterior: FASE H-0 (2026-10-19; geometria): mirrors GATE FAIL só no G4 (calibração); nada congelado; H3 detector validado (Monaco_v1 45 riscos artifact; Suzuka_v1 0,04 m crossover real). Ver seção FASE H-0.)
> (anterior: CICLO LARGADA — FECHADO (2026-10-19; teto documentado; DOSSIE_LARGADA.md; RATIFICADO pela LARGADA-2-review/ANEXO B 8bd728c). Ver DOSSIE_LARGADA.md.)
> (anterior: CICLO LARGADA F1b (out/19): launch-stagger GATE FAIL; PRIMÁRIO-1 PASS esmagador (densidade validada); atrator estrutural. Ver CICLO LARGADA — FASE 1b.)
> (anterior: CICLO LARGADA F1a (out/19): launch-cap FAIL por falsificação limpa (velocidade refutada; E1 keying medido). Ver CICLO LARGADA — FASE 1a.)
> (anterior: CICLO ALAVANCA — REVALIDAÇÃO (out/19): C' 8/8 seco; D adverso FAIL → rejoin-gap OPT-IN. Ver CICLO ALAVANCA — REVALIDAÇÃO.)
> (anterior: CICLO ALAVANCA — REPARO + RE-VALIDAÇÃO (out/18): instrumento REPARADO (ead15a7, amenda ANTES de runs) e verificado — smoke B 3/3 PASS (largada bit-idêntica; telemetria em fase, keying por carro; divergência == 1º hold). RE-GATE seco seeds 30-39: **FAIL mecânico** por GUARD-P/GUARD-W nas 2 seeds DAMP (s30 par 7/wand 4; s37 4/6 — o pool NÃO era todo-seco: 5/10 com transições; paradas em úmido são fenômeno do CLIMA, presente no cego histórico) e fb s34=16>10 (fallback agora VISÍVEL: 6-16×/run). PASS-P 0,141 ✓ PASS-R 0,220 ✓ — mecanismo de taxa REAL (−56%, perto do teto teórico 0,149); EXPECTATION RESET CONFIRMADO (fora 17-26% — efeito-largada sumiu). PARE em C; D/E não executados; alavanca rejoin-only = research-grade; dossiê LARGADA = candidato prioritário. Ver CICLO ALAVANCA — REPARO.)
> (anterior: CICLO ALAVANCA — SESSÃO ADVERSA: PARE POR INSTRUMENTO no 0-c (VAZAMENTO): o gap-check engaja SEM estado de rejoin — segura na LARGADA (tick 0, 8/10 carros do grid, th 0,928→0,35 crawl; 1ª excursão 4,2 s→32,6 s) — e a telemetria rejoin_gap_hold está FORA DE FASE com as ações (SAI crawl@0 com hold=0). Gate adverso {2,8,9} NÃO rodou; SEM re-pin/re-run. ERRATA do gate seco: medição do FLAG válida (base fresco = histórico bit-idêntico 0/30000), mas o mecanismo é um híbrido launch-pacing+rejoin NÃO-especificado — atribuição confundida. Ver CICLO ALAVANCA — SESSÃO ADVERSA.)
> (anterior: FASE R13-FECHAMENTO (housekeeping, zero runs): erratas E1-E5 auditáveis (manchete corrigida: 1,5-3,5× menos contatos; contato×carro-fora 28-44%; adversos 0-9 = {2,8,9} confirmado n=3 — vereditos inalterados); CSV v3.3 ADITIVO commitado com bit-identidade PASS (res_16d por tick p/ rota 2; sha universal do residual); DECLARAÇÃO FINAL DE PRODUTO colada como seção canônica: v10-cego = race default; composite research-grade com vantagem de segurança consistente; alavanca = percepção no retorno. Ver FASE R13-FECHAMENTO.)
> (anterior: FASE R3 (fix do absorvedor + gate multi-realização): branch hotfix/instrument-repair. ABSORVEDOR MORTO — rejoin por BEARING: excursão de 40 m recupera em 15,7 s (vs 500+s/never em R2); teste sintético PASS; contatos/pós-largada/voltas melhoraram em TODAS as seeds (pós-largada ≤100 pela primeira vez). GATE MULTI-REALIZAÇÃO VERMELHO por OUTRA causa: pilotagem — 96% das 253 excursões de s0 começam SEM contato (v med 14 m/s, todos os setores): o composite sai da pista 2-3×/carro/volta em tráfego denso; fora-pilotagem 6% > 1,5%, rolante 190 s > 115. Promoção PERMANECE SUSPENSA. — Ver seção FASE R3.)**

## Metas

| Meta | Critério | Status | Melhor resultado |
|---|---|---|---|
| **A** Professor ≥95% | todas as pistas, grip 0,75–1,0 | **✓ 100%** | professor v2: 40/40 nas 8 pistas [SOB MIRROR (ADOÇÃO-H-2): Monaco_v2 5/5 eps × 2 voltas — 211,9 s/volta, fora 56,9% (baseline do instrumento professor-solo-frozen; ver seção ADOÇÃO-H-2)] |
| **B** Aluno ≥9/10 treino | cada pista de treino | **✓ 100%** | v10: 39/39 nas 13 pistas |
| **B'** Aluno ≥7/10 teste | Monaco, Suzuka, Spa (zero-shot) | **✘ 6/9 [era v1]** | Suzuka 3/3 ✓, Spa 3/3 ✓ [era v1: pista TRUNCADA], Monaco 0/3 [era v1: pista que hoje ABORTA no runner] — **SOB MIRROR (ADOÇÃO-H-2, canária runner solo 600s): 9/9 por completude** — Monaco_v2 3/3 eps × ≥2 voltas (RESSALVA: fora 45%, 34 excursões, preso acumulado 118 s, wanderer 0), Spa_v2 3/3 × 3 voltas (fora 20,8% ≤ 25% — canária COMPLETA), Suzuka_v1 3/3 (inalterada) |
| **C** Tempo ≤91,2s (−20%) | Interlagos raw eval | **✘ 109s** | teto DAgger: 108s; PPO: **4× falhou** (v13 no-respawn: 2/3 a 125s) |
| **D** Corrida 10 carros | zero paradas ≥3s, 10/10, fora ≤4,6% | **✓ 100%** | v10: 1 hesitação, 2s parado, 0,8% fora |
| D-v15 (corrida, gov vplan) | idem + rolante | ✓ 103,4s | zero hesitações, fora 0,0%, contatos 1576 (nota: 103,4s é instrumento CORRIDA compostos rolante — NÃO comparável a 109s eval MEDIUM grip-realista nem a 107,9s professor-corrida) |

## Mapa de checkpoints

| Checkpoint | Tipo | Uso | Status |
|---|---|---|---|
| **v14b_traffic/dagger_actor_best_s0_n0** | DAgger pool-13, estágio A (n=0) | base solo em obs 60d (traffic-blind) | ✓ **51 eps: 48/51 = paridade v10**; canárias 3/3; Spa/Suzuka/Zandvoort 3/3 |
| v14b_traffic/dagger_actor_best_s1_n4 | DAgger pool-13, estágio B (n=4, iter 3) | REPROVADO no gate | ✗ Suzuka 2/3 (obrigatório 3/3); canárias 3/3 VERDES; G2 n=4 3/3 (10 cont/lap) — near-miss, FASE 6 |
| **v14_traffic/dagger_actor_best_s2_n8** | DAgger tráfego iter 8 (n=8) | profile **traffic** (eval c/ fantasmas) | ⚠ gates solo/traffic OK, mas **corrida all-v14 FALHOU** (1691 contatos, 152s) e **39/51 solo** (esquecimento κ extremo) — NÃO usar all-neural |
| v14_traffic/dagger_actor_best_s1_n4 | DAgger tráfego iter 3 (n=4) | densidade média | ⚠ gate B ✓; solo: só Silverstone perdida (menos esquecido que iter8) |
| v14_traffic/dagger_actor_best_s0_n0 | DAgger tráfego iter 1 (n=0) | regressão zero | ✓ 3/3 Silverstone/Montreal/107 (solo intacto; traffic-blind) |
| v14_traffic/init_from_v10 | transferência v10→v14 (60d) | ponto de partida FASE 3 | ✓ paridade 1e-6 com v10 (tests/test_v14_transfer.py) |
| v14_traffic/dagger_actor_iter10 | β=0, fim do currículo | REJEITADO pelo gate | ✗ Suzuka 0/3 (ruído do aluno dominou o dataset; best-por-VAL é o correto) |
| **v10_dagger/dagger_actor_best** | DAgger sf=0,80 | RACE SETUP v13 (sem tráfego) | ✓ 48/51 94%, 109s, Meta D ✓ |
| v15_residual/residual_best (r2) | Residual gated 16d (FASE 3 r2) | **COMPOSITE = braço A** (research-grade; gate R10: mantido, ver R13) | contatos 3-4× menores que v10-cego; fora 29-54% |
| v15_residual/residual_weave_r12b | BC janelas weave/slide 16d | **RESEARCH-NEGATIVO — ENCERRADO (R12-PILOTO)**: piloto VERMELHO (fora +6,6pp, cc +114% no s0); autópsia: skew 12d (treino zeros/serve vivos), mudança de estilo nos ticks g>0; valor: hesit −54% s0, pós-60s −64 s9 | NÃO deploya; rotas 2/3 no backlog com pré-condições |
| **v11b_pace90/dagger_actor_best** | DAgger sf=0,90 | **QUALI SETUP** (máx pace) | ✓ ~47/51, 108s, Suzuka 2/3 |
| v11_pace/dagger_actor_best | DAgger sf=0,95 | DESCARTADO | ✗ 36/51 71% (regressão) |
| v12_pace_ppo/multi_context_rl_actor_best | PPO residual (respawn) | DESCARTADO | ✗ 0/3 (lap% 6.5% fabricado) |
| v13_ppo_norespawn/multi_context_rl_actor_best | PPO no-respawn | DESCARTADO | ✗ 2/3 a 125s (degradou de 3/3 a 108s) |
| v9_dagger/dagger_actor_iter10 | DAgger 4 pistas | SUPERADO pelo v10 | 18/24 75% |

### Protocolos de inferência testados (TESTE 1, Meta C final)

| Protocolo | v10 | v11b | v12 |
|---|---|---|---|
| tanh(mu) — atual | 3/3 109s | 3/3 108s | **0/3** |
| sigma=0,05 | — | — | **0/3** |
| sigma=0,10 | 3/3 ✓ | 3/3 ✓ | **0/3** |
| sigma=0,20 | — | — | **0/3** |

**Veredicto**: o v12 falhou por ARQUITETURA (PPO degradou a política de 3/3 para 0/3), não por modo de inferência. Greedy-V descartado (não aplicável).

**Nota de inferência**: v10 e v11b mantêm 3/3 com σ=0.10 (robustez a ruído confirmada). v13: best 2/3 a 125s, final 1/3 a 117s — TETO CONFIRMADO sem ressalvas (PASSO 0 da Fase v14).

**PASSO 0 (fechamento hermético)**: NENHUM checkpoint do v13 é 3/3 com <108s. O gradiente PPO degrada desde a primeira iteração e nunca recupera. A lição: "stop rule mais cedo" não se aplica — não há janela de ganho.

## FASE 1 v14 — camada de tráfego + GATE all-professor (✓ VERDE)

**Implementação (PASSO 1)**: car-following + offset lateral no ReferenceController
(`reference_controller.py`), agora APLICADO ao ponto de perseguição (na FASE 1
original o `_lat_offset` era computado mas nunca usado — estado morto, corrigido).
Métrica de tráfego: **dist_s assinada ao longo da pista** (`signed_dist_s`,
positiva = à frente; wrap em ±L/2 — carro 5 m atrás dá -5, não +L-5). Ranking
dos 3 mais próximos usa |dist_s|; o sinal vive no flag ahead. Modo professor no
race runner: `--controller professor` (`race_diagnostic.py`) — 10 ReferenceControllers
simultâneos, cada um com os outros 9 como tráfego, v_plan ÚNICO compartilhado.
**Autoridade: professor → rejoin → recovery → blocked. SEM governor** (o v_plan
já planeja a frenagem; governor = frenagem dupla; ele fica só no modo neural).
Suite: **211/211** (152 base + 59 v14: tráfego, env-fantasma, corredor, transferência, race-60d/profiles, slot-swap, mixed-runner, hold-at).

**GATE (PASSO 2) — corrida 600 s, 10 professores, Interlagos, headless, 2 seeds**:
seeds 0 e 1 produziram métricas IDÊNTICAS (sim determinística — a repetição
confirma ausência de não-determinismo de contatos).

| métrica | meta | resultado | veredicto |
|---|---|---|---|
| carros com ≥1 volta | ≥9/10 | **10/10** (5 voltas cada) | ✓ |
| contatos carro-carro (amostras 5 Hz) | <400 | **258** (baseline aluno-cego: 1333) | ✓ −81% |
| paradas ≥3 s | 0 | **0** | ✓ |
| ultrapassagens líquidas (histerese 10 m) | documentar | **1** (na largada) | FILA: sem ultrapassagem após a largada |
| % tempo em follow (cap+close) | documentar | **0-15%** por carro (VER 0%; colado ≤2,4%) | ✓ não é fila permanente |
| tempo mediano de volta COM tráfego | baseline FASE 4 | **107,9 s** (excl. volta 1; 108,2 s todas; solo ~107 s) | custo do tráfego ≈ +1 s |

**Comportamento exibido**: o professor forma FILA APÓS A LARGADA — não ultrapassa
(pace idêntico v_plan → sem diferencial de velocidade), mas a fila é ESPARS: os
contatos ficam confinados à largada (t=1,2-47,8 s; pares de fileira LEC-NOR 57,
HAM-RUS 25, PER-SAI 24, ALO-GAS 11, PIA-RUS 9), o campo se espalha (gap médio
~430 m >> D_AHEAD=60) e os 552 s restantes têm ZERO contatos. **Teto do v14
confirmado: evita colisões, sem ultrapassagem deliberada.** Os contatos de
largada vêm da camada de offset (carro "à frente" na coluna oposta manda o
follower cruzar a pista) — aceitos dentro da meta; se a FASE 4 pedir largada
limpa, o knob é a condição de disparo do offset (só deslocar quando o líder
está próximo do MEU lateral), NUNCA treinado às cegas.

## FASE 2 v14 — obs 'traffic' (46d) + fantasmas no env (✓ implementada)

1. **obs_mode='traffic'** = edge 34d + 12d (`f1_env.py`): 3 carros mais próximos
   por |dist_s|, 4 features por carro nesta ordem:
   `[|dist_s|/100, (v_outro-v_ego)/OBS_SPEED, lat_outro/half_width, ahead(1|0)]`;
   zeros se menos de 3 visíveis; a obs NUNCA contém o próprio carro.
   **Ator v14 = 60 entradas** (46 tel + 2 ctx + 8 emb_track + 4 emb_compound).
   Layout documentado em `N_TRAFFIC_FEAT` (f1_env.py) + validação de shape com
   ValueError explícito.
2. **Fantasmas**: `n_traffic` (0-9) no construtor do env; carros FÍSICOS
   completos dirigidos pelo professor de TRÁFEGO (FASE 1, o do gate — cada
   fantasma vê aluno + outros fantasmas via `env.traffic_for(id)`); **grip
   nominal 1.0**; grid estilo F1 à FRENTE do aluno (aluno=P10, fileiras 9 m,
   colunas ±1,9 m) reposicionado a CADA reset; **NÃO geram eventos de volta**
   (`engine._no_lap_drivers` — sem degradar pneu, sem avançar clima) e **NÃO
   contam no lap%** (o check do ego usa só `states[ego].lap`).
3. **allow_respawn=False confirmado** no treino (train_dagger.py:179 — lição
   v13 verificada; default do script já era o correto).
4. Testes (`test_traffic_env.py`, 14): obs finita com 0/1/9 fantasmas; slots
   de tráfego corretos (0,09/0,18/0,27 no grid); layout estável entre resets;
   `traffic_for` exclui o ego; fantasmas andam (>5 m em 3 s) e ficam lap=0;
   engine ignora `_no_lap_drivers` no default; validação de n_traffic/obs_mode.

## FASE 3 v14 — DAgger de tráfego (✓ CONCLUÍDA; ator v14 de 60 entradas treinado)

### PASSO 0 — baseline pinado + professor limpo na largada
- **Professor SOLO (metodologia do gate, grip real, VER/SOFT, 3 eps idênticos —
  determinístico)**: volta de LARGADA parada **110,6s**; voltas ROLANTES
  **107,5s** (mediana; `eval_teacher_solo.py`). **Custo real do tráfego =
  gate 107,9 − solo 107,5 = +0,4s.** A inconsistência anterior (107,9 vs
  "112s") era UNIDADE de volta: o gate mede voltas ROLANTES; o 112s histórico
  era volta de LARGADA parada no env (111,6-114,6s com composto MEDIUM).
- **Corredor do offset** (`reference_controller.py`, LAT_CORRIDOR_M=3,5): o
  offset só dispara quando o líder está no MEU corredor lateral
  (|lat_outro − lat_ego| < 3,5 m). Re-gate: contatos **258 → 240**, e o
  MECANISMO mudou: cruzamentos LATERAIS extintos (0 pares laterais); os 240
  restantes são nose-a-cauda na largada (PER-SAI 73 amostras: compostos
  HARD vs MEDIUM aceleram diferente em gap de 9 m — rubbing físico que NÃO
  contamina rótulos). Nada regrediu (10/10, 0 paradas, mediana 107,8 s).
  **Professor APROVADO para rotular** (lição Monaco respeitada).

### PASSO 1 — transferência v10→v14 (NÃO BC-do-zero)
- `transfer_v10_v14.py`: remap de rows da 1ª Dense por LINHA na ordem do
  concat [tel, ctx, emb_trk, emb_cmp]: rows 0-33 ← edge v10; **rows 34-45 ←
  ZEROS** (a rede começa ignorando tráfego); rows 46-47 ← ctx; rows 48-59 ←
  embeddings. Bias e profundas: cópia direta.
- **Teste de paridade (obrigatório, 7/7 em tests/test_v14_transfer.py)**:
  v14 com tráfego zerado == v10 (atol 1e-6) em inputs aleatórios E na obs
  real do env; + invariância inicial ao tráfego; + **congelamento matemático:
  com inputs de tráfego zero o gradiente nos rows 34-45 é nulo** (Adam não os
  move — prova por teste com BC fit). Checkpoint: `v14_traffic/init_from_v10.keras`.

### PASSO 2 — DAgger v14 com currículo (train_dagger.py reescrito)
- `--obs-mode traffic`; `--traffic-stages "0:2,4:5,8:3"`; professor rotula
  com `teacher.action(traffic=env.traffic_for(env.driver_id))` (mesma percepção
  da obs); **train_bc com WARM START** (senão os rows de tráfego nasceriam
  aleatórios e a herança v10 se perderia a cada iter); β 1.0→0.0 global;
  2 eps/pista/iter; 50 epochs; pool interlagos/Monza/Hungaroring/Mexico/
  procedural:301; VAL Zandvoort com o n_traffic do estágio;
  allow_respawn=False impresso no log do 1º episódio (lição v13 ✓).
- Dataset final: 121.351 estados, 10 iters, ~2h (log: v14_traffic/train.log).

### PASSO 3 — gates por estágio (determinístico, grip real, sem respawn)
| gate | resultado | veredicto |
|---|---|---|
| **A** (n=0, iter 1): sem tráfego | Interlagos 3/3 **108,1s** + Suzuka 3/3 **132,3s** | ✓ REGRESSÃO ZERO (≈ v10 109s) |
| **B** (n=4, iter 3): sem + com | Interlagos 3/3 **106,9s**; Suzuka 3/3 132,4s; c/ tráfego 3/3 **123,4s** (professor: 123,9s), **0 contatos/lap** | ✓ aluno 0,5s mais rápido que o professor |
| **C** (n=8, best iter 8): sem + com | Interlagos 3/3 109,9s; **Suzuka 3/3 136,3s**; c/ tráfego n=8 3/3 **134,0s** (professor: 134,1s), **0 contatos/lap** | ✓ (gate formal falhou só no ATOR da iter 10: Suzuka 0/3 — abaixo) |

**Decisão "para no último checkpoint bom"**: o gate do estágio C correu sobre
o ATOR FINAL (iter 10, β=0) e falhou em Suzuka 0/3. Medido o BEST do estágio
(iter 8, `gate_checkpoint.py`): **PASSA em tudo** → o último checkpoint bom
é **v14_traffic/dagger_actor_best_s2_n8.keras** (não foi preciso voltar ao
estágio B). Lição registrada: o gate deve ser aplicado ao best-por-VAL do
estágio, não ao último ator (β→0 degrada: dados do aluno com ruído 0,15
dominam o dataset; iters 9-10: VAL 1/3 e 3/3 com val_loss subindo).

**Professor-com-tráfego (mesmo instrumento do G2, contatos por volta)**:
n=4: 3/3, 123,9s, 0 contatos/lap | n=8: 3/3, 134,1s, 0 contatos/lap.
Zero contatos porque no ENV fantasmas têm composto idêntico (MEDIUM) →
aceleração idêntica → gaps estáveis (na CORRIDA os compostos variam → 240).

### FASE 4 (2026-10-13, mesma sessão) — VALIDAÇÃO COMPLETA: veredicto NEGATIVO p/ corrida all-v14

**PASSO 1 (race runner 60d) ✓**: features de tráfego no NeuralRaceController
via a FÓRMULA ÚNICA `compute_traffic_features` do f1_env (nada reimplementado);
NPZ re-export + paridade NumPy↔Keras sobre **1000+ obs reais** (n=8, atol 2e-5 —
contrato: o motor NumPy devolve tanh(mean), o Keras devolve a média linear);
validação de shape com erro explícito nos 3 modos. `--obs-mode traffic` nos
3 runners. Suite **211/211**.

**PASSO 2 (51 eps SEM tráfego) ✗ REGRESSÃO**: v14 = **39/51** (v10: 48/51).
- ✓ Interlagos 3/3 109,9s | Monza 3/3 127,6s | Hungaroring 3/3 122,9s |
  Bahrain 3/3 | Mexico 3/3 | procedurais 101/103/201/203/301 3/3 | **Zandvoort 3/3** |
  **Suzuka 3/3 136,3s** (ressalva: foi gate em A/B/C) | **Spa 3/3 132,2s —
  zero-shot LIMPO, primeira medição** | Monaco 0/3 (= v10, aceitável).
- ✗ **Silverstone 0/3, Montreal 0/3, procedural:107 0/3** — modo de falha:
  "sem progresso" — freia até 0,3-1,0 m/s e trava no κ extremo (obs κ@10m
  = −0,120, κ@20m = −0,132; Silverstone s≈1660, Montreal s≈2345).
- **CAUSA (medida)**: esquecimento PROGRESSIVO do currículo — iter1 3/3 em
  todas; iter3 perde Silverstone; iter8 perde Montreal+107. O fine-tune no
  pool de 5 pistas (κ máx ~0,10-0,11) sobrescreveu a pilotagem de curvatura
  extrema que o v10 tinha de Montreal/107/Silverstone (lição Monaco de novo:
  distribuição do fine-tune ≠ distribuição do deploy).
- **Consequência de deploy: solo/corrida padrão PERMANECE v10.**

**PASSO 3 (n=5, aluno vs professor, mesmo instrumento)**:
| pista | aluno (iter8) | professor | veredito do escrutínio |
|---|---|---|---|
| interlagos | 3/3 **126,9s**, 0 cont/lap | 3/3 127,3s, 0 | aluno 0,4s mais rápido — **LIMPO** (impulso 0=0, odômetro igual) |
| Hungaroring | 3/3 142,1s, 0 | 3/3 141,8s, 0 | paridade (prof 0,3s mais rápido) |
| Mexico | 3/3 130,3s, 7,7 cont/lap | 3/3 130,5s, 0 | "0,2s mais rápido" CONTAMINADO por empurrão (imp 88k) — não declarável |
| procedural:301 | **2/3**, 185 cont/lap | 3/3 100,6s, 7,3 | aluno pior em completude; tempo (98,5s) contaminado (imp 677k) |
| Monza | **0/3**, 660 cont/lap | **2/3**, 244 cont/lap, imp 1,8M | AMBOS ruins — ver lição abaixo |

**PASSO 4 (corrida 600 s all-v14, Interlagos) ✗ FALHOU** (Monza extra cancelada
pela regra "só se Interlagos passar"):
| métrica | v10 (cego) | professor-gate | v14 all | meta |
|---|---|---|---|---|
| contatos carro-carro (5 Hz) | 1333 | 240 | **1691** | <400 ✗ |
| contatos pós-largada (t>60s) | ? | 0 | **852** | ≈0 ✗ |
| hesitações ≥0,3s pós-largada | 1 | 0 | **33** (0,4s+; GAS/NOR 7) | ≤3 ✗ |
| tempo mediano rolante | 137s | 107,9s | **152,4s** (piora p/ 186-315s na v3) | ≤prof ✗ |
| fora do asfalto | 0,8% | 0,03% | **1,22%** | ≤1,5% ✓ |
| carros ≥1 volta | 10/10 | 10/10 | **10/10** | 10/10 ✓ |

**Diagnóstico da corrida (do CSV)**: contatos em toda a corrida (839 no min 0;
212/246 nos min 6/8) quando o campo, após incidentes individuais, volta a se
aglomerar em velocidade de rastejo (v média do líder cai 30→5,8 m/s no min 6-8).
**Fila-encravamento**: o v14 aprendeu a ESPERAR atrás de carro lento (rótulos
do professor: v_cap=v_ahead), mas nunca viu um carro PARADO na linha (fantasmas
de treino são professores que nunca param) nem carros ATRÁS (grade sempre à
frente). Todo incidente cria uma fila instável em baixa velocidade → empurrões.

### Declaração de produto (deliverable FASE 4)
| dimensão | v10 | v11b | v14 (iter8) |
|---|---|---|---|
| Solo (51 eps) | **48/51, 109s** | ~47/51, 108s | 39/51 — NÃO substitui o v10 |
| Zero-shot | Suzuka 3/3, Spa 3/3 | Suzuka 2/3 | Suzuka 3/3 (gate), **Spa 3/3 limpo**, Monaco 0/3 |
| Tráfego n=5 solo-eval | cego (não vê) | cego | **paridade limpa c/ professor em Interlagos/Hungaroring**; empurrões em Mexico/301 |
| Corrida 10 carros | 1333 contatos, 137s | — | **1691 contatos, 152s — PIOR que cego: fila-encravamento** |

**v14 = "evita colisões"? NÃO em corrida all-neural** (1691 contatos). Em
tráfego esparsoly controlado (eval com fantasmas-professores) sim: 0 cont/lap
em Interlagos/Hungaroring até n=8. Ultrapassagem: não ensinada, não observada.

### DEPLOY (3 profiles explícitos — o default por mtime foi REMOVIDO)
`run_race_10_cars.py --profile race|quali|traffic` (default **race**, documentado):
- **race** (padrão): v10_dagger, obs edge — único validado em corrida (Meta D).
- **quali**: v11b_pace90, obs edge — pace máximo.
- **traffic**: v14 (obs traffic 60d) — especialista em tráfego de fantasmas (eval).
  **Campo misto (FASE 5 A2, CONDICIONAL)**: use `--traffic-actor
  v14_traffic/dagger_actor_best_s1_n4.keras` (iter3) ou no máx. 1× iter8;
  par de iter8 e all-iter8 PROIBIDOS (encravamento). Runner:
  `race_diagnostic.py --mixed "traffic:2,edge:8" --traffic-actor <iter3>`.

### Próximos passos (FASE 5)
1. **FASE 6 em execução**: v14c treinando (replay-anchor + fantasmas
   parados + carros atrás; diagnóstico do near-miss fechado: desvio do BC).
   Ao abrir a sessão: `tail model_train/v14c_traffic/train.log` → se gates
   verdes, B3 completo + declaração final de produto;
   de 13 pistas (ou replay de dados solo do v10 nos estágios B/C) — a causa
   está medida (progressiva: iter1 ok → iter8 perde 3 pistas).
2. **Fix da fila-encravamento**: rótulos para "contornar carro lento/parado"
   (fantasmas com paradas programadas + professor com desvio) — medir primeiro.
3. **Fix do gap 'close'**: v_cap = v_ahead − ε quando gap < seguro (Monza: gap
   med 3,7m em contato sustentado; o cap nunca REABRE o gap) — uma variável,
   re-gate.
4. Carros ATRÁS do aluno no grid de treino (nunca treinado; a corrida tem).

## Limitações documentadas

1. **Física kappa>0,15**: o carro desliza lateralmente em curvatura extrema (hairpin Monaco R=6,4m) mesmo a 4 m/s com esterço máximo. Causa: interação das fases 4a/4b não mantém o vetor velocidade alinhado. NÃO corrigir sem medir (invalida professor calibrado).
2. **Obs de oponentes (FECHADA — estado final)**: pipeline completo e
   testado (obs 46d, fantasmas, race runner 60d, paridade NumPy). Produto:
   eval de tráfego LIMPO (iter3/iter8: 0 cont/lap), campo misto validado
   com controle (iter3), solo preservado na base (v14b_s0: 48/51). O ator
   de tráfego COMPLETO (solo+tráfego) não foi alcançado: v14c/v14d
   research-grade (Suzuka solo degradado pelos rótulos de contorno).
   Histórico (FASE 5): (a) esquecimento RESOLVIDO
   — v14b best_s0_n0 faz **48/51 = paridade v10** com canárias recuperadas
   (pool de 13 pistas); (b) tráfego: eval limpo (0 cont/lap n=4/n=8 no v14)
   e **campo misto validado com controle**: o all-v10 com grid embaralhado
   dá 1820 contatos (vs 1333 original) — as mistas (ii) 1573 e (iii) 1406
   ficam ABAIXO do controle, ou seja, **iter3 ou 1× iter8 não degradam o
   campo**; só o par de iter8 (2389) degrada (+31% vs controle); (c) o
   ator de tráfego do v14b NÃO existe (estágio B reprovado por Suzuka 2/3);
   (d) encravamento: veredicto abaixo; (e) ultrapassagem fora do escopo.
   DEPLOY de tráfego em campo misto: **iter3 (best_s1_n4)**; eval denso:
   best_s2_n8.
3. **Gerador procedural R≥10m**: o spline com pontos base espaçados atinge R≈15m nos hairpins (não R=6-8m como Monaco). Montreal (R=8,5m real) cobre a faixa apertada.
4. **Teto do pure pursuit ~100s** (sf=1,0): o gap teórico (85s) → professor (100s) = 15s/volta perdidos pelo path-following. O aluno DAgger herda este teto. Para 91,2s: racing line ou MPC.
5. **PPO estruturalmente falho (4× confirmado)**: com respawn (v6/v12) lap% fabricado → 0/N determinístico. SEM respawn (v13, protocolo correto): lap% honesto 2% → 2/3 a 125s (DEGRADOU de 3/3 a 108s). O gradiente PPO empurra a política PARA LONGE do comportamento DAgger. **Teto do stack: DAgger ~108s.**
6. **Recompensa v_allow**: corrigida na Fase 0 da Meta C (downforce físico). `sf_reward` parametrizável (default 0,80). O A_LAT_MAX=14 fixo original PROIBIA o ritmo de curvas rápidas.
7. **Contatos na largada (FECHADA na FASE 3)**: o corredor do offset
   (|lat_outro − lat_ego| < 3,5 m) EXTINGUIU os cruzamentos laterais do gate
   (258 → 240; 0 pares laterais restantes). Os 240 remanescentes são
   nose-a-cauda de largada por compostos diferentes (HARD vs MEDIUM em gap
   de 9 m) — rubbing físico sem efeito nos rótulos; o professor-com-tráfego
   no env (compostos idênticos) tem 0 contatos/lap. Dentro da meta (<400).
8. **β→0 degrada o final do currículo (FASE 3)**: iters 9-10 (β=0,11/0)
   regrediram (VAL 1/3; Suzuka 0/3 no ator final). O dataset fica dominado
   por estados do ALUNO com ruído 0,15. Mitigação usada: seleção best-por-VAL
   + gate sobre o best. Para o próximo currículo: considerar beta_end=0,3
   (medição primeiro) ou reduzir noise-std nas últimas iters.


## FASE 5 PARTE A (2026-10-13) — slot-swap + campo MISTO (inferência apenas)

### A1 — hipótese slot-swap: CONFIRMADA (contribuinte, não única causa)
Do race_diag_v14_all.csv (30.000 transições, 5 Hz): taxa de permutações do
top-3 por |dist_s| **0,484 swaps/s nas janelas ±5s dos contatos vs 0,203
baseline (2,38×)**; correlação ponto-bisserial fraca (0,067 — o swap é
condição necessária-ish mas não suficiente). **Veredito: SIM — o slot-swap
contribui para a divergência eval↔corrida** (o treino com fantasmas de gaps
estáveis nunca expôs o ranking permutando). NOTA DE DESIGN v15: histerese de
slots (mudança de slot só após N ticks estáveis). NÃO mudar a obs do v14
agora — mudaria a distribuição vs treino. Instrumento: `slot_swap_analysis.py`.

### A2 — corridas de campo MISTO (`--mixed "traffic:N,edge:M"`, grid embaralhado)
| config | v14 (grupo traffic) | v10 (grupo edge) | veredito |
|---|---|---|---|
| (i) 2× iter8 + 8× v10 | 381 cont (222 pós-larg), **15 hesit**, 142,2s, 1,58% fora | 2008 cont, 137,0s, 0 hesit | **FALHA — encravamento** |
| (ii) 1× iter8 + 9× v10 | 70 cont (**0 pós-larg**), **0 hesit**, 137,4s, 5 voltas | 1503 cont, 137,0s, 0 hesit | **PASSA** |
| (iii) 2× iter3 + 8× v10 | 84 cont (**0 pós-larg**), **0 hesit**, 138,2s, 9 voltas, 0,13% fora | 1322 cont, 137,0s, 0 hesit | **PASSA** |

- **iter8 em par reproduz o encravamento** (contatos traffic-traffic 55×;
  hesitações); **iter3 (menos esquecido) é cidadão limpo** (0 contato entre os
  dois v14s); iter8 sozinho também limpo. Os v10s NUNCA hesitam e mantêm o
  pace (137,0s = baseline) — a "degradação" dos v10s é só de EXPOSIÇÃO a
  contatos (165-251/carro vs 133 do baseline), possivelmente artefato do grid
  embaralhado (controle all-v10 embaralhado NÃO foi rodado — limitação).
- **Veredito de produto: CONDICIONAL.** O profile "traffic" ganha nota de uso
  "campo misto" com RESSALVAS: **usar best_s1_n4 (iter3) ou no máx. 1× iter8;
  par de iter8 proibido** (all-iter8 continua proibido — FASE 4).
- Bug corrigido durante A2: lap-time por wrap usava índice de amostra × 0,1s
  (amostras são 5 Hz = 0,2s) — `mixed_summary` agora usa VALORES de tick × 0,1
  (tempos das corridas acima já revisados; logs antigos impressos com o valor
  pela metade — CSVs são a fonte da verdade).
- Suite: **209/209** (+4 slot-swap, +8 mixed-runner).

### PARTE B (2026-10-14) — RESULTADO: esquecimento RESOLVIDO; estágio de tráfego REPROVADO por 1 volta
Tabela de estágios (gates automáticos no best-por-VAL; log v14b_traffic/train.log):
| estágio | best | gates | veredito |
|---|---|---|---|
| A (n=0, 2 iters) | best_s0_n0 (iter 2) | 5 canárias 3/3: Interlagos 110,8s, Suzuka 133,0s, **Silverstone 141,7s, Montreal 110,3s, proc:107 93,2s** | ✓ VERDE |
| B (n=4, 5 iters) | best_s1_n4 (iter 3) | canárias 3/3 VERDES; G2 n=4 3/3 (10 cont/lap); **Suzuka 2/3** | ✗ REPROVADO (obrigatório 3/3) |
| C (n=8) | — | não rodou (regra: parar no último verde) | abortado por regra |

**B3.1 (51 eps com o último verde, best_s0_n0): 48/51 = paridade v10** (meta
atingida): 39/39 treino (canárias recuperadas), Zandvoort 3/3 118,1s, Suzuka
3/3 133,0s, **Spa 3/3 124,4s**, Monaco 0/3 (= v10). O FIX DO ESQUECIMENTO
FUNCIONA (v14-iter8: 39/51 → v14b: 48/51).
**B3.2/B3.3: NÃO executados** — o único estágio verde é traffic-blind (rows
de tráfego zerados por construção, estágio A); ator de tráfego do v14b não
existe (estágio B reprovado; regra: não retreinar sem evidência nova, não
validar ator reprovado). Nota: a linha "[FINAL] último checkpoint bom" do
train.log aponta o best_s1_n4 (reprovado) — bug de relatório conhecido
(last_good é setado antes do gate); o último VERDE é o best_s0_n0.

8. **β→0 degrada o final do currículo (FASE 3)**: iters 9-10 (β=0,11/0)
   regrediram (VAL 1/3; Suzuka 0/3 no ator final). O dataset fica dominado
   por estados do ALUNO com ruído 0,15. Mitigação usada: seleção best-por-VAL
   + gate sobre o best. Para o próximo currículo: considerar beta_end=0,3
   (medição primeiro) ou reduzir noise-std nas últimas iters.
9. **VEREDITO DO ENCRAVAMENTO (FASE 5, parágrafo honesto)**: NÃO resolvido.
   O pool-13 resolveu o ESQUECIMENTO (solo), mas o estágio de tráfego do
   v14b reprovou (Suzuka 2/3) antes de produzir um ator de tráfego novo.
   A evidência acumulada aponta o encravamento como deficiência de
   TREINAMENTO, não de checkpoint: o MESMO iter8 encrava em par (15
   hesitações, 222 contatos pós-largada) e é limpo sozinho (0/0) —
   comportamento que depende de interações nunca rotuladas (carro parado,
   carros atrás, ranking permutando — slot-swap 2,38×). FASE 6: fantasmas
   com paradas programadas, carros atrás no grid, rótulos de contorno, +
   re-run do estágio B com âncora de replay (Suzuka near-miss).

## FASE 6 (2026-10-14) — diagnóstico do near-miss + v14c em treino

### PASSO 1 — Diagnóstico do Suzuka 2/3 (veredito: DESVIO DO BC)
Reprodução determinística do gate (seeds 0-2): o best_s1_n4-v14b falha a
**seed 2 SOZINHO** — off-track nos esses (s≈2093-2098, lat 8,1-8,2 m,
v 13-14 m/s), com o BLOCO DE TRÁFEGO ZERADO. Ablação n=0 vs n=4 (seeds 0-4):
- n=0 (cego): **3/5** (falhas seeds 2 e 4 — nos seeds do gate: 2/3 ✓ idêntico)
- n=4 (fantasmas): **5/5** — o pace reduzido do follow MASCARA a borda
**Veredito: o estágio B do BC degradou a pilotagem SOLO nos esses de Suzuka**
(não é interação tráfego×esses) — remédio direto: âncora de replay.
Instrumento: `model_train/diag_suzuka.py`.

### PASSO 2 — três adições (v14c) + pré-gate do professor
1. **ÂNCORA DE REPLAY**: `--solo-anchor 8` — 8 eps solo (professor puro, n=0,
   grip_random do treino) por iter nos estágios com tráfego, rotacionando
   pelas 13 pistas (~24% dos dados de cada fit; a pilotagem limpa nunca
   perde gradiente).
2. **FANTASMAS PARADOS**: `ghost_hold_ticks=(150,250)`, 1 fantasma/episódio
   congela na pose (set_position+reset_vel) — rótulos de CONTORNO. Pré-gate
   OBRIGATÓRIO executado: professor contorna o fantasma parado **com 0
   contatos** e completa a volta (o +46s vs solo vem de seguir o fantasma em
   re-aceleração pós-hold — rótulos de follow normais). **Ajuste de camada
   exigido pelo pré-gate**: `V_MIN_FOLLOW=1,0` no ReferenceController —
   líder PARADO não gera v_cap (senão o professor rasteja a 2 m/s atrás
   dele; sem cap o corredor de offset desvia) — 3 testes novos.
3. **CARROS ATRÁS**: `grid_position=(5,7)` — aluno no meio do grid, fantasmas
   à frente E atrás (obs ahead=0; slots por proximidade: ±9, ±18, ... m).
- Bug de relatório corrigido: `last_good` no train_dagger agora só avança
  DEPOIS do gate passar (+3 testes) — o [FINAL] do v14b apontava reprovado.
- Suite: **221/221**.

### v14c — RESULTADO: estágio B REPROVADO (mesmo modo de falha)
| gate (best-por-VAL = iter 2) | resultado |
|---|---|
| Interlagos solo | 3/3, 105,8s ✓ |
| **Suzuka solo** | **1/3 ✗** (v14b era 2/3) |
| Silverstone / Montreal / proc:107 | 3/3 / 3/3 / 3/3 ✓ (âncora segurou as canárias) |
| professor n=4 | 3/3, 123,5s, 0 cont/lap |
| G2 n=4 | 3/3 mas **53 cont/lap** (v14b: 10) |
Diagnóstico (diag_suzuka no best): MESMO MODO — solo 1/5 (esses s≈2091-2098,
lat 7,9, tráfego zerado; + falha nova a 39 m/s em s=2205; com n=4: 3/5 com
saídas em s≈33). Âncora 8 não segurou Suzuka; suspeita registrada (F6b): os
rótulos de contorno do ghost_hold (presente em TODAS as eps de tráfego) e
carros atrás deslocam o esterço solo. Crash corrigido no train_dagger
(last_good None quando o estágio 0 reprova). ÁRVORE da sessão: um re-treino
autorizado → **v14d (âncora 12, β-end 0,4, resto idêntico)** em voo
(model_train/v14d_traffic/train.log). Se Suzuka reprovar de novo:
ENCERRAMENTO honesto — ator de tráfego research-grade; deploy mantém iter3.

### v14c — TREINANDO em background (log: model_train/v14c_traffic/train.log)
Init v14b/best_s0_n0 (base solo 48/51 provada), estágios "4:5,8:3", β 1,0→0,3,
gates automáticos nas 5 canárias no best-por-VAL. Est. ~8-9h. AO TERMINAR:
conferir gates; se verdes → B3 completo (51 eps; G2 n=8; compare n=5; corridas
all-v14c + mista par + --hold-at) e a declaração final de produto (tabela 5
dimensões). Comandos no rodapé.

10. **LIÇÃO DE GATES (FASE 6, estrutural)**: G2 com tráfego pode
   MASCARAR degradação solo — evidência: o mesmo checkpoint (v14b best_s1_n4)
   faz solo 3/5 (off-track nos esses de Suzuka, bloco de tráfego zerado) e
   5/5 com 4 fantasmas (o pace reduzido do follow esconde a borda perdida).
   **Gates de currículo de tráfego exigem G1 (solo) e G2 (com tráfego)
   SEPARADOS e ambos verdes** — nunca G2 sozinho.

## v15 FASE 0 — organização + MLflow (2026-10-14, CONCLUÍDA; PARE p/ aprovação)

- **Manifest**: `repo_manifest.csv` (464 arquivos; caminho/size/mtime/referenciado_em).
- **Movido p/ archive/ (NUNCA deletado; READMEs de proveniência em cada lote)**:
  22 dirs de checkpoints (PPO v2–v8b, v6_CONTAMINADO, v9, v11, v12, v13,
  v14c, v14d + `archive/checkpoints/v14b_evidence/best_s1_n4.keras` — a
  evidência da cadeia 2/3→1/5→0/3), 13 checkpoints soltos da raiz (BC/RL),
  15 scripts obsoletos (train.py, train_multi_context.py, evaluate_policy.py
  etc. — `train_multi_context_ppo.py` FICA: train_dagger importa o
  MultiContextPPOAgent; verificado por grep). Suite verde após CADA lote.
  `test_regression_v2v4.py` atualizado para os paths de archive (v2/v4).
- **experiments/legacy/**: 56 CSVs/logs de diagnóstico (188 MB) — candidatos
  ao MLflow legacy-import.
- **Deletado (regenerável)**: __pycache__ + 32 `dagger_actor_iterN.keras`
  não-best dos runs mantidos (métricas de cada iter confirmadas nos
  training_meta.json antes). ~270 MB liberados no total.
- **MLflow** (`model_train/tracking.py`; backend sqlite:///mlflow.db,
  artefatos mlruns/): `start_run/log_eval/log_race/log_checkpoint`,
  experimentos dagger-solo/dagger-traffic/race-layer/overtaking/legacy-import.
  **Registry f1-bot**: aliases `race`→v10_best, `quali`→v11b_best,
  `traffic`→iter3 (versões 1-3). `--profile` resolve por alias com fallback
  de arquivo (testado). Integração best-effort (guards) em race_diagnostic,
  eval_protocol, run_race_10_cars. `mlflow ui` → backend/mlflow.db.
- **PROFILES['traffic'] alinhado à declaração final**: iter3 (o iter8 em
  par/all-neural é proibido) — divergência registry↔runner detectada pelo
  teste novo e corrigida.
- **Pendente (não bloqueia FASE 1)**: legacy-import dos training_meta/CSVs
  como runs MLflow; consolidação dos caches FastF1 (env usa
  model_train/cache_fastf1; API usa backend/cache — ambos no .gitignore).
- **Suite: 222/222** (+1 registry). v14d colhido formalmente: gate Suzuka
  **0/3**, "NENHUM estágio verde" — research-grade confirmado.

**FASE 1 (próxima, com aprovação)**: por que a corrida neural é ~28s mais
lenta que o professor — 4 corridas de medição (governor off / teto v_plan)
com gate ≤115s + Meta D + contatos ≤1333. Expectativa verificável da
hipótese: o gap do governor concentra-se em curvas médias-rápidas
(κ=0,01: cap 37 vs física ~54 m/s), não em curvas fechadas (R=20m: 16,7 vs
17,6). FALSA → não trocar o governor.

## v15 FASE 1 — por que a corrida neural era ~28s mais lenta (2026-10-14, FECHADA)

**Expectativa verificável ANTES das corridas** (teste de falsificação, analítico):
o cap do governor (sqrt(14/κ_ahead@120m), sem downforce, sem distância de
frenagem) difere do v_plan **em TODAS as bandas** — não só nas médias-rápidas
como a hipótese original: retas −15,3 m/s médios (cap ~60 vs plano 75 — o
κ_ahead@120m vê curva adiante e limita a RETA INTEIRA), médias-rápidas −18,7,
médias −17,9, fechadas −22,3; **138/167 pontos da pista com cap abaixo do
plano; ~35,7% de perda de pace global**. Hipótese refinada: o deficit é
generalizado; a intervenção (teto v_plan) segue justificada — com expectativa
quantificada.

**Tabela das configs** (v10, Interlagos, 600s, 10 carros, seed 0; MLflow
race-layer com params.governor):
| config | rolante | voltas | contatos (pós-largada) | hesit. | fora | autoridade gov |
|---|---|---|---|---|---|---|
| on (histórico) | 137,1s | 48 | 1512 (491) | 1 | 0,36% | 28,5% |
| off | 103,6s | 60 | 1632 (808) | 0 | 0,0% | 0% |
| **vplan (ADOTADO)** | **103,4s** | 60 | 1576 (748) | **0** | **0,0%** | 2,4% |

**Escolha final: governor vplan.** Justificativa com números: recupera o
MESMO pace do governor-off (Δ 0,2s) mantendo um freio de segurança ativo
(2,4% dos ticks vs 28,5% antes), zero hesitações e zero fora. Gate de pace:
103,4 ≤ 115 ✓; Meta D: 0 paradas ≥3s ✓, 10/10 (6 voltas/carro) ✓, fora 0,0%
≤4,6% ✓; contatos: 1576 > 1333 (histórico) e +4% vs baseline da mesma sessão
(1512) — **registrado conforme a regra: a cura de contatos é a FASE 3
(percepção de tráfego), NÃO reverter o governor**. Nota de instrumento: o
baseline histórico 1333 foi medido em código pré-v14; o baseline atual é 1512.
Nota de honestidade: a primeira rodada das 3 corridas deu resultados idênticos
porque o edit do bloco do governor não gravou (asserção de texto falhou) —
detectado pela coluna authority (gov=off ainda 28,5%), corrigido e re-rodado.
**Experimento 4 (perfil por setor) NÃO foi necessário** (gate ≤115s atingido).

**ADOÇÃO (fix de camada, SEM retreino)**: `--gov vplan` é o DEFAULT do
race_diagnostic e do run_race_10_cars (o comportamento histórico fica
disponível via `--gov on`). O race profile MANTÉM o v10 como ator — só a
camada de corrida mudou. Baselines re-pinados p/ a FASE 2: o professor
(inalterado) mantém 107,5/107,9s; o NMEWS neural com vplan: 103,4s; contatos
neural 1576 (cura na FASE 3).

## v15 FASE 3 gates (2026-10-16, PARE com diagnóstico)

### O que passou
- **3.0**: BUG crítico corrigido — `forward_linear()` (m PRÉ-tanh) no
  NumpyNeuralActor; o atanh(tanh(m)) perdia precisão quando a política
  saturava em retas (+1 teste; 252/252). Paridade composite NumPy↔Keras
  COM tráfego: max diff 4,8e-07 sobre 1000 obs reais.
- **3.1 G1 solo (teorema)**: Interlagos 3/3 109,1s; Suzuka 3/3 131,4s —
  o composite É v10 em solo, por construção ✓.
- **3.2 Disciplina**: p95 |g·r| n=0 = **0,0000** (o residual NÃO dispara
  em tráfego neutro — o antídoto do v14c funciona); p95 n=4 = 0,686
  (age em tráfego ativo). Separação perfeita.

### O que falhou
- **3.3 G2 n=4**: **0/3** — o composite sai da pista em s≈3096 (Curva do
  Lago), lat 8,7. Decomposição: r=(−0,2→−0,4, **−1,3→−1,6**) quando g>0,6 —
  freio fortíssimo + esterço contra, independente do κ da curva. O v10
  solo segura a linha; o residual o derruba.
- **Causa**: a distribuição de TREINO usou SÓ heterog+hold+grid5:7 (o
  prompt pedia MISTO). O cenário de eval (fantasma uniforme P10, sem hold)
  não foi visto no treino.

### VEREDICTO: G2 ✗ com G1 ✓ e disciplina neutro=0 → não é bug do gate —
o residual está sub-treinado para a distribuição padrão de eval. Opções:
1. Re-treino limitado com fantasmas MISTOS (alternar config por episódio).
2. Research-grade: residual documentado; deploy mantém v10+vplan.

## v15 FASE 3 r2 (2026-10-16) — GATES VERDES + FASE G veredictos; PARE duplo

### Trilha A: re-treino r2 (fantasmas mistos round-robin)
- Treino: 7 iters (0:1,4:4,8:2), 73.359 estados, solo hash estável em TODAS.
- **G1 solo**: Interlagos 3/3 109,1s + Suzuka 3/3 131,4s (teorema).
- **G2 n=4**: 3/3, 121,4s, 6,0 cont/lap (professor: 123,5s, 0) ✓.
- **G2 n=8**: 3/3, 131,9s, 65,0 cont/lap ✓ (denso; professor: 134,1s, 0).
- **Disciplina**: p95 |g·r| n=0 = 0,0000 (antídoto v14c funciona).
- **Decomposição s=2005-2270**: r agora contextual (SEM o freio-forte do r1).
- **Hold-at**: 2/2 voltas, 1-12 contatos — o composite CONTORNA o carro parado.
- **51 eps**: 48/51 (30/33 medidas + procedurais = v10 por construção).
- **Monza 'close'**: 770 < 1383 → fix MANTIDO.
- Corridas all-composite/mista/hold-at 600s: **BLOQUEADAS** (composite no
  race runner = FASE 4 — o residual input precisa de wiring de prev/v/κ).

### Trilha B: FASE G auditoria de geometria
- **Monaco v1 = ARTEFATO DE SPLINE**: clearance 1,71m com gap curto 53m;
  56 pares < 8m. Proposta: v2 via mirror 2021 + gate geom ≥8m.
- **Suzuka = crossover REAL**: clearance 0,39m com gap 2205m (meia volta) —
  o crossover na ponte/esses é legítimo; G3 (saltos de hint) pendente.
- **SF Interlagos = 63,8% da volta** — ~~não na reta!~~ **CORREÇÃO R2/R3: o
  veredicto "errado" foi REFUTADO.** SF 729 é a linha FIA real (heading 55°,
  reta de 45 m antes); toda a base de evidência verde (B3.1/B3.2/B3.3c/v14)
  foi medida com ela. O "não está na reta" vinha do detector de retas do
  audit, que não separa curva suave de reta em polilinha real (a pista
  frozen não tem reta >280 m em critério algum); a função pura
  find_best_start_waypoint herda esse defeito e escolheu um SWEEPER (929) —
  refutado em B3.1-v2 (1352 contatos, 68% fora). SF canônico = **729**.
- **Spa INCOMPLETA no cache**: 4352m vs 7004m oficial (−37,9%).
- 7 pistas congeladas com sha256 em `model_train/tracks_frozen/`.

### Pistas congeladas (tracks_frozen/)
| pista | wp | sha256 | observação |
|---|---|---|---|
| interlagos_v1 | 1131 | (ver JSON) | SF 729 = linha FIA (verdade canônica) |
| **interlagos_v2** | 1131 | 164876196eb12174 | **CANÔNICO: SF 729** (json autoritativo no loader) |
| Monza_v1 | 1477 | | |
| Monaco_v1 | 913 | | ARTEFATO clearance |
| Suzuka_v1 | 1485 | | crossover real |
| Hungaroring_v1 | 1138 | | |
| Zandvoort_v1 | 1099 | | |
| Spa_v1 | 1167 | | INCOMPLETA |

## v15 FASE 4 (2026-10-16) — B3 executado; PROMOÇÃO proposta; PARE

### B3 corridas 600s Interlagos v1 (seed 0, gov vplan, determinístico)
| corrida | contatos (pós-larg) | fora | rolante | hesit. |
|---|---|---|---|---|
| **B3.1 all-composite** | **223 (0)** | 0,17% | 103,4s | 0 |
| B3.2 hold-at 1200 | 3975 (3727) — pilha | 0,36% | — | 13 |
| B3.3c CONTROLE v10 cego vplan | **3433 (3061)** [PRÉ-CANÔNICO: instrumento live pré-R2, clima-loteria; o regime canônico é 21-32% fora (R13)] | **73,6%** [idem] | — | — |

### B3.1 — TODAS as metas verdes → PROMOÇÃO
| meta | resultado |
|---|---|
| 10/10 ≥1 volta | ✓ 60 wraps (6/carro) |
| 0 paradas ≥3s | ✓ |
| hesitações ≤3 | ✓ 0 |
| fora ≤1,5% | ✓ 0,17% |
| rolante ≤115s | ✓ 103,4s |
| contatos <1576 | ✓ **223** (−86%) |
| pós-largada ≤748 | ✓ **0** |

### PROMOÇÃO: race default = COMPOSITE (proposta para aprovação)
O composite (solo v10 congelado + residual gated) é o v10 exato em solo
(48/51, hash-verificado) + segurança em tráfego (223 vs 1576 contatos,
0 vs 73,6% fora). O v10 cego+vplan (o FASE 1) acelerou o pace mas DEGRADOU
a segurança — o composite resolve ambos. `race-blind` preserva o v10.

### Limitações do composite
1. **Contornos múltiplos não coordenados**: 9 composites no mesmo hold-at
   geram pilha (B3.2: 3975 contatos, 13 paradas). Sem comunicação inter-carros.
2. **B3.3 mista** não executada (wiring: o grupo traffic precisaria do
   composite completo, não de um ator único .keras).
3. **FASE H** (Monaco v2, SF, Spa, G3): NÃO executada nesta sessão.

## ESTADO FINAL DO PROJETO (declaração de produto — ciclo v14 encerrado)

### Tabela de produto (5 dimensões, números medidos)
| checkpoint | solo 51 eps | tráfego eval (cont/lap) | corrida all (600s) | misto em par (vs controle 1820) | hold (carro parado) |
|---|---|---|---|---|---|
| **v10 (race)** | **48/51, 109s** | cego | 1333 (grid orig.) / 1820 (embaralhado); Meta D ✓ | baseline | cego (não contorna; segue/para) |
| v11b (quali) | ~47/51, 108s | cego | — | — | cego |
| **v14-iter3 (traffic)** | ~42/51 (só Silverstone) | n=4: 0 (123,4s) | — | **PASSA** (1406; 0 pós-largada) | não medido |
| v14-iter8 | 39/51 | n=8: 0 (134,0s) | **1691 FALHOU** (33 hesit.) | FALHA (2389) | n/a |
| v14b best_s0_n0 | **48/51** (paridade v10) | cego por construção | n/a | n/a | n/a |
| v14c best_s0_n4 | **Suzuka solo 1/5** (gate 1/3 ✗) | n=4: **53** | não rodado (reprovado) | não rodado | **2/2 voltas, 23-33 contatos** |

### DEPLOY final (aplicado)
- **race (default)**: v10_dagger — único validado em corrida (Meta D verde;
  all-neural alternativo nunca cumpriu os critérios de promoção: all-iter8
  1691 contatos; all-v14c não rodou por reprovação do ator).
- **quali**: v11b_pace90.
- **traffic (campo misto, CONDICIONAL)**: **iter3 (v14_traffic/best_s1_n4)**,
  até 2 carros v14; par de iter8 e all-v14 proibidos; eval denso: iter8.
- **v14c/v14d: research-grade** — não deployar.

### Enunciado de comportamento (para o usuário do bot)
O bot DEPLOYADO (v10/iter3): SEGUE carro lento em movimento (v+2, sem
ultrapassagem — por design do professor, NÃO é bug); NÃO contorna carro
PARADO (para atrás — encravamento conhecido; o race runner tem --hold-at
apenas como instrumento de teste). O v14c (research) contorna carro parado
sem travar (2/2 voltas) mas com contato (23-33) e solo degradado em esses.

### Veredito do encravamento (limitação 9, FECHADA): PARCIAL — competência
aprendida, produto NÃO. O v14c provou que rótulos de contorno (ghost_hold)
ensinam a não-TRAVAR (mini-gate hold: 2/2 voltas, pace normal), mas: (a)
passa com 23-33 contatos (higiene zero); (b) a MESMA distribuição de rótulos
degrada o solo nos esses (Suzuka 1/5 vs 48/51 da base) — trade-off estrutural
desta arquitetura de dados (v14b 2/3 → v14c 1/5 → v14d-iter1 0/3 solo).
Fila pós-v1: contorno limpo com margem nos rótulos; separar as cabeças de
solo/tráfego; histerese de slots (v15).

## Splits de pistas (NUNCA alterar)

- **TREINO**: interlagos, Monza, Hungaroring, Silverstone, Montreal, Bahrain, Mexico, procedural:101-301 (13 pistas)
- **VALIDAÇÃO**: Zandvoort (seleção de checkpoint)
- **TESTE**: Monaco, Suzuka, Spa (zero-shot, NUNCA treinar/selecionar nelas)

## Arquivos-chave

| Arquivo | Descrição |
|---|---|
| `model_train/f1_env.py` | env (obs legacy 23d / edge 34d; sf_reward) |
| `model_train/velocity_profile.py` | v_plan físico (downforce, círculo de atrito, sf adaptativo, híbrido peak/avg) |
| `model_train/reference_controller.py` | professor v2 (pure pursuit + v_plan, lookahead adaptado) |
| `model_train/procedural_track.py` | gerador procedural (hairpins, esses, gate de kappa) |
| `model_train/train_dagger.py` | DAgger multi-pista (--init-actor, --sf, --obs-mode) |
| `model_train/train_multi_context_ppo.py` | PPO (--sf-reward, --obs-mode, --init-actor) — **NÃO RECOMENDADO** |
| `model_train/eval_policy.py` | avaliação determinística (--obs-mode, --noise-sigma) |
| `model_train/race_diagnostic.py` | corrida headless (--actor, --obs-mode, --track; **--controller professor** = gate all-professor v14) |
| `model_train/reference_controller.py` | professor v2 + camada de TRÁFEGO (signed_dist_s, car-following, offset c/ corredor; driver_id p/ fantasmas) |
| `model_train/transfer_v10_v14.py` | PASSO 1 FASE 3: transferência v10→v14 por remap de rows (+CLI do checkpoint init) |
| `model_train/eval_teacher_solo.py` | PASSO 0 FASE 3: baseline do professor solo na metodologia do gate (largada vs rolantes) |
| `model_train/gate_checkpoint.py` | PASSO 3 FASE 3: gate manual de checkpoint (G1 sem tráfego + G2 com tráfego) |
| `model_train/eval_protocol.py` | PASSO 2 FASE 4: protocolo 51 eps vs v10 pinado |
| `model_train/eval_traffic_compare.py` | PASSO 3 FASE 4: aluno vs professor n=5 c/ escrutínio (impulso, follow%, linha) |
| `scripts/run_race_10_cars.py` | corrida: --profile race/quali/traffic (default race; obs 'traffic' 60d no NeuralRaceController) |
| `model_train/train_dagger.py` | DAgger multi-pista --obs-mode traffic --traffic-stages "n:iters,..." + warm start + gates por estágio |
| `model_train/physics_frontier.json` | fronteira R_min(v) calibrada |
| `model_train/AUDITORIA_RL.md` | histórico completo de investigação (restaurado VERBATIM da versão-FONTE 439f402 no commit 2fb1d37 — LARGADA-4; bloco de proveniência no topo) |

## Comandos essenciais

```bash
cd backend
# testes
.venv/bin/python -m pytest tests/ -q  # 20F/349P/3S (20F pré-existentes; +4 t_pe1 do PISTAS_EXPAND_1; composite_parity:45 skip condicional)
# avaliação determinística
.venv/bin/python model_train/eval_policy.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras \
  --episodes 3 --obs-mode edge
# corrida (aluno neural)
.venv/bin/python model_train/race_diagnostic.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras \
  --obs-mode edge --ticks 6000 --out race.csv
# GATE all-professor v14 (reproduzível — sim determinística)
.venv/bin/python model_train/race_diagnostic.py \
  --controller professor --ticks 6000 --laps 99 \
  --track interlagos --out race_diag_prof_gate_s0.csv --seed 0
# baseline do professor solo (largada vs rolantes)
.venv/bin/python model_train/eval_teacher_solo.py --laps 3 --episodes 3
# gate manual de checkpoint v14
.venv/bin/python model_train/gate_checkpoint.py \
  --actor model_train/v14_traffic/dagger_actor_best_s2_n8.keras \
  --g1-tracks "interlagos,Suzuka" --g2-traffic 8
# DAgger novo
.venv/bin/python model_train/train_dagger.py --obs-mode edge \
  --tracks "interlagos,Monza,..." --val-track Zandvoort \
  --iters 10 --save-dir model_train/vN_dagger
# DAgger de TRÁFEGO v14c (FASE 6 — o treino em voo; init na base solo 48/51)
.venv/bin/python model_train/train_dagger.py --obs-mode traffic \
  --traffic-stages "4:5,8:3" \
  --tracks "interlagos,Monza,Hungaroring,Silverstone,Montreal,Bahrain,Mexico,procedural:101,procedural:103,procedural:107,procedural:201,procedural:203,procedural:301" \
  --val-track Zandvoort --epochs 50 --episodes-per-track 2 --beta-end 0.3 \
  --gate-tracks "interlagos,Suzuka,Silverstone,Montreal,procedural:107" \
  --solo-anchor 8 --ghost-hold "150:250" --ghost-hold-n 1 --grid-position "5:7" \
  --init-actor model_train/v14b_traffic/dagger_actor_best_s0_n0.keras \
  --save-dir model_train/v14c_traffic --seed 42
# DAgger de TRÁFEGO v14 — comando REAL (FASE 5 PARTE B: pool-13, β-end 0,3,
# gates nas 5 canárias; reproduz o treino do v14b)
.venv/bin/python model_train/train_dagger.py --obs-mode traffic \
  --traffic-stages "0:2,4:5,8:3" \
  --tracks "interlagos,Monza,Hungaroring,Silverstone,Montreal,Bahrain,Mexico,procedural:101,procedural:103,procedural:107,procedural:201,procedural:203,procedural:301" \
  --val-track Zandvoort --epochs 50 --episodes-per-track 2 --beta-end 0.3 \
  --gate-tracks "interlagos,Suzuka,Silverstone,Montreal,procedural:107" \
  --init-actor model_train/v14_traffic/init_from_v10.keras \
  --save-dir model_train/vN_traffic
# veredito ANTI-D3-1 (mecânico; commitado ANTES das corridas — PADRÃO-OURO)
.venv/bin/python scripts/anti_d3_verdict.py \
  experiments/anti-d3-1/1_controle.csv experiments/anti-d3-1/2_allcomposite.csv
# probe pós-veredito ANTI-D3-1 (read-only; 1ª-divergência ON vs OFF)
.venv/bin/python scripts/anti_d3_probe.py \
  experiments/anti-d3-1/2_allcomposite.csv \
  experiments/f4v15-wiring/2_allcomposite.csv
# diagnóstico SANIDADE-0 D1-D3 (read-only sobre CSVs F4v15)
.venv/bin/python scripts/sanidade_diag.py
# veredito SANIDADE-0 (mecânico; commitado antes das corridas)
.venv/bin/python scripts/sanidade_verdict.py \
  experiments/sanidade-0/1_prot_v0.csv experiments/sanidade-0/2_prot_comp.csv \
  experiments/sanidade-0/3_gate_v0_s70.csv experiments/sanidade-0/4_gate_comp_s71.csv \
  experiments/sanidade-0/5_gate_v0_s72.csv experiments/sanidade-0/6_gate_comp_s73.csv
# veredito SANIDADE-1b (auto-validável: --selftest reproduz F4v15+SANIDADE-0)
.venv/bin/python scripts/sanidade1b_verdict.py --selftest
.venv/bin/python scripts/sanidade1b_verdict.py \
  experiments/sanidade-1b/1_prot_v0.csv experiments/sanidade-1b/2_prot_comp.csv \
  experiments/sanidade-1b/3_m2only_comp_s0.csv experiments/sanidade-1b/4_gate_v0_s74.csv \
  experiments/sanidade-1b/5_gate_comp_s74.csv experiments/sanidade-1b/6_gate_v0_s75.csv \
  experiments/sanidade-1b/7_gate_comp_s75.csv
# DESENHO DE PISTA (FONTE-2: mirrors → OpenF1 → ERRO LOUD; preset silencioso morto)
.venv/bin/python scripts/draw_track.py --track monaco --save monaco.png
#   ^ instantâneo, ZERO rede: interlagos|monaco|spa = mirrors canônicos
.venv/bin/python scripts/draw_track.py --track Italy --year 2024 --save monza.png
#   ^ OpenF1 location (país F1 2023+, sem login; 1ª vez ~10 s + cache local)
.venv/bin/python scripts/draw_track.py --track pista-xyz
#   ^ ERRO LOUD com lista de opções (nunca desenha outra pista)
.venv/bin/python scripts/draw_track.py --track Monza --legacy-preset
#   ^ caminho ANTIGO (FastF1 morto → preset Interlagos) — use sabendo
# PISTAS_EXPAND_1 (aquisição OpenF1 → mirrors v2; 17/25 chamadas gastas;
# streams em backend/cache/openf1_pistas_expand_1 = reprocessar SEM rede)
.venv/bin/python scripts/pistas_expand_1.py t0      # inventário offline
.venv/bin/python scripts/pistas_expand_1.py golden  # §4: canônicos/v1s intocados + manifest×arquivos
#   manifest: experiments/pistas-expand-1/manifest_pistas_expand_1.csv
#   mirror NOVO congelado: load_track_frozen('LasVegas') (case-exata; −0,998%)
#   candidato Suzuka (b): experiments/pistas-expand-1/candidatos/Suzuka_candidato_openf1.json
# ESPECTADOR (GUI; bundle = só mecanismo verde M2 rejoin-perceptive;
# atribuição solo LIMPA: comp s0 fora 28,0% <= 29,9; cc 516; hesit 6)
.venv/bin/python scripts/run_race_10_cars.py --profile race-blind \
  --modo espectador --seed 0 --laps 99
# VARIEDADE-1 (opt-in; default 0 = canônico bit-idêntico; o COMANDO DO DONO:
# mesma seed + N diferente = corrida diferente; mesma (seed,N) = bit-idêntica)
.venv/bin/python scripts/run_race_10_cars.py --profile race-blind \
  --modo espectador --seed 0 --variedade 1 --laps 99
# PROF-MONACO-1: selftest do instrumento (Interlagos + Monaco) e bateria
.venv/bin/python scripts/saidas_verdict.py --selftest
.venv/bin/python scripts/saidas_verdict.py --track monaco \
  --label-a "PROFESSOR (solo-frozen)" --label-b "ALUNO (v10-cego)" \
  --files-a experiments/prof-monaco-1/prof_s0.csv experiments/prof-monaco-1/prof_s1.csv \
             experiments/prof-monaco-1/prof_s2.csv experiments/prof-monaco-1/prof_s3.csv \
             experiments/prof-monaco-1/prof_s4.csv \
  --files-b experiments/prof-monaco-1/aluno_s0.csv experiments/prof-monaco-1/aluno_s1.csv \
             experiments/prof-monaco-1/aluno_s2.csv experiments/prof-monaco-1/aluno_s3.csv \
             experiments/prof-monaco-1/aluno_s4.csv \
  --out-dir experiments/prof-monaco-1
# veredito VARIEDADE-1 (mecânico; selftest reproduz as âncoras)
.venv/bin/python scripts/variedade_verdict.py --selftest
.venv/bin/python scripts/variedade_verdict.py \
  experiments/variedade-1/1_prot_v0.csv experiments/variedade-1/2_prot_comp.csv \
  experiments/variedade-1/3_var1_v0.csv experiments/variedade-1/4_var1_v0_rep.csv \
  experiments/variedade-1/5_var2_v0.csv experiments/variedade-1/6_var1_comp.csv
# veredito SAIDAS-1 (mecânico e auto-validável: --selftest reproduz casos sintéticos; Q1-Q4 cruas)
.venv/bin/python scripts/saidas_verdict.py --selftest
.venv/bin/python scripts/saidas_verdict.py \
  --ctrl experiments/f4v15-wiring/1_controle.csv \
  --comp experiments/f4v15-wiring/2_allcomposite.csv \
  --out-dir experiments/saidas-1
```

## v15 FASE R2 (2026-10-17) — unificação do SF + re-medida B3.1-v2: VERMELHO; caos + rejoin são as causas

### S1–S4 (unificação)
- **S1**: `find_best_start_waypoint(waypoints)` extraída como função PURA (geometria, sem estado de env).
- **S2**: validação cruzada IMPOSSIBILITADA — FastF1 offline (circuit_info 401; cache existe mas não carrega). Env standalone cai no preset 240wp (SF 109). A pista frozen (1131wp, 4160,4m) é a ÚNICA via para a geometria real.
- **S3**: `interlagos_v2.json` criado com SF 729→929 (função pura, 81,4% da volta).
- **S4**: loader prefere v2; env usa a função pura. Testes de contrato verdes (48+1 skip).
- **BUG DO S4 ENCONTRADO NA RE-MEDIDA**: `load_track_frozen` fazia OVERRIDE do sf_idx do json com a função pura em runtime (herança do FASE R) — o json era peso morto. B3.1-v2 (json SF929) e o run FASE R (json v1 SF729) rodaram IDÊNTICOS (1352 contatos bit-a-bit) porque ambos usaram SF 929 por override. **CORRIGIDO: o sf_idx do json é AUTORITATIVO** (a função pura é a ferramenta que GEROU o valor, não um reajuste em runtime).

### S5 — re-medida (gate B3.1: 10/10 voltas, 0 paradas≥3s, hesit≤3, fora≤1,5%, rolante≤115s, contatos<1576, pós-larg≈0)
| realização | cc | pós-60s | fora | voltas | veredicto |
|---|---|---|---|---|---|
| B3.1 verde (live, seed 0) — registro histórico | 223 | 0 | 0,17% | 10/10 | VERDE (realização ÚNICA) |
| frozen SF929 (v2 original, seed 0) | 1352 | 1260 | 68,2% | 7/10 | ✗ largada no sweeper |
| frozen SF729 seed 0 | 309 | 128 | 60,3% | 7/10 | ✗ |
| frozen SF729 seed 1 | 211 | 82 | 45,9% | 9/10 | ✗ |
| frozen SF729 seed 2 | 271 | 120 | 49,5% | 10/10 | ✗ |

- **SF 929 REFUTADO**: o "best straight" da função pura é um sweeper com quebras de 2,3-2,6°/wp a cada ~35m (o detector de reta não separa curva suave de reta em polilinha real); a pista frozen não tem reta >280m em nenhum critério. A âncora empírica de TODA a base verde (B3.1/B3.2/B3.3c/v14) é SF 729 (reta de 45m, heading 55° — linha FIA real). **interlagos_v2.json RECONSTRUÍDO com sf_idx=729** (sha256 164876196eb12174), sf_method documentando a refutação.
- **Diagnóstico dirigido (árvore pré-registrada)**:
  - *g active%*: instrumento composite VIVO (g>0 25-27% vs 33% verde; r_norm ≤~3 na largada em ar limpo). r_norm 20-40 observado é SINTOMA OOD (carros fora de pista projetam s/lat lixo que envenenam as features de tráfego de TODOS), não causa.
  - *fora por setor*: colapso é na LARGADA (t=4-46s, s 2655-2820/0-80) — pares de colunas colidem em cadeia (PIA↔RUS, SAI↔PER, ALO↔GAS), carros lançados a 45-100m da pista.
  - *hint resync*: projeção EXONERADA — a divergência de sinal lat_s×obs4 (~43-50% dos ticks) é ARTEFATO DE CONVENÇÃO do CSV diagnóstico, presente também em todos os runs verdes (v14_all: 43%). O grid físico é correto (±1,9m alternados, confirmado por obs4; a coluna `lat` do CSV tem convenção invertida — CAVEAT de instrumento).
- **CAOS A/B (decisivo)**: v14-actor live (verde: 1691cc, 1,2% fora, lat_max 16m) vs v14-actor frozen (1871cc, ~66% fora): trajetórias IDÊNTICAS por 13-21 ticks (diferença ≤cm), depois UM flip de threshold (VER t=2,1s: v≈21,0 → verde acelera, frozen freia) e a cascata acoplada por contatos diverge o fim completamente. Fonte da perturbação: nível float (json é float64 exato; candidatas: atributos do Track live [length_m explícito 4309 vs computado 4160 — sem efeito pré-volta-1 identificado], ordem de soma, estado pybullet). **Conclusão: a largada de 10 carros a 3,8m de separação lateral é um sistema caótico; o gate de 1 realização/600s não é instrumento sombro para ele.**
- **MODO DE FALHA REAL (novo, produto)**: carro lançado >20m fora NUNCA recupera — rejoin (th 0,35, teto 8 m/s) + recovery (saída só com progresso físico) não vencem o grip da grama a 50-100m; carros encravam a v≈1,5 m/s por 500+s (seed 0: 6 carros; seeds 1-2: parcial — reentraram e laparam a 136-205s). Este modo NUNCA foi exercitado na era verde (nada saiu >16m).

### S6 — VEREDICTO
**B3.1-v2 = VERMELHO (3/3 seeds). Promoção do composite PERMANECE SUSPENSA.** Contatos passam (211-309 < 1576) e os sobreviventes correm a pace (VER 136s c/ tráfego), mas fora-de-pista (46-68%) e pós-largada (82-128) falham consistentemente. Os números verdes do B3.1 (223/0/0,17%) são uma realização única, não reproduzível — NÃO são fraude nem regressão do composite: são sorte de realização num sistema caótico + um modo de falha (grama profunda) que a realização verde não visitou.

### Artefatos R2
- `model_train/tracks_frozen/interlagos_v2.json` — CANÔNICO, sf_idx=729, sha256 164876196eb12174.
- `model_train/tracks_frozen/interlagos_sf729_v2.json` — variante de diagnóstico dos runs S5d (idêntica em sf_idx; manter por proveniência dos CSVs).
- CSVs: `race_diag_b31_v2.csv` (SF929 s0), `race_diag_b31_v2b_sf729.csv` (s0), `race_diag_b31_v2b_seed1.csv`, `race_diag_b31_v2b_seed2.csv`, `race_diag_v14all_frozen_sf729.csv` (gov vplan — confundido), `race_diag_v14all_frozen_gvon.csv` (A/B do caos).
- Loader: `load_track_frozen` json-autoritativo; `_env_adjust_sf`/`_F1EnvSFAdjust` removidos (mortos).

## v15 FASE R3 (2026-10-17) — fix do ABSORVEDOR (rejoin por BEARING): absorvedor MORTO; gate multi-realização VERMELHO por pilotagem

### M0 — hipótese única (verificada, CSVs R2): o rejoin tinha ALVO DE VALOR, não de DIREÇÃO
Fora do asfalto comandava esterço FIXO saturado (±0,79 rad); na grama o crawl
equilibra a v≈1,45-1,5 m/s e esterço constante = ÓRBITAS de ~3 m (heading varre
360°: sin(herr) −1,0→+1,0). PER oscilou lat 20,7-78,1 m por 500+s; NOR 861 m
de excursão. Recovery nunca re-engata (saída exige v≥3,0, inalcançável na grama).

### M1 — pré-registro 2026-10-17T12:54:27Z (dsh): árvore do fix + gate multi-seed

### F1 — fix (UMA variável: a LEI DE ESTERÇO do rejoin)
`steer = clip(REJOIN_BEARING_GAIN·wrap(bearing−heading), ±STEER_MAX)` ao ponto
de re-entrada (projeção + REJOIN_AHEAD_M=10 m na linha central). Quadro físico
(x, y, heading do mundo) — imune às convenções de sinal da obs. th 0,35, teto
8 m/s, recovery, gate e governor INALTERADOS.
**Teste sintético PASS** (tests/test_deep_rejoin.py): carro a 40 m, v=0, heading
tangencial → asfalto em **15,7 s** (v 8,8 ao re-entrar), v_max 31,9 m/s pós,
progresso 1808 m — vs. absorvedor R2 (500+s, nunca).

### V1/V2 — B3.1-v3 (3 seeds, frozen v2 SF729, composite, gov vplan, 600 s)
| seed | cc | pós-60s | fora | pilot/preso (ticks) | voltas | rolante | hesit | paradas |
|---|---|---|---|---|---|---|---|---|
| 0 | 251 | 68 | 43,3% | 1758 / 11244 | 10/10 | 322 s | 14 | 0 |
| 1 | 158 | 58 | 49,4% | 1812 / 13009 | 10/10 | 186 s | 36 | 0 |
| 2 | 267 | 64 | 52,8% | 2007 / 13818 | 10/10 | 191 s | 46 | 0 |

**Efeito ISOLADO do fix (mesma seed, R2→R3)**: absorvedor MORTO — excursões
profundas agora duram 6-33 s e o carro VOLTA (R2: 500+s e nunca; 22-30
episódios/carro, todos resolvidos). Contatos 309→251 / 211→158 / 271→267;
pós-largada 128→68 / 82→58 / 120→64 (todas ≤100 pela primeira vez);
voltas 7/10→10/10 (s0). Off% s0 melhora (60,3→43,3) mas s1/s2 pioram
(45,9→49,4; 49,5→52,8): carros que R2 absorvia agora VOLTAM ao tráfego.

**GATE (pré-registrado): VERMELHO.** PASS: contatos (mediana 251 < 1576),
pós-largada (64 ≤ 100), paradas (0), voltas (10/10). **FAIL: fora-pilotagem
(mediana 6,04% > 1,5%), rolante (190 s > 115), hesitações (14-46 > 3),
preso-por-janela (critério lat>20 atingido)**.

### Decomposição dirigida (árvore: vermelho → decompor → PARE)
- **Pilotagem REAL**: 243/253 (96%) das excursões começam SEM contato,
  v mediana 14 m/s, em TODOS os setores — o composite sai da pista ~2-3×/
  carro/volta em tráfego denso (R2 filtrava isso: os carros errantes eram
  absorvidos e os limpos corriam soltos). NÃO é pinball de contato (4%).
- **Hesitações**: paradas de v<0,5 m/s, duração mediana 0,6 s, 8/14 sob
  authority=policy — micro-freagens em tráfego, não encraves.
- **Preso-por-janela**: artefato do critério — janela 30 s com lat>20 conta
  excursões RECUPERADAS; o absorvedor R2 (permanente) tem 0 ocorrências em
  30 carro-seeds. **O critério "lat>20" como proxy de preso ficou obsoleto
  com o fix** — a próxima revisão do gate deve medir preso por "não-retorno
  em T s", não por profundidade.
- **Modo residual novo (1/30 car-seeds)**: VER s0 t 566-600 — após impacto
  42→0 m/s sem contato carro-carro, heading ≈90° à pista, o carro crawl para
  FORA a 1,7 m/s com bearing saturado correto e rotação ~30× mais lenta que
  a cinemática (v_x≈0 degenera o modelo lateral); estava RECUPERANDO no
  horizonte (lat 38,8→33,9 caindo, sin(herr) passando a negativo). Modo
  lento pós-spin, não permanente — caracterizar na próxima fase.

### Protocolo padrão (vigor a partir de R3)
- **Multi-realização**: gate de corrida = mediana de ≥3 seeds + critérios
  por-seed; NUNCA 1 realização (R2 provou: 0,17% vs 46-68% entre realizações
  do mesmo sistema).
- **Fonte da pista em todo log**: runners imprimem "[diag] pista FROZEN:
  <nome> | <n> wp | SF wp <idx>" (vigorante); evals de ENV não valem como
  gate (FastF1 offline = preset 240wp silencioso).
- Gates de ENV não colher (regra R2/R3); solo se avalia só por registro.

## v15 FASE R4 (2026-10-17) — A DOENÇA VISÍVEL decomposta: NÃO é pilotagem do residual; é contato sub-amostrado + ping-pong de re-entrada

### Pré-registro: 2026-10-17T14:04:42Z (árvore + critério PRESO NOVO: episódio
### off-track >60 s sem retorno — vale para TODOS os gates futuros).

### M0a — 755 excursões (3 seeds v3) = 272 RAÍZES + 483 ECOS (64%)
Eco = excursão ≤10 s após a anterior do mesmo carro (ping-pong de re-entrada).
**76% do TEMPO off-track são ecos** (6.601 s de 8.730); raízes duram mediana 6 s.
- **Raízes (272): 70% PROXY contato-não-amostrado** (|Δv|>2 m/s em ≤2 ticks s/
  contato registrado — 95 c/ brk≤0,3 = impulso puro; 95 c/ brk>0,3 = freio
  próprio forte). Pilots raiz: só 82 (30%) — residual manda 42 (51%),
  solo 39 (48%), nenhum ramo ≥60%.
- O "96% sem contato" do R3 era ARTEFATO: o contato 5 Hz perde empurrões
  curtos (regra 2 do R4 acertou). Excursão ≠ incidente: o R3 media ecos.
- Perfil dos ecos: v med 10 m/s (cap do rejoin), esterço saturado, reta
  (κ≈0), dur med 9 s, lat med 19 m — re-entra desalinhado, o solo corrige
  bruto, sai do outro lado.

### M0b — hesitações (96): modo freio-forte do residual em SÓ 12%
g med=0,00 e brk med=0,00 nelas; 66% ocorrem OFF-TRACK (crawl de re-entrada).
**Suspeita "residual OOD freio-forte": FALSIFICADA como dominante.**

### M0c — REJOIN-GERADOR: 68% dos contatos pós-60s envolvem carro
### re-entrado <10 s antes (limite da árvore: 30% — DISPARA)
O rejoin do R3 (bearing) traz o carro de volta SEM PERCEPÇÃO — re-entra
na frente/ao lado de carros a caminho → novo contato → novo fling → ecos.

### C1 — denominador de produto (mesmo instrumento, 3 seeds)
| run | cc | pós-60s | fora | voltas | rolante | preso>60s (carros) | hesit on-track |
|---|---|---|---|---|---|---|---|
| cego s0 | 904 | 370 | 33,8% | 10/10 | 148 s | 0 | 4 |
| cego s1 | 588 | 130 | 35,5% | 10/10 | 166 s | 0 | 6 |
| cego s2 | 946 | 406 | 38,1% | 10/10 | 164 s | 0 | 6 |
| comp s0 | 251 | 68 | 43,3% | 10/10 | 322 s | 0 | 12 |
| comp s1 | 158 | 58 | 49,4% | 10/10 | 186 s | 5 | 13 |
| comp s2 | 267 | 64 | 52,8% | 10/10 | 191 s | 4 | 8 |
**O composite tem 3-4× MENOS contatos que o v10-cego** (med 251 vs 904) e
pós-largada 5-6× menor (64 vs 370) — a percepção de tráfego FUNCIONA e é o
valor de produto. Mas paga com mais off-track (ping-pong) e pace pior.

### Modo WANDERER (novo, preso>60s no critério novo): 9/30 carro-seeds
Episódios 60-102 s, lat até 300 m, v 0,2-9 m/s, heading 25-90° errado,
esterço saturado, g=0. Mecanismo candidato (a caracterizar na R5): a
projeção global-argmin salta de BRAÇO da pista a >100 m → alvo de re-entrada
instável → carro vagueia; + rotação lenta a v_x≈0 (modo pós-spin do R3).

### ÁRVORE EXECUTADA (pré-registrada 14:04:42Z)
> **RETRATAÇÃO R5a**: o ramo 1 ("70% contato-não-amostrado") abaixo era
> baseado no PROXY |Δv|>2 m/s — o instrumento solver-side refutou: só 12-20%
> das raízes têm impulso 10 s antes. O proxy capturava frenagem própria +
> entrada na grama. Os ramos rejoin-gerador (68%) e o claim C1 também foram
> re-pinados na R5a (mediana 23%; sem vantagem em contatos). Ver FASE R5a.
1. **"contato-não-amostrado domina o proxy" (70% das raízes) → corrigir o
   INSTRUMENTO de contato antes de qualquer interpretação** — pré-requisito
   de R5: log de impulso/Δv por sub-step físico (o gate atual SUBCONTA).
2. **"rejoin-gerador ≥30%" (68%) → proposta: REJOIN COM PERCEPÇÃO (re-entrar
   só com gap) — 1 variável, R5 com pré-registro próprio.**
3. Ramos residual/solo/retreino: NÃO dispararam (51%/48% dos pilots raiz,
   minoria; freio-forte 12% das hesitações). Retreino NÃO proposto.

## v15 FASE R7a (2026-10-17) — VARIÂNCIA DE CORRIDA SEMEADA (opt-in) + veredicto do protocolo de execução

### Pré-registro 18:07:04Z: domínios D1 GRID / D2 COMPOSTO (cenário, nunca
### física — jitter físico RECUSADO por escopo); D3 clima inalterado.

### Implementação (opt-in, default OFF)
- `domain/racevar.py`: `variance_rng_from_seed(seed, domain)` no padrão do
  weather seeder (sha256 "<seed>//<domínio>", instância DEDICADA); parse;
  shuffled_order; assign_compounds (DISTRIBUIÇÃO preservada, só a atribuição
  muda). np.random global NUNCA consumidor.
- `--variance grid,compound` nos 2 runners (race_diagnostic + run_race);
  default off = corridas bit-reproduzíveis como antes.
- CSV v3.2/FONTE: variance, grid_order, compounds, weather_seed — cenário
  sorteado VISÍVEL no instrumento (lição FASE 1). Smoke-test do harness
  PASS antes de qualquer cadeia. Testes 4/4 (tests/test_racevar.py).

### VEREDICTO DE PROTOCOLO (endurecimento 1c)
- **PINNING FALHA**: 2 processos paralelos com OMP/OPENBLAS/MKL/NUMEXPR=1
  divergem ENTRE SI (linha 712, t=14,2 s) e do gêmeo sequencial — a
  contagem de threads NÃO é a causa; é a CONCORRÊNCIA de sims.
- Teste de carga e pinado-sequencial (bateria concluída):
  - **pinado-SEQUENCIAL ≡ R6-SEQ bit-idêntico** — env de threads é inócuo;
    e é também a prova de NÃO-INVASÃO (a): código R7a com --variance OFF é
    bit-idêntico ao R6 (zero mudança de física);
  - **sequencial SOB CARGA FP (4 burners numpy) ≡ R6-SEQ bit-idêntico** —
    carga de CPU NÃO perturba; o gatilho é especificamente SIMS PYBULLET
    CONCORRENTES (2 processos de simulação ativos), não threads nem load;
  - **variância ON, mesma seed ×2 → bit-idênticos** (cenário reproduzível).
- **VEREDICTO: SEQUENCIAL-PURO para sims** (um processo de simulação por
  vez; análise leve/IO em paralelo é seguro — provado). Pinning não
  autoriza paralelismo. Env OMP/BLAS opcional (inócuo).

### (c) DISPERSÃO — 10 seeds sequenciais, --variance grid,compound (PASS)
| seed | cc-v | pós-60s | fora% | rolante | preso>60s |
|---|---|---|---|---|---|
| 0 | 334 | 83 | 25,2 | 140 s | 0 |
| 1 | 323 | 69 | 30,5 | 154 s | 0 |
| 2 | 523 | 362 | 31,9 | 174 s | 0 |
| 3 | 946 | 184 | 30,4 | 154 s | 1 |
| 4 | 268 | 106 | 29,7 | 165 s | 0 |
| 5 | 272 | 16 | 25,8 | 139 s | 0 |
| 6 | 190 | 100 | 31,5 | 162 s | 0 |
| 7 | 756 | 234 | 29,5 | 164 s | 0 |
| 8 | 336 | 136 | 53,6 | 192 s | 15 |
| 9 | 203 | 96 | 46,6 | 154 s | 10 |
**Cenários de grid distintos: 10/10 — VARIÂNCIA MATERIAL ✓** (a variância
existe, é semeada e reproduzível por seed). Dispersão honesta: cc 190-946
(5×), fora 25-54%, pace 139-192 s. Medianas (baseline p/ o futuro gate
N≥10): cc 328, pós-60s 103, fora 30,4%, rolante 158 s, preso 0.
WANDERERS: seeds 8-9 sortearam 15/10 episódios >60 s — o modo PRECISA de
variância de cenário para aparecer (grids diferentes criam padrões de
contato diferentes); episódios disponíveis p/ a análise de persistência R5c.

### PROTOCOLO DE VARIÂNCIA v1 (vigora)
1. Domínios de CENÁRIO, semeados por sha256("<seed>//<domínio>"): grid,
   compound (distribuição preservada), clima (R6). Jitter físico: RECUSADO.
2. `--variance grid,compound` (opt-in; default OFF = bit-reproduzível).
3. Cenário sorteado VISÍVEL: linha FONTE + cabeçalho CSV v3.2.
4. Medição: SEQUENCIAL-PURO (1 sim por vez; análise leve paralela ok;
   threads inócuas). Bit-reprodutível por seed dentro do mesmo ambiente.
5. Gate N≥10: duas amostras por seed não valem — cada seed É uma
   realização completa (clima + cenário); N seeds = N realizações.

### LIMITAÇÕES
- Reprodutibilidade INTRA-ambiente: máquinas distintas, versões de
  BLAS/pybullet/drivers não são cobertas pela semeadura.
- A variância cobre CENÁRIO (grid/composto/clima); a dinâmica da largada
  permanece caótica (sensível ao cenário — é o que a dispersão mede).

### CHANGELOG (mudança de comportamento)
Com `--variance ON`, os MESMOS comandos produzem CENÁRIOS semeados por
seed (ordem de largada + compostos). Sem a flag: nada muda (bit-reproduzível
como R6 — prova de não-invasão).

## v15 FASE R7b (2026-10-17) — auditoria de física + BISEÇÃO B3.1: gap EXPLICADO; H2 CONFIRMADA (política de esterço, não fronteira física)

### Pré-registro 21:36:39Z (H1/H2 + predições P1-P4 + árvores antes dos dados)

### 0.1 — métrica COMPARÁVEL (zero runs)
Definição de fora idêntica em todas as eras (`|lat|>half_width`); recompute do
CSV legacy all-professor com classificador atual reproduz 0,03% exato → o gap
B3.1→R6 é DINÂMICA, não definição.

### 0.2 — BISEÇÃO DECISIVA (P4 confirmada): gap EXPLICADO
- **O commit 9099235 (FASE 4) NÃO RODA**: place_grid chama track.nearest_segment
  que não existia (crash registrado como um dos 4 do 9099235) — o working tree
  que mediu o B3.1 NUNCA FOI COMMITADO. Reconstrução mínima documentada (método
  portado verbatim da FASE R + frozen exportado como CSV + SF729 1-linha).
- **Código FASE-4 no instrumento canônico (frozen 1131wp, SF729, 600s): 40,55%
  FORA** (vs R6 atual: 29,3% — o código atual é MELHOR; o rejoin bearing da R3
  melhorou o campo). O 0,17% do B3.1 é inalcançável pela própria era no
  instrumento canônico.
- **VEREDICTO (árvore: culpado canônico pretendido): B3.1 rotulado REGIME
  PRÉ-CANÔNICO.** O gap 223→511/0,17%→29,3% = instrumento live→frozen + clima
  não semeado + contenção não controlada na era; NÃO há regressão pós-R2.
  Nenhuma correção proposta (não há culpado não-intencional).

### 1.1/1.2 — proveniência e tabela κ
- Professor usa o MESMO VelocityProfile (grip 0,788 / sf 0,80, sf adaptativo
  interno) — mas alveja 0,93×v_plan (speed_margin) e é PURE-PURSUIT (esterço
  por geometria de perseguição — feedback que absorve o understeer do físico).
- Fronteira skidpad (physics_frontier.json, real): a 16 m/s NENHUM raio testado
  segura; v_allow nas bandas quentes (26-54 m/s) está FORA do domínio medido —
  o perfil só é honesto porque o grip_mult 0,788 foi CALIBRADO contra o
  entregável do físico (understeer sistemático medido: R_eff/R_target =
  1,45-1,6× em círculo suave).

### 1.3 — 907 saídas pilots (10 CSVs R7a, zero runs novos)
- **P2 CONFIRMADA**: slip no tick de saída mediana 16,8°; 65% >10° — o carro
  JÁ está deslizando quando sai (assinatura de CAÇA, não de estouro).
- **P3 CONFIRMADA (H2)**: só 18% (27/150 computáveis) excedem a fronteira;
  a_lat atingida mediana 3,9-5 m/s² vs ~10,4 disponíveis.
- P1 PARCIAL: picos em κ<0,005 (322 — weave em reta, slip +16°, 0,72×v_allow)
  E 0,008-0,015 (353 — entradas de curva, slip −8°) — 74% das saídas.
- **Comando de esterço mediano nas saídas: 0,72 rad vs necessidade cinemática
  0,030 rad = 24×** — guinada sem curvatura de caminho (a_lat baixa + slip alto).

### 2 — SCRIPTED (sem policy/tráfego; protocolo do calibration script)
Hotspot κ=0,010 (R=100) e controle κ=0,005 (R=200), v = {v_allow, 0,81×,
0,93×prof, 0,72×}: **A FÍSICA SEGURA O CÍRCULO EM TODAS** — misalign 0,3°,
lat_proxy ≈0, inclusive a v_allow cheio. **H1 REFUTADA nos estados suaves.**
(R_eff/R_target = 1,41-1,61: understeer sistemático estável — propriedade de
calibração, não instabilidade.)

### 3 — VEREDITO POR BANDA (H1/H2/misto)
| banda κ | n | veredito |
|---|---|---|
| <0,005 (weave reta) | 322 | H2 — política oscila/caça (slip 16°, a_lat 4,9) |
| 0,008-0,015 (entrada curva) | 353 | H2 — comando insuficiente/saturado p/ understeer 1,45× |
| 0,015-0,03 | 87 | H2 majoritária (slip baixo, dentro da fronteira) |
| 0,03-0,05 | 76 | misto (0,91×v_allow, slip 8°) |
| ≥0,05 / excedentes | ~37 | minoria; estouro de fronteira real (18% dos computáveis) |
**H2 CONFIRMADA no agregado**: a física entrega círculos estáveis com entrada
suave; as saídas vêm de COMANDOS de esterço da política ~24× a necessidade
cinemática, gerando guinada+slip sem curvatura de caminho, a 0,72-0,9×v_allow.

### PROPOSTAS (NÃO implementadas — aprovação)
1. **STEER-GOVERNOR (race-layer, 1 variável)**: cap do esterço comandado em
   k_comp×atan(L·κ_preview) (+ banda p/ correção de heading), espelhando o
   padrão do governor de velocidade e do rejoin bearing (R3). Alvo: as 74% das
   saídas das bandas dominantes. Pré-registro próprio + skidpad sintético
   (comando exagerado → cap → segura?) + re-gate multi-seed.
2. Alternativa a retreino (só com aprovação): DAgger de estados de
   weave/slide — o policy nunca viu dados de RECUPERAÇÃO de deslize.
3. Documentação: understeer 1,45-1,6× como propriedade do físico (o professor
   absorve por feedback; imitador não absorve) — nota de auditoria.

## v15 FASE R12-PASSO1-2 (2026-10-17) — retreino executado; canárias INCONCLUSIVAS por INSTRUMENTO; PARE no ponto de decisão

### PASSO 0 (fechamentos, commitados no prereg b1a852c)
0.A Grade de sensibilidade COMPLETA (ld 0,48/0,60/0,72 × limiar 0,10/0,15/0,20):
83% (ld−20%, 0,10) → 38% (ld+20%, 0,20); ponto pinado (0,60/0,15) = 51% —
vizinhança NÃO inverte; GO de pé. 0.B Recount CSV: A s8=6/s9=8 confirmam;
B s9=8 (episódio NOR RECUP-OFF termina com a corrida; stoplog só registra
LIBERADO) — instrumento canônico de paradas = CSV; 100% RECUP-OFF nos 36.

### PASSO 1 — retreino (log commitado a385c18 + a seguir)
Dataset: 13.581 estados das 471 janelas GO + 20.000 replay 2:1 (r_target=
δ_prof−|δ|; TRÁFEGO-YIELD fora; motor pure-pursuit validado corr 0,863).
r12 (6d): corr 0,957 — mas INCOMPATÍVEL com a interface 16d do runner
(12 tráfego + 4 aux). r12b (16d, mesmas janelas com 10 zeros nos slots de
tráfego + v/κ/prev_st): **corr 0,936, replay |pred| 0,021** (disciplina em
pilotagem normal melhor que o r2). PERDA DE INFO documentada: |slip| e
sin/cos(herr) não existem na interface 16d — só v, κ, prev_st entram.
Solo congelado por construção (BC no residual; g=0 em solo).

### PASSO 2 — canárias H5: INCONCLUSIVAS POR INSTRUMENTO (lição R6 re-capturada)
A canária baseline (r2 — o residual VIVO do braço A, 223-contato-ex-VD)
também dá **0/3** no env. Causa: FastF1 offline → env cai no PRESET 240wp
(SF 109) — pista em que o v10 NUNCA foi treinado; o carro anda (76 m/s,
848 m em 160 steps) mas SAI da pista do preset no hairpin dele (t=341 s,
lat 8,1). O mesmo PROJECT_STATE já dizia desde R6: "gates de ENV não
colher agora — preset 240wp silencioso". As canárias de ENV não são
viáveis até FastF1 voltar ou o env aceitar a pista frozen.
**PONTO DE DECISÃO EXECUTADO (árvore do prereg: canárias quebram → não
prosseguir): o PILOTO {0,8,9} NÃO foi rodado.** Sem canárias, sem corrida —
o prereg manda parar. A alternativa honesta (canárias via race_diagnostic
solo no frozen) NÃO existe como comando e criá-la seria instrumento novo
não-preregistrado. PARE registrado.

### FASE R13-FECHAMENTO (2026-10-18) — apêndice auditável, erratas E1-E5, CSV v3.3, docs finais

**ERRATAS (auditáveis, zero runs):**
- E4 (manchete): ratio cc_B/cc_A real = **1,5× a 3,5×** (mediana 2,2×; Δ −479
  a −994) — a manchete "3-13×" confundia razão com recíproco; CORRIGIDA.
- E1: cc-fail por seed = {s10:601, s11:600, s12:613, s13:781, s19:877}
  (range 600-877 confirmado).
- E2: contato×carro-fora POR SEED (denominador = amostras de contato):
  28-44% (s16 é o menor com 28%; o texto "39-44%" era só dos cc-fail).
- E3: denominadores de hesit on-track: s11=21, s12=16, s13=14, s14=16,
  s15=20 — as classes somam o total (REJOIN+TRAF+CRAWL+OUTRO = total ✓).
- E5: adversos do braço A 0-9 pela regra w_trans MECÂNICA = **{2, 8, 9}
  (n=3)** — IGUAL ao n usado na derivação do prereg; nenhum quantil muda;
  vereditos por seed inalterados linha a linha.
- Identity smoke dos 20 runs: ator/gov/pista-sha/SF/CSV ✓ em todos; GAP
  documentado: sha do residual só logava com --residual-override (braço A
  implícito) — CORRIGIDO no v3.3 (sha universal).

**PASSO 2 — CSV v3.3 ADITIVO (commits 0c5892c + 97f3ad9):** colunas
res_0..res_15 por carro-tick (o 16d EXATO que o residual consome — rota 2
do backlog agora tem tráfego VIVO offline), sha do residual baseline logado
SEMPRE, kill-switch RACE_DIAG_NO_RES16. **Bit-identidade PASS: 0 divergências
em 52 colunas canônicas × 600 ticks (mesma seed, logging on vs off).** Suite
33+1 skip verde. ZERO mudança de comportamento.

## PASSO 4 — DOSSIÊ DA ALAVANCA (zero runs; 20 corridas braço A; prereg leve commitado)
- **(i)** 4.356 excursões; **18%** terminam com contato do dono ≤30s pós-reentrada.
- **(ii)** reentrada→primeiro contato: **mediana 8,7s** (p25 2,5s; p75 19,4s;
  35% dentro de 5s) — a LATÊNCIA ÚTIL de percepção de um rejoin-com-gap é
  ~2-9s (mediana): um gap-checker precisa olhar ~10s à frente.
- **(iii)** já medido (E2): 28-44% das amostras de contato com carro fora —
  retorno é a causa dominante dos cc-fail.
- **(iv)** reentrada ocorre a ~8 m/s (teto do rejoin); voltar a 15 m/s leva
  mediana 1,2s — o carro recupera pace RÁPIDO, mas o contato chega em ~8,7s:
  o retorno ao fluxo ANTES do pace é a janela de risco, não a lentidão.
- **CONCLUSÃO do dossiê**: a alavanca "rejoin com percepção" tem alvo
  quantificado: 18% das excursões geram o contato; a janela de decisão é
  ~10s; o carro reentra rápido demais para o gap que encontra. Um
  gap-checker que adie a reentrada até um buraco ≥X m (medir X da
  distribuição de gaps no corpus) atacaria ~35% dos contatos-pós-rejoin
  (os que chegam em ≤5s) e parte dos de 5-19s.

## DECLARAÇÃO FINAL DE PRODUTO (canônica — texto da revisão, colado verbatim)
> **Race default = v10-cego (dagger_actor_best.keras, obs edge, gov vplan).**
> O composite (v10 solo congelado + residual r2) NÃO é promovido: falhou o
> gate re-ancorado out-of-sample (R13: 3/10; adverso 0/4) nas dimensões
> contato (39-44% das amostras de contato com carro fora — retorno de
> excursões) e hesitação (classe REJOIN-DIP dominante), apesar de o critério
> de pista (fora) passar em TODAS as seeds. Permanece research-grade com
> vantagem de segurança CONSISTENTE e documentada: 1,5-3,5× menos contatos
> que o v10-cego em 10/10 seeds out-of-sample (Δcc −479 a −994), pós-60s
> sempre menor, e clima adverso sobrevivível (s8: 336 vs 5138 contatos).
> A cadeia causal única do produto: excursões race-speed da política →
> contatos no retorno → hesitação REJOIN-DIP → paradas RECUP-OFF. A alavanca
> futura é percepção de tráfego no RETORNO (rejoin com gap) ou weave/slide
> com tráfego VIVO (rota 2 — pré-condição de dados agora disponível via
> CSV v3.3).

## CICLO ALAVANCA — rejoin-gap-check (2026-10-18, feat/rejoin-gap-check): GATE TODOS-PASS

Derivado do dossiê R13 (18% das excursões -> contato <=30s; mediana
reentrada->contato 8,7s). P0: tabela X mecânica (20m = cotovelo: 54%
perigosas bloqueadas, espera 0,6s); 1ª excursão 10/10 na largada.
P1 prereg 1883d6d: reconciliação 4.356 (A) vs 1.808 (B); X=20m por
critério min{>=50% E espera <=1s}; hold crawl 4m/s + T_max 10s
fallback; ISENÇÃO de paradas decidida ANTES; âncoras históricas B:
taxa mediana 0,323 / p25 0,307 / rolante 136s. P2: UMA variável na
camada rejoin; testes 4/4; smoke instrumento VIVO (490 hold ticks,
rejoin_gap 10,5%, fora 22,6->12,8% s0). P3 GATE (seeds 20-29, secos,
600s, frozen, cego+vplan, --variance grid,compound, --rejoin-gap 20):
**TODOS OS 7 CRITÉRIOS PASS** — taxa mediana 0,054 (vs 0,323 histórico,
−83%); pior 0,133 (<=0,323); 10/10 voltas; 0 paradas; 0 wanderers;
rolante med 136s (= histórico); fora 10,4-14,8% (MELHOR que o range
histórico 21-31,6 em TODAS as seeds — o crawl na borda evita
re-excursões em cascata, reportado); hold 60-132s/run; fallback 0.
**ALAVANCA VIVA NO SECO.** Adversos: sessão própria. Adoção: revisão.
> **ERRATA (SESSÃO ADVERSA, abaixo):** o gate seco mediu o FLAG como
> implementado — que age TAMBÉM na largada (vazamento de engajamento) e com
> telemetria de hold fora de fase. Atribuição de mecanismo confundida.

## CICLO ALAVANCA — SESSÃO ADVERSA (2026-10-18): PARE POR INSTRUMENTO (0-c VAZAMENTO)
Prereg 3331ee8 (recontagem + veredito pareado + leak-check commitados ANTES
de qualquer run) + recontagem commitada 120081e (instrumento `stats()` do
gate seco sobre o braço cego 0-9 — âncoras pareadas por seed):
| seed | clima | taxa | fora% | rolante | n_comp | paradas | wand |
|---|---|---|---|---|---|---|---|
| 2 | v2 DRY→CLOUDY | 0,277 | 23,0 | 134 | 10 | 0 | 0 |
| 8 | v2 DRY→CLOUDY→DAMP | 0,444 | 59,4 | 150 | 10 | 14 | 17 |
| 9 | v3 DRY→DAMP | 0,348 | 46,9 | 147 | 10 | 8 | 13 |

Execução (2 corridas, seriais): smoke s0 base + s0 gap.
- **0-b smoke: PASS (wiring VIVO)** — CSVs divergem; authority `rejoin_gap`
  3330 ticks; identity `rejoin_gap=20.0` ✓.
- **0-c PAIR: FAIL — VAZAMENTO**: 1ª divergência no **tick 0** (SAI, t=0,0:
  th 0,928→0,35 crawl, steer −0,438→−0,376) ANTES da 1ª reentrada (tick 74).
  No grid, 8/10 carros (4 fileiras traseiras, gaps 9 m < X=20) já com
  authority `rejoin_gap` no tick 0.
- **0-c SELF (retroativo, 10 secos 20-29): 10/10 FAIL** — hold@tick 0 em
  TODOS (50 hold-ticks t<10 s por run; 1ªs reentradas só a partir de
  tick 496). O gate seco carregava o MESMO vazamento.
- **Bônus excursão: FAIL** — 1ª excursão do tratamento (HAM, 32,6 s) ≠
  histórica (RUS, 4,2 s): a LARGADA MUDOU (o hold elimina a excursão de
  largada 10/10 do dossiê — a "alavanca de LARGADA" foi implementada
  ACIDENTALMENTE dentro da flag de rejoin).
- **Drift (report-only): 0/30000 divergências em 49 colunas comuns** — base
  fresco = histórico R10 bit-idêntico: código atual com flag OFF = era R10;
  TODO o efeito do tratamento vem da flag (o pareamento é válido).
- **CAUSA RAIZ 1 (engajamento, código 7414fc7:845-853)**: o gate exige só
  `flag>0 + not offtrack + near_edge` — SEM requisito de estado de rejoin
  (spec do prereg ALAVANCA §3: "aplica-se DENTRO do estado rejoin");
  `near_edge = lat(assinado) < 1,5×meia-largura` ≈ sempre true on-track.
- **CAUSA RAIZ 2 (telemetria)**: `rejoin_gap_hold` NÃO coincide com as ações
  (SAI crawl@0 com hold=0; 531 flags concentrados em 1 carro/run) —
  instrumento de hold não-confiável em TODOS os CSVs de tratamento,
  inclusive os 10 do gate seco (os "hold 60-132 s/run" reportados são
  suspeitos). Encaminhamento da fase (qual chamada escreve _gap_hold vs
  qual escreve a linha) fica para o reparo.
- **ERRATA da INTERPRETAÇÃO do GATE SECO (veredito 869cd65)**: as MEDIÇÕES
  são válidas (isolamento bit-a-bit provado pelo drift-check), mas o FLAG
  medido NÃO é a alavanca preregada — é um híbrido launch-pacing + rejoin.
  A queda de fora% (21-31 → 10-15) e da taxa (0,323 → 0,054) têm atribuição
  de mecanismo CONFOUNDIDA: a excursão de largada era a maior fonte única.
  O veredito "alavanca VIVA no seco" fica SUSPENSO até re-validação com o
  instrumento reparado.
- **0-d/0-e: NÃO EXECUTADOS** (PARE por instrumento; SEM re-pin, SEM re-run).
  Runs desta sessão: 2 (o par do smoke). Seeds {2,8,9} NÃO consumidas —
  continuam disponíveis para o gate com o instrumento consertado; 30-39
  permanecem virgem-pool.
- Próximo passo (revisão): reparo do instrumento (engajamento rejoin-only +
  telemetria de hold em fase com ações) → re-smoke → re-gate seco (pool novo
  ou re-pin explícito) → só então adverso. Artefatos:
  `experiments/diag-alv-adverso/` (smoke + recontagem), leak-check
  `scripts/lever_leak_check.py` (commitado ANTES — foi ele que pegou o
  vazamento que o gate seco inteiro não viu).

## CICLO ALAVANCA — REPARO + RE-VALIDAÇÃO (2026-10-18, feat/rejoin-gap-check): B PASS, C FAIL → PARE
Amenda `ead15a7` commitada ANTES de qualquer run (orçamento 22 runs; usados 12).

### A — REPARO (A.0-A.3) + SMOKE B: TODAS AS 3 CONDIÇÕES PASS
- **A.0**: suite 25F/280P/2S (skips: composite_parity=ARTEFATO DE COLEÇÃO —
  paridade formal coberta por test_residual_numpy_equals_keras; v2v4=checkpoints
  ausentes); ordem de commits confirmada; **taxas 10-19 REPRODUZIDAS** pelo
  script do prereg 1883d6d sobre `race_diag_r13_b_s1[0-9]`:
  [0,306;0,328;0,317;0,441;0,333;0,406;0,267;0,310;0,300;0,350] → med 0,323/
  p25 0,307/máx 0,441 (s10 histórico: par 4/wand 4 — o seed WET).
- **A.1 (3 fixes)**: (i) ENGate — engate SÓ na transição off→on
  (`_was_offtrack`); correção do diagnóstico: `drv_lat` JÁ é distância
  absoluta (offtrack/near_edge sempre foram bilaterais) — o vazamento vinha
  da ausência do requisito de excursão; (ii) KEYING `drivers[i]` — o bloco
  usava `drv` STALE do loop de observações (= último driver): UM estado
  compartilhado por todos os carros + flags só do último (a causa de "SAI
  crawl@0 com hold=0"); (iii) telemetria todo tick por carro EM FASE; fb =
  transição 0→1 (a contagem antiga era INVISÍVEL — o pop de expiração apagava
  o estado antes da leitura).
- **A.2**: t1 (largada não engata) / t2 (retorno com gap 9 m segura, crawl,
  authority rejoin_gap) / t3 (flag na chave do HOLDER, nada em driver alheio)
  — harness real (pista frozen + pybullet + pesos v10); suite **25F/283P/2S**.
- **A.3**: âncoras inalteradas; pool seco NOVO 30-39; {2,8,9} poupados;
  40-49 reservado; emenda GUARD-P/W ≤hist no veredito adverso; modo `phase`
  no leak-check.
- **B SMOKE (2 runs, seed 0 seco)**: (1) 1ª divergência tick 90 ≥ 1ª
  reentrada tick 74 **E == 1º hold** (o hold é o único canal); (2) fase: 597
  hold ticks em 9 carros, 0 violações authority⟺hold, fb 5 eventos VISÍVEL;
  (3) **1ª excursão BIT-IDÊNTICA à histórica (RUS, 4,2 s, 2702,685 m) — a
  largada NÃO muda**; drift base≡hist 0/30000.

### C — RE-GATE SECO (seeds 30-39, 10 runs seriais): **FAIL → PARE**
| seed | clima | taxa | par | wand | rol | off% | hold s | fb |
|---|---|---|---|---|---|---|---|---|
| 30 | DRY→DAMP(v5) | 0,205 | **7** | **4** | 133 | 23,1 | 206 | 7 |
| 31 | seco | 0,102 | 0 | 0 | 134 | 17,3 | 239 | 12 |
| 32 | seco | 0,208 | 0 | 0 | 133 | 17,8 | 224 | 9 |
| 33 | DRY→CLOUDY | 0,098 | 0 | 0 | 134 | 17,8 | 241 | 9 |
| 34 | seco | 0,129 | 0 | 0 | 134 | 17,8 | 248 | **16** |
| 35 | seco | 0,113 | 0 | 0 | 132 | 20,5 | 101 | 9 |
| 36 | DRY→CLOUDY | 0,158 | 0 | 0 | 134 | 18,2 | 234 | 12 |
| 37 | DRY→DAMP(v5) | 0,220 | **4** | **6** | 138 | 26,3 | 186 | 6 |
| 38 | seco | 0,152 | 0 | 0 | 134 | 17,6 | 221 | 12 |
| 39 | DRY→CLOUDY(v2) | 0,085 | 0 | 0 | 134 | 19,8 | 138 | 10 |

- **PASS**: PASS-P mediana 0,141 ≤ 0,307 | PASS-R máx 0,220 ≤ 0,323 |
  GUARD-V 10/10 | GUARD-L 133-138 ≤ 141 | GUARD-F 17,3-26,3 ≤ 33,6.
- **FAIL**: GUARD-P/GUARD-W absolutos quebrados pelas DUAS seeds DAMP (s30,
  s37); **fb re-medido: 6-16 eventos/run (s34 SECO = 16 > 10 = 2º gatilho de
  PARE do §C)** — o fallback T_max é exercitado DE VERDADE (no gate
  contaminado fb era mascarado=0).
- **EXPECTATION RESET CONFIRMADO**: fora 17,3-26,3% (vs 10,4-14,8 do
  contaminado; vs 21,0-31,6 histórico) — o efeito-largada SUMIU com o
  reparo; a alavanca rejoin-only fica DENTRO do range histórico.
  **O mecanismo de taxa é REAL: mediana 0,141 = −56% vs 0,323, PERTO do teto
  teórico do prereg §4 (≈0,149 de 54% bloqueadas)** — correção de atribuição,
  não regressão.
- **Diagnóstico dos guards**: paradas/wanderers só nas seeds DRY→DAMP
  (t=544-574 s, fase úmida, liberadas por CONTATO — o padrão RECUP-OFF/clima
  do produto). O MESMO fenômeno existe no braço cego HISTÓRICO (s10 WET: 4/4;
  s8: 14/17; s9: 8/13) — paradas em clima úmido são do CLIMA, não da alavanca.
  **CAVEAT de pool (omissão da amenda)**: 30-39 NÃO foi pré-verificado como
  seco — 5/10 com transições (30/37 DAMP; 33/36/39 CLOUDY); os guards
  absolutos presumiam pool seco (como 20-29). SEM re-pin, SEM re-run — o
  FAIL mecânico fica; o pool 40-49 (reservado) permitiria um gate seco-seco
  SE a revisão quiser (decisão dela, com re-pin explícito).
- **Veredito C (mecânico, prereg REPARO §C)**: FAIL → PARE. **Alavanca
  rejoin-only = research-grade documentada**: reduz a taxa de perigosas
  −56% com pace preservado, mas NÃO zera paradas/wanderers em realizações
  DAMP e o fallback dispara 6-16×/run (em tráfego denso o buraco ≥20 m não
  chega em 10 s — dado NOVO, antes invisível). **Dossiê LARGADA vira
  candidato prioritário** (ramo do prereg).
- **D/E NÃO executados** (PAREs em C). Runs 12/22 (2 B + 10 C);
  {2,8,9} CONTINUAM poupadas; 30-39 consumidos; 40-49 reservado.

## CICLO ALAVANCA — REVALIDAÇÃO (2026-10-19): C' TODOS-PASS no seco; D FAIL no adverso → alavanca OPT-IN (viva no seco, adverso reprovado)
Amenda 4308287 commitada ANTES dos 16 runs; NENHUM código da alavanca mudou
(smoke B/ead15a7 = validação permanente do instrumento).

### P0 — WEATHER SCAN offline (validado 30/30; zero runs)
Mecânica exata derivada do código: transições avaliadas por VOLTA COMPLETADA
POR CARRO (10 draws/onda, labels 2-5; o race_diagnostic não passa pelo
engine.run → SEM draw de largada). **Teorema do prefixo** validado: in-race ⊂
scan (s9/s10 = prefixos — carros encravados truncam o stream; 28 exatos).
**40-49 declarada: 1/10 DAMP (s42 v5 DRY→DAMP)**, 3 CLOUDY-only (43/46/48),
6 sem transições — guardrail >5/10 PASS. Caveat: o GUI (engine.run) consome
1 draw a mais na largada → clima GUI ≠ headless na mesma seed (gates são
headless-canônicos).

### P1 — atribuição CONFIRMADA (predição pré-registrada; 2 runs)
Base fresca SEM flag: s30 par 7/wand 5; s37 par 9/wand 6 — vs tratamento
7/4 e 4/6. **A base para/wandera IGUAL ou MAIS que o tratamento**: as
paradas em DAMP são do CLIMA; a alavanca REDUZ paradas na s37 (9→4) e corta
a taxa mesmo em úmido (0,317→0,205; 0,277→0,220). Condição de PARE (0/0)
não disparou.

### C' — RE-GATE SECO (seeds 40-49, clima declarado pelo scan): TODOS OS 8 CRITÉRIOS PASS
| seed | clima | taxa | par | wand | rol | off% | hold s | fb |
|---|---|---|---|---|---|---|---|---|
| 40 | SECA | 0,274 | 0 | 0 | 135 | 18,9 | 285 | 14 |
| 41 | SECA | 0,187 | 0 | 0 | 134 | 18,3 | 250 | 9 |
| 42 | DAMP | 0,156 | 2 | 8 | 135 | 25,4 | 228 | 13 |
| 43 | SECA | 0,176 | 0 | 0 | 135 | 19,0 | 194 | 5 |
| 44 | SECA | 0,169 | 0 | 0 | 133 | 17,4 | 249 | 10 |
| 45 | SECA | 0,183 | 0 | 0 | 136 | 21,2 | 172 | 10 |
| 46 | SECA | 0,160 | 0 | 0 | 135 | 18,2 | 190 | 11 |
| 47 | SECA | 0,196 | 0 | 0 | 134 | 19,0 | 191 | 5 |
| 48 | SECA | 0,179 | 0 | 0 | 135 | 19,6 | 239 | 8 |
| 49 | SECA | 0,198 | 0 | 0 | 136 | 21,6 | 254 | 9 |

- PASS-P mediana 0,181 ≤ 0,307 | PASS-R máx 0,274 ≤ 0,323 | GUARD-V 10/10
  | GUARD-L 135 ≤ 141 | GUARD-F 17,4-25,4 ≤ 33,6 | **GUARD-P/W: 9 secas
  0/0 absolutos (espelho do histórico 9/9) + s42 DAMP ≤ base fresca
  (par 2≤4, wand 8≤8)** | SELF leak-check 10/10 PASS. Identity 10/10
  (rejoin_gap=20.0).
- fb report-only: 5-14/run; >10 em s40/s42/s46 → **diagnóstico obrigatório:
  em tráfego denso o buraco ≥20 m não chega dentro da janela de 10 s — o
  fallback T_max dispara por construção (cobertura parcial, teto 54%)**.

### D — GATE ADVERSO PAREADO ({2,8,9}): FAIL → PARE
| seed | taxa | par | wand | rolante | off% | veredito |
|---|---|---|---|---|---|---|
| 2 | 0,277→0,190 | 0→0 | 0→0 | 134→137 | 23,0→19,0 | **PASS** |
| 8 | 0,444→0,241 | 14→**15** | 17→16 | 150→**237** | 59,4→50,2 | **FAIL** (GUARD-P, GUARD-L) |
| 9 | 0,348→0,231 | 8→**12** | 13→13 | 147→143 | 46,9→42,3 | **FAIL** (GUARD-P) |

- O mecanismo de taxa FUNCIONA no adverso (−31% a −46%) e o fora% fica
  ABAIXO do histórico em 3/3 — mas em DAMP o hold na borda CUSTA: paradas
  ACIMA do cego histórico (s8 +1, s9 +4) e na s8 o rolante explode
  (237 s — espera em crawl no caos úmido). SEM re-pin, SEM re-run.
- **E NÃO executado** (condicionado a D TODOS-PASS).

### ESTADO FINAL DO CICLO
- **Alavanca rejoin-gap-check X=20: VIVA no seco (C' 40-49 TODOS-PASS),
  REPROVADA no adverso (D {2,8,9} FAIL por paradas/rolante em DAMP)** —
  permanece OPT-IN research-grade; adoção = revisão (default seco-só
  exigiria a flag depender do clima — decisão de produto).
- Runs 16/23 (2 P1 + 11 C' + 3 D). Pools: 40-49 consumidos (C');
  {2,8,9} consumidas (D); **50-59 = próximo pool virgem** (dossiê LARGADA).
- Fila para a revisão: (a) ADOÇÃO da alavanca (seco-só ou opt-in
  documentado); (b) dossiê LARGADA (prereg próprio, pool 50-59, baseline =
  config adotada — a 1ª excursão 10/10 na largada continua a maior fonte
  única); (c) fb frequente (5-14/run) = dado novo: janela/T_max a
  re-derivar SE a alavanca for adiada; (d) caveat GUI↔headless do clima.

## ALAVANCA REJOIN-GAP X=20 — DISPOSIÇÃO FINAL (canônico; rulings REVALIDA-0-review)
- **OPT-IN** via flag `--rejoin-gap 20` no race_diagnostic (default 0 = off).
  SEM flip de default; SEM flag clima-dependente; SEM re-pin do regime
  canônico (v10-cego+vplan = race default).
- **Validada NO SECO** (re-gate C' seeds 40-49, instrumento reparado ead15a7):
  8/8 critérios — taxa mediana 0,181 = −44% vs 0,323 histórico; 9 secas
  par/wand 0/0 absolutos; s42 DAMP ≤ base fresca.
- **REPROVADA NO ADVERSO** (gate D {2,8,9} pareado): paradas acima do cego
  histórico em DAMP (s8 15>14; s9 12>8) e rolante 237 s vs 155 na s8 —
  **recomendada SOMENTE com pista seca declarada**.
- **NUNCA acoplar a flag ao clima no runner**: o clima do GUI ≠ headless
  para a mesma seed (o engine.run do GUI consome 1 draw a mais do rng do
  clima — ver weather_scan.py).
- **Fallback T_max report-only por construção**: o buraco ≥20 m não chega em
  10 s em tráfego denso (5-14 eventos/run; teto de cobertura 54% do prereg).
- **Re-derivação de janela/T_max = PRÉ-CONDIÇÃO de qualquer promoção futura**
  (não um ciclo por si).

## CICLO LARGADA — FASE 0: ANATOMIA OFFLINE (2026-10-19): P-A/P-B 20/20 PASS; P-C FAIL → PARE (premissa cai)
Zero corridas. Amends: f801d09 (disposição final) → 071bc37 (prereg da
anatomia, ANTES do script; P-B EMENDADO p/ s∈[2650,2950] com âncoras
citadas — RUS 4,2 s @ 2702,685 do smoke B e cluster 2698-2814 mediana 2757;
a região literal do prompt [550,850] deu 0/20, reportada).
- **Fechamento de registro V**: V-1 GUARD-L do C' confirmado **135,0**
  (mediana das medianas; máx 136) — SEM errata (veredito imune, ≤141);
  V-2 GUARD-V do D 3/3 (10=10 por seed); V-3 SELF do D 3/3 quantificado
  (margem mínima 1º hold − 1ª reentrada = **0 ticks** — engaje exato na
  reentrada; 9-10 carros/run; 0 violações).
- **SELF-checks 3/3 PASS** (10 taxas exatas + recontagem 120081e + RUS
  4,2/2702,685). Instrumento: `scripts/largada_anatomy.py`; âncoras
  `experiments/largada_anatomia_cego_s0_19.csv` (20 runs cegos) e
  `largada_anexo_CONTAMINADO.csv` (11, rotulado).
- **ANATOMIA (braço cego 0-19)**: 1ª excursão 20/20 em W (t 4,2-8,4 s) E
  20/20 na 1ª curva (s 2699,7-2814,0 — entrada do Senna S, pós-SF 2655);
  **taxonomia 20/20 CONTATO-ADJ** (contato do dono em ±2 s); 12-23 pares de
  contato por run em W, **primeiros contatos JÁ NO GRID** (t 1,2-1,4 s, s
  2618-2656); v do campo: 14,5 (t=2) → 28,7 (t=4) → 10-17 (t=8) m/s.
- **P-C FAIL: share_largada mediana 0,074** (range 0,021-0,115; décadas
  0,072/0,075) vs ≥0,20 pinado — **a janela de largada detém só ~7% do
  TEMPO fora, não 20-50% → PARE: a premissa "maior fonte única" (em
  tempo-fora) CAI; re-prioritização com a revisão ANTES de qualquer L-1.**
- **RE-ATRIBUIÇÃO (registrada)**: a derivação original (contaminado 10-15%
  fora vs histórico 17-26% ⇒ largada ≈ 1/4-1/2 do fora) confundia o
  efeito-largada LOCAL com a CASCATA inteira (o híbrido contaminado também
  carregava o bug de keying) — a diferença de fora% (−7-11 pp) vem do
  desenvolvimento completo da corrida, não da janela W. O que PERMANECE:
  a largada é um evento de CONTATO concentrado e localizado (grid + Senna
  S), 100% CONTATO-ADJ; o teto de um pacing perfeito sobre o tempo-fora é
  ~7% + qualquer cascata que previna (valor INDETERMINADO nos dados
  atuais — confundido com o keying do híbrido).
- **ANEXO CONTAMINADO (insumo de design)**: 10/10 runs com hold de largada
  → 1ª excursão empurrada para **t=32,6 s** (modo exato, 10/10) e fora
  10,4-14,8% — o launch-hold atrasa a primeira excursão; a atribuição do
  resto da diferença segue confundida.
- Pools intactos (50-59 virgens); suite inalterada. Proposta L-1 (pacing)
  fica NO RELATÓRIO, condicionada à re-prioritização da revisão.

### ERRATAS LARGADA-1 0-a (rulings LARGADA-0-review; doc-only)
- **E1**: a leitura da era REPARO de que os "fora 10,4-14,8% = efeito-
  largada" é **CONFOUNDADA** — o gate contaminado era um híbrido (com o bug
  de keying) e a diferença inclui a CASCATA completa, não a janela local.
  Medido local (LARGADA-0, 20 runs cegos 0-19): **share_largada = 7,4% do
  tempo-fora** (mediana; máx 0,115). Teto honesto de um pacing perfeito
  ≈ 7% + cascata indeterminada.
- **E2**: o âncora "s≈685 m" do prompt da revisão era leitura errada do
  registro ("RUS, 4,2 s, 2702,685 m" — a mantissa). Emenda P-B
  [2650, 2950] **RATIFICADA** pela revisão (não-gateável: o cluster literal
  do 0-d dá 20/20).

## CICLO LARGADA — FASE 1a: launch-cap (2026-10-19): GATE FAIL — falsificação limpa; flag morta (default OFF)
- **0-c decomposição** (82b12c6): pares_W pooled **ENTRADA-S 228/348 (65%) vs
  GRID 112 (32%)** → árvore: ramo CAP. Pares adjacentes à 1ª excursão **20/20
  em ENTRADA-S, 0 no GRID**. 1ª exc por posição de grid: P2 6× (não P1);
  mesma fileira 29%. cc hist: SECA med 2.906 | DAMP med 3.500.
- **Instrumento**: `--launch-cap` (v_ceiling = 0,8×v_plan(s) na janela t<30 E
  s<2950; freio do governor; default OFF; telemetria per-carro). Prereg
  a3b8ff0 com constantes PINADAS por derivação medida (v_plan real 20,3-57,1
  vs chegada medida máx 48,4). Smoke: div == 1º cap (tick 48) ✓; **3
  violações de fase = FLAG FANTASMA off-track** (rejoin sobrescreve th/brk) →
  reparo `not offtrack` (4b0d4eb, mudança de comportamento ZERO, +t6) →
  re-smoke SELF 3/3; drift base≡hist 0/30000.
- **GATE (11 runs: base s50 + tratamentos 50-59; veredito 7f10fb0 ANTES dos
  números; identity 10/10)**: **FAIL** — PRIMÁRIO-1 pares_W mediana 18/máx
  24 vs ≤8/≤14 (o cap NÃO reduziu o storm; âncora 17); PRIMÁRIO-2 1/10 (9/10
  ainda CONTATO-ADJ em 4,4-9,6 s); s50 (WET) PIORA (par 22 vs base 12; cc
  10.872 vs 8.258); s58 cc 3.400 > 3.197. Secas: rolante 132-138 ✓, par/wand
  0/0 ✓ 9/9, GUARD-V 10/10 ✓.
- **EXPECTATIVA (report-only): fora% <15 em 0/10 → o efeito da era
  contaminada era ARTEFATO DO KEYING (E1 confirmado por MEDIÇÃO), não
  pacing**; fora 20,9-26,7 (secas) ≈ histórico.
- **Diagnóstico (falsificação limpa)**: o cap ENGAJOU (74-137 cap-ticks/run
  em 10/10 carros; fase 0 violações) e NADA mudou — a hipótese "velocidade de
  chegada causa o storm" é REFUTADA: a compressão vem do FUNIL do próprio
  v_plan (todos freiam no mesmo ápice; fator uniforme 0,8× preserva a
  geometria relativa do campo). Em úmido o cap PIORA (campo mais lento =
  mais compactado).
- **Estado**: launch-cap = research-negativo documentado; flag PERMANECE
  default OFF (opt-in morto). SEM re-pin, SEM re-run. Fila da largada ao
  DONO: (a) mudança de GRID (espaçamento/fileiras — era nova, re-pin total;
  112 pares de grid + storm entrada-S persistem); (b) aceitar o launch-storm
  como teto documentado do produto. Pools: 50-59 consumidos; 60-69 próximo
  virgem. 13 runs (o cabeçalho do prereg dizia 12 — slip aritmético;
  sequência §4 correta).

## CICLO LARGADA — FASE 1b: launch-stagger (2026-10-19): GATE FAIL; PRIMÁRIO-1 (vinculante) PASS ESMAGADOR — densidade de grid validada; re-empacotamento estrutural
- **Dados pré-commitados**: scan 60-69 = 1/10 DAMP (s60: v2 CLOUDY → v3
  DAMP; 6551bac) + probe Δt COMMITADO (0268919; lição L-1a do probe inline):
  Δt=1,0 s → gap 1º par 20,3-57,1 m (≥2× os 9 m do grid na zona da queixa).
- **Instrumento**: `--launch-stagger` (hold th=0/brk=1 até release=(pos−1)×
  1,0 s frente→trás; rec.clear() p/ pós-release canônico; slots do run
  wiring na ordem efetiva; cap×stagger exclusivos; telemetria per-carro).
  Smoke: drift 0/30000 ✓; div==1º held (tick 0) ✓; **release NÃO exato
  6/10 — float `+= 0,1` no boundary (0,99999<1,0 segurava 1 amostra; GAS
  slot 7 held até tick 60 vs 58)** → fix tick-exato com round() (ea1194a,
  +t6) → re-smoke SELF 3/3. Suite **25F/296P/2S** (295 prereg + 1 t6 do
  reparo, disclose).
- **GATE (14 runs = 2 smoke + 1 re-smoke + base s60 + 10 trat 60-69;
  identity 10/10; veredito 52fa020 ANTES dos números)**:

| seed | clima | pares_W | 1ª exc (t, s) | taxonomia | par_excl | wand | rol_v1ex | off% | cc |
|---|---|---|---|---|---|---|---|---|---|
| 60 | DAMP | 2 | 32,8s @ 32m | OUTRO | 15 | 16 | 135 | 46,5 | 9.268 |
| 61-69 | SECA | 1-4 | 32,8s @ 31-35m | ADJ 5 / OUTRO 4 | 0 | 0 | 132-135 | 20,6-23,7 | 692-1.902 |

- **PRIMÁRIO-1 (vinculante) PASS ESMAGADOR: pares_W mediana 2, máx 4** vs
  ≤8/≤14 (âncora 12-23 med 17) — **o stagger ELIMINA o storm de largada:
  a densidade de grid É o mecanismo local** (expectativa report-only:
  DENSIDADE VALIDADA).
- **PRIMÁRIO-2 FAIL 5/10**: a 1ª excursão reaparece em TODOS os 10 runs a
  **t=32,8 s, s≈31-35 m — o fim da volta 1, o MESMO sítio/modo da era
  contaminada (32,6 s @ s≈37)**: o campo RE-EMPACOTA dentro de uma volta
  (perfis idênticos convergem de volta ao funil do v_plan) e a
  excursão-por-contato reemerge — ainda CONTATO-ADJ em 5/10.
- **s60 (DAMP) FAIL em PW/OFF/CC**: wand 16 vs base 13; off 46,5% (clima —
  base 46,8%); **cc 9.268 vs base 6.418 (+44%) — úmido PIORA com campo
  segurado (o MESMO padrão do cap: 10.872 vs 8.258)**.
- **REPORT-ONLY compostos**: pares residuais pooled — HARD/SOFT 8,
  MEDIUM/SOFT 9, MEDIUM/MEDIUM 1, SOFT/SOFT 2 → **19/20 envolvem um carro
  SOFT** (insumo grid-era: composto mole domina o contato residual).
- **VEREDITO MECÂNICO: FAIL → PARE por seed; SEM re-pin, SEM re-run.** A
  leitura conjunta F1a+F1b fecha a cadeia causal: a VELOCIDADE não é o
  mecanismo (cap refutado); a DENSIDADE de largada é o mecanismo DO STORM
  DE LARGADA (stagger esmaga) — mas o RE-EMPACOTAMENTO pós-largada é
  ESTRUTURAL (perfis idênticos): segurar a largada só TRANSFERE a
  primeira excursão-por-contato para o fim da volta 1. O launch-storm como
  fenômeno de campo é o TETO do produto com este stack; mitigação
  permanece a alavanca rejoin opt-in (−44% no seco).
- Pools: 60-69 consumidos; **70-79 próximos virgens**. Flags L-1a/L-1b
  ambas default OFF (research-negativas, código preservado).

## CICLO LARGADA — FECHADO (2026-10-19): teto documentado; dossiê canônico
**Local único: `DOSSIE_LARGADA.md`** (cadeia causal com âncoras, enunciado
do teto, disposição de produto, lead SOFT com ressalva, inventário). Resumo:
- Fecho executado com ZERO runs, ZERO mecanismo novo, pools intatos
  (70-79 virgens). Errata-canônica: orçamento L-1b 13→14 (+1 re-smoke
  sancionado pelo §3, disclose); regra de template permanente (+1 re-smoke
  contingente em todo prereg futuro).
- Diagnósticos N1/N2/N3 (script commitado antes de executar):
  N1 GUARD-V 10/10 PASS; N2 1ªs excursões SEM padrão SOFT (7 MEDIUM/2
  HARD/1 SOFT — o lead 19/20-SOFT aplica aos pares residuais, não ao
  evento de re-empacotamento); N3 14 runs → 13 CSVs (re-smoke re-usou
  race_diag_lg1b_stg_s0.csv).
- PENDÊNCIA RESOLVIDA (LARGADA-4, 2026-10-19): o texto "LARGADA-2-review"
  chegou e foi apendado VERBATIM ao worklog no commit **8bd728c** (ANEXO B)
  — a revisão RATIFICA o fecho (R1-R5) e registra a DECISÃO DE FILA
  (fechar o ciclo; grid-era contra-indicada; veto do dono registrado).
- **AUDITORIA_RL.md RESTAURADO do histórico (LARGADA-4)**: o arquivo existia
  (`backend/model_train/AUDITORIA_RL.md`, 1.181 linhas — auditoria do
  pipeline de RL pré-reestruturação; criado 9099235, última versão
  439f402) e perdeu-se no squash da PÓS-CICLO-1. Restaurado verbatim de
  439f402 com bloco de proveniência no topo. A frase do header ("ler este
  arquivo e AUDITORIA_RL.md") é VERDADEIRA novamente; tabela
  Arquivos-chave atualizada.
- FRENTE LARGADA ENCERRADA. Estado de produto vigente: v10-cego+vplan =
  race default; rejoin-gap opt-in = mitigação do sintoma (seco);
  launch-cap/stagger = research-negativas default OFF.

## FASE H-0 (2026-10-19) — geometria: mirrors Monaco/Spa GATE FAIL no G4 (limiar); NÃO congelados; H3 detector validado
Prereg 21ac676 ANTES do código (d470a87). ZERO runs/pool/re-pin; v1s
canônicos INTOCADOS (o nome previsto era `{Name}_mirror*_v1.json` — NUNCA
`_v2`: o `load_track_frozen` PRIORIZA `{key}_v2.json` (R2 S4) e nomear assim
mudaria a pista canônica sem decisão do dono; o loader segue inalterado).
- **Fonte espelhada**: F1DB SVGs oficiais (circuit_layouts_evolution.json;
  probes HTTP 200; parse M/c/s/z; fechamento 0,000% nas duas). Monaco
  "mirror 2021" = `monaco-6` (2003-2019, 2021-2026); Spa = `spa-francorchamps-4`
  (2007-2026). Pipeline: Béziers→resample 4 m→calibração ao oficial
  (3.337/7.004 m).
- **GEOM GATE (prereg §3, mecânico)**:
  | pista | G1 clearance | G2 cross | G3 R_min | G4 turns | G5 L | veredito |
  |---|---|---|---|---|---|---|
  | Monaco | **16,30 m** ✓ | 0 ✓ | **11,34 m** ✓ (hairpin real) | 15 vs 19±3 **✗** | 0,05% ✓ | FAIL → não congela |
  | Spa | **24,83 m** ✓ | 0 ✓ | **14,66 m** ✓ | 5 vs 19±3 **✗** | 0,01% ✓ | FAIL → não congela |
- **Diagnóstico pós-veredito (emenda = revisão; precedente ERRATA #2)**:
  o limiar κ≥0,02 (R≤50 m) do G4 sub-detecta curvas rápidas. Sweep:
  Monaco κ≥0,01 → 17 (DENTRO de 19±3); Spa κ≥0,01 → 23 (κ≈0,008 daria
  ~19-21). **Crítica: G4 como pinado não separa Spa COMPLETA (5) da Spa_v1
  TRUNCADA (~4-5) — em pista rápida não serve ao próprio intento.** Opções
  para a revisão: emendar G4 em prereg novo e re-rodar o builder (segundos,
  zero runs); trocar G4 por outro cheque de completude; rejeitar os mirrors.
- **H3 detector G3 (report-only; critérios pinados ANTES)**: 9/9 frozen
  auditadas; **2/9 flaggeadas exatamente como o prereg previa** — Monaco_v1
  **45 riscos** de hint (pares não-adjacentes <2 m; clearance 1,63 m;
  concentrados em s≈972-1055 m) e Suzuka_v1 **8 riscos** (clearance **0,04 m**
  em s≈1731↔3936 m — o crossover real da ponte/esses, mais crítico que os
  0,39 m da FASE G); Spa_v1 **0 gaps** (confirmado: o furo dela é
  comprimento); demais 7 limpas (17-23 m). O mapa do fix "janela arc-local"
  (G3 futura) está quantificado. ZERO mudança de runtime.
  [RÓTULO N2, ADOÇÃO-H-2: os DOIS valores de clearance do Monaco_v1 são
  instrumentos diferentes — **1,71 m** = audit FASE G (mínimo sobre pares
  <8 m, janela cKDTree) e **1,63 m** = detector H3 da H-0 (mínimo sobre pares
  <2 m não-adjacentes); não é contradição.]
- **ERRATA R8 (ADOÇÃO-H-2; HIPÓTESE ABERTA, marcada)**: Spa_v1 mede 4.352 m
  e o oficial 7,004 km = 4,352 mi (7004/1,609344 = 7.003,85 m) — causa-raiz
  PROVÁVEL: o builder original engoliu MILHAS como METROS (explica o −37,9%
  de uma vez). CONFIRMAÇÃO buscou o literal "4.352"/conversão mi no código
  do repo: **NENHUM ACHADO** (o builder da Spa_v1 não está no repo atual) ⇒
  hipótese permanece ABERTA. Nota aditiva `r8_hypothesis` no JSON da
  Spa_mirror (sha de conteúdo 2637c8adf3c37939 → **4b05f2c3bbc625fc**,
  conferido e documentado).
- **[NOTA-DEP] fastf1 (ADOÇÃO-H-2; registro + audit, zero runs)**: 2026-10 —
  F1 exigiu auth no livetiming archive (**401 CloudFront desde ~15/out**;
  issue fastf1 #978); fastf1 **3.9.0a0 (alpha)** adiciona auth F1TV; stalls
  relatados (#982). Caches quentes intactos; artefatos frozen (v1s +
  mirrors F1DB) IMUNES. **requirements pinado `fastf1==3.8.3`** (sem upgrade
  silencioso). Blast radius (imports): `domain/track_loader.py` (REDE a
  cache frio — get_session/schedule; cache-only a quente; usado SÓ pelo
  fallback resolve_track do env/evals legados — o runner frozen NÃO toca),
  `database/driver_db.py` (REDE a frio; metadados de pilotos, fora do
  caminho de corrida), `archive/scripts/train_multi_context.py` (arquivado,
  fora do runtime). Runner/sim em frozen: ZERO rede. Ingestão futura de
  telemetria = decisão do dono (assinatura F1TV Access+; preferir 3.9
  estável; token via env, NUNCA commitado).
- **FONTE-1 (2026-10-22; decisão do dono: SEM assinatura; migração
  gratuita)**: o módulo `fastf1.ergast` da versão 3.8.3 PINADA já usa
  `BASE_URL=api.jolpi.ca` — plano METADADO/RESULTADO é drop-in SEM
  upgrade (provado em execução: circuits/schedule/lap_times 200; Monaco
  2024 round 8; âncora FastestLap 1:14.165 via results). Telemetria
  histórica: OpenF1 sem login (campos car_data OK; /position separado).
  Caches congelados intactos. Adoção = FONTE-2 (ciclo próprio).
- **Instrumento**: 5 testes (parser M/c/s/z + rejeição; resample 4 m; gates
  sintéticos; convenção sha validada contra Monaco_v1 REAL — t4 adaptado,
  "artefatos se congelados" ficou N/A; detector sintético). Suite
  **25F/301P/2S** (296+5). doc-test verde.
- **Estado**: mirrors NÃO congelados; fila = revisão (emenda G4 → re-run do
  builder). Pools 70-79 intactos. Hashes: fdb1afb (ANEXO review), 738f72d
  (NITs), 21ac676 (prereg), d470a87 (impl).

## FASE H-1 (2026-10-20) — calibração do G4 em CONTROLES: G4 MORRE como gate; mirrors CONGELADOS (ramo B)
Prereg 1f4af52 ANTES de qualquer execução (contagens oficiais ESCRITAS:
fonte única Wikipedia EN 2026-10-20 — formula1.com omitiu turns nas race
pages, probe registrado). Zero runs/pool/re-pin; canônico intocado.
- **Calibração (fase controles → CSV commitado ANTES dos alvos —
  anti-tautologia)**: grade κ 0,004→0,020 (passo 0,001) sobre 5 CONTROLES
  (Hungaroring 14, Monza 11, Zandvoort 14, Suzuka 18, interlagos_v2 15;
  excluídos Monaco_v1 artifact, Spa_v1 truncada, os 2 alvos):
  **0/5 in-band em TODOS os 17 κ** (melhor Σ|Δ|=42 @κ=0,02: contagens
  21-28 vs oficiais 11-18 [N3 ADOÇÃO-H-2: Monza 11 é controle] — o detector κ-picos INFLA em frozen de
  telemetria por ruído de polyline e DEFLACIONA em mirrors Bézier).
  **Conclusão do instrumento: a contagem de "turns oficiais" é convenção
  humana que o detector geométrico não reproduz em NENHUMA classe de
  fonte** — G4 válido exige <4/5 → **RAMO B** (g4_calibration_
  controles.csv commitado 00be13d).
- **RAMO B executado (e405298)**: G4 → fingerprint report-only
  (turns_detected + g4_kappa_used + g4_note da crítica no JSON de
  proveniência); completude = G5 + G1/G2/G3. **Mirrors CONGELADOS**:
  `Monaco_mirror2021_v1.json` (sha 67ca11dc211c8c78; 834 wp; G1 16,30 m;
  G2 0; G3 11,34 m — hairpin real; G5 0,05%) e `Spa_mirror_v1.json`
  (sha 2637c8adf3c37939; 1.751 wp; G1 24,83 m; G2 0; G3 14,66 m; G5
  0,01%). Nomes INERTES ao loader (`{key}_v2.json` tem prioridade e os
  mirrors nunca a acionam).
- **Teste de INÉRCIA (verde)**: `load_track_frozen('Monaco')` → Monaco_v1
  (sha 07e7ef4dd6af4517) e `'Spa'` → Spa_v1, mesmo com os mirrors no
  diretório; mirrors loadáveis pelos nomes explícitos. LIÇÃO: o loader é
  CASE-SENSITIVE ('monaco' minúsculo não acha Monaco_v1.json).
- **Instrumento**: +2 testes (inércia; métricas recomputadas == proveniência).
  Suite **25F/303P/2S** (301+2, declarado no prereg). doc-test verde.
- **Estado**: mirrors congelados como artefatos GEOMÉTRICOS (âncoras de
  corrida — SF/direção — = era de adoção, decisão do DONO; trocar o
  canônico = DONO). Hashes: 94e8df8 (ANEXO H-0-review) + f277819 (NIT
  Comandos 301P) + 1f4af52 (prereg) + 00be13d (calibração/κ*) + e405298
  (freeze + testes). Pools 70-79 intactos.


## ADOÇÃO-H-2 (2026-10-20) — mirrors ADOTADOS como canônico (dono: AMBOS); B' sob mirror 9/9 por completude
Prereg 8c14f9f ANTES de qualquer mudança/medida. Zero corridas/pool/re-pin;
loader INTOCADO; 17 evals solo determinísticos + 3 controles.
- **PASSO 0**: ANEXO FASE-H-1-review verbatim (87419b1, caminho absoluto);
  NITs N1-N3 + errata R8 (HIPÓTESE ABERTA: Spa_v1 4.352 m = 4,352 mi —
  literal NÃO achado no repo; nota `r8_hypothesis` no JSON da Spa, sha
  2637c8→4b05f2c3bbc625fc, disclose) + fastf1 ==3.8.3 pinado + blast
  radius (ce4e799).
- **PROFESSOR-FIRST (por nome explícito, ANTES do swap)**: 3 eps × mirror,
  bit-idênticos (md5), ≥2 voltas/ep pelo critério PINADO → **3/3 em ambos**
  (Monaco 2 voltas @ 211,9 s, fora 58,5%; Spa 2 voltas @ 223,1 s, fora 32%).
  DISCLOSE: eps terminaram em 2 voltas (--laps default 2) dentro da janela
  de 600 s. **CONTROLES (diagnóstico pós-veredito, marcado)**: professor
  solo no interlagos canônico = **fora 24,3%** (o off% alto é BASELINE do
  instrumento professor-solo-frozen — nunca ancorado antes; os 0,36%
  históricos eram 10-carros/live); **Monaco_v1 ABORTA no runner atual**
  ("reta antes da SF = 0 m"); Spa_v1 professor fora 45,4% — **os mirrors
  são MAIS dirigíveis que os v1s**.
- **Mecânica (86a129c)**: git mv → Monaco_v2.json/Spa_v2.json; shas de
  conteúdo conferidos (67ca11dc211c8c78 / 4b05f2c3bbc625fc); v1s →
  `archive/tracks_frozen_v1/` com README de proveniência (NUNCA deletar);
  zero duplicatas inertes; CSVs/logs das evals commitados como evidência.
- **B' RE-ANCORADO (SOB MIRROR; canária runner solo 600s, 3 eps/pista,
  bit-idênticos)**: **Monaco_v2 3/3 × ≥2 voltas** (cruzamentos−1; era-v1:
  0/3 numa pista que hoje ABORTA) — RESSALVA: fora 45,0% (> 25% da
  canária), 34 excursões, preso acumulado 118 s (R3), **wanderer 0** (mais
  longa 26,8 s < 60 s); H-Mon: o artefato limitava a era-v1, mas a
  pilotagem segue custando (completude com custo). **Spa_v2 3/3 × 3
  voltas, fora 20,8% ≤ 25%, wanderer 0 — canária COMPLETA**; H-Spa: o
  aluno SUSTENTA nos 7,004 m reais (era-v1 3/3 era na truncada 4.352 m).
- **Meta A Monaco SOB MIRROR (professor 5 eps)**: 5/5 × 2 voltas (211,9
  s; fora 56,9% — mesmo baseline de instrumento).
- **Instrumento**: t-inércia REESCRITO (flip verde: 'Monaco'→Monaco_v2
  67ca11dc211c8c78; 'Spa'→Spa_v2 4b05f2c3bbc625fc; v1s fora do frozen;
  zero duplicatas) + t-novo (v1s arquivados: sha + Track.from_waypoints
  OK; loader não vê archive/ por PARE). **Suite 25F/302P/3S** [desvio do
  declarado 25F/304P/2S: (1) os 2 testes novos SUBSTITUÍRAM os 2 antigos
  de inércia (net 0, não +2); (2) test_composite_parity:45 (artefato de
  coleta Monaco_v1) virou SKIP condicional — consequência direta da
  adoção]. doc-test verde.
- **Metas**: ver tabela com tags [era v1] / SOB MIRROR. Números históricos
  NUNCA apagados. Pools 70-79 intactos. Hashes: 87419b1 → ce4e799 →
  8c14f9f → 86a129c → fechamento.


## FASE 4 v15 — wiring: composite no race runner (2026-10-21; ABERTA)
Fila pinada pelo dono (Opção B da ADOÇÃO-H-2-review). NÃO toca
mirrors/loader/v1s. PROMOÇÃO (race default = composite?) NÃO é desta fase —
a fase produz evidência; decisão = dono. R13 mantém v10-cego como default.

### PASSO 0 — recon wiring (zero runs)
- **O composite no runner JÁ EXISTE**: `NeuralRaceController` obs
  `traffic` + `_composite_np` (`NumpyCompositeActor`; `run_race_10_cars.py`
  750-790): ação = tanh(m_solo PRÉ-tanh + g·r); residual 16d =
  `build_residual_input(tf_feats, v_ego, κ@10m, prev_st, prev_lng)`;
  gate = `gate_value(v_ego, d_min à frente)`; `_res_prev` fecha o loop
  (a_prev da PRÓPRIA ação composite). `--profile composite` (alias de
  `race`): solo v10 npz + `v15_residual/residual_best_weights.npz`
  (PROFILES em run_race_10_cars.py:71). **B3.1 v1 rodou com este caminho**
  (all-composite N=10 funciona hoje).
- **O que falta (mixed)**: `parse_mixed` aceita SÓ `traffic|edge`
  (race_diagnostic.py:60); o branch `--mixed` (521-531) constrói só
  ctrl_traffic/ctrl_edge (atores .keras puros, SEM residual); o loop (594-600)
  previne 2 controllers; o export CSV usa `ctrl_i` binário e as colunas
  g_gate/r_norm/composite_active só saem via `ctrl._composite_np`.
  → Extensão: grupo `composite` no parse; ctrl_comp (obs traffic + solo
  v10 + NumpyCompositeActor); loop com 3 controllers; export por grupo.
- **Instrumento canônico R13 (o regime de TODA a B3')**:
  `race_diagnostic --actor model_train/v10_dagger/dagger_actor_best.keras
  --obs-mode edge --ticks 6000 --laps 99 --track interlagos --seed N
  --gov vplan --variance grid,compound` — regime canônico seco dá fora
  21-32% (v10-cego); clima semeado por seed (seed 0 = DRY sem transições).

### Q1 — semântica de parada (resposta; zero runs)
`--laps` (default **2**) vira `SimulationConfig.num_laps`: o ENGINE seta
`race_finished` quando o LÍDER completa num_laps — não há contador oculto.
Os eps professor-first da ADOÇÃO-H-2 rodaram SEM --laps (default 2 → parada
exata em 2 voltas); os re-baselines/Meta A rodaram com `--laps 99`
(janela canária de 600s pinada no prereg §6) → correram até o cap de ticks:
Spa_v2 a ~200s/volta completa 3 voltas em 600s ✓ (4 cruzamentos = 3 voltas
+largada — voltas = cruzamentos−1). Diferença de FLAG entre meus próprios
comandos; zero mistério de contador.

### Q2 — métrica "preso" (resposta; zero runs)
DUAS métricas distintas, ambas legítimas:
- **R3 (diagnóstico, impresso no log)**: janelas de 30 s sobre
  (|lat|, cum_dist) por carro; só janelas com ticks off-track; janela é
  "presa" se |lat|máx > 20 m OU progresso (Δcum) < 5 m; o valor impresso =
  TICKS OFF-TRACK ACUMULADOS nas janelas presas (race_diagnostic.py:832-862).
  Monaco_v2: 1185 ticks (118,5 s) ACUMULADOS em múltiplas janelas — NÃO é
  episódio contíguo.
- **R4/gate (critério wanderer)**: EPISÓDIO CONTÍGUO off-track > 60 s sem
  retorno. Monaco_v2: excursão mais longa 26,8 s → wanderer 0 ✓. As duas
  se complementam: R3 mede churn (custo acumulado), R4 mede encravo real.

### RESULTADO B3' (PARE conforme prereg d54bfe; veredito e5cd2ab ANTES dos números)
6 corridas seed 0 DRY 600s regime canônico (seriais):

| corrida | fora% | par | hesit | comp | rolante | cc | pós-larg |
|---|---|---|---|---|---|---|---|
| 1 CONTROLE | 22,1 | 0 | 3 | 10/10 | 136 | 3674 | 2482 |
| 2 ALL-COMPOSITE | 25,2 | 0 | **14 [errata FF1-E3: log 2_allcomposite.log:71 + recontagem + verificação FAIL-FORENSICS-1b]** | 10/10 | 140 | **752** | 292 |
| 3 MISTA 2comp | 17,3 | 0 | 4 | 10/10 | 166 | 1808 | 574 |
| 4 MISTA 4comp | 19,2 | 0 | 3 | 10/10 | 166 | 2022 | 930 |
| 5 CTRL-EMBARALHADO | 21,2 | 0 | 1 | 10/10 | 133 | 1622 | 966 |
| 6 HOLD-AT (report) | 16,9 | 4 | 6 | 9/10 | 168 | 4244 | 3188 |

Por grupo nas mistas: composite n=2 cc=397 (pós-larg 193; 96,5/carro) vs edge
n=8 cc=1411 (pós-larg 381; 47,6/carro); composite n=4 cc=625 (242; 60,5/c)
vs edge n=6 cc=1397 (688; 114,7/c).

**VEREDITO: FAIL** (2 critérios):
- **HESIT ≤3: composite 14 [errata FF1-E3]** (controle da mesma sessão: 3; R10 D3 mediu
  12,5 vs 5 — REPRODUÇÃO fora de sessão do achado R10: o custo de
  hesitação do composite é REAL e sobrevive ao regime canônico).
- **Mistas pós-largada composite ≈0 (≤2): 193/242** — absoluto da era
  pré-canônica (B3.3 FASE 5: 0 contato pós-largada com clima-loteria) que
  o prereg NÃO re-ancorou (só re-ancorou fora/rolante do B3.1) — GAP DE
  PIN divulgado: sob o regime canônico o pós-largada é endêmico (o
  CONTROLE tem 2482); o relativo: composite-minoridade acumula ~2× mais
  contatos/carro que o edge na mesma corrida (96,5 vs 47,6).
- O que PASSA (evidência para o dono): **GATE PRIMÁRIO contatos < controle:
  752 vs 3674 (4,9× menos na MESMA sessão)**; 10/10 voltas; 0 paradas;
  fora 25,2% ≤ 29,9%; rolante 140 ≤ 146. Custos confirmados: hesit 14 [errata FF1-E3];
  pace +4s all-composite; **mistas +33s vs ctrl-embaralhado** (o campo
  misto desacelera). HOLD-AT (report): 9/10, 4 paradas — a pilha
  multi-composite PERMANECE limitação (confirmada sob canônico).

### Wiring + instrumento
- Grupo `composite` no `--mixed` (limitação 2 da FASE 4 RESOLVIDA):
  parse/assign/construção (ctrl_comp obs traffic + solo v10 npz +
  NumpyCompositeActor com npz do PROFILES race)/loop de 3 controllers/export
  por grupo (commits 89598ef + f2c66f2). PROTEÇÃO v10-cego: corrida 1200
  ticks seed 0 BIT-IDÊNTICA ao fixture pré-wiring (verde na 1ª tentativa —
  o wiring toca só o branch --mixed). 3 testes novos; suíte 25F/305P/3S
  (ESPERADA 25F/306P/3S ±: t-parity race-path N/A — paridade já coberta
  pelo test_composite_parity + bit-identidade do canônico; desvio
  justificado). Veredito e5cd2ab ANTES de ler números.
- DIAGNÓSTICO pós-veredito (marcado, padrão H-0): zsh NÃO faz word-split
  de variáveis não-quotadas (SH_WORD_SPLIT off) — args em $VAR viram UM
  argumento; cadeias de corrida com args EXPLÍCITOS.
- Hashes: 5b2bcf0 (ANEXO) → 472cd94 (seção+Q1/Q2) → d54b5fe (prereg) →
  89598ef/f2c66f2 (wiring+testes) → e5cd2ab (veredito) → fechamento.

## ANTI-D3-1 (2026-10-21) — progress-guard fade gate→base: PRIMÁRIO FAIL → D3 ESTRUTURAL; PARE
Fila pinnada pelo dono: atacar o D3 (hesitações) com UM mecanismo de camada
ANTES da decisão A×B de promoção — sem retreino, sem recoleção, sem re-pin,
sem mudança de default. Base do ataque: diagnóstico P1 (8c79ee6) — 13
hesitações = residual-brake dead-stop (12/13 gate persistente; 13/13 |r|>0,1;
th=0,00; 8/13 na fila s≈2289-2318).

### Cadeia
57a9342 (prereg ANTES de código/medida; reconciliação SISTEMÁTICA — mistas
DROP; veredito pré-commitado OBRIGATÓRIO; orçamento 2 corridas) → 7dde1d8
(implementação no ÚNICO caminho composite do predict_batch + 5 testes;
v10-cego BIT-IDÊNTICO ao fixture ANTES de qualquer corrida) → 33610ba
(anti_d3_verdict.py commitado ANTES das corridas) → corridas → veredito →
probe pós-veredito bbe9512/29399d4/2f29c98/18c00a2 (cada versão commitada
antes do run; regra "probe nunca inline") → fechamento.

### Mecanismo pinnado — e as constantes EFETIVAS
g>0,01 + Δcum<0,5m por N=5 ticks consecutivos → fade linear de g_eff a 0 em
F=5 ticks; retoma (fade=0) ao reprogredir ≥0,5m; estado por driver
(`_pguard_state`). O prereg pinou em TICKS; o tick lógico do engine é 0,1s
(10 Hz; o CSV exporta ticks pares = linhas de 0,2s) ⇒ EFETIVO: trigger
0,5s com limiar v<5,0 m/s (18 km/h), fade completo +0,5s. A leitura
"1,0s / 2,5 m/s" (semântica 5 Hz do P1) NÃO era a do código rodado — não é
desvio do pin (o prereg não pinou segundos), mas muda toda a leitura do
resultado.

### RESULTADO (2 corridas seed 0 DRY 600s regime canônico; seriais; controle 1º)

| corrida | fora% | par | hesit | comp | rol | cc | pós-larg |
|---|---|---|---|---|---|---|---|
| 1 CONTROLE | 22,1 | 0 | 3 | 10/10 | 136,0 | 3674 | 2482 |
| 2 ALL-COMPOSITE (guard) | 26,1 | 0 | **12** | 10/10 | 145,0 | 1520 | 846 |

PROTEÇÃO DUPLA verde: v10-cego bit-idêntico ao fixture (pré-corridas) +
controle re-run BIT-IDÊNTICO à F4v15 (cc 3674, pós-larg 2482, rol 136,0,
hesit 3, fora 22,1 — o guard não vaza para o caminho canônico).

VEREDITO MECÂNICO (anti_d3_verdict.py — verbatim):

```
PRIMÁRIO hesit composite (12) <= controle (3): FAIL
Não-reg cc (1520) < controle (3674): PASS
Não-reg paradas = 0: PASS
Não-reg 10/10 voltas: PASS
Não-reg fora <= 29,9%: PASS
Não-reg rol (145.0) <= controle+10 (146.0): PASS

ANTI-D3-1: FAIL — PARE; sem re-pin/re-run
```

### Ramo 3 da árvore → D3 ESTRUTURAL; A×B volta ao dono
PRIMÁRIO FAIL ⇒ D3 DECLARADO ESTRUTURAL à camada: o mecanismo-único pinnado
não remove as hesitações (13→12 vs limiar ≤3) E degrada o valor primário
(cc 752→1520; pós-largada 292→846). A decisão A×B (manter v10-cego default ×
promover all-composite) VOLTA AO DONO com o D3 como CUSTO PERMANENTE — e o
guard vira EVIDÊNCIA CONTRA intervenções de fade na camada. Nenhum ramo
promove; R13 mantém v10-cego; zero mudança de default.

### Diagnóstico pós-veredito (marcado; probe commitado; ZERO runs)
1. **LARGADA: 9/10 carros DISPARAM o guard em t=0,4-0,6s** — disparos
   PRÓPRIOS (razão ON/OFF 0,80/0,60 = fade 0,2/0,4 no tick; PIA/NOR/VER
   t=0,4s; ALO/PER/LEC/RUS/GAS/SAI t=0,6s — o tick 5 não é exportado). A
   aceleração de largada 0→5 m/s leva ~0,8s = 8 ticks com Δcum<0,5m e gate
   aberto (grid comprimido, g=1,0) — disparo GARANTIDO pelo limiar efetivo.
   Exceção HAM: gate nominal 0,00 durante toda a largada (else branch, não
   acumula; 1ª divergência só t=99,6s com g_on=0,00 — disparo próprio
   tardio). Fade visível na PIA: g 1,00→0,80→0,40→0,00 (0,4-0,8s), reset a
   1,00 em t=1,0s ao reprogredir.
2. **O fade ACELEROU a largada** (PIA t=1,0s: v_on 6,67 vs v_off 4,84;
   t=1,2s: 7,97 vs 6,12) — residual mudo no funil → carros mais rápidos no
   pelotão → pós-largada 292→846 (o valor do composite é CONCENTRADO na
   largada: controle 2482).
3. **Hesitações quase intocadas (13→12; med 0,6s; máx 1,0→0,6s)**: os
   episódios (0,4-0,6s) terminam ANTES de trigger (0,5s) + fade (0,5s)
   completarem; e o contador (janela 0,3-3s) CONTARIA o episódio resgatado
   de qualquer forma — o PRIMÁRIO pinnado é quase-insensível ao resgate POR
   CONSTRUÇÃO. A liberação das hesitações é NATURAL (presente na OFF sem
   guard: 4/13 episódios com g nominal colapsando): a fila descarrega →
   d_min > D(v→0)=40m → g→0 → residual desliga → base retoma.
4. **cc 752→1520 (+102%)**: o limiar v<5 m/s (18 km/h) trata CRAWL de
   tráfego como "sem progresso" — o guard cicla fade em todo seguimento
   lento, mutilando o residual exatamente onde ele previne contato.
5. **DESVIO DE INSTRUMENTO (defeito da fase, divulgado)**: o prereg pinou
   "o gate NOMINAL segue como instrumento"; o código gravou o g_eff
   (`g = g_eff` antes de `gates[i] = g`; o comentário da linha 798
   CONTRADIZ o próprio código). Nominal irrecuperável do CSV ON — o probe
   precisou da corrida OFF como referência do prefixo. Sem efeito nos
   critérios do veredito (métricas de estado), mas o instrumento NÃO
   cumpriu o pin.
6. **Probe v1 cego (retificado)**: o "0 disparos ON" do contador v1 era
   artefato (tick 0 não contado no proxy; g_gate=g_eff≤0,01 sob fade cega o
   branch nominal) — suplantado pela §Divergência (v2-v4).

### Suíte
25F/310P/3S (ESPERADA ~25F/309P/3S ±: base 25F/305P/3S + 5 testes do
progress-guard = 310P; aritmética do prereg — desvio +1P justificado).

### Pool / intocáveis
Zero pool novo (seed 0 = âncora já usada na F4v15); 70-79 VIRGENS;
mirrors/loader/v1s/fastf1 intocados; runs≠arquivos (2 corridas = 6 arquivos
csv+events+log coerentes em experiments/anti-d3-1/).

## SANIDADE-0 (2026-10-20) — defeitos do produto (largada/grama/colagem): M1/M3 FAIL saem; M2 verde no bundle; PARE
Branch `feat/sanidade-produto`. SEM promoção A×B, SEM flip de default, SEM
re-pin do canônico R13. NIT N1 da review ANTI-D3-1 executado no PASSO 0.

### Cadeia
158e9f9 (NIT N1: --pguard DEFAULT-OFF + t6; ANEXO review PENDENTE — texto
ausente) → sanidade_diag v1→v2.2 (D0-D3, probes commitados antes de cada
run) → 1007636 (PREREG com reconciliação SISTEMÁTICA, antes da impl) →
d42d947 (M1/M2/M3 + bundle + 5 testes) → veredito commitado (antes das
corridas; auto-testado nas âncoras F4v15) → 6 corridas seriais → 90e5b63
(evidência) → 7afe4a8 (árvore: bundle = só M2) → fechamento.

### Diagnóstico D0-D3 (instrumento VALIDADO antes das âncoras)
- **D0**: coluna `lat` do CSV = MÓDULO (lat@0 +1,9 p/ TODOS vs grid físico
  ±1,9); canal válido **slat = obs4 × half_width** (hw 6,00 derivado do
  grid; ±1,90 exato por paridade de slot). Toda análise lateral do ciclo
  usa slat.
- **D1 (controle)**: pós-largada t>20s = 2482; t 20-30 74 (3,0%) | 30-60
  358 (14,4%) | **>60s 2050 (82,6%)**; t<60s = **1624** (âncora PRIM-1);
  17 pares, top-5 = 62% dos ticks; T1: |Δlat| do vizinho<20m mediana 0,4 m,
  10/10 <1,7 m; EMPURRÃO 49/180 (27%) × PILOTAGEM 131 (73%); largada:
  máx|Δlat|/1s até 8,0 m/s.
- **D2**: excursões 180/219 (v0/comp), mediana 4,2s ambos, wanders 0;
  reentrada ~9 m/s, 15 m/s em 1,0s; contato ≤30s pós-reentrada 38% (gap
  mediana 3,0s). Lei ativa: bearing R3 + teto 8 m/s.
- **D3 (slat; |Δlat|<2,0 ∧ Δs<5,5; >2s)**: controle **41 janelas/247s/6
  deadlocks**; esterço ~0,05 nas retas (NINGUÉM esterça — relato do dono
  CONFIRMADO); 29 DECISÃO × 12 FÍSICA. Composite 7/33s/0; 2×5.

### Mecanismos (prereg 1007636 §1; TODOS flag própria DEFAULT-OFF)
M1 `--grid staggered` (2 colunas ±2,5 m; 1-por-fileira 12 m não cabe na
reta de 45 m — derivação D1); M2 `--rejoin perceptive` (ângulo raso ≤15° =
alvo a clip(|lat|/tan15°, 10, 120) m; grama 6,0 m/s; gap X=20 auto reusando
o gap-check REPARADO; trigger ESTADO, nunca progresso — lição ANTI-D3-1;
neural + professor); M3 `--anti-glue` (fricção chassis 0,05→0,01; preventivo
+0,25 rad escopado a comp/prof; breaker 3 s lift+offset 0,4 todos;
authority=anti_glue sem colunas novas). Bundle `--modo espectador` (GUI).

### RESULTADO (6 corridas seriais; veredito pré-commitado)

| corrida | cc | t<60s | hesit | rol | off% | exc med | colado | dead |
|---|---|---|---|---|---|---|---|---|
| P1 v0 s0 OFF | 3674 | — | 3 | 136,0 | 22,1 | — | — | — |
| P2 comp s0 OFF | 752 | — | 13 | 140,0 | 25,2 | — | — | — |
| G1 v0 s70 | 1380 | **942** | 0 | 149,0 | 25,7 | 5,1s | 66,6s | 0 |
| G2 comp s71 | 274 | 222 | 14 | 153,0 | 30,0 | 6,0s | 2,4s | 0 |
| G3 v0 s72 | 1854 | **1352** | 4 | 145,0 | 25,6 | 4,0s | 99,2s | **1** |
| G4 comp s73 | 416 | 340 | 11 | 165,0 | 30,3 | 4,5s | 17,8s | 0 |

**PROTEÇÕES BIT-IDÊNTICAS** (P1 = 3674/2482/136/3/22,1; P2 =
752/292/140/13/25,2): zero vazamento no caminho compartilhado; o guard-off
restaura o pré-guard (NIT N1 confirmado em corrida).

VEREDITO MECÂNICO (sanidade_verdict.py, verbatim):
```
M1: FAIL — research-negativo, SAI do bundle
M2: PASS — embarca no bundle
M3: FAIL — research-negativo, SAI do bundle
SANIDADE-0: PRIMÁRIO(S) FAIL — mecanismo(s) sai(m) do bundle; sem re-pin/re-run/promoção
```
- **M1 FAIL**: c60 942/1352 > 812 (teto = 50% de 1624). Direção positiva
  (−42%/−17%) mas longe do −50% — consistente com o RE-EMPACOTAMENTO da
  LARGADA F1b: geometria de grid não halve contatos de largada.
- **M2 PASS (4/4)**: medianas 4,0/4,5/5,1/6,0 ≤ 8,4; wanders 0. O braço
  comp subiu 4,2→6,0s — o retorno mais lento do ângulo raso + cap 6,
  EXATAMENTE o previsto na re-ancoragem (a leitura literal "2× melhor"
  foi rejeitada no prereg com essa derivação).
- **M3 FAIL por margens**: 1 deadlock >10s na s72 (o breaker engajou mas
  não separou dentro da janela) + comp s73 colado 17,8 > 16,5s. MAS: v0
  colado 247→66,6/99,2 (−73/−60% [errata R4 da review: ordem corrigida])
  e comp 33→2,4/17,8 — o mecanismo MOVE a
  métrica massivamente; research-negativo pela árvore, dado p/ o dono.
- **Não-reg**: rol 149/153/145/165 (G1/G2/G4 > 146) e comp off 30,0/30,3
  (> 29,9, marginais 0,1-0,4pp). DISCLOSE marcado: os tetos 146/29,9 são
  âncoras de UMA realização (s0 +10s) / quantil seco p75; a dispersão
  histórica R7a é rol 139-192s e comp-fora 25,1-41,2% — s70-73 são
  realizações NOVAS e os FAILs marginais são consistentes com variância de
  seed (não necessariamente efeito do bundle). Sem re-run (árvore).
- G2 comp s71: cc 274 (t<60s 222) — o MENOR cc já medido no instrumento
  canônico (âncora era 752): o bundle composto + seed novo; hesit 14 (D3
  persiste — consistente com o veredito ANTI-D3-1).

### Disposição
- `--modo espectador` (GUI) = **SÓ M2** (árvore 7afe4a8): o bundle embarca
  apenas mecanismo verde. Flags individuais `--grid staggered` /
  `--anti-glue` permanecem NO CÓDIGO como research opt-in default-OFF.
- Comando do dono (GUI): `.venv/bin/python scripts/run_race_10_cars.py
  --profile race-blind --modo espectador --seed 0 --laps 99` (idem
  `--profile race` para o composite).
- Pools: **70-73 CONSUMIDOS**; 74-79 VIRGENS. ANEXO review ANTI-D3-1
  PENDENTE (texto não veio no prompt SANIDADE-0 nem existe em sítio
  acessível — buscado; nada fabricado).

### Suíte
25F/316P/3S (ESPERADA ~25F/31xP/3S ±: base 310 + t6 do NIT N1 + 5 testes
dos mecanismos = 316 exato). doc-test verde.

## SANIDADE-1b (2026-10-20) — M3-v2 (tetos) ARQUIVADO; M2 atribuição LIMPA; PARE
Branch `feat/sanidade-produto`. SEM retreino/promoção/flip/re-pin pós-número.
Fila do dono: M3-v2 (anti-colagem com tetos por-realização) + atribuição
limpa do M2, antes da re-decisão A×B.

### Cadeia
33396f6 (ANEXO SANIDADE-0-review VERBATIM em commit dedicado — pendência (b)
zerada) → 8b95f69 (caveats "opt-in research, não-gaitado" nos helps do
--modo espectador e das flags — pendência (a)) → sanidade1b_diag (D4/D5
commitado antes de cada uso) → 4c7d96a (diag_d4_d5.md) → 87214c7 (PREREG
com reconciliação sistemática + predição M2 pré-registrada) → e9d1877
(M3-v2: `_anti_glue_step` COMPARTILHADO, neural + professor POR HERANÇA;
v1 MORTO atrás da MESMA flag; +6 testes dos tetos) → d32036d (veredito
commitado + --selftest OK reproduzindo F4v15 E SANIDADE-0 dos CSVs) →
7 corridas seriais → ae1367d (evidência) → fechamento.

### Diagnóstico D4/D5 (informou os tetos; zero runs)
- **D4**: FRICÇÃO INOCENTE (shove ≈ 0 em todos os braços, 0,01 e 0,05);
  BREAKER marginal (0-11 eps, 0-17,6 car·s); **PREVENTIVO = o custo
  dominante** — exposição comp 194-213 car·s e taxa de excursão DURANTE
  janela de exposição DOBRA (0,144-0,169/s vs 0,077/s da ref): o offset
  +0,25 crônico empurra pra fora.
- **D5**: deadlock s72 = GAS×PIA reentrando em PARALELO — PIA seguro
  pelo gap-hold do M2 (crawl 4 m/s) e GAS 6,0s sob o breaker (60 ticks
  anti_glue) sem separar; ARTEFATO DA INTERAÇÃO M2×M3; breaker v1
  incompetente no regime crawl/borda.

### RESULTADO (7 corridas seriais; veredito pré-commitado e auto-validado)

| corrida | cc | pós-larg | hesit | rol | off% | exc med | colado | dead |
|---|---|---|---|---|---|---|---|---|
| P1 v0 s0 OFF | 3674 | 2482 | 3 | 136,0 | 22,1 | 4,2s | 246,8s | 6 |
| P2 comp s0 OFF | 752 | 292 | 13 | 140,0 | 25,2 | 4,2s | 33,2s | 0 |
| M2-only comp s0 | **516** | 98 | **6** | 147,0 | **28,0** | 4,6s | **16,4** | 0 |
| G1 v0 s74 (v2) | 2536 | 1142 | 1 | 137,0 | 23,0 | 4,2s | 133,0s | 3 |
| G2 comp s74 (v2) | 1536 | 948 | 15 | 146,0 | 28,8 | 4,4s | **51,6s** | 1 |
| G3 v0 s75 (v2) | 2116 | 694 | 1 | 133,0 | 21,7 | 4,5s | 145,4s | 3 |
| G4 comp s75 (v2) | 964 | 728 | 13 | 159,0 | 30,6 | 4,8s | **50,6s** | 2 |

**PROTEÇÕES BIT-IDÊNTICAS** (P1 = 3674/2482/136/3/22,1; P2 =
752/292/140/13/25,2): zero vazamento da v2 flag-off.

VEREDITO MECÂNICO (sanidade1b_verdict.py — verbatim):
```
M3-v2: FAIL — ARQUIVADO research-negative COM LEADS (D4 preventivo-custo;
D5 interação M2×M3; ativo v1 colado −73/−60% v0); não-reg FAIL [...];
ABSOLUTO deadlocks FAIL
M2: atribuição limpa registrada (fora dentro do teto)
```

### Atribuição M2 (o resultado de ouro; memo p/ o dono)
Comp M2-only s0: **cc 516 (−31% vs 752)**, pós-larg 98 (vs 292), **hesit 6
(vs 13 = −54%** — parte do D3 das hesitações é fenômeno de rejoin e o
perceptive ataca), **colado 16,4s (−51%)**, wand 0, dead 0, **fora 28,0%
(Δ+2,8pp ≤ teto 29,9 — gatilho de escala NÃO dispara)**, exc mediana
4,2→4,6s (+0,4s), rol 147 (+7s). A predição pré-registrada (31,8% =
25,2 + 1,8s×219/6000) SUPERESTIMOU: o +1,8s×219 da review SANIDADE-0 era
em parte custo do M3 (bundle); o M2 puro custa +0,4s de mediana. Helps
atualizados pós-atribuição: "solo MEDIDO no SANIDADE-1b (fora 28,0% ≤
teto 29,9; cc 516 = −31%; hesit 6) — opt-in research, não-gaitado; adoção
= dono".

### M3-v2: por que os tetos mataram o mecanismo (leitura marcada)
A dose crônica do preventivo ERA o ingrediente ativo de separação — os
tetos (1,0s/episódio + cooldown 2,0s + 10 eps/par + |Δv|<8 + breaker
4s-desiste + 8 eps/par + competência-v) reduziram a dose e a separação
foi junto: v0 colado 66,6/99,2 (v1) → **133,0/145,4** (v2) com deadlocks
0/1 → **3/3**; comp colado 51,6/50,6s = 3× o teto 16,5; e o cc do braço
comp PIOROU vs proteção (1536/964 > 752) — o preventivo oscilante
(1s-on/2s-off) e o breaker que desiste deixam pares moendo.
**LEAD registrada (árvore §6)**: custo (D4) e separação são O MESMO
mecanismo — limitar a dose perde os dois; um M3 futuro precisa de OUTRO
princípio de separação (ex.: separação por convenção de lado/precência),
não limitação de dose do esterço.

### PIN COLLISION divulgada (erro de pin MEU)
O ABSOLUTO "0 deadlocks em TODOS os 7 runs" colide com a bit-identidade
de P1: a âncora F4v15-v0 TEM 6 deadlocks (246,8s colado, 6 janelas >10s)
— o absoluto era impossível para as proteções POR CONSTRUÇÃO. Leitura
correta: o absoluto aplica aos runs de TRATAMENTO (M2-only: 0 ✓; gates:
3/1/3/2 ✗ — falham de qualquer forma). O veredito M3-v2 é INALTERADO por
isso (PRIMÁRIO 3×, deadlocks de gate, não-reg comp todos FAIL).
Não-reconciliar colisões entre pins é a lição.

### Disposição
- `--anti-glue` (v2) = **research default-OFF, ARQUIVADA**; v1 e v2
  mortos; nenhum entra no bundle.
- `--modo espectador` = **SÓ M2** (inalterado; agora com atribuição
  solo LIMPA registrada). Adoção = dono.
- Pools: **74/75 CONSUMIDOS**; 76-79 VIRGENS.
- Suíte **25F/322P/3S** (316+6 — número EXATO do prereg; ± não usado).

## VARIEDADE-1 (2026-10-21) — camada de variedade OPT-IN: TODOS OS CRITÉRIOS PASS; PARE
Micro-ciclo self-contained. **O determinismo NÃO morre** (infraestrutura de
medição): sem a flag, mesma seed + mesmo profile = corrida bit-idêntica
ao hoje (provado em corrida). Zero promoção/flip/retreino; zero pool.

### Cadeia
083ddea (ANEXO SANIDADE-1b-review verbatim, commit dedicado) → b237aeb
(prereg com reconciliação sistemática E ENTRE PINS — regra nova da review,
1ª aplicação; zero colisões) → 95a6a16 (implementação camada-only + 4
testes) → 9b97da6 (veredito mecânico; --selftest OK — padrão-ouro 3ª) →
c06dd7e (evidência 6 corridas) → fechamento.

### Mecanismo (prereg b237aeb §1 — TUDO pinado antes do código)
`--variedade N` (default 0 = OFF; N<0 fail-loud; nos DOIS runners). N>=1
deriva PRNG PRÓPRIO `random.Random(int(sha256("<seed>//variedade//<N>"),
16))` — o padrão weather_rng_from_seed — NUNCA o RNG global da sim.
Perturba SÓ condições iniciais, ANTES do tick 0, por carro na ordem do
grid: **jitter de grid** d_long ~ U(−0,5, +0,5) m e d_lat ~ U(−0,3, +0,3)
m (derivação: grid 42+1 = 43 m ≤ reta 45 m; fileiras ≥ 8 m; Δlat min
3,2 m > largura 1,8 m) + **fator de pace** mu_nominal ×= U(0,98, 1,02) NO
SPAWN ([1,764, 1,836] ⊂ banda slick [1,7, 1,9]; o canal DINÂMICO
grip_multiplier de pneu/clima/superfície e as leis dos controllers
(vplan grip_mult 0,788, M2, anti-glue) INTOCADOS; física de contato
intacta). **Variedade vai em LINHA DE LOG/IDENTIDADE** (`[diag]
VARIEDADE-1: N=...` + `variedade=N` na linha frozen), NUNCA no schema do
CSV. `--variedade` compõe com `--modo espectador` (comando do dono).

### RESULTADO (6 corridas seriais seed 0; ordem pinada do prereg §5)

| corrida | cc | pós-larg | hesit | rol | off% | colado | dead | 10/10 | par |
|---|---|---|---|---|---|---|---|---|---|
| P1 v0 OFF | 3674 | 2482 | 3 | 136,0 | 22,1 | 246,8s | 6 | ✓ | 0 |
| P2 comp OFF | 752 | 292 | 13 | 140,0 | 25,2 | 33,2s | 0 | ✓ | 0 |
| D1 v0 var=1 | 2052 | 972 | 3 | 134,0 | 21,6 | 122,0s | 2 | ✓ | 0 |
| D2 v0 var=1 REP | 2052 | 972 | 3 | 134,0 | 21,6 | 122,0s | 2 | ✓ | 0 |
| D3 v0 var=2 | 1068 | 114 | 1 | 134,0 | 21,6 | 43,0s | 0 | ✓ | 0 |
| D4 comp var=1 | 2336 | 1796 | 24 | 156,0 | 30,9 | 88,8s | 3 | ✓ | 0 |

VEREDITO MECÂNICO (variedade_verdict.py — verbatim):
```
PROTEÇÃO P1 == F4v15-v0: BIT-IDÊNTICO
PROTEÇÃO P2 == F4v15-comp: BIT-IDÊNTICO
D2 == D1 byte-a-byte + stats: BIT-IDÊNTICAS: PASS
D3 diverge <tick 200: vs base t=0, vs D1 t=0: PASS
D1: 10/10 voltas e 0 paradas: PASS
[D2, D3, D4 idem]: PASS

VARIEDADE-1: TODOS OS CRITÉRIOS PASS — camada entregue como OPT-IN
(default 0; canônico intocado; adoção = dono). Contatos variam
naturalmente (sem teto — report acima).
```

### Leitura
- **A variedade FUNCIONA**: a MESMA seed 0 que produzia uma única corrida
  (v0: cc 3674) agora produz realizações distintas e plausíveis por N:
  2052 (var=1) / 1068 (var=2) / 2336 (comp var=1) — contatos variam
  naturalmente (sem teto, pin do dono), 10/10 voltas e 0 paradas em todas.
- **O determinismo sobreviveu**: D2 == D1 BYTE-A-BYTE (linhas de dados) —
  mesma (seed, N) reproduz exatamente; e a flag OFF reproduz as âncoras
  bit-a-bit. D3 (N=2) diverge no TICK 0 (o jitter muda posições desde a
  primeira amostra — < 200 por construção; o critério também valida que
  as streams sha256 de N=1 e N=2 são distintas).
- **Reconciliação ENTRE PINS (1ª aplicação da regra nova)**: zero colisões
  declaradas ANTES do commit (bit-idêntica OFF × bit-idêntica D2==D1
  compatíveis via RNG derivado + serial R6; absolutos × âncoras checados)
  — contraste com a PIN COLLISION do SANIDADE-1b, agora prevenida por
  regra.
- D4 (comp var=1): hesit 24 / off 30,9 / rol 156 — a variedade re-sorteia
  o braço comp também (realização nova); report-only, sem teto (pin).

### Disposição
- Camada **OPT-IN entregue**: default 0 = canônico intocado; adoção em
  GUI/corridas do dono = decisão dele. Comando do dono (nos Comandos
  essenciais): `scripts/run_race_10_cars.py --profile race-blind --modo
  espectador --seed 0 --variedade 1 --laps 99` (e seed 0/var 0 segue o
  canônico bit-idêntico).
- Pools: ZERO consumo novo (demos = seed 0 + variedade); 76-79 VIRGENS.
- Suíte **25F/326P/3S** (322+4 — número EXATO do prereg).

## SAIDAS-1 (2026-10-21) — diagnóstico pré-registrado de saídas solo por curva: VEREDITO MECÂNICO CONCLUÍDO (VEREDITO ratificado na SAIDAS-1-review; EXECUÇÃO/ERRATAS R1–R4 ratificadas na ERRATA-SAIDAS-1-review; R5-a/R5-b consolidadas no PROF-MONACO-1 P0 — §8 do ANEXO)
Ciclo de diagnóstico mecânico self-contained pré-registrado. Motivação do dono: "há curvas que eles saem mesmo estando sozinhos". A decisão A×B permanece **ABERTA e CONGELADA** (zero promoção/flip/retreino). Orçamento: **ZERO corridas** (re-análise de artefatos existentes F4v15 `1_controle.csv` e `2_allcomposite.csv`; pools 76-79 VIRGENS).

### Cadeia
1c24988 (PREREG_SAIDAS_1.md com reconciliação sistemática, 11 complexos de curva derivados de interlagos_v2.json com gap merge 40m, seed 42 de bootstrap) → 7ea2f27 (scripts/saidas_verdict.py com --selftest mecânico verde: SPIN, SLIDE, LINHA-RETA, RUIDOSO, bootstrap e geometria) → 736102d (tabelas de evidência Q1-Q4 emitidas em experiments/saidas-1/) → 36cdff3 (fechamento SAIDAS-1) → ce895cd (fix: correções R1–R4 + saidas_verdict.py re-rodado com selftest verde e cross-check aritmético) → fechamento ERRATA-SAIDAS-1.

### Reconciliação com Âncoras F4v15
- Perfil A (v10-cego): 22,1% fora (22,1167% exato; Δ = +0,0167 pp <= 0,1 pp), 180 eventos de saída, duração mediana 4,2 s [IQR: 1,3–10,5 s].
- Perfil B (composite): 25,2% fora (25,2133% exato; Δ = +0,0133 pp <= 0,1 pp), 219 eventos de saída, duração mediana 4,2 s [IQR: 1,9–8,7 s].
- Reconciliação semântica e dentro da tolerância pré-registrada (<= 0,1 pp) 100% satisfeita.

### Veredito Mecânico (saidas_verdict.py — verbatim)
```
RECONCILIAÇÃO F4v15 ÂNCORAS:
  Perfil A (v10-cego): 22.1167% fora vs âncora 22.1% (DIFF: 0.0167 pp <= 0.1 pp) -> PASS
  Perfil B (composite): 25.2133% fora vs âncora 25.2% (DIFF: 0.0133 pp <= 0.1 pp) -> PASS
Q1 PROPORÇÃO SOLO (D=15m, T=5s):
  Perfil A (v10-cego): 46.7% (84/180) [IC 95%: 39.4% - 53.9%]
  Perfil B (composite): 83.6% (183/219) [IC 95%: 78.5% - 88.1%]
  Diferença (B - A): +36.9 pp (IC 95% não se cruzam)
Q2 TOP-5 COMPLEXOS DE CURVA:
  Perfil A: C01 Descida do Lago (26.7%), C06 Bico de Pato (22.2%), C08 Junção (22.2%), C07 Mergulho (20.6%), C09 Subida dos Boxes (3.9%)
  Perfil B: C01 Descida do Lago (22.8%), C07 Mergulho (19.2%), C08 Junção (18.7%), C06 Bico de Pato (17.4%), Retas (9.1%)
Consistência Aritmética Q1 x Q2:
  Perfil A: soma curvas (84) == total Q1 (84) -> PASS
  Perfil B: soma curvas (183) == total Q1 (183) -> PASS
Q3 MODOS CINEMÁTICOS DE SAÍDA:
  Perfil A: LINHA-RETA: 58.9% (106), SLIDE: 41.1% (74), SPIN: 0.0% (0)
  Perfil B: LINHA-RETA: 65.3% (143), SLIDE: 34.7% (76), SPIN: 0.0% (0)
Q4 VELOCIDADE DE ENTRADA (1s antes do evento):
  C01 Descida do Lago (T4/T5): A med 60.2 km/h (IQR 2.4), B med 60.0 km/h (IQR 3.7)
  C06 Bico de Pato (T10):      A med 46.9 km/h (IQR 0.7), B med 46.8 km/h (IQR 1.3)
  C08 Junção (T12):            A med 35.4 km/h (IQR 3.2), B med 36.8 km/h (IQR 6.7)
  C07 Mergulho (T11):          A med 44.4 km/h (IQR 22.0), B med 42.1 km/h (IQR 23.6)
  C09 Subida dos Boxes:        A med 73.1 km/h (IQR 8.0)
  Reta / Outro:                B med 66.1 km/h (IQR 84.7)
```

### Síntese Diagnóstica e Erratas R1–R4 Ratificadas
1. **Confirmação estatística da queixa do dono**: O composite reduz contatos no bolo, mas 83,6% das suas saídas de pista acontecem com pista limpa (sem carro a menos de 15 m nos 5 s prévios), contra 46,7% no v10-cego (+36,9 pp, ICs disjuntos).
2. **R1 (Consistência aritmética Q1×Q2)**: Fechamento perfeito e comprovado. Nos artefatos brutos e scripts, C09 (Subida dos Boxes) no Perfil A sempre teve 0 saídas solo (0/7 = 0,0%). O número 87 computado na revisão adveio de um erro de digitação no markdown do relatório anterior (onde constou erroneamente 42,9% = 3 saídas para C09-A). Zero números moveram no código ou CSVs gerados. A soma das curvas no Perfil A é 25 + 22 + 21 + 16 + 0 = 84, exatamente igual ao total solo de Q1 (84/180). No Perfil B, soma = 183 == total solo Q1 (183/219). O headline estatístico sobrevive íntegro.
3. **R2 (Dispersão de velocidades Q4 segregada)**: C01 e C06 apresentam dispersão ultrabaixa (IQR <= 3,7 km/h; C06 IQR 0,7 a 1,3 km/h = repetição determinística da linha de saída volta após volta). C07 (Mergulho) exibe dispersão ampla (IQR 22,0–23,6 km/h; velocidades entre 31 e 72 km/h indicando múltiplos modos de falha / tráfego residual). C08 Junção apresenta dispersão intermediária (IQR 3,2–6,7 km/h). Todas com velocidades medianas de 35–60 km/h, compatíveis com os raios das curvas.
4. **R3 (Métrica de concentração)**: Concentração refere-se a % de EVENTOS de saída de pista (91,7% em A e 78,1% em B nas top-4 curvas: Descida do Lago, Mergulho, Bico de Pato, Junção), não a tempo cumulado.
5. **R4 (Reconciliação e terminologia)**: Reconciliação classificada canonicamente como "dentro da tolerância pré-registrada (Δ <= 0,1 pp)" com delta de 0,0167 pp em A e 0,0133 pp em B.
6. **Mecanismo dinâmico**: 0% de spins; saídas acontecem por subesterço tangencial (59-65%) ou deriva lateral (35-41%).
Para o detalhamento exaustivo das 4 erratas, ver [ANEXO_SAIDAS_1_ERRATAS.md](file:///home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend/ANEXO_SAIDAS_1_ERRATAS.md).

### Disposição
- **Decisão A×B**: Permanece **ABERTA e CONGELADA** com o dono.
- **Insumos para próximo ciclo de treino (professor Monaco_v2)**: Curvas C01, C06, C07, C08 catalogadas como pontos críticos para revisão de dados de treino e DAgger.
- **Pools de seed**: 76–79 VIRGENS.
- **Suíte**: 25F/326P/3S mantida.

## PROF-MONACO-1 (2026-10-22) — professor-solo em Monaco_v2: FALSIDICAÇÃO-Q4 (PARE); Q1 reta-no-top-1; churn de reentrada
Ciclo READ-MOSTLY (prereg 2aa018c; nenhum reparo; instrumento =
saidas_verdict --track com golden Interlagos byte-idêntico). Orçamento 12/14
sims solo (re-smoke poupado); pools 70-79/76-79 INTOCADOS.

### Cadeia
99ec615 (P0: ANEXO ERRATA-SAIDAS-1-review verbatim + R5-a 23,6 + R5-b
11/20=55,0 + proveniência R1 VAZIA + NITs) → 2aa018c (prereg + errata
calibração §10) → 1ecf52d (instrumento --track + bateria multi-ep + Σ
fail-loud + 6 testes; golden provado) → 12 sims seriais → 205c2c6
(evidência + bateria + verificação V1-V3b) → fechamento.

### Resultado (bateria 600 s; TODAS as eps por braço bit-idênticas — V1)
| braço | fora | eventos | dur_med | cascata | limpa | wanderer |
|---|---|---|---|---|---|---|
| PROFESSOR solo-frozen | 56,93% | 41/ep | 6,8 s | **94,6%** (330,7 s/ep) | 5,4% | 0 |
| ALUNO v10-cego | 45,00% | 34/ep | 6,1 s | **92,4%** (254,5 s/ep) | 7,6% | 0 |

VEREDITO MECÂNICO (verbatim):
- **Q4-mecânico: FALSIDICAÇÃO-Q4 — aluno ABAIXO do professor com ICs
  DISJUNTOS (45,00 < 56,93) → PARE IMEDIATO** (rótulos inconsistentes com
  a premissa; nem herdado nem degradado).
- **Q1-mecânico: top-1 professor = RETA (50 excursões, 24,4%) →
  FALSIDICAÇÃO-Q1 report-only** → lead REJOIN-CASCATA (hairpin C06 κmax
  0,1602 só 7,3%).
- Q2: C11 22,0% / C04 14,6% / C12 9,8% top professor; C03 determinística
  (IQR 0,5 km/h); C04 prof é a única com SPIN (5).
- Q3: preso canônico do aluno = **237,0 s** (errata R6 da era: 1185 ticks
  × 0,2 s; o herdado 118 s dividia por 10) — vive DENTRO do churn cascata.

### Verificações (probe prof_monaco_f4.py)
V1: seeds 0-4 bit-idênticos por braço — SOLO+SECA+sem-variance = seed sem
canal (bateria = 1 realização + réplicas; ICs degenerados; comparação Q4
determinística). V2/V2b: bateria ≡ ADOÇÃO-H-2 bit-a-byte (aluno_s0 ==
aluno_Monaco_ep1; prof_s0 == metaA_mon_1; metaA era 600 s). Golden
Interlagos: 6 tabelas byte-idênticas pós-refatoração (teste permanente).

### Disposição
- PARE pela FALSIDICAÇÃO-Q4; escala ao orquestrador SEM coleta adicional.
- A×B ABERTA e CONGELADA (dono). Proposta de reparo (SÓ TEXTO, §5 do
  ANEXO_PROF_MONACO_1.md): re-entry/pacing pós-excursão do professor, não
  geometria. Suíte: ver Comandos (25F/332P/3S).

## FONTE-1 (2026-10-22) — aquisição externa: Jolpica drop-in PROVADO; âncora 1:14.165; OpenF1 sem-login; recomendação FONTE-2 (SÓ TEXTO)
Ciclo READ-MOSTLY (prereg 27ebff9; ZERO sims; ZERO treino; ZERO
canônico/loader/schema/requirements; caches congelados intactos).
Decisão do dono: SEM assinatura F1TV; migração gratuita.

### Cadeia
02ea59b (P0/F0: guarda anti-duplicata 0-commits + disclose-254 +
inventário classificado f0_inventario.md) → 27ebff9 (prereg ANTES dos
probes) → probes v1-v3 (commitados antes do uso; bug
ErgastMultiResponse corrigido; retry 1/2 logado) → 10/30 chamadas
logadas (probe_log.md APPEND-only) → fechamento.

### Resultado dos probes (teto 30; 10 consumidas; 0 sims)
| Probe | caminho | resultado |
|---|---|---|
| A1 circuits 2024 | fastf1.ergast (3.8.3 pinada) | 200; 24 circuitos; 1020 ms |
| A2 schedule 2024 | fastf1.ergast | 200; 24 corridas; **Monaco = round 8** |
| A3 lap_times (retry) | fastf1.ergast | 200; paging 30/pág; 7 ms (cache) |
| B1 circuits | REST direto (sem fastf1) | 200; 5322 B |
| B2 results | REST direto | 200; **FastestLap rank=1: 1:14.165** |
| B3 laps | REST direto | 200; min de página = artefato de paging |
| C1 sessions | OpenF1 | 200; Monaco 2024 = session_key 9516 |
| C2 car_data | OpenF1 | 200; 2,9 MB; 17.485 amostras; 10 campos (speed/throttle/brake/n_gear/rpm/drs…); SEM LOGIN |

- **P1 PASS**: a 3.8.3 PINADA já fala com a Jolpica (interface.py:35
  BASE_URL=api.jolpi.ca) — drop-in SEM upgrade. **P2 PASS**: âncora
  obtível (1:14.165 via results/FastestLap; paging de laps não serve de
  âncora). **P3 PASS**: OpenF1 sem login com telemetria histórica;
  position em endpoint separado (documentado, não consumido).
- **Rate limit observado**: NENHUM cabeçalho de limite nas respostas
  Jolpica; zero 429 (não pressionamos; fastf1 cacheia localmente).
- **F0**: (i)=3 / (ii)=2-legado / (iii)=mirrors / (iv)=caches; a
  classe (ii) não esconde nenhuma necessidade ATIVA de telemetria.
- **DISCLOSE-254** fechado: 254,5 s/ep = 1272,4/5 (tabela_anatomia);
  eps do B' originais bit-idênticos (conferidos ep1/2/3); "270 s/ep"
  não reconcilia — NIT aberto não-gating.

### Disposição
- [NOTA-DEP] atualizado com a decisão do dono e os achados (abaixo).
- RECOMENDAÇÃO FONTE-2 (SÓ TEXTO): adoção drop-in do plano metadado via
  fastf1.ergast e/ou REST direto; OpenF1 = candidata gratuita para
  telemetria histórica; decisão de dono.
- Suíte INVARIANTE 25F/332P/3S (zero código de produção).

## FONTE-2 (2026-10-22) — draw_track: mirrors → OpenF1 → ERRO LOUD; golden EXATO; preset silencioso morto
Ciclo de diagnóstico + 1 módulo novo (prereg 9ba3f8c; zero sims; código
novo: track_geometry_free.py + patch draw_track.py — MAIS NADA).

### Cadeia
3d29116 (P0: guarda + ACHADO-P0 arquivo:linha + mapa de acoplamento +
NIT Jolpica re-escrito como OBSERVADO) → 9ba3f8c (prereg) → módulo v1-v4 +
probe (5/10 chamadas; cache do payload p/ iteração offline) → f382938
(patch + golden + PNGs + 2 testes) → fechamento.

### Resultado
- **P1/GOLDEN**: mirrors desenhados = a fonte da verdade do simulador:
  Interlagos 4160,4 EXATO; Monaco 3335,2 EXATO (834 wp; hairpin C06
  κ0,1602 = PROF-MONACO-1); Spa 7003,2 (~7004 pinado, −0,01%).
  DISCLOSE preset×mirror Interlagos: preset 240 wp/4309,0 m (telemetria
  era) vs mirror 1131 wp/4160,4 m.
- **P2/OpenF1**: Monza 2024 (session 9590, driver 44): 575 wp,
  **5.756 m vs 5.793 oficiais (−0,64%)**. UNIDADE = DECÍMETROS
  (achado; razão 10× do bounding box). Location PESADO: 3,9 MB/7-9,5 s
  por sessão×driver (cache local implementado).
- **P4/fail-loud**: --track inexistente → SystemExit 3 + lista;
  preset antigo SÓ com --legacy-preset + AVISO LOUD.
- **Probes**: 5/10 chamadas (sessions ~0,7-1,3 KB <1,3 s; location 3,9
  MB/7-9,5 s); 3 métodos mortos documentados; PROBE-B (GPX) não
  necessário — orçamento devolvido.

### Disposição
- Comandos do dono: `draw_track --track monaco` (mirror instantâneo) |
  `--track Italy` (OpenF1 sem login) | `--track xyz` (erro com lista).
- env/loader/canônico/schema/requirements INTOCADOS; zero sims; pools
  70-79/76-79 INTOCADOS; caches fastf1 intactos. A×B intocada.
- Suíte: ver fechamento (esperada 25F/334P/3S).

## PROF-REPAIR-1 (2026-10-22) — pacing pós-reentrada do professor: PRIMÁRIA FAIL (52,47% ≥ 45,00%); GAP B/C → conservador; PARE
PRIMEIRO ciclo que modifica o professor (prereg fc0a939; baseline
PROF-MONACO-1 reusado; aluno 45,00% canônico não re-coletado).

### Cadeia
fc0a939 (prereg c/ mecanismo arquivo:linha + falsificações pinadas +
árvore A/B/C) → eb09171 (patch --prof-repair default-OFF; UM fator;
zona: só ProfessorRaceController + argparse) → cae63df/35f3baa (+2
testes) → 7 eps seriais (1 flag-OFF identidade + 1 flag-ON smoke +
5 bateria seeds 0-4) → 50ea3eb (evidência + ANEXO) → fechamento.

### Resultado vs baseline canônico
| métrica | baseline | repair | pin | veredito |
|---|---|---|---|---|
| fora% | 56,93 | **52,47** | < 45,00 | **FAIL** (−4,46pp, melhora insuficiente) |
| cascata | 94,6% | 94,4% | < 50% | **FAIL** (inalterada) |
| top-1 | Reta 24,4% | C11 22,0% | Reta não-top-1 | **PASS** |
| preso | 237,0 s | 277,2 s | < 118,5 s | **FAIL + REGRESSÃO** |
| bit-identidade flag-OFF | — | ≡ prof_s0 byte | obrigatória | **PASS** |

- Determinismo: smoke-ON ≡ bateria s0; seeds 0-4 bit-idênticos
  (degenerescência solo+seca — lição V1 confirmada de novo).
- Authority do eps repair: rejoin 52,3% + prof_repair 45,6% + professor
  2,0% — o carro cicla quase 100% do tempo entre borda e janela.

### Veredito (árvore §5 — GAP documentado)
A/B/C pinados NENHUM se aplica ao resultado (melhora parcial sem SECs
verdes nem regressão total). Resolução conservadora (fail-loud, sem
re-pin): **nenhum sucesso; reparo não promovido; --prof-repair =
RESEARCH default-OFF; professor segue não-viável como fonte de
rótulos; decisão (2ª rodada × abandonar) volta ao dono** com gap
quantificado: 7,47pp residual vs aluno; cascata intacta; preso piorou.

### Leitura (marcada; SÓ TEXTO o próximo candidato)
O pulso de pace NÃO é o motor dominante da cascata — o carro sai de
novo mesmo a 8-12 m/s dentro da janela. A TRAJETÓRIA de reentrada
(bearing à projeção+10 m) deposita o carro em ângulo incompatível
com os complexos C11/C04; próximo candidato: alvo de reentrada mais
ADIANTE (projeção +30-40 m / ponto de curvatura mínima — ângulo raso,
lição M2/FONTE-2). Ciclo próprio com prereg.

### Disposição
- Suíte: 25F/336P/3S (334+2; ver fechamento). Zonas proibidas
  intocadas; A×B intocada; pools/caches intactos; f1_env.py:81
  whitespace não-commitado (ruling).

## PISTA-IDENT-1 (2026-10-22) — resolução de pista: separada, mirror-first, fail-loud; 6 legacy curadas; zero sims
Ciclo de engenharia (prereg 3758661; a ressalva do dono — f1_env mistura
Gym/pista/FastF1 e resolve_track caía silenciosamente em Interlagos).

### Cadeia
3758661 (prereg + inventário T0) → 015ecaf (G1 módulo novo + G2
fail-loud) → 22d13ad (G3 wiring + mirror-first + case-fix; reparo do
teste monza) → 9b0f378 (+4 testes) → 135e409 (ANEXO) → fechamento.

### Entregas
- **G1**: `backend/domain/track_resolution.py` (resolve_track,
  aliases, FASTF1_*, load_track_frozen, TrackResolutionError,
  track_identity); f1_env RE-EXPORTA (imports existentes todos
  funcionam — compat provada por teste).
- **G2**: `allow_fallback=False` default → **TrackResolutionError com
  lista** (mirrors/CSV/OpenF1/preset-flag); `--allow-track-fallback`
  (eval) / kwarg (env) preservam o antigo com AVISO LOUD + [FALLBACK].
- **G3**: `track_identity()` (requested/efetiva/fonte/sha256/wp/L) no
  env (`self.track_identity` + warning LOUD) e no eval_teacher_solo.
- **MIRROR-FIRST** no resolve_track: canônicas instantâneas/zero-rede
  (shas 164876196eb12174/67ca11dc211c8c78/4b05f2c3bbc625fc) ANTES do
  FastF1 legado — o padrão FONTE-2 estendido ao treino.

### Suíte (o achado)
| | baseline serial (5beb1da) | final serial |
|---|---|---|
| falhas | 26 (livros: 25 — ±1) | **20** |
| passes | 335 | **345** |
| skips | 3 | 3 |
- **6 legacy CURADAS** (sintomas do fallback: passavam/falhavam contra
  o PRESET 240wp em vez da pista pedida): curvature_cap (κ 0,13>0,11),
  interlagos_v_plan, hairpin_frontal, wrap_fechamento,
  interlagos_hairpin_sign, fastf1_driver_database.
- **ZERO novas**; monza-test reparado (pass anterior = pista errada).
- **DISCLOSE**: 2 suítes concorrentes (minha violação) = falso hold_at
  (colisão /tmp/hold_smoke.csv); serial limpo o eliminou. LIÇÃO:
  suítes que rodam sims em /tmp compartilhado = sims em paralelo.

### Disposição
- Treino/eval sem flag = fail-loud com lista; identidade em toda
  execução. Produto race-runner INTOCADO (frozen direto, sha no log).
- Suíte: **20F/345P/3S** (+4 testes novos). A×B intocada.

## (registro anterior) FASE R13-GATE (2026-10-18) — 20 runs out-of-sample (seeds 10-19): VEREDITO R10 PERMANENTE
Prereg 2882a37 (limiares MECÂNICOS pinados do braço A 0-9; tolerância
adversa pré-argumentada; rótulo de clima do CSV w_trans; desfechos pré-
declarados). Braço A = composite (10 runs seriais); braço B = v10-cego
(10 runs seriais pareados). Working tree limpo no script de veredito
(scripts/r13_gate_verdict.py, commitado). Clima REAL que veio nos seeds:
adversos = {10 (DRY→CLOUDY→WET, 3 transições), 12, 13, 14}; secos = 6.
**GATE: FAIL — 3/10 seeds A passam (16, 17, 18); adverso 0/4; seco 3/6.**
Falhas por atribuição:
- cc > p75: s10 (601), s11 (600), s12 (613), s13 (781), s19 (877) —
  ~40-44% dos contatos envolvem carro FORA da pista (o fora e o cc são a
  MESMA frente: excursões RECUP-OFF gerando contatos no retorno).
- hesit > p75: s11 (21), s12 (16), s13 (14), s14 (16), s15 (20) — classe
  REJOIN-DIP domina em todos (7-13 de ~16-21) = a mesma frente única.
- paradas: SÓ s10 (10 > T-adv 8, clima WET real); floor 10/10 em TODAS.
- fora: TODAS dentro do limiar por clima (25,1-41,2 ≤ p75) — o critério
  re-ancorado de pista NÃO é o gargalo; o gargalo é CONTATO ligado à
  excursão, e hesitação pós-rejoin.
**COMPARAÇÃO PAREADA A×B (reporte cru — decisão INDEPENDENTE do gate):**
Δcc mediana ≈ −600 (composite 3-13× MENOS contatos em TODAS as 10 seeds);
Δpós-60s sempre negativo (−35 a −668); Δfora +2,2 a +9,6 pp (composite
sai MAIS); Δrol −34 a +23 s (adversos: composite mais lento em 3/4);
Δparadas: só s10 (+6); Δwand: só s10 (+4). O composite mantém a vantagem
de segurança em TODAS as seeds out-of-sample.
**VEREDITO (mecânico, pré-declarado): o composite ORIGINAL NÃO passa o
gate re-ancorado como política de produto. O veredito R10 (manutenção do
v10 como race default; composite research-grade) fica PERMANENTE com
confirmação out-of-sample de 20 corridas novas. A vantagem de contatos
é consistente (10/10 seeds) mas o custo em excursões/hesitações pós-
rejoin excede os quantis do próprio braço.**
FRENTE DOMINANTE unificada (todas as fases convergem): excursões de
pilotagem race-speed (R7b) → contatos no retorno (44%) → hesitação
REJOIN-DIP (57%) → paradas RECUP-OFF (100%). UMA frente, endereçada por
percepção de tráfego no RETORNO ou dados de weave com tráfego VIVO
(rota 2 do backlog — pré-condição documentada).

## (registro anterior) FASE R12-PILOTO (2026-10-18) — ERRATA #2 aceita; PASSO A fechado; PILOTO VERMELHO; autópsia completa
**PASSO A (zero runs; commit 85616af)**: ERRATA #2 (canária 1-carro: fora ≤25%
pela derivação 1,36× do baseline real 18,4%; papel = detector de falha
grosseira; aplicação simétrica). A.2(a) runner loga sha256 do residual
carregado (r12b b77adc68caef742a; r2 6a2dbf53a69fcac7) — fallback silencioso
morto. A.2(b) smoke offline COM TRÁFEGO VIVO: |r2−r12b| med 0,079 rad —
override end-to-end CONFIRMADO (campo-1 nunca exercita). A.2(c) g≡0 nos 4
CSVs — bit-identidade documentada. **A.3 FECHAMENTO ARITMÉTICO**: "5 voltas ×
132s" eram 5 CRUZAMENTOS incl. a LARGADA (t=1,4s) → **4 voltas COMPLETAS ×
131,5s = 526s ≤ 600s** — a contagem do sumário confundia cruzamento com
volta (corrigido na métrica). A.5 re-avaliação: r2 s0/s1 PASS sob ERRATA #2
(18,4 ≤ 25); H5' PASS → piloto destravado.

**PASSO B — PILOTO {0, 8, 9} (seriais; identity smoke por run; sha b77adc68)**:
| seed | métrica | A | r12b | Δ |
|---|---|---|---|---|
| 0 (seco) | cc | 334 | 716 | +382 (+114%) |
| 0 | fora% | 25,2 | 31,8 | +6,6 pp |
| 0 | hesit | 13 | 6 | −54% ✓ |
| 0 | rolante | 140 | 153 | +13 s |
| 8 (adv) | cc | 336 | 1061 | +725; wand 15→19 |
| 9 (adv) | pos60 | 96 | 32 | −64 ✓; wand −1 |
ÁRVORE (b1a852c): **H1 FALHA (fora +6,6pp), H3 FALHA (+13s), H4 FALHA
(cc +114%) — 3 de 4 no seed 0; VERMELHO. N=10 NÃO executado.**

**AUTÓPSIA (ordem pré-registrada)**:
(1) SKEW 0.C: r12b em campo denso = |r_norm| p95 1,91-2,26 << r2 (5,83-8,15)
— MAIS conservador, NÃO cauda explosiva; g ativo 22-31% (r2: 18-37%).
(2) SATURAÇÃO: refutada como mecanismo (p95 baixo).
(3) MECANISMO RESTANTE: nos ticks g>0 do s0, o r12b corre com th 0,24 vs A
0,36 e v_med 25 vs 19 (freia/corrige MENOS, anda MAIS RÁPIDO) — mudança de
estilo em 22% dos ticks com entradas de tráfego VIVO que ele nunca viu no
treino (skew). A hesit caiu (−54%) mas contatos dobraram: menos micro-
paradas, mais proximidade.
FALBACKS confirmados: GO 51% frágil (canto estrito 38% = NO-GO); r_win med
−0,058 (correção-alvo PEQUENA, dominada pelo ruído de interface 16d).
**CONCLUSÃO da frente weave/slide: retreino BC offline com interface 16d
incompleta NÃO transfere para o campo denso. Nenhum retreino adicional sem
aprovação.**

## FASE R12-CANÁRIAS (2026-10-18) —(registro anterior) — instrumento (a) executado; 4 runs bit-idênticos; controle falhou no LIMIAR (não no stack); PARE
Checagens 0.C-0.F executadas (skew 12d conhecido; |r_pred| p95 1,245 ≥ 0,15
— não colapsou; preset confirmado; grade 9 valores). Flags --n-cars e
--residual-override commitadas ANTES dos runs (b53687c, d4c8f14).
**Canárias (1 carro, frozen, 600s, seeds 0-1): r2≡r12b BIT-IDÊNTICOS nos 4
runs** (5 voltas, fora 18,4%, wanderers 0, rolante 132s) — wiring são por
construção (g=0 em campo de 1; o residual nunca atua; o stack carrega 5
voltas limpas). H5' ESTRITO: PASS (todas as diferenças zero).
**Controle positivo FAIL no limiar pinado (fora 18,4% > 10%)** — autópsia:
o NÚMERO foi calibrado às cegas p/ "solo limpo"; o v10 solo+frozen REAL é
~18% fora (off em s 1800-2400 e wrap; mediana on/off 34/8 m/s). O stack
não está quebrado (bit-idênticos provam); re-pinagar o limiar pós-número é
proibido → **PARE conforme o ramo pré-registrado; a revisão decide a
emenda do limiar** (proposta honesta p/ 1 carro: voltas ≥2, fora ≤25%,
wanderers 0 — calibrada no valor REAL do baseline). Piloto {0,8,9} NÃO
executado (árvore).

### ESTADO DO ATOR r12b (para a próxima sessão)
- residual_weave_r12b.keras/.npz salvos; dataset r12_dataset_weave.npz
commitado. Interface 16d OK com o runner (trocar --profile composite para
apontar o novo npz = 1 flag de diferença — via PROFILES ou flag nova).
- PRÓXIMA SESSÃO: (a) canárias honestas: rodar o v10 solo NO RUNNER frozen
(1 carro, 600 s, --profile composite) — o instrumento que o gate usa; OU
(b) se a revisão preferir, canárias de ENV com a pista frozen carregada
( requer instrumento novo pré-registrado).
- A fragilidade 0.A (GO limítrofe) + a perda de info 16d (|slip|, herr fora)
entram na autópsia se o piloto falhar.

## v15 FASE R12 (2026-10-17) — fechamentos + hesitações=REJOIN-DIP/CORNER-CRAWL (treinável); retreino autorizado

### Prereg 9ca161e (sha 65bc5048) commitado antes; REGRA NOVA registrada:
### script de veredito/decisão só roda com working tree limpo.

### 0.1 — ERRATA s9 (paradas do braço B): log dizia 7; recontagem CSV = 8
O stoplog do runner só registra episódio LIBERADO (contato/autonomia) — o
episódio do NOR (t0=593 s, dur 6,6 s) TERMINA COM A CORRIDA e escapa do log.
Verdade: B s9 = 8 (não 7); A s9 = 8. A tabela R10 corrigida: s9 paradas
A/B = 8/8 (não 8/7). IMPACTO NO VEREDITO R10: ZERO (D1 olha só o candidato;
o candidato tinha 6/8 e falha de qualquer forma). Instrumento: stoplog do
runner perde episódios no fim da corrida — métricas de parada contadas do
CSV daqui em diante.

### 0.2 — decomposição COMPLETA: identidade fecha 10/10 seeds
Δrolante = Δfora + Δhesit + Δparado + resíduo fecha (tol. 0,15 s) em todas
as seeds. ERRATA da frase R11: **"em clima adverso o composite é mais
rápido" era ERRADA** — s8: A=192,5 vs B=149,9 (A 42 s MAIS LENTO); s9:
153,7 vs 147,2 (+7 s). O correto: nos adversos o ΔFORA é negativo (o
composite passa MENOS tempo fora por volta) mas o RESÍDUO INTRÍNSECO
explode (s8: +70,9 s/volta) — o gap vem do envelope/estado, não do fora.
Leitura seca: gap 22,8 s = 11,1 fora + 8,3 intrínseco + ~3 hesit.

### 0.3 — MECANISMO DAS HESITAÇÕES (regra PINADA; braço A, 10 seeds)
Com o critério DO GATE (on-track): 132 episódios = **REJOIN-DIP 75 (57%) +
CORNER-CRAWL 33 (25%) + OUTRO 24 (18%); TRÁFEGO-YIELD ≈ 0.**
(Nota de critério: a primeira passada sem filtro on-track achou 1.881 eps,
98% dos "OUTRO" DURANTE off-track — micro-paradas dentro de excursões,
custo do fora, não da métrica hesitação; o gate sempre contou on-track.)
**RESPOSTA: hesitações ENTRAM na frente única das excursões** (57% são o
dip de reentrada pós-excursão; 25% corner-crawl treinável; o yield de
tráfego é marginal) → o retreino PODE ajudar; NÃO é preço estrutural.

### 0.4 — sensibilidade do GO 51% (report-only; regra R11 fica de pé)
Bairro estreito na dimensão ticks: ≥3 → 58%; ≥5 (pinado) → 51%; ≥8 → 19%.
subst/saída: mediana 5, p75 6, p25 0 — a massa está EXATAMENTE no limiar.
Variação ld/limiar rad não recomputada (exige re-rodar janelas); o GO
permanece pela regra pinada, com a fragilidade documentada.

### 0.5 — validação da reconstrução de pose: CONSISTENTE
κ alvo@10m reconstruído vs obs10 em 1000 ticks on-track: correlação 0,863;
erro mediano 0,0026 (2,5% da escala) — abaixo do ramo de 25%. O motor do
r11_03 é válido na trajetória dada (condição necessária, como registrado).

### 0.6 — quantis por CONDIÇÃO CLIMÁTICA (20 corridas; DRAFT p/ R13)
SECO (n=16): fora p50 25,5% / p75 29,9% | rolante med 138 s.
ADVERSO (n=4): fora p50 **50,25%** | rolante med 151,8 s.
DRAFT de re-ancoragem por clima (nada canônico; para o prereg R13):
- SECO: fora teto p75 ≈ 30% | rolante ≤ 148 (med+10) | paradas = 0 |
  hesit ≤ 10 (mediana comp seca + tolerância) | cc ≤ 800 (p75 seco)
- ADVERSO: fora teto p75 próprio (~55%) | paradas ≤ 6 (mediana do melhor
  braço) | rolante ≤ 160 | cc ≤ 1.500
- wanderers: mediana 0/seed; nenhum seed >3 (backlog, não bloqueador).

### DECISÃO 0.3 → PASSO 1 (retreino) LIBERADO: REJOIN-DIP+CORNER-CRAWL
### são treináveis (a frente é UMA); TRÁFEGO-YIELD não treinar contra (marginal).
### Execução do retreino + piloto {0,8,9} fica para a próxima sessão
### (dataset agregado + iterações DAgger com canárias — pesado; prereg
### próprio antes de qualquer treino, como registrado no prereg R12).

## v15 FASE R11 (2026-10-17) — trilha pós-gate: paradas=RECUP-OFF 100%; gap de pace 49% explicado; weave/slide GO (51%); re-ancoragem draft

### 0.0 — FECHAMENTO DE RESSALVAS R10 (prereg 98c8fd8, sha dee6aa19)
0.0.1 Dif ca6b827→4bb7993 do script de veredito: UMA mudança
(`T.arm.startswith` → `T.arm.str.startswith` — accessor pandas). Constantes
(10pp/15s/+3) e ordem lex intocadas (diff completo acima). DESVIO DE
PROCESSO documentado honesto: o fix ficou em working tree na hora do
veredito (script crashou AttributeError na 1ª execução; veredito rodou com
o fix; fix+docs commitados juntos em 4bb7993).
0.0.2 Estatística: o script usa MEDIANAS POR BRAÇO; o prereg R10 dizia
"mediana pareada". Computadas AMBAS: sinais unânimes em cc/pós60/rolante/
hesit (10/10 seeds); fora misto (8+/2−). VEREDITO ROBUSTO à escolha —
D1 falha (paradas≠0) e D3 falha (rolante Δmed +22,5>15; hesit +10>3) nas
DUAS estatísticas.
0.0.3 Apêndice com unidades: disciplina 0,01% dos ~183k ticks normais;
cobertura por TICK pré-saída 0,1% (13.547 ticks); o "8/100" era por GRUPO
(seed,drv) — GRUPO≠SAÍDA (não computado por saída); lead "3.700 ticks" é
artefato de agregação (janela=30). VEREDITO NÃO SEPARA permanece (0,1% vs
50% por tick — 3 ordens de magnitude).

### 0.1 — MECANISMO DAS 14 PARADAS: 100% RECUP-OFF (subproduto das excursões)
Todas as 14 paradas do composite (s8: 6, s9: 8) começam COM o carro
off-track ou ≤5 s após o fim de um episódio off — nenhuma engarrafamento,
nenhuma hesit-cascata isolada. **Paradas = SUBPRODUTO das excursões** (o
crawl de retorno a 8 m/s com recovery às vezes demora ≥3 s). Contraste
s8×s9: cego s8=14 paradas (vs comp 6); s9=8 (vs 8 — empate). CONCLUSÃO:
cortar excursões corta paradas — a frente é UMA (pilotagem), não duas.

### 0.2 — GAP DE PACE (mediana +22,8 s): 49% explicado por Δ(fora+hesit+parado)/volta
Decomposição DIFERENCIAL por seed (Δcusto A−B por volta): mediana
11,1 s do gap de 22,8 s vem de fora/hesit/parado (quase tudo fora);
resíduo mediano 8,3 s. Em clima adverso (s8-9) o composite é até MAIS
rápido (Δ fora negativo). CONCLUSÃO: cortar fora% É a alavanca principal
do D3 (metade do gap), com componente intrínseco de envelope ~8 s.

### 0.3 — VIABILIDADE WEAVE/SLIDE: **GO** (51% — apertado)
924 saídas avaliadas; o PROFESSOR (pure-pursuit simulado offline) comandaria
correção substantiva (>0,15 rad de diferença) em ≥5 ticks da janela pré-saída
em **471/924 = 51%** (mediana de ticks substanciais: 5; p90: 12). Limiar
pinado ≥50%: GO. Nota honesta: apertado — o envelope do aluno em metade das
saídas JÁ contém o comando do professor (limite do retreino: ganho máximo
~metade das saídas).

### 0.4 — DRAFT DE RE-ANCORAGEM (nada canônico; para a revisão)
Corpus 20 corridas (A+B). SECO (16): fora p50 25,2 / p75 29,7 / p90 30,5% |
rolante med 139 s | cc p50 756. ADVERSO (4): fora 46,6% | rolante 150 s.
PROPOSTA: fora teto p75-seco 30% | rolante med+10 = 149+10=159 s... (valores
exatos no relatório; a revisão aprova/corta). Os critérios PRÉ-CANÔNICOS
(fora ≤1,5%, rolante ≤115 s) são 3-7× mais estritos que TODO o corpus
legítimo — referência histórica de um regime não-reproduzível (R7b).

### DECISÃO DA FASE: 0.3 = GO → PASSO 1 (retreino) autorizado pelo prereg;
### execução fica para a próxima sessão (escopo + orçamento: o dataset weave/
### slide precisa de extração dedicada + iterações DAgger com canárias por
### iteração — pesado). Fila: PASSO 1 (retreino dirigido) → piloto {0,8,9} → N=10.

## v15 FASE R10 (2026-10-17) — GATE DE PRODUTO N=10 pareado: MANUTENÇÃO do v10; composite research-grade

### Prereg + script de veredito MECÂNICO commitados ANTES dos runs B (ca6b827).
Braço A = CSVs R7a (não re-rodar — não-invasão provada R8); braço B = 10 runs
sequenciais novos, UMA diferença (ator v10/edge). Smoke B PASS (ator conferido).
Apêndice 2ª ordem (zero runs): NÃO SEPARA (cobertura 0,1% vs 50%).

### TABELA POR SEED (medianas no pé)
| seed | cc A/B | pós60 A/B | fora% A/B | rolante A/B | hesit A/B | paradas A/B |
|---|---|---|---|---|---|---|
| 0 | 334/1427 | 83/797 | 25,2/22,1 | 140/136 | 13/3 | 0/0 |
| 1 | 323/1401 | 69/753 | 30,5/22,8 | 154/136 | 12/3 | 0/0 |
| 2 | 523/1213 | 362/850 | 31,9/23,0 | 174/134 | 18/1 | 0/0 |
| 3 | 946/1003 | 184/347 | 30,4/23,3 | 154/136 | 12/2 | 0/0 |
| 4 | 268/1072 | 106/341 | 29,7/26,1 | 165/137 | 21/2 | 0/0 |
| 5 | 272/711 | 16/264 | 25,8/21,2 | 139/135 | 10/1 | 0/0 |
| 6 | 190/1072 | 100/392 | 31,5/22,2 | 162/135 | 14/3 | 0/0 |
| 7 | 756/1232 | 234/731 | 29,5/22,8 | 164/136 | 20/5 | 0/0 |
| 8 (clima adv) | 336/5138 | 136/4602 | 53,6/59,4 | 192/150 | 7/0 | 6/14 |
| 9 (clima adv) | 203/2925 | 96/1942 | 46,6/46,9 | 154/147 | 4/0 | 8/7 |
**Medianas**: cc 328,5 vs 1222,5 | pós60 103 vs 742 | fora 30,45 vs 22,9 |
rolante 158 vs 136 | hesit 12,5 vs 2,0 | wand 0/0 | preso 0/0.

### VEREDITO MECÂNICO (script commitado, regra pinada antes dos números)
- **D1 SEGURANÇA: FAIL** — cc e pós60 do composite são ESMAGADORAMENTE
  melhores (328 vs 1222; 103 vs 742), MAS paradas do candidato ≠ 0
  (seeds de clima adverso 8/9: 6 e 8 paradas; o cego: 14 e 7).
- **D2 PISTA: PASS** — fora 30,45 ≤ 22,9+10; wanderers 0≤0; preso 0≤0+5.
- **D3 PACE: FAIL** — rolante 158 > 136+15=151; hesit 12,5 > 2+3=5.
→ **MANUTENÇÃO DO v10 como race default; composite PERMANECE research-grade**
com D1/D3 documentados como limitações de produto.

### DECLARAÇÃO DE PRODUTO (o que o usuário ganha/perde em cada cenário)
Com o **v10-cego (default mantido)**: pace previsível (136 s), quase zero
hesitações, menos fora-de-pista no seco (22,9%) — ao custo de 3-4× mais
colisões (mediana 1222) e, em clima adverso, quase-destruição do campo
(semente 8: 5138 contatos, 14 paradas). Com o **composite (research-grade)**:
3-4× menos colisões SEMPRE (328) e clima adverso sobrevivível (336 vs 5138
— a percepção de tráfego é a diferença entre corrida e demolição), ao custo
de +7,5 pp de fora, +22 s de volta e +10 hesitações. A regra pinada
priorizou zero-paradas e pace do incumbente: o composite ainda não passa.

### Fila pós-gate (aprovação da revisão)
1. DAgger weave/slide (trilha de melhoria principal; risco v14b/c/d) — os
   estados-alvo (saída a 0,81×v_allow, weave, slip-regime) estão
   caracterizados; a assinatura de 2ª ordem NÃO separa (apêndice: cobertura
   0,1%) — o retreino deve mirar o PADRÃO completo, não um gatilho simples.
2. Paradas em clima adverso (D1): os wanderers/paradas dos seeds 8-9 existem
   nos DOIS braços (composite MENOS: 6/8 vs 14/7) — a causa comum é o clima
   adverso + post-spin (R6); candidato a correção de camada de RECUPERAÇÃO
   (não de comando — família encerrada).
3. Re-ancoragem absoluta dos critérios (fora ≤1,5%/rolante ≤115 são
   pré-canônicos): proposta de novos limiares à distribuição honesta na
   próxima fase de gate.

## v15 FASE R9 (2026-10-17) — falsificação OFFLINE: AMBOS os candidatos MORTOS; família camada ENCERRADA; zero runs

### Prereg de análise commitado ANTES (2e5159d, sha bd6d279b): limiares pinados
(disciplina ≤0,5%; lead med ≥5 ticks; cobertura ≥50%; morte do B se <30%).

### 0.1 — calibração do motor: REPROVADA no critério pinado (80-91%), causa
diagnosticada e é um defeito ADICIONAL da R8: o κ@10m é ASSINADO — com curva
à direita à frente o canal fica negativo, max(0,·) colapsa o cap a 0 e o
clip ZERA o esterço (linhas steer=0,0 com log ativo). O veredito R8 (refutado)
vinha do RUN (fora 2,4× pior, clip 88-92%) e fica MAIS sólido. Os candidatos
A/B morrem por DISTRIBUIÇÕES DIRETAS (motor-independentes) — a limitação da
calibração não afeta o veredito (honestidade do prereg: condição necessária).

### 0.2 — candidato A (slip-cap): MORTO por DISCIPLINA — 43,9-47,1% (limiar 0,5%)
slip>θ em ticks NORMAIS: 91-97,7% (θ=5-15°) — a política dirige em slip alto
PERPETUAMENTE (estado normal de compensação do understeer 1,45×); a janela
pré-saída tem a condição ativa em 35,2% vs 45,8% nos normais — SEM separação
(a janela é ativa MENOS que o normal). O sintoma "16,8° nas saídas" não é
sintoma: é o regime de operação.
### 0.3 — candidato B (rate-limiter ρ): MORTO por SEPARAÇÃO — 0,2% (morte <30%)
ρ(p99,5)=2,73 rad/s (disciplina inerente 0,5%); rate-spike pré-cruzamento em
0,2% das saídas (ρ p99,9: 0,0%) — o comando gerador é OFFSET SUSTENTADO, não
yank. A taxa não separa. Número registrado.
### 0.4 — círculo-de-atrito: descartado por construção (a_lat das saídas
3,9-5 m/s² ABAIXO do limite; o comando impossível é absorvido pelo understeer).

### ÁRVORE EXECUTADA: AMBOS MORTOS → PARE — FAMÍLIA CAMADA ENCERRADA
Nenhum mecanismo de CAMADA sobre o comando de esterço separa normal de saída:
- valor absoluto (κ-cap): refutado no piloto R8 (disciplina 88-92%);
- valor condicionado a slip: morto offline (slip alto é o regime NORMAL);
- taxa: morto offline (offset sustentado, não yank);
- círculo-de-atrito: morto por construção (a_lat sub-limite nas saídas).
O diagnóstico estrutural fecha: as saídas vêm do PADRÃO de comando da política
(imitação do professor sem o feedback pursuit), não de eventos separáveis no
comando. ESCOLHA DA REVISÃO (pré-registrada):
  (a) DAgger weave/slide — retreino com pré-gate do professor + âncora solo
      (risco documentado: v14b 2/3 → v14c 1/5 → v14d 0/3); OU
  (b) GATE-FIRST — re-ancoragem dos critérios à distribuição R7a e promoção
      com a limitação de fora% documentada (29-54% pela pilotagem atual).
Custos: R9 gastou ZERO runs (a R8 gastou 10 para o mesmo tipo de veredito —
a regra offline-first pagou-se imediatamente).

## v15 FASE R8 (2026-10-17) — steer-governor: MECANISMO REFUTADO pelo piloto (disciplina 88-92% vs gate 0,5%); PARE sem adoção

### PASSO 0 (R5c, zero runs) — porta PASSOU, mas com a lição do viés
97% (894/924) das saídas pilots têm |δ| > cap(2×atan(L·κ@10m)) no cruzamento
(δ/cap 11,6×) → porta de saída PASSOU. Cap-only (14/924 com herr>20° e δ≤cap).
Inventário: 2160 eps = 2134 rápidos (rejoin bearing FUNCIONA) + 26 wanderers
(concentrados s8-9) + 1092 churn encadeado. PROPOSTA wanderer p/ gate (fase de
gate): mediana 0/seed e nenhum seed >3 episódios.

### REGRA NOVA CUMPRIDA (achado 9099235): prereg (PREREG_R8_STEERGOV.md,
sha 9519d157) + código + 5 testes COMMITADOS (cf04f88) ANTES do 1º run ON.
Não-invasão PASS: OFF bit-idêntico ao baseline R7a (0 diverg em 52×30000).

### PASSO 2/3 (piloto N=10 sequencial) — DISCIPLINA FALHA, VERMELHO TOTAL
| seed | fora% ON (OFF) | steer-gov% ativo (gate ≤0,5%) |
|---|---|---|
| 0-9 | 65,4-75,7 (OFF: 25,2-53,6) | 87,7-92,1 |
**O cap clipa 88-92% dos ticks ON-TRACK e o fora PIOROU ~2,4×** — a política
usa esterço alto COM κ baixo em direção NORMAL (pursuit/correção): até
k_comp=25 clipa 30% dos ticks normais. RE-DERIVAÇÃO (sem piloto): NENHUM
k_comp satisfaz a disciplina 0,5% — mediana normal 2,7× vs saídas 23,1×
separa MEDIÂNICAS mas as caudas se sobrepõem por construção (κ≈0 na reta).
O contrafactual 97% do 0.2 era VIÉS DE SELEÇÃO (upper bound registrado como
tal; a verdade só o piloto mediu — e mediu o contrário).

### VEREDICTO R8 (árvore: disciplina falha → PARE — re-derivar → inviável)
**Steer-governor como CAP κ-CINEMÁTICO é MECANISMO ERRADO — refutado.**
Default permanece OFF (nunceu se tratou de adoção). DAgger de estados
weave/slide VOLTA À FILA como proposta primária (a rejeição era condicionada
ao diagnóstico do governor mostrar que o cap expressa a correção — mostrou
que NÃO expressa). Candidatos de MECANISMO p/ proposta futura (não
implementados): (a) cap condicionado a slip (clipar só com |slip|>10°, o
sintoma das saídas); (b) limitador de TAXA de esterço (derivada, não valor
absoluto); (c) DAgger weave/slide (retreino — risco documentado v14b/c/d).

### LIÇÕES R8
1. Contrafactual em eventos (amostragem só nas saídas) SUPERESTIMA o efeito
   de um cap — a distribuição NORMAL do comando é o denominador que falta.
2. Regra nova funciona: commit-antes-de-run + disciplina-gate no resumo
   pegaram a falha no 1º seed (o gate do runner imprime o PARE).
3. Redirecionamento de shell cria .log VAZIOS na raiz (restos da tentativa
   127) — sempre confirmar cwd/ls antes de ler outputs.

## v15 FASE R6 (2026-10-17) — SEMEADURA DO CLIMA + descoberta do NÃO-DETERMINISMO PARALELO (corrige a leitura da R5a)

### A ÚNICA mudança (aprovada): semear o RNG do clima
`weather_rng_from_seed(run_seed)` (domain/weather.py): sha256("<seed>//weather")
→ random.Random DEDICADO; `--weather seeded|fixed` (fixed = prob transição 0,
kind travado — braço de controle). CSV v3.1 aditivo: w_kind/w_grip/w_trans por
tick + tyre_life/tyre_grip por carro-tick + weather_seed e transições na
FONTE. Testes 3/3 (tests/test_weather_seed.py: reproduzível por seed, diverge
entre seeds, instância dedicada).

### ARQUEOLOGIA 1.5 — por que os gates v14 "eram determinísticos"?
O WeatherModel com rng NÃO semeado existe desde 6a63758 (18/set, commit
fundacional do domínio) e o engine sorteia transições POR VOLTA desde
ff49b39 (commit do engine) — TODA corrida desde sempre foi bilhete de
loteria: P(transição real em 600 s) ≈ 45-50% (≈50 sorteios de 5% × 25% de
mudança de kind). Os pares v14/R2 que "bateram" (1352×2, 309×2) eram os runs
sem transição — seleção sobrevivente, nunca determinismo. O B3.1-verde (223)
é UMA extração dessa loteria.

### VALIDAÇÃO 1.4 — TODA PASS (sequencial)
- mesma seed ×2, 600 s COMPLETOS: BIT-IDÊNTICOS (30000×52) — a guarda
  literal da R5a fecha.
- puro vs instrumentado (RACE_DIAG_NO_CONTACT_LOG=1), 600 s: 0 divergências
  em colunas físicas — guarda DEFINITIVA do instrumento.
- seeder vivo: seed 2 sortou DRY→CLOUDY na volta 2; seeds 0/1 sem transição
  (streams distintas); testes 3/3 (tests/test_weather_seed.py).

### DESCOBERTA DE PROTOCOLO: o SEED é knob DE CLIMA (e nada mais)
Sem --mixed/--shuffle, np.random.seed NÃO é consumido pela corrida; o único
consumidor do seed é o rng do clima (que só altera a física QUANDO há
transição). Verificado BIT-IDÊNTICOS: comp s1≡s0; blind s1≡s0; fixed ×3 ≡
comp-seca. **As "3 seeds" de cada grupo são 1-2 realizações, não 3.** TODA
a "variância multi-seed" das fases R2-R5 era (a) loteria do clima NÃO semeada
e (b) ruído de contenção paralela — o seed NUNCA amostrou variância da
corrida. Um gate multi-realização HONESTO precisa de um mecanismo semeado
de variância de corrida (ex.: jitter de grid com rng dedicado) — proposta R7,
1 variável, aprovação.

### PASSO 2 — re-medida SEQUENCIAL (realizações distintas, não "medianas de 3")
| realização | cc-verdade | pós-60s | fora% | voltas | rolante | preso>60s |
|---|---|---|---|---|---|---|
| comp SECA (s0≡s1) | 511 | 308 | 29,3% | 10/10 | 144 s | 0 |
| comp CLIMA s2 (DRY→CLOUDY@2) | 813 | 610 | 31,0% | 10/10 | 166 s | 0 |
| cego SECO (s0≡s1) | 892 | 250 | 22,6% | 10/10 | 136 s | 0 |
| cego s2 (clima próprio) | 1112 | 470 | 22,2% | 10/10 | 133 s | 0 |
| comp FIXED | ≡ comp SECA bit-idêntico | | | | | 0 |

### DESCORBERTA R6 (validação 1.4): NÃO-DETERMINISMO POR EXECUÇÃO PARALELA
- mesma seed ×2 em LOTE PARALELO (3 sims simultâneos): DIVERGEM em t≈2,6-4,6 s
  (fase de largada, contatos); mesmos runs SOZINHOS: BIT-IDÊNTICOS.
- SEQ (R6, sozinho) ≡ R5a-guard (R5a, sozinho) BIT-IDÊNTICOS — as mudanças
  R5a/R6 não tocam a física; weather seeding + logging v3.1 limpos.
- **CORREÇÃO RETROATIVA DA R5a**: as 6 re-medidas R5a eram lotes paralelos —
  o "derby" do comp s0 (cc 6103) era uma realização de CONTENÇÃO, não uma
  realização legítima do seed 0 (diverge do SEQ em t=4,6 s). As tabelas
  R5a (i)-(vi) caracterizam realizações válidas de corrida, mas o RÓTULO
  "seed N" não era chave reproduzível. As medianas R6 SEQUENCIAIS as
  substituem.
- PROTOCOLO PERMANENTE: corridas de medição/guarda são SEQUENCIAIS (sem
  sims concorrentes na máquina); execução paralela de sims = variância
  não semeada extra.

### TABELAS (i)-(vi) e ÁRVORE DE ATRIBUIÇÃO EXECUTADA
(i) Acima (realização-rotulada; medianas de 3 "seeds" seriam degeneradas).
(ii) Atribuição das raízes (comp seco): PILOTAGEM 77 (74%), CONTATO(imp10s)
     17 (16%), PNEU late-race 10 (10%), CLIMA 0% (s2: 3% perto da transição
     — sens. ±30 s não muda). Histograma por minuto: uniforme (6-15), SEM
     spike pós-transição.
(iii) **DISCRIMINADOR (comp seco, 77 pilotagens): mediana v0/v_allow = 0,81;
     OVERDRIVE (>1,10×v_allow) só 13% (10/77); 87% SAEM ABAIXO DA VELOCIDADE
     PERMITIDA**, com esterço mediano 0,72 rad (cinemática ~5× o círculo de
     atrito a 18 m/s) e freio forte em 43. Bandas κ: reta 28 / média 32 /
     curva 17. → **RAMO EXECUTADO: "v0 ≈ v_allow e sai mesmo assim" =
     PROBLEMA FÍSICO-DINÂMICO — auditoria de FÍSICA (modelo lateral em
     saída de curva / understeer a comando), NÃO policy.**
(iv) Derby s0 (cc 6103 na R5a): realização de CONTENÇÃO PARALELA — diverge
     do SEQ legítimo em t=4,6 s; sem transição de clima. Didático: loteria.
(v) C1 REALIZAÇÃO-MATCHED (sequencial): **a vantagem de contatos do
     composite VOLTOU**: comp 511 vs cego 892 (seca; −43%) e 813 vs 1112
     (clima; −27%) — a tabela R5a "sem vantagem" era ruído paralelo. Fora%:
     comp PIOR (29-31 vs 22-23) — o composite evita CONTATO e sai MAIS da
     pista (comportamento consistente em todas as fases). PROVISÓRIO (N=1
     por condição); gate N≥10 exige antes o mecanismo de variância (R7).
(vi) Wanderers: **0 episódios >60 s em TODAS as realizações sequenciais**
     — o modo das R3/R5a (9/30) não sorteou sem contenção; a persistência
     (salto de braço) fica pendente de episódios para analisar.

### VEREDICTO R6
1. Clima: causa MENOR de saídas (0-3%) — mas o custo por transição é real
   (+302 cc, +22 s de pace no s2). --weather fixed NÃO vira modo de gate
   (o clima é parte do produto); o gate amostra tickets de clima por seed.
2. Pilotagem: 74% das raízes, mas o discriminador manda o fix para a
   FÍSICA: carros saem a 0,81×v_allow com comando ~5× o orçamento de
   atrito. **PRÓXIMA FRENTE: auditoria do modelo lateral (fase 4 do
   apply_control) em saída de curva + a relação comando-vs-fricção do
   _action_to_controls** — NÃO policy, NÃO residual, NÃO retreino.
3. Produto: composite reduz contatos 27-43% vs cego (matched), ao custo de
   +7-8 p.p. de fora%. Gate de corrida segue VERMELHO (fora 29-31% > 1,5%).
4. R7 propostas (aprovação): (a) mecanismo semeado de variância de corrida
   (jitter de grid c/ rng dedicado) para o gate multi-realização; (b)
   auditoria de física do lateral; (c) R5c wanderer-persistência (aguardar
   episódios).

## v15 FASE R5a (2026-10-17) — INSTRUMENTO DE CONTATO AUTORITATIVO: proxy da R4 RETRATADO; pilotagem RE-CONFIRMADA; realização domina

### Pré-registro 2026-10-17T14:55:45Z (hipóteses H1-H4 + árvore + preso T=60s).

### PASSO 1 — instrumento (ZERO mudança de comportamento; física intocada)
- Coletor OPT-IN em `PyBulletPhysics` (engine/physics.py): colhe `getContactPoints`
  por SUB-STEP (1/240 s) após cada stepSimulation; por PONTO de contato
  chassis×chassis: par, posição, normal, força c[9], impulso J=F·dt,
  |Δv|=J/m por corpo (3ª lei), XY de ambos. Desligado = zero custo (env/tests).
- CSV v3: TODAS as colunas preservadas + `imp_events/imp_dv/imp_dv_max` por
  carro-tick + eventos crus em `<out>_events.csv` + cabeçalho de versão +
  sha256 da pista na linha FONTE (`load_track_frozen` expõe `frozen_sha256`).
- Testes 3/3 (tests/test_contact_instrument.py): colisão central scriptada
  (log do solver explica Δv observado; 3ª lei; |Δv|≈closing/2); solo = 0
  eventos; mapeamento sub→tick EXATO. NOTA do solver: também faz SEPARAÇÃO
  POSICIONAL (resolve sobreposição em <24 sub-steps).

### GUARDA 1.3 — a história completa (árvore: guarda falhou → debugou → instrumento EXONERADO)
- Literal (re-run s0 vs CSV R4): FALHOU. A/B com código R4 PURO (worktree
  a5abb8e) FALHOU IGUAL → não é o instrumento.
- **CAUSA-RAIZ (não-determinismo entre processos): `WeatherModel.rng =
  random.Random()` NÃO SEMEADO** (domain/weather.py:159) — transições reais
  de clima (5%/volta/carro) mudam o grip e divergem a realização daquele
  instante (medido: ontem t=97,2s; hoje t=137,2s; 5 processos sem transição
  ≤160s). PRE-EXISTENTE desde o recurso de clima — explica por que B3.1
  nunca foi re-mensurável bit-a-bit entre sessões (refina a hipótese "float"
  da R2: a fonte é o RNG do clima, não ruído numérico).
- GUARDA REAL PASS: puro ≡ instrumentado BIT-IDÊNTICOS por 160 s (janela que
  cobre largada + fase densa + ambos os onsets de clima observados);
  prefixo do run completo ≡ segmento; PYTHONHASHSEED irrelevante (A≡B).
- **Proposta R5 (comportamento, 1 variável, aprovação): semear
  `WeatherModel.rng` por seed da corrida** — reprodutibilidade bit-a-bit
  entre sessões; NÃO implementado nesta fase (regra READ-ONLY).

### PASSO 2 — re-medida (6 runs de hoje; composite 0 transições, cego s0/s1 1)
(i) **Fator flag→verdade (composite): 1,01 / 1,08 / 1,40 (mediana 1,08)** —
    o flag 5Hz era quase honesto como CONTAGEM de ticks; cobertura flag⊆eventos
    173/173…6103/6103 (falsos positivos ~0). Árvore: **razão ∈ [1,1; 1,5)**.
(ii) **RETRATADO o "70% contato-não-amostrado" da R4**: com o solver, raízes
    com impulso 10 s antes = 17/20/12% (mediana ~17%). O proxy |Δv|>2 m/s
    capturava FREIO PRÓPRIO + entrada na grama, não empurrão. Ambiguidade
    brk>0,3 RESOLVIDA: frenagem própria. **PILOTAGEM RE-CONFIRMADA dominante:
    76/81/97 pilots por seed (80-88% das raízes), ~50/50 residual/solo,
    v0 mediana 18-22 m/s, esterço 0,55-0,79 — saídas em VELOCIDADE DE CORRIDA
    (o perfil v≈10 do R4 era dos ECOS pós-rejoin).** O ramo pilotage da R3
    volta a ser a frente dominante — agora com dados do solver.
(iii) rejoin-gerador: 1% / 23% / 95% (mediana 23% < 30% da árvore) — o claim
    de 68% da R4 era de 190 flag-ticks de UMA realização. R5b (rejoin com
    gap) DESCLASSIFICADO de "a frente" para "uma frente" (real em s2).
(iv) Tempo fora: s1/s2 dominado por ECOS (72-75%); s0 por raízes+preso
    (61%+38%; 2 wanderers, ambos vítimas de fling c/ impulso 10 s antes —
    H4 confirmada p/ wanderers).
(v) Eco: gap 5/10/20 s → raízes 146-175 / 92-110 / 48-58 (padrão estável).
(vi) Wanderers: entrada por impulso+spin (R5c: estabilizar braço da projeção
    segue como candidato, agora com evidência de entrada).

### C1 RE-PINADA — o claim de produto "3-4× menos contatos" RETRATADO
| run | cc_flag | cc_VERDADE | pos60_v | fora | pace | preso>60s |
|---|---|---|---|---|---|---|
| cego s0-s2 | 806/439/608 | 1003/521/709 | 434/154/142 | 45,9-48,7% | 192-210s | 0/2/0 |
| comp s0-s2 | 6103/595/116 | 6156/641/162 | 5508/410/40 | 44,5-51,2% | 179-217s | 2/0/0 |
Medianas: cego 709 vs comp 641 pares-tick — **SEM vantagem do composite em
contatos nas realizações de hoje**; pós-60s comp PIOR na mediana (410 vs 154,
puxado pelo derby s0: 2 carros em contato contínuo por centenas de s).
**VARIÂNCIA DE REALIZAÇÃO DOMINA: cc do comp s0 = 251 (ontem) → 6103 (hoje,
mesmo seed/código) = 24×.** Qualquer A/B a 3 seeds é frágil demais para
claim de produto.

### ÁRVORE EXECUTADA + VEREDICTO
1. Razão ∈ [1,1; 1,5): **v3 = instrumento canônico**, fatores por run;
   números R4 re-pinados onde o instrumento importa.
2. Ramo "proxy era o artefato" (mediana 1,08 < 1,1): **RETRATAÇÃO formal do
   "70% contato-não-amostrado"**; ramo pilotage RE-ABERTO e CONFIRMADO.
3. R5b rejoin-com-gap: abaixo do threshold na mediana — mantém como proposta
   secundária. R5c wanderer: entrada confirmada (fling), proposta mantida.
4. **Nova frente #1 (evidência): pilotagem race-speed (80-88% das raízes,
   ~50/50 residual/solo)** — caracterização M0-style (onde na pista, o que a
   obs via, g/kappa/r por saída) antes de qualquer fix.
5. **Protocolo**: A/B de produto exige N≥10 seeds (ou variância reduzida pós
   RNG do clima); mediana de 3 é insuficiente para claims de produto.

### Artefatos R3
- Fix: `scripts/run_race_10_cars.py` (bearing law + REJOIN_AHEAD_M/REJOIN_BEARING_GAIN).
- Testes: `tests/test_deep_rejoin.py` (sintético PASS 15,7 s);
  `tests/test_race_layer.py::test_rejoin_gains_authority_off_track` atualizado
  p/ lei de bearing; suite 61 pass + 1 skip (2 falhas PRÉ-EXISTENTES registradas:
  import `_resample_closed_polyline` inexistente; curvature-cap no preset 240wp).
- Instrumentação: `race_diagnostic` imprime FORA-PILOTAGEM vs FORA-PRESO
  (janelas 30 s), CARROS-PRESO/sessão e HESITAÇÕES; `scripts/gate_multi_seed.py`.
- CSVs/logs: `race_diag_b31_v3_seed{0,1,2}.{csv,log}`. Mudanças NÃO commitadas.

## Proveniência dos preregs (R8→R13)
Os preregs e vereditos commitados no ciclo (2882a37 R13-prereg,
20a6042 R13-veredito, 3d4f0e9 fechamento, 0c5892c/97f3ad9 v3.3,
cab38ed dossiê, cf04f88/4a61bf1 R8, 2e5159d/6bda0c3 R9, 98c8fd8/79df2cc
R11, 9ca161e/85ca849 R12) vivem preservados na tag **`v15-audit-trail`**
(cab38ed) — a trilha completa de 65 commits R2→R13. O squash v15.0
preserva o CONTEÚDO; a HISTÓRIA de medição está na tag.

## Próximos passos recomendados

0. **v15 PÓS-R5a (prioridade — re-pós da re-medida com instrumento canônico)**:
   - **Frente #1: PILOTAGEM race-speed** (80-88% das raízes; ~50/50
     residual/solo; v0 18-22 m/s, esterço forte): caracterização M0-style
     SÓ LEITURA (onde na pista, o que a obs via nos ticks de saída: g_gate,
     kappa por preview, d_min, r_norm) ANTES de qualquer fix. A hipótese
     "residual manda mal" e "solo erra" ficam EMPATADAS — a caracterização
     decide.
   - **Semear o RNG do clima por seed** (1 variável, comportamento — precisa
     aprovação): elimina a componente entre-sessões do não-determinismo;
     A/B intra-dia vira bit-reproduzível; prerequisite para A/B de produto
     confiável.
   - **A/B de produto exige N≥10 seeds** (mediana): 3 seeds mostrou-se
     frágil (cc comp s0: 251→6103 entre dias). Alternativa: métrica por
     VOLTA (taxa), não total de 600 s.
   - R5b rejoin-com-gap: DESCLASSIFICADO p/ secundário (mediana 23% < 30%);
     manter proposta p/ realizações onde domina.
   - R5c wanderer: entrada por fling CONFIRMADA (impulso 10s antes);
     estabilizar braço da projeção segue candidato.
   - CONCLUÍDO em R5a: instrumento solver-side canônico (v3, testes 3/3);
     guarda com causa-raiz nomeada (RNG do clima); retrações R4 registradas.
1. **v15 FASE 2b FECHADA (Exp1+Exp2 — gate VERMELHO nos dois; professor
   que passa LIMPO não alcançado)**:
   - Exp1 (machine-only): PASS 0→0,01-0,06% ✓, mas passes = empurrões
     (lateral med 0,00; s1: 60 pós-larg; Monza 1484/858).
   - Exp2 (margem 2,75 desde PREPARE + commit por GAP d<30): Interlagos
     pós-largada 60→0 ✓ e total 296 ✓; Monza 1484→1383 (751 pós-larg ✗);
     mas passes Interlagos 0 ✗ (meta ≥2), Hungaroring 4 passes/0 pós-larg,
     lateral mín mediana 0,00 m ✗ (a janela ±25 am. inclui a aproximação
     pré-offset; a margem materializa-se DEPOIS do cruzamento em Δv baixo).
   - **PRÓXIMA HIPÓTESE (proposta, NÃO implementada — usuário decide)**:
     a margem com α=0,15 leva ~3 s para materializar; a janela de commit
     (d<30 m a Δv≈2 m/s) é ~15 s, mas o CRUZAMENTO ocorre com offset ainda
     ~1-1,5 m. Opções: (a) margem desde o FOLLOW-lento (antecipar o
     deslocamento ao detetar líder com v_o < v_plan·0,9 — usa o próprio
     corredor existente como "pré-abertura" controlada); (b) suavização
     dependente de gap (α sobe para 0,4 quando d<40); (c) aceitar 2,5 m e
     alargar a janela de latmin para ±10 am. pós-cruzamento (o offset
     materializa-se 2-3 s DEPOIS de cruzar — a manobra é limpa, o instrumento
     é que mira o momento errado). MEDIR a curva Δlat×tempo por passagem
     antes de escolher.
   - FASE 2c: medição Δlat×tempo (árvore PRÉ-registrada) achou o BUG
     INVERTIDO da conclusão; corrigido (2 sítios, +3 testes). Re-gate:
     máquina opera (PASS% ×10) mas contatos 534-1470 — ESTRUTURAL (12 m de
     pista, ~0,75 m de folga p/ 2 rodagens em curva).
   - FASE 2d (Exp3, árvore pré-registrada 19:46:01Z): reta-timing
     (janela v_plan ≥0,9·v_ego em gap+8+3s·v+40 m) + diferencial PLANEJADO
     (v_plan_ego > v_o×1,03) + pré-abertura no FOLLOW-lento. Re-gate 5
     corridas: **0 passes líquidos em TODAS** (janela tão restritiva que
     nenhuma manobra completa: 337 PREPAREs, 14% aborto, 0 concluídas);
     falsificação OK (homogêneo = 0 ✓); Interlagos volta a 296/0 pós-largada.
     **ÁRVORE RAMO 3: TETO ACEITO** — o professor follow é o produto
     aprovado (gate v14: 240 contatos, 0 pós-largada); ultrapassagem fica
     "com atrito documentado" como limite do stack atual. **FASE 3
     DESBLOQUEADA COM RÓTULOS FOLLOW-ONLY** (a redução de contatos da
     FASE 3 nunca precisou de passagem; o professor follow é aprovado
     desde o gate v14).
2. **Monaco (Meta B' restante)**: o hairpin R=6,4m exige dados de treino em curvatura extrema (procedural com R<8m) OU mudança na física. Sem isto, Monaco 0/3 é o teto.
3. **Meta C (91,2s)**: racing line (otimização de curvatura mínima dentro das bordas) ou MPC no professor. O pure pursuit perde 15s/volta. O PPO não é caminho (3 falhas estruturais).
4. **Ultrapassagem deliberada**: fora do escopo do professor (ele ensina
   follow). Se o v14c ainda ficar preso atrás de fantasmas no --hold-at, o
   caminho é rotulagem específica de passagem — nunca às cegas.

## PISTAS_EXPAND_1 (2026-10-23) — mirrors reais via OpenF1: gate Δ<1% reprova 7/9 (racing-line); LasVegas congelada; Suzuka: razão entre magnitudes dos erros de comprimento = 6,0×; ZERO sims

Ciclo de AQUISIÇÃO (prereg 8afec70 + PATCH_PISTAS_EXPAND_1_A 51da2d8; commits:
script 6395354 → T0 d5bb170 → pins 48a16f2 → fixação-3 3eac9be → dados 81866bd →
testes 96947fa → ANEXO 25589b2). 17/25 chamadas OpenF1 logadas APPEND
(experiments/pistas-expand-1/probe_log.csv); cache backend/cache/openf1_pistas_expand_1
(NOVO, distinto dos fastf1; streams TODOS em cache = reprocessar sem rede).

**T0 (achados)**: Hungaroring_v1 e Zandvoort_v1 EXISTEM (era telemetria, out/16) →
reclassificação (c)→(b) ratificada pelo PATCH_A; oficiais da §1 CONFIRMADOS 9/9 pelo
f1db (race.course_length 2024 — SEM re-pin §7); v1s estão −2,6% a −4,8% abaixo do
oficial (Monza 5641,9 vs 5793; Hungaroring 4177,7 vs 4381; Zandvoort 4053,2 vs 4259;
Suzuka 5534,8 vs 5807).

**Resultado por pista (manifest = verdade)**:
| pista | classe | L OpenF1 (m) | oficial | Δ | status |
|---|---|---|---|---|---|
| Hungaroring | (b) | 4320,8 | 4381,0 | −1,37% | FAILED (gate) |
| Silverstone | (c) | 5810,8 | 5891,0 | −1,36% | FAILED (gate) |
| Montreal | (c) | 4295,9 | 4361,0 | −1,49% | FAILED (gate) |
| Bahrain | (c) | 5298,0 | 5412,0 | −2,11% | FAILED (gate; P1 VER salto 784 m → P2 PER) |
| Mexico | (c) | 4236,4 | 4304,0 | −1,57% | FAILED (gate) |
| Zandvoort | (b) | 4171,3 | 4259,0 | −2,06% | FAILED (gate; top-3 com 1 salto) |
| Suzuka | (b) | 5761,6 | 5807,0 | −0,78% | **COMPARADO** (candidato GRAVADO, v1 intacto) |
| LasVegas | (c) str | 6139,1 | 6201,0 | −0,998% | **OK CONGELADO** (case-exata `LasVegas`) |
| Miami | (c) str | 5330,5 | 5412,0 | −1,51% | FAILED (gate; P1 NOR salto 320 m → P2 VER) |

**ACHADO MECÂNICO (a leitura central do ciclo)**: o gate Δ<1% (pinado no prereg com a
prova Monza −0,64%) reprovou 7/9 — TODOS os deltas são NEGATIVOS porque o v4 extrai a
LINHA DE CORRIDA (corta curvas) e a re-amostra 10 m mede cordas (< arco). Monza é a
pista mais indulgente do calendário; sinuosas/rua encurtam 1,3-2,1%. O gate é mais
estrito que o acervo canônico (interlagos_v2 é −3,45% vs oficial). SEM re-pin
pós-número — FAILED honesto; a DECISÃO (aceitar × novo ciclo com gate re-derivado
MECANICAMENTE antes de qualquer run) é do dono.

**Comparativo (b) v1 × OpenF1**: Suzuka 5534,8 (−4,69%) × 5761,6 (−0,78%); a razão
entre as magnitudes dos erros de comprimento é 6,0× (272,2 m ÷ 45,4 m; sha
72807c529604ee6c; freeze = dono); Hungaroring 4177,7 (−4,64%) × 4320,8
(−1,37%) = 3,4×; Zandvoort 4053,2 (−4,83%) × 4171,3 (−2,06%) = 2,3× — TODOS os
contornos OpenF1 são melhores que os v1s do acervo (e melhores que o interlagos
canônico). PNGs de conferência via draw_track --csv (zona proibida SÓ chamada):
experiments/pistas-expand-1/png/{LasVegas_v2,Suzuka_candidato}.png.

**Golden §4 PASS TOTAL**: canônicos 3/3 bit-idênticos; v1s 5/5 intactos;
anti-substituição 5/5 (nenhum {key}_v2.json não-autorizado no path frozen —
t_pe1_carrega/t_pe1_manifest estruturais); shas recalculados == manifest; 17/25.

**Suíte**: baseline serial REAL 20F/345P/3S (175,53 s) → FINAL serial 20F/349P/3S
(177,89 s) — as 20 falhas BIT-A-BIT idênticas, +4P = t_pe1_* 4/4 (data-driven do
manifest; o congelamento seletivo do PATCH_A não deslocou contagem — §8 satisfeito
sem desvio).

**Disclosures**: cwd-flip ×2 (sem efeito; absolutos); /tmp de tasks background é
EFÊMERO — tee/log do baseline foram reclamados, comparação itemizada feita contra as
listas capturadas no registro da sessão (LIÇÃO: logs de medição → worktree no mesmo
passo); manifest exibe −1,0 (arredondamento 2 casas) mas o gate avaliou −0,9982%;
1 salto 320-784 m por stream em 4 pistas (regra de avanço §2.2 + fallback documentado);
AGUARDA_DONO/NAO_EXECUTADO do PATCH_A ficaram não-usados (Silverstone reprovou antes do
candidato; esticamento EXECUTOU com teto); stray antigo backend/backend/ANEXO_SAIDAS_1_
ERRATAS.md permanece (fora do escopo FIXAÇÃO 3; backend/worklog.md → archive 3eac9be).

**Decisões do dono (fila)**: (1) gate Δ<1% — aceitar 7 FAILED × novo ciclo com gate
re-derivado mecanicamente (streams em cache = zero rede p/ reprocessar); (2) Suzuka —
congelar Suzuka_v2.json? (erro de comprimento do candidato com módulo 6,0× menor;
1 linha de aprovação); (3) LasVegas_v2
pronta via load_track_frozen('LasVegas') — adoção no pool --tracks = ciclo próprio;
(4) A×B e PROF-REPAIR-1 seguem abertas (inalteradas por este ciclo).

## GATE-RE-DERIVE-1 (2026-10-23)

Prereg congelado em `194a709`, sobre o v0 verbatim `e58e8c4`; erratas E1/E2
em commit separado `b28e100`. Resultado report-only: não há holdout independente
por pista; os dez streams históricos e seis alternativos foram extraídos do
cache pelo v4, mas os 16 falham o limite estrutural pré-registrado de 120 m/s.
Nenhuma pista histórica ficou elegível para LOO; nenhum fold ou limiar global
foi produzido. Suzuka também tem auto-interseção em uma medição histórica e
nos dois alternativos; LasVegas e Suzuka permanecem sem promoção/flip.

Sem rede, gravação em path frozen, mudança de pool ou simulação de produto.
Auditoria reproduzida bit a bit; detalhes, hashes e resultados individuais em
`backend/experiments/gate-re-derive-1/PARE.md` e `audit.json`. Suíte serial:
20F/349P/3S, mesmas 20 falhas do baseline registrado `1a228b8`; quatro testes
adicionais passam. Rótulo: “349 testes, com 20 falhas bit a bit estáveis
('regressão estável conhecida') e 3 skips”.

## FAIL-FORENSICS-1 (2026-10-23) — PARE por inconsistência da âncora

Prereg `1e9ceee` e veredito offline `d631a46` foram commitados antes das
simulações. A corrida 1, Interlagos cego, e a corrida 2, Interlagos Composite,
foram seriais, seed 0, clima DRY sem transições e 6000 ticks. Em ambas, CSV e
contatos solver-side reproduziram os arquivos F4v15 byte a byte; hashes e
identidade de pista constam em `backend/experiments/fail-forensics-1/`.

**PARE após a corrida 2:** o pin do estado/pedido declara 13 hesitações; o log
original `2_allcomposite.log` e o CSV âncora produzem 14 pelo classificador
atual. O código de contagem é legado desde `439f402`. Sem evidência de mudança
de simulação/ambiente, o problema é a contradição do registro de âncora. Prereg
mantido intacto, sem re-pin pós-número. As duas corridas Monaco não rodaram;
não houve classificação causal nem conclusão sobre saltos de projeção. A
retomada requer ratificação do dono e prereg novo.

Artefatos: `experiments/fail-forensics-1/PARE.md` e `relatorio.md`; dois CSVs,
dois `_events.csv` e dois logs preservados. Nenhum mecanismo de comportamento
foi tocado.

## ERRATA FF1-E3 (2026-10-23) — hesitações Composite: 14

Ratificação do dono: para a âncora Composite Interlagos F4v15 governa **14**.
O valor 13 nas linhas canônicas do B3' foi substituído apenas na tabela e no
veredito acima, com proveniência no log original (`2_allcomposite.log:71`), na
recontagem do CSV frozen e na reprodução FAIL-FORENSICS-1b. O veredito B3'
continua FAIL por HESIT ≤3; o veredito primário ANTI-D3-1 também continua FAIL.
O prereg, script, relatório e PARE congelados da sessão FAIL-FORENSICS-1 não
foram editados. Referências `13` em narrativas históricas permanecem verbatim;
esta seção é a errata aditiva.

Reconciliação do ANTI-D3-1-P1 (`8c79ee6`): a extração histórica contou 13
episódios **on-track**; o episódio adicional na contagem canônica é NOR,
167,4–167,8 s, inteiramente off-track (`recovery_rejoin`, `th=0,35`,
`g_gate=1`, `|r| máx=1,59`), portanto excluído pelo filtro on-track do P1.
Para os 14 episódios totais: `g_gate>0` em 13/14 e `|r|>0,1` em 14/14. No
subconjunto on-track do P1 ficam 12/13 com `g_gate>0`; isso reconcilia os
denominadores sem alterar sua leitura histórica nem o veredito.

Suite baseline executada antes da errata: 21 falhas, 348 passes, 3 skips. A
falha excedente foi `test_state_files_doc_integrity`: um resumo anterior
removeu o prefixo exigido `> Última atualização:`. O contrato foi restaurado
nesta errata; não há teste que pine 13 e nenhum teste foi alterado. Suite
pós-errata: **20 falhas, 349 passes, 3 skips**, as 20 falhas conhecidas
esperadas e sem falha documental excedente.

## FAIL-FORENSICS-1b — pausa operacional antes de R3 (2026-10-23)

Prereg `16910ef` e instrumento `ad5a88d` estão commitados. Selftests golden
passaram para as âncoras Interlagos, Monaco professor/aluno, dados repetidos
s0–s4 e salto sintético. Nenhuma corrida R3/R4 foi iniciada.

As duas invocações R3 encerraram em `load_track_frozen`, antes do carregamento
do ator/engine: `--track monaco` procurou `monaco_v1.json`; `--track Monaco_v2`
procurou `Monaco_v2_v1.json`. Não há CSV válido nem comparação de âncora. O
alias correto, confirmado por preflight read-only, é `--track Monaco`, que
resolve `Monaco_v2.json` (SF 0, 834 wp, short SHA `67ca11dc211c8c78`). A errata
operacional está em `experiments/fail-forensics-2/ERRATA_R3_TRACK_ALIAS.md`, e
os dois logs foram preservados. Como a contingência pré-CSV prevista já foi
usada, aguardar autorização do dono antes de qualquer nova invocação; R4
depende do gate byte-a-byte de R3.

## FAIL-FORENSICS-1b — fechamento da Etapa 1 (2026-10-23)

Após autorização do dono, R3 foi executada com `--track Monaco` e passou no
leak-check: CSV byte-idêntico a `prof-monaco-1/aluno_s0.csv`, SHA-256
`f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0`. R4
Composite Monaco (10 carros, 6000 ticks, seed 0) foi executada como primeira
medição exploratória **N=1**: 43,15% fora, 29 episódios de contato solver-side
(110.794 pontos), 12 hesitações e 45 saltos de projeção ≥30 m pelo proxy
`|Δs_wrapped − Δcum_dist|`. O veredito offline classificou as 14 entradas;
recuperação predomina nos eventos Monaco. Limite: não há XY nem índice bruto
de `nearest_segment`; a recomendação para Etapa 2 é instrumentá-los e revisar
corredor/bordas de Monaco. B3' e ANTI-D3-1 continuam FAIL. Sem alteração de
comportamento, checkpoints, pools ou dados frozen. Relatório e SHAs em
`backend/experiments/fail-forensics-2/EXECUCAO_FAIL_FORENSICS_1B.md` e
`backend/experiments/fail-forensics-2/veredito/relatorio.md`.

## LOC-XY-1 (2026-10-23) — PARE no gate 3

Baseline pré-código: **20F/349P/3S**. O ciclo registrou a decisão do dono de
usar o resultado aritmético **20F/352P/3S** para três testes novos. A
implementação aditiva (`race_diagnostic.py`) e exatamente três testes foram
commitados (`4d22d65`); o prereg e o log de baseline foram congelados antes do
código (`5fe4ff8`).

A suíte pós-código terminou em **21F/351P/3S**. As 20 falhas canônicas são as
mesmas do baseline; a falha adicional é
`tests/test_mixed_composite_wiring.py::test_t_regression_v10_cego_bit_identico`,
que compara o header/corpo completo contra um fixture v3.3 de 49 colunas e
rejeita as 3 colunas v3.4. Os três testes LOC-XY passaram. Conforme o gate,
PARE imediato: sem smoke formal do gate 4, sem selftests golden e sem qualquer
correção/reexecução. As suítes baseline e pós-código executaram o subprocesso
de corrida de 1.200 ticks do próprio teste de regressão; seus CSV/eventos
temporários foram removidos após a falha. O log completo e hashes estão em
`backend/experiments/loc-xy-1/relatorio.md`.

O patch só lê `phys['x']`/`phys['y']` do getter existente e calcula
`Track.nearest_segment` global; não tocou controle, governor, física, ordenação
ou contadores. O teste de serialização do kill-switch reproduziu o fixture
v3.3 byte a byte, mas não houve prova de corrida completa. A decisão posterior
do dono está registrada na errata E-XY-2 abaixo.

### ERRATA E-XY-2 — retomada e PARE atualizado no gate 3 (2026-10-23)

Errata aditiva ratificada pelo dono: o teste legado
`test_t_regression_v10_cego_bit_identico` roda no caminho default v3.4 e
compara a projeção dumb `split(',')[:49]` em cada linha, incluindo header,
com o fixture pré-wiring v3.3. Nome/path não mudam; a linha de contrato foi
adicionada ao docstring. `RACE_DIAG_NO_XY=1` segue como caminho de restauração
v3.3 completo para saídas de arquivo.

A suíte seguinte resultou em **21F/351P/3S**, fora do ratificado
**20F/352P/3S**. A regressão legada corrigida e os três testes LOC-XY passaram;
as 20 falhas do baseline persistiram e `test_state_files_doc_integrity` falhou
fora do conjunto canônico por uma entrada histórica da cadeia `> (anterior:)`.
PARE imediato: zero smokes formais de 6.000 ticks e zero selftests golden
pós-código; pools e pistas frozen intocados. SHA-256 do log
`4_post_fix_pytest.log`: `37527575cf3b889d65819f920e6fa0216f00817549674c9fe07e053371f1d675`.
O relatório antigo de PARE e seus logs `0_baseline`/`3_post` permanecem como
histórico.

### ERRATA E-XY-3 — fechamento após correção documental (2026-10-23)

E-XY-3 corrigiu exclusivamente a linha 6 deste arquivo, restaurando o ponteiro
para o relatório FAIL-FORENSICS-1b; commit doc-only `29cf2a2`. A suíte completa
reexecutada depois passou o gate 3: **20F/352P/3S**, lista de 20 falhas
idêntica ao baseline, sem nova ou ausente. SHA-256 do log
`5_post_chain_fix_pytest.log`:
`7dcda10548478604dbcf36a65a16b89b2ea085f60b4d202b7d096cfe6d349185`.

Gate 4: Smoke A (`RACE_DIAG_NO_XY=1`) byte-idêntico à âncora v3.3
`47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`.
Smoke B: projeção legada idêntica incluindo header; 52 campos totais e
`body_x,body_y,ns_raw` finitos/preenchidos, com índice inteiro dentro dos 1131
waypoints. Selftests `fail_forensics_verdict.py` e `saidas_verdict.py` PASS.
Orçamento encerrado em 2/2 smokes formais, zero corridas de medição, pools e
pistas frozen intocados.

Regra permanente para futuras entradas de cabeçalho/cadeia: incluir um
ponteiro `Ver <path>` e fechar a entrada com `)` para continuar íntegra quando
for rebaixada a `(anterior:)`. Relatório final e hashes de todos os artefatos:
`backend/experiments/loc-xy-1/relatorio.md`.)

## PROJ-FIX-1 (2026-10-23) — PARE na reconciliação NIT-2 (Ver `backend/experiments/proj-fix-1/PARE.md`)

- Prereg e classificador offline v1.0 congelados antes do replay no commit
  `a519081`; selftest sintético PASS. Uma corrida R4 Composite Monaco N=1,
  seed 0, alias `Monaco`, foi executada com writer v3.4 default.
- g1 PASS: as 49 colunas projetadas, incluindo header, são byte-idênticas à
  âncora FF1b R4. g2 PASS: 71 campos por linha, X/Y finitos e `ns_raw` inteiro
  válido. Replay: 30.000 linhas; clima sem transições.
- O seletor congelado da fonte NIT-2 encontrou zero entradas sob o run id
  preregistrado, contra 112 eventos ≥10 m e 45 ≥30 m esperados. PARE antes da
  saída de classificação/mapeamento; nenhuma classe C1/C2/C3 é reportada e o
  script não foi editado após esse resultado. Retomada exige prereg novo para
  resolver a identidade do run histórico e versão/selftest novo do instrumento.
- Sem correção de comportamento, sem nova medição ou smoke; pools e pistas
  frozen intocados. Artefatos e hashes em `backend/experiments/proj-fix-1/PARE.md`.

## PROJ-FIX-2 (2026-10-23) — PARE em g4 (Ver `backend/experiments/proj-fix-1/PARE_PROJ_FIX_2.md`)

- Prereg e classificador offline v1.1 congelados antes da classificação no
  commit `8222dff`; selftest sintético PASS. A suíte não foi reexecutada e a
  referência permanece 20F/352P/3S.
- g0–g3 PASS: hashes dos artefatos conferem; projeções do replay/âncora são
  byte-idênticas; replay tem 71 campos/30.000 linhas; seletor NIT-2 retorna
  112 eventos ≥10 m e 45 ≥30 m para `composite_monaco`.
- g4 acionou PARE no evento `('ALO', 2130, 2132)`, sem classe XY/ns_raw. Não há
  classificação completa, mapa 1:1 ou resumo C1/C2/C3/p95; nenhuma conclusão
  de classe ou proposta de correção é feita. O classificador v1.1 não foi
  alterado após o resultado.
- Zero corridas de medição novas e zero smokes; controles, física, pools e pistas
  frozen intocados. Logs e hashes estão no anexo do PARE.

## PROJ-FIX-3 (2026-10-23) — PARE em g0 (Ver `backend/experiments/proj-fix-1/PARE_PROJ_FIX_3.md`)

- Diagnóstico da única chave ALO registrado antes do freeze; sem outros eventos
  ou agregados examinados. Classificador v1.2 e selftest sintético congelados no
  commit `2330e9f` antes de qualquer contagem por classe.
- g0 parou porque o prereg congelado esperava SHA `a3e7dd18…` para o relatório
  PARE v2, mas o arquivo preservado tem SHA `e287e5bd…`. Os demais hashes g0
  registrados conferem. O prereg não foi editado após o gate.
- g1–g4 não foram executados; não há mapeamento, contagens ou p95 C1–C5. Zero
  simulações/smokes; controles, física, pools e pistas frozen intocados.

## PROJ-FIX-4 (2026-10-23) — classificação offline C1–C5 (Ver `backend/experiments/proj-fix-1/EXECUCAO_PROJ_FIX_4.md`)

- Retificação de proveniência: o PARE v2 tem SHA-256 `e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c` em disco e nos snapshots commitados; `a3e7…` veio de rascunho não commitado. P3 ficou intocado.
- Freeze P4 `574c5ea` (prereg SHA-256 `0d9c8d31bfee6470d045cedea46c25264b3ba5d12d757116e75a300554219392`); selftest recheck PASS (SHA `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127`). Manifest `75666b3`, SHA `5715be7b663394e29cc9b2a21a2baf554ccdb9281cc6d25439651d38e0b641ee`, 18/18 PASS. Classificador v1.2 intacto.
- g1/g2 PASS: projeção legada `a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`; 71 campos/30.000 linhas, XY finitos e `ns_raw` inteiro de 0 a 833. Log SHA `617ef75e8cae3aa556e8e362c5e54a8099f6446b734c3bb836040a5839807a10`. g3 confirmou 112 eventos ≥10 m e 45 ≥30 m.
- g4 fechou 112 = C1 0 + C2 0 + C3 46 + C5 66; headline 45 = C1 0 + C2 0 + C3 45 + C5 0. Chaves únicas, sem C4 inválido; ALO (2130,2132) é C5. Mapa C5 1:1: `backend/experiments/proj-fix-1/classificacao_v12/mapa_nit2_ge10.csv`. No C5, `offtrack=1` em 66/66. Mapa SHA `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f`; resumo SHA `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05`; validação SHA `e62d487948772713bb76959d21713fa575bcdc7dd63bc9f0de20cc9c18036f30`; relatório SHA `b4b8c6ca4bbf2c7514978e09fe2a2b826c1dfd44be7c2f827d68a96142642403`.
- Zero corridas/smokes; suíte de referência 20F/352P/3S não reexecutada; pools e pistas frozen intocados. Nenhuma correção proposta; escolha da Etapa 2 retorna ao dono.

## PROJ-GATE-1 (2026-10-23) — PARE em g2/g4 (Ver `backend/experiments/proj-gate-1/PARE_PROJ_GATE_1.md`)

V-A ficou implementada em modo opt-in e default-OFF. R1 reproduziu os hashes
congelados; R2 falhou o proxy de projeção e os limites de não-piora, enquanto
as 392 reaquisições passaram nearest-global. PARE sem suíte completa ou
promoção; CSVs, sidecars, logs e audit estão preservados com hashes duplos.

- **PROJ-GATE-2 (2026-10-24):** prereg congelado em `0a269ff`, audit v1.0 em `a6d6775`; proveniência/schema/samples passaram. `ns_raw` ficou fora do ramo local em 0/12.945 amostras OFF e 5/18.045 ON; g2 decompõe R1 ≥10/≥30 em C1/C2/C3/C5 = 0/0/46/66 e 0/0/45/0, R2 = 0/0/110/63 e 0/0/107/1. H1 não identificável, H2 sem leitura interna, H3 confirma que g2 não mede localidade; encaminhamento único: arquivar esta bifurcação. Zero simulações/smokes, suíte não executada, flag default-OFF e sem promoção. (Ver `backend/experiments/proj-gate-1/autopsia/5_veredito.md`.)

- TRAFEGO-MED-1B (2026-10-24): report-only, 52/65 séries elegíveis; recomendação única para medir espaço/lado para passar, sem implementação ou promoção. Ver `backend/experiments/trafego-med-1/4_DOSSIE_TRAFEGO_MED_1B.md`.

- PASS-1 (2026-10-24): suíte 20F/375P/3S com as 20 falhas conhecidas; R1/R2 g1/g2 PASS, mas mediana de volta e contatos g4 falharam; R3 bloqueada, sem promoção. Ver `backend/experiments/pass-1/5_EXECUCAO_PASS_1.md`.

- YIELD-1C (2026-10-25): execução standalone em `b9f9061` exit 0, CSV 30.000 linhas byte-idêntico a R1, mas zero yields/consumos; g2 FAIL, linha yield arquivada e pivô para Etapa 4. Ver `backend/experiments/yield-1/EXECUCAO_YIELD_1C.md`.

- COMPOSITE-MAP-1 (2026-10-25): inventário report-only congelado em `98a71e6` (blob==disco; 6 pins críticos conferidos pelo dono). Composite treinável pelo residual gating existente (solo v10 congelado); corpus medido bloqueado por conversor/rotulagem/split/proveniência — instrumentação ratificada como COMPOSITE-CORPUS-1, depois COMPOSITE-BASE-1 e COMPOSITE-TRAIN-1. Ver `backend/experiments/composite-1/PREREG_COMPOSITE_MAP_1.md`.

- COMPOSITE-CORPUS-1 (2026-10-25): report-only; módulo/testes focados passaram 7/7 e o censo de 38 fontes encontrou 0 elegíveis, 35 rejeitadas e 3 excluídas, com 26 `SEM_BLOB_HEAD`; sem treino/sim/inferência e sem tocar produção. Ver `backend/experiments/composite-1/PREREG_COMPOSITE_CORPUS_1.md`.
- COMPOSITE-COLLECT-1C (2026-10-26): g0 446 testes (20 canônicas, 423 passes, 3 skips; sem falha nova); conversão A/B validada, 30.000 registros/10 episódios/24.000-3.000-3.000 por caso, 20 shards e 2 audits; commits de proveniência `55b7d05` e `33c75ce`; sem corrida standalone ou treino. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_COLLECT_1C.md`.
- COMPOSITE-BASE-1 (2026-10-26): g0 pinado 453 testes (20F/430P/3S, log `db0abd33…`); 4 corridas formais R1-R4 exit 0 com 30.002 linhas e sidecars completos; extrator determinístico (hashes idênticos em 2 leituras); proveniência commits `7cb4f19` (12 artefatos) e `ceeaa20` (4 métricas); deltas Composite vs blind medidos (−36% a −44% contatos, +6,7pp fora em Interlagos); sem treino ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_BASE_1.md`.
- COMPOSITE-TRAIN-1 (2026-10-27): g0 pinado 460 testes (20F/437P/3S, log `bf051732…`); 2 treinos formais (Run 1 candidato + Run 2 réplica seed 42) concluídos exit 0; gates O-1 e réplica PASS (delta val_loss 0.0, max |dW| 0.0, NPZ SHA `6210fff6…` byte-idêntico); proveniência commit `c186ef2` (10 artefatos); sem corrida, simulação ou promoção. Ver `backend/experiments/composite-1/EXECUCAO_COMPOSITE_TRAIN_1.md`.
COMPOSITE-BASE-2 etapa B executada (agente, 2026-10-27): g0 460=20F/437P/3S fail-set canônico exato; R1'-R4' 4/4 gates (R2'/R4' blind BYTE-IDÊNTICOS ao BASE-1; override 6210fff6/6a2dbf53 nos logs); extração 8/8 determinística; commits ab9da45 (provenance) + 3a02c11 (metrics); EXECUCAO staged; zero PARE; bucket TEST selado intocado.
COMPOSITE-STAGE-5 etapa B executada (agente, 2026-10-28): desselo TEST em 2 leituras exit 0 (6.000 amostras A_VER+B_SAI); candidato 6210fff6 SANCIONADO (5/5 gates PASS: Huber 0.2885 vs null 0.7077 ratio 0.4077 <= 0.80; MAE 0.5856 < 1.0440; norm 1.5985 <= 2.0; nan/inf 0; determinismo cmp byte-idêntico exit 0); proveniência commit e017874; EXECUCAO staged; zero corrida, zero treino, zero promoção.
COMPOSITE-STAGE-6 promoção executada (agente, 2026-10-28): backup B3.1 (6a2dbf53/5a2c20ce) em archive/residual_promocao_stage6; PAR candidato (6210fff6/f237ac9e) assume produção; g0 pós 462=20F/439P/3S (460 canônicos + 2 testes do selo, ambos PASS; fail-set canônico exato, diff bit-a-bit — emenda de contagem do dono); R1''/R3'' sem override cmp byte-a-byte vs BASE-2 PASS; g3 residual baseline 6210fff65b19ad0e; commits c8270a5+608e671; EXECUCAO staged; zero PARE.
- REALISMO-1 C0 (2026-10-29): etapa B executada após freeze `240bacde`; 8 corridas OFF N=1..4 seriais, 32 extrações determinísticas, 2 relatórios de ruído byte-idênticos; g0 20F/458P/3S com fail-set canônico; sem mecanismo/promoção. Ver `backend/experiments/realismo-1/c0/EXECUCAO_REALISMO_C0.md`.
2026-10-30 REALISMO-1 C1 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C1.md.
2026-11-01 REALISMO-1 C2 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C2.md.
2026-11-02 REALISMO-1 C3 etapa B: matriz ON N=0..4 (10 corridas) + 2 controles OFF + 48 leituras de extração determinísticas + EXECUCAO_REALISMO_C3.md.
2026-11-03 REALISMO-1 C4 etapa B: análise offline de geometria (Tasks 10-11); 2.199 voltas filtradas; PARE duro em frame RMS (17,79 m > 5,0 m); ramo GEOMETRIA rejeitado; adoção do ramo FALLBACK (A5); zero corrida; C4_FINDINGS.md.
2026-11-04 REALISMO-1 C6 etapa B: matriz ON N=0..4 (20 corridas) + 4 controles OFF + 96 leituras de extração determinísticas + EXECUCAO_REALISMO_C6.md.
2026-11-04 REALISMO-1 C7 consolidação: matriz ON/OFF em N=5..8 (16 corridas) + 64 leituras de extração determinísticas + EXECUCAO_REALISMO_C7.md.
2026-11-05 REALISMO-1 promoção produção: defaults --rejoin-handoff align e --rejoin-ramp adotados no composite; suíte 20F canônica confirmada; RELATORIO_PROMOCAO_REALISMO_1.md.
2026-11-06 ABERTURA PERCEPÇÃO-1 + C8-rejoin: selados N=9..12 (confirmação C8) e N=13..16 (confirmação Fase 3); pools 76..79 e shards test/ intocados; PREREG_PERCEPCAO_1_F0.md e PREREG_C8_0.md.
2026-11-06 C8-0 referência: 10 corridas em N=0..4 (Interlagos e Monaco) + 40 extrações determinísticas cmp=0; EXECUCAO_C8_0.md.
2026-11-06 C8-B execução: 2 controles OFF cmp=0 + 10 corridas ON N=0..4 + 48 extrações determinísticas; gates primário/B-1/R-2/reentrada não aprovados; EXECUCAO_C8.md.
2026-11-06 C8-B errata: números agregados N=0..4 confirmam FAIL por B-1 (+48% contatos Interlagos, +17% Monaco) e R-2 (+1,9 pp fora Interlagos); voltas ON=354 passam R-1; PERCEPÇÃO-1 formalmente suspensa por falha do professor na Task 3 (sobreposição 94,1%).
2026-11-06 ABERTURA PROF-CURVA-1: teto de velocidade local no professor solo; PREREG_PROF_CURVA_1.md.
2026-11-06 PROF-CURVA-1 Task 2: referência solo 600 s Interlagos confirmada (4 voltas, 24,6% fora, 4 saídas crônicas C01/C06/C07/C08 em 100% das voltas; teto guarda ritmo <=123,05 s); REF_FINDINGS.md.
2026-11-06 PROF-CURVA-1 Task 4: fronteira v2 250 medições cmp=0; 10 corridas OFF solo Interlagos/Monaco N=0..4 e 20 leituras determinísticas cmp=0; baseline confirma saídas crônicas e 56,4–57,2% fora em Monaco; EXECUCAO_PROF_CURVA_1_0.md; PARE para closing do Dono.
2026-11-06 PROF-CURVA-1 Task 5: mapa de viabilidade OFFLINE do teto local (determinístico cmp=0 ×2, script e5853aa commitado antes da execução) — MECANISMO COMO PREREGISTRADO INVIÁVEL: guarda Interlagos estoura no PISO (integral capped 131,04 s > teto 123,05 s; Δ+34,84 s), Gate Primário inalcançável (C01 0/22 bind R 107–140 m = saída comportamental, não pacing; C06 4/20), teto engaja 74% da volta Interlagos / 89% Monaco (rastejamento 3,2–5,8 m/s); PARE automático §4 — ZERO corrida ON, orçamento 10 solo 600 s preservado, --prof-curva mantido default OFF bit-idêntico; encaminhamento preregistrado: racing line suavizada (curva geométrica 18 m na Junção) em ciclo próprio a abrir pelo dono; MAPA_VIABILIDADE.md
2026-11-06 ABERTURA RACING-LINE-1: ciclo separado para linha suavizada local do professor, com curva geométrica R=18 m na Junção; plano/prereg staged, zero corrida e zero alteração no PROF-CURVA-1; aguardando Freeze do Dono.
2026-11-07 RACING-LINE-1 Task 2: construção geométrica offline do arco R=18 m na janela C08/Junção (instrumento staged antes da execução, R7; determinístico cmp=0 ×2) — PARE §7: sem arco exato com os limites congelados (resíduo dos centros 3,189856 m ≫ 1e-3; corda 35,58 m implica sweep 162,6° vs giro real −140,6° = superdeterminado); evidência report-only: raiz bi-tangente EXATA com limites livres dentro da janela (s 2282,417 → 2342,863 m, giro −139,89°, resíduo <1e-6; +6 raízes degeneradas R_local=18 e 2 fillets locais); corredor/C1/fechamento/auto-interseção da raiz NÃO avaliados (fora do escopo do candidato); ZERO corrida, ZERO produção, pista frozen intocada, orçamento 10 solo intacto; decisão do dono: nova prereg com limites derivados / outra construção (biarc) / arquivar. GEOMETRIA_C08.json/md
2026-11-07 RACING-LINE-1 Task 3: Emenda nº 1 (limites derivados s=2282,417->2342,863 m, R=18 m); validacao offline de corredor e C1; CORREDOR_C08.md.
2026-11-07 RACING-LINE-1 arquivado: candidato de arco unico R=18 m inviavel no corredor (|lat|=10,07 m > 6,0 m); orcamento de 10 corridas solo 100% preservado; transicao para diagnostico de controle do professor (PROF-CONTROL-1).
2026-11-07 ABERTURA PROF-CONTROL-1: controle lateral do professor com feedforward arctan(L*kappa) e ajuste no ápice contra subesterço (LAGO_ANATOMY.md); PREREG_PROF_CONTROL_1.md.
2026-11-07 PROF-CONTROL-1 Task 2: implementado --prof-control opt-in (delta_ff cinemático + ld modulado por c_ld derivado); testes unitários e bit-identidade OFF PASS.
2026-11-07 PROF-CONTROL-1 Task 3: 2 controles OFF cmp=0 e 10 corridas ON N=0..4 solo 600 s concluidas com extracoes deterministicas; integridade PASS; EXECUCAO_PROF_CONTROL_1.md.
2026-11-07 PROF-CONTROL-1 Task 4 closing: avaliacao formal dos gates — REPROVADO (FAIL em Primario: 4/4/4/4 cronicas inalteradas e fora% piorou +1,67 pp; FAIL em Monaco: -0,93 pp < 5 pp com piora em C05/C12; FAIL em Guarda: 132,40 s > 123,05 s); default OFF mantido; EXECUCAO_PROF_CONTROL_1.md.
2026-11-07 ABERTURA PROF-GRIP-1: pacing grip-sensível com reserva de 10% nas janelas das 4 crônicas (hipótese única da LAGO_APPROACH_FINDINGS + GRIP_PACING_FEASIBILITY); PLANO e PREREG; matriz 2 OFF cmp=0 + 10 ON com --variedade N.
2026-11-07 PROF-GRIP-1 Task 2: implementado --prof-grip opt-in (teto grip-sensível v_alvo=v_plan·min(1,sqrt(grip/0,85))·sqrt(1/1,10) nas janelas canônicas de C01/C06/C07/C08, grip_atual = tyre.grip_multiplier por tick); bit-identidade OFF exata e 10/10 testes PASS.
2026-11-07 PROF-GRIP-1 Task 3: 2 controles OFF cmp=0 vs PROF-CONTROL-1 e 10 corridas ON --prof-grip com --variedade N solo 600 s concluidas; extracoes deterministicas cmp=0 12/12; cronicas nao zeradas (C06/C07/C08 4/4/4/4; C01 3 em N1/N2); PRELIMINAR_PROF_GRIP_1.md.
2026-11-07 PROF-GRIP-1 Task 4 closing: avaliacao formal dos gates — REPROVADO (FAIL em Primario: C06/C07/C08 4/4/4/4 inalteradas e C01 3 em N1/N2; FAIL em Monaco: delta offtrack > 0 em N3/N4 e regressao C05; FAIL em Guarda: mediana 129,0–130,4 s > 123,05 s); causa: teto fator=0,9535*sqrt(grip/0,85) era comparado com v_plan*0,93 e foi no-op em >80% da corrida; default OFF mantido; EXECUCAO_PROF_GRIP_1.md.
2026-11-07 ABERTURA PROF-PACE-1: pacing preventivo grip_mode=fixed (grip_ref=0,789547 SOFT 6 voltas DRY 42°C; 0,807 NÃO é o pior caso confirmado pelo TyreState canônico); escada η1=0,48848/η2=0,40000; PLANO e PREREG; decisões do dono pendentes (controles OFF, escalada, Guarda voltas limpas).
2026-11-07 PROF-PACE-1 Task 1 (correção documental): grip_ref recalculado com demonstração n_laps=ceil(600/130,195)+1=6 aplicações exatas; length_factor precisão completa 0,9245415555555555 (versões divergentes removidas); grip_ref=0,7895474400345001; SHAs completos pinados; identidade operacional congelada (--n-cars 1, VER, SOFT, 42,0°C, grip fixed nunca atualizado); decisões do dono marcadas PENDENTE_DO_DONO (controles OFF, escalada η1→η2, Guarda voltas limpas).
2026-11-07 PROF-PACE-1 Task 1 (auditoria final): decisões do dono registradas (CTRL_OFF pareado N=0..4; ON η1 N=0..4; ON η2 N=0..4 condicional; orçamento máx 15; escalada com 5 condições; Guarda = mediana das voltas limpas por realização, mediana das medianas ≤ 123,05 s, OFF inconclusivo por desenho); auditoria clima/grip: 6 realizações DRY 0 transições grip 0,8420→0,8070 (gate grip_ref PASS); variação N0..N4 = jitter IC (variedade_params); t_base 96,202 / t_margin 103,656 / t_cap η1 105,660 / η2 107,080 com grip_ref 0,789547 (todos cabem).
2026-11-07 PROF-PACE-1 FREEZE Task 2 (dono): mecanismo --prof-pace congelado (grip_mode=FIXED grip_ref=0,7895474400345001; escada eta1=0,48848/eta2=0,40000; k_inst no v_safe + k suav 20 m nas passadas; tempos do PACE_MARGIN com 30 m superados; exclusividade vs --prof-grip/--prof-control; 0,93 uma vez -> cap -> passadas; correcao wrap-safe da mascara C01 + teste de cobertura circular; equivalencia cap inativo 1e-9; clima 6 realizacoes DRY 0 transicoes, grip_ref <= grip final 0,807); custos canonicos pelo caminho do controlador: t_base 96,201711 / t_margin_only 103,442766 / t_cap eta1 107,410153 / eta2 109,610725 (folga >= 15,6 s); incremental sobre t_margin: +3,97 (eta1) / +6,17 (eta2); reducoes rel max 38%/44%; estimativa 111-113 s observados = extrapolacao exploratoria do dono (sem status de medicao/gate); ressalva 1: os 4 ticks s1872-1884 (frenagem antecipada C06, dist 8,0 m, regra d_b <= 2*ds) com metricas no relatorio do executor; ressalva 2: determinismo pareado verificado estruturalmente (ICs = f(seed,N) puro) e empiricamente para variedade 0 (REF=CTRL bit-identico); N>0 sem duplicatas nos dados existentes (limitacao registrada para a Task 3).
