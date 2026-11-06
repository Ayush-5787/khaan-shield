"""
KHAAN-SHIELD report: summarizes shift.log.jsonl into a shift report.
Run standalone with:  python -m src.report
"""
import json
import os
from collections import Counter

from .alert_logger import LOG_PATH


def print_report():
    print("============================================")
    print("KHAAN-SHIELD SHIFT REPORT")
    print("============================================")

    if not os.path.exists(LOG_PATH):
        print("No shift log found - nothing to report.")
        print("============================================")
        return

    levels = Counter()
    sources = Counter()
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            levels[rec.get("level", "?")] += 1
            sources[rec.get("source", "?")] += 1

    print(f"Total alerts : {sum(levels.values())}")
    for level in ("WARN", "CRITICAL", "HALT"):
        print(f"{level:13s}: {levels.get(level, 0)}")
    top = ", ".join(f"{s} x{c}" for s, c in sources.most_common())
    print(f"Top sources  : {top}" if top else "Top sources  : none")
    print("============================================")


if __name__ == "__main__":
    print_report()