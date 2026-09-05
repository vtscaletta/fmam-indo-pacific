"""
Построение карты условий.

Карта отвечает на вопрос работы. Она указывает, при каких сочетаниях остроты
угрожающей среды и прочности союзных гарантий пересмотр девятой статьи
оказывается решающим, а при каких безразличным.

Изображаются три вещи. Область, занимаемая всяким фазовым режимом при
сохранении нынешнего положения. Полоса, в которой пересмотр переводит систему
через порог. Изолиния порога каскадной дестабилизации.

Величины берутся из самой модели, отчего изображение не может разойтись с
расчётом.

Запуск из корня хранилища.

    python build_map_figure.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import build_map as bm
from engine.influence import build_influence
from engine.markov import MARKOV
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import Simulator
from engine.synthesis import phase_thresholds

THREAT = np.round(np.arange(0.70, 1.86, 0.115), 3)
TRUST = np.round(np.arange(0.35, 1.66, 0.13), 3)
CACHE = Path("map_grid.json")

rcParams["font.family"] = "DejaVu Sans"
rcParams["font.size"] = 9
rcParams["axes.linewidth"] = 0.8


def compute() -> dict:
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, bm.HISTORY)
    influence = build_influence(agents, obs, "data/relations.csv")
    sim = Simulator(agents, influence)

    keep = np.zeros((len(THREAT), len(TRUST)))
    rev = np.zeros_like(keep)
    for i, th in enumerate(THREAT):
        for j, tr in enumerate(TRUST):
            typ = bm.scaled_typical(inputs.typical, float(th), float(tr))
            k = sim.run(bm.PROJECTION, inputs.initial,
                        bm.ScenarioErosion(inputs, False),
                        inputs.incident_at, typ)
            r = sim.run(bm.PROJECTION, inputs.initial,
                        bm.ScenarioErosion(inputs, True),
                        inputs.incident_at, typ)
            n = k.years.index(max(bm.PROJECTION))
            keep[i, j] = k.tension[n]
            rev[i, j] = r.tension[n]
        print(f"  острота {th:.3f} посчитана")
    th_ = phase_thresholds(MARKOV)
    return {"keep": keep.tolist(), "rev": rev.tolist(),
            "s12": float(th_["S1->S2"]), "s23": float(th_["S2->S3"])}


def main() -> None:
    if CACHE.exists():
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        print("решётка взята из сохранённой")
    else:
        data = compute()
        CACHE.write_text(json.dumps(data), encoding="utf-8")

    keep = np.array(data["keep"])
    rev = np.array(data["rev"])
    s12, s23 = data["s12"], data["s23"]
    diff = rev - keep

    fig, ax = plt.subplots(figsize=(7.4, 5.2), dpi=200)

    ax.contourf(TRUST, THREAT, keep, levels=[0.0, s12, s23, 1.0],
                colors=["#f7f7f7", "#e2e2e2", "#bdbdbd"])

    # полоса между двумя изолиниями порога каскада
    ax.contourf(TRUST, THREAT, np.where((keep < s23) & (rev >= s23), 1.0, 0.0),
                levels=[0.5, 1.5], colors=["none"], hatches=["/////"])

    ax.contour(TRUST, THREAT, keep, levels=[s23], colors="0.1",
               linewidths=1.8)
    ax.contour(TRUST, THREAT, rev, levels=[s23], colors="0.1",
               linewidths=1.2, linestyles="dashed")
    ax.contour(TRUST, THREAT, keep, levels=[s12], colors="0.45",
               linewidths=1.0, linestyles="dotted")

    ax.annotate("порог каскада при сохранении", xy=(0.545, 1.66),
                xytext=(0.92, 1.62), fontsize=8.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", linewidth=0.8, color="0.25"))
    ax.annotate("тот же порог при пересмотре", xy=(0.62, 1.60),
                xytext=(0.92, 1.34), fontsize=8.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", linewidth=0.8, color="0.25"))
    ax.annotate("при прочной гарантии пересмотр\nне меняет режима ни при какой\nостроте среды", xy=(1.30, 1.10),
                fontsize=8.5, ha="center", va="center", color="0.3")

    ax.set_xlabel("Прочность союзных гарантий, доля от наблюдаемого уровня")
    ax.set_ylabel("Острота угрожающей среды, доля от наблюдаемого уровня")
    ax.set_xlim(TRUST.min(), TRUST.max())
    ax.set_ylim(THREAT.min(), THREAT.max())
    ax.set_xticks(np.arange(0.4, 1.7, 0.2))
    ax.set_yticks(np.arange(0.8, 1.9, 0.2))
    ax.set_xticklabels([f"{v:.1f}".replace(".", ",")
                        for v in np.arange(0.4, 1.7, 0.2)])
    ax.set_yticklabels([f"{v:.1f}".replace(".", ",")
                        for v in np.arange(0.8, 1.9, 0.2)])
    ax.grid(True, linestyle=":", linewidth=0.4, color="0.65")
    ax.set_axisbelow(True)

    handles = [
        Patch(facecolor="#f7f7f7", edgecolor="0.5", label="Устойчивый баланс"),
        Patch(facecolor="#e2e2e2", edgecolor="0.5", label="Холодная конфронтация"),
        Patch(facecolor="#bdbdbd", edgecolor="0.5", label="Каскадная дестабилизация"),
        Patch(facecolor="white", edgecolor="0.1", hatch="/////",
              label="Полоса, где пересмотр решает"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8,
              frameon=True, edgecolor="0.5", framealpha=0.95)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig("figure_map.png", bbox_inches="tight")
    fig.savefig("figure_map.svg", bbox_inches="tight")

    band = np.where((keep < s23) & (rev >= s23), 1.0, 0.0)
    n = int(band.sum())
    print(f"\nразность от {diff.min():.5f} до {diff.max():.5f}, "
          f"знак положителен всюду: {bool((diff > 0).all())}")
    print(f"клеток, где пересмотр переводит через порог: {n} из {band.size}")
    print("записано figure_map.png и figure_map.svg")


if __name__ == "__main__":
    main()
