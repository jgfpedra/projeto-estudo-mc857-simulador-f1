# PREREG_FAIL_FORENSICS_1 — medir falhas sem mudar comportamento

**Status:** congelado antes das simulações
**Escopo:** Etapa 1 do plano pinado; instrumentação offline/report-only
**Base do checkout:** `b93cae6669d1030e6fe1c2f8c01a0da9787eff50` (`feat/sanidade-produto`)
**Execução:** exatamente quatro processos de simulação, seriais, seed 0, 6000 ticks; nenhum treino, patch de comportamento, promoção, re-pin ou mudança de default.

## 1. Estado e configuração pinados

- Cego: v10 DAgger, obs `edge`, `--gov vplan`.
- Composite: v10 solo congelado + residual r2, `--profile composite`, `--gov vplan`.
- Clima: `seeded`, seed 0; o resultado só é classificado como seco se o log confirmar `weather_transitions=[]`.
- Variância multi-carro: `grid,compound`, conforme o cabeçalho dos dois CSVs âncora F4v15. No Monaco solo: `off`, igual ao âncora PROF-MONACO-1.
- Grid: 10 carros nas três medições de campo; a checagem do aluno em Monaco é `--n-cars 1`, igual ao âncora solo.
- Pistas carregadas somente dos arquivos frozen existentes, sem gate por FastF1/ENV:
  - Interlagos: `interlagos_v2.json`, SF 729, short SHA `164876196eb12174`, SHA-256 completo `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613`.
  - Monaco: `Monaco_v2.json`, SF 0, short SHA `67ca11dc211c8c78`, SHA-256 completo `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`.

O bloco “Comandos essenciais” do `PROJECT_STATE.md` registra o runner `race_diagnostic.py`, `--ticks 6000`, o ator v10/obs `edge` e a seleção `--profile composite`, mas não lista os parâmetros completos da realização F4v15. Para reproduzir as âncoras byte a byte, este prereg fixa as opções de clima/variância/grid presentes nos cabeçalhos e logs das âncoras; os nomes de opções são os já existentes no parser de `race_diagnostic.py`. Não será usado o runner GUI `run_race_10_cars.py`.

## 2. Ordem e comandos

Executar de `backend/`, um comando por vez. Cada stdout/stderr será salvo no `runN.log` no mesmo passo. O runner cria `<out>_events.csv` com contatos brutos do solver. Antes de iniciar o próximo processo, verificar o código de saída, identidade da pista/clima/grid/perfil e, quando houver âncora, comparar o CSV (e o arquivo de eventos quando existente) byte a byte. Qualquer divergência nas três âncoras = **PARE imediato**; não rodar as etapas posteriores nem interpretar causalidade.

```bash
# 1 — cego Interlagos, 10 carros
.venv/bin/python model_train/race_diagnostic.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge \
  --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 \
  --weather seeded --gov vplan --variance grid,compound \
  --out experiments/fail-forensics-1/1_blind_interlagos_s0.csv

# 2 — composite Interlagos, 10 carros
.venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track interlagos --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --out experiments/fail-forensics-1/2_composite_interlagos_s0.csv

# 3 — aluno v10 Monaco, canário solo (N=1), âncora PROF-MONACO-1
.venv/bin/python model_train/race_diagnostic.py \
  --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge \
  --n-cars 1 --ticks 6000 --laps 99 --track monaco --seed 0 \
  --weather seeded --gov vplan --variance off \
  --out experiments/fail-forensics-1/3_blind_monaco_s0.csv

# 4 — composite Monaco, 10 carros; primeira realização, N=1
.venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --out experiments/fail-forensics-1/4_composite_monaco_s0.csv
```

## 3. Âncoras de validade e critério de parada

| Etapa | Referência | SHA-256 do CSV referência | Métricas de reconciliação |
|---|---|---|---|
| 1 | `experiments/f4v15-wiring/1_controle.csv` | `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733` | contatos carro-carro 3674; pós-60s 2482; rolante 136,0 s; hesitações 3; fora 22,1% |
| 2 | `experiments/f4v15-wiring/2_allcomposite.csv` | `512ba0d2553b1c3acacc69582a6877a883f570aee4cf72658a7925f164310155` | contatos carro-carro 752; pós-60s 292; rolante 140,0 s; hesitações 13; fora 25,2% |
| 3 | `experiments/prof-monaco-1/aluno_s0.csv` | `f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0` | CSV byte-idêntico |

Âncoras solver-side adicionais para as etapas 1–2: `1_controle_events.csv` SHA-256 `11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9`; `2_allcomposite_events.csv` SHA-256 `1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54`. A etapa 3 não tem CSV de eventos na referência.

Reconciliar também os campos impressos de clima, pista/SF/hash, perfil, número de carros, autoridade e CSV. No composite, confirmar `res_0..res_15`; no cego, essas colunas não se aplicam. Uma divergência de byte ou configuração nas etapas 1–3 invalida o ciclo e aciona o PARE/leak-check antes de qualquer interpretação. A etapa 4 é uma única realização exploratória; divulgar N=1 sem intervalo inferencial.

## 4. Contrato de dados confirmado antes da coleta

O CSV `race_diag_v3_3_res16d` contém uma linha por carro e amostra de 5 Hz: tick/tempo, carro, velocidade, `s`/`lat`, acelerador/freio/esterço, autoridade, off-track, clima/transições, pneu/aderência, odômetro `cum_dist`, observação 23d e, no perfil Composite, gate/norma/resíduo 16d (`res_0..res_15`). O CSV não carrega `x,y` nem o índice cru do segmento escolhido; a análise de projeção usará o `s` persistido, `cum_dist` e a geometria frozen para derivar/localizar o segmento representado por `s`. Essa limitação será divulgada.

O `<out>_events.csv` `race_diag_v3_contact_solver_v1` traz pontos de contato do solver (`sub`, participantes, `j_n`, `dv_a`, `dv_b` e geometria do contato); converter `sub` em tick por `sub//24`. O número de amostras `car_car` no CSV não substitui esta fonte de contato solver-side.

## 5. Métrica pré-registrada: descontinuidades da projeção

Por carro, ordenar por tick e comparar amostras adjacentes. Calcular o avanço projetado assinado `Δs` com wrap modular pelo comprimento frozen, e `Δodo = cum_dist[t] - cum_dist[t-1]`. Localizar os segmentos correspondentes a cada `s` com a mesma tabela cumulativa de waypoints da geometria usada pelo `saidas_verdict.py`.

- Métrica primária: contar como salto uma amostra com `abs(Δs - Δodo) >= 30 m` (limiar conservador de descontinuidade grosseira, congelado antes da coleta).
- Sensibilidade descritiva, sem gates: publicar contagens em `>=10 m`, `>=20 m` e `>=30 m`, quantis do erro absoluto e todos os locais/ticks com os segmentos anterior/seguinte, `s`, `lat`, velocidade, comandos, authority e estado de recuperação.
- Cruzar saltos com off-track, contato solver-side, preso e hesitação. Não usar os saltos para mudar comportamento nem excluir observações da bateria.

## 6. Taxonomia causal e unidade dos eventos

Reusar `scripts/saidas_verdict.py` para a extração de excursões, nomes/complexos de curva e modo cinemático `LINHA-RETA`/`SLIDE`/`SPIN`, com `--track monaco` na geometria Monaco. Nenhuma alteração nesse classificador será feita nesta etapa.

- **Off-track:** episódio contíguo de amostras `offtrack=1`; unidade = início do episódio.
- **Contato:** agrupar pontos do solver por tick/par de carros; contato contíguo do mesmo par, com intervalo máximo de 10 ticks, é um episódio. Guardar contagem de pontos, soma de `j_n` e máximo de `dv_a/dv_b`.
- **Preso:** replicar a definição R3 já usada pelo `race_diagnostic.py`: janelas alinhadas de 30 s que têm amostras off-track e satisfazem `max(|lat|)>20 m` ou amplitude de `cum_dist <5 m`. Unidade = janela/carro; manter também número de ticks off-track classificados como preso.
- **Hesitação:** replicar a definição atual: episódio contíguo de `speed<0,5 m/s`, após `t>20 s`, duração `0,3–<3,0 s`. Unidade = episódio/carro.
- **Salto de projeção:** cada amostra que satisfaz a métrica primária acima; unidade = transição de amostras/carro.

Atribuir exatamente uma causa por evento, usando evidência da janela anterior ao início e esta precedência congelada:

1. **COLISÃO:** evento de contato é colisão por definição; para off-track/preso/hesitação, exigir impulso normal solver-side positivo do mesmo carro até 1,0 s antes do evento.
2. **RECUPERAÇÃO:** na ausência de colisão, autoridade `rejoin`, `recovery` ou `recovery_rejoin` no evento ou nos 10 s anteriores (inclui retorno/crawl e ecos).
3. **CURVA:** na ausência das anteriores, modo `SLIDE`/`SPIN` ou localização em complexo de curva segundo `saidas_verdict.py`; guardar o modo literal, inclusive `LINHA-RETA`.
4. **TRAJETÓRIA:** caso restante, incluindo descontinuidade da projeção sem evidência anterior de colisão/recuperação e saída limpa com pista sem slip extremo.

Cada linha classificada terá tick/tempo, carro(s), `s`/lat, velocidade, comandos, authority, impulso/Δv quando houver, segmento derivado, modo/complexo de curva e causa. A classificação é mecânica e report-only, não prova contrafactual.

## 7. Entregáveis e leitura

Salvar nesta pasta os quatro CSVs, eventos solver-side quando produzidos, logs completos, script offline de veredito, `eventos_classificados.csv`, `saltos_projecao.csv`, tabelas `pista × braço × causa-raiz`, `relatorio.md` e o PARE. Mostrar 3–5 casos exemplares com a evidência acima; comparar Interlagos × Monaco_v2 e cego × Composite. Monaco Composite permanece N=1; Monaco cego é a checagem solo N=1, não uma comparação de tráfego pareada.

Resultado desta etapa = recomendação concreta de dados necessários para a Etapa 2 (localização/rejoin e gate Monaco de zero atalhos entre trechos). Não propor reparo comportamental, promoção, retreino, mudança de default ou re-pin. Atualizar `PROJECT_STATE.md` aditivamente, `worklog.md` e ai-memory no fechamento, preservando todo o histórico anterior e o arquivo preexistente não rastreado `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`.
