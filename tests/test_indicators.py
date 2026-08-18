"""
Проверки реестра индикаторов.

Реестр не вычисляет по данным, вследствие чего проверки удостоверяют его
внутреннюю связность, а именно полноту описания каждого показателя,
правильность применимости к агентам и отсутствие противоречий в составе
переменных.
"""
from __future__ import annotations

import pytest

from engine.measurement.indicators import (
    ALL, BY_KEY, REGISTRY, Indicator, Kind, Role, Var,
    additive, damper, describe, for_var,
)


# --- полнота описания ---------------------------------------------------

def test_у_каждого_показателя_есть_название_и_источник():
    """Показатель без источника непроверяем и в реестре недопустим."""
    for ind in REGISTRY:
        assert ind.title.strip(), f"{ind.key} без названия"
        assert ind.source.strip(), f"{ind.key} без источника"


def test_реперы_заданы_там_где_правило_их_требует():
    """Линейное приведение без реперов не определено."""
    for ind in REGISTRY:
        if ind.kind is Kind.LINEAR:
            assert ind.low is not None and ind.high is not None, ind.key
            assert ind.low != ind.high, ind.key
        if ind.kind is Kind.ORDINAL:
            assert ind.n_steps and ind.n_steps >= 2, ind.key
        if ind.kind is Kind.COUNT:
            assert ind.total and ind.total > 0, ind.key
        if ind.kind is Kind.SHARE:
            assert ind.pair_key, ind.key


def test_ключи_показателей_не_повторяются():
    """Повтор ключа означал бы, что один ряд читается дважды."""
    keys = [i.key for i in REGISTRY]
    assert len(keys) == len(set(keys))
    assert len(BY_KEY) == len(REGISTRY)


# --- состав переменных --------------------------------------------------

def test_состав_переменных_для_японии():
    """У Японии применимы все показатели, включая аффективный."""
    assert [i.key for i in for_var(Var.THREAT, "jpn")] == [
        "milex", "incidents", "affinity"]
    assert [i.key for i in for_var(Var.TRUST, "jpn")] == [
        "exercises", "arms_share"]
    assert [i.key for i in for_var(Var.EROSION, "jpn")] == [
        "ceiling", "categories", "commitments", "dissent"]


def test_аффективный_показатель_только_у_японии():
    """Сопоставимых непрерывных рядов по прочим агентам не существует."""
    assert "affinity" in [i.key for i in for_var(Var.THREAT, "jpn")]
    for code in ("usa", "chn", "twn", "kor", "ind", "aus", "phl", "idn", "prk"):
        assert "affinity" not in [i.key for i in for_var(Var.THREAT, code)]


def test_несогласие_аудитории_только_у_агентов_с_потолком():
    """Показатель применяется там, где есть что защищать несогласием."""
    with_ceiling = ("jpn", "kor", "phl", "ind")
    without = ("usa", "chn", "twn", "aus", "idn", "prk")
    for code in with_ceiling:
        assert damper(Var.EROSION, code) is not None, code
    for code in without:
        assert damper(Var.EROSION, code) is None, code


def test_у_переменной_не_более_одного_множителя():
    """Два множителя означали бы двойное умножение результата."""
    for code in ("jpn", "kor", "usa"):
        for var in Var:
            damper(var, code)  # бросит ValueError при нарушении


def test_множитель_не_попадает_в_слагаемые():
    """Несогласие аудитории не складывается с прочими показателями."""
    keys = [i.key for i in additive(Var.EROSION, "jpn")]
    assert "dissent" not in keys
    assert keys == ["ceiling", "categories", "commitments"]


# --- направления шкал ---------------------------------------------------

def test_близость_к_противнику_измеряется_обращённо():
    """Чем ближе население к противнику, тем ниже восприятие угрозы."""
    ind = BY_KEY["affinity"]
    assert ind.low > ind.high


def test_ступень_потолка_обращена():
    """Крепкий потолок означает малую эрозию."""
    ind = BY_KEY["ceiling"]
    assert ind.kind is Kind.ORDINAL
    assert ind.inverted is True
    assert ind.n_steps == 4


def test_перечень_запретов_закрыт_и_равен_пяти():
    """Пять запретов, каждый установлен датированным актом."""
    assert BY_KEY["categories"].total == 5.0


def test_обязательства_нормируются_числом_прочих_агентов():
    """Девять прочих участников системы образуют предел показателя."""
    assert BY_KEY["commitments"].total == 9.0


# --- снятый показатель ---------------------------------------------------

def test_командные_структуры_в_реестре_отсутствуют():
    """
    Показатель снят, поскольку не даёт годового ряда, не сопоставим между
    агентами и движется вместе с числом совместных учений.
    """
    assert "command" not in BY_KEY
    assert len(for_var(Var.TRUST, "jpn")) == 2


# --- печатное описание ---------------------------------------------------

def test_описание_содержит_все_показатели():
    """Описание идёт в приложение и обязано быть полным."""
    text = describe()
    for ind in REGISTRY:
        assert ind.key in text
        assert ind.title in text
