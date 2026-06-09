"""Модуль 12, фундамент. Слой данных отчёта."""

import pytest

from engine.scenarios import ALL_SCENARIOS
from engine.simulator import SIMULATOR
from engine.agents import AGENTS
from engine.synthesis import phase_thresholds
from engine.markov import MARKOV
from engine.report import build_report_data


@pytest.fixture(scope="module")
def thresholds():
    return phase_thresholds(MARKOV)


def _run(key, horizon=6):
    return SIMULATOR.run(ALL_SCENARIOS[key], AGENTS, horizon=horizon)


def test_structure_has_three_standard_sections(thresholds):
    traj = _run("taiwan")
    d = build_report_data(traj, ALL_SCENARIOS["taiwan"], thresholds)
    for key in ("meta", "verdict", "threat_type", "thresholds",
                "timeline", "nodal_years", "drivers", "events", "gaps"):
        assert key in d, f"нет раздела {key}"


def test_timeline_length_matches_horizon(thresholds):
    traj = _run("article9", horizon=5)
    d = build_report_data(traj, ALL_SCENARIOS["article9"], thresholds)
    assert len(d["timeline"]) == 5
    assert d["meta"]["horizon"] == 5


def test_nodal_years_bookended_by_start_and_final(thresholds):
    traj = _run("inertial")
    d = build_report_data(traj, ALL_SCENARIOS["inertial"], thresholds)
    kinds = [n["kind"] for n in d["nodal_years"]]
    assert kinds[0] == "старт"
    assert kinds[-1] == "финал"


def test_gaps_always_present_with_constant_caveats(thresholds):
    traj = _run("inertial")
    d = build_report_data(traj, ALL_SCENARIOS["inertial"], thresholds)
    assert len(d["gaps"]) >= 3  # постоянные методологические оговорки


def test_near_threshold_adds_specific_gap(thresholds):
    """Сценарий у порога получает оговорку о хрупкости, инерционный нет."""
    taiwan = build_report_data(_run("taiwan"), ALL_SCENARIOS["taiwan"], thresholds)
    inertial = build_report_data(_run("inertial"), ALL_SCENARIOS["inertial"], thresholds)
    near_gap = "вблизи порога"
    taiwan_has = any(near_gap in g for g in taiwan["gaps"])
    inertial_has = any(near_gap in g for g in inertial["gaps"])
    # Тайвань ближе к порогу каскада, чем инерционный дрейф.
    assert taiwan["timeline"][-1]["tension"] > inertial["timeline"][-1]["tension"]


def test_timeline_zones_are_valid(thresholds):
    traj = _run("taiwan")
    d = build_report_data(traj, ALL_SCENARIOS["taiwan"], thresholds)
    for row in d["timeline"]:
        assert row["zone"] in ("S1", "S2", "S3")
        assert 0.0 <= row["tension"] <= 1.0


def test_events_extracted_for_shock_scenario(thresholds):
    traj = _run("taiwan")
    d = build_report_data(traj, ALL_SCENARIOS["taiwan"], thresholds)
    assert len(d["events"]) > 0
    for ev in d["events"]:
        assert ev["variable"] in ("z1", "z2", "z3")
