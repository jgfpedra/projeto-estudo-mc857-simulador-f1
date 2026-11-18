"""Rule-based race controller inspired by the Apex Formula AI drivers.

The controller follows the track with pure pursuit, plans speed from the
curvature ahead, leaves room around nearby cars, and adds small seeded driver
differences so a run can be replayed with the same seed.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .controllers import CarController, CarInput, EnvironmentState


@dataclass
class _DriverStyle:
    rng: random.Random
    skill: float
    consistency: float
    start_reaction_s: float = 0.0
    lap: int = -1
    lap_noise: float = 1.0
    mistake_cooldown_s: float = 0.0
    mistake_left_s: float = 0.0
    mistake_throttle_factor: float = 1.0
    form_left_s: float = 0.0
    form_factor: float = 1.0
    form_target: float = 1.0
    avoid_offset_m: float = 0.0
    avoid_target_id: Optional[str] = None
    avoid_side: float = 1.0
    last_sim_ts: Optional[float] = None
    rejoining: bool = False


class RuleBasedRaceController(CarController):
    """Pure-pursuit controller for the ten-car race runner.

    One instance is shared by all cars; racecraft and random state are keyed
    by ``driver_id`` so each car keeps its own style and remains deterministic.
    """

    G = 9.81
    AIR_DENSITY = 1.225
    ROLLING_COEFFICIENT = 0.015
    MAX_ENGINE_BRAKING_MPS2 = 50.0
    MU_NOMINAL = 1.8
    LATERAL_GRIP_FACTOR = 0.58
    MAX_TARGET_ACCEL_MPS2 = 6.0
    INTERLAGOS_LATERAL_GRIP_FACTOR = 0.65
    INTERLAGOS_MAX_TARGET_ACCEL_MPS2 = 10.0
    HAIRPIN_SPEED_CAP_MPS = 6.8
    INTERLAGOS_HAIRPIN_SPEED_CAP_MPS = 7.2
    HAIRPIN_MIN_LOOKAHEAD_M = 3.2
    HAIRPIN_STEER_LIMIT_FACTOR = 1.40
    INTERLAGOS_LINE_FRACTION = 0.5
    INTERLAGOS_GEOMETRY_SHA256 = "24461ba0b6c38983bf589ba0daefab78498d977a014845979324979f7e8223d6"
    REJOIN_SURFACE_GRIP_FLOOR = 0.50
    REJOIN_MAX_STEER_RAD = 0.45
    REJOIN_DEEP_GRASS_MARGIN_M = 4.0
    REJOIN_NEAR_SPEED_MPS = 5.0
    REJOIN_DEEP_SPEED_MPS = 6.0
    REJOIN_ON_TRACK_SPEED_MPS = 4.0
    OVERTAKE_OFFSET_M = 2.9
    FOLLOW_LATERAL_CLEARANCE_M = 2.35
    BRAKING_GRIP_FACTOR = 0.80
    MAX_PLAN_BRAKING_MPS2 = 24.0
    CURVATURE_PEAK_LIMIT = 0.25  # raio mínimo planejado: 4 m
    MIN_SPEED_PLAN_HORIZON_M = 180.0
    MAX_SPEED_PLAN_HORIZON_M = 700.0
    SPEED_PLAN_STEP_M = 3.0

    def __init__(self, track: Any, seed: int = 0) -> None:
        self.track = track
        self.seed = int(seed)
        self._points = np.asarray(track.waypoints, dtype=np.float64)
        if self._points.ndim != 2 or self._points.shape[0] < 3:
            raise ValueError("RuleBasedRaceController precisa de ao menos 3 waypoints")

        self._half_width = max(2.0, float(track.width_m) * 0.5)
        self._a = self._points
        self._ab = np.roll(self._points, -1, axis=0) - self._points
        self._seg_len = np.linalg.norm(self._ab, axis=1)
        if np.any(self._seg_len < 1e-6):
            raise ValueError("A pista contém segmentos de comprimento quase zero")
        self._seg_len_sq = self._seg_len * self._seg_len
        self._seg_s = np.concatenate(([0.0], np.cumsum(self._seg_len[:-1])))
        self._track_len = float(self._seg_len.sum())
        self._heading = np.arctan2(self._ab[:, 1], self._ab[:, 0])

        # FastF1's frozen centerline can contain sharp sample-to-sample kinks.
        # Follow a lightly rounded line within the usable track corridor while
        # keeping projection and off-track detection on the original centerline.
        weights = np.asarray((1, 2, 3, 4, 5, 4, 3, 2, 1), dtype=np.float64)
        smoothed = sum(
            weights[j] * np.roll(self._points, j - 4, axis=0)
            for j in range(len(weights))
        ) / float(weights.sum())
        displacement = smoothed - self._points
        displacement_len = np.linalg.norm(displacement, axis=1)
        shift_limit = max(0.0, self._half_width - 2.0)
        shift_scale = np.minimum(
            1.0, shift_limit / np.maximum(displacement_len, 1e-9),
        )
        self._set_line_points(self._points + displacement * shift_scale[:, None])
        # Planeje a velocidade pela geometria conservadora original. Uma linha
        # mais aberta não deve apagar a necessidade de frear antes da curva.
        self._planning_curvature = self._curvature.copy()
        self._planning_raw_curvature = self._raw_curvature.copy()
        self._hairpin_speed_cap_mps = self.HAIRPIN_SPEED_CAP_MPS
        self._lateral_grip_factor = self.LATERAL_GRIP_FACTOR
        self._max_target_accel_mps2 = self.MAX_TARGET_ACCEL_MPS2
        self._interlagos_line_applied = False
        self._apply_local_racing_line()

        self._hints: Dict[str, int] = {}
        self._styles: Dict[str, _DriverStyle] = {}
        self.last_authority: Dict[str, str] = {}
        self.REJOIN_RAMP_ENABLED = False

    def _set_line_points(self, points: np.ndarray) -> None:
        """Atualiza a geometria usada para seguir a linha de corrida."""
        self._line_points = points
        self._line_ab = np.roll(self._line_points, -1, axis=0) - self._line_points
        self._line_seg_len = np.linalg.norm(self._line_ab, axis=1)
        self._line_heading = np.arctan2(self._line_ab[:, 1], self._line_ab[:, 0])
        left = np.column_stack((-np.sin(self._heading), np.cos(self._heading)))
        self._line_offset = np.sum(
            (self._line_points - self._points) * left, axis=1,
        )

        heading_delta = self._wrap_array(
            np.roll(self._line_heading, -1) - self._line_heading,
        )
        span = (self._line_seg_len + np.roll(self._line_seg_len, -1)) * 0.5
        self._signed_curvature = heading_delta / np.maximum(span, 0.25)
        raw_curvature = np.abs(self._signed_curvature)
        self._raw_curvature = raw_curvature
        self._curvature = (
            np.roll(raw_curvature, 1) + 2.0 * raw_curvature
            + np.roll(raw_curvature, -1)
        ) * 0.25

    def _apply_local_racing_line(self) -> None:
        """Usa a linha calibrada somente na geometria e largura verificadas."""
        geometry_hash = hashlib.sha256(self._points.tobytes()).hexdigest()
        if (geometry_hash != self.INTERLAGOS_GEOMETRY_SHA256
                or abs(float(self.track.width_m) - 12.0) > 1e-6):
            return
        profile_path = Path(__file__).with_name("racing_lines") / "interlagos_rule_line.json"
        with profile_path.open(encoding="utf-8") as profile_file:
            profile = json.load(profile_file)
        if (profile["geometry_sha256"] != geometry_hash
                or profile["track_width_m"] != 12.0):
            raise ValueError("Perfil de linha de corrida incompatível com a pista")
        offsets = np.asarray(profile["offsets_xy_m"], dtype=np.float64)
        start = int(profile["first_waypoint"])
        if (offsets.ndim != 2 or offsets.shape[1] != 2
                or not np.isfinite(offsets).all() or start < 0
                or start + len(offsets) > len(self._line_points)):
            raise ValueError("Perfil de linha de corrida inválido")
        line = self._line_points.copy()
        line[start:start + len(offsets)] += self.INTERLAGOS_LINE_FRACTION * offsets
        self._set_line_points(line)
        self._hairpin_speed_cap_mps = self.INTERLAGOS_HAIRPIN_SPEED_CAP_MPS
        # The higher pace calibration was measured only on this frozen
        # Interlagos geometry; keep the conservative defaults on other tracks.
        self._lateral_grip_factor = self.INTERLAGOS_LATERAL_GRIP_FACTOR
        self._max_target_accel_mps2 = self.INTERLAGOS_MAX_TARGET_ACCEL_MPS2
        self._interlagos_line_applied = True

    @staticmethod
    def _wrap(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

    @staticmethod
    def _wrap_array(angles: np.ndarray) -> np.ndarray:
        return (angles + math.pi) % (2.0 * math.pi) - math.pi

    def _style_for(self, driver_id: str) -> _DriverStyle:
        style = self._styles.get(driver_id)
        if style is not None:
            return style

        digest = hashlib.sha256(
            f"{self.seed}//apex-formula//{driver_id}".encode("utf-8")
        ).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        launch_digest = hashlib.sha256(
            f"{self.seed}//launch//{driver_id}".encode("utf-8")
        ).digest()
        launch_rng = random.Random(int.from_bytes(launch_digest[:8], "big"))
        style = _DriverStyle(
            rng=rng,
            skill=rng.uniform(0.982, 1.012),
            consistency=rng.uniform(0.86, 0.99),
            start_reaction_s=launch_rng.uniform(0.05, 0.75),
            lap_noise=rng.uniform(0.997, 1.003),
            mistake_cooldown_s=rng.uniform(10.0, 20.0),
        )
        self._styles[driver_id] = style
        return style

    def reset(self) -> None:
        self._hints.clear()
        self._styles.clear()
        self.last_authority.clear()

    def _project(self, driver_id: str, x: float, y: float) -> Tuple[float, float]:
        n = len(self._a)
        hint = self._hints.get(driver_id)
        if hint is None or n <= 101:
            indices = np.arange(n, dtype=np.int64)
        else:
            # At 10 Hz a car moves at most about 11 m per controller call.
            # A wide local window handles dense tracks and start/finish wrap.
            offsets = np.arange(-50, 51, dtype=np.int64)
            indices = (hint + offsets) % n

        px = self._a[indices, 0]
        py = self._a[indices, 1]
        abx = self._ab[indices, 0]
        aby = self._ab[indices, 1]
        t = np.clip(
            ((x - px) * abx + (y - py) * aby)
            / self._seg_len_sq[indices], 0.0, 1.0,
        )
        qx = px + t * abx
        qy = py + t * aby
        dist_sq = (qx - x) ** 2 + (qy - y) ** 2
        local = int(np.argmin(dist_sq))
        idx = int(indices[local])
        segment_t = float(t[local])
        distance = math.sqrt(float(dist_sq[local]))
        cross = self._ab[idx, 0] * (y - qy[local]) - self._ab[idx, 1] * (x - qx[local])
        signed_lat = distance if cross >= 0.0 else -distance
        s = float((self._seg_s[idx] + segment_t * self._seg_len[idx]) % self._track_len)
        self._hints[driver_id] = idx
        return s, signed_lat

    def _segment_at(self, s: float) -> int:
        return int(np.searchsorted(self._seg_s, s % self._track_len, side="right") - 1) % len(self._a)

    def _point_at(self, s: float, lateral_offset_m: float = 0.0,
                  centerline: bool = False) -> Tuple[float, float]:
        s %= self._track_len
        idx = self._segment_at(s)
        t = (s - self._seg_s[idx]) / self._seg_len[idx]
        points = self._points if centerline else self._line_points
        segments = self._ab if centerline else self._line_ab
        headings = self._heading if centerline else self._line_heading
        x, y = points[idx] + t * segments[idx]
        heading = float(headings[idx])
        return (
            float(x - math.sin(heading) * lateral_offset_m),
            float(y + math.cos(heading) * lateral_offset_m),
        )

    def _line_offset_at(self, s: float) -> float:
        idx = self._segment_at(s)
        next_idx = (idx + 1) % len(self._line_offset)
        t = (s % self._track_len - self._seg_s[idx]) / self._seg_len[idx]
        return float(
            self._line_offset[idx]
            + t * (self._line_offset[next_idx] - self._line_offset[idx])
        )

    def _curvature_at(self, idx: int) -> float:
        """Curvatura conservadora: preserva picos locais que a média dilui."""
        smoothed = float(self._curvature[idx])
        sampled_peak = float(self._raw_curvature[idx])
        return min(self.CURVATURE_PEAK_LIMIT, max(smoothed, sampled_peak))

    def _planning_curvature_at(self, idx: int) -> float:
        return min(self.CURVATURE_PEAK_LIMIT, max(
            float(self._planning_curvature[idx]),
            float(self._planning_raw_curvature[idx]),
        ))

    def _grip_and_acceleration(self, env: EnvironmentState,
                               driver_state: Any,
                               speed_mps: float,
                               lateral_m: float,
                               surface_grip_floor: Optional[float] = None
                               ) -> Tuple[float, float, float, float]:
        weather = env.weather
        grip = driver_state.tyre.grip_multiplier(weather.kind, weather.track_temp)
        surface = self.track.surface_grip_factor_from_distance(abs(lateral_m))
        if surface_grip_floor is None:
            effective_grip = max(0.30, min(1.20, float(grip) * surface))
        else:
            surface = max(surface, surface_grip_floor)
            effective_grip = max(0.3, min(1.2, float(grip))) * surface

        specs = driver_state.car.specs
        mass = max(1.0, float(driver_state.car.total_mass))
        downforce_per_speed_sq = (
            0.5 * 1.225 * float(specs.downforce_coeff)
            * float(specs.frontal_area_m2) / mass
        )
        downforce_accel = downforce_per_speed_sq * speed_mps * speed_mps
        nominal_mu = max(
            0.1, float(getattr(specs, "mu_nominal", self.MU_NOMINAL)),
        )
        effective_mu = nominal_mu * effective_grip
        normal_accel = self.G + downforce_accel
        # PhysicsCarHandle applies mu_nominal * grip_multiplier to both tire
        # forces. Keep the planner on that same scale, with a small reserve so
        # the target does not ask the car to use the full tire envelope.
        tire_accel = effective_mu * normal_accel
        braking_accel = max(
            4.0,
            min(
                self.MAX_PLAN_BRAKING_MPS2,
                tire_accel * self.BRAKING_GRIP_FACTOR,
            ),
        )
        return effective_grip, effective_mu, braking_accel, downforce_per_speed_sq

    def _planned_speed(self, s: float, top_speed: float,
                       effective_mu: float, downforce_per_speed_sq: float,
                       braking_accel: float, current_speed: float) -> float:
        target = top_speed
        distance = 0.0
        horizon = max(
            self.MIN_SPEED_PLAN_HORIZON_M,
            current_speed * current_speed / (2.0 * 18.0) + 50.0,
        )
        horizon = min(self.MAX_SPEED_PLAN_HORIZON_M, horizon)
        while distance <= horizon:
            idx = self._segment_at(s + distance)
            curvature = self._planning_curvature_at(idx) * 1.08
            denominator = (
                curvature
                - self._lateral_grip_factor * effective_mu * downforce_per_speed_sq
            )
            if denominator <= 1e-5:
                corner_speed = top_speed
            else:
                corner_speed = min(
                    top_speed,
                    math.sqrt(self._lateral_grip_factor * effective_mu * self.G
                              / denominator),
                )

            # Teto calibrado no hairpin mais fechado: acima dele, a linha sai
            # do corredor antes que o chassi consiga acompanhar a curva.
            if curvature > 0.09:
                corner_speed = min(corner_speed, self._hairpin_speed_cap_mps)

            # Desaceleração efetiva média entre velocidade atual e velocidade de curva.
            # O downforce cai com v² durante a frenagem, portanto usar o freio avaliado
            # na velocidade de reta superestima a capacidade de frenagem em ~2x.
            v_mid = 0.5 * (current_speed + corner_speed)
            downforce_mid = downforce_per_speed_sq * v_mid * v_mid
            safe_brake = max(
                8.0,
                min(
                    self.MAX_PLAN_BRAKING_MPS2,
                    effective_mu * (self.G + downforce_mid) * self.BRAKING_GRIP_FACTOR,
                ),
            )

            # Zona de aproximação em curvas fechadas: atinge a velocidade alvo antes do ápice
            eff_dist = max(0.0, distance - 14.0) if curvature > 0.065 else distance
            allowed_now = math.sqrt(
                corner_speed * corner_speed + 2.0 * safe_brake * eff_dist
            )
            target = min(target, allowed_now)
            distance += self.SPEED_PLAN_STEP_M
        return target

    def _longitudinal_commands(
        self,
        driver_state: Any,
        speed: float,
        target_speed: float,
        effective_grip: float,
        effective_mu: float,
        downforce_per_speed_sq: float,
        braking_accel: float,
        aero_drag_multiplier: float = 1.0,
    ) -> Tuple[float, float]:
        """Smooth speed tracking with drag/rolling-resistance feed-forward."""
        specs = driver_state.car.specs
        mass = max(1.0, float(driver_state.car.total_mass))
        speed_abs = max(0.0, float(speed))
        downforce = mass * downforce_per_speed_sq * speed_abs * speed_abs
        normal_load = mass * self.G + downforce
        rolling_coefficient = self.ROLLING_COEFFICIENT / max(
            0.2, min(1.0, float(effective_grip)),
        )
        rolling_force = rolling_coefficient * normal_load
        drag_force = (
            0.5 * self.AIR_DENSITY * float(specs.drag_coeff)
            * float(specs.frontal_area_m2) * speed_abs * speed_abs
            * max(0.5, min(1.0, float(aero_drag_multiplier)))
        )

        speed_error = float(target_speed) - speed_abs
        if speed_error < -0.5:
            # Demanda de frenagem progressiva e firme: atinge freio pleno (1.0)
            # quando a velocidade estiver 4.8 m/s (~17 km/h) acima do planejado.
            brake = min(1.0, -speed_error / 4.8)
            return 0.0, brake
        else:
            # The engine independently limits drive force by power and rear
            # tire traction. A 6 m/s² request was below what this F1 model can
            # deliver after slow corners, leaving throttle unused on exits.
            accel_request = min(
                self._max_target_accel_mps2, 0.85 * speed_error,
            )
            required_force = rolling_force + drag_force + mass * accel_request
            if required_force > 0.0:
                required_power = required_force * max(speed_abs, 1.0)
                available_power = max(1.0, float(specs.power_kw) * 1000.0)
                throttle = max(0.0, min(1.0, required_power / available_power))
            else:
                throttle = 0.0
            return throttle, 0.0

    @staticmethod
    def _forward_gap(from_s: float, to_s: float, track_len: float) -> float:
        return (to_s - from_s + track_len * 0.5) % track_len - track_len * 0.5

    def compute_input(self, env: EnvironmentState, driver_state: Any) -> CarInput:
        driver_id = driver_state.driver_id
        style = self._style_for(driver_id)
        dt = (0.1 if style.last_sim_ts is None else
              max(0.01, min(0.25, float(env.sim_ts) - style.last_sim_ts)))
        style.last_sim_ts = float(env.sim_ts)

        if driver_state.lap != style.lap:
            style.lap = int(driver_state.lap)
            style.lap_noise = style.rng.uniform(0.997, 1.003)

        # Each driver has a slowly changing rhythm over a stint. The factor
        # only reduces the planned speed, keeping the corner safety envelope.
        style.form_left_s -= dt
        if style.form_left_s <= 0.0:
            style.form_target = style.rng.uniform(0.965, 1.0)
            style.form_left_s = style.rng.uniform(20.0, 36.0)
        form_step = 0.002 * dt
        style.form_factor += max(
            -form_step, min(form_step, style.form_target - style.form_factor),
        )

        s, signed_lat = self._project(
            driver_id, float(driver_state.position_x), float(driver_state.position_y),
        )
        speed = max(0.0, float(driver_state.velocity_mps))
        track_heading = float(self._heading[self._segment_at(s)])
        heading_error = self._wrap(track_heading - float(driver_state.heading_rad))
        near_edge_and_wrong_way = (
            abs(signed_lat) > self._half_width - 1.5
            and abs(heading_error) > math.radians(120.0)
        )
        if (abs(signed_lat) > self._half_width - 0.5
                or near_edge_and_wrong_way):
            style.rejoining = True
        elif (style.rejoining
                and abs(signed_lat) <= self._half_width - 1.5
                and abs(heading_error) < math.radians(35.0)):
            # Keep the recovery controller in charge after crossing the edge;
            # release only once the car is inside and pointed down the track.
            style.rejoining = False
        rejoining = style.rejoining
        aero_drag_multiplier = float(
            getattr(env, "aero_drag_multipliers", {}).get(driver_id, 1.0)
        )

        # Inspect nearby cars on the cyclic track coordinate.
        blocker = None
        blocker_gap = float("inf")
        blocker_lat = 0.0
        attacker = None
        attacker_gap = -float("inf")
        attacker_lat = 0.0
        attack_target = None
        attack_gap = float("inf")
        nearby_cars = []
        straight_ahead = speed > 25.0 and max(
            self._planning_curvature_at(self._segment_at(s + distance))
            for distance in (0.0, 15.0, 30.0, 45.0)
        ) < 0.015
        for other_id, other in env.all_driver_states.items():
            if other_id == driver_id or getattr(other, "pitting", False):
                continue
            other_s, other_lat = self._project(
                other_id, float(other.position_x), float(other.position_y),
            )
            gap = self._forward_gap(s, other_s, self._track_len)
            lat_gap = abs(other_lat - signed_lat)
            nearby_cars.append((other_id, gap, other_lat))
            if (straight_ahead and 0.35 < gap < 65.0 and lat_gap < 3.6
                    and abs(other_lat) <= self._half_width + 1.0
                    and speed > float(other.velocity_mps) + 1.0 and gap < attack_gap):
                attack_target, attack_gap = other, gap
            if (0.35 < gap < 38.0 and lat_gap < 3.6
                    and float(other.velocity_mps) < speed + 4.0 and gap < blocker_gap):
                blocker = other
                blocker_gap, blocker_lat = gap, other_lat
            if (-23.0 < gap < -5.5 and lat_gap < 4.0
                    and float(other.velocity_mps) > speed + 1.5
                    and gap > attacker_gap):
                attacker = other
                attacker_gap, attacker_lat = gap, other_lat

        # Move smoothly off the line around a car ahead; on a clear straight,
        # make one modest defensive move when a faster car closes from behind.
        line_offset = self._line_offset_at(s)
        room = max(0.0, self._half_width - 1.9 - abs(line_offset))
        desired_offset = 0.0
        passing_target = env.all_driver_states.get(style.avoid_target_id)
        if passing_target is not None and not getattr(passing_target, "pitting", False):
            target_s, target_lat = self._project(
                passing_target.driver_id,
                float(passing_target.position_x), float(passing_target.position_y),
            )
            target_gap = self._forward_gap(s, target_s, self._track_len)
            if (not -8.0 < target_gap < 50.0
                    or abs(target_lat) > self._half_width + 1.0):
                passing_target = None
        else:
            passing_target = None
        if rejoining:
            style.avoid_target_id = None
            style.avoid_offset_m = 0.0
        elif passing_target is not None and room > 0.6:
            # Remain alongside until the opponent is safely behind. Otherwise
            # leaving their slipstream cancels the move before a pass occurs.
            desired_offset = style.avoid_side * min(self.OVERTAKE_OFFSET_M, room)
        elif room > 0.6 and (attack_target is not None
                             or (blocker is not None and blocker_gap < 12.0)):
            target = attack_target if attack_target is not None else blocker
            target_offset = min(self.OVERTAKE_OFFSET_M, room)
            free_sides = [
                side for side in (-1.0, 1.0)
                if not any(
                    other_id != target.driver_id and -12.0 < gap < 18.0
                    and abs(other_lat - (line_offset + side * target_offset)) < 2.6
                    for other_id, gap, other_lat in nearby_cars
                )
            ]
            if free_sides:
                target_lat = next(lat for other_id, _, lat in nearby_cars
                                  if other_id == target.driver_id)
                preferred = (-math.copysign(1.0, target_lat - signed_lat)
                             if abs(target_lat - signed_lat) > 0.65
                             else style.rng.choice((-1.0, 1.0)))
                style.avoid_side = preferred if preferred in free_sides else free_sides[0]
                style.avoid_target_id = target.driver_id
                desired_offset = style.avoid_side * target_offset
            else:
                style.avoid_target_id = None
        else:
            style.avoid_target_id = None
            if attacker is not None and room > 0.6:
                upcoming_kappa = float(self._curvature[self._segment_at(s + 18.0)])
                if upcoming_kappa < 0.004:
                    desired_offset = (
                        -math.copysign(1.0, attacker_lat - signed_lat)
                        * min(1.35, room)
                    )
        if not rejoining:
            max_offset_step = 1.8 * dt
            offset_error = desired_offset - style.avoid_offset_m
            style.avoid_offset_m += max(-max_offset_step, min(max_offset_step, offset_error))
            style.avoid_offset_m = max(-room, min(room, style.avoid_offset_m))

        base_lookahead = max(8.0, min(50.0, 6.0 + speed * 0.45))
        curve_preview_m = min(40.0, base_lookahead)
        preview_steps = max(1, int(math.ceil(curve_preview_m / 4.0)))
        preview_curvature = max(
            self._curvature_at(self._segment_at(s + i * 4.0))
            for i in range(preview_steps + 1)
        )
        steering_curvature = max(
            self._curvature_at(self._segment_at(s + offset))
            for offset in range(-32, 33, 4)
        )
        # Lookahead adaptativo: em hairpins fechados (R < 12 m),
        # o piso precisa encolher para 3.2m para não mirar fora do arco da curva.
        if rejoining:
            lookahead = max(4.0, min(8.0, 4.0 + speed * 0.1))
            target_x, target_y = self._point_at(
                s + lookahead, centerline=True,
            )
        else:
            min_lookahead = (
                self.HAIRPIN_MIN_LOOKAHEAD_M if preview_curvature > 0.07
                else (4.5 if preview_curvature > 0.03 else 7.5)
            )
            lookahead = max(min_lookahead, base_lookahead / (1.0 + 16.0 * preview_curvature))
            target_x, target_y = self._point_at(s + lookahead, style.avoid_offset_m)
        bearing = math.atan2(target_y - driver_state.position_y,
                             target_x - driver_state.position_x)
        alpha = self._wrap(bearing - float(driver_state.heading_rad))
        wheelbase = max(2.5, float(driver_state.car.specs.wheelbase_m))
        steering = math.atan2(2.0 * wheelbase * math.sin(alpha), lookahead)

        if not rejoining:
            # Cross-track feedback para puxar o carro de volta quando houver desvio
            lateral_error = line_offset + style.avoid_offset_m - signed_lat
            steering += math.atan2(
                0.70 * lateral_error,
                abs(speed) + 2.0,
            )

            # Feedforward cinemático da curvatura local: delta_ff = arctan(L * kappa)
            idx_now = self._segment_at(s)
            kappa_signed = float(self._signed_curvature[idx_now])
            steering += math.atan2(wheelbase * kappa_signed * 0.90, 1.0)

        # Limite físico de esterço do simulador: decai suavemente com a velocidade
        steer_limit = max(0.04, math.radians(45.0) / (1.0 + (speed / 25.0) ** 2))
        if rejoining:
            # Full lock creates large tire scrub in the physics model and
            # keeps a stranded car crawling. A gentler limit rotates it while
            # preserving enough forward speed to get back onto the asphalt.
            steer_limit = min(steer_limit, self.REJOIN_MAX_STEER_RAD)
        if rejoining and abs(alpha) > 2.35:
            # Pure pursuit tends to zero when its target is almost directly
            # behind the car. Turn hard toward the target, using the track side
            # only to break the exact 180-degree tie.
            turn_sine = math.sin(alpha)
            turn_side = (
                turn_sine if abs(turn_sine) > 0.12
                else -signed_lat
            )
            if abs(turn_side) < 0.1:
                turn_side = alpha
            steering = math.copysign(steer_limit, turn_side)
        if (not rejoining and self._interlagos_line_applied
                and steering_curvature > 0.07):
            curvature_steer_limit = self.HAIRPIN_STEER_LIMIT_FACTOR * math.atan(
                wheelbase * steering_curvature
            )
            steer_limit = min(steer_limit, curvature_steer_limit)
        steering = max(-steer_limit, min(steer_limit, steering))

        grip_override = None
        recovery_grip_floor = (
            self.REJOIN_SURFACE_GRIP_FLOOR
            if rejoining and abs(signed_lat) > self._half_width
            else None
        )
        effective_grip, effective_mu, braking_accel, downforce_per_speed_sq = (
            self._grip_and_acceleration(
                env, driver_state, speed, signed_lat,
                surface_grip_floor=recovery_grip_floor,
            )
        )
        if recovery_grip_floor is not None:
            recovery_surface = max(
                self.track.surface_grip_factor_from_distance(abs(signed_lat)),
                recovery_grip_floor,
            )
            tire_grip = driver_state.tyre.grip_multiplier(
                env.weather.kind, env.weather.track_temp,
            )
            # Keep tire and weather effects, easing only the off-track
            # surface penalty while this controller is actively recovering.
            grip_override = max(0.3, min(1.2, float(tire_grip))) * recovery_surface

        top_speed = max(20.0, float(driver_state.car.max_speed_kmh()) / 3.6)
        target_speed = self._planned_speed(
            s, top_speed, effective_mu, downforce_per_speed_sq,
            braking_accel, speed,
        )

        chasing = blocker is not None and blocker_gap < 140.0
        if chasing and blocker_gap / max(speed, 28.0) < 1.0:
            target_speed *= 1.006
        target_speed *= style.skill * style.lap_noise * style.form_factor

        follow_brake = 0.0
        if (blocker is not None
                and abs(blocker_lat - signed_lat) < self.FOLLOW_LATERAL_CLEARANCE_M):
            closing = max(0.0, speed - float(blocker.velocity_mps))
            safe_gap = 5.2 + min(3.0, speed * 0.04) + min(6.0, closing * 0.4)
            gap_error = safe_gap - blocker_gap
            if gap_error > 0.0:
                target_speed = min(
                    target_speed,
                    max(6.5, float(blocker.velocity_mps) - min(2.0, gap_error * 0.25)),
                )
                if closing > 0.5 or gap_error > 1.5:
                    follow_brake = min(0.65, 0.04 + gap_error * 0.08 + closing * 0.05)

        if rejoining:
            # Carry speed while far into the grass, then slow as the car enters
            # the usable lane. The previous fixed 8 m/s cap let a backwards-
            # facing car cross the whole track before it could align.
            grass_depth = max(0.0, abs(signed_lat) - self._half_width)
            if grass_depth > self.REJOIN_DEEP_GRASS_MARGIN_M:
                recovery_cap = self.REJOIN_DEEP_SPEED_MPS
            elif grass_depth > 0.0:
                recovery_cap = self.REJOIN_NEAR_SPEED_MPS
            else:
                recovery_cap = self.REJOIN_ON_TRACK_SPEED_MPS
            target_speed = min(target_speed, recovery_cap)
            self.last_authority[driver_id] = "rejoin"
        elif follow_brake > 0.0:
            self.last_authority[driver_id] = "traffic"
        else:
            self.last_authority[driver_id] = "apex-rules"

        # Occasional brief lifts give drivers different exits without random
        # steering impulses or a guaranteed loss of control.
        style.mistake_cooldown_s -= dt
        style.mistake_left_s = max(0.0, style.mistake_left_s - dt)
        if style.mistake_cooldown_s <= 0.0:
            style.mistake_cooldown_s = style.rng.uniform(18.0, 32.0)
            if style.rng.random() < 0.16 + (1.0 - style.consistency) * 0.35:
                style.mistake_left_s = style.rng.uniform(0.9, 1.8)
                style.mistake_throttle_factor = style.rng.uniform(0.60, 0.82)

        throttle, brake = self._longitudinal_commands(
            driver_state, speed, target_speed, effective_grip, effective_mu,
            downforce_per_speed_sq, braking_accel,
            aero_drag_multiplier=aero_drag_multiplier,
        )
        if follow_brake > 0.0:
            throttle = 0.0
            brake = max(brake, follow_brake)
        if style.mistake_left_s > 0.0 and not rejoining:
            throttle *= style.mistake_throttle_factor
        if (not rejoining and driver_state.lap == 0 and speed < 2.0
                and float(env.sim_ts) < style.start_reaction_s):
            throttle = 0.0

        return CarInput(
            steering_yaw_rad=steering,
            brake=max(0.0, min(1.0, brake)),
            throttle=max(0.0, min(1.0, throttle)),
            grip_override=grip_override,
        )
