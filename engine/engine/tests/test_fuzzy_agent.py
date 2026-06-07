"""
Тесты нечёткого контроллера агента "Япония".

Запуск из корня проекта:
    pytest -v
или без pytest:
    python -m tests.test_fuzzy_agent
"""

import numpy as np
from engine.fuzzy_agent import FuzzyAgent, JAPAN_CONFIG


def test_membership_matches_dissertation():
    """Степени принадлежности при z=(0.72, 0.55, 0.65) воспроизводят эталон."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    f = agent.fuzzify(0.72, 0.55, 0.65)
    assert abs(f["z1"]["med"] - 0.34) < 0.02
    assert abs(f["z1"]["high"] - 0.60) < 0.02
    assert abs(f["z2"]["med"] - 0.82) < 0.02
    assert abs(f["z2"]["low"] - 0.18) < 0.02
    assert abs(f["z3"]["med"] - 0.52) < 0.02
    assert abs(f["z3"]["high"] - 0.48) < 0.02


def test_dominant_rule_matches_dissertation():
    """Доминирующее правило угроза ВЫСОКАЯ, доверие СРЕДНЕЕ, эрозия СРЕДНЯЯ."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    rules = agent.active_rules(0.72, 0.55, 0.65)
    top = rules[0]
    assert top["if"] == {"threat": "high", "trust": "med", "erosion": "med"}
    assert abs(top["alpha"] - 0.52) < 0.02
    # Консеквенты доминирующего правила: значительные расходы, умеренная
    # риторика, ускоренный дрейф.
    assert top["then"]["milex"] == "high"
    assert top["then"]["rhet"] == "med"
    assert top["then"]["drift"] == "high"


def test_output_vector_matches_dissertation():
    """Вектор действия воспроизводит A_JP(2022) = (0.61, 0.48, 0.54)."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    r = agent.step(0.72, 0.55, 0.65)
    assert abs(r["milex"] - 0.61) < 0.04
    assert abs(r["rhet"] - 0.48) < 0.04
    assert abs(r["drift"] - 0.54) < 0.04
    assert abs(r["norm"] - 0.95) < 0.05


def test_milex_rises_on_high_threat_low_trust():
    """Ключевое требование. Высокая угроза при низком доверии поднимает расходы."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    low = agent.step(0.15, 0.85, 0.30)   # спокойная среда, союзник надёжен
    high = agent.step(0.90, 0.15, 0.50)  # угроза высока, союзник ненадёжен
    assert high["milex"] > low["milex"] + 0.20


def test_milex_monotonic_in_threat():
    """При прочих равных рост угрозы не снижает военные расходы."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    prev = -1.0
    for z1 in np.linspace(0.05, 0.95, 10):
        m = agent.step(z1, 0.5, 0.5)["milex"]
        assert m >= prev - 1e-6
        prev = m


def test_outputs_within_unit_interval():
    """Все выходы остаются в [0, 1] на сетке входов."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    for z1 in (0.1, 0.5, 0.9):
        for z2 in (0.1, 0.5, 0.9):
            for z3 in (0.1, 0.5, 0.9):
                r = agent.step(z1, z2, z3)
                for k in ("milex", "rhet", "drift"):
                    assert 0.0 <= r[k] <= 1.0


def test_rejects_out_of_range():
    """Вход вне [0, 1] отвергается."""
    agent = FuzzyAgent(JAPAN_CONFIG)
    for bad in ((-0.1, 0.5, 0.5), (0.5, 1.2, 0.5), (0.5, 0.5, 2.0)):
        try:
            agent.step(*bad)
        except ValueError:
            continue
        raise AssertionError(f"не отвергнут недопустимый вход {bad}")


if __name__ == "__main__":
    agent = FuzzyAgent(JAPAN_CONFIG)
    r = agent.step(0.72, 0.55, 0.65)
    print("Эталон диссертации A_JP(2022) = (0.61, 0.48, 0.54), норма 0.95")
    print("Контроллер: ({:.3f}, {:.3f}, {:.3f}), норма {:.3f}".format(
        r["milex"], r["rhet"], r["drift"], r["norm"]))
    print("Тесты запускаются командой pytest -v")
