"""
Реестр выверенных источников. Модуль 12, фактологическая основа.

Содержит состоявшиеся факты, на которых держится калибровка стартовых
значений агентов и реальность исторических событий. Каждый факт привязан к
агенту, году, оси давления и источнику, и несёт устойчивый ключ, по которому
проза отчёта цепляет инлайн-ссылку к конкретной фразе. Свежие факты 2024 по
2026 визированы поиском первоисточника, исторические опоры общеизвестны и
подтверждены в списке литературы диссертации.

Принцип жёсткий. Ни одной выдуманной ссылки. Прогнозные годы за пределами
настоящего в реестр не входят, потому что будущего в источниках нет, и отчёт
по сценарным годам сознательно идёт без ссылок. Поле verified отмечает факты,
ссылку которых подтвердил поиск первоисточника на момент сборки.

Поля записи.
  key      устойчивый уникальный якорь факта, по нему проза ставит ссылку
  agent    код агента, к чьей калибровке относится факт, строчными jpn chn
  year     год факта
  axis     ось давления, material военная, alliance союзная, normative нормативная
  fact     человекочитаемая формулировка факта
  source   издание или документ
  url      ссылка на первоисточник либо None
  verified подтверждена ли ссылка поиском первоисточника

Соглашение по ключам. Имя складывается как agent_topic_year строчными через
подчёркивание, например jpn_arms_export_2026. По мере расширения реестра на
прочих агентов новые ключи следуют тому же образцу, и реестр остаётся
самосогласованным.

Разделение ответственности. Реестр только хранит и фильтрует факты. Имена
агентов он не разворачивает, это дело engine.agents, чтобы не плодить второй
источник истины. Ключи обязаны быть уникальными, иначе инлайн-ссылка получит
неоднозначную цель, потому уникальность проверяется при импорте громко.
"""

from __future__ import annotations


# key якорь, agent код агента, year, axis, fact, source, url,
# verified визирован ли поиском первоисточника.
SOURCES = [
    {
        "key": "jpn_senkaku_nationalization_2012",
        "agent": "jpn", "year": 2012, "axis": "normative",
        "fact": "Национализация трёх островов архипелага Сэнкаку правительством "
                "Японии, запуск устойчивой эскалации присутствия КНР.",
        "source": "Asia News Network, обзор морской экспансии КНР",
        "url": "https://asianews.network/new-developments-seen-in-chinas-maritime-expansion-japan-govt-official-urges-calm-stout-response/",
        "verified": True,
    },
    {
        "key": "jpn_collective_defense_2014",
        "agent": "jpn", "year": 2014, "axis": "normative",
        "fact": "Легитимация права на коллективную самооборону через "
                "правительственное толкование, без изменения текста статьи 9.",
        "source": "Решение Кабинета министров Японии, 2014",
        "url": None,
        "verified": False,
    },
    {
        "key": "jpn_peace_security_laws_2015",
        "agent": "jpn", "year": 2015, "axis": "normative",
        "fact": "Принятие пакета законов о мире и безопасности, закрепление "
                "коллективной самообороны на институциональном уровне.",
        "source": "Пакет законов о мире и безопасности, 2015",
        "url": None,
        "verified": False,
    },
    {
        "key": "jpn_nss_counterstrike_2022",
        "agent": "jpn", "year": 2022, "axis": "material",
        "fact": "Принятие Стратегии национальной безопасности с легитимацией "
                "потенциала ответного удара, перевод доктрины к наступательным "
                "конвенциональным возможностям.",
        "source": "Стратегия национальной безопасности Японии, 2022",
        "url": None,
        "verified": False,
    },
    {
        "key": "chn_senkaku_presence_2024",
        "agent": "chn", "year": 2024, "axis": "material",
        "fact": "Рекорд присутствия КНР у Сэнкаку, 355 дней в прилежащей зоне, "
                "1351 судно за год, по данным Береговой охраны Японии.",
        "source": "The Diplomat",
        "url": "https://thediplomat.com/2025/01/china-sets-record-for-activity-near-senkaku-diaoyu-islands-in-2024/",
        "verified": True,
    },
    {
        "key": "jpn_takaichi_taiwan_2025",
        "agent": "jpn", "year": 2025, "axis": "alliance",
        "fact": "Заявление премьер-министра Такаити о возможном вовлечении Сил "
                "самообороны при нападении КНР на Тайвань, ноябрь 2025.",
        "source": "Defense News",
        "url": "https://www.defensenews.com/global/asia-pacific/2025/12/26/japans-cabinet-oks-record-defense-budget-that-aims-to-deter-china/",
        "verified": True,
    },
    {
        "key": "jpn_defense_budget_2026",
        "agent": "jpn", "year": 2026, "axis": "material",
        "fact": "Рекордный оборонный бюджет на 2026 финансовый год около 9 трлн "
                "йен, рост 9,4 процента, выход на 2 процента ВВП с опережением "
                "графика, ракеты Type-12 дальностью около 1000 км.",
        "source": "The Diplomat, Defense News, Indo-Pacific Defense Forum",
        "url": "https://thediplomat.com/2025/12/japan-accelerates-defense-buildup-with-record-budget-and-expanded-unmanned-capabilities/",
        "verified": True,
    },
    {
        "key": "jpn_ldp_supermajority_2026",
        "agent": "jpn", "year": 2026, "axis": "normative",
        "fact": "Победа ЛДП на выборах 8 февраля 2026, 316 из 465 мест, "
                "супербольшинство в две трети, впервые с послевоенного периода "
                "одна партия, заявленный курс на конституционную реформу.",
        "source": "The Japan Times, Nippon.com",
        "url": "https://www.japantimes.co.jp/news/2026/02/09/japan/politics/japan-2026-lower-house-election/",
        "verified": True,
    },
    {
        "key": "jpn_arms_export_2026",
        "agent": "jpn", "year": 2026, "axis": "normative",
        "fact": "Отмена запрета на экспорт летального оружия, 21 апреля 2026, "
                "пересмотр Трёх принципов и отмена системы пяти категорий, "
                "разрешён экспорт истребителей, ракет и кораблей партнёрам.",
        "source": "The Diplomat, IISS, Al Jazeera",
        "url": "https://thediplomat.com/2026/04/breaking-the-postwar-taboo-japan-lifts-its-ban-on-lethal-arms-exports/",
        "verified": True,
    },
]


# Уникальность ключей это инвариант, на котором стоит инлайн-цитирование.
# Дубль ключа делает цель ссылки неоднозначной, потому валим импорт громко,
# чтобы ошибка вскрылась сразу при сборке, а не тихо на экране отчёта.
_keys = [s["key"] for s in SOURCES]
_dups = sorted({k for k in _keys if _keys.count(k) > 1})
if _dups:
    raise ValueError(
        "Реестр источников содержит повторяющиеся ключи, инлайн-ссылка "
        "получит неоднозначную цель. Повторы " + ", ".join(_dups))


def sources_until(year: int) -> list:
    """Факты для годов вплоть до указанного включительно, отсортированы."""
    rows = [s for s in SOURCES if s["year"] <= year]
    rows.sort(key=lambda s: s["year"])
    return rows


def sources_for_axis(axis: str) -> list:
    """Факты по одной оси давления."""
    return [s for s in SOURCES if s["axis"] == axis]


def sources_for_agent(agent: str) -> list:
    """Факты калибровки одного агента, отсортированы по году. Опора M-C при
    расширении реестра на США, КНР, Тайвань и Южную Корею."""
    rows = [s for s in SOURCES if s["agent"] == agent]
    rows.sort(key=lambda s: s["year"])
    return rows


def source_by_key(key: str):
    """Один факт по устойчивому ключу либо None. Опора инлайн-цитирования,
    через него M-B разрешает якорь прозы в ссылку и издание."""
    for s in SOURCES:
        if s["key"] == key:
            return s
    return None


def agents_in_registry() -> list:
    """Коды агентов, присутствующих в реестре, выведены из самих данных без
    второго источника истины. По мере наполнения список растёт сам."""
    return sorted({s["agent"] for s in SOURCES})
