import os
import requests
import time

from metrics import record_ollama_call, record_ollama_availability

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT", "30"))

# Parâmetros otimizados para latência
OLLAMA_OPTIONS = {
    "keep_alive": "30m",      # Mantém modelo carregado por 30 min
    "num_predict": 150,       # Limita tokens de resposta (JSON curto)
    "num_ctx": 2048,          # Contexto menor = mais rápido
    "temperature": 0.5,       # Equilíbrio entre coerência e variedade
    "top_p": 0.9,             # Nucleus sampling
    "repeat_penalty": 1.1,    # Evita repetições
}


def warm_up():
    """Chamada descartável só para carregar o modelo na memória antes do uso real."""
    print("[client] aquecendo modelo...")
    result = call_model('Responda apenas: {"status": "ok"}')
    print(f"[client] aquecimento concluído em {result['elapsed']:.1f}s")
    record_ollama_availability(result["ok"])


def call_model(
    prompt: str,
    options: dict | None = None,
    timeout: float | None = None,
) -> dict:
    """
    Retorna {"ok": True, "response": str, "elapsed": float}
    ou {"ok": False, "error": str, "elapsed": float} — nunca levanta exceção,
    pra quem chama poder decidir o fallback sem try/except espalhado.
    ``options`` e ``timeout`` permitem ampliar tarefas como o debrief sem
    alterar os parâmetros curtos e rápidos das sugestões ao vivo.
    """
    request_timeout = TIMEOUT_SECONDS if timeout is None else timeout
    start = time.time()
    error_type = None
    ok = False

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {**OLLAMA_OPTIONS, **(options or {})},
            },
            timeout=request_timeout,
        )
        elapsed = time.time() - start
        response.raise_for_status()
        ok = True
        record_ollama_call(elapsed=elapsed, ok=True)
        record_ollama_availability(True)
        return {"ok": True, "response": response.json()["response"], "elapsed": elapsed}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        error_type = "timeout"
        record_ollama_call(elapsed=elapsed, ok=False, error_type="timeout")
        record_ollama_availability(False)
        return {"ok": False, "error": f"timeout após {request_timeout:g}s", "elapsed": elapsed}

    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start
        error_type = "connection"
        record_ollama_call(elapsed=elapsed, ok=False, error_type="connection")
        record_ollama_availability(False)
        return {"ok": False, "error": f"erro de conexão: {e}", "elapsed": elapsed}

    except Exception as e:
        elapsed = time.time() - start
        error_type = "exception"
        record_ollama_call(elapsed=elapsed, ok=False, error_type="exception")
        record_ollama_availability(False)
        return {"ok": False, "error": f"erro inesperado: {e}", "elapsed": elapsed}
