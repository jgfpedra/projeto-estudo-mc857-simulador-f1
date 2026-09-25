"""Simulation engine.

Orquestra o avanço da corrida:

1. Tick contínuo de física (PyBullet, 1/240 s) — controle de tração, steering,
   colisão entre carros.
2. Loop volta-a-volta — quando um carro cruza a linha de largada/chegada,
   aplica as regras de domínio: consumo de combustível, degradação de pneu,
   avaliação de transição de clima, decisão de pit stop.
3. Publicação de eventos e snapshots para o ``Publisher``.

O motor consome módulos puros do domínio (car, tyre, weather, track, driver).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from domain import (
    CarSpecs,
    CarState,
    Driver,
    DriverState,
    Track,
    TyreCompound,
    TyreModel,
    TyreState,
    TYRE_CATALOG,
    WeatherKind,
    WeatherModel,
    WeatherState,
    WeatherTransitionConfig,
    BASE_CONDITIONS,
)
from .events import (
    Event,
    LapCompletedEvent,
    PitStopEvent,
    PositionUpdateEvent,
    RaceEndEvent,
    RaceStartEvent,
    TickEvent,
    TyreWornEvent,
    WeatherChangedEvent,
)
from .physics import PhysicsCarHandle, PyBulletPhysics
from .publisher import JSONLPublisher, NullPublisher, Publisher
from .controllers import (
    CarController,
    CarInput,
    EnvironmentState,
    ExternalController,
    InputSourceController,
    ManualController,
)
from .input_source import InputEntry, InputSource, InMemoryInputSource
from .keyboard_pilot import KeyboardPilot


# ---------------------------------------------------------------------------
# Configuração da simulação
# ---------------------------------------------------------------------------

@dataclass
class SimulationConfig:
    race_id: str = "race_001"
    num_laps: int = 10
    physics_sub_steps: int = 8        # sub-passos PyBullet por step de lógica
    logic_step_hz: float = 10.0        # frequência do loop de lógica (Hz)
    position_update_every_lap: int = 1 # snapshot por volta
    pit_time_s: float = 22.0          # tempo médio de pit (reabastecimento + troca)
    fuel_threshold_kg: float = 6.0
    tyre_life_threshold: float = 18.0
    gui: bool = True
    random_seed: int = 42
    # Opções de visualização (apenas com gui=True)
    camera_mode: str = "overview"     # "overview" | "follow" | "none"
    draw_track: bool = False           # desenha racing line em GUI
    realtime: bool = False            # pausa para sincronizar com tempo real
    # Opções de input externo
    input_source_type: str = "memory"  # "memory" | "redis"
    input_fallback: str = "brake"       # "brake" (freia aos poucos) | "neutral" (parado)
    input_stale_after_s: float = 1.0    # input sem atualização há mais de N segundos → fallback


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """Orquestrador da simulação de corrida.

    Uso típico::

        engine = SimulationEngine(config, track, drivers, publisher)
        engine.setup()
        engine.run()
    """

    def __init__(
        self,
        config: SimulationConfig,
        track: Track,
        drivers: List[Driver],
        publisher: Optional[Publisher] = None,
        weather_model: Optional[WeatherModel] = None,
        input_source: Optional[InputSource] = None,
    ) -> None:
        self.config = config
        self.track = track
        self.drivers = drivers
        self.publisher = publisher or NullPublisher()
        self.weather_model = weather_model or WeatherModel(
            initial=BASE_CONDITIONS[WeatherKind.DRY],
            config=WeatherTransitionConfig.default(),
        )

        # Estado interno
        self.physics = PyBulletPhysics(gui=config.gui)
        self.states: Dict[str, DriverState] = {}
        self.handles: Dict[str, PhysicsCarHandle] = {}
        # Registry de controllers por driver_id.
        # Por default, cada driver usa InputSourceController que consome da
        # InputSource injetada (default: InMemoryInputSource).
        self.controllers: Dict[str, CarController] = {}
        self.input_source: InputSource = input_source or InMemoryInputSource()
        # Último input aplicado por driver (para inspeção/debug)
        self.last_inputs: Dict[str, CarInput] = {}
        # Última vez que um input "fresco" foi recebido (para detectar stale)
        self.last_input_ts: Dict[str, float] = {}
        # Estado do controle por teclado da janela GUI (driver[0])
        self.keyboard_pilot = KeyboardPilot()
        self.sim_ts: float = 0.0
        self.current_lap: int = 0
        self.race_started: bool = False
        self.race_finished: bool = False
        self.prev_waypoint_idx: Dict[str, int] = {}
        self.max_wp_visited: Dict[str, int] = {}
        self.lap_start_ts: Dict[str, float] = {}
        self.cum_dist_m: Dict[str, float] = {}
        self.last_pos: Dict[str, Tuple[float, float]] = {}
        self.last_tyre_warn_pct: Dict[str, float] = {}
        self.last_weather_kind: WeatherKind = self.weather_model.current.kind

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self) -> None:
        self.physics.init()
        self.keyboard_pilot.reset()
            # Chão dimensionado pela pista: sempre necessário (física + visual),
        # independente de gui=True ou False. Sem isso, em pistas grandes o chão
        # default do PyBullet (~100x100) é menor que a pista e carros podem
        # "cair" fora da área de colisão em modo headless.
        self.physics.create_ground_plane(waypoints=self.track.waypoints, margin_m=500.0)
        # Posiciona carros um pouco atrás da linha de largada, lado a lado
        sf_wp = self.track.waypoints[self.track.start_finish_waypoint]
        next_wp = self.track.waypoints[self.track.next_waypoint(self.track.start_finish_waypoint, 1)]
        # heading inicial = direção do waypoint 0 → 1
        dx = next_wp[0] - sf_wp[0]
        dy = next_wp[1] - sf_wp[1]
        initial_yaw = math.atan2(dy, dx)
        for i, drv in enumerate(self.drivers):
            state = drv.initial_state()
            self.states[drv.driver_id] = state
            px, py = self.track.initial_position(i)
            color = self._color_for_index(i)
            handle = self.physics.spawn_car(
                driver_id=drv.driver_id,
                mass_kg=state.car.total_mass,
                start_pos=(px, py, 0.5),
                start_yaw_rad=initial_yaw,
                color_rgb=color,
                specs=state.car.specs,
            )
            self.handles[drv.driver_id] = handle
            state.position_x = px
            state.position_y = py
            state.heading_rad = initial_yaw
            self.prev_waypoint_idx[drv.driver_id] = self.track.start_finish_waypoint
            self.max_wp_visited[drv.driver_id] = self.track.start_finish_waypoint
            self.lap_start_ts[drv.driver_id] = 0.0
            self.cum_dist_m[drv.driver_id] = 0.0
            self.last_pos[drv.driver_id] = (px, py)
            self.last_tyre_warn_pct[drv.driver_id] = 100.0
            # Cria InputSourceController para cada driver por default
            if drv.driver_id not in self.controllers:
                self.controllers[drv.driver_id] = InputSourceController(
                    driver_id=drv.driver_id,
                    source=self.input_source,
                    stale_after_s=self.config.input_stale_after_s,
                )

        # Configura visualização (apenas GUI)
        self._setup_visualization()

    # ------------------------------------------------------------------
    # API de input externo
    # ------------------------------------------------------------------

    def set_input_source(self, source: InputSource) -> None:
        """Troca a fonte de inputs. Recria controllers para todos os drivers."""
        self.input_source = source
        for drv in self.drivers:
            self.controllers[drv.driver_id] = InputSourceController(
                driver_id=drv.driver_id,
                source=source,
                stale_after_s=self.config.input_stale_after_s,
            )
        print(f"[engine] input source: {source.name}")

    def set_controller(self, driver_id: str, controller: CarController) -> None:
        """Define explicitamente o controller para um driver (sobrescreve o default)."""
        if driver_id not in {d.driver_id for d in self.drivers}:
            raise KeyError(f"unknown driver_id: {driver_id!r}")
        self.controllers[driver_id] = controller

    def set_driver_input(
        self,
        driver_id: str,
        target_speed_mps: float = 0.0,
        steering_yaw_rad: float = 0.0,
        brake: float = 0.0,
        grip_override: Optional[float] = None,
        throttle: Optional[float] = None,
        source: str = "api",
    ) -> None:
        """Atalho para publicar um input na fonte de inputs.

        Publica no ``input_source`` (em memória ou Redis), independente de
        qual controller está anexado ao driver. Se o controller for o
        ``InputSourceController`` default, ele vai ler este input no próximo tick.
        """
        car_input = CarInput(
            target_speed_mps=float(target_speed_mps),
            steering_yaw_rad=float(steering_yaw_rad),
            brake=float(brake),
            grip_override=grip_override,
            throttle=float(throttle) if throttle is not None else None,
        )
        self.input_source.update_last_input(driver_id, car_input, source=source)

    def get_last_input(self, driver_id: str) -> Optional[CarInput]:
        """Retorna o último input aplicado a um driver (ou None)."""
        return self.last_inputs.get(driver_id)

    def get_input_source_stats(self) -> dict:
        """Estatísticas da fonte de inputs (para debug)."""
        return self.input_source.stats()

    def _get_controller(self, driver_id: str) -> CarController:
        """Retorna o controller registrado, ou cria um InputSourceController default."""
        if driver_id not in self.controllers:
            self.controllers[driver_id] = InputSourceController(
                driver_id=driver_id,
                source=self.input_source,
                stale_after_s=self.config.input_stale_after_s,
            )
        return self.controllers[driver_id]

    def _setup_visualization(self) -> None:
        """Configura câmera inicial e desenha pista (modo GUI)."""
        if not self.config.gui:
            return
        
        # Calcula centro e raio da pista a partir dos waypoints
        xs = [w[0] for w in self.track.waypoints]
        ys = [w[1] for w in self.track.waypoints]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        radius = max(
            max(xs) - min(xs),
            max(ys) - min(ys),
        ) / 2.0
        if self.config.draw_track:
            self.physics.draw_track_surface(
                self.track.waypoints,
                track_width_m=self.track.width_m,
            )
            self.physics.draw_track_lines(
                self.track.waypoints,
                start_finish_waypoint=self.track.start_finish_waypoint,
                track_width_m=self.track.width_m,
            )
        if self.config.camera_mode == "overview":
            self.physics.setup_overview_camera((cx, cy), radius)
            print(f"[gui] overview camera set at ({cx:.0f},{cy:.0f}) radius={radius:.0f}m")
            print(f"[gui] racing line drawn ({len(self.track.waypoints)} waypoints)")
            print(f"[gui] red line = start/finish")
        elif self.config.camera_mode == "follow" and self.drivers:
            # Segue o primeiro driver
            handle = self.handles[self.drivers[0].driver_id]
            self.physics.set_follow_target(handle)
            print(f"[gui] follow camera active (following {self.drivers[0].name})")

    def _color_for_index(self, i: int) -> Tuple[float, float, float, float]:
        palette = [
            (1.0, 0.1, 0.1, 1.0),   # vermelho
            (0.1, 0.3, 1.0, 1.0),   # azul
            (0.1, 0.8, 0.2, 1.0),   # verde
            (1.0, 0.7, 0.0, 1.0),   # amarelo
            (0.8, 0.1, 0.9, 1.0),   # magenta
        ]
        return palette[i % len(palette)]

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def run(self) -> None:
        if not self.states:
            self.setup()

        self.race_started = True
        self._publish_race_start()

        logic_dt = 1.0 / max(1.0, self.config.logic_step_hz)
        # Usa o valor da config; deve satisfazer physics_sub_steps = logic_dt / time_step
        # para manter o sim_ts sincronizado com o tempo físico do PyBullet.
        physics_sub_steps = max(1, int(self.config.physics_sub_steps))
        # Sanity check: se descompassado, recalcula e avisa.
        expected_sub_steps = max(1, int(round(logic_dt / self.physics.time_step_s)))
        if physics_sub_steps != expected_sub_steps:
            print(f"[warn] physics_sub_steps={physics_sub_steps} but expected "
                  f"{expected_sub_steps} (logic_dt={logic_dt:.3f}s, time_step={self.physics.time_step_s:.4f}s). "
                  f"sim_ts will desync from physics time.")
            physics_sub_steps = expected_sub_steps

        # Etapa: dar start imediato em weather (avalia no início da volta 1)
        self.weather_model.step(lap=1)
        self._publish_weather_changed(prev_kind=self.last_weather_kind, new_kind=self.weather_model.current.kind, new_lap=1)

        # Cap de segurança: 3x o tempo esperado para a corrida
        # (~75s/volta * num_laps * 3 = generoso; evita corrida infinita)
        max_ticks = int(self.config.num_laps * 200 * 3)
        tick = 0
        last_real_time = time.time()

        while not self.race_finished and tick < max_ticks:
            self._step_tick(logic_dt, physics_sub_steps)
            # Atualiza câmera se em modo follow
            if self.config.gui and self.config.camera_mode == "follow":
                self.physics.update_camera()
            # Sincroniza com tempo real (modo realtime)
            if self.config.realtime:
                elapsed_real = time.time() - last_real_time
                if elapsed_real < logic_dt:
                    time.sleep(logic_dt - elapsed_real)
                last_real_time = time.time()
            tick += 1

        self.race_finished = True
        self._publish_race_end()
        self.publisher.flush()
        self.publisher.close()

    # ------------------------------------------------------------------
    # Step de simulação (1 tick lógico)
    # ------------------------------------------------------------------

    def _step_tick(self, dt: float, sub_steps: int) -> None:
        """Avança um tick lógico.

        Para cada carro:
        1. :meth:`_sync_driver_state`  — sincroniza estado físico → driver state
        2. :meth:`_resolve_car_input`  — busca input + fallback + timestamp stale
        3. :meth:`_compute_grip`       — calcula grip (override ou pneu+clima+surface)
        4. Empilha controle e avança a física.
        """
        if self.config.gui and self.drivers:
            self._poll_gui_keyboard(dt)

        weather      = self.weather_model.current
        weather_kind = weather.kind
        track_temp   = weather.track_temp

        env = EnvironmentState(
            sim_ts=self.sim_ts,
            lap=self.current_lap,
            weather=weather,
            track=self.track,
            all_driver_states=dict(self.states),
        )

        controls = []
        for drv in self.drivers:
            state  = self.states[drv.driver_id]
            handle = self.handles[drv.driver_id]

            # 1 — sincroniza estado físico do PyBullet no driver state
            self._sync_driver_state(state, handle)

            # Pit lane: carro parado independente do controller
            if state.pitting:
                controls.append((handle, 0.0, 0.0, 0.0, 1.0, 0.0))
                self.last_inputs[drv.driver_id] = CarInput.neutral()
                continue

            # 2 — pede input ao controller e trata ausência de input
            car_input = self._resolve_car_input(drv.driver_id, env, state)

            # 3 — calcula grip efectivo (pneu + clima + superfície)
            grip = self._compute_grip(drv.driver_id, car_input, state, weather_kind, track_temp)

            controls.append((
                handle,
                car_input.target_speed_mps,
                car_input.steering_yaw_rad,
                grip,
                car_input.brake,
                car_input.throttle,
            ))

        # 4 — avança física reaplicando os controles a cada sub-step
        self.physics.step_with_control(controls, sub_steps)
        self.sim_ts += dt

        self._check_lap_completion()
        self._publish_tick()

    # ------------------------------------------------------------------
    # Helpers de tick — extraídos de _step_tick para melhorar legibilidade
    # ------------------------------------------------------------------

    def _sync_driver_state(self, state, handle) -> None:
        """Sincroniza posição / velocidade / heading do PyBullet no driver state."""
        phys = self.physics.get_state(handle)
        state.position_x  = phys["x"]
        state.position_y  = phys["y"]
        state.heading_rad = phys["heading_rad"]
        state.velocity_mps = phys["speed_mps"]

    def _resolve_car_input(self, driver_id: str, env, state) -> "CarInput":
        """Obtém o :class:`CarInput` para o driver: controller → fallback → cache.

        Atualiza ``last_inputs`` e ``last_input_ts`` como efeito colateral.
        """
        controller = self._get_controller(driver_id)
        car_input  = controller.compute_input(env, state)

        if car_input is None:
            car_input = self._fallback_input(driver_id)

        self.last_inputs[driver_id] = car_input

        # Registra timestamp do input fresco para detecção de stale
        if isinstance(controller, InputSourceController) and controller.last_entry is not None:
            self.last_input_ts[driver_id] = controller.last_entry.ts

        return car_input

    def _compute_grip(self, driver_id: str, car_input, state, weather_kind, track_temp) -> float:
        """Calcula o grip efectivo: override explícito ou pneu × clima × surface.

        Retorna
        -------
        float
            Multiplicador de grip em [0.1, 1.5].
        """
        if car_input.grip_override is not None:
            return max(0.1, min(1.5, car_input.grip_override))

        # Grip base do composto de pneu ajustado ao clima
        grip = state.tyre.grip_multiplier(weather_kind, track_temp)

        # Factor de superfície: reduz grip fora do asfalto
        hint = self.prev_waypoint_idx.get(driver_id, self.track.start_finish_waypoint)
        dist_to_cl, new_idx = self.track.distance_to_centerline_near(
            state.position_x, state.position_y, hint_idx=hint,
        )
        self.prev_waypoint_idx[driver_id] = new_idx
        surface_factor = self.track.surface_grip_factor_from_distance(dist_to_cl)

        return max(0.3, min(1.2, grip)) * surface_factor

    def _fallback_input(self, driver_id: str) -> CarInput:
        """Input usado quando nenhum input fresco foi recebido do InputSource.

        Comportamento (configurável via ``config.input_fallback``):
        - ``brake`` (default): mantém steering do último input, decai target_speed
          gradualmente até parar. Simula um piloto que solta o acelerador.
        - ``neutral``: input totalmente neutro (speed=0, steer=0, brake=0).
          Carro para instantaneamente (pouco realista, mas útil para teste).
        """
        last_input = self.last_inputs.get(driver_id)
        fallback_mode = self.config.input_fallback

        if fallback_mode == "neutral":
            return CarInput.neutral()

        # Modo "brake": freia aos poucos
        if last_input is None:
            # Nunca recebeu input: carro parado
            return CarInput.neutral()

        # Verifica se o último input está "stale" (sem atualização há muito tempo)
        last_ts = self.last_input_ts.get(driver_id, 0.0)
        stale = (time.time() - last_ts) > self.config.input_stale_after_s if last_ts > 0 else True
        if not stale:
            # Input ainda é fresco: usa como está
            return last_input

        # Input stale: decai target_speed gradualmente (5 m/s por tick = ~50 m/s²)
        decay_rate = 5.0
        new_speed = max(0.0, last_input.target_speed_mps - decay_rate)
        # Steering decai para zero também (centro automático)
        new_steer = last_input.steering_yaw_rad * 0.9
        # Brake ativo (proporcional à velocidade restante)
        brake = 0.3 if new_speed > 0 else 1.0
        return CarInput(
            target_speed_mps=new_speed,
            steering_yaw_rad=new_steer,
            brake=brake,
        )

    def _poll_gui_keyboard(self, dt: float) -> None:
        """Lê teclas da janela GUI do PyBullet e publica o input do tick.

        A lógica de "feel" (taxa de steering, auto-centralização, lock
        sensível à velocidade, aceleração contínua) vive no
        :class:`~engine.keyboard_pilot.KeyboardPilot`; aqui só lemos os
        eventos e publicamos o resultado.

        Publica enquanto há controle ativo (tecla mantida ou estado não-zero
        do piloto), o que mantém o input "fresco" e evita que o fallback
        stale freie o carro sozinho durante a pilotagem. Com o piloto em
        repouso a engine publica nada, deixando a fonte externa (ex.:
        ``scripts/publish_keyboard.py``) assumir o controle.
        """
        if not self.drivers:
            return
        drv_id = self.drivers[0].driver_id
        state = self.states.get(drv_id)
        actual_speed = state.velocity_mps if state is not None else None
        events = self.physics.get_keyboard_events()
        car_input = self.keyboard_pilot.update(events, dt, speed_mps=actual_speed)

        pilot_idle = (
            not self.keyboard_pilot.held_keys
            and car_input.target_speed_mps <= 0.0
            and abs(car_input.steering_yaw_rad) <= 1e-9
        )
        if pilot_idle:
            return
        self.input_source.update_last_input(drv_id, car_input, source="pybullet_gui")

    # ------------------------------------------------------------------
    # (Cálculos de pace automático removidos — agora tudo vem do input externo)
    # ------------------------------------------------------------------

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        """Diferença angular normalizada para [-pi, pi]."""
        d = a - b
        while d > math.pi:
            d -= 2.0 * math.pi
        while d < -math.pi:
            d += 2.0 * math.pi
        return d

    # ------------------------------------------------------------------
    # Detecção de volta
    # ------------------------------------------------------------------

    def _check_lap_completion(self) -> None:
        """Para cada carro, detecta se cruzou a linha de largada/chegada.

        Estratégia: rastreamos a distância percorrida acumulada (sem módulo).
        Quando ``cum_dist_m`` cruza um múltiplo de ``track.length_m``,
        completamos uma volta. Isso evita falsos-positivos quando o carro
        começa a corrida ANTES da linha de largada.
        """
        for drv in self.drivers:
            state = self.states[drv.driver_id]
            if state.pitting:
                # Mesmo parado, atualiza a última posição para evitar salto
                handle = self.handles[drv.driver_id]
                phys = self.physics.get_state(handle)
                self.last_pos[drv.driver_id] = (phys["x"], phys["y"])
                continue
            handle = self.handles[drv.driver_id]
            phys = self.physics.get_state(handle)
            curr_x, curr_y = phys["x"], phys["y"]
            last_x, last_y = self.last_pos[drv.driver_id]
            dx = curr_x - last_x
            dy = curr_y - last_y
            step_dist = math.hypot(dx, dy)
            # Ignora saltos grandes (reset de posição, por exemplo)
            if step_dist < 100.0:
                self.cum_dist_m[drv.driver_id] += step_dist
            self.last_pos[drv.driver_id] = (curr_x, curr_y)

            # Detecta volta: cum_dist >= (lap_atual + 1) * track_length_m
            target_dist = (state.lap + 1) * self.track.length_m
            if self.cum_dist_m[drv.driver_id] >= target_dist:
                self._complete_lap(drv)

    def _complete_lap(self, driver: Driver) -> None:
        state = self.states[driver.driver_id]
        lap_time = self.sim_ts - self.lap_start_ts.get(driver.driver_id, 0.0)
        # Subtrai penalidade de pit pendente (aplicada no tempo)
        if state.pit_penalty_pending_s > 0:
            lap_time += state.pit_penalty_pending_s  # soma porque o carro ficou parado
            state.pit_penalty_pending_s = 0.0

        state.lap += 1
        state.last_lap_time_s = lap_time
        state.lap_times.append(lap_time)
        state.best_lap_time_s = min(state.best_lap_time_s, lap_time)
        state.total_time_s += lap_time
        self.lap_start_ts[driver.driver_id] = self.sim_ts

        # Aplica regras de domínio: consumo de combustível + degradação de pneu
        weather = self.weather_model.current
        weather_grip = weather.grip_factor

        # Combustível (car.apply_lap devolve penalidade de pace por peso)
        car_pace_penalty = state.car.apply_lap(self.track.length_km, driver.aggressive)

        # Pneu: aplica degradação e recebe penalidade de tempo por desgaste
        tyre_pace_penalty = state.tyre.apply_lap(
            self.track.length_km, weather_grip, driver.aggressive
        )

        # Ajuste de pace (não usamos diretamente aqui porque a física já
        # representa grip dinamicamente, mas logamos para auditoria).

        # Evento: volta completada
        self.publisher.publish(LapCompletedEvent(
            sim_ts=self.sim_ts,
            driver_id=driver.driver_id,
            driver_name=driver.name,
            lap=state.lap,
            lap_time_s=lap_time,
            best_lap_time_s=state.best_lap_time_s if state.best_lap_time_s != float("inf") else 0.0,
            fuel_kg=state.car.fuel_kg,
            tyre=state.tyre.to_dict(),
        ))

        # Aviso de pneu gasto (threshold)
        if state.tyre.tyre_life < 25.0 and state.tyre.tyre_life < self.last_tyre_warn_pct[driver.driver_id] - 10:
            self.publisher.publish(TyreWornEvent(
                sim_ts=self.sim_ts,
                driver_id=driver.driver_id,
                driver_name=driver.name,
                compound=state.tyre.model.compound.value,
                tyre_life_pct=state.tyre.tyre_life,
                age_laps=state.tyre.age_laps,
            ))
            self.last_tyre_warn_pct[driver.driver_id] = state.tyre.tyre_life

        # Avalia transição de clima (no início da nova volta)
        prev_kind = self.weather_model.current.kind
        new_weather = self.weather_model.step(lap=state.lap + 1)
        if new_weather.kind != prev_kind:
            self._publish_weather_changed(prev_kind=prev_kind, new_kind=new_weather.kind, new_lap=state.lap + 1)
            self.last_weather_kind = new_weather.kind

        # Decisão de pit stop
        if state.needs_pit(self.config.fuel_threshold_kg, self.config.tyre_life_threshold):
            # Escolhe pneu com base no clima atual
            new_compound = self._pick_compound_for_weather(new_weather.kind)
            # Reabastece até 70% do tanque
            fuel_to_add = state.car.specs.fuel_capacity_kg * 0.7 - state.car.fuel_kg
            fuel_to_add = max(0.0, fuel_to_add)
            # Aplica pit stop: tempo de pit
            self._perform_pit(driver, new_compound, fuel_to_add)

        # Snapshot de posições a cada volta
        if state.lap % self.config.position_update_every_lap == 0:
            self._publish_position_update(state.lap)

        # Verifica término da corrida: termina quando o PRIMEIRO piloto
        # atinge num_laps (líder da corrida). Os demais param onde estão.
        leader_laps = max(self.states[d.driver_id].lap for d in self.drivers)
        if leader_laps >= self.config.num_laps:
            self.race_finished = True

    def _pick_compound_for_weather(self, weather_kind: WeatherKind) -> TyreCompound:
        if weather_kind == WeatherKind.WET:
            return TyreCompound.WET
        if weather_kind == WeatherKind.DAMP:
            return TyreCompound.INTERMEDIATE
        # DRY/CLOUDY → soft se quiser pace, ou medium
        return TyreCompound.MEDIUM

    def _perform_pit(
        self,
        driver: Driver,
        new_compound: TyreCompound,
        fuel_to_add_kg: float,
    ) -> None:
        state = self.states[driver.driver_id]
        # Salva estado antes
        old_tyre = state.tyre.model.compound.value
        old_fuel = state.car.fuel_kg
        state.perform_pit_stop(
            new_compound=new_compound,
            fuel_to_add_kg=fuel_to_add_kg,
            pit_time_s=self.config.pit_time_s,
        )
        added = state.car.fuel_kg - old_fuel
        self.publisher.publish(PitStopEvent(
            sim_ts=self.sim_ts,
            driver_id=driver.driver_id,
            driver_name=driver.name,
            lap=state.lap,
            new_compound=new_compound.value,
            fuel_added_kg=added,
            pit_time_s=self.config.pit_time_s,
        ))

    # ------------------------------------------------------------------
    # Publicação de eventos
    # ------------------------------------------------------------------

    def _publish_race_start(self) -> None:
        self.publisher.publish(RaceStartEvent(
            sim_ts=self.sim_ts,
            race_id=self.config.race_id,
            track_name=self.track.name,
            num_laps=self.config.num_laps,
            num_drivers=len(self.drivers),
            config={
                "track_length_m": round(self.track.length_m, 1),
                "fuel_threshold_kg": self.config.fuel_threshold_kg,
                "tyre_life_threshold": self.config.tyre_life_threshold,
                "pit_time_s": self.config.pit_time_s,
                "initial_weather": self.weather_model.current.to_dict(),
            },
        ))

    def _publish_race_end(self) -> None:
        # Classificação: ordena por (a) mais voltas completadas, (b) menor tempo total
        def classification_key(d):
            s = self.states[d.driver_id]
            return (-s.lap, s.total_time_s)
        classification = []
        for d in sorted(self.drivers, key=classification_key):
            s = self.states[d.driver_id]
            classification.append({
                "position": len(classification) + 1,
                "driver_id": d.driver_id,
                "driver_name": d.name,
                "laps_completed": s.lap,
                "total_time_s": round(s.total_time_s, 3),
                "best_lap_time_s": round(s.best_lap_time_s, 3) if s.best_lap_time_s != float("inf") else None,
                "pit_stops": s.pit_stop_done,
                "fuel_remaining_kg": round(s.car.fuel_kg, 2),
                "tyre": s.tyre.to_dict(),
            })
        self.publisher.publish(RaceEndEvent(
            sim_ts=self.sim_ts,
            race_id=self.config.race_id,
            final_classification=classification,
            total_time_s=self.sim_ts,
        ))

    def _publish_weather_changed(self, prev_kind: WeatherKind, new_kind: WeatherKind, new_lap: int) -> None:
        # Busca estado anterior e atual
        prev = BASE_CONDITIONS[prev_kind]
        cur = self.weather_model.current
        self.publisher.publish(WeatherChangedEvent(
            sim_ts=self.sim_ts,
            lap=new_lap,
            previous=prev.to_dict(),
            current=cur.to_dict(),
        ))

    def _publish_position_update(self, lap: int) -> None:
        positions = [self._snapshot_position(d) for d in self.drivers]
        self.publisher.publish(PositionUpdateEvent(
            sim_ts=self.sim_ts,
            lap=lap,
            positions=positions,
        ))

    def _publish_tick(self) -> None:
        positions = [self._snapshot_position(d) for d in self.drivers]
        self.publisher.publish(TickEvent(
            sim_ts=self.sim_ts,
            lap=max(0, min(s.lap for s in self.states.values())) if self.states else 0,
            tick_in_lap=int(self.sim_ts * self.config.logic_step_hz),
            positions=positions,
            weather=self.weather_model.current.to_dict(),
        ))

    def _snapshot_position(self, driver: Driver) -> dict:
        s = self.states[driver.driver_id]
        last_input = self.last_inputs.get(driver.driver_id)
        controller = self._get_controller(driver.driver_id)
        # Verifica se o input está stale
        last_ts = self.last_input_ts.get(driver.driver_id, 0.0)
        is_stale = (
            (time.time() - last_ts) > self.config.input_stale_after_s
            if last_ts > 0 else True
        )
        return {
            "driver_id": driver.driver_id,
            "driver_name": driver.name,
            "lap": s.lap,
            "position_xy": [round(s.position_x, 2), round(s.position_y, 2)],
            "velocity_mps": round(s.velocity_mps, 2),
            "heading_deg": round(math.degrees(s.heading_rad), 1),
            "fuel_kg": round(s.car.fuel_kg, 2),
            "tyre_life_pct": round(s.tyre.tyre_life, 1),
            "tyre_compound": s.tyre.model.compound.value,
            "pitting": s.pitting,
            "controller": type(controller).__name__,
            "input_stale": is_stale,
            "last_input": {
                "target_speed_mps": round(last_input.target_speed_mps, 2) if last_input else None,
                "steering_yaw_rad": round(last_input.steering_yaw_rad, 3) if last_input else None,
                "brake": round(last_input.brake, 2) if last_input else None,
            } if last_input else None,
        }

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def teardown(self) -> None:
        self.physics.close()
        if hasattr(self.input_source, "close"):
            self.input_source.close()
