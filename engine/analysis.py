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
