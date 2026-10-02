"""Weather domain module.

Modela condições climáticas (seco, nublado, chuva), transições probabilísticas
ao longo da corrida e o impacto no grip por composto de pneu.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class WeatherKind(str, Enum):
    """Condições climáticas macro."""

    DRY = "DRY"
    CLOUDY = "CLOUDY"
    DAMP = "DAMP"          # pista úmida, sem chuva ativa
    WET = "WET"            # chuva ativa, pista molhada


@dataclass(frozen=True)
class WeatherState:
    """Snapshot imutável de uma condição climática.

    Atributos seguem a nomenclatura usada em telemetria oficial de F1:
    ``AirTemp``, ``TrackTemp``, ``Rainfall`` (mm/h), ``Humidity`` (%).
    """

    kind: WeatherKind
    air_temp: float       # AirTemp (°C)
    track_temp: float     # TrackTemp (°C)
    rainfall: float       # Rainfall (mm/h)
    humidity: float       # Humidity (%)

    @property
    def grip_factor(self) -> float:
        """Multiplicador genérico de grip imposto pelo clima (0..1+).

        Usado como entrada para o cálculo de degradação do pneu (pneus secos
        em pista com baixo grip desgastam mais).
        """
        if self.kind == WeatherKind.DRY:
            return 1.00
        if self.kind == WeatherKind.CLOUDY:
            return 0.98
        if self.kind == WeatherKind.DAMP:
            return 0.75
        # WET
        # Quanto maior o rainfall, menor o grip geral.
        return max(0.45, 0.85 - 0.05 * self.rainfall)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "air_temp": round(self.air_temp, 1),
            "track_temp": round(self.track_temp, 1),
            "rainfall": round(self.rainfall, 2),
            "humidity": round(self.humidity, 1),
            "grip_factor": round(self.grip_factor, 3),
        }


# Catálogo de condições base (valores típicos)
BASE_CONDITIONS: Dict[WeatherKind, WeatherState] = {
    WeatherKind.DRY: WeatherState(
        kind=WeatherKind.DRY,
        air_temp=24.0,
        track_temp=42.0,
        rainfall=0.0,
        humidity=45.0,
    ),
    WeatherKind.CLOUDY: WeatherState(
        kind=WeatherKind.CLOUDY,
        air_temp=21.0,
        track_temp=35.0,
        rainfall=0.0,
        humidity=60.0,
    ),
    WeatherKind.DAMP: WeatherState(
        kind=WeatherKind.DAMP,
        air_temp=18.0,
        track_temp=24.0,
        rainfall=0.0,
        humidity=80.0,
    ),
    WeatherKind.WET: WeatherState(
        kind=WeatherKind.WET,
        air_temp=17.0,
        track_temp=19.0,
        rainfall=2.5,
        humidity=92.0,
    ),
}


@dataclass
class WeatherTransitionConfig:
    """Configuração das transições de clima.

    ``transition_matrix[a][b]`` é a probabilidade de, estando no clima ``a``,
    transitar para ``b`` por volta. As linhas devem somar ~1.0.
    """

    transition_matrix: Dict[WeatherKind, Dict[WeatherKind, float]]
    transition_prob_per_lap: float = 0.05    # chance de avaliar transição por volta

    @classmethod
    def default(cls, transition_prob_per_lap: float = 0.05) -> "WeatherTransitionConfig":
        """Matriz de transição conservadora: tende a permanecer no estado atual."""
        return cls(
            transition_matrix={
                WeatherKind.DRY: {
                    WeatherKind.DRY: 0.75,
                    WeatherKind.CLOUDY: 0.20,
                    WeatherKind.DAMP: 0.04,
                    WeatherKind.WET: 0.01,
                },
                WeatherKind.CLOUDY: {
                    WeatherKind.DRY: 0.25,
                    WeatherKind.CLOUDY: 0.55,
                    WeatherKind.DAMP: 0.15,
                    WeatherKind.WET: 0.05,
                },
                WeatherKind.DAMP: {
                    WeatherKind.DRY: 0.15,
                    WeatherKind.CLOUDY: 0.25,
                    WeatherKind.DAMP: 0.35,
                    WeatherKind.WET: 0.25,
                },
                WeatherKind.WET: {
                    WeatherKind.DRY: 0.05,
                    WeatherKind.CLOUDY: 0.20,
                    WeatherKind.DAMP: 0.35,
                    WeatherKind.WET: 0.40,
                },
            },
            transition_prob_per_lap=transition_prob_per_lap,
        )


class WeatherModel:
    """Máquina de estados do clima ao longo da corrida.

    Mantém o estado atual, expõe ``step(lap)`` que avalia (com probabilidade
    configurável) uma transição, e devolve o novo ``WeatherState``.
    """

    def __init__(
        self,
        initial: WeatherState,
        config: Optional[WeatherTransitionConfig] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.current = initial
        self.config = config or WeatherTransitionConfig.default()
        self.rng = rng or random.Random()
        # histórico de transições (lap, from, to)
        self.history: list[tuple[int, WeatherKind, WeatherKind]] = []

    def step(self, lap: int) -> WeatherState:
        """Avalia transição no início da volta. Retorna o estado vigente."""
        if self.rng.random() > self.config.transition_prob_per_lap:
            return self.current

        current_kind = self.current.kind
        transitions = self.config.transition_matrix.get(current_kind, {})
        if not transitions:
            return self.current

        # amostra o próximo estado
        r = self.rng.random()
        cumulative = 0.0
        next_kind = current_kind
        for kind, prob in transitions.items():
            cumulative += prob
            if r <= cumulative:
                next_kind = kind
                break

        if next_kind != current_kind:
            self.history.append((lap, current_kind, next_kind))
            # adiciona pequena variação nas temperaturas ao redor do baseline
            base = BASE_CONDITIONS[next_kind]
            jitter = lambda v: v + self.rng.uniform(-1.5, 1.5)
            self.current = WeatherState(
                kind=base.kind,
                air_temp=jitter(base.air_temp),
                track_temp=jitter(base.track_temp),
                rainfall=max(0.0, base.rainfall + self.rng.uniform(-0.3, 0.3)),
                humidity=max(0.0, min(100.0, jitter(base.humidity))),
            )
        return self.current

    def to_dict(self) -> dict:
        return self.current.to_dict()
