"""Тесты конструктора сценариев и классификации угроз. Запуск: pytest -v"""

from engine.simulator import SIMULATOR
from engine.scenarios import (ALL_SCENARIOS, EVENT_CATALOG, MAGNITUDE_LEVELS,
                              build_custom_scenario, Scenario)
from engine.agents import AGENTS
from engine.analysis import classify_threat_type, THREAT_TYPES


def _base():
    return SIMULATOR.run(ALL_SCENARIOS["inertial"], AGENTS, horizon=10)


def test_event_catalog_structure():
    """Каждое событие каталога задаёт переменную и знак."""
    for key, e in EVENT_CATALOG.items():
        assert e["var"] in ("z1", "z2", "z3")
        assert e["sign"] in (-1, 1)
        assert "ru" in e and "en" in e


def test_build_custom_scenario():
    """Сборщик превращает спецификацию в корректный сценарий."""
    spec = [{"step": 2, "agent": "jpn", "event": "norm_shift", "magnitude": "strong"}]
    sc = build_custom_scenario(spec, "Тест")
    assert isinstance(sc, Scenario)
    assert len(sc.events) == 1
    ev = sc.events[0]
    assert ev.step == 2 and ev.target == "jpn" and ev.variable == "z3"
    assert abs(ev.delta - 0.20) < 1e-9


def test_custom_scenario_runs():
    """Собранный сценарий прогоняется движком."""
    spec = [{"step": 1, "agent": "twn", "event": "mil_escalation", "magnitude": "extreme"}]
    sc = build_custom_scenario(spec)
    traj = SIMULATOR.run(sc, AGENTS, horizon=8)
    assert len(traj.years) == 8


def test_threat_type_pure_trust_collapse():
    """Чистый обвал доверия классифицируется как обвал доверия."""
    spec = [
        {"step": 2, "agent": "jpn", "event": "alliance_loss", "magnitude": "extreme"},
        {"step": 2, "agent": "kor", "event": "alliance_loss", "magnitude": "extreme"},
        {"step": 2, "agent": "twn", "event": "alliance_loss", "magnitude": "strong"},
    ]
    traj = SIMULATOR.run(build_custom_scenario(spec), AGENTS, horizon=10)
    c = classify_threat_type(traj, baseline=_base())
    assert c["type"] == "alliance"


def test_threat_type_pure_normative():
    """Чистый нормативный сдвиг классифицируется как нормативный распад."""
    spec = [{"step": 2, "agent": "jpn", "event": "norm_shift", "magnitude": "extreme"},
            {"step": 3, "agent": "jpn", "event": "norm_shift", "magnitude": "strong"}]
    traj = SIMULATOR.run(build_custom_scenario(spec), AGENTS, horizon=10)
    c = classify_threat_type(traj, baseline=_base())
    assert c["type"] == "normative"


def test_inertial_is_mixed():
    """Инерционный сценарий не имеет специфической угрозы сверх фона."""
    base = _base()
    c = classify_threat_type(base, baseline=base)
    assert c["type"] == "mixed"


def test_threat_type_fields():
    """Классификация возвращает тип, ярлык, текст и баллы."""
    c = classify_threat_type(_base())
    assert c["type"] in THREAT_TYPES
    assert c["label"] and c["text"]
    assert set(c["scores"]) == {"material", "alliance", "normative"}


def test_magnitude_levels_ordered():
    """Уровни силы возрастают."""
    v = [MAGNITUDE_LEVELS[k]["value"] for k in ("light", "strong", "extreme")]
    assert v[0] < v[1] < v[2]
