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


# --- Модуль 11.1. Математический слой и свод правил ---

def test_all_rules_returns_27():
    from engine.fuzzy_agent import JAPAN
    rules = JAPAN.all_rules()
    assert len(rules) == 27
    keys = {(r["if"]["threat"], r["if"]["trust"], r["if"]["erosion"]) for r in rules}
    assert len(keys) == 27  # все комбинации уникальны


def test_all_rules_have_three_consequents():
    from engine.fuzzy_agent import JAPAN
    for r in JAPAN.all_rules():
        assert set(r["then"]) == {"milex", "rhet", "drift"}


def test_mf_params_match_config():
    from engine.fuzzy_agent import JAPAN, JAPAN_CONFIG
    assert JAPAN.mf_params("z1", "high") == JAPAN_CONFIG.threat.high
    assert JAPAN.mf_params("z2", "med") == JAPAN_CONFIG.trust.med
    assert JAPAN.mf_params("z3", "low") == JAPAN_CONFIG.erosion.low


def test_gauss_formula_matches_fuzzify():
    """Гауссова формула разбора совпадает с фаззификацией движка."""
    import math
    from engine.fuzzy_agent import JAPAN
    z = 0.72
    fz = JAPAN.fuzzify(z, 0.5, 0.5)
    term = max(fz["z1"], key=fz["z1"].get)
    c, s = JAPAN.mf_params("z1", term)
    manual = math.exp(-((z - c) ** 2) / (2 * s * s))
    assert abs(manual - fz["z1"][term]) < 0.01
