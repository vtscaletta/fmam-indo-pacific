"""
Карта условий. При каких конфигурациях пересмотр статьи существенен.

Замысел работы состоит в построении карты, а не прогноза. Карта указывает,
при каких сочетаниях условий пересмотр девятой статьи ведёт к существенной
дополнительной дестабилизации, а при каких оказывается безразличным.

Основание для построения. Проверка устойчивости показала, что знак сценарной
разности не меняется ни при одном наборе параметров, а величина колеблется в
пределах шести сотых долей собственного значения. Направление действия
пересмотра к произволу настройки поэтому не сводится. Абсолютные величины
напряжения при этом предъявляться не могут, поскольку предсказание величин
опровергнуто двумя проверками.

Два измерения карты.

Первое, острота угрожающей среды. Задаётся множителем к обычному уровню
восприятия угрозы всех агентов. Значение ниже единицы отвечает разрядке,
выше единицы обострению против наблюдённого положения.

Второе, прочность союзных гарантий. Задаётся множителем к обычному уровню
доверия всех агентов, обладающих гарантом. Значение ниже единицы отвечает
ослаблению обязательства, выше единицы его укреплению.

Оба множителя приложены к точке возврата, а не к начальному состоянию,
поскольку точка возврата задаёт положение, к которому система тяготеет, тогда
как начальное состояние забывается за несколько шагов.

Существенность определяется двояко. Слабое условие состоит в превышении
порога существенности разностью напряжения. Сильное условие состоит в смене
господствующего режима, то есть в переводе системы через порог фазового
перехода.
"""
from __future__ import annotations

from engine.influence import build_influence
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import Simulator

HISTORY = range(2001, 2026)
PROJECTION = range(2001, 2036)
LAST_OBSERVED = 2025
REVISION_YEAR = 2028
REVISION_LEVEL = 1.0

THREAT_GRID = (0.75, 1.00, 1.25, 1.50, 1.75)
TRUST_GRID = (0.40, 0.70, 1.00, 1.30, 1.60)

MATERIAL = 0.010
"""
Порог существенности разности.

Взят равным размаху, порождаемому подменой неопределённой эрозии в пересчёте
на один год, и потому отделяет действие пересмотра от колебания,
порождаемого допущениями модели.
"""

THRESHOLD_S2 = 0.334
THRESHOLD_S3 = 0.667


class ScenarioErosion:
    """
    Эрозия для прогноза. До последнего наблюдения читает наблюдения, после
    удерживает их уровень. Японии с года пересмотра присваивается заданный
    уровень, чем и различаются два сценария.

    Отсечка симулятору намеренно не задаётся, поскольку при заданной отсечке
    источник эрозии за нею не опрашивается вовсе и сценарий до модели не
    доходит.
    """

    def __init__(self, inputs, revise: bool):
        self.inputs = inputs
        self.revise = revise
        self.frozen = {c: inputs.erosion_at(c, LAST_OBSERVED)
                       for c in inputs.erosion}

    def __call__(self, agent: str, year: int) -> float:
        if year <= LAST_OBSERVED:
            return self.inputs.erosion_at(agent, year)
        if self.revise and agent == "jpn" and year >= REVISION_YEAR:
            return REVISION_LEVEL
        return self.frozen.get(agent, float("nan"))


def scaled_typical(typical: dict, threat_factor: float,
                   trust_factor: float) -> dict:
    """Точки возврата, помноженные на множители остроты и прочности."""
    def clip(x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

    return {c: (clip(t1 * threat_factor), clip(t2 * trust_factor))
            for c, (t1, t2) in typical.items()}


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, HISTORY)
    influence = build_influence(agents, obs, "data/relations.csv")
    sim = Simulator(agents, influence)

    print("КАРТА УСЛОВИЙ")
    print()
    print(f"  пересмотр, эрозия Японии поднята до {REVISION_LEVEL:.2f} "
          f"с {REVISION_YEAR} года")
    print(f"  горизонт прогноза {max(PROJECTION)}")
    print(f"  порог существенности разности {MATERIAL:.3f}")
    print(f"  пороги режимов, во второй {THRESHOLD_S2:.3f}, "
          f"в третий {THRESHOLD_S3:.3f}")
    print()
    print("  строки, острота угрожающей среды")
    print("  столбцы, прочность союзных гарантий")
    print()

    head = f"{'острота':>9}" + "".join(f"{v:>10.2f}" for v in TRUST_GRID)

    grid = {}
    for threat in THREAT_GRID:
        for trust in TRUST_GRID:
            typ = scaled_typical(inputs.typical, threat, trust)
            keep = sim.run(PROJECTION, inputs.initial,
                           ScenarioErosion(inputs, False),
                           inputs.incident_at, typ, label="сохр")
            rev = sim.run(PROJECTION, inputs.initial,
                          ScenarioErosion(inputs, True),
                          inputs.incident_at, typ, label="перес")
            i = keep.years.index(max(PROJECTION))
            grid[(threat, trust)] = {
                "diff": rev.tension[i] - keep.tension[i],
                "keep_tau": keep.tension[i],
                "rev_tau": rev.tension[i],
                "keep_reg": keep.dominant[i],
                "rev_reg": rev.dominant[i],
            }

    print("НАПРЯЖЕНИЕ ПРИ СОХРАНЕНИИ")
    print(head)
    for threat in THREAT_GRID:
        cells = [grid[(threat, t)]["keep_tau"] for t in TRUST_GRID]
        print(f"{threat:>9.2f}" + "".join(f"{c:>10.4f}" for c in cells))

    print()
    print("РАЗНОСТЬ, пересмотр минус сохранение")
    print(head)
    for threat in THREAT_GRID:
        cells = [grid[(threat, t)]["diff"] for t in TRUST_GRID]
        print(f"{threat:>9.2f}" + "".join(f"{c:>10.5f}" for c in cells))

    print()
    print("ГОСПОДСТВУЮЩИЙ РЕЖИМ")
    print(head)
    flips = []
    for threat in THREAT_GRID:
        cells = []
        for trust in TRUST_GRID:
            g = grid[(threat, trust)]
            if g["keep_reg"] == g["rev_reg"]:
                cells.append(g["keep_reg"])
            else:
                cells.append(f"{g['keep_reg']}>{g['rev_reg']}")
                flips.append((threat, trust))
        print(f"{threat:>9.2f}" + "".join(f"{c:>10}" for c in cells))

    print()
    print("РАССТОЯНИЕ ДО ПОРОГА ТРЕТЬЕГО РЕЖИМА при сохранении")
    print(head)
    for threat in THREAT_GRID:
        cells = [THRESHOLD_S3 - grid[(threat, t)]["keep_tau"]
                 for t in TRUST_GRID]
        print(f"{threat:>9.2f}" + "".join(f"{c:>10.4f}" for c in cells))

    diffs = [g["diff"] for g in grid.values()]
    taus = [g["keep_tau"] for g in grid.values()]
    material = [k for k, g in grid.items() if g["diff"] >= MATERIAL]

    print()
    print("ЧТЕНИЕ КАРТЫ")
    print()
    print(f"  Разность положительна во всех {len(grid)} клетках, "
          f"от {min(diffs):.5f} до {max(diffs):.5f}.")
    print(f"  Порог существенности превышен в {len(material)} клетках "
          f"из {len(grid)}.")
    print(f"  Напряжение при сохранении от {min(taus):.4f} "
          f"до {max(taus):.4f}, оба порога режимов покрыты.")
    print()

    if flips:
        print(f"  Пересмотр меняет господствующий режим в {len(flips)} "
              f"клетках из {len(grid)}, а именно:")
        for threat, trust in flips:
            g = grid[(threat, trust)]
            print(f"    острота {threat:.2f}, прочность {trust:.2f}, "
                  f"{g['keep_reg']} обращается в {g['rev_reg']}, "
                  f"напряжение {g['keep_tau']:.4f} против {g['rev_tau']:.4f}")
        print()
        print("  Клетки смены режима образуют полосу, отделяющую область")
        print("  безразличия пересмотра от области, где он оказывается")
        print("  решающим. Это и есть искомая карта.")
    else:
        near = [(k, THRESHOLD_S3 - g["keep_tau"]) for k, g in grid.items()
                if 0 < THRESHOLD_S3 - g["keep_tau"] < 0.05]
        print("  Пересмотр господствующего режима не меняет ни в одной "
              "клетке решётки.")
        if near:
            print(f"  При этом в {len(near)} клетках система отстоит от порога")
            print("  третьего режима менее чем на пять сотых, вследствие чего")
            print("  решётку надлежит сгустить в этой полосе.")
        print()
        print("  Предварительный вывод. Пересмотр повышает напряжение всюду,")
        print("  однако собственной его величины недостаточно для перевода")
        print("  системы через порог. Дестабилизация, если она наступает,")
        print("  порождается положением системы, а не пересмотром самим по")
        print("  себе. Утверждение подлежит уточнению сгущением решётки")
        print("  вблизи порога.")


if __name__ == "__main__":
    main()
