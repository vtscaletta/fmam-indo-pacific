"""
Симулятор. Сборка всех уровней модели в единый цикл по времени.

Один шаг от года t к году t+1 проходит шесть стадий.
    1. Сценарий вносит шоки текущего года в состояния агентов.
    2. Каждый агент прогоняется через нечёткий контроллер и порождает вектор
       стратегического действия.
    3. Матрица влияния превращает действия в приращения угрозы и доверия.
    4. Состояния агентов обновляются по трём согласованным законам.
    5. Связка уровней сворачивает действия в системное напряжение с памятью.
    6. Марковское ядро продвигает распределение по режимам.

Законы обновления состояний содержательно различны и повторяют логику
дифференцированной памяти. Восприятие угрозы растёт от давления противников,
но в покое спадает к исходному уровню, страх не вечен. Доверие к союзнику
подтачивается риторикой противника, но альянс инерционен и тянет доверие
обратно. Нормативная эрозия есть храповик и здесь: накопленный
институциональный дрейф поднимает её и не отпускает назад.

Модель полностью детерминирована. Марковское ядро продвигает распределение
вероятностей, а не разыгрывает исход, поэтому одинаковый сценарий всегда даёт
одну и ту же траекторию. Слой случайной выборки сознательно исключён.
"""

from __future__ import annotations
from dataclasses import dataclass, field

import numpy as np

from engine.fuzzy_agent import FuzzyAgent, JAPAN_CONFIG
from engine.influence import InfluenceMatrix, INFLUENCE, CODES
from engine.synthesis import LevelCoupling, aggregate
from engine.markov import MarkovCore, MARKOV, INITIAL_DISTRIBUTION


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass(frozen=True)
class DynamicsParams:
    """Параметры законов обновления состояний агентов."""
    rho_threat: float = 0.45    # реверсия восприятия угрозы к базису
    rho_trust: float = 0.4      # реверсия доверия к базису
    kappa_erosion: float = 0.15  # накопление нормативной эрозии
    drift_neutral: float = 0.5  # нейтральный уровень дрейфа, выше которого эрозия растёт


@dataclass
class Trajectory:
    """Полная история прогона. Структура удобна для графиков и отчётов."""
    scenario: str
    base_year: int
    years: list = field(default_factory=list)
    tension: list = field(default_factory=list)
    dominant: list = field(default_factory=list)
    regime_dist: list = field(default_factory=list)
    agent_states: dict = field(default_factory=dict)   # код -> список [z1, z2, z3]
    agent_actions: dict = field(default_factory=dict)  # код -> список векторов действия
    events_log: list = field(default_factory=list)     # (год, описание, переменная)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "base_year": self.base_year,
            "years": list(self.years),
            "tension": [float(t) for t in self.tension],
            "dominant": list(self.dominant),
            "regime_dist": [list(map(float, d)) for d in self.regime_dist],
            "agent_states": {c: [list(map(float, s)) for s in v]
                             for c, v in self.agent_states.items()},
            "agent_actions": {c: [dict(a) for a in v]
                              for c, v in self.agent_actions.items()},
            "events_log": list(self.events_log),
        }


class Simulator:
    """Оркестратор. Прогоняет сценарий на заданный горизонт."""

    def __init__(self, controller: FuzzyAgent = None, influence: InfluenceMatrix = None,
                 markov: MarkovCore = None, dynamics: DynamicsParams = None):
        self.controller = controller or FuzzyAgent(JAPAN_CONFIG)
        self.influence = influence or INFLUENCE
        self.markov = markov or MARKOV
        self.dynamics = dynamics or DynamicsParams()

    def run(self, scenario, agents: dict, horizon: int = 10, base_year: int = 2026) -> Trajectory:
        """
        Прогоняет сценарий. agents суть словарь код -> объект состояния с
        атрибутами z1, z2, z3. horizon в годах.
        """
        d = self.dynamics
        states = {c: [agents[c].z1, agents[c].z2, agents[c].z3] for c in CODES}
        base = {c: list(states[c]) for c in CODES}

        # Свежая связка с собственной памятью на каждый прогон. Память
        # инициализируется поведением базового года, чтобы снять холодный старт.
        coupling = LevelCoupling()
        warm = {c: self.controller.step(*states[c]) for c in CODES}
        coupling.memory.seed(aggregate(warm, coupling.weights))
        regime = INITIAL_DISTRIBUTION.copy()
        traj = Trajectory(scenario=scenario.name, base_year=base_year)
        traj.agent_states = {c: [] for c in CODES}
        traj.agent_actions = {c: [] for c in CODES}

        for k in range(horizon):
            year = base_year + k

            # Стадия 1. Шоки сценария в состояния текущего года.
            applied = scenario.apply(k, states)
            for desc, var in applied:
                traj.events_log.append((year, desc, var))

            # Стадия 2. Действия агентов.
            actions = {c: self.controller.step(*states[c]) for c in CODES}

            # Стадия 3. Межагентные приращения.
            td = self.influence.threat_delta(actions)
            tr = self.influence.trust_delta(actions)

            # Запись состояния и действий до обновления, это снимок года.
            for c in CODES:
                traj.agent_states[c].append(list(states[c]))
                traj.agent_actions[c].append(dict(actions[c]))

            # Стадия 5. Системное напряжение с памятью и конфигурацией состояний.
            tau = coupling.tension(actions, states)

            # Стадия 6. Продвижение режима.
            regime = self.markov.step(regime, tau)

            traj.years.append(year)
            traj.tension.append(tau)
            traj.regime_dist.append(np.asarray(regime, dtype=float))
            traj.dominant.append(self.markov.dominant_regime(regime))

            # Стадия 4. Обновление состояний к следующему году.
            for c in CODES:
                z1, z2, z3 = states[c]
                z1 = _clip(z1 + td[c] - d.rho_threat * (z1 - base[c][0]))
                z2 = _clip(z2 + tr[c] + d.rho_trust * (base[c][1] - z2))
                z3 = _clip(z3 + max(0.0, d.kappa_erosion * (actions[c]["drift"] - d.drift_neutral)))
                states[c] = [z1, z2, z3]

        return traj


SIMULATOR = Simulator()
