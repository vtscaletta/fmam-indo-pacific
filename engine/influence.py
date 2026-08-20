"""
Матрица межагентного влияния.

Назначение слоя. Стратегическое действие одного агента не остаётся внутри
него, а перетекает во входные переменные прочих на следующем шаге. Рост
военных расходов государства повышает восприятие угрозы у тех, кто видит в
нём противника. Рост стратегической риторики главного противника понижает
доверие агента к собственному гаранту, чем и воспроизводится страх
оставления.

Устройство веса. Вес влияния источника на цель есть произведение двух
сомножителей. Первый выражает род отношения между парой, второй мощь
источника, поскольку сильное государство пугает сильнее слабого при том же
действии.

Происхождение величин. Ни одна из них не назначена.

Род отношения задан четырьмя разрядами, а именно взаимное оспаривание
государственности, неурегулированный территориальный спор, соприкосновение
без спора и его отсутствие. Разрядам присвоены равноотстоящие числа тем же
правилом, каким приводятся прочие порядковые величины исследования.
Отнесение всякой пары к разряду хранится в таблице фактов вместе с
основанием отнесения.

Мощь источника выводится из индекса совокупных возможностей, взятого из
таблицы наблюдений годовым рядом. Вес пересчитывается на каждом шаге,
вследствие чего усиление одних участников и ослабление прочих сказывается
на матрице сразу.

Коэффициент усиления остаётся единственной подбираемой величиной слоя и
входит в число параметров, настраиваемых на калибровочном интервале.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from engine.measurement.loaders import AgentPassport, DataError
from engine.measurement.scales import NA, ordinal

RELATION_KINDS = ("none", "contact", "dispute", "sovereignty")
"""
Разряды отношения по возрастанию напряжённости.

none         прямого соприкосновения нет, влияние отсутствует
contact      соприкосновение без неурегулированного спора
dispute      неурегулированный территориальный спор
sovereignty  взаимное оспаривание государственности

Разряд первичного противника отдельно не заводится. Он берётся из паспорта
агента и повышает разряд пары на одну ступень, поскольку отношение к
первичному противнику напряжённее отношения того же рода к прочим.
"""

POWER_FLOOR = 0.5
"""
Нижняя граница сомножителя мощи. Слабейший участник влияет вдвое слабее
сильнейшего, а не перестаёт влиять вовсе, поскольку действие малого
государства в оспариваемой акватории наблюдается прочими и учитывается ими.
"""


@dataclass(frozen=True)
class Relation:
    """Род отношения одной упорядоченной пары с основанием отнесения."""
    source: str
    target: str
    kind: str
    note: str


def load_relations(path: str | Path) -> dict[tuple[str, str], Relation]:
    """
    Читает таблицу отношений и проверяет её полноту.

    Проверяется, что разряд взят из закрытого перечня, что основание
    отнесения указано, что пара не состоит из одного агента и что пары не
    повторяются. Отсутствие пары в таблице означает отсутствие
    соприкосновения.
    """
    p = Path(path)
    if not p.exists():
        raise DataError(f"Файл отношений не найден, {p}")
    out: dict[tuple[str, str], Relation] = {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        need = {"source", "target", "kind", "note"}
        missing = need - set(reader.fieldnames or [])
        if missing:
            raise DataError(f"{p}, отсутствуют столбцы {sorted(missing)}")
        for i, r in enumerate(reader, start=2):
            src, tgt = r["source"].strip(), r["target"].strip()
            kind = r["kind"].strip()
            if kind not in RELATION_KINDS:
                raise DataError(f"{p}, строка {i}, разряд {kind!r} неизвестен, "
                                f"допустимы {list(RELATION_KINDS)}")
            if not r["note"].strip():
                raise DataError(f"{p}, строка {i}, отнесение без основания")
            if src == tgt:
                raise DataError(f"{p}, строка {i}, пара из одного агента")
            key = (src, tgt)
            if key in out:
                raise DataError(f"{p}, строка {i}, пара {key} повторяется")
            out[key] = Relation(src, tgt, kind, r["note"].strip())
    return out


class InfluenceMatrix:
    """
    Матрица влияния произвольного числа агентов и две передаточные функции,
    переводящие действия одного шага в приращения входов следующего.

    Веса пересчитываются на каждый год, поскольку мощь участников меняется.
    """

    def __init__(self, agents: dict[str, AgentPassport],
                 relations: dict[tuple[str, str], Relation],
                 cinc: dict[tuple[str, int], float],
                 gain: float = 0.1):
        self.agents = agents
        self.codes = tuple(sorted(agents))
        self.relations = relations
        self.cinc = cinc
        self.gain = gain
        self._cache: dict[int, dict[str, dict[str, float]]] = {}

    # --- составляющие веса ------------------------------------------------

    def relation_level(self, source: str, target: str) -> int:
        """
        Разряд отношения от источника к цели с поправкой на первичного
        противника.

        Отношение к тому, кто назван первичным противником в паспорте цели,
        повышается на одну ступень, но выше высшего разряда не поднимается.
        """
        rel = self.relations.get((source, target))
        base = RELATION_KINDS.index(rel.kind) if rel else 0
        if self.agents[target].adversary == source:
            base += 1
        return min(base, len(RELATION_KINDS) - 1)

    def relation_weight(self, source: str, target: str) -> float:
        """Разряд отношения, приведённый равноотстоящими значениями."""
        return ordinal(self.relation_level(source, target),
                       len(RELATION_KINDS))

    def power(self, code: str, year: int) -> float:
        """
        Сомножитель мощи источника в данном году.

        Берётся долей от наибольшей мощи в системе того же года и
        приводится к отрезку от нижней границы до единицы.
        """
        vals = {c: self.cinc.get((c, year), NA) for c in self.codes}
        known = [v for v in vals.values() if not math.isnan(v)]
        if not known:
            return NA
        top = max(known)
        own = vals[code]
        if math.isnan(own) or top <= 0:
            return NA
        return POWER_FLOOR + (1.0 - POWER_FLOOR) * (own / top)

    def weights(self, year: int) -> dict[str, dict[str, float]]:
        """Полная матрица весов за год. Строка источник, столбец цель."""
        if year in self._cache:
            return self._cache[year]
        W: dict[str, dict[str, float]] = {}
        for i in self.codes:
            p = self.power(i, year)
            W[i] = {}
            for j in self.codes:
                if i == j:
                    W[i][j] = 0.0
                    continue
                r = self.relation_weight(i, j)
                W[i][j] = 0.0 if math.isnan(p) else r * p
        self._cache[year] = W
        return W

    # --- передаточные функции ---------------------------------------------

    def main_source(self, target: str, year: int) -> str | None:
        """Источник, сильнее прочих повышающий угрозу данной цели."""
        W = self.weights(year)
        incoming = {i: W[i][target] for i in self.codes if i != target}
        if not incoming or max(incoming.values()) <= 0.0:
            return None
        return max(incoming, key=incoming.get)

    def threat_delta(self, actions: dict, year: int) -> dict[str, float]:
        """
        Приращение восприятия угрозы каждого агента от военных расходов
        прочих. Действия суть словарь кода агента и вектора его действий.
        """
        W = self.weights(year)
        out = {}
        for j in self.codes:
            s = sum(W[i][j] * actions[i]["milex"]
                    for i in self.codes if i in actions)
            out[j] = s * self.gain
        return out

    def trust_delta(self, actions: dict, year: int) -> dict[str, float]:
        """
        Изменение доверия к гаранту. Рост риторики главного источника угрозы
        понижает доверие, отсюда отрицательный знак. Агенты без гаранта
        получают ноль, поскольку доверять им некому.
        """
        out = {}
        for j in self.codes:
            if not self.agents[j].guarantor:
                out[j] = 0.0
                continue
            src = self.main_source(j, year)
            if src is None or src not in actions:
                out[j] = 0.0
                continue
            out[j] = -self.gain * actions[src]["rhet"]
        return out

    # --- отчёты -----------------------------------------------------------

    def contribution(self, target: str, year: int) -> list[tuple[str, float]]:
        """
        Вклад каждого источника в давление на данную цель, по убыванию.

        Служит для отчёта о том, чьи действия определяют положение агента, и
        позволяет назвать участников, чей вклад мал, с указанием величины.
        """
        W = self.weights(year)
        total = sum(W[i][target] for i in self.codes if i != target)
        if total <= 0:
            return []
        pairs = [(i, W[i][target] / total)
                 for i in self.codes if i != target and W[i][target] > 0]
        return sorted(pairs, key=lambda x: -x[1])

    def describe(self, year: int) -> str:
        """Печатное описание матрицы за год для приложения к работе."""
        W = self.weights(year)
        head = f"{'':6}" + "".join(f"{c:>7}" for c in self.codes)
        lines = [f"Веса влияния, {year} год. Строка источник, столбец цель.",
                 head]
        for i in self.codes:
            lines.append(f"{i:6}" + "".join(f"{W[i][j]:>7.3f}"
                                            for j in self.codes))
        return "\n".join(lines)


def build_influence(agents: dict[str, AgentPassport],
                    observations, relations_path: str | Path,
                    gain: float = 0.1) -> InfluenceMatrix:
    """
    Собирает матрицу из паспортов, таблицы отношений и наблюдений.

    Индекс совокупных возможностей извлекается из таблицы наблюдений как
    вспомогательный ряд, во входные переменные модели не входящий.
    """
    relations = load_relations(relations_path)
    cinc = {(a, y): v for (a, y, k), v in observations.values.items()
            if k == "cinc"}
    if not cinc:
        raise DataError("В таблице наблюдений отсутствует ряд cinc, "
                        "без него веса влияния не вычисляются")
    return InfluenceMatrix(agents, relations, cinc, gain=gain)
