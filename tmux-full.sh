#!/usr/bin/env bash
# f1-all.sh — Llama + Redis (docker), API, IA, viz3d, frontend e a corrida.
# Uso: export F1_PY=/caminho/do/venv/bin/python ; ./f1-all.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SESSION="f1-all"
LAPS="${F1_LAPS:-3}"
DRIVERS="${F1_DRIVERS:-10}"
FOLLOWED="${F1_FOLLOWED:-drv_02}"
PY="${F1_PY:-}"

if [ -z "$PY" ] || [ ! -x "$PY" ]; then
  echo "ERRO: defina F1_PY (ex.: export F1_PY=\$HOME/venvs/f1/bin/python)"; exit 1
fi
cd "$ROOT"

# --- checagens de Docker (kernel desatualizado derruba o Docker no Arch)
if [ ! -d "/lib/modules/$(uname -r)" ]; then
  echo "ERRO: sem módulos para o kernel em uso ($(uname -r)). Reinicie o PC."; exit 1
fi
docker info >/dev/null 2>&1 || { echo "ERRO: Docker não responde (sudo systemctl start docker)"; exit 1; }

free_port() {
  local port="$1" pids
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
  elif command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti "tcp:${port}" || true)"
    [ -n "$pids" ] && kill $pids 2>/dev/null || true
  fi
}

echo "== Limpando sessão e portas antigas =="
tmux kill-session -t "$SESSION" 2>/dev/null || true
for p in 8000 5173 5174 3001; do free_port "$p"; done
sleep 1

echo "== Docker: llama + redis =="
docker compose up -d llama redis
for _ in $(seq 1 30); do
  docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && break
  sleep 1
done
docker compose exec -T redis redis-cli ping | grep -q PONG || { echo "ERRO: Redis não respondeu"; exit 1; }
# Redis só de desenvolvimento: limpa corridas antigas (F1_KEEP_REDIS=1 para manter)
[ "${F1_KEEP_REDIS:-0}" = "1" ] || docker compose exec -T redis redis-cli FLUSHDB >/dev/null

echo "== Subindo sessão tmux: $SESSION =="

# 1) API
tmux new-session -d -s "$SESSION" -n api -c "$ROOT" \
  "\"$PY\" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000; exec bash"

# 2) IA (espera o Ollama ter o llama3.2; na 1a vez baixa ~2GB)
tmux new-window -t "$SESSION:" -n ai -c "$ROOT/ai/app" \
  "until curl -sf http://127.0.0.1:11434/api/tags | grep -q llama3.2; do echo 'aguardando Ollama + llama3.2...'; sleep 3; done; PYTHONPATH=. \"$PY\" -u redis_listener.py; exec bash"

# 3) Visualizador 3D (porta fixa: se estiver ocupada, falha em vez de trocar)
tmux new-window -t "$SESSION:" -n viz -c "$ROOT/viz3d" \
  "[ -d node_modules ] || npm install; npm run dev -- --host 127.0.0.1 --port 3001 --strictPort; exec bash"

# 4) Frontend
tmux new-window -t "$SESSION:" -n frontend -c "$ROOT/frontend" \
  "[ -d node_modules ] || npm install; BROWSER=none npm run dev; exec bash"

# 5) Corrida: espera API e viz, depois anuncia a corrida e imprime a URL
tmux new-window -t "$SESSION:" -n race -c "$ROOT" \
  "until curl -sf http://127.0.0.1:8000/docs >/dev/null && curl -sf http://127.0.0.1:3001/ >/dev/null; do sleep 1; done; sleep 3; F1_VIZ_PORT=3001 \"$PY\" backend/scripts/visualization/run_live_compare.py --attach --laps $LAPS --drivers $DRIVERS --track interlagos --followed-driver $FOLLOWED --random-events --no-browser; exec bash"

# 6) Só as sugestões da IA publicadas no Redis
tmux new-window -t "$SESSION:" -n suggestions -c "$ROOT" \
  "docker compose exec -T redis redis-cli PSUBSCRIBE 'race:*:events' | grep --line-buffered ai_suggestion; exec bash"

tmux select-window -t "$SESSION:race"
echo "Pronto. Abra a URL impressa na janela 'race' (viz: http://127.0.0.1:3001/?race=<id>)."
echo "Encerrar: tmux kill-session -t $SESSION && docker compose stop llama redis"

if [ -n "${TMUX:-}" ]; then tmux switch-client -t "$SESSION"; else tmux attach -t "$SESSION"; fi