"""Keyboard input publisher.

Lê teclas no terminal (WASD / setas / espaço / Q) e publica inputs no
InputSource (InMemoryInputSource por default, ou RedisInputSource com --redis).

A engine consome esses inputs sem saber de onde vêm.

Como rodar (dois terminais):

Terminal 1 (engine):
    python scripts/run_sim.py --laps 10 --input-source memory

Terminal 2 (publisher de teclado):
    python scripts/publish_keyboard.py --driver drv_01

Controles:
    W / ↑     — acelerar (aumenta target_speed)
    S / ↓     — frear/reduzir (diminui target_speed)
    A / ←     — virar à esquerda
    D / →     — virar à direita
    Espaço    — freio de mão (target_speed = 0)
    R         — reset (zera velocidade e steering)
    Q         — sair

Notas:
- Este script usa `keyboard` library (precisa de permissão de leitura de
  /dev/input/event* no Linux). Instale com: pip install keyboard
- Alternativa sem `keyboard`: use `--stdin` para ler caracteres do stdin
  (útil para testes com echo/pipe).

Para Redis (em vez de in-memory), o publisher escreve diretamente no Redis:

    HSET race:{race_id}:input {driver_id} {json_payload}

E a engine (outro processo) lê via RedisInputSource.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from engine import CarInput, FileInputSource, InMemoryInputSource, RedisInputSource
except ImportError:
    from engine import (
        CarInput,
        FileInputSource,
        InMemoryInputSource,
        RedisInputSource,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Publish keyboard inputs to InputSource.")
    p.add_argument("--driver", default="drv_01", help="driver_id to control")
    p.add_argument(
        "--source",
        default="file",
        choices=["file", "memory", "redis"],
        help="input source: file (default, cross-process IPC without Redis), "
             "memory (in-process), or redis",
    )
    p.add_argument("--race-id", default="interlagos_001",
                   help="race_id (required for redis/file source)")
    p.add_argument("--redis-host", default="localhost")
    p.add_argument("--redis-port", type=int, default=6379)
    # Parâmetros de controle
    p.add_argument("--max-speed", type=float, default=80.0,
                   help="max target speed in m/s (default 80 = ~288 km/h)")
    p.add_argument("--accel-rate", type=float, default=20.0,
                   help="acceleration rate in m/s per second of W held")
    p.add_argument("--steer-rate", type=float, default=0.5,
                   help="steering rate in rad/s of A/D held")
    p.add_argument("--max-steer-deg", type=float, default=25.0,
                   help="max steering angle in degrees")
    p.add_argument("--stdin", action="store_true",
                   help="read keys from stdin instead of keyboard (no root needed)")
    return p.parse_args()


def make_source(args) -> "InputSource":
    if args.source == "redis":
        return RedisInputSource(
            race_id=args.race_id,
            host=args.redis_host,
            port=args.redis_port,
        )
    if args.source == "file":
        return FileInputSource(race_id=args.race_id)
    return InMemoryInputSource(fallback_race_id=args.race_id)


def main() -> int:
    args = parse_args()
    source = make_source(args)

    print("=" * 60)
    print(" Keyboard Input Publisher")
    print("=" * 60)
    print(f"  Driver:      {args.driver}")
    print(f"  Source:      {source.name}")
    if args.source == "redis":
        print(f"  Redis:       {args.redis_host}:{args.redis_port}")
        print(f"  Race ID:     {args.race_id}")
    print()
    print("Controls:")
    print("  W / ↑       — accelerate")
    print("  S / ↓       — brake / decelerate")
    print("  A / ←       — steer left")
    print("  D / →       — steer right")
    print("  SPACE       — handbrake (target_speed = 0)")
    print("  R           — reset")
    print("  Q           — quit")
    print()
    print(f"  Max speed:  {args.max_speed:.1f} m/s")
    print(f"  Accel rate: {args.accel_rate:.1f} m/s²")
    print(f"  Steer rate: {args.steer_rate:.2f} rad/s")
    print(f"  Max steer:  {args.max_steer_deg:.1f}°")
    print("=" * 60)
    print()

    max_steer_rad = math.radians(args.max_steer_deg)
    current_speed = 0.0
    current_steer = 0.0
    current_brake = 0.0
    last_publish_ts = time.time()
    last_w_press_ts = 0.0
    running = True

    # Tenta importar keyboard; se falhar, usa stdin
    kb = None
    if not args.stdin:
        try:
            import keyboard  # type: ignore
            kb = keyboard
        except ImportError:
            print("[warn] keyboard library not installed (pip install keyboard).")
            print("[warn] Falling back to --stdin mode.")
            print("[warn] Type one char + Enter to send a command:")
            print("[warn]   w=accel, s=brake, a=left, d=right, space=handbrake, r=reset, q=quit")
            args.stdin = True

    if kb is not None:
        # Hook de teclado global
        import atexit

        def cleanup():
            try:
                kb.unhook_all()
            except Exception:
                pass
        atexit.register(cleanup)

        print("[info] Listening for key presses. Press ESC or Q to quit.")
        print("[info] The engine (in another terminal) will receive inputs via InputSource.")
        print()

        def on_key(event):
            nonlocal current_speed, current_steer, current_brake, last_w_press_ts, running
            name = event.name.lower() if event.name else ""
            if name in ("q", "esc"):
                running = False
                return
            if name == "space":
                current_speed = 0.0
                current_brake = 1.0
            elif name == "r":
                current_speed = 0.0
                current_steer = 0.0
                current_brake = 0.0
            elif name in ("w", "up"):
                last_w_press_ts = time.time()
                current_speed = min(args.max_speed, current_speed + args.accel_rate * 0.1)
                current_brake = 0.0
            elif name in ("s", "down"):
                current_speed = max(0.0, current_speed - args.accel_rate * 0.15)
                current_brake = 0.5 if current_speed == 0.0 else 0.0
            elif name in ("a", "left"):
                # Virar à esquerda (positivo em radianos)
                current_steer = min(max_steer_rad, current_steer + args.steer_rate * 0.1)
                # Atrito induzido em curva (tire scrub imediato)
                current_speed = max(0.0, current_speed - max(0.4, current_speed * 0.04))
            elif name in ("d", "right"):
                # Virar à direita (negativo em radianos)
                current_steer = max(-max_steer_rad, current_steer - args.steer_rate * 0.1)
                # Atrito induzido em curva (tire scrub imediato)
                current_speed = max(0.0, current_speed - max(0.4, current_speed * 0.04))
            else:
                return

            inp = CarInput(target_speed_mps=current_speed, steering_yaw_rad=current_steer, brake=current_brake)
            source.update_last_input(args.driver, inp, source="keyboard")

        kb.on_press(on_key)

        # Loop: imprime estado na tela, aplica atrito contínuo a todo tempo e auto-decay no volante
        try:
            while running:
                now = time.time()
                dt = max(0.001, min(0.2, now - last_publish_ts))
                last_publish_ts = now

                # 1. Verifica se acelerador está sendo pressionado
                is_accelerating = False
                if kb is not None:
                    try:
                        is_accelerating = kb.is_pressed("w") or kb.is_pressed("up")
                    except Exception:
                        is_accelerating = (now - last_w_press_ts) < 0.15
                else:
                    is_accelerating = (now - last_w_press_ts) < 0.15

                # 2. Dinâmica de atrito a todo tempo
                if is_accelerating:
                    current_speed = min(args.max_speed, current_speed + args.accel_rate * dt)
                    current_brake = 0.0
                elif current_brake > 0.0:
                    current_speed = max(0.0, current_speed - (args.accel_rate * 1.5 + 8.0) * dt)
                elif current_speed > 0.0:
                    # Atrito a todo tempo quando sem acelerador:
                    # - Atrito de rolamento mecânico e freio-motor (~3.5 m/s²)
                    # - Arrasto aerodinâmico (cresce com v²)
                    # - Atrito induzido de curva ao esterçar (proporcional ao ângulo e velocidade)
                    rolling_decel = 3.5
                    aero_decel = 0.0015 * (current_speed ** 2)
                    steer_ratio = abs(current_steer) / max(0.01, max_steer_rad)
                    cornering_decel = 6.0 * steer_ratio * (current_speed / 30.0)
                    total_friction = rolling_decel + aero_decel + cornering_decel
                    current_speed = max(0.0, current_speed - total_friction * dt)

                # 3. Auto-centralização do volante quando não estiver esterçando ativamente
                is_steering = False
                if kb is not None:
                    try:
                        is_steering = (
                            kb.is_pressed("a") or kb.is_pressed("left") or
                            kb.is_pressed("d") or kb.is_pressed("right")
                        )
                    except Exception:
                        pass
                if not is_steering and abs(current_steer) > 0.001:
                    decay = args.steer_rate * dt * 1.2
                    if abs(current_steer) <= decay:
                        current_steer = 0.0
                    else:
                        current_steer -= decay * (1.0 if current_steer > 0 else -1.0)

                # 4. Publicação periódica para a engine refletir as perdas de atrito em tempo real
                inp = CarInput(target_speed_mps=current_speed, steering_yaw_rad=current_steer, brake=current_brake)
                source.update_last_input(args.driver, inp, source="keyboard")

                sys.stdout.write(
                    f"\r[speed={current_speed:5.1f} m/s ({current_speed * 3.6:5.1f} km/h) | steer={math.degrees(current_steer):+5.1f}° | brake={current_brake:.1f}]  "
                )
                sys.stdout.flush()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n[info] interrupted by user")
    else:
        # Modo stdin interativo (idêntico ao demo_external_input.py)
        print("[info] Reading from stdin. Type command char and press Enter:")
        print("  w (+10 m/s), s (-10 m/s), a (left), d (right), space (stop), r (reset), q (quit)")
        while running:
            try:
                prompt_str = f"[speed={current_speed:5.1f} m/s | steer={math.degrees(current_steer):+5.1f}° | brake={current_brake:.1f}] > "
                line = input(prompt_str).strip().lower()
                if not line:
                    continue
                key = line[0]
                if key == "q":
                    running = False
                    break
                elif key == " ":
                    current_speed = 0.0
                    current_brake = 1.0
                elif key == "r":
                    current_speed = 0.0
                    current_steer = 0.0
                    current_brake = 0.0
                elif key == "w":
                    current_speed = min(args.max_speed, current_speed + 10.0)
                    current_brake = 0.0
                elif key == "s":
                    current_speed = max(0.0, current_speed - 10.0)
                    current_brake = 0.5 if current_speed == 0.0 else 0.0
                elif key == "a":
                    current_steer = min(max_steer_rad, current_steer + math.radians(5.0))
                    # Atrito em curva
                    current_speed = max(0.0, current_speed - max(1.5, current_speed * 0.08))
                elif key == "d":
                    current_steer = max(-max_steer_rad, current_steer - math.radians(5.0))
                    # Atrito em curva
                    current_speed = max(0.0, current_speed - max(1.5, current_speed * 0.08))
                else:
                    print(f"  unknown key: {key!r} (use w, s, a, d, space, r, q)")
                    continue

                # Publica input com atrito aplicado
                inp = CarInput(target_speed_mps=current_speed, steering_yaw_rad=current_steer, brake=current_brake)
                source.update_last_input(args.driver, inp, source="keyboard_stdin")
                print(f"  -> published: speed={current_speed:.1f} m/s ({current_speed * 3.6:.1f} km/h), steer={math.degrees(current_steer):+.1f}°, brake={current_brake:.1f}")
            except (EOFError, KeyboardInterrupt):
                running = False
                break

    running = False
    source.close()
    print("\n[info] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
