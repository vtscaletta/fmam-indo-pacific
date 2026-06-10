"""
Тесты связки уровней.

Запуск из корня проекта:
    pytest -v
"""

import numpy as np
from engine.synthesis import (
    aggregate, influence_weights, perceptual_pressure, DifferentialMemory,
    LevelCoupling, phase_thresholds, stationary_distribution, COMPONENTS,
)
from engine.agents import AGENTS, run_agent
from engine.influence import CODES
from engine.markov import MARKOV


def _actions():
    return {c: run_agent(c) for c in CODES}


def _states():
    return {c: [AGENTS[c].z1, AGENTS[c].z2, AGENTS[c].z3] for c in CODES}


def _flat_actions(v):
    return {c: {"milex": v, "rhet": v, "drift": v} for c in CODES}


def _flat_states(z1, z2, z3):
    return {c: [z1, z2, z3] for c in CODES}


def test_aggregation_weights_sum_to_one():
    w = influence_weights()
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["chn"] == max(w.values())


def test_aggregate_within_unit_interval():
    comps = aggregate(_actions())
    for c in COMPONENTS:
        assert 0.0 <= comps[c] <= 1.0


def test_perceptual_pressure_responds_to_configuration():
    calm = perceptual_pressure(_flat_states(0.1, 0.9, 0.1))
    tense = perceptual_pressure(_flat_states(0.9, 0.1, 0.9))
    assert tense > calm
    assert 0.0 <= calm <= 1.0 and 0.0 <= tense <= 1.0


def test_memory_converges_to_constant_input():
    mem = DifferentialMemory()
    target = {"milex": 0.7, "rhet": 0.7, "drift": 0.7}
    for _ in range(100):
        H = mem.update(target)
    for c in COMPONENTS:
        assert abs(H[c] - 0.7) < 1e-3


def test_drift_remembered_longer_than_rhetoric():
    mem = DifferentialMemory()
    mem.seed({"milex": 0.0, "rhet": 0.0, "drift": 0.0})
    spike = {"milex": 1.0, "rhet": 1.0, "drift": 1.0}
    for _ in range(5):
        mem.update(spike)
    calm = {"milex": 0.0, "rhet": 0.0, "drift": 0.0}
    for _ in range(5):
        H = mem.update(calm)
    assert H["drift"] > H["milex"] > H["rhet"]


def test_tension_monotone_in_pressure():
    c = LevelCoupling()
    acts = _flat_actions(0.5)
    lo = c.raw_tension(acts, _flat_states(0.2, 0.8, 0.2))
    hi = c.raw_tension(acts, _flat_states(0.9, 0.1, 0.9))
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    assert lo < hi


def test_tension_monotone_in_actions():
    c = LevelCoupling()
    st = _states()
    lo = c.raw_tension(_flat_actions(0.2), st)
    hi = c.raw_tension(_flat_actions(0.9), st)
    assert lo < hi


def test_quiet_system_low_tension():
    c = LevelCoupling()
    tau = c.raw_tension(_flat_actions(0.0), _flat_states(0.0, 1.0, 0.0))
    assert tau < 0.32


def test_base_year_tension_in_confrontation_band():
    c = LevelCoupling()
    tau = c.raw_tension(_actions(), _states())
    assert 0.48 < tau < 0.65


def test_hysteresis_from_memory():
    st = _flat_states(0.3, 0.7, 0.3)
    cold = LevelCoupling()
    cold.memory.seed({"milex": 0.0, "rhet": 0.0, "drift": 0.0})
    baseline = cold.tension(_flat_actions(0.0), st)
    hot = LevelCoupling()
    hot.memory.seed({"milex": 0.0, "rhet": 0.0, "drift": 0.0})
    for _ in range(6):
        hot.tension(_flat_actions(0.9), st)
    for _ in range(6):
        residual = hot.tension(_flat_actions(0.0), st)
    assert residual > baseline + 0.03


def test_phase_thresholds_ordered_and_plausible():
    th = phase_thresholds(MARKOV)
    assert "S1->S2" in th and "S2->S3" in th
    assert th["S1->S2"] < th["S2->S3"]
    assert 0.28 < th["S1->S2"] < 0.38
    assert 0.62 < th["S2->S3"] < 0.72


def test_stationary_distribution_normalized():
    pi = stationary_distribution(MARKOV, 0.5)
    assert abs(pi.sum() - 1.0) < 1e-6


def test_explain_has_no_side_effects():
    c = LevelCoupling()
    c.memory.seed({"milex": 0.3, "rhet": 0.3, "drift": 0.3})
    before = dict(c.memory.H)
    rep = c.explain(_flat_actions(0.8), _states())
    assert c.memory.H == before
    assert set(rep) == {"components", "memory_prev", "smoothed",
                        "perceptual_pressure", "sigmoid_arg", "tension"}
    assert 0.0 <= rep["tension"] <= 1.0
