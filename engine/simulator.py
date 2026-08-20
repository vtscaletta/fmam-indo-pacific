"""
Симулятор. Сборка уровней модели в единый цикл по времени.

Устройство шага. Один шаг от года к следующему проходит пять стадий.

    1. Нормативная эрозия каждого агента берётся извне, из наблюдений либо
       из сценария, и подставляется в состояние.
    2. Каждый агент прогоняется через нечёткий контроллер и порождает
       вектор стратегического действия.
    3. Матрица влияния превращает действия в приращения восприятия угрозы
       и доверия у прочих агентов.
    4. Связка уровней сворачивает действия в системное напряжение с памятью.
    5. Марковское ядро продвигает распределение по фазовым режимам.

Разделение заданного и возникающего. Нормативная эрозия приходит извне,
поскольку она есть запись датированных решений. Восприятие угрозы и доверие
берутся из наблюдений однократно, на первом году, и далее возникают из
взаимного влияния. Наблюдаемые ряды отношения расходов в модель не
подаются и служат мишенью проверки.

Законы обновления. Восприятие угрозы растёт от давления прочих и в покое
спадает к исходному уровню, поскольку страх не вечен. Доверие подтачивается
риторикой главного источника угрозы и тянется обратно инерцией союза.
Нормативная эрозия эндогенного закона не имеет вовсе, она приходит извне.

Определённость. Модель полностью детерминирована. Марковское ядро продвигает
распределение вероятностей, а не разыгрывает исход, вследствие чего
одинаковые входы всегда дают одинаковую траекторию. Слой случайной выборки
сознательно исключён.

Свойство выходной шкалы. Дефаззификация методом центра тяжести на
ограниченной области определения даёт достижимый размах примерно от 0,166
до 0,834, симметричный относительно середины. Порядок и относительные
различия при этом сохраняются, а коэффициенты синтез-формулы поглощают
масштаб, отчего пересчёт к полному отрезку не производится.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Protocol

import numpy as np

from engine.fuzzy_agent import STANDARD_CONFIG, FuzzyAgent
from engine.influence import InfluenceMatrix
from engine.markov import INITIAL_DISTRIBUTION, MARKOV, MarkovCore
from engine.measurement.inputs import ModelInputs
from engine.measurement.loaders import AgentPassport
from engine.synthesis import LevelCoupling, aggregate, influence_weights


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


class ErosionSource(Protocol):
    """
    Источник нормативной эрозии.

    Возвращает значение переменной для данного агента и года. В
    ретроспективном прогоне читает наблюдения, в сценарном берёт из
    заданной траектории.
    """

    def __call__(self, agent: str, year: int) -> float: ...


class ObservedErosion:
    """Эрозия из наблюдений. Применяется в ретроспективном прогоне."""

    def __init__(self, inputs: ModelInputs):
        self.inputs = inputs

    def __call__(self, agent: str, year: int) -> float:
        return self.inputs.erosion_at(agent, year)


class FixedErosion:
    """
    Эрозия, замороженная на уровне последнего наблюдённого года.

    Применяется в сценарии, где предполагается отсутствие новых решений о
    расширении допустимого.
    """

    def __init__(self, inputs: ModelInputs, last_year: int):
        self.values = {c: inputs.erosion_at(c, last_year)
                       for c in inputs.erosion}

    def __call__(self, agent: str, year: int) -> float:
        return self.values.get(agent, float("nan"))


@dataclass(frozen=True)
class DynamicsParams:
    """
    Параметры законов обновления состояний.

    rho_threat  скорость возврата восприятия угрозы к исходному уровню
    rho_trust   скорость возврата доверия к исходному уровню

    Обе величины подбираются на калибровочном интервале и входят в число
    настраиваемых параметров модели. Закона накопления эрозии здесь нет,
    поскольку она приходит извне.
    """
    rho_threat: float = 0.45
    rho_trust: float = 0.40


@dataclass
class Trajectory:
    """Полная история прогона, пригодная для отчётов и графиков."""
    label: str
    years: list[int] = field(default_factory=list)
    tension: list[float] = field(default_factory=list)
    dominant: list[str] = field(default_factory=list)
    regime_dist: list = field(default_factory=list)
    agent_states: dict[str, list[list[float]]] = field(default_factory=dict)
    agent_actions: dict[str, list[dict]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def state_series(self, agent: str, index: int) -> list[float]:
        """Ряд одной переменной агента по годам. Индекс 0, 1 либо 2."""
        return [s[index] for s in self.agent_states[agent]]

    def action_series(self, agent: str, key: str) -> list[float]:
        """Ряд одного выхода агента по годам."""
        return [a[key] for a in self.agent_actions[agent]]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "years": list(self.years),
            "tension": [float(t) for t in self.tension],
            "dominant": list(self.dominant),
            "regime_dist": [list(map(float, d)) for d in self.regime_dist],
            "agent_states": {c: [list(map(float, s)) for s in v]
                             for c, v in self.agent_states.items()},
            "agent_actions": {c: [dict(a) for a in v]
                              for c, v in self.agent_actions.items()},
            "notes": list(self.notes),
        }


class Simulator:
    """
    Оркестратор. Прогоняет заданный интервал лет на заданном наборе агентов.

    Собственного состояния между прогонами не хранит. Связка уровней с её
    памятью создаётся заново на каждый прогон, вследствие чего повторный
    вызов с теми же входами даёт тот же результат.
    """

    def __init__(self, agents: dict[str, AgentPassport],
                 influence: InfluenceMatrix,
                 controller: FuzzyAgent | None = None,
                 markov: MarkovCore | None = None,
                 dynamics: DynamicsParams | None = None):
        self.agents = agents
        self.codes = tuple(sorted(agents))
        self.influence = influence
        self.controller = controller or FuzzyAgent(STANDARD_CONFIG)
        self.markov = markov or MARKOV
        self.dynamics = dynamics or DynamicsParams()

    def run(self, years: range,
            initial: dict[str, tuple[float, float, float]],
            erosion: ErosionSource,
            incidents: Callable[[str, int], float] | None = None,
            typical: dict[str, tuple[float, float]] | None = None,
            label: str = "ретроспектива") -> Trajectory:
        """
        Прогоняет интервал.

        initial суть начальные значения трёх переменных на первом году.
        erosion суть источник нормативной эрозии на каждый год.
        incidents суть источник наблюдаемой составляющей восприятия угрозы,
        складываемой с возникающей из взаимного влияния равной долей.

        Агенты, у которых начальное восприятие угрозы либо доверие не
        вычислено, из прогона исключаются с записью причины, поскольку
        подстановка произвольного числа исказила бы взаимное влияние.
        """
        d = self.dynamics
        traj = Trajectory(label=label)

        active = []
        for c in self.codes:
            z1, z2, z3 = initial[c]
            if math.isnan(z1) or math.isnan(z2):
                traj.notes.append(
                    f"{c}, исключён из прогона, начальное состояние "
                    f"не вычислено")
                continue
            active.append(c)

        states = {c: list(initial[c]) for c in active}
        # Точкой возврата служит обычный уровень агента, а не значение
        # первого года. Возврат к первому году заставлял бы систему первые
        # годы двигаться к равновесию независимо от событий.
        base = {c: list(typical[c]) if typical and c in typical
                else list(initial[c][:2]) for c in active}
        traj.agent_states = {c: [] for c in active}
        traj.agent_actions = {c: [] for c in active}

        first = min(years)
        weights = influence_weights(self.influence, first, active)
        coupling = LevelCoupling(weights=weights)
        warm = {c: self.controller.step(*self._inputs(states[c]))
                for c in active}
        coupling.memory.seed(aggregate(warm, weights))
        regime = INITIAL_DISTRIBUTION.copy()

        for year in years:
            # Стадия 1. Эрозия приходит извне.
            for c in active:
                e = erosion(c, year)
                if not math.isnan(e):
                    states[c][2] = e

            # Стадия 2. Действия агентов.
            actions = {c: self.controller.step(*self._inputs(states[c]))
                       for c in active}

            # Снимок года до обновления.
            for c in active:
                traj.agent_states[c].append(list(states[c]))
                traj.agent_actions[c].append(dict(actions[c]))

            # Стадия 3. Приращения от взаимного влияния.
            td = self.influence.threat_delta(actions, year)
            tr = self.influence.trust_delta(actions, year)

            # Стадия 4. Системное напряжение с памятью. Веса пересчитываются
            # на каждый год, поскольку мощь участников меняется.
            coupling.weights = influence_weights(self.influence, year, active)
            tau = coupling.tension(actions, states)

            # Стадия 5. Продвижение режима.
            regime = self.markov.step(regime, tau)

            traj.years.append(year)
            traj.tension.append(tau)
            traj.regime_dist.append(np.asarray(regime, dtype=float))
            traj.dominant.append(self.markov.dominant_regime(regime))

            # Обновление к следующему году. Эрозия не обновляется, она
            # придёт извне на следующем шаге.
            nxt = year + 1
            for c in active:
                z1, z2, z3 = states[c]
                z1 = _clip(z1 + td.get(c, 0.0)
                           - d.rho_threat * (z1 - base[c][0]))
                if incidents is not None:
                    obs_inc = incidents(c, nxt)
                    if not math.isnan(obs_inc):
                        z1 = _clip(0.5 * z1 + 0.5 * obs_inc)
                z2 = _clip(z2 + tr.get(c, 0.0)
                           + d.rho_trust * (base[c][1] - z2))
                states[c] = [z1, z2, z3]

        return traj

    @staticmethod
    def _inputs(state: list[float]) -> tuple[float, float, float]:
        """Состояние в вид, принимаемый контроллером."""
        z1, z2, z3 = state
        return (z1, z2, 0.5 if math.isnan(z3) else z3)


def build_simulator(agents: dict[str, AgentPassport],
                    influence: InfluenceMatrix,
                    dynamics: DynamicsParams | None = None) -> Simulator:
    """Собирает симулятор со стандартной разметкой и марковским ядром."""
    return Simulator(agents=agents, influence=influence, dynamics=dynamics)
