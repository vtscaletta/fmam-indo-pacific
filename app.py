"""
Индо-Тихоокеанский комплекс безопасности. Аналитический дашборд.

Тонкий оркестратор. Вся аналитика в движке, всё оформление в слое интерфейса.
Прогон запускается осознанно, по кнопке, и разворачивается в насыщенную
панель показателей с заключением системы.
"""

import streamlit as st

from engine.agents import AGENTS, run_agent
from engine.scenarios import ALL_SCENARIOS
from engine.simulator import SIMULATOR
from engine.markov import MARKOV
from engine.synthesis import phase_thresholds
from engine.analysis import classify

from ui.theme import build_css, PALETTE, regime_color
from ui.i18n import t, LANGUAGES
from ui.charts import (
    gauge_figure, tension_area_figure, regime_donut_figure,
    regime_area_figure, influence_heatmap_figure, agent_radar_figure,
)
from ui.components import verdict_banner, kpi, panel_open, panel_close, agent_card


st.set_page_config(page_title="Indo-Pacific Security Complex", layout="wide")
st.markdown(f"<style>{build_css()}</style>", unsafe_allow_html=True)

SCENARIO_LABELS = {
    "inertial": "scenario_inertial", "article9": "scenario_article9",
    "taiwan": "scenario_taiwan", "alliance": "scenario_alliance",
}
PLOT_CFG = {"displayModeBar": False}


@st.cache_data(show_spinner=False)
def cached_thresholds():
    return phase_thresholds(MARKOV)


@st.cache_data(show_spinner=False)
def cached_run(scenario_key: str, horizon: int):
    return SIMULATOR.run(ALL_SCENARIOS[scenario_key], AGENTS, horizon=horizon)


def sidebar():
    with st.sidebar:
        st.markdown(f"#### {t('language_label', 'ru')} · Language")
        lang = st.radio("lang", list(LANGUAGES), horizontal=True, label_visibility="collapsed",
                        format_func=lambda x: {"ru": "Русский", "en": "English"}[x])
        st.markdown(f"#### {t('scenario_label', lang)}")
        scenario_key = st.selectbox("scen", list(SCENARIO_LABELS), label_visibility="collapsed",
                                    format_func=lambda k: t(SCENARIO_LABELS[k], lang))
        horizon = st.slider(t("horizon_label", lang), 5, 10, 10)
        run = st.button(t("run_button", lang), use_container_width=True, type="primary")
    return lang, scenario_key, horizon, run


def overview(traj, thresholds, lang):
    verdict = classify(traj, thresholds)
    verdict_banner(verdict)
    st.write("")

    final = traj.dominant[-1]
    last, peak, risk = traj.tension[-1], max(traj.tension), traj.regime_dist[-1][2]
    to_th = thresholds["S2->S3"] - peak

    c = st.columns(4)
    with c[0]: kpi(t("tension_label", lang), f"{last:.3f}", PALETTE["accent"])
    with c[1]: kpi(t("dominant_regime", lang), final, regime_color(final))
    with c[2]: kpi(t("gauge_risk", lang), f"{risk*100:.0f}%", regime_color("S3"))
    with c[3]: kpi(t("to_threshold", lang), f"{to_th:+.3f}",
                   PALETTE["s1"] if to_th > 0 else PALETTE["s3"])
    st.write("")

    a, b = st.columns([1, 2])
    with a:
        panel_open(t("gauge_tension", lang))
        st.plotly_chart(gauge_figure(last, thresholds, ""), use_container_width=True, config=PLOT_CFG)
        panel_close()
    with b:
        panel_open(t("tension_trace", lang))
        st.plotly_chart(tension_area_figure(traj, thresholds, lang), use_container_width=True, config=PLOT_CFG)
        panel_close()

    a, b = st.columns([1, 2])
    with a:
        panel_open(t("regime_final", lang))
        st.plotly_chart(regime_donut_figure(traj.regime_dist[-1], lang), use_container_width=True, config=PLOT_CFG)
        panel_close()
    with b:
        panel_open(t("regime_mix", lang))
        st.plotly_chart(regime_area_figure(traj, lang), use_container_width=True, config=PLOT_CFG)
        panel_close()

    panel_open(t("influence_title", lang))
    st.plotly_chart(influence_heatmap_figure(lang), use_container_width=True, config=PLOT_CFG)
    panel_close()

    if traj.events_log:
        panel_open(t("events_title", lang))
        for year, desc in traj.events_log:
            st.markdown(
                f'<div style="font-size:14px;color:{PALETTE["text_secondary"]};margin:3px 0">'
                f'<b style="color:{PALETTE["accent"]}">{year}</b> · {desc}</div>',
                unsafe_allow_html=True)
        panel_close()


def agents(lang):
    cols = st.columns(5)
    for col, code in zip(cols, AGENTS):
        a = AGENTS[code]
        with col:
            agent_card(a.name, a.adversary, (a.z1, a.z2, a.z3), run_agent(code), lang)
    st.write("")
    cols = st.columns(5)
    for col, code in zip(cols, AGENTS):
        a = AGENTS[code]
        with col:
            st.plotly_chart(agent_radar_figure((a.z1, a.z2, a.z3), a.name, lang),
                            use_container_width=True, config=PLOT_CFG)


def main():
    lang, scenario_key, horizon, run = sidebar()

    if "params" not in st.session_state:
        st.session_state["params"] = None
    if run:
        st.session_state["params"] = (scenario_key, horizon)

    st.markdown(
        f'<div class="dash-eyebrow">{t("app_title", lang)}</div>',
        unsafe_allow_html=True)

    if st.session_state["params"] is None:
        invite = ("Выберите сценарий слева и нажмите «Рассчитать прогноз»."
                  if lang == "ru" else "Pick a scenario on the left and press Run forecast.")
        st.markdown(
            f'<h1>{t("app_subtitle", lang)}</h1>'
            f'<div class="panel" style="margin-top:18px;text-align:center;padding:48px 24px">'
            f'<div style="font-size:20px;font-weight:700;color:{PALETTE["text_primary"]};margin-bottom:8px">'
            f'{"Готов к расчёту" if lang == "ru" else "Ready to compute"}</div>'
            f'<div style="font-size:16px;color:{PALETTE["text_secondary"]}">{invite}</div></div>',
            unsafe_allow_html=True)
        return

    active_key, active_h = st.session_state["params"]
    thresholds = cached_thresholds()
    traj = cached_run(active_key, active_h)

    st.markdown(
        f'<h1>{t(SCENARIO_LABELS[active_key], lang)}, {traj.years[0]}–{traj.years[-1]}</h1>'
        f'<div class="dash-sub">{t("app_subtitle", lang)}</div>',
        unsafe_allow_html=True)
    st.write("")

    tabs = st.tabs([t("tab_overview", lang), t("tab_agents", lang),
                    t("tab_transparency", lang), t("tab_report", lang)])
    with tabs[0]:
        overview(traj, thresholds, lang)
    with tabs[1]:
        agents(lang)
    with tabs[2]:
        st.info("Разбор решения по шагам появится в следующем модуле."
                if lang == "ru" else "Step-by-step trace arrives next.")
    with tabs[3]:
        st.info("Генерация отчёта появится в финальном модуле."
                if lang == "ru" else "Report generation arrives in the final module.")


main()
