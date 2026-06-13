"""
Слой данных отчёта. Модуль 12, фундамент.

Извлекает из готового прогона всё, что повествовательный отчёт будет
описывать, и складывает в строгую структуру. Здесь нет генерации текста,
нет источников, нет графики. Только факты прогона, разложенные по трём
разделам разведывательного стандарта, что знаем, что думаем, чего не знаем.
Слой представления ляжет сверху отдельными модулями.

Разделение ответственности. Этот модуль ничего не вычисляет заново, он
агрегирует выводы аналитического слоя и поля траектории. Если число
расходится с дашбордом, ошибка не здесь, а в источнике, что упрощает поиск.
"""

from __future__ import annotations

from engine.analysis import classify, classify_threat_type, axis_scores_by_year
from engine.sources import sources_until
from engine.agents import AGENTS
from engine.judgment import read_axes
from engine.synthesis import LevelCoupling, aggregate, DEFAULT_BETA
from engine.influence import CODES


# Порог резкого сдвига напряжения за один год. Подобран так, чтобы отмечать
# переломы, но не реагировать на инерционное сползание.
_JUMP = 0.04


def _regime_label(code: str) -> str:
    """Человекочитаемое имя режима по коду S1, S2, S3."""
    return {"S1": "стабильный баланс", "S2": "холодная конфронтация",
            "S3": "каскадная дестабилизация"}.get(code, code)


def _timeline(traj, thresholds: dict) -> list:
    """Состояние системы по годам. Напряжение, режим, годовой сдвиг."""
    th12 = thresholds.get("S1->S2")
    th23 = thresholds.get("S2->S3")
    rows = []
    for i, year in enumerate(traj.years):
        tau = float(traj.tension[i])
        prev = float(traj.tension[i - 1]) if i > 0 else tau
        # Зона по порогам. Куда попадает напряжение этого года.
        if th23 is not None and tau >= th23:
            zone = "S3"
        elif th12 is not None and tau >= th12:
            zone = "S2"
        else:
            zone = "S1"
        rows.append({
            "year": year,
            "tension": tau,
            "delta": round(tau - prev, 4),
            "zone": zone,
            "regime": traj.dominant[i] if i < len(traj.dominant) else zone,
        })
    return rows


def _nodal_years(timeline: list) -> list:
    """
    Узловые годы для повествования. Точки, где система делает нечто
    качественное, пересекает порог, меняет режим или резко сдвигается.
    Именно сюда в готовом отчёте лягут врезки разбора и холмики.
    """
    nodes = []
    for i, row in enumerate(timeline):
        if i == 0:
            nodes.append({"year": row["year"], "kind": "старт",
                          "note": f"Отправная точка, напряжение {row['tension']:.3f}, "
                                  f"режим {_regime_label(row['regime'])}."})
            continue
        prev = timeline[i - 1]
        kinds = []
        if prev["zone"] != row["zone"]:
            arrow = "вверх" if row["zone"] > prev["zone"] else "вниз"
            kinds.append(f"транзит через критический порог {arrow}, "
                         f"{_regime_label(prev['zone'])} → {_regime_label(row['zone'])}")
        if prev["regime"] != row["regime"]:
            kinds.append(f"смена доминирующего режима на {_regime_label(row['regime'])}")
        if abs(row["delta"]) >= _JUMP:
            sign = "+" if row["delta"] > 0 else "−"
            term = "приращение" if row["delta"] > 0 else "редукция"
            kinds.append(f"экстремальное {term} системного напряжения "
                         f"(Δ = {sign}{abs(row['delta']):.3f})")
        if kinds:
            nodes.append({"year": row["year"], "kind": "; ".join(kinds),
                          "note": f"Напряжение {row['tension']:.3f}."})
    last = timeline[-1]
    nodes.append({"year": last["year"], "kind": "финал",
                  "note": f"Итог горизонта, напряжение {last['tension']:.3f}, "
                          f"режим {_regime_label(last['regime'])}."})
    return nodes


# Порог следа прямого шока. Скачок переменной за один год выше него выдаёт
# прямой экзогенный удар сценария, ниже остаётся реакцией через матрицу влияния.
# Прямые шоки каталога лежат в полосе от 0.05 до 0.30, реакция копится плавно,
# потому 0.10 отсекает реагента от инициатора. Авторский порог, защищается вслух.
_INIT_SHOCK = 0.10


def _actors(traj) -> list:
    """
    Действующие лица прогона. Протагонист отбирается в два сита. Сперва
    инициатива, затем вес. Инициатива отделяет субъекта сценария от реагента.
    Прямой экзогенный шок оставляет в траектории резкий годовой скачок
    переменной, тогда как реакция через матрицу влияния копится плавно. Агент
    без прямого удара есть реагент, он мог раскачаться сильно, но сюжета не вёл,
    и в протагонисты не проходит, как бы громко ни отзывался.

    Среди инициаторов ранжирование по сведённому весу. Громкость, совокупная
    величина действий milex rhet drift, поднимает того, кто давил весомо, но
    раздувает агента, простоявшего горизонт на старом максимуме. Сдвиг, путь
    состояния от старта к финалу, поднимает переломленного, но возносит мелкую
    дрожь. Вес есть среднее двух нормированных компонент поровну. Протагонисты
    суть два тяжелейших инициатора, прочее фон. Прямых ударов нет вовсе, значит
    нет и протагонистов, и это честное затишье.
    """
    states = getattr(traj, "agent_states", {}) or {}
    actions = getattr(traj, "agent_actions", {}) or {}
    codes = list(states.keys()) or list(actions.keys())
    loud, shift, initiative = {}, {}, {}
    for c in codes:
        acts = actions.get(c, [])
        loud[c] = sum(abs(a.get("milex", 0)) + abs(a.get("rhet", 0))
                      + abs(a.get("drift", 0)) for a in acts)
        st = states.get(c, [])
        if len(st) >= 2:
            s0, s1 = st[0], st[-1]
            shift[c] = sum(abs(s1[k] - s0[k]) for k in range(3))
        else:
            shift[c] = 0.0
        # След прямого удара. Наибольший скачок любой переменной за один год.
        jump = 0.0
        for t in range(1, len(st)):
            for k in range(3):
                jump = max(jump, abs(st[t][k] - st[t - 1][k]))
        initiative[c] = jump
    lmax = max(loud.values()) if loud else 0.0
    smax = max(shift.values()) if shift else 0.0
    rows = []
    for c in codes:
        ln = (loud[c] / lmax) if lmax > 0 else 0.0
        sn = (shift[c] / smax) if smax > 0 else 0.0
        st = states.get(c, [])
        start_z = [round(float(v), 3) for v in st[0]] if st else None
        rows.append({
            "code": c,
            "name": AGENTS[c].name if c in AGENTS else c,
            "start_z": start_z,
            "loudness": round(loud[c], 4), "shift": round(shift[c], 4),
            "loud_norm": round(ln, 4), "shift_norm": round(sn, 4),
            "weight": round((ln + sn) / 2, 4),
            "initiative": round(initiative[c], 4),
            "initiator": initiative[c] >= _INIT_SHOCK - 1e-9,
        })
    rows.sort(key=lambda r: r["weight"], reverse=True)
    # Протагонисты только среди инициаторов, потолок два. Реагент не проходит,
    # как бы сильно его ни раскачало через матрицу влияния.
    initiators = [r for r in rows if r["initiator"]]
    protag = {r["code"] for r in initiators[:2]}
    for i, r in enumerate(rows):
        r["rank"] = i + 1
        r["is_protagonist"] = r["code"] in protag
    return rows


def _drivers(traj, threat_type: dict) -> dict:
    """
    Что тащит систему. Вклад трёх осей из классификатора плюс ключевые
    агенты, чья активность весит в синтезе тяжелее прочих.
    """
    scores = threat_type.get("scores", {})
    total = sum(scores.values()) or 1.0
    shares = {k: round(v / total, 3) for k, v in scores.items()}
    ordered = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)
    # Средняя нормативная эрозия Японии за горизонт, ключевой узел работы.
    jp_states = traj.agent_states.get("jpn", [])
    jp_erosion = (sum(s[2] for s in jp_states) / len(jp_states)) if jp_states else None
    # Средняя совокупная активность КНР, первичный источник давления.
    cn_actions = traj.agent_actions.get("chn", [])
    cn_milex = (sum(a["milex"] for a in cn_actions) / len(cn_actions)) if cn_actions else None
    return {
        "axis_scores": scores,
        "axis_shares": shares,
        "axis_ranked": ordered,
        "dominant_axis": threat_type.get("type"),
        "japan_mean_erosion": round(jp_erosion, 3) if jp_erosion is not None else None,
        "china_mean_milex": round(cn_milex, 3) if cn_milex is not None else None,
    }


def _comparison(traj, baseline, thresholds: dict) -> dict:
    """
    Сравнение с инерционным фоном и положение относительно порога срыва.
    Отвечает на вопрос, что добавили именно заданные шоки сверх дрейфа.
    """
    final = float(traj.tension[-1]) if traj.tension else 0.0
    peak = max((float(x) for x in traj.tension), default=0.0)
    th23 = thresholds.get("S2->S3")
    out = {
        "final": round(final, 4),
        "peak": round(peak, 4),
        "gap_to_collapse": round(th23 - peak, 4) if th23 is not None else None,
    }
    if baseline is not None and getattr(baseline, "tension", None):
        b_final = float(baseline.tension[-1])
        b_peak = max(float(x) for x in baseline.tension)
        out["baseline_final"] = round(b_final, 4)
        out["baseline_peak"] = round(b_peak, 4)
        out["excess_final"] = round(final - b_final, 4)
        out["excess_peak"] = round(peak - b_peak, 4)
    return out


def _events(traj) -> list:
    """
    Шоки сценария по годам из лога траектории. Год абсолютный, описание
    человекочитаемое. Дёрнутая переменная z идёт параллельным списком event_vars
    в том же порядке, чтобы основной лог остался двухэлементным и не ломал
    распаковку на дашборде. Если параллельного списка нет, переменная пуста.
    """
    log = list(getattr(traj, "events_log", []))
    evars = list(getattr(traj, "event_vars", []))
    out = []
    for i, rec in enumerate(log):
        year, description = rec[0], rec[1]
        variable = evars[i] if i < len(evars) else None
        out.append({"year": year, "description": description, "variable": variable})
    return out


def _gaps(traj, thresholds: dict, base_year: int) -> list:
    """
    Чего мы не знаем. Раздел неопределённости по разведывательному стандарту.
    Часть оговорок постоянна и держит честность модели, часть рождается из
    конкретного прогона, например близость к порогу.
    """
    gaps = [
        "Фиксация параметров агентов в рамках исторической калибровки обусловлена "
        "необходимостью верификации базового латентного тренда подсистемы. При "
        "возникновении экзогенных шоков, выходящих за пределы заданного каталога, "
        "реальные траектории акторов могут демонстрировать структурные девиации.",
        "Параметризация перцептивного контура и весов влияния опирается на "
        "экспертно-аналитическое структурирование верифицированных источников, "
        "что обеспечивает репрезентативность качественного профиля модели.",
        "Качественное ядро вывода устойчиво к вариации весов синтез-формулы, "
        "ранжирование сценариев по степени риска и недостижимость зоны разрядки "
        "сохраняются при возмущении параметров. Абсолютное же положение траектории "
        "относительно порога каскадной дестабилизации чувствительно к калибровке и "
        "потому трактуется в условном модусе, как сценарно обусловленная граница "
        "устойчивости, а не безусловный прогноз.",
    ]
    # Специфичная оговорка. Если финал близок к порогу, вывод требует условного модуса.
    th23 = thresholds.get("S2->S3")
    if th23 is not None and traj.tension:
        final = float(traj.tension[-1])
        if abs(final - th23) <= 0.05:
            gaps.append(
                f"Локализация финального напряжения ({final:.3f}) в непосредственной "
                f"близости от теоретического порога каскадной дестабилизации "
                f"({th23:.3f}) указывает на высокую чувствительность системы к малым "
                f"приращениям входных переменных. Данное обстоятельство "
                f"предопределяет использование условного аналитического модуса при "
                f"формулировании долгосрочных качественных выводов в исследуемой зоне.")
    return gaps


def _trace_at(traj, k: int) -> dict:
    """
    Разбор синтеза для заданного шага k. Движок не правится, разбор
    воспроизводится прокруткой свежей связки по сохранённым действиям и
    совпадает с живым напряжением до машинной точности.
    """
    actions_log = getattr(traj, "agent_actions", {}) or {}
    states_log = getattr(traj, "agent_states", {}) or {}
    years = list(traj.years)
    codes = [c for c in CODES if c in actions_log and c in states_log]
    if not codes or k < 0 or k >= len(years):
        return None
    coup = LevelCoupling()
    warm = {c: {kk: actions_log[c][0][kk] for kk in ("milex", "rhet", "drift")}
            for c in codes}
    coup.memory.seed(aggregate(warm, coup.weights))
    for j in range(k):
        coup.memory.update(aggregate({c: actions_log[c][j] for c in codes}, coup.weights))
    a = {c: actions_log[c][k] for c in codes}
    s = {c: states_log[c][k] for c in codes}
    ex = coup.explain(a, s)
    b = DEFAULT_BETA
    sm = ex["smoothed"]
    material_term = b["milex"] * sm["milex"] + b["rhet"] * sm["rhet"] + b["drift"] * sm["drift"]
    pressure_term = b["pressure"] * ex["perceptual_pressure"]
    return {
        "year": years[k],
        "perceptual_pressure": round(ex["perceptual_pressure"], 4),
        "material_term": round(material_term, 4),
        "pressure_term": round(pressure_term, 4),
        "sigmoid_arg": round(ex["sigmoid_arg"], 4),
        "tension": round(ex["tension"], 4),
    }


# Порог содержательного перелома. Скачок ниже него считается прогревом памяти
# или плавной динамикой, а не структурным переломом, и расчёт к нему не вяжется.
_PIVOT_JUMP = 0.035


def _synthesis_points(traj) -> dict:
    """
    Дозированный расчётный слой. Разбор итогового напряжения присутствует
    всегда, ибо итог есть главный довод отчёта. Разбор переломного года
    добавляется только при содержательном резком переломе, не в годы прогрева и
    не на финале, иначе он сел бы на искусственный ранний скачок ровного
    сценария. Робастно к горизонту, на коротком прогоне перелом просто пуст.
    """
    years = list(traj.years)
    tens = list(traj.tension)
    H = len(years)
    if H == 0:
        return {"final": None, "pivot": None}
    final = _trace_at(traj, H - 1)
    pivot = None
    if H >= 4:
        deltas = [abs(tens[i] - tens[i - 1]) for i in range(1, H)]
        mx = max(deltas) if deltas else 0.0
        kmax = deltas.index(mx) + 1
        if mx >= _PIVOT_JUMP and 2 <= kmax <= H - 2:
            pivot = _trace_at(traj, kmax)
    return {"final": final, "pivot": pivot}


def build_report_data(traj, scenario, thresholds: dict, base_year: int = 2026,
                      baseline=None) -> dict:
    """
    Главная сборка. Возвращает структуру отчёта по разведывательному
    стандарту, что знаем, что думаем, чего не знаем, плюс узловые годы для
    врезок. Если передан инерционный baseline, добавляется сравнение фона.
    Текст и источники накладываются последующими модулями.
    """
    timeline = _timeline(traj, thresholds)
    verdict = classify(traj, thresholds)
    threat_type = classify_threat_type(traj, baseline=baseline)
    data = {
        "meta": {
            "scenario": getattr(scenario, "name", "сценарий"),
            "scenario_description": getattr(scenario, "description", ""),
            "base_year": traj.years[0] if traj.years else base_year,
            "final_year": traj.years[-1] if traj.years else base_year,
            "horizon": len(traj.years),
            "years": list(traj.years),
        },
        # Что думаем. Вывод модели.
        "verdict": verdict,
        "threat_type": threat_type,
        "thresholds": {k: (round(float(v), 4) if v is not None else None)
                       for k, v in thresholds.items()},
        "timeline": timeline,
        "nodal_years": _nodal_years(timeline),
        "drivers": _drivers(traj, threat_type),
        "actors": _actors(traj),
        "comparison": _comparison(traj, baseline, thresholds),
        # Что знаем. Заданные сценарием толчки и выверенные источники.
        # Источники охватывают все состоявшиеся факты вплоть до настоящего,
        # независимо от стартового года симуляции, поскольку обоснование
        # калибровки опирается на всё известное на момент сборки.
        "events": _events(traj),
        "sources": sources_until(2026),
        # Чего не знаем.
        "gaps": _gaps(traj, thresholds, base_year),
    }
    # Погодовая раскладка осей давления для оси смены природы давления.
    data["axis_by_year"] = axis_scores_by_year(traj, baseline=baseline)
    # Дозированный расчётный слой. Разбор итогового напряжения всегда, разбор
    # переломного года при содержательном переломе. Восстановлен из траектории.
    data["synthesis"] = _synthesis_points(traj)
    # Суждение по решётке. Читается из уже собранных данных, оттого ставится
    # последним, когда timeline, comparison, drivers, actors и thresholds готовы.
    data["judgment"] = read_axes(data)
    return data
