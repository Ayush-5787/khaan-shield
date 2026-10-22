"""Simulated shift demo for KHAAN-SHIELD with auto shift report."""
from .alert_engine import AlertEngine
from .sensors import simulated_shift
from .alert_logger import AlertLogger
from .notifier import Notifier
from .report import ShiftReport

engine = AlertEngine()
logger = AlertLogger()
notifier = Notifier()

print("=== KHAAN-SHIELD v0.1 - simulated shift ===")
for i, reading in enumerate(simulated_shift(), start=1):
    alert = engine.evaluate(reading)
    notifier_output = notifier.dispatch(alert)
    if alert.level != "NORMAL":
        logger.log(alert)
        print(f"[{i:02d}] gas={reading.gas_ppm:5.1f}ppm  rear={reading.rear_distance:4.1f}m  eyes={reading.eye_closure:0.2f}  ->  {alert.level:8s}  [{alert.source}] {alert.message}")
        print("     >>>", notifier_output)
    else:
        print(f"[{i:02d}] gas={reading.gas_ppm:5.1f}ppm  rear={reading.rear_distance:4.1f}m  eyes={reading.eye_closure:0.2f}  ->  {alert.level:8s}  [{alert.source}] {alert.message}")

print("\n")
ShiftReport().summarize()