"""
Построение вспомогательных рисунков.

Три изображения, нужных и разделу 2.3, и изложению для незнакомой аудитории.

    Ступени нормативной эрозии Японии с указанием породившего акта.
    Траектория системного напряжения с порогами фазовых режимов.
    Устойчивость сценарной разности к выбору неопределяемых величин.

Величины берутся из самой модели.

Запуск из корня хранилища.

    python build_figures.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

from engine.influence import build_influence
from engine.markov import MARKOV
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import DynamicsParams, ObservedErosion, Simulator
from engine.synthesis import phase_thresholds

YEARS = range(2001, 2026)
CUTOFF = 2019

rcParams["font.family"] = "DejaVu Sans"
rcParams["font.size"] = 9
rcParams["axes.linewidth"] = 0.8

ACTS = {
    2008: "Основной закон\nо космосе",
    2013: "Совет безопасности,\nзакон о тайнах",
    2014: "переосмысление права\nна коллективную самооборону",
    2015: "законы\nо безопасности",
    2022: "три стратегических\nдокумента",
    2025: "закон об активной\nкиберзащите",
}


def ru(v: float, n: int = 2) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def fig_erosion(inputs) -> None:
    e = inputs.erosion["jpn"]
    ys = sorted(e)
    v = [e[y] for y in ys]

    fig, ax = plt.subplots(figsize=(7.4, 3.8), dpi=200)
    ax.step(ys, v, where="post", color="0.15", linewidth=1.8)
    ax.fill_between(ys, 0, v, step="post", color="0.15", alpha=0.07)

    off = {2008: (-30, 34), 2013: (-70, 30), 2014: (-16, -46),
           2015: (52, -8), 2022: (-56, 34), 2025: (-30, 30)}
    for y, name in ACTS.items():
        if y not in e:
            continue
        ax.plot([y], [e[y]], "o", color="0.15", markersize=4.5,
                markerfacecolor="white", markeredgewidth=1.2)
        dx, dy = off[y]
        ax.annotate(name, xy=(y, e[y]), xytext=(dx, dy),
                    textcoords="offset points", fontsize=7.6, ha="center",
                    color="0.25",
                    arrowprops=dict(arrowstyle="-", linewidth=0.7,
                                    color="0.5", shrinkB=3))

    ax.set_xlim(2000.4, 2025.6)
    ax.set_ylim(-0.06, 0.60)
    ax.set_xticks(range(2001, 2026, 3))
    ax.set_yticks(np.arange(0, 0.51, 0.1))
    ax.set_yticklabels([ru(x, 1) for x in np.arange(0, 0.51, 0.1)])
    ax.set_xlabel("Год")
    ax.set_ylabel("Нормативная эрозия")
    ax.grid(True, linestyle=":", linewidth=0.4, color="0.75")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig("figure_erosion.png", bbox_inches="tight")
    fig.savefig("figure_erosion.svg", bbox_inches="tight")
    print("  записано figure_erosion")


def fig_tension(agents, inputs, influence) -> None:
    sim = Simulator(agents, influence)
    full = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical)
    blind = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                    inputs.incident_at, inputs.typical, cutoff=CUTOFF)
    th = phase_thresholds(MARKOV)
    ys = list(full.years)
    k = ys.index(CUTOFF)

    fig, ax = plt.subplots(figsize=(7.4, 4.0), dpi=200)
    ax.axhspan(0, th["S1->S2"], color="0.96")
    ax.axhspan(th["S1->S2"], th["S2->S3"], color="0.90")
    ax.axhspan(th["S2->S3"], 1.0, color="0.80")
    ax.axhline(th["S1->S2"], color="0.4", linewidth=0.9, linestyle="dotted")
    ax.axhline(th["S2->S3"], color="0.2", linewidth=1.3)

    ax.plot(ys, full.tension, color="0.1", linewidth=1.9,
            label="при наблюдениях")
    ax.plot(ys[k:], blind.tension[k:], color="0.35", linewidth=1.4,
            linestyle="dashed", label="без наблюдений после 2019 года")
    ax.axvline(CUTOFF, color="0.5", linewidth=0.8, linestyle=(0, (2, 3)))
    ax.annotate("отсечка наблюдений", xy=(CUTOFF, 0.40),
                xytext=(CUTOFF - 0.5, 0.40), rotation=90,
                fontsize=7.6, color="0.4", ha="right", va="bottom")

    ax.annotate("порог каскадной дестабилизации", xy=(2002, th["S2->S3"]),
                xytext=(2002, th["S2->S3"] + 0.022), fontsize=7.8,
                color="0.2")
    ax.annotate("порог холодной конфронтации", xy=(2002, th["S1->S2"]),
                xytext=(2002, th["S1->S2"] + 0.022), fontsize=7.8,
                color="0.35")

    ax.set_xlim(2001, 2025)
    ax.set_ylim(0.15, 0.80)
    ax.set_xticks(range(2001, 2026, 3))
    ax.set_yticks(np.arange(0.2, 0.81, 0.1))
    ax.set_yticklabels([ru(x, 1) for x in np.arange(0.2, 0.81, 0.1)])
    ax.set_xlabel("Год")
    ax.set_ylabel("Системное напряжение")
    ax.legend(loc="lower right", fontsize=8, frameon=True, edgecolor="0.5")
    ax.grid(True, axis="x", linestyle=":", linewidth=0.4, color="0.75")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig("figure_tension.png", bbox_inches="tight")
    fig.savefig("figure_tension.svg", bbox_inches="tight")
    print("  записано figure_tension")


def fig_stability(agents, obs, inputs) -> None:
    import build_map as bm
    sets = [("скорость возврата угрозы", [0.30, 0.45, 0.60],
             lambda v: (dict(rho_threat=v, rho_trust=0.40), 0.10)),
            ("скорость возврата доверия", [0.25, 0.40, 0.55],
             lambda v: (dict(rho_threat=0.45, rho_trust=v), 0.10)),
            ("коэффициент усиления", [0.05, 0.10, 0.15],
             lambda v: (dict(rho_threat=0.45, rho_trust=0.40), v))]
    labels, values = [], []
    for name, vs, mk in sets:
        for v in vs:
            dyn, gain = mk(v)
            infl = build_influence(agents, obs, "data/relations.csv",
                                   gain=gain)
            sim = Simulator(agents, infl, dynamics=DynamicsParams(**dyn))
            keep = sim.run(bm.PROJECTION, inputs.initial,
                           bm.ScenarioErosion(inputs, False),
                           inputs.incident_at, inputs.typical)
            rev = sim.run(bm.PROJECTION, inputs.initial,
                          bm.ScenarioErosion(inputs, True),
                          inputs.incident_at, inputs.typical)
            n = keep.years.index(max(bm.PROJECTION))
            labels.append(ru(v))
            values.append(rev.tension[n] - keep.tension[n])
            print(f"  {name} {v}: {values[-1]:+.5f}")

    fig, ax = plt.subplots(figsize=(7.4, 3.8), dpi=200)
    x = np.arange(len(values))
    ax.bar(x, values, color="0.6", edgecolor="0.15", linewidth=0.8, width=0.66)
    ax.axhline(0, color="0.1", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    top = max(values) * 1.55
    for i, (name, _, _) in enumerate(sets):
        c = i * 3 + 1
        ax.annotate(name, xy=(c, top * 0.90), fontsize=8.2, ha="center",
                    color="0.2")
        ax.plot([i * 3 - 0.38, i * 3 + 2.38], [top * 0.83] * 2,
                color="0.45", linewidth=0.8)
    for xi, v in zip(x, values):
        ax.annotate(ru(v, 4), xy=(xi, v), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=7.4,
                    color="0.25")
    ax.set_ylabel("Разность напряжения,\nпересмотр минус сохранение")
    ax.set_ylim(0, top)
    ax.set_yticks(np.arange(0, 0.026, 0.005))
    ax.set_yticklabels([ru(v, 3) for v in np.arange(0, 0.026, 0.005)])
    ax.grid(True, axis="y", linestyle=":", linewidth=0.4, color="0.75")
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig("figure_stability.png", bbox_inches="tight")
    fig.savefig("figure_stability.svg", bbox_inches="tight")
    print("  записано figure_stability")


def main() -> None:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")
    fig_erosion(inputs)
    fig_tension(agents, inputs, influence)
    fig_stability(agents, obs, inputs)


if __name__ == "__main__":
    main()
