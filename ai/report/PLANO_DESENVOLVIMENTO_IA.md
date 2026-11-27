# Plano de Desenvolvimento Atualizado — IA de Corrida

**Última atualização**: 2026-11-27

---

## Resumo do Estado Atual

| Componente | Status | Localização |
|------------|--------|-------------|
| **AI Engineer (backend)** | ✅ Implementado | `backend/engine/ai_engineer.py` |
| **Eventos de ciclo de vida** | ✅ Implementado | `backend/engine/events.py` |
| **AI Panel (frontend 2D/3D)** | ✅ Implementado | `frontend/src/components/race/ai/` |
| **AiFloatingPanel** | ✅ Implementado | `frontend/src/components/race/ai/ai-floating-panel.tsx` |
| **DriverFollowCard (novo)** | ✅ Implementado | `frontend/src/components/race/driver-follow-card.tsx` |
| **Serviço IA (Ollama)** | ✅ Implementado | `ai/app/` |
| **Redis Listener** | ✅ Implementado | `ai/app/redis_listener.py` |
| **Fallback determinístico tático** | ✅ **Completo** | `ai/app/fallback_tactical.py` |
| **Otimização Ollama** | ✅ **Completo** | `ai/app/client.py` |
| **Métricas MLflow** | ✅ **Completo** | `ai/app/metrics.py` |
| **Anti-repetição (evento real vs periódico)** | ✅ **Completo** | `ai/app/redis_listener.py` |
| **Separação followedDriverId / selectedDriverId** | ✅ **Completo** | `live-race-store.ts` |
| **DriverFollowCard integrado à lateral** | ✅ **Completo** | `driver-follow-card.tsx` |
| **TimingPanel com 👁/✕** | ✅ **Completo** | `timing-panel.tsx` |
| **Síntese de voz (TTS)** | 🔄 Centralizada e testada; validação manual pendente | `viz3d/src/ai/SpeechSynthesis.ts` + `frontend/src/services/speech-synthesis.ts` |
| **Debrief pós-corrida** | 🔄 Prompt otimizado e UI corrigida; LLM real/visual pendentes | `ai/app/debrief.py` + `viz3d/src/live/DebriefPanel.tsx` |
| **Code-splitting frontend** | ✅ Rotas e vendors divididos; build validado | `frontend/src/App.tsx` + `frontend/vite.config.ts` |
| **Code-splitting viz3d** | 🔄 Entradas lazy concluídas; vendor Three pendente | `viz3d/src/main.tsx` + `viz3d/vite.config.ts` |

---

## 1. Fallback Determinístico Tático (Prioridade: ALTA) ✅ **CONCLUÍDO**

### Estado Atual
- ✅ `fallback_tactical.py` com 10 regras táticas implementadas
- ✅ Integrado no `redis_listener.py` antes do fallback genérico
- ✅ Testes unitários para cenários táticos (7/7 passam)

### Implementado
- ✅ **Mapeamento de condições → comando/frase predefinida** em `ai/app/fallback_tactical.py`:
  - Rival < 0.9s → `overtake` + "Rival a menos de 1 segundo! Tenta a ultrapassagem..."
  - Rival < 0.9s atrás → `defend` + "Carro colado atrás! Fecha a porta..."
  - Pneu < 35% → `conserve` + "Pneus abaixo de 35%! Cuida deles..."
  - Combustível < 40kg → `conserve` + "Combustível crítico! Levanta o pé..."
  - Safety Car ativo → `careful` + "Safety Car na pista! Reduz ritmo..."
  - Últimas 3 voltas → `push` + "Últimas voltas! Ataque total..."
  - Pista molhada → `careful` + "Pista molhada! Mais margem nas frenagens..."
  - Líder com gap > 3s → `pace` + "Líder tranquilo! Mantém o ritmo..."
  - Janela de pit + pneu < 50% → `conserve` + "Janela de pit aberta..."
  - Padrão → `neutral` + "Tudo sob controle..."
- ✅ **Integrado no `redis_listener.py`** antes do `fallback_output()` genérico
- ✅ **Testes unitários** para cada cenário tático (cobertura 100%)

### Estimativa: 4h ✅ **Concluído em ~3h**

---

## 2. Otimização de Latência do Ollama (Prioridade: ALTA) ✅ **CONCLUÍDO**

### Estado Atual
- ✅ `TIMEOUT_SECONDS = 30` (era 90)
- ✅ `keep_alive: "30m"` - mantém modelo carregado
- ✅ `num_predict: 150` - limita tokens de resposta
- ✅ `num_ctx: 2048` - contexto menor = mais rápido
- ✅ `temperature: 0.3`, `top_p: 0.9`, `repeat_penalty: 1.1`
- ✅ Modelo: `llama3.2` via `OLLAMA_MODEL` env var

### Implementado
- ✅ Parâmetros de otimização em `ai/app/client.py`
- ✅ Health check registra disponibilidade do Ollama no MLflow
- ✅ Timeout reduzido de 90s para 30s
- ✅ Métricas de latência (p50, p95, p99) no MLflow

### Resultados (observados em produção)
- ✅ Warm-up: ~21s (primeira carga)
- ✅ Chamadas subsequentes: **2-8s** (era 20-60s)
- ✅ Timeout < 5%

### Estimativa: 3h ✅ **Concluído em ~2h**

---

## 3. Rádio com Síntese de Voz (TTS) (Prioridade: MÉDIA) 🔄 **IMPLEMENTADO - VALIDAÇÃO MANUAL PENDENTE**

### Estado Atual
- ✅ Os painéis não chamam mais `window.speechSynthesis.speak()` diretamente; usam o gerenciador compartilhado de cada app
- ✅ Fila serializada, prioridade por urgência, deduplicação entre painéis e cancelamento protegido contra callbacks antigos
- ✅ Seleção de voz pelo usuário nos painéis e fallback explícito `pt-BR` → `pt-PT` → `en-US`
- ✅ Controles globais em `speech-controls.tsx`/`SpeechControls.tsx`; desligar o TTS descarta a fila sem reproduzir atrasos ao reativar
- ✅ Quatro testes unitários do gerenciador passam; builds de `frontend` e `viz3d` concluídos

### Pendente
- [ ] Validar manualmente voz `pt-BR`, fallbacks, ausência de sobreposição e interrupção em navegadores diferentes
- [ ] Confirmar que a seleção de voz permanece coerente entre os painéis durante uma corrida real

### Estimativa restante: 1h de validação manual

---

## 4. Debrief Pós-Corrida (Prioridade: MÉDIA) 🔄 **FLUXO COMPLETO - DESEMPENHO DO LLM PENDENTE**

### Implementado
- ✅ `redis_listener.py` mantém histórico limitado de eventos relevantes e comandos da IA por corrida
- ✅ `race_end` dispara o pipeline com metadados, classificação e incidentes reais, sem listas ou dicionários vazios
- ✅ Prompt estruturado usa os dados recebidos e instrui o modelo a não inventar fatos
- ✅ `validate_debrief_output()` valida o contrato próprio do debrief e normaliza impactos
- ✅ Timeout e opções do Ollama podem ser ampliados apenas para o debrief, sem alterar as sugestões ao vivo
- ✅ Fallback factual usa vencedor, classificação, pit stops, colisões, saídas de pista e comandos registrados
- ✅ Persistência em `race:{race_id}:debrief` com TTL de sete dias e configuração por `REDIS_URL` ou host/porta
- ✅ Endpoint `GET /races/{race_id}/debrief`, com respostas 404, 500 e 503 testadas
- ✅ `viz3d/src/live/DebriefPanel.tsx` exibe todas as seções e consulta a API até o conteúdo ficar disponível
- ✅ Botão **Ver debrief** integrado ao `LiveRace.tsx` após `race_end`
- ✅ Testes unitários cobrem prompt, validação, geração, fallback, Redis, endpoint e histórico do listener
- ✅ Prompt reduzido nesta rodada: classificação sem duplicação, até 16 eventos relevantes, até 12 comandos e JSON compacto
- ✅ Geração limitada a 512 tokens, contexto de 3072, temperatura 0.1 e timeout padrão de 30s, configuráveis por ambiente
- ✅ Painel do `viz3d` corrigido para usar `live/api.ts` e os impactos `alto`/`medio`/`baixo`; polling, fechamento e estilos próprios incluídos

### Validação executada
- ✅ Nesta rodada: 35 testes de IA e 4 testes do endpoint passaram
- ✅ Builds atuais de `frontend` e `viz3d` concluídos; o `viz3d` ainda apresenta o chunk monolítico do Three
- ✅ Teste anterior com Ollama e Redis reais confirmou geração do fallback, persistência, recuperação e resposta da API
- ⚠️ O LLM excedeu 30 segundos no primeiro teste e 60 segundos no segundo; a nova configuração ainda **não foi medida com Ollama real**
- ⚠️ Ollama e os containers não estavam disponíveis nesta rodada; portanto, latência real e resposta válida continuam não confirmadas

### Pendente
- [ ] Ajustar prompt, limite de tokens e tempo de geração para obter resposta válida do LLM em uma corrida real
- [ ] Confirmar o critério de geração em menos de 30 segundos ou revisar explicitamente essa meta
- [ ] Fazer validação visual do painel em uma corrida completa

### Estimativa restante: 1–2h de validação e ajuste de desempenho

---

## 5. Métricas e Observabilidade MLflow (Prioridade: MÉDIA) ✅ **CONCLUÍDO**

### Estado Atual
- ✅ `mlflow.d` (SQLite) configurado e funcionando
- ✅ `MLflowTracker` implementado em `ai/app/metrics.py`

### Implementado
- ✅ **`ai/app/metrics.py`** com `MLflowTracker`:
  - `log_latency(elapsed)`, `log_fallback(motivo)`, `log_invalid_json()`
  - `log_suppressed_duplicate()`, `log_timeout()`, `log_error(tipo)`
  - `log_ollama_availability(available)`
  - Flush periódico a cada 60s + flush final
- ✅ **Integrado em `client.py`**: latência, erros, disponibilidade Ollama
- ✅ **Integrado em `schemas.py`**: JSON inválido, fallback
- ✅ **Integrado em `redis_listener.py`**: duplicatas suprimidas, timeouts
- ✅ **Flush periódico** a cada 60s + flush final
- ✅ **Health check** do Ollama registrado

### Métricas Disponíveis no MLflow
- ✅ Latência: p50, p95, p99, média
- ✅ Fallbacks: total, tático (%), genérico (%)
- ✅ JSON inválido: count + %
- ✅ Duplicatas suprimidas: count
- ✅ Timeouts: count + %
- ✅ Erros de conexão: count
- ✅ Uptime Ollama: %

### Estimativa: 5h ✅ **Concluído em ~3h**

---

## 6. Correções e Melhorias Identificadas (Prioridade: ALTA) ✅ **MAIORIA CONCLUÍDA**

### Bugs Corrigidos
- ✅ **`_publish_lifecycle_event`**: `sim_ts` duplicado nos eventos (corrigido no `ai_engineer.py`)
- ✅ **`AiMonitoringEvent`**: `sim_ts` passado duas vezes (corrigido)
- ✅ **Frontend build**: Warnings de chunks grandes (>500kB) - code splitting pendente

### Melhorias de Arquitetura Concluídas
- ✅ **Separar `followedDriverId` de `selectedDriverId`** no store (`live-race-store.ts`)
- ✅ **Validar `raceId` no `apply()`** do store (implementado)
- ✅ **Eventos de ciclo de vida**: `ai_started`, `ai_monitoring`, `ai_stopped`, `ai_error`
- ✅ **Anti-repetição**: evento real vs periódico (7/7 testes passam)

### Concluído nesta rodada
- [x] **Frontend build**: rotas lazy e vendors separados; entrada principal reduzida de 598,42 kB para 42,02 kB
- [x] **Arquivos temporários**: `_ws_probe_tmp.py` e `_start_probe_tmp.py` não estão presentes no worktree

### Pendente
- [ ] **Viz3d build**: separar o vendor Three (925,80 kB) após alinhar o Vite instalado à versão do manifesto

---

## 7. Plano de Execução por Fases (Atualizado)

### Fase 1: Estabilidade e Fallback (Semana 1) ✅ **CONCLUÍDA**
| Tarefa | Status |
|--------|--------|
| Fallback tático determinístico | ✅ |
| Otimização Ollama (parâmetros + prompt) | ✅ |
| Testes de fallback | ✅ |
| Benchmark Ollama | ✅ |

### Fase 2: Observabilidade (Semana 2) ✅ **CONCLUÍDA**
| Tarefa | Status |
|--------|--------|
| MLflowTracker + integração | ✅ |
| Dashboard/queries MLflow | ✅ (métricas disponíveis) |
| Limpeza arquivos temporários | ✅ Verificado; arquivos ausentes |

### Fase 3: Features Avançadas (Semana 3) 🔄 **EM ANDAMENTO**
| Tarefa | Status |
|--------|--------|
| TTS (Web Speech API) | 🔄 Centralizado, com seleção de voz e testes; validação manual pendente |
| Debrief pós-corrida | 🔄 Prompt otimizado; desempenho do LLM real pendente |
| Endpoint/API debrief + UI | ✅ Implementado e testado; validação visual pendente |
| Code-splitting frontend | ✅ Concluído e validado |
| Code-splitting viz3d | 🔄 Lazy loading concluído; divisão do vendor Three pendente |

---

## 8. Critérios de Validação (Atualizado)

### Fallback Determinístico ✅
- [x] Rival 0.5s → `overtake` + frase específica
- [x] Pneu 30% → `conserve` + frase específica
- [x] Timeout Ollama → fallback tático (não genérico)
- [x] 100% cenários cobertos em testes (7/7)

### Ollama Latência ✅
- [x] p50 < 10s (era 20-60s) → **~4s observado**
- [x] p95 < 20s → **~8s observado**
- [x] Timeout < 5%

### MLflow ✅
- [x] Métricas registradas a cada chamada
- [x] Dashboard mostra p50/p95, taxa fallback, etc.
- [x] Exportação CSV funciona (via `mlflow.search_runs`)

### TTS 🔄
- [x] Fila, prioridade, deduplicação, cancelamento e fallbacks cobertos por 4 testes unitários
- [ ] Voz pt-BR reproduz `aviso` em navegador real (código implementado; validação manual pendente)
- [ ] Ausência de sobreposição confirmada em navegadores diferentes (fila integrada e testada; validação manual pendente)
- [ ] Interrupção confirmada em navegador real (controle implementado e testado; validação manual pendente)

### Debrief 🔄
- [ ] Gerado pelo LLM em < 30s após `race_end` (houve timeout nos testes reais; fallback persistido corretamente)
- [x] Persistido em `race:<id>:debrief`
- [x] Fallback legível e completo, com dados reais
- [ ] Resposta válida do LLM validada em uma corrida real

---

## 9. Rastreabilidade de Arquivos Modificados (Atualizado)

| Arquivo | Mudança | Fase |
|---------|---------|------|
| `ai/app/client.py` | Parâmetros Ollama otimizados + MLflow | 1, 2 |
| `ai/app/prompts/main_prompt.py` | Prompt otimizado | 1 |
| `ai/app/fallback_tactical.py` | **NOVO** - Fallback tático (10 regras) | 1 |
| `ai/app/schemas.py` | Integração fallback tático + MLflow | 1, 2 |
| `ai/app/redis_listener.py` | Fallback tático + anti-repetição + MLflow | 1, 2 |
| `ai/app/metrics.py` | **NOVO** - MLflowTracker | 2 |
| `ai/app/debrief.py` | **NOVO** - Prompt, validação, fallback e persistência do debrief | 3 |
| `ai/app/redis_listener.py` | Histórico de eventos e disparo do debrief no `race_end` | 3 |
| `ai/tests/test_debrief.py` | **NOVO** - Testes do contrato, geração, fallback e Redis | 3 |
| `ai/tests/test_debrief_listener.py` | **NOVO** - Teste do histórico enviado pelo listener | 3 |
| `backend/api/main.py` | Endpoint `GET /races/{race_id}/debrief` | 3 |
| `backend/tests/test_debrief_api.py` | **NOVO** - Testes 200/404/500/503 do endpoint | 3 |
| `viz3d/src/live/DebriefPanel.tsx` | **NOVO** - Painel pós-corrida com atualização automática | 3 |
| `viz3d/src/live/LiveRace.tsx` | Botão e estado para abrir o debrief | 3 |
| `ai/app/fallback_tactical.py` | **NOVO** - Fallback tático | 1 |
| `backend/engine/ai_engineer.py` | Eventos ciclo de vida + correção sim_ts | 1, 2 |
| `backend/engine/events.py` | +4 eventos: `ai_started`, `ai_monitoring`, `ai_stopped`, `ai_error` | 1 |
| `frontend/src/stores/live-race-store.ts` | `followedDriverId`, `followDriver`, `unfollowDriver` | 10 |
| `frontend/src/components/race/driver-follow-card.tsx` | **NOVO** - Painel acompanhamento lateral | 10 |
| `frontend/src/components/race/timing-panel.tsx` | Botões 👁/✕ por linha | 10 |
| `frontend/src/components/race/ai/ai-floating-panel.tsx` | Lê `followedDriverId` do store | 10 |
| `frontend/src/pages/race-simulation.tsx` | `DriverFollowCard` + botão condicional | 10 |
| `frontend/src/components/race/driver-follow-card.tsx` | **NOVO** - Componente acompanhamento | 10 |
| `.github/workflows/ai-validation.yml` | **NOVO** - CI/CD pipeline | - |

---

## 10. Correção do Modal de Acompanhamento de Piloto ✅ **CONCLUÍDO**

### 10.1. Auditoria do posicionamento atual ✅
- [x] Identificado: `DriverCard` renderizado em `bottom-4 right-4` (canto)
- [x] Localizado: `race-simulation.tsx` linha ~214
- [x] CSS: `position: absolute`, `z-20`, fora do container do simulador
- [x] Conflitos: Canvas/WebGL, HUD, AiFloatingPanel

### 10.2. Corrigir o posicionamento e integrar à tela ✅
- [x] **Novo componente**: `DriverFollowCard` (`driver-follow-card.tsx`)
- [x] Posicionamento: lateral direita da área do simulador (`w-60 h-full border-l`)
- [x] Respeita limites do container do simulador (não viewport)
- [x] Elimina posicionamento no canto superior direito
- [x] Sem sobreposição com HUD, AiFloatingPanel, controles
- [x] Compatível 2D e 3D (mesmo componente)
- [x] Responsivo (`w-60` fixo, `h-full` com scroll)

### 10.3. Controlar a exibição pelo estado de acompanhamento ✅
- [x] **REGRA**: Modal só aparece quando `followedDriverId` está setado
- [x] Inicialmente oculto (sem piloto acompanhado)
- [x] Não aparece ao iniciar corrida (sem `followedDriverId`)
- [x] Clicar 👁 no TimingPanel → `followDriver()` → modal aparece
- [x] Associado ao `driver_id` do carro acompanhado
- [x] Trocar acompanhado → `followDriver(novo_id)` → modal atualiza
- [x] Clicar ✕ → `unfollowDriver()` → modal desaparece
- [x] Seleção visual (`selectedDriverId`) ≠ acompanhamento (`followedDriverId`)
- [x] Estado preservado em reconexões (store persiste)

### 10.4. Separação dos estados ✅
- [x] `selectedDriverId`: piloto selecionado visualmente (câmera, card)
- [x] `followedDriverId`: piloto efetivamente acompanhado (rádio, modal)
- [x] `followedDriverId` = condição principal para exibir modal
- [x] TimingPanel usa `followedDriverId` para mostrar 👁/✕
- [x] AiFloatingPanel lê `followedDriverId` do store
- [x] Sincronização Zustand garantida

### 10.5. Testes de aceitação ✅ **TODOS PASSAM**
- [x] Iniciar corrida sem acompanhar: modal **oculto**
- [x] Clicar 👁 no TimingPanel: modal **aparece na lateral**
- [x] Trocar carro acompanhado: modal **atualiza automaticamente**
- [x] Clicar ✕: modal **desaparece**
- [x] Alternar 2D/3D: modal **mantém posição**
- [x] Redimensionar janela: modal **dentro da área do simulador**
- [x] Atualizar navegador: modal **respeita estado recuperado**
- [x] Não interfere com AiFloatingPanel, HUD, câmera

**Critério de conclusão: ✅ ATENDIDO** — modal integrado à área do simulador, não flutua no canto, só renderiza com piloto acompanhado.

---

## 11. Próximos Passos Imediatos (Atualizado)

A execução foi dividida em duas frentes com arquivos isolados; detalhes, bloqueios e critérios de conclusão estão na **seção 15**.

1. **Frente A — IA/Ollama:** medir o novo prompt do debrief com serviços reais, ajustar somente se os dados mostrarem necessidade e validar `race_end` → Redis → API.
2. **Frente B — Frontend/TTS/Viz3d:** alinhar o Vite do `viz3d`, concluir a divisão do vendor Three e executar as validações manuais de voz e do painel.
3. **Integração final:** após as duas frentes, rodar uma corrida completa e atualizar este plano com resultados medidos, sem marcar validações manuais como concluídas antecipadamente.

---

## 12. Comandos de Validação Docker

```bash
# Build e subir ambiente
docker compose up -d --build

# Verificar logs IA
docker compose logs -f ai

# Testar fallback (simular timeout)
# Editar TIMEOUT_SECONDS=1 em client.py temporariamente

# Ver métricas MLflow
docker compose exec backend python -c "
import mlflow
mlflow.set_tracking_uri('sqlite:///mlflow.d')
exp = mlflow.get_experiment_by_name('Default')
runs = mlflow.search_runs(exp.experiment_id)
print(runs[['params.key', 'metrics.latency_p50', 'metrics.fallback_rate_pct']].head())
"

# Ver debrief persistido
docker compose exec redis redis-cli GET "race:<id>:debrief"

# Testes
.venv/bin/python -m pytest ai/tests/ -v
.venv/bin/python -m pytest backend/tests/test_random_events.py backend/tests/test_live_race_api.py -v
cd frontend && npm run build
```

---

## 13. Notas e Decisões Técnicas

- **Não duplicar** `AiEngineer` do backend (já existe em `backend/engine/`)
- **Não modificar** física PyBullet para resolver UI
- **Preservar** compatibilidade com `viz3d` e `frontend/`
- **Usar** `mlflow.d` SQLite existente (não criar novo)
- **Web Speech API** é nativa, sem dependência externa
- **Debrief** síncrono no `race_end` (não interfere tempo real); timeout específico padrão de 30s e fallback factual garantem persistência mesmo sem resposta do LLM
- **Desempenho do debrief** ainda não foi medido após a redução do prompt; não marcar o critério de 30s como concluído sem Ollama real
- **Code-splitting frontend** concluído; o Three permanece como vendor monolítico de 675,59 kB e possui orçamento explícito de 700 kB
- **Code-splitting viz3d** parcial; o build atual ainda contém `AiEngineer` de 925,80 kB porque o vendor não foi separado
- **Separação clara**: `followedDriverId` (rádio/modal) ≠ `selectedDriverId` (visual/câmera)

---

## 14. Arquivos Prováveis para as Próximas Modificações

Os caminhos abaixo indicam onde cada pendência provavelmente será alterada ou verificada. Não é necessário abrir todos: começar pelos arquivos principais e consultar integração e testes conforme o comportamento observado.

### 14.1. Desempenho e validação do debrief pelo LLM

| Finalidade | Arquivos |
|------------|----------|
| Ajustar prompt, limite de tokens, timeout, validação e fallback | `ai/app/debrief.py` |
| Conferir parâmetros enviados ao Ollama | `ai/app/client.py` |
| Revisar coleta do histórico e disparo no `race_end` | `ai/app/redis_listener.py` |
| Configurar variáveis de ambiente do serviço | `docker-compose.yml` |
| Verificar contrato e consulta do debrief | `backend/api/main.py`, `viz3d/src/live/api.ts`, `viz3d/src/live/types.ts` |
| Validar apresentação e abertura após a corrida | `viz3d/src/live/DebriefPanel.tsx`, `viz3d/src/live/LiveRace.tsx` |
| Ampliar testes do fluxo | `ai/tests/test_debrief.py`, `ai/tests/test_debrief_listener.py`, `ai/tests/test_client.py`, `backend/tests/test_debrief_api.py` |

### 14.2. Centralização e validação do TTS

| Finalidade | Arquivos |
|------------|----------|
| Centralizar fila, prioridade, seleção de voz e controles | `viz3d/src/ai/SpeechSynthesis.ts` |
| Substituir chamadas diretas à Web Speech API no viz3d | `viz3d/src/ai/AiEngineer.tsx`, `viz3d/src/ai/AiPanel.tsx` |
| Avaliar a mesma integração nos painéis do frontend | `frontend/src/components/race/ai/ai-panel.tsx`, `frontend/src/components/race/ai/ai-floating-panel.tsx` |
| Conferir contratos das mensagens faladas | `frontend/src/types/race.ts`, `viz3d/src/live/types.ts` |

### 14.3. Code-splitting dos frontends

| Finalidade | Arquivos |
|------------|----------|
| Configurar divisão dos bundles | `frontend/vite.config.ts`, `viz3d/vite.config.ts` |
| Revisar carregamento das páginas principais | `frontend/src/App.tsx`, `frontend/src/pages/race-simulation.tsx`, `viz3d/src/App.tsx`, `viz3d/src/live/LiveRace.tsx` |
| Manter a cena 3D sob carregamento lazy | `frontend/src/components/race/view-3d/race-view-3d.tsx`, `frontend/src/components/race/view-3d/race-scene.tsx` |
| Executar e comparar os builds | `frontend/package.json`, `viz3d/package.json` |

### 14.4. Validação integrada de uma corrida completa

| Finalidade | Arquivos |
|------------|----------|
| Criar corridas curtas e injetar eventos de demonstração | `backend/scripts/visualization/run_live_compare.py`, `backend/scripts/visualization/random_events.py` |
| Subir e configurar os serviços | `docker-compose.yml` |
| Registrar os resultados da validação manual | `ai/report/VALIDACAO_DOCKER.md` |
| Manter a automação alinhada ao fluxo validado | `.github/workflows/ai-validation.yml` |

Após as modificações, atualizar este plano e `ai/report/VALIDACAO_DOCKER.md` somente com resultados efetivamente reproduzidos, distinguindo testes unitários, builds, validação com serviços reais e verificação visual.

---

## 15. Handoff e Execução Paralela (2026-11-27)

Esta seção é o estado mais recente e prevalece sobre resumos anteriores quando houver divergência.

### 15.1. O que foi feito nesta rodada

- **Debrief:** prompt e histórico reduzidos; classificação não é mais duplicada; limite de 512 tokens e timeout de 30s; novo teste garante o limite de eventos.
- **UI do debrief:** removidas as duplicações que impediam o TypeScript de compilar; o painel agora recebe `raceId` por props, usa `live/api.ts`, fecha corretamente e possui CSS próprio do `viz3d`.
- **TTS:** chamadas nativas espalhadas substituídas por gerenciadores com fila, prioridade, deduplicação, cancelamento, seleção de voz e fallbacks.
- **Frontend:** páginas carregadas com `React.lazy`; vendors separados no Vite/Rolldown.
- **Viz3d:** modos gravação/ao vivo carregados com `React.lazy`; build voltou a compilar.

Validações reproduzidas:

| Validação | Resultado |
|-----------|-----------|
| `pytest ai/tests/ -q` | **35 passed** |
| `pytest backend/tests/test_debrief_api.py -q` | **4 passed** |
| Testes do frontend | **56 passed** |
| Testes do gerenciador TTS | **4 passed** |
| `frontend/npm run build` | **Passou** |
| `viz3d/npm run build` | **Passou**, com aviso do chunk Three de 925,80 kB |
| Ollama + corrida real após as mudanças | **Não executado; serviços indisponíveis** |
| Validação manual de voz/painel em navegador | **Pendente** |

Bundles do frontend:

| Chunk | Antes | Agora |
|-------|-------|-------|
| Entrada `index` | 598,42 kB | **42,02 kB** |
| `race-scene` | 1.007,61 kB | **157,75 kB** |
| `race-simulation` | incluído na entrada | **52,41 kB** |
| `react-three` | incluído na cena | **169,58 kB** |
| `three` | incluído na cena | **675,59 kB** (171,52 kB gzip) |

O orçamento de aviso do Three foi definido explicitamente como 700 kB. Isso **não significa** que todos os chunks ficaram abaixo de 500 kB; significa que o vendor monolítico foi isolado e o código da aplicação foi dividido.

### 15.2. Dificuldades e bloqueios conhecidos

1. **Sem benchmark real do novo debrief:** Ollama não respondeu em `localhost:11434` e `docker compose ps` não mostrou serviços ativos. Ajustes de latência foram validados por testes, não por uma corrida real.
2. **Versões divergentes no `viz3d`:** o `node_modules` contém Vite **5.4.21**, enquanto `package.json` e `package-lock.json` declaram **8.2.2**. A configuração `rolldownOptions` funciona no frontend com Vite 8, mas falha no TypeScript do `viz3d` com Vite 5. A configuração incompatível foi revertida; não se deve manter as duas versões como estado final.
3. **Three monolítico:** o Rolldown separa rotas e dependências, mas não divide o módulo principal do Three em unidades menores que 500 kB. O vendor ficou isolado; qualquer aumento de `chunkSizeWarningLimit` precisa ser documentado, não apresentado como redução de código.
4. **Validação de Web Speech depende do navegador:** testes com mocks provam fila e seleção, mas não provam voz audível, política de autoplay nem diferenças Chrome/Firefox.
5. **Worktree compartilhado:** há uma frente independente de recuperação de corridas em `ai/report/plano-recuperacao-corridas.md`, com alterações em checkpoint, `race_manager`, store, tipos e `docker-compose.yml`. Essas alterações **não fazem parte desta rodada de IA/TTS e não devem ser sobrescritas**.

### 15.3. Frente A — IA/Ollama/Debrief (uma IA)

**Objetivo:** obter evidência real de que o debrief atual produz JSON válido em até 30s, ou registrar medidas suficientes para revisar essa meta.

**Arquivos que pode alterar:**

- `ai/app/debrief.py`, `ai/app/client.py` e `ai/app/redis_listener.py` (somente se um defeito for reproduzido)
- `ai/tests/test_debrief.py`, `ai/tests/test_debrief_listener.py`, `ai/tests/test_client.py`
- `ai/report/VALIDACAO_DOCKER.md`

**Não alterar:** frontends, `docker-compose.yml`, arquivos de checkpoint/recovery e este plano principal durante a execução.

**Passos:**

- [ ] **A1 — Preparar serviços:** subir Ollama/Redis e confirmar modelo carregado; não editar o compose compartilhado para isso.
- [ ] **A2 — Medir antes de otimizar novamente:** executar uma chamada fria e pelo menos três chamadas quentes com dados reais; registrar latência, tokens, `fallback`, `fallback_motivo` e validade do JSON.
- [ ] **A3 — Ajustar somente com evidência:** se necessário, alterar `DEBRIEF_NUM_PREDICT`, `DEBRIEF_NUM_CTX` ou o prompt sem mudar os parâmetros das sugestões ao vivo.
- [ ] **A4 — Validar fluxo integral:** executar `race_end` → geração → `race:{id}:debrief` → `GET /races/{id}/debrief`; testar também timeout/fallback.
- [ ] **A5 — Registrar handoff:** documentar comandos, ambiente, versões e medições em `VALIDACAO_DOCKER.md`; devolver um resumo para o integrador atualizar este plano.

**Critérios de conclusão:**

- JSON do LLM aceito por `validate_debrief_output()` e persistido com `fallback: false`.
- Meta de 30s medida em corrida real, ou nova meta explicitamente justificada pelos resultados.
- Testes de IA e do endpoint continuam passando.

### 15.4. Frente B — Frontend/Viz3d/TTS (outra IA)

**Objetivo:** terminar o bundle do `viz3d` e fazer as validações que dependem de navegador, sem tocar no backend nem na frente de recovery.

**Arquivos que pode alterar:**

- `frontend/src/App.tsx`, `frontend/vite.config.ts`
- `frontend/src/services/speech-synthesis.ts`, `frontend/src/components/race/ai/*`
- `viz3d/src/main.tsx`, `viz3d/vite.config.ts`, `viz3d/src/ai/*`
- `viz3d/src/live/DebriefPanel.tsx`, `DebriefPanel.css`, `LiveRace.tsx`, `api.ts`, `types.ts`
- `viz3d/src/services/api.ts`
- `ai/report/VALIDACAO_FRONTEND.md` (novo, para evitar escrita concorrente no relatório da Frente A)

**Não alterar:** `ai/app/*`, backend, `docker-compose.yml`, `frontend/src/stores/live-race-store.ts`, `frontend/src/types/race.ts`, arquivos de recovery e este plano principal durante a execução.

**Passos:**

- [ ] **B1 — Reproduzir o ambiente:** no `viz3d`, executar `npm ci` e confirmar que o Vite instalado é 8.2.2. Se a instalação não for possível, registrar o bloqueio e usar configuração compatível, sem alterar versões do manifesto silenciosamente.
- [ ] **B2 — Fechar o code-splitting:** separar React/Three/R3F no `viz3d`, mantendo `App` e `LiveRace` lazy. Documentar qualquer orçamento acima de 500 kB; não ocultar avisos sem justificativa.
- [ ] **B3 — Regressão automática:** rodar builds e todos os testes de `frontend` e `viz3d`; verificar navegação entre rotas e alternância 2D/3D após o lazy loading.
- [ ] **B4 — Validar TTS manualmente:** em Chrome e Firefox disponíveis, testar `pt-BR`, seleção de voz, fallback instalado, fila sem sobreposição, desligar durante a fala e reativar sem backlog.
- [ ] **B5 — Validar o painel:** abrir/fechar o debrief após `race_end`, verificar todas as seções, polling enquanto não existe conteúdo, estado de erro e apresentação do fallback. A validação com LLM depende da Frente A; a validação com fallback pode começar já.
- [ ] **B6 — Registrar handoff:** salvar evidências em `VALIDACAO_FRONTEND.md` e devolver resumo ao integrador.

**Critérios de conclusão:**

- `npm run build` e testes passam nos dois frontends com dependências alinhadas aos manifestos.
- `viz3d` não contém mais o chunk de aplicação+Three de 925,80 kB; qualquer vendor restante está isolado e justificado.
- Checklist manual registra navegador, voz, comportamento ouvido e resultado; testes com mocks não são usados como substitutos.

### 15.5. Integração final (após A e B)

- [ ] Executar uma corrida curta completa com Ollama, Redis, backend e frontends.
- [ ] Confirmar TTS durante a corrida e debrief real após `race_end` na mesma execução.
- [ ] Rodar a suíte combinada e comparar os tamanhos finais dos bundles com a tabela acima.
- [ ] Atualizar este plano central em uma única escrita, incorporando os dois handoffs.
- [ ] Validar recovery separadamente pelo plano próprio; não misturar seus critérios com os de IA/TTS.

### 15.6. Regra para as duas IAs

Trabalhar em **worktrees separados** é o preferível. Se usarem o mesmo worktree, cada uma deve respeitar estritamente sua lista de arquivos, não rodar `git reset`/`checkout`, não apagar mudanças alheias e não editar este plano principal. Commits e pushes somente mediante solicitação explícita do usuário.

### 15.7. Identificação sugerida para a entrega

- **Branch atual:** `feat/ai-engineer-integration-4`
- **Branch sugerida, caso esta entrega seja separada:** `feat/ai-debrief-tts-bundles`
- **Título de commit sugerido:** `feat(ai): otimizar debrief, centralizar TTS e dividir bundles`

**Resumo da entrega:**

- Reduzir o prompt e os parâmetros de geração do debrief, mantendo fallback e contrato validados por testes.
- Corrigir o painel de debrief do `viz3d`, incluindo integração da API, polling, fechamento e estilos próprios.
- Centralizar o TTS em gerenciadores com fila, prioridade, deduplicação, cancelamento e seleção de voz com fallbacks.
- Adicionar testes para limites do prompt e comportamento do gerenciador de voz.
- Aplicar lazy loading às rotas do frontend e às entradas do `viz3d`.
- Separar os vendors do frontend e registrar explicitamente o orçamento do Three monolítico.
- Atualizar o plano de desenvolvimento e o relatório de validação com resultados e pendências reais.
- Corrigir o pipeline de pull request: caminho do lockfile no cache npm, f-strings incompatíveis com Python 3.11 nos contextos/schemas, stub Redis do teste de largada e configuração TypeScript 6 do `viz3d` validada no Docker.

**Validação registrada:** 35 testes de IA, 4 testes da API do debrief, 56 testes do frontend e 4 testes de TTS passando; builds dos dois frontends concluídos.

**Fora do escopo deste commit:** alterações de checkpoint/recovery, `race_manager`, store/tipos da recuperação e configurações compartilhadas do `docker-compose.yml`. Antes de um commit solicitado pelo usuário, revisar o stage para não misturar essas frentes.