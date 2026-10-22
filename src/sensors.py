from dataclasses import dataclass
import random

@dataclass
class GasReading:
    gas_ppm: float

@dataclass
class ProximityReading:
    rear_distance: float

@dataclass
class FatigueReading:
    eye_closure: float

@dataclass
class Reading:
    gas_ppm: float
    rear_distance: float
    eye_closure: float

def simulated_shift():
    """Yield 30 simulated readings for the demo shift."""
    random.seed(42)
    for i in range(30):
        gas = 25 + random.uniform(-5, 10)
        if i in (18, 22):
            gas = 190 + random.uniform(-5, 5)
        rear = random.uniform(0.5, 30)
        if i == 18:
            rear = 0.9
        eyes = 0.1 + i * 0.015 + random.uniform(-0.02, 0.02)
        yield Reading(gas, rear, max(0, eyes))