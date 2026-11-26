# Plano de Desenvolvimento Atualizado — IA de Corrida

**Última atualização**: 2026-11-26

---

## Resumo do Estado Atual

| Componente | Status | Localização |
|------------|--------|-------------|
| **AI Engineer (backend)** | ✅ Implementado | `backend/engine/ai_engineer.py` |
| **Eventos de ciclo de vida** | ✅ Implementado | `backend/engine/events.py` |
| **AI Panel (frontend 2D/3D)** | ✅ Implementado | `frontend/src/components/race/ai/` |
| **AiFloatingPanel** | ✅ Implementado | `frontend/src/components/race/ai/ai-floating-panel.tsx` |
| **Serviço IA (Ollama)** | ✅ Implementado | `ai/app/` |
| **Redis Listener** | ✅ Implementado | `ai/app/redis_listener.py` |
| **Fallback determinístico** | ✅ Parcial | `ai/app/schemas.py:fallback_output()` |
| **Síntese de voz (TTS)** | ❌ Pendente | - |
| **Debrief pós-corrida** | ❌ Pendente | - |
| **Métricas MLflow** | ❌ Pendente | - |
| **Otimização Ollama** | 🔄 Parcial | `ai/app/client.py` |

---

## 1. Fallback Determinístico (Prioridade: ALTA)

### Estado Atual
- ✅ `fallback_output()` em `ai/app/schemas.py` retorna estrutura padrão
- ✅ Captura timeout, erro de conexão, JSON inválido
- ❌ **Falta**: Respostas táticas específicas baseadas em condições reais

### A Implementar
- [ ] **Mapeamento de condições → comando/frase predefinida** em `ai/app/fallback_tactical.py`
  - Rival < 0.9s → `overtake` + "Rival colado, tenta a ultrapassagem!"
  - Pneu < 35% → `conserve` + "Pneus desgastados, cuida deles!"
  - Combustível < 40kg → `conserve` + "Combustível crítico, economiza!"
  - Safety Car ativo → `careful` + "Safety Car na pista, mais margem!"
  - Últimas 3 voltas → `push` + "Últimas voltas, ataque total!"
  - Pista molhada → `careful` + "Pista escorregadia, cautela!"
- [ ] **Integrar no `redis_listener.py`** antes do `fallback_output()` genérico
- [ ] **Testes unitários** para cada cenário tático

### Estimativa: 4h

---

## 2. Otimização de Latência do Ollama (Prioridade: ALTA)

### Estado Atual
- `client.py`: `TIMEOUT_SECONDS = 90`, sem `keep_alive`, `num_predict`, `num_ctx`
- Modelo: `llama3.2` (padrão)
- Latência observada: 20-60s

### A Implementar
- [ ] **Adicionar parâmetros de otimização** em `ai/app/client.py`:
  ```python
  json={
      "model": MODEL,
      "prompt": prompt,
      "stream": False,
      "format": "json",
      "options": {
          "keep_alive": "30m",
          "num_predict": 150,
          "num_ctx": 2048,
          "temperature": 0.3,
          "top_p": 0.9,
      }
  }
  ```
- [ ] **Otimizar prompt** em `ai/app/prompts/main_prompt.py`:
  - Remover redundâncias
  - Encurtar instruções
  - Usar exemplos few-shot mais compactos
- [ ] **Benchmark antes/depois** com script de medição
- [ ] **Registrar resultados** em `docs/OLLAMA_LATENCY_BENCHMARK.md`

### Estimativa: 3h

---

## 3. Rádio com Síntese de Voz (TTS) (Prioridade: MÉDIA)

### Estado Atual
- ❌ Não implementado no `viz3d`
- Frontend usa apenas texto no HUD

### A Implementar
- [ ] **Criar `viz3d/src/ai/SpeechSynthesis.ts`**:
  - Usar `window.speechSynthesis` (Web Speech API)
  - Priorizar vozes `pt-BR`
  - Fila de mensagens (evitar sobreposição)
  - Interromper mensagem anterior se nova chegar
  - Controle de volume/velocidade
- [ ] **Integrar no `AiEngineer.tsx`** (orb 3D) e `AiPanel.tsx` (2D)
- [ ] **Configuração do usuário**: ativar/desativar, selecionar voz
- [ ] **Fallback**: se voz pt-BR não disponível, usar `pt-PT` ou `en-US`

### Estimativa: 5h

---

## 4. Debrief Pós-Corrida (Prioridade: MÉDIA)

### Estado Atual
- ❌ Não implementado
- Evento `race_end` existe mas não dispara debrief

### A Implementar
- [ ] **Criar `ai/app/debrief.py`**:
  - Coletar dados: largada, chegadas, saídas de pista, pits, comandos IA, contatos
  - Montar prompt estruturado para LLM
  - Chamar Ollama **uma vez** no evento `race_end`
  - Persistir em `race:<id>:debrief` (JSON + markdown)
- [ ] **Integrar no `redis_listener.py`**: detectar `race_end` e disparar
- [ ] **Endpoint API** `GET /races/{id}/debrief` para visualizador
- [ ] **Exibir no `viz3d`** nova aba/painel "Debrief"

### Estimativa: 6h

---

## 5. Métricas e Observabilidade MLflow (Prioridade: MÉDIA)

### Estado Atual
- `mlflow.d` existe (SQLite) mas não é usado pela IA
- Logs básicos no console

### A Implementar
- [ ] **Criar `ai/app/metrics.py`** com `MLflowTracker`:
  ```python
  class MLflowTracker:
      def log_latency(self, elapsed: float)
      def log_fallback(self, motivo: str)
      def log_invalid_json(self)
      def log_suppressed_duplicate(self)
      def log_timeout(self)
      def log_error(self, error_type: str)
      def log_ollama_availability(self, available: bool)
  ```
- [ ] **Integrar em `client.py`**, `schemas.py`, `redis_listener.py`
- [ ] **Dashboard MLflow** com queries para slides:
  - Latência p50/p95
  - Taxa fallback (%)
  - JSON inválido (%)
  - Timeouts/erros
  - Disponibilidade Ollama
- [ ] **Script de exportação** para CSV/gráficos

### Estimativa: 5h

---

## 6. Correções e Melhorias Identificadas (Prioridade: ALTA)

### Bugs Conhecidos
- [ ] **`_publish_lifecycle_event`**: `sim_ts` duplicado nos eventos (já corrigido no `ai_engineer.py`)
- [ ] **`AiMonitoringEvent`**: `sim_ts` passado duas vezes (corrigido)
- [ ] **Frontend build**: Warnings de chunks grandes (>500kB) - code splitting

### Melhorias de Arquitetura
- [ ] **Separar `followedDriverId` de `selectedDriverId`** no store (parcialmente feito)
- [ ] **Validar `raceId` no `apply()`** do store (já implementado)
- [ ] **Limpar arquivos temporários**: `_ws_probe_tmp.py`, `_start_probe_tmp.py`

---

## 7. Plano de Execução por Fases

### Fase 1: Estabilidade e Fallback (Semana 1)
| Tarefa | Esforço | Dependência |
|--------|---------|-------------|
| Fallback tático determinístico | 4h | - |
| Otimização Ollama (parâmetros + prompt) | 3h | - |
| Testes de fallback | 2h | Fallback tático |
| Benchmark Ollama | 1h | Otimização |

**Total: 10h**

### Fase 2: Observabilidade (Semana 2)
| Tarefa | Esforço | Dependência |
|--------|---------|-------------|
| MLflowTracker + integração | 5h | - |
| Dashboard/queries MLflow | 3h | MLflowTracker |
| Limpeza arquivos temporários | 1h | - |

**Total: 9h**

### Fase 3: Features Avançadas (Semana 3)
| Tarefa | Esforço | Dependência |
|--------|---------|-------------|
| TTS (Web Speech API) | 5h | - |
| Debrief pós-corrida | 6h | Redis listener |
| Endpoint/API debrief + UI | 3h | Debrief core |

**Total: 14h**

---

## 8. Critérios de Validação

### Fallback Determinístico
- [ ] Rival 0.5s → `overtake` + frase específica
- [ ] Pneu 30% → `conserve` + frase específica
- [ ] Timeout Ollama → fallback tático (não genérico)
- [ ] 100% cenários cobertos em testes

### Ollama Latência
- [ ] p50 < 10s (era 20-60s)
- [ ] p95 < 20s
- [ ] Timeout < 5%

### TTS
- [ ] Voz pt-BR reproduz `aviso`
- [ ] Sem sobreposição de mensagens
- [ ] Interrupção funciona

### Debrief
- [ ] Gerado em < 30s após `race_end`
- [ ] Persistido em `race:<id>:debrief`
- [ ] Legível e completo

### MLflow
- [ ] Métricas registradas a cada chamada
- [ ] Dashboard mostra p50/p95, taxa fallback, etc.
- [ ] Exportação CSV funciona

---

## 9. Rastreabilidade de Arquivos Modificados

| Arquivo | Mudança | Fase |
|---------|---------|------|
| `ai/app/client.py` | Parâmetros Ollama otimizados | 1 |
| `ai/app/prompts/main_prompt.py` | Prompt otimizado | 1 |
| `ai/app/fallback_tactical.py` | **NOVO** - Fallback tático | 1 |
| `ai/app/schemas.py` | Integração fallback tático | 1 |
| `ai/app/redis_listener.py` | Usa fallback tático | 1 |
| `ai/app/metrics.py` | **NOVO** - MLflowTracker | 2 |
| `ai/app/client.py` | Log latência/erros no MLflow | 2 |
| `ai/app/schemas.py` | Log fallback/inválido no MLflow | 2 |
| `ai/app/redis_listener.py` | Log duplicatas/timeouts no MLflow | 2 |
| `viz3d/src/ai/SpeechSynthesis.ts` | **NOVO** - TTS | 3 |
| `viz3d/src/ai/AiEngineer.tsx` | Integração TTS | 3 |
| `viz3d/src/components/race/ai/ai-panel.tsx` | Integração TTS | 3 |
| `ai/app/debrief.py` | **NOVO** - Debrief generator | 3 |
| `ai/app/redis_listener.py` | Dispara debrief no `race_end` | 3 |
| `backend/api/main.py` | Endpoint `/debrief` | 3 |
| `viz3d/src/live/DebriefPanel.tsx` | **NOVO** - UI Debrief | 3 |

---

## 10. Próximos Passos Imediatos

1. **Criar `fallback_tactical.py`** com mapeamento completo
2. **Atualizar `client.py`** com parâmetros otimizados
3. **Rodar benchmark** de latência antes/depois
4. **Implementar `MLflowTracker`** básico
5. **Testar integração** completa em Docker

---

## 11. Comandos de Validação Docker

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
print(runs[['params.key', 'metrics.latency']].head())
"

# Ver debrief
docker exec redis redis-cli GET "race:<id>:debrief"
```

---

## 12. Notas e Decisões Técnicas

- **Não duplicar** `AiEngineer` do backend (já existe em `backend/engine/`)
- **Não modificar** física PyBullet para resolver UI
- **Preservar** compatibilidade com `viz3d` e `frontend/`
- **Usar** `mlflow.d` SQLite existente (não criar novo)
- **Web Speech API** é nativa, sem dependência externa
- **Debrief** síncrono no `race_end` (não interfere tempo real)