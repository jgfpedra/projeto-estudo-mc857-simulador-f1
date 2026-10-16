"""Gerencia o ciclo de vida das corridas em memória.

Cada corrida roda a :class:`SimulationEngine` numa thread própria (o motor é
síncrono/bloqueante — ver ``engine/simulation.py::run``). Os eventos que o
motor publica chegam aqui através de um :class:`Publisher` customizado
(:class:`BroadcastPublisher`) e são repassados para todas as conexões
WebSocket inscritas naquele ``race_id``.

Não há Redis envolvido ainda: tudo acontece dentro do mesmo processo Python.
Se no futuro for preciso escalar para múltiplos processos/instâncias, basta
trocar o ``BroadcastPublisher`` por ``engine.RedisPublisher`` (já existe no
projeto) e o ``InMemoryInputSource`` por ``RedisInputSource`` — a interface
pública (``create_race`` / ``subscribe``) não muda.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import uuid
from dataclasses import replace
from typing import Dict, Optional, Set

# Garante que "backend/" (raiz dos pacotes config/engine/domain) está no
# sys.path, igual ao truque usado em backend/scripts/run_sim.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_HERE)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG, CircuitLoadError, load_track
from engine import InMemoryInputSource, NullPublisher, Publisher, SimulationEngine
from engine.events import Event


class BroadcastPublisher(Publisher):
    """Publisher que repassa cada evento aos websockets inscritos na corrida.

    O motor roda numa thread separada do loop de eventos do asyncio (a thread
    da engine), então não dá para chamar ``await queue.put(...)`` direto daqui
    -- usamos ``asyncio.run_coroutine_threadsafe`` para agendar o broadcast de
    volta na thread principal do FastAPI, que é quem detém o event loop.
    """

    def __init__(self, race_id: str, manager: "RaceManager", loop: asyncio.AbstractEventLoop) -> None:
        self.race_id = race_id
        self.manager = manager
        self.loop = loop

    def publish(self, event: Event) -> None:
        payload = event.to_dict()
        asyncio.run_coroutine_threadsafe(
            self.manager.broadcast(self.race_id, payload),
            self.loop,
        )


class RaceHandle:
    """Estado interno de uma corrida ativa."""

    def __init__(self, engine: SimulationEngine, thread: threading.Thread) -> None:
        self.engine = engine
        self.thread = thread
        self.subscribers: Set[asyncio.Queue] = set()


class RaceManager:
    """Registro de corridas ativas + ponte engine -> websockets."""

    def __init__(self) -> None:
        self._races: Dict[str, RaceHandle] = {}
        self._lock = threading.Lock()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Chamado no startup do FastAPI para guardar o event loop principal."""
        self.loop = loop

    # ------------------------------------------------------------------
    # Criação da corrida
    # ------------------------------------------------------------------

    def create_race(self, laps: int, track: Optional[str], year: Optional[int]):
        if self.loop is None:
            raise RuntimeError("RaceManager.bind_loop() precisa ser chamado no startup")

        track_obj = load_track(track_name=track, year=year)

        race_id = f"race_{uuid.uuid4().hex[:8]}"
        config = replace(
            DEFAULT_INTERLAGOS_CONFIG,
            race_id=race_id,
            num_laps=laps,
            gui=False,      # sem janela do PyBullet: isso roda num servidor
            realtime=True,  # pacing em tempo real, pro front acompanhar "ao vivo"
        )

        drivers = list(DEFAULT_DRIVERS)
        input_source = InMemoryInputSource(fallback_race_id=race_id)
        publisher = BroadcastPublisher(race_id, self, self.loop)

        engine = SimulationEngine(
            config=config,
            track=track_obj,
            drivers=drivers,
            publisher=publisher,
            input_source=input_source,
        )

        thread = threading.Thread(target=self._run_engine, args=(engine,), daemon=True)

        with self._lock:
            self._races[race_id] = RaceHandle(engine=engine, thread=thread)

        thread.start()
        return race_id, track_obj, config

    @staticmethod
    def _run_engine(engine: SimulationEngine) -> None:
        try:
            engine.run()
        finally:
            engine.teardown()

    # ------------------------------------------------------------------
    # Pub/sub para os websockets
    # ------------------------------------------------------------------

    def exists(self, race_id: str) -> bool:
        with self._lock:
            return race_id in self._races

    def subscribe(self, race_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self._lock:
            self._races[race_id].subscribers.add(queue)
        return queue

    def unsubscribe(self, race_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            handle = self._races.get(race_id)
            if handle is not None:
                handle.subscribers.discard(queue)

    async def broadcast(self, race_id: str, payload: dict) -> None:
        with self._lock:
            handle = self._races.get(race_id)
            subscribers = set(handle.subscribers) if handle else set()
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Cliente lento: descarta o evento mais antigo e tenta de novo.
                try:
                    queue.get_nowait()
                    queue.put_nowait(payload)
                except asyncio.QueueEmpty:
                    pass


# Instância única compartilhada pelo app (ver api/main.py).
race_manager = RaceManager()
