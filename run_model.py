"""
Точка входа для воспроизведения численных результатов.

Запуск из корня репозитория командой python run_model.py.

Печатает состав данных, полный прогон, слепой прогон с отсечкой на 2019
годе и три объявленные проверки. Ничего не настраивает и ничего не
подбирает. Все величины, влияющие на результат, перечислены в начале
вывода вместе с местом, где заданы.
"""
from __future__ import annotations

import statistics

from engine.influence import POWER_FLOOR, build_influence
from engine.markov import MARKOV
from engine.measurement.compose import CALIBRATION_WINDOW, DAMPER_LIMIT
from engine.measurement.inputs import build_inputs, readiness_report
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import DynamicsParams, ObservedErosion, Simulator
from engine.synthesis import DEFAULT_BETA, PRESSURE_WEIGHTS, STEEPNESS

YEARS = range(2001, 2026)
CUTOFF = 2019


def parameters() -> str:
    d = DynamicsParams()
    lines = ["ВЕЛИЧИНЫ, ВЛИЯЮЩИЕ НА РЕЗУЛЬТАТ", ""]
    lines.append(f"  окно калибровки            {CALIBRATION_WINDOW.start}-"
                 f"{CALIBRATION_WINDOW.stop - 1}   compose.py")
    lines.append(f"  отсечка слепого прогона    {CUTOFF}        run_model.py")
    lines.append(f"  предел множителя           {DAMPER_LIMIT}       compose.py")
    lines.append(f"  нижняя граница мощи        {POWER_FLOOR}        influence.py")
    lines.append(f"  крутизна отклика           {STEEPNESS}        synthesis.py")
    lines.append(f"  коэффициенты синтеза       "
                 f"{ {k: round(v, 3) for k, v in DEFAULT_BETA.items()} }")
    lines.append(f"  веса давления              "
                 f"{ {k: round(v, 3) for k, v in PRESSURE_WEIGHTS.items()} }")
    lines.append(f"  скорость возврата угрозы   {d.rho_threat}       simulator.py")
    lines.append(f"  скорость возврата доверия  {d.rho_trust}       simulator.py")
    lines.append("")
    lines.append("  пороги режимов выведены равным делением отрезка, "
                 "markov.py")
    return "\n".join(lines)


def regime_thresholds() -> str:
    import numpy as np
    prev, out = None, []
    for t in np.arange(0.0, 1.001, 0.001):
        d = MARKOV._attractiveness(t)
        r = ["S1", "S2", "S3"][int(np.argmax(d))]
        if prev and r != prev:
            out.append(f"  переход {prev} в {r} при напряжении {t:.3f}")
        prev = r
    return "\n".join(out)


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")
    sim = Simulator(agents, influence)

    print(parameters())
    print()
    print("ПОРОГИ ФАЗОВЫХ ПЕРЕХОДОВ")
    print(regime_thresholds())
    print()
    print(readiness_report(inputs, agents))
    print()

    full = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical, label="полный")
    blind = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                    inputs.incident_at, inputs.typical, cutoff=CUTOFF,
                    label="вслепую")

    print("ТРАЕКТОРИЯ")
    print(f"{'год':6}{'полный':>10}{'вслепую':>10}{'режим':>8}")
    prev = None
    for i, y in enumerate(full.years):
        mark = "  <-- смена" if prev and full.dominant[i] != prev else ""
        print(f"{y:<6}{full.tension[i]:>10.4f}{blind.tension[i]:>10.4f}"
              f"{full.dominant[i]:>8}{mark}")
        prev = full.dominant[i]

    print()
    print("ПРОВЕРКА НА ПЕРЕМЕШАННЫХ ГОДАХ")
    print("  положение опровергается при связи траекторий выше 0,80")
    r = shuffled_test(agents, obs, influence, inputs, sim)
    print(f"  связь составила {r:.3f}, "
          f"{'опровергнуто' if r > 0.80 else 'не опровергнуто'}")

    print()
    print("СЛЕПОЙ ПРОГОН ПРОТИВ НАИВНОГО")
    print("  предсказательная способность опровергается при отношении "
          "отклонений выше 1,00")
    ratio, rm, rn = naive_test(full, blind)
    print(f"  отклонение модели {rm:.4f}, наивного {rn:.4f}, "
          f"отношение {ratio:.3f}, "
          f"{'опровергнуто' if ratio > 1.0 else 'не опровергнуто'}")


def shuffled_test(agents, obs, influence, inputs, sim, seed: int = 20260101):
    """
    Прогон на перемешанном порядке лет.

    Значения переменных остаются теми же, меняется лишь порядок их
    предъявления. Если траектория напряжения при этом почти не меняется,
    порядок событий на результат не влияет и оператор памяти избыточен.
    """
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
                   inputs.incident_at, inputs.typical, label="верный порядок")
    mix = sim.run(YEARS, inputs.initial,
                  Shuffled(ObservedErosion(inputs)),
                  Shuffled(inputs.incident_at), inputs.typical,
                  label="перемешанный")
    return statistics.correlation(base.tension, mix.tension)


def naive_test(full, blind):
    """
    Слепой прогон против удержания последнего видимого значения.

    Наивным прогнозом называется постоянное значение года отсечки. Модель
    имеет предсказательное содержание, если отклоняется от действительной
    траектории меньше наивного прогноза.
    """
    idx = [i for i, y in enumerate(full.years) if y > CUTOFF]
    anchor = full.tension[full.years.index(CUTOFF)]
    rm = (sum((blind.tension[i] - full.tension[i]) ** 2
              for i in idx) / len(idx)) ** 0.5
    rn = (sum((anchor - full.tension[i]) ** 2
              for i in idx) / len(idx)) ** 0.5
    return (rm / rn if rn else float("inf")), rm, rn


if __name__ == "__main__":
    main()
