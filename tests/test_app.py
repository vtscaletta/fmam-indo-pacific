"""Тесты слоя представления и аналитического вывода. Запуск: pytest -v"""

import ast, os
import plotly.graph_objects as go

from engine.simulator import SIMULATOR
from engine.scenarios import ALL_SCENARIOS
from engine.agents import AGENTS, run_agent
from engine.synthesis import phase_thresholds
from engine.markov import MARKOV
from engine.analysis import classify
from ui.charts import (gauge_figure, tension_area_figure, regime_donut_figure,
                       regime_area_figure, influence_heatmap_figure, agent_radar_figure)


def _traj(key="taiwan"):
    return SIMULATOR.run(ALL_SCENARIOS[key], AGENTS, horizon=10)


def test_all_widgets_build():
    th = phase_thresholds(MARKOV); tr = _traj()
    assert isinstance(gauge_figure(0.6, th), go.Figure)
    assert len(tension_area_figure(tr, th).data) == 1
    assert len(regime_donut_figure(tr.regime_dist[-1]).data) == 1
    assert len(regime_area_figure(tr).data) == 3
    assert len(influence_heatmap_figure().data) == 1
    assert len(agent_radar_figure((0.7, 0.5, 0.6), (0.8, 0.4, 0.7), "X").data) == 2


def test_gauge_zones_from_thresholds():
    th = phase_thresholds(MARKOV)
    fig = gauge_figure(0.5, th)
    steps = fig.data[0].gauge.steps
    assert len(steps) == 3


def test_verdict_distinguishes_scenarios():
    th = phase_thresholds(MARKOV)
    base = classify(_traj("inertial"), th)
    crisis = classify(_traj("taiwan"), th)
    assert crisis["level"] == "red"
    assert base["level"] in ("amber", "green")
    assert crisis["risk"] > base["risk"]


def test_verdict_fields():
    v = classify(_traj("taiwan"), phase_thresholds(MARKOV))
    assert set(v) >= {"level", "title", "text", "risk", "peak", "breaches_collapse"}
    assert v["level"] in ("green", "amber", "red")
    assert len(v["text"]) > 0


def test_crisis_breaches_collapse():
    v = classify(_traj("taiwan"), phase_thresholds(MARKOV))
    assert v["breaches_collapse"] is True


def test_charts_localize():
    tr = _traj()
    assert regime_area_figure(tr, "ru").data[0].name == "Устойчивый баланс"
    assert regime_area_figure(tr, "en").data[0].name == "Stable balance"


def test_app_parses():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "app.py"), encoding="utf-8") as f:
        ast.parse(f.read())
