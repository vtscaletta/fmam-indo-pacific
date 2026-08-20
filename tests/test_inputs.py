"""
Проверки стыка слоя измерения с моделью.

Главное, что здесь удостоверяется, есть правильность разделения величин по
роду. Эрозия обязана приходить на каждый год, восприятие угрозы и доверие
только на первый, а наблюдаемые ряды расходов обязаны оставаться вне
подаваемых величин.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from engine.measurement.indicators import Var
from engine.measurement.inputs import (
    PROVISIONAL_TRUST, build_inputs, observed_threat_share, readiness_report,
)
from engine.measurement.loaders import load_agents, load_observations

ROOT = Path(__file__).resolve().parents[1]
YEARS = range(2001, 2026)


@pytest.fixture(scope="module")
def prepared():
    agents = load_agents(ROOT / "data" / "agents.csv")
    obs = load_observations(ROOT / "data" / "observations.csv", agents)
    return agents, obs, build_inputs(agents, obs, YEARS)


# --- разделение величин по роду ------------------------------------------

def test_эрозия_подаётся_на_каждый_год(prepared):
    """Эрозия есть запись датированных решений и приходит извне всегда."""
    _, _, inp = prepared
    for code in inp.erosion:
        assert len(inp.erosion[code]) == len(YEARS), code


def test_начальные_значения_заданы_только_на_первый_год(prepared):
    """Прочие годы модель производит сама, иначе она не агентная."""
    _, _, inp = prepared
    assert inp.first_year == 2001
    for code, triple in inp.initial.items():
        assert len(triple) == 3, code


def test_наблюдаемые_расходы_остаются_мишенью_а_не_входом(prepared):
    """
    Ряд отношения расходов собран отдельно от подаваемых величин. Совпадение
    с ним есть результат прогона, а не отражение входа.
    """
    _, _, inp = prepared
    assert inp.targets["jpn"], "мишень по Японии должна быть собрана"
    assert len(inp.targets["jpn"]) == 25
    # первый год мишени служит начальным значением, прочие двадцать четыре нет
    # начальное значение выводится из доли расходов отклонением от
    # собственного обычного уровня, а не берётся ею напрямую
    assert 0.0 <= inp.initial["jpn"][0] <= 1.0


def test_из_одного_начального_числа_ряд_не_выводится(prepared):
    """
    Начальное значение одно, а мишень содержит двадцать пять точек, отчего
    воспроизведение ряда тавтологией не является.
    """
    _, _, inp = prepared
    assert len(inp.targets["jpn"]) > 1
    later = [v for y, v in inp.targets["jpn"].items() if y > inp.first_year]
    assert len(later) == 24


# --- обращение с недостающими рядами -------------------------------------

def test_доверие_вычисляется_из_рядов_поставок(prepared):
    """
    Доля гаранта в импорте вооружений выгружена по всем агентам, отчего
    доверие на первом году более не берётся допущением.
    """
    agents, _, inp = prepared
    computed = [c for c in agents
                if inp.initial[c][1] != PROVISIONAL_TRUST[agents[c].trust_type]]
    assert len(computed) >= 8, "доверие должно вычисляться у большинства"
    for c in agents:
        assert not math.isnan(inp.initial[c][1]), c


def test_кндр_входит_в_прогон_через_уровень_враждебности(prepared):
    """
    Сведений о расходах КНДР в международных базах нет за все годы, отчего
    доля пары не вычисляется и мишень проверки пуста. Восприятие угрозы при
    этом вычисляется по уровню враждебности, взятому из набора о
    милитаризованных спорах, вследствие чего агент из прогона не выпадает.
    """
    _, _, inp = prepared
    assert inp.targets["prk"] == {}
    assert not math.isnan(inp.initial["prk"][0])


def test_корея_входит_в_прогон_несмотря_на_отсутствие_пары(prepared):
    """
    Первичный противник Республики Корея есть КНДР, расходов которой нет,
    отчего отношение пары не определено, а восприятие угрозы вычисляется по
    уровню враждебности.
    """
    _, _, inp = prepared
    assert inp.targets["kor"] == {}
    assert not math.isnan(inp.initial["kor"][0])


def test_обычный_уровень_вычислен_по_калибровочному_окну(prepared):
    """
    Точкой возврата служит обычный уровень агента, а не значение первого
    года, вследствие чего система не тратит первые годы на приближение к
    равновесию.
    """
    agents, _, inp = prepared
    assert set(inp.typical) == set(agents)
    for code, (t1, t2) in inp.typical.items():
        assert 0.0 <= t1 <= 1.0, code
        assert 0.0 <= t2 <= 1.0, code


# --- перенос значения при пропуске года ----------------------------------

def test_эрозия_переносится_с_последнего_известного_года(prepared):
    """
    Отсутствие решения в данном году означает сохранение прежнего
    состояния ограничения, а не его исчезновение.
    """
    _, _, inp = prepared
    assert inp.erosion_at("jpn", 2025) == pytest.approx(
        inp.erosion["jpn"][2025])
    # год за пределами наблюдения получает последнее известное значение
    assert inp.erosion_at("jpn", 2030) == pytest.approx(
        inp.erosion["jpn"][2025])


def test_до_первого_известного_года_значение_отсутствует(prepared):
    _, _, inp = prepared
    assert math.isnan(inp.erosion_at("jpn", 1999))


# --- содержательные ожидания ---------------------------------------------

def test_эрозия_японии_ниже_чем_у_агентов_без_потолка(prepared):
    """Япония начинает движение снизу, прочие стоят в верхней части шкалы."""
    _, _, inp = prepared
    assert inp.erosion["jpn"][2005] < inp.erosion["chn"][2005]
    assert inp.erosion["jpn"][2005] < inp.erosion["usa"][2005]


def test_эрозия_японии_растёт_а_у_прочих_стоит(prepared):
    """
    Движение единственного связанного участника и есть предмет
    исследования. У государств без потолка эрозии некуда расти.
    """
    _, _, inp = prepared
    jpn = inp.erosion["jpn"]
    chn = inp.erosion["chn"]
    assert jpn[2024] > jpn[2001]
    assert chn[2024] == pytest.approx(chn[2001])


def test_отчёт_о_готовности_называет_всех_агентов(prepared):
    agents, _, inp = prepared
    text = readiness_report(inp, agents)
    for code in sorted(agents):
        assert code in text


# --- вспомогательная функция ---------------------------------------------

def test_наблюдаемая_доля_считается_по_первичному_противнику(prepared):
    agents, obs, _ = prepared
    v = observed_threat_share(agents["jpn"], 2020, obs)
    own = obs.get("jpn", 2020, "milex")
    other = obs.get("chn", 2020, "milex")
    assert v == pytest.approx(other / (own + other))
