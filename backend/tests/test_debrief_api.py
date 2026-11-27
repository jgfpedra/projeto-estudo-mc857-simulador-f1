import json

import pytest
import redis
from fastapi import HTTPException

from api import main


class Store:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def get(self, _key):
        if self.error:
            raise self.error
        return self.value


def test_get_race_debrief_returns_saved_json(monkeypatch):
    payload = {"race_id": "race_test", "resumo_geral": "Resumo da corrida"}
    monkeypatch.setattr(
        main,
        "sync_client",
        lambda _url: Store(json.dumps(payload)),
    )

    assert main.get_race_debrief("race_test") == payload


def test_get_race_debrief_returns_404_while_not_generated(monkeypatch):
    monkeypatch.setattr(main, "sync_client", lambda _url: Store())

    with pytest.raises(HTTPException) as error:
        main.get_race_debrief("race_test")
    assert error.value.status_code == 404


def test_get_race_debrief_maps_redis_failure_to_503(monkeypatch):
    monkeypatch.setattr(
        main,
        "sync_client",
        lambda _url: Store(error=redis.RedisError("offline")),
    )

    with pytest.raises(HTTPException) as error:
        main.get_race_debrief("race_test")
    assert error.value.status_code == 503


def test_get_race_debrief_rejects_corrupted_json(monkeypatch):
    monkeypatch.setattr(main, "sync_client", lambda _url: Store("not-json"))

    with pytest.raises(HTTPException) as error:
        main.get_race_debrief("race_test")
    assert error.value.status_code == 500
