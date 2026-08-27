"""
Проверка модели на объявленной мишени.

Мишенью объявлен наблюдаемый ряд доли первичного противника в военных
расходах пары. Модель, ведомая датированными решениями, обязана произвести
траекторию восприятия угрозы, согласную с этим рядом, при том что сам ряд ей
на шагах не подаётся.

Сравнение ведётся на общей шкале. Наблюдаемая доля приводится тем же
правилом отклонения от обычного уровня, каким приводится показатель расходов
внутри переменной угрозы, вследствие чего обе величины лежат в отрезке
[0, 1] и сопоставимы.

Проверка ставится против двух наивных соперников. Первый удерживает значение
первого года постоянным весь интервал. Второй удерживает постоянным среднее
значение ряда, что для несведущего наблюдателя есть наилучшая догадка.
Модель признаётся имеющей содержание, если отклоняется от наблюдаемого ряда
меньше обоих.

Проверка выполняется в благоприятном случае, а именно на модели в нынешнем
виде, где точка возврата содержит показатель расходов. Прохождение в таком
случае необходимо, но недостаточно, тогда как непрохождение решает вопрос
окончательно.
"""
from __future__ import annotations

import math
import statistics

from engine.influence import build_influence
from engine.measurement import scales as sc
from engine.measurement.inputs import (
    build_inputs, observed_threat_share, share_baseline,
)
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import ObservedErosion, Simulator

YEARS = range(2001, 2026)
CALIBRATION = range(2001, 2020)


def observed_series(agent, obs) -> dict[int, float]:
    """
    Наблюдаемый ряд, приведённый к шкале переменной угрозы.

    Обычный уровень вычисляется по калибровочному окну, вследствие чего
    приведение отложенного отрезка обучающей выборкой не пользуется.
    """
    base = share_baseline(agent, obs, CALIBRATION)
    if base is None:
        return {}
    out = {}
    for y in YEARS:
        raw = observed_threat_share(agent, y, obs)
        if math.isnan(raw):
            continue
        out[y] = sc.deviation_from_baseline(raw, base.center, base.spread)
    return out


def rmse(a: list[float], b: list[float]) -> float:
    return (sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)) ** 0.5


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")
    sim = Simulator(agents, influence)

    traj = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical, label="полный")

    print("ПРОВЕРКА НА ОБЪЯВЛЕННОЙ МИШЕНИ")
    print()
    print("  мишень: наблюдаемая доля противника в расходах пары,")
    print("  приведённая к шкале переменной угрозы")
    print()
    print(f"{'агент':7}{'лет':>5}{'модель':>10}{'первый год':>13}"
          f"{'среднее':>10}{'связь':>9}   вывод")

    wins, losses, skipped = [], [], []
    for code in sorted(agents):
        agent = agents[code]
        series = observed_series(agent, obs)
        if len(series) < 5:
            skipped.append(code)
            print(f"{code:7}{len(series):>5}{'—':>10}{'—':>13}{'—':>10}"
                  f"{'—':>9}   ряд короток, не проверяется")
            continue

        years = sorted(series)
        target = [series[y] for y in years]
        model = [traj.state_series(code, 0)[traj.years.index(y)]
                 for y in years]

        r_model = rmse(model, target)
        r_first = rmse([target[0]] * len(target), target)
        r_mean = rmse([statistics.fmean(target)] * len(target), target)

        try:
            link = statistics.correlation(model, target)
        except statistics.StatisticsError:
            link = float("nan")

        beats = r_model < r_first and r_model < r_mean
        (wins if beats else losses).append(code)

        verdict = "модель точнее обоих" if beats else "модель уступает"
        lk = "нет" if math.isnan(link) else f"{link:+.3f}"
        print(f"{code:7}{len(years):>5}{r_model:>10.4f}{r_first:>13.4f}"
              f"{r_mean:>10.4f}{lk:>9}   {verdict}")

    print()
    print(f"  Модель точнее обоих наивных соперников у {len(wins)} агентов "
          f"из {len(wins) + len(losses)} проверенных.")
    if wins:
        print(f"  Проверку прошли: {', '.join(wins)}.")
    if losses:
        print(f"  Проверку не прошли: {', '.join(losses)}.")
    if skipped:
        print(f"  Не проверялись из-за короткого ряда: {', '.join(skipped)}.")

    print()
    if not wins:
        print("  Модель не превосходит наивного удержания ни у одного агента.")
        print("  Проверка на мишени провалена в благоприятном случае, то есть")
        print("  при точке возврата, содержащей самый проверяемый ряд.")
        print("  Дальнейшая очистка точки возврата исхода не изменит.")
    elif len(wins) >= len(losses):
        print("  Модель превосходит наивных соперников у большинства агентов.")
        print("  Проверка пройдена в благоприятном случае, вследствие чего")
        print("  подлежит повторению при очищенной точке возврата, где")
        print("  проверяемый ряд в модель не входит вовсе.")
    else:
        print("  Исход неоднороден по агентам и решающим не является.")


if __name__ == "__main__":
    main()
