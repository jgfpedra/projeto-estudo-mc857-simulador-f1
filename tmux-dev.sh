#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="${F1_TMUX_SESSION:-f1-dev}"
SERVICES=(llama redis backend ai frontend viz3d)

for command in docker tmux nvim; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Erro: comando obrigatório não encontrado: $command" >&2
    exit 1
  fi
done

docker compose up -d "${SERVICES[@]}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "A sessão tmux '$SESSION' já existe; anexando a ela."
else
  tmux new-session -d -s "$SESSION" -n code -c "$ROOT"
  tmux send-keys -t "$SESSION:code" 'nvim' C-m

  for service in "${SERVICES[@]}"; do
    tmux new-window -t "$SESSION" -n "logs-$service" -c "$ROOT" \
      "docker compose logs --follow --tail=100 --timestamps '$service'; exec \${SHELL:-/bin/bash} -l"
  done

  tmux select-window -t "$SESSION:code"
  echo "Sessão '$SESSION' criada: janela code + logs de ${#SERVICES[@]} serviços."
fi

if [[ -n "${TMUX:-}" ]]; then
  exec tmux switch-client -t "$SESSION"
else
  exec tmux attach-session -t "$SESSION"
fi
