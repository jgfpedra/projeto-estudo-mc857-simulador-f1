"""Tyre domain module.

Modela compostos de pneu (HARD, MEDIUM, SOFT, WET, INTERMEDIATE), suas curvas de
degradação e o impacto no tempo de volta.

A lógica é pura: dado um ``TyreState`` e uma condição climática, é possível calcular
o multiplicador de grip e a penalidade de tempo por volta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class TyreCompound(str, Enum):
    """Compostos de pneu suportados."""

    HARD = "HARD"
    MEDIUM = "MEDIUM"
    SOFT = "SOFT"
    WET = "WET"
    INTERMEDIATE = "INTERMEDIATE"


@dataclass(frozen=True)
class TyreModel:
    """Modelo estático de um composto de pneu.

    Atributos
    ---------
    compound : TyreCompound
        Identificador do composto.
    base_pace : float
        Diferença de pace (em segundos por volta) em relação ao composto de
        referência (HARD). Negativo = mais rápido.
    degradation_per_lap : float
        Penalidade de tempo (segundos) adicionada por volta de uso, na fase
        linear da curva de degradação.
    knee_lap : int
        Volta a partir da qual a degradação acelera (joelho da curva).
    knee_steepness : float
        Fator de aceleração da degradação após o joelho. ``1.0`` = linear.
    grip_dry : float
        Multiplicador de grip em pista seca (1.0 = referência).
    grip_wet : float
        Multiplicador de grip em pista molhada.
    grip_damp : float
        Multiplicador de grip em pista úmida (intermediária).
    optimal_track_temp : float
        Temperatura de pista ideal (°C) para este composto.
    temp_sensitivity : float
        Quanto o grip cai por °C de desvio da temperatura ideal.
    life_decay_per_lap : float
        Quantos pontos percentuais de TyreLife são consumidos por volta.
    """

    compound: TyreCompound
    base_pace: float
    degradation_per_lap: float
    knee_lap: int
    knee_steepness: float
    grip_dry: float
    grip_wet: float
    grip_damp: float
    optimal_track_temp: float
    temp_sensitivity: float
    life_decay_per_lap: float

    def __repr__(self) -> str:
        return f"TyreModel({self.compound.value})"


# Catálogo de compostos. Valores calibrados para uma volta de ~90s em circuito
# de ~4.5km. Não são valores oficiais — são razoáveis para uma simulação.
TYRE_CATALOG: Dict[TyreCompound, TyreModel] = {
    TyreCompound.HARD: TyreModel(
        compound=TyreCompound.HARD,
        base_pace=0.0,                # referência
        degradation_per_lap=0.05,     # degrada devagar
        knee_lap=25,
        knee_steepness=1.6,
        grip_dry=1.00,
        grip_wet=0.35,                # pneu seco em pista molhada é ruim
        grip_damp=0.55,
        optimal_track_temp=95.0,
        temp_sensitivity=0.004,
        life_decay_per_lap=4.0,
    ),
    TyreCompound.MEDIUM: TyreModel(
        compound=TyreCompound.MEDIUM,
        base_pace=-0.4,               # ~0.4s mais rápido que HARD
        degradation_per_lap=0.09,
        knee_lap=18,
        knee_steepness=1.8,
        grip_dry=1.02,
        grip_wet=0.38,
        grip_damp=0.58,
        optimal_track_temp=85.0,
        temp_sensitivity=0.005,
        life_decay_per_lap=5.5,
    ),
    TyreCompound.SOFT: TyreModel(
        compound=TyreCompound.SOFT,
        base_pace=-0.8,                # ~0.8s mais rápido que HARD
        degradation_per_lap=0.16,
        knee_lap=12,
        knee_steepness=2.1,
        grip_dry=1.05,
        grip_wet=0.42,
        grip_damp=0.60,
        optimal_track_temp=75.0,
        temp_sensitivity=0.006,
        life_decay_per_lap=7.5,
    ),
    TyreCompound.INTERMEDIATE: TyreModel(
        compound=TyreCompound.INTERMEDIATE,
        base_pace=1.2,                # mais lento que SOFT em seco
        degradation_per_lap=0.10,
        knee_lap=20,
        knee_steepness=1.7,
        grip_dry=0.85,
        grip_wet=0.75,
        grip_damp=0.95,               # ótimo em úmido
        optimal_track_temp=55.0,
        temp_sensitivity=0.003,
        life_decay_per_lap=6.0,
    ),
    TyreCompound.WET: TyreModel(
        compound=TyreCompound.WET,
        base_pace=3.5,                # bem mais lento em seco
        degradation_per_lap=0.08,
        knee_lap=25,
        knee_steepness=1.5,
        grip_dry=0.65,
        grip_wet=0.95,               # ótimo em molhado
        grip_damp=0.85,
        optimal_track_temp=40.0,
        temp_sensitivity=0.002,
        life_decay_per_lap=4.5,
    ),
}


@dataclass
class TyreState:
    """Estado runtime de um jogo de pneus montado no carro.

    Atributos
    ---------
    model : TyreModel
        Modelo do composto instalado.
    age_laps : float
        Idade do pneu em voltas completas (fracionário para ticks parciais).
    tyre_life : float
        Vida restante em %, de 0 a 100.
    fresh : bool
        ``True`` até a primeira volta ser completada (espelha o ``FreshTyre``
        da telemetria real).
    """

    model: TyreModel
    age_laps: float = 0.0
    tyre_life: float = 100.0
    fresh: bool = True

    # --- aplicação de uma volta -------------------------------------------

    def apply_lap(
        self,
        track_length_km: float,
        weather_grip_factor: float,
        aggressive: float = 1.0,
    ) -> float:
        """Aplica uma volta de uso ao pneu.

        Parâmetros
        ----------
        track_length_km : float
            Comprimento da pista em km (usado para normalizar o consumo).
        weather_grip_factor : float
            Multiplicador de grip imposto pelo clima (0..1+). Pneus secos em
            pista molhada consomem mais.
        aggressive : float
            Fator de agressividade do piloto (1.0 = nominal).

        Retorna
        -------
        float
            Penalidade de tempo (em segundos) que essa volta sofreu por causa
            do desgaste acumulado.
        """
        # Pneus secos em pista com baixo grip (molhada) desgastam mais rápido.
        compound = self.model.compound
        if compound in (TyreCompound.HARD, TyreCompound.MEDIUM, TyreCompound.SOFT):
            weather_wear_penalty = 1.0 + max(0.0, 1.0 - weather_grip_factor) * 2.0
        else:
            # Intermediates e Wets desgastam mais em pista seca
            dryness = max(0.0, 1.0 - weather_grip_factor) if weather_grip_factor < 1.0 else 0.0
            weather_wear_penalty = 1.0 + dryness * 1.5

        length_factor = track_length_km / 4.5  # normalizado a ~4.5km

        decay = (
            self.model.life_decay_per_lap
            * weather_wear_penalty
            * length_factor
            * aggressive
        )
        self.tyre_life = max(0.0, self.tyre_life - decay)
        self.age_laps += 1.0

        if self.age_laps >= 1.0:
            self.fresh = False

        return self.lap_time_penalty()

    # --- leituras derivadas -----------------------------------------------

    def lap_time_penalty(self) -> float:
        """Penalidade de tempo (s) por volta devido ao desgaste acumulado."""
        m = self.model
        if self.age_laps <= m.knee_lap:
            return self.age_laps * m.degradation_per_lap
        extra = self.age_laps - m.knee_lap
        linear = m.knee_lap * m.degradation_per_lap
        # Crescimento exponencial suave após o joelho.
        accel = m.degradation_per_lap * (m.knee_steepness ** min(extra, 30))
        return linear + extra * accel

    def grip_multiplier(self, weather_kind: "WeatherKind", track_temp_c: float) -> float:
        """Multiplicador de grip considerando clima, temperatura e desgaste."""
        from .weather import WeatherKind  # local import para evitar ciclo

        if weather_kind == WeatherKind.DRY:
            base = self.model.grip_dry
        elif weather_kind == WeatherKind.CLOUDY:
            base = self.model.grip_dry * 0.99
        elif weather_kind == WeatherKind.DAMP:
            base = self.model.grip_damp
        else:  # WET
            base = self.model.grip_wet

        # Quanto mais gasto, menos grip (até -15% no fim da vida).
        wear_factor = 0.85 + 0.15 * (self.tyre_life / 100.0)

        # Desvio de temperatura
        temp_dev = abs(track_temp_c - self.model.optimal_track_temp)
        temp_factor = max(0.5, 1.0 - temp_dev * self.model.temp_sensitivity)

        return base * wear_factor * temp_factor

    def to_dict(self) -> dict:
        return {
            "compound": self.model.compound.value,
            "age_laps": round(self.age_laps, 2),
            "tyre_life_pct": round(self.tyre_life, 1),
            "fresh": self.fresh,
        }
