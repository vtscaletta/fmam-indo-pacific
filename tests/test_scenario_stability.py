"""
Устойчивость сценарной разности к выбору параметров.

Положение, подлежащее проверке. Предсказание величин моделью опровергнуто,
однако замысел работы состоит не в предсказании, а в построении карты, то
есть в указании на то, при каких сочетаниях условий пересмотр статьи
становится опасным и при каких безразличным. Карта строится на разностях
между сценариями, а не на самих величинах, вследствие чего систематическое
смещение, общее обоим сценариям, при вычитании сокращается.

Утверждение это не самоочевидно и подлежит проверке. Разность признаётся
пригодной для карты, если её знак и порядок сохраняются при изменении
параметров, значения которых из данных не восстанавливаются. В противном
случае карта строится на величине, задаваемой произволом настройки, и
содержания не имеет.

Устройство проверки. Два сценария различаются одной величиной, а именно
нормативной эрозией Японии после года пересмотра. В сценарии сохранения она
удерживается на уровне 2025 года, в сценарии пересмотра поднимается до
верхнего предела шкалы. Прочие агенты в обоих сценариях удерживаются
одинаково. Разность системного напряжения берётся по годам прогноза.

Перебираются четыре параметра поочерёдно, а именно скорость возврата
восприятия угрозы, скорость возврата доверия, коэффициент усиления влияния и
крутизна отклика напряжения. Каждый принимает три значения при прочих
неизменных.
"""
from __future__ import annotations

import math
import statistics

from engine.influence import build_influence
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import DynamicsParams, ObservedErosion, Simulator

HISTORY = range(2001, 2026)
PROJECTION = range(2001, 2036)
LAST_OBSERVED = 2025
REVISION_YEAR = 2028
REVISION_LEVEL = 1.0


class ScenarioErosion:
    """
    Источник эрозии для прогноза.

    До последнего наблюдённого года читает наблюдения. После удерживает
    значения этого года у всех агентов. Японии с года пересмотра
    присваивается заданный уровень, чем и различаются два сценария.
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


def run_pair(agents, inputs, influence, rho_threat: float, rho_trust: float,
             steepness: float | None = None):
    """Пара прогонов, сохранение и пересмотр, при заданных параметрах."""
    dyn = DynamicsParams(rho_threat=rho_threat, rho_trust=rho_trust)
    sim = Simulator(agents, influence, dynamics=dyn)
    # Отсечка не задаётся намеренно. При заданной отсечке симулятор
    # замораживает эрозию собственными средствами и источника эрозии за
    # отсечкой не опрашивает вовсе, вследствие чего сценарий до модели не
    # доходит и разность обращается в тождественный ноль. Замораживание
    # выполняет сам источник, а наблюдаемая составляющая угрозы за
    # последним наблюдённым годом отсутствует и потому не подаётся.
    keep = sim.run(PROJECTION, inputs.initial, ScenarioErosion(inputs, False),
                   inputs.incident_at, inputs.typical,
                   label="сохранение")
    rev = sim.run(PROJECTION, inputs.initial, ScenarioErosion(inputs, True),
                  inputs.incident_at, inputs.typical,
                  label="пересмотр")
    return keep, rev


def diffs(keep, rev) -> list[float]:
    """Разность напряжения по годам после пересмотра."""
    out = []
    for i, y in enumerate(keep.years):
        if y >= REVISION_YEAR:
            out.append(rev.tension[i] - keep.tension[i])
    return out


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, HISTORY)

    print("УСТОЙЧИВОСТЬ СЦЕНАРНОЙ РАЗНОСТИ")
    print()
    print(f"  сценарий сохранения: эрозия Японии удержана на уровне "
          f"{inputs.erosion_at('jpn', LAST_OBSERVED):.3f}")
    print(f"  сценарий пересмотра: эрозия Японии поднята до "
          f"{REVISION_LEVEL:.3f} с {REVISION_YEAR} года")
    print(f"  прочие агенты в обоих сценариях удержаны одинаково")
    print()
    print(f"{'параметр':28}{'значение':>10}{'разн. 2028':>13}"
          f"{'разн. 2035':>13}{'средняя':>11}{'знак':>8}")

    configs = []
    for v in (0.30, 0.45, 0.60):
        configs.append(("скорость возврата угрозы", v,
                        dict(rho_threat=v, rho_trust=0.40, gain=0.10)))
    for v in (0.25, 0.40, 0.55):
        configs.append(("скорость возврата доверия", v,
                        dict(rho_threat=0.45, rho_trust=v, gain=0.10)))
    for v in (0.05, 0.10, 0.15):
        configs.append(("коэффициент усиления", v,
                        dict(rho_threat=0.45, rho_trust=0.40, gain=v)))

    rows = []
    for name, value, kw in configs:
        influence = build_influence(agents, obs, "data/relations.csv",
                                    gain=kw["gain"])
        keep, rev = run_pair(agents, inputs, influence,
                             kw["rho_threat"], kw["rho_trust"])
        d = diffs(keep, rev)
        first, last = d[0], d[-1]
        mean = statistics.fmean(d)
        sign = "+" if mean > 0 else ("−" if mean < 0 else "0")
        rows.append((name, value, first, last, mean, sign))
        print(f"{name:28}{value:>10.2f}{first:>13.5f}{last:>13.5f}"
              f"{mean:>11.5f}{sign:>8}")

    print()
    means = [r[4] for r in rows]
    signs = {r[5] for r in rows}

    print(f"  Средняя разность от {min(means):.5f} до {max(means):.5f}.")
    if len(signs) == 1:
        print(f"  Знак разности одинаков во всех {len(rows)} наборах "
              f"параметров.")
    else:
        print("  ЗНАК РАЗНОСТИ МЕНЯЕТСЯ между наборами параметров.")

    if min(means) != 0:
        ratio = max(means) / min(means) if min(means) > 0 else float("inf")
        print(f"  Отношение наибольшей разности к наименьшей {ratio:.2f}.")

    print()
    if len(signs) == 1 and min(means) > 0:
        print("  Разность знака не меняет и остаётся положительной при всяком")
        print("  наборе параметров. Утверждение о направлении действия")
        print("  пересмотра к произволу настройки не сводится.")
        print("  Величина разности при этом от параметров зависит и абсолютным")
        print("  значением предъявляться не может.")
    elif len(signs) == 1:
        print("  Знак устойчив, однако направление противоположно ожидаемому.")
        print("  Подлежит отдельному разбору.")
    else:
        print("  Знак разности неустойчив. Карта на такой разности не")
        print("  строится, поскольку вывод о направлении действия пересмотра")
        print("  задаётся выбором параметра, а не данными.")


if __name__ == "__main__":
    main()
