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
    """
    Площадь отклонения по трём осям за горизонт, взвешенная по влиянию агента.
    Сдвиг у тяжёлого игрока весит больше, чем у малого, оттого эскалация КНР
    не тонет в усреднении по мелким государствам.
    """
    from engine.influence import CODES
    from engine.synthesis import influence_weights
    w = influence_weights()
    threat_area = trust_area = erosion_area = 0.0
    for c in CODES:
        states = trajectory.agent_states[c]
        z1_0, z2_0, z3_0 = states[0]
        for z1, z2, z3 in states:
            threat_area += w[c] * max(0.0, z1 - z1_0)
            trust_area += w[c] * max(0.0, z2_0 - z2)
            erosion_area += w[c] * max(0.0, z3 - z3_0)
    years = len(trajectory.agent_states[CODES[0]])
    return {"material": threat_area / years,
            "alliance": trust_area / years,
            "normative": erosion_area / years}


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

    names = {
        "material": "ростом восприятия угрозы и гонкой вооружений",
        "alliance": "обвалом доверия к союзникам",
        "normative": "нормативным распадом, эрозией ограничений на применение силы",
    }

    # Два разных смешанных случая, которые нельзя путать.
    # Околофоновый: события слабо отклоняют систему или взаимно гасятся.
    # Многоосевой: несколько осей растут сопоставимо, без явного лидера.
    near_background = (baseline is not None) and (top_val < 0.015)
    no_leader = (top_val - runner) < 0.008

    if near_background:
        kind = "mixed"
        text = ("События слабо отклоняют систему от инерционного фона либо "
                "взаимно гасят друг друга. Выраженного типа угрозы нет, "
                "динамика близка к естественному дрейфу.")
    elif no_leader:
        kind = "mixed"
        text = ("Несколько осей смещаются сопоставимо, без явного лидера. "
                "Профиль комбинированный, угроза, доверие и эрозия сдвигаются "
                "соизмеримо.")
    else:
        kind = top_key
        ref = " над инерционным фоном" if baseline is not None else ""
        text = (f"Сценарий развивается преимущественно {names[kind]}. "
                f"Избыток{ref} по ведущей оси составляет {top_val:.2f}.")

    return {"type": kind, "label": THREAT_TYPES[kind], "text": text, "scores": scores}
