"""
Прогностические сценарии. Каждый задаёт расписание шоков, вносимых в
состояния агентов по ходу прогона.

Шок декларативен: год относительно начала, цель, переменная, величина и
человекочитаемое описание события. Прозрачность намеренная, интерфейс и
отчёт показывают, что именно и когда произошло.

Переменные состояния.
    z1 восприятие угрозы
    z2 доверие к союзнику
    z3 нормативная эрозия

Четыре сценария.
    Инерционный дрейф. Контрольный прогон без внешних шоков. Система
        эволюционирует от базового года по одной внутренней динамике.
    Формальная ревизия девятой статьи. Япония закрепляет нормативный сдвиг
        конституционной реформой, эрозия скачком растёт и не откатывается.
    Тайваньский кризис. Резкий всплеск восприятия угрозы у Тайваня, Японии и
        США, испытание системы на срыв в дестабилизацию.
    Ослабление альянса. Отступление США, скачкообразная потеря доверия
        союзниками с последующей дилеммой безопасности.
"""

from __future__ import annotations
from dataclasses import dataclass, field


_VAR_INDEX = {"z1": 0, "z2": 1, "z3": 2}


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass(frozen=True)
class ShockEvent:
    """Единичное событие сценария."""
    step: int            # год относительно начала прогона, отсчёт от нуля
    target: str          # код агента
    variable: str        # z1, z2 или z3
    delta: float         # приращение переменной
    description: str     # человекочитаемое описание


@dataclass
class Scenario:
    """Сценарий есть имя, описание и список событий."""
    name: str
    description: str
    events: list = field(default_factory=list)

    def apply(self, step: int, states: dict) -> list:
        """
        Применяет события данного года к состояниям, изменяя их на месте.
        Возвращает описания сработавших событий.
        """
        fired = []
        for ev in self.events:
            if ev.step != step:
                continue
            idx = _VAR_INDEX[ev.variable]
            vec = states[ev.target]
            vec[idx] = _clip(vec[idx] + ev.delta)
            fired.append((ev.description, ev.variable))
        return fired


# --- Четыре готовых сценария ---

INERTIAL = Scenario(
    name="Инерционный дрейф",
    description="Контрольный прогон без внешних шоков.",
    events=[],
)

ARTICLE9_REVISION = Scenario(
    name="Пересмотр девятой статьи",
    description="Япония закрепляет нормативный сдвиг конституционной реформой.",
    events=[
        ShockEvent(2, "jpn", "z3", 0.25,
                   "Конституционная реформа закрепляет эрозию ограничений на применение силы."),
        ShockEvent(2, "jpn", "z1", 0.05,
                   "Рост восприятия угрозы как обоснование реформы."),
        ShockEvent(3, "chn", "z1", 0.08,
                   "КНР воспринимает ремилитаризацию Японии как прямую угрозу."),
    ],
)

TAIWAN_CRISIS = Scenario(
    name="Тайваньский кризис",
    description="Затяжная эскалация вокруг Тайваньского пролива, втягивающая КНР.",
    events=[
        ShockEvent(3, "twn", "z1", 0.20,
                   "Эскалация военного давления КНР на Тайвань."),
        ShockEvent(3, "twn", "z3", 0.25,
                   "Всеобщая мобилизация Тайваня, необратимый нормативный сдвиг."),
        ShockEvent(3, "jpn", "z1", 0.12,
                   "Япония воспринимает кризис как угрозу первой островной цепи."),
        ShockEvent(3, "chn", "z1", 0.15,
                   "КНР переходит к открытому принуждению."),
        ShockEvent(3, "chn", "z3", 0.15,
                   "Мобилизация НОАК и военная экономика КНР, необратимо."),
        ShockEvent(4, "chn", "z3", 0.12,
                   "Углубление военного режима КНР."),
        ShockEvent(4, "twn", "z3", 0.10,
                   "Закрепление чрезвычайных полномочий Тайваня."),
        ShockEvent(4, "usa", "z1", 0.10,
                   "США наращивают присутствие в зоне кризиса."),
        ShockEvent(5, "chn", "z1", 0.10,
                   "Затяжной характер противостояния."),
    ],
)

ALLIANCE_WEAKENING = Scenario(
    name="Ослабление альянса",
    description="Отступление США, эрозия доверия и последующая гонка.",
    events=[
        ShockEvent(2, "jpn", "z2", -0.22,
                   "Сигналы отступления США подрывают доверие Японии."),
        ShockEvent(2, "kor", "z2", -0.22,
                   "Республика Корея теряет уверенность в гарантиях."),
        ShockEvent(2, "twn", "z2", -0.18,
                   "Тайвань остаётся без надёжного покровителя."),
        ShockEvent(2, "chn", "z1", 0.12,
                   "КНР видит окно возможностей в ослаблении альянса."),
        ShockEvent(3, "jpn", "z3", 0.12,
                   "Япония форсирует автономную оборону, необратимый сдвиг."),
        ShockEvent(3, "kor", "z3", 0.10,
                   "Республика Корея расширяет самостоятельный военный потенциал."),
        ShockEvent(3, "chn", "z3", 0.10,
                   "КНР закрепляет военное превосходство в регионе."),
    ],
)

ALL_SCENARIOS = {
    "inertial": INERTIAL,
    "article9": ARTICLE9_REVISION,
    "taiwan": TAIWAN_CRISIS,
    "alliance": ALLIANCE_WEAKENING,
}


# --- Конструктор пользовательских сценариев ---

# Каталог типов событий. Понятное название переводится в переменную состояния
# и знак воздействия. Пользователь собирает мир из этих кубиков, а модель сама
# вычисляет, как агенты на них отреагируют.
EVENT_CATALOG = {
    "mil_escalation": {"var": "z1", "sign": +1,
                       "ru": "Военная эскалация", "en": "Military escalation"},
    "detente": {"var": "z1", "sign": -1,
                "ru": "Военная разрядка", "en": "Military detente"},
    "alliance_loss": {"var": "z2", "sign": -1,
                      "ru": "Подрыв доверия к союзнику", "en": "Erosion of alliance trust"},
    "alliance_boost": {"var": "z2", "sign": +1,
                       "ru": "Укрепление альянса", "en": "Alliance reinforcement"},
    "norm_shift": {"var": "z3", "sign": +1,
                   "ru": "Нормативный сдвиг, мобилизация, реформа", "en": "Normative shift"},
}

# Уровни силы события.
MAGNITUDE_LEVELS = {
    "light": {"value": 0.10, "ru": "умеренное", "en": "light"},
    "strong": {"value": 0.20, "ru": "сильное", "en": "strong"},
    "extreme": {"value": 0.30, "ru": "экстремальное", "en": "extreme"},
}


def build_custom_scenario(spec: list, name: str = "Свой сценарий") -> Scenario:
    """
    Собирает сценарий из пользовательской спецификации.

    spec суть список словарей с ключами step, agent, event, magnitude.
    step    год относительно начала, отсчёт от нуля
    agent   код агента
    event   ключ из EVENT_CATALOG
    magnitude  ключ из MAGNITUDE_LEVELS

    Кубики задают внешние события мира, не действия агентов. Реакцию агентов
    модель вычисляет сама, причинность сохранена.
    """
    events = []
    for item in spec:
        cat = EVENT_CATALOG[item["event"]]
        mag = MAGNITUDE_LEVELS[item["magnitude"]]["value"]
        delta = cat["sign"] * mag
        agent_name = AGENTS_NAME.get(item["agent"], item["agent"])
        desc = f"{agent_name}: {cat['ru']} ({MAGNITUDE_LEVELS[item['magnitude']]['ru']})"
        events.append(ShockEvent(item["step"], item["agent"], cat["var"], delta, desc))
    return Scenario(name=name, description="Пользовательский набор событий.", events=events)


# Имена агентов для описаний, без импорта на уровне модуля во избежание цикла.
AGENTS_NAME = {"usa": "США", "chn": "КНР", "jpn": "Япония", "twn": "Тайвань", "kor": "Республика Корея"}
