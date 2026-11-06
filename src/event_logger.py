"""
event_logger.py — Phase 4a: KHAAN Shield Event Logger
Har fatigue/critical event CSV mein save hota hai = permanent proof!

Chalana (logs dekhne ke liye):  python -m src.event_logger
"""

import csv
import os
from datetime import datetime

LOG_FILE = "logs/events.csv"


def log_event(event_type, details=""):
    """Event ko CSV mein append karo. Kabhi crash nahi hota."""
    try:
        os.makedirs("logs", exist_ok=True)
        is_new = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["timestamp", "event_type", "details"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_type,
                details,
            ])
        print(f"[LOG] {event_type}: {details}")
        return True
    except Exception as e:
        print(f"[LOG] failed (system continues): {e}")
        return False


def show_recent(n=10):
    """Last n events print karo (naye pehle)."""
    if not os.path.exists(LOG_FILE):
        print("Koi log nahi hai abhi — pehle monitor chalao!")
        return
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if len(rows) <= 1:
        print("Log file khali hai.")
        return
    print(f"=== Last {min(n, len(rows)-1)} Events ===")
    for row in reversed(rows[-n:]):
        print(" | ".join(row))


if __name__ == "__main__":
    # Standalone test: khud ek event log karo, phir dikhao
    log_event("TEST", "logger test event")
    show_recent()