"""PyBullet physics wrapper.

Gerencia o mundo físico do PyBullet: plano (asfalto), obstáculos de borda da
pista e os corpos dos carros (chassis + 4 rodas).

Cada carro é um multi-body com:
- chassis: caixa, massa = specs.mass_kg + fuel_kg + 75 (piloto)
- 4 rodas: cilindros presos via joints com fricção configurável

A cada tick o motor chama ``step(...)`` com:
- posição alvo (waypoint look-ahead)
- velocidade alvo (computada pelo Engine com base em potência, pneu, clima)

Internamente aplicamos:
- força de tração nas rodas traseiras (motor force)
- steering nas rodas dianteiras (ângulo)
- fricção lateral (controla grip dinâmico = função de pneu + clima)

A colisão entre carros é resolvida pelo próprio PyBullet.
-----
- Usa o modo DIRECT (headless) por padrão. Para visual, passe ``gui=True``.
- O timestep interno é 1/240s; fazemos N sub-steps por chamada de ``step``.
- Não usamos ``racecar.urdf`` do pybullet_data porque ele não vem instalado
  na versão atual; construímos os carros via ``createMultiBody`` para ter
  controle total sobre o coeficiente de atrito (essencial para refletir
  pneu/clima dinamicamente).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pybullet as p
import pybullet_data


@dataclass
class PhysicsCarHandle:
    """Handle para um corpo de carro no mundo PyBullet com física aprimorada de F1."""

    driver_id: str
    chassis_id: int
    wheel_ids: List[int] = field(default_factory=list)
    joint_ids: List[int] = field(default_factory=list)  # índices das joints (chassis-wheel)
    steering_joint_ids: List[int] = field(default_factory=list)  # subconjunto dianteiro
    drive_joint_ids: List[int] = field(default_factory=list)     # subconjunto traseiro
    mass_kg: float = 798.0
    # Geometria e especificações de F1
    power_kw: float = 735.0          # ~1000 cv
    drag_coeff: float = 0.85
    downforce_coeff: float = 3.2     # CL de alta pressão aerodinâmica típica de F1
    frontal_area_m2: float = 1.5
    wheelbase_m: float = 3.4
    half_length: float = 2.5
    half_width: float = 0.9
    wheel_radius: float = 0.33
    # Parâmetros de pneus e freio
    mu_nominal: float = 1.8          # Pneu slick F1 seco (mu ~1.7-1.9 em asfalto limpo)
    brake_decel_max: float = 50.0    # ~5G capacidade máxima de frenagem com freios de carbono
    air_density: float = 1.225       # kg/m³
    # Telemetria em tempo real
    last_downforce_n: float = 0.0
    last_drag_n: float = 0.0
    last_drive_force_n: float = 0.0
    last_brake_force_n: float = 0.0
    last_lateral_force_n: float = 0.0
    last_slip_f: float = 0.0
    last_slip_r: float = 0.0
    last_g_lat: float = 0.0
    last_g_long: float = 0.0
    last_rolling_friction_n: float = 0.0
    last_cornering_drag_n: float = 0.0
    last_engine_brake_n: float = 0.0


class PyBulletPhysics:
    """Wrapper do PyBullet para a simulação de corrida com física de F1.

    O mundo contém:
    - Um plano de asfalto (z=0)
    - N carros F1 (um ``PhysicsCarHandle`` por driver)

    Modela:
    - Aerodinâmica realística de F1: Downforce (proporcional a v²)
    - Dinâmica Longitudinal: tração nas rodas traseiras limitada por potência
      do motor (P/v) e limite de aderência do pneu; frenagem de alta desaceleração (~5G).
    - Dinâmica Lateral (Bicycle Model + Pacejka Curve): cálculo de slip angle dianteiro
      e traseiro, saturação não-linear de aderência e momento natural de guinada (yaw).
    """

    def __init__(
        self,
        gui: bool = False,
        time_step_s: float = 1.0 / 240.0,
        gravity: Tuple[float, float, float] = (0.0, 0.0, -9.81),
        plane_lateral_friction: float = 1.0,
    ) -> None:
        self.gui = gui
        self.time_step_s = time_step_s
        self.gravity = gravity
        self.plane_lateral_friction = plane_lateral_friction
        self._client_id: Optional[int] = None
        self._plane_id: Optional[int] = None
        self._cars: Dict[str, PhysicsCarHandle] = {}
        self._initialised = False
        # Estado de câmera
        self._camera_follow_handle: Optional[PhysicsCarHandle] = None
        self._camera_overview_set: bool = False

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def init(self) -> None:
        if self._initialised:
            return
        connection_mode = p.GUI if self.gui else p.DIRECT
        client_id = p.connect(connection_mode)
        self._client_id = client_id
        if client_id < 0:
            raise RuntimeError("failed to connect to PyBullet")
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client_id)
        p.setGravity(*self.gravity, physicsClientId=client_id)
        p.setTimeStep(self.time_step_s, physicsClientId=client_id)
        self._initialised = True
        # Cria chão padrão amplo (2000x2000m em z=0) para suportar acelerações longas
        self.create_ground_plane()

    def close(self) -> None:
        if self._client_id is not None and p.isConnected(self._client_id):
            p.disconnect(physicsClientId=self._client_id)
        self._client_id = None
        self._cars = {}
        self._plane_id = None
        self._initialised = False

    def create_ground_plane(
        self,
        waypoints: Optional[Sequence[Tuple[float, float]]] = None,
        margin_m: float = 500.0,
        color: Tuple[float, float, float, float] = (0.25, 0.35, 0.18, 1.0),
    ) -> None:
        """Substitui o plano padrão (limitado, ~100x100) por um chão do tamanho
        da pista + margem. Deve ser chamado logo após ``init()``.

        Sem isso, pistas grandes (vários km) ficam maiores que o chão default do
        PyBullet, deixando vazio ao redor e causando artefatos visuais (z-fighting)
        entre a malha de asfalto e o fundo.
        """
        if not self._initialised:
            raise RuntimeError("physics not initialised; call init() first")
        cid = self._client_id

        # Remove o plano antigo (pequeno) se existir
        if self._plane_id is not None:
            try:
                p.removeBody(self._plane_id, physicsClientId=cid)
            except Exception:
                pass

        if waypoints:
            xs = [w[0] for w in waypoints]
            ys = [w[1] for w in waypoints]
            half_x = (max(xs) - min(xs)) / 2.0 + margin_m
            half_y = (max(ys) - min(ys)) / 2.0 + margin_m
            cx = (max(xs) + min(xs)) / 2.0
            cy = (max(ys) + min(ys)) / 2.0
        else:
            half_x = half_y = 1000.0
            cx = cy = 0.0

        half_thickness = 0.5
        ground_z = -half_thickness  # topo do chão fica em z=0

        col = p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=[half_x, half_y, half_thickness],
            physicsClientId=cid,
        )
        vis = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=[half_x, half_y, half_thickness],
            rgbaColor=color,
            physicsClientId=cid,
        )
        self._plane_id = p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[cx, cy, ground_z],
            physicsClientId=cid,
        )
        p.changeDynamics(
            self._plane_id, -1,
            lateralFriction=self.plane_lateral_friction,
            restitution=0.0,
            physicsClientId=cid,
        )
        

    # ------------------------------------------------------------------
    # Criação de carros
    # ------------------------------------------------------------------

    def spawn_car(
        self,
        driver_id: str,
        mass_kg: float,
        start_pos: Tuple[float, float, float] = (0.0, 0.0, 0.5),
        start_yaw_rad: float = 0.0,
        color_rgb: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
        specs: Optional[Any] = None,
    ) -> PhysicsCarHandle:
        """Cria um carro F1 no mundo físico.

        As forças aerodinâmicas, dinâmicas de pneus e tração são calculadas
        em cada sub-step e aplicadas de forma analítica no chassis.
        """
        if not self._initialised:
            raise RuntimeError("physics not initialised; call init() first")

        cid = self._client_id
        half_length = 2.5
        half_width = 0.9
        half_height = 0.35
        wheel_radius = 0.33

        # Geometria do chassis
        chassis_col = p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=[half_length, half_width, half_height],
            physicsClientId=cid,
        )
        chassis_vis = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=[half_length, half_width, half_height],
            rgbaColor=color_rgb,
            physicsClientId=cid,
        )

        orn = p.getQuaternionFromEuler([0.0, 0.0, start_yaw_rad])

        car_id = p.createMultiBody(
            baseMass=max(1.0, mass_kg),
            baseCollisionShapeIndex=chassis_col,
            baseVisualShapeIndex=chassis_vis,
            basePosition=start_pos,
            baseOrientation=orn,
            physicsClientId=cid,
        )

        # Fricção do chassis com o solo propositalmente baixa para que toda a física
        # de contato de pneus seja gerida pelo modelo analítico com downforce.
        # contactStiffness/contactDamping deixamos nos defaults do PyBullet (solver de impulso).
        p.changeDynamics(
            car_id, -1,
            lateralFriction=0.05,
            rollingFriction=0.0,
            spinningFriction=0.0,
            restitution=0.0,
            linearDamping=0.0,
            angularDamping=0.05,
            physicsClientId=cid,
        )

        power_kw = getattr(specs, "power_kw", 735.0) if specs else 735.0
        drag_coeff = getattr(specs, "drag_coeff", 0.85) if specs else 0.85
        downforce_coeff = getattr(specs, "downforce_coeff", 3.2) if specs else 3.2
        frontal_area_m2 = getattr(specs, "frontal_area_m2", 1.5) if specs else 1.5
        wheelbase_m = getattr(specs, "wheelbase_m", 3.4) if specs else 3.4

        handle = PhysicsCarHandle(
            driver_id=driver_id,
            chassis_id=car_id,
            wheel_ids=[],
            joint_ids=[],
            steering_joint_ids=[],
            drive_joint_ids=[],
            mass_kg=mass_kg,
            power_kw=power_kw,
            drag_coeff=drag_coeff,
            downforce_coeff=downforce_coeff,
            frontal_area_m2=frontal_area_m2,
            wheelbase_m=wheelbase_m,
            half_length=half_length,
            half_width=half_width,
            wheel_radius=wheel_radius,
        )
        self._cars[driver_id] = handle
        return handle

    # ------------------------------------------------------------------
    # Controle do carro
    # ------------------------------------------------------------------

    def apply_control(
        self,
        handle: PhysicsCarHandle,
        target_speed_mps: float = 0.0,
        steering_yaw_rad: float = 0.0,
        grip_multiplier: float = 1.0,
        brake: float = 0.0,
        throttle: Optional[float] = None,
    ) -> None:
        """Aplica força de tração, frenagem, downforce e steering no chassis (1 sub-step)."""
        self._apply_control_internal(
            handle,
            target_speed_mps=target_speed_mps,
            steering_yaw_rad=steering_yaw_rad,
            grip_multiplier=grip_multiplier,
            brake=brake,
            throttle=throttle,
        )

    def _apply_control_internal(
        self,
        handle: PhysicsCarHandle,
        target_speed_mps: float = 0.0,
        steering_yaw_rad: float = 0.0,
        grip_multiplier: float = 1.0,
        brake: float = 0.0,
        throttle: Optional[float] = None,
    ) -> None:
        """Orquestra as 4 fases de física analítica de F1 para 1 sub-step.

        1. :meth:`_read_chassis_state`  — cinemática atual (pos / vel / heading)
        2. :meth:`_apply_aero`          — downforce + drag + cargas verticais (Fz)
        3. :meth:`_apply_longitudinal`  — tração / freio / atrito de rolamento
        4. :meth:`_apply_lateral`       — forças laterais (Pacejka) + guinada + atrito de curva
        """
        cid    = self._client_id
        car_id = handle.chassis_id
        mass   = max(1.0, handle.mass_kg)
        g      = 9.81
        dt_sub = max(0.001, self.time_step_s)

        # Fase 1 — lê posição / orientação / velocidades do chassis
        pos, orn, forward, left, lin_vel, v_forward, v_lateral, v_speed, yaw_rate = \
            self._read_chassis_state(car_id, cid)

        # Fase 2 — aerodinâmica (downforce + drag) e cargas verticais nos eixos
        downforce, drag_magnitude, f_z_total, f_z_front, f_z_rear = \
            self._apply_aero(car_id, pos, lin_vel, v_speed, handle, mass, g, cid)

        # Fase 3 — dinâmica longitudinal (tração / freio / atrito de rolamento)
        mu_effective = handle.mu_nominal * max(0.1, grip_multiplier)
        cmd_throttle, cmd_brake = self._resolve_throttle_brake(
            throttle, brake, target_speed_mps, v_forward
        )
        drive_force, actual_brake, f_rolling, f_engine_drag, \
        v_forward, v_lateral, v_speed, yaw_rate = self._apply_longitudinal(
            car_id, pos, forward, handle,
            cmd_throttle, cmd_brake, grip_multiplier, mu_effective,
            f_z_total, f_z_rear, v_forward, v_lateral, v_speed, yaw_rate,
            mass, lin_vel, dt_sub, cid,
        )

        # Fase 4 — dinâmica lateral + guinada + atrito de curva
        dir_forward = 1.0 if v_forward >= 0 else -1.0
        total_lat_force, slip_f, slip_r, f_cornering_drag = self._apply_lateral(
            car_id, pos, forward, left,
            v_forward, v_lateral, v_speed, yaw_rate,
            float(steering_yaw_rad), mu_effective,
            f_z_front, f_z_rear, f_z_total,
            handle.wheelbase_m, dir_forward, dt_sub, mass, grip_multiplier, cid,
        )

        # Armazena telemetria no handle para leitura posterior em get_state()
        long_force = drive_force - (actual_brake + f_rolling + f_engine_drag) * dir_forward
        self._store_telemetry(
            handle, downforce, drag_magnitude, drive_force, actual_brake,
            total_lat_force, slip_f, slip_r, long_force, f_cornering_drag,
            dir_forward, f_rolling, f_engine_drag, mass, g,
        )

    # ------------------------------------------------------------------
    # Helpers de física — cada um representa uma fase do modelo analítico
    # ------------------------------------------------------------------

    def _read_chassis_state(self, car_id: int, cid: int):
        """Lê posição, orientação e velocidades no referencial local do chassis.

        Retorna
        -------
        pos, orn, forward, left, lin_vel, v_forward, v_lateral, v_speed, yaw_rate
        """
        pos, orn     = p.getBasePositionAndOrientation(car_id, physicsClientId=cid)
        lin_vel, ang_vel = p.getBaseVelocity(car_id, physicsClientId=cid)
        v_world = np.array([lin_vel[0], lin_vel[1], lin_vel[2]], dtype=float)

        rot     = np.array(p.getMatrixFromQuaternion(orn)).reshape(3, 3)
        forward = rot @ np.array([1.0, 0.0, 0.0])  # eixo longitudinal (X local)
        left    = rot @ np.array([0.0, 1.0, 0.0])  # eixo lateral    (Y local)

        v_forward = float(v_world @ forward)
        v_lateral = float(v_world @ left)
        v_speed   = math.sqrt(lin_vel[0] ** 2 + lin_vel[1] ** 2)
        yaw_rate  = float(ang_vel[2])

        return pos, orn, forward, left, lin_vel, v_forward, v_lateral, v_speed, yaw_rate

    def _apply_aero(
        self,
        car_id: int,
        pos,
        lin_vel,
        v_speed: float,
        handle: PhysicsCarHandle,
        mass: float,
        g: float,
        cid: int,
    ):
        """Aplica downforce e drag aerodinâmico; devolve cargas verticais nos eixos.

        Retorna
        -------
        downforce, drag_magnitude, f_z_total, f_z_front, f_z_rear
        """
        rho  = handle.air_density
        area = handle.frontal_area_m2
        cl   = handle.downforce_coeff
        cd   = handle.drag_coeff

        # Ambas as forças são proporcionais a v² (equação da pressão dinâmica)
        downforce      = 0.5 * rho * cl * area * (v_speed ** 2)
        drag_magnitude = 0.5 * rho * cd * area * (v_speed ** 2)

        # Downforce: força vertical para baixo no chassis
        p.applyExternalForce(
            car_id, -1,
            forceObj=[0.0, 0.0, -float(downforce)],
            posObj=pos, flags=p.WORLD_FRAME, physicsClientId=cid,
        )

        # Drag: oposto à direção de movimento no plano XY
        if v_speed > 0.01:
            v_world_xy = np.array([lin_vel[0], lin_vel[1]], dtype=float)
            drag_dir   = -v_world_xy / v_speed
            drag_vec   = drag_magnitude * np.array([drag_dir[0], drag_dir[1], 0.0])
            p.applyExternalForce(
                car_id, -1,
                forceObj=[float(drag_vec[0]), float(drag_vec[1]), 0.0],
                posObj=pos, flags=p.WORLD_FRAME, physicsClientId=cid,
            )
        else:
            drag_magnitude = 0.0

        # Carga vertical total: nunca menor que o peso estático do carro
        f_z_total = max(mass * g, (mass * g) + downforce)
        f_z_front = f_z_total * 0.45  # 45 % no eixo dianteiro
        f_z_rear  = f_z_total * 0.55  # 55 % no eixo traseiro

        return downforce, drag_magnitude, f_z_total, f_z_front, f_z_rear

    def _resolve_throttle_brake(
        self,
        throttle: Optional[float],
        brake: float,
        target_speed_mps: float,
        v_forward: float,
    ):
        """Converte o comando de entrada em ``cmd_throttle`` e ``cmd_brake`` em [0, 1].

        Dois modos:
        - ``throttle`` explícito (modo direto / gym)
        - ``target_speed_mps`` com P-controller implícito

        Retorna
        -------
        cmd_throttle, cmd_brake
        """
        if throttle is not None:
            cmd_throttle = max(0.0, min(1.0, float(throttle)))
            cmd_brake    = max(0.0, min(1.0, float(brake)))
        else:
            # P-controller: converte erro de velocidade em acelerador/freio
            v_err = target_speed_mps - v_forward
            if v_err > 0.0:
                cmd_throttle = min(1.0, v_err / 12.0)
                cmd_brake    = max(0.0, min(1.0, float(brake)))
            else:
                cmd_throttle = 0.0
                cmd_brake    = max(float(brake), min(1.0, -v_err / 18.0))
        return cmd_throttle, cmd_brake

    def _apply_longitudinal(
        self,
        car_id: int,
        pos,
        forward,
        handle: PhysicsCarHandle,
        cmd_throttle: float,
        cmd_brake: float,
        grip_multiplier: float,
        mu_effective: float,
        f_z_total: float,
        f_z_rear: float,
        v_forward: float,
        v_lateral: float,
        v_speed: float,
        yaw_rate: float,
        mass: float,
        lin_vel,
        dt_sub: float,
        cid: int,
    ):
        """Calcula e aplica força longitudinal líquida (tração − freios − atrito).

        Todos os atritos são puramente dissipativos: não invertem o sentido de marcha.

        Retorna
        -------
        drive_force, actual_brake, f_rolling, f_engine_drag,
        v_forward, v_lateral, v_speed, yaw_rate   (atualizados se parada estável)
        """
        # --- Tração (limitada por P/v e por aderência do pneu traseiro) ---
        drive_force = 0.0
        if cmd_throttle > 0.0:
            power_watts    = (handle.power_kw * 1000.0) * cmd_throttle
            f_engine       = power_watts / max(v_forward, 1.0)
            f_traction_max = mu_effective * f_z_rear
            drive_force    = min(f_engine, f_traction_max)

        # --- Frenagem (até ~5G, limitada por Fz total) ---
        brake_force = 0.0
        if cmd_brake > 0.0:
            f_brake_demand = mass * handle.brake_decel_max * cmd_brake
            f_brake_max    = mu_effective * f_z_total
            brake_force    = min(f_brake_demand, f_brake_max)

        # Orçamento dissipativo: impede que atritos revertam o sentido de marcha
        f_stop_limit = (mass * abs(v_forward) / dt_sub) if abs(v_forward) > 0.02 else 0.0
        actual_brake = min(brake_force, f_stop_limit)
        f_stop_rem   = max(0.0, f_stop_limit - actual_brake)

        # --- Atrito de rolamento (Crr ≈ 0.015 para slicks secos) ---
        c_rr       = 0.015 / max(0.2, min(1.0, float(grip_multiplier)))
        f_rolling  = min(c_rr * f_z_total, f_stop_rem)
        f_stop_rem = max(0.0, f_stop_rem - f_rolling)

        # --- Freio-motor / resistência mecânica da transmissão ---
        if cmd_throttle == 0.0 and cmd_brake == 0.0 and abs(v_forward) > 0.05:
            f_engine_drag = min(mass * 1.8, f_stop_rem)
        else:
            f_engine_drag = 0.0

        # --- Parada estável: anula velocidade residual abaixo do limiar ---
        if abs(v_forward) < 0.2 and cmd_throttle == 0.0:
            drive_force = actual_brake = f_rolling = f_engine_drag = 0.0
            p.resetBaseVelocity(
                car_id, [0.0, 0.0, lin_vel[2]], [0.0, 0.0, 0.0], physicsClientId=cid
            )
            v_forward = v_lateral = v_speed = yaw_rate = 0.0

        dir_forward    = 1.0 if v_forward >= 0 else -1.0
        long_resist    = (actual_brake + f_rolling + f_engine_drag) * dir_forward
        long_force_vec = (drive_force - long_resist) * forward

        p.applyExternalForce(
            car_id, -1,
            forceObj=[float(long_force_vec[0]), float(long_force_vec[1]), float(long_force_vec[2])],
            posObj=pos, flags=p.WORLD_FRAME, physicsClientId=cid,
        )

        return drive_force, actual_brake, f_rolling, f_engine_drag, \
               v_forward, v_lateral, v_speed, yaw_rate

    def _apply_lateral(
        self,
        car_id: int,
        pos,
        forward,
        left,
        v_forward: float,
        v_lateral: float,
        v_speed: float,
        yaw_rate: float,
        steer_angle: float,
        mu_effective: float,
        f_z_front: float,
        f_z_rear: float,
        f_z_total: float,
        wheelbase_m: float,
        dir_forward: float,
        dt_sub: float,
        mass: float,
        grip_multiplier: float,
        cid: int,
    ):
        """Aplica forças laterais (Pacejka), amortecimento lateral, atrito de curva e torque de guinada.

        Retorna
        -------
        total_lat_force, slip_f, slip_r, f_cornering_drag
        """
        a = 0.45 * wheelbase_m  # distância CG → eixo dianteiro
        b = 0.55 * wheelbase_m  # distância CG → eixo traseiro

        # Blends de velocidade e estabilidade
        stability_blend = 0.0
        if v_speed > 0.5 and abs(v_forward) > 0.1:
            stability_blend = max(0.0, min(1.0, abs(v_forward) / v_speed))
        speed_blend = min(1.0, max(0.1, v_speed / 1.5))

        # Velocidades laterais nos eixos (bicycle model)
        v_x_eff = max(abs(v_forward), 1.5)
        slip_f  = math.atan2(v_lateral + a * yaw_rate, v_x_eff) - steer_angle
        slip_r  = math.atan2(v_lateral - b * yaw_rate, v_x_eff)

        # Curva de Pacejka suavizada com rolloff
        c_alpha   = 12.0
        f_yf_peak = mu_effective * f_z_front
        f_yr_peak = mu_effective * f_z_rear

        def _pacejka(peak: float, slip: float) -> float:
            return -peak * math.tanh(c_alpha * slip) * (
                1.0 - 0.2 * (abs(slip) / (0.25 + abs(slip)))
            )

        f_yf = _pacejka(f_yf_peak, slip_f) * speed_blend * stability_blend
        f_yr = _pacejka(f_yr_peak, slip_r) * speed_blend * stability_blend

        # Força lateral total no CG, limitada pela aderência máxima
        max_lat_force   = mu_effective * f_z_total
        total_lat_force = max(-max_lat_force, min(max_lat_force,
                              (f_yf * math.cos(steer_angle)) + f_yr))
        lat_force_vec   = total_lat_force * left

        p.applyExternalForce(
            car_id, -1,
            forceObj=[float(lat_force_vec[0]), float(lat_force_vec[1]), float(lat_force_vec[2])],
            posObj=pos, flags=p.WORLD_FRAME, physicsClientId=cid,
        )

        # Atrito de curva (cornering scrub): esterço + deriva consomem energia longitudinal
        f_scrub_steer = abs(f_yf * math.sin(steer_angle))
        f_scrub_slip  = 0.35 * (abs(f_yf * math.sin(slip_f)) + abs(f_yr * math.sin(slip_r)))
        if abs(v_forward) > 0.05:
            f_cornering_drag = min(f_scrub_steer + f_scrub_slip, mass * abs(v_forward) / dt_sub)
            drag_vec = -(f_cornering_drag * dir_forward) * forward
            p.applyExternalForce(
                car_id, -1,
                forceObj=[float(drag_vec[0]), float(drag_vec[1]), float(drag_vec[2])],
                posObj=pos, flags=p.WORLD_FRAME, physicsClientId=cid,
            )
        else:
            f_cornering_drag = 0.0

        # Amortecimento lateral direto (previne slide em linha reta)
        lat_damp_force = (
            -min(max_lat_force, mass * abs(v_lateral) * 20.0)
            * math.copysign(1.0, v_lateral)
        )
        lat_damp_vec = lat_damp_force * left
        p.applyExternalForce(
            car_id, -1,
            forceObj=[float(lat_damp_vec[0]), float(lat_damp_vec[1]), 0.0],
            posObj=pos, flags=p.WORLD_FRAME, physicsClientId=cid,
        )

        # Torque de guinada orgânico + amortecimento proporcional à velocidade
        yaw_moment     = ((a * f_yf * math.cos(steer_angle)) - (b * f_yr)) * stability_blend
        yaw_damp_coeff = 0.8 + 0.4 * min(1.0, v_speed / 50.0)
        yaw_damping    = -yaw_damp_coeff * mass * yaw_rate * max(0.5, grip_multiplier)
        total_yaw      = max(-mass * 8.0, min(mass * 8.0, yaw_moment + yaw_damping))

        p.applyExternalTorque(
            car_id, -1,
            torqueObj=[0.0, 0.0, float(total_yaw)],
            flags=p.WORLD_FRAME, physicsClientId=cid,
        )

        return total_lat_force, slip_f, slip_r, f_cornering_drag

    def _store_telemetry(
        self,
        handle: PhysicsCarHandle,
        downforce: float,
        drag_magnitude: float,
        drive_force: float,
        brake_force: float,
        total_lat_force: float,
        slip_f: float,
        slip_r: float,
        long_force: float,
        f_cornering_drag: float,
        dir_forward: float,
        f_rolling: float,
        f_engine_drag: float,
        mass: float,
        g: float,
    ) -> None:
        """Persiste valores de telemetria no handle para leitura em ``get_state``."""
        handle.last_downforce_n        = float(downforce)
        handle.last_drag_n             = float(drag_magnitude)
        handle.last_drive_force_n      = float(drive_force)
        handle.last_brake_force_n      = float(brake_force)
        handle.last_lateral_force_n    = float(total_lat_force)
        handle.last_slip_f             = float(slip_f)
        handle.last_slip_r             = float(slip_r)
        handle.last_g_lat              = float(total_lat_force / (mass * g))
        handle.last_g_long             = float((long_force - f_cornering_drag * dir_forward) / (mass * g))
        handle.last_rolling_friction_n = float(f_rolling)
        handle.last_cornering_drag_n   = float(f_cornering_drag)
        handle.last_engine_brake_n     = float(f_engine_drag)
    # ------------------------------------------------------------------
    # Câmera / visualização (apenas em modo GUI)
    # ------------------------------------------------------------------

    def setup_overview_camera(self, track_center: Tuple[float, float], track_radius: float) -> None:
        """Posiciona a câmera numa vista top-down cobrindo toda a pista.

        Deve ser chamado depois que o plano e os carros foram criados.
        Só tem efeito em modo GUI.

        Parâmetros
        ----------
        track_center : (cx, cy)
            Centro aproximado da pista.
        track_radius : float
            Raio aproximado da pista (maior distância do centro a um waypoint).
        """
        if not self.gui or self._client_id is None:
            return
        cx, cy = track_center
        # Altura suficiente para ver toda a pista: ~1.5x o raio.
        cam_dist = max(track_radius * 1.5, 200.0)
        # Câmera olhando de cima (yaw=0, pitch=-90° = top-down puro)
        # pitch em radianos: -pi/2 = top-down; -pi/3 = 60° de inclinação (mais natural)
        try:
            p.resetDebugVisualizerCamera(
                cameraDistance=cam_dist,
                cameraYaw=0.0,
                cameraPitch=-50.0,   # graus (-90 = top-down puro, -50 = vista isométrica)
                cameraTargetPosition=[cx, cy, 0.0],
                physicsClientId=self._client_id,
            )
            self._camera_overview_set = True
        except Exception as exc:  # noqa: BLE001
            print(f"[physics] could not set overview camera: {exc}")

    def get_keyboard_events(self) -> dict:
        """Retorna eventos de teclado capturados na janela GUI do PyBullet."""
        if not self.gui or self._client_id is None:
            return {}
        try:
            return p.getKeyboardEvents(physicsClientId=self._client_id)
        except Exception:
            return {}

    def draw_track_lines(
        self,
        waypoints: Sequence[Tuple[float, float]],
        start_finish_waypoint: int = 0,
        color: Tuple[float, float, float] = (0.2, 0.8, 0.2),
        track_width_m: float = 12.0,
    ) -> None:
        """Desenha a linha central e a linha de chegada no PyBullet.

        Só tem efeito em modo GUI. Os waypoints contêm apenas coordenadas 2D
        ``(x, y)``; a terceira coordenada é sempre zero no mundo físico.
        """
        if not self.gui or self._client_id is None:
            return
        n = len(waypoints)
        if n < 2:
            return

        def _draw_polyline(
            points: Sequence[Tuple[float, float]],
            line_color: Tuple[float, float, float],
            width: float,
            z: float,
        ) -> None:
            for i in range(len(points)):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % len(points)]
                try:
                    p.addUserDebugLine(
                        lineFromXYZ=[x1, y1, z],
                        lineToXYZ=[x2, y2, z],
                        lineColorRGB=line_color,
                        lineWidth=width,
                        lifeTime=0.0,
                        physicsClientId=self._client_id,
                    )
                except Exception:
                    pass

        _draw_polyline(waypoints, color, 2.0, 0.05)

        # Bordas aproximadas pela largura da pista, deslocadas na normal local.
        if track_width_m > 0.0:
            half_width = track_width_m / 2.0
            left_edge: List[Tuple[float, float]] = []
            right_edge: List[Tuple[float, float]] = []
            for i in range(n):
                prev_x, prev_y = waypoints[(i - 1) % n]
                next_x, next_y = waypoints[(i + 1) % n]
                tx, ty = next_x - prev_x, next_y - prev_y
                tangent_len = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / tangent_len, tx / tangent_len
                x, y = waypoints[i]
                left_edge.append((x + nx * half_width, y + ny * half_width))
                right_edge.append((x - nx * half_width, y - ny * half_width))
            border = (0.85, 0.85, 0.9)
            _draw_polyline(left_edge, border, 1.5, 0.04)
            _draw_polyline(right_edge, border, 1.5, 0.04)

        # A linha de chegada fica perpendicular à direção local da pista.
        sf_idx = start_finish_waypoint % n
        previous_x, previous_y = waypoints[(sf_idx - 1) % n]
        next_x, next_y = waypoints[(sf_idx + 1) % n]
        tangent_x = next_x - previous_x
        tangent_y = next_y - previous_y
        tangent_length = math.hypot(tangent_x, tangent_y)
        if tangent_length > 1e-9:
            tangent_x /= tangent_length
            tangent_y /= tangent_length
        normal_x, normal_y = -tangent_y, tangent_x
        half_width = max(1.0, track_width_m / 2.0)
        sf_x, sf_y = waypoints[sf_idx]
        try:
            p.addUserDebugLine(
                lineFromXYZ=[
                    sf_x - normal_x * half_width,
                    sf_y - normal_y * half_width,
                    0.1,
                ],
                lineToXYZ=[
                    sf_x + normal_x * half_width,
                    sf_y + normal_y * half_width,
                    0.1,
                ],
                lineColorRGB=(1.0, 0.1, 0.1),
                lineWidth=4.0,
                lifeTime=0.0,
                physicsClientId=self._client_id,
            )
        except Exception:
            pass

    def set_follow_target(self, handle: Optional[PhysicsCarHandle]) -> None:
        """Define qual carro a câmera deve seguir (ou None para parar de seguir)."""
        self._camera_follow_handle = handle

    def update_camera(self) -> None:
        """Atualiza a câmera para seguir o carro alvo. Chamar a cada tick lógico.

        Mantém uma distância fixa atrás do carro, com pitch baixo para dar
        sensação de perspectiva.
        """
        if not self.gui or self._client_id is None:
            return
        if self._camera_follow_handle is None:
            return
        handle = self._camera_follow_handle
        try:
            pos, orn = p.getBasePositionAndOrientation(handle.chassis_id, physicsClientId=self._client_id)
        except Exception:
            return
        # Câmera olha para o carro de cima e um pouco atrás.
        # Distância suficiente para ver 30-50m de pista à frente.
        try:
            p.resetDebugVisualizerCamera(
                cameraDistance=60.0,
                cameraYaw=0.0,
                cameraPitch=-40.0,    # graus
                cameraTargetPosition=[pos[0], pos[1], 0.0],
                physicsClientId=self._client_id,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Step de simulação
    # ------------------------------------------------------------------

    def step(self, sub_steps: int = 8) -> None:
        """Avança ``sub_steps`` sub-passos de ``time_step_s`` cada.

        Note: ``applyExternalForce`` é consumido no primeiro ``stepSimulation``
        e resetado em seguida. Se você quer manter força constante durante
        vários sub-passos, use :meth:`step_with_control`.
        """
        if not self._initialised:
            return
        cid = self._client_id
        for _ in range(sub_steps):
            p.stepSimulation(physicsClientId=cid)

    def step_with_control(
        self,
        controls: List[Any],
        sub_steps: int = 8,
    ) -> None:
        """Avança ``sub_steps`` sub-passos reaplicando os controles a cada sub-step.

        Parâmetros
        ----------
        controls : list
            Lista de tuplas de controle:
            - (handle, target_speed, steering, grip) [4 elementos]
            - (handle, target_speed, steering, grip, brake) [5 elementos]
            - (handle, target_speed, steering, grip, brake, throttle) [6 elementos]
        sub_steps : int
            Número de sub-passos PyBullet a executar.
        """
        if not self._initialised:
            return
        cid = self._client_id
        for _ in range(sub_steps):
            for ctrl in controls:
                if len(ctrl) == 4:
                    handle, target_speed, steering, grip = ctrl
                    self._apply_control_internal(handle, target_speed, steering, grip)
                elif len(ctrl) == 5:
                    handle, target_speed, steering, grip, brake = ctrl[:5]
                    self._apply_control_internal(handle, target_speed, steering, grip, brake=brake)
                elif len(ctrl) >= 6:
                    handle, target_speed, steering, grip, brake, throttle = ctrl[:6]
                    self._apply_control_internal(
                        handle, target_speed, steering, grip, brake=brake, throttle=throttle
                    )
            p.stepSimulation(physicsClientId=cid)

    # ------------------------------------------------------------------
    # Leitura de estado
    # ------------------------------------------------------------------

    def get_state(self, handle: PhysicsCarHandle) -> Dict[str, float]:
        cid = self._client_id
        pos, orn = p.getBasePositionAndOrientation(handle.chassis_id, physicsClientId=cid)
        lin_vel, ang_vel = p.getBaseVelocity(handle.chassis_id, physicsClientId=cid)
        # heading = ângulo de yaw do chassis (eixo Z)
        euler = p.getEulerFromQuaternion(orn)
        heading_rad = euler[2]
        speed_mps = float(math.sqrt(lin_vel[0] ** 2 + lin_vel[1] ** 2))
        return {
            "x": float(pos[0]),
            "y": float(pos[1]),
            "z": float(pos[2]),
            "vx": float(lin_vel[0]),
            "vy": float(lin_vel[1]),
            "vz": float(lin_vel[2]),
            "speed_mps": speed_mps,
            "speed_kmh": float(speed_mps * 3.6),
            "heading_rad": float(heading_rad),
            "yaw_rate": float(ang_vel[2]),
            "downforce_n": handle.last_downforce_n,
            "drag_n": handle.last_drag_n,
            "drive_force_n": handle.last_drive_force_n,
            "brake_force_n": handle.last_brake_force_n,
            "lateral_force_n": handle.last_lateral_force_n,
            "rolling_friction_n": handle.last_rolling_friction_n,
            "cornering_drag_n": handle.last_cornering_drag_n,
            "slip_angle_f_deg": float(math.degrees(handle.last_slip_f)),
            "slip_angle_r_deg": float(math.degrees(handle.last_slip_r)),
            "g_lat": handle.last_g_lat,
            "g_long": handle.last_g_long,
        }

    def set_position(
        self,
        handle: PhysicsCarHandle,
        pos: Tuple[float, float, float],
        yaw_rad: float = 0.0,
        reset_vel: bool = True,
    ) -> None:
        cid = self._client_id
        orn = p.getQuaternionFromEuler([0.0, 0.0, yaw_rad])
        p.resetBasePositionAndOrientation(
            handle.chassis_id, pos, orn, physicsClientId=cid,
        )
        if reset_vel:
            p.resetBaseVelocity(handle.chassis_id, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], physicsClientId=cid)

    def get_car_handle(self, driver_id: str) -> Optional[PhysicsCarHandle]:
        return self._cars.get(driver_id)

    def all_handles(self) -> List[PhysicsCarHandle]:
        return list(self._cars.values())

    def draw_track_surface(
        self,
        waypoints: Sequence[Tuple[float, float]],
        track_width_m: float = 12.0,
        asphalt_color: Tuple[float, float, float, float] = (0.12, 0.12, 0.13, 1.0),
        z: float = 0.05,
    ) -> None:
        """Desenha a pista como uma faixa de asfalto sólida (mesh), não uma linha.

        Gera uma malha triangulada ("ribbon") entre as bordas esquerda e direita
        e a insere como corpo estático sem colisão (a física de pneu é analítica,
        então isso é puramente visual — evita conflito com o modelo de grip).
        """
        if not self.gui or self._client_id is None:
            return
        n = len(waypoints)
        if n < 3:
            return

        half_width = track_width_m / 2.0
        vertices: List[List[float]] = []
        indices: List[int] = []

        for i in range(n):
            prev_x, prev_y = waypoints[(i - 1) % n]
            next_x, next_y = waypoints[(i + 1) % n]
            tx, ty = next_x - prev_x, next_y - prev_y
            tangent_len = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / tangent_len, tx / tangent_len
            x, y = waypoints[i]
            vertices.append([x + nx * half_width, y + ny * half_width, z])  # borda esquerda
            vertices.append([x - nx * half_width, y - ny * half_width, z])  # borda direita

        for i in range(n):
            l0, r0 = 2 * i, 2 * i + 1
            l1, r1 = 2 * ((i + 1) % n), 2 * ((i + 1) % n) + 1
            indices.extend([l0, r0, r1])
            indices.extend([l0, r1, l1])

        try:
            visual_shape = p.createVisualShape(
                p.GEOM_MESH,
                vertices=vertices,
                indices=indices,
                rgbaColor=asphalt_color,
                physicsClientId=self._client_id,
            )
            p.createMultiBody(
                baseMass=0.0,
                baseCollisionShapeIndex=-1,  # só visual — sem colisão
                baseVisualShapeIndex=visual_shape,
                basePosition=[0.0, 0.0, 0.0],
                physicsClientId=self._client_id,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[physics] could not draw track surface mesh: {exc}")
