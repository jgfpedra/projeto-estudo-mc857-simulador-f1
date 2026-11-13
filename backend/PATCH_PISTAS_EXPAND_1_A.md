# PATCH_PISTAS_EXPAND_1_A — fixações mid-cycle do orquestrador

Cadeia de documentos: PREREG_PISTAS_EXPAND_1 → PATCH_PISTAS_EXPAND_1_A (este). Leia o patch INTEIRO e registre-o no seu worklog (APPEND) ANTES de continuar. Ele NÃO cancela o PREREG: altera/fixa 4 pontos; em conflito, VALE ESTE PATCH. Se as fixações já chegaram até você em texto bruto, este patch é a versão canônica de auditoria (mesmo conteúdo, formalizado).

FIXAÇÃO 1 — Reclassificação (b)×(c) atualizada pelo seu T0:
- (b) TÊM v1 → produza o contorno OpenF1 + tabela comparativa v1×candidato, mas NÃO congela v2 nesta rodada — congelamento só com aprovação do dono (congelar v2 = loader passa a preferir v2 = substituição prática da resolução):
  · Suzuka · Hungaroring · Zandvoort
- (c) SEM v1 → produza v2 e CONGELA nesta rodada:
  · Montreal · Bahrain · Mexico
- (c) SEM v1 → produza v2 candidato + comparativo; status AGUARDA_DONO no manifest; NÃO escrever no path frozen canônico (o dono decide o freeze na revisão do PARE):
  · Silverstone
- Esticamento, SÓ após a primária completa e se o teto de chamadas deixar: LasVegas · Miami → mesma regra de (c): produza v2 e congela; sem teto restante, status NAO_EXECUTADO (resultado honesto).
- Se o PREREG já define vocabulário de status no manifest, mantenha-o e acrescente AGUARDA_DONO / NAO_EXECUTADO apenas se não existirem.
- Inventário de v1s conforme o seu T0; se o repositório mostrar algo diferente (v1 extra ou faltante), fail-loud no PARE — sem reclassificação silenciosa.
- Nota fail-loud: se a suíte parametriza sobre mirrors congelados, o congelamento seletivo pode deslocar a contagem prevista no §8 — qualquer desvio vs 20F/345P/3S é itemizado no PARE com causa raiz (sem ajuste silencioso de expectativa).

FIXAÇÃO 2 — Escopo do git add -f: SÓ para deliverables canônicos (JSONs de mirror novos, manifest CSV, PNGs, ANEXO). NUNCA para respostas cruas da OpenF1 — cache local fica fora do git. Se o path frozen canônico já é tracked, entra sem -f.

FIXAÇÃO 3 — Stray backend/worklog.md: confirme que a raiz contém as entradas (FONTE-1/PROF-REPAIR-1) e então mova para archive/ com um README de 1 linha (proveniência: duplicata por cwd-flip). Não deletar.

FIXAÇÃO 4 — Formato dos novos mirrors = v2: official_length_m (do f1db), sf_idx=0 + sf_note quando a fonte não marca SF, sha256 recalculado sobre o conteúdo novo. A tabela de chaves case-exatas (anti-H-1) entra no ANEXO.

Lembretes de execução (reafirmação):
- Contador de chamadas: APPEND desde a 1ª chamada. Estado atual: nada de rede ainda ✓ — ordem correta (scripts commitados antes de qualquer GET).
- Cache local antes de re-baixar: nunca 2× o mesmo GET.
- Gates fail-loud: FAILED = resultado honesto no manifest, sem mirror congelado.
- ZERO sims; pool de treino --tracks INTOCADO (congelar mirror ≠ adotar no pool; adoção = ciclo próprio com aprovação do dono).
- Suíte SERIAL no fim + comparação itemizada contra 1a228b8 (20F/345P/3S, zero FAIL novo; testes novos do §5 de pé).

Próximo ponto de contato: PARE final com manifest + golden + PNGs (+ ANEXO com a tabela de chaves case-exatas).
