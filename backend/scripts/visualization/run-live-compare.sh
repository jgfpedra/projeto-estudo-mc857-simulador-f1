#!/usr/bin/env bash
# A mesma engine alimenta a janela PyBullet e o navegador via Redis/WebSocket.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
PYTHON_BIN="${F1_PYTHON:-$ROOT_DIR/backend/.venv/bin/python}"
API_PORT="${F1_API_PORT:-8000}"
VIZ_PORT="${F1_VIZ_PORT:-5174}"
LAPS=3
NUM_DRIVERS=2
TRACK=interlagos
YEAR=
CAMERA=follow
OPEN_BROWSER=1
API_PID=
VIZ_PID=
REDIS_CONTAINER=

usage() {
  cat <<'HELP'
Uso: backend/scripts/visualization/run-live-compare.sh [--laps N] [--drivers N] [--track NOME] [--year ANO] [--camera follow|overview] [--no-browser]

Inicia uma corrida na engine com a janela do PyBullet e abre a mesma corrida
no visualizador 3D do navegador. Pressione Ctrl+C para encerrar.

Variáveis opcionais: F1_PYTHON, F1_API_PORT, F1_VIZ_PORT, REDIS_URL.
Sem REDIS_URL, é iniciado um contêiner Redis temporário pelo Docker.
HELP
}

while (($#)); do
  case "$1" in
    --laps|--drivers|--track|--year|--camera)
      if (($# < 2)); then printf 'Falta valor para %s\n' "$1" >&2; exit 2; fi
      case "$1" in
        --laps) LAPS=$2;; --drivers) NUM_DRIVERS=$2;; --track) TRACK=$2;; --year) YEAR=$2;; --camera) CAMERA=$2;;
      esac
      shift 2;;
    --no-browser) OPEN_BROWSER=0; shift;;
    -h|--help) usage; exit 0;;
    *) printf 'Opção desconhecida: %s\n' "$1" >&2; usage >&2; exit 2;;
  esac
done

[[ "$LAPS" =~ ^[0-9]+$ ]] && ((10#$LAPS >= 1 && 10#$LAPS <= 200)) || { echo 'Voltas devem estar entre 1 e 200.' >&2; exit 2; }
[[ "$NUM_DRIVERS" =~ ^[0-9]+$ ]] && ((10#$NUM_DRIVERS >= 1 && 10#$NUM_DRIVERS <= 24)) || { echo 'Corredores devem estar entre 1 e 24.' >&2; exit 2; }
[[ -z "$YEAR" || "$YEAR" =~ ^[0-9]{4}$ ]] || { echo 'Ano inválido.' >&2; exit 2; }
[[ "$CAMERA" == follow || "$CAMERA" == overview ]] || { echo 'Câmera deve ser follow ou overview.' >&2; exit 2; }
for port in "$API_PORT" "$VIZ_PORT"; do
  [[ "$port" =~ ^[0-9]+$ ]] && ((10#$port >= 1 && 10#$port <= 65535)) || { echo "Porta inválida: $port" >&2; exit 2; }
done
[[ -n "${DISPLAY:-}" ]] || { echo 'A janela do PyBullet precisa de uma sessão gráfica com DISPLAY configurado.' >&2; exit 1; }
[[ -x "$PYTHON_BIN" ]] || { echo "Python do backend não encontrado: $PYTHON_BIN. Crie backend/.venv e instale backend/requirements.txt." >&2; exit 1; }
for command in npm curl; do
  command -v "$command" >/dev/null || { echo "Comando necessário não encontrado: $command" >&2; exit 1; }
done
"$PYTHON_BIN" -c 'import redis, fastapi, uvicorn, pybullet' >/dev/null || { echo 'Instale as dependências com: backend/.venv/bin/pip install -r backend/requirements.txt' >&2; exit 1; }
"$PYTHON_BIN" - "$API_PORT" "$VIZ_PORT" <<'PYPORT'
import socket, sys
sockets = []
try:
    for port in map(int, sys.argv[1:]):
        sock = socket.socket()
        sockets.append(sock)
        sock.bind(("127.0.0.1", port))
except OSError as exc:
    print(f"Porta indisponível: {port} ({exc}). Use F1_API_PORT ou F1_VIZ_PORT.", file=sys.stderr)
    sys.exit(1)
finally:
    for sock in sockets: sock.close()
PYPORT

cleanup() {
  trap - EXIT INT TERM
  [[ -z "$VIZ_PID" ]] || kill "$VIZ_PID" 2>/dev/null || true
  [[ -z "$API_PID" ]] || kill "$API_PID" 2>/dev/null || true
  [[ -z "$VIZ_PID" ]] || wait "$VIZ_PID" 2>/dev/null || true
  [[ -z "$API_PID" ]] || wait "$API_PID" 2>/dev/null || true
  if [[ -n "$REDIS_CONTAINER" ]]; then docker stop -t 1 "$REDIS_CONTAINER" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ -z "${REDIS_URL:-}" ]]; then
  command -v docker >/dev/null || { echo 'Instale o Docker ou informe REDIS_URL para um Redis existente.' >&2; exit 1; }
  docker info >/dev/null 2>&1 || { echo 'Não foi possível acessar o Docker. Inicie-o ou informe REDIS_URL.' >&2; exit 1; }
  redis_name="f1-live-compare-$$-${RANDOM}"
  echo 'Iniciando Redis temporário…'
  REDIS_CONTAINER=$(docker run --rm -d --name "$redis_name" -p 127.0.0.1::6379 redis:7-alpine)
  redis_address=$(docker port "$REDIS_CONTAINER" 6379/tcp)
  REDIS_URL="redis://127.0.0.1:${redis_address##*:}/0"
fi
export REDIS_URL
for _ in {1..40}; do
  if "$PYTHON_BIN" -c 'import os, redis; redis.Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=1).ping()' >/dev/null 2>&1; then break; fi
  sleep 0.25
done
"$PYTHON_BIN" -c 'import os, redis; redis.Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=1).ping()' >/dev/null || { echo 'Redis indisponível.' >&2; exit 1; }

if [[ ! -x "$ROOT_DIR/viz3d/node_modules/.bin/vite" ]]; then
  echo 'Instalando dependências do visualizador…'
  (cd "$ROOT_DIR/viz3d" && npm ci --no-audit --no-fund)
fi

export F1_PYBULLET_GUI=1
export F1_GUI_CAMERA="$CAMERA"
export CORS_ORIGINS="http://127.0.0.1:$VIZ_PORT,http://localhost:$VIZ_PORT"
export VITE_API_URL="http://127.0.0.1:$API_PORT"
"$PYTHON_BIN" -m uvicorn api.main:app --app-dir "$ROOT_DIR/backend" --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!
(cd "$ROOT_DIR/viz3d" && exec ./node_modules/.bin/vite --host 127.0.0.1 --port "$VIZ_PORT" --strictPort) &
VIZ_PID=$!

for _ in {1..120}; do
  if ! kill -0 "$API_PID" 2>/dev/null || ! kill -0 "$VIZ_PID" 2>/dev/null; then echo 'A API ou o visualizador encerrou durante a inicialização.' >&2; exit 1; fi
  if curl -fsS "http://127.0.0.1:$API_PORT/docs" >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:$VIZ_PORT/" >/dev/null 2>&1; then break; fi
  sleep 0.25
done
curl -fsS "http://127.0.0.1:$API_PORT/docs" >/dev/null || { echo 'API não ficou pronta.' >&2; exit 1; }
curl -fsS "http://127.0.0.1:$VIZ_PORT/" >/dev/null || { echo 'Visualizador não ficou pronto.' >&2; exit 1; }

payload=$("$PYTHON_BIN" -c 'import json,sys; print(json.dumps({"laps":int(sys.argv[1]), "num_drivers":int(sys.argv[2]), "track":sys.argv[3] or None, "year":int(sys.argv[4]) if sys.argv[4] else None}))' "$LAPS" "$NUM_DRIVERS" "$TRACK" "$YEAR")
response=$(curl -fsS -X POST "http://127.0.0.1:$API_PORT/races" -H 'Content-Type: application/json' -d "$payload") || { echo 'Falha ao iniciar a corrida.' >&2; exit 1; }
race_id=$("$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["race_id"])' <<< "$response")
echo 'Aguardando o primeiro passo da engine e a janela do PyBullet…'
"$PYTHON_BIN" - "$race_id" <<'PYREADY'
import json, os, sys, time
import redis
client = redis.Redis.from_url(os.environ['REDIS_URL'], decode_responses=True)
race_id = sys.argv[1]
for _ in range(120):
    if client.get(f'race:{race_id}:state'):
        break
    result = client.get(f'race:{race_id}:result')
    if result:
        print('Falha na simulação:', json.loads(result).get('message', result), file=sys.stderr)
        sys.exit(1)
    time.sleep(0.25)
else:
    print('A engine não publicou o primeiro estado em 30 segundos.', file=sys.stderr)
    sys.exit(1)
PYREADY
url="http://127.0.0.1:$VIZ_PORT/?race=$race_id"
printf '\nCorrida: %s\nVisualização: %s\nPyBullet: janela local (câmera %s)\nPressione Ctrl+C para encerrar.\n\n' "$race_id" "$url" "$CAMERA"
if ((OPEN_BROWSER)); then
  if command -v xdg-open >/dev/null; then
    xdg-open "$url" >/dev/null 2>&1 || echo 'Não foi possível abrir o navegador automaticamente; acesse o endereço acima.' >&2
  else
    echo 'Abra o endereço acima no navegador.' >&2
  fi
fi
if wait -n "$API_PID" "$VIZ_PID"; then
  echo 'A API ou o visualizador encerrou.' >&2
  exit 1
else
  status=$?
  echo "A API ou o visualizador encerrou com código $status." >&2
  exit "$status"
fi
