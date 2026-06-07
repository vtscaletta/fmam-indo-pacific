"""
Графики траекторий. Чистые построители фигур plotly в тёмной теме.

Функции принимают траекторию прогона и возвращают готовую фигуру. Логика
отделена от интерфейса, оттого проверяема без запуска браузера.
"""

from __future__ import annotations

import plotly.graph_objects as go

from ui.theme import PALETTE, regime_color
from ui.i18n import t


def _base_layout(fig: go.Figure, lang: str) -> go.Figure:
    """Накладывает тёмное оформление, общее для всех фигур."""
    fig.update_layout(
        paper_bgcolor=PALETTE["bg_panel"],
        plot_bgcolor=PALETTE["bg_panel"],
        font=dict(family="JetBrains Mono, monospace", color=PALETTE["text_secondary"], size=12),
        margin=dict(l=56, r=24, t=40, b=44),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(gridcolor=PALETTE["border"], zeroline=False, linecolor=PALETTE["border"])
    fig.update_yaxes(gridcolor=PALETTE["border"], zeroline=False, linecolor=PALETTE["border"])
    return fig


def tension_figure(trajectory, thresholds: dict, lang: str = "ru") -> go.Figure:
    """
    Линия системного напряжения по годам с порогами фазовых переходов.
    thresholds суть словарь с ключами S1->S2 и S2->S3.
    """
    years = trajectory.years
    tension = trajectory.tension
    fig = go.Figure()

    th12 = thresholds.get("S1->S2")
    th23 = thresholds.get("S2->S3")
    if th12 is not None:
        fig.add_hline(y=th12, line=dict(color=PALETTE["s1"], width=1, dash="dot"),
                      annotation_text=f"{t('regime_S1', lang)} | {t('regime_S2', lang)}",
                      annotation_position="top left",
                      annotation_font=dict(color=PALETTE["s1_glow"], size=11))
    if th23 is not None:
        fig.add_hline(y=th23, line=dict(color=PALETTE["s3"], width=1, dash="dot"),
                      annotation_text=f"{t('regime_S2', lang)} | {t('regime_S3', lang)}",
                      annotation_position="top left",
                      annotation_font=dict(color=PALETTE["s3_glow"], size=11))

    fig.add_trace(go.Scatter(
        x=years, y=tension, mode="lines+markers",
        name=t("tension_label", lang),
        line=dict(color=PALETTE["accent_glow"], width=2.5, shape="spline"),
        marker=dict(size=6, color=PALETTE["accent_glow"]),
        hovertemplate="%{x}: %{y:.3f}<extra></extra>",
    ))

    fig.update_yaxes(range=[0, 1], title=t("tension_label", lang))
    fig.update_xaxes(title=t("year_label", lang))
    return _base_layout(fig, lang)


def regime_figure(trajectory, lang: str = "ru") -> go.Figure:
    """Доли режимов по годам стопкой площадей в цветах режимов."""
    years = trajectory.years
    dist = trajectory.regime_dist
    s1 = [float(d[0]) for d in dist]
    s2 = [float(d[1]) for d in dist]
    s3 = [float(d[2]) for d in dist]

    fig = go.Figure()
    for series, code in ((s1, "S1"), (s2, "S2"), (s3, "S3")):
        fig.add_trace(go.Scatter(
            x=years, y=series, mode="lines", name=t(f"regime_{code}", lang),
            stackgroup="regime", line=dict(width=0.5, color=regime_color(code)),
            fillcolor=regime_color(code),
            hovertemplate="%{y:.0%}<extra></extra>",
        ))
    fig.update_yaxes(range=[0, 1], tickformat=".0%", title=t("dominant_regime", lang))
    fig.update_xaxes(title=t("year_label", lang))
    return _base_layout(fig, lang)


def agent_action_figure(action: dict, lang: str = "ru") -> go.Figure:
    """Компактный столбчатый профиль действия одного агента."""
    labels = [t("out_milex", lang), t("out_rhet", lang), t("out_drift", lang)]
    values = [action["milex"], action["rhet"], action["drift"]]
    colors = [PALETTE["accent_glow"], PALETTE["s2"], PALETTE["accent_alt"]]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors),
        hovertemplate="%{x:.3f}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 1])
    fig.update_layout(height=160, showlegend=False)
    return _base_layout(fig, lang)
