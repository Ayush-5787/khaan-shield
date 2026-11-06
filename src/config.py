"""
KHAAN-SHIELD configuration: every tunable number in one place.
Change thresholds here - never inside the logic files.
"""

# ---- Gas / CO (MQ-7, ppm) ----
GAS_WARN_PPM = 120      # rising trend - operator should ventilate
GAS_CRITICAL_PPM = 200  # inform supervisor
GAS_HALT_PPM = 300      # stop work, engine cut-off

# ---- Rear proximity (HC-SR04, meters) ----
PROX_WARN_M = 1.5       # slow down
PROX_CRITICAL_M = 1.0   # slow down + supervisor
PROX_HALT_M = 0.5       # STOP + engine cut-off

# ---- Fatigue (eye closure 0.0 open .. 1.0 closed) ----
FATIGUE_WARN = 0.3      # take micro-break
FATIGUE_CRITICAL = 0.5  # pull over and rest

# ---- Alert engine ----
COOLDOWN_TICKS = 5      # same source stays silent for N ticks unless it escalates

# ---- Camera ----
FATIGUE_CAMERA_INDEX = 0