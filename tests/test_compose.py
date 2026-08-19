"""
Проверки модуля свёртки.

Первая часть проверяет правила на построенных примерах, где ответ известен
заранее и вычисляется в уме. Вторая часть проверяет поведение на настоящих
данных репозитория.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from engine.measurement.compose import (
    DAMPER_LIMIT, baselines, compose_all, compose_var, coverage_report,
)
from engine.measurement.indicators import Var
from engine.measurement.loaders import load_agents, load_observations

ROOT = Path(__file__).resolve().parents[1]
AGENTS_CSV = ROOT / "data" / "agents.csv"
OBS_CSV = ROOT / "data" / "observations.csv"

HEAD_A = "code,name,adversary,guarantor,trust_type,note\n"
HEAD_O = "agent,year,key,value,source\n"

BASE_AGENTS = (HEAD_A +
               "jpn,Япония,chn,usa,treaty,x\n"
               "chn,КНР,usa,,guarantor,x\n"
               "usa,США,chn,,guarantor,x\n")


def _setup(tmp_path, obs_rows):
    a = tmp_path / "a.csv"
    a.write_text(BASE_AGENTS, encoding="utf-8")
    o = tmp_path / "o.csv"
    o.write_text(HEAD_O + obs_rows, encoding="utf-8")
    agents = load_agents(a)
    return agents, load_observations(o, agents)


# --- равные доли --------------------------------------------------------

def test_доля_считается_от_наблюдённых_а_не_предусмотренных(tmp_path):
    """
    У переменной эрозии три слагаемых показателя. При двух наблюдениях
    делить следует на два, а не на три, иначе пропуск занижал бы значение.
    """
    agents, obs = _setup(tmp_path,
                         "jpn,2014,ceiling,2,x\n"
                         "jpn,2014,categories,4,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2014, obs)
    # ceiling 2 из 4 разрядов с обращением даёт 1/3, categories 4 из 5 даёт 0,8
    assert t.value == pytest.approx((1 / 3 + 0.8) / 2)
    assert t.missing == ("commitments",)


def test_полное_отсутствие_наблюдений_даёт_пропуск(tmp_path):
    """Пропуск не подменяется нулём, поскольку ноль есть значение шкалы."""
    agents, obs = _setup(tmp_path, "jpn,2014,ceiling,2,x\n")
    t = compose_var(Var.THREAT, agents["jpn"], 2014, obs)
    assert math.isnan(t.value)


# --- доля в паре --------------------------------------------------------

def test_доля_противника_берётся_из_ряда_противника(tmp_path):
    """Первичный противник Японии есть КНР, отсюда и берётся вторая величина."""
    agents, obs = _setup(tmp_path,
                         "jpn,2020,milex,40,x\n"
                         "chn,2020,milex,160,x\n")
    t = compose_var(Var.THREAT, agents["jpn"], 2020, obs)
    assert t.parts["milex"][1] == pytest.approx(0.8)
    assert t.value == pytest.approx(0.8)


def test_отсутствие_ряда_противника_даёт_пропуск_показателя(tmp_path):
    agents, obs = _setup(tmp_path, "jpn,2020,milex,40,x\n")
    t = compose_var(Var.THREAT, agents["jpn"], 2020, obs)
    assert "milex" in t.missing


# --- множитель ----------------------------------------------------------

def test_несогласие_умножает_а_не_складывается(tmp_path):
    """
    При полном несогласии сумма уменьшается ровно на величину предела, и
    показатель в слагаемые не попадает.
    """
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,x\n"
                         "jpn,2013,categories,4,x\n"
                         "jpn,2013,commitments,0,x\n"
                         "jpn,2013,dissent,100,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2013, obs)
    plain = (1 / 3 + 0.8 + 0.0) / 3
    assert t.damper_factor == pytest.approx(1.0 - DAMPER_LIMIT)
    assert t.value == pytest.approx(plain * (1.0 - DAMPER_LIMIT))
    assert "dissent" not in t.parts


def test_нулевое_несогласие_не_меняет_суммы(tmp_path):
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,x\n"
                         "jpn,2013,categories,4,x\n"
                         "jpn,2013,commitments,0,x\n"
                         "jpn,2013,dissent,0,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2013, obs)
    assert t.damper_factor == pytest.approx(1.0)
    assert t.value == pytest.approx((1 / 3 + 0.8 + 0.0) / 3)


def test_отсутствие_несогласия_оставляет_сумму_без_множителя(tmp_path):
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,x\n"
                         "jpn,2013,categories,4,x\n"
                         "jpn,2013,commitments,0,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2013, obs)
    assert t.damper_factor == pytest.approx(1.0)


def test_у_агента_без_потолка_множителя_нет(tmp_path):
    """КНР правового потолка не имеет, следовательно и множителя тоже."""
    agents, obs = _setup(tmp_path,
                         "chn,2013,ceiling,0,x\n"
                         "chn,2013,categories,5,x\n"
                         "chn,2013,commitments,0,x\n")
    t = compose_var(Var.EROSION, agents["chn"], 2013, obs)
    assert t.damper_factor == pytest.approx(1.0)
    assert math.isnan(t.damper_raw)


# --- отклонение от собственного уровня ----------------------------------

def test_короткий_ряд_не_даёт_отклонения(tmp_path):
    """При ряде короче трёх наблюдений обычный уровень не определён."""
    agents, obs = _setup(tmp_path, "jpn,2014,exercises,10,x\n")
    assert baselines(obs, "jpn", "exercises") is None
    t = compose_var(Var.TRUST, agents["jpn"], 2014, obs)
    assert math.isnan(t.value)


def test_значение_равное_обычному_уровню_даёт_середину(tmp_path):
    rows = "".join(f"jpn,{y},exercises,{v},x\n"
                   for y, v in zip(range(2010, 2015), [8, 9, 10, 11, 12]))
    agents, obs = _setup(tmp_path, rows)
    b = baselines(obs, "jpn", "exercises")
    assert b.center == pytest.approx(10)
    t = compose_var(Var.TRUST, agents["jpn"], 2012, obs)
    assert t.parts["exercises"][1] == pytest.approx(0.5)


def test_ухудшение_относительно_привычного_снижает_доверие(tmp_path):
    rows = "".join(f"jpn,{y},exercises,{v},x\n"
                   for y, v in zip(range(2010, 2015), [8, 9, 10, 11, 12]))
    agents, obs = _setup(tmp_path, rows)
    low = compose_var(Var.TRUST, agents["jpn"], 2010, obs).value
    high = compose_var(Var.TRUST, agents["jpn"], 2014, obs).value
    assert low < 0.5 < high


# --- отчёт о происхождении ----------------------------------------------

def test_объяснение_содержит_все_составляющие(tmp_path):
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,x\n"
                         "jpn,2013,categories,4,x\n"
                         "jpn,2013,dissent,76.9,x\n")
    text = compose_var(Var.EROSION, agents["jpn"], 2013, obs).explain()
    assert "ceiling" in text and "categories" in text
    assert "множитель" in text
    assert "нет наблюдений" in text


# --- настоящие данные репозитория ---------------------------------------

@pytest.fixture(scope="module")
def real():
    agents = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, agents)
    return agents, obs


def test_восприятие_угрозы_японии_растёт_за_период(real):
    """
    Отношение потенциалов ухудшалось, следовательно доля противника росла.
    Значение получено из расходов, а не назначено.

    В 2001 году наблюдение одно, расходы, и переменная равна доле противника.
    В 2025 году наблюдений два, расходы и присутствие судов, вследствие чего
    переменная равна их среднему. Проверяется и то, и другое.
    """
    agents, obs = real
    early = compose_var(Var.THREAT, agents["jpn"], 2001, obs)
    late = compose_var(Var.THREAT, agents["jpn"], 2025, obs)

    assert set(early.parts) == {"milex"}
    assert early.value == pytest.approx(early.parts["milex"][1])
    assert 0.55 < early.value < 0.60

    assert set(late.parts) == {"milex", "incidents"}
    expected = (late.parts["milex"][1] + late.parts["incidents"][1]) / 2
    assert late.value == pytest.approx(expected)
    assert late.value > early.value


def test_эрозия_японии_растёт_ступенями(real):
    """Ступени соответствуют датированным решениям, а не подобранным толчкам."""
    agents, obs = real
    vals = {y: compose_var(Var.EROSION, agents["jpn"], y, obs).value
            for y in (2005, 2010, 2016, 2024)}
    assert vals[2005] < vals[2010] < vals[2016] < vals[2024]


def test_эрозия_японии_ниже_чем_у_агентов_без_потолка(real):
    """
    Япония начинает движение снизу, тогда как государства без потолка стоят
    в верхней части шкалы. Различие видно лишь при общей шкале.
    """
    agents, obs = real
    jpn = compose_var(Var.EROSION, agents["jpn"], 2005, obs).value
    chn = compose_var(Var.EROSION, agents["chn"], 2005, obs).value
    usa = compose_var(Var.EROSION, agents["usa"], 2005, obs).value
    assert jpn < chn
    assert jpn < usa


def test_у_кндр_восприятие_угрозы_не_вычисляется(real):
    """Сведений о её расходах в международных базах нет за все годы."""
    agents, obs = real
    t = compose_var(Var.THREAT, agents["prk"], 2015, obs)
    assert math.isnan(t.value)
    assert "milex" in t.missing


def test_доверие_пока_не_вычисляется_ни_у_кого(real):
    """Ряды учений и поставок ещё не выгружены, и модуль это показывает."""
    agents, obs = real
    for code in agents:
        t = compose_var(Var.TRUST, agents[code], 2015, obs)
        assert math.isnan(t.value)


def test_свёртка_всего_массива_воспроизводима(real):
    agents, obs = real
    years = range(2001, 2027)
    a = compose_all(agents, obs, years)
    b = compose_all(agents, obs, years)
    assert list(a) == list(b)
    for k in a:
        x, y = a[k].value, b[k].value
        assert (math.isnan(x) and math.isnan(y)) or x == y
