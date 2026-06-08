"""
Компоненты дашборда. Блоки разметки в светлой деловой теме.
"""

from __future__ import annotations

import streamlit as st

from ui.theme import PALETTE, regime_color, verdict_color
from ui.i18n import t, tooltip


def verdict_banner(verdict: dict) -> None:
    """Крупная плашка-светофор с заключением и объяснением из чисел."""
    color = verdict_color(verdict["level"])
    soft = verdict_color(verdict["level"], soft=True)
    st.markdown(
        f"""<div class="verdict" style="background:{soft};border:1px solid {color}">
        <div class="verdict-title" style="color:{color}">
          <span class="verdict-dot" style="background:{color}"></span>{verdict['title']}</div>
        <div class="verdict-text" style="color:{PALETTE['text_primary']}">{verdict['text']}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, color: str = None, delta: str = "") -> None:
    """Карточка показателя с крупной цифрой."""
    c = color or PALETTE["text_primary"]
    d = f'<div class="kpi-delta" style="color:{PALETTE["text_muted"]}">{delta}</div>' if delta else ""
    st.markdown(
        f"""<div class="kpi">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{c}">{value}</div>{d}</div>""",
        unsafe_allow_html=True,
    )


def panel_open(title: str) -> None:
    st.markdown(f'<div class="panel"><div class="panel-title">{title}</div>', unsafe_allow_html=True)


def panel_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def agent_card(name: str, adversary: str, inputs: tuple, action: dict, lang="ru") -> None:
    """Карточка агента с цветными полосами входов и профилем действия."""
    z1, z2, z3 = inputs

    def bar(label_key, value, color, tip_key):
        tip = tooltip(tip_key, lang).replace('"', "&quot;")
        pct = int(round(value * 100))
        return (
            f'<div class="barrow"><span title="{tip}" style="border-bottom:1px dotted {PALETTE["text_muted"]}">'
            f'{t(label_key, lang)}</span><span style="font-weight:700;color:{PALETTE["text_primary"]}">{value:.2f}</span></div>'
            f'<div class="bartrack"><div class="barfill" style="width:{pct}%;background:{color}"></div></div>'
        )

    body = (
        bar("var_threat", z1, PALETTE["s3"], "var_threat")
        + bar("var_trust", z2, PALETTE["s1"], "var_trust")
        + bar("var_erosion", z3, PALETTE["s2"], "var_erosion")
    )
    st.markdown(
        f"""<div class="agentcard">
        <div class="agentcard-name">{name}</div>
        <div class="agentcard-adv">противник · {adversary}</div>
        {body}
        <div style="margin-top:12px;font-size:12px;color:{PALETTE['text_muted']};font-weight:600">
        {t('out_milex', lang)} · {t('out_rhet', lang)} · {t('out_drift', lang)}</div>
        <div style="font-weight:700;color:{PALETTE['text_secondary']};font-size:14px">
        {action['milex']:.2f} · {action['rhet']:.2f} · {action['drift']:.2f}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def threat_type_badge(classification: dict, lang="ru") -> None:
    """Бейдж доминирующего типа угрозы с пояснением."""
    palette_by_type = {
        "material": PALETTE["accent"],
        "alliance": PALETTE["s2"],
        "normative": PALETTE["s3"],
        "mixed": PALETTE["text_muted"],
    }
    color = palette_by_type.get(classification["type"], PALETTE["text_muted"])
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:4px 0 10px 0">
        <span class="pill" style="background:{color};color:#fff">{classification['label']}</span>
        <span style="font-size:14px;color:{PALETTE['text_secondary']}">{classification['text']}</span>
        </div>""",
        unsafe_allow_html=True,
    )



def comparison_matrix(rows: list, lang="ru") -> None:
    """Сводная таблица сравнения сценариев со светофорными точками вердикта."""
    from ui.theme import verdict_color
    head = (f'<tr style="text-align:left;color:{PALETTE["text_muted"]};font-size:12px;'
            f'letter-spacing:1px;text-transform:uppercase">'
            f'<th style="padding:10px 14px">{t("col_scenario", lang)}</th>'
            f'<th style="padding:10px 14px">{t("col_verdict", lang)}</th>'
            f'<th style="padding:10px 14px">{t("col_tension", lang)}</th>'
            f'<th style="padding:10px 14px">{t("col_risk", lang)}</th>'
            f'<th style="padding:10px 14px">{t("col_peak", lang)}</th>'
            f'<th style="padding:10px 14px">{t("col_threat", lang)}</th></tr>')
    body = ""
    for r in rows:
        vc = verdict_color(r["verdict_level"])
        body += (f'<tr style="border-top:1px solid {PALETTE["border"]}">'
                 f'<td style="padding:12px 14px;font-weight:700;color:{PALETTE["text_primary"]}">{r["name"]}</td>'
                 f'<td style="padding:12px 14px"><span class="verdict-dot" '
                 f'style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{vc}"></span></td>'
                 f'<td style="padding:12px 14px;font-weight:700;color:{PALETTE["accent"]}">{r["tension"]:.3f}</td>'
                 f'<td style="padding:12px 14px;font-weight:700;color:{vc}">{r["risk"]*100:.0f}%</td>'
                 f'<td style="padding:12px 14px;color:{PALETTE["text_secondary"]}">{r["peak"]:.3f}</td>'
                 f'<td style="padding:12px 14px;color:{PALETTE["text_secondary"]}">{r["threat_label"]}</td></tr>')
    st.markdown(
        f'<div class="panel"><table style="width:100%;border-collapse:collapse">'
        f'{head}{body}</table></div>',
        unsafe_allow_html=True,
    )
