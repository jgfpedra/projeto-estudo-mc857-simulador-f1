import json
from unittest.mock import patch

import redis

from api.race_manager import LivePublisher, RaceManager
from domain import TyreCompound
from engine.events import RaceStartEvent


class Store:
    def __init__(self):
        self.values = {'race:r:meta': json.dumps({'drivers': [{'driver_id': 'driver'}]}),
                       'race:r:owner': '172.29.163.21'}
    def get(self, key): return self.values.get(key)


def test_request_to_other_backend_forwards_to_owner():
    manager = RaceManager(client=Store())
    manager._distributed, manager._owner_address = True, '172.29.163.22'
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{}'
    with patch('urllib.request.urlopen', return_value=Response()) as urlopen:
        manager.request_pit_stop('r', 'driver', TyreCompound.HARD)
        req = urlopen.call_args.args[0]
        assert req.full_url == 'http://172.29.163.21:8000/races/r/drivers/driver/pit-stop'
        assert json.loads(req.data)['tyre_compound'] == 'HARD'


def test_publication_retries_failover_without_changing_snapshot(monkeypatch):
    class Pipeline:
        def __init__(self, store): self.store = store
        def set(self, *args, **kw): return self
        def publish(self, *args, **kw): return self
        def execute(self):
            self.store.calls += 1
            if self.store.calls == 1: raise redis.ConnectionError('failover')
    class Client:
        calls = 0
        def pipeline(self, **kw): return Pipeline(self)
    client = Client()
    monkeypatch.setattr('api.race_manager.time.sleep', lambda _: None)
    LivePublisher(client, 'r').publish(RaceStartEvent(sim_ts=0))
    assert client.calls == 2


def test_stale_owner_cannot_publish_a_tick():
    import pytest
    from api.race_manager import LostRaceLease

    class Pipeline:
        def watch(self, key): self.key = key
        def get(self, key): return 'new-owner'
        def reset(self): pass
    class Client:
        def pipeline(self, **kw): return Pipeline()
    publisher = LivePublisher(Client(), 'r')
    publisher.lease_token = 'old-owner'
    publisher.owner_address = '172.29.163.21'
    with pytest.raises(LostRaceLease):
        publisher.publish(RaceStartEvent(sim_ts=1))


def test_async_sentinel_pubsub_does_not_timeout_while_simulation_recovers(monkeypatch):
    from api.redis_client import async_client
    monkeypatch.setenv('REDIS_SENTINELS', 'sentinel-1:26379,sentinel-2:26379')
    client = async_client('redis://localhost:6379')
    assert client.connection_pool.connection_kwargs['socket_timeout'] is None
