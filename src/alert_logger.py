import json, os, time
from datetime import datetime

class AlertLogger:
    def __init__(self, path="logs/alerts.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, alert):
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "epoch": round(time.time(), 3),
            "level": alert.level,
            "source": alert.source,
            "message": alert.message,
            "action": alert.action,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]