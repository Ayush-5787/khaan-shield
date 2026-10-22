"""Shift report - summarizes alerts from logs/alerts.jsonl"""
import json
import os
from collections import Counter

class ShiftReport:
    def __init__(self, path="logs/alerts.jsonl"):
        self.path = path

    def load(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def summarize(self):
        records = self.load()
        counts = Counter(r["level"] for r in records)
        source_counts = Counter(r["source"] for r in records if r["level"] != "NORMAL")
        top_source = source_counts.most_common(1)[0][0] if source_counts else "none"

        print("=== KHAAN-SHIELD Shift Report ===")
        print(f"Total alerts logged: {len(records)}")
        print(f"WARN: {counts.get('WARN',0)} | CRITICAL: {counts.get('CRITICAL',0)} | HALT: {counts.get('HALT',0)}")
        print(f"Top hazard source: {top_source}")
        print("\nLast 5 alerts:")
        for r in records[-5:]:
            print(f"  {r['ts']}  {r['level']:8s}  [{r['source']}] {r['message']}")

if __name__ == "__main__":
    ShiftReport().summarize()