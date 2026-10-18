"""FASE R5a 1.4 — testes do INSTRUMENTO de contato autoritativo (solver-side).

O pybullet é o solver: stepSimulation resolve colisões com impulsos reais.
O coletor (opt-in) loga getContactPoints por SUB-STEP. Testes:

(a) colisão scriptada: 2 caixas iguais, impacto central, restitution 0 →
    |Δv| de cada corpo ≈ closing/2 (analítico), momento conservado, e o log
    do solver explica o Δv OBSERVADO (Σ j_n/m ≈ Δv medido);
(b) solo sem tráfego: ZERO eventos chassis×chassis;
(c) cobertura/plumbing: carro sobrepostos em contato contínuo — eventos
    existem em TODOS os ticks e o mapeamento tick = sub//sub_steps é exato.
"""
import math
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR.parent))

from backend.engine.physics import PyBulletPhysics as PhysicsEngine


def _mk_engine():
    eng = PhysicsEngine(gui=False)
    eng.init()
    return eng


@pytest.fixture()
def eng():
    e = _mk_engine()
    yield e
    e.close()


def _vel(eng, h):
    import pybullet as p
    v, _ = p.getBaseVelocity(h.chassis_id, physicsClientId=eng._client_id)
    return v


class TestScriptedCollision:
    def test_central_impact_dv_matches_solver_log(self, eng):
        """(a) Duas caixas iguais de massa m, impacto central frontal,
        restitution 0: velocidade comum = closing/2 → |Δv| ≈ closing/2 cada.
        O Σ j_n/m logado deve explicar o Δv OBSERVADO."""
        import pybullet as p
        m = 800.0
        # gap de 1 m entre as faces (half-length 2,5): contato em ~15 sub-steps
        ha = eng.spawn_car("A", mass_kg=m, start_pos=(-3.0, 0.0, 0.5), start_yaw_rad=0.0)
        hb = eng.spawn_car("B", mass_kg=m, start_pos=(+3.0, 0.0, 0.5), start_yaw_rad=math.pi)
        eng.contact_collector = []
        v_close = 8.0
        p.resetBaseVelocity(ha.chassis_id, [v_close, 0, 0], [0, 0, 0],
                            physicsClientId=eng._client_id)
        p.resetBaseVelocity(hb.chassis_id, [-v_close, 0, 0], [0, 0, 0],
                            physicsClientId=eng._client_id)
        vA0 = _vel(eng, ha)[0]
        # 60 sub-steps (0,25 s) de balística pura — sem forças analíticas
        eng.step(sub_steps=60)
        vA1 = _vel(eng, ha)[0]
        vB1 = _vel(eng, hb)[0]
        assert len(eng.contact_collector) > 0, "sem eventos de contato no impacto"

        import pandas as pd
        ev = pd.DataFrame(eng.contact_collector)
        # (3ª lei) mesmo impulso para os dois corpos por evento
        assert ((ev.dv_a * m - ev.dv_b * m).abs() < 1e-6).all()
        jA = ev[ev.drv_a == 'A'].j_n.sum()
        # log do solver explica o Δv observado (±35% — atrito de caixa/solo)
        dv_obs = abs(vA1 - vA0)
        dv_log = jA / m
        assert dv_log > 0.1, f"impulso logado irrelevante: {dv_log:.3f} m/s"
        assert abs(dv_log - dv_obs) <= 0.35 * max(dv_obs, 1e-6) + 0.1, (
            f"|Δv| log {dv_log:.3f} vs observado {dv_obs:.3f} m/s")
        # momento central (restitution 0): corpos saem com velocidades ~iguais
        assert abs(vA1 - vB1) <= 0.35 * (2 * v_close), (
            f"impacto central deveria equalizar: vA={vA1:.2f} vB={vB1:.2f}")
        # |Δv| de cada ≈ closing/2 (analítico, tolerância de solver)
        dv_each = abs(vA1 - vA0)
        assert 0.35 * v_close <= dv_each <= 1.65 * v_close, (
            f"|Δv|={dv_each:.2f} fora da faixa analítica ±closing/2={v_close:.2f}")

    def test_solo_drive_zero_events(self, eng):
        """(b) Um carro só, dirigindo: ZERO eventos chassis×chassis."""
        h = eng.spawn_car("SOLO", mass_kg=800.0)
        eng.contact_collector = []
        for _ in range(30):  # 30 ticks de 24 sub-steps
            eng.step_with_control([(h, 12.0, 0.0, 1.0)], sub_steps=24)
        assert len(eng.contact_collector) == 0, (
            f"carro sozinho gerou {len(eng.contact_collector)} eventos carro-carro")

    def test_tick_mapping_and_coverage(self, eng):
        """(c) Dois chassis sobrepostos (contato contínuo): eventos em todos
        os ticks e o mapeamento tick = sub//sub_steps é EXATO por chunk."""
        ha = eng.spawn_car("A", mass_kg=800.0, start_pos=(0.0, 0.0, 0.5))
        hb = eng.spawn_car("B", mass_kg=800.0, start_pos=(0.0, 0.0, 0.5))
        eng.contact_collector = []
        sub = 24
        # NOTA do instrumento: o solver faz SEPARAÇÃO POSICIONAL — uma
        # sobreposição é resolvida (carros afastados) em <24 sub-steps.
        # O teste re-sobrepon a cada tick para manter contato contínuo e
        # validar o mapeamento sub//sub_steps por chunk.
        for tick in range(5):
            eng.set_position(hb, pos=(0.0, 0.0, 0.5), yaw_rad=0.0, reset_vel=True)
            n0 = eng._contact_sub_counter
            eng.step(sub_steps=sub)
            evs = [e for e in eng.contact_collector
                   if n0 <= e['sub'] < n0 + sub]
            assert evs, f"tick {tick}: sem eventos apesar de sobreposição"
            ticks_seen = {e['sub'] // sub for e in evs}
            assert ticks_seen == {tick}, (
                f"mapeamento sub//{sub} quebrou: eventos de tick {tick} "
                f"caíram em {ticks_seen}")
