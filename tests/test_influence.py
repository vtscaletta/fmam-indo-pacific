"""
Тесты матрицы межагентного влияния.

Запуск из корня проекта:
    pytest -v
"""

from engine.influence import InfluenceMatrix, INFLUENCE, CODES, ALLY


def _zero_actions():
    return {c: {"milex": 0.0, "rhet": 0.0, "drift": 0.0} for c in CODES}


def test_matrix_dimensions_and_diagonal():
    """Матрица пять на пять, агент не влияет сам на себя."""
    W = INFLUENCE.W
    assert set(W) == set(CODES)
    for i in CODES:
        assert set(W[i]) == set(CODES)
        assert W[i][i] == 0.0


def test_weights_within_unit_interval():
    """Все веса лежат в [0, 1]."""
    for i in CODES:
        for j in CODES:
            assert 0.0 <= INFLUENCE.W[i][j] <= 1.0


def test_china_is_strongest_threat_source():
    """КНР как мощнейший противник имеет наибольший суммарный вес влияния."""
    out = {i: sum(INFLUENCE.W[i][j] for j in CODES) for i in CODES}
    assert out["chn"] == max(out.values())


def test_isolated_china_buildup_hits_taiwan_hardest():
    """
    Изолированный рост расходов КНР сильнее всего повышает угрозу Тайваня,
    далее Японии. Это структура китайского давления.
    """
    acts = _zero_actions()
    acts["chn"]["milex"] = 1.0
    d = INFLUENCE.threat_delta(acts)
    ranked = sorted(d, key=d.get, reverse=True)
    assert ranked[0] == "twn"
    assert ranked[1] == "jpn"


def test_ally_buildup_does_not_threaten_partner():
    """Рост расходов США не повышает угрозу его союзников, только угрозу КНР."""
    acts = _zero_actions()
    acts["usa"]["milex"] = 1.0
    d = INFLUENCE.threat_delta(acts)
    assert d["chn"] > 0.0
    assert d["jpn"] == 0.0
    assert d["kor"] == 0.0
    assert d["twn"] == 0.0


def test_main_adversary_resolution():
    """Главный противник Японии, Тайваня и Кореи есть КНР."""
    assert INFLUENCE.main_adversary("jpn") == "chn"
    assert INFLUENCE.main_adversary("twn") == "chn"
    assert INFLUENCE.main_adversary("kor") == "chn"


def test_trust_erodes_only_for_allies():
    """
    Риторика КНР понижает доверие союзников США. Сами США и КНР, не имеющие
    старшего союзника, изменения доверия не получают.
    """
    acts = _zero_actions()
    acts["chn"]["rhet"] = 1.0
    d = INFLUENCE.trust_delta(acts)
    assert d["jpn"] < 0.0
    assert d["twn"] < 0.0
    assert d["kor"] < 0.0
    assert d["usa"] == 0.0
    assert d["chn"] == 0.0


def test_gain_scales_linearly():
    """Удвоение усиления удваивает приращение угрозы."""
    acts = _zero_actions()
    acts["chn"]["milex"] = 1.0
    low = InfluenceMatrix(gain=0.1).threat_delta(acts)["twn"]
    high = InfluenceMatrix(gain=0.2).threat_delta(acts)["twn"]
    assert abs(high - 2.0 * low) < 1e-9


def test_alliance_structure():
    """США и КНР без старшего союзника, прочие опираются на США."""
    assert ALLY["usa"] is None
    assert ALLY["chn"] is None
    assert ALLY["jpn"] == "usa"
    assert ALLY["twn"] == "usa"
    assert ALLY["kor"] == "usa"
