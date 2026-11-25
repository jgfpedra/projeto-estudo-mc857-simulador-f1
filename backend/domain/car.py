"""Car domain module.

Modela características do carro (potência, massa, capacidade de combustível) e
a lógica de consumo/alívio de peso de combustível ao longo das voltas, com
impacto na velocidade máxima e no pace.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CarSpecs:
    """Especificações estáticas de um carro.

    Atributos
    ---------
    name : str
        Nome amigável do carro (ex.: "Red Car").
    power_kw : float
        Potência do motor em kW (1 kW ≈ 1.36 cv).
    mass_kg : float
        Massa seca do carro (sem combustível e sem piloto) em kg.
    fuel_capacity_kg : float
        Capacidade máxima do tanque em kg (≈ litros para gasolina/E85).
    drag_coeff : float
        Coeficiente de arrasto adimensional (usado em 0.5 * rho * Cd * A * v^2).
    frontal_area_m2 : float
        Área frontal em m².
    wheelbase_m : float
        Distância entre eixos em metros (afeta resposta à direção).
    max_speed_kmh : float
        Velocidade máxima teórica (com tanque cheio, sem upgrade de pneu).
    """

    name: str
    power_kw: float
    mass_kg: float
    fuel_capacity_kg: float
    drag_coeff: float = 0.85
    downforce_coeff: float = 3.2
    frontal_area_m2: float = 1.5
    wheelbase_m: float = 3.4
    max_speed_kmh: float = 330.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "power_kw": self.power_kw,
            "power_hp": round(self.power_kw * 1.35962, 1),
            "mass_kg": self.mass_kg,
            "fuel_capacity_kg": self.fuel_capacity_kg,
            "drag_coeff": self.drag_coeff,
            "downforce_coeff": self.downforce_coeff,
            "frontal_area_m2": self.frontal_area_m2,
            "wheelbase_m": self.wheelbase_m,
            "max_speed_kmh": self.max_speed_kmh,
        }


@dataclass
class CarState:
    """Estado runtime de um carro durante a corrida.

    Acompanha combustível atual, massa total e velocidade máxima derivada.
    """

    specs: CarSpecs
    fuel_kg: float

    @classmethod
    def from_specs(cls, specs: CarSpecs, fuel_pct: float = 1.0) -> "CarState":
        fuel_kg = specs.fuel_capacity_kg * max(0.0, min(1.0, fuel_pct))
        return cls(specs=specs, fuel_kg=fuel_kg)

    @property
    def total_mass(self) -> float:
        """Massa total = massa seca + combustível atual + piloto (75 kg)."""
        return self.specs.mass_kg + self.fuel_kg + 75.0

    @property
    def power_to_weight(self) -> float:
        """Razão potência/massa (kW/kg). Mais alta = melhor aceleração."""
        return self.specs.power_kw / max(1.0, self.total_mass)

    def max_speed_kmh(self) -> float:
        """Velocidade máxima ajustada pelo peso de combustível.

        Carro com tanque cheio atinge velocidade máxima menor. Modelo simples:
        cada 10 kg de combustível acima de zero reduz a velocidade máxima em
        ~0.4 km/h (efeito real observado em corridas de endurance).
        """
        fuel_penalty = (self.fuel_kg / 10.0) * 0.4  # 0.4 km/h por 10 kg
        return max(180.0, self.specs.max_speed_kmh - fuel_penalty)

    def consume_fuel_per_lap(self, track_length_km: float, aggressive: float = 1.0) -> float:
        """Calcula consumo de combustível em kg para uma volta.

        Modelo aproximado: consumo específico de ~0.35 L/km para um F1-like,
        multiplicado pela agressividade do piloto. Considera que potência maior
        implica consumo maior.
        """
        base_consumption_l_per_km = 0.35 * (self.specs.power_kw / 735.0)  # normalizado a 735 kW (~1000 HP)
        liters = base_consumption_l_per_km * track_length_km * aggressive
        # densidade ≈ 0.75 kg/L
        kg = liters * 0.75
        return kg

    def apply_lap(self, track_length_km: float, aggressive: float = 1.0) -> float:
        """Aplica consumo de combustível de uma volta.

        Retorna o tempo (em segundos) de penalidade por peso extra na volta
        seguinte — usado pelo Engine para ajustar pace.
        """
        consumed = self.consume_fuel_per_lap(track_length_km, aggressive)
        consumed = min(consumed, self.fuel_kg)  # nunca negativo
        self.fuel_kg = max(0.0, self.fuel_kg - consumed)
        # Penalidade aproximada: cada 10 kg de combustível = +0.1s por volta
        # (alívio de peso melhora pace). Calculada como diferença antes/depois.
        avg_fuel = consumed / 2.0  # média durante a volta
        return avg_fuel * 0.01  # ~0.1s por 10 kg = 0.01 s/kg

    def refuel(self, kg: float) -> float:
        """Reabastece, devolvendo quanto efetivamente entrou."""
        space = self.specs.fuel_capacity_kg - self.fuel_kg
        added = min(kg, space)
        self.fuel_kg += added
        return added

    def to_dict(self) -> dict:
        return {
            "specs": self.specs.to_dict(),
            "fuel_kg": round(self.fuel_kg, 2),
            "total_mass_kg": round(self.total_mass, 1),
            "max_speed_kmh": round(self.max_speed_kmh(), 1),
            "power_to_weight": round(self.power_to_weight, 4),
        } 