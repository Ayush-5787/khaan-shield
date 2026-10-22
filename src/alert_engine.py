from dataclasses import dataclass
from . import config
import time


@dataclass
class Alert:
    level: str
    source: str
    message: str
    action: str


class AlertEngine:
    def __init__(self):
        self.last_alert = {}

    def evaluate(self, a, b=None, c=None):
        # Support both: evaluate(Reading) and evaluate(GasReading, ProximityReading, FatigueReading)
        if b is None and c is None:
            # single Reading object
            gas_ppm = a.gas_ppm
            rear = a.rear_distance
            eyes = a.eye_closure
        else:
            gas_ppm = a.gas_ppm
            rear = b.rear_distance
            eyes = c.eye_closure

        alerts = []

        if gas_ppm >= config.GAS_HALT:
            alerts.append(Alert("HALT", "gas", f"CO {gas_ppm:.1f} ppm - ventilate, stop work", "in-cab + GSM + engine cut-off"))
        elif gas_ppm >= config.GAS_CRITICAL:
            alerts.append(Alert("CRITICAL", "gas", f"CO {gas_ppm:.1f} ppm - ventilate, inform supervisor", "in-cab buzzer + GSM SMS"))
        elif gas_ppm >= config.GAS_WARN:
            alerts.append(Alert("WARN", "gas", f"CO {gas_ppm:.1f} ppm rising", "in-cab buzzer"))
        else:
            alerts.append(Alert("NORMAL", "gas", "gas normal", "none"))

        if rear <= config.PROX_HALT:
            alerts.append(Alert("HALT", "proximity", f"rear obstacle at {rear:.1f} m - STOP", "in-cab + GSM + engine cut-off"))
        elif rear <= config.PROX_CRITICAL:
            alerts.append(Alert("CRITICAL", "proximity", f"rear obstacle at {rear:.1f} m - slow down", "in-cab buzzer + GSM"))
        elif rear <= config.PROX_WARN:
            alerts.append(Alert("WARN", "proximity", f"rear obstacle at {rear:.1f} m - slow down", "in-cab buzzer"))
        else:
            alerts.append(Alert("NORMAL", "proximity", f"rear clear ({rear:.1f} m)", "none"))

        if eyes >= config.FATIGUE_CRITICAL:
            alerts.append(Alert("CRITICAL", "fatigue", f"eye-closure {eyes:.2f} - pull over and rest", "in-cab buzzer + GSM SMS"))
        elif eyes >= config.FATIGUE_WARN:
            alerts.append(Alert("WARN", "fatigue", f"eye-closure {eyes:.2f} - take micro-break", "in-cab buzzer"))
        else:
            alerts.append(Alert("NORMAL", "fatigue", "driver alert", "none"))

        best = alerts[0]
        for a_alert in alerts[1:]:
            if config.SEVERITY_RANK[a_alert.level] > config.SEVERITY_RANK[best.level]:
                best = a_alert
            elif config.SEVERITY_RANK[a_alert.level] == config.SEVERITY_RANK[best.level] and a_alert.level != "NORMAL":
                if config.MODULE_PRIORITY[a_alert.source] > config.MODULE_PRIORITY[best.source]:
                    best = a_alert

        now = time.time()
        key = best.source
        last = self.last_alert.get(key)
        if last:
            last_level, last_ts = last
            if last_level == best.level and now - last_ts < config.COOLDOWN_SECONDS:
                return Alert("NORMAL", "engine", "alert in cooldown", "none")

        if best.level != "NORMAL":
            self.last_alert[key] = (best.level, now)
        return best