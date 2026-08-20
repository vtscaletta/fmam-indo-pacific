"""
Свёртка показателей в три входные переменные модели.

Назначение слоя. Здесь сходятся все прежние слои. Наблюдения приводятся к
единому отрезку правилами из scales, состав переменных берётся из
indicators, сами наблюдения из loaders, а на выходе получаются числа,
которые принимает нечёткий контроллер.

Что модуль знает. Правило равных долей и правило множителя.
Чего модуль не знает. Ни происхождения чисел, ни устройства контроллера.

Правило равных долей. Показатели, входящие слагаемыми, складываются с
равными весами. Теоретическая рамка указывает, какие показатели
существенны, и не указывает, во сколько раз один существеннее другого,
вследствие чего равные доли составляют назначение, не требующее
дополнительных допущений.

Правило множителя. Показатель несогласия аудитории в сумму не входит, а
умножает её результат на величину, убывающую при возрастании несогласия.
Сложение означало бы, что недостаток по одному показателю возмещается
избытком по другому, тогда как массовое несогласие не возмещается
принятием дополнительных документов, а ограничивает глубину произведённого
ими сдвига.

Обращение с пропусками. Доля вычисляется от числа наблюдённых показателей,
а не от числа предусмотренных. При полном отсутствии наблюдений переменная
возвращается как пропуск и подмене нулём не подлежит.

Обращение с доверием. Показатели этой переменной измеряются отклонением от
собственного обычного уровня агента, вследствие чего сперва по всему
интервалу вычисляются середина и разброс ряда, и лишь затем каждое
наблюдение сравнивается с ними.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from engine.measurement import scales as sc
from engine.measurement.indicators import (
    BY_KEY, Indicator, Kind, Var, additive, damper,
)
from engine.measurement.loaders import AgentPassport, Observations

DAMPER_LIMIT = 0.30
"""
Предел, до которого множитель уменьшает результат.

Величина источниками не выводится и подлежит проверке расчётом. Она
ограничена сверху содержательно, поскольку выступления 2015 года
прохождения законов не остановили, а лишь уменьшили нормативную глубину
состоявшегося сдвига.
"""


@dataclass(frozen=True)
class Baseline:
    """Обычный уровень ряда и его разброс для одного агента и показателя."""
    center: float
    spread: float


@dataclass
class Trace:
    """
    Запись хода вычисления одной переменной за один год.

    Служит для отчёта о происхождении числа. Всякое значение переменной
    сопровождается перечнем показателей, их наблюдёнными и приведёнными
    величинами и указанием, чего недоставало.
    """
    agent: str
    year: int
    var: Var
    parts: dict[str, tuple[float, float]] = field(default_factory=dict)
    missing: tuple[str, ...] = ()
    damper_raw: float = sc.NA
    damper_factor: float = 1.0
    value: float = sc.NA

    def explain(self) -> str:
        """Печатное объяснение, откуда взялось число."""
        lines = [f"{self.agent} {self.year} {self.var.value} = "
                 f"{_fmt(self.value)}"]
        for key, (raw, unit) in self.parts.items():
            lines.append(f"    {key:12} наблюдение {_fmt(raw):>9}"
                         f"  приведено {_fmt(unit)}")
        if not math.isnan(self.damper_raw):
            lines.append(f"    множитель    несогласие {_fmt(self.damper_raw)}"
                         f"  коэффициент {_fmt(self.damper_factor)}")
        if self.missing:
            lines.append(f"    нет наблюдений: {', '.join(self.missing)}")
        return "\n".join(lines)


def _fmt(x: float) -> str:
    return "нет" if math.isnan(x) else f"{x:.3f}"


CALIBRATION_WINDOW = range(2001, 2020)
"""
Окно, по которому вычисляется обычный уровень рядов.

Ограничено калибровочным интервалом намеренно. Вычисление обычного уровня
по всему периоду наблюдения означало бы заглядывание в отложенный отрезок,
вследствие чего проверка на нём перестала бы быть проверкой вне обучающей
выборки.
"""


def baselines(obs: Observations, agent: str, key: str,
              window: range = CALIBRATION_WINDOW) -> Baseline | None:
    """
    Обычный уровень и разброс ряда по всему интервалу наблюдения.

    Серединой берётся медиана, поскольку она устойчива к единичным
    выбросам, разбросом половина межквартильного размаха. При ряде короче
    трёх наблюдений отклонение не определено и переменная по этому
    показателю не вычисляется.

    Межквартильный размах обращается в ноль там, где ряд почти постоянен и
    отклоняется лишь в единичных годах. Разброс в таком случае берётся
    средним квадратическим, поскольку нулевой разброс обратил бы все годы
    ряда в середину шкалы и стёр бы единственные наблюдаемые отклонения.
    """
    full = obs.series(agent, key)
    series = [v for y, v in full.items()
              if y in window and not math.isnan(v)]
    if len(series) < 3:
        return None
    center = statistics.median(series)
    spread = 0.0
    if len(series) >= 4:
        q = statistics.quantiles(series, n=4)
        spread = (q[2] - q[0]) / 2
    if spread <= 0.0:
        spread = statistics.pstdev(series)
    return Baseline(center=center, spread=spread)


def normalize(ind: Indicator, agent: AgentPassport, year: int,
              obs: Observations,
              base: Baseline | None = None) -> tuple[float, float]:
    """
    Приводит одно наблюдение к отрезку по правилу показателя.

    Возвращает пару, наблюдённую величину и приведённую. Наблюдённая нужна
    для отчёта о происхождении числа.
    """
    raw = obs.get(agent.code, year, ind.key)

    if ind.kind is Kind.SHARE:
        other = obs.get(agent.adversary, year, ind.key) if agent.adversary \
            else sc.NA
        return raw, sc.share(raw, other)

    if ind.kind is Kind.LINEAR:
        return raw, sc.linear(raw, ind.low, ind.high)

    if ind.kind is Kind.ORDINAL:
        step = None if math.isnan(raw) else int(round(raw))
        return raw, sc.ordinal(step, ind.n_steps, inverted=ind.inverted)

    if ind.kind is Kind.COUNT:
        return raw, sc.count_of(raw, ind.total)

    if ind.kind is Kind.DEVIATION:
        if base is None:
            return raw, sc.NA
        return raw, sc.deviation_from_baseline(raw, base.center, base.spread)

    raise ValueError(f"Неизвестное правило приведения {ind.kind}")


def compose_var(var: Var, agent: AgentPassport, year: int,
                obs: Observations) -> Trace:
    """
    Вычисляет одну переменную за один год для одного агента.

    Порядок действий. Каждый применимый показатель приводится к отрезку.
    Приведённые значения складываются с равными долями, причём доля
    считается от числа наблюдённых, а не предусмотренных показателей. Если
    для переменной предусмотрен множитель и наблюдение по нему есть, сумма
    умножается на убывающий коэффициент.
    """
    trace = Trace(agent=agent.code, year=year, var=var)
    units: list[float] = []
    missing: list[str] = []

    for ind in additive(var, agent.code):
        base = baselines(obs, agent.code, ind.key) \
            if ind.kind is Kind.DEVIATION else None
        raw, unit = normalize(ind, agent, year, obs, base)
        if math.isnan(unit):
            missing.append(ind.key)
            continue
        trace.parts[ind.key] = (raw, unit)
        units.append(unit)

    trace.missing = tuple(missing)

    if not units:
        trace.value = sc.NA
        return trace

    total = sum(units) / len(units)

    d = damper(var, agent.code)
    if d is not None:
        raw, unit = normalize(d, agent, year, obs)
        if not math.isnan(unit):
            trace.damper_raw = raw
            trace.damper_factor = 1.0 - DAMPER_LIMIT * unit
            total *= trace.damper_factor

    trace.value = total
    return trace


def compose_year(agent: AgentPassport, year: int,
                 obs: Observations) -> dict[Var, Trace]:
    """Три переменные одного агента за один год."""
    return {var: compose_var(var, agent, year, obs) for var in Var}


def compose_all(agents: dict[str, AgentPassport], obs: Observations,
                years: range) -> dict[tuple[str, int, Var], Trace]:
    """
    Весь массив значений переменных.

    Ключ состоит из кода агента, года и переменной. Порядок обхода
    определён и повторяется, вследствие чего результат воспроизводим.
    """
    out: dict[tuple[str, int, Var], Trace] = {}
    for code in sorted(agents):
        agent = agents[code]
        for year in years:
            for var, trace in compose_year(agent, year, obs).items():
                out[(code, year, var)] = trace
    return out


def coverage_report(traces: dict[tuple[str, int, Var], Trace],
                    agents: dict[str, AgentPassport],
                    years: range) -> str:
    """
    Отчёт о том, для скольких лет каждая переменная вычислена.

    Показывает, где неполнота данных не позволяет получить значение, и
    потому служит указателем очерёдности добора рядов.
    """
    lines = [f"{'агент':6}{'z1':>8}{'z2':>8}{'z3':>8}   всего лет "
             f"{len(years)}"]
    for code in sorted(agents):
        counts = []
        for var in Var:
            n = sum(1 for y in years
                    if not math.isnan(traces[(code, y, var)].value))
            counts.append(n)
        lines.append(f"{code:6}" + "".join(f"{n:>8}" for n in counts))
    return "\n".join(lines)
