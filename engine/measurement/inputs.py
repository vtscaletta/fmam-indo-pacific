"""
Стык слоя измерения с моделью.

Назначение слоя. Модель различает два рода величин. Одни приходят извне и
задаются наблюдением, другие возникают из взаимодействия агентов. Здесь
проводится это разделение и готовятся три набора величин для симулятора.

Разделение и его основание.

Нормативная эрозия приходит извне на каждом шаге, поскольку она есть запись
датированных решений. Снятие запрета либо смена ступени правового потолка
суть события внешнего мира, а не следствия взаимодействия агентов внутри
модели, вследствие чего подавать их из наблюдений правомерно.

Восприятие угрозы складывается из двух составляющих. Одна возникает из
взаимного влияния и производится моделью, другая приходит из наблюдений в
виде частотности инцидентов в зоне соприкосновения. Инцидент есть событие
внешнего мира в том же смысле, в каком им является правительственное
решение, вследствие чего исключать его из шага оснований нет. Составляющие
складываются равными долями.

Доверие к гаранту берётся из наблюдений однократно, на первом году
интервала, и далее производится моделью, поскольку оно возникает из
взаимного влияния целиком.

Доля первичного противника в расходах пары в модель не подаётся ни на одном
шаге, за исключением первого года, где образует начальное значение, и
служит мишенью проверки.

Наблюдаемые ряды отношения расходов в модель не подаются вовсе и образуют
мишень проверки. Модель, ведомая датированными решениями, обязана
произвести траекторию, которой не видела, отчего совпадение с наблюдаемой
становится результатом, а не отражением входа.

Что модуль знает. Разделение величин по роду и порядок их подготовки.
Чего модуль не знает. Ни правил приведения, ни устройства контроллера, ни
марковского ядра.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from engine.measurement import scales as sc
import statistics

from engine.measurement.compose import (
    CALIBRATION_WINDOW, Baseline, Trace, compose_var,
)
from engine.measurement.indicators import BY_KEY, Var
from engine.measurement.loaders import AgentPassport, Observations


PROVISIONAL_TRUST = {
    "treaty": 0.65,
    "patronage": 0.50,
    "hedging": 0.50,
    "guarantor": 0.70,
}
"""
Предварительные начальные значения доверия по типу опоры.

Величины наблюдением не выведены и потому помечены как предварительные.
Они применяются лишь до выгрузки рядов совместных мероприятий и поставок
вооружений, после чего заменяются вычисленными. Влияние их выбора на итог
подлежит установлению расчётом.
"""


@dataclass(frozen=True)
class ModelInputs:
    """
    Три набора величин, готовых к подаче в симулятор.

    erosion   нормативная эрозия по агентам и годам, внешнее воздействие
    incidents наблюдаемая частотность инцидентов по агентам и годам
    initial   начальные значения трёх переменных на первом году интервала
    targets   наблюдаемое отношение расходов, мишень проверки
    traces    записи хода вычисления для отчёта о происхождении чисел
    notes     перечень величин, взятых допущением, а не наблюдением
    """
    first_year: int
    years: tuple[int, ...]
    erosion: dict[str, dict[int, float]]
    incidents: dict[str, dict[int, float]]
    initial: dict[str, tuple[float, float, float]]
    targets: dict[str, dict[int, float]]
    traces: dict[tuple[str, int, Var], Trace] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def incident_at(self, agent: str, year: int) -> float:
        """
        Наблюдаемая составляющая восприятия угрозы за год.

        Отсутствие наблюдения возвращается пропуском и нулём не
        подменяется, поскольку отсутствие сведений об инцидентах не есть
        сведение об их отсутствии.
        """
        return self.incidents.get(agent, {}).get(year, sc.NA)

    def erosion_at(self, agent: str, year: int) -> float:
        """Эрозия агента за год либо перенос последнего известного значения."""
        row = self.erosion.get(agent, {})
        if year in row:
            return row[year]
        earlier = [y for y in row if y < year]
        return row[max(earlier)] if earlier else sc.NA


def observed_threat_share(agent: AgentPassport, year: int,
                          obs: Observations) -> float:
    """
    Наблюдаемое отношение расходов, доля первичного противника в паре.

    Служит мишенью проверки и в модель не подаётся, за исключением первого
    года интервала, где по нему вычисляется начальное значение.
    """
    own = obs.get(agent.code, year, "milex")
    other = obs.get(agent.adversary, year, "milex") if agent.adversary else sc.NA
    return sc.share(own, other)


def share_baseline(agent: AgentPassport, obs: Observations,
                   window: range) -> Baseline | None:
    """
    Обычный уровень отношения расходов для данной пары.

    Постоянная асимметрия сил не означает постоянной угрозы. Малое
    государство, живущее рядом с большим десятилетиями, не пребывает в
    непрерывном кризисе, вследствие чего восприятие измеряется отклонением
    от привычного положения, а не самим уровнем. Правило то же, что и для
    инцидентов и для доверия.
    """
    vals = []
    for y in window:
        v = observed_threat_share(agent, y, obs)
        if not math.isnan(v):
            vals.append(v)
    if len(vals) < 3:
        return None
    center = statistics.median(vals)
    spread = 0.0
    if len(vals) >= 4:
        q = statistics.quantiles(vals, n=4)
        spread = (q[2] - q[0]) / 2
    if spread <= 0.0:
        spread = statistics.pstdev(vals)
    return Baseline(center=center, spread=spread)


def build_inputs(agents: dict[str, AgentPassport], obs: Observations,
                 years: range) -> ModelInputs:
    """
    Готовит величины для прогона.

    Порядок действий. Для каждого агента и каждого года вычисляется эрозия.
    Для первого года вычисляются начальные значения трёх переменных. По всем
    годам собирается наблюдаемое отношение расходов как мишень проверки.
    Величины, взятые допущением, перечисляются отдельно.
    """
    first = min(years)
    erosion: dict[str, dict[int, float]] = {}
    incidents: dict[str, dict[int, float]] = {}
    initial: dict[str, tuple[float, float, float]] = {}
    targets: dict[str, dict[int, float]] = {}
    traces: dict[tuple[str, int, Var], Trace] = {}
    notes: list[str] = []

    for code in sorted(agents):
        agent = agents[code]
        erosion[code] = {}
        incidents[code] = {}
        targets[code] = {}
        ind = BY_KEY["incidents"]
        base_inc = None
        if ind.covers(code):
            from engine.measurement.compose import baselines
            base_inc = baselines(obs, code, "incidents")

        for year in years:
            tr = compose_var(Var.EROSION, agent, year, obs)
            traces[(code, year, Var.EROSION)] = tr
            if not math.isnan(tr.value):
                erosion[code][year] = tr.value

            if base_inc is not None:
                from engine.measurement.compose import normalize
                _, unit = normalize(ind, agent, year, obs, base_inc)
                if not math.isnan(unit):
                    incidents[code][year] = unit

            share = observed_threat_share(agent, year, obs)
            if not math.isnan(share):
                targets[code][year] = share

        raw_share = targets[code].get(first, sc.NA)
        sb = share_baseline(agent, obs, CALIBRATION_WINDOW)
        if math.isnan(raw_share) or sb is None:
            z1 = _fallback_threat(agent, obs, first, notes)
        else:
            z1 = sc.deviation_from_baseline(raw_share, sb.center, sb.spread)

        z2_trace = compose_var(Var.TRUST, agent, first, obs)
        traces[(code, first, Var.TRUST)] = z2_trace
        z2 = z2_trace.value
        if math.isnan(z2):
            z2 = PROVISIONAL_TRUST[agent.trust_type]
            notes.append(f"{code}, доверие на {first} год взято допущением "
                         f"по типу опоры {agent.trust_type}, значение {z2}")

        z3 = erosion[code].get(first, sc.NA)
        if math.isnan(z3):
            notes.append(f"{code}, эрозия на {first} год не вычислена")

        initial[code] = (z1, z2, z3)

    return ModelInputs(
        first_year=first,
        years=tuple(years),
        erosion=erosion,
        incidents=incidents,
        initial=initial,
        targets=targets,
        traces=traces,
        notes=tuple(notes),
    )


def _fallback_threat(agent: AgentPassport, obs: Observations, year: int,
                     notes: list[str]) -> float:
    """
    Начальное восприятие угрозы при отсутствии ряда расходов у пары.

    Случай встречается там, где расходов нет у самого агента либо у его
    первичного противника. Наблюдение заменяется ближайшим доступным годом,
    а при полном отсутствии ряда величина помечается как отсутствующая.
    """
    own_years = set(obs.years(agent.code, "milex"))
    adv_years = set(obs.years(agent.adversary, "milex")) if agent.adversary \
        else set()
    common = sorted(own_years & adv_years)
    if not common:
        notes.append(f"{agent.code}, восприятие угрозы на {year} год не "
                     f"вычислено, ряд расходов пары отсутствует")
        return sc.NA
    nearest = min(common, key=lambda y: abs(y - year))
    notes.append(f"{agent.code}, восприятие угрозы на {year} год взято по "
                 f"ближайшему доступному {nearest} году")
    return sc.share(obs.get(agent.code, nearest, "milex"),
                    obs.get(agent.adversary, nearest, "milex"))


def readiness_report(inputs: ModelInputs,
                     agents: dict[str, AgentPassport]) -> str:
    """
    Отчёт о готовности величин к прогону.

    Показывает, для скольких лет вычислена эрозия, каковы начальные
    значения и какие величины взяты допущением. Служит указателем
    очерёдности выгрузки недостающих рядов.
    """
    n = len(inputs.years)
    lines = [f"Интервал {inputs.first_year}-{max(inputs.years)}, лет {n}", ""]
    lines.append(f"{'агент':6}{'эрозия':>9}{'z1':>8}{'z2':>8}{'z3':>8}"
                 f"{'мишень':>9}")
    for code in sorted(agents):
        z1, z2, z3 = inputs.initial[code]
        lines.append(
            f"{code:6}"
            f"{len(inputs.erosion[code]):>9}"
            f"{_f(z1):>8}{_f(z2):>8}{_f(z3):>8}"
            f"{len(inputs.targets[code]):>9}")
    if inputs.notes:
        lines.append("")
        lines.append("величины, взятые допущением либо не вычисленные")
        for note in inputs.notes:
            lines.append(f"  {note}")
    return "\n".join(lines)


def _f(x: float) -> str:
    return "нет" if math.isnan(x) else f"{x:.3f}"
