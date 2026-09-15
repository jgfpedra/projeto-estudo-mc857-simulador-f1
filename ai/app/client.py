# ai/app/client.py
import os
import requests
import time
import threading
import sys

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
MODEL = "llama3.2"


def _show_progress(stop_event: threading.Event):
    start = time.time()
    while not stop_event.is_set():
        elapsed = time.time() - start
        sys.stdout.write(f"\r[aguardando resposta do modelo... {elapsed:.1f}s]")
        sys.stdout.flush()
        time.sleep(0.5)
    sys.stdout.write("\r" + " " * 50 + "\r")  # limpa a linha ao terminar


def call_model(prompt: str) -> tuple[str, float]:
    stop_event = threading.Event()
    progress_thread = threading.Thread(target=_show_progress, args=(stop_event,))
    progress_thread.start()

    start = time.time()
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        })
        elapsed = time.time() - start
        response.raise_for_status()
        result = response.json()["response"]
    finally:
        stop_event.set()
        progress_thread.join()

    return result, elapsed
