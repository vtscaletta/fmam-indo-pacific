"""
Реестр выверенных источников. Модуль 12, фактологическая основа.

Содержит состоявшиеся факты, на которых держится калибровка стартовых
значений агентов и реальность исторических событий. Каждый факт привязан к
году, оси давления и источнику. Свежие факts 2024 по 2026 визированы поиском
первоисточника, исторические опоры общеизвестны и подтверждены в списке
литературы диссертации.

Принцип жёсткий. Ни одной выдуманной ссылки. Прогнозные годы за пределами
настоящего в реестр не входят, потому что будущего в источниках нет, и отчёт
по сценарным годам сознательно идёт без ссылок. Поле verified отмечает
факты, ссылку которых подтвердил поиск первоисточника на момент сборки.

Оси. material военная и материальная, alliance союзная, normative нормативная.
"""

from __future__ import annotations


# Год, ось, факт, источник, ссылка, визирован ли поиском первоисточника.
SOURCES = [
    {
        "year": 2012, "axis": "normative",
        "fact": "Национализация трёх островов архипелага Сэнкаку правительством "
                "Японии, запуск устойчивой эскалации присутствия КНР.",
        "source": "Asia News Network, обзор морской экспансии КНР",
        "url": "https://asianews.network/new-developments-seen-in-chinas-maritime-expansion-japan-govt-official-urges-calm-stout-response/",
        "verified": True,
    },
    {
        "year": 2014, "axis": "normative",
        "fact": "Легитимация права на коллективную самооборону через "
                "правительственное толкование, без изменения текста статьи 9.",
        "source": "Решение Кабинета министров Японии, 2014",
        "url": None,
        "verified": False,
    },
    {
        "year": 2015, "axis": "normative",
        "fact": "Принятие пакета законов о мире и безопасности, закрепление "
                "коллективной самообороны на институциональном уровне.",
        "source": "Пакет законов о мире и безопасности, 2015",
        "url": None,
        "verified": False,
    },
    {
        "year": 2022, "axis": "material",
        "fact": "Принятие Стратегии национальной безопасности с легитимацией "
                "потенциала ответного удара, перевод доктрины к наступательным "
                "конвенциональным возможностям.",
        "source": "Стратегия национальной безопасности Японии, 2022",
        "url": None,
        "verified": False,
    },
    {
        "year": 2024, "axis": "material",
        "fact": "Рекорд присутствия КНР у Сэнкаку, 355 дней в прилежащей зоне, "
                "1351 судно за год, по данным Береговой охраны Японии.",
        "source": "The Diplomat",
        "url": "https://thediplomat.com/2025/01/china-sets-record-for-activity-near-senkaku-diaoyu-islands-in-2024/",
        "verified": True,
    },
    {
        "year": 2025, "axis": "alliance",
        "fact": "Заявление премьер-министра Такаити о возможном вовлечении Сил "
                "самообороны при нападении КНР на Тайвань, ноябрь 2025.",
        "source": "Defense News",
        "url": "https://www.defensenews.com/global/asia-pacific/2025/12/26/japans-cabinet-oks-record-defense-budget-that-aims-to-deter-china/",
        "verified": True,
    },
    {
        "year": 2026, "axis": "material",
        "fact": "Рекордный оборонный бюджет на 2026 финансовый год около 9 трлн "
                "йен, рост 9,4 процента, выход на 2 процента ВВП с опережением "
                "графика, ракеты Type-12 дальностью около 1000 км.",
        "source": "The Diplomat, Defense News, Indo-Pacific Defense Forum",
        "url": "https://thediplomat.com/2025/12/japan-accelerates-defense-buildup-with-record-budget-and-expanded-unmanned-capabilities/",
        "verified": True,
    },
    {
        "year": 2026, "axis": "normative",
        "fact": "Победа ЛДП на выборах 8 февраля 2026, 316 из 465 мест, "
                "супербольшинство в две трети, впервые с послевоенного периода "
                "одна партия, заявленный курс на конституционную реформу.",
        "source": "The Japan Times, Nippon.com",
        "url": "https://www.japantimes.co.jp/news/2026/02/09/japan/politics/japan-2026-lower-house-election/",
        "verified": True,
    },
    {
        "year": 2026, "axis": "normative",
        "fact": "Отмена запрета на экспорт летального оружия, 21 апреля 2026, "
                "пересмотр Трёх принципов и отмена системы пяти категорий, "
                "разрешён экспорт истребителей, ракет и кораблей партнёрам.",
        "source": "The Diplomat, IISS, Al Jazeera",
        "url": "https://thediplomat.com/2026/04/breaking-the-postwar-taboo-japan-lifts-its-ban-on-lethal-arms-exports/",
        "verified": True,
    },
]


def sources_until(year: int) -> list:
    """Факты для годов вплоть до указанного включительно, отсортированы."""
    rows = [s for s in SOURCES if s["year"] <= year]
    rows.sort(key=lambda s: s["year"])
    return rows


def sources_for_axis(axis: str) -> list:
    """Факты по одной оси давления."""
    return [s for s in SOURCES if s["axis"] == axis]
