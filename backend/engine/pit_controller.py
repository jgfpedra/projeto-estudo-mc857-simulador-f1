"""Controle de trajetória da via de boxes usando os comandos físicos existentes."""
from __future__ import annotations

from bisect import bisect_right
import math

from .controllers import CarInput


class PitController:
    def __init__(self, track):
        self.track = track
        self.pit = track.pit
        self.track_length = sum(math.dist(a, b) for a, b in
                                zip(track.waypoints, track.waypoints[1:] + track.waypoints[:1]))
        self.points = self.pit.waypoints
        self.cumulative = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            self.cumulative.append(self.cumulative[-1] + math.dist(a, b))
        if self.cumulative[-1] <= 1e-6:
            raise ValueError('Trajeto dos boxes sem comprimento')
        self.progress = {}
        # Durante a frenagem, seguir a pista até a entrada evita cortar curvas
        # ao mirar diretamente no primeiro ponto dos boxes a 80 m de distância.
        preceding = []
        idx = self.pit.entry_waypoint
        distance = 0.0
        for _ in range(len(track.waypoints) - 1):
            point = track.waypoints[idx]
            preceding.append(point)
            previous_idx = (idx - 1) % len(track.waypoints)
            distance += math.dist(point, track.waypoints[previous_idx])
            idx = previous_idx
            if distance >= max(350.0, self.track_length * .08):
                break
        self.approach_points = list(reversed(preceding))
        if not self.approach_points or math.dist(self.approach_points[-1], self.points[0]) > 1e-6:
            self.approach_points.append(self.points[0])
        self.approach_cumulative = [0.0]
        for a, b in zip(self.approach_points, self.approach_points[1:]):
            self.approach_cumulative.append(self.approach_cumulative[-1] + math.dist(a, b))
        if self.pit.entry_s_m is None:
            # Pistas com geometria própria informam entrada por índice.
            sf = track.waypoints[track.start_finish_waypoint:] + track.waypoints[:track.start_finish_waypoint]
            distance = 0.0
            idx = track.start_finish_waypoint
            for _ in range(len(sf)):
                if idx == self.pit.entry_waypoint:
                    break
                nxt = (idx + 1) % len(track.waypoints)
                distance += math.dist(track.waypoints[idx], track.waypoints[nxt])
                idx = nxt
            self.entry_s = distance % self.track_length
        else:
            self.entry_s = self.pit.entry_s_m

    def distance_to_lane(self, x, y):
        best = float('inf')
        for a, b in zip(self.points, self.points[1:]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            seg2 = dx*dx + dy*dy
            if seg2 < 1e-12:
                continue
            t = min(1.0, max(0.0, ((x-a[0])*dx + (y-a[1])*dy)/seg2))
            best = min(best, math.hypot(x-a[0]-t*dx, y-a[1]-t*dy))
        return best

    def should_enter(self, s, speed):
        if s is None:
            return False
        # Inicia a frenagem antes da divergência sem iniciar durante a volta
        # imediatamente anterior se o ponto de entrada já tiver sido passado.
        distance = (self.entry_s - s) % self.track_length
        approach = min(self.track_length * .08, max(80.0, speed * 2.0))
        return distance <= approach

    def has_entered(self, state):
        """Se o centro do carro já cruzou o início da via de boxes.

        O controle do pit começa antes do primeiro waypoint para frear; a flag
        pitting, sozinha, portanto não indica que a entrada já foi cruzada.
        """
        if not state.pitting:
            return False
        if self.progress.get(state.driver_id, 0.0) > 0.01:
            return True
        a, b = self.points[0], self.points[1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        return (state.position_x - a[0]) * dx + (state.position_y - a[1]) * dy > 0.0

    def reset(self, driver_id):
        self.progress.pop(driver_id, None)

    def compute_input(self, state, other_states=()):
        x, y = state.position_x, state.position_y
        previous = self.progress.get(state.driver_id, 0.0)
        best = None
        for i, (a, b) in enumerate(zip(self.points, self.points[1:])):
            dx, dy = b[0]-a[0], b[1]-a[1]
            seg2 = dx*dx + dy*dy
            if seg2 < 1e-12:
                continue
            t = min(1.0, max(0.0, ((x-a[0])*dx + (y-a[1])*dy)/seg2))
            pos = self.cumulative[i] + math.sqrt(seg2)*t
            if pos < previous - 15.0 or pos > previous + max(80.0, state.velocity_mps*3):
                continue
            dist2 = (x-a[0]-dx*t)**2 + (y-a[1]-dy*t)**2
            if best is None or dist2 < best[0]:
                best = dist2, pos
        progress = max(previous, best[1]) if best else previous
        self.progress[state.driver_id] = progress
        # Long enough to avoid swerving and short enough to follow the entrance.
        lookahead = max(14.0, min(30.0, state.velocity_mps * 1.2))
        target = min(self.cumulative[-1], progress + lookahead)
        idx = min(bisect_right(self.cumulative, target)-1, len(self.points)-2)
        segment = self.cumulative[idx+1] - self.cumulative[idx]
        frac = (target-self.cumulative[idx])/segment if segment > 0 else 0
        a, b = self.points[idx], self.points[idx+1]
        tx, ty = a[0]+(b[0]-a[0])*frac, a[1]+(b[1]-a[1])*frac
        if progress == 0.0 and math.dist((x, y), self.points[0]) > 20.0:
            nearest = None
            for i, (a, b) in enumerate(zip(self.approach_points, self.approach_points[1:])):
                dx, dy = b[0] - a[0], b[1] - a[1]
                seg2 = dx * dx + dy * dy
                if seg2 < 1e-12:
                    continue
                t = min(1.0, max(0.0, ((x-a[0])*dx + (y-a[1])*dy)/seg2))
                dist2 = (x-a[0]-t*dx)**2 + (y-a[1]-t*dy)**2
                if nearest is None or dist2 < nearest[0]:
                    nearest = dist2, self.approach_cumulative[i] + math.sqrt(seg2)*t
            if nearest is not None:
                target = min(self.approach_cumulative[-1], nearest[1] + lookahead)
                i = min(bisect_right(self.approach_cumulative, target)-1, len(self.approach_points)-2)
                segment = self.approach_cumulative[i+1] - self.approach_cumulative[i]
                frac = (target-self.approach_cumulative[i])/segment if segment > 0 else 0
                a, b = self.approach_points[i], self.approach_points[i+1]
                tx, ty = a[0]+(b[0]-a[0])*frac, a[1]+(b[1]-a[1])*frac
        actual_lookahead = max(3.0, math.hypot(tx-x, ty-y))
        alpha = (math.atan2(ty-y, tx-x) - state.heading_rad + math.pi) % (2*math.pi) - math.pi
        wheelbase = float(getattr(state.car.specs, 'wheelbase_m', 3.6))
        steering = math.atan2(2.0 * wheelbase * math.sin(alpha), actual_lookahead)
        steering = max(-.35, min(.35, steering))
        target_speed = min(self.pit.speed_limit_kmh/3.6, 18.0)
        # Mantém distância de outro carro na mesma fila dos boxes.
        # A projeção é local ao carro, portanto também funciona na aproximação.
        brake = 0.0
        forward_x, forward_y = math.cos(state.heading_rad), math.sin(state.heading_rad)
        for other in other_states:
            if other.driver_id == state.driver_id:
                continue
            dx, dy = other.position_x - x, other.position_y - y
            ahead = dx * forward_x + dy * forward_y
            lateral = abs(-dx * forward_y + dy * forward_x)
            if ahead <= 0.0 or ahead > 45.0 or lateral > self.pit.width_m:
                continue
            other_speed = max(0.0, other.velocity_mps)
            safe_gap = 7.0 + max(0.0, state.velocity_mps) * 0.6
            target_speed = min(target_speed, max(0.0, other_speed + (ahead - safe_gap) * 0.7))
            closing = max(0.0, state.velocity_mps - other_speed)
            if ahead < safe_gap and closing > 0.5:
                brake = max(brake, min(0.8, (safe_gap - ahead) * 0.08 + closing * 0.08))
        # A via é asfalto: a engine aplica pneu e clima sem a penalidade de grama.
        return CarInput(target_speed_mps=target_speed, steering_yaw_rad=steering, brake=brake), progress/self.cumulative[-1]
