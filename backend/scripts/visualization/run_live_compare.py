#!/usr/bin/env python3
"""Run one authoritative race in the PyBullet GUI and the browser viewer."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import webbrowser


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
VIZ_ROOT = PROJECT_ROOT / "viz3d"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Abre a mesma corrida na GUI do PyBullet e no visualizador 3D web."
    )
    parser.add_argument("--laps", type=int, default=3, help="voltas (1–200; padrão: 3)")
    parser.add_argument("--drivers", type=int, default=2, help="corredores (1–24; padrão: 2)")
    parser.add_argument("--track", default="interlagos", help="pista (padrão: interlagos)")
    parser.add_argument("--year", type=int, help="ano da sessão FastF1, quando aplicável")
    parser.add_argument("--camera", choices=("follow", "overview"), default="follow")
    parser.add_argument("--no-browser", action="store_true", help="não abrir o navegador automaticamente")
    args = parser.parse_args()
    if not 1 <= args.laps <= 200:
        parser.error("--laps deve estar entre 1 e 200")
    if not 1 <= args.drivers <= 24:
        parser.error("--drivers deve estar entre 1 e 24")
    if args.year is not None and not 1000 <= args.year <= 9999:
        parser.error("--year deve ter quatro dígitos")
    return args


def python_executable() -> str:
    override = os.environ.get("F1_PYTHON")
    if override:
        return override
    if os.name == "nt":
        candidate = BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = BACKEND_ROOT / ".venv" / "bin" / "python"
    return str(candidate) if candidate.is_file() else sys.executable


def npm_command(*args: str) -> list[str]:
    executable = shutil.which("npm")
    if executable is None:
        raise RuntimeError("Node.js/npm não encontrado no PATH.")
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        return ["cmd", "/c", executable, *args]
    return [executable, *args]


def check_port(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Porta {port} indisponível; ajuste F1_API_PORT ou F1_VIZ_PORT.") from exc


def check_python_dependencies(python: str) -> None:
    result = subprocess.run(
        [python, "-c", "import fastapi, pybullet, redis, uvicorn"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            "Dependências do backend ausentes. Instale os requisitos com "
            f"{python} -m pip install -r {BACKEND_ROOT / 'requirements.txt'}.\n{result.stderr.strip()}"
        )


def ping_redis(python: str, redis_url: str) -> bool:
    check = subprocess.run(
        [python, "-c", "import redis,sys; redis.Redis.from_url(sys.argv[1], socket_connect_timeout=1).ping()", redis_url],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    return check.returncode == 0


def http_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def process_options() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def redis_state(python: str, redis_url: str, race_id: str) -> tuple[bool, str | None]:
    code = (
        "import json,redis,sys; c=redis.Redis.from_url(sys.argv[1],decode_responses=True); "
        "state=c.get(f'race:{sys.argv[2]}:state'); result=c.get(f'race:{sys.argv[2]}:result'); "
        "print('STATE' if state else ('RESULT '+result if result else 'WAIT'))"
    )
    result = subprocess.run(
        [python, "-c", code, redis_url, race_id],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        return False, None
    output = result.stdout.strip()
    if output == "STATE":
        return True, None
    if output.startswith("RESULT "):
        try:
            message = json.loads(output[7:]).get("message", output[7:])
        except json.JSONDecodeError:
            message = output[7:]
        return False, str(message)
    return False, None


def run() -> int:
    args = parse_args()
    api_port = int(os.environ.get("F1_API_PORT", "8000"))
    viz_port = int(os.environ.get("F1_VIZ_PORT", "5174"))
    if not 1 <= api_port <= 65535 or not 1 <= viz_port <= 65535:
        raise RuntimeError("F1_API_PORT e F1_VIZ_PORT devem estar entre 1 e 65535.")
    check_port(api_port)
    check_port(viz_port)

    python = python_executable()
    check_python_dependencies(python)
    npm_command("--version")

    redis_container: str | None = None
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        if shutil.which("docker") is None:
            raise RuntimeError("Informe REDIS_URL ou instale Docker para iniciar um Redis temporário.")
        name = f"f1-live-compare-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        started = subprocess.run(
            ["docker", "run", "--rm", "-d", "--name", name, "-p", "127.0.0.1::6379", "redis:7-alpine"],
            capture_output=True,
            text=True,
        )
        if started.returncode:
            raise RuntimeError(f"Não foi possível iniciar Redis via Docker.\n{started.stderr.strip()}")
        redis_container = started.stdout.strip()
        mapped_result = subprocess.run(
            ["docker", "port", redis_container, "6379/tcp"], capture_output=True, text=True
        )
        mapped_lines = mapped_result.stdout.strip().splitlines()
        if mapped_result.returncode or not mapped_lines:
            subprocess.run(["docker", "stop", "-t", "1", redis_container],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            raise RuntimeError(f"Não foi possível localizar a porta do Redis.\n{mapped_result.stderr.strip()}")
        mapped = mapped_lines[0]
        redis_url = f"redis://{mapped}/0"

    api_process = viz_process = None
    environment = os.environ.copy()
    environment.update(
        REDIS_URL=redis_url,
        F1_PYBULLET_GUI="1",
        F1_GUI_CAMERA=args.camera,
        CORS_ORIGINS=f"http://127.0.0.1:{viz_port},http://localhost:{viz_port}",
        VITE_API_URL=f"http://127.0.0.1:{api_port}",
    )
    try:
        for _ in range(40):
            if ping_redis(python, redis_url):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("Redis indisponível.")

        if not (VIZ_ROOT / "node_modules").is_dir():
            print("Instalando dependências do visualizador…")
            subprocess.run(npm_command("ci", "--no-audit", "--no-fund"), cwd=VIZ_ROOT, check=True)

        api_process = subprocess.Popen(
            [python, "-m", "uvicorn", "api.main:app", "--app-dir", str(BACKEND_ROOT),
             "--host", "127.0.0.1", "--port", str(api_port)],
            cwd=PROJECT_ROOT,
            env=environment,
            **process_options(),
        )
        vite_command = npm_command("run", "dev", "--", "--host", "127.0.0.1", "--port", str(viz_port), "--strictPort")
        viz_process = subprocess.Popen(
            vite_command,
            cwd=VIZ_ROOT,
            env=environment,
            **process_options(),
        )

        api_url, viz_url = f"http://127.0.0.1:{api_port}/docs", f"http://127.0.0.1:{viz_port}/"
        for _ in range(120):
            if api_process.poll() is not None or viz_process.poll() is not None:
                raise RuntimeError("A API ou o visualizador encerrou durante a inicialização.")
            if http_ready(api_url) and http_ready(viz_url):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("API ou visualizador não ficou pronto.")

        payload = {"laps": args.laps, "num_drivers": args.drivers, "track": args.track or None, "year": args.year}
        request = urllib.request.Request(
            f"http://127.0.0.1:{api_port}/races",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                race_id = json.load(response)["race_id"]
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Falha ao iniciar a corrida: HTTP {exc.code} {exc.read().decode(errors='replace')}") from exc

        print("Aguardando o primeiro estado da engine e a janela do PyBullet…")
        for _ in range(120):
            ready, failure = redis_state(python, redis_url, race_id)
            if ready:
                break
            if failure:
                raise RuntimeError(f"Falha na simulação: {failure}")
            if api_process.poll() is not None:
                raise RuntimeError("A API encerrou antes do primeiro estado.")
            time.sleep(0.25)
        else:
            raise RuntimeError("A engine não publicou o primeiro estado em 30 segundos.")

        viewer_url = f"http://127.0.0.1:{viz_port}/?race={race_id}"
        print(f"\nCorrida: {race_id}\nVisualização 3D: {viewer_url}\nPyBullet: janela local ({args.camera})")
        print(f"Corredores: {args.drivers}. Pressione Ctrl+C para encerrar.\n")
        if not args.no_browser:
            webbrowser.open(viewer_url)

        while True:
            for process in (api_process, viz_process):
                status = process.poll()
                if status is not None:
                    raise RuntimeError(f"A API ou o visualizador encerrou com código {status}.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 130
    finally:
        stop_process(viz_process)
        stop_process(api_process)
        if redis_container:
            subprocess.run(["docker", "stop", "-t", "1", redis_container], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
