"""Unit tests for KHAAN-SHIELD alert arbitration logic."""
import pytest
from types import SimpleNamespace

from src.alert_engine import AlertEngine
from src import config


@pytest.fixture
def engine():
    return AlertEngine()


def reading(gas, rear, eyes):
    """Build a sensor-reading object the engine understands."""
    return SimpleNamespace(gas_ppm=gas, rear_distance=rear, eye_closure=eyes)


# ---------- NORMAL ----------

def test_normal_readings_stay_normal(engine):
    result = engine.evaluate(reading(gas=10, rear=100, eyes=0.05))
    assert result.level == "NORMAL"


# ---------- GAS ----------

def test_gas_spike_triggers_critical(engine):
    gas = config.GAS_CRITICAL + (config.GAS_HALT - config.GAS_CRITICAL) / 2
    result = engine.evaluate(reading(gas=gas, rear=100, eyes=0.05))
    assert result.level == "CRITICAL"
    assert result.source == "gas"


def test_extreme_gas_triggers_halt(engine):
    result = engine.evaluate(reading(gas=config.GAS_HALT + 10, rear=100, eyes=0.05))
    assert result.level == "HALT"
    assert result.source == "gas"


# ---------- PROXIMITY ----------

def test_close_proximity_triggers_critical(engine):
    rear = config.PROX_CRITICAL - (config.PROX_CRITICAL - config.PROX_HALT) / 2
    result = engine.evaluate(reading(gas=10, rear=rear, eyes=0.05))
    assert result.level == "CRITICAL"
    assert result.source == "proximity"


def test_halt_cuts_engine(engine):
    result = engine.evaluate(reading(gas=10, rear=config.PROX_HALT / 2, eyes=0.05))
    assert result.level == "HALT"
    assert "engine cut-off" in result.action


# ---------- FATIGUE ----------

def test_driver_fatigue_triggers_critical(engine):
    eyes = config.FATIGUE_CRITICAL + 0.1
    result = engine.evaluate(reading(gas=10, rear=100, eyes=eyes))
    assert result.level == "CRITICAL"
    assert result.source == "fatigue"


def test_fatigue_warn(engine):
    eyes = config.FATIGUE_WARN + (config.FATIGUE_CRITICAL - config.FATIGUE_WARN) / 2
    result = engine.evaluate(reading(gas=10, rear=100, eyes=eyes))
    assert result.level == "WARN"
    assert result.source == "fatigue"


# ---------- ARBITRATION ----------

def test_worst_severity_wins(engine):
    """Gas HALT + fatigue CRITICAL together must not downgrade."""
    result = engine.evaluate(
        reading(gas=config.GAS_HALT + 10, rear=100, eyes=config.FATIGUE_CRITICAL + 0.1)
    )
    assert result.level == "HALT"
    assert result.source == "gas"


# ---------- COOLDOWN ----------

def test_cooldown_suppresses_repeat_alerts(engine):
    gas = config.GAS_HALT + 10
    first = engine.evaluate(reading(gas=gas, rear=100, eyes=0.05))
    assert first.source == "gas"
    second = engine.evaluate(reading(gas=gas, rear=100, eyes=0.05))
    assert second.level == "NORMAL"
    assert second.message == "alert in cooldown"