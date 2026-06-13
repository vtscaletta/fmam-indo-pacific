"""
Холмы функций принадлежности. Делает зримым то, как сырое число превращается в
лингвистический терм нечёткого вывода. Для каждой входной переменной три
гауссовых холма, низкий, средний, высокий, поверх них вертикаль текущего
значения агента и точки на пересечении, дающие степени принадлежности. Это
визуальный двойник первого шага вывода Мамдани, ядро прозрачности модели.

Кладётся в ui, импортируется на вкладке агентов или прозрачности. Функции
принадлежности и степени берутся из самого движка, не дублируются, оттого
картинка не разойдётся с расчётом.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.theme import PALETTE, plotly_layout

# Цвет терма по нарастанию интенсивности, светофор. Низкий покоен, высокий тревожен.
_TERM_COLOR = {"low": PALETTE["s1"], "med": PALETTE["s2"], "high": PALETTE["s3"]}
_TERM_RU = {"low": "низкий", "med": "средний", "high": "высокий"}
_TERM_EN = {"low": "low", "med": "mid", "high": "high"}

# Входные переменные в нотации диссертации, с подписью и индексом.
_VARS = [
    ("z1", "Восприятие угрозы", "Threat perception", "z\u2081"),
    ("z2", "Доверие к союзнику", "Alliance trust", "z\u2082"),
    ("z3", "Нормативная эрозия", "Normative erosion", "z\u2083"),
]


def _gauss(x: np.ndarray, c: float, s: float) -> np.ndarray:
    return np.exp(-((x - c) ** 2) / (2.0 * s * s))


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def membership_figure(agent, z_state, lang: str = "ru"):
    """
    Холмы принадлежности для одного состояния агента.

    agent    нечёткий контроллер с методами mf_params(var, term) и fuzzify,
             обычно общий экземпляр движка.
    z_state  тройка (z1, z2, z3), текущее состояние агента из траектории.
    """
    z1, z2, z3 = float(z_state[0]), float(z_state[1]), float(z_state[2])
    zmap = {"z1": z1, "z2": z2, "z3": z3}
    terms = _TERM_RU if lang == "ru" else _TERM_EN
    x = np.linspace(0.0, 1.0, 240)

    titles = [f"{(ru if lang=='ru' else en)} ({sym})"
              for _, ru, en, sym in _VARS]
    fig = make_subplots(rows=1, cols=3, subplot_titles=titles, horizontal_spacing=0.06)

    deg = agent.fuzzify(z1, z2, z3)
    for col, (var, _ru, _en, _sym) in enumerate(_VARS, start=1):
        z = zmap[var]
        # Холмы термов.
        for term in ("low", "med", "high"):
            c, s = agent.mf_params(var, term)
            y = _gauss(x, c, s)
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", name=terms[term],
                line=dict(color=_TERM_COLOR[term], width=2),
                fill="tozeroy", fillcolor=_rgba(_TERM_COLOR[term], 0.10),
                legendgroup=term, showlegend=(col == 1),
                hovertemplate=f"{terms[term]} %{{y:.2f}}<extra></extra>"),
                row=1, col=col)
        # Вертикаль текущего значения z.
        fig.add_vline(x=z, line=dict(color=PALETTE["text_primary"], width=1.4, dash="dot"),
                      row=1, col=col)
        fig.add_annotation(x=z, y=1.06, text=f"{z:.2f}", showarrow=False,
                           font=dict(size=12, color=PALETTE["text_primary"]),
                           row=1, col=col)
        # Точки принадлежности на пересечении вертикали с холмами.
        for term in ("low", "med", "high"):
            mu = deg[var][term]
            if mu > 0.01:
                fig.add_trace(go.Scatter(
                    x=[z], y=[mu], mode="markers",
                    marker=dict(color=_TERM_COLOR[term], size=9,
                                line=dict(color="#ffffff", width=1.5)),
                    showlegend=False,
                    hovertemplate=f"{terms[term]} \u03bc=%{{y:.2f}}<extra></extra>"),
                    row=1, col=col)

    lay = plotly_layout()
    lay["margin"] = dict(l=36, r=16, t=54, b=30)
    fig.update_layout(**lay, height=300,
                      legend=dict(orientation="h", yanchor="bottom", y=1.18,
                                  xanchor="center", x=0.5, font=dict(size=12)))
    fig.update_xaxes(range=[0, 1], showgrid=False, tickfont=dict(size=11),
                     dtick=0.25)
    fig.update_yaxes(range=[0, 1.12], showgrid=True, gridcolor=PALETTE["border"],
                     tickfont=dict(size=11), dtick=0.5)
    # Подписи подграфиков крупнее, под общий шрифт.
    for ann in fig.layout.annotations:
        if ann.text and "(" in ann.text:
            ann.font = dict(size=13, color=PALETTE["text_primary"],
                            family="Spectral, serif")
    return fig
