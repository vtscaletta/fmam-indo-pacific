"""
Проверки модуля шкал.

Каждая проверка отвечает на один вопрос и снабжена пояснением, что именно
она удостоверяет. Проверки запускаются командой python -m pytest tests.
"""
from __future__ import annotations

import math
import pytest

from engine.measurement import scales as s


# --- отсутствие наблюдения --------------------------------------------

def test_пропуск_распространяется_а_не_подменяется_нулём():
    """Отсутствие наблюдения обязано остаться отсутствием на выходе."""
    assert math.isnan(s.linear(None, 0, 365))
    assert math.isnan(s.share(None, 10))
    assert math.isnan(s.count_of(None, 5))
    assert math.isnan(s.invert(None))
    assert math.isnan(s.ordinal(None, 4))


# --- линейное приведение ----------------------------------------------

def test_линейное_приведение_по_реперам():
    """Нижний репер даёт ноль, верхний единицу, середина половину."""
    assert s.linear(0, 0, 365) == 0.0
    assert s.linear(365, 0, 365) == 1.0
    assert s.linear(182.5, 0, 365) == pytest.approx(0.5)


def test_выход_за_репер_прижимается_к_границе():
    """Превышение предела означает достижение предела, а не выход за смысл."""
    assert s.linear(400, 0, 365) == 1.0
    assert s.linear(-5, 0, 365) == 0.0


def test_обращённая_шкала_через_порядок_реперов():
    """Близость к противнику измеряется в обратную сторону."""
    assert s.linear(100, 100, 0) == 0.0
    assert s.linear(0, 100, 0) == 1.0
    assert s.linear(25, 100, 0) == pytest.approx(0.75)


def test_совпадение_реперов_есть_ошибка():
    """Шкала нулевой длины не определена и молча нулём не подменяется."""
    with pytest.raises(ValueError):
        s.linear(1, 5, 5)


# --- доля в паре -------------------------------------------------------

def test_паритет_даёт_половину():
    """Равенство величин есть середина шкалы по построению."""
    assert s.share(50, 50) == pytest.approx(0.5)


def test_усиление_противника_растит_показатель():
    """Показатель растёт при усилении второй стороны."""
    assert s.share(10, 90) == pytest.approx(0.9)
    assert s.share(90, 10) == pytest.approx(0.1)


def test_нулевая_сумма_есть_отсутствие_измерения():
    """При нулевой сумме соотношение не определено."""
    assert math.isnan(s.share(0, 0))


# --- порядковые разряды -------------------------------------------------

def test_четыре_разряда_дают_равные_промежутки():
    """При четырёх разрядах промежутков три, каждый равен трети."""
    assert s.ordinal(0, 4) == pytest.approx(0.0)
    assert s.ordinal(1, 4) == pytest.approx(1 / 3)
    assert s.ordinal(2, 4) == pytest.approx(2 / 3)
    assert s.ordinal(3, 4) == pytest.approx(1.0)


def test_три_разряда_дают_ноль_половину_единицу():
    """Общее правило проверяется на ином числе разрядов."""
    assert s.ordinal(0, 3) == pytest.approx(0.0)
    assert s.ordinal(1, 3) == pytest.approx(0.5)
    assert s.ordinal(2, 3) == pytest.approx(1.0)


def test_обращение_разрядов():
    """Крепкий потолок означает малую эрозию, отсюда обращение."""
    assert s.ordinal(3, 4, inverted=True) == pytest.approx(0.0)
    assert s.ordinal(0, 4, inverted=True) == pytest.approx(1.0)


def test_разряд_вне_диапазона_есть_ошибка():
    """Молчаливое прижатие скрыло бы ошибку в данных."""
    with pytest.raises(ValueError):
        s.ordinal(4, 4)
    with pytest.raises(ValueError):
        s.ordinal(-1, 4)


# --- доля от закрытого перечня -----------------------------------------

def test_доля_от_перечня():
    """Два снятых запрета из пяти дают четыре десятых."""
    assert s.count_of(2, 5) == pytest.approx(0.4)
    assert s.count_of(5, 5) == pytest.approx(1.0)


def test_пустой_перечень_есть_ошибка():
    with pytest.raises(ValueError):
        s.count_of(1, 0)


# --- отклонение от собственного уровня ----------------------------------

def test_привычное_положение_даёт_середину():
    """Значение, равное обычному уровню агента, есть середина шкалы."""
    assert s.deviation_from_baseline(10, 10, 2) == pytest.approx(0.5)


def test_ухудшение_относительно_привычного_снижает_показатель():
    """Положение хуже привычного даёт значение ниже середины."""
    assert s.deviation_from_baseline(8, 10, 2) < 0.5
    assert s.deviation_from_baseline(12, 10, 2) > 0.5


def test_нулевой_разброс_даёт_середину():
    """При неизменном ряде отклонения не существует."""
    assert s.deviation_from_baseline(10, 10, 0) == pytest.approx(0.5)


def test_шкала_отклонения_не_выходит_за_отрезок():
    """Крайние отклонения прижимаются к границам отрезка."""
    assert s.deviation_from_baseline(-100, 10, 2) == pytest.approx(0.0)
    assert s.deviation_from_baseline(100, 10, 2) == pytest.approx(1.0)


# --- обращение ----------------------------------------------------------

def test_обращение_приведённого_значения():
    assert s.invert(0.3) == pytest.approx(0.7)
    assert s.invert(0.0) == pytest.approx(1.0)
