"""
Словарь строк интерфейса. Мультиязычность.

Все надписи вынесены сюда, чтобы добавление нового языка сводилось к одной
колонке. Сейчас заполнены русский и английский. Структура готова принять
японский, казахский, китайский без правки кода.

Отдельный раздел подсказок поясняет термины модели на месте, чтобы человек
без профильной подготовки понимал, что перед ним, не держа всё в голове.
"""

from __future__ import annotations

# Активные и зарезервированные языки. Порядок задаёт вид переключателя.
LANGUAGES = ("ru", "en")
DEFAULT_LANG = "ru"


STRINGS: dict[str, dict[str, str]] = {
    # Шапка
    "app_title": {"ru": "Индо-Тихоокеанский комплекс безопасности",
                  "en": "Indo-Pacific Security Complex"},
    "app_subtitle": {"ru": "Аналитический движок фазовой динамики",
                     "en": "Phase dynamics analytical engine"},

    # Вкладки
    "tab_overview": {"ru": "Обзор", "en": "Overview"},
    "tab_agents": {"ru": "Агенты", "en": "Agents"},
    "tab_transparency": {"ru": "Разбор решения", "en": "Decision trace"},
    "tab_report": {"ru": "Отчёт", "en": "Report"},

    # Управление
    "scenario_label": {"ru": "Сценарий", "en": "Scenario"},
    "horizon_label": {"ru": "Горизонт, лет", "en": "Horizon, years"},
    "language_label": {"ru": "Язык", "en": "Language"},
    "run_button": {"ru": "Рассчитать прогноз", "en": "Run forecast"},
    "agent_label": {"ru": "Агент", "en": "Agent"},
    "year_label": {"ru": "Год", "en": "Year"},

    # Сценарии
    "scenario_inertial": {"ru": "Инерционный дрейф", "en": "Inertial drift"},
    "scenario_article9": {"ru": "Ревизия девятой статьи", "en": "Article 9 revision"},
    "scenario_taiwan": {"ru": "Тайваньский кризис", "en": "Taiwan crisis"},
    "scenario_alliance": {"ru": "Ослабление альянса", "en": "Alliance weakening"},

    # Режимы системы
    "regime_S1": {"ru": "Устойчивый баланс", "en": "Stable balance"},
    "regime_S2": {"ru": "Холодная конфронтация", "en": "Cold confrontation"},
    "regime_S3": {"ru": "Каскадная дестабилизация", "en": "Cascade destabilization"},

    # Входные переменные
    "var_threat": {"ru": "Восприятие угрозы", "en": "Threat perception"},
    "var_trust": {"ru": "Доверие к союзнику", "en": "Alliance trust"},
    "var_erosion": {"ru": "Нормативная эрозия", "en": "Normative erosion"},

    # Выходные переменные
    "out_milex": {"ru": "Военные расходы", "en": "Military expenditure"},
    "out_rhet": {"ru": "Стратегическая риторика", "en": "Strategic rhetoric"},
    "out_drift": {"ru": "Институциональный дрейф", "en": "Institutional drift"},

    # Метрики
    "tension_label": {"ru": "Системное напряжение", "en": "System tension"},
    "risk_collapse": {"ru": "Риск дестабилизации", "en": "Destabilization risk"},
    "threshold_label": {"ru": "Порог фазового перехода", "en": "Phase transition threshold"},
    "dominant_regime": {"ru": "Доминирующий режим", "en": "Dominant regime"},

    # Разбор решения
    "step_fuzzify": {"ru": "Фаззификация", "en": "Fuzzification"},
    "step_rules": {"ru": "Сработавшие правила", "en": "Fired rules"},
    "step_defuzzify": {"ru": "Дефаззификация", "en": "Defuzzification"},
    "term_low": {"ru": "низкий", "en": "low"},
    "term_med": {"ru": "средний", "en": "medium"},
    "term_high": {"ru": "высокий", "en": "high"},

    # Прочее
    "preliminary_note": {"ru": "Параметры предварительные",
                         "en": "Parameters are preliminary"},
    "no_events": {"ru": "Событий нет", "en": "No events"},
}


# Подсказки терминов. Появляются при наведении в точке, где нужны.
TOOLTIPS: dict[str, dict[str, str]] = {
    "var_threat": {
        "ru": "Насколько остро государство воспринимает угрозу от первичного противника. Ноль спокойствие, единица тревога.",
        "en": "How acutely a state perceives threat from its primary adversary. Zero calm, one alarm.",
    },
    "var_trust": {
        "ru": "Насколько государство уверено в поддержке своего союзника. Падение доверия толкает опираться на свои силы.",
        "en": "How much a state trusts its ally. Falling trust pushes it to rely on its own forces.",
    },
    "var_erosion": {
        "ru": "Насколько демонтированы внутренние правовые ограничения на применение силы. Ведёт себя как храповик, растёт легко, назад почти не идёт.",
        "en": "How far internal legal limits on the use of force are dismantled. Behaves as a ratchet, rises easily, hardly reverses.",
    },
    "tension_label": {
        "ru": "Сводная мера напряжённости всей системы. Складывается из материального слоя, что государства строят, и перцептивного, насколько остра конфигурация страха.",
        "en": "Aggregate measure of system-wide tension. Combines a material layer of what states build and a perceptual layer of how acute the configuration of fear is.",
    },
    "threshold_label": {
        "ru": "Уровень напряжения, при котором система меняет долгосрочный режим. Вычисляется строго из устойчивого состояния цепи.",
        "en": "Tension level at which the system changes its long-run regime. Computed strictly from the chain stationary state.",
    },
    "lambda": {
        "ru": "Коэффициент забывания. Чем выше, тем медленнее измерение теряет память о прошлом.",
        "en": "Forgetting coefficient. The higher it is, the slower a dimension loses memory of the past.",
    },
    "ratchet": {
        "ru": "Храповик. Деталь, что движется только в одну сторону. Так ведёт себя институциональный сдвиг, наросло и обратно не идёт.",
        "en": "Ratchet. A mechanism that moves only one way. Institutional shift behaves so, once gained it does not reverse.",
    },
    "regime_S1": {"ru": "Силы уравновешены, переходы редки.", "en": "Forces balanced, transitions rare."},
    "regime_S2": {"ru": "Устойчивое соперничество без открытого срыва.", "en": "Sustained rivalry short of open breakdown."},
    "regime_S3": {"ru": "Самоусиливающийся срыв устойчивости.", "en": "Self-reinforcing loss of stability."},
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """
    Возвращает строку по ключу на заданном языке. При отсутствии перевода
    откатывается на язык по умолчанию, затем на сам ключ.
    """
    entry = STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


def tooltip(key: str, lang: str = DEFAULT_LANG) -> str:
    """Возвращает подсказку по ключу термина, пустую строку при отсутствии."""
    entry = TOOLTIPS.get(key)
    if entry is None:
        return ""
    return entry.get(lang) or entry.get(DEFAULT_LANG) or ""
