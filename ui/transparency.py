"""
Разбор решения. Прозрачность вычисления по шагам, как учитель у доски.

Раскрывает кухню движка для одного агента в один год: как числовое
состояние переводится в нечёткие термины, какие правила реализма срабатывают
и с какой силой, как они сворачиваются в действие. Никакого чёрного ящика.
"""

from __future__ import annotations

import streamlit as st

from engine.agents import AGENTS
from engine.fuzzy_agent import JAPAN as CONTROLLER
from ui.theme import PALETTE
from ui.i18n import t
from ui.components import panel_open, panel_close


# Перевод служебных меток в человеческий язык интерфейса.
_TERM = {"low": "term_low", "med": "term_med", "high": "term_high"}
_VAR = {"threat": "var_threat", "trust": "var_trust", "erosion": "var_erosion"}
_OUT = {"milex": "out_milex", "rhet": "out_rhet", "drift": "out_drift"}
_VAR_ORDER = [("z1", "var_threat"), ("z2", "var_trust"), ("z3", "var_erosion")]


def _membership_bars(memberships: dict, lang: str) -> str:
    """Разметка степеней принадлежности по одной переменной."""
    colors = {"low": PALETTE["s1"], "med": PALETTE["s2"], "high": PALETTE["s3"]}
    rows = ""
    for term in ("low", "med", "high"):
        val = memberships[term]
        pct = int(round(val * 100))
        rows += (
            f'<div style="display:flex;align-items:center;gap:10px;margin:3px 0">'
            f'<div style="width:80px;font-size:13px;color:{PALETTE["text_secondary"]}">{t(_TERM[term], lang)}</div>'
            f'<div style="flex:1;background:{PALETTE["bg_page"]};border-radius:6px;height:10px">'
            f'<div style="width:{pct}%;height:10px;border-radius:6px;background:{colors[term]}"></div></div>'
            f'<div style="width:44px;text-align:right;font-weight:700;font-size:13px;'
            f'color:{PALETTE["text_primary"]}">{val:.2f}</div></div>'
        )
    return rows


def render_transparency(traj, lang: str) -> None:
    """Главная функция вкладки разбора решения."""
    st.markdown(f'<div style="font-size:15px;color:{PALETTE["text_secondary"]};'
                f'margin-bottom:14px;line-height:1.55">{t("trn_intro", lang)}</div>',
                unsafe_allow_html=True)

    c = st.columns(2)
    with c[0]:
        code = st.selectbox(t("trn_pick_agent", lang), list(AGENTS),
                            format_func=lambda k: AGENTS[k].name, key="trn_agent")
    with c[1]:
        year = st.selectbox(t("trn_pick_year", lang), traj.years, key="trn_year")
    idx = traj.years.index(year)
    z1, z2, z3 = traj.agent_states[code][idx]

    # Шаг 1. Фаззификация.
    panel_open(t("trn_s1", lang))
    st.markdown(f'<div style="font-size:13px;color:{PALETTE["text_muted"]};margin-bottom:10px">'
                f'{t("trn_s1_hint", lang)}</div>', unsafe_allow_html=True)
    fz = CONTROLLER.fuzzify(z1, z2, z3)
    cols = st.columns(3)
    for col, (zkey, vkey) in zip(cols, _VAR_ORDER):
        raw = {"z1": z1, "z2": z2, "z3": z3}[zkey]
        with col:
            st.markdown(f'<div style="font-weight:700;color:{PALETTE["text_primary"]};margin-bottom:4px">'
                        f'{t(vkey, lang)} <span style="color:{PALETTE["accent"]}">{raw:.2f}</span></div>'
                        + _membership_bars(fz[zkey], lang), unsafe_allow_html=True)
    panel_close()

    # Шаг 2. Правила.
    panel_open(t("trn_s2", lang))
    st.markdown(f'<div style="font-size:13px;color:{PALETTE["text_muted"]};margin-bottom:10px">'
                f'{t("trn_s2_hint", lang)}</div>', unsafe_allow_html=True)
    rules = sorted(CONTROLLER.active_rules(z1, z2, z3), key=lambda r: r["alpha"], reverse=True)[:5]
    for r in rules:
        cond = " · ".join(f'{t(_VAR[k], lang)} {t(_TERM[v], lang)}' for k, v in r["if"].items())
        cons = " · ".join(f'{t(_OUT[k], lang)} {t(_TERM[v], lang)}' for k, v in r["then"].items())
        strength = int(round(r["alpha"] * 100))
        st.markdown(
            f'<div style="border-left:3px solid {PALETTE["accent"]};padding:8px 14px;margin:8px 0;'
            f'background:{PALETTE["bg_subtle"]};border-radius:0 10px 10px 0">'
            f'<span style="color:{PALETTE["text_muted"]};font-size:12px;text-transform:uppercase">'
            f'{t("trn_rule_if", lang)}</span> '
            f'<span style="color:{PALETTE["text_primary"]};font-weight:600">{cond}</span><br>'
            f'<span style="color:{PALETTE["text_muted"]};font-size:12px;text-transform:uppercase">'
            f'{t("trn_rule_then", lang)}</span> '
            f'<span style="color:{PALETTE["text_primary"]};font-weight:600">{cons}</span> '
            f'<span style="color:{PALETTE["accent"]};font-weight:700;margin-left:8px">'
            f'{t("trn_rule_strength", lang)} {strength}%</span></div>',
            unsafe_allow_html=True)
    panel_close()

    # Шаг 3. Действие.
    panel_open(t("trn_s3", lang))
    st.markdown(f'<div style="font-size:13px;color:{PALETTE["text_muted"]};margin-bottom:10px">'
                f'{t("trn_s3_hint", lang)}</div>', unsafe_allow_html=True)
    action = traj.agent_actions[code][idx]
    cols = st.columns(3)
    for col, okey in zip(cols, ("milex", "rhet", "drift")):
        with col:
            st.markdown(
                f'<div class="kpi"><div class="kpi-label">{t(_OUT[okey], lang)}</div>'
                f'<div class="kpi-value" style="color:{PALETTE["accent"]};font-size:34px">'
                f'{action[okey]:.2f}</div></div>', unsafe_allow_html=True)
    panel_close()
