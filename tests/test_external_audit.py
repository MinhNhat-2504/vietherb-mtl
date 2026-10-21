import math

from vietherb_mtl.external import strict_affinity


def test_strict_affinity_accepts_only_finite_exact_positive_values() -> None:
    assert strict_affinity(" 2.9") == 2.9
    assert strict_affinity("1.2e+3") == 1200.0
    assert strict_affinity("0") is None
    assert strict_affinity("nan") is None
    assert strict_affinity(str(math.inf)) is None


def test_strict_affinity_rejects_censored_relations() -> None:
    assert strict_affinity("<10") is None
    assert strict_affinity("> 10000") is None
    assert strict_affinity("~25") is None
