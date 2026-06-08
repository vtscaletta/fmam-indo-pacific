"""Тесты разбора решения. Запуск: pytest -v"""

from engine.fuzzy_agent import JAPAN
from engine.simulator import SIMULATOR
from engine.scenarios import ALL_SCENARIOS
from engine.agents import AGENTS


def test_fuzzify_returns_three_terms_per_var():
    fz = JAPAN.fuzzify(0.72, 0.55, 0.65)
    for v in ("z1", "z2", "z3"):
        assert set(fz[v]) == {"low", "med", "high"}
        for term in fz[v].values():
            assert 0.0 <= term <= 1.0


def test_active_rules_have_structure():
    rules = JAPAN.active_rules(0.72, 0.55, 0.65)
    assert len(rules) > 0
    r = rules[0]
    assert set(r["if"]) == {"threat", "trust", "erosion"}
    assert set(r["then"]) == {"milex", "rhet", "drift"}
    assert 0.0 <= r["alpha"] <= 1.0


def test_transparency_imports():
    """Модуль разбора импортируется и видит контроллер."""
    from ui.transparency import render_transparency, _membership_bars, _TERM, _VAR, _OUT
    assert set(_TERM) == {"low", "med", "high"}
    assert set(_VAR) == {"threat", "trust", "erosion"}
    assert set(_OUT) == {"milex", "rhet", "drift"}


def test_trajectory_supplies_states_for_trace():
    """Траектория даёт состояния и действия на каждый год для разбора."""
    tr = SIMULATOR.run(ALL_SCENARIOS["taiwan"], AGENTS, horizon=8)
    for c in AGENTS:
        assert len(tr.agent_states[c]) == 8
        assert len(tr.agent_actions[c]) == 8
