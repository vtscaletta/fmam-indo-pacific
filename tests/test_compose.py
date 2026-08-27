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
HEAD_O = "agent,year,key,value,quality,source\n"

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
                         "jpn,2014,ceiling,2,наблюдение,x\n"
                         "jpn,2014,categories,4,наблюдение,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2014, obs)
    # ceiling 2 из 4 разрядов с обращением даёт 1/3, categories 4 из 5 даёт 0,8
    assert t.value == pytest.approx((1 / 3 + 0.8) / 2)
    assert t.missing == ("commitments",)


def test_полное_отсутствие_наблюдений_даёт_пропуск(tmp_path):
    """Пропуск не подменяется нулём, поскольку ноль есть значение шкалы."""
    agents, obs = _setup(tmp_path, "jpn,2014,ceiling,2,наблюдение,x\n")
    t = compose_var(Var.THREAT, agents["jpn"], 2014, obs)
    assert math.isnan(t.value)


# --- доля в паре --------------------------------------------------------

def test_доля_противника_берётся_из_ряда_противника(tmp_path):
    """
    Первичный противник Японии есть КНР, отсюда и берётся вторая величина.
    Доля приводится отклонением от обычного уровня пары, вследствие чего
    для вычисления требуется ряд не короче трёх лет.
    """
    rows = "".join(
        f"jpn,{y},milex,40,наблюдение,x\nchn,{y},milex,{m},наблюдение,x\n"
        for y, m in zip(range(2010, 2016), [80, 100, 120, 140, 160, 180]))
    agents, obs = _setup(tmp_path, rows)
    early = compose_var(Var.THREAT, agents["jpn"], 2010, obs)
    late = compose_var(Var.THREAT, agents["jpn"], 2015, obs)
    # наблюдённая доля растёт вместе с расходами противника
    assert early.parts["milex"][0] == pytest.approx(80 / 120)
    assert late.parts["milex"][0] == pytest.approx(180 / 220)
    # приведённое значение растёт вместе с ней
    assert late.parts["milex"][1] > early.parts["milex"][1]


def test_отсутствие_ряда_противника_даёт_пропуск_показателя(tmp_path):
    agents, obs = _setup(tmp_path, "jpn,2020,milex,40,наблюдение,x\n")
    t = compose_var(Var.THREAT, agents["jpn"], 2020, obs)
    assert "milex" in t.missing


# --- множитель ----------------------------------------------------------

def test_несогласие_умножает_а_не_складывается(tmp_path):
    """
    При полном несогласии сумма уменьшается ровно на величину предела, и
    показатель в слагаемые не попадает.
    """
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,наблюдение,x\n"
                         "jpn,2013,categories,4,наблюдение,x\n"
                         "jpn,2013,commitments,0,наблюдение,x\n"
                         "jpn,2013,dissent,100,наблюдение,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2013, obs)
    plain = (1 / 3 + 0.8 + 0.0) / 3
    assert t.damper_factor == pytest.approx(1.0 - DAMPER_LIMIT)
    assert t.value == pytest.approx(plain * (1.0 - DAMPER_LIMIT))
    assert "dissent" not in t.parts


def test_нулевое_несогласие_не_меняет_суммы(tmp_path):
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,наблюдение,x\n"
                         "jpn,2013,categories,4,наблюдение,x\n"
                         "jpn,2013,commitments,0,наблюдение,x\n"
                         "jpn,2013,dissent,0,наблюдение,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2013, obs)
    assert t.damper_factor == pytest.approx(1.0)
    assert t.value == pytest.approx((1 / 3 + 0.8 + 0.0) / 3)


def test_отсутствие_несогласия_оставляет_сумму_без_множителя(tmp_path):
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,наблюдение,x\n"
                         "jpn,2013,categories,4,наблюдение,x\n"
                         "jpn,2013,commitments,0,наблюдение,x\n")
    t = compose_var(Var.EROSION, agents["jpn"], 2013, obs)
    assert t.damper_factor == pytest.approx(1.0)


def test_у_агента_без_потолка_множителя_нет(tmp_path):
    """КНР правового потолка не имеет, следовательно и множителя тоже."""
    agents, obs = _setup(tmp_path,
                         "chn,2013,ceiling,0,наблюдение,x\n"
                         "chn,2013,categories,5,наблюдение,x\n"
                         "chn,2013,commitments,0,наблюдение,x\n")
    t = compose_var(Var.EROSION, agents["chn"], 2013, obs)
    assert t.damper_factor == pytest.approx(1.0)
    assert math.isnan(t.damper_raw)


# --- отклонение от собственного уровня ----------------------------------

def test_короткий_ряд_не_даёт_отклонения(tmp_path):
    """При ряде короче трёх наблюдений обычный уровень не определён."""
    agents, obs = _setup(tmp_path, "jpn,2014,exercises,10,наблюдение,x\n")
    assert baselines(obs, "jpn", "exercises") is None
    t = compose_var(Var.TRUST, agents["jpn"], 2014, obs)
    assert math.isnan(t.value)


def test_значение_равное_обычному_уровню_даёт_середину(tmp_path):
    rows = "".join(f"jpn,{y},exercises,{v},наблюдение,x\n"
                   for y, v in zip(range(2010, 2015), [8, 9, 10, 11, 12]))
    agents, obs = _setup(tmp_path, rows)
    b = baselines(obs, "jpn", "exercises")
    assert b.center == pytest.approx(10)
    t = compose_var(Var.TRUST, agents["jpn"], 2012, obs)
    assert t.parts["exercises"][1] == pytest.approx(0.5)


def test_ухудшение_относительно_привычного_снижает_доверие(tmp_path):
    rows = "".join(f"jpn,{y},exercises,{v},наблюдение,x\n"
                   for y, v in zip(range(2010, 2015), [8, 9, 10, 11, 12]))
    agents, obs = _setup(tmp_path, rows)
    low = compose_var(Var.TRUST, agents["jpn"], 2010, obs).value
    high = compose_var(Var.TRUST, agents["jpn"], 2014, obs).value
    assert low < 0.5 < high


# --- отчёт о происхождении ----------------------------------------------

def test_объяснение_содержит_все_составляющие(tmp_path):
    agents, obs = _setup(tmp_path,
                         "jpn,2013,ceiling,2,наблюдение,x\n"
                         "jpn,2013,categories,4,наблюдение,x\n"
                         "jpn,2013,dissent,76.9,наблюдение,x\n")
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

    В обоих годах наблюдений два, доля расходов и уровень враждебности.
    Уровень за 2001 год взят из набора о милитаризованных спорах, за 2025
    год получен собственным кодированием по тем же правилам, поскольку
    набор завершается 2014 годом.
    """
    agents, obs = real
    early = compose_var(Var.THREAT, agents["jpn"], 2001, obs)
    late = compose_var(Var.THREAT, agents["jpn"], 2025, obs)

    assert set(early.parts) == {"milex", "incidents"}
    assert early.value == pytest.approx(
        sum(u for _, u in early.parts.values()) / 2)

    assert set(late.parts) == {"milex", "incidents"}
    assert late.parts["milex"][1] > early.parts["milex"][1]
    assert obs.quality_of("jpn", 2001, "incidents") == "наблюдение"
    assert obs.quality_of("jpn", 2025, "incidents") == "оценка"


def test_эрозия_японии_растёт_ступенями(real):
    """Ступени соответствуют датированным решениям, а не подобранным толчкам."""
    agents, obs = real
    vals = {y: compose_var(Var.EROSION, agents["jpn"], y, obs).value
            for y in (2005, 2010, 2016, 2024)}
    assert vals[2005] < vals[2010] < vals[2016] < vals[2024]


def test_эрозия_не_определена_у_агентов_без_потолка(real):
    """
    Переменная измеряет разрушение действующего ограничения. Государству,
    у которого ограничения не было, разрушать нечего, вследствие чего
    величина для него не определена и заглушкой не подменяется.
    """
    agents, obs = real
    for code in ("usa", "chn", "twn", "aus", "idn", "prk"):
        assert math.isnan(
            compose_var(Var.EROSION, agents[code], 2005, obs).value), code
    for code in ("jpn", "kor", "phl", "ind"):
        assert not math.isnan(
            compose_var(Var.EROSION, agents[code], 2005, obs).value), code


def test_у_кндр_угроза_держится_на_уровне_враждебности(real):
    """
    Сведений о расходах КНДР в международных базах нет за все годы, отчего
    доля пары не вычисляется. Переменная опирается на уровень враждебности,
    взятый из набора о милитаризованных спорах.
    """
    agents, obs = real
    t = compose_var(Var.THREAT, agents["prk"], 2010, obs)
    assert "milex" in t.missing
    assert set(t.parts) == {"incidents"}
    assert not math.isnan(t.value)


def test_доверие_вычисляется_по_выгруженным_рядам(real):
    """
    Доля гаранта в импорте вооружений выгружена по всем десяти агентам,
    совместные учения только по Республике Корея, отчего у неё переменная
    опирается на два показателя, а у прочих на один.
    """
    agents, obs = real
    kor = compose_var(Var.TRUST, agents["kor"], 2015, obs)
    assert set(kor.parts) == {"exercises", "arms_share"}
    jpn = compose_var(Var.TRUST, agents["jpn"], 2015, obs)
    assert set(jpn.parts) == {"arms_share"}
    assert not math.isnan(jpn.value)


def test_свёртка_всего_массива_воспроизводима(real):
    agents, obs = real
    years = range(2001, 2026)
    a = compose_all(agents, obs, years)
    b = compose_all(agents, obs, years)
    assert list(a) == list(b)
    for k in a:
        x, y = a[k].value, b[k].value
        assert (math.isnan(x) and math.isnan(y)) or x == y
