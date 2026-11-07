"""Detecção de colisões carro × carro.

Dois passos, ambos sem dependência de PyBullet (testáveis com dados sintéticos):

1. :func:`car_contacts_from_raw` — transforma os contatos crus de
   ``pybullet.getContactPoints()`` em um :class:`CarContact` por PAR de carros.
2. :class:`CollisionTracker` — guarda quais pares já estão em contato e devolve
   só os que COMEÇARAM a se tocar neste tick (um aviso por batida, não um por tick).

Este módulo só detecta. Não altera física nem aplica consequências.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

# Layout das tuplas de pybullet.getContactPoints (14 campos). Ver
# model_train/AUDITORIA_RL.md: são TUPLAS, não objetos.
_BODY_A = 1
_BODY_B = 2
_POS_ON_A = 5
_CONTACT_DISTANCE = 8   # < 0 = corpos penetrando um no outro
_NORMAL_FORCE = 9
_MIN_FIELDS = 10


@dataclass(frozen=True)
class CarContact:
    """Contato entre dois carros, agregado por par, em um passo de física."""

    driver_a_id: str
    driver_b_id: str
    normal_force_n: float
    position_xy: Tuple[float, float]
    penetration_m: float = 0.0

    @property
    def pair(self) -> Tuple[str, str]:
        return (self.driver_a_id, self.driver_b_id)


def car_contacts_from_raw(
    raw_contacts: Sequence,
    chassis_to_driver: Dict[int, str],
    force_threshold_n: float = 1.0,
    penetration_threshold_m: float = 0.001,
) -> List[CarContact]:
    """Agrega contatos crus do PyBullet em um :class:`CarContact` por par de carros.

    - Ignora contatos em que algum dos corpos não é chassi de carro (ex.: chão).
    - Um ponto de contato conta como batida se tiver força normal >=
      ``force_threshold_n`` (mesmo critério dos scripts de medição) **ou**
      penetração >= ``penetration_threshold_m``.

      O critério de penetração existe porque a força vem do ÚLTIMO sub-passo de
      física do tick: numa batida de velocidade moderada o impulso é aplicado
      num sub-passo anterior e, no último, os carros já se afastam com força
      normal 0,0 — mas ainda penetrados. Sem ele, só choques muito fortes eram
      detectados. ``penetration_threshold_m <= 0`` desliga esse critério.
    - Dois carros em contato costumam gerar vários pontos: as forças são somadas
      e a posição reportada é a do ponto mais forte (ou o mais profundo, se
      todas as forças forem 0).
    """
    # por par: lista de (força, penetração, xy)
    by_pair: Dict[Tuple[str, str], List[Tuple[float, float, Tuple[float, float]]]] = {}

    for c in raw_contacts:
        if len(c) < _MIN_FIELDS:
            continue
        drv_a = chassis_to_driver.get(c[_BODY_A])
        drv_b = chassis_to_driver.get(c[_BODY_B])
        if drv_a is None or drv_b is None or drv_a == drv_b:
            continue
        force = abs(float(c[_NORMAL_FORCE]))
        depth = max(0.0, -float(c[_CONTACT_DISTANCE]))
        by_force = force >= force_threshold_n
        by_penetration = penetration_threshold_m > 0 and depth >= penetration_threshold_m
        if not (by_force or by_penetration):
            continue
        pos = c[_POS_ON_A]
        xy = (float(pos[0]), float(pos[1]))
        key = (drv_a, drv_b) if drv_a < drv_b else (drv_b, drv_a)
        by_pair.setdefault(key, []).append((force, depth, xy))

    contacts: List[CarContact] = []
    for (a, b), points in by_pair.items():
        total = sum(f for f, _, _ in points)
        deepest = max(d for _, d, _ in points)
        strongest_xy = max(points, key=lambda p: (p[0], p[1]))[2]
        contacts.append(CarContact(a, b, total, strongest_xy, deepest))
    return contacts


class CollisionTracker:
    """Transforma "contato agora" em "contato COMEÇOU agora".

    Um mesmo choque dura vários ticks, e o PyBullet pode perder o contato por
    um instante (os carros quicam/escorregam). Por isso um par só é dado como
    separado depois de ``release_after_s`` segundos simulados sem contato; só
    então uma nova batida entre os mesmos dois carros gera novo aviso.
    """

    def __init__(self, release_after_s: float = 0.5) -> None:
        self.release_after_s = release_after_s
        self._last_contact_ts: Dict[Tuple[str, str], float] = {}

    def update(self, contacts: Iterable[CarContact], sim_ts: float) -> List[CarContact]:
        """Recebe os contatos deste tick e devolve só os que acabaram de começar."""
        started: List[CarContact] = []
        seen = set()

        for contact in contacts:
            key = contact.pair
            if key in seen:
                continue
            seen.add(key)
            if key not in self._last_contact_ts:
                started.append(contact)
            self._last_contact_ts[key] = sim_ts

        for key in list(self._last_contact_ts):
            if key not in seen and sim_ts - self._last_contact_ts[key] > self.release_after_s:
                del self._last_contact_ts[key]

        return started

    def reset(self) -> None:
        self._last_contact_ts.clear()

    @property
    def active_pairs(self) -> List[Tuple[str, str]]:
        """Pares atualmente considerados em contato (para debug/testes)."""
        return list(self._last_contact_ts)
