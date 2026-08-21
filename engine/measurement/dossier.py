"""
Досье для кодирования уровня враждебности.

Назначение слоя. Кодировщики получают не перечень изданий, а готовое
изложение задокументированных событий, одно и то же для всех. Здесь
хранятся события и собирается досье по единицам кодирования.

Устройство хранилища. Таблица событий длинным видом. Одна строка на одно
задокументированное действие. Столбцы, date дата в виде года и месяца либо
одного года, agent_a и agent_b коды участников, action краткое обозначение
действия, description изложение в одну-две строки, source наименование
источника, url постоянная ссылка.

Событие относится к обоим участникам одновременно, поскольку государство
выступает участником спора независимо от того, действовало ли оно само либо
действия совершались против него.

Единица кодирования есть пара из государства и года. Досье единицы
содержит все события, где государство названо одним из участников, за
данный год, в порядке дат.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from engine.measurement.loaders import DataError

CODING_YEARS = range(2015, 2026)
"""
Годы, подлежащие кодированию. Набор данных о милитаризованных спорах
завершается 2014 годом, вследствие чего последующие годы восполняются
кодированием по правилам той же кодовой книги.
"""


@dataclass(frozen=True)
class Event:
    """Одно задокументированное действие."""
    date: str
    agent_a: str
    agent_b: str
    action: str
    description: str
    source: str
    url: str

    @property
    def year(self) -> int:
        return int(self.date[:4])

    def involves(self, code: str) -> bool:
        return code in (self.agent_a, self.agent_b)


def load_events(path: str | Path, agents: dict) -> list[Event]:
    """
    Читает таблицу событий и проверяет её.

    Проверяется, что участники известны, что год лежит в подлежащем
    кодированию интервале, что изложение и источник не пусты и что
    участники не совпадают.
    """
    p = Path(path)
    if not p.exists():
        raise DataError(f"Файл событий не найден, {p}")
    out: list[Event] = []
    with p.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        need = {"date", "agent_a", "agent_b", "action", "description",
                "source", "url"}
        missing = need - set(reader.fieldnames or [])
        if missing:
            raise DataError(f"{p}, отсутствуют столбцы {sorted(missing)}")
        for i, r in enumerate(reader, start=2):
            a, b = r["agent_a"].strip(), r["agent_b"].strip()
            if a not in agents or b not in agents:
                raise DataError(f"{p}, строка {i}, неизвестный участник")
            if a == b:
                raise DataError(f"{p}, строка {i}, участники совпадают")
            date = r["date"].strip()
            if len(date) < 4 or not date[:4].isdigit():
                raise DataError(f"{p}, строка {i}, дата {date!r} неверна")
            if int(date[:4]) not in CODING_YEARS:
                raise DataError(f"{p}, строка {i}, год вне интервала "
                                f"кодирования")
            if not r["description"].strip():
                raise DataError(f"{p}, строка {i}, изложение пусто")
            if not r["source"].strip():
                raise DataError(f"{p}, строка {i}, источник не указан")
            out.append(Event(
                date=date, agent_a=a, agent_b=b,
                action=r["action"].strip(),
                description=r["description"].strip(),
                source=r["source"].strip(),
                url=r["url"].strip(),
            ))
    return sorted(out, key=lambda e: (e.date, e.agent_a, e.agent_b))


def by_unit(events: list[Event], agents: dict) -> dict[tuple[str, int],
                                                       list[Event]]:
    """Досье по единицам кодирования. Ключ есть код агента и год."""
    out: dict[tuple[str, int], list[Event]] = defaultdict(list)
    for code in sorted(agents):
        for year in CODING_YEARS:
            out[(code, year)] = [e for e in events
                                 if e.involves(code) and e.year == year]
    return dict(out)


def coverage(units: dict[tuple[str, int], list[Event]],
             agents: dict) -> str:
    """Полнота досье. Число событий по агентам и годам."""
    lines = [f"{'агент':6}" + "".join(f"{y % 100:>5}" for y in CODING_YEARS)
             + f"{'всего':>8}"]
    for code in sorted(agents):
        row = [len(units[(code, y)]) for y in CODING_YEARS]
        lines.append(f"{code:6}" + "".join(f"{n:>5}" for n in row)
                     + f"{sum(row):>8}")
    total = sum(len(v) for v in units.values())
    lines.append(f"единиц {len(units)}, записей в досье {total}, "
                 f"пустых единиц "
                 f"{sum(1 for v in units.values() if not v)}")
    return "\n".join(lines)


def render_unit(code: str, year: int, events: list[Event],
                agents: dict) -> str:
    """Досье одной единицы в виде, пригодном для предъявления кодировщику."""
    name = agents[code].name
    head = f"Единица. {name} ({code}), {year} год."
    if not events:
        return head + "\n  Задокументированных событий не обнаружено."
    lines = [head]
    for e in events:
        other = e.agent_b if e.agent_a == code else e.agent_a
        lines.append(f"  {e.date}. Вторая сторона {agents[other].name}. "
                     f"{e.description}")
        lines.append(f"    Источник. {e.source}")
    return "\n".join(lines)


def render_all(units: dict[tuple[str, int], list[Event]], agents: dict,
               shuffle_seed: int = 20260101) -> list[tuple[str, str]]:
    """
    Все единицы в перемешанном порядке.

    Порядок задаётся зерном и потому воспроизводим. Перемешивание нужно
    затем, чтобы соседние единицы не подсказывали кодировщику ход рядом
    стоящих лет.
    """
    import random
    keys = sorted(units)
    rnd = random.Random(shuffle_seed)
    rnd.shuffle(keys)
    return [(f"{code}-{year}", render_unit(code, year, units[(code, year)],
                                           agents))
            for code, year in keys]
