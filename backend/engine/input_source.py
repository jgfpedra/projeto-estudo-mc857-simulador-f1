"""Input source — interface para consumir inputs de agentes externos.

A engine NÃO sabe de onde os inputs vêm (Redis, websocket, stdin, teclado,
arquivo de replay, etc.). Ela só conhece a interface :class:`InputSource`,
que expõe:

- :meth:`get_last_input(driver_id) -> Optional[InputEntry]`
- :meth:`update_last_input(driver_id, input) -> None`  (para agentes publicarem)
- :meth:`poll_all(driver_ids) -> Dict[driver_id, InputEntry]`

Implementações:

- :class:`InMemoryInputSource` — stub local, sem Redis. Bom para dev e teste.
- :class:`RedisInputSource` (em redis_input.py) — consome de Redis de verdade.

Formato do :class:`InputEntry`:
    Um dataclass com ``CarInput`` + timestamp Unix (``ts``) + contador (``seq``).
    O timestamp permite detectar "input stale" (sem atualização há muito tempo).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .controllers import CarInput


@dataclass
class InputEntry:
    """Um input publicado por um agente externo, com metadados de proveniência.

    Atributos
    --------
    car_input : CarInput
        O input em si (target_speed, steering, brake, grip_override).
    ts : float
        Timestamp Unix de quando o input foi publicado (segundos).
    seq : int
        Número de sequência incremental (para detectar ordem/queda de mensagens).
    source : str
        Identificador do agente que publicou (ex.: "keyboard", "rl_agent",
        "llm_v1"). Útil para log/auditoria.
    """

    car_input: CarInput
    ts: float
    seq: int
    source: str = "unknown"


class InputSource:
    """Interface base para fontes de input.

    Subclasses implementam:
    - :meth:`get_last_input` — lê o último input publicado para um driver.
    - :meth:`update_last_input` — publica um novo input (chamado por agentes externos).
    - :meth:`poll_all` — lê inputs de múltiplos drivers de uma vez.
    - :meth:`close` — libera recursos.

    A engine chama :meth:`get_last_input` (ou :meth:`poll_all`) a cada tick.
    Agentes externos (threads, processos, serviços) chamam
    :meth:`update_last_input` quando têm um novo input para publicar.
    """

    def get_last_input(self, driver_id: str) -> Optional[InputEntry]:
        raise NotImplementedError

    def update_last_input(
        self,
        driver_id: str,
        car_input: CarInput,
        source: str = "unknown",
    ) -> None:
        raise NotImplementedError

    def poll_all(self, driver_ids: List[str]) -> Dict[str, Optional[InputEntry]]:
        """Lê inputs para múltiplos drivers de uma vez. Default: itera um a um."""
        return {d: self.get_last_input(d) for d in driver_ids}

    def close(self) -> None:
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


# ---------------------------------------------------------------------------
# FileInputSource — IPC local baseado em arquivo JSON (sem Redis)
# ---------------------------------------------------------------------------

class FileInputSource(InputSource):
    """Consome e publica inputs via arquivo JSON compartilhado em disco.

    Permite comunicação segura entre processos (ex.: terminal da engine e
    terminal do teclado) sem precisar de Redis ou rede.
    """

    def __init__(
        self,
        race_id: str = "interlagos_001",
        file_path: Optional[str | Path] = None,
    ) -> None:
        self.race_id = race_id
        if file_path is not None:
            self.file_path = Path(file_path)
        else:
            self.file_path = Path(tempfile.gettempdir()) / f"f1_sim_inputs_{race_id}.json"
        self._lock = threading.RLock()
        self._cached_data: Dict[str, dict] = {}
        self._last_mtime: float = 0.0
        self._seq_counter = 0
        self.update_count = 0
        self.read_count = 0

    def _read_file(self) -> Dict[str, dict]:
        if not self.file_path.exists():
            return {}
        try:
            mtime = self.file_path.stat().st_mtime
            if mtime == self._last_mtime and self._cached_data:
                return self._cached_data
            with open(self.file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    self._cached_data = data
                    self._last_mtime = mtime
                    return self._cached_data
        except Exception:
            pass
        return self._cached_data

    def get_last_input(self, driver_id: str) -> Optional[InputEntry]:
        with self._lock:
            self.read_count += 1
            data = self._read_file()
            raw = data.get(driver_id)
            if not raw or not isinstance(raw, dict):
                return None
            try:
                car_input = CarInput(
                    target_speed_mps=float(raw.get("target_speed_mps", 0.0)),
                    steering_yaw_rad=float(raw.get("steering_yaw_rad", 0.0)),
                    brake=float(raw.get("brake", 0.0)),
                    grip_override=raw.get("grip_override"),
                    throttle=raw.get("throttle"),
                )
                return InputEntry(
                    car_input=car_input,
                    ts=float(raw.get("ts", time.time())),
                    seq=int(raw.get("seq", 0)),
                    source=str(raw.get("source", "file")),
                )
            except (ValueError, TypeError):
                return None

    def update_last_input(
        self,
        driver_id: str,
        car_input: CarInput,
        source: str = "unknown",
    ) -> None:
        with self._lock:
            self._seq_counter += 1
            self.update_count += 1
            current = dict(self._read_file())
            current[driver_id] = {
                "target_speed_mps": float(car_input.target_speed_mps),
                "steering_yaw_rad": float(car_input.steering_yaw_rad),
                "brake": float(car_input.brake),
                "grip_override": car_input.grip_override,
                "throttle": car_input.throttle,
                "ts": time.time(),
                "seq": self._seq_counter,
                "source": source,
            }
            self._cached_data = current

            # Escrita atômica via arquivo temporário no mesmo diretório
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_name = f".tmp_{self.file_path.name}_{os.getpid()}_{self._seq_counter}"
                tmp_path = self.file_path.parent / tmp_name
                with open(tmp_path, "w", encoding="utf-8") as fh:
                    json.dump(current, fh)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_path, self.file_path)
                self._last_mtime = self.file_path.stat().st_mtime
            except Exception:
                pass

    def poll_all(self, driver_ids: List[str]) -> Dict[str, Optional[InputEntry]]:
        with self._lock:
            return {d: self.get_last_input(d) for d in driver_ids}

    def stats(self) -> dict:
        with self._lock:
            return {
                "source": "file",
                "file_path": str(self.file_path),
                "updates": self.update_count,
                "reads": self.read_count,
            }


# ---------------------------------------------------------------------------
# InMemoryInputSource — stub local (sem Redis)
# ---------------------------------------------------------------------------

class InMemoryInputSource(InputSource):
    """Stub local: mantém inputs em um dict protegido por lock e sincroniza com IPC local.

    - Thread-safe: agentes externos (threads) podem publicar enquanto a
      engine consome no loop principal.
    - Sincronização de arquivo: se executado entre processos separados,
      permite trocar mensagens via FileInputSource transparente.
    """

    def __init__(self, fallback_race_id: Optional[str] = "interlagos_001") -> None:
        self._inputs: Dict[str, InputEntry] = {}
        self._lock = threading.RLock()
        self._seq_counter = 0
        self.update_count = 0
        self.read_count = 0
        self._file_ipc: Optional[FileInputSource] = (
            FileInputSource(race_id=fallback_race_id) if fallback_race_id else None
        )

    def get_last_input(self, driver_id: str) -> Optional[InputEntry]:
        with self._lock:
            self.read_count += 1
            mem_entry = self._inputs.get(driver_id)
            file_entry = self._file_ipc.get_last_input(driver_id) if self._file_ipc else None
            if mem_entry is None:
                return file_entry
            if file_entry is None:
                return mem_entry

            return file_entry if file_entry.ts >= mem_entry.ts else mem_entry

    def update_last_input(
        self,
        driver_id: str,
        car_input: CarInput,
        source: str = "unknown",
    ) -> None:
        with self._lock:
            self._seq_counter += 1
            self._inputs[driver_id] = InputEntry(
                car_input=car_input,
                ts=time.time(),
                seq=self._seq_counter,
                source=source,
            )
            self.update_count += 1
            if self._file_ipc is not None:
                self._file_ipc.update_last_input(driver_id, car_input, source=source)

    def poll_all(self, driver_ids: List[str]) -> Dict[str, Optional[InputEntry]]:
        with self._lock:
            self.read_count += 1
            res = {}
            for d in driver_ids:
                mem_entry = self._inputs.get(d)
                file_entry = self._file_ipc.get_last_input(d) if self._file_ipc else None
                if mem_entry is None:
                    res[d] = file_entry
                elif file_entry is None:
                    res[d] = mem_entry
                else:
                    res[d] = file_entry if file_entry.ts >= mem_entry.ts else mem_entry
            return res

    def stats(self) -> dict:
        with self._lock:
            return {
                "source": "memory",
                "drivers": list(self._inputs.keys()),
                "updates": self.update_count,
                "reads": self.read_count,
            }


# ---------------------------------------------------------------------------
# RedisInputSource — consome/publica inputs via Redis
# ---------------------------------------------------------------------------

class RedisInputSource(InputSource):
    """Consome e publica inputs via Redis Hash (`race:{race_id}:input`).

    Tenta lazy import de `redis`. Se o Redis não estiver instalado ou não
    estiver rodando, mantém um fallback em memória para evitar crashes.
    """

    def __init__(
        self,
        race_id: str = "race_001",
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
    ) -> None:
        self.race_id = race_id
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key = f"race:{race_id}:input"
        self._redis = None
        self._connected = False
        self._fallback_memory = InMemoryInputSource()

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
        except Exception:
            self._connected = False
            return False

    def get_last_input(self, driver_id: str) -> Optional[InputEntry]:
        import json
        if self._connect():
            try:
                val = self._redis.hget(self.key, driver_id)
                if val:
                    data = json.loads(val)
                    car_input = CarInput(
                        target_speed_mps=float(data.get("target_speed_mps", 0.0)),
                        steering_yaw_rad=float(data.get("steering_yaw_rad", 0.0)),
                        brake=float(data.get("brake", 0.0)),
                        grip_override=data.get("grip_override"),
                        throttle=data.get("throttle"),
                    )
                    return InputEntry(
                        car_input=car_input,
                        ts=float(data.get("ts", time.time())),
                        seq=int(data.get("seq", 0)),
                        source=data.get("source", "redis"),
                    )
            except Exception:
                self._connected = False
        return self._fallback_memory.get_last_input(driver_id)

    def update_last_input(
        self,
        driver_id: str,
        car_input: CarInput,
        source: str = "unknown",
    ) -> None:
        import json
        self._fallback_memory.update_last_input(driver_id, car_input, source=source)
        if self._connect():
            try:
                payload = json.dumps({
                    "target_speed_mps": car_input.target_speed_mps,
                    "steering_yaw_rad": car_input.steering_yaw_rad,
                    "brake": car_input.brake,
                    "grip_override": car_input.grip_override,
                    "throttle": car_input.throttle,
                    "ts": time.time(),
                    "source": source,
                })
                self._redis.hset(self.key, driver_id, payload)
            except Exception:
                self._connected = False

    def close(self) -> None:
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception:
                pass
        self._redis = None
        self._connected = False

    @property
    def name(self) -> str:
        return "RedisInputSource" if self._connected else "RedisInputSource(fallback_memory)"


__all__ = ["InputEntry", "InputSource", "InMemoryInputSource", "FileInputSource", "RedisInputSource"]
