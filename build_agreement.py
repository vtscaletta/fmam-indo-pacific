"""
Расчёт согласия кодировщиков.

Запуск из корня хранилища.

    python build_agreement.py data/Ответы_кодировщиков.xlsx

Читает таблицу отметок, вычисляет попарное согласие и печатает отчёт,
пригодный для перенесения в раздел 2.2 и в приложение.

Устройство таблицы. Первый столбец содержит опознаватель единицы, прочие
столбцы содержат отметки кодировщиков, по столбцу на кодировщика. Заголовок
столбца служит наименованием кодировщика. Единицы с непроставленной отметкой
хотя бы у одного кодировщика из расчёта исключаются, и число таковых
объявляется.

Принимаются таблицы в разрядах xlsx и csv. Разряд определяется по окончанию
имени.

Порог приемлемости не объявляется намеренно. Каппа приводится с
доверительным интервалом и долями совпадений, истолкование даётся по
принятой градации.
"""
from __future__ import annotations

import sys
from pathlib import Path

from engine.measurement.agreement import (
    compare, confusion, disagreements,
)

LEVELS = 5
"""Число разрядов шкалы уровней враждебности, от нуля до четырёх."""


def read_table(path: str | Path) -> tuple[list[str], dict[str, list]]:
    """
    Читает таблицу отметок.

    Возвращает опознаватели единиц и словарь кодировщика с рядом его отметок.
    Ряды выдаются в порядке следования строк таблицы, отчего расчёт
    воспроизводим.
    """
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Таблица не найдена, {p}")

    if p.suffix.lower() in (".xlsx", ".xlsm"):
        rows = _read_xlsx(p)
    elif p.suffix.lower() in (".csv", ".tsv"):
        rows = _read_csv(p)
    else:
        raise SystemExit(f"Разряд таблицы неизвестен, {p.suffix}")

    if not rows:
        raise SystemExit("Таблица пуста")

    header = rows[0]
    coders = [str(h).strip() for h in header[1:] if h is not None
              and str(h).strip()]
    if len(coders) < 2:
        raise SystemExit("Кодировщиков менее двух, согласие не вычисляется")

    ids: list[str] = []
    marks: dict[str, list[int]] = {c: [] for c in coders}
    skipped: list[str] = []

    for row in rows[1:]:
        if not row or row[0] is None or not str(row[0]).strip():
            continue
        ident = str(row[0]).strip()
        values = []
        complete = True
        for i, _ in enumerate(coders, start=1):
            cell = row[i] if i < len(row) else None
            if cell is None or str(cell).strip() == "":
                complete = False
                break
            try:
                v = int(round(float(str(cell).replace(",", "."))))
            except ValueError:
                complete = False
                break
            if not 0 <= v <= LEVELS - 1:
                raise SystemExit(
                    f"Единица {ident}, отметка {v} вне разрядов "
                    f"0..{LEVELS - 1}")
            values.append(v)
        if not complete:
            skipped.append(ident)
            continue
        ids.append(ident)
        for c, v in zip(coders, values):
            marks[c].append(v)

    if skipped:
        print(f"Единиц с непроставленной отметкой {len(skipped)}, "
              f"из расчёта исключены.")
        print(f"  {', '.join(skipped[:20])}"
              f"{' и прочие' if len(skipped) > 20 else ''}")
        print()

    if not ids:
        raise SystemExit("Полностью закодированных единиц нет")
    return ids, marks


def _read_xlsx(p: Path) -> list[list]:
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("Для чтения xlsx нужен openpyxl, "
                         "установите его командой pip install openpyxl")
    wb = openpyxl.load_workbook(p, data_only=True)
    ws = wb.worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _read_csv(p: Path) -> list[list]:
    import csv
    delim = "\t" if p.suffix.lower() == ".tsv" else ","
    with p.open(encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.reader(f, delimiter=delim)]


SCALES = {
    "Лэндис и Кох": (
        (0.81, "почти полное"),
        (0.61, "существенное"),
        (0.41, "умеренное"),
        (0.21, "слабое"),
        (0.00, "незначительное"),
    ),
    "Криппендорф": (
        (0.800, "пригодно для твёрдых выводов"),
        (0.667, "пригодно для предварительных выводов"),
        (0.000, "непригодно"),
    ),
    "Мак-Хью": (
        (0.90, "почти полное"),
        (0.80, "сильное"),
        (0.60, "умеренное"),
        (0.00, "недостаточное"),
    ),
}
"""
Три ходовые шкалы истолкования согласия.

Приводятся все три намеренно. Общепринятой отсечки не существует, шкалы между
собою не согласуются, и выбор одной из них есть выбор исследователя, который
надлежит оставить читателю, а не совершать за него. Ладбрук указывает, что
шкала Лэндиса и Коха здравого теоретического основания не имеет; Криппендорф
предлагает более строгие рубежи; Мак-Хью полагает недостаточным всё, что ниже
шести десятых.
"""

LOWER_BOUND_TEST = 0.60
"""
Рубеж строгой проверки существенности.

Существенность признаётся доказанной, если нижняя граница доверительного
интервала лежит выше рубежа. Требование строже сравнения точечной оценки с
отсечкой, поскольку учитывает неопределённость самой оценки.
"""


def read_scale(kappa: float, scale) -> str:
    """Разряд, к которому значение относится по данной шкале."""
    for bound, name in scale:
        if kappa >= bound:
            return name
    return "отрицательное"


def scales_reading(results) -> None:
    """
    Истолкование полученных значений по трём шкалам и строгая проверка.

    Печатается разряд по каждой шкале и отдельно исход проверки по нижней
    границе доверительного интервала.
    """
    print("ИСТОЛКОВАНИЕ ПО ТРЁМ ШКАЛАМ")
    print()
    for g in results:
        pair = f"{g.left} и {g.right}"
        print(f"  {pair}, каппа {g.kappa:.3f}")
        for name, scale in SCALES.items():
            print(f"      {name:16} {read_scale(g.kappa, scale)}")
        print()

    print("СТРОГАЯ ПРОВЕРКА ПО НИЖНЕЙ ГРАНИЦЕ ИНТЕРВАЛА")
    print()
    print(f"  Существенность признаётся доказанной, если нижняя граница")
    print(f"  доверительного интервала лежит выше {LOWER_BOUND_TEST:.2f}.")
    print()
    passed = 0
    for g in results:
        ok = g.lower > LOWER_BOUND_TEST
        passed += ok
        pair = f"{g.left} и {g.right}"
        verdict = "доказана" if ok else "не доказана"
        print(f"  {pair:34} нижняя граница {g.lower:.3f}, {verdict}")
    print()
    if passed == 0:
        print("  Ни у одной пары строгая проверка не пройдена. Точечные")
        print("  оценки существенность показывают, однако при учёте")
        print("  неопределённости самой оценки она не доказана.")
        print("  Обстоятельство подлежит объявлению.")
    elif passed < len(results):
        print(f"  Строгую проверку прошли {passed} пар из {len(results)}.")
    else:
        print("  Строгую проверку прошли все пары.")
    print()


def boundaries(ids: list[str], marks: dict[str, list[int]],
               levels: int = LEVELS) -> None:
    """
    Разбор того, на каких границах шкалы сосредоточены расхождения.

    Мера согласия сама по себе говорит лишь, насколько кодировщики сошлись,
    но не говорит, где именно разошлись. Между тем расхождение, рассеянное по
    всей шкале, и расхождение, сосредоточенное на одной или двух границах,
    означают разное. Первое указывает на неопределённость правила вообще,
    второе на двусмысленность в названных точках, устранимую уточнением
    инструкции.

    Печатается распределение расхождений по парам разрядов, отдельно по
    каждой паре кодировщиков и в совокупности.
    """
    from collections import Counter

    names = list(marks)
    total: Counter = Counter()

    print("СОСРЕДОТОЧЕНИЕ РАСХОЖДЕНИЙ ПО ГРАНИЦАМ ШКАЛЫ")
    print()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            c: Counter = Counter()
            for x, y in zip(marks[a], marks[b]):
                if x != y:
                    key = (min(x, y), max(x, y))
                    c[key] += 1
                    total[key] += 1
            s = sum(c.values())
            print(f"  {a} и {b}, расхождений {s} из {len(ids)}")
            for (lo, hi), n in c.most_common():
                print(f"      {lo} против {hi}: {n} "
                      f"({n / s * 100:.0f} процентов)")
            print()

    s = sum(total.values())
    if not s:
        print("  Расхождений нет.")
        return

    print(f"  По всем парам, расхождений {s}")
    for (lo, hi), n in total.most_common():
        print(f"      {lo} против {hi}: {n} ({n / s * 100:.0f} процентов)")
    print()

    top = total.most_common(2)
    covered = sum(n for _, n in top)
    print(f"  На две наиболее частые границы приходится "
          f"{covered / s * 100:.0f} процентов расхождений.")
    adjacent = sum(n for (lo, hi), n in total.items() if hi - lo == 1)
    print(f"  На смежные разряды приходится "
          f"{adjacent / s * 100:.0f} процентов расхождений.")
    print()
    if covered / s > 0.8:
        print("  Расхождение сосредоточено, а не рассеяно. Двусмысленность")
        print("  правила приурочена к названным границам и устраняется их")
        print("  уточнением, а не пересмотром инструкции целиком.")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Укажите таблицу отметок, "
                         "например python build_agreement.py "
                         "data/coders.xlsx")

    ids, marks = read_table(sys.argv[1])
    names = list(marks)

    print("СОГЛАСИЕ КОДИРОВЩИКОВ")
    print()
    print(f"  единиц в расчёте {len(ids)}")
    print(f"  кодировщиков {len(names)}, а именно {', '.join(names)}")
    print(f"  разрядов шкалы {LEVELS}, от 0 до {LEVELS - 1}")
    print(f"  мера согласия, каппа с квадратичным взвешиванием")
    print(f"  интервал построен повторной выборкой с возвращением")
    print()

    print("РАСПРЕДЕЛЕНИЕ ОТМЕТОК")
    print(f"{'разряд':>8}" + "".join(f"{c:>14}" for c in names))
    for lvl in range(LEVELS):
        row = "".join(f"{sum(1 for v in marks[c] if v == lvl):>14}"
                      for c in names)
        print(f"{lvl:>8}" + row)
    print()

    print("ПОПАРНОЕ СОГЛАСИЕ")
    print(f"{'пара':30}{'каппа':>8}{'интервал':>18}{'точных':>9}"
          f"{'в пределах 1':>14}{'разряд':>17}")
    results = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            g = compare(names[i], marks[names[i]],
                        names[j], marks[names[j]], LEVELS)
            results.append(g)
            pair = f"{g.left} и {g.right}"
            interval = f"[{g.lower:.3f}, {g.upper:.3f}]"
            print(f"{pair:30}{g.kappa:>8.3f}{interval:>18}"
                  f"{g.exact * 100:>8.0f}%{g.within_one * 100:>13.0f}%"
                  f"{g.verdict():>17}")
    print()

    kappas = [g.kappa for g in results]
    exacts = [g.exact for g in results]
    nears = [g.within_one for g in results]
    lowers = [g.lower for g in results]
    uppers = [g.upper for g in results]

    print("СВОДНОЕ ЧТЕНИЕ")
    print()
    print(f"  Каппа от {min(kappas):.3f} до {max(kappas):.3f}.")
    print(f"  Доверительные интервалы от {min(lowers):.3f} "
          f"до {max(uppers):.3f}.")
    print(f"  Доля точных совпадений от {min(exacts) * 100:.0f} "
          f"до {max(exacts) * 100:.0f} процентов.")
    print(f"  Доля совпадений в пределах одного разряда от "
          f"{min(nears) * 100:.0f} до {max(nears) * 100:.0f} процентов.")
    print()
    print("  Единый порог приемлемости не объявляется, поскольку")
    print("  общепринятой отсечки не существует, а ходовые шкалы между")
    print("  собою не согласуются. Истолкование приводится по трём шкалам,")
    print("  отчего выбор остаётся за читателем.")
    print()

    scales_reading(results)

    boundaries(ids, marks)
    print()

    print("РАСХОЖДЕНИЯ, по убыванию размаха")
    diffs = disagreements(ids, marks, minimum=1)
    print(f"  единиц с расхождением {len(diffs)} из {len(ids)}")
    span_two = [d for d in diffs if d[2] >= 2]
    print(f"  из них с размахом два разряда и более {len(span_two)}")
    print()
    print(f"{'единица':16}" + "".join(f"{c:>14}" for c in names)
          + f"{'размах':>9}")
    for ident, vals, span in diffs[:25]:
        print(f"{ident:16}" + "".join(f"{vals[c]:>14}" for c in names)
              + f"{span:>9}")
    if len(diffs) > 25:
        print(f"  и ещё {len(diffs) - 25} единиц с расхождением")
    print()

    print("МАТРИЦЫ СОВПАДЕНИЙ")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            m = confusion(marks[names[i]], marks[names[j]], LEVELS)
            print(f"  {names[i]} по строкам, {names[j]} по столбцам")
            print("       " + "".join(f"{k:>6}" for k in range(LEVELS)))
            for k in range(LEVELS):
                print(f"  {k:<5}" + "".join(f"{int(m[k][q]):>6}"
                                            for q in range(LEVELS)))
            print()


if __name__ == "__main__":
    main()
