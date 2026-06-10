"""
Тесты ретроспективной валидации.

Запуск из корня проекта:
    pytest -v
"""

from engine.historical import (
    validate, AGENTS_2012, HISTORICAL_SCENARIO, FORECAST_ANCHOR_START,
)
from engine.influence import CODES


def test_report_structure():
    """Отчёт валидации содержит траекторию, проверки и вердикт."""
    r = validate()
    assert len(r["years"]) == 11
    assert r["years"][0] == 2012 and r["years"][-1] == 2022
    assert set(r["checks"]) == {
        "growth_positive", "starts_in_balance", "settles_in_confrontation",
        "breakpoint_in_2022", "continuity_with_forecast",
    }


def test_tension_grows_over_decade():
    """Напряжение существенно растёт за десятилетие."""
    r = validate()
    assert r["growth"] > 0.08
    assert r["tension"][-1] > r["tension"][0]


def test_starts_in_balance_settles_in_confrontation():
    """Регион стартует в балансе и оседает в холодной конфронтации."""
    r = validate()
    assert r["regime"][0] == "S1"
    assert r["regime"][-1] == "S2"


def test_breakpoint_falls_on_2022():
    """
    Год наибольшего скачка напряжения есть 2022. Совпадает с независимо
    установленным секьюритизационным переломом по текстовому анализу.
    """
    r = validate()
    assert r["breakpoint_year"] == 2022
    # Скачок перелома крупнейший в ряду.
    jumps = [r["tension"][i] - r["tension"][i - 1] for i in range(1, len(r["tension"]))]
    assert r["breakpoint_jump"] == max(jumps)


def test_continuity_with_forecast():
    """
    Финиш ретроспективы стыкуется со стартом прогноза. Прошлое и будущее
    сходятся, модель согласована во времени.
    """
    r = validate()
    assert r["continuity_gap"] < 0.06
    assert abs(r["tension"][-1] - FORECAST_ANCHOR_START) < 0.06


def test_overall_verdict_passes():
    """Все проверки пройдены, валидация состоялась."""
    r = validate()
    assert r["verdict"] is True


def test_initial_states_calmer_than_base():
    """Состояния 2012 года заметно спокойнее базового 2026."""
    from engine.agents import AGENTS as A_BASE
    for c in CODES:
        # эрозия 2012 ниже эрозии базового 2026 у каждого агента
        assert AGENTS_2012[c].z3 <= A_BASE[c].z3 + 1e-9


def test_states_within_unit_interval_through_run():
    """Состояния остаются в [0, 1] на всём историческом прогоне."""
    r = validate()
    traj = r["trajectory"]
    for c in CODES:
        for s in traj.agent_states[c]:
            for z in s:
                assert 0.0 <= z <= 1.0


def test_historical_events_logged():
    """Перелом 2022 года присутствует в журнале событий."""
    r = validate()
    assert any(year == 2022 for year, _ in r["trajectory"].events_log)
