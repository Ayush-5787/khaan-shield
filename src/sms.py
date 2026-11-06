"""
KHAAN-SHIELD SMS channel (Phase 3b).

Mock mode (now, laptop): "sends" SMS to the console + sms_outbox.txt so the
full alert flow can be tested with zero hardware.
Real mode (later, Raspberry Pi + SIM800L): only _transmit() changes - it will
speak AT commands over serial. Nothing else in the project touches this.

Standalone test (no main loop needed):
    python -m src.sms
"""
import threading
import time
from datetime import datetime

# ---- Config ----
SUPERVISOR_PHONE = "+91-XXXXXXXXXX"  # real number goes here on hardware day
SMS_COOLDOWN_S = 300                 # same alert won't SMS more than once per 5 min
OUTBOX_FILE = "sms_outbox.txt"

_lock = threading.Lock()
_last_sent = {}                      # (source, level) -> timestamp
_stats = {"sent": 0, "suppressed": 0, "errors": 0}


def send_sms(source, level, message):
    """Send one SMS alert. Never raises, never blocks the safety loop.
    Cooldown: the same source+level is suppressed for SMS_COOLDOWN_S,
    but a MORE severe level (HALT after CRITICAL) still gets through."""
    key = (source, level)
    now = time.time()

    with _lock:
        if now - _last_sent.get(key, 0) < SMS_COOLDOWN_S:
            _stats["suppressed"] += 1
            return False
        _last_sent[key] = now

    text = f"[KHAAN-SHIELD {level}] {source.upper()}: {message} ({datetime.now():%H:%M:%S})"
    try:
        # Threaded: on hardware day a real SMS takes ~5-10 s - must not stall ticks
        threading.Thread(target=_transmit, args=(SUPERVISOR_PHONE, text), daemon=True).start()
        with _lock:
            _stats["sent"] += 1
        return True
    except Exception as exc:
        with _lock:
            _stats["errors"] += 1
        print(f"[SMS] send failed: {exc}")
        return False


def _transmit(phone, text):
    """Mock transport: console + outbox file.
    Hardware day: this becomes SIM800L AT commands (AT+CMGS=...)."""
    line = f"[SMS->mock] to {phone}: {text}"
    print(line)
    with open(OUTBOX_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sms_self_test():
    """Proves the SMS pipeline end-to-end without hardware."""
    print("[SMS] self-test (mock mode): 3 sends - expect 2 sent, 1 suppressed")
    send_sms("fatigue", "CRITICAL", "SELF-TEST: driver eyes closed - pull over")
    send_sms("gas", "HALT", "SELF-TEST: CO 350 ppm - stop work")
    send_sms("fatigue", "CRITICAL", "SELF-TEST repeat: must be suppressed by cooldown")
    time.sleep(0.5)  # let the mock threads finish printing
    sms_report()


def sms_report():
    """Call at shutdown: proves how many SMS actually left the system."""
    s, sup, e = _stats["sent"], _stats["suppressed"], _stats["errors"]
    print(f"[SMS] sent: {s} | suppressed by cooldown: {sup} | errors: {e}")


if __name__ == "__main__":
    sms_self_test()