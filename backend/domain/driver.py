"""Driver domain module.

Agrega carro + pneu + estado de corrida para um piloto individual.
Mantém posição na pista, volta atual, setor atual, tempo total, tempo de volta,
e flags de pit stop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .car import CarSpecs, CarState
from .tyre import TyreCompound, TyreModel, TyreState, TYRE_CATALOG
import math

@dataclass
class DriverState:
    """Estado runtime de um piloto durante a corrida.

    Mantém informação tanto do ponto de vista da lógica de negócio (volta,
    setor, tempo) quanto do ponto de vista do mundo físico (posição x,y,
    velocidade, ângulo de steering, etc. — preenchido pelo Engine).
    """

    driver_id: str
    name: str
    car: CarState
    tyre: TyreState

    # Estado de corrida
    lap: int = 0                 # volta atual
    sector: int = 1
    last_lap_time_s: float = 0.0
    best_lap_time_s: float = float("inf")
    total_time_s: float = 0.0
    lap_times: List[float] = field(default_factory=list)
    sector_times: List[float] = field(default_factory=list)  # tempos do setor atual
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_mps: float = 0.0
    heading_rad: float = 0.0

    # Estado de pit
    pitting: bool = False
    pit_stop_done: int = 0
    pit_penalty_pending_s: float = 0.0  # tempo perdido no pit (a ser descontado do pace)

    # Telemetria de pneu usada para decisão de pit
    def needs_pit(self, fuel_threshold_kg: float = 5.0, tyre_life_threshold: float = 15.0) -> bool:
        """Decide se o piloto precisa ir aos boxes.

        Critério simples: combustível abaixo do threshold OU vida de pneu
        abaixo do threshold.
        """
        if self.car.fuel_kg <= fuel_threshold_kg:
            return True
        if self.tyre.tyre_life <= tyre_life_threshold:
            return True
        return False

    def perform_pit_stop(
        self,
        new_compound: TyreCompound,
        fuel_to_add_kg: float,
        pit_time_s: float,
    ) -> None:
        """Executa um pit stop: troca pneus + reabastece."""
        added = self.car.refuel(fuel_to_add_kg)
        self.tyre = TyreState(model=TYRE_CATALOG[new_compound], age_laps=0.0, tyre_life=100.0, fresh=True)
        self.pit_penalty_pending_s = pit_time_s
        self.pit_stop_done += 1
        self.pitting = False

    def to_dict(self) -> dict:
        return {
            "driver_id": self.driver_id,
            "name": self.name,
            "lap": self.lap,
            "sector": self.sector,
            "position": [round(self.position_x, 2), round(self.position_y, 2)],
            "velocity_mps": round(self.velocity_mps, 2),
            "heading_deg": round(math.degrees(self.heading_rad), 1),
            "last_lap_time_s": round(self.last_lap_time_s, 3),
            "best_lap_time_s": round(self.best_lap_time_s, 3) if self.best_lap_time_s != float("inf") else None,
            "total_time_s": round(self.total_time_s, 3),
            "fuel_kg": round(self.car.fuel_kg, 2),
            "tyre": self.tyre.to_dict(),
            "pitting": self.pitting,
            "pit_stops": self.pit_stop_done,
            "pit_penalty_pending_s": round(self.pit_penalty_pending_s, 2),
        }


@dataclass
class Driver:
    """Configuração estática de um piloto + seu carro inicial."""

    driver_id: str
    name: str
    car_specs: CarSpecs
    starting_tyre_compound: TyreCompound = TyreCompound.MEDIUM
    starting_fuel_pct: float = 1.0
    aggressive: float = 1.0

    def initial_state(self) -> DriverState:
        car = CarState.from_specs(self.car_specs, self.starting_fuel_pct)
        tyre = TyreState(
            model=TYRE_CATALOG[self.starting_tyre_compound],
            age_laps=0.0,
            tyre_life=100.0,
            fresh=True,
        )
        return DriverState(
            driver_id=self.driver_id,
            name=self.name,
            car=car,
            tyre=tyre,
        )
