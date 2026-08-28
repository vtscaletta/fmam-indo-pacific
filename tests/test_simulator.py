"""
Проверки симулятора.

Переписаны при вычистке беты. Прежний состав прогонял вымышленных агентов по
готовым сценариям снятого поколения и обращался к общему образцу симулятора,
которого более не существует. Существо проверок сохранено, прогон же ведётся
теперь по действительным наблюдениям из таблиц.

Проверяются свойства, обязанные выполняться при всяком наборе данных, а
именно длины рядов, пребывание состояний в отрезке, нормировка распределения
по режимам, повторяемость прогона и необратимость нормативной эрозии.
Величин предметной области проверки не назначают, поскольку те следуют из
данных и при их пополнении меняются.

Запуск из корня хранилища.

    pytest tests/test_simulator.py -v
"""
from __future__ import annotations

import math

import pytest

from engine.influence import build_influence
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import ObservedErosion, Simulator

YEARS = range(2001, 2026)
CUTOFF = 2019


@pytest.fixture(scope="module")
def setup():
    """Общая для всех проверок сборка движка на действительных данных."""
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")
    sim = Simulator(agents, influence)
    return agents, inputs, sim


def _run(setup, cutoff=None):
    agents, inputs, sim = setup
    return sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical, cutoff=cutoff)


# --- Устройство траектории ----------------------------------------------

def test_trajectory_lengths_match_period(setup):
    """Все ряды траектории имеют длину периода наблюдения."""
    traj = _run(setup)
    n = len(YEARS)
    assert len(traj.years) == n
    assert len(traj.tension) == n
    assert len(traj.dominant) == n
    for code in traj.agent_states:
        assert len(traj.agent_states[code]) == n
        assert len(traj.agent_actions[code]) == n


def test_tension_within_unit_interval(setup):
    """Напряжение остаётся в отрезке на всём периоде."""
    traj = _run(setup)
    for tau in traj.tension:
        assert 0.0 <= tau <= 1.0


def test_states_within_unit_interval(setup):
    """
    Состояния остаются в отрезке. Неопределённая эрозия исключается из
    проверки, поскольку отсутствие величины отрезку не принадлежит и подмене
    не подлежит.
    """
    traj = _run(setup)
    for code, series in traj.agent_states.items():
        for state in series:
            for z in state:
                if math.isnan(z):
                    continue
                assert 0.0 <= z <= 1.0, f"{code} вне отрезка"


def test_regime_distribution_normalized(setup):
    """Распределение по режимам нормировано на каждом шаге."""
    traj = _run(setup)
    for dist in traj.regime_dist:
        assert abs(sum(dist) - 1.0) < 1e-9


def test_dominant_regime_from_known_set(setup):
    """Господствующий режим взят из объявленного перечня."""
    traj = _run(setup)
    for regime in traj.dominant:
        assert regime in ("S1", "S2", "S3")


# --- Повторяемость ------------------------------------------------------

def test_run_is_deterministic(setup):
    """
    Два прогона на одних данных дают тождественные траектории. Случайности в
    движке нет ни одной, отчего повторяемость обязана быть точной, а не
    приблизительной.
    """
    a = _run(setup)
    b = _run(setup)
    assert a.tension == b.tension
    assert a.dominant == b.dominant


# --- Необратимость эрозии -----------------------------------------------

def test_erosion_never_decreases(setup):
    """
    Нормативная эрозия по траектории не убывает ни у одного агента. Свойство
    следует из природы величины, поскольку снятое ограничение обратно не
    возвращается, и потому обязано выполняться при всяком наборе данных.
    """
    traj = _run(setup)
    for code, series in traj.agent_states.items():
        z3 = [s[2] for s in series]
        known = [(i, v) for i, v in enumerate(z3) if not math.isnan(v)]
        for k in range(1, len(known)):
            prev, cur = known[k - 1][1], known[k][1]
            assert cur >= prev - 1e-9, f"{code} эрозия убыла"


# --- Отсечка ------------------------------------------------------------

def test_cutoff_matches_until_cutoff_year(setup):
    """
    До года отсечки слепой прогон совпадает с полным, поскольку до отсечки оба
    получают одни и те же наблюдения. Расхождение начинается лишь после.
    """
    full = _run(setup)
    blind = _run(setup, cutoff=CUTOFF)
    idx = full.years.index(CUTOFF)
    for i in range(idx + 1):
        assert abs(full.tension[i] - blind.tension[i]) < 1e-9


def test_cutoff_diverges_after_cutoff_year(setup):
    """
    После отсечки слепой прогон расходится с полным. Совпадение означало бы,
    что наблюдения за отсечкой в модель всё же поступают, то есть протекание
    отложенного отрезка.
    """
    full = _run(setup)
    blind = _run(setup, cutoff=CUTOFF)
    idx = full.years.index(CUTOFF)
    diffs = [abs(full.tension[i] - blind.tension[i])
             for i in range(idx + 1, len(full.years))]
    assert max(diffs) > 1e-6, "отложенный отрезок не является слепым"
