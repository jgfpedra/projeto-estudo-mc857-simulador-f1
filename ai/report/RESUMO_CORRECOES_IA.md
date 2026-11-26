# Resumo das Correções no AI Engineer

## Problemas Abordados

✅ **Engenheiro ignora piloto do usuário** - Agora analisa mas não executa comandos automáticos
✅ **Lógica de recomendação misturada com execução** - Separada em `_analyze_driver()` e `_execute_recommendation()`
✅ **IA não analisa piloto do usuário** - Agora analisa e publica sugestões textuais (`_publish_suggestion_only()`)
✅ **Inicialização automática** - Já funcionava via `race_manager.py`, mantido
✅ **Dados corretos do SimulationEngine** - Via `publisher.snapshot` (já funcionava)
✅ **Frequência de análise** - Reduzida de 8s para 5s (simulado) + rate limit 10s (real)
✅ **Eventos de ciclo de vida** - Implementados: `ai_started`, `ai_monitoring`, `ai_stopped`, `ai_error`
✅ **Publicação imediata de `ai_started`** - No método `start()`
✅ **Heartbeat `ai_monitoring`** - A cada 10 ciclos (~3s real)
✅ **Ausência de recomendações ≠ falha** - Status "monitoring" mostra IA ativa
✅ **Erros comunicados ao frontend** - Evento `ai_error` com detalhes
✅ **Encerramento correto** - `stop(reason)` publica `ai_stopped` com stats

---

## Arquivos Modificados

### Backend

| Arquivo | Mudanças Principais |
|---------|---------------------|
| `engine/ai_engineer.py` | **Reescrita completa**: separação análise/execução, DriverRole enum, Recommendation dataclass, eventos de ciclo de vida, logs estruturados, stats |
| `engine/events.py` | +4 novos eventos: `AiStartedEvent`, `AiMonitoringEvent`, `AiStoppedEvent`, `AiErrorEvent` |

### Frontend

| Arquivo | Mudanças Principais |
|---------|---------------------|
| `types/race.ts` | +4 tipos: `AiStarted`, `AiMonitoring`, `AiStopped`, `AiError` + union no `LiveMessage` |
| `services/race-parser.ts` | +4 cases no `parseLiveMessage()` para novos eventos |
| `stores/live-race-store.ts` | +3 campos de estado (`aiEngineerStatus`, `aiEngineerStats`, `aiEngineerError`) + handlers no `apply()` |
| `components/race/ai/ai-panel.tsx` | Props expandidas: `engineerStatus`, `engineerStats`, `engineerError` + UI de status, stats, erros |
| `components/race/ai/ai-engineer.tsx` | Props expandidas + cor/baseada em status, indicador visual, pulsaçao adaptativa |
| `components/race/view-3d/race-scene.tsx` | Selectors novos + passa props para `AiEngineer` |
| `pages/race-simulation.tsx` | Selectors novos + passa props para `AiPanel` |

---

## Fluxo de Dados Atualizado

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (AiEngineer)                         │
├─────────────────────────────────────────────────────────────────────┤
│  start() ──▶ ai_started (race_id, total_laps, user_driver_id, ...) │
│     │                                                                │
│     ▼                                                                │
│  _run() loop (0.3s real)                                            │
│     │                                                                │
│     ├──▶ _evaluate_and_recommend() ──▶ _build_situations()         │
│     │         │                           │                         │
│     │         │                           ▼                         │
│     │         │                    _analyze_driver() ◀── TODOS     │
│     │         │                           │      (inclui user)      │
│     │         │                           ▼                         │
│     │         │                    Retorna Recommendation[]         │
│     │         │                           │                         │
│     │         ├──▶ _execute_recommendation() ──▶ bus.push()        │
│     │         │         (só se !is_user)        │                  │
│     │         │                           ▼                         │
│     │         │                    publisher.publish(AiCommandEvent)│
│     │         │                                                                │
│     │         └──▶ _publish_suggestion_only() ──▶ publisher.publish│
│     │                   (só se is_user)        (AiSuggestionEvent) │
│     │                                                                │
│     ├──▶ a cada 10 ciclos: publisher.publish(AiMonitoringEvent)   │
│     │                                                                │
│     └──▶ stop(reason) ──▶ publisher.publish(AiStoppedEvent)       │
│                                                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Redis Pub/Sub
                              │
                              ▼ WebSocket (backend/api/main.py)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (race-parser.ts)                     │
├─────────────────────────────────────────────────────────────────────┤
│  parseLiveMessage() ──▶ LiveMessage (union com ai_* events)        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (live-race-store.ts)                    │
├─────────────────────────────────────────────────────────────────────┤
│  apply(msg) ──▶ set({ aiEngineerStatus, aiEngineerStats, ... })    │
│     │                                                                │
│     ├── ai_started ──▶ status="started", stats={...}, feed msg    │
│     ├── ai_monitoring ──▶ status="monitoring", stats={...}        │
│     ├── ai_stopped ──▶ status="stopped", stats={...}, feed msg    │
│     ├── ai_error ──▶ status="error", error="...", feed msg        │
│     ├── ai_suggestion ──▶ aiSuggestions[], feed msg               │
│     └── ai_command ──▶ aiCommands.set(), feed msg                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Components)                          │
├─────────────────────────────────────────────────────────────────────┤
│  AiPanel (2D): Mostra status badge, stats, erros, sugestões       │
│  AiEngineer (3D): Orb com cor/status, indicador topo, pulso adapt  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Comportamento do Piloto do Usuário

| Antes | Agora |
|-------|-------|
| `if (sit.is_user) return` - ignorava completamente | Analisa normalmente via `_analyze_driver()` |
| Não recebia nada | Recebe `AiSuggestionEvent` com `comando.confianca` |
| IA "sumia" para o jogador | IA aparece como "analisando" + sugestões textuais |
| Sem feedback de por que não agia | Log: `ANÁLISE do piloto do usuário: PUSH — Fechar gap...` |

---

## Intervalos Ajustados

| Parâmetro | Antes | Agora | Justificativa |
|-----------|-------|-------|---------------|
| `DECISION_INTERVAL_S` | 8.0s | 5.0s | Resposta mais rápida a mudanças |
| `MIN_COMMAND_INTERVAL_S` | 15.0s | 10.0s | Menos spam, mas mais responsivo |
| `PIT_WINDOW_START_PCT` | 25% | 20% | Janela de pit abre mais cedo |
| `PIT_WINDOW_END_PCT` | 80% | 85% | Janela de pit fecha mais tarde |
| Variação aleatória | 5% | 3% | Menos ruído, mais determinístico |

---

## Testes de Validação

### Backend (logs esperados)
```bash
# Início
=== AiEngineer INICIADO para corrida abc123 ===
  total_laps=10, user_driver_id=HAM, drivers=20, decision_interval=5.0s

# Loop
=== AiEngineer LOOP INICIADO para abc123 ===
AiEngineer abc123: ANÁLISE do piloto do usuário HAM (P3): push — Fechar gap 2.1s para P2 [media]

# Ciclo de vida no Redis pub/sub
redis-cli SUBSCRIBE "race:abc123:events"
# {"type":"ai_started","race_id":"abc123",...}
# {"type":"ai_monitoring","race_id":"abc123","status":"monitoring","stats":{...}}
# {"type":"ai_suggestion","driver_id":"HAM","aviso":"Vamos lá...","urgencia":"media",...}
# {"type":"ai_command","driver_id":"VER","command":"push","value":0,...}
# {"type":"ai_stopped","race_id":"abc123","reason":"race_ended",...}
```

### Frontend (DevTools Console)
```javascript
// Filtro: "AiPanel" OR "AiEngineer" OR "live-store" OR "race-parser"
// Deve aparecer:
[live-store] ai_started received: {raceId: "abc123", totalLaps: 10, ...}
[live-store] ai_monitoring received: {status: "monitoring", stats: {cycles: 10, ...}}
[AiPanel] suggestions: [...], commands: Map(3), engineerStatus: "monitoring"
```

### UI Visual
- **2D**: Painel topo central com badge "🟢 analisando", stats (ciclos, recomendações, executados), sugestões
- **3D**: Orb holográfico acima S/F - verde pulsante (monitoring), azul (started), vermelho (error), cinza (stopped)
- **Feed**: Mensagens "🤖 Engenheiro de IA iniciado — monitorando 20 pilotos"

---

## Próximos Passos Opcionais

1. **Persistir sugestões do usuário** no store para histórico completo
2. **Adicionar comando manual** "Pedir sugestão ao engenheiro" (botão no HUD)
3. **Tuning de thresholds** baseado em telemetria real
4. **Múltiplos engenheiros** (estratégia, pneus, combustível separados)
5. **Integração com CoachController** para aceitar comandos do usuário via IA