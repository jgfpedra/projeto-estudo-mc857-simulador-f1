# FONTE-1 — F0: inventário classificado das referências a fastf1 (read-only)

> Guarda anti-duplicata: 0 commits FONTE-1 pré-existentes ✓. Fonte de
> classificação: os 2 PLANOS de dados pinados pelo orquestrador
> (TELEMETRIA/SESSÃO = bloqueado por auth F1TV; METADADO/RESULTADO =
> Jolpica, gratuito). Classes: (i) substituível por Jolpica; (ii) órfão
> na Jolpica; (iii) geometria/mirror = intocar; (iv) cache/morto/arquivado.
> [NOTA-DEP] da ADOÇÃO-H-2 (PROJECT_STATE:1634) = ponto de partida.

| # | arquivo:linha | o que busca | classe | nota |
|---|---|---|---|---|
| 1 | `domain/track_loader.py:199,281` | `fastf1.get_session(year, event, session)` (fallback `resolve_track` de env/evals legados) | **(ii)** | carrega a sessão (plano bloqueado a frio); o runner frozen NÃO toca |
| 2 | `domain/track_loader.py:314` | `ff1_session.get_circuit_info()` (cantos do circuito) | **(ii)** | o DADO pedido é GEOMETRIA — já suprido canonicamente pelos mirrors F1DB (ADOÇÃO-H-2; classe (iii) substitui a NECESSIDADE); a CHAMADA é do plano sessão |
| 3 | `database/driver_db.py:79,266` | `fastf1.get_event_schedule(year)` (calendário p/ metadados de pilotos) | **(i)** | metadado puro — substituível por `Ergast.get_race_schedule` |
| 4 | `database/driver_db.py:95` | `fastf1.get_session(year, r, "R")` (resultados p/ nome/equipe/cor de pilotos) | **(ii) chamada / (i) necessidade** | a chamada é do plano sessão; o DADO (resultados/nomes) é metadado — substituível por `Ergast.get_race_results` |
| 5 | `database/driver_db.py:243-246` | `from fastf1.ergast import Ergast; Ergast()` (next-season drivers) | **(i)** | JÁ USA o módulo ergast — backend **api.jolpi.ca** na versão instalada |
| 6 | `archive/scripts/train_multi_context.py:14,23` | treino legado (eras v14) | **(iv)** | arquivado, fora do runtime |
| 7 | `requirements.txt:3` | pin `fastf1==3.8.3` | — | NIT (a) ADOÇÃO-H-2; **o módulo ergast desta versão JÁ aponta para Jolpica** (`fastf1/ergast/interface.py:35` BASE_URL=`https://api.jolpi.ca/ergast/f1`) — não exige upgrade para falar com a Jolpica |
| 8 | `model_train/cache_fastf1/` (96K) + `backend/cache/` (935M) | caches quentes | **(iv) ATIVO CONGELADO** | intactos, irreplaceáveis sem assinatura; PROIBIDO limpar |
| 9 | `backend/f1db.db` (71M) + `data/circuit_layouts_evolution.json` | base F1DB (bootstrap `fetch_track_layouts.py`) | **(iii)** | independente de fastf1; geometria canônica via mirrors |

**Contagem por classe**: (i) substituível por Jolpica = **3**
(track_loader#3, driver_db#3-4/#5); (ii) órfão na Jolpica = **2**
(track_loader#1-2; driver_db#4 por chamada); (iii) intocar = **1**
(+ os mirrors); (iv) congelado/arquivado = **3**.

**Classe (ii) NÃO-VAZIA** → PROBE-C (OpenF1) obrigatório pela árvore.
RESSALVA-CHAVE da (ii): os dois usos órfãos são de caminhos LEGADOS
(fallback resolve_track + carregamento frio de driver_db) que o produto
corrente (runner frozen + mirrors) NÃO exerce; e o dado de #2 (cantos)
já tem supersede canônico (mirrors F1DB). A Jolpica cobre as NECESSIDADES
de dados de #1-#5; o que fica órfão de VERDADE é telemetria/canais de
carro — que NENHUM código ativo consome hoje (a R2-era registrou: "pista
frozen é a única via").

## O que a era ADV-FASTF1-401 deixou (verificado no repo)
- `[NOTA-DEP]` em PROJECT_STATE (blast radius, decisão de pin, ingestão
  futura = dono); pin `fastf1==3.8.3` em requirements com NIT (a);
  caches preservados; artefatos frozen imunes; runner/sim = ZERO rede.

## Versão instalada × Jolpica (achado p/ FONTE-2)
- `fastf1 3.8.3` INSTALADA já contém `fastf1/ergast` com
  `BASE_URL = https://api.jolpi.ca/ergast/f1` — **o pin atual JÁ fala
  com a Jolpica no plano metadado**. O upgrade p/ 3.9 (auth F1TV) só
  interessaria ao plano TELEMETRIA — que este ciclo NÃO adota.
  REGISTRADO COMO ACHADO (sem tocar requirements).
