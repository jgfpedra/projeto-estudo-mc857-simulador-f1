"""Engenheiro de pista (IA) aplicando comandos de alto nível ao carro.

O ``CoachController`` **envolve** qualquer :class:`CarController` sem alterar o
controlador original. A cada tick ele:

1. pergunta o input base ao controlador (por exemplo o ``apex-rules``);
2. lê o último comando de alto nível publicado para o piloto;
3. aplica o comando no input (pace, pneu, cuidado, defesa...);
4. publica ``ai_command`` quando um comando novo é aplicado;
5. detecta transições de saída/retorno de pista e publica
   ``off_track`` / ``on_track``.

A alteração de comportamento já fica no input do carro; o evento é o "porquê"
que o HUD do viz3d mostra. Tudo continua dentro do backend: o visualizador só
consome os eventos.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .controllers import CarController, CarInput, EnvironmentState
from .events import AiCommandEvent, OffTrackEvent, OnTrackEvent

# Aliases aceitos vindos do LLM ou de um endpoint humano.
_COMMAND_ALIASES = {
    "attack": "push",
    "atacar": "push",
    "push": "push",
    "conserve": "conserve",
    "economizar": "conserve",
    "fuel_save": "conserve",
    "save": "conserve",
    "careful": "careful",
    "cuidado": "careful",
    "defend": "defend",
    "defender": "defend",
    "overtake": "overtake",
    "ultrapassar": "overtake",
    "neutral": "neutral",
    "clear": "neutral",
    "none": "neutral",
}


def normalize_command(command: str) -> str:
    """Mapeia sinônimos (pt/en) para o verbo canônico do coach."""
    return _COMMAND_ALIASES.get(str(command or "").strip().lower(), "neutral")


@dataclass
class CoachCommand:
    """Um comando de alto nível aguardando aplicação."""

    command: str = "neutral"
    value: float = 0.0
    reason: str = ""
    issued_by: str = "ai"
    seq: int = 0


class CommandBus:
    """Último comando por piloto, seguro entre a thread da API e a do motor."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._commands: Dict[str, CoachCommand] = {}
        self._seq = 0

    def push(
        self,
        driver_id: str,
        command: str,
        value: float = 0.0,
        reason: str = "",
        issued_by: str = "ai",
    ) -> CoachCommand:
        with self._lock:
            self._seq += 1
            cmd = CoachCommand(
                command=normalize_command(command),
                value=float(value or 0.0),
                reason=str(reason or ""),
                issued_by=str(issued_by or "ai"),
                seq=self._seq,
            )
            self._commands[driver_id] = cmd
            return cmd

    def latest(self, driver_id: str) -> Optional[CoachCommand]:
        with self._lock:
            cmd = self._commands.get(driver_id)
            if cmd is None:
                return None
            # Copia: a thread do motor não pode ler um objeto mutado depois.
            return CoachCommand(cmd.command, cmd.value, cmd.reason, cmd.issued_by, cmd.seq)


class CoachController(CarController):
    """Aplica comandos do engenheiro sobre um controlador existente."""

    OFFTRACK_DISTANCE_MARGIN_M = 0.8

    def __init__(
        self,
        base: CarController,
        driver_id: str,
        publisher: Any = None,
        bus: Optional[CommandBus] = None,
        off_track_margin_m: float = OFFTRACK_DISTANCE_MARGIN_M,
    ) -> None:
        self.base = base
        self.driver_id = driver_id
        self.publisher = publisher
        self.bus = bus
        self.off_track_margin_m = max(0.0, float(off_track_margin_m))

        self._last_seq = -1
        self._last_command = "neutral"
        self._off_track = False
        self._off_since_s = 0.0

    # ------------------------------------------------------------------
    # CarController
    # ------------------------------------------------------------------
    def compute_input(self, env: EnvironmentState, driver_state: Any) -> CarInput:
        car_input = self.base.compute_input(env, driver_state)
        if car_input is None:
            return car_input

        self._publish_track_status(env, driver_state)
        self._apply_command(env, driver_state, car_input)
        return car_input

    def reset(self) -> None:
        reset = getattr(self.base, "reset", None)
        if callable(reset):
            reset()
        self._last_seq = -1
        self._last_command = "neutral"
        self._off_track = False
        self._off_since_s = 0.0

    # ------------------------------------------------------------------
    # Comandos de alto nível
    # ------------------------------------------------------------------
    def _apply_command(self, env: EnvironmentState, driver_state: Any,
                       car_input: CarInput) -> None:
        if self.bus is None:
            return
        cmd = self.bus.latest(self.driver_id)
        if cmd is None or cmd.seq == self._last_seq:
            return
        self._last_seq = cmd.seq
        self._last_command = cmd.command

        multiplier = self._throttle_multiplier(cmd)
        if multiplier != 1.0:
            throttle = car_input.throttle
            if throttle is not None:
                car_input.throttle = max(0.0, min(1.0, float(throttle) * multiplier))
        if cmd.command == "careful":
            car_input.brake = max(float(car_input.brake or 0.0), 0.05)

        if self.publisher is not None:
            self.publisher.publish(AiCommandEvent(
                sim_ts=float(env.sim_ts),
                driver_id=self.driver_id,
                driver_name=str(getattr(driver_state, "name", "")),
                lap=int(getattr(driver_state, "lap", 0)),
                command=cmd.command,
                value=float(cmd.value),
                reason=cmd.reason,
                issued_by=cmd.issued_by,
            ))

    @staticmethod
    def _throttle_multiplier(cmd: CoachCommand) -> float:
        if cmd.command == "push":
            return 1.10
        if cmd.command == "overtake":
            return 1.08
        if cmd.command == "conserve":
            return 0.90
        if cmd.command == "defend":
            return 0.97
        if cmd.command == "careful":
            return 0.82
        if cmd.command == "pace":
            value = float(cmd.value or 1.0)
            return max(0.5, min(1.15, value))
        return 1.0

    # ------------------------------------------------------------------
    # Saída / retorno de pista
    # ------------------------------------------------------------------
    def _publish_track_status(self, env: EnvironmentState, driver_state: Any) -> None:
        project = getattr(self.base, "_project", None)
        half_width = getattr(self.base, "_half_width", None)
        if project is None or half_width is None or self.publisher is None:
            return

        x = float(getattr(driver_state, "position_x", 0.0))
        y = float(getattr(driver_state, "position_y", 0.0))
        try:
            _, signed_lat = project(self.driver_id, x, y)
        except Exception:
            return

        lat = abs(float(signed_lat))
        off = lat > float(half_width) + self.off_track_margin_m
        sim_ts = float(env.sim_ts)

        if off and not self._off_track:
            self._off_since_s = sim_ts
            excess = max(0.0, lat - float(half_width))
            self.publisher.publish(OffTrackEvent(
                sim_ts=sim_ts,
                driver_id=self.driver_id,
                driver_name=str(getattr(driver_state, "name", "")),
                lap=int(getattr(driver_state, "lap", 0)),
                side="esquerda" if signed_lat > 0 else "direita",
                distance_m=round(excess, 2),
                speed_mps=round(float(getattr(driver_state, "velocity_mps", 0.0)), 2),
                severity="grave" if excess > 3.0 else "leve",
            ))
        elif not off and self._off_track:
            self.publisher.publish(OnTrackEvent(
                sim_ts=sim_ts,
                driver_id=self.driver_id,
                driver_name=str(getattr(driver_state, "name", "")),
                lap=int(getattr(driver_state, "lap", 0)),
                duration_s=round(sim_ts - self._off_since_s, 2),
            ))

        self._off_track = off
