"""Simple deterministic pit decisions, independent of the driving controller."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from domain import TYRE_CATALOG, TyreCompound, WeatherKind

SLICKS = frozenset((TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD))


@dataclass(frozen=True)
class PitDecision:
    compound: TyreCompound
    fuel_kg: float
    reason: str


def preferred_compound(weather, laps_left: float) -> TyreCompound:
    if weather.kind == WeatherKind.DAMP:
        return TyreCompound.INTERMEDIATE
    if weather.kind == WeatherKind.WET:
        return TyreCompound.WET if weather.rainfall >= 1.5 else TyreCompound.INTERMEDIATE
    if laps_left <= 6:
        return TyreCompound.SOFT
    if laps_left <= 13:
        return TyreCompound.MEDIUM
    return TyreCompound.HARD


def decide_pit(state, driver, weather, track_length_km: float, laps_left: float,
               fuel_threshold_kg: float, tyre_threshold_pct: float,
               strategy_seed: int = 0, race_laps: int | None = None) -> PitDecision | None:
    """Use predicted next-lap wear/fuel and substantial weather mismatches.

    ``laps_left`` is distance to the scheduled finish in laps, not an integer
    stint count. The strategy deliberately avoids a stop on the final lap
    unless there is a serious grip or fuel problem.
    """
    laps_left = max(0.0, laps_left)
    if laps_left <= 0.05:
        return None
    current = state.tyre.model.compound
    target = preferred_compound(weather, laps_left)
    rainy = weather.kind in (WeatherKind.DAMP, WeatherKind.WET)
    weather_mismatch = (rainy and current in SLICKS) or (not rainy and current not in SLICKS)
    # A change from WET to INTERMEDIATE (or vice versa) is worthwhile only
    # with enough race remaining to pay for the physical pit passage.
    if rainy and current not in SLICKS and current != target and laps_left >= 4:
        weather_mismatch = True
    grip = weather.grip_factor
    wear_factor = (1.0 + max(0.0, 1.0-grip)*2.0 if current in SLICKS
                   else 1.0 + max(0.0, 1.0-grip)*1.5)
    per_lap_wear = state.tyre.model.life_decay_per_lap * wear_factor * (track_length_km/4.5) * driver.aggressive
    per_lap_fuel = state.car.consume_fuel_per_lap(track_length_km, driver.aggressive)
    horizon = min(laps_left, 1.25)
    projected_life = state.tyre.tyre_life - per_lap_wear*horizon
    projected_fuel = state.car.fuel_kg - per_lap_fuel*horizon
    fuel_emergency = state.car.fuel_kg < per_lap_fuel * min(laps_left, 1.0)
    tyre_emergency = state.tyre.tyre_life <= 5.0
    if laps_left <= 1.0 and not (weather_mismatch or fuel_emergency or tyre_emergency):
        return None
    digest = hashlib.sha256(f"{strategy_seed}//pit//{driver.driver_id}".encode()).digest()
    # In longer dry races, bots plan one tyre change at different times. This
    # follows the two-compound idea without prescribing the user's strategy.
    planned_lap = (max(1.5, race_laps * (0.33 + 0.07 * (digest[1] % 5)))
                   if race_laps is not None and race_laps >= 7 else None)
    strategy_stop = (planned_lap is not None and not rainy
                     and state.pit_stop_done == 0 and laps_left > 1.25
                     and race_laps - laps_left >= planned_lap)
    if weather_mismatch:
        reason = 'weather'
    elif tyre_emergency or (laps_left > 1.0 and projected_life <= tyre_threshold_pct):
        reason = 'tyres'
    elif fuel_emergency or (laps_left > 1.0 and projected_fuel <= fuel_threshold_kg):
        reason = 'fuel'
    elif strategy_stop:
        reason = 'strategy'
    else:
        return None
    if not rainy and target == TyreCompound.MEDIUM and laps_left >= 7.0:
        # Independent deterministic plans create undercuts/overcuts without
        # compromising mandatory wet-weather choices. Only use a soft if its
        # projected remaining life leaves a reserve at the finish.
        plan = digest[0] % 3
        soft_wear = (TYRE_CATALOG[TyreCompound.SOFT].life_decay_per_lap
                     * (1.0 + max(0.0, 1.0 - grip) * 2.0)
                     * (track_length_km / 4.5) * driver.aggressive)
        if plan == 0 and 100.0 - soft_wear * laps_left >= max(20.0, tyre_threshold_pct + 5.0):
            target = TyreCompound.SOFT
        elif plan == 2:
            target = TyreCompound.HARD
    if (not rainy and race_laps is not None and race_laps >= 7
            and state.pit_stop_done == 0 and target == current):
        # A first stop also serves the planned dry-compound change, including
        # when low fuel or worn tyres brought the stop forward.
        if current == TyreCompound.SOFT:
            target = TyreCompound.MEDIUM
        elif current == TyreCompound.MEDIUM:
            soft_wear = (TYRE_CATALOG[TyreCompound.SOFT].life_decay_per_lap
                         * (1.0 + max(0.0, 1.0 - grip) * 2.0)
                         * (track_length_km / 4.5) * driver.aggressive)
            target = (TyreCompound.SOFT if 100.0 - soft_wear * laps_left
                      >= max(20.0, tyre_threshold_pct + 5.0) else TyreCompound.HARD)
        else:
            target = TyreCompound.MEDIUM
    needed_fuel = max(0.0, per_lap_fuel*laps_left*1.1 + 1.0 - state.car.fuel_kg)
    fuel = min(max(0.0, state.car.specs.fuel_capacity_kg - state.car.fuel_kg), needed_fuel)
    return PitDecision(target, fuel, reason)
