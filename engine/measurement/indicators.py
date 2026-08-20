"""
Реестр индикаторов.

Назначение слоя. Здесь объявляется, из чего складывается каждая из трёх
входных переменных модели. Для всякого показателя указано, к какой
переменной он относится, каким правилом приводится к отрезку [0, 1], к
каким агентам применяется и какие реперные точки имеет.

Что модуль знает. Состав переменных и правила приведения.
Чего модуль не знает. Ни файлов, ни годов, ни самих наблюдений. Реестр
объявляет устройство измерения и ничего не вычисляет по данным.

Устройство записи. Всякий индикатор описывается неизменяемой записью, а
поле kind указывает, какое правило приведения к нему применяется. Правила
собраны в модуле scales и здесь не повторяются.

Применимость. Индикатор применяется не ко всем агентам. Аффективный
показатель существует только для Японии, а показатель несогласия аудитории
только для агентов, обладающих правовым потолком. Поле applies_to
перечисляет коды агентов либо содержит ALL, если применяется ко всем.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


ALL = "*"


class Var(str, Enum):
    """Три входные переменные нечёткого контроллера."""
    THREAT = "z1"      # восприятие угрозы
    TRUST = "z2"       # доверие, степень опоры на внешнюю гарантию
    EROSION = "z3"     # нормативная эрозия


class Kind(str, Enum):
    """
    Правило приведения наблюдения к отрезку [0, 1].

    SHARE        доля второй величины в сумме пары, реперов не требует
    LINEAR       линейное приведение по двум реперным точкам
    ORDINAL      порядковый разряд, равноотстоящие значения
    COUNT        доля от закрытого перечня позиций
    DEVIATION    отклонение от собственного обычного уровня агента

    Правило DEVIATION применяется там, где абсолютная величина между
    агентами несопоставима. Двадцать судов у островов при обычных трёхстах
    означают затишье, тогда как двадцать ракетных пусков при обычных двух
    означают кризис, вследствие чего общая реперная точка для инцидентов
    стёрла бы различие. Основание в том, что восприятие определяется
    отклонением от привычного положения, а не самой величиной.
    """
    SHARE = "share"
    LINEAR = "linear"
    ORDINAL = "ordinal"
    COUNT = "count"
    DEVIATION = "deviation"


class Role(str, Enum):
    """
    Способ вхождения индикатора в переменную.

    ADDITIVE     входит во взвешенную сумму равной долей
    DAMPER       не входит в сумму, умножает её результат

    Различие существенно. Сложение означает, что недостаток по одному
    показателю возмещается избытком по другому. Для несогласия аудитории
    такое возмещение неприемлемо, поскольку массовое несогласие не
    возмещается принятием дополнительных документов, а ограничивает глубину
    произведённого ими сдвига.
    """
    ADDITIVE = "additive"
    DAMPER = "damper"


@dataclass(frozen=True)
class Indicator:
    """
    Объявление одного показателя.

    key         имя в таблице наблюдений
    var         переменная, в которую входит
    kind        правило приведения
    role        способ вхождения, слагаемым либо множителем
    low, high   реперные точки для LINEAR, порядок задаёт направление шкалы
    n_steps     число разрядов для ORDINAL
    inverted    обращение шкалы для ORDINAL
    total       размер закрытого перечня для COUNT
    pair_key    имя парной величины для SHARE
    applies_to  коды агентов либо ALL
    title       название по-русски для отчётов
    source      происхождение ряда
    """
    key: str
    var: Var
    kind: Kind
    title: str
    source: str
    role: Role = Role.ADDITIVE
    low: float | None = None
    high: float | None = None
    n_steps: int | None = None
    inverted: bool = False
    total: float | None = None
    pair_key: str | None = None
    applies_to: tuple[str, ...] | str = ALL

    def covers(self, agent_code: str) -> bool:
        """Применяется ли показатель к данному агенту."""
        return self.applies_to == ALL or agent_code in self.applies_to


# --- Переменная восприятия угрозы --------------------------------------

_THREAT = [
    Indicator(
        key="milex",
        var=Var.THREAT,
        kind=Kind.SHARE,
        pair_key="milex",
        title="Доля первичного противника в военных расходах пары",
        source="SIPRI Military Expenditure Database, постоянные цены 2024",
    ),
    Indicator(
        key="incidents",
        var=Var.THREAT,
        kind=Kind.ORDINAL,
        n_steps=5,
        title="Наивысший уровень враждебности в спорах агента за год",
        source="Correlates of War, Militarized Interstate Disputes v5.0, "
               "шкала уровней враждебности по кодовой книге Палмера и др.",
    ),
    Indicator(
        key="affinity",
        var=Var.THREAT,
        kind=Kind.LINEAR,
        low=100.0, high=0.0,
        applies_to=("jpn",),
        title="Доля населения, испытывающего близость к противнику",
        source="Опрос Канцелярии Кабинета министров Японии",
    ),
]

# --- Переменная доверия -------------------------------------------------
# Третий показатель, изменения в командных структурах, снят по трём
# основаниям. Он не даёт годового ряда, поскольку события такого рода
# происходят раз в десятилетие. Он не сопоставим между агентами, поскольку
# устройство командования в каждом союзе своё. Он движется вместе с числом
# совместных учений и потому сведений сверх них не приносит.

_TRUST = [
    Indicator(
        key="exercises",
        var=Var.TRUST,
        kind=Kind.DEVIATION,
        title="Число совместных мероприятий с гарантом",
        source="Официальные сообщения сторон",
    ),
    Indicator(
        key="arms_share",
        var=Var.TRUST,
        kind=Kind.DEVIATION,
        title="Доля гаранта в импорте вооружений",
        source="SIPRI Arms Transfers Database",
    ),
]

# --- Переменная нормативной эрозии --------------------------------------

_EROSION = [
    Indicator(
        key="ceiling",
        var=Var.EROSION,
        kind=Kind.ORDINAL,
        n_steps=4, inverted=True,
        title="Ступень правового потолка на применение силы",
        source="Конституции и правительственные позиции агентов",
    ),
    Indicator(
        key="categories",
        var=Var.EROSION,
        kind=Kind.COUNT,
        total=5.0,
        title="Снятые запреты из закрытого перечня",
        source="Датированные акты снятия запретов",
    ),
    Indicator(
        key="commitments",
        var=Var.EROSION,
        kind=Kind.COUNT,
        total=9.0,
        title="Обязательства, допускающие применение силы вне территории",
        source="Договорная база агентов",
    ),
    Indicator(
        key="dissent",
        var=Var.EROSION,
        kind=Kind.LINEAR,
        low=0.0, high=100.0,
        role=Role.DAMPER,
        applies_to=("jpn", "kor", "phl", "ind"),
        title="Несогласие аудитории",
        source="Национальные опросы и итоги публичных обсуждений",
    ),
]


AUXILIARY: dict[str, str] = {
    "cinc": "Индекс совокупных возможностей, Correlates of War NMC v7.0",
    "senkaku_days": "Дни присутствия судов в прилежащей зоне Сэнкаку, "
                    "Береговая охрана Японии",
    "dprk_launches": "Число ракетных пусков КНДР за год, Белая книга по "
                     "обороне Японии",
}
"""
Ряды, хранимые наравне с наблюдениями, но во входные переменные не
входящие. Индекс совокупных возможностей задаёт веса матрицы взаимного
влияния, то есть служит структурным параметром системы, а не измерением
состояния агента. В переменную восприятия угрозы он не вводится, поскольку
для пяти пар из семи его ряд повторяет ряд отношения расходов с
коэффициентом связи выше девяти десятых, отчего сведений сверх него не
приносит.

Дни присутствия судов и число ракетных пусков хранятся ради проверки
качества собственного кодирования. Уровень враждебности за годы после
завершения набора данных кодируется по тем же правилам, и совпадение
кода с независимо наблюдаемым рядом удостоверяет годность кодирования.
"""

REGISTRY: tuple[Indicator, ...] = tuple(_THREAT + _TRUST + _EROSION)

BY_KEY: dict[str, Indicator] = {ind.key: ind for ind in REGISTRY}


def for_var(var: Var, agent_code: str) -> list[Indicator]:
    """
    Показатели данной переменной, применимые к данному агенту.

    Порядок сохраняется тот, в каком они объявлены, что делает вывод
    отчётов воспроизводимым.
    """
    return [ind for ind in REGISTRY if ind.var is var and ind.covers(agent_code)]


def additive(var: Var, agent_code: str) -> list[Indicator]:
    """Показатели, входящие во взвешенную сумму."""
    return [i for i in for_var(var, agent_code) if i.role is Role.ADDITIVE]


def damper(var: Var, agent_code: str) -> Indicator | None:
    """Показатель, входящий множителем, если он для агента предусмотрен."""
    found = [i for i in for_var(var, agent_code) if i.role is Role.DAMPER]
    if len(found) > 1:
        raise ValueError(f"У переменной {var} более одного множителя")
    return found[0] if found else None


def describe() -> str:
    """Печатное описание реестра для приложения к работе."""
    lines = []
    for var in Var:
        lines.append(f"{var.value}")
        for ind in (i for i in REGISTRY if i.var is var):
            scope = ("все агенты" if ind.applies_to == ALL
                     else ", ".join(ind.applies_to))
            role = "множитель" if ind.role is Role.DAMPER else "слагаемое"
            lines.append(f"  {ind.key:12} {ind.title}")
            lines.append(f"  {'':12} правило {ind.kind.value}, {role}, {scope}")
            lines.append(f"  {'':12} источник {ind.source}")
    return "\n".join(lines)
