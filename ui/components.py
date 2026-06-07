"""
Компоненты интерфейса. Переиспользуемые блоки разметки в тёмной теме.

Каждая функция печатает готовый фрагмент через streamlit. Разметка опирается
на классы темы, объявленные в build_css.
"""

from __future__ import annotations

import streamlit as st

from ui.theme import PALETTE, regime_color
from ui.i18n import t, tooltip


def metric_card(label: str, value: str, accent: str = None) -> None:
    """Карточка одной метрики: подпись сверху, крупное моноширинное значение."""
    color = accent or PALETTE["text_primary"]
    st.markdown(
        f"""<div class="fmam-card">
        <div class="fmam-label">{label}</div>
        <div class="fmam-metric" style="color:{color}">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def regime_badge(code: str, lang: str = "ru") -> str:
    """Возвращает разметку бейджа режима в его цвете."""
    name = t(f"regime_{code}", lang)
    cls = {"S1": "fmam-s1", "S2": "fmam-s2", "S3": "fmam-s3"}[code]
    return f'<span class="fmam-badge {cls}">{code} · {name}</span>'


def term_with_tooltip(label: str, key: str, lang: str = "ru") -> str:
    """Термин с пунктирным подчёркиванием и всплывающей подсказкой."""
    tip = tooltip(key, lang)
    if not tip:
        return label
    safe = tip.replace('"', "&quot;")
    return f'<span class="fmam-tooltip" title="{safe}">{label}</span>'


def agent_card(name: str, inputs: tuple, action: dict, lang: str = "ru") -> None:
    """
    Карточка агента: входное состояние и порождённое действие. Полоски дают
    мгновенное сравнение уровней без чтения чисел.
    """
    z1, z2, z3 = inputs

    def bar(label_key, value, color, tip_key):
        label = term_with_tooltip(t(label_key, lang), tip_key, lang)
        pct = int(round(value * 100))
        return f"""<div style="margin:6px 0">
          <div style="display:flex;justify-content:space-between;font-size:12px;color:{PALETTE['text_secondary']}">
            <span>{label}</span><span class="fmam-mono">{value:.2f}</span></div>
          <div style="background:{PALETTE['bg_base']};border-radius:6px;height:7px;margin-top:3px">
            <div style="width:{pct}%;height:7px;border-radius:6px;background:{color}"></div></div>
        </div>"""

    body = (
        bar("var_threat", z1, PALETTE["s3"], "var_threat")
        + bar("var_trust", z2, PALETTE["s1_glow"], "var_trust")
        + bar("var_erosion", z3, PALETTE["s2"], "var_erosion")
    )
    st.markdown(
        f"""<div class="fmam-card">
        <div style="font-weight:700;font-size:16px;margin-bottom:8px;color:{PALETTE['text_primary']}">{name}</div>
        {body}
        <div class="fmam-label" style="margin-top:10px">{t('out_milex', lang)} · {t('out_rhet', lang)} · {t('out_drift', lang)}</div>
        <div class="fmam-mono" style="color:{PALETTE['text_secondary']};font-size:13px">
        {action['milex']:.2f} · {action['rhet']:.2f} · {action['drift']:.2f}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    """Заголовок раздела с тонкой линией снизу."""
    st.markdown(
        f"""<div style="border-bottom:1px solid {PALETTE['border']};
        padding-bottom:6px;margin:8px 0 14px 0;font-weight:700;font-size:18px;
        color:{PALETTE['text_primary']}">{text}</div>""",
        unsafe_allow_html=True,
    )
