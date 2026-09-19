"""Publisher interface.

Camada de saída do motor de simulação.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, TextIO

from .events import Event


class Publisher:
    """Interface base."""

    def publish(self, event: Event) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class NullPublisher(Publisher):
    """Descarta eventos. Útil para testes."""

    def publish(self, event: Event) -> None:
        return None


class JSONLPublisher(Publisher):
    """Escreve eventos em um arquivo JSONL (1 evento por linha)."""

    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        self._fh: Optional[TextIO] = None
        self._count = 0

    def _ensure_open(self) -> TextIO:
        if self._fh is None:
            self._fh = open(self.path, "w", encoding="utf-8")
        return self._fh

    def publish(self, event: Event) -> None:
        fh = self._ensure_open()
        line = json.dumps(event.to_dict(), ensure_ascii=False, default=str)
        fh.write(line + "\n")
        self._count += 1

    def flush(self) -> None:
        if self._fh is not None:
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.flush()
            self._fh.close()
            self._fh = None

    @property
    def event_count(self) -> int:
        return self._count


class RedisPublisher(Publisher):
    """Stub de publisher para Redis.

    Quando o Redis estiver disponível, basta instanciar com a configuração
    correta (host, port, channel). A implementação tenta ``import redis``
    de forma lazy; se falhar, fica em modo "simulado" (apenas imprime no log).

    Estado de corrida publicado:
    - channel ``race:{race_id}:events``  : eventos (JSON)
    - channel ``race:{race_id}:state``   : snapshot mais recente (hash/set)
    """

    def __init__(
        self,
        race_id: str,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        events_channel: Optional[str] = None,
        state_key: Optional[str] = None,
    ) -> None:
        self.race_id = race_id
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.events_channel = events_channel or f"race:{race_id}:events"
        self.state_key = state_key or f"race:{race_id}:state"
        self._redis = None
        self._connected = False
        self._last_state: Dict[str, Any] = {}

    def _connect(self) -> bool:
        if self._connected:
            return True
        try:
            import redis  # type: ignore
            self._redis = redis.Redis(
                host=self.host, port=self.port, db=self.db,
                password=self.password, decode_responses=True,
            )
            self._redis.ping()
            self._connected = True
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[RedisPublisher] could not connect to {self.host}:{self.port}: {exc}")
            self._connected = False
            return False

    def publish(self, event: Event) -> None:
        payload = json.dumps(event.to_dict(), ensure_ascii=False, default=str)
        if self._connect():
            try:
                self._redis.publish(self.events_channel, payload)
                if event.type in ("position_update", "tick", "lap_completed", "race_end"):
                    # atualiza estado "atual"
                    self._redis.hset(self.state_key, mapping={
                        "ts": event.ts,
                        "sim_ts": event.sim_ts,
                        "type": event.type,
                        "payload": payload,
                    })
            except Exception as exc:  # noqa: BLE001
                print(f"[RedisPublisher] publish failed: {exc}")
                self._connected = False
        else:
            # Modo simulado: apenas mantém último estado em memória.
            self._last_state = event.to_dict()

    def flush(self) -> None:
        pass

    def close(self) -> None:
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception:
                pass
