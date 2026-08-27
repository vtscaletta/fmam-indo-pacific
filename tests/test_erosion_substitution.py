"""
Проверка чувствительности результата к подмене неопределённой эрозии.

Вопрос. Шесть агентов из десяти не имеют правового потолка, вследствие чего
нормативная эрозия у них не определена. Контроллер требует трёх чисел, и в
`Simulator._inputs` отсутствующее значение подменяется серединой шкалы, то
есть числом 0,5. Подмена действует на каждом шаге всякого прогона, включая
калибровочный период, а не только за отсечкой.

Проверяется, влияет ли выбор подменяющего числа на два объявленных
результата, а именно на год перехода из первого режима во второй и на обе
проверки. Подмена признаётся несущественной, если год перехода не меняется
ни при одном значении из перебираемых, и существенной в противном случае.

Перебираются пять значений, от нижнего предела шкалы до верхнего.
"""
from __future__ import annotations

import statistics

from engine.influence import build_influence
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import ObservedErosion, Simulator

YEARS = range(2001, 2026)
CUTOFF = 2019
SUBSTITUTES = (0.0, 0.25, 0.5, 0.75, 1.0)


def patched_inputs(fill: float):
    """Метод подготовки входов контроллера с заданным подменяющим числом."""
    import math

    def _inputs(state):
        z1, z2, z3 = state
        return (z1, z2, fill if math.isnan(z3) else z3)

    return staticmethod(_inputs)


def transition_year(traj) -> int | None:
    """Первый год, в котором сменился доминирующий режим."""
    for i in range(1, len(traj.years)):
        if traj.dominant[i] != traj.dominant[i - 1]:
            return traj.years[i]
    return None


def naive_ratio(full, blind) -> float:
    idx = [i for i, y in enumerate(full.years) if y > CUTOFF]
    anchor = full.tension[full.years.index(CUTOFF)]
    rm = (sum((blind.tension[i] - full.tension[i]) ** 2
              for i in idx) / len(idx)) ** 0.5
    rn = (sum((anchor - full.tension[i]) ** 2
              for i in idx) / len(idx)) ** 0.5
    return rm / rn if rn else float("inf")


def shuffled_link(sim, inputs, seed: int = 20260101) -> float:
    import random
    years = list(YEARS)
    rnd = random.Random(seed)
    mixed = list(years)
    rnd.shuffle(mixed)
    mapping = dict(zip(years, mixed))

    class Shuffled:
        def __init__(self, src):
            self.src = src

        def __call__(self, agent, year):
            return self.src(agent, mapping.get(year, year))

    base = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical, label="верный")
    mix = sim.run(YEARS, inputs.initial,
                  Shuffled(ObservedErosion(inputs)),
                  Shuffled(inputs.incident_at), inputs.typical,
                  label="перемешанный")
    return statistics.correlation(base.tension, mix.tension)


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")

    print("ЧУВСТВИТЕЛЬНОСТЬ К ПОДМЕНЕ НЕОПРЕДЕЛЁННОЙ ЭРОЗИИ")
    print()
    print("  затронуто агентов: шесть из десяти, а именно aus, chn, idn, "
          "prk, twn, usa")
    print("  подмена действует на каждом шаге, включая калибровочный период")
    print()
    print(f"{'подмена':>9}{'год перехода':>15}{'напр. 2001':>13}"
          f"{'напр. 2019':>13}{'напр. 2025':>13}{'перемеш.':>11}"
          f"{'наивный':>10}")

    rows = []
    for fill in SUBSTITUTES:
        Simulator._inputs = patched_inputs(fill)
        sim = Simulator(agents, influence)
        full = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                       inputs.incident_at, inputs.typical, label="полный")
        blind = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                        inputs.incident_at, inputs.typical, cutoff=CUTOFF,
                        label="вслепую")
        ty = transition_year(full)
        link = shuffled_link(sim, inputs)
        ratio = naive_ratio(full, blind)
        i2001 = full.years.index(2001)
        i2019 = full.years.index(2019)
        i2025 = full.years.index(2025)
        rows.append((fill, ty, full.tension[i2001], full.tension[i2019],
                     full.tension[i2025], link, ratio))
        print(f"{fill:>9.2f}{str(ty):>15}{full.tension[i2001]:>13.4f}"
              f"{full.tension[i2019]:>13.4f}{full.tension[i2025]:>13.4f}"
              f"{link:>11.3f}{ratio:>10.3f}")

    print()
    years_set = {r[1] for r in rows}
    if len(years_set) == 1:
        print(f"  Год перехода не зависит от подменяющего числа, он равен "
              f"{rows[0][1]} при всяком значении.")
        print("  Подмена на год перехода не влияет.")
    else:
        print(f"  Год перехода меняется, наблюдались значения "
              f"{sorted(y for y in years_set if y)}.")
        print("  Подмена на год перехода влияет и подлежит объявлению.")

    spread = max(r[4] for r in rows) - min(r[4] for r in rows)
    print(f"  Размах напряжения 2025 года по подменам составил {spread:.4f}.")

    ratios = [r[6] for r in rows]
    print(f"  Отношение отклонений от {min(ratios):.3f} до {max(ratios):.3f}, "
          f"порог опровержения 1,00.")
    if min(ratios) > 1.0:
        print("  Предсказательная способность опровергается при всяком "
              "подменяющем числе.")


if __name__ == "__main__":
    main()
