# PREREG_PISTAS_EXPAND_1 — Biblioteca de mirrors reais expandida via OpenF1 (aquisição de dados; 0 sims)

Branch `feat/sanidade-produto` · 2026-10-23 · Commitar ESTE prereg ANTES de qualquer patch ou chamada de rede.
Ciclo de AQUISIÇÃO: gerar contornos REAIS de pista (OpenF1 /location, método v4 do FONTE-2) para as pistas-alvo, congelar como mirrors v2 com IDENTIDADE verificável (track_identity) e MANIFEST com sha256. O pool de treino NÃO muda. NENHUMA sim de treino/corrida. Suíte em SERIAL.

## Contexto pinado (não re-derivar)
- FONTE-2 provou o método: /location x/y em DECÍMETROS (razão exata 10×); algoritmo v4 = remove-parado → célula-60m-mais-visitada → janelas-entre-visitas=volta → mediana → re-amostra 10 m. Prova: Monza 2024 (session 9590, d44): 575 wp / 5756 m vs 5793 oficiais (−0,64%).
- PISTA-IDENT-1 (1a228b8) entregou: backend/domain/track_resolution.py (fail-loud, allow_fallback=False default), track_identity() (requested × efetiva × fonte × sha256 × wp × L) e load_track_frozen (mirror-first). Mirrors canônicos atuais: interlagos (164876196eb12174), Monaco_v2 (67ca11dc211c8c78), Spa_v2 (4b05f2c3bbc625fc). Monza_v1 e Suzuka_v1 existem (consultar no T0).
- Lição H-1 REINCIDENTE 2× no ciclo anterior: o loader é CASE-EXATO ('monaco' ≠ 'Monaco_v2.json'). A tabela de chaves exatas é deliverable deste ciclo.

## §1 T0 (primeiro commit de dados) — inventário
1. Listar TODOS os tracks_frozen existentes (v1/v2): arquivo, CASE EXATA da chave de carregamento, sha256, carregável ou não.
2. Classificar cada pista-alvo:
   - (a) mirror canônico v2 já existente → PULAR (não regenerar);
   - (b) mirror v1 existente → COMPARAR (v1 × OpenF1 novo) e REPORTAR; NÃO substituir v1 sem aprovação do dono;
   - (c) sem mirror → PRODUZIR v2 novo.
3. Tabela alvo (comprimentos oficiais a CONFIRMAR em fonte oficial no T0; divergência → reportar e re-pin no ANEXO):

| pista (chave alvo) | oficial (km, confirmar no T0) | classificação esperada |
|---|---|---|
| Hungaroring | 4,381 | (c) |
| Silverstone | 5,891 | (c) |
| Montreal | 4,361 | (c) |
| Bahrain | 5,412 | (c) |
| Mexico | 4,304 | (c) |
| Zandvoort | 4,259 | (c) |
| Suzuka | 5,807 | (b) se v1 carregável |
| LasVegas | 6,201 | (c) — ESTICAMENTO |
| Miami | 5,412 | (c) — ESTICAMENTO |

- LISTA PRIMÁRIA: as 7 primeiras. ESTICAMENTO (LasVegas, Miami) SÓ se a primária estiver completa dentro do teto de chamadas.
- Nomes de arquivo seguem a CONVENÇÃO DO LOADER case-exata (confirmar no T0 qual casing o load_track_frozen espera — H-1: NUNCA assumir).

## §2 Pipeline por pista (reuso EXATO do método FONTE-2 v4 — sem reinvenção)
1. Descoberta de sessão: OpenF1 /sessions (year 2023–2024, session_name='Race'); para pistas do MESMO país (EUA: Miami × Austin × Vegas) discriminar por location/nome oficial do circuito. Chamada leve, logada.
2. Driver: P1 da classificação final da corrida (regra determinística; se o stream /location do P1 tiver saltos >300 m — método morto documentado no FONTE-2 — avançar para o próximo classificado e registrar no manifest).
3. GET /location (session_key, driver_number) — PESADO (3–4 MB). CACHE LOCAL OBRIGATÓRIO (nunca baixar 2×; diretório de cache OpenF1 NOVO e DISTINTO dos caches fastf1, que ficam INTACTOS).
4. v4: remove-parado → célula-60m → janelas=volta → mediana → re-amostra 10 m.
5. Gate de qualidade por pista (fail-loud, SEM forçar): bounding box plausível vs escala real (÷10); comprimento vs oficial Δ < 1%; fechamento do contorno; espaçamento ~10 m. FALHOU = pista marcada FAILED no manifest, sem mirror congelado (não é regressão; é resultado honesto).
6. Gravar {Track}_v2.json (formato idêntico aos mirrors canônicos) + sha256 no manifest + PNG de conferência via draw_track EXISTENTE (draw_track é zona intocada — só chamar).

## §3 Manifest e identidade (deliverables)
- manifest_pistas_expand_1.csv: pista | chave case-exata | session_key | ano | driver | n_amostras | wp | L_m | L_oficial_m | Δ% | sha256 | status (OK / FAILED / COMPARADO).
- Para cada OK: output de track_identity() colado no ANEXO (fonte=openf1).
- Para cada (b): tabela comparativa v1 × candidato (L, wp, Δ%); decisão de substituição = dono.

## §4 Golden (tabela de verificação)
| caso | esperado |
|---|---|
| load_track_frozen de cada mirror novo com a case EXATA | carrega; n_wp/L == manifest |
| track_identity(mirror novo) | fonte=openf1; L dentro de 1% da oficial |
| mirrors canônicos (interlagos/Monaco/Spa) | bit-idênticos (sha estável), NÃO tocados |
| suíte completa | 20F/345P/3S + testes novos, ZERO FAIL novo |

## §5 Plano de testes (+3-4 declarados)
1. t_pe1_carrega: cada mirror novo carrega via load_track_frozen com a case EXATA documentada (anti-H-1 estrutural).
2. t_pe1_identidade: track_identity de cada novo: fonte=openf1 e |ΔL| < 1% da tabela §1.
3. t_pe1_manifest: todo JSON tem linha no manifest; sha256 recalculado == manifest (determinístico entre execuções).
4. t_pe1_schema: contorno fecha (primeiro≈último wp), espaçamento médio 10 m ± margem, n_wp plausível.

## §6 Orçamento e proibições
- Chamadas OpenF1: TETO 25, logadas APPEND (descoberta leve + location pesadas; cache local evita re-baixar). Qualquer chamada FORA do teto/contexto = disclose imediato.
- ZERO sims de treino/corrida; suíte apenas em SERIAL (lição PISTA-IDENT-1: suítes que rodam sims em /tmp compartilhado também são "sims em paralelo" — este ciclo não deve gerar corrida nenhuma).
- Proibido: tocar física/recompensa/professor/obs/pools 70-79/76-79/caches fastf1/draw_track/--prof-repair/--variedade/perfis-default; deletar ou substituir v1s; mudar o pool de treino (--tracks) ou perfis de deploy; A×B; retreino; promoção de qualquer ator.
- Rede ZERO fora do ciclo de aquisição §2.

## §7 Reconciliações entre pins
- "0 sims" × PNGs: draw_track é PLOT de geometria, não simulação ✓.
- Rede esperada: SÓ aquisição §2, com teto e log APPEND ✓.
- H-1: este ciclo NÃO implementa normalizador canônico de chaves (fica para ciclo futuro de infra); mitiga com tabela de chaves exatas + teste estrutural (t_pe1_carrega) ✓.
- Comprimentos oficiais: tabela §1 é ÂNCORA; divergência achada no T0 → reportar e re-pin no ANEXO antes de produzir mirrors ✓.

## §8 Suíte esperada
20F/345P/3S + 3-4 testes novos (zero FAIL novo). Qualquer FAIL novo = disclose com itemização (comparação serial × serial contra 1a228b8).
