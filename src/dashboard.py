"""
dashboard.py — Phase 4b: KHAAN Shield Live Dashboard
Streamlit web app jo events.csv ka data sundar page pe dikhata hai.

Chalana (project root se):
    streamlit run src/dashboard.py
Browser khud khul jayega: http://localhost:8501
"""

import csv
import os
from datetime import datetime

import streamlit as st

LOG_FILE = "logs/events.csv"

st.set_page_config(page_title="KHAAN Shield", page_icon="🛡️", layout="wide")


def load_events():
    """CSV se saare events load karo (file na ho to khali list)."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[1:] if len(rows) > 1 else []   # header skip


events = load_events()

# ================= HEADER =================
st.title("🛡️ KHAAN Shield — Driver Fatigue Dashboard")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ================= STATS =================
fatigue  = sum(1 for e in events if len(e) > 1 and e[1] == "FATIGUE")
critical = sum(1 for e in events if len(e) > 1 and e[1] == "CRITICAL")
tests    = sum(1 for e in events if len(e) > 1 and e[1] == "TEST")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Events", len(events))
c2.metric("⚠️ Fatigue Alerts", fatigue)
c3.metric("🚨 Critical Alerts", critical)
c4.metric("🧪 Test Events", tests)

st.divider()

# ================= CHART =================
st.subheader("📊 Events by Type")
if events:
    st.bar_chart({"count": {"FATIGUE": fatigue, "CRITICAL": critical, "TEST": tests}})
else:
    st.info("Chart ke liye data nahi hai — pehle monitor chalao!")

st.divider()

# ================= RECENT EVENTS =================
st.subheader("📋 Recent Events (naye pehle)")
if events:
    for e in reversed(events[-15:]):
        ts, etype, details = (e + ["", ""])[:3]
        if etype == "CRITICAL":
            st.error(f"🚨 **{ts}** — CRITICAL — {details}")
        elif etype == "FATIGUE":
            st.warning(f"⚠️ **{ts}** — FATIGUE — {details}")
        else:
            st.info(f"ℹ️ **{ts}** — {etype} — {details}")
else:
    st.info("Abhi koi events nahi. `python -m src.fatigue_monitor` chalao!")

st.divider()
if st.button("🔄 Refresh"):
    st.rerun()
st.caption("KHAAN Shield v1.0 — Phase 4b | Made with ❤️")