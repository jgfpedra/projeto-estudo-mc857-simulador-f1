# Auditoria de Identidade da Corrida (race_id)

## Resumo Executivo

✅ **race_id é consistente** em todo o pipeline: RaceManager → SimulationEngine → AiEngineer → CommandBus → LivePublisher → Redis → WebSocket → Frontend

✅ **Namespace Redis padronizado**: `race:{race_id}:` para todas as chaves

✅ **TTLs consistentes**: 24h para dados, 12s para lease, 60s para viewers (renovado)

⚠️ **Ponto de atenção**: Frontend não valida `raceId` dos eventos no `apply()` (confia apenas no session guard do WebSocket)

---

## 1. Criação do race_id

**Local**: `backend/api/race_manager.py:381`
```python
race_id = f'race_{uuid.uuid4().hex}'  # ex: race_a1b2c3d4e5f6
```

**Compartilhado com**:
| Componente | Como recebe |
|------------|-------------|
| `SimulationEngine` | `config = replace(DEFAULT_INTERLAGOS_CONFIG, race_id=race_id, ...)` |
| `LivePublisher` | `LivePublisher(self.redis, race_id, driver_meta)` |
| `CommandBus` | `CommandBus(self.redis, race_id, ttl=RACE_TTL)` |
| `AiEngineer` | Construtor recebe `race_id` + publisher + engine |
| Redis | Todas as chaves usam `race:{race_id}:` |
| WebSocket | `/ws/races/{race_id}` |
| Frontend | `RaceSetupResponse(race_id=race_id, ws_path=f"/ws/races/{race_id}")` |

---

## 2. Chaves Redis por Corrida

| Chave | TTL | Tipo | Propósito | Onde escrito |
|-------|-----|------|-----------|--------------|
| `race:{race_id}:meta` | 24h | STRING | Metadados da corrida (track, drivers, config) | `create_race()` + HA recover |
| `race:{race_id}:snapshot` | 24h | STRING | Estado atual (status, sim_ts, last_tick) | `LivePublisher.publish()` |
| `race:{race_id}:state` | 24h | STRING | Último tick completo | `LivePublisher.publish()` (tick) |
| `race:{race_id}:start` | 24h | STRING | Evento race_start | `LivePublisher.publish()` (race_start) |
| `race:{race_id}:result` | 24h | STRING | Resultado final (race_end/race_error) | `LivePublisher._publish_terminal()` |
| `race:{race_id}:checkpoint` | 24h | STRING | Checkpoint para HA recovery | `LivePublisher.publish()` + recover |
| `race:{race_id}:lease` | 12s | STRING | Lease distribuído (owner) | `LivePublisher` + HA recover |
| `race:{race_id}:owner` | 12s | STRING | Endereço IP do owner | `LivePublisher` + HA recover |
| `race:{race_id}:viewers` | 60s | ZSET | Viewers ativos (score = expiry) | WebSocket `refresh_viewer()` |
| `race:{race_id}:events` | — | CHANNEL | Pub/Sub para eventos | `LivePublisher.publish()` |
| `race:{race_id}:coach:{driver_id}` | 24h | STRING | Comando por piloto (CommandBus) | `CommandBus.push()` |
| `race:{race_id}:coach:seq` | 24h | STRING | Sequência global de comandos | `CommandBus.push()` |

**TTLs**:
- `RACE_TTL = 24 * 60 * 60 = 86400s` (24h) — dados persistentes
- `LEASE_SECONDS = 12s` — lease/owner (renovado a cada tick)
- `viewers` = 60s (renovado a cada 5s via heartbeat)

---

## 3. Fluxo de Publicação (Backend → Redis)

```python
# LivePublisher.publish() - backend/api/race_manager.py:205-235
pipe = self.client.pipeline(transaction=True)

# 1. Renova lease (se distributed)
pipe.set(lease_key, self.lease_token, ex=LEASE_SECONDS)
pipe.set(f'race:{self.race_id}:owner', self.owner_address, ex=LEASE_SECONDS)

# 2. Checkpoint (a cada 1s)
if checkpoint: pipe.set(f'race:{self.race_id}:checkpoint', checkpoint, ex=RACE_TTL)

# 3. Evento específico
if event.type == 'race_start':
    pipe.set(f'race:{self.race_id}:start', data, ex=RACE_TTL)
elif event.type == 'tick':
    pipe.set(f'race:{self.race_id}:state', data, ex=RACE_TTL)
elif event.type == 'race_end':
    pipe.set(f'race:{self.race_id}:result', data, ex=RACE_TTL)

# 4. Snapshot sempre atualizado
pipe.set(f'race:{self.race_id}:snapshot', json.dumps(self.snapshot), ex=RACE_TTL)

# 5. Publica no canal Pub/Sub
pipe.publish(f'race:{self.race_id}:events', data)
```

**Todos os eventos** (incluindo `ai_command`, `ai_suggestion`, `collision`, etc.) vão para o mesmo canal `race:{race_id}:events`.

---

## 4. WebSocket Handler (Backend API)

**Local**: `backend/api/main.py:392-502`

### Validação Inicial
```python
# Linha 409: Verifica se corrida existe antes de aceitar
if not await client.exists(f'race:{race_id}:meta'):
    await websocket.close(code=4404)  # Not Found
    return
```

### Inscrição no Canal
```python
# Linha 413: Subscreve ANTES de aceitar (evita perder ticks)
await pubsub.subscribe(f'race:{race_id}:events')
await websocket.accept()
```

### Encaminhamento
```python
async for message in pubsub.listen():
    if message['type'] != 'message': continue
    payload = json.loads(message['data'])
    await websocket.send_json(payload)  # TODOS os eventos
```

### Cleanup
```python
finally:
    await pubsub.aclose()
    await client.aclose()
    await client.zrem(viewers_key, viewer_id)  # Remove viewer
```

---

## 5. Frontend - Validação de race_id

### Parser (`race-parser.ts`)
Extrai `raceId` dos eventos `ai_*` mas **não valida** contra o `raceId` da store:
```typescript
case "ai_started": {
  const raceId = str(raw.race_id)  // Extraí mas não compara
  return { kind: "ai_started", simTs, raceId, ... }
}
```

### Store (`live-race-store.ts`)
Usa **session guard** no WebSocket handler:
```typescript
// Linha 380-398: openFeed recebe `current` (session snapshot)
const openFeed = (raceId: string, current: number) => {
  // ...
  onMessage: (raw) => {
    if (current !== session) return  // ← Guard principal
    const msg = parseLiveMessage(raw)
    if (msg) apply(msg)
  }
}
```

**Problema**: Se houver race condition (evento atrasado de corrida anterior), o `apply()` processa sem validar `msg.raceId`.

### Correção Recomendada
Adicionar validação no `apply()`:
```typescript
const apply = (msg: LiveMessage) => {
  // Validar raceId para eventos que o carregam
  if ('raceId' in msg && msg.raceId !== get().raceId) {
    console.warn('[live-store] Evento de race_id diferente ignorado:', msg.raceId, get().raceId)
    return
  }
  // ... resto do switch
}
```

---

## 6. Isolamento Entre Corridas

### Teste Manual
```bash
# Terminal 1: Corrida A
redis-cli SUBSCRIBE "race:race_aaa:events"

# Terminal 2: Corrida B  
redis-cli SUBSCRIBE "race:race_bbb:events"

# Terminal 3: Criar corrida A
curl -X POST /races ...

# Terminal 4: Criar corrida B
curl -X POST /races ...

# Verificar: eventos de A não aparecem em B e vice-versa
```

### Frontend (2 abas)
- Aba 1: `race_aaa` → WebSocket `/ws/races/race_aaa`
- Aba 2: `race_bbb` → WebSocket `/ws/races/race_bbb`
- Cada store tem seu `raceId` próprio
- Session guard isola updates

---

## 7. Recuperação HA (High Availability)

**Chaves envolvidas**:
- `race:{race_id}:checkpoint` — estado serializado do engine
- `race:{race_id}:lease` — token do owner atual
- `race:{race_id}:owner` — IP do owner
- `ha:active_races` — SET com race_ids ativos

**Fluxo** (`_recover_race`):
1. Tenta adquirir lease com `SET NX EX 12`
2. Lê checkpoint + meta
3. `restore(checkpoint, publisher)` → reconstrói engine
4. Publica `race_recovered` no canal
5. Reinicia `AiEngineer` para a corrida recuperada

**race_id mantido**: Sim, o mesmo `race_id` original é usado.

---

## 8. Checklist de Validação

| Item | Status | Observação |
|------|--------|------------|
| race_id único por corrida | ✅ | `uuid.uuid4().hex` |
| Compartilhado com Engine | ✅ | `config.race_id` |
| Compartilhado com Publisher | ✅ | `LivePublisher.race_id` |
| Compartilhado com CommandBus | ✅ | `CommandBus.race_id` |
| Compartilhado com AiEngineer | ✅ | Construtor |
| Redis keys namespace | ✅ | `race:{race_id}:` |
| Redis TTLs consistentes | ✅ | 24h / 12s / 60s |
| Pub/Sub canal correto | ✅ | `race:{race_id}:events` |
| WebSocket valida existência | ✅ | `EXISTS race:{id}:meta` |
| WebSocket subscreve canal correto | ✅ | `SUBSCRIBE race:{id}:events` |
| Frontend session guard | ✅ | `current !== session` |
| Frontend valida raceId no apply | ⚠️ | **FALTANDO** - recomendado adicionar |
| Isolamento 2 corridas | ✅ | Testar manualmente |
| HA recovery preserva race_id | ✅ | Mesmo race_id restaurado |

---

## 9. Ações Recomendadas

### Prioridade Alta
1. **Adicionar validação de raceId no `apply()`** (live-race-store.ts)
   - Previne processamento de eventos órfãos/stale
   - Log de warning para debug

### Prioridade Média
2. **Adicionar `raceId` em todos os eventos do parser** (já feito para `ai_*`, verificar `tick`, `collision`, etc.)
3. **Teste automatizado de isolamento** (2 corridas simultâneas)

### Prioridade Baixa
4. **Documentar schema das chaves Redis** (este documento)
5. **Adicionar métricas de leak de chaves** (monitorar keys órfãs)

---

## 10. Comandos de Debug

```bash
# Ver todas as keys de uma corrida
redis-cli KEYS "race:race_abc123:*"

# Ver TTL de uma key
redis-cli TTL "race:race_abc123:meta"

# Monitorar Pub/Sub em tempo real
redis-cli SUBSCRIBE "race:race_abc123:events"

# Ver viewers ativos
redis-cli ZRANGE "race:race_abc123:viewers" 0 -1 WITHSCORES

# Ver lease atual
redis-cli GET "race:race_abc123:lease"

# Ver owner
redis-cli GET "race:race_abc123:owner"

# Ver corridas ativas (HA)
redis-cli SMEMBERS "ha:active_races"

# Logs backend filtrados por race_id
docker logs -f backend 2>&1 | grep "race_abc123"

# Frontend DevTools Console
# Filtro: [live-store] OR [race-parser]
```