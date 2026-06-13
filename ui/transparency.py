"""
Разбор решения. Прозрачность вычисления по шагам, как учитель у доски.

Раскрывает кухню движка для одного агента в один год: как числовое
состояние переводится в нечёткие термины, какие правила реализма срабатывают
и с какой силой, как они сворачиваются в действие, и как действия всех
агентов синтезируются в системное напряжение года. Каждый шаг сопровождается
точной формулой с подстановкой реальных чисел. Никакого чёрного ящика.
"""

from __future__ import annotations

import streamlit as st

from engine.agents import AGENTS
from engine.fuzzy_agent import JAPAN as CONTROLLER
from engine.synthesis import (
    perceptual_pressure,
    influence_weights,
    DifferentialMemory,
    DEFAULT_BETA,
    PRESSURE_WEIGHTS,
)
from ui.theme import PALETTE
from ui.i18n import t
from ui.components import panel_open, panel_close
from ui.charts import membership_figure


# Перевод служебных меток в человеческий язык интерфейса.
_TERM = {"low": "term_low", "med": "term_med", "high": "term_high"}
_VAR = {"threat": "var_threat", "trust": "var_trust", "erosion": "var_erosion"}
_OUT = {"milex": "out_milex", "rhet": "out_rhet", "drift": "out_drift"}
_VAR_ORDER = [("z1", "var_threat"), ("z2", "var_trust"), ("z3", "var_erosion")]
# Латинский индекс терма для формул, чтобы KaTeX рендерил без кириллицы.
_TERM_TEX = {"low": "L", "med": "M", "high": "H"}
_VAR_TEX = {"z1": "z_1", "z2": "z_2", "z3": "z_3"}


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


def _hint(text: str) -> None:
    st.markdown(f'<div style="font-size:13px;color:{PALETTE["text_muted"]};margin-bottom:10px">'
                f'{text}</div>', unsafe_allow_html=True)


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
    zmap = {"z1": z1, "z2": z2, "z3": z3}

    # --- Шаг 1. Фаззификация ---
    panel_open(t("trn_s1", lang))
    _hint(t("trn_s1_hint", lang))
    fz = CONTROLLER.fuzzify(z1, z2, z3)
    cols = st.columns(3)
    for col, (zkey, vkey) in zip(cols, _VAR_ORDER):
        params = {term: CONTROLLER.mf_params(zkey, term) for term in ("low", "med", "high")}
        with col:
            st.plotly_chart(
                membership_figure(t(vkey, lang), zmap[zkey], params, fz[zkey], lang),
                use_container_width=True,
                config={"displaylogo": False, "scrollZoom": False,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]},
                key=f"trn_mf_{zkey}",
            )

    _hint(t("trn_s1_math", lang))
    for zkey, _vkey in _VAR_ORDER:
        term = max(fz[zkey], key=fz[zkey].get)        # доминирующий терм
        cen, sig = CONTROLLER.mf_params(zkey, term)
        z = zmap[zkey]
        mu = fz[zkey][term]
        st.latex(
            rf"\mu_{{{_TERM_TEX[term]}}}({_VAR_TEX[zkey]}) "
            rf"= \exp\!\left(-\frac{{({z:.2f} - {cen:.2f})^2}}{{2\cdot {sig:.3f}^2}}\right) = {mu:.2f}"
        )
    panel_close()

    # --- Шаг 2. Правила ---
    panel_open(t("trn_s2", lang))
    _hint(t("trn_s2_hint", lang))
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

    _hint(t("trn_s2_math", lang))
    top = rules[0]
    mu1 = fz["z1"][top["if"]["threat"]]
    mu2 = fz["z2"][top["if"]["trust"]]
    mu3 = fz["z3"][top["if"]["erosion"]]
    st.latex(
        rf"\alpha = \min(\mu_1, \mu_2, \mu_3) "
        rf"= \min({mu1:.2f},\ {mu2:.2f},\ {mu3:.2f}) = {top['alpha']:.2f}"
    )
    panel_close()

    # --- Шаг 3. Действие ---
    panel_open(t("trn_s3", lang))
    _hint(t("trn_s3_hint", lang))
    action = traj.agent_actions[code][idx]
    cols = st.columns(3)
    for col, okey in zip(cols, ("milex", "rhet", "drift")):
        with col:
            st.markdown(
                f'<div class="kpi"><div class="kpi-label">{t(_OUT[okey], lang)}</div>'
                f'<div class="kpi-value" style="color:{PALETTE["accent"]};font-size:34px">'
                f'{action[okey]:.2f}</div></div>', unsafe_allow_html=True)

    _hint(t("trn_s3_math", lang))
    st.latex(
        r"X^{*} = \frac{\int \mu(z)\,z\,dz}{\int \mu(z)\,dz}"
        rf"\quad\Rightarrow\quad \Delta\text{{MilEx}} = {action['milex']:.2f},\ "
        rf"\Delta\text{{Rhet}} = {action['rhet']:.2f},\ "
        rf"\Delta\text{{Drift}} = {action['drift']:.2f}"
    )
    panel_close()

    # --- Шаг 4. Системный уровень. Синтез напряжения ---
    panel_open(t("trn_s4", lang))
    _hint(t("trn_s4_hint", lang))

    # Память: формула и коэффициенты забывания.
    st.latex(
        r"\hat{H}_X(t) = \lambda_X^{\uparrow}\,\hat{H}_X(t{-}1) "
        r"+ (1-\lambda_X^{\uparrow})\,\bar{X}(t)\quad"
        r"[\,\bar{X}(t)\ge \hat{H}_X(t{-}1)\,]"
    )
    _hint(t("trn_s4_mem", lang))
    lam = DifferentialMemory().lam
    lam_rows = " · ".join(
        f'{t(_OUT[k], lang)} (↑ {lam[k][0]}, ↓ {lam[k][1]})' for k in ("milex", "rhet", "drift")
    )
    st.markdown(f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin:2px 0 12px">'
                f'{t("trn_lam_label", lang)}: {lam_rows}</div>', unsafe_allow_html=True)

    # Перцептивное давление: формула с подстановкой по году.
    states_year = {ac: traj.agent_states[ac][idx] for ac in AGENTS}
    pi = perceptual_pressure(states_year, influence_weights())
    pw = PRESSURE_WEIGHTS
    st.latex(
        r"\Pi(t) = \sum_n w_n\,(c_1 z_1 + c_2(1-z_2) + c_3 z_3)"
        rf",\quad c=({pw['threat']},\ {pw['distrust']},\ {pw['erosion']})"
        rf"\quad\Rightarrow\quad \Pi = {pi:.3f}"
    )
    _hint(t("trn_s4_pi", lang))

    # Синтез: формула и итоговое напряжение года.
    b = DEFAULT_BETA
    tau = traj.tension[idx]
    st.latex(
        r"\tau(t) = \Phi\!\left(\beta_0 + \beta_M \hat{H}_M + \beta_R \hat{H}_R "
        r"+ \beta_D \hat{H}_D + \beta_\Pi\,\Pi\right)"
        rf"\quad\Rightarrow\quad \tau = {tau:.3f}"
    )
    st.markdown(
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin:2px 0">'
        f'β₀ {b["b0"]} · β_M {b["milex"]} · β_R {b["rhet"]} · β_D {b["drift"]} · β_Π {b["pressure"]}</div>',
        unsafe_allow_html=True)
    _hint(t("trn_s4_tau", lang))
    panel_close()

    # --- Полный свод 27 правил для приложения ---
    with st.expander(t("trn_all_rules", lang)):
        for i, r in enumerate(CONTROLLER.all_rules(), 1):
            cond = " · ".join(f'{t(_VAR[k], lang)} {t(_TERM[v], lang)}' for k, v in r["if"].items())
            cons = " · ".join(f'{t(_OUT[k], lang)} {t(_TERM[v], lang)}' for k, v in r["then"].items())
            st.markdown(
                f'<div style="font-size:12.5px;padding:4px 0;border-bottom:1px solid {PALETTE["bg_page"]}">'
                f'<span style="color:{PALETTE["text_muted"]}">{i:>2}.</span> '
                f'<span style="color:{PALETTE["text_muted"]};text-transform:uppercase;font-size:11px">'
                f'{t("trn_rule_if", lang)}</span> {cond} '
                f'<span style="color:{PALETTE["text_muted"]};text-transform:uppercase;font-size:11px">'
                f'{t("trn_rule_then", lang)}</span> '
                f'<span style="color:{PALETTE["text_primary"]}">{cons}</span></div>',
                unsafe_allow_html=True)
