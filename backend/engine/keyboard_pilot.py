"""KeyboardPilot — estado entre ticks do controle por teclado da janela GUI.

Mapeia os eventos de ``p.getKeyboardEvents()`` para um :class:`CarInput`,
mantendo estado entre ticks: teclas pressionadas, velocidade-alvo e ângulo
de steering. A lógica é pura (não importa PyBullet) para ser testável
headless.

Semântica dos eventos PyBullet 3.x (retornados a cada poll):

- ``KEY_IS_DOWN`` (1)      — tecla segue pressionada (reportada em todo poll)
- ``KEY_WAS_TRIGGERED`` (2) — tecla acabou de ser pressionada neste poll
- ``KEY_WAS_RELEASED`` (4)  — tecla foi solta neste poll

Teclas pressionadas são reportadas a cada poll; se ficarem ausentes por
``missed_polls_to_release`` polls seguidos (janela sem foco, release
perdido), são tratadas como soltas para o volante/pedal não "travar".

Comportamento do controle:

- ``W``/↑ mantido   — acelera o target a ``accel_rate_mps2``
- ``S``/↓ mantido   — reduz o target mais forte (freio)
- soltou tudo       — decai naturalmente (``coast_rate_mps2``), sem freio fantasma
- ``A``/← e ``D``/→ — steering por **taxa** (``steer_rate_rad_s``) por tick
- soltou A/D        — auto-centralização (``center_rate_rad_s``)
- lock de steering  — reduz com a velocidade (``min_steer_frac`` em ``max_speed``)
- espaço            — freio de mão; ``R`` — zera tudo

Convenção de steering: **positivo = esquerda** (igual ao docstring de
:class:`~engine.controllers.CarInput` e a ``scripts/publish_keyboard.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Set

from .controllers import CarInput

KEY_IS_DOWN = 1
KEY_WAS_TRIGGERED = 2
KEY_WAS_RELEASED = 4

ACCEL = "accel"
DECEL = "decel"
LEFT = "left"
RIGHT = "right"
BRAKE = "brake"
RESET = "reset"

# key codes do PyBullet (ASCII para letras/espaço, keysyms X11 para setas)
_KEY_ACTIONS: Dict[int, str] = {
    ord("w"): ACCEL, ord("W"): ACCEL,
    ord("s"): DECEL, ord("S"): DECEL,
    ord("a"): LEFT, ord("A"): LEFT,
    ord("d"): RIGHT, ord("D"): RIGHT,
    ord(" "): BRAKE,
    ord("r"): RESET, ord("R"): RESET,
    65296: LEFT,    # seta esquerda
    65297: ACCEL,   # seta cima
    65298: DECEL,   # seta baixo
    65299: RIGHT,   # seta direita
}


@dataclass
class KeyboardPilotConfig:
    """Parâmetros de tuning do controle por teclado."""

    max_speed_mps: float = 80.0
    accel_rate_mps2: float = 20.0
    decel_rate_mps2: float = 12.0
    coast_rate_mps2: float = 4.0
    steer_rate_rad_s: float = math.radians(50.0)
    center_rate_rad_s: float = math.radians(70.0)
    max_steer_deg: float = 25.0
    min_steer_frac: float = 0.40
    speed_sensitive_ref_mps: float = 30.0
    missed_polls_to_release: int = 3
    max_dt_s: float = 0.25


class KeyboardPilot:
    """Converte eventos de teclado (poll-a-poll) em :class:`CarInput`."""

    def __init__(self, config: Optional[KeyboardPilotConfig] = None) -> None:
        self.config = config or KeyboardPilotConfig()
        self.reset()

    def reset(self) -> None:
        """Zera estado do piloto (teclas, velocidade-alvo e steering)."""
        self._held_keys: Dict[int, int] = {}
        self.speed_mps: float = 0.0
        self.steer_rad: float = 0.0
        self.brake: float = 0.0

    @property
    def held_keys(self) -> Set[int]:
        return set(self._held_keys)

    @property
    def held_actions(self) -> Set[str]:
        return {_KEY_ACTIONS[k] for k in self._held_keys}

    def update(
        self,
        events: Mapping[int, int],
        dt: float,
        speed_mps: Optional[float] = None,
    ) -> CarInput:
        """Avança um tick: assimila eventos, atualiza estado e devolve o input.

        Parameters
        ----------
        events : dict-like
            Saída de ``p.getKeyboardEvents()``: ``{key_code: state}``.
        dt : float
            Duração do tick lógico em segundos.
        speed_mps : float, opcional
            Velocidade real do carro (para o lock de steering ser sensível à
            velocidade verdadeira). Se ausente, usa a velocidade-alvo interna.
        """
        dt = min(max(float(dt), 1e-3), self.config.max_dt_s)
        self._merge_events(events or {})
        actions = self._actions()

        # --- Velocidade-alvo ---
        if RESET in actions:
            self.speed_mps = 0.0
            self.steer_rad = 0.0
            self.brake = 0.0

        if BRAKE in actions:
            self.speed_mps = 0.0
            self.brake = 1.0
        else:
            self.brake = 0.0
            # Freio tem prioridade sobre o acelerador (se as duas teclas
            # estiverem "seguradas" ao mesmo tempo, desacelera).
            if DECEL in actions:
                self.speed_mps = max(
                    0.0, self.speed_mps - self.config.decel_rate_mps2 * dt
                )
            elif ACCEL in actions:
                self.speed_mps = min(
                    self.config.max_speed_mps,
                    self.speed_mps + self.config.accel_rate_mps2 * dt,
                )
            else:
                self.speed_mps = max(
                    0.0, self.speed_mps - self.config.coast_rate_mps2 * dt
                )

        # --- Steering (taxa por tick + auto-centralização) ---
        actual_speed = speed_mps if speed_mps is not None else self.speed_mps
        limit = self._steer_limit(actual_speed)
        if (LEFT in actions) != (RIGHT in actions):
            delta = self.config.steer_rate_rad_s * dt
            self.steer_rad += delta if LEFT in actions else -delta
        else:
            center = self.config.center_rate_rad_s * dt
            if abs(self.steer_rad) <= center:
                self.steer_rad = 0.0
            else:
                self.steer_rad -= math.copysign(center, self.steer_rad)
        # Lock pode ter encolhido por causa da velocidade: respeita o novo limite
        self.steer_rad = max(-limit, min(limit, self.steer_rad))

        return CarInput(
            target_speed_mps=self.speed_mps,
            steering_yaw_rad=self.steer_rad,
            brake=self.brake,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _merge_events(self, events: Mapping[int, int]) -> None:
        """Atualiza o conjunto de teclas pressionadas a partir do poll."""
        seen: Set[int] = set()
        for key, state in events.items():
            key = int(key)
            if key not in _KEY_ACTIONS:
                continue
            down = bool(state & (KEY_IS_DOWN | KEY_WAS_TRIGGERED))
            released = bool(state & KEY_WAS_RELEASED)
            if released and not down:
                self._held_keys.pop(key, None)
                continue
            if down:
                self._held_keys[key] = 0
                seen.add(key)

        # Tecla mantida é reportada a cada poll; ausência prolongada = solta
        # (protege contra release perdido quando a janela perde o foco).
        for key in list(self._held_keys):
            if key in seen:
                continue
            self._held_keys[key] += 1
            if self._held_keys[key] > self.config.missed_polls_to_release:
                del self._held_keys[key]

    def _actions(self) -> Set[str]:
        return {_KEY_ACTIONS[k] for k in self._held_keys}

    def _steer_limit(self, speed_mps: float) -> float:
        """Lock máximo do volante: cheio até ``speed_sensitive_ref_mps`` e
        decrescendo linearmente até ``min_steer_frac`` em ``max_speed_mps``."""
        cfg = self.config
        full = math.radians(cfg.max_steer_deg)
        if speed_mps <= cfg.speed_sensitive_ref_mps:
            return full
        span = max(1.0, cfg.max_speed_mps - cfg.speed_sensitive_ref_mps)
        t = min(1.0, (speed_mps - cfg.speed_sensitive_ref_mps) / span)
        scale = 1.0 - t * (1.0 - cfg.min_steer_frac)
        return full * scale


__all__ = ["KeyboardPilot", "KeyboardPilotConfig", "KEY_IS_DOWN",
           "KEY_WAS_TRIGGERED", "KEY_WAS_RELEASED"]
