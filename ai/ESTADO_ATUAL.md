# Estado atual — engenheiro de pista ao vivo (IA)

Documento de contexto do serviço de IA em `ai/` e da integração com o simulador
e o visualizador 3D. Descreve **o que existe hoje**, não um plano.

---

## 1. Objetivo

Um engenheiro de pista de F1 fala por **texto** no HUD do visualizador e altera
o comportamento do carro acompanhado (`drv_02`) por **comandos de alto nível**,
durante uma corrida que está acontecendo **ao vivo**.

- A corrida é criada pela API (`POST /races`) e roda dentro do processo da API.
- O serviço de IA (processo separado) descobre a corrida e escuta os eventos.
- O `viz3d` apenas **consome** (`GET /races/{id}` + `WS /ws/races/{id}`), nunca
  cria a corrida.
- O `frontend/` (React antigo) continua com `USE_MOCKS = true` e não é tocado.

---

## 2. Como rodar

```bash
./tmux.sh
```

O script sobe (no tmux) Redis/Docker, API, serviço de IA, viz (Vite), monitor do
Redis, e uma janela `race` que espera a API e cria a corrida:

```bash
.venv/bin/python backend/scripts/visualization/run_live_compare.py \
  --attach --laps 3 --drivers 10 --followed-driver drv_02 \
  --random-events --no-browser
```

Portas/serviços padrão:

| serviço | endereço |
|---|---|
| API (uvicorn) | `http://127.0.0.1:8000` |
| viz3d (Vite) | `http://127.0.0.1:5173/?race=<race_id>` |
| Redis | `redis://localhost:6379/0` |
| Ollama | `http://localhost:11434` (modelo `llama3.2`) |

A corrida **não larga sozinha**: os carros ficam parados no grid até o primeiro
visualizador conectar no WebSocket (ver §7). Abra a URL impressa na janela
`race`.

---

## 3. Arquitetura

```
POST /races
   │
   ├── API/RaceManager cria meta, engine e publica "race_created" em race:control
   │
   ├── engine (thread na API)  ──ticks/eventos──►  race:<id>:events (Redis pub/sub)
   │                                                    │
   │                                                    ├── WS /ws/races/{id} ──► viz3d
   │                                                    └── listener da IA
   │
   └── IA ──POST /races/{id}/commands──► CommandBus ──► CoachController (no engine)
                                                     └── ai_command em race:<id>:events
```

### Chaves e canais no Redis

- `race:control` — canal de descoberta (`race_created`).
- `race:<id>:meta` — metadados (pista, pilotos, `num_laps`, `followed_driver_id`).
- `race:<id>:state` — último tick consolidado (usado no snapshot do WS).
- `race:<id>:result` — resultado/erro; é a fonte de verdade de "corrida encerrada".
- `race:<id>:events` — pub/sub de ticks e eventos.
- `race:<id>:suggestions` — lista (LPUSH/LTRIM 50, TTL 24 h) com as últimas
  sugestões da IA, para replay a quem conectar depois.

### Endpoints da API

- `POST /races` — cria a corrida (`laps`, `num_drivers`, `track`, `year`,
  `followed_driver_id`).
- `GET /races/{id}` — metadados (usado pelo viz para montar a pista/carros).
- `WS /ws/races/{id}` — snapshot + eventos; libera a largada ao conectar.
- `POST /races/{id}/commands` — comando de alto nível para o coach.

---

## 4. Fluxo ao vivo, passo a passo

1. `POST /races` cria meta, engine, `CommandBus` e publica `race_created` em
   `race:control`.
2. O listener da IA está em **modo control**: assina `race:control`, recebe a
   corrida e inicia um listener próprio para ela. Ao subir, também varre o Redis
   e se anexa a corridas já ativas.
3. A engine fica **parada no grid** até o WS conectar (gate de largada).
4. Ao conectar, o WS envia o snapshot (se houver), a lista de sugestões
   persistidas e libera a largada.
5. A engine publica `race_start`, `weather_changed` e um `tick` a 10 Hz em
   `race:<id>:events`.
6. O listener da IA processa os eventos, acumula gatilhos e chama o LLM.
7. A resposta vira:
   - `ai_suggestion` em `race:<id>:events` (texto + urgência + comando);
   - `POST /races/{id}/commands` (o comando entra no `CommandBus`);
   - a sugestão também é persistida em `race:<id>:suggestions`.
8. O `CoachController` aplica o comando no input base do carro no próximo tick e
   publica `ai_command` (o HUD mostra o comando ativo).
9. Ao terminar, a engine publica `race_end` e grava `race:<id>:result`; a IA
   encerra o listener daquela corrida.

---

## 5. Lógica do engenheiro (serviço de IA)

### Gatilhos

- **Evento relevante**: saída/retorno de pista, mudança de posição do
  acompanhado, pneu gasto, pit stop, clima, rádio, volta completada.
- **Periódico**: a cada `8 s` de tempo real, com jitter de `0.75×` a `1.35×`
  para o engenheiro não falar como um relógio.
- **Debounce**: no mínimo `3 s` entre duas chamadas ao LLM.
- Antes de chamar o modelo, o listener **drena a fila** já recebida e usa o
  estado mais recente (o modelo local demora dezenas de segundos).
- Antes da largada (sem `positions`) não gasta chamada; o gatilho fica vencido
  e fala no primeiro tick.
- Ignora os próprios eventos (`ai_suggestion`, `ai_command`,
  `ai_command_accepted`) para não reagir a si mesmo.

### Contexto enviado ao modelo (`live_context.py`)

Montado a cada chamada, em português:

- `Volta X de Y` e `Urgência da volta` (ver §6);
- carro acompanhado: nome, posição, combustível, composto/vida do pneu, ritmo;
- rival à frente e atrás (posição, pneu, gap em segundos);
- **leitura tática** (só quando há duelo real):
  - pneu < 35% ou combustível < 40 kg → prioriza `conserve`;
  - rival à frente a menos de `0.9 s` → sugere `overtake`/`push`;
  - rival atrás a menos de `0.9 s` → sugere `defend`;
  - sem duelo → pede para usar o rádio/eventos e não repetir comando;
- clima (tipo, temperatura de pista, aderência);
- últimos eventos (no máximo 12), incluindo:
  - `Você saiu da pista` / `Você voltou para a pista`;
  - `O rival saiu da pista` (quando for outro carro);
  - `Rádio da equipe (<estado>): <mensagem>`;
  - mudanças de posição, pneu, pit, clima, volta;
- **última mensagem do engenheiro** + comando, para o modelo variar.

### Contrato de resposta (`schemas.py`)

O modelo responde **somente JSON**:

```json
{
  "aviso": "frase curta em português, nunca null",
  "previsao": {
    "pit_stop_recomendado": true,
    "volta_estimada": 12,
    "composto_sugerido": "SOFT"
  },
  "urgencia": "baixa|media|alta",
  "comando": {
    "tipo": "push|overtake|defend|conserve|careful|neutral",
    "valor": 0,
    "motivo": "por que"
  }
}
```

- `validate_agent_output` normaliza `aviso` nulo/inválido.
- Falha/timeout do Llama → `fallback_output` (texto de indisponibilidade,
  `neutral`, `fallback: true`), sem travar a corrida.
- O listener **força o piso de urgência** mesmo que o modelo responda menos.
- Se a corrida terminar enquanto o modelo pensa, a resposta é descartada.

### Comandos de alto nível

Nunca steer/throttle crus. O `CoachController` envolve o `RuleBasedRaceController`
e aplica só um multiplicador de throttle (e um freio mínimo no `careful`):

| comando | efeito prático |
|---|---|
| `push` | throttle × 1.10 |
| `overtake` | throttle × 1.08 |
| `defend` | throttle × 0.97 |
| `conserve` | throttle × 0.90 |
| `careful` | throttle × 0.82 + freio mínimo 0.05 |
| `pace` | throttle × valor (0.5–1.15) |
| `neutral` | limpa o comando anterior (× 1.0) |

Só o carro acompanhado recebe comandos na prática (a IA só publica para ele).
O `ai_command` é publicado apenas quando o `seq` do comando muda.

### Anti-repetição

- Duplicata **exata** (mesmo comando **e** mesmo texto) é suprimida mesmo vindo
  de evento real — o comando já está aplicado no carro.
- No gatilho periódico, se só o comando **ou** só o texto repete, fica em
  silêncio.
- Evento real com comando/texto diferentes sempre fala (não engole mudança de
  plano, ex.: rádio pediu ataque e o modelo mudou para `push`).
- O prompt também recebe a última mensagem e instruções explícitas de variação.

### Persistência e replay

- Cada sugestão publicada é gravada em `race:<id>:suggestions` (até 50).
- Ao conectar, o WS envia a lista em ordem cronológica, depois do snapshot.
- O `viz3d/src/live/store.ts` deduplica por `driver_id + sim_ts + aviso`, então
  o replay + o evento ao vivo não duplicam no HUD.

---

## 6. Urgência por volta

- `LiveRaceState.total_laps` é lido de `race:<id>:meta` (`num_laps`).
- `lap_urgency_floor(lap, total_laps)`:
  - até ~50% da corrida → `baixa`;
  - de ~50% até ~85% → `media`;
  - última volta (ou ~15% finais) → `alta`;
  - sem `total_laps` → `baixa`.
- O contexto mostra `Urgência da volta: <piso> (faltam N volta(s) depois desta)`.
- O prompt exige que `urgencia` **nunca fique abaixo do piso**; em urgência
  `alta`, prefere atacar/defender a `neutral` se houver rival perto.
- O listener aplica `max_urgency(resposta, piso)` antes de publicar.

Exemplo (3 voltas): volta 1 = baixa, volta 2 = media, volta 3 = alta.

---

## 7. Largada (gate de largada)

Problema observado: o viz conectava depois do início e o usuário via a corrida
já espalhada, sem largada.

Solução implementada:

- `POST /races` cria um `threading.Event` (gate) por corrida.
- A thread da engine espera o gate antes de `engine.run()`.
- O WS chama `race_manager.signal_viewer_connected(race_id)` ao conectar.
- Se ninguém conectar, a corrida larga sozinha após
  `F1_START_GATE_TIMEOUT_S` (padrão **120 s**).
- Enquanto o gate está fechado, o carro fica parado no grid e o rádio aleatório
  (`random_events.py`) espera a chave `race:<id>:state` existir para não falar
  antes da largada.

O `run_live_compare.py --attach` imprime aviso de que a largada acontece quando
o visualizador conectar.

---

## 8. Rádio aleatório (demo/teste)

`backend/scripts/visualization/random_events.py` publica avisos de rádio em
`race:<id>:events` em intervalos aleatórios (padrão 10–22 s). **Não altera
física, classificação nem resultado.**

Estados sorteados: `ataque`, `defesa`, `economia`, `cautela`, `info`.
Mensagens curtas, mapeadas no prompt para um comando de alto nível.

Flags do `run_live_compare.py`:

```bash
--random-events
--events-seed <int>            # reproduzir uma sequência
--events-min-interval 10
--events-max-interval 22
```

Em `--attach`, o rádio roda em primeiro plano na janela `race` e para sozinho
quando a corrida termina (`race:<id>:result`).

---

## 9. Visualizador (resumo)

- Entra com `?race=<id>`; busca `GET /races/{id}` e abre o WebSocket.
- Buffer + interpolação dos ticks; timeline live.
- `AiPanel` sempre no piloto acompanhado (não no carro selecionado pelo mouse),
  mostra status, posição, volta, comando ativo e as últimas mensagens com cor de
  urgência.
- `CarPanel` mostra o comando ativo no carro.
- Sugestões deduplicadas no `store.ts`.

---

## 10. Testes

```bash
.venv/bin/python -m pytest ai/tests -q
.venv/bin/python -m pytest backend/tests/test_random_events.py \
  backend/tests/test_live_race_api.py -q
cd viz3d && npm run typecheck
```

Cobertura relevante:

- `ai/tests/test_live_context.py` — rival próximo/distante, contexto tático,
  rádio, última mensagem, urgência por volta.
- `ai/tests/test_repetition.py` — regras de silêncio/anti-repetição.
- `ai/tests/test_schemas.py` / `test_client.py` — validação e fallback.
- `backend/tests/test_random_events.py` — formato, semente, intervalos e espera
  pela largada.
- `backend/tests/test_live_race_api.py` — snapshot, roundtrip e gate de largada.

---

## 11. Limitações e observações atuais

- **Largada com muito contato**: um probe determinístico (10 carros, semente 42)
  mostra o pelotão chegando compacto na primeira frenagem (~t=19 s) e contatos
  fortes; o `drv_02` pode perder muitas posições e chegar a andar devagar por
  alguns segundos. A largada em si existe e é visível com o gate, mas o
  comportamento do pelotão ainda não está convincente.
- O modelo local (`llama3.2`) leva ~20–60 s por chamada; a primeira sugestão
  pode demorar ~1 min. O fallback evita travar, mas a cadência é limitada.
- Arquivos temporários de diagnóstico ainda na árvore de trabalho:
  - `backend/scripts/visualization/_ws_probe_tmp.py`
  - `backend/scripts/visualization/_start_probe_tmp.py`

  Devem ser removidos antes de finalizar.
- `tmux.sh` é ignorado pelo git.

---

## 12. O que precisa ser feito

<!-- Preencher à vontade. Itens sugeridos para começar: -->

- [ ] 
- [ ] 
- [ ] 
