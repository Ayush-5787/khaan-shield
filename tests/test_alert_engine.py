"""Tests for the KHAAN-SHIELD alert engine (the brain)."""
from src import config
from src.alert_engine import AlertEngine
from src.sensors import Reading


def quiet():
    return Reading(gas_ppm=50, rear_distance=4.0, eye_closure=0.05)


def test_normal_when_all_quiet():
    assert AlertEngine().evaluate(quiet()).level == "NORMAL"


def test_gas_warn():
    r = Reading(gas_ppm=config.GAS_WARN_PPM + 10, rear_distance=4.0, eye_closure=0.0)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("WARN", "gas")


def test_gas_critical():
    r = Reading(gas_ppm=config.GAS_CRITICAL_PPM + 10, rear_distance=4.0, eye_closure=0.0)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("CRITICAL", "gas")


def test_gas_halt():
    r = Reading(gas_ppm=config.GAS_HALT_PPM + 10, rear_distance=4.0, eye_closure=0.0)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("HALT", "gas")


def test_proximity_halt():
    r = Reading(gas_ppm=50, rear_distance=config.PROX_HALT_M - 0.1, eye_closure=0.0)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("HALT", "proximity")


def test_fatigue_warn():
    r = Reading(gas_ppm=50, rear_distance=4.0, eye_closure=config.FATIGUE_WARN + 0.05)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("WARN", "fatigue")


def test_fatigue_critical():
    r = Reading(gas_ppm=50, rear_distance=4.0, eye_closure=config.FATIGUE_CRITICAL + 0.05)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("CRITICAL", "fatigue")


def test_cooldown_suppresses_repeat():
    engine = AlertEngine()
    r = Reading(gas_ppm=config.GAS_HALT_PPM + 10, rear_distance=4.5, eye_closure=0.0)
    assert engine.evaluate(r).level == "HALT"     # first: fires
    assert engine.evaluate(r).level == "NORMAL"   # immediate repeat: suppressed


def test_cooldown_allows_escalation():
    engine = AlertEngine()
    warn = Reading(gas_ppm=config.GAS_WARN_PPM + 10, rear_distance=4.5, eye_closure=0.0)
    halt = Reading(gas_ppm=config.GAS_HALT_PPM + 10, rear_distance=4.5, eye_closure=0.0)
    assert engine.evaluate(warn).level == "WARN"
    assert engine.evaluate(halt).level == "HALT"  # escalation bypasses cooldown


def test_highest_severity_wins():
    r = Reading(gas_ppm=config.GAS_HALT_PPM + 10,
                rear_distance=config.PROX_WARN_M - 0.1, eye_closure=0.0)
    a = AlertEngine().evaluate(r)
    assert (a.level, a.source) == ("HALT", "gas")