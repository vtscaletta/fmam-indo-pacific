"""
Виджеты дашборда. Насыщенные фигуры plotly в светлой деловой теме.

Каждый виджет привязан к реальной части модели: индикатор к напряжению и
риску, диаграмма связей к матрице влияния, радар к профилю агента. Логика
отделена от интерфейса и проверяема без браузера.
"""

from __future__ import annotations

import plotly.graph_objects as go

from ui.theme import PALETTE, regime_color, plotly_layout
from ui.i18n import t
from engine.influence import INFLUENCE, CODES
from engine.agents import AGENTS


def _apply(fig, height=None):
    fig.update_layout(**plotly_layout())
    if height:
        fig.update_layout(height=height)
    return fig


def gauge_figure(value: float, thresholds: dict, title: str = "") -> go.Figure:
    """Дуговой индикатор со стрелкой и зонами светофора по порогам."""
    th12 = thresholds.get("S1->S2", 0.324)
    th23 = thresholds.get("S2->S3", 0.676)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(value, 3),
        number=dict(font=dict(size=40, color=PALETTE["text_primary"])),
        gauge=dict(
            axis=dict(range=[0, 1], tickwidth=1, tickcolor=PALETTE["border_strong"]),
            bar=dict(color=PALETTE["text_primary"], thickness=0.18),
            borderwidth=0,
            steps=[
                dict(range=[0, th12], color=PALETTE["s1_soft"]),
                dict(range=[th12, th23], color=PALETTE["s2_soft"]),
                dict(range=[th23, 1], color=PALETTE["s3_soft"]),
            ],
            threshold=dict(line=dict(color=PALETTE["s3"], width=3), thickness=0.8, value=th23),
        ),
        title=dict(text=title, font=dict(size=14, color=PALETTE["text_muted"])),
    ))
    return _apply(fig, height=240)


def tension_area_figure(trajectory, thresholds: dict, lang="ru") -> go.Figure:
    """Заливная линия напряжения с пороговыми отсечками."""
    years, tension = trajectory.years, trajectory.tension
    th12 = thresholds.get("S1->S2")
    th23 = thresholds.get("S2->S3")
    fig = go.Figure()
    if th12 is not None:
        fig.add_hline(y=th12, line=dict(color=PALETTE["s1"], width=1, dash="dot"))
    if th23 is not None:
        fig.add_hline(y=th23, line=dict(color=PALETTE["s3"], width=1, dash="dot"))
    fig.add_trace(go.Scatter(
        x=years, y=tension, mode="lines+markers", name=t("tension_label", lang),
        line=dict(color=PALETTE["accent"], width=3, shape="spline"),
        marker=dict(size=7, color=PALETTE["accent"]),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.10)",
        hovertemplate="%{x}: %{y:.3f}<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 1], gridcolor=PALETTE["border"])
    fig.update_xaxes(gridcolor=PALETTE["border"])
    return _apply(fig, height=320)


def regime_donut_figure(dist, lang="ru") -> go.Figure:
    """Кольцо долей режимов на финальном шаге."""
    labels = [t("regime_S1", lang), t("regime_S2", lang), t("regime_S3", lang)]
    colors = [regime_color("S1"), regime_color("S2"), regime_color("S3")]
    fig = go.Figure(go.Pie(
        labels=labels, values=[float(dist[0]), float(dist[1]), float(dist[2])],
        hole=0.62, marker=dict(colors=colors, line=dict(color=PALETTE["bg_panel"], width=2)),
        textinfo="percent", textfont=dict(size=14, color="#FFFFFF"),
        hovertemplate="%{label}: %{percent}<extra></extra>", sort=False,
    ))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1))
    return _apply(fig, height=300)


def regime_area_figure(trajectory, lang="ru") -> go.Figure:
    """Доли режимов по годам стопкой площадей."""
    years, dist = trajectory.years, trajectory.regime_dist
    fig = go.Figure()
    for idx, code in ((0, "S1"), (1, "S2"), (2, "S3")):
        fig.add_trace(go.Scatter(
            x=years, y=[float(d[idx]) for d in dist], mode="lines", name=t(f"regime_{code}", lang),
            stackgroup="r", line=dict(width=0.5, color=regime_color(code)), fillcolor=regime_color(code),
            hovertemplate="%{y:.0%}<extra></extra>",
        ))
    fig.update_yaxes(range=[0, 1], tickformat=".0%", gridcolor=PALETTE["border"])
    fig.update_xaxes(gridcolor=PALETTE["border"])
    fig.update_layout(legend=dict(orientation="h", y=1.08))
    return _apply(fig, height=300)


def influence_heatmap_figure(lang="ru") -> go.Figure:
    """Тепловая карта матрицы влияния: кто на кого давит."""
    names = [AGENTS[c].name for c in CODES]
    z = [[INFLUENCE.W[i][j] for j in CODES] for i in CODES]
    fig = go.Figure(go.Heatmap(
        z=z, x=names, y=names,
        colorscale=[[0, PALETTE["bg_subtle"]], [0.5, PALETTE["accent2"]], [1, PALETTE["accent"]]],
        zmin=0, zmax=1, xgap=3, ygap=3,
        colorbar=dict(thickness=12, len=0.8),
        hovertemplate="%{y} → %{x}: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _apply(fig, height=340)


def agent_radar_figure(state, name="", lang="ru") -> go.Figure:
    """Радарный профиль трёх входных переменных агента."""
    cats = [t("var_threat", lang), t("var_trust", lang), t("var_erosion", lang)]
    z1, z2, z3 = state
    fig = go.Figure(go.Scatterpolar(
        r=[z1, z2, z3, z1], theta=cats + [cats[0]], fill="toself",
        line=dict(color=PALETTE["accent"], width=2), fillcolor="rgba(37,99,235,0.18)",
        hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
    ))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 1], showticklabels=False)),
                      showlegend=False, title=dict(text=name, font=dict(size=14)))
    return _apply(fig, height=260)
