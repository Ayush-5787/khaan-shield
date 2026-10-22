class Notifier:
    def __init__(self, engine_cutoff_pin=18, buzzer_pin=23):
        self.engine_cutoff_pin = engine_cutoff_pin
        self.buzzer_pin = buzzer_pin

    def dispatch(self, alert):
        level = alert.level.upper()
        source = alert.source
        msg = alert.message
        action = alert.action

        if level == "NORMAL":
            return f"[Notifier] {source}: normal - no action"

        if level == "WARN":
            self._buzz_once()
            return f"[Notifier] WARN {source}: {msg} | action: in-cab buzzer + dashboard | {action}"

        if level == "CRITICAL":
            self._buzz_pattern(critical=True)
            self._send_sms(f"CRITICAL {source}: {msg}")
            return f"[Notifier] CRITICAL {source}: {msg} | action: buzzer + SMS to supervisor | {action}"

        if level == "HALT":
            self._buzz_pattern(critical=True)
            self._send_sms(f"HALT {source}: {msg}")
            self._request_engine_cutoff()
            return f"[Notifier] HALT {source}: {msg} | action: buzzer + SMS + engine cut-off request | {action}"

        return f"[Notifier] Unknown level {level}"

    def _buzz_once(self):
        print(">>> BUZZER: short beep")

    def _buzz_pattern(self, critical=False):
        print(">>> BUZZER: urgent pattern")

    def _send_sms(self, text):
        print(f">>> SMS to supervisor: {text}")

    def _request_engine_cutoff(self):
        print(">>> ENGINE: cut-off request issued")