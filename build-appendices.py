"""
Сборка приложений, производимых моделью, в единый документ Word.

Приложение показывает устройство и позволяет проверить расчёт на образце,
тогда как полные ряды остаются в хранилище, постоянный идентификатор
которого приводится в приложении о техническом авторстве. Печать тысячи
четырёхсот строк наблюдений заняла бы свыше тридцати страниц, не прибавив к
проверяемости ничего сверх того, что даёт открытое хранилище.

Запуск из корня хранилища.

    python build_appendices.py
"""
from __future__ import annotations

import csv, json, math, subprocess
from collections import defaultdict
from pathlib import Path

from engine.fuzzy_agent import JAPAN
from engine.influence import build_influence
from engine.markov import MARKOV
from engine.measurement.compose import compose_var
from engine.measurement.indicators import Var
from engine.measurement.inputs import build_inputs
from engine.measurement.loaders import load_agents, load_observations
from engine.simulator import ObservedErosion, Simulator
from engine.synthesis import phase_thresholds

YEARS = range(2001, 2026)
STEP_YEAR = 2022
RU = {"jpn":"Япония","chn":"КНР","usa":"США","kor":"Корея","prk":"КНДР",
      "twn":"Тайвань","phl":"Филиппины","ind":"Индия","aus":"Австралия","idn":"Индонезия"}
T = {"low":"Н","med":"С","high":"В"}
KEYRU = {"milex":"Расходы","incidents":"Враждебность","affinity":"Близость",
 "us_rok_exercises":"Учения США и РК","exercises":"Учения","arms_share":"Импорт",
 "ceiling":"Ступень","categories":"Запреты","commitments":"Обязательства",
 "dissent":"Несогласие","cinc":"Возможности"}
KEYS = list(KEYRU)
KINDS = {"none":"нет","contact":"сопр.","dispute":"спор","sovereignty":"госуд."}
d3 = lambda x: f"{x:.3f}".replace(".", ",")

def collect():
    agents = load_agents("data/agents.csv")
    obs = load_observations("data/observations.csv", agents)
    inputs = build_inputs(agents, obs, YEARS)
    influence = build_influence(agents, obs, "data/relations.csv")
    sim = Simulator(agents, influence)
    codes = sorted(agents)

    rules = [[str(i+1), T[r["if"]["threat"]], T[r["if"]["trust"]], T[r["if"]["erosion"]],
              T[r["then"]["milex"]], T[r["then"]["rhet"]], T[r["then"]["drift"]]]
             for i, r in enumerate(JAPAN.all_rules())]

    step = []
    for c in codes:
        z = [compose_var(k, agents[c], STEP_YEAR, obs).value
             for k in (Var.THREAT, Var.TRUST, Var.EROSION)]
        zz = [x if not math.isnan(x) else 0.5 for x in z]
        a = JAPAN.step(*zz)
        f = lambda x: "н. о." if math.isnan(x) else d3(x)
        step.append([RU[c], f(z[0]), f(z[1]), f(z[2]),
                     d3(a["milex"]), d3(a["rhet"]), d3(a["drift"])])
    traj = sim.run(YEARS, inputs.initial, ObservedErosion(inputs),
                   inputs.incident_at, inputs.typical)
    i = traj.years.index(STEP_YEAR)
    th = phase_thresholds(MARKOV)

    from engine.synthesis import (COMPONENTS, DEFAULT_BETA, DifferentialMemory,
                                  influence_weights, aggregate,
                                  perceptual_pressure)
    mem = DifferentialMemory()
    prevH, cur = None, None
    for k2, y2 in enumerate(traj.years):
        w2 = influence_weights(influence, y2)
        ac = {c: traj.agent_actions[c][k2] for c in traj.agent_actions}
        cm = aggregate(ac, w2)
        if y2 == STEP_YEAR:
            prevH, cur = dict(mem.H), cm
            break
        mem.update(cm)
    w = influence_weights(influence, STEP_YEAR)
    lam = DifferentialMemory().lam
    newH, memrows = {}, []
    for c in COMPONENTS:
        l = lam[c][0] if cur[c] >= prevH[c] else lam[c][1]
        newH[c] = l * prevH[c] + (1.0 - l) * cur[c]
        memrows.append([{"milex": "Расходы", "rhet": "Риторика",
                         "drift": "Дрейф"}[c], d3(prevH[c]), d3(cur[c]),
                        "нарастание" if cur[c] >= prevH[c] else "спад",
                        f"{l}".replace(".", ","), d3(newH[c])])
    st = {c: traj.agent_states[c][i] for c in traj.agent_states}
    P = perceptual_pressure(st, w)
    b = DEFAULT_BETA
    mat = sum(b[c] * newH[c] for c in COMPONENTS)
    wrows = [[RU[c], d3(w[c])] for c in sorted(w, key=lambda x: -w[x])]
    meta = {"tension": f"{traj.tension[i]:.4f}".replace(".", ","),
            "regime": traj.dominant[i], "s12": d3(th["S1->S2"]),
            "s23": d3(th["S2->S3"]),
            "aggM": d3(cur["milex"]), "aggR": d3(cur["rhet"]),
            "aggD": d3(cur["drift"]),
            "P": d3(P), "mat": d3(mat), "perc": d3(b["pressure"] * P),
            "arg": d3(b["b0"] + mat + b["pressure"] * P),
            "b0": d3(b["b0"]), "bm": d3(b["milex"]), "bp": d3(b["pressure"]),
            "memrows": memrows, "wrows": wrows,
            "topw": RU[max(w, key=w.get)], "topwv": d3(max(w.values()))}

    zj = [compose_var(k, agents["jpn"], STEP_YEAR, obs).value
          for k in (Var.THREAT, Var.TRUST, Var.EROSION)]
    fj = JAPAN.fuzzify(*zj)
    NM = {"low": "низкий", "med": "средний", "high": "высокий"}
    fuzz = [[{"z1": "Восприятие угрозы", "z2": "Доверие",
              "z3": "Нормативная эрозия"}[k], d3(zj[idx])] +
            [d3(fj[k][t]) for t in ("low", "med", "high")]
            for idx, k in enumerate(("z1", "z2", "z3"))]
    rl = JAPAN.active_rules(*zj)
    top = [[NM[r["if"]["threat"]], NM[r["if"]["trust"]], NM[r["if"]["erosion"]],
            NM[r["then"]["milex"]], NM[r["then"]["rhet"]], NM[r["then"]["drift"]],
            d3(r["alpha"])] for r in rl[:3]]
    outj = JAPAN.step(*zj)
    cH, sH = JAPAN.mf_params("z1", "high")
    jp = {"z": [d3(x) for x in zj], "fuzz": fuzz, "top": top,
          "sigma": f"{sH:.4f}".replace(".", ","),
          "out": [d3(outj[k]) for k in ("milex", "rhet", "drift")],
          "alpha": d3(rl[0]["alpha"]),
          "muhigh": d3(fj["z1"]["high"])}

    rows = list(csv.DictReader(open("data/observations.csv", encoding="utf-8-sig")))
    cov = defaultdict(lambda: defaultdict(int))
    for r in rows: cov[r["agent"]][r["key"]] += 1
    coverage = [[RU[c]] + [str(cov[c].get(k,0)) if cov[c].get(k) else "\u2014" for k in KEYS]
                for c in codes]
    q = defaultdict(int)
    for r in rows: q[r["quality"]] += 1
    tot = len(rows)
    quality = [[k, str(v), f"{v/tot*100:.1f}".replace(".", ",")]
               for k, v in sorted(q.items(), key=lambda x: -x[1])]
    sample = [[r["agent"], r["year"], KEYRU.get(r["key"], r["key"]), r["value"],
               r["quality"], r["source"][:56]]
              for r in rows if r["agent"]=="jpn" and r["key"] in
              ("ceiling","categories","commitments","dissent")
              and int(r["year"]) in (2008,2013,2014,2015,2022,2025)][:12]

    grid = []
    for a in codes:
        row = [RU[a]]
        for b in codes:
            if a == b: row.append("\u2014")
            else:
                rel = influence.relations.get((a,b))
                row.append(KINDS.get(rel.kind,"нет") if rel else "нет")
        grid.append(row)
    W = influence.weights(STEP_YEAR)
    weights = [[RU[a]] + [f"{W[a][b]:.2f}".replace(".", ",") for b in codes] for a in codes]

    coders = []
    with open("data/coders.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            v = [row["автор"], row["модель_1"], row["модель_2"]]
            sp = max(int(x) for x in v) - min(int(x) for x in v)
            coders.append([row["идентификатор"]] + v +
                          ["\u2014" if sp == 0 else str(sp)])
    ncol = 3
    per = -(-len(coders) // ncol)
    cols = [coders[i * per:(i + 1) * per] for i in range(ncol)]
    while len(cols[-1]) < per:
        cols[-1].append(["", "", "", "", ""])
    codes_grid = [sum((cols[j][i] for j in range(ncol)), []) for i in range(per)]
    same = sum(1 for c in coders if c[4] == "\u2014")
    one = sum(1 for c in coders if c[4] == "1")
    two = sum(1 for c in coders if c[4] not in ("\u2014", "1"))

    exc = []
    with open("data/coders_excluded.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            exc.append([row["идентификатор"], row["основание"][:70]])
    ex_ag = defaultdict(int)
    for e in exc:
        ex_ag[e[0].split("-")[0]] += 1
    exsum = [[RU.get(k, k), str(v)] for k, v in
             sorted(ex_ag.items(), key=lambda x: -x[1])]

    ev = list(csv.DictReader(open("data/events.csv", encoding="utf-8-sig")))
    KIND = {"incident": "Отдельное происшествие",
            "pattern": "Длящийся порядок",
            "legal": "Правовой акт",
            "uncertain": "Разряд не установлен",
            "confirmed_zero": "Подтверждённое отсутствие",
            "unresolved_gap": "Неразрешённый пробел"}
    kc = defaultdict(int)
    for e in ev:
        kc[e["тип_события"]] += 1
    evkind = [[KIND.get(k, k), str(v)] for k, v in
              sorted(kc.items(), key=lambda x: -x[1])]
    yc = defaultdict(int)
    for e in ev:
        yc[str(e["дата"])[:4]] += 1
    ys = sorted(yc)
    evyear = [[y, str(yc[y])] for y in ys]
    evsample = [[str(e["дата"])[:10], e["агент_a"], e["агент_b"],
                 (e["действие"] or "")[:34], (e["описание"] or "")[:96]]
                for e in ev if e["тип_события"] == "incident"][:10]

    return {"exc": exc, "exsum": exsum, "nexc": str(len(exc)),
            "evkind": evkind, "evyear": evyear, "evsample": evsample,
            "nev": str(len(ev)),
            "codes":[RU[c] for c in codes], "rules":rules, "step":step,
            "jp": jp, "codes_grid": codes_grid, "nsame": str(same), "none": str(one),
            "ntwo": str(two), "ncoded": str(len(coders)),
            "meta":meta, "coverage":coverage, "quality":quality, "sample":sample,
            "grid":grid, "weights":weights, "total":tot, "memrows":meta["memrows"], "wrows":meta["wrows"],
            "keys":[KEYRU[k] for k in KEYS], "year":str(STEP_YEAR)}

def main():
    data = collect()
    Path("appendix_data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("данные собраны, строк наблюдений", data["total"])
    subprocess.run(["node", "build_appendices.js"], check=True)

if __name__ == "__main__":
    main()
