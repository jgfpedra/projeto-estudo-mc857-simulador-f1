"""Car controllers.

Camada que desacopla "quem decide o input" do "motor que aplica na física".
Cada controller implementa ``compute_input(env_state, driver_state) -> CarInput``.

Implementações incluídas:

- :class:`ManualController` — input fixo (para teste ou replay).
- :class:`ExternalController` — recebe input via :meth:`set_input`; usado por
  agentes externos (IA via API, websocket, replay, etc.) no MESMO processo.
- :class:`InputSourceController` — consome input de uma :class:`InputSource`
  (ex.: Redis, InMemoryInputSource). A engine se inscreve na fonte e o
  controller apenas repassa o último input publicado.

**Importante**: NÃO há mais controller que faz o carro "andar sozinho"
(waypoint follower foi removido). O motor espera inputs externos.

A ideia é que o :class:`~racing_sim.engine.simulation.SimulationEngine`
mantenha um registry ``driver_id -> controller`` e, a cada tick, chame
``compute_input`` para obter o :class:`CarInput` que será aplicado na física.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class CarInput:
    """Input de controle para um carro em um tick.

    Atributos
    --------
    target_speed_mps : float
        Velocidade-alvo em m/s. Se throttle for None, o motor calcula tração
        proporcional a este valor. Use 0.0 para parar o carro.
    steering_yaw_rad : float
        Ângulo de steering em radianos. Range típico: [-pi/4, +pi/4].
        Positivo = virar à esquerda, negativo = virar à direita.
    brake : float
        Intensidade de frenagem em [0, 1]. 0 = sem freio, 1 = freio total.
    grip_override : Optional[float]
        Se fornecido, sobrescreve o grip_multiplier calculado pelo motor
        (que usa pneu + clima). Útil para simular falhas de pneu manualmente.
    throttle : Optional[float]
        Intensidade de acelerador em [0, 1]. Se fornecido, comanda diretamente
        o acelerador do carro (modo ideal para Gymnasium e simulador manual).
    """

    target_speed_mps: float = 0.0
    steering_yaw_rad: float = 0.0
    brake: float = 0.0
    grip_override: Optional[float] = None
    throttle: Optional[float] = None

    @classmethod
    def neutral(cls) -> "CarInput":
        """Input neutro: carro parado, sem steering, sem freio."""
        return cls(target_speed_mps=0.0, steering_yaw_rad=0.0, brake=0.0, throttle=0.0)

    @classmethod
    def brake_full(cls) -> "CarInput":
        """Input de freio total: speed=0, brake=1."""
        return cls(target_speed_mps=0.0, steering_yaw_rad=0.0, brake=1.0, throttle=0.0)


@dataclass
class EnvironmentState:
    """Snapshot do estado do ambiente repassado aos controllers a cada tick.

    Controllers podem usar essa informação (e o ``DriverState`` recebido)
    para decidir o próximo input.
    """

    sim_ts: float
    lap: int
    weather: Any  # WeatherState
    track: Any    # Track
    all_driver_states: Dict[str, Any]  # driver_id -> DriverState


class CarController:
    """Interface base para controllers de carro.

    Subclasses implementam :meth:`compute_input`.
    """

    def compute_input(
        self,
        env: EnvironmentState,
        driver_state: Any,
    ) -> CarInput:
        raise NotImplementedError

    def reset(self) -> None:
        """Chamado quando a simulação reinicia. Override opcional."""
        pass


# ---------------------------------------------------------------------------
# ManualController — input fixo (para teste/replay)
# ---------------------------------------------------------------------------

class ManualController(CarController):
    """Retorna sempre o mesmo input. Útil para testes determinísticos.

    Exemplo::

        ctrl = ManualController(target_speed_mps=30.0, steering_yaw_rad=0.0)
        engine.set_controller("drv_01", ctrl)
    """

    def __init__(
        self,
        target_speed_mps: float = 0.0,
        steering_yaw_rad: float = 0.0,
        brake: float = 0.0,
    ) -> None:
        self._fixed_input = CarInput(
            target_speed_mps=target_speed_mps,
            steering_yaw_rad=steering_yaw_rad,
            brake=brake,
        )

    def compute_input(self, env: EnvironmentState, driver_state: Any) -> CarInput:
        return self._fixed_input

    def set_input(self, target_speed_mps: float, steering_yaw_rad: float, brake: float = 0.0) -> None:
        self._fixed_input = CarInput(
            target_speed_mps=target_speed_mps,
            steering_yaw_rad=steering_yaw_rad,
            brake=brake,
        )


# ---------------------------------------------------------------------------
# ExternalController — recebe input via set_input (para IA externa in-process)
# ---------------------------------------------------------------------------

class ExternalController(CarController):
    """Controller que recebe inputs via :meth:`set_input`.

    Caso de uso: um agente externo (IA, websocket, replay JSONL) calcula
    o input e o publica no controller antes de cada tick, no MESMO processo.

    Se nenhum input for setado antes do primeiro tick, retorna input neutro
    (carro parado).

    Exemplo::

        ctrl = ExternalController()
        engine.set_controller("drv_01", ctrl)
        # ... em outro thread/callback:
        ctrl.set_input(target_speed=45.0, steering=0.1, brake=0.0)
    """

    def __init__(self) -> None:
        self._current_input = CarInput.neutral()
        self._last_update_ts: float = 0.0
        self._update_count: int = 0

    def set_input(
        self,
        target_speed_mps: float = 0.0,
        steering_yaw_rad: float = 0.0,
        brake: float = 0.0,
        grip_override: Optional[float] = None,
        throttle: Optional[float] = None,
    ) -> None:
        """Atualiza o input que será aplicado no próximo tick."""
        self._current_input = CarInput(
            target_speed_mps=float(target_speed_mps),
            steering_yaw_rad=float(steering_yaw_rad),
            brake=float(brake),
            grip_override=grip_override,
            throttle=float(throttle) if throttle is not None else None,
        )
        self._update_count += 1
        self._last_update_ts = time.time()

    def compute_input(self, env: EnvironmentState, driver_state: Any) -> CarInput:
        return self._current_input

    def reset(self) -> None:
        self._current_input = CarInput.neutral()
        self._last_update_ts = 0.0
        self._update_count = 0

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def last_update_ts(self) -> float:
        return self._last_update_ts


# ---------------------------------------------------------------------------
# InputSourceController — consome input de uma InputSource (Redis ou in-memory)
# ---------------------------------------------------------------------------

class InputSourceController(CarController):
    """Controller que consome input de uma :class:`InputSource`.

    A engine cria o :class:`InputSource` (Redis ou in-memory) e o injeta
    neste controller. A cada tick, o controller chama
    ``source.get_last_input(driver_id)`` e retorna o input encontrado.

    Se nenhum input foi publicado, OU o último input é "stale" (sem
    atualização há mais de ``stale_after_s`` segundos), retorna ``None``
    para a engine decidir o fallback (default: freia aos poucos).

    Exemplo::

        from racing_sim.engine import InputSourceController, InMemoryInputSource

        source = InMemoryInputSource()
        engine.set_input_source(source)  # engine cria controllers automaticamente

        # ou manualmente:
        ctrl = InputSourceController(
            driver_id="drv_01",
            source=source,
            stale_after_s=1.0,
        )
        engine.set_controller("drv_01", ctrl)
    """

    def __init__(
        self,
        driver_id: str,
        source: Any,  # InputSource (import lazy para evitar circularidade)
        fallback_input: Optional[CarInput] = None,
        stale_after_s: float = 1.0,
    ) -> None:
        self.driver_id = driver_id
        self.source = source
        self.fallback_input = fallback_input
        self.stale_after_s = stale_after_s
        self._last_entry: Any = None  # InputEntry
        self._last_input: Optional[CarInput] = None

    def compute_input(self, env: EnvironmentState, driver_state: Any) -> Optional[CarInput]:
        """Lê o último input da fonte; se não houver ou for stale, retorna None.

        Retorna ``None`` quando:
        - Nenhum input foi publicado ainda.
        - O último input foi publicado há mais de ``stale_after_s`` segundos
          (input "stale" — considera-se que o agente externo parou de responder).

        Em ambos os casos, a engine decide o fallback (default: freia aos poucos).
        """
        import time
        entry = self.source.get_last_input(self.driver_id)
        if entry is None:
            # Nenhum input publicado
            return self.fallback_input

        # Verifica se o input é stale (sem atualização há muito tempo)
        # ``entry.ts`` é o timestamp de quando foi publicado
        if self.stale_after_s > 0:
            age = time.time() - entry.ts
            if age > self.stale_after_s:
                # Input stale — retorna None para a engine aplicar fallback
                return self.fallback_input

        self._last_entry = entry
        self._last_input = entry.car_input
        return entry.car_input

    @property
    def last_entry(self) -> Any:
        """Último :class:`InputEntry` lido (com timestamp e source)."""
        return self._last_entry

    @property
    def last_input(self) -> Optional[CarInput]:
        return self._last_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _angle_diff(a: float, b: float) -> float:
    """Diferença angular normalizada para [-pi, pi]."""
    d = a - b
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return d


__all__ = [
    "CarInput",
    "EnvironmentState",
    "CarController",
    "ManualController",
    "ExternalController",
    "InputSourceController",
]
