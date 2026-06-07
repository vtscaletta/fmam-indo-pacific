"""
Тесты слоя представления.

Проверяют построители графиков на реальной траектории и синтаксическую
целостность главного файла. Визуальный рендер проверяется развёртыванием.

Запуск из корня проекта:
    pytest -v
"""

import ast
import os

import plotly.graph_objects as go

from engine.simulator import SIMULATOR
from engine.scenarios import ALL_SCENARIOS
from engine.agents import AGENTS, run_agent
from engine.synthesis import phase_thresholds
from engine.markov import MARKOV
from ui.charts import tension_figure, regime_figure, agent_action_figure


def _traj():
    return SIMULATOR.run(ALL_SCENARIOS["taiwan"], AGENTS, horizon=10)


def test_tension_figure_has_line_and_thresholds():
    """Фигура напряжения содержит линию и две пороговые отсечки."""
    th = phase_thresholds(MARKOV)
    fig = tension_figure(_traj(), th, "ru")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    ys = sorted(round(s["y0"], 3) for s in fig.layout.shapes)
    assert ys == [round(th["S1->S2"], 3), round(th["S2->S3"], 3)]


def test_tension_axis_bounded_unit():
    """Ось напряжения ограничена единичным интервалом."""
    fig = tension_figure(_traj(), phase_thresholds(MARKOV), "en")
    assert tuple(fig.layout.yaxis.range) == (0, 1)


def test_regime_figure_three_stacked_series():
    """Фигура режимов содержит три площади стопкой."""
    fig = regime_figure(_traj(), "ru")
    assert len(fig.data) == 3
    for tr in fig.data:
        assert tr.stackgroup == "regime"


def test_agent_action_figure_single_bar_group():
    """Профиль действия агента содержит один набор столбцов."""
    fig = agent_action_figure(run_agent("jpn"), "en")
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 3


def test_charts_localize():
    """Подписи графиков переключаются по языку."""
    tr = _traj()
    ru = regime_figure(tr, "ru")
    en = regime_figure(tr, "en")
    assert ru.data[0].name == "Устойчивый баланс"
    assert en.data[0].name == "Stable balance"


def test_app_module_parses():
    """Главный файл синтаксически корректен."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "app.py"), encoding="utf-8") as f:
        ast.parse(f.read())
