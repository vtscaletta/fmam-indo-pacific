"""
Проверки связки уровней.

Переписаны при вычистке беты. Прежний состав опирался на вымышленных агентов
и готовые сценарии снятого поколения, отчего запускаться перестал. Существо
проверок сохранено, источником же входов служат теперь искусственные наборы,
задаваемые в самих проверках, вследствие чего связка испытывается сама по
себе, без обращения к данным.

Запуск из корня хранилища.

    pytest tests/test_synthesis.py -v
"""
from __future__ import annotations

from engine.markov import MARKOV
from engine.synthesis import (
    COMPONENTS, DifferentialMemory, LevelCoupling, aggregate,
    perceptual_pressure, phase_thresholds, stationary_distribution,
)

CODES = ("usa", "chn", "jpn", "twn", "kor")
"""Искусственный состав участников. Величин предметной области не несёт."""


def _weights() -> dict:
    """Равные доли участников в системном итоге."""
    return {c: 1.0 / len(CODES) for c in CODES}


def _flat_actions(v: float) -> dict:
    return {c: {"milex": v, "rhet": v, "drift": v} for c in CODES}


def _flat_states(z1: float, z2: float, z3: float) -> dict:
    return {c: [z1, z2, z3] for c in CODES}


# --- Свёртка действий ---------------------------------------------------

def test_aggregate_within_unit_interval():
    """Свёрнутые составляющие остаются в отрезке."""
    comps = aggregate(_flat_actions(0.4), _weights())
    for c in COMPONENTS:
        assert 0.0 <= comps[c] <= 1.0


def test_aggregate_of_equal_actions_equals_action():
    """При равных действиях свёртка равна самому действию."""
    comps = aggregate(_flat_actions(0.7), _weights())
    for c in COMPONENTS:
        assert abs(comps[c] - 0.7) < 1e-9


def test_aggregate_ignores_absent_agents():
    """Отсутствие участника в действиях нормировки не нарушает."""
    acts = _flat_actions(0.6)
    del acts["kor"]
    comps = aggregate(acts, _weights())
    for c in COMPONENTS:
        assert abs(comps[c] - 0.6) < 1e-9


# --- Перцептивное давление ----------------------------------------------

def test_perceptual_pressure_responds_to_configuration():
    """Острая конфигурация даёт большее давление, чем спокойная."""
    w = _weights()
    calm = perceptual_pressure(_flat_states(0.1, 0.9, 0.1), w)
    tense = perceptual_pressure(_flat_states(0.9, 0.1, 0.9), w)
    assert tense > calm
    assert 0.0 <= calm <= 1.0 and 0.0 <= tense <= 1.0


def test_perceptual_pressure_excludes_undefined_erosion():
    """
    Неопределённая эрозия подмене не подлежит, доля её перераспределяется
    между прочими составляющими. Проверяется тем, что давление при
    неопределённой эрозии равно давлению, вычисленному по двум оставшимся
    составляющим.
    """
    w = _weights()
    nan = float("nan")
    with_nan = perceptual_pressure({c: [0.8, 0.2, nan] for c in CODES}, w)
    expected = (0.8 + (1.0 - 0.2)) / 2.0
    assert abs(with_nan - expected) < 1e-9


# --- Оператор памяти ----------------------------------------------------

def test_memory_converges_to_constant_input():
    """При неизменном входе память сходится к нему."""
    mem = DifferentialMemory()
    target = {"milex": 0.7, "rhet": 0.7, "drift": 0.7}
    for _ in range(100):
        H = mem.update(target)
    for c in COMPONENTS:
        assert abs(H[c] - 0.7) < 1e-3


def test_drift_remembered_longer_than_rhetoric():
    """
    Дрейф удерживается дольше расходов, а расходы дольше риторики. Это и есть
    храповик необратимости, положенный в основание оператора памяти.
    """
    mem = DifferentialMemory()
    mem.seed({c: 0.0 for c in COMPONENTS})
    for _ in range(5):
        mem.update({c: 1.0 for c in COMPONENTS})
    for _ in range(5):
        H = mem.update({c: 0.0 for c in COMPONENTS})
    assert H["drift"] > H["milex"] > H["rhet"]


def test_preview_has_no_side_effects():
    """Предпросмотр памяти её не продвигает."""
    mem = DifferentialMemory()
    mem.seed({c: 0.3 for c in COMPONENTS})
    before = dict(mem.H)
    mem.preview({c: 0.9 for c in COMPONENTS})
    assert mem.H == before


# --- Напряжение ---------------------------------------------------------

def test_tension_monotone_in_pressure():
    """При неизменных действиях напряжение растёт с остротой конфигурации."""
    c = LevelCoupling(_weights())
    acts = _flat_actions(0.5)
    lo = c.raw_tension(acts, _flat_states(0.2, 0.8, 0.2))
    hi = c.raw_tension(acts, _flat_states(0.9, 0.1, 0.9))
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    assert lo < hi


def test_tension_monotone_in_actions():
    """При неизменной конфигурации напряжение растёт с действиями."""
    c = LevelCoupling(_weights())
    st = _flat_states(0.5, 0.5, 0.5)
    lo = c.raw_tension(_flat_actions(0.2), st)
    hi = c.raw_tension(_flat_actions(0.9), st)
    assert lo < hi


def test_middle_of_scale_gives_middle_tension():
    """
    Условие середины шкалы. Система, у которой все переменные стоят
    посередине, даёт напряжение посередине. Из этого условия выведено
    смещение синтез-формулы, отчего проверка удостоверяет вывод.
    """
    c = LevelCoupling(_weights())
    tau = c.raw_tension(_flat_actions(0.5), _flat_states(0.5, 0.5, 0.5))
    assert abs(tau - 0.5) < 1e-6


def test_quiet_system_low_tension():
    """Спокойная система даёт напряжение ниже порога первого режима."""
    c = LevelCoupling(_weights())
    tau = c.raw_tension(_flat_actions(0.0), _flat_states(0.0, 1.0, 0.0))
    assert tau < 0.32


def test_hysteresis_from_memory():
    """
    Накопленный сдвиг удерживает напряжение после того, как видимое поведение
    успокоилось. Это гистерезис, приходящий в систему от оператора памяти.
    """
    st = _flat_states(0.3, 0.7, 0.3)
    cold = LevelCoupling(_weights())
    cold.memory.seed({c: 0.0 for c in COMPONENTS})
    baseline = cold.tension(_flat_actions(0.0), st)

    hot = LevelCoupling(_weights())
    hot.memory.seed({c: 0.0 for c in COMPONENTS})
    for _ in range(6):
        hot.tension(_flat_actions(0.9), st)
    for _ in range(6):
        residual = hot.tension(_flat_actions(0.0), st)
    assert residual > baseline + 0.03


def test_explain_has_no_side_effects():
    """Разбор шага память не продвигает и выдаёт полный состав величин."""
    c = LevelCoupling(_weights())
    c.memory.seed({comp: 0.3 for comp in COMPONENTS})
    before = dict(c.memory.H)
    rep = c.explain(_flat_actions(0.8), _flat_states(0.5, 0.5, 0.5))
    assert c.memory.H == before
    assert set(rep) == {"components", "memory_prev", "smoothed",
                        "perceptual_pressure", "sigmoid_arg", "tension"}
    assert 0.0 <= rep["tension"] <= 1.0


# --- Пороги фазовых переходов -------------------------------------------

def test_phase_thresholds_ordered_and_plausible():
    """Пороги упорядочены и лежат там, где им положено по построению."""
    th = phase_thresholds(MARKOV)
    assert "S1->S2" in th and "S2->S3" in th
    assert th["S1->S2"] < th["S2->S3"]
    assert 0.28 < th["S1->S2"] < 0.38
    assert 0.62 < th["S2->S3"] < 0.72


def test_stationary_distribution_normalized():
    """Стационарное распределение нормировано."""
    pi = stationary_distribution(MARKOV, 0.5)
    assert abs(pi.sum() - 1.0) < 1e-6
