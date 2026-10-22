"""Deterministic tests for the AlertEngine."""
from src.sensors import GasReading, ProximityReading, FatigueReading
from src.alert_engine import AlertEngine


def make_engine():
    return AlertEngine()


def test_all_clear_is_normal():
    a = make_engine().evaluate(GasReading(20), ProximityReading(25), FatigueReading(0.05))
    assert a.level == "NORMAL"


def test_gas_warn():
    a = make_engine().evaluate(GasReading(60), ProximityReading(25), FatigueReading(0.05))
    assert a.level == "WARN" and a.source == "gas"


def test_gas_halt():
    a = make_engine().evaluate(GasReading(250), ProximityReading(25), FatigueReading(0.05))
    assert a.level == "HALT" and a.source == "gas"


def test_proximity_critical():
    a = make_engine().evaluate(GasReading(20), ProximityReading(3.0), FatigueReading(0.05))
    assert a.level == "CRITICAL" and a.source == "proximity"


def test_proximity_halt_beats_gas_halt():
    a = make_engine().evaluate(GasReading(250), ProximityReading(1.0), FatigueReading(0.05))
    assert a.level == "HALT" and a.source == "proximity"


def test_fatigue_critical():
    a = make_engine().evaluate(GasReading(20), ProximityReading(25), FatigueReading(0.7))
    assert a.level == "CRITICAL" and a.source == "fatigue"


def test_highest_severity_wins_across_modules():
    a = make_engine().evaluate(GasReading(60), ProximityReading(3.0), FatigueReading(0.7))
    assert a.level == "CRITICAL" and a.source == "proximity"


def test_cooldown_suppresses_repeat():
    e = make_engine()
    a1 = e.evaluate(GasReading(60), ProximityReading(25), FatigueReading(0.05))
    a2 = e.evaluate(GasReading(60), ProximityReading(25), FatigueReading(0.05))
    assert a1.level == "WARN"
    assert a2.level == "NORMAL" and a2.source == "engine"