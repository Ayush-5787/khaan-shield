"""
KHAAN-SHIELD main loop.

Run from the project root (must use -m form):
    python -m src.main
"""
import time

from src.alert_engine import AlertEngine
from src.alert_logger import log_event
from src.notifier import Notifier, sound_report
from src.report import print_report
from src.sensors import get_sensors

SHIFT_TICKS = 30
TICK_SECONDS = 1


def run_shift(ticks=SHIFT_TICKS):
    sensors = get_sensors()
    engine = AlertEngine()
    notifier = Notifier(self_test=True)   # EDIT 1: audible self-test at startup

    try:
        for tick in range(1, ticks + 1):
            reading = sensors.tick()
            alert = engine.evaluate(reading)

            if alert.level != "NORMAL":
                log_event(alert, reading)
                notifier.dispatch(alert)
                print(f"Tick {tick:02d}: {alert.level:8s} | {alert.source:9s} | {alert.message}")
            else:
                print(f"Tick {tick:02d}: NORMAL   | gas={reading.gas_ppm:5.0f}ppm "
                      f"rear={reading.rear_distance:4.1f}m eyes={reading.eye_closure:4.2f}")

            time.sleep(TICK_SECONDS)
    finally:
        # Release resources cleanly on exit (including Ctrl+C)
        sensors.close()
        try:
            from src.sensors import ON_PI
            if ON_PI:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
        except Exception:
            pass

    print_report()
    sound_report()                        # EDIT 2: prove whether beeps reached the speaker


if __name__ == "__main__":
    run_shift()