from types import SimpleNamespace
from engine.ai_engineer import AiEngineer


class Bus:
    def __init__(self):
        self.requested = []

    def latest(self, driver_id):
        self.requested.append(driver_id)
        return None


def test_only_user_is_analyzed_and_other_cars_provide_context():
    bus = Bus()
    engineer = AiEngineer('race', None, bus, None, None, 10, [], user_driver_id='user')
    positions = [
        {'driver_id': 'ahead', 'gap_to_leader_s': 0.0},
        {'driver_id': 'user', 'gap_to_leader_s': 2.0},
        {'driver_id': 'behind', 'gap_to_leader_s': 3.5},
    ]
    situations = engineer._build_situations(positions, {'lap': 1})
    assert [s.driver_id for s in situations] == ['user']
    assert situations[0].gap_ahead_s == 2.0
    assert situations[0].gap_behind_s == 1.5
    assert bus.requested == ['user']


def test_no_user_means_no_recommendations():
    engineer = AiEngineer('race', None, Bus(), SimpleNamespace(snapshot={'status': 'running'}), None, 10, [])
    assert engineer._evaluate_and_recommend() == []
