"""
Тесты связки уровней.

Запуск из корня проекта:
    pytest -v
"""

import numpy as np
from engine.synthesis import (
    aggregate, influence_weights, DifferentialMemory, LevelCoupling,
    phase_thresholds, stationary_distribution, COMPONENTS,
)
from engine.agents import AGENTS, run_agent
from engine.influence import CODES
from engine.markov import MARKOV


def _actions():
    return {c: run_agent(c) for c in CODES}


def _flat(value):
    return {c: {"milex": value, "rhet": value, "drift": value} for c in CODES}


def test_aggregation_weights_sum_to_one():
    """Веса агрегации нормированы, КНР доминирует как главный драйвер."""
    w = influence_weights()
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["chn"] == max(w.values())


def test_aggregate_within_unit_interval():
    """Системные компоненты лежат в [0, 1]."""
    comps = aggregate(_actions())
    for c in COMPONENTS:
        assert 0.0 <= comps[c] <= 1.0


def test_memory_converges_to_constant_input():
    """При постоянном входе память сходится к нему по всем измерениям."""
    mem = DifferentialMemory()
    target = {"milex": 0.7, "rhet": 0.7, "drift": 0.7}
    for _ in range(100):
        H = mem.update(target)
    for c in COMPONENTS:
        assert abs(H[c] - 0.7) < 1e-3


def test_drift_remembered_longer_than_rhetoric():
    """
    После импульса и отката институциональный дрейф удерживается в памяти
    дольше риторики. Прямая проверка дифференцированного забывания.
    """
    mem = DifferentialMemory()
    mem.seed({"milex": 0.0, "rhet": 0.0, "drift": 0.0})
    spike = {"milex": 1.0, "rhet": 1.0, "drift": 1.0}
    for _ in range(5):
        mem.update(spike)
    calm = {"milex": 0.0, "rhet": 0.0, "drift": 0.0}
    for _ in range(5):
        H = mem.update(calm)
    assert H["drift"] > H["milex"] > H["rhet"]


def test_tension_within_unit_interval_and_monotone():
    """Напряжение в [0, 1] и не убывает с ростом любого компонента."""
    c = LevelCoupling()
    lo = c.raw_tension(_flat(0.2))
    mid = c.raw_tension(_flat(0.5))
    hi = c.raw_tension(_flat(0.9))
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    assert lo < mid < hi


def test_quiet_system_low_tension():
    """Покоящаяся система держит низкое напряжение ниже первого порога."""
    c = LevelCoupling()
    assert c.raw_tension(_flat(0.0)) < 0.32


def test_year2025_tension_in_confrontation_band():
    """
    Напряжение базового года ложится в полосу холодной конфронтации между
    порогами, что отвечает тезису о регионе в фазовом переходе.
    """
    c = LevelCoupling()
    tau = c.raw_tension(_actions())
    assert 0.40 < tau < 0.65


def test_hysteresis_from_memory():
    """
    Гистерезис. После импульса дрейфа и полного отката поведения остаточное
    напряжение выше, чем у системы, стартующей с нуля. Институциональный
    сдвиг залипает.
    """
    cold = LevelCoupling()
    cold.memory.seed({"milex": 0.0, "rhet": 0.0, "drift": 0.0})
    baseline = cold.tension(_flat(0.0))

    hot = LevelCoupling()
    hot.memory.seed({"milex": 0.0, "rhet": 0.0, "drift": 0.0})
    for _ in range(6):
        hot.tension(_flat(0.9))
    for _ in range(6):
        residual = hot.tension(_flat(0.0))
    assert residual > baseline + 0.05


def test_phase_thresholds_ordered_and_plausible():
    """Пороги фазовых переходов упорядочены и лежат в ожидаемых окрестностях."""
    th = phase_thresholds(MARKOV)
    assert "S1->S2" in th and "S2->S3" in th
    assert th["S1->S2"] < th["S2->S3"]
    assert 0.28 < th["S1->S2"] < 0.38
    assert 0.62 < th["S2->S3"] < 0.72


def test_stationary_distribution_normalized():
    """Стационарное распределение нормировано."""
    pi = stationary_distribution(MARKOV, 0.5)
    assert abs(pi.sum() - 1.0) < 1e-6


def test_explain_has_no_side_effects():
    """Разбор шага не двигает память."""
    c = LevelCoupling()
    c.memory.seed({"milex": 0.3, "rhet": 0.3, "drift": 0.3})
    before = dict(c.memory.H)
    rep = c.explain(_flat(0.8))
    assert c.memory.H == before
    assert set(rep) == {"components", "memory_prev", "smoothed", "sigmoid_arg", "tension"}
    assert 0.0 <= rep["tension"] <= 1.0
