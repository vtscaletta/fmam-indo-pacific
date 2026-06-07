"""
Индо-Тихоокеанский комплекс безопасности. Главный файл интерфейса.

Тонкий оркестратор. Вся аналитика в движке, всё оформление в слое интерфейса.
Здесь собирается боковая панель управления, прогон выбранного сценария и
вкладки представления результата.
"""

import streamlit as st

from engine.agents import AGENTS, run_agent
from engine.scenarios import ALL_SCENARIOS
from engine.simulator import SIMULATOR
from engine.markov import MARKOV
from engine.synthesis import phase_thresholds

from ui.theme import build_css, PALETTE, regime_color
from ui.i18n import t, LANGUAGES
from ui.charts import tension_figure, regime_figure
from ui.components import metric_card, regime_badge, agent_card, section_title


st.set_page_config(page_title="Indo-Pacific Security Complex", layout="wide")
st.markdown(f"<style>{build_css()}</style>", unsafe_allow_html=True)


# Соответствие ключей сценариев их подписям в словаре.
SCENARIO_LABELS = {
    "inertial": "scenario_inertial",
    "article9": "scenario_article9",
    "taiwan": "scenario_taiwan",
    "alliance": "scenario_alliance",
}


@st.cache_data(show_spinner=False)
def cached_thresholds():
    return phase_thresholds(MARKOV)


@st.cache_data(show_spinner=False)
def cached_run(scenario_key: str, horizon: int):
    return SIMULATOR.run(ALL_SCENARIOS[scenario_key], AGENTS, horizon=horizon)


def sidebar():
    """Боковая панель управления. Возвращает выбранные язык, сценарий, горизонт."""
    with st.sidebar:
        st.markdown(f"### {t('language_label', 'ru')} · Language")
        lang = st.radio("", list(LANGUAGES), horizontal=True, label_visibility="collapsed",
                        format_func=lambda x: {"ru": "Русский", "en": "English"}[x])

        st.markdown(f"### {t('scenario_label', lang)}")
        scenario_key = st.selectbox(
            "", list(SCENARIO_LABELS), label_visibility="collapsed",
            format_func=lambda k: t(SCENARIO_LABELS[k], lang),
        )

        horizon = st.slider(t("horizon_label", lang), min_value=5, max_value=10, value=10)
        run = st.button(t("run_button", lang), use_container_width=True, type="primary")
    return lang, scenario_key, horizon, run


def overview_tab(traj, thresholds, lang):
    """Вкладка обзора. Сводные метрики и две траектории."""
    final_regime = traj.dominant[-1]
    risk = traj.regime_dist[-1][2]
    peak = max(traj.tension)
    last = traj.tension[-1]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(t("tension_label", lang), f"{last:.3f}", PALETTE["accent_glow"])
    with c2:
        metric_card(t("dominant_regime", lang), final_regime, regime_color(final_regime, glow=True))
    with c3:
        metric_card(t("risk_collapse", lang), f"{risk*100:.0f}%", regime_color("S3", glow=True))
    with c4:
        metric_card("Пик · Peak", f"{peak:.3f}", PALETTE["s2_glow"])

    st.markdown(regime_badge(final_regime, lang), unsafe_allow_html=True)
    st.write("")

    st.plotly_chart(tension_figure(traj, thresholds, lang), use_container_width=True)
    st.plotly_chart(regime_figure(traj, lang), use_container_width=True)

    if traj.events_log:
        section_title(t("step_rules", lang) if False else ("События · Events" if lang == "ru" else "Events"))
        for year, desc in traj.events_log:
            st.markdown(
                f'<div style="color:{PALETTE["text_secondary"]};font-size:13px;margin:2px 0">'
                f'<span class="fmam-mono" style="color:{PALETTE["s2_glow"]}">{year}</span> · {desc}</div>',
                unsafe_allow_html=True,
            )


def agents_tab(lang):
    """Вкладка агентов. Состояния и действия пяти государств базового года."""
    section_title(t("tab_agents", lang))
    cols = st.columns(5)
    for col, code in zip(cols, AGENTS):
        a = AGENTS[code]
        with col:
            agent_card(a.name, (a.z1, a.z2, a.z3), run_agent(code), lang)


def main():
    lang, scenario_key, horizon, _ = sidebar()
    thresholds = cached_thresholds()
    traj = cached_run(scenario_key, horizon)

    st.markdown(
        f'<h1 style="margin-bottom:0">{t("app_title", lang)}</h1>'
        f'<div style="color:{PALETTE["text_muted"]};font-size:14px;margin-bottom:18px">'
        f'{t("app_subtitle", lang)} · {t(SCENARIO_LABELS[scenario_key], lang)}</div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs([
        t("tab_overview", lang), t("tab_agents", lang),
        t("tab_transparency", lang), t("tab_report", lang),
    ])
    with tabs[0]:
        overview_tab(traj, thresholds, lang)
    with tabs[1]:
        agents_tab(lang)
    with tabs[2]:
        st.info("Разбор решения по шагам появится в следующем модуле."
                if lang == "ru" else "Step-by-step decision trace arrives in the next module.")
    with tabs[3]:
        st.info("Генерация отчёта появится в финальном модуле."
                if lang == "ru" else "Report generation arrives in the final module.")


main()
