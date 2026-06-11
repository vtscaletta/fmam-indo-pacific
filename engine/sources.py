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

    # --- Тайвань. M-C ---
    {
        "key": "twn_conscription_2024",
        "agent": "twn", "year": 2024, "axis": "normative",
        "fact": "Возврат годичной воинской повинности с января 2024 года, "
                "объявлен в декабре 2022, разворот к всеобщей обороне против КНР.",
        "source": "Канцелярия президента Китайской Республики, Тайвань",
        "url": "https://english.president.gov.tw/News/6417",
        "verified": True,
    },
    {
        "key": "twn_pla_pressure_2024",
        "agent": "twn", "year": 2024, "axis": "material",
        "fact": "Рекорд давления НОАК, 3615 самолётовылетов в зону опознавания "
                "за 2024 год, вдвое выше 2023, учения Joint Sword после "
                "инаугурации президента Лая.",
        "source": "Janes, по данным Министерства обороны Тайваня",
        "url": "https://www.janes.com/osint-insights/defence-and-national-security-analysis/china-sets-new-records-in-air-sea-operations-around-taiwan",
        "verified": True,
    },
    {
        "key": "twn_defense_budget_2026",
        "agent": "twn", "year": 2026, "axis": "material",
        "fact": "Рекордный оборонный бюджет на 2026 год, 949,5 млрд тайваньских "
                "долларов, 3,32 процента ВВП, впервые выше 3 процентов с 2009 года.",
        "source": "The Diplomat, Focus Taiwan",
        "url": "https://thediplomat.com/2025/08/taiwans-government-eyes-expanded-defense-budget-at-3-3-of-gdp/",
        "verified": True,
    },
    {
        "key": "twn_special_budget_split_2026",
        "agent": "twn", "year": 2026, "axis": "material",
        "fact": "Особый оборонный бюджет около 40 млрд долларов на асимметричные "
                "средства, урезан оппозиционным Законодательным Юанем на "
                "38 процентов в мае 2026, годовой бюджет к июню не принят.",
        "source": "Congressional Research Service, IF12481",
        "url": "https://www.congress.gov/crs-product/IF12481",
        "verified": True,
    },

    # --- Республика Корея. M-C ---
    {
        "key": "kor_martial_law_2024",
        "agent": "kor", "year": 2024, "axis": "normative",
        "fact": "Объявление военного положения президентом Юном 3 декабря 2024 "
                "года, первое с демократизации 1987 года, импичмент 14 декабря.",
        "source": "Congressional Research Service, IN12474",
        "url": "https://www.congress.gov/crs-product/IN12474",
        "verified": True,
    },
    {
        "key": "kor_three_axis_2025",
        "agent": "kor", "year": 2025, "axis": "normative",
        "fact": "Трёхосевая система сдерживания против КНДР, упреждающий удар "
                "Kill Chain, ПРО KAMD и обезглавливающее возмездие KMPR, "
                "наступательный разворот доктрины за десятилетие.",
        "source": "CSIS",
        "url": "https://www.csis.org/analysis/south-koreas-offensive-military-strategy-and-its-dilemma",
        "verified": True,
    },
    {
        "key": "kor_defense_budget_2026",
        "agent": "kor", "year": 2026, "axis": "material",
        "fact": "Оборонный бюджет на 2026 год, 66,3 трлн вон около 47,6 млрд "
                "долларов, рост 8,2 процента, крупнейший за семь лет, расходы на "
                "трёхосевую систему выше на 22 процента.",
        "source": "The Korea Herald",
        "url": "https://www.koreaherald.com/article/10567523",
        "verified": True,
    },
    {
        "key": "kor_nuclear_debate_2025",
        "agent": "kor", "year": 2025, "axis": "alliance",
        "fact": "Дебаты о собственном ядерном вооружении перестали быть табу, "
                "дилемма между опорой на расширенное сдерживание США и "
                "автономной ядерной защитой от КНДР.",
        "source": "Defense News",
        "url": "https://www.defensenews.com/opinion/2025/11/25/south-koreas-nuclear-debate-is-no-longer-taboo/",
        "verified": True,
    },

    # --- КНР. M-C-2 ---
    {
        "key": "chn_defense_budget_2026",
        "agent": "chn", "year": 2026, "axis": "material",
        "fact": "Оборонный бюджет на 2026 год 1,91 трлн юаней около 277 млрд "
                "долларов, рост 7 процентов, объявлен на сессии ВСНП 5 марта "
                "2026 года на фоне чистки военного руководства.",
        "source": "Министерство обороны КНР, CNBC",
        "url": "http://eng.mod.gov.cn/2025xb/P/16447711.html",
        "verified": True,
    },
    {
        "key": "chn_military_buildup_2025",
        "agent": "chn", "year": 2025, "axis": "material",
        "fact": "Оценка SIPRI военных расходов КНР за 2025 год 336 млрд "
                "долларов, тридцатый год роста подряд, ядерный арсенал около "
                "600 боеголовок, ввод авианосца Фуцзянь в ноябре 2025 года.",
        "source": "SIPRI, по сводке militaryspend",
        "url": "https://militaryspend.org/country-profiles/china",
        "verified": True,
    },
    {
        "key": "chn_philippines_shoal_2024",
        "agent": "chn", "year": 2024, "axis": "material",
        "fact": "Силовое давление у рифа Второй Томас, водомёты по филиппинским "
                "судам в марте 2024 и силовой захват катера с ранениями "
                "17 июня 2024 года, эрозия операционных норм Южно-Китайского моря.",
        "source": "Asia Maritime Transparency Initiative, CSIS",
        "url": "https://amti.csis.org/shifting-tactics-at-second-thomas-shoal/",
        "verified": True,
    },
    {
        "key": "chn_pla_purge_2026",
        "agent": "chn", "year": 2026, "axis": "material",
        "fact": "Чистка военного руководства, девять генералов смещены в "
                "октябре 2025, генерал Чжан Юся и начальник штаба в январе "
                "2026, Центральный военный совет урезан с семи до двух.",
        "source": "ChinaPower, CSIS",
        "url": "https://chinapower.csis.org/china-pla-military-purges/",
        "verified": True,
    },

    # --- США. M-C-2 ---
    {
        "key": "usa_defense_budget_2025",
        "agent": "usa", "year": 2025, "axis": "material",
        "fact": "Крупнейший в мире оборонный бюджет, около 850 млрд долларов "
                "по плану 2025 финансового года и около 919 млрд по факту "
                "расходов, порядка 13 процентов федеральных трат.",
        "source": "CNBC, USAFacts",
        "url": "https://www.cnbc.com/2026/03/05/china-defense-spending-7-percent-2026-budget.html",
        "verified": True,
    },
    {
        "key": "usa_allies_pressure_2025",
        "agent": "usa", "year": 2025, "axis": "alliance",
        "fact": "Администрация Трампа требует от союзников поднять расходы до "
                "5 процентов ВВП, кандидат в Пентагон Колби настаивает на "
                "10 процентах для Тайваня, разворот к разделению бремени.",
        "source": "Центральное информагентство Китайской Республики",
        "url": "https://www.globalsecurity.org/wmd/library/news/taiwan/2025/taiwan-250305-cna01.htm",
        "verified": True,
    },
    {
        "key": "usa_strategic_ambiguity_2025",
        "agent": "usa", "year": 2025, "axis": "alliance",
        "fact": "Обязательство США по Тайваню названо подразумеваемым, "
                "косвенным и обычным, военный баланс с КНР, по оценке "
                "Колби, резко сместился, стратегическая неопределённость сохранена.",
        "source": "Taiwan News",
        "url": "https://www.taiwannews.com.tw/news/6051873",
        "verified": True,
    },
    {
        "key": "usa_trump_xi_busan_2025",
        "agent": "usa", "year": 2025, "axis": "alliance",
        "fact": "Встреча Трампа и Си в Пусане 30 октября 2025, первая очная во "
                "втором сроке, разрядка торговой войны, снижение пошлин в обмен "
                "на редкоземельные металлы и закупки сои.",
        "source": "Atlantic Council",
        "url": "https://www.atlanticcouncil.org/blogs/new-atlanticist/experts-react/experts-react-what-does-the-trump-xi-meeting-mean-for-trade-technology-security-and-beyond/",
        "verified": True,
    },

    # --- Союзная опора Тайваня и Кореи. M-C-2 ---
    {
        "key": "twn_us_arms_2025",
        "agent": "twn", "year": 2025, "axis": "alliance",
        "fact": "Пакет американских вооружений по уведомлению Конгресса декабря "
                "2025, ракеты TOW-2B и Javelin, гаубицы M109A7 и системы "
                "HIMARS, опора асимметричной обороны при дефиците гарантий.",
        "source": "Brookings",
        "url": "https://www.brookings.edu/articles/defense-in-a-democracy-political-competition-and-taiwans-special-defense-budget/",
        "verified": True,
    },
    {
        "key": "kor_us_submarine_2025",
        "agent": "kor", "year": 2025, "axis": "alliance",
        "fact": "Саммит Трампа и Ли 30 октября 2025, согласие США поделиться "
                "технологией атомной подводной лодки для Республики Корея, "
                "укрепление союзной опоры на фоне ядерных дебатов.",
        "source": "PBS NewsHour",
        "url": "https://www.pbs.org/newshour/world/chinas-xi-promises-to-protect-free-trade-at-apec-as-trump-snubs-major-summit",
        "verified": True,
    },

    # --- Япония. Глубокая интеграция. M-C-3 ---
    {
        "key": "jpn_camp_david_2023",
        "agent": "jpn", "year": 2023, "axis": "alliance",
        "fact": "Трёхсторонний саммит США, Японии и Республики Корея в "
                "Кэмп-Дэвиде 18 августа 2023, первый отдельный в истории, дух "
                "Кэмп-Дэвида и обязательство о консультациях при угрозах.",
        "source": "Белый дом, совместное заявление",
        "url": "https://bidenwhitehouse.archives.gov/briefing-room/statements-releases/2023/08/18/the-spirit-of-camp-david-joint-statement-of-japan-the-republic-of-korea-and-the-united-states/",
        "verified": True,
    },
    {
        "key": "jpn_type12_deployment_2026",
        "agent": "jpn", "year": 2026, "axis": "material",
        "fact": "Развёртывание модернизированной противокорабельной ракеты "
                "Type-12 дальностью около 1000 км в лагере Кенгун на Кюсю "
                "31 марта 2026, ввод HVGP Block I, обретение потенциала "
                "ответного удара.",
        "source": "Stars and Stripes",
        "url": "https://www.stripes.com/theaters/asia_pacific/2026-03-12/japan-type-12-missile-deployment-21036511.html",
        "verified": True,
    },
    {
        "key": "jpn_balikatan_2026",
        "agent": "jpn", "year": 2026, "axis": "normative",
        "fact": "Первый с 1945 года пуск наступательной ракеты Силами "
                "самообороны с чужой земли на учениях Баликатан на Филиппинах "
                "в мае 2026, выход военной активности за пределы территории.",
        "source": "Global Defense Corp",
        "url": "https://www.globaldefensecorp.com/2026/05/13/japan-fires-a-type-88-anti-ship-missile-during-the-balikatan-2026-exercise-in-the-philippines/",
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
