"""
KHAAN-SHIELD notifier: turns alerts into real-world signals.

Laptop (now): audible alerts via winsound (Windows built-in) + console log.
Raspberry Pi (later): GPIO buzzer code goes HERE - this is the only file
that changes. The brain (alert_engine.py) never does.

Standalone sound test (no main loop needed):
    python -m src.notifier
"""
import threading
import time

try:
    import winsound  # Windows only
    WINSOUND_OK = True
except ImportError:
    winsound = None
    WINSOUND_OK = False


# ---- Dispatch targets per alert level (matches the log format) ----
_TARGETS = {
    "WARN":     ["BUZZER"],
    "CRITICAL": ["BUZZER", "SMS->supervisor"],
    "HALT":     ["BUZZER", "SMS->supervisor", "ENGINE_CUTOFF"],
}

# ---- Beep patterns per level: list of (frequency_hz, duration_ms) ----
_BEEP_PATTERNS = {
    "WARN":     [(1000, 250)],                            # single short beep
    "CRITICAL": [(1400, 250), (1400, 250)],               # double beep
    "HALT":     [(2000, 400), (1500, 400), (2000, 700)],  # urgent triple
}

# ---- System-sound aliases: play through the NORMAL audio path (like YouTube) ----
_SOUND_ALIASES = {
    "WARN":     "SystemExclamation",
    "CRITICAL": "SystemHand",
    "HALT":     "SystemHand",
}

_GAP_S = 0.06        # tiny gap so repeated beeps sound distinct
_MAX_PENDING = 4     # flood control: never stack an endless beep backlog

_beep_lock = threading.Lock()      # serializes sounds: queue, don't overlap
_pending = 0
_pending_lock = threading.Lock()
_stats = {"played": 0, "dropped": 0, "errors": 0}


def _play_alert(level):
    """Blocking: play one level's alert sound on BOTH audio paths:
      1. PlaySound alias -> normal Windows audio session (same one YouTube uses)
      2. Beep pattern    -> classic console beep path
    Whichever path your laptop can actually hear, you will hear."""
    if level in _SOUND_ALIASES:
        winsound.PlaySound(_SOUND_ALIASES[level], winsound.SND_ALIAS)
    for freq, ms in _BEEP_PATTERNS.get(level, []):
        winsound.Beep(freq, ms)
        time.sleep(_GAP_S)


def _beep(level):
    """Play the level's alert sound in a background thread.
    Never blocks the safety loop and never raises."""
    global _pending
    if level not in _BEEP_PATTERNS:
        return

    with _pending_lock:
        if _pending >= _MAX_PENDING:
            _stats["dropped"] += 1
            return  # flood control: skip instead of stacking minutes of sound
        _pending += 1

    def _play():
        global _pending
        with _beep_lock:
            try:
                if WINSOUND_OK:
                    _play_alert(level)
                    _stats["played"] += 1
                else:
                    print("\a", end="", flush=True)  # terminal bell fallback
            except Exception as exc:
                _stats["errors"] += 1
                print(f"[SOUND] alert sound failed: {exc}")  # never crash the loop
            finally:
                with _pending_lock:
                    _pending -= 1

    threading.Thread(target=_play, daemon=True).start()


def sound_self_test():
    """Power-on self test, like real industrial safety systems do.
    Plays one alert per level. Silence here = Windows audio problem."""
    print("[SOUND] self-test: expect WARN sound, then CRITICAL sound, then HALT sound")
    if not WINSOUND_OK:
        print("[SOUND] winsound not available - terminal bell fallback")
        print("\a", end="", flush=True)
        return
    try:
        for level in ("WARN", "CRITICAL", "HALT"):
            _play_alert(level)
            _stats["played"] += 1
        print("[SOUND] self-test done - heard nothing? -> volume mixer / output device")
    except Exception as exc:
        print(f"[SOUND] self-test FAILED: {exc}")


def sound_report():
    """Call at shutdown: proves whether alert sounds actually reached Windows."""
    p, d, e = _stats["played"], _stats["dropped"], _stats["errors"]
    print(f"[SOUND] alerts sounded: {p} | skipped by flood control: {d} | errors: {e}")
    if p == 0 and e == 0:
        print("[SOUND] no sound reached Windows -> check volume / output device")


class Notifier:
    """Dispatches alerts to available output channels."""

    def __init__(self, self_test=False):
        if self_test:
            sound_self_test()

    def dispatch(self, alert):
        targets = _TARGETS.get(alert.level, ["LOG"])
        print(f"[NOTIFY] {alert.level} | {alert.source} | {alert.message} -> {', '.join(targets)}")
        _beep(alert.level)


if __name__ == "__main__":
    sound_self_test()
    sound_report()