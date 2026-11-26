import os
import requests
import time

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
MODEL = "llama3.2"
TIMEOUT_SECONDS = 90


def warm_up():
    """Chamada descartável só para carregar o modelo na memória antes do uso real."""
    print("[client] aquecendo modelo...")
    result = call_model('Responda apenas: {"status": "ok"}')
    print(f"[client] aquecimento concluído em {result['elapsed']:.1f}s")


def call_model(prompt: str) -> dict:
    """
    Retorna {"ok": True, "response": str, "elapsed": float}
    ou {"ok": False, "error": str, "elapsed": float} — nunca levanta exceção,
    pra quem chama poder decidir o fallback sem try/except espalhado.
    """
    start = time.time()
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=TIMEOUT_SECONDS,
        )
        elapsed = time.time() - start
        response.raise_for_status()
        return {"ok": True, "response": response.json()["response"], "elapsed": elapsed}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        return {"ok": False, "error": f"timeout após {TIMEOUT_SECONDS}s", "elapsed": elapsed}

    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start
        return {"ok": False, "error": f"erro de conexão: {e}", "elapsed": elapsed}

    except Exception as e:
        elapsed = time.time() - start
        return {"ok": False, "error": f"erro inesperado: {e}", "elapsed": elapsed}
