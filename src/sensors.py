"""
KHAAN-SHIELD sensors: gas (MQ-7), rear proximity (HC-SR04), fatigue (webcam).

Auto-detects the environment:
  - Laptop: gas + proximity are SIMULATED, fatigue is the REAL webcam.
  - Raspberry Pi: real MQ-7 via MCP3008 ADC, real HC-SR04 via GPIO,
    same webcam fatigue module.

The brain (alert_engine.py) only ever sees Reading objects - it never
knows or cares where the numbers came from.
"""
import random
import time
from dataclasses import dataclass

from . import config

# ---- Environment detection ----
ON_PI = False
GPIO = None
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    pass


@dataclass
class Reading:
    gas_ppm: float        # CO concentration (ppm)
    rear_distance: float  # nearest obstacle behind (meters)
    eye_closure: float    # rolling eye closure 0.0 open .. 1.0 closed


# ================= SIMULATED (laptop) =================

class SimulatedGasSensor:
    """Random-walk CO ppm in a realistic 40-350 band."""

    def __init__(self):
        self._ppm = 80.0

    def read(self) -> float:
        self._ppm = min(350.0, max(40.0, self._ppm + random.uniform(-70, 70)))
        return self._ppm


class SimulatedProximitySensor:
    """Uniform random rear distance 0.3-4.8 m."""

    def read(self) -> float:
        return random.uniform(0.3, 4.8)


# ================= REAL (Raspberry Pi) =================

class PiGasSensor:
    """MQ-7 CO sensor via MCP3008 ADC (SPI, channel 0)."""

    def __init__(self, channel=0, vref=3.3):
        import spidev
        self._spi = spidev.SpiDev()
        self._spi.open(0, 0)
        self._spi.max_speed_hz = 1_350_000
        self._channel = channel
        self._vref = vref

    def _read_adc(self) -> int:
        r = self._spi.xfer2([1, (8 + self._channel) << 4, 0])
        return ((r[1] & 3) << 8) + r[2]

    def read(self) -> float:
        volts = self._read_adc() / 1023.0 * self._vref
        # Rough linear mapping - replace with a 2-point calibration
        # against a known CO source before field use.
        return max(0.0, (volts / self._vref) * 400.0)


class PiProximitySensor:
    """HC-SR04 ultrasonic rear sensor via GPIO."""

    TRIG = 23
    ECHO = 24

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)
        GPIO.output(self.TRIG, False)
        time.sleep(0.1)

    def read(self) -> float:
        GPIO.output(self.TRIG, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG, False)

        t0 = time.time()
        while GPIO.input(self.ECHO) == 0:
            pulse_start = time.time()
            if time.time() - t0 > 0.1:
                return 99.0  # timeout: nothing in range / wiring issue
        t0 = time.time()
        while GPIO.input(self.ECHO) == 1:
            pulse_end = time.time()
            if time.time() - t0 > 0.1:
                return 99.0

        distance_cm = (pulse_end - pulse_start) * 17150.0
        return max(0.02, distance_cm / 100.0)


# ================= COMBINED =================

class CombinedSensors:
    """One tick() -> Reading from all three channels."""

    def __init__(self, gas=None, proximity=None):
        self.gas = gas if gas is not None else SimulatedGasSensor()
        self.proximity = proximity if proximity is not None else SimulatedProximitySensor()
        self.fatigue = None
        try:
            from .fatigue import FatigueSensor
            self.fatigue = FatigueSensor()
            print("[FATIGUE] webcam eye monitor active")
        except Exception as e:
            print(f"[FATIGUE] unavailable ({e}) - eye_closure fixed at 0.0")

    def tick(self) -> Reading:
        eye = self.fatigue.tick() if self.fatigue else 0.0
        return Reading(
            gas_ppm=self.gas.read(),
            rear_distance=self.proximity.read(),
            eye_closure=eye,
        )

    def close(self):
        if self.fatigue is not None:
            self.fatigue.close()


def get_sensors() -> CombinedSensors:
    """Auto-detect: real sensors on the Pi, simulation on the laptop."""
    if ON_PI:
        return CombinedSensors(gas=PiGasSensor(), proximity=PiProximitySensor())
    return CombinedSensors()