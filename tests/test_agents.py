"""
Тесты калибровок пяти агентов.

Запуск из корня проекта:
    pytest -v
"""

from engine.agents import AGENTS, CONTROLLER, get_agent, run_agent
from engine.fuzzy_agent import JAPAN_CONFIG, FuzzyAgent


def test_five_agents_present():
    """Прототип охватывает ровно пять заявленных агентов."""
    assert set(AGENTS) == {"usa", "chn", "jpn", "twn", "kor"}


def test_inputs_within_unit_interval():
    """Все три входа каждого агента лежат в [0, 1]."""
    for a in AGENTS.values():
        for z in a.inputs():
            assert 0.0 <= z <= 1.0, f"{a.name}: вход {z} вне диапазона"


def test_military_expenditure_positive_and_ordered():
    """Расходы положительны и согласуются с порядком SIPRI 2025."""
    bn = {c: a.milex_bn for c, a in AGENTS.items()}
    for v in bn.values():
        assert v > 0
    # США крупнейший, далее КНР, Япония, Корея, Тайвань.
    assert bn["usa"] > bn["chn"] > bn["jpn"] > bn["kor"] > bn["twn"]


def test_each_agent_runs_within_unit_interval():
    """Каждое состояние прогоняется контроллером и даёт корректный вектор."""
    for code in AGENTS:
        r = run_agent(code)
        for k in ("milex", "rhet", "drift"):
            assert 0.0 <= r[k] <= 1.0
        assert r["norm"] >= 0.0


def test_taiwan_most_active_usa_least():
    """
    Содержательная проверка. Тайвань под экзистенциальным давлением имеет
    наивысшую совокупную активность, США как гегемон наинизшую.
    """
    norms = {code: run_agent(code)["norm"] for code in AGENTS}
    assert norms["twn"] == max(norms.values())
    assert norms["usa"] == min(norms.values())


def test_taiwan_milex_exceeds_usa():
    """Высокая угроза Тайваня даёт большее приращение расходов, чем у США."""
    assert run_agent("twn")["milex"] > run_agent("usa")["milex"]


def test_japan_drift_high():
    """Высокая нормативная эрозия Японии даёт высокий институциональный дрейф."""
    jp = run_agent("jpn")
    us = run_agent("usa")
    assert jp["drift"] > us["drift"] + 0.08


def test_shared_scale_preserves_japan_anchor():
    """
    Общая шкала не сломала якорь. Контроллер на стандартной калибровке всё
    ещё воспроизводит эталон диссертации при z = (0.72, 0.55, 0.65).
    """
    ctrl = FuzzyAgent(JAPAN_CONFIG)
    r = ctrl.step(0.72, 0.55, 0.65)
    assert abs(r["milex"] - 0.61) < 0.04
    assert abs(r["rhet"] - 0.48) < 0.04
    assert abs(r["drift"] - 0.54) < 0.04


def test_get_agent_roundtrip():
    """get_agent возвращает запрошенного агента."""
    assert get_agent("jpn").name == "Япония"
