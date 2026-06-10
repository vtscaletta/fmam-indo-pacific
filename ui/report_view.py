"""
Слой представления отчёта. Модуль 12, витрина.

Превращает невидимые слои данных и текста в видимый отчёт на экране и в
самодостаточный HTML для скачивания. Экранная и выгруженная версии собраны
из одного источника, потому тождественны по содержанию. График в HTML живой,
встроен целиком, поэтому файл открывается в любом браузере и печатается в PDF
с сохранением графика.

Разделение ответственности. Модуль ничего не считает и не сочиняет, только
размещает готовые структуры build_report_data и build_narrative по экрану и
собирает из них HTML. Источники и врезки холмиков лягут следующими модулями.
"""

from __future__ import annotations

import html as _html
import re

import streamlit as st
import plotly.io as pio

from engine.report import build_report_data
from engine.report_text import build_narrative
from ui.theme import PALETTE
from ui.i18n import t
from ui.components import verdict_banner, threat_type_badge, panel_open, panel_close
from ui.charts import tension_area_figure


class _Meta:
    """Лёгкая обёртка имени и описания сценария для слоя данных.

    События отчёт берёт из самой траектории, потому объект сценария здесь не
    нужен, достаточно имени и описания для шапки.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.events = []


_PLOT_CFG = {"displaylogo": False, "scrollZoom": False,
             "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


_CITE_RE = re.compile(r"\[\[(.+?)\|\|(.+?)\]\]")


def _render_inline(text: str, by_key: dict, color: str) -> str:
    """
    Превращает абзац прозы с якорями [[ключ||фраза]] в безопасный HTML, где
    помеченная фраза становится инлайн-ссылкой на первоисточник. Сегменты
    экранируются по отдельности, потому спецсимволы текста безвредны.

    Три ветки. Ключ найден и у источника есть ссылка, фраза становится цветной
    ссылкой со штриховым подчёркиванием. Ключ найден, но публичной ссылки нет,
    фраза получает пунктир и всплывающее имя источника, без перехода. Ключ не
    найден, фраза остаётся обычным текстом, а рассинхрон ловится тестом, не
    падением отрисовки.
    """
    out, pos = [], 0
    for m in _CITE_RE.finditer(text):
        out.append(_html.escape(text[pos:m.start()]))
        key, phrase = m.group(1), m.group(2)
        src = by_key.get(key)
        esc = _html.escape(phrase)
        if src and src.get("url"):
            out.append(
                f'<a href="{_html.escape(src["url"])}" target="_blank" rel="noopener" '
                f'style="color:{color};text-decoration:none;'
                f'border-bottom:1px dashed {color}">{esc}</a>')
        elif src:
            out.append(
                f'<span style="border-bottom:1px dotted {color};cursor:help" '
                f'title="{_html.escape(src["source"])}">{esc}</span>')
        else:
            out.append(esc)
        pos = m.end()
    out.append(_html.escape(text[pos:]))
    return "".join(out)


def _to_html(narr: dict, data: dict, fig, lang: str) -> str:
    """
    Самодостаточный HTML отчёта с живым графиком внутри. Печатается в PDF из
    браузера с сохранением графики. Кириллица в UTF-8 без хлопот со шрифтами.
    """
    chart = pio.to_html(fig, include_plotlyjs="inline", full_html=False,
                        config={"displayModeBar": False})
    by_key = {s["key"]: s for s in data.get("sources", [])}
    blocks = [f'<h1>{_html.escape(narr["title"])}</h1>',
              f'<p class="sub">{_html.escape(narr["subtitle"])}</p>']
    for i, sec in enumerate(narr["sections"]):
        blocks.append(f'<h2>{_html.escape(sec["heading"])}</h2>')
        for p in sec["paragraphs"]:
            blocks.append(f'<p>{_render_inline(p, by_key, "#9D2933")}</p>')
        # График после раздела динамики.
        if sec["heading"].startswith("Динамика"):
            blocks.append(f'<div class="chart">{chart}</div>')
    body = "\n".join(blocks)
    # Источники теперь вплетены в саму прозу инлайн-ссылками, отдельной панели
    # калибровки в конце документа нет.
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>{_html.escape(narr["title"])}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 820px;
         margin: 40px auto; padding: 0 24px; color: #1a1a1a; line-height: 1.65;
         font-size: 17px; }}
  h1 {{ font-size: 26px; color: #1F4788; margin-bottom: 4px; }}
  h2 {{ font-size: 22px; color: #1F4788; margin-top: 28px;
        border-bottom: 1px solid #d8dee9; padding-bottom: 5px; }}
  p {{ font-size: 17px; margin: 11px 0; text-align: justify; }}
  .sub {{ color: #6b7280; font-style: italic; font-size: 16px; }}
  .chart {{ margin: 18px 0; }}
  @media print {{ body {{ margin: 0; }} h2 {{ page-break-after: avoid; }} }}
</style></head><body>
{body}
</body></html>"""


def render_report(traj, title: str, description: str, thresholds: dict,
                  lang: str, baseline=None) -> None:
    """Главная функция вкладки отчёта. Экран плюс выгрузка в HTML."""
    data = build_report_data(traj, _Meta(title, description), thresholds,
                             baseline=baseline)
    narr = build_narrative(data)
    by_key = {s["key"]: s for s in data.get("sources", [])}

    st.markdown(f'<h2 style="margin-bottom:2px;font-size:26px">{narr["title"]}</h2>'
                f'<div style="color:{PALETTE["text_muted"]};font-size:16px;'
                f'margin-bottom:12px">{narr["subtitle"]}</div>', unsafe_allow_html=True)

    verdict_banner(data["verdict"])
    threat_type_badge(data["threat_type"], lang)

    fig = tension_area_figure(traj, thresholds, lang)

    # Текстовые разделы. Резюме отражено баннером выше, потому пропускаем.
    for sec in narr["sections"]:
        if sec["heading"] == "Сводное заключение":
            continue
        panel_open(sec["heading"])
        for p in sec["paragraphs"]:
            st.markdown(f'<div style="font-size:17px;line-height:1.65;'
                        f'color:{PALETTE["text_primary"]};margin-bottom:9px">'
                        f'{_render_inline(p, by_key, PALETTE["accent"])}</div>',
                        unsafe_allow_html=True)
        # Врезка графика после раздела динамики.
        if sec["heading"].startswith("Динамика"):
            st.plotly_chart(fig, use_container_width=True, config=_PLOT_CFG,
                            key="report_tension_chart")
        panel_close()

    # Таблица узловых лет.
    panel_open(t("report_nodal", lang))
    tmap = {row["year"]: row["tension"] for row in data["timeline"]}
    rows = "".join(
        f'<tr><td style="padding:8px 14px;font-weight:700;font-size:17px;'
        f'color:{PALETTE["accent"]}">{n["year"]}</td>'
        f'<td style="padding:8px 14px;font-size:16px;color:{PALETTE["text_primary"]}">{n["kind"]}</td>'
        f'<td style="padding:8px 14px;text-align:right;font-family:monospace;'
        f'font-size:16px">{tmap.get(n["year"], 0):.3f}</td></tr>'
        for n in data["nodal_years"]
    )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<tr style="color:{PALETTE["text_muted"]};font-size:14px;text-transform:uppercase">'
        f'<th style="padding:8px 14px;text-align:left">{t("report_year", lang)}</th>'
        f'<th style="padding:8px 14px;text-align:left">{t("report_event", lang)}</th>'
        f'<th style="padding:8px 14px;text-align:right">{t("report_tension", lang)}</th></tr>'
        f'{rows}</table>', unsafe_allow_html=True)
    panel_close()

    # Панели источников калибровки больше нет. Источники вплетены в прозу
    # инлайн-ссылками, цветное слово ведёт на первоисточник своего утверждения.

    # Выгрузка в самодостаточный HTML с живым графиком.
    html_doc = _to_html(narr, data, fig, lang)
    st.download_button(
        t("report_download", lang), data=html_doc.encode("utf-8"),
        file_name="fmam_report.html", mime="text/html",
        use_container_width=False,
    )
    st.caption(t("report_print_hint", lang))
