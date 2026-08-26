"""
Досье для кодирования уровня враждебности.

Назначение слоя. Кодировщики получают не перечень изданий, а готовое
изложение задокументированных событий, одно и то же для всех. Здесь
хранятся события и собирается досье по единицам кодирования.

Устройство хранилища. Таблица событий длинным видом. Одна строка на одно
задокументированное действие. Столбцы, date дата в виде года, года с месяцем
либо диапазона лет, agent_a и agent_b коды участников, action краткое
обозначение действия, description изложение в одну-две строки, source
наименование источника, url постоянная ссылка, event_type разряд записи,
note примечание составителя.

Разряды записи и их назначение.

    incident        физическое действие с датой и проверяемым источником,
                    а именно таран, водомёт, обстрел, опасный перехват.
                    Образует ядро кодирования.
    pattern         режим либо длящийся порядок без единичной даты, а
                    именно непрерывное присутствие, циклы облётов.
    legal           правовое либо демонстративное событие без прямого
                    физического соприкосновения.
    uncertain       случай, где принадлежность действия, дата либо разряд
                    установлены не окончательно.
    confirmed_zero  единица, по которой отсутствие событий подтверждено
                    двойной проверкой.
    unresolved_gap  единица, по которой поиск признан недостаточным и
                    которая кодированию не подлежит.

Ядро кодирования составляют разряды incident, pattern, legal и uncertain,
поскольку по ним есть что кодировать. Разряд confirmed_zero даёт нулевой
уровень без обращения к кодировщику. Разряд unresolved_gap выводит единицу
из набора вовсе, отчего переменная данного агента за данный год опирается
на прочие показатели.

Различение разрядов введено ради того, чтобы калибровка модели велась на
сильном сигнале. Смешение единичного физического действия с годовым
обобщением портит калибровку, поскольку второе не имеет ни даты, ни
величины.

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


EVENT_TYPES = ("incident", "pattern", "legal", "uncertain",
               "confirmed_zero", "unresolved_gap")

CODEABLE = ("incident", "pattern", "legal", "uncertain")
"""Разряды, по которым кодировщику есть что кодировать."""

CORE = ("incident",)
"""Разряд, образующий ядро калибровки."""


@dataclass(frozen=True)
class Event:
    """Одна запись таблицы событий."""
    date: str
    agent_a: str
    agent_b: str
    action: str
    description: str
    source: str
    url: str
    event_type: str = "incident"
    note: str = ""

    @property
    def years(self) -> tuple[int, ...]:
        """
        Годы, к которым относится запись.

        Дата вида 2019-06 даёт один год, дата вида 2015-2018 даёт весь
        диапазон, поскольку длящийся порядок относится к каждому году, в
        котором он наблюдался.
        """
        s = self.date.strip()
        if len(s) == 9 and s[4] == "-" and s[:4].isdigit() and s[5:].isdigit():
            return tuple(range(int(s[:4]), int(s[5:]) + 1))
        return (int(s[:4]),)

    @property
    def year(self) -> int:
        return self.years[0]

    def involves(self, code: str) -> bool:
        return code in (self.agent_a, self.agent_b)

    @property
    def is_core(self) -> bool:
        return self.event_type in CORE

    @property
    def is_codeable(self) -> bool:
        return self.event_type in CODEABLE


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
                "source", "url", "event_type"}
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
            etype = r["event_type"].strip()
            if etype not in EVENT_TYPES:
                raise DataError(f"{p}, строка {i}, разряд {etype!r} неизвестен, "
                                f"допустимы {list(EVENT_TYPES)}")
            if etype in CODEABLE and not r["source"].strip():
                raise DataError(f"{p}, строка {i}, источник не указан. "
                                f"Записи разрядов {list(CODEABLE)} без "
                                f"источника непроверяемы и недопустимы")
            out.append(Event(
                date=date, agent_a=a, agent_b=b,
                action=r["action"].strip(),
                description=r["description"].strip(),
                source=r["source"].strip(),
                url=r["url"].strip(),
                event_type=etype,
                note=r.get("note", "").strip(),
            ))
    return sorted(out, key=lambda e: (e.date, e.agent_a, e.agent_b))


def by_unit(events: list[Event], agents: dict, *,
            only: tuple[str, ...] | None = None
            ) -> dict[tuple[str, int], list[Event]]:
    """
    Досье по единицам кодирования. Ключ есть код агента и год.

    Аргумент only отбирает разряды записей. По умолчанию берутся все, что
    позволяет видеть полную картину. Передача CORE даёт ядро калибровки,
    передача CODEABLE даёт набор, предъявляемый кодировщикам.
    """
    out: dict[tuple[str, int], list[Event]] = defaultdict(list)
    for code in sorted(agents):
        for year in CODING_YEARS:
            out[(code, year)] = [
                e for e in events
                if e.involves(code) and year in e.years
                and (only is None or e.event_type in only)]
    return dict(out)


def unit_status(events: list[Event], agents: dict) -> dict[tuple[str, int], str]:
    """
    Состояние каждой единицы.

    Возвращает одно из четырёх, а именно ядро при наличии физических
    инцидентов, серая зона при наличии лишь фона, правовых либо
    неопределённых записей, подтверждённый ноль и объявленный пробел.
    Единица без единой записи получает объявленный пробел, поскольку
    отсутствие отметки не есть подтверждение отсутствия событий.
    """
    units = by_unit(events, agents)
    out: dict[tuple[str, int], str] = {}
    for key, evs in units.items():
        types = {e.event_type for e in evs}
        if "incident" in types:
            out[key] = "ядро"
        elif types & {"pattern", "legal", "uncertain"}:
            out[key] = "серая зона"
        elif "confirmed_zero" in types:
            out[key] = "подтверждённый ноль"
        else:
            out[key] = "объявленный пробел"
    return out


def composition(events: list[Event], agents: dict) -> str:
    """Состав набора по разрядам и состояниям единиц."""
    st = unit_status(events, agents)
    order = ["ядро", "серая зона", "подтверждённый ноль", "объявленный пробел"]
    counts = {k: sum(1 for v in st.values() if v == k) for k in order}
    total = len(st)
    lines = ["Состояние единиц кодирования"]
    for k in order:
        lines.append(f"  {k:22} {counts[k]:>4}  ({counts[k] / total * 100:.0f} %)")
    lines.append("")
    lines.append("Записи по разрядам")
    for t in EVENT_TYPES:
        n = sum(1 for e in events if e.event_type == t)
        if n:
            lines.append(f"  {t:16} {n:>4}")
    codeable = counts["ядро"] + counts["серая зона"] + counts["подтверждённый ноль"]
    lines.append("")
    lines.append(f"Кодированию подлежат {codeable} единиц из {total}, "
                 f"исключены {counts['объявленный пробел']}")
    return "\n".join(lines)


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
