"""
Проверки матрицы влияния.

Главное, что здесь удостоверяется, есть отсутствие назначенных величин.
Всякий вес обязан выводиться из разряда отношения и мощи источника, причём
разряд берётся из таблицы фактов, а мощь из наблюдаемого ряда.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from engine.influence import (
    POWER_FLOOR, RELATION_KINDS, build_influence, load_relations,
)
from engine.measurement.loaders import DataError, load_agents, load_observations

ROOT = Path(__file__).resolve().parents[1]
AGENTS_CSV = ROOT / "data" / "agents.csv"
OBS_CSV = ROOT / "data" / "observations.csv"
REL_CSV = ROOT / "data" / "relations.csv"


@pytest.fixture(scope="module")
def matrix():
    agents = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, agents)
    return build_influence(agents, obs, REL_CSV)


# --- таблица отношений ---------------------------------------------------

def test_отношения_покрывают_все_упорядоченные_пары():
    """Десять агентов дают девяносто упорядоченных пар."""
    rel = load_relations(REL_CSV)
    assert len(rel) == 90


def test_всякое_отнесение_имеет_основание():
    """Пара без основания отнесения непроверяема и недопустима."""
    rel = load_relations(REL_CSV)
    for r in rel.values():
        assert r.note.strip(), (r.source, r.target)
        assert r.kind in RELATION_KINDS


def test_неизвестный_разряд_есть_ошибка(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("source,target,kind,note\njpn,chn,вражда,x\n", encoding="utf-8")
    with pytest.raises(DataError, match="разряд"):
        load_relations(p)


def test_отнесение_без_основания_есть_ошибка(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("source,target,kind,note\njpn,chn,dispute,\n", encoding="utf-8")
    with pytest.raises(DataError, match="без основания"):
        load_relations(p)


def test_пара_из_одного_агента_есть_ошибка(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("source,target,kind,note\njpn,jpn,contact,x\n", encoding="utf-8")
    with pytest.raises(DataError, match="из одного агента"):
        load_relations(p)


# --- разряды и их приведение ---------------------------------------------

def test_разряды_приводятся_равноотстоящими_значениями(matrix):
    """Четыре разряда дают ноль, треть, две трети и единицу."""
    seen = {matrix.relation_weight(i, j)
            for i in matrix.codes for j in matrix.codes if i != j}
    for v in seen:
        assert any(math.isclose(v, x) for x in (0.0, 1/3, 2/3, 1.0)), v


def test_первичный_противник_повышает_разряд_на_ступень(matrix):
    """
    Для Японии первичным противником назван КНР. Пара имеет спор об
    островах Сэнкаку, то есть второй разряд, и повышается до третьего.
    """
    assert matrix.relation_level("chn", "jpn") == 3
    # обратное направление остаётся вторым, поскольку у КНР иной противник
    assert matrix.relation_level("jpn", "chn") == 2


def test_разряд_выше_высшего_не_поднимается(matrix):
    """Взаимное оспаривание государственности уже есть высший разряд."""
    assert matrix.relation_level("prk", "kor") == 3
    assert matrix.relation_level("chn", "twn") == 3


def test_отсутствие_соприкосновения_даёт_нулевой_вес(matrix):
    """Индия и КНДР прямого соприкосновения не имеют."""
    assert matrix.relation_weight("ind", "prk") == 0.0
    assert matrix.weights(2020)["ind"]["prk"] == 0.0


def test_агент_на_себя_не_влияет(matrix):
    for y in (2001, 2015, 2025):
        for c in matrix.codes:
            assert matrix.weights(y)[c][c] == 0.0


# --- мощь источника ------------------------------------------------------

def test_мощь_лежит_между_нижней_границей_и_единицей(matrix):
    for y in (2001, 2015, 2025):
        for c in matrix.codes:
            p = matrix.power(c, y)
            assert POWER_FLOOR <= p <= 1.0, (c, y, p)


def test_сильнейший_агент_получает_единицу(matrix):
    """Мощь берётся долей от наибольшей в системе того же года."""
    for y in (2001, 2015, 2022):
        vals = {c: matrix.power(c, y) for c in matrix.codes}
        assert math.isclose(max(vals.values()), 1.0)


def test_мощь_меняется_по_годам(matrix):
    """
    Индекс взят годовым рядом, а не замороженным числом, вследствие чего
    ослабление одних участников относительно прочих отражается в весах.
    """
    early = matrix.power("usa", 2001)
    late = matrix.power("usa", 2022)
    assert early != late
    assert early > late


def test_веса_меняются_по_годам(matrix):
    """Изменение мощи обязано сказаться на весах влияния."""
    w1 = matrix.weights(2001)["usa"]["jpn"]
    w2 = matrix.weights(2022)["usa"]["jpn"]
    assert w1 != w2


# --- передаточные функции -------------------------------------------------

def test_главный_источник_угрозы_для_японии_есть_кнр(matrix):
    assert matrix.main_source("jpn", 2025) == "chn"


def test_главный_источник_угрозы_для_кндр_есть_республика_корея(matrix):
    """
    Взаимное оспаривание государственности даёт высший разряд отношения,
    вследствие чего Республика Корея опережает Соединённые Штаты несмотря
    на их большую мощь. Вклад Соединённых Штатов при этом остаётся
    значительным.
    """
    contrib = dict(matrix.contribution("prk", 2025))
    assert matrix.main_source("prk", 2025) == "kor"
    assert contrib["kor"] > contrib["usa"] > 0.15


def test_агент_без_гаранта_не_меняет_доверия(matrix):
    """Индия и Индонезия выбор стороны не производят, доверять им некому."""
    actions = {c: {"milex": 0.6, "rhet": 0.6, "drift": 0.5}
               for c in matrix.codes}
    d = matrix.trust_delta(actions, 2025)
    assert d["ind"] == 0.0
    assert d["idn"] == 0.0
    assert d["usa"] == 0.0


def test_рост_риторики_противника_понижает_доверие(matrix):
    """Страх оставления растёт при усилении главного источника угрозы."""
    quiet = {c: {"milex": 0.5, "rhet": 0.1, "drift": 0.5} for c in matrix.codes}
    loud = {c: {"milex": 0.5, "rhet": 0.9, "drift": 0.5} for c in matrix.codes}
    assert matrix.trust_delta(loud, 2025)["jpn"] < \
           matrix.trust_delta(quiet, 2025)["jpn"] < 0


def test_рост_расходов_повышает_угрозу_у_соседей(matrix):
    low = {c: {"milex": 0.1, "rhet": 0.5, "drift": 0.5} for c in matrix.codes}
    high = {c: {"milex": 0.9, "rhet": 0.5, "drift": 0.5} for c in matrix.codes}
    assert matrix.threat_delta(high, 2025)["jpn"] > \
           matrix.threat_delta(low, 2025)["jpn"] > 0


# --- отчёт о вкладе ------------------------------------------------------

def test_вклады_в_сумме_дают_единицу(matrix):
    for target in ("jpn", "idn", "twn"):
        total = sum(v for _, v in matrix.contribution(target, 2025))
        assert math.isclose(total, 1.0, rel_tol=1e-9)


def test_наибольший_вклад_в_давление_на_японию_даёт_кнр(matrix):
    first, share = matrix.contribution("jpn", 2025)[0]
    assert first == "chn"
    assert share > 0.3


def test_малый_вклад_остаётся_величиной_а_не_умолчанием(matrix):
    """
    Участник, чей вклад невелик, назван с указанием доли. Утверждение о
    слабом участии есть содержательный результат, а не пропуск.
    """
    contrib = dict(matrix.contribution("jpn", 2025))
    assert "aus" in contrib
    assert 0.0 < contrib["aus"] < 0.10


def test_описание_матрицы_содержит_всех_агентов(matrix):
    text = matrix.describe(2025)
    for c in matrix.codes:
        assert c in text
