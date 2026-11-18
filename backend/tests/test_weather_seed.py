"""FASE R6 1.1 — semeadura do RNG do clima (determinístico por seed).

- mesmo seed → mesma stream (reproduzível entre processos);
- seeds diferentes → streams diferentes (seeder vivo — config não morta);
- derivação documentada (sha256("<seed>//weather")) — nunca compartilha
  stream com outro RNG (instância dedicada).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.domain.weather import weather_rng_from_seed


def test_same_seed_reproduces_stream():
    a = [weather_rng_from_seed(7).random() for _ in range(10)]
    b = [weather_rng_from_seed(7).random() for _ in range(10)]
    assert a == b, "mesmo seed deve reproduzir a stream do clima"


def test_different_seeds_diverge():
    a = weather_rng_from_seed(0).random()
    b = weather_rng_from_seed(1).random()
    c = weather_rng_from_seed(2).random()
    assert len({a, b, c}) == 3, "seeds distintos devem dar streams distintas"


def test_dedicated_instance():
    r1 = weather_rng_from_seed(5)
    r2 = weather_rng_from_seed(5)
    assert r1 is not r2, "cada chamada devolve instância DEDICADA (nunca stream global)"
