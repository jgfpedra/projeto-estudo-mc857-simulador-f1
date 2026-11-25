"""FASE R7a — variância de corrida semeada (domínios de CENÁRIO).

- streams dedicadas por domínio (reproduzíveis por seed, distintas entre
  domains e entre seeds);
- parse_variance: off válido, domínios válidos, domínio desconhecido = erro;
- shuffled_order/assign_compounds: permutação válida; distribuição de
  compostos PRESERVADA (mesmo pool, só a atribuição muda).
"""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.domain.racevar import (VARIANCE_DOMAINS, variance_rng_from_seed,
                                     parse_variance, shuffled_order,
                                     assign_compounds)


def test_streams_reproducible_and_distinct():
    a = [variance_rng_from_seed(3, 'grid').random() for _ in range(0)] or None
    r1 = variance_rng_from_seed(3, 'grid'); s1 = [r1.random() for _ in range(5)]
    r2 = variance_rng_from_seed(3, 'grid'); s2 = [r2.random() for _ in range(5)]
    assert s1 == s2, "mesmo seed/domínio deve reproduzir"
    g = [variance_rng_from_seed(3, 'grid').random() for _ in range(0)]
    r3 = variance_rng_from_seed(3, 'grid'); r4 = variance_rng_from_seed(3, 'compound')
    s3 = r3.random(); s4 = r4.random()
    r5 = variance_rng_from_seed(4, 'grid'); s5 = r5.random()
    assert len({s3, s4, s5}) == 3, "domínios/seeds distintos → streams distintas"


def test_parse_variance():
    assert parse_variance('off') == set()
    assert parse_variance('') == set()
    assert parse_variance('grid') == {'grid'}
    assert parse_variance('grid,compound') == {'grid', 'compound'}
    try:
        parse_variance('grip')  # domínio físico é FORA de escopo — recusa
        raise SystemExit('deveria recusar domínio desconhecido')
    except ValueError:
        pass


def test_shuffled_order_is_permutation():
    order = shuffled_order(variance_rng_from_seed(0, 'grid'), 10)
    assert sorted(order) == list(range(10)), "permutação válida"


def test_assign_compounds_preserves_distribution():
    ids = ['A', 'B', 'C', 'D']
    pool = ['HARD', 'MEDIUM', 'MEDIUM', 'SOFT']
    m1 = assign_compounds(variance_rng_from_seed(0, 'compound'), ids, pool)
    m2 = assign_compounds(variance_rng_from_seed(0, 'compound'), ids, pool)
    assert m1 == m2, "mesma seed reproduz a atribuição"
    assert Counter(m1.values()) == Counter(pool), "distribuição PRESERVADA"
    m3 = assign_compounds(variance_rng_from_seed(1, 'compound'), ids, pool)
    assert m3 != m1, "seeds distintas devem atribuir diferente (variância material)"
