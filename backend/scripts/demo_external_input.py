"""Demo: engine + keyboard publisher no MESMO processo (InMemoryInputSource compartilhado).

Cenário:
- Engine roda em background thread, consumindo inputs da InMemoryInputSource.
- Publisher (script principal) lê teclas do stdin e publica inputs.
- Engine aplica inputs imediatamente em cada tick.

Este demo é útil para validar o fluxo sem precisar de Redis.

Para testar com Redis (processos separados):
    Terminal 1: python scripts/run_sim.py --input-source redis --redis
    Terminal 2: python scripts/publish_keyboard.py --source redis --driver drv_01
"""
import sys, os, math, time, threading
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import DEFAULT_INTERLAGOS_CONFIG, DEFAULT_DRIVERS, INTERLAGOS_TRACK
from domain.weather import BASE_CONDITIONS, WeatherKind, WeatherModel, WeatherTransitionConfig
from engine import (
    SimulationEngine, InMemoryInputSource, CarInput, NullPublisher,
)

# Cria engine + source compartilhado
cfg = DEFAULT_INTERLAGOS_CONFIG
cfg.num_laps = 1
cfg.input_stale_after_s = 2.0  # tolerante para teste manual
cfg.realtime = True            # pace com tempo real
cfg.gui = True
cfg.camera_mode = "follow"

track = INTERLAGOS_TRACK
drivers = list(DEFAULT_DRIVERS)
weather = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY], config=WeatherTransitionConfig.default(0.06))
source = InMemoryInputSource()
pub = NullPublisher()

engine = SimulationEngine(
    config=cfg, track=track, drivers=drivers,
    publisher=pub, weather_model=weather,
    input_source=source,
)
engine.setup()

# Thread para rodar a engine em background
should_stop = False

def run_engine():
    global should_stop
    print("[engine] starting in background thread...")
    engine.race_started = True
    engine._publish_race_start()
    engine.weather_model.step(lap=1)
    engine._publish_weather_changed(
        prev_kind=engine.last_weather_kind,
        new_kind=engine.weather_model.current.kind,
        new_lap=1,
    )
    logic_dt = 1.0 / cfg.logic_step_hz
    sub_steps = cfg.physics_sub_steps
    last_real = time.time()
    tick = 0
    max_ticks = 600  # cap de segurança (60s de sim)
    while not should_stop and tick < max_ticks:
        engine._step_tick(logic_dt, sub_steps)
        # Realtime pacing
        elapsed = time.time() - last_real
        if elapsed < logic_dt:
            time.sleep(logic_dt - elapsed)
        last_real = time.time()
        tick += 1
    engine._publish_race_end()
    pub.flush()
    print(f"[engine] finished after {tick} ticks, sim_ts={engine.sim_ts:.1f}s")

t = threading.Thread(target=run_engine, daemon=True)  # daemon: morre com o processo
t.start()

# Pequena pausa para a engine inicializar
time.sleep(0.5)

# Publisher no thread principal: lê stdin e publica inputs
print("=" * 60)
print(" Demo: external input via shared InMemoryInputSource")
print("=" * 60)
print("Controls (type + Enter):")
print("  w = accelerate (+10 m/s)")
print("  s = brake (-10 m/s)")
print("  a = steer left  (+5°)")
print("  d = steer right (-5°)")
print("  space = handbrake (speed=0)")
print("  q = quit")
print("=" * 60)
print()

current_speed = 0.0
current_steer = 0.0
max_speed = 80.0
max_steer = math.radians(25.0)

try:
    while t.is_alive():
        try:
            line = input(f"[speed={current_speed:5.1f} m/s | steer={math.degrees(current_steer):+5.1f}°] > ").strip().lower()
        except EOFError:
            # stdin fechou (ex.: pipe terminou) — continua rodando até timeout ou q
            time.sleep(0.5)
            continue
        if not line:
            continue
        key = line[0]
        if key == "q":
            should_stop = True
            break
        elif key == " ":
            current_speed = 0.0
        elif key == "w":
            current_speed = min(max_speed, current_speed + 10.0)
        elif key == "s":
            current_speed = max(0.0, current_speed - 10.0)
        elif key == "a":
            current_steer = min(max_steer, current_steer + math.radians(5.0))
        elif key == "d":
            current_steer = max(-max_steer, current_steer - math.radians(5.0))
        else:
            print(f"  unknown key: {key!r}")
            continue
        # Publica input
        source.update_last_input(
            "drv_01",
            CarInput(target_speed_mps=current_speed, steering_yaw_rad=current_steer, brake=0.0),
            source="demo_stdin",
        )
        print(f"  published: speed={current_speed:.1f} m/s, steer={math.degrees(current_steer):+.1f}°")
except KeyboardInterrupt:
    print("\n[info] interrupted")
    should_stop = True

# Aguarda até 10s pela engine terminar (ou timeout)
deadline = time.time() + 10.0
while t.is_alive() and time.time() < deadline:
    time.sleep(0.1)
should_stop = True  # força parada se ainda rodando

t.join(timeout=2.0)
# Garante flush dos eventos
try:
    pub.flush()
    pub.close()
except Exception:
    pass
engine.teardown()
print()
print("Input source stats:", engine.get_input_source_stats())
print("Engine sim_ts:", engine.sim_ts)
