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

import json
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import redis

from .controllers import CarController, CarInput, EnvironmentState
from .events import AiCommandEvent, AiSuggestionEvent, OffTrackEvent, OnTrackEvent

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
    ts: float = 0.0  # Unix timestamp

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoachCommand":
        return cls(**data)


class CommandBus:
    """Bus de comandos por piloto.

    Implementação baseada em Redis para persistência e suporte a múltiplas
    instâncias do backend (HA). Cada corrida tem seu próprio namespace.
    """

    def __init__(self, client: redis.Redis, race_id: str, ttl: int = 86400) -> None:
        self.client = client
        self.race_id = race_id
        self.ttl = ttl
        self._seq = 0
        self._seq_lock = threading.Lock()

    def _key(self, driver_id: str) -> str:
        return f"race:{self.race_id}:coach:{driver_id}"

    def _seq_key(self) -> str:
        return f"race:{self.race_id}:coach:seq"

    def push(
        self,
        driver_id: str,
        command: str,
        value: float = 0.0,
        reason: str = "",
        issued_by: str = "ai",
    ) -> CoachCommand:
        with self._seq_lock:
            # A sequência pertence à corrida, mesmo entre processos e após recovery.
            local_seq = int(self.client.eval(
                "local n = math.max(tonumber(redis.call('get', KEYS[1]) or '0'), tonumber(ARGV[1])) + 1; "
                "redis.call('set', KEYS[1], n, 'EX', ARGV[2]); return n",
                1, self._seq_key(), self._seq, self.ttl,
            ))
            self._seq = local_seq

        cmd = CoachCommand(
            command=normalize_command(command),
            value=float(value or 0.0),
            reason=str(reason or ""),
            issued_by=str(issued_by or "ai"),
            seq=local_seq,
            ts=time.time(),
        )
        self.client.setex(self._key(driver_id), self.ttl, json.dumps(cmd.to_dict()))
        return cmd

    def latest(self, driver_id: str) -> Optional[CoachCommand]:
        data = self.client.get(self._key(driver_id))
        if not data:
            return None
        try:
            return CoachCommand.from_dict(json.loads(data))
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def clear(self, driver_id: str) -> None:
        self.client.delete(self._key(driver_id))


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
            # Também publica sugestão textual para o HUD
            suggestion_text = self._suggestion_text(cmd)
            if suggestion_text:
                self.publisher.publish(AiSuggestionEvent(
                    sim_ts=float(env.sim_ts),
                    driver_id=self.driver_id,
                    driver_name=str(getattr(driver_state, "name", "")),
                    lap=int(getattr(driver_state, "lap", 0)),
                    aviso=suggestion_text,
                    urgencia=self._suggestion_urgency(cmd),
                    comando={"tipo": cmd.command, "valor": float(cmd.value), "motivo": cmd.reason} if cmd.command != "neutral" else None,
                    fallback=False,
                ))

    def _suggestion_text(self, cmd: CoachCommand) -> str:
        """Gera texto da sugestão baseada no comando."""
        if cmd.command == "push":
            return f"Vamos atacar! {cmd.reason or 'Aumentando ritmo.'}"
        if cmd.command == "overtake":
            return f"Hora da ultrapassagem! {cmd.reason or 'Modo ataque ativado.'}"
        if cmd.command == "conserve":
            return f"Economizando. {cmd.reason or 'Gerenciando pneus/combustível.'}"
        if cmd.command == "defend":
            return f"Defenda a posição! {cmd.reason or 'Protegendo a linha interna.'}"
        if cmd.command == "careful":
            return f"Cuidado! {cmd.reason or 'Condições difíceis, mais margem.'}"
        if cmd.command == "pace":
            return f"Ajuste de ritmo: {cmd.value:.0%}. {cmd.reason or ''}"
        if cmd.command == "neutral" and cmd.reason:
            return cmd.reason
        return ""

    def _suggestion_urgency(self, cmd: CoachCommand) -> str:
        """Define urgência baseada no comando."""
        if cmd.command in ("push", "overtake", "careful"):
            return "alta"
        if cmd.command in ("conserve", "defend", "pace"):
            return "media"
        return "baixa"

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
