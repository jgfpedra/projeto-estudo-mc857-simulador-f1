"""VARIEDADE-1 — testes da camada de variedade opt-in (prereg b237aeb §1/§7).

t_v1: PRNG próprio — mesma (seed, N) -> mesma lista de ICs (determinismo);
      N diferente -> ICs diferentes; N=0 -> None (inércia); faixas dos pins
      (±0,5 m / ±0,3 m / mu ∈ [0,98, 1,02]).
t_v2: jitter no place_grid — carro desloca ~hypot(d_long, d_lat) do pose
      base (grid na reta — localmente reto); None = pose idêntico.
t_v3: scale_mu_nominal — fator no handle (IC de setup); canal dinâmico
      grip_multiplier intocado.
t_v4: inércia OFF + validação de faixa — defaults 0 nos dois runners;
      N<0 = fail-loud; variedade vai em LINHA DE LOG, nunca no schema.
"""
import inspect
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.run_race_10_cars import (place_grid, variedade_params,
                                             build_grid_drivers)
from backend.engine.physics import PhysicsCarHandle, PyBulletPhysics


class _MockPhysics:
    def __init__(self):
        self.poses = []

    def set_position(self, handle, pos, yaw_rad=0.0, reset_vel=True):
        self.poses.append((pos[0], pos[1]))


class _MockEngine:
    def __init__(self):
        self.physics = _MockPhysics()
        self.handles = {}
        self.states = {}
        self.last_pos = {}
        self.cum_dist_m = {}
        self.prev_waypoint_idx = {}


def _poses(jitter=None):
    from backend.model_train.f1_env import load_track_frozen
    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()
    eng = _MockEngine()
    for d in drivers:
        eng.handles[d.driver_id] = object()
        eng.states[d.driver_id] = type("S", (), {})()
    place_grid(eng, track, drivers, jitter=jitter)
    return eng.physics.poses


def test_t_v1_prng_proprio_deterministico_e_faixas():
    a1 = variedade_params(0, 1)
    a2 = variedade_params(0, 1)
    assert a1 == a2 and a1 is not None, "mesma (seed,N) deve ser bit-idêntica"
    b = variedade_params(0, 2)
    assert a1 != b, "N diferente deve gerar ICs diferentes"
    assert variedade_params(0, 0) is None, "N=0 = OFF (inércia)"
    assert variedade_params(0, -3) is None, "N<0 rejeitado no helper (argparse fail-loud)"
    assert len(a1) == 10
    for d_long, d_lat, mu_f in a1:
        assert -0.5 <= d_long <= 0.5, "pin ±0,5 m longitudinal"
        assert -0.3 <= d_lat <= 0.3, "pin ±0,3 m lateral"
        assert 0.98 <= mu_f <= 1.02, "pin mu ∈ [0,98, 1,02]"
    # tamanho parametrizável (canária --n-cars 1 futura)
    assert variedade_params(0, 1, n_cars=2) is not None


def test_t_v2_place_grid_jitter_e_inercia():
    base = _poses(None)
    jit = _poses([(0.5, 0.3)] * 10)
    assert len(base) == len(jit) == 10
    for (bx, by), (jx, jy) in zip(base, jit):
        dist = math.hypot(jx - bx, jy - by)
        # grid na RETA (localmente reto): deslocamento ≈ hypot(0,5; 0,3)
        assert abs(dist - math.hypot(0.5, 0.3)) < 0.05, \
            f"jitter deve deslocar ~0,583 m (veio {dist:.3f})"
    rep = _poses([(0.5, 0.3)] * 10)
    assert jit == rep, "mesmas ICs -> mesmas poses (determinismo)"


def test_t_v3_scale_mu_nominal():
    ph = PyBulletPhysics.__new__(PyBulletPhysics)
    ph._cars = {"ALO": PhysicsCarHandle(driver_id="ALO", chassis_id=1)}
    assert ph._cars["ALO"].mu_nominal == 1.8, "slick seco nominal (dataclass)"
    ph.scale_mu_nominal("ALO", 1.02)
    assert abs(ph._cars["ALO"].mu_nominal - 1.8 * 1.02) < 1e-12
    ph.scale_mu_nominal("ALO", 0.98)
    assert 1.764 <= ph._cars["ALO"].mu_nominal <= 1.836, \
        "banda slick [1,7, 1,9] preservada nos pins do prereg"


def test_t_v4_inercia_off_validacao_e_log_nao_schema():
    rr = (Path(__file__).resolve().parent.parent
          / 'scripts' / 'run_race_10_cars.py').read_text()
    rd = (Path(__file__).resolve().parent.parent
          / 'model_train' / 'race_diagnostic.py').read_text()
    # default 0 nos dois runners + fail-loud N<0
    for src in (rr, rd):
        assert 'add_argument("--variedade", type=int, default=0' in src \
            or "add_argument('--variedade', type=int, default=0" in src
        assert "variedade < 0" in src
    # inércia por construção: helper retorna None e o gate é `if var_params:`
    assert "if n <= 0:\n        return None" in rr
    assert rr.count("if var_params:") == 1 and rd.count("if var_params:") == 1
    # jitter default None no place_grid (bit-identidade do caminho OFF)
    sig = inspect.signature(place_grid)
    assert sig.parameters["jitter"].default is None
    # variedade vai em LINHA DE LOG/IDENTIDADE — nunca no schema do CSV
    assert "variedade={args.variedade}" in rd
    assert "VARIEDADE-1: N=" in rr and "VARIEDADE-1: N=" in rd
    assert "row['variedade']" not in rd and "row['variedade']" not in rr
