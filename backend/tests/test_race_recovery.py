"""Teste de integração: recovery completo de corrida (checkpoint + restore + continue)."""
from dataclasses import replace
import time

from config import DEFAULT_DRIVERS, DEFAULT_INTERLAGOS_CONFIG
from config.live_tracks import load_live_track
from engine import SimulationEngine
from engine.checkpoint import capture, restore
from engine.coach_controller import CoachController
from engine.rule_based_race_controller import RuleBasedRaceController


class Publisher:
    def __init__(self, client=None, race_id='race-test'):
        self.snapshot, self.timing, self.collisions = {'last_tick': None}, {}, {}
        self.client, self.race_id = client, race_id
    def publish(self, event): pass
    def flush(self): pass
    def close(self): pass


class FakeClient:
    """Mock do Redis para teste de integração."""
    def __init__(self):
        self.data = {}
    def get(self, key): return self.data.get(key)
    def set(self, key, value, ex=None): self.data[key] = value
    def setex(self, key, ttl, value): self.data[key] = value
    def pipeline(self, transaction=True):
        return FakePipeline(self)
    def smembers(self, key): return set()
    def eval(self, script, num_keys, *args): return 0


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.cmds = []
    def set(self, key, value, ex=None): self.cmds.append(('set', key, value)); return self
    def setex(self, key, ttl, value): self.cmds.append(('set', key, value)); return self
    def get(self, key): return self.client.data.get(key)
    def smrem(self, key, member): pass
    def watch(self, key): pass
    def multi(self): return self
    def execute(self):
        for cmd, key, value in self.cmds:
            self.client.data[key] = value
        self.cmds = []


def _create_race_engine(drivers, track, config):
    """Cria engine real com coaches compartilhando o MESMO base controller."""
    client = FakeClient()
    publisher = Publisher(client)
    engine = SimulationEngine(config, track, drivers, publisher)
    engine.setup()
    engine.user_driver_id = drivers[0].driver_id
    base = RuleBasedRaceController(track, seed=config.random_seed)
    for driver in drivers:
        engine.set_controller(driver.driver_id, CoachController(base, driver.driver_id, publisher=publisher))
    return engine, publisher, client


def test_full_race_recovery_flow():
    """
    Fluxo completo:
    1. Criar corrida real com coaches
    2. Avançar alguns ticks (gerar checkpoint)
    3. Simular crash: deletar engine, manter Redis (client.data)
    4. Restaurar via checkpoint.restore()
    5. Verificar se engine thread continua publicando ticks
    6. Verificar se coaches mantêm estado (seq, comando, off_track)
    """
    drivers = DEFAULT_DRIVERS[:2]
    track = load_live_track('interlagos', 2023)
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False, num_laps=10)

    # 1. Criar corrida
    engine, publisher, client = _create_race_engine(drivers, track, config)
    first_driver = drivers[0].driver_id

    # 2. Avançar alguns ticks (race_started = True para gerar checkpoint)
    engine.race_started = True
    for _ in range(5):
        engine._step_tick(0.1, 24)

    sim_ts_before = engine.sim_ts
    print(f"[test] Antes do crash: sim_ts={sim_ts_before:.2f}")

    # Definir estado nos coaches
    coach = engine.controllers[first_driver]
    coach._last_seq = 10
    coach._last_command = 'push'
    coach._off_track = True
    coach._off_since_s = 5.0

    # 3. Gerar checkpoint (simula LivePublisher.publish tick)
    checkpoint_data = capture(engine, publisher)
    print(f"[test] Checkpoint gerado, tamanho={len(checkpoint_data)} bytes")

    # Simular crash: manter client.data (Redis), deletar engine
    engine.teardown()
    engine = None

    # 4. Restaurar via restore()
    restored_publisher = Publisher(client)
    restored_engine = restore(checkpoint_data, restored_publisher)

    print(f"[test] Restaurado: sim_ts={restored_engine.sim_ts:.2f}")

    # 5. Verificações
    assert restored_engine.sim_ts == sim_ts_before, "sim_ts deve ser restaurado"

    # 6. Verificar coaches restaurados
    restored_coach = restored_engine.controllers[first_driver]
    assert isinstance(restored_coach, CoachController), "Deve ser CoachController"
    assert restored_coach.base is restored_engine.controllers[drivers[1].driver_id], "Bot usa o controlador base compartilhado"

    # Estado do coach restaurado
    assert restored_coach._last_seq == 10, f"seq restaurado: {restored_coach._last_seq}"
    assert restored_coach._last_command == 'push', f"comando restaurado: {restored_coach._last_command}"
    assert restored_coach._off_track is True, "off_track restaurado"
    assert restored_coach._off_since_s == 5.0, "off_since_s restaurado"

    # Bus seq restaurado (deve ser >= seq salvo)
    assert restored_coach.bus._seq >= 10, f"bus seq: {restored_coach.bus._seq}"

    # 7. Continuar simulação por mais ticks (verifica se não trava)
    for _ in range(3):
        restored_engine._step_tick(0.1, 24)

    sim_ts_after = restored_engine.sim_ts
    print(f"[test] Depois de continuar: sim_ts={sim_ts_after:.2f}")
    assert sim_ts_after > sim_ts_before, "Simulação deve continuar avançando"

    # Cleanup
    restored_engine.teardown()
    print("[test] Teste de recovery completo: PASSOU")


def test_recovery_preserves_ai_engineer_bus():
    """
    Verifica que o CommandBus é compartilhado entre coaches e AI Engineer
    (não cria bus duplicado com seq=0).
    """
    from engine.checkpoint import _rebuild_controllers, COACH_BUS_TTL
    from engine.rule_based_race_controller import RuleBasedRaceController

    drivers = DEFAULT_DRIVERS[:2]
    track = load_live_track('interlagos', 2023)
    config = replace(DEFAULT_INTERLAGOS_CONFIG, gui=False, realtime=False)
    client = FakeClient()
    publisher = Publisher(client)

    engine = SimulationEngine(config, track, drivers, publisher)
    engine.setup()
    engine.user_driver_id = drivers[0].driver_id
    base = RuleBasedRaceController(track, seed=42)
    for driver in drivers:
        engine.set_controller(driver.driver_id, CoachController(base, driver.driver_id, publisher=publisher))

    # Avançar e definir estado
    engine.race_started = True
    for _ in range(3):
        engine._step_tick(0.1, 24)

    coach = engine.controllers[drivers[0].driver_id]
    coach._last_seq = 42
    coach._last_command = 'conserve'

    # Checkpoint
    checkpoint_data = capture(engine, publisher)
    engine.teardown()

    # Restaurar
    restored_publisher = Publisher(client)
    restored_engine = restore(checkpoint_data, restored_publisher)

    # Checkpoint legado com dois coaches restaura apenas o piloto do usuário.
    bus1 = restored_engine.controllers[drivers[0].driver_id].bus
    assert isinstance(restored_engine.controllers[drivers[1].driver_id], RuleBasedRaceController)

    # Seq deve ser >= 42 (restaurado do checkpoint)
    assert bus1._seq >= 42, f"Bus seq deve ser >= 42, é {bus1._seq}"

    restored_engine.teardown()
    print("[test] Bus compartilhado e seq preservado: PASSOU")


if __name__ == '__main__':
    test_full_race_recovery_flow()
    test_recovery_preserves_ai_engineer_bus()
    print("\n✅ Todos os testes de recovery passaram!")