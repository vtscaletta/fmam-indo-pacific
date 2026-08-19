"""
Проверки модуля чтения данных.

Две части. Первая удостоверяет, что порча данных обнаруживается и
возбуждает ошибку, а не исправляется молча. Вторая удостоверяет, что
настоящие таблицы репозитория читаются и связны.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from engine.measurement.loaders import (
    DataError, YEAR_MAX, YEAR_MIN, load_agents, load_observations,
)

ROOT = Path(__file__).resolve().parents[1]
AGENTS_CSV = ROOT / "data" / "agents.csv"
OBS_CSV = ROOT / "data" / "observations.csv"

HEAD_A = "code,name,adversary,guarantor,trust_type,note\n"
HEAD_O = "agent,year,key,value,quality,source\n"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def agents(tmp_path):
    p = _write(tmp_path, "a.csv", HEAD_A +
               "jpn,Япония,chn,usa,treaty,примечание\n"
               "chn,КНР,usa,,guarantor,примечание\n"
               "usa,США,chn,,guarantor,примечание\n")
    return load_agents(p)


# --- обнаружение порчи в паспортах --------------------------------------

def test_повтор_кода_агента_есть_ошибка(tmp_path):
    p = _write(tmp_path, "a.csv", HEAD_A +
               "jpn,Япония,chn,,treaty,x\njpn,Япония,chn,,treaty,x\n")
    with pytest.raises(DataError, match="повторяется"):
        load_agents(p)


def test_неизвестный_тип_опоры_есть_ошибка(tmp_path):
    p = _write(tmp_path, "a.csv", HEAD_A + "jpn,Япония,chn,,союз,x\n")
    with pytest.raises(DataError, match="тип опоры"):
        load_agents(p)


def test_противник_вне_перечня_участников_есть_ошибка(tmp_path):
    p = _write(tmp_path, "a.csv", HEAD_A + "jpn,Япония,rus,,treaty,x\n")
    with pytest.raises(DataError, match="противник"):
        load_agents(p)


def test_агент_не_может_быть_противником_самому_себе(tmp_path):
    p = _write(tmp_path, "a.csv", HEAD_A + "jpn,Япония,jpn,,treaty,x\n")
    with pytest.raises(DataError, match="самому себе"):
        load_agents(p)


def test_отсутствие_столбца_есть_ошибка(tmp_path):
    p = _write(tmp_path, "a.csv", "code,name\njpn,Япония\n")
    with pytest.raises(DataError, match="отсутствуют столбцы"):
        load_agents(p)


# --- обнаружение порчи в наблюдениях ------------------------------------

def test_неизвестный_агент_есть_ошибка(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O + "rus,2010,milex,50,наблюдение,SIPRI\n")
    with pytest.raises(DataError, match="неизвестный агент"):
        load_observations(p, agents)


def test_показатель_вне_реестра_есть_ошибка(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O + "jpn,2010,мощь,50,наблюдение,x\n")
    with pytest.raises(DataError, match="не объявлен"):
        load_observations(p, agents)


def test_показатель_неприменимый_к_агенту_есть_ошибка(tmp_path, agents):
    """Аффективный показатель существует только для Японии."""
    p = _write(tmp_path, "o.csv", HEAD_O + "chn,2010,affinity,30,наблюдение,x\n")
    with pytest.raises(DataError, match="не применяется"):
        load_observations(p, agents)


def test_год_вне_периода_есть_ошибка(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O + f"jpn,{YEAR_MIN - 1},milex,50,наблюдение,x\n")
    with pytest.raises(DataError, match="вне периода"):
        load_observations(p, agents)


def test_пустое_значение_есть_ошибка(tmp_path, agents):
    """Отсутствие наблюдения обозначается отсутствием строки."""
    p = _write(tmp_path, "o.csv", HEAD_O + "jpn,2010,milex,,наблюдение,x\n")
    with pytest.raises(DataError, match="пустое значение"):
        load_observations(p, agents)


def test_повтор_наблюдения_есть_ошибка(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O +
               "jpn,2010,milex,50,наблюдение,x\n"
               "jpn,2010,milex,51,наблюдение,x\n")
    with pytest.raises(DataError, match="дважды"):
        load_observations(p, agents)


def test_нечисловое_значение_есть_ошибка(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O + "jpn,2010,milex,много,наблюдение,x\n")
    with pytest.raises(DataError, match="не число"):
        load_observations(p, agents)


# --- поведение при отсутствии наблюдения --------------------------------

def test_отсутствующее_наблюдение_возвращается_как_пропуск(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O + "jpn,2010,milex,50,наблюдение,x\n")
    obs = load_observations(p, agents)
    assert obs.get("jpn", 2010, "milex") == 50.0
    assert math.isnan(obs.get("jpn", 2011, "milex"))
    assert math.isnan(obs.get("chn", 2010, "milex"))


def test_ряд_по_годам_упорядочен(tmp_path, agents):
    p = _write(tmp_path, "o.csv", HEAD_O +
               "jpn,2012,milex,52,наблюдение,x\n"
               "jpn,2010,milex,50,наблюдение,x\n"
               "jpn,2011,milex,51,наблюдение,x\n")
    obs = load_observations(p, agents)
    assert obs.years("jpn", "milex") == [2010, 2011, 2012]
    assert list(obs.series("jpn", "milex").values()) == [50.0, 51.0, 52.0]


# --- настоящие таблицы репозитория --------------------------------------

def test_таблицы_репозитория_читаются_и_связны():
    ag = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, ag)
    assert len(ag) == 10, "участников должно быть десять"
    assert set(ag) == {"usa", "chn", "jpn", "twn", "kor",
                       "prk", "ind", "aus", "phl", "idn"}
    assert len(obs.values) > 1000


def test_расходы_выгружены_по_девяти_агентам_из_десяти():
    """КНДР в базе SIPRI отсутствует за все годы наблюдения."""
    ag = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, ag)
    with_milex = [c for c in ag if obs.years(c, "milex")]
    assert len(with_milex) == 9
    assert "prk" not in with_milex


def test_ступень_потолка_японии_меняется_в_2013_году():
    """Переход связан с кадровым решением, а не с изменением нормы."""
    ag = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, ag)
    assert obs.get("jpn", 2012, "ceiling") == 3
    assert obs.get("jpn", 2013, "ceiling") == 2
    assert obs.get("jpn", 2025, "ceiling") == 2


def test_снятые_запреты_японии_растут_ступенями():
    ag = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, ag)
    assert obs.get("jpn", 2001, "categories") == 1
    assert obs.get("jpn", 2008, "categories") == 2
    assert obs.get("jpn", 2014, "categories") == 4
    assert obs.get("jpn", 2022, "categories") == 5


def test_у_каждого_наблюдения_указан_источник():
    ag = load_agents(AGENTS_CSV)
    obs = load_observations(OBS_CSV, ag)
    for cell in obs.values:
        assert obs.sources[cell].strip(), f"без источника, {cell}"
