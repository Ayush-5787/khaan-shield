"""
KHAAN-SHIELD brain: the alert engine.

Pure logic - no hardware, no I/O. Takes a Reading, returns the single most
urgent alert allowed to fire right now, respecting per-source cooldowns
while still permitting escalations (WARN -> CRITICAL -> HALT).

This file NEVER changes between laptop and Raspberry Pi.
"""
from dataclasses import dataclass

from . import config

_SEVERITY = {"NORMAL": 0, "WARN": 1, "CRITICAL": 2, "HALT": 3}


@dataclass
class Alert:
    level: str    # NORMAL | WARN | CRITICAL | HALT
    source: str   # gas | proximity | fatigue | none
    message: str


class AlertEngine:
    def __init__(self, cooldown_ticks=None):
        self.cooldown_ticks = (
            config.COOLDOWN_TICKS if cooldown_ticks is None else cooldown_ticks
        )
        self._last_fired = {}   # source -> (tick, level)
        self._tick = 0

    # ---- per-source level + message ----
    def _gas_alert(self, ppm):
        if ppm >= config.GAS_HALT_PPM:
            return "HALT", f"CO {ppm:.1f} ppm - ventilate, stop work"
        if ppm >= config.GAS_CRITICAL_PPM:
            return "CRITICAL", f"CO {ppm:.1f} ppm - ventilate, inform supervisor"
        if ppm >= config.GAS_WARN_PPM:
            return "WARN", f"CO {ppm:.1f} ppm rising"
        return None

    def _proximity_alert(self, dist):
        if dist <= config.PROX_HALT_M:
            return "HALT", f"rear obstacle at {dist:.1f} m - STOP"
        if dist <= config.PROX_CRITICAL_M:
            return "CRITICAL", f"rear obstacle at {dist:.1f} m - slow down"
        if dist <= config.PROX_WARN_M:
            return "WARN", f"rear obstacle at {dist:.1f} m - slow down"
        return None

    def _fatigue_alert(self, closure):
        if closure >= config.FATIGUE_CRITICAL:
            return "CRITICAL", f"eye-closure {closure:.2f} - pull over and rest"
        if closure >= config.FATIGUE_WARN:
            return "WARN", f"eye-closure {closure:.2f} - take micro-break"
        return None

    def evaluate(self, reading) -> Alert:
        self._tick += 1

        candidates = []
        for source, detector, value in (
            ("gas", self._gas_alert, reading.gas_ppm),
            ("proximity", self._proximity_alert, reading.rear_distance),
            ("fatigue", self._fatigue_alert, reading.eye_closure),
        ):
            hit = detector(value)
            if hit is not None:
                candidates.append((hit[0], source, hit[1]))

        # Cooldown filter: suppress repeats, but always allow escalation
        allowed = []
        for level, source, message in candidates:
            last = self._last_fired.get(source)
            if last is not None:
                last_tick, last_level = last
                in_cooldown = (self._tick - last_tick) < self.cooldown_ticks
                escalating = _SEVERITY[level] > _SEVERITY[last_level]
                if in_cooldown and not escalating:
                    continue
            allowed.append((level, source, message))

        if not allowed:
            return Alert("NORMAL", "none", "")

        allowed.sort(key=lambda a: _SEVERITY[a[0]], reverse=True)
        level, source, message = allowed[0]
        self._last_fired[source] = (self._tick, level)
        return Alert(level, source, message)