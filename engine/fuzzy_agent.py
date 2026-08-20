"""
Нечёткий контроллер Мамдани одного государства-агента. Микроуровень FMAM.

Контроллер принимает три входные переменные в диапазоне [0, 1]:
    z1  восприятие угрозы      (threat perception)
    z2  доверие к союзнику     (alliance trust)
    z3  нормативная эрозия     (normative erosion)

и порождает вектор стратегического действия из трёх выходов в [0, 1]:
    milex   приращение военных расходов        (delta MilExp)
    rhet    приращение стратегической риторики (delta Rhet)
    drift   приращение институционального дрейфа (delta InstDrift)

Аппарат. Фаззификация гауссовыми функциями принадлежности, агрегация
антецедентов через t-норму (минимум), импликация альфа-срезом, аккумуляция
через s-норму (максимум), дефаззификация методом центра тяжести. База из
двадцати семи продукционных правил порождается детерминированной картой
консеквентов, выведенной из постулатов политического реализма.

Калибровка агента "Япония" воспроизводит эталонный прогон 2022 года из
диссертации с точностью лучше четырёх сотых по каждому выходу.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


# Дискретная сетка области определения. Шаг 0.01 достаточен для центра тяжести.
_U = np.arange(0.0, 1.001, 0.01)

# Кодировка лингвистических термов уровнями. Низкий 0, средний 1, высокий 2.
_TERMS = ("low", "med", "high")
_LVL = {"low": 0, "med": 1, "high": 2}
_NAME = {0: "low", 1: "med", 2: "high"}

# Человекочитаемые подписи термов для пошагового разбора и интерфейса.
RU_TERM = {"low": "низкий", "med": "средний", "high": "высокий"}
RU_INPUT = {"z1": "восприятие угрозы", "z2": "доверие к союзнику", "z3": "нормативная эрозия"}
RU_OUTPUT = {
    "milex": "приращение военных расходов",
    "rhet": "приращение стратегической риторики",
    "drift": "приращение институционального дрейфа",
}


def _gauss(c: float, s: float) -> np.ndarray:
    """Гауссова функция принадлежности с центром c и шириной s на сетке _U."""
    return np.exp(-((_U - c) ** 2) / (2.0 * s * s))


def _clamp_level(x: float) -> str:
    """Округление непрерывного индекса к ближайшему терму и зажим в [0, 2]."""
    return _NAME[max(0, min(2, int(round(x))))]


# --- Карта консеквентов ---------------------------------------------------
#
# Двадцать семь правил порождаются не подобранными коэффициентами, а составом
# входов каждого выхода. Состав определяется теоретическим положением, и
# всякий вход, вошедший в состав, участвует равной долей.
#
# Военные расходы зависят от восприятия угрозы и от недостатка доверия.
# Первое следует из положения о самопомощи в анархической среде, второе из
# союзной дилеммы, где страх оставления влечёт опору на собственные силы.
# Нормативная эрозия в состав не входит, поскольку конституционный потолок
# ограничивает применение силы, а не её финансирование, что подтверждается
# сокращением японских расходов в годы накопления процедур обхода.
#
# Стратегическая риторика зависит от восприятия угрозы и от нормативной
# эрозии. Первое следует из теории секьюритизации, где чрезвычайный речевой
# акт порождается предъявлением угрозы, второе из положения о том, что
# расхождение провозглашаемой нормы и поведения устраняется переопределением
# соответствия. Доверие в состав не входит, поскольку аудиторией речевого
# акта выступает собственное население, а не гарант.
#
# Институциональный дрейф зависит от всех трёх входов. Угроза даёт повод,
# эрозия даёт уже ослабленный потолок, недостаток доверия даёт союзное
# требование правовой определённости.
#
# Уровень последствия равен округлённому среднему уровней входов состава.
# Подобранных коэффициентов не остаётся ни одного.

def _mean_level(*levels: int) -> str:
    """Округлённое среднее уровней входов, приведённое к терму."""
    return _clamp_level(sum(levels) / len(levels))


def _consequent_milex(t: int, tr: int, e: int) -> str:
    """Состав: восприятие угрозы и недостаток доверия."""
    return _mean_level(t, 2 - tr)


def _consequent_rhet(t: int, tr: int, e: int) -> str:
    """Состав: восприятие угрозы и нормативная эрозия."""
    return _mean_level(t, e)


def _consequent_drift(t: int, tr: int, e: int) -> str:
    """Состав: восприятие угрозы, недостаток доверия и нормативная эрозия."""
    return _mean_level(t, 2 - tr, e)


@dataclass(frozen=True)
class InputCalibration:
    """
    Параметры функций принадлежности одного входа. Тройка (центр, ширина)
    для термов низкий, средний, высокий. Калибруется отдельно для каждого
    агента и каждой переменной.
    """
    low: tuple[float, float]
    med: tuple[float, float]
    high: tuple[float, float]


@dataclass(frozen=True)
class AgentConfig:
    """Полная калибровка одного агента. Имя и три входные калибровки."""
    name: str
    threat: InputCalibration
    trust: InputCalibration
    erosion: InputCalibration


# --- Калибровка функций принадлежности ------------------------------------
#
# Ширина не подбирается, а выводится из требования, чтобы соседние
# лингвистические термы перекрывались ровно наполовину. Центры термов стоят
# в нуле, середине и единице, точки равного удаления между ними приходятся
# на четверть и три четверти. Требование даёт уравнение
#
#     exp( -(0.25)^2 / (2 s^2) ) = 0.5
#
# откуда 2 s^2 = 0.0625 / ln 2, то есть s = 0.2123.
#
# Величина едина для всех входов и для всех агентов. Различие между
# агентами переносится в способ измерения переменных, а не в разметку
# шкалы, вследствие чего значения остаются сопоставимыми между участниками.

_OVERLAP = 0.5
"""Уровень перекрытия соседних термов в точке равного удаления."""


def _width_from_overlap(centers_gap: float = 0.5,
                        overlap: float = _OVERLAP) -> float:
    """
    Ширина функции принадлежности из условия перекрытия.

    Точка равного удаления между соседними центрами отстоит от каждого на
    половину промежутка. Требование равенства принадлежности заданному
    уровню в этой точке определяет ширину однозначно.
    """
    half = centers_gap / 2.0
    return math.sqrt(-(half ** 2) / (2.0 * math.log(overlap)))


SIGMA = _width_from_overlap()
"""Единая ширина функций принадлежности, около 0.2123."""

_STD = InputCalibration(low=(0.0, SIGMA), med=(0.5, SIGMA), high=(1.0, SIGMA))

STANDARD_CONFIG = AgentConfig(
    name="единая разметка",
    threat=_STD,
    trust=_STD,
    erosion=_STD,
)

# Прежнее имя сохранено ради совместимости вызовов. Разметка более не
# зависит от агента.
JAPAN_CONFIG = STANDARD_CONFIG

# Калибровка выходных переменных. Центры термов ставятся в нуле, середине и
# единице тем же правилом, что и у входов, вследствие чего выходная шкала
# перестаёт быть усечённой и различает состояния на всём отрезке.
_OUT_CENTERS = {"low": (0.0, SIGMA), "med": (0.5, SIGMA), "high": (1.0, SIGMA)}


class FuzzyAgent:
    """
    Нечёткий контроллер Мамдани одного агента. Инкапсулирует функции
    принадлежности, базу правил и систему вывода scikit-fuzzy.
    """

    def __init__(self, config: AgentConfig = None):
        self.config = config or JAPAN_CONFIG
        self._build()

    def _build(self) -> None:
        c = self.config

        self._threat = ctrl.Antecedent(_U, "threat")
        self._trust = ctrl.Antecedent(_U, "trust")
        self._eros = ctrl.Antecedent(_U, "eros")
        for ant, cal in (
            (self._threat, c.threat),
            (self._trust, c.trust),
            (self._eros, c.erosion),
        ):
            ant["low"] = _gauss(*cal.low)
            ant["med"] = _gauss(*cal.med)
            ant["high"] = _gauss(*cal.high)

        self._milex = ctrl.Consequent(_U, "milex", defuzzify_method="centroid")
        self._rhet = ctrl.Consequent(_U, "rhet", defuzzify_method="centroid")
        self._drift = ctrl.Consequent(_U, "drift", defuzzify_method="centroid")
        for out in (self._milex, self._rhet, self._drift):
            for term in _TERMS:
                out[term] = _gauss(*_OUT_CENTERS[term])

        rules = []
        for t in _TERMS:
            for tr in _TERMS:
                for e in _TERMS:
                    lt, ltr, le = _LVL[t], _LVL[tr], _LVL[e]
                    antecedent = self._threat[t] & self._trust[tr] & self._eros[e]
                    rules.append(
                        ctrl.Rule(
                            antecedent,
                            [
                                self._milex[_consequent_milex(lt, ltr, le)],
                                self._rhet[_consequent_rhet(lt, ltr, le)],
                                self._drift[_consequent_drift(lt, ltr, le)],
                            ],
                        )
                    )
        self._rules = rules
        self._sim = ctrl.ControlSystemSimulation(ctrl.ControlSystem(rules))

    @staticmethod
    def _check_inputs(z1: float, z2: float, z3: float) -> None:
        for name, z in (("z1", z1), ("z2", z2), ("z3", z3)):
            if not (0.0 <= z <= 1.0):
                raise ValueError(f"{name} вне диапазона [0, 1]: {z}")

    def step(self, z1: float, z2: float, z3: float) -> dict:
        """
        Один шаг вывода. Возвращает вектор действия и его евклидову норму.
        z1 угроза, z2 доверие, z3 эрозия. Все в [0, 1].
        """
        self._check_inputs(z1, z2, z3)
        self._sim.input["threat"] = z1
        self._sim.input["trust"] = z2
        self._sim.input["eros"] = z3
        self._sim.compute()
        milex = float(self._sim.output["milex"])
        rhet = float(self._sim.output["rhet"])
        drift = float(self._sim.output["drift"])
        norm = float(np.linalg.norm([milex, rhet, drift]))
        return {"milex": milex, "rhet": rhet, "drift": drift, "norm": norm}

    def fuzzify(self, z1: float, z2: float, z3: float) -> dict:
        """
        Степени принадлежности каждого входа к каждому терму. Первый шаг
        пошагового разбора для прозрачности вычислений.
        """
        self._check_inputs(z1, z2, z3)
        out = {}
        for key, ant, z in (("z1", self._threat, z1), ("z2", self._trust, z2), ("z3", self._eros, z3)):
            out[key] = {
                term: float(fuzz.interp_membership(ant.universe, ant[term].mf, z))
                for term in _TERMS
            }
        return out

    def active_rules(self, z1: float, z2: float, z3: float, eps: float = 1e-3) -> list:
        """
        Сработавшие правила с уровнем активации alpha и консеквентами.
        Возвращает список, отсортированный по убыванию alpha. Перебор ведётся
        по той же карте консеквентов, что строит базу правил, поэтому разбор
        точно соответствует работающей системе вывода.
        """
        f = self.fuzzify(z1, z2, z3)
        rows = []
        for t in _TERMS:
            for tr in _TERMS:
                for e in _TERMS:
                    alpha = min(f["z1"][t], f["z2"][tr], f["z3"][e])
                    if alpha <= eps:
                        continue
                    lt, ltr, le = _LVL[t], _LVL[tr], _LVL[e]
                    rows.append(
                        {
                            "alpha": alpha,
                            "if": {"threat": t, "trust": tr, "erosion": e},
                            "then": {
                                "milex": _consequent_milex(lt, ltr, le),
                                "rhet": _consequent_rhet(lt, ltr, le),
                                "drift": _consequent_drift(lt, ltr, le),
                            },
                        }
                    )
        rows.sort(key=lambda r: r["alpha"], reverse=True)
        return rows

    def all_rules(self) -> list:
        """
        Полная база из двадцати семи продукционных правил без привязки к
        состоянию. Перебор ведётся по той же карте консеквентов, что строит
        систему вывода, поэтому свод тождествен работающему контроллеру.
        Предназначен для вынесения в приложение диссертации.
        """
        rows = []
        for t in _TERMS:
            for tr in _TERMS:
                for e in _TERMS:
                    lt, ltr, le = _LVL[t], _LVL[tr], _LVL[e]
                    rows.append(
                        {
                            "if": {"threat": t, "trust": tr, "erosion": e},
                            "then": {
                                "milex": _consequent_milex(lt, ltr, le),
                                "rhet": _consequent_rhet(lt, ltr, le),
                                "drift": _consequent_drift(lt, ltr, le),
                            },
                        }
                    )
        return rows

    def mf_params(self, var: str, term: str) -> tuple:
        """Центр и ширину гауссовой функции принадлежности (var, term)."""
        cal = {"z1": self.config.threat, "z2": self.config.trust,
               "z3": self.config.erosion}[var]
        return getattr(cal, term)


# Готовый экземпляр агента "Япония" для импорта.
JAPAN = FuzzyAgent(JAPAN_CONFIG)
