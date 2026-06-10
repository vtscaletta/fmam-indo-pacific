"""
Слой суждения. Модуль 13, чтение прогона по решётке.

Относит готовый прогон к значениям восьми осей суждения. Здесь нет прозы и нет
интерфейса, только детерминированная классификация чисел в значения. Машина
считает и относит, суждение за пределы факта прогона не выносит, вербализацию
накладывает текстовый слой. На один и тот же прогон ответ всегда один, оттого
вывод воспроизводим и проверяем построчно.

Восемь осей. Доминирующая сила давления, направление траектории, форма
движения, состояние критической безопасности, смена природы давления,
расстановка протагонистов, вклад сценария сверх инерции, темп выхода на
экстремум. Три первые ведут суждение, пять уточняют, компоновку держит
текстовый слой.

Пороги. Часть вынесена константами как явный авторский выбор и подлежит защите
вслух, часть наследована из калибровки рабочего кода, часть динамическая и
приходит из самой модели через thresholds. Решётка не претендует на пророчество,
она переводит уже посчитанный моделью прогон на язык, и читать перевод можно
верно либо неверно, что проверяемо на самом тексте.
"""

from __future__ import annotations


# Авторский выбор, защищается вслух как обоснованное решение, а не данность.
DOM_LEAD = 0.50      # доля лидера для чистой доминанты, ось 1
DOM_GAP = 0.15       # отрыв лидера от второго, ось 1
DUO_SUM = 2.0 / 3.0  # сумма двух первых сил для двухфакторной, ось 1
SHARP_MULT = 2.0     # во сколько раз годовой шаг бьёт среднюю скорость, ось 3
OSC_FLIPS = 2        # смен знака приращения для колебательной, ось 3
ACTOR_FLOOR = 0.05   # порог веса активного актёра, ось 6
HEGEMON = 2.0        # кратность отрыва гегемона, ось 6
TAIL_SHARE = 0.50    # доля хвоста против пары лидеров для свалки, ось 6

# Наследовано из рабочего кода, защищается ссылкой на существующую калибровку.
EPS = 0.005          # фильтр шума и порог заметности, разрешение выходной шкалы
EDGE = 0.05          # зазор кромки срыва, из раздела пределов достоверности


def _axis_dominance(data: dict) -> dict:
    """Ось 1. Откуда идёт давление. Прямая логика долей трёх сил."""
    shares = data.get("drivers", {}).get("axis_shares", {})
    if not shares:
        return {"value": None}
    ranked = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)
    (k1, v1) = ranked[0]
    (k2, v2) = ranked[1] if len(ranked) > 1 else (None, 0.0)
    if v1 >= DOM_LEAD and (v1 - v2) > DOM_GAP:
        return {"value": "single", "axis": k1, "share": round(v1, 3)}
    if (v1 + v2) >= DUO_SUM:
        return {"value": "duo", "axes": [k1, k2], "shares": [round(v1, 3), round(v2, 3)]}
    return {"value": "diffuse", "top": k1}


def _axis_direction(data: dict) -> dict:
    """Ось 2. Куда пришла система. Чистая дельта старт финал."""
    tl = data.get("timeline", [])
    if len(tl) < 2:
        return {"value": None}
    delta = tl[-1]["tension"] - tl[0]["tension"]
    if abs(delta) <= EPS:
        return {"value": "flat", "delta": round(delta, 4)}
    return {"value": "rising" if delta > 0 else "falling", "delta": round(delta, 4)}


def _axis_shape(data: dict) -> dict:
    """Ось 3. Как именно шла. Колебательность через смены знака, иначе
    динамический порог резкости, страхующий от плавающего горизонта."""
    tl = data.get("timeline", [])
    if len(tl) < 3:
        return {"value": None}
    tens = [r["tension"] for r in tl]
    deltas = [tens[i] - tens[i - 1] for i in range(1, len(tens))]
    signif = [d for d in deltas if abs(d) > EPS]
    flips = sum(1 for i in range(1, len(signif)) if (signif[i] > 0) != (signif[i - 1] > 0))
    if flips >= OSC_FLIPS:
        return {"value": "oscillating", "flips": flips}
    total = abs(tens[-1] - tens[0])
    if total <= EPS:
        # Плоская по итогу. Резкость не считаем, чтобы не делить на малое.
        return {"value": "creeping", "reason": "flat"}
    n = len(tl)
    max_step = max(abs(d) for d in deltas)
    if max_step > SHARP_MULT * total / n:
        return {"value": "sharp", "max_step": round(max_step, 4)}
    return {"value": "creeping", "max_step": round(max_step, 4)}


def _axis_safety(data: dict) -> dict:
    """Ось 4. Где финал относительно порога срыва. Шкала от динамического
    порога модели, а не от математической единицы, которой сигмоида не достигает."""
    th = data.get("thresholds", {})
    tau = th.get("S2->S3")
    theta = th.get("S1->S2")
    comp = data.get("comparison", {})
    final = comp.get("final")
    peak = comp.get("peak")
    if tau is None or final is None:
        return {"value": None}
    if final >= tau:
        return {"value": "breached", "final": final, "tau": tau}
    if peak is not None and peak >= tau:
        return {"value": "revived", "final": final, "peak": peak, "tau": tau}
    if (tau - final) <= EDGE:
        return {"value": "edge", "final": final, "tau": tau, "gap": round(tau - final, 4)}
    if theta is not None and final < theta:
        return {"value": "deep", "final": final, "theta": theta}
    return {"value": "stable", "final": final, "tau": tau}


def _axis_shift(data: dict) -> dict:
    """Ось 5. Менялась ли природа давления по ходу горизонта. Покоординатный
    трекинг лидера по годам. Качель по нормативной оси помечается как аномалия,
    ибо храповик дрейфа делает откат нормы маловероятным по механике модели."""
    seq = [r.get("leader") for r in data.get("axis_by_year", []) if r.get("leader")]
    if len(seq) < 2:
        return {"value": "steady", "leader": seq[0] if seq else None}
    runs = [seq[0]]
    for x in seq[1:]:
        if x != runs[-1]:
            runs.append(x)
    changes = len(runs) - 1
    if changes == 0:
        return {"value": "steady", "leader": runs[0]}
    if changes == 1:
        return {"value": "handover", "from_axis": runs[0], "to_axis": runs[-1]}
    norm_anomaly = runs.count("normative") >= 2
    return {"value": "swing", "runs": runs, "normative_anomaly": norm_anomaly}


def _axis_actors(data: dict) -> dict:
    """Ось 6. Конфигурация действующих сил по весам актёров из M-B2."""
    acts = sorted(data.get("actors", []), key=lambda a: a["weight"], reverse=True)
    if not acts:
        return {"value": None}
    if all(a["weight"] < ACTOR_FLOOR for a in acts):
        return {"value": "lull"}
    w1 = acts[0]["weight"]
    w2 = acts[1]["weight"] if len(acts) > 1 else 0.0
    if w2 < ACTOR_FLOOR or (w2 > 0 and w1 / w2 >= HEGEMON):
        return {"value": "hegemon", "leader": acts[0]["name"]}
    tail = sum(a["weight"] for a in acts[2:5])
    if tail > TAIL_SHARE * (w1 + w2):
        return {"value": "melee", "leaders": [acts[0]["name"], acts[1]["name"]]}
    return {"value": "duel", "a": acts[0]["name"], "b": acts[1]["name"]}


def _axis_counterfactual(data: dict) -> dict:
    """Ось 7. Что добавил сценарий сверх инерционного фона. Контрфакт к baseline."""
    comp = data.get("comparison", {})
    if "baseline_final" not in comp:
        return {"value": "background"}
    eff = comp.get("excess_final", 0.0)
    th = data.get("thresholds", {})
    tau = th.get("S2->S3")
    final = comp.get("final")
    b_final = comp.get("baseline_final")
    if eff > EPS:
        return {"value": "aggravating", "excess": eff}
    if eff < -EPS:
        held = (tau is not None and b_final is not None and final is not None
                and b_final >= tau and final < tau)
        if held:
            return {"value": "mitigating", "excess": eff}
        return {"value": "inertial", "excess": eff, "soft": True}
    return {"value": "inertial", "excess": eff}


def _axis_tempo(data: dict) -> dict:
    """Ось 8. Когда система выходит на пик. Год глобального максимума против
    динамического деления горизонта на трети."""
    tl = data.get("timeline", [])
    if len(tl) < 2:
        return {"value": None}
    tens = [r["tension"] for r in tl]
    imax = max(range(len(tens)), key=lambda i: tens[i])
    third = len(tens) / 3.0
    year = tl[imax]["year"]
    if imax < third:
        return {"value": "explosive", "year": year}
    if imax < 2 * third:
        return {"value": "linear", "year": year}
    return {"value": "delayed", "year": year}


def read_axes(data: dict) -> dict:
    """
    Главное чтение. Относит прогон к значениям восьми осей решётки и возвращает
    структуру, из которой текстовый слой соберёт суждение. Ничего не печатает.
    """
    return {
        "dominance": _axis_dominance(data),
        "direction": _axis_direction(data),
        "shape": _axis_shape(data),
        "safety": _axis_safety(data),
        "shift": _axis_shift(data),
        "actors": _axis_actors(data),
        "counterfactual": _axis_counterfactual(data),
        "tempo": _axis_tempo(data),
    }
