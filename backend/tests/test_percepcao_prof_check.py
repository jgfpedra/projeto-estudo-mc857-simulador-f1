from scripts.analysis.percepcao_prof_check import overlap_ratio


def test_overlap_ratio_zero():
    rows = {"C01": {"taxa_prof": 0, "taxa_v10": 1}}
    assert overlap_ratio(rows) == 0.0


def test_overlap_ratio_fifty_percent():
    rows = {
        "C01": {"taxa_prof": 0.5, "taxa_v10": 1.0},
        "C02": {"taxa_prof": 0.0, "taxa_v10": 1.0},
    }
    assert overlap_ratio(rows) == 0.25


def test_overlap_ratio_full():
    rows = {"C01": {"taxa_prof": 2, "taxa_v10": 2}}
    assert overlap_ratio(rows) == 1.0
