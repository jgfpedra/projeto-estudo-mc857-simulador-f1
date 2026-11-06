"""Testes da RECUPERAÇÃO de imobilização (máquina de estado com progresso).

Substitui os testes do anti-stall antigo (removido): a recuperação agora é um
MODO com histerese e saída por progresso FÍSICO, não por velocidade — o
anti-stall anterior criava um ciclo-limite parar/andar nas curvas fora da
distribuição da política (96 episódios de 0,3-1 s em 600 s de corrida).

Cenários obrigatórios (Fase G):
  1. parado com freio residual da política
  2. parado com a política insistindo em frear
  3. parado com acelerador positivo e sem movimento físico
  4. recuperação assume e MANTÉM autoridade
  5. timer não é resetável por freio residual/oscilações
  6. bloqueado por contato: torque limitado (cap na composição)
  7. estados independentes por piloto
  8. frenagem normal em curva não dispara recuperação
  +. saída exige progresso REAL; re-stall re-engata rápido (anti-chatter)
"""

import math
import sys
import types

import numpy as np
import pytest


def _ctrl():
    """NeuralRaceController sem carregar ator — só a máquina de recuperação."""
    from backend.scripts.run_race_10_cars import NeuralRaceController as N
    return object.__new__(N)


class TestRecoveryStateMachine:
    # 1 + 2: freio residual/persistente não bloqueia a recuperação
    def test_1_2_engages_despite_policy_brake(self):
        c = _ctrl()
        rec = {}
        # 1.2 s parado com freio 0.99 da política
        th, brk, act = c._recovery_step(rec, 0.0, 0.0, 0.99, 0.0, 10.0, False)
        assert not act, "dentro do timeout a política manda"
        th, brk, act = c._recovery_step(rec, 0.0, 0.0, 0.99, 1.2, 10.0, False)
        assert act and brk == 0.0 and th >= 0.25, \
            "recuperação deve vencer o freio persistente da política"

    # 3: parado com throttle positivo e sem movimento: recuperação mantém autoridade
    def test_3_positive_throttle_no_motion(self):
        c = _ctrl()
        rec = {}
        for t in (0.0, 0.5, 1.0, 1.5):
            th, brk, act = c._recovery_step(rec, 0.0, 0.6, 0.0, t, 10.0, False)
        assert act, "sem movimento físico, a recuperação engata mesmo com th>0"

    # 4: mantém autoridade até progresso REAL (não solta ao cruzar 5 m/s)
    def test_4_keeps_authority_until_real_progress(self):
        c = _ctrl()
        rec = {}
        c._recovery_step(rec, 0.0, 0.0, 0.9, 0.0, 0.0, False)   # prime: timer inicia
        _, _, act = c._recovery_step(rec, 0.0, 0.0, 0.9, 1.2, 0.0, False)
        assert act
        # carro acelerou a 6 m/s mas só andou 5 m: NÃO solta
        th, brk, act = c._recovery_step(rec, 6.0, 0.0, 0.0, 3.0, 5.0, False)
        assert act and brk == 0.0, "velocidade alta sem progresso não devolve o controle"
        # progresso suficiente: solta
        th, brk, act = c._recovery_step(rec, 8.0, 0.5, 0.0, 4.0, 26.0, False)
        assert not act, f"deveria devolver após 25 m de progresso (ganhou 26)"

    # 5: timer não reseta com freio residual; só com velocidade real
    def test_5_timer_resists_residual_brake_and_oscillation(self):
        c = _ctrl()
        rec = {}
        # 4 ticks parado freando: timer acumula (não reseta por freio)
        for t in (0.0, 0.3, 0.6, 0.9):
            c._recovery_step(rec, 0.0, 0.0, 0.9, t, 0.0, False)
        th, brk, act = c._recovery_step(rec, 0.0, 0.0, 0.9, 1.1, 0.0, False)
        assert act, "timer deve estourar apesar do freio contínuo"
        # oscilação 0->4->0 dentro do release NÃO reseta o timer
        rec2 = {}
        for t, v in ((0.0, 0.0), (0.2, 4.0), (0.4, 0.5), (0.6, 3.0), (0.8, 0.5), (1.0, 0.0)):
            _, _, a = c._recovery_step(rec2, v, 0.0, 0.5, t, 0.0, False)
        # v nunca chegou a 5 (release): timer corria; em 1.2 s engata
        _, _, act = c._recovery_step(rec2, 0.0, 0.0, 0.5, 1.2, 0.0, False)
        assert act, "oscilar abaixo de 5 m/s não pode resetar o timer"

    # 7: estados independentes por piloto
    def test_7_independent_per_driver(self):
        c = _ctrl()
        ra, rb = {}, {}
        # A parado (timer primeado em t=0); B andando a 30 m/s
        c._recovery_step(ra, 0.0, 0.0, 0.9, 0.0, 0.0, False)
        _, _, a_act = c._recovery_step(ra, 0.0, 0.0, 0.9, 1.2, 0.0, False)
        th_b, brk_b, b_act = c._recovery_step(rb, 30.0, 0.7, 0.0, 1.2, 500.0, False)
        assert a_act and not b_act and (th_b, brk_b) == (0.7, 0.0)

    # 8: frenagem normal de curva (8-12 m/s) não dispara
    def test_8_corner_deceleration_no_trigger(self):
        c = _ctrl()
        rec = {}
        for t in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0):
            th, brk, act = c._recovery_step(rec, 9.0, 0.2, 0.0, t, 50.0, False)
        assert not act and (th, brk) == (0.2, 0.0), "curva a 9 m/s não é stall"

    # +: re-stall pós-liberação re-engata rápido (anti-chatter)
    def test_restock_reengages_fast(self):
        c = _ctrl()
        rec = {}
        c._recovery_step(rec, 0.0, 0.0, 0.9, 0.0, 0.0, False)                 # prime
        _, _, _ = c._recovery_step(rec, 0.0, 0.0, 0.9, 1.2, 0.0, False)     # engata
        _, _, _ = c._recovery_step(rec, 8.0, 0.5, 0.0, 4.0, 26.0, False)   # libera
        # policy re-freou o carro imediatamente: 0.2 s parado -> re-engata
        th, brk, act = c._recovery_step(rec, 0.0, 0.0, 1.0, 4.2, 26.0, False)
        assert act and brk == 0.0, "re-stall pós-liberação deve re-engatar rápido"

    # +: fora da pista, a recuperação só zera o freio (rejoin comanda a vel.)
    def test_offtrack_recovery_zeroes_brake_only(self):
        c = _ctrl()
        rec = {}
        c._recovery_step(rec, 0.0, 0.0, 0.99, 0.0, 10.0, True)                # prime
        _, _, act = c._recovery_step(rec, 0.0, 0.0, 0.99, 1.2, 10.0, True)
        assert act
        # rejoin já setou th=0.35; recovery mantém e zera freio
        th, brk, act = c._recovery_step(rec, 3.0, 0.35, 0.0, 1.3, 12.0, True)
        assert (th, brk) == (0.35, 0.0) and act


# ------------------------------------------------ composição: cap de bloqueio

class TestBlockedContact:
    def _fake_pb(self, bodies, force=500.0):
        fake = types.ModuleType("pybullet")
        fake.getContactPoints = lambda *a, **k: [
            (0, bodies[0], bodies[1], -1, -1, (0, 0, 0), (0, 0, 0),
             (0, 0, 1), -0.001, force, 0.0, (0, 0, 0), 0.0, (0, 0, 0))]
        real = sys.modules.get("pybullet")
        sys.modules["pybullet"] = fake
        return real

    def test_6_contact_caps_throttle(self):
        from backend.scripts.run_race_10_cars import NeuralRaceController as N
        real = self._fake_pb([1, 2])
        try:
            class _H:
                chassis_id = 1
            class _H2:
                chassis_id = 2
            class _Drv:
                driver_id = "A"
            class _DrvB:
                driver_id = "B"
            class _Eng:
                class _P:
                    _client_id = 0
                physics = _P()
                handles = {"A": _H(), "B": _H2()}
            ctrl = object.__new__(N)
            drv = _Drv(); drvs = [drv, _DrvB()]
            assert ctrl._contact_with_other_car(_Eng(), drvs, 0) is True
            assert ctrl._contact_with_other_car(_Eng(), [drv], 0) is False
            # cap da composição: torque de recuperação limitado ao teto
            assert min(0.9, N.BLOCKED_THROTTLE) == N.BLOCKED_THROTTLE <= 0.3
        finally:
            if real is not None:
                sys.modules["pybullet"] = real
            else:
                sys.modules.pop("pybullet", None)
