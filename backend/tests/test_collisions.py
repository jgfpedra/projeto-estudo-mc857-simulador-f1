"""Aviso de colisão carro×carro (CollisionEvent).

Parte 1 — lógica pura (sem PyBullet): agregação de contatos e tracker.
Parte 2 — integração com a física real: um aviso por batida, nenhum quando
longe, nada quando a opção está desligada (default).
"""

from __future__ import annotations

import pytest

from engine.collisions import CarContact, CollisionTracker, car_contacts_from_raw
from engine.events import CollisionEvent


# ---------------------------------------------------------------------------
# Helpers: tupla crua de 14 campos do pybullet.getContactPoints
# ---------------------------------------------------------------------------

def raw(body_a: int, body_b: int, force: float, xy=(0.0, 0.0), distance: float = 0.0):
    """Monta uma tupla no layout do PyBullet.

    c[1]=A, c[2]=B, c[5]=posA, c[8]=distância de contato (<0 = penetrando),
    c[9]=força normal.
    """
    return (0, body_a, body_b, -1, -1, (xy[0], xy[1], 0.0), (xy[0], xy[1], 0.0),
            (1.0, 0.0, 0.0), distance, force, 0.0, (0, 0, 0), 0.0, (0, 0, 0))


CHASSIS = {10: "drv_01", 11: "drv_02", 12: "drv_03"}
GROUND = 0


# ---------------------------------------------------------------------------
# Parte 1 — car_contacts_from_raw
# ---------------------------------------------------------------------------

def test_ignora_contato_com_o_chao():
    assert car_contacts_from_raw([raw(10, GROUND, 500.0)], CHASSIS) == []


def test_ignora_forca_abaixo_do_limiar():
    assert car_contacts_from_raw([raw(10, 11, 0.4)], CHASSIS, force_threshold_n=1.0) == []


def test_agrega_varios_pontos_do_mesmo_par_somando_forca():
    contacts = car_contacts_from_raw(
        [raw(10, 11, 100.0, xy=(1.0, 2.0)), raw(11, 10, 300.0, xy=(5.0, 6.0))],
        CHASSIS,
    )
    assert len(contacts) == 1
    c = contacts[0]
    assert c.pair == ("drv_01", "drv_02")
    assert c.normal_force_n == pytest.approx(400.0)
    assert c.position_xy == (5.0, 6.0)  # posição do ponto mais forte


def test_par_vem_em_ordem_alfabetica_independente_da_ordem_do_pybullet():
    a = car_contacts_from_raw([raw(11, 10, 50.0)], CHASSIS)[0]
    b = car_contacts_from_raw([raw(10, 11, 50.0)], CHASSIS)[0]
    assert a.pair == b.pair == ("drv_01", "drv_02")


def test_pares_diferentes_geram_contatos_separados():
    contacts = car_contacts_from_raw([raw(10, 11, 50.0), raw(11, 12, 70.0)], CHASSIS)
    assert {c.pair for c in contacts} == {("drv_01", "drv_02"), ("drv_02", "drv_03")}


def test_tupla_curta_e_ignorada_sem_erro():
    assert car_contacts_from_raw([(0, 10, 11)], CHASSIS) == []


def test_penetracao_conta_mesmo_com_forca_zero():
    """Regressão: batida moderada chega com força 0,0 no último sub-passo."""
    contacts = car_contacts_from_raw([raw(10, 11, 0.0, distance=-0.022)], CHASSIS)
    assert len(contacts) == 1
    assert contacts[0].normal_force_n == 0.0
    assert contacts[0].penetration_m == pytest.approx(0.022)


def test_penetracao_rasa_e_ignorada():
    assert car_contacts_from_raw([raw(10, 11, 0.0, distance=-0.0005)], CHASSIS) == []


def test_contato_proximo_sem_penetracao_e_ignorado():
    """distância > 0 = carros perto, mas sem se tocar."""
    assert car_contacts_from_raw([raw(10, 11, 0.0, distance=0.02)], CHASSIS) == []


def test_criterio_de_penetracao_pode_ser_desligado():
    contacts = car_contacts_from_raw(
        [raw(10, 11, 0.0, distance=-0.05)], CHASSIS, penetration_threshold_m=0.0
    )
    assert contacts == []


def test_penetracao_reportada_e_a_maior_do_par():
    contacts = car_contacts_from_raw(
        [raw(10, 11, 0.0, distance=-0.01), raw(10, 11, 0.0, distance=-0.03)], CHASSIS
    )
    assert len(contacts) == 1
    assert contacts[0].penetration_m == pytest.approx(0.03)


def test_posicao_usa_ponto_mais_fundo_quando_todas_as_forcas_sao_zero():
    contacts = car_contacts_from_raw(
        [raw(10, 11, 0.0, xy=(1.0, 1.0), distance=-0.01),
         raw(10, 11, 0.0, xy=(7.0, 8.0), distance=-0.04)],
        CHASSIS,
    )
    assert contacts[0].position_xy == (7.0, 8.0)


# ---------------------------------------------------------------------------
# Parte 1 — CollisionTracker
# ---------------------------------------------------------------------------

def _contact(pair=("drv_01", "drv_02"), force=100.0):
    return CarContact(pair[0], pair[1], force, (0.0, 0.0))


def test_tracker_avisa_so_no_primeiro_tick_do_contato():
    t = CollisionTracker(release_after_s=0.5)
    assert len(t.update([_contact()], sim_ts=1.0)) == 1
    assert t.update([_contact()], sim_ts=1.1) == []
    assert t.update([_contact()], sim_ts=1.2) == []


def test_tracker_nao_reavisa_se_o_contato_some_por_instantes():
    """Contato que pisca (some 0,2 s e volta) é a MESMA batida."""
    t = CollisionTracker(release_after_s=0.5)
    assert len(t.update([_contact()], 1.0)) == 1
    assert t.update([], 1.1) == []
    assert t.update([], 1.2) == []
    assert t.update([_contact()], 1.3) == []


def test_tracker_reavisa_depois_de_separar_de_verdade():
    t = CollisionTracker(release_after_s=0.5)
    assert len(t.update([_contact()], 1.0)) == 1
    t.update([], 1.3)
    t.update([], 1.7)          # >0,5 s sem contato: par liberado
    assert t.active_pairs == []
    assert len(t.update([_contact()], 2.0)) == 1


def test_tracker_pares_independentes():
    t = CollisionTracker()
    started = t.update([_contact(("drv_01", "drv_02")), _contact(("drv_02", "drv_03"))], 1.0)
    assert len(started) == 2
    # só o segundo par continua em contato; o primeiro não gera novo aviso
    assert t.update([_contact(("drv_02", "drv_03"))], 1.1) == []


def test_tracker_reset_limpa_estado():
    t = CollisionTracker()
    t.update([_contact()], 1.0)
    t.reset()
    assert len(t.update([_contact()], 1.1)) == 1


# ---------------------------------------------------------------------------
# CollisionEvent
# ---------------------------------------------------------------------------

def test_collision_event_serializa_para_dict():
    d = CollisionEvent(
        sim_ts=12.3, lap=2,
        driver_a_id="drv_01", driver_a_name="A", driver_b_id="drv_02", driver_b_name="B",
        position_xy=[1.0, 2.0], impact_force_n=840.5, penetration_m=0.021,
    ).to_dict()
    assert d["type"] == "collision"
    assert d["driver_a_id"] == "drv_01" and d["driver_b_id"] == "drv_02"
    assert d["position_xy"] == [1.0, 2.0]
    assert d["impact_force_n"] == 840.5
    assert d["penetration_m"] == 0.021


# ---------------------------------------------------------------------------
# Parte 2 — integração com a física real
# ---------------------------------------------------------------------------

pytest.importorskip("pybullet")

from config import DEFAULT_DRIVERS, INTERLAGOS_TRACK  # noqa: E402
from engine import InMemoryInputSource, Publisher, SimulationConfig, SimulationEngine  # noqa: E402


class ListPublisher(Publisher):
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _engine(collision_events: bool):
    pub = ListPublisher()
    cfg = SimulationConfig(
        num_laps=1, gui=False,
        input_fallback="neutral",
        collision_events=collision_events,
    )
    engine = SimulationEngine(
        config=cfg, track=INTERLAGOS_TRACK,
        drivers=list(DEFAULT_DRIVERS[:2]),
        publisher=pub,
        input_source=InMemoryInputSource(fallback_race_id="test_collisions"),
    )
    engine.setup()
    return engine, pub


def _place(engine, driver_idx: int, x: float, y: float):
    drv = engine.drivers[driver_idx]
    engine.physics.set_position(engine.handles[drv.driver_id], (x, y, 0.5), yaw_rad=0.0)


def _run(engine, ticks: int):
    dt = 1.0 / engine.config.logic_step_hz
    for _ in range(ticks):
        engine._step_tick(dt, engine.config.physics_sub_steps)


def _collisions(pub):
    return [e for e in pub.events if isinstance(e, CollisionEvent)]


def _launch_rear_end(engine, speed_mps: float, gap_m: float = 6.0):
    """Carro 0 vem na traseira do carro 1 (parado) a ``speed_mps``.

    Não se teletransporta um carro para dentro do outro: o PyBullet ejeta o
    corpo para cima (z sobe) e a "batida" dura 2 ticks sem força — não é um
    choque de verdade. Aqui o impacto acontece por movimento, como na corrida.
    """
    import pybullet as pb

    cid = engine.physics._client_id
    a, b = engine.drivers[0], engine.drivers[1]
    # chassis tem 5 m de comprimento: centros a 5 m = encostados.
    _place(engine, 0, 0.0, 0.0)
    _place(engine, 1, 5.0 + gap_m, 0.0)
    pb.resetBaseVelocity(
        engine.handles[a.driver_id].chassis_id,
        linearVelocity=[speed_mps, 0.0, 0.0],
        physicsClientId=cid,
    )


@pytest.mark.parametrize("speed_mps", [7.0, 20.0, 50.0])
def test_integracao_batida_traseira_gera_um_unico_aviso(speed_mps):
    """20 m/s (72 km/h) é a regressão: o último sub-passo reporta força 0,0.

    7 m/s (25 km/h) é um toque leve (~3 mm de penetração): garante que o limiar
    de penetração de 1 mm o pega.
    """
    engine, pub = _engine(collision_events=True)
    try:
        _launch_rear_end(engine, speed_mps)
        _run(engine, 40)
        events = _collisions(pub)
        assert len(events) == 1, f"esperava 1 aviso por batida, veio {len(events)}"
        e = events[0]
        assert {e.driver_a_id, e.driver_b_id} == {d.driver_id for d in engine.drivers}
        assert e.penetration_m > 0
        assert len(e.position_xy) == 2
    finally:
        engine.teardown()


@pytest.mark.parametrize("lateral_m", [1.80, 1.85])
def test_integracao_carros_parados_lado_a_lado_nao_geram_aviso(lateral_m):
    """Grid de largada: encostados (1,80 m = largura do chassi) ou quase, parados."""
    engine, pub = _engine(collision_events=True)
    try:
        _place(engine, 0, 0.0, 0.0)
        _place(engine, 1, 0.0, lateral_m)
        _run(engine, 60)
        assert _collisions(pub) == []
    finally:
        engine.teardown()


def test_integracao_carros_longe_nao_geram_aviso():
    engine, pub = _engine(collision_events=True)
    try:
        _place(engine, 0, 0.0, 0.0)
        _place(engine, 1, 200.0, 0.0)
        _run(engine, 15)
        assert _collisions(pub) == []
    finally:
        engine.teardown()


def test_integracao_desligado_por_padrao_nao_publica_nada():
    engine, pub = _engine(collision_events=False)
    try:
        _place(engine, 0, 0.0, 0.0)
        _place(engine, 1, 2.0, 0.0)
        _run(engine, 15)
        assert _collisions(pub) == []
    finally:
        engine.teardown()


def test_integracao_aviso_nao_altera_a_fisica():
    """Mesma cena com e sem o aviso: posições finais idênticas (só detecta)."""
    finals = []
    for flag in (False, True):
        engine, _ = _engine(collision_events=flag)
        try:
            _place(engine, 0, 0.0, 0.0)
            _place(engine, 1, 2.0, 0.0)
            _run(engine, 15)
            finals.append([
                (round(engine.states[d.driver_id].position_x, 6),
                 round(engine.states[d.driver_id].position_y, 6))
                for d in engine.drivers
            ])
        finally:
            engine.teardown()
    assert finals[0] == finals[1]
