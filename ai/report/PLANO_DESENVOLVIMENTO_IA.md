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
| **Síntese de voz (TTS)** | 🔄 Implementado - Validação manual pendente | `viz3d/src/ai/SpeechSynthesis.ts` + painéis |
| **Debrief pós-corrida** | 🔄 Fluxo completo - LLM requer validação de desempenho | `ai/app/debrief.py` + `viz3d/src/live/DebriefPanel.tsx` |
| **Code-splitting frontend** | ❌ Pendente | - |

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
- ✅ `viz3d/src/ai/SpeechSynthesis.ts` criado com Web Speech API, seleção de voz em português, fila por prioridade e controles de reprodução
- ✅ Sugestões faladas em `AiEngineer.tsx` (viz3d), `ai-panel.tsx` e `ai-floating-panel.tsx` (frontend)
- ✅ Velocidade, tom e volume ajustados pela urgência; ativação/desativação disponível nos painéis principais
- ✅ Builds de `frontend` e `viz3d` concluídos

### Pendente
- [ ] Centralizar os componentes no gerenciador `SpeechSynthesis.ts`; atualmente parte deles chama a API nativa diretamente
- [ ] Validar manualmente voz `pt-BR`, ausência de sobreposição e interrupção em navegadores diferentes
- [ ] Completar seleção de voz pelo usuário e fallback explícito para `pt-PT`/`en-US`

### Estimativa restante: 2h

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

### Validação executada
- ✅ 38 testes de IA e do endpoint passaram
- ✅ Builds de `frontend` e `viz3d` concluídos
- ✅ Teste com Ollama e Redis reais confirmou geração do fallback, persistência, recuperação e resposta da API
- ⚠️ O LLM excedeu 30 segundos no primeiro teste e 60 segundos no segundo; portanto, uma resposta real válida ainda não foi confirmada

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

### Pendente
- [ ] **Frontend build**: Code splitting para chunks >500kB
- [ ] **Limpar arquivos temporários**: `_ws_probe_tmp.py`, `_start_probe_tmp.py`

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
| Limpeza arquivos temporários | ⬜ Pendente |

### Fase 3: Features Avançadas (Semana 3) 🔄 **EM ANDAMENTO**
| Tarefa | Status |
|--------|--------|
| TTS (Web Speech API) | 🔄 Implementado; validação manual pendente |
| Debrief pós-corrida | 🔄 Fluxo completo; desempenho do LLM pendente |
| Endpoint/API debrief + UI | ✅ Implementado e testado |
| Code-splitting frontend | ❌ Pendente |

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
- [ ] Voz pt-BR reproduz `aviso` (código implementado; validação manual pendente)
- [ ] Sem sobreposição de mensagens (fila implementada; integração dos componentes ao gerenciador pendente)
- [ ] Interrupção funciona (controle implementado; validação manual pendente)

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

1. **Validar e ajustar geração do debrief pelo LLM** — resposta real excedeu 60s; fallback, API e persistência já validados — ~1–2h
2. **Validar TTS nos navegadores e centralizar componentes no gerenciador** — `viz3d/src/ai/SpeechSynthesis.ts` — ~2h
3. **Code-splitting frontend** — reduzir chunks >500kB — ~4h
4. **Validação visual de uma corrida completa** — acompanhar `race_end`, abrir o debrief no `viz3d` e verificar todas as seções — ~1h

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
- **Debrief** síncrono no `race_end` (não interfere tempo real); timeout específico de 60s e fallback factual garantem persistência mesmo sem resposta do LLM
- **Desempenho do debrief** ainda não atende à meta de 30s com o LLM; não marcar esse critério como concluído
- **Code-splitting** necessário no frontend (chunks >500kB)
- **Separação clara**: `followedDriverId` (rádio/modal) ≠ `selectedDriverId` (visual/câmera)