"""
Аналитический вывод. Превращение траектории в вердикт на естественном языке.

Здесь сырые числа прогона читаются как заключение: уровень тревоги по логике
светофора и текст, объясняющий, почему уровень такой. Логика отделена от
интерфейса, оттого проверяема и переносима.
"""

from __future__ import annotations


def classify(trajectory, thresholds: dict) -> dict:
    """
    Возвращает вердикт по траектории.

    level   green, amber или red
    title   краткое заключение
    text    объяснение из чисел
    risk    итоговая масса дестабилизации
    peak    пиковое напряжение
    breaches_collapse  пробивает ли пик порог срыва
    """
    risk = float(trajectory.regime_dist[-1][2])
    peak = float(max(trajectory.tension))
    final = trajectory.dominant[-1]
    th23 = thresholds.get("S2->S3", 0.676)
    th12 = thresholds.get("S1->S2", 0.324)
    breaches = bool(peak >= th23)

    if final == "S3" or risk >= 0.45 or breaches:
        level, title = "red", "Высокий риск, требуется внимание"
    elif final == "S2" or risk >= 0.28 or peak >= (th12 + th23) / 2:
        level, title = "amber", "Умеренный риск, наблюдение"
    else:
        level, title = "green", "Стабильно, пространство для долгой игры"

    s1 = f"К концу горизонта риск дестабилизации составляет {risk * 100:.0f} процентов."
    if breaches:
        s2 = f"В пике напряжение пробивает порог срыва {th23:.3f}."
    else:
        s2 = f"Пик напряжения {peak:.3f} остаётся ниже порога срыва {th23:.3f}."
    if level == "red":
        s3 = "Обстановка требует оперативного решения, долгосрочные стратегии вторичны."
    elif level == "amber":
        s3 = "Устойчивая конфронтация без открытого срыва, нужен присмотр."
    else:
        s3 = "Силы уравновешены, допустимы долгосрочные стратегии."

    return {
        "level": level,
        "title": title,
        "text": " ".join([s1, s2, s3]),
        "risk": risk,
        "peak": peak,
        "final_regime": final,
        "breaches_collapse": breaches,
    }


# --- Классификация сценария по доминирующему типу угрозы ---

THREAT_TYPES = {
    "material": "Материальная гонка",
    "alliance": "Обвал доверия",
    "normative": "Нормативный распад",
    "mixed": "Смешанный профиль",
}


def _axis_scores(trajectory) -> dict:
    """Площадь отклонения по трём осям за горизонт, нормированная."""
    from engine.influence import CODES
    threat_area = trust_area = erosion_area = 0.0
    for c in CODES:
        states = trajectory.agent_states[c]
        z1_0, z2_0, z3_0 = states[0]
        for z1, z2, z3 in states:
            threat_area += max(0.0, z1 - z1_0)
            trust_area += max(0.0, z2_0 - z2)
            erosion_area += max(0.0, z3 - z3_0)
    horizon = len(trajectory.agent_states[CODES[0]]) * len(CODES)
    return {"material": threat_area / horizon,
            "alliance": trust_area / horizon,
            "normative": erosion_area / horizon}


def classify_threat_type(trajectory, baseline=None) -> dict:
    """
    Относит сценарий к доминирующему типу угрозы по трём осям безопасности.
    Материальная гонка через рост восприятия угрозы, обвал доверия через
    падение доверия, нормативный распад через рост эрозии.

    Если передан инерционный baseline, классификация ведётся по избытку над
    ним. Это вычитает фоновую дилемму безопасности, которая поднимает угрозу
    почти одинаково во всех сценариях, и обнажает специфический драйвер.
    """
    raw = _axis_scores(trajectory)
    if baseline is not None:
        base = _axis_scores(baseline)
        scores = {k: max(0.0, raw[k] - base[k]) for k in raw}
    else:
        scores = raw

    top_key = max(scores, key=scores.get)
    top_val = scores[top_key]
    runner = sorted(scores.values(), reverse=True)[1]

    if top_val < 0.015 or (top_val - runner) < 0.008:
        kind = "mixed"
    else:
        kind = top_key

    names = {
        "material": "ростом восприятия угрозы и гонкой вооружений",
        "alliance": "обвалом доверия к союзникам",
        "normative": "нормативным распадом, эрозией ограничений на силу",
        "mixed": "сразу по нескольким осям без явного лидера",
    }
    text = (f"Сценарий развивается преимущественно {names[kind]}. "
            f"Сдвиги осей за горизонт: угроза {scores['material']:+.2f}, "
            f"доверие {-scores['alliance']:+.2f}, эрозия {scores['normative']:+.2f}.")

    return {"type": kind, "label": THREAT_TYPES[kind], "text": text, "scores": scores}
