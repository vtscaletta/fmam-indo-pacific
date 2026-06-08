"""
Индо-Тихоокеанский комплекс безопасности. Аналитический дашборд.

Сценарный анализ, не прогноз. Система не предсказывает одно будущее, а
проигрывает условные траектории при заданных допущениях и обнажает их
механику. Готовые сценарии и конструктор собственного мира из событий.
"""

import streamlit as st

from engine.agents import AGENTS, run_agent
from engine.scenarios import (ALL_SCENARIOS, EVENT_CATALOG, MAGNITUDE_LEVELS,
                              build_custom_scenario)
from engine.simulator import SIMULATOR
from engine.markov import MARKOV
from engine.synthesis import phase_thresholds
from engine.analysis import classify, classify_threat_type

from ui.theme import build_css, PALETTE, regime_color
from ui.i18n import t, LANGUAGES
from ui.charts import (gauge_figure, tension_area_figure, regime_donut_figure,
                       regime_area_figure, influence_heatmap_figure, agent_radar_figure)
from ui.components import (verdict_banner, kpi, panel_open, panel_close,
                           agent_card, threat_type_badge)


st.set_page_config(page_title="Indo-Pacific Security Complex", layout="wide")
st.markdown(f"<style>{build_css()}</style>", unsafe_allow_html=True)

SCENARIO_LABELS = {"inertial": "scenario_inertial", "article9": "scenario_article9",
                   "taiwan": "scenario_taiwan", "alliance": "scenario_alliance"}
PLOT_CFG = {"displayModeBar": False}


@st.cache_data(show_spinner=False)
def cached_thresholds():
    return phase_thresholds(MARKOV)


@st.cache_data(show_spinner=False)
def cached_run(scenario_key: str, horizon: int):
    return SIMULATOR.run(ALL_SCENARIOS[scenario_key], AGENTS, horizon=horizon)


def run_custom(spec, horizon, name):
    return SIMULATOR.run(build_custom_scenario(spec, name), AGENTS, horizon=horizon)


def sidebar():
    with st.sidebar:
        st.markdown(f"#### {t('language_label', 'ru')} · Language")
        lang = st.radio("lang", list(LANGUAGES), horizontal=True, label_visibility="collapsed",
                        format_func=lambda x: {"ru": "Русский", "en": "English"}[x])
        st.markdown(f"#### {t('mode_label', lang)}")
        mode = st.radio("mode", ["ready", "custom", "compare"], label_visibility="collapsed",
                        format_func=lambda m: t(f"mode_{m}", lang))
        horizon = st.slider(t("horizon_label", lang), 5, 10, 10)
        key, run = None, False
        if mode == "ready":
            st.markdown(f"#### {t('scenario_label', lang)}")
            key = st.selectbox("scen", list(SCENARIO_LABELS), label_visibility="collapsed",
                               format_func=lambda k: t(SCENARIO_LABELS[k], lang))
            run = st.button(t("run_button", lang), use_container_width=True, type="primary")
        st.markdown("---")
        if st.button(t("reset_button", lang), use_container_width=True):
            for k in ("active", "custom_traj", "builder_spec"):
                st.session_state.pop(k, None)
            st.rerun()
    return lang, mode, key, horizon, run


def builder_panel(lang, horizon):
    """Конструктор мира. Возвращает (spec, play)."""
    if "builder_spec" not in st.session_state:
        st.session_state["builder_spec"] = []
    spec = st.session_state["builder_spec"]

    panel_open(t("builder_title", lang))
    st.markdown(f'<div style="color:{PALETTE["text_secondary"]};font-size:14px;margin-bottom:12px">'
                f'{t("builder_hint", lang)}</div>', unsafe_allow_html=True)

    c = st.columns([1, 1.4, 1.8, 1.2, 0.9])
    years = list(range(2025, 2025 + horizon))
    with c[0]:
        year = st.selectbox(t("ev_year", lang), years, key="ev_year")
    with c[1]:
        agent = st.selectbox(t("ev_agent", lang), list(AGENTS),
                             format_func=lambda k: AGENTS[k].name, key="ev_agent")
    with c[2]:
        event = st.selectbox(t("ev_type", lang), list(EVENT_CATALOG),
                             format_func=lambda k: EVENT_CATALOG[k][lang], key="ev_type")
    with c[3]:
        force = st.selectbox(t("ev_force", lang), list(MAGNITUDE_LEVELS),
                             format_func=lambda k: t(f"force_{k}", lang), key="ev_force")
    with c[4]:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button(t("ev_add", lang), use_container_width=True):
            spec.append({"step": year - 2025, "agent": agent, "event": event, "magnitude": force})

    if spec:
        for i, it in enumerate(spec):
            cat = EVENT_CATALOG[it["event"]]
            force_label = t(f"force_{it['magnitude']}", lang)
            line = (f'{2025 + it["step"]} · {AGENTS[it["agent"]].name} · '
                    f'{cat[lang]} · {force_label}')
            col = st.columns([8, 1])
            with col[0]:
                st.markdown(f'<div style="font-size:14px;color:{PALETTE["text_secondary"]};'
                            f'padding:4px 0">{line}</div>', unsafe_allow_html=True)
            with col[1]:
                if st.button(t("ev_remove", lang), key=f"del_{i}"):
                    spec.pop(i)
                    st.rerun()
    else:
        st.markdown(f'<div style="color:{PALETTE["text_muted"]};font-size:14px;padding:8px 0">'
                    f'{t("ev_empty", lang)}</div>', unsafe_allow_html=True)

    b = st.columns([1, 1, 3])
    with b[0]:
        play = st.button(t("ev_play", lang), use_container_width=True, type="primary", disabled=not spec)
    with b[1]:
        if st.button(t("ev_clear", lang), use_container_width=True):
            st.session_state["builder_spec"] = []
            st.rerun()
    panel_close()
    return spec, play


def overview(traj, thresholds, baseline, lang):
    verdict = classify(traj, thresholds)
    verdict_banner(verdict)
    threat = classify_threat_type(traj, baseline=baseline)
    threat_type_badge(threat, lang)
    st.write("")

    final = traj.dominant[-1]
    last, peak, risk = traj.tension[-1], max(traj.tension), traj.regime_dist[-1][2]
    to_th = thresholds["S2->S3"] - peak
    c = st.columns(4)
    with c[0]: kpi(t("tension_label", lang), f"{last:.3f}", PALETTE["accent"])
    with c[1]: kpi(t("dominant_regime", lang), final, regime_color(final))
    with c[2]: kpi(t("gauge_risk", lang), f"{risk*100:.0f}%", regime_color("S3"))
    with c[3]: kpi(t("to_threshold", lang), f"{to_th:+.3f}", PALETTE["s1"] if to_th > 0 else PALETTE["s3"])
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
        view = st.radio(t("regime_view", lang), ["area", "lines"], horizontal=True,
                        label_visibility="collapsed", key="regime_view_sel",
                        format_func=lambda m: t(f"view_{m}", lang))
        st.plotly_chart(regime_area_figure(traj, lang, mode=view), use_container_width=True, config=PLOT_CFG)
        panel_close()

    panel_open(t("influence_title", lang))
    st.plotly_chart(influence_heatmap_figure(lang), use_container_width=True, config=PLOT_CFG)
    panel_close()

    if traj.events_log:
        panel_open(t("events_title", lang))
        for year, desc in traj.events_log:
            st.markdown(f'<div style="font-size:14px;color:{PALETTE["text_secondary"]};margin:3px 0">'
                        f'<b style="color:{PALETTE["accent"]}">{year}</b> · {desc}</div>', unsafe_allow_html=True)
        panel_close()


def agents(traj, lang):
    cols = st.columns(5)
    for col, code in zip(cols, AGENTS):
        a = AGENTS[code]
        start = tuple(traj.agent_states[code][0])
        final = tuple(traj.agent_states[code][-1])
        action = traj.agent_actions[code][-1]
        with col:
            agent_card(a.name, a.adversary, start, final, action, lang)
    st.write("")
    cols = st.columns(5)
    for col, code in zip(cols, AGENTS):
        a = AGENTS[code]
        start = tuple(traj.agent_states[code][0])
        final = tuple(traj.agent_states[code][-1])
        with col:
            st.plotly_chart(agent_radar_figure(start, final, a.name, lang),
                            use_container_width=True, config=PLOT_CFG)


def render_dashboard(traj, title, lang):
    thresholds = cached_thresholds()
    baseline = cached_run("inertial", len(traj.years))
    st.markdown(f'<h1>{title}, {traj.years[0]}–{traj.years[-1]}</h1>'
                f'<div class="dash-sub">{t("app_subtitle", lang)}</div>', unsafe_allow_html=True)
    st.write("")
    tabs = st.tabs([t("tab_overview", lang), t("tab_agents", lang),
                    t("tab_transparency", lang), t("tab_report", lang)])
    with tabs[0]:
        overview(traj, thresholds, baseline, lang)
    with tabs[1]:
        agents(traj, lang)
    with tabs[2]:
        st.info("Разбор решения по шагам появится в следующем модуле."
                if lang == "ru" else "Step-by-step trace arrives next.")
    with tabs[3]:
        st.info("Генерация отчёта появится в финальном модуле."
                if lang == "ru" else "Report generation arrives in the final module.")


def compare_view(lang, horizon):
    """Сравнение всех готовых сценариев бок о бок."""
    from ui.charts import comparison_tension_figure, comparison_risk_figure
    from ui.components import comparison_matrix

    thresholds = cached_thresholds()
    baseline = cached_run("inertial", horizon)
    trajs = {k: cached_run(k, horizon) for k in SCENARIO_LABELS}
    labels = {k: t(SCENARIO_LABELS[k], lang) for k in SCENARIO_LABELS}

    # Если пользователь собрал свой сценарий, он встаёт пятой линией.
    custom = st.session_state.get("custom_traj")
    has_custom = custom is not None and len(custom.years) == horizon
    if has_custom:
        trajs["custom"] = custom
        labels["custom"] = t("custom_name", lang)

    st.markdown(f'<h1>{t("cmp_title", lang)}</h1>'
                f'<div class="dash-sub">{t("app_subtitle", lang)}</div>', unsafe_allow_html=True)
    if not has_custom:
        st.markdown(
            f'<div style="font-size:14px;color:{PALETTE["text_muted"]};margin-bottom:6px">'
            + ("Соберите свой сценарий в режиме «Свой сценарий», и он встанет пятой линией для сравнения."
               if lang == "ru" else
               "Assemble a custom scenario to add it as a fifth line here.")
            + "</div>", unsafe_allow_html=True)
    st.write("")

    panel_open(t("cmp_tension", lang))
    st.plotly_chart(comparison_tension_figure(trajs, thresholds, labels, lang),
                    use_container_width=True, config=PLOT_CFG)
    panel_close()

    rows = []
    for k in trajs:
        tr = trajs[k]
        v = classify(tr, thresholds)
        threat = classify_threat_type(tr, baseline=baseline)
        rows.append({"name": labels[k], "verdict_level": v["level"],
                     "tension": tr.tension[-1], "risk": tr.regime_dist[-1][2],
                     "peak": max(tr.tension), "threat_label": threat["label"]})

    a, b = st.columns([3, 2])
    with a:
        panel_open(t("cmp_table", lang))
        comparison_matrix(rows, lang)
        panel_close()
    with b:
        panel_open(t("cmp_risk", lang))
        st.plotly_chart(comparison_risk_figure(trajs, labels, lang),
                        use_container_width=True, config=PLOT_CFG)
        panel_close()


def main():
    lang, mode, key, horizon, run = sidebar()
    st.markdown(f'<div class="dash-eyebrow">{t("app_title", lang)}</div>', unsafe_allow_html=True)

    if mode == "compare":
        compare_view(lang, horizon)
        return

    if mode == "ready":
        if run:
            st.session_state["active"] = ("preset", key, horizon)
        active = st.session_state.get("active")
        if not active or active[0] != "preset":
            invite = ("Выберите сценарий слева и нажмите «Проиграть сценарий»."
                      if lang == "ru" else "Pick a scenario and press Run scenario.")
            st.markdown(f'<h1>{t("app_subtitle", lang)}</h1>'
                        f'<div class="panel" style="margin-top:18px;text-align:center;padding:48px 24px">'
                        f'<div style="font-size:20px;font-weight:700;margin-bottom:8px">'
                        f'{"Готов к расчёту" if lang=="ru" else "Ready"}</div>'
                        f'<div style="font-size:16px;color:{PALETTE["text_secondary"]}">{invite}</div></div>',
                        unsafe_allow_html=True)
            return
        _, k, h = active
        render_dashboard(cached_run(k, h), t(SCENARIO_LABELS[k], lang), lang)
    else:
        spec, play = builder_panel(lang, horizon)
        if play and spec:
            traj = run_custom(list(spec), horizon, t("custom_name", lang))
            st.session_state["custom_traj"] = traj
        traj = st.session_state.get("custom_traj")
        if traj is not None:
            st.write("")
            render_dashboard(traj, t("custom_name", lang), lang)


main()
