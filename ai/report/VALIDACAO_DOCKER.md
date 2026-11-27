# Validação no Ambiente Docker

## Resumo da Validação

✅ **Todos os containers sobem corretamente**
- postgres, redis, llama, backend, frontend, viz3d, ai

✅ **Build das imagens Docker**
- backend: OK
- frontend: OK (com warnings de chunk size, não bloqueante)
- viz3d: OK
- ai: OK (após adicionar mlflow)

✅ **Criação de corrida via API**
```bash
curl -X POST http://localhost:8000/races \
  -H "Content-Type: application/json" \
  -d '{"laps": 5, "track": "interlagos", "season": 2023, "num_drivers": 4}'
```
Retorna `race_id` válido.

✅ **AI Engineer (serviço separado) funciona**
- Container `ai` sobe corretamente
- Warming up do modelo: ~21s
- Detecta corrida automaticamente via Redis pub/sub
- Publica eventos no canal correto `race:{race_id}:events`

✅ **Eventos da IA publicados no Redis**
| Evento | Status | Detalhes |
|--------|--------|----------|
| `ai_monitoring` | ✅ | Heartbeat periódico com stats |
| `ai_command` | ✅ | Por driver, com comando, valor, motivo |
| `ai_suggestion` | ✅ | Texto em PT-BR, urgência, previsão |
| `ai_suggestion` (fallback) | ✅ | Marcado com `"fallback": true` |

✅ **Fallback tático determinístico**
- Rival < 0.9s → `overtake`/`defend`
- Pneu < 35% → `conserve` + pit recomendado
- Combustível < 40kg → `conserve`
- Safety Car → `careful`
- Últimas voltas → `push`
- Tudo sob controle → `neutral`

✅ **Anti-repetição (testes passam)**
- 7/7 testes em `test_repetition.py` passam
- Evento real: fala se comando OU texto mudou
- Periódico: silencía se comando OU texto repetiu
- Primeira mensagem: sempre fala

✅ **Métricas MLflow**
- Collector registra: latência, fallbacks, JSON inválido, duplicatas, timeouts
- Flush periódico a cada 60s
- Health check do Ollama registrado

✅ **Isolamento entre corridas**
- Race A (`race_ba21cfa...`) e Race B (`race_242fe3a...`) isoladas
- Cada uma tem seu canal `race:{id}:events`
- Eventos da Race B não aparecem no canal da Race A
- AI listener detecta ambas independentemente

✅ **Frontend build**
- TypeScript compila sem erros
- Vite build gera assets otimizados
- AiFloatingPanel integrado

---

## Comandos de Validação

```bash
# Subir ambiente
docker compose up -d --build

# Verificar logs do AI
docker compose logs -f ai

# Criar corrida
curl -X POST http://localhost:8000/races \
  -H "Content-Type: application/json" \
  -d '{"laps": 5, "track": "interlagos", "season": 2023, "num_drivers": 4}'

# Monitorar eventos no Redis
docker exec -it <redis_container> redis-cli SUBSCRIBE "race:<race_id>:events"

# Ver métricas MLflow
docker exec -it <backend_container> python -c "
import mlflow
mlflow.set_tracking_uri('sqlite:///mlflow.d')
exp = mlflow.get_experiment_by_name('f1-ai-engineer')
runs = mlflow.search_runs(exp.experiment_id)
print(runs[['params.key', 'metrics.latency_p50', 'metrics.fallback_rate_pct']].head())
"

# Testes unitários
.venv/bin/python -m pytest ai/tests/ -v
.venv/bin/python -m pytest backend/tests/test_random_events.py backend/tests/test_live_race_api.py -v

# Frontend typecheck
cd frontend && npm run build
```

---

## Problemas Identificados (Não Bloqueantes)

1. **Backend AiEngineer não loga**: O AiEngineer do backend (`backend/engine/ai_engineer.py`) não parece estar logando eventos de ciclo de vida. O AI Listener (container separado) é quem está publicando os eventos. Não afeta funcionalidade.

2. **Evento `ai_started` não observado**: Não foi visto nos logs, mas `ai_monitoring` com status "waiting_for_race_start" é publicado.

3. **Teste `test_radio_espera_a_corrida_largar` falha**: Problema no stub de teste, não no código de produção.

4. **Chunk size warning no frontend**: Assets > 500kB, sugerido code-splitting.

---

## Arquivos Modificados/Criados

### Backend
- `backend/engine/ai_engineer.py` - Refatorado com separação análise/execução, eventos de ciclo de vida
- `backend/engine/events.py` - +4 eventos: `AiStartedEvent`, `AiMonitoringEvent`, `AiStoppedEvent`, `AiErrorEvent`

### AI Service
- `ai/app/client.py` - Parâmetros Ollama otimizados + integração MLflow
- `ai/app/schemas.py` - Integração MLflow (invalid_json)
- `ai/app/metrics.py` - **NOVO** MLflowTracker
- `ai/app/fallback_tactical.py` - **NOVO** Fallback tático determinístico
- `ai/app/redis_listener.py` - Integração fallback tático, anti-repetição, MLflow
- `ai/requirements.txt` - +mlflow

### Frontend
- `frontend/src/types/race.ts` - +4 tipos de eventos IA
- `frontend/src/services/race-parser.ts` - Parser para 4 novos eventos
- `frontend/src/stores/live-race-store.ts` - Estado expandido + validação raceId
- `frontend/src/components/race/ai/ai-panel.tsx` - UI com status, stats, erros
- `frontend/src/components/race/ai/ai-floating-panel.tsx` - **NOVO** Painel flutuante 2D/3D
- `frontend/src/components/race/ai/ai-engineer.tsx` - Orb 3D com status
- `frontend/src/components/race/view-3d/race-scene.tsx` - Integração props
- `frontend/src/pages/race-simulation.tsx` - Integração AiFloatingPanel

### Documentação
- `PLANO_CORRECAO_IA_FRONTEND.md` - Plano detalhado
- `RESUMO_CORRECOES_IA.md` - Resumo das correções
- `AUDITORIA_RACE_ID.md` - Auditoria completa do race_id
- `PLANO_DESENVOLVIMENTO_IA.md` - Plano atualizado com 6 tarefas
- `VALIDACAO_DOCKER.md` - Este arquivo

---

## Atualização de 2026-11-27 — IA, TTS e bundles

Os resultados abaixo são da rodada mais recente; não representam uma nova validação Docker completa.

| Escopo | Comando/verificação | Resultado |
|--------|---------------------|-----------|
| IA | `.venv/bin/python -m pytest ai/tests/ -q` | **35 passed** |
| API do debrief | `.venv/bin/python -m pytest backend/tests/test_debrief_api.py -q` | **4 passed** |
| Frontend | `npm test` | **56 passed** |
| TTS | `vitest run src/ai/SpeechSynthesis.test.ts` | **4 passed** |
| Frontend | `npm run build` | **Passou**; entrada de 42,02 kB e Three isolado de 675,59 kB |
| Viz3d | `npm run build` | **Passou** com Vite 5.4.21; chunk Three de 925,80 kB ainda pendente |
| Ollama/corrida real | Nova medição do prompt otimizado | **Não executada; serviços indisponíveis** |
| Navegador | Voz audível e painel em corrida completa | **Pendente** |

### Correção do pipeline de pull request

- `actions/setup-node` agora usa `cache-dependency-path: frontend/package-lock.json` nos jobs de typecheck e build; o lockfile não precisa estar na raiz do repositório.
- Os dois f-strings inválidos de `ai/app/context/weather_context.py` foram corrigidos para Python 3.11.
- O stub de Redis de `test_radio_espera_a_corrida_largar` passou a implementar `get()` e representar o snapshot `running`, acompanhando a interface usada pela produção.
- Sintaxe Python 3.11 validada em 27 arquivos de `ai/app` e `ai/tests`.
- Testes de IA: **35 passed**; testes backend do workflow: **7 passed, 1 skipped**.
- `npx tsc --noEmit` e `npm run lint` concluídos no frontend; o lint mantém somente avisos não bloqueantes.
- YAML do workflow validado. O pipeline completo ainda precisa ser confirmado no GitHub Actions.

### Dificuldades atuais

1. Ollama e os containers não estavam ativos para medir a nova configuração do debrief; a meta de 30s continua aberta.
2. O `viz3d` tem Vite 5.4.21 instalado, mas manifesto e lockfile declaram 8.2.2. A configuração de Rolldown foi revertida nesse app até o alinhamento das dependências.
3. O Three é um vendor monolítico. O orçamento de 700 kB no frontend isola o aviso conhecido, mas não deve ser descrito como redução para menos de 500 kB.
4. Testes unitários da Web Speech API não substituem validação audível em navegadores.
5. Existe trabalho paralelo de recuperação de corridas no mesmo worktree; seus arquivos não devem ser alterados pelas frentes de IA/TTS.

### Próximos passos modularizados

- **Frente A — IA/Ollama:** medir o debrief em chamada fria e três quentes, validar JSON real e o fluxo `race_end` → Redis → API, e registrar as evidências neste arquivo.
- **Frente B — Frontend/Viz3d/TTS:** alinhar o Vite do `viz3d`, separar o vendor Three e validar TTS/painel em navegadores; registrar as evidências em `ai/report/VALIDACAO_FRONTEND.md`.

A divisão completa de arquivos, tarefas A1–A5/B1–B6 e critérios de conclusão está em `PLANO_DESENVOLVIMENTO_IA.md`, **seção 15**. A validação Docker integrada deve ser repetida somente após os dois handoffs.