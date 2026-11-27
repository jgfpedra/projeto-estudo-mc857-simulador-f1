# Plano de Correção: Recuperação de Corridas (HA / Distributed Mode)

## Contexto
- Usuário implementou tela de recuperação no frontend
- Testou derrubando o container do backend e reiniciando
- A corrida fica "travada" (não avança, carros não se movem)
- Recuperação só funciona em modo distribuído (`F1_DISTRIBUTED_COMMANDS=1` ou `compose.ha.yml`)
- Tentou modo distribuído mas deu erro: **"Checkpoint só aceita controlador por regras compartilhado"**
- Aplicou correção do branch `origin/feat/reconnecting-message` (checkpoint v3 + CoachController support)
- Adicionou variáveis de ambiente no `docker-compose.yml`

## Status Atual
✅ Branch `origin/feat/reconnecting-message` aplicado + melhorias adicionais:
- `backend/engine/checkpoint.py` v3 com suporte a `CoachController`
- `backend/tests/test_checkpoint_coach.py` - testes passando
- `docker-compose.yml` com `F1_DISTRIBUTED_COMMANDS: "1"` e `F1_CHECKPOINT_SECRET`
- **Checkpoint agora é criado SEMPRE** (modo single-instance e distribuído)
- **Recovery não depende mais de env var** - funciona nos dois modos
- Código defensivo: não quebra com mocks de teste

---

## Problemas Identificados

### 1. Frontend não trata evento `race_recovered` 🔴 **CRÍTICO** ✅ **RESOLVIDO**
**Arquivo:** `frontend/src/stores/live-race-store.ts`
- Backend publica `race_recovered` após restaurar corrida
- Frontend não tinha `case "race_recovered"` no `apply()`
- **Corrigido:** Adicionado handler que seta `status: "live"`

### 2. Checkpoint só era criado em modo distribuído 🟡 **ALTO** ✅ **RESOLVIDO**
**Arquivo:** `backend/api/race_manager.py`
- Antes: checkpoint só era salvo se `F1_DISTRIBUTED_COMMANDS=1`
- **Corrigido:** Checkpoint inicial e periódico são criados/salvos em **ambos os modos**
- Modo single-instance: salva checkpoint sem lease/HA
- Modo distribuído: salva checkpoint + lease + recovery thread

### 3. Versionamento de checkpoint incompatível 🟡 **ALTO** ⚠️ **PENDENTE**
**Arquivo:** `backend/engine/checkpoint.py`
- Checkpoint version bumped para 3
- Checkpoints v2 existentes no Redis falharão com "Versão de checkpoint incompatível"
- **Ação necessária:** Limpar checkpoints v2 ou implementar migração

### 4. AI Engineer não era reiniciado e criava CommandBus separado após recovery 🟡 **MÉDIO** ✅ **RESOLVIDO**
**Arquivo:** `backend/api/race_manager.py` → `_recover_race()`
- O fluxo agora recria e inicia o `AiEngineer` depois de restaurar a engine, usando os metadados da corrida, e o registra em `_ai_engineers`.
- O engenheiro reutiliza o `CommandBus` dos `CoachController` restaurados; um novo bus só é criado como fallback para checkpoints sem coaches.
- A sequência restaurada é preservada, evitando que novos comandos reutilizem números já consumidos.
- Falha isolada na inicialização da IA é registrada sem derrubar a engine recuperada.

### 5. Variável `F1_CHECKPOINT_SECRET` precisa ser consistente 🟡 **MÉDIO**
**Arquivo:** `docker-compose.yml` + `.env`
- Secret usado para assinar checkpoints (HMAC)
- Se mudar entre restarts, checkpoints antigos falham na validação
- Default: `f1-development-checkpoint` - OK para dev, deve ser fixo em prod

### 6. Falta teste de integração end-to-end de recovery 🔵 **BAIXO**
- Testes unitários passam (`test_checkpoint_coach.py`)
- Não há teste que simule: criar corrida → checkpoint → matar processo → restaurar → continuar

---

## Plano de Ação

### Fase 1: Correções Críticas (fazer agora)

#### 1.1 ✅ **CONCLUÍDO** - Adicionar handler `race_recovered` no frontend
**Arquivos modificados:**
- `frontend/src/stores/live-race-store.ts` - adicionado case `"race_recovered"`
- `frontend/src/types/race.ts` - adicionado tipo `{ kind: "race_recovered"; simTs: number; raceId: string }` ao `LiveMessage`

```typescript
// frontend/src/stores/live-race-store.ts
case "race_recovered":
  // Corrida foi recuperada no backend (HA). O snapshot já será buscado via resync() no onOpen.
  // Apenas garantimos que o status volte para "live" para a UI sair do estado "reconnecting".
  set({ status: "live" })
  return
```

#### 1.2 ✅ **CONCLUÍDO** - Checkpoint sempre criado (independente de env var)
**Arquivos modificados:**
- `backend/api/race_manager.py` - `create_race()` e `LivePublisher.publish()`
- Checkpoint inicial criado em ambos os modos
- Checkpoint periódico salvo em ambos os modos
- Lease/HA recovery thread só no modo distribuído

#### 1.3 ⚠️ **PENDENTE** - Limpar checkpoints v2 antigos
```bash
# No Redis, remover chaves race:*:checkpoint antigas
# Ou implementar migração v2→v3 no restore() se necessário
```
- Checkpoint version foi bumped para 3
- Checkpoints v2 existentes no Redis falharão com "Versão de checkpoint incompatível"

#### 1.4 `F1_CHECKPOINT_SECRET` - já OK no compose
```yaml
# docker-compose.yml (já está)
environment:
  F1_CHECKPOINT_SECRET: ${F1_CHECKPOINT_SECRET:-f1-development-checkpoint}
```
- **Dev:** usa default `f1-development-checkpoint` (funciona, não precisa `.env`)
- **Prod:** definir via variável de ambiente do servidor / secrets manager (não commitar `.env`)
- Se secret mudar entre deploys → checkpoints antigos invalidam ("Assinatura inválida")

### Fase 2: Melhorias de Robustez

#### 2.1 ✅ **CONCLUÍDO** - Unificar CommandBus no recovery
**Arquivo:** `backend/api/race_manager.py` → `_recover_race()`
- Reutiliza o `CommandBus` dos coaches restaurados (mesmo bus, mesma seq)
- Não cria bus duplicado para AI Engineer

#### 2.2 ✅ **CONCLUÍDO** - Adicionar log/observabilidade no recovery
```python
# Em _recover_race(), logar cada passo:
logger.info('Tentando recuperar corrida %s', race_id)
logger.info('Lease adquirido para recuperar corrida %s', race_id)
logger.info('Checkpoint e metadados encontrados para %s, restaurando...', race_id)
logger.info('Corrida %s restaurada em sim_ts=%.1fs', race_id, engine.sim_ts)
logger.info('Engine thread reiniciada para corrida %s', race_id)
logger.info('AiEngineer iniciado para corrida recuperada %s (bus seq=%d)', race_id, command_bus._seq)
logger.info('Corrida %s retomada em %.1fs', race_id, engine.sim_ts)
```

#### 2.3 ✅ **CONCLUÍDO** - Checkpoint periódico defensivo
- `LivePublisher.publish()`: captura checkpoint com try/except + hasattr
- Não quebra com mocks de teste

### Fase 3: Testes e Validação

#### 3.1 ✅ **CONCLUÍDO** - Criar teste de integração de recovery
**Arquivo:** `backend/tests/test_race_recovery.py`
```python
def test_full_race_recovery_flow():
    # 1. Criar corrida real com coaches
    # 2. Avançar alguns ticks (gerar checkpoint)
    # 3. Simular crash: deletar engine, manter Redis (client.data)
    # 4. Restaurar via checkpoint.restore()
    # 5. Verificar se engine thread continua publicando ticks
    # 6. Verificar se coaches mantêm estado (seq, comando, off_track)

def test_recovery_preserves_ai_engineer_bus():
    # Verifica que o CommandBus é compartilhado entre coaches e AI Engineer
    # (não cria bus duplicado com seq=0)
```

#### 3.1.1 ✅ **CONCLUÍDO** - Cobrir o reinício no fluxo da API
**Arquivo:** `backend/tests/test_race_recovery_ai.py`
- Executa `_recover_race()` com engine restaurada e mocks de Redis/AI.
- Confirma que a thread da engine é iniciada, que o `AiEngineer` é iniciado e registrado e que recebe engine, publisher e metadados corretos.
- Confirma que o bus recebido é exatamente o dos coaches restaurados, com `_seq == 42`.

#### 3.2 Testar cenários de falha (manual)
- Recovery com viewers conectados
- Recovery sem viewers (race cancelled após grace period)
- Múltiplos backends (HA) - um cai, outro assume

---

## Checklist de Verificação Pós-Deploy

- [x] Frontend trata `race_recovered` e volta para status "live"
- [x] Checkpoint criado em ambos os modos (single-instance e distribuído)
- [x] `F1_CHECKPOINT_SECRET` OK no compose (default dev, override em prod via env var)
- [ ] Checkpoints v2 limpos ou migrados
- [x] Logs mostram recovery bem-sucedido: `Corrida X retomada em Ys`
- [ ] Engine thread publica ticks após recovery (verificar Redis `race:*:state`)
- [ ] Frontend recebe ticks e carros se movem
- [x] AI Engineer é iniciado no recovery e reutiliza o bus restaurado (teste automatizado)
- [ ] AI Engineer continua funcionando após recovery (sugestões/comandos aparecem em validação manual)

---

## Arquivos Modificados

| Arquivo | Mudança | Prioridade | Status |
|---------|---------|------------|--------|
| `frontend/src/stores/live-race-store.ts` | Adicionar case `race_recovered` | 🔴 Crítica | ✅ Feito |
| `frontend/src/types/race.ts` | Adicionar tipo `race_recovered` ao `LiveMessage` | 🔴 Crítica | ✅ Feito |
| `backend/api/race_manager.py` | Checkpoint sempre criado + código defensivo + CommandBus unificado + logs | 🟡 Alta | ✅ Feito |
| `backend/engine/checkpoint.py` | Documentar versionamento / migração v2→v3 | 🟡 Alta | Pendente |
| `docker-compose.yml` | `F1_CHECKPOINT_SECRET` com default dev | 🟡 Alta | OK (já tem default) |
| `backend/tests/test_race_recovery.py` (novo) | Teste de integração end-to-end | 🔵 Baixa | ✅ Feito |
| `backend/tests/test_race_recovery_ai.py` (novo) | Reinício da IA no fluxo da API + identidade/sequência do bus | 🔴 Alta | ✅ Feito |
| `frontend/src/services/speech-synthesis.ts` | Fix `erasableSyntaxOnly` (private → #private) | 🟢 Fix build | ✅ Feito |
| `frontend/src/components/race/ai/ai-floating-panel.tsx` | Fix imports (Volume2, VolumeX) | 🟢 Fix build | ✅ Feito |

---

## Próximos Passos Imediatos

1. **Limpar checkpoints v2** no Redis (se houver):
   ```bash
   redis-cli KEYS "race:*:checkpoint" | xargs redis-cli DEL
   ```
2. **Testar recovery manualmente** com docker-compose:
   ```bash
   docker-compose up -d
   # Criar corrida → derrubar backend → subir backend → verificar recovery
   ```

> **Nota sobre secret:** Em prod, defina `F1_CHECKPOINT_SECRET` via variável de ambiente do servidor / secrets manager (não use `.env` no repo). O default `f1-development-checkpoint` serve só para dev.