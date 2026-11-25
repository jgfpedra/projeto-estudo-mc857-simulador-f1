#!/usr/bin/env bash
# Fluxo AO VIVO do simulador:
#   docker  -> llama (engenheiro) + redis
#   api     -> backend/api: cria a corrida, guarda ticks, serve o WebSocket
#   ai      -> ai/app/redis_listener.py: descobre corridas em race:control,
#              gera o texto e manda comandos de alto nível para o carro seguido
#   viz     -> viz3d: entre em http://localhost:5173/?race=<race_id>
#   race    -> espera a API e cria uma corrida de 10 pilotos automaticamente
#
# Rode de dentro de uma sessão tmux, ou crie uma antes:
#   tmux new-session -s f1 -c "$PWD"
#   ./tmux.sh
ROOT="$(pwd)"

# 1. Infra: modelo local (Ollama) e Redis.
tmux new-window -n docker -c "$ROOT"
tmux send-keys -t docker 'docker compose up llama redis' C-m

# 2. API: é quem cria a corrida e publica os eventos no Redis/WebSocket.
tmux new-window -n api -c "$ROOT"
tmux send-keys -t api '.venv/bin/python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000' C-m

# 3. Serviço de IA: modo control (sem argumentos). Ele abre um listener por
#    corrida anunciada em race:control e só age no followed_driver_id.
tmux new-window -n ai -c "$ROOT"
tmux send-keys -t ai 'cd ai/app && PYTHONPATH=. ../../.venv/bin/python -u redis_listener.py' C-m

# 4. Visualizador: modo live via ?race=<id>. Não cria corrida.
tmux new-window -n viz -c "$ROOT/viz3d"
tmux send-keys -t viz 'npm run dev -- --host 127.0.0.1 --port 5173' C-m

# 5. Monitor do canal de controle: mostra cada corrida que nasce.
tmux new-window -n redis-mon -c "$ROOT"
tmux send-keys -t redis-mon 'docker compose exec redis redis-cli SUBSCRIBE race:control' C-m

# 6. Criação de uma corrida pelo script que já existe. `--attach` usa a
#    API/viz das janelas acima (não sobe outra stack) e imprime a URL do viz3d.
#    10 pilotos porque todos largam juntos do começo da corrida. O comando só
#    dispara quando a API responde, e a pausa extra deixa a IA assinar
#    race:control antes do anúncio da corrida. `--random-events` publica avisos
#    de rádio aleatórios (demo) para a IA não repetir sempre o mesmo comando.
tmux new-window -n race -c "$ROOT"
tmux send-keys -t race 'while ! curl -sf http://127.0.0.1:8000/docs >/dev/null; do sleep 1; done; sleep 3; .venv/bin/python backend/scripts/visualization/run_live_compare.py --attach --laps 3 --drivers 10 --followed-driver drv_02 --random-events --no-browser' C-m

# 7. Janelas de trabalho.
tmux new-window -n code -c "$ROOT"
tmux send-keys -t code 'nvim' C-m

tmux new-window -n git -c "$ROOT"
tmux send-keys -t git 'git status' C-m

# Garante uma sessão para o agente, sem duplicar.
tmux has-session -t opencode 2>/dev/null || {
  tmux new-session -d -s opencode -n opencode -c "$ROOT"
  tmux send-keys -t opencode:opencode 'opencode' C-m
}
