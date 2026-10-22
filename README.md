`# KHAAN-SHIELD v0.1 Safety system for open-cast mine dumpers. Pure-Python decision engine with hardware-independent alert arbitration.

Problem
Dumper operators face gas spikes, rear-collision risks, and driver fatigue. Current systems are siloed and hardware-coupled.

Architecture
Sensing - src/sensors.py simulated now, hardware later
Decision - src/alert_engine.py pure Python arbitration, no hardware deps
Action - src/notifier.py stub for buzzer/SMS/engine cut-off
Logging - src/alert_logger.py JSONL append-only
Reporting - src/report.py shift summary
Live dashboard - web_preview.py Flask view of logs/khaan.log
Runpowershell
pip install flask .\demo.ps1 # one-click: dashboard + simulation + browser

manual
python web_preview.py # terminal 1 -> http://localhost:5000 python -m src.main # terminal 2

## Test
```powershell
python -m pytest tests/ -v


Save the file (Ctrl+S). Done ✅