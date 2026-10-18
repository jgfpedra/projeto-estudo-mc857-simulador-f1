"""v15 FASE R7a — variância de corrida INTENCIONAL e SEMEADA (opt-in).

Domínios de CENÁRIO (nunca física): grid (ordem de largada) e compound
(atribuição de compostos por carro). Cada domínio recebe um RNG DEDICADO
derivado do seed da corrida no mesmo padrão do weather seeder (R6):
sha256("<seed>//<domain>") → random.Random(int). O np.random global NÃO é
consumidor. Default: DESLIGADO — corridas sem --variance permanecem
bit-reproduzíveis exatamente como antes (prova: teste de não-invasão).

FORA DE ESCOPO (pré-registrado R7a): qualquer jitter de grip/sf/massa/pneu.
"""
from __future__ import annotations

import hashlib
import random

VARIANCE_DOMAINS = ("grid", "compound")


def variance_rng_from_seed(run_seed: int, domain: str) -> random.Random:
    """RNG dedicado de um domínio de variância, derivado do seed da corrida.

    Mesma derivação do weather seeder (domain/weather.py, R6):
    sha256("<seed>//<domain>") → int.from_bytes(8) → random.Random.
    Instância DEDICADA por chamada — nunca compartilha stream com outro
    domínio nem com o clima (que usa o sufixo "//weather").
    """
    if domain not in VARIANCE_DOMAINS:
        raise ValueError(f"domínio de variância desconhecido: {domain!r} "
                          f"(válidos: {VARIANCE_DOMAINS})")
    digest = hashlib.sha256(f"{int(run_seed)}//{domain}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def parse_variance(spec: str):
    """Parseia a flag --variance ("off" | "grid,compound" | ...).

    Retorna um set de domínios ativos (vazio = desligado).
    """
    spec = (spec or "off").strip().lower()
    if spec in ("", "off", "none", "0"):
        return set()
    domains = {d.strip() for d in spec.split(",") if d.strip()}
    unknown = domains - set(VARIANCE_DOMAINS)
    if unknown:
        raise ValueError(f"domínios de --variance desconhecidos: {sorted(unknown)} "
                         f"(válidos: {VARIANCE_DOMAINS})")
    return domains


def shuffled_order(rng: random.Random, n: int):
    """Permutação de largada pela stream dedicada do domínio grid."""
    order = list(range(n))
    rng.shuffle(order)
    return order


def assign_compounds(rng: random.Random, driver_ids, pool):
    """Atribui compostos do POOL aos carros pela stream dedicada.

    ``pool`` é a lista de compostos da configuração atual (um por carro,
    na ordem de build_grid_drivers). A DISTRIBUIÇÃO permanece (mesmos
    compostos, mesmas contagens); só QUAL carro recebe QUAL composto é
    sorteado. Retorna dict driver_id -> composto.
    """
    if len(pool) != len(driver_ids):
        raise ValueError(f"pool de compostos ({len(pool)}) != carros ({len(driver_ids)})")
    bag = list(pool)
    rng.shuffle(bag)
    return dict(zip(driver_ids, bag))
