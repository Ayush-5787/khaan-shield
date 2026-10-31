"""
telegram_alert.py — Phase 3b: KHAAN Shield Telegram Alert Engine
Supervisor ke phone par real-time alerts bhejta hai.

Setup (ek baar):
1. @BotFather se bot banao -> TOKEN copy karo
2. Token ko FILE mein kabhi mat likho (GitHub-safe!)
   Har terminal session mein ye chalao:
       $env:KHAAN_BOT_TOKEN = "apna-token"
3. Bot ko Telegram se ek baar "hi" bhejo (chat ID activate karne ke liye)

Test karne ke liye:  python -m src.telegram_alert
"""

import os
import requests

# ================== CONFIG ==================
# Token SIRF environment variable se aayega — file mein kabhi nahi!
# (Public repo pe hardcoded token = koi bhi bot control kar sakta hai)
BOT_TOKEN = os.environ.get("KHAAN_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("KHAAN_CHAT_ID", "5415570983")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
# ============================================


def send_message(text):
    """Telegram par message bhejo. Fail ho to system CRASH NAHI hoga
    (fatigue detection kabhi rukni nahi chahiye!)."""
    try:
        r = requests.post(
            f"{API_BASE}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if r.status_code == 200:
            print("[TG] alert sent ✔")
            return True
        print(f"[TG] failed ({r.status_code}): {r.text[:120]}")
        return False
    except Exception as e:
        print(f"[TG] failed (system continues): {e}")
        return False


def alert_fatigue(confidence=0.8):
    """FATIGUE alert — aankhein ~2 sec band. fatigue_monitor.py isse call karta hai."""
    msg = (
        "⚠️ <b>FATIGUE ALERT</b>\n"
        "👀 Driver ke aankhein 2+ sec se band hain!\n"
        f"📊 Confidence: {confidence:.0%}\n"
        "🚜 KHAAN Shield monitoring active..."
    )
    return send_message(msg)


def alert_critical(message=None):
    """CRITICAL alert — aankhein ~5 sec band. Custom message bhi chalega."""
    if message is None:
        message = (
            "🚨 <b>CRITICAL ALERT</b>\n"
            "😴 Driver 5+ sec se aankhein band — SAMBHAVIT SO GAYA!\n"
            "📞 TURANT contact karo!"
        )
    return send_message(message)


def alert_test():
    """Simple test message — setup verify karne ke liye."""
    return send_message("🧪 <b>KHAAN Shield test</b> — system online! ✅")


if __name__ == "__main__":
    print("=== Telegram Alert Engine Test ===")
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN set nahi hai!")
        print("   PowerShell mein ye chalao (har naye terminal mein ek baar):")
        print('   $env:KHAAN_BOT_TOKEN = "apna-botfather-token"')
        print("   Phir dobara: python -m src.telegram_alert")
    else:
        alert_test()