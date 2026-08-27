"""
Проверка независимости объявленной мишени.

Положение, подлежащее проверке. Докстринг `inputs.py` утверждает, что
наблюдаемые ряды отношения расходов в модель не подаются вовсе и образуют
мишень проверки, вследствие чего совпадение произведённой траектории с
наблюдаемой становится результатом, а не отражением входа.

Утверждение проверяется прямо. Точкой возврата восприятия угрозы служит
величина `typical`, вычисляемая в `build_inputs` медианой переменной угрозы
по калибровочному окну. Переменная угрозы складывается из трёх показателей,
среди которых доля первичного противника в расходах пары. Если медиана от
этого показателя зависит, то ряд расходов входит в модель через точку
возврата, и мишень независимой не является.

Проверка состоит в пересчёте `typical` при исключённом показателе расходов и
сравнении с исходным значением. Расхождение означает зависимость.
"""
from __future__ import annotations

import math
import statistics

from engine.measurement.compose import CALIBRATION_WINDOW, baselines, normalize
from engine.measurement.indicators import BY_KEY, Var, additive
from engine.measurement.inputs import build_inputs, share_baseline
from engine.measurement.loaders import load_agents, load_observations

YEARS = range(2001, 2026)


def threat_without_milex(agent, year, obs) -> float:
    """
    Переменная угрозы, вычисленная без показателя расходов.

    Порядок вычисления повторяет `compose_var`, но показатель milex из
    состава исключается. Служит для сравнения с исходным значением.
    """
    units = []
    for ind in additive(Var.THREAT, agent.code):
        if ind.key == "milex":
            continue
        base = None
        if ind.kind.value == "deviation":
            base = baselines(obs, agent.code, ind.key)
        _, unit = normalize(ind, agent, year, obs, base)
        if not math.isnan(unit):
            units.append(unit)
    if not units:
        return float("nan")
    return sum(units) / len(units)


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)

    print("НЕЗАВИСИМОСТЬ ОБЪЯВЛЕННОЙ МИШЕНИ")
    print()
    print("  Утверждение: ряд отношения расходов в модель не подаётся и")
    print("  образует мишень проверки.")
    print()
    print("  Проверка: входит ли этот ряд в точку возврата `typical`,")
    print("  к которой модель тянет восприятие угрозы на каждом шаге.")
    print()
    print(f"{'агент':7}{'typical исходн.':>17}{'без расходов':>15}"
          f"{'расхождение':>14}{'вклад milex':>14}")

    contaminated = []
    for code in sorted(agents):
        agent = agents[code]
        t_orig = inputs.typical[code][0]

        vals = []
        for y in CALIBRATION_WINDOW:
            v = threat_without_milex(agent, y, obs)
            if not math.isnan(v):
                vals.append(v)
        t_clean = statistics.median(vals) if vals else float("nan")

        if math.isnan(t_clean):
            diff = float("nan")
            share = float("nan")
        else:
            diff = t_orig - t_clean
            share = abs(diff) / t_orig if t_orig else float("nan")

        if not math.isnan(diff) and abs(diff) > 1e-9:
            contaminated.append(code)

        def f(x):
            return "нет" if math.isnan(x) else f"{x:.4f}"

        print(f"{code:7}{f(t_orig):>17}{f(t_clean):>15}{f(diff):>14}"
              f"{f(share):>14}")

    print()
    if contaminated:
        print(f"  Ряд расходов входит в точку возврата у агентов: "
              f"{', '.join(contaminated)}.")
        print()
        print("  Отсюда следует, что объявленная мишень независимой не")
        print("  является. Модель тянется к уровню, вычисленному по тому же")
        print("  ряду, с которым её выход предполагалось сравнивать.")
        print()
        print("  Сравнение произведённой траектории с наблюдаемой долей")
        print("  расходов в нынешнем виде проверкой не является, поскольку")
        print("  часть совпадения обеспечена входом, а не работой модели.")
    else:
        print("  Ряд расходов в точку возврата не входит, мишень независима.")

    print()
    print("  Дополнительно. Начальное значение восприятия угрозы на первом")
    print("  году вычисляется той же переменной и потому также содержит")
    print("  показатель расходов. Это оговорено в докстринге прямо и")
    print("  нарушением не является, поскольку касается одного года.")
    print("  Точка возврата, напротив, действует на каждом шаге.")


if __name__ == "__main__":
    main()
