# Mock do backend da corrida

Servidor que implementa o contrato da corrida (REST + WebSocket) sem o motor de simulação.
Serve para testar a tela `/race-simulation/:raceId` do frontend.

## Subir o mock

```bash
cd mock-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn mock_server:app --port 8000
```

Variáveis úteis (opcionais):

| Variável | Padrão | Efeito |
|---|---|---|
| `MOCK_SPEED` | `2` | segundos de simulação por segundo real. `1` = tempo real |
| `MOCK_LAPS` | `3` | voltas da corrida demo e das corridas criadas por `POST /races` |
| `MOCK_RED_FLAG` | `0` | `1` inclui uma bandeira vermelha no meio da corrida |
| `MOCK_SEED` | `2025` | mesma semente, mesma corrida |
| `MOCK_DEMO` | `1` | cria ao subir a corrida `demo` |

Exemplo para uma corrida curta, com bandeira vermelha:

```bash
MOCK_LAPS=2 MOCK_SPEED=4 MOCK_RED_FLAG=1 uvicorn mock_server:app --port 8000
```

## Ver a tela

Com o frontend rodando (`npm run dev`, porta 5173) e `.env.development` apontando para `http://localhost:8000` e `ws://localhost:8000`:

- Direto na corrida demo: <http://localhost:5173/race-simulation/demo>
- Fluxo completo: menu → circuito → pilotos → clima/pneus → Iniciar. O POST cria uma corrida nova e a tela abre em `/race-simulation/<id>`.

A corrida demo começa ao subir o servidor. Se você abrir a página depois que ela terminar, a tela mostra o resultado final pelo snapshot. Para assistir desde a largada, reinicie o servidor.

## O que o mock simula

- 20 pilotos com cores de equipe e siglas. Grid de 8 m entre carros, tempos de volta diferentes, então há ultrapassagens de verdade.
- Pit stop de 20 s por carro, com troca de composto e desgaste de pneu (gera `tyre_worn`).
- Safety car no início da corrida (40 s), com ticks mais lentos e gaps mantidos.
- Troca de clima no meio da corrida (`weather_changed`).
- Gap calculado pelo tempo em que o líder passou pelo mesmo ponto do carro, e `laps_behind` quando há volta de diferença.
- `race_end` com classificação e fechamento do WebSocket com código 1000.
- Corrida inexistente: WebSocket fecha com código 4404 e REST responde 404.

## O que o mock não faz

- Carros não colidem, não há penalidades, e a estratégia do `POST` (`stints`) é só aceita e avisada em `warnings`.
- `race_start` não é enviado, porque a tela não depende dele.
- Circuito e temporada: um circuito (Interlagos) e a temporada 2025.

## Verificar o contrato

Com o servidor rodando, `python smoke_test.py` cria uma corrida, lê o WebSocket até o `race_end` e imprime a contagem de mensagens.

## Observação sobre o contrato

`POST /races` devolve `grid` como lista de objetos (`position`, `driver_id`, `name`), como o backend real. O tipo `ApiRaceResponse` em `src/types/api.ts` ainda declara `grid: string[]`. O frontend não usa o campo, mas o tipo está errado e deve ser ajustado para `{ position: number; driver_id: string; name: string }[]`.
