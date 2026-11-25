#!/usr/bin/env bash
# start-f1.sh — sobe Redis e depois a stack tmux

set -euo pipefail

echo "=== Parando containers Redis antigos ==="
docker stop f1-redis 2>/dev/null || true
docker rm f1-redis 2>/dev/null || true

echo "=== Subindo Redis ==="
docker run --rm -d -p 6379:6379 --name f1-redis redis:7-alpine
sleep 2

if ! docker ps | grep -q f1-redis; then
  echo "ERRO: Redis não subiu"
  exit 1
fi

echo "=== Redis OK. Escolha a stack: ==="
echo "1) tmux-ai.sh    (API + IA + corrida + redis-mon)"
echo "2) tmux-full.sh  (tudo: + viz3d + frontend)"
echo ""
read -p "Opção [1/2]: " opt

case "$opt" in
  1) ./tmux-ai.sh ;;
  2) ./tmux-full.sh ;;
  *) echo "Inválido"; exit 1 ;;
esac

echo ""
echo "Pronto! Anexe com:"
echo "  tmux attach -t f1-ai"
echo "ou"
echo "  tmux attach -t f1-full"