"""
Слой представления отчёта. Модуль 12, витрина.

Превращает невидимые слои данных и текста в видимый отчёт на экране и в файл
для скачивания. Оба собираются из одного источника, потому экранная и
выгруженная версии тождественны по содержанию. Графики живут на экране,
скачиваемый файл несёт текст и таблицы.

Разделение ответственности. Этот модуль ничего не считает и не сочиняет, он
только размещает готовые структуры build_report_data и build_narrative по
экрану и собирает из них Markdown. Источники и врезки холмиков по узловым
годам лягут следующими модулями.
"""

from __future__ import annotations

import streamlit as st

from engine.report import build_report_data
from engine.report_text import build_narrative
from ui.theme import PALETTE
from ui.i18n import t
from ui.components import verdict_banner, threat_type_badge, panel_open, panel_close
from ui.charts import tension_area_figure


class _Meta:
    """Лёгкая обёртка имени и описания сценария для слоя данных.

    События отчёт берёт из самой траектории, поэтому объект сценария здесь не
    нужен, достаточно имени и описания для шапки.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.events = []


_PLOT_CFG = {"displaylogo": False, "scrollZoom": False,
             "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def _to_markdown(narr: dict, data: dict, lang: str) -> str:
    """Собирает скачиваемый Markdown из тех же структур, что и экран."""
    lines = [f"# {narr['title']}", "", f"_{narr['subtitle']}_", ""]
    for sec in narr["sections"]:
        lines.append(f"## {sec['heading']}")
        lines.append("")
        for p in sec["paragraphs"]:
            lines.append(p)
            lines.append("")
    # Таблица узловых лет.
    lines.append(f"## {t('report_nodal', lang)}")
    lines.append("")
    lines.append(f"| {t('report_year', lang)} | {t('report_event', lang)} | {t('report_tension', lang)} |")
    lines.append("| --- | --- | --- |")
    tmap = {row["year"]: row["tension"] for row in data["timeline"]}
    for node in data["nodal_years"]:
        tau = tmap.get(node["year"], "")
        tau_s = f"{tau:.3f}" if isinstance(tau, float) else ""
        lines.append(f"| {node['year']} | {node['kind']} | {tau_s} |")
    lines.append("")
    return "\n".join(lines)


def render_report(traj, title: str, description: str, thresholds: dict, lang: str) -> None:
    """Главная функция вкладки отчёта. Экран плюс кнопка скачивания."""
    data = build_report_data(traj, _Meta(title, description), thresholds)
    narr = build_narrative(data)

    st.markdown(f'<h2 style="margin-bottom:2px">{narr["title"]}</h2>'
                f'<div style="color:{PALETTE["text_muted"]};font-size:14px;margin-bottom:14px">'
                f'{narr["subtitle"]}</div>', unsafe_allow_html=True)

    # Приговор и природа угрозы наверху, как исполнительное резюме.
    verdict_banner(data["verdict"])
    threat_type_badge(data["threat_type"], lang)

    # Врезка, траектория напряжения с порогами.
    panel_open(t("report_trajectory", lang))
    st.plotly_chart(tension_area_figure(traj, thresholds, lang),
                    use_container_width=True, config=_PLOT_CFG)
    panel_close()

    # Текстовые разделы, что знаем, что думаем, чего не знаем.
    for sec in narr["sections"]:
        if sec["heading"] == "Резюме":
            continue  # резюме уже отражено баннером и бейджем выше
        panel_open(sec["heading"])
        for p in sec["paragraphs"]:
            st.markdown(f'<div style="font-size:15px;line-height:1.6;'
                        f'color:{PALETTE["text_primary"]};margin-bottom:10px">{p}</div>',
                        unsafe_allow_html=True)
        panel_close()

    # Таблица узловых лет.
    panel_open(t("report_nodal", lang))
    tmap = {row["year"]: row["tension"] for row in data["timeline"]}
    rows = "".join(
        f'<tr><td style="padding:7px 14px;font-weight:700;color:{PALETTE["accent"]}">{n["year"]}</td>'
        f'<td style="padding:7px 14px;color:{PALETTE["text_primary"]}">{n["kind"]}</td>'
        f'<td style="padding:7px 14px;text-align:right;font-family:monospace">'
        f'{tmap.get(n["year"], 0):.3f}</td></tr>'
        for n in data["nodal_years"]
    )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
        f'<tr style="color:{PALETTE["text_muted"]};font-size:12px;text-transform:uppercase">'
        f'<th style="padding:7px 14px;text-align:left">{t("report_year", lang)}</th>'
        f'<th style="padding:7px 14px;text-align:left">{t("report_event", lang)}</th>'
        f'<th style="padding:7px 14px;text-align:right">{t("report_tension", lang)}</th></tr>'
        f'{rows}</table>', unsafe_allow_html=True)
    panel_close()

    # Скачивание из единого источника.
    md = _to_markdown(narr, data, lang)
    st.download_button(
        t("report_download", lang), data=md.encode("utf-8"),
        file_name="fmam_report.md", mime="text/markdown",
        use_container_width=True,
    )
