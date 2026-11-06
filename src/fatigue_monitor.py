"""
fatigue_monitor.py — KHAAN Shield: Phase 3c + 3b + 4a FULL INTEGRATED (v5)
v5 FIX: AUTO camera scan (index 0/1/2) + quality check — IR/black camera
        ko skip karke asli RGB camera khud dhoondh lega! + MJPG force.

Flow:
- Aankhein ~2 sec band = FATIGUE  -> Telegram alert + CSV log
- Aankhein ~5 sec band = CRITICAL -> Telegram alert + CSV log + beep

Chalana:  python -m src.fatigue_monitor    (project root se)
Band kar: video window ke andar 'q' dabao
"""

import os
import time
from collections import deque

import cv2
import requests

from src.telegram_alert import alert_fatigue, alert_critical
from src.event_logger import log_event

# ================== TUNING (zaroorat ho to badlo) ==================
CAMERA_INDEX     = 0      # pehle YE try hoga, phir 1, 2 auto-scan
FATIGUE_SECONDS  = 2.0    # itni der aankhein band = fatigue alert
CRITICAL_SECONDS = 5.0    # itni der band = CRITICAL alert
SMOOTH_FRAMES    = 8      # flicker hatane ke liye itne frames ka average
SHOW_DEBUG       = True   # True = face/eye boxes + counter dikhao
# ===================================================================

CASCADE_DIR = "models"
FACE_FILE   = "haarcascade_frontalface_default.xml"
EYE_FILE    = "haarcascade_eye.xml"
RAW_BASE    = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/"

_face_cascade = None
_eye_cascade  = None


def _get_cascade(filename):
    """Cascade load karo (cv2 bundled, warna internet se download)."""
    try:
        bundled = os.path.join(cv2.data.haarcascades, filename)
        if os.path.exists(bundled):
            c = cv2.CascadeClassifier(bundled)
            if not c.empty():
                print(f"[OK] {filename} (cv2 bundled)")
                return c
    except Exception:
        pass

    os.makedirs(CASCADE_DIR, exist_ok=True)
    local = os.path.join(CASCADE_DIR, filename)
    if not os.path.exists(local):
        print(f"[DL] {filename} download ho raha hai...")
        r = requests.get(RAW_BASE + filename, timeout=30)
        r.raise_for_status()
        with open(local, "wb") as f:
            f.write(r.content)
        print(f"[DL] saved -> {local}")
    print(f"[OK] {filename} (models/ folder)")
    return cv2.CascadeClassifier(local)


def _brightness(frame):
    """Frame ki average brightness (0-255). Black/garbage frame = bahut kam."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def _open_camera():
    """Saare cameras scan karo (index 0,1,2 x DSHOW/MSMF backend).
    Har ek se test frame lo — BLACK/garbage frame wala camera SKIP karo
    (HP laptops ka IR camera black dikhata hai — wo nahi chahiye!)."""
    indices = [CAMERA_INDEX] + [i for i in (0, 1, 2) if i != CAMERA_INDEX]
    for idx in indices:
        for name, backend in [("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF)]:
            print(f"[CAM] index {idx} + backend {name} try kar raha hoon...")
            cap = cv2.VideoCapture(idx, backend)
            if not cap.isOpened():
                print(f"[CAM]   -> open fail")
                cap.release()
                continue

            # MJPG + 640x480 force (garbage frames ka classic fix)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Warm-up: pehle 15 frames discard (shuru mein garbage aata hai)
            last_frame = None
            for _ in range(15):
                ok, frame = cap.read()
                if ok and frame is not None:
                    last_frame = frame
                time.sleep(0.03)

            if last_frame is None:
                print(f"[CAM]   -> khula par koi frame nahi mila")
                cap.release()
                continue

            q = _brightness(last_frame)
            if q < 8:
                print(f"[CAM]   -> frame BLACK/garbage (brightness {q:.1f}) "
                      f"— shayad IR camera hai, SKIP!")
                cap.release()
                continue

            print(f"[OK] asli camera mila! index {idx}, backend {name} "
                  f"(brightness {q:.1f})")
            return cap
    return None


def detect_face_and_eyes(frame):
    """Face + aankhein detect karo (auto-brightness ke saath).
    Returns: (face_rect ya None, eyes_list)"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.15, minNeighbors=4, minSize=(60, 60))
    if len(faces) == 0:
        return None, []

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    roi = gray[y:y + int(h * 0.55), x:x + w]
    eyes = _eye_cascade.detectMultiScale(
        roi, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))
    return (x, y, w, h), eyes


def _beep():
    try:
        import winsound
        winsound.Beep(1000, 700)
    except Exception:
        pass


def run_monitor():
    global _face_cascade, _eye_cascade

    print("=== KHAAN Shield: Fatigue Monitor (v5 + auto camera scan) ===")
    try:
        _face_cascade = _get_cascade(FACE_FILE)
        _eye_cascade  = _get_cascade(EYE_FILE)
    except Exception as e:
        print(f"❌ Cascade files load/download nahi ho paye: {e}")
        return
    if _face_cascade.empty() or _eye_cascade.empty():
        print("❌ Cascade file corrupt — 'models' folder delete karke dobara chalao!")
        return

    cap = _open_camera()
    if cap is None:
        print("❌ Koi asli camera nahi mila! Checklist:")
        print("   1. Zoom/Teams/Chrome band karo (camera busy)")
        print("   2. Windows Camera app mein video dikhti hai? Confirm karo")
        print("   3. Laptop restart karo (driver stuck)")
        return
    print("Camera chalu! Tips:")
    print("   - Light MUH pe aaye (peeche window na ho)")
    print("   - Laptop se ~50-70 cm door, seedha camera dekho\n")

    recent = deque(maxlen=SMOOTH_FRAMES)
    closed_since = None
    fatigue_sent = False
    critical_sent = False
    fail_count = 0
    dark_count = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            fail_count += 1
            if fail_count >= 120:
                print("❌ Camera frames de hi nahi raha — restart karke try karo.")
                break
            time.sleep(0.05)
            continue
        fail_count = 0

        # Garbage/black frame guard — ise detection mein mat daalo!
        if _brightness(frame) < 8:
            dark_count += 1
            if dark_count % 90 == 30:
                print("[CAM] black frames aa rahe hain — camera switch ho gaya hoga?")
            if dark_count > 300:
                print("❌ Bahut zyada black frames — 'q' dabao, dobara chalao.")
            time.sleep(0.05)
            continue
        dark_count = 0

        frame = cv2.flip(frame, 1)
        face, eyes = detect_face_and_eyes(frame)

        # Debug boxes: face = hara, aankhein = neele
        if SHOW_DEBUG and face is not None:
            fx, fy, fw, fh = face
            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (0, 255, 0), 2)
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(frame, (fx + ex, fy + ey),
                              (fx + ex + ew, fy + ey + eh), (255, 200, 0), 2)

        # No face -> 'open' maano (galat alert se bachne ke liye)
        recent.append(1 if (face is None or len(eyes) >= 1) else 0)
        eyes_closed = (
            len(recent) == recent.maxlen
            and sum(recent) / len(recent) < 0.25
        )

        now = time.time()
        status, color = "AWAKE", (0, 200, 0)

        if eyes_closed:
            if closed_since is None:
                closed_since = now
            closed_for = now - closed_since

            if closed_for >= CRITICAL_SECONDS:
                status, color = f"CRITICAL! eyes closed {closed_for:.0f}s", (0, 0, 255)
                if not critical_sent:
                    alert_critical(
                        "🚨 <b>CRITICAL</b>\n👀 Driver ne 5+ sec aankhein band ki — TURANT check karo!"
                    )
                    log_event("CRITICAL", f"eyes closed {closed_for:.0f}s")
                    _beep()
                    critical_sent = True
            elif closed_for >= FATIGUE_SECONDS:
                status, color = f"FATIGUE! eyes closed {closed_for:.0f}s", (0, 165, 255)
                if not fatigue_sent:
                    alert_fatigue(confidence=min(0.99, closed_for / CRITICAL_SECONDS))
                    log_event("FATIGUE", f"eyes closed {closed_for:.0f}s")
                    fatigue_sent = True
            else:
                status, color = f"eyes closing... {closed_for:.1f}s", (0, 165, 255)
        else:
            closed_since = None
            fatigue_sent = False
            critical_sent = False

        # HUD: status + debug counter
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 85), (0, 0, 0), -1)
        cv2.putText(frame, status, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        if SHOW_DEBUG:
            dbg = f"FACE: {'YES' if face is not None else 'NO '} | EYES: {len(eyes)}"
            dbg_color = (0, 255, 0) if face is not None else (0, 0, 255)
            cv2.putText(frame, dbg, (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, dbg_color, 2)
        cv2.putText(frame, "'q' = quit", (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("KHAAN Shield - Fatigue Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\nMonitor band ho gaya. Safe travels! 🚜")


if __name__ == "__main__":
    run_monitor()