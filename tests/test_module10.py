"""Тесты сравнения сценариев. Запуск: pytest -v"""

import plotly.graph_objects as go
from engine.simulator import SIMULATOR
from engine.scenarios import ALL_SCENARIOS
from engine.agents import AGENTS
from engine.synthesis import phase_thresholds
from engine.markov import MARKOV
from ui.charts import comparison_tension_figure, comparison_risk_figure, COMPARE_COLORS


def _trajs():
    return {k: SIMULATOR.run(ALL_SCENARIOS[k], AGENTS, horizon=10) for k in ALL_SCENARIOS}


def test_comparison_tension_one_line_per_scenario():
    trajs = _trajs()
    fig = comparison_tension_figure(trajs, phase_thresholds(MARKOV), {k: k for k in trajs})
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == len(trajs)


def test_comparison_tension_has_thresholds():
    fig = comparison_tension_figure(_trajs(), phase_thresholds(MARKOV), {k: k for k in ALL_SCENARIOS})
    assert len(fig.layout.shapes) == 2


def test_comparison_risk_bars():
    trajs = _trajs()
    fig = comparison_risk_figure(trajs, {k: k for k in trajs})
    assert len(fig.data[0].x) == len(trajs)


def test_compare_colors_cover_presets():
    for k in ALL_SCENARIOS:
        assert k in COMPARE_COLORS


def test_taiwan_highest_risk_in_comparison():
    """В сравнении тайваньский кризис несёт наибольший риск."""
    trajs = _trajs()
    risks = {k: trajs[k].regime_dist[-1][2] for k in trajs}
    assert risks["taiwan"] == max(risks.values())


def test_comparison_accepts_custom_scenario():
    """Свой сценарий встаёт пятой линией и столбиком в сравнении."""
    from engine.scenarios import build_custom_scenario
    trajs = _trajs()
    spec = [{"step": 3, "agent": "chn", "event": "mil_escalation", "magnitude": "extreme"}]
    trajs["custom"] = SIMULATOR.run(build_custom_scenario(spec), AGENTS, horizon=10)
    labels = {k: k for k in trajs}
    fig = comparison_tension_figure(trajs, phase_thresholds(MARKOV), labels)
    bar = comparison_risk_figure(trajs, labels)
    assert len(fig.data) == 5
    assert len(bar.data[0].x) == 5
    assert "custom" in COMPARE_COLORS
