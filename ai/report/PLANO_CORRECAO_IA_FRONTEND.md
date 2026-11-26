# Plano de Correção Completo: IA no Frontend (2D/3D) + Auditoria de Corrida

## Resumo do Problema
O engenheiro de IA (AiEngineer) não está aparecendo em uma caixa separada no frontend (nem no 2D, nem no 3D) quando uma corrida é iniciada. O usuário também suspeita que o Redis pode não estar associando corretamente a corrida.

---

## Arquitetura do Fluxo de Dados da IA

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Backend        │     │  Redis Pub/Sub   │     │  Backend API    │     │  Frontend       │
│  AiEngineer     │────▶│  race:{id}:events│────▶│  WebSocket      │────▶│  race-parser    │
│  (thread)       │     │                  │     │  (main.py)      │     │  + live-store   │
└─────────────────┘     └──────────────────┘     └─────────────────┘     └──────────────────┘
                                                                                   │
                                                                                   ▼
                                                                        ┌──────────────────┐
                                                                        │  AiPanel (2D)    │
                                                                        │  AiEngineer (3D) │
                                                                        └──────────────────┘
```

---

## 1. AUDITORIA E IDENTIDADE DA CORRIDA (race_id)

### 1.1 Fluxo Completo de Inicialização
- [ ] Analisar o fluxo completo de inicialização de uma corrida (POST `/races` → `RaceManager.create_race()` → `SimulationEngine` → `AiEngineer` → Redis → WebSocket → Frontend)
- [ ] Identificar onde o `race_id` é criado no `RaceManager` (linha ~420: `race_id = f'race_{uuid.uuid4().hex}'`)
- [ ] Verificar se o mesmo `race_id` é compartilhado entre todos os componentes:
  - [ ] `RaceManager` (dicionários `_threads`, `_engines`, `_ai_engineers`, `_viewers`)
  - [ ] `SimulationEngine` (config.race_id)
  - [ ] `AiEngineer` (construtor + events)
  - [ ] `CommandBus` (prefixo Redis `race:{race_id}:commands`)
  - [ ] `LivePublisher` (race_id + chaves Redis)
  - [ ] Redis (todas as chaves `race:{race_id}:*`)
  - [ ] WebSocket (`/ws/races/{race_id}`)
  - [ ] Frontend Zustand Store (`raceId`, `race.raceId`)

### 1.2 Verificar Componentes Criando/Sobrescrevendo IDs
- [ ] Buscar por `uuid.uuid4()`, `uuid.uuid1()`, `random` em arquivos de corrida
- [ ] Verificar se `race_manager.create_race()` é chamado apenas uma vez por corrida
- [ ] Verificar se recuperação HA (`_recover_race`) reusa o mesmo `race_id`

### 1.3 Auditoria de Chaves Redis
| Chave | TTL | Propósito | Componente |
|-------|-----|-----------|------------|
| `race:{race_id}:meta` | 24h | Metadados da corrida | RaceManager |
| `race:{race_id}:snapshot` | 24h | Estado atual (status, sim_ts, last_tick) | LivePublisher |
| `race:{race_id}:state` | 24h | Último tick completo | LivePublisher |
| `race:{race_id}:start` | 24h | Evento race_start | LivePublisher |
| `race:{race_id}:result` | 24h | Resultado final | LivePublisher |
| `race:{race_id}:checkpoint` | 24h | Checkpoint para HA | LivePublisher |
| `race:{race_id}:lease` | 12s | Lease distribuído | LivePublisher |
| `race:{race_id}:owner` | 12s | Endereço do owner | LivePublisher |
| `race:{race_id}:viewers` | 60s | Viewers ativos (ZSET) | WebSocket |
| `race:{race_id}:events` | — | Canal Pub/Sub | LivePublisher + WebSocket |
| `race:{race_id}:commands` | 24h | CommandBus (hash) | CommandBus |

- [ ] Verificar se **todas** as chaves usam o namespace `race:{race_id}:`
- [ ] Verificar se não há chaves órfãs (sem race_id válido)
- [ ] Verificar TTL consistente (24h para dados, 12s para lease)

### 1.4 Canais Redis Pub/Sub
- [ ] Verificar se `LivePublisher` publica em `race:{race_id}:events`
- [ ] Verificar se WebSocket subscreve **exclusivamente** `race:{race_id}:events`
- [ ] Verificar se não há vazamento entre canais de corridas diferentes

### 1.5 WebSocket - Inscrição e Validação
- [ ] Verificar `race_websocket()` em `backend/api/main.py`:
  - [ ] `await pubsub.subscribe(f'race:{race_id}:events')`
  - [ ] `await pubsub.unsubscribe()` no finally
  - [ ] Validação de `race_id` no handshake (`client.exists(f'race:{race_id}:meta')`)

### 1.6 Frontend - Validação de race_id nos Eventos
- [ ] Em `race-parser.ts`: validar se `race_id` do evento bate com `raceId` da store
- [ ] Em `live-race-store.ts` (`apply()`): rejeitar eventos de `race_id` diferente
- [ ] Implementar `session` guard (já existe via closure `current`)

### 1.7 Testes de Isolamento
- [ ] Criar 2 corridas simultâneas (race_A, race_B)
- [ ] Verificar logs: eventos de race_A não aparecem em race_B
- [ ] Verificar Redis: chaves separadas
- [ ] Verificar Frontend: abrir 2 abas, cada uma vê só sua corrida
- [ ] Encerrar race_A → race_B continua funcionando

---

## 2. CORREÇÕES JÁ IMPLEMENTADAS NO AI ENGINEER (Backend)

> **Status**: ✅ CONCLUÍDO - Ver `RESUMO_CORRECOES_IA.md`

### 2.1 Separação Análise vs Execução
- `_analyze_driver()` → retorna `Recommendation` (para TODOS, inclusive user)
- `_execute_recommendation()` → `bus.push()` (só bots)
- `_publish_suggestion_only()` → `AiSuggestionEvent` (só user)

### 2.2 Eventos de Ciclo de Vida
| Evento | Tipo | Publicado Em | Payload Principal |
|--------|------|--------------|-------------------|
| `ai_started` | AiStartedEvent | `start()` | race_id, total_laps, user_driver_id, num_drivers, decision_interval_s |
| `ai_monitoring` | AiMonitoringEvent | Loop (10 ciclos) | race_id, status, sim_ts, stats |
| `ai_stopped` | AiStoppedEvent | `stop(reason)` | race_id, reason, stats |
| `ai_error` | AiErrorEvent | `except` no loop | race_id, error, error_type, cycle, driver_id |

### 2.3 Parâmetros Ajustados
- `DECISION_INTERVAL_S`: 8.0 → **5.0s** (tempo simulado)
- `MIN_COMMAND_INTERVAL_S`: 15.0 → **10.0s** (tempo real)
- `PIT_WINDOW_START_PCT`: 25% → **20%**
- `PIT_WINDOW_END_PCT`: 80% → **85%**
- Variação aleatória: 5% → **3%**

### 2.4 Pilot do Usuário
- Analisado normalmente (logs: `ANÁLISE do piloto do usuário`)
- Recebe sugestões textuais com `confianca`
- IA **não** assume controle (não executa `bus.push`)

---

## 3. CRIAÇÃO DO PAINEL FLUTUANTE INDEPENDENTE (2D/3D)

### 3.1 Auditoria do Componente Atual
- [ ] `AiPanel` (`frontend/src/components/race/ai/ai-panel.tsx`)
  - Props: `suggestions`, `commands`, `followedDriverId`
  - **Novas props adicionadas**: `engineerStatus`, `engineerStats`, `engineerError`
  - Posicionamento: `absolute top-4 left-1/2 -translate-x-1/2 z-30`
  - Mostra "aguardando primeira sugestão…" quando vazio

- [ ] Uso em `race-simulation.tsx` (linha ~174):
  - Renderizado **fora** do Canvas/WebGL ✅
  - Mesmo componente para 2D e 3D ✅
  - Recebe estado do Zustand ✅

### 3.2 Problemas Identificados
- [ ] **Z-index**: `z-30` pode ser coberto por header (`z-40`?) ou modais
- [ ] **pointer-events-none**: impede interação (botões, scroll)
- [ ] **Posição fixa topo central**: pode conflitar com `RaceBanner`
- [ ] **Troca 2D↔3D**: componente **não desmonta** (mesmo local no JSX) ✅

### 3.3 Novo Componente: `AiFloatingPanel`
**Local**: `frontend/src/components/race/ai/ai-floating-panel.tsx`

```tsx
interface AiFloatingPanelProps {
  // Estado da IA
  engineerStatus: "idle" | "started" | "monitoring" | "stopped" | "error";
  engineerStats?: Record<string, unknown> | null;
  engineerError?: string | null;
  
  // Dados da corrida
  raceId: string;
  raceName: string;
  
  // Piloto acompanhado
  followedDriverId: string | null;
  followedDriverName: string;
  
  // Dados de recomendação
  suggestions: AiSuggestion[];
  commands: Map<string, AiCommand>;
  
  // Config
  position?: "top-center" | "top-right" | "bottom-right";
  onClose?: () => void;
  onFollowDriver?: (driverId: string) => void;
}
```

### 3.4 Requisitos do Painel

#### 3.4.1 Renderização
- [ ] Fora do Canvas/WebGL (HTML overlay)
- [ ] Independente da cena 3D (não usa R3F)
- [ ] Mesmo componente para 2D e 3D
- [ ] Não desmonta na troca 2D↔3D

#### 3.4.2 Posicionamento
- [ ] Área fixa da interface (ex: `top-right` com `right-4 top-4`)
- [ ] `z-index: 50` (acima de header, banner, canvas)
- [ ] `pointer-events-auto` (interativo)
- [ ] Responsivo (mobile: bottom sheet)

#### 3.4.3 Indicador Visual de Status
| Status | Badge | Cor | Animação |
|--------|-------|-----|----------|
| `idle` | PARADO | cinza | — |
| `started` | INICIANDO | azul | pulse |
| `monitoring` | MONITORANDO | verde | pulse |
| `analyzing` | ANALISANDO | âmbar | spin |
| `error` | ERRO | vermelho | pulse |
| `disconnected` | DESCONECTADO | laranja | blink |
| `stopped` | ENCERRADO | cinza | — |

#### 3.4.4 Conteúdo Obrigatório
- [ ] **Identificação da corrida**: `raceId` (curto) + `raceName`
- [ ] **Piloto acompanhado**: Nome + sigla + badge "🎯 ENGENHEIRO"
- [ ] **Última análise**: Timestamp + driver + resumo
- [ ] **Recomendações recentes**: Lista (últimas 5) com prioridade
- [ ] **Nível de prioridade**: 🔴 ALTA / 🟡 MÉDIA / 🟢 BAIXA
- [ ] **Comandos ativos**: Por driver (badge no timing panel)
- [ ] **Mensagens de erro/reconexão**: Toast inline
- [ ] **Botão "Seguir piloto"**: Altera `followedDriverId`

#### 3.4.5 Atualização Automática
- [ ] Reactivo ao Zustand (já funciona via selectors)
- [ ] WebSocket → Parser → Store → Re-render
- [ ] Debounce de render (máx 10fps para suggestions)

#### 3.4.6 Aparecimento Imediato
- [ ] Mostra estado `started`/`monitoring` **assim que corrida inicia**
- [ ] Não espera primeira recomendação
- [ ] Badge "MONITORANDO" visível em <1s após `race_start`

---

## 4. INTEGRAÇÃO REDIS → WEBSOCKET → FRONTEND

### 4.1 Publicação de Eventos (Backend)
- [ ] `AiEngineer` → `publisher.publish(AiStartedEvent|AiSuggestionEvent|...)`
- [ ] `LivePublisher.publish()` → serializa `event.to_dict()` → JSON
- [ ] Pipeline Redis:
  - `SET race:{race_id}:state` (tick)
  - `PUBLISH race:{race_id}:events` (todos eventos)
- [ ] Verificar se `schema_version` incluído

### 4.2 WebSocket Handler (`backend/api/main.py`)
- [ ] `race_websocket()`:
  - [ ] `await pubsub.subscribe(f'race:{race_id}:events')`
  - [ ] `async for message in pubsub.listen()`
  - [ ] `websocket.send_json(payload)` para **todos** tipos
  - [ ] Heartbeat viewer (distribuído): `ZADD race:{race_id}:viewers`
  - [ ] Cleanup no `finally`: unsubscribe, ZREM viewer

### 4.3 Parser Frontend (`race-parser.ts`)
- [ ] `parseLiveMessage()` reconhece:
  - [ ] `ai_started` → `LiveMessage.kind = "ai_started"`
  - [ ] `ai_monitoring` → `LiveMessage.kind = "ai_monitoring"`
  - [ ] `ai_stopped` → `LiveMessage.kind = "ai_stopped"`
  - [ ] `ai_error` → `LiveMessage.kind = "ai_error"`
  - [ ] `ai_suggestion` → `LiveMessage.kind = "ai_suggestion"`
  - [ ] `ai_command` → `LiveMessage.kind = "ai_command"`
- [ ] Validação de campos obrigatórios
- [ ] Tratamento de eventos desconhecidos → `console.warn` + retorna `null`

### 4.4 Zustand Store (`live-race-store.ts`)
- [ ] Estado expandido:
  ```typescript
  aiEngineerStatus: "idle" | "started" | "monitoring" | "stopped" | "error"
  aiEngineerStats: Record<string, unknown> | null
  aiEngineerError: string | null
  ```
- [ ] `apply()` handlers para todos os 4 novos eventos
- [ ] Feed messages para `ai_started`/`ai_stopped`/`ai_error`
- [ ] `ai_monitoring` **não** vai para feed (apenas estado)

### 4.5 Reconexão e Recuperação
- [ ] WebSocket reconexão automática (já existe: `reconnectTimer`, `MAX_RECONNECTS=5`)
- [ ] Após reconexão: `resync()` busca snapshot + `last_tick`
- [ ] **Recuperar estado da IA**:
  - [ ] `aiEngineerStatus` → "monitoring" (se race running)
  - [ ] `aiEngineerStats` → do snapshot ou zerado
  - [ ] `aiSuggestions` / `aiCommands` → do snapshot `last_tick` se houver
- [ ] Persistência de histórico: `MAX_AI_SUGGESTIONS = 50` (já configurado)

### 4.6 Logs Estruturados (Rastreabilidade)
```json
// Backend (logger)
{
  "race_id": "race_abc123",
  "driver_id": "HAM",
  "event_type": "ai_suggestion",
  "sim_ts": 45.2,
  "timestamp": "2026-11-26T18:30:00.123Z",
  "command": "push",
  "urgency": "media"
}

// Frontend (console)
[race-parser] Parsed: { kind: "ai_suggestion", raceId: "race_abc123", ... }
[live-store] ai_suggestion received: { driverId: "HAM", ... }
[AiFloatingPanel] render: { suggestions: 3, status: "monitoring" }
```

- [ ] Adicionar `race_id`, `driver_id`, `event_type`, `sim_ts`, `timestamp` em todos os logs
- [ ] Frontend: prefixar logs com `[race-parser]`, `[live-store]`, `[AiFloatingPanel]`

---

## 5. ASSOCIAÇÃO ENTRE IA E PILOTO ACOMPANHADO

### 5.1 Propriedades Atuais
| Propriedade | Origem | Uso |
|-------------|--------|-----|
| `user_driver_id` | Backend (RaceManager meta) | Piloto controlado pelo jogador |
| `followedDriverId` | Frontend (Zustand) | Piloto que o engenheiro "fala" no HUD |
| `selectedDriverId` | Frontend (Zustand) | Piloto selecionado visualmente (câmera 3D, card) |

### 5.2 Problema: Conflito entre followed vs selected
- [ ] Atualmente: `followedDriverId === selectedDriverId` (mesmo valor)
- [ ] **Separar**: engenheiro acompanha **sempre** o `user_driver_id` (backend)
- [ ] Visual: usuário pode selecionar outro carro (`selectedDriverId`) sem mudar alvo da IA

### 5.3 Estado Independente no Frontend
```typescript
// Zustand - NOVOS CAMPOS
followedDriverId: string | null;      // Alvo do engenheiro (fixo = user_driver_id)
selectedDriverId: string | null;      // Seleção visual do usuário
aiSuggestions: AiSuggestion[];        // Todas (indexadas por driver_id)
aiCommands: Map<string, AiCommand>;   // Por driver_id
```

### 5.4 Associação Backend → Frontend
- [ ] Backend: `race.meta.user_driver_id` → `followedDriverId` inicial
- [ ] Backend: Cada `AiSuggestionEvent`/`AiCommandEvent` tem `driver_id`
- [ ] Frontend: `aiSuggestions` array + `aiCommands` Map (key = driver_id)
- [ ] Painel: Mostra badge "🎯 ACOMPANHADO" no piloto do `followedDriverId`

### 5.5 Validação de Consistência
- [ ] `followedDriverId` === `race.userDriverId` (sempre)
- [ ] `selectedDriverId` pode ser diferente (navegação visual)
- [ ] Recomendações no painel: filtro por `followedDriverId` (destaque) + outras (colapsadas)
- [ ] Testar: clicar em outro carro no timing panel → `selectedDriverId` muda, `followedDriverId` não

---

## 6. TESTES DE INTEGRAÇÃO E VALIDAÇÃO FINAL

### 6.1 Testes Unitários (Backend)
- [ ] `AiEngineer._analyze_driver()` - cenários: pit window, defesa, ataque, liderança, últimas voltas
- [ ] `AiEngineer._build_situations()` - gaps, pneus, combustível
- [ ] `AiEngineer._execute_recommendation()` - bus.push chamado
- [ ] `AiEngineer._publish_suggestion_only()` - publisher.publish chamado
- [ ] Eventos: `to_dict()` serializa todos campos

### 6.2 Testes de Isolamento
- [ ] 2 corridas simultâneas → Redis keys separadas
- [ ] 2 WebSockets → cada um recebe só seus eventos
- [ ] Encerrar corrida A → corrida B continua
- [ ] Recuperação HA: corrida A recupera, corrida B não afetada

### 6.3 Testes Redis Pub/Sub
- [ ] Publicar evento → receber no subscriber
- [ ] Evento com `race_id` errado → não entregue
- [ ] Canal `race:{id}:events` isolado por corrida

### 6.4 Testes WebSocket
- [ ] Conectar → receber `race_start` + `state`
- [ ] Receber ticks contínuos
- [ ] Desconectar/reconectar → `resync` funciona
- [ ] Código 4404 (not found) / 4410 (cancelled) tratados

### 6.5 Testes Parser
- [ ] Todos os 16+ tipos de `LiveMessage` parseados
- [ ] Eventos malformados → `null` + warning
- [ ] Novos eventos `ai_*` → tipos corretos

### 6.6 Testes Zustand Store
- [ ] `apply()` atualiza estado imutavelmente
- [ ] `aiEngineerStatus` transições corretas
- [ ] `aiSuggestions` limitado a 50
- [ ] `aiCommands` Map por driver_id

### 6.7 Testes Renderização AiFloatingPanel
- [ ] Monta sem erros
- [ ] Props reativas (status, stats, suggestions)
- [ ] Status badges corretos
- [ ] Lista de sugestões renderiza
- [ ] Botão "Seguir" funciona

### 6.8 Testes E2E (Cenários Reais)
| Cenário | Critério de Sucesso |
|---------|---------------------|
| Iniciar corrida do zero | Painel aparece em <1s com "MONITORANDO" |
| Primeira recomendação | Chega ao painel em <5s sim_ts |
| Comando real (bot) | Badge "COMANDO ATIVO" no timing panel |
| Alternar 2D ↔ 3D | Painel permanece, não pisca |
| Refresh navegador (F5) | Reconecta, recupera estado IA |
| Desconexão WS (rede) | Reconecta auto, painel mostra "RECONECTANDO" |
| 2 corridas simultâneas | Isolamento total (logs, Redis, UI) |
| Encerrar corrida | `ai_stopped` → painel "ENCERRADO" + stats finais |
| Redis indisponível | Erro visível, não mostra "ONLINE" falso |

---

## 7. RESTRIÇÕES TÉCNICAS OBRIGATÓRIAS

> A IA de desenvolvimento deve respeitar durante toda a implementação:

- [ ] **Não reconstruir** a arquitetura do Redis
- [ ] **Não criar** um segundo AI Engineer
- [ ] **Não duplicar** painéis para 2D e 3D (um só: `AiFloatingPanel`)
- [ ] **Não modificar** desnecessariamente o motor de física PyBullet
- [ ] **Não alterar** parâmetros de treinamento dos pilotos neurais
- [ ] **Não modificar** a dinâmica de corrida para resolver problemas de interface
- [ ] **Não remover** funcionalidades existentes
- [ ] **Não substituir** componentes funcionais sem justificativa técnica
- [ ] **Não implementar** soluções temporárias que simulem eventos reais da IA
- [ ] **Não apresentar** status ONLINE sem confirmação da inicialização efetiva
- [ ] **Não considerar** uma publicação Redis como prova de entrega ao frontend
- [ ] **Preservar** compatibilidade com a arquitetura atual
- [ ] **Documentar** todos os arquivos modificados
- [ ] **Executar testes** após cada etapa
- [ ] **Não avançar** para a próxima etapa enquanto houver falhas bloqueadoras na anterior

---

## 8. ENTREGA OBRIGATÓRIA

Ao concluir, apresentar:

### 8.1 Documentação
- [ ] **Diagnóstico dos problemas encontrados** (root cause analysis)
- [ ] **Lista de arquivos modificados** (backend + frontend)
- [ ] **Descrição das correções realizadas** (por componente)
- [ ] **Novos componentes criados** (`AiFloatingPanel`, eventos)
- [ ] **Novos eventos implementados** (`ai_started`, `ai_monitoring`, `ai_stopped`, `ai_error`)

### 8.2 Evidências Técnicas
- [ ] **Associação correta race_id ↔ Redis** (logs + `redis-cli KEYS`)
- [ ] **Entrega eventos WebSocket** (Network tab + `wscat` dump)
- [ ] **Renderização recomendações frontend** (DevTools React + Console)
- [ ] **Isolamento entre corridas** (2 abas + 2 race_ids)

### 8.3 Resultados de Testes
- [ ] **Testes automatizados** (unit + integration) - relatório
- [ ] **Corrida completa 2D** - vídeo/logs + screenshots painel
- [ ] **Corrida completa 3D** - vídeo/logs + screenshots painel + orb

### 8.4 Pendências
- [ ] **Problemas ainda pendentes**, caso existam (com mitigação)

---

## CRONOGRAMA SUGERIDO

| Fase | Atividades | Estimativa |
|------|------------|------------|
| **1. Auditoria race_id** | Verificar fluxo, chaves Redis, WebSocket, isolamento | 2h |
| **2. AiFloatingPanel** | Criar componente, integrar 2D/3D, status badges | 3h |
| **3. Integração Redis→WS→FE** | Parser, Store, reconexão, logs estruturados | 2h |
| **4. Associação IA↔Piloto** | Separar followed/selected, validar consistência | 1h |
| **5. Testes E2E** | Cenários da tabela 6.8, 2 corridas simultâneas | 3h |
| **6. Documentação** | Entregáveis 8.1-8.4 | 1h |
| **TOTAL** | | **~12h** |

---

## COMANDOS DE VALIDAÇÃO RÁPIDA

```bash
# 1. Verificar chaves Redis de uma corrida
redis-cli KEYS "race:race_abc123:*"

# 2. Monitorar eventos em tempo real
redis-cli SUBSCRIBE "race:race_abc123:events"

# 3. Testar WebSocket manual
wscat -c ws://localhost:8000/ws/races/race_abc123

# 4. Logs backend filtrados
docker logs -f backend 2>&1 | grep -E "race_abc123|ai_|AiEngineer"

# 5. Frontend DevTools Console - filtros
# [race-parser] OR [live-store] OR [AiFloatingPanel] OR [AiEngineer3D]

# 6. Verificar isolamento (2 terminais)
redis-cli SUBSCRIBE "race:race_A:events"
redis-cli SUBSCRIBE "race:race_B:events"
# Criar 2 corridas → eventos não vazam
```

---

## CHECKLIST FINAL DE CONCLUSÃO

- [ ] race_id único e consistente em todo pipeline
- [ ] AiFloatingPanel visível e funcional em 2D e 3D
- [ ] Status badges: ONLINE → MONITORANDO → ANALISANDO → ENCERRADO/ERRO
- [ ] Eventos `ai_*` parseados e no Zustand
- [ ] Reconexão recupera estado da IA
- [ ] followedDriverId (engenheiro) ≠ selectedDriverId (visual)
- [ ] 2 corridas isoladas (Redis, WS, Frontend)
- [ ] Logs estruturados com race_id em todas as camadas
- [ ] Documentação completa entregue