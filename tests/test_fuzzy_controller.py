"""
Проверки нечёткого контроллера.

Спасены из `test_module11.py` при вычистке беты. Прежний файл проверял
контроллер вперемешку с прогонами по вымышленным агентам и готовым
сценариям, вследствие чего целиком опирался на снятое поколение и
запускаться перестал. Проверки самого контроллера к тому поколению
отношения не имели и потому перенесены сюда без изменения существа.

Запуск из корня хранилища.

    pytest tests/test_fuzzy_controller.py -v
"""
from __future__ import annotations

import math

from engine.fuzzy_agent import JAPAN, JAPAN_CONFIG


def test_fuzzify_returns_three_terms_per_var():
    """Всякая переменная получает три терма со степенями в отрезке."""
    fz = JAPAN.fuzzify(0.72, 0.55, 0.65)
    for v in ("z1", "z2", "z3"):
        assert set(fz[v]) == {"low", "med", "high"}
        for degree in fz[v].values():
            assert 0.0 <= degree <= 1.0


def test_active_rules_have_structure():
    """Сработавшее правило несёт посылку, заключение и вес."""
    rules = JAPAN.active_rules(0.72, 0.55, 0.65)
    assert len(rules) > 0
    r = rules[0]
    assert set(r["if"]) == {"threat", "trust", "erosion"}
    assert set(r["then"]) == {"milex", "rhet", "drift"}
    assert 0.0 <= r["alpha"] <= 1.0


def test_all_rules_returns_twenty_seven():
    """Свод правил полон, три терма в трёх переменных дают двадцать семь."""
    rules = JAPAN.all_rules()
    assert len(rules) == 27
    keys = {(r["if"]["threat"], r["if"]["trust"], r["if"]["erosion"])
            for r in rules}
    assert len(keys) == 27


def test_all_rules_have_three_consequents():
    """Всякое правило задаёт все три исходящие величины."""
    for r in JAPAN.all_rules():
        assert set(r["then"]) == {"milex", "rhet", "drift"}


def test_mf_params_match_config():
    """Выдаваемые параметры холмов совпадают с объявленными в настройке."""
    assert JAPAN.mf_params("z1", "high") == JAPAN_CONFIG.threat.high
    assert JAPAN.mf_params("z2", "med") == JAPAN_CONFIG.trust.med
    assert JAPAN.mf_params("z3", "low") == JAPAN_CONFIG.erosion.low


def test_gauss_formula_matches_fuzzify():
    """
    Степень принадлежности, вычисленная по гауссовой формуле вручную,
    совпадает с выдаваемой контроллером. Служит порукой тому, что картинка
    функций принадлежности не разойдётся с расчётом.
    """
    z = 0.72
    fz = JAPAN.fuzzify(z, 0.5, 0.5)
    term = max(fz["z1"], key=fz["z1"].get)
    c, s = JAPAN.mf_params("z1", term)
    manual = math.exp(-((z - c) ** 2) / (2.0 * s * s))
    assert abs(manual - fz["z1"][term]) < 0.01
