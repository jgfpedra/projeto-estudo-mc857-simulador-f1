"""
Métricas e observabilidade via MLflow para o engenheiro de IA.

Registra:
- Latência p50/p95 das chamadas ao Ollama
- Taxa de utilização do fallback (tático vs genérico)
- Quantidade de respostas JSON inválidas
- Mensagens suprimidas por repetição
- Quantidade de timeouts e erros
- Disponibilidade do Ollama
"""

from __future__ import annotations

import os
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

import mlflow

# Configuração MLflow
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.d")
EXPERIMENT_NAME = "f1-ai-engineer"

# Inicialização lazy
_mlflow_initialized = False
_init_lock = threading.Lock()


def _init_mlflow():
    """Inicializa MLflow uma única vez (thread-safe)."""
    global _mlflow_initialized
    with _init_lock:
        if _mlflow_initialized:
            return
        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
            if exp is None:
                mlflow.create_experiment(EXPERIMENT_NAME)
            mlflow.set_experiment(EXPERIMENT_NAME)
            _mlflow_initialized = True
        except Exception as e:
            print(f"[metrics] AVISO: Falha ao inicializar MLflow: {e}")


@dataclass
class MetricsCollector:
    """Coletor de métricas em memória com flush periódico no MLflow."""

    # Contadores
    total_calls: int = 0
    total_latency: float = 0.0
    latencies: list = field(default_factory=list)

    fallbacks_total: int = 0
    fallbacks_tactical: int = 0
    fallbacks_generic: int = 0

    invalid_json: int = 0
    suppressed_duplicates: int = 0
    timeouts: int = 0
    connection_errors: int = 0
    other_errors: int = 0

    ollama_available_checks: int = 0
    ollama_available_success: int = 0

    _lock: threading.RLock = field(default_factory=threading.RLock)

    def record_call(self, elapsed: float, ok: bool, error_type: str = None,
                    fallback: bool = False, fallback_tactical: bool = False,
                    invalid_json: bool = False, suppressed: bool = False):
        with self._lock:
            self.total_calls += 1
            self.total_latency += elapsed
            self.latencies.append(elapsed)
            # Manter apenas últimas 1000 latências para percentis
            if len(self.latencies) > 1000:
                self.latencies = self.latencies[-1000:]

            if not ok:
                if error_type == "timeout":
                    self.timeouts += 1
                elif error_type == "connection":
                    self.connection_errors += 1
                else:
                    self.other_errors += 1

            if fallback:
                self.fallbacks_total += 1
                if fallback_tactical:
                    self.fallbacks_tactical += 1
                else:
                    self.fallbacks_generic += 1

            if invalid_json:
                self.invalid_json += 1

            if suppressed:
                self.suppressed_duplicates += 1

    def record_ollama_availability(self, available: bool):
        with self._lock:
            self.ollama_available_checks += 1
            if available:
                self.ollama_available_success += 1

    def get_percentile(self, p: float) -> float:
        """Calcula percentil das latências (p em 0-100)."""
        with self._lock:
            if not self.latencies:
                return 0.0
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * p / 100)
            idx = min(idx, len(sorted_lat) - 1)
            return sorted_lat[idx]

    def get_stats(self) -> dict:
        """Retorna estatísticas agregadas."""
        with self._lock:
            if self.total_calls == 0:
                return {}

            p50 = self.get_percentile(50)
            p95 = self.get_percentile(95)
            p99 = self.get_percentile(99)

            fallback_rate = (self.fallbacks_total / self.total_calls * 100) if self.total_calls else 0
            tactical_rate = (self.fallbacks_tactical / self.fallbacks_total * 100) if self.fallbacks_total else 0
            invalid_rate = (self.invalid_json / self.total_calls * 100) if self.total_calls else 0
            timeout_rate = (self.timeouts / self.total_calls * 100) if self.total_calls else 0
            ollama_uptime = (self.ollama_available_success / self.ollama_available_checks * 100) if self.ollama_available_checks else 0

            return {
                "total_calls": self.total_calls,
                "latency_avg": self.total_latency / self.total_calls,
                "latency_p50": p50,
                "latency_p95": p95,
                "latency_p99": p99,
                "fallbacks_total": self.fallbacks_total,
                "fallback_rate_pct": round(fallback_rate, 1),
                "fallback_tactical": self.fallbacks_tactical,
                "fallback_tactical_rate_pct": round(tactical_rate, 1),
                "fallback_generic": self.fallbacks_generic,
                "invalid_json": self.invalid_json,
                "invalid_json_rate_pct": round(invalid_rate, 1),
                "suppressed_duplicates": self.suppressed_duplicates,
                "timeouts": self.timeouts,
                "timeout_rate_pct": round(timeout_rate, 1),
                "connection_errors": self.connection_errors,
                "other_errors": self.other_errors,
                "ollama_uptime_pct": round(ollama_uptime, 1),
            }

    def flush_to_mlflow(self, run_name: str = None):
        """Envia métricas atuais para MLflow."""
        _init_mlflow()
        if not _mlflow_initialized:
            return

        stats = self.get_stats()
        if not stats:
            return

        try:
            with mlflow.start_run(run_name=run_name or f"ai-engineer-{int(time.time())}", nested=True):
                # Métricas numéricas
                for key, value in stats.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value)

                # Tags informativas
                mlflow.set_tag("component", "ai-engineer")
                mlflow.set_tag("version", "1.0")

        except Exception as e:
            print(f"[metrics] Erro ao enviar para MLflow: {e}")


# Instância global
_collector = MetricsCollector()
_flush_thread: Optional[threading.Thread] = None
_flush_stop = threading.Event()


def get_collector() -> MetricsCollector:
    """Retorna o coletor global."""
    return _collector


def start_periodic_flush(interval_seconds: int = 60):
    """Inicia thread de flush periódico no MLflow."""
    global _flush_thread
    if _flush_thread and _flush_thread.is_alive():
        return

    _flush_stop.clear()

    def _flush_loop():
        while not _flush_stop.wait(interval_seconds):
            _collector.flush_to_mlflow(run_name="periodic-flush")

    _flush_thread = threading.Thread(target=_flush_loop, daemon=True, name="MLflowFlusher")
    _flush_thread.start()
    print(f"[metrics] Flush periódico iniciado (intervalo: {interval_seconds}s)")


def stop_periodic_flush():
    """Para a thread de flush periódico."""
    global _flush_thread
    _flush_stop.set()
    if _flush_thread:
        _flush_thread.join(timeout=5)
        _flush_thread = None
    # Flush final
    _collector.flush_to_mlflow(run_name="final-flush")
    print("[metrics] Flush periódico parado")


@contextmanager
def track_ollama_call():
    """Context manager para medir latência de chamada ao Ollama."""
    start = time.time()
    ok = True
    error_type = None
    fallback = False
    fallback_tactical = False
    invalid_json = False
    suppressed = False

    try:
        yield lambda **kwargs: None  # placeholder para setar flags
    except Exception:
        ok = False
        error_type = "exception"
        raise
    finally:
        elapsed = time.time() - start
        # As flags reais são setadas pelo caller via setattr no objeto yielded
        _collector.record_call(
            elapsed=elapsed,
            ok=ok,
            error_type=error_type,
            fallback=fallback,
            fallback_tactical=fallback_tactical,
            invalid_json=invalid_json,
            suppressed=suppressed,
        )


def record_ollama_call(elapsed: float, ok: bool, error_type: str = None,
                       fallback: bool = False, fallback_tactical: bool = False,
                       invalid_json: bool = False, suppressed: bool = False):
    """Registra uma chamada ao Ollama (função simples para uso direto)."""
    _collector.record_call(
        elapsed=elapsed,
        ok=ok,
        error_type=error_type,
        fallback=fallback,
        fallback_tactical=fallback_tactical,
        invalid_json=invalid_json,
        suppressed=suppressed,
    )


def record_duplicate_suppressed():
    """Registra que uma mensagem duplicada foi suprimida."""
    with _collector._lock:
        _collector.suppressed_duplicates += 1


def record_ollama_availability(available: bool):
    """Registra resultado de health check do Ollama."""
    _collector.record_ollama_availability(available)


def get_current_stats() -> dict:
    """Retorna estatísticas atuais (para dashboard/debug)."""
    return _collector.get_stats()