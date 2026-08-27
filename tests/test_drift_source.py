"""
Установление причины подъёма напряжения за отсечкой.

Положение, подлежащее проверке. Слепой прогон уходит вверх монотонно, тогда
как действительная траектория после 2019 года почти плоска. Названы три
возможных источника, и первый из них состоит в том, что за отсечкой петля
замкнута, а именно приращение восприятия угрозы вычисляется по предсказанным
состояниям прочих агентов и наблюдениями не поправляется.

Проверка разделяет два слагаемых закона обновления. Первое есть приращение
от чужих действий, второе есть возврат к обычному уровню. Если подъём
порождается замкнутой петлёй, то при обнулении приращения от чужих действий
за отсечкой траектория должна перестать расти и приблизиться к плоской.

Прогоняются три случая. Обычный слепой прогон, слепой прогон с обнулённым
приращением и действительная траектория для сравнения.
"""
from __future__ import annotations

import math

from engine.influence import build_influence
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import ObservedErosion, Simulator

YEARS = range(2001, 2026)
CUTOFF = 2019


class NoFeedbackInfluence:
    """
    Обёртка матрицы влияния, обнуляющая приращения за отсечкой.

    Служит одной цели, а именно отделить подъём, порождённый замкнутой
    петлёй, от подъёма, порождённого прочими причинами. Ни для чего иного не
    предназначена.
    """

    def __init__(self, inner, cutoff: int):
        self.inner = inner
        self.cutoff = cutoff

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def threat_delta(self, actions, year):
        base = self.inner.threat_delta(actions, year)
        if year > self.cutoff:
            return {k: 0.0 for k in base}
        return base

    def trust_delta(self, actions, year):
        base = self.inner.trust_delta(actions, year)
        if year > self.cutoff:
            return {k: 0.0 for k in base}
        return base


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")

    sim = Simulator(agents, influence)
    full = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical, label="полный")
    blind = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                    inputs.incident_at, inputs.typical, cutoff=CUTOFF,
                    label="вслепую")

    muted = Simulator(agents, NoFeedbackInfluence(influence, CUTOFF))
    blind_nf = muted.run(YEARS, inputs.initial, ObservedErosion(inputs),
                         inputs.incident_at, inputs.typical, cutoff=CUTOFF,
                         label="вслепую без петли")

    print("ИСТОЧНИК ПОДЪЁМА ЗА ОТСЕЧКОЙ")
    print()
    print(f"{'год':6}{'действит.':>12}{'вслепую':>11}"
          f"{'без петли':>12}")
    for i, y in enumerate(full.years):
        if y < CUTOFF:
            continue
        print(f"{y:<6}{full.tension[i]:>12.4f}{blind.tension[i]:>11.4f}"
              f"{blind_nf.tension[i]:>12.4f}")

    idx = [i for i, y in enumerate(full.years) if y > CUTOFF]

    def rmse(traj):
        return (sum((traj.tension[i] - full.tension[i]) ** 2
                    for i in idx) / len(idx)) ** 0.5

    anchor = full.tension[full.years.index(CUTOFF)]
    rn = (sum((anchor - full.tension[i]) ** 2 for i in idx) / len(idx)) ** 0.5

    r_blind = rmse(blind)
    r_nf = rmse(blind_nf)

    print()
    print(f"  отклонение обычного слепого прогона   {r_blind:.4f}, "
          f"отношение к наивному {r_blind / rn:.3f}")
    print(f"  отклонение прогона без петли          {r_nf:.4f}, "
          f"отношение к наивному {r_nf / rn:.3f}")
    print(f"  отклонение наивного удержания         {rn:.4f}")
    print()

    rise_blind = blind.tension[-1] - blind.tension[full.years.index(CUTOFF)]
    rise_nf = blind_nf.tension[-1] - blind_nf.tension[full.years.index(CUTOFF)]
    rise_real = full.tension[-1] - full.tension[full.years.index(CUTOFF)]
    print(f"  подъём за 2019-2025, действительный  {rise_real:+.4f}")
    print(f"  подъём за 2019-2025, слепой          {rise_blind:+.4f}")
    print(f"  подъём за 2019-2025, без петли       {rise_nf:+.4f}")
    print()

    if abs(rise_nf) < abs(rise_blind) / 2:
        print("  Обнуление приращения от чужих действий подъём устраняет "
              "либо существенно уменьшает.")
        print("  Источником подъёма выступает замкнутая петля, а не "
              "внутренняя динамика сама по себе.")
    else:
        print("  Обнуление приращения подъём не устраняет.")
        print("  Источник подъёма лежит вне петли и подлежит дальнейшему "
              "установлению.")

    if r_nf < rn:
        print()
        print("  Прогон без петли отклоняется от действительной траектории "
              "меньше наивного удержания.")
        print("  Предсказательная способность при устранённой петле "
              "не опровергается.")


if __name__ == "__main__":
    main()
