"""
KHAAN-SHIELD logger: appends every alert + reading snapshot to shift.log.jsonl.
One JSON object per line - easy to replay, analyze, or feed to a dashboard.
"""
import json
import os
import time

LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shift.log.jsonl"
)


def log_event(alert, reading):
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "level": alert.level,
        "source": alert.source,
        "message": alert.message,
        "gas_ppm": round(reading.gas_ppm, 1),
        "rear_distance": round(reading.rear_distance, 2),
        "eye_closure": round(reading.eye_closure, 2),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")