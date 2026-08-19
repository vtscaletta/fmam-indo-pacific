"""
Чтение наблюдений и паспортов агентов.

Назначение слоя. Числа предметной области хранятся в таблицах, а не в
программе. Здесь они читаются, проверяются на целостность и выдаются
остальным слоям в готовом виде.

Что модуль знает. Устройство двух таблиц и правила их проверки.
Чего модуль не знает. Ни правил приведения к отрезку, ни состава
переменных, ни того, как показатели сворачиваются. Он не вычисляет ничего.

Две таблицы.

agents.csv содержит паспорта участников. Одна строка на агента. Столбцы,
code краткий код, name название, adversary код первичного противника,
guarantor код гаранта либо пусто, trust_type тип опоры на внешнюю
гарантию, note примечание с обоснованием.

observations.csv содержит наблюдения длинным видом. Одна строка на одно
наблюдение. Столбцы, agent код агента, year год, key ключ показателя из
реестра либо вспомогательного ряда, value значение в собственных единицах
показателя, quality качество сведения, source происхождение сведения.

Качество принимает три значения. Наблюдение означает величину, взятую из
источника прямо. Оценка означает величину, восстановленную по графику либо
выведенную из косвенных данных. Перенос означает повторение последнего
известного значения при отсутствии нового наблюдения.

Различение введено ради того, чтобы доля оценок в каждой переменной была
измерена и объявлена, а не скрыта. Величина, взятая оценкой, остаётся
пригодной при условии, что таковой названа.

Длинный вид выбран сознательно. При добавлении нового показателя таблица
не перестраивается, а лишь пополняется строками, вследствие чего ни схема,
ни программа не меняются.

Отсутствие наблюдения обозначается отсутствием строки, а не нулём и не
пустой ячейкой. Ноль есть осмысленное значение и означает наблюдённый
ноль, тогда как отсутствие строки означает, что наблюдения не было.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from engine.measurement.indicators import AUXILIARY, BY_KEY
from engine.measurement.scales import NA

YEAR_MIN = 2001
YEAR_MAX = 2025
"""
Границы периода наблюдения. Верхняя определяется правилом, согласно
которому период завершается последним полным календарным годом, поскольку
статистика незавершённого года неполна и сопоставлению с прочими не
подлежит. Годы после верхней границы принадлежат прогнозу.
"""


class DataError(ValueError):
    """Порча данных. Возбуждается вместо молчаливого исправления."""


@dataclass(frozen=True)
class AgentPassport:
    """
    Паспорт участника. Чисел, кроме кодов, не содержит.

    code        краткий код, совпадает с кодом в таблице наблюдений
    name        название по-русски
    adversary   код первичного противника, определяет пару для доли расходов
    guarantor   код гаранта безопасности либо пусто у хеджирующих
    trust_type  тип опоры, treaty, patronage, hedging либо guarantor
    note        обоснование отнесения с указанием источника
    """
    code: str
    name: str
    adversary: str
    guarantor: str
    trust_type: str
    note: str


TRUST_TYPES = {"treaty", "patronage", "hedging", "guarantor"}

QUALITIES = {"наблюдение", "оценка", "перенос"}
"""
Качество сведения. Наблюдение взято из источника прямо, оценка
восстановлена по графику либо косвенным путём, перенос повторяет последнее
известное значение.
"""


def load_agents(path: str | Path) -> dict[str, AgentPassport]:
    """
    Читает паспорта участников и проверяет их связность.

    Проверяется, что коды не повторяются, что первичный противник и гарант
    указывают на существующих участников либо пусты, и что тип опоры взят
    из закрытого перечня.
    """
    rows = _read_csv(path, {"code", "name", "adversary", "guarantor",
                            "trust_type", "note"})
    agents: dict[str, AgentPassport] = {}
    for i, r in enumerate(rows, start=2):
        code = r["code"].strip()
        if not code:
            raise DataError(f"{path}, строка {i}, пустой код агента")
        if code in agents:
            raise DataError(f"{path}, строка {i}, код {code} повторяется")
        ttype = r["trust_type"].strip()
        if ttype not in TRUST_TYPES:
            raise DataError(
                f"{path}, строка {i}, неизвестный тип опоры {ttype!r}, "
                f"допустимы {sorted(TRUST_TYPES)}")
        agents[code] = AgentPassport(
            code=code,
            name=r["name"].strip(),
            adversary=r["adversary"].strip(),
            guarantor=r["guarantor"].strip(),
            trust_type=ttype,
            note=r["note"].strip(),
        )

    for a in agents.values():
        if a.adversary and a.adversary not in agents:
            raise DataError(
                f"У агента {a.code} противник {a.adversary} отсутствует "
                f"в перечне участников")
        if a.guarantor and a.guarantor not in agents:
            raise DataError(
                f"У агента {a.code} гарант {a.guarantor} отсутствует "
                f"в перечне участников")
        if a.adversary == a.code:
            raise DataError(f"Агент {a.code} назначен противником самому себе")
    return agents


@dataclass(frozen=True)
class Observations:
    """
    Наблюдения, готовые к чтению по трём ключам.

    Хранение устроено словарём с ключом из кода агента, года и ключа
    показателя. Отсутствующее наблюдение возвращается как NA, а не как
    ошибка, поскольку неполнота рядов есть обычное положение дел и
    обрабатывается на следующем слое.
    """
    values: dict[tuple[str, int, str], float]
    sources: dict[tuple[str, int, str], str]
    qualities: dict[tuple[str, int, str], str]

    def get(self, agent: str, year: int, key: str) -> float:
        """Наблюдение либо NA при его отсутствии."""
        return self.values.get((agent, year, key), NA)

    def source_of(self, agent: str, year: int, key: str) -> str:
        """Происхождение наблюдения либо пустая строка."""
        return self.sources.get((agent, year, key), "")

    def quality_of(self, agent: str, year: int, key: str) -> str:
        """Качество сведения либо пустая строка при его отсутствии."""
        return self.qualities.get((agent, year, key), "")

    def quality_share(self, keys: list[str] | None = None) -> dict[str, float]:
        """
        Доля сведений каждого качества среди отобранных показателей.

        Служит для отчёта о том, какая часть параметризации опирается на
        наблюдения, а какая на оценки и переносы.
        """
        cells = [c for c in self.values if keys is None or c[2] in keys]
        if not cells:
            return {}
        counts: dict[str, int] = {}
        for c in cells:
            q = self.qualities.get(c, "")
            counts[q] = counts.get(q, 0) + 1
        return {q: n / len(cells) for q, n in sorted(counts.items())}

    def years(self, agent: str, key: str) -> list[int]:
        """Годы, за которые наблюдение есть, по возрастанию."""
        return sorted(y for (a, y, k) in self.values if a == agent and k == key)

    def series(self, agent: str, key: str) -> dict[int, float]:
        """Ряд наблюдений по годам."""
        return {y: self.values[(agent, y, key)] for y in self.years(agent, key)}

    def coverage(self, agents: list[str]) -> dict[str, dict[str, int]]:
        """
        Полнота покрытия, число лет с наблюдением по каждому показателю.

        Служит для отчёта о том, какие ряды выгружены, а какие ещё нет.
        """
        out: dict[str, dict[str, int]] = {}
        for code in agents:
            out[code] = {}
            for key, ind in BY_KEY.items():
                if ind.covers(code):
                    out[code][key] = len(self.years(code, key))
        return out


def load_observations(path: str | Path,
                      agents: dict[str, AgentPassport]) -> Observations:
    """
    Читает наблюдения и проверяет их на целостность.

    Проверяется, что агент известен, что показатель объявлен в реестре, что
    показатель применим к данному агенту, что год лежит в границах периода
    наблюдения, что значение читается как число и что одно и то же
    наблюдение не встречается дважды.
    """
    rows = _read_csv(path, {"agent", "year", "key", "value", "quality",
                            "source"})
    values: dict[tuple[str, int, str], float] = {}
    sources: dict[tuple[str, int, str], str] = {}
    qualities: dict[tuple[str, int, str], str] = {}

    for i, r in enumerate(rows, start=2):
        agent = r["agent"].strip()
        key = r["key"].strip()
        raw_year = r["year"].strip()
        raw_value = r["value"].strip()

        if agent not in agents:
            raise DataError(f"{path}, строка {i}, неизвестный агент {agent!r}")
        if key not in BY_KEY and key not in AUXILIARY:
            raise DataError(f"{path}, строка {i}, показатель {key!r} "
                            f"не объявлен ни в реестре, ни среди "
                            f"вспомогательных рядов")
        if key in BY_KEY and not BY_KEY[key].covers(agent):
            raise DataError(f"{path}, строка {i}, показатель {key!r} "
                            f"к агенту {agent!r} не применяется")
        try:
            year = int(raw_year)
        except ValueError:
            raise DataError(f"{path}, строка {i}, год {raw_year!r} не число")
        if not YEAR_MIN <= year <= YEAR_MAX:
            raise DataError(f"{path}, строка {i}, год {year} вне периода "
                            f"{YEAR_MIN}-{YEAR_MAX}")
        if raw_value == "":
            raise DataError(f"{path}, строка {i}, пустое значение. "
                            f"Отсутствие наблюдения обозначается отсутствием "
                            f"строки, а не пустой ячейкой")
        try:
            value = float(raw_value.replace(",", "."))
        except ValueError:
            raise DataError(f"{path}, строка {i}, значение {raw_value!r} "
                            f"не число")

        cell = (agent, year, key)
        if cell in values:
            raise DataError(f"{path}, строка {i}, наблюдение {cell} "
                            f"встречается дважды")
        quality = r["quality"].strip()
        if quality not in QUALITIES:
            raise DataError(f"{path}, строка {i}, качество {quality!r} "
                            f"неизвестно, допустимы {sorted(QUALITIES)}")
        values[cell] = value
        sources[cell] = r["source"].strip()
        qualities[cell] = quality

    return Observations(values=values, sources=sources, qualities=qualities)


def _read_csv(path: str | Path, required: set[str]) -> list[dict[str, str]]:
    """Читает таблицу и удостоверяет наличие обязательных столбцов."""
    p = Path(path)
    if not p.exists():
        raise DataError(f"Файл данных не найден, {p}")
    with p.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = set(reader.fieldnames or [])
        missing = required - header
        if missing:
            raise DataError(f"{p}, отсутствуют столбцы {sorted(missing)}")
        return list(reader)
