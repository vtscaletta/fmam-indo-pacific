"""
Расчёт согласия кодировщиков.

Мера согласия. Взвешенная каппа с квадратичным взвешиванием. Обычная каппа
считает всякое расхождение одинаково тяжёлым, тогда как шкала уровней
враждебности упорядочена, и расхождение на два уровня тяжелее расхождения
на один. Квадратичное взвешивание учитывает это различие.

Устройство меры. Из наблюдаемого несогласия вычитается то несогласие,
какое возникло бы при независимом проставлении отметок с теми же
частотами. Единица означает полное совпадение, ноль означает совпадение не
лучше случайного, отрицательные значения означают систематическое
расхождение.

Доверительный интервал строится способом повторной выборки с
возвращением, поскольку распределение каппы при малых наборах от
нормального отличается. Число повторов и зерно объявлены, отчего интервал
воспроизводим.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

SEED = 20260101
BOOTSTRAP = 5000
THRESHOLD = 0.70
"""Порог приемлемости, объявленный до расчёта."""


@dataclass(frozen=True)
class Agreement:
    """Согласие двух кодировщиков."""
    left: str
    right: str
    kappa: float
    lower: float
    upper: float
    n: int
    exact: float
    within_one: float

    def verdict(self, threshold: float = THRESHOLD) -> str:
        return "принято" if self.kappa >= threshold else "не принято"


def _weights(k: int) -> np.ndarray:
    """Матрица квадратичных весов расхождения."""
    i = np.arange(k).reshape(-1, 1)
    j = np.arange(k).reshape(1, -1)
    return ((i - j) ** 2) / ((k - 1) ** 2)


def weighted_kappa(a: list[int], b: list[int], k: int = 5) -> float:
    """
    Взвешенная каппа двух рядов отметок.

    Ряды обязаны быть одинаковой длины и содержать отметки от нуля до k-1.
    """
    if len(a) != len(b):
        raise ValueError("ряды разной длины")
    n = len(a)
    if n == 0:
        raise ValueError("пустые ряды")
    w = _weights(k)

    obs = np.zeros((k, k))
    for x, y in zip(a, b):
        obs[x, y] += 1
    obs /= n

    pa = np.bincount(a, minlength=k) / n
    pb = np.bincount(b, minlength=k) / n
    exp = np.outer(pa, pb)

    denom = float((w * exp).sum())
    if denom == 0.0:
        return 1.0 if float((w * obs).sum()) == 0.0 else 0.0
    return 1.0 - float((w * obs).sum()) / denom


def bootstrap_ci(a: list[int], b: list[int], k: int = 5,
                 repeats: int = BOOTSTRAP,
                 seed: int = SEED) -> tuple[float, float]:
    """Доверительный интервал каппы способом повторной выборки."""
    rnd = random.Random(seed)
    n = len(a)
    vals = []
    for _ in range(repeats):
        idx = [rnd.randrange(n) for _ in range(n)]
        sa = [a[i] for i in idx]
        sb = [b[i] for i in idx]
        if len(set(sa)) == 1 and len(set(sb)) == 1:
            continue
        vals.append(weighted_kappa(sa, sb, k))
    if not vals:
        return (float("nan"), float("nan"))
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[int(0.975 * len(vals)) - 1]
    return (lo, hi)


def compare(name_a: str, a: list[int], name_b: str, b: list[int],
            k: int = 5) -> Agreement:
    """Полное сравнение двух кодировщиков."""
    kappa = weighted_kappa(a, b, k)
    lo, hi = bootstrap_ci(a, b, k)
    exact = sum(1 for x, y in zip(a, b) if x == y) / len(a)
    near = sum(1 for x, y in zip(a, b) if abs(x - y) <= 1) / len(a)
    return Agreement(left=name_a, right=name_b, kappa=kappa, lower=lo,
                     upper=hi, n=len(a), exact=exact, within_one=near)


def confusion(a: list[int], b: list[int], k: int = 5) -> np.ndarray:
    """Матрица совпадений отметок двух кодировщиков."""
    m = np.zeros((k, k), dtype=int)
    for x, y in zip(a, b):
        m[x, y] += 1
    return m


def disagreements(ids: list[str], coders: dict[str, list[int]],
                  minimum: int = 1) -> list[tuple[str, dict[str, int], int]]:
    """
    Единицы, где кодировщики разошлись, по убыванию размаха.

    Размах есть разность наибольшей и наименьшей отметки. Служит для
    разбора того, на каких именно разрядах правило оказалось
    двусмысленным.
    """
    out = []
    names = list(coders)
    for i, ident in enumerate(ids):
        vals = {c: coders[c][i] for c in names}
        span = max(vals.values()) - min(vals.values())
        if span >= minimum:
            out.append((ident, vals, span))
    return sorted(out, key=lambda x: -x[2])


def report(ids: list[str], coders: dict[str, list[int]],
           k: int = 5) -> str:
    """Печатный отчёт о согласии для приложения к работе."""
    names = list(coders)
    lines = [f"Единиц закодировано {len(ids)}", ""]
    lines.append("Распределение отметок по кодировщикам")
    head = f"{'уровень':10}" + "".join(f"{c:>12}" for c in names)
    lines.append(head)
    for lvl in range(k):
        row = "".join(f"{sum(1 for v in coders[c] if v == lvl):>12}"
                      for c in names)
        lines.append(f"{lvl:<10}" + row)
    lines.append("")
    lines.append("Попарное согласие")
    lines.append(f"{'пара':28}{'каппа':>8}{'интервал':>18}"
                 f"{'точных':>9}{'в пределах 1':>14}{'вердикт':>12}")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            g = compare(names[i], coders[names[i]],
                        names[j], coders[names[j]], k)
            pair = f"{g.left} и {g.right}"
            lines.append(
                f"{pair:28}{g.kappa:>8.3f}"
                f"{f'[{g.lower:.2f}, {g.upper:.2f}]':>18}"
                f"{g.exact * 100:>8.0f}%{g.within_one * 100:>13.0f}%"
                f"{g.verdict():>12}")
    return "\n".join(lines)
