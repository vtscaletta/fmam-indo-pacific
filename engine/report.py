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

from engine.analysis import classify, classify_threat_type


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
            kinds.append(f"переход порога {arrow}, {_regime_label(prev['zone'])} "
                         f"→ {_regime_label(row['zone'])}")
        if prev["regime"] != row["regime"]:
            kinds.append(f"смена доминирующего режима на {_regime_label(row['regime'])}")
        if abs(row["delta"]) >= _JUMP:
            direction = "рост" if row["delta"] > 0 else "спад"
            kinds.append(f"резкий {direction} напряжения на {abs(row['delta']):.3f}")
        if kinds:
            nodes.append({"year": row["year"], "kind": "; ".join(kinds),
                          "note": f"Напряжение {row['tension']:.3f}."})
    last = timeline[-1]
    nodes.append({"year": last["year"], "kind": "финал",
                  "note": f"Итог горизонта, напряжение {last['tension']:.3f}, "
                          f"режим {_regime_label(last['regime'])}."})
    return nodes


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
    человекочитаемое. Лог траектории есть единственный источник, что
    исключает рассинхрон с объектом сценария.
    """
    out = []
    for year, description in getattr(traj, "events_log", []):
        out.append({"year": year, "description": description})
    return out


def _gaps(traj, thresholds: dict, base_year: int) -> list:
    """
    Чего мы не знаем. Раздел неопределённости по разведывательному стандарту.
    Часть оговорок постоянна и держит честность модели, часть рождается из
    конкретного прогона, например близость к порогу.
    """
    gaps = [
        "Параметры агентов заморожены на исторической калибровке. При шоках "
        "за пределами заданного каталога реальные траектории могут отклоняться.",
        "Годы за пределами настоящего суть сценарные допущения при оговорённых "
        "условиях, а не безусловный прогноз единственного будущего.",
        "Перцептивный контур и веса влияния калиброваны экспертно по таблице "
        "источников, а не извлечены автоматически, что вносит неустранимую "
        "субъективность параметризации.",
    ]
    # Специфичная оговорка. Если финал близок к порогу, исход хрупок.
    th23 = thresholds.get("S2->S3")
    if th23 is not None and traj.tension:
        final = float(traj.tension[-1])
        if abs(final - th23) <= 0.05:
            gaps.append(
                f"Финальное напряжение {final:.3f} лежит вблизи порога каскадной "
                f"дестабилизации {th23:.3f}. Исход чувствителен к малым изменениям "
                f"входных переменных, и качественный вывод в этой зоне наименее устойчив.")
    return gaps


def build_report_data(traj, scenario, thresholds: dict, base_year: int = 2025,
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
    return {
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
        "comparison": _comparison(traj, baseline, thresholds),
        # Что знаем. Заданные сценарием толчки.
        "events": _events(traj),
        # Чего не знаем.
        "gaps": _gaps(traj, thresholds, base_year),
    }
