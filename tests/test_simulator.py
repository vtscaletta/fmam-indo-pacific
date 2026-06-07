"""
Тесты симулятора и сценариев.

Запуск из корня проекта:
    pytest -v
"""

import numpy as np
from engine.simulator import Simulator, SIMULATOR, Trajectory
from engine.scenarios import (
    INERTIAL, ARTICLE9_REVISION, TAIWAN_CRISIS, ALLIANCE_WEAKENING, ALL_SCENARIOS,
)
from engine.agents import AGENTS
from engine.influence import CODES


def _run(scenario, horizon=10):
    return SIMULATOR.run(scenario, AGENTS, horizon=horizon)


def test_trajectory_shape():
    """Траектория имеет длину горизонта по всем рядам."""
    t = _run(INERTIAL, horizon=10)
    assert len(t.years) == 10
    assert len(t.tension) == 10
    assert len(t.dominant) == 10
    for c in CODES:
        assert len(t.agent_states[c]) == 10
        assert len(t.agent_actions[c]) == 10


def test_states_stay_in_unit_interval():
    """Состояния всех агентов остаются в [0, 1] на всём горизонте."""
    t = _run(INERTIAL, horizon=15)
    for c in CODES:
        for s in t.agent_states[c]:
            for z in s:
                assert 0.0 <= z <= 1.0


def test_regime_distributions_normalized():
    """Распределение по режимам нормировано на каждом шаге."""
    t = _run(TAIWAN_CRISIS)
    for d in t.regime_dist:
        assert abs(sum(d) - 1.0) < 1e-9


def test_inertial_stays_in_confrontation():
    """Без шоков система держится в холодной конфронтации, не срываясь."""
    t = _run(INERTIAL, horizon=10)
    assert t.dominant[-1] == "S2"


def test_determinism():
    """Один сценарий, прогнанный дважды, даёт идентичные траектории."""
    a = _run(TAIWAN_CRISIS)
    b = _run(TAIWAN_CRISIS)
    assert a.tension == b.tension
    assert a.dominant == b.dominant


def test_erosion_is_ratchet():
    """Нормативная эрозия не убывает по траектории ни у одного агента."""
    t = _run(INERTIAL, horizon=12)
    for c in CODES:
        z3 = [s[2] for s in t.agent_states[c]]
        for i in range(1, len(z3)):
            assert z3[i] >= z3[i - 1] - 1e-9


def test_taiwan_crisis_raises_tension_above_inertial():
    """Тайваньский кризис поднимает напряжение выше инерционного фона."""
    base = _run(INERTIAL)
    crisis = _run(TAIWAN_CRISIS)
    assert max(crisis.tension[3:]) > max(base.tension[3:]) + 0.02


def test_taiwan_crisis_breaches_collapse_threshold():
    """В разгар кризиса напряжение пробивает порог дестабилизации 0.676."""
    crisis = _run(TAIWAN_CRISIS)
    assert max(crisis.tension) > 0.676


def test_scenarios_ordered_by_collapse_mass():
    """
    Итоговая масса дестабилизации упорядочена по тяжести сценария: инерционный
    дрейф мягче ревизии, та мягче ослабления альянса, кризис тяжелее всех.
    """
    s3 = {k: _run(s).regime_dist[-1][2]
          for k, s in (("inertial", INERTIAL), ("article9", ARTICLE9_REVISION),
                       ("alliance", ALLIANCE_WEAKENING), ("taiwan", TAIWAN_CRISIS))}
    assert s3["inertial"] <= s3["article9"] <= s3["alliance"] <= s3["taiwan"]
    assert s3["taiwan"] > s3["inertial"] + 0.04


def test_article9_revision_lifts_japanese_erosion():
    """Ревизия девятой статьи поднимает эрозию Японии выше инерционной."""
    base = _run(INERTIAL)
    rev = _run(ARTICLE9_REVISION)
    base_z3 = base.agent_states["jpn"][-1][2]
    rev_z3 = rev.agent_states["jpn"][-1][2]
    assert rev_z3 > base_z3 + 0.1


def test_alliance_weakening_drops_ally_trust():
    """Ослабление альянса роняет доверие союзников ниже инерционного."""
    base = _run(INERTIAL)
    weak = _run(ALLIANCE_WEAKENING)
    for c in ("jpn", "kor", "twn"):
        assert weak.agent_states[c][-1][1] < base.agent_states[c][-1][1]


def test_crisis_more_likely_to_reach_collapse():
    """
    Тайваньский кризис накапливает больше вероятностной массы в режиме
    дестабилизации, чем инерционный фон.
    """
    base = _run(INERTIAL)
    crisis = _run(TAIWAN_CRISIS)
    base_s3 = base.regime_dist[-1][2]
    crisis_s3 = crisis.regime_dist[-1][2]
    assert crisis_s3 > base_s3


def test_events_logged():
    """Сработавшие шоки попадают в журнал событий с годом."""
    t = _run(TAIWAN_CRISIS)
    assert any(year == 2028 for year, _ in t.events_log)


def test_scenario_registry_complete():
    """Реестр сценариев содержит все четыре прогностических сценария."""
    assert set(ALL_SCENARIOS) == {"inertial", "article9", "taiwan", "alliance"}


def test_to_dict_serializable():
    """Траектория сериализуется в простые типы."""
    import json
    t = _run(ARTICLE9_REVISION, horizon=5)
    s = json.dumps(t.to_dict())
    assert isinstance(s, str) and len(s) > 0
