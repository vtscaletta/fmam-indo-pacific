"""
Виджеты дашборда. Насыщенные фигуры plotly в светлой деловой теме.

Каждый виджет привязан к реальной части модели: индикатор к напряжению и
риску, диаграмма связей к матрице влияния, радар к профилю агента. Логика
отделена от интерфейса и проверяема без браузера.
"""

from __future__ import annotations

import numpy as np
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


def regime_area_figure(trajectory, lang="ru", mode="area") -> go.Figure:
    """
    Доли режимов по годам. mode area даёт стопку площадей, mode lines даёт
    три раздельные линии, что иногда читается тоньше на близких долях.
    """
    years, dist = trajectory.years, trajectory.regime_dist
    fig = go.Figure()
    for idx, code in ((0, "S1"), (1, "S2"), (2, "S3")):
        series = [float(d[idx]) for d in dist]
        if mode == "lines":
            fig.add_trace(go.Scatter(
                x=years, y=series, mode="lines+markers", name=t(f"regime_{code}", lang),
                line=dict(width=2.5, color=regime_color(code)), marker=dict(size=5),
                hovertemplate="%{y:.0%}<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(
                x=years, y=series, mode="lines", name=t(f"regime_{code}", lang),
                stackgroup="r", line=dict(width=0.5, color=regime_color(code)),
                fillcolor=regime_color(code), hovertemplate="%{y:.0%}<extra></extra>"))
    fig.update_yaxes(range=[0, 1], tickformat=".0%", gridcolor=PALETTE["border"])
    fig.update_xaxes(gridcolor=PALETTE["border"])
    fig = _apply(fig, height=320)
    fig.update_layout(legend=dict(orientation="h", y=-0.18, x=0), margin=dict(t=20))
    return fig


SHORT_NAMES = {"usa": "США", "chn": "КНР", "jpn": "Япония", "twn": "Тайвань", "kor": "Ю.Корея"}


def influence_heatmap_figure(lang="ru") -> go.Figure:
    """Тепловая карта матрицы влияния: кто на кого давит."""
    names = [SHORT_NAMES[c] for c in CODES]
    z = [[INFLUENCE.W[i][j] for j in CODES] for i in CODES]
    text = [[f"{INFLUENCE.W[i][j]:.2f}" if INFLUENCE.W[i][j] > 0 else "" for j in CODES] for i in CODES]
    fig = go.Figure(go.Heatmap(
        z=z, x=names, y=names, text=text, texttemplate="%{text}",
        textfont=dict(size=13, color=PALETTE["text_primary"]),
        colorscale=[[0, PALETTE["bg_subtle"]], [0.5, PALETTE["accent2"]], [1, PALETTE["accent"]]],
        zmin=0, zmax=1, xgap=4, ygap=4,
        colorbar=dict(thickness=12, len=0.7, x=1.02),
        hovertemplate="%{y} → %{x}: %{z:.2f}<extra></extra>",
    ))
    fig = _apply(fig, height=360)
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=90, r=90, t=20, b=50))
    return fig


def agent_radar_figure(start, final=None, name="", lang="ru") -> go.Figure:
    """
    Радарный профиль агента. Если дан финал, поверх стартового профиля 2025
    года ложится профиль конца сценария, и сдвиг виден глазом.
    """
    cats = [t("var_threat", lang), t("var_trust", lang), t("var_erosion", lang)]
    theta = cats + [cats[0]]
    fig = go.Figure()
    s1, s2, s3 = start
    fig.add_trace(go.Scatterpolar(
        r=[s1, s2, s3, s1], theta=theta, fill="toself", name=t("agent_start", lang),
        line=dict(color=PALETTE["text_muted"], width=1.5, dash="dot"),
        fillcolor="rgba(148,163,184,0.12)",
        hovertemplate="%{theta}: %{r:.2f}<extra>" + t("agent_start", lang) + "</extra>",
    ))
    if final is not None:
        f1, f2, f3 = final
        fig.add_trace(go.Scatterpolar(
            r=[f1, f2, f3, f1], theta=theta, fill="toself", name=t("agent_final", lang),
            line=dict(color=PALETTE["accent"], width=2.5), fillcolor="rgba(37,99,235,0.18)",
            hovertemplate="%{theta}: %{r:.2f}<extra>" + t("agent_final", lang) + "</extra>",
        ))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 1], showticklabels=False)),
                      showlegend=final is not None,
                      legend=dict(orientation="h", y=-0.12, font=dict(size=11)),
                      title=dict(text=name, font=dict(size=14)))
    return _apply(fig, height=300)


_TERM_COLOR = {"low": PALETTE["s1"], "med": PALETTE["s2"], "high": PALETTE["s3"]}
_TERM_FILL = {"low": "rgba(22,163,74,0.10)", "med": "rgba(217,119,6,0.10)",
              "high": "rgba(220,38,38,0.10)"}
_TERM_LABEL = {"low": "term_low", "med": "term_med", "high": "term_high"}


def membership_figure(var_label: str, z_value: float, params: dict,
                      memberships: dict, lang: str = "ru") -> go.Figure:
    """
    График функций принадлежности одной переменной, те самые холмики.

    Три гауссовых терма на области [0, 1], вертикаль на текущем значении и
    маркеры в точках пересечения со степенями принадлежности. Делает зримым
    то, что формула выражает числом: значение частично принадлежит сразу
    нескольким термам. params суть {term: (центр, ширина)}, memberships суть
    {term: степень}.
    """
    u = np.arange(0.0, 1.001, 0.005)
    fig = go.Figure()
    for term in ("low", "med", "high"):
        c, s = params[term]
        mu = np.exp(-((u - c) ** 2) / (2.0 * s * s))
        fig.add_trace(go.Scatter(
            x=u, y=mu, mode="lines", name=t(_TERM_LABEL[term], lang),
            line=dict(color=_TERM_COLOR[term], width=2),
            fill="tozeroy", fillcolor=_TERM_FILL[term],
            hoverinfo="skip",
        ))
    # Вертикаль на текущем значении.
    fig.add_shape(type="line", x0=z_value, x1=z_value, y0=0, y1=1.04,
                  line=dict(color=PALETTE["text_secondary"], width=1.5, dash="dash"))
    # Маркеры степеней принадлежности на вертикали.
    for term in ("low", "med", "high"):
        val = memberships[term]
        if val < 0.02:
            continue
        fig.add_trace(go.Scatter(
            x=[z_value], y=[val], mode="markers+text",
            marker=dict(color=_TERM_COLOR[term], size=9,
                        line=dict(color="white", width=1.5)),
            text=[f"{val:.2f}"], textposition="middle right",
            textfont=dict(size=11, color=_TERM_COLOR[term]),
            showlegend=False, hoverinfo="skip",
        ))
    fig.update_layout(
        title=dict(text=f"{var_label} · {z_value:.2f}", font=dict(size=13)),
        xaxis=dict(range=[0, 1], showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(range=[0, 1.1], showticklabels=False, showgrid=False),
        showlegend=True,
        legend=dict(orientation="h", y=-0.18, font=dict(size=10)),
        margin=dict(l=10, r=10, t=34, b=10),
    )
    return _apply(fig, height=240)


# Цвета сценариев для сравнения. Тайвань багряный как тяжелейший.
COMPARE_COLORS = {
    "inertial": PALETTE["text_muted"],
    "article9": PALETTE["accent"],
    "alliance": PALETTE["accent2"],
    "taiwan": PALETTE["s3"],
    "custom": "#7C3AED",
}


def comparison_tension_figure(trajs: dict, thresholds: dict, labels: dict, lang="ru") -> go.Figure:
    """Траектории напряжения нескольких сценариев на одних осях."""
    fig = go.Figure()
    th12, th23 = thresholds.get("S1->S2"), thresholds.get("S2->S3")
    if th12 is not None:
        fig.add_hline(y=th12, line=dict(color=PALETTE["s1"], width=1, dash="dot"))
    if th23 is not None:
        fig.add_hline(y=th23, line=dict(color=PALETTE["s3"], width=1, dash="dot"))
    for key, tr in trajs.items():
        fig.add_trace(go.Scatter(
            x=tr.years, y=tr.tension, mode="lines+markers", name=labels.get(key, key),
            line=dict(color=COMPARE_COLORS.get(key, PALETTE["accent"]), width=3, shape="spline"),
            marker=dict(size=6),
            hovertemplate="%{x}: %{y:.3f}<extra></extra>",
        ))
    fig.update_yaxes(range=[0, 1], gridcolor=PALETTE["border"])
    fig.update_xaxes(gridcolor=PALETTE["border"])
    fig = _apply(fig, height=380)
    fig.update_layout(legend=dict(orientation="h", y=-0.16, x=0))
    return fig


def comparison_risk_figure(trajs: dict, labels: dict, lang="ru") -> go.Figure:
    """Столбики итогового риска дестабилизации по сценариям."""
    keys = list(trajs)
    names = [labels.get(k, k) for k in keys]
    risks = [float(trajs[k].regime_dist[-1][2]) * 100 for k in keys]
    colors = [COMPARE_COLORS.get(k, PALETTE["accent"]) for k in keys]
    fig = go.Figure(go.Bar(
        x=risks, y=names, orientation="h", marker=dict(color=colors),
        text=[f"{r:.0f}%" for r in risks], textposition="outside",
        hovertemplate="%{x:.0f}%<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(risks) * 1.25 if risks else 1], ticksuffix="%", gridcolor=PALETTE["border"])
    fig = _apply(fig, height=300)
    fig.update_layout(showlegend=False)
    return fig
