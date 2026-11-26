"""Races without spectators release the owning simulation thread and physics."""
import threading
import time

from api.providers.race_data import FallbackProvider
from api.race_manager import RaceManager


class Store:
    def __init__(self):
        self.values = {}
        self.lock = threading.Lock()

    def ping(self):
        return True

    def set(self, key, value, ex=None):
        with self.lock:
            self.values[key] = value

    def get(self, key):
        with self.lock:
            return self.values.get(key)

    def pipeline(self, transaction=True):
        return Pipeline(self)


class Pipeline:
    def __init__(self, store):
        self.store = store
        self.writes = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def set(self, key, value, ex=None):
        self.writes[key] = value

    def publish(self, channel, message):
        pass

    def execute(self):
        with self.store.lock:
            self.store.values.update(self.writes)


def test_disconnected_races_expire_but_other_viewers_keep_their_race_running():
    manager = RaceManager(Store(), provider=FallbackProvider())
    running = []
    try:
        for _ in range(3):
            race_id, _, _ = manager.create_race(3, 'interlagos', 2023)
            running.append((race_id, manager._threads[race_id], manager._engines[race_id]))
            assert manager.attach_viewer(race_id)
        race_id, thread, engine = running[-1]
        assert manager.attach_viewer(race_id)
        manager.detach_viewer(race_id)
        for old_id, _, _ in running[:-1]:
            manager.detach_viewer(old_id)
        with manager._engines_lock:
            for viewers in manager._viewers.values():
                viewers.idle_since = time.monotonic() - 31
        for old_id, old_thread, old_engine in running[:-1]:
            old_thread.join(timeout=5)
            assert not old_thread.is_alive()
            assert not old_engine.physics._initialised
            snapshot = manager.snapshot(old_id)
            assert snapshot['status'] == 'cancelled'
            assert snapshot['classification'] is None
        assert thread.is_alive()
        assert not manager._viewer_timeout(race_id)

        manager.detach_viewer(race_id)
        assert not manager._viewer_timeout(race_id)
        assert manager.attach_viewer(race_id)
        assert thread.is_alive()
    finally:
        for race_id, thread, _ in running:
            with manager._engines_lock:
                viewers = manager._viewers.get(race_id)
                if viewers is not None:
                    viewers.count = 0
                    viewers.idle_since = time.monotonic() - 31
            thread.join(timeout=5)
    assert not manager._engines and not manager._threads and not manager._viewers


def test_race_that_is_never_opened_also_expires():
    manager = RaceManager(Store(), provider=FallbackProvider(), viewer_grace_s=0)
    race_id, _, _ = manager.create_race(3, 'interlagos', 2023)
    deadline = time.monotonic() + 5
    while race_id in manager._threads and time.monotonic() < deadline:
        time.sleep(.01)
    assert race_id not in manager._threads
    assert manager.snapshot(race_id)['status'] == 'cancelled'
