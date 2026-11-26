import importlib.util
import random
from pathlib import Path


_PATH = (Path(__file__).resolve().parents[1]
         / "scripts" / "visualization" / "random_events.py")
_spec = importlib.util.spec_from_file_location("random_events", _PATH)
random_events = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(random_events)


def test_evento_de_radio_tem_campos_esperados():
    event = random_events.build_radio_event(random.Random(1), "race_x", lap=2)
    assert event["type"] == "race_radio"
    assert event["race_id"] == "race_x"
    assert event["lap"] == 2
    assert event["state"] in {"ataque", "defesa", "economia", "cautela", "info"}
    assert event["message"].strip()


def test_semente_reproduz_a_mesma_escolha():
    a = random_events.build_radio_event(random.Random(7), "r")
    b = random_events.build_radio_event(random.Random(7), "r")
    assert a == b


def test_intervalo_respeita_os_limites():
    rng = random.Random(0)
    for _ in range(50):
        value = random_events.pick_interval(rng, 5.0, 10.0)
        assert 5.0 <= value <= 10.0


class _RedisStub:
    def __init__(self, has_state):
        self.has_state = has_state

    def exists(self, key):
        return self.has_state and key.endswith(':state')


def test_radio_espera_a_corrida_largar():
    assert random_events._race_started(_RedisStub(False), 'race_x') is False
    assert random_events._race_started(_RedisStub(True), 'race_x') is True
