"""
Тесты марковского ядра макроуровня.

Запуск из корня проекта:
    pytest -v
"""

import numpy as np
from engine.markov import MarkovCore, MARKOV, REGIMES, INITIAL_DISTRIBUTION


def test_rows_are_stochastic():
    """Строки матрицы переходов суммируются в единицу при любом напряжении."""
    for tension in (0.0, 0.25, 0.5, 0.75, 1.0):
        P = MARKOV.transition_matrix(tension)
        assert P.shape == (3, 3)
        for i in range(3):
            assert abs(P[i].sum() - 1.0) < 1e-9
            assert all(p >= 0.0 for p in P[i])


def test_low_tension_favours_balance():
    """При низком напряжении система устойчиво держится в балансе."""
    P = MARKOV.transition_matrix(0.1)
    assert P[0, 0] > 0.9


def test_high_tension_favours_destabilization():
    """При высоком напряжении дестабилизация поглощает, выход из неё редок."""
    P = MARKOV.transition_matrix(0.9)
    assert P[2, 2] > 0.9


def test_cascade_downward():
    """Из баланса при высоком напряжении срыв идёт через конфронтацию."""
    P = MARKOV.transition_matrix(0.9)
    assert P[0, 1] > P[0, 2]


def test_cascade_upward():
    """Восстановление из коллапса при низком напряжении тоже постепенно."""
    P = MARKOV.transition_matrix(0.1)
    assert P[2, 1] > P[2, 0]


def test_stay_probability_falls_with_tension():
    """Удержание в балансе слабеет по мере роста напряжения."""
    stay = [MARKOV.transition_matrix(t)[0, 0] for t in (0.1, 0.5, 0.9)]
    assert stay[0] > stay[1] > stay[2]


def test_step_preserves_normalization():
    """Шаг сохраняет нормировку распределения."""
    dist = INITIAL_DISTRIBUTION.copy()
    for _ in range(20):
        dist = MARKOV.step(dist, tension=0.7)
        assert abs(dist.sum() - 1.0) < 1e-9
        assert all(p >= 0.0 for p in dist)


def test_sustained_high_tension_drifts_to_collapse():
    """Длительное высокое напряжение сдвигает массу к дестабилизации."""
    dist = INITIAL_DISTRIBUTION.copy()
    for _ in range(40):
        dist = MARKOV.step(dist, tension=0.9)
    assert MARKOV.dominant_regime(dist) == "S3"


def test_sustained_low_tension_settles_in_balance():
    """Длительное низкое напряжение возвращает систему в баланс."""
    dist = np.array([0.1, 0.3, 0.6])
    for _ in range(40):
        dist = MARKOV.step(dist, tension=0.1)
    assert MARKOV.dominant_regime(dist) == "S1"


def test_rejects_out_of_range_tension():
    """Напряжение вне диапазона отвергается."""
    for bad in (-0.1, 1.5):
        try:
            MARKOV.transition_matrix(bad)
        except ValueError:
            continue
        raise AssertionError(f"не отвергнуто напряжение {bad}")


def test_dominant_regime_labels():
    """Определение доминирующего режима по распределению."""
    assert MarkovCore.dominant_regime(np.array([0.8, 0.1, 0.1])) == "S1"
    assert MarkovCore.dominant_regime(np.array([0.1, 0.8, 0.1])) == "S2"
    assert MarkovCore.dominant_regime(np.array([0.1, 0.1, 0.8])) == "S3"
