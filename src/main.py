"""Simulated shift demo for KHAAN-SHIELD with auto shift report."""
import sys
from pathlib import Path

from .alert_engine import AlertEngine
from .sensors import simulated_shift
from .alert_logger import AlertLogger
from .notifier import Notifier
from .report import ShiftReport

# --- mirror all console output to logs/khaan.log for the live dashboard ---
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "khaan.log"

class _Tee:
    """Send every print() to both the terminal and the log file."""
    def __init__(self, path):
        self._file = open(path, "a", encoding="utf-8")
        self._stdout = sys.stdout

    def write(self, data):
        self._stdout.write(data)
        self._file.write(data)
        self._file.flush()

    def flush(self):
        self._stdout.flush()
        self._file.flush()

sys.stdout = _Tee(LOG_FILE)
# --------------------------------------------------------------------------

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