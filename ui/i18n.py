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
    "run_button": {"ru": "Проиграть сценарий", "en": "Run scenario"},
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
    # Дашборд и вердикт
    "verdict_title": {"ru": "Заключение системы", "en": "System verdict"},
    "influence_title": {"ru": "Матрица влияния · кто на кого давит", "en": "Influence matrix · who pressures whom"},
    "tension_trace": {"ru": "Траектория напряжения", "en": "Tension trajectory"},
    "regime_mix": {"ru": "Состав режимов по годам", "en": "Regime mix over years"},
    "regime_final": {"ru": "Режимы на финальном году", "en": "Regimes at final year"},
    "gauge_tension": {"ru": "Напряжение", "en": "Tension"},
    "gauge_risk": {"ru": "Риск срыва", "en": "Collapse risk"},
    "peak_label": {"ru": "Пик напряжения", "en": "Peak tension"},
    "to_threshold": {"ru": "До порога срыва", "en": "To collapse threshold"},
    "events_title": {"ru": "События сценария", "en": "Scenario events"},
    # Конструктор и классификация
    "mode_label": {"ru": "Режим", "en": "Mode"},
    "mode_ready": {"ru": "Эталонные сценарии", "en": "Reference scenarios"},
    "mode_custom": {"ru": "Авторский сценарий", "en": "Authored scenario"},
    "builder_title": {"ru": "Конструктор сценария", "en": "Scenario builder"},
    "builder_hint": {"ru": "Соберите мир из событий. Модель сама вычислит, как государства отреагируют.", "en": "Assemble a world from events. The model computes how states react."},
    "ev_year": {"ru": "Год", "en": "Year"},
    "ev_agent": {"ru": "Государство", "en": "State"},
    "ev_type": {"ru": "Событие", "en": "Event"},
    "ev_force": {"ru": "Сила", "en": "Magnitude"},
    "ev_add": {"ru": "Добавить событие", "en": "Add event"},
    "ev_clear": {"ru": "Очистить всё", "en": "Clear all"},
    "ev_play": {"ru": "Проиграть собранный сценарий", "en": "Run assembled scenario"},
    "ev_empty": {"ru": "Событий пока нет. Добавьте хотя бы одно.", "en": "No events yet. Add at least one."},
    "ev_remove": {"ru": "удалить", "en": "remove"},
    "threat_type_title": {"ru": "Тип угрозы", "en": "Threat type"},
    "force_light": {"ru": "умеренное", "en": "light"},
    "force_strong": {"ru": "сильное", "en": "strong"},
    "force_extreme": {"ru": "экстремальное", "en": "extreme"},
    "custom_name": {"ru": "Свой сценарий", "en": "Custom scenario"},
    # Сравнение сценариев
    "mode_compare": {"ru": "Сопоставление сценариев", "en": "Scenario comparison"},
    "cmp_title": {"ru": "Сравнение сценариев бок о бок", "en": "Scenarios side by side"},
    "cmp_tension": {"ru": "Траектории напряжения", "en": "Tension trajectories"},
    "cmp_risk": {"ru": "Риск дестабилизации к концу горизонта", "en": "Destabilization risk at horizon end"},
    "cmp_table": {"ru": "Сводная таблица", "en": "Summary table"},
    "col_scenario": {"ru": "Сценарий", "en": "Scenario"},
    "col_verdict": {"ru": "Оценка", "en": "Verdict"},
    "col_tension": {"ru": "Напряжение", "en": "Tension"},
    "col_risk": {"ru": "Риск", "en": "Risk"},
    "col_peak": {"ru": "Пик", "en": "Peak"},
    "col_threat": {"ru": "Тип угрозы", "en": "Threat type"},


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
