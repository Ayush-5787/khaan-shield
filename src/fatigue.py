"""
KHAAN-SHIELD Phase 3c: Camera fatigue monitor.

Webcam -> MediaPipe FaceLandmarker -> Eye Aspect Ratio (EAR) -> closure 0.0-1.0.
Camera runs in a background thread so the main loop never blocks.

Standalone test mode (live overlay for calibration):
    python -m src.fatigue
"""
import os
import sys
import threading
import time
import urllib.request
from collections import deque

import cv2
import numpy as np

from . import config

try:
    import mediapipe as mp
    MEDIAPIPE_OK = True
except ImportError:
    mp = None
    MEDIAPIPE_OK = False

# ---- Eye landmarks (identical indices in BOTH MediaPipe APIs) ----
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# ---- Calibration (tuned to measured values - re-verify with the overlay) ----
EAR_OPEN = 0.25     # measured open-eye EAR
EAR_CLOSED = 0.08   # provisional closed-eye EAR - verify with overlay
WINDOW_SIZE = 30    # rolling window (~1 second at 30 fps)

# ---- Model file for the Tasks API ----
_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "face_landmarker.task")
_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
              "face_landmarker/float16/1/face_landmarker.task")


def _ensure_model() -> str:
    """Download the Tasks-API model once, then reuse it forever."""
    if os.path.exists(_MODEL_PATH):
        return _MODEL_PATH
    os.makedirs(_MODEL_DIR, exist_ok=True)
    print("[FATIGUE] downloading face_landmarker.task (~3.7 MB, one-time)...")
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    print("[FATIGUE] model ready")
    return _MODEL_PATH


def _make_landmarker():
    """Create a face landmarker using whichever MediaPipe API is installed."""
    if hasattr(mp, "tasks") and hasattr(mp.tasks, "vision"):
        try:
            BaseOptions = mp.tasks.BaseOptions
        except AttributeError:
            from mediapipe.tasks import python as _mp_python
            BaseOptions = _mp_python.BaseOptions
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_ensure_model()),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
        )
        return mp.tasks.vision.FaceLandmarker.create_from_options(options)
    # Legacy Solutions API (older mediapipe, e.g. Raspberry Pi)
    return mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )


def _process(landmarker, rgb):
    """Run detection. Returns list of faces (list of landmarks) or None."""
    if hasattr(landmarker, "detect"):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
        return result.face_landmarks or None
    result = landmarker.process(rgb)
    return result.multi_face_landmarks or None


def ear_to_closure(ear: float) -> float:
    """Map EAR to closure: EAR_OPEN -> 0.0, EAR_CLOSED -> 1.0, clamped."""
    span = EAR_OPEN - EAR_CLOSED
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (EAR_OPEN - ear) / span))


def eye_aspect_ratio(landmarks, eye_idx, w, h) -> float:
    """Classic EAR: vertical eye openness / horizontal eye width."""
    p = [(landmarks[i].x * w, landmarks[i].y * h) for i in eye_idx]
    p1, p2, p3, p4, p5, p6 = p
    horiz = np.hypot(p4[0] - p1[0], p4[1] - p1[1])
    vert = (np.hypot(p6[0] - p2[0], p6[1] - p2[1]) +
            np.hypot(p5[0] - p3[0], p5[1] - p3[1])) / 2.0
    return vert / horiz if horiz > 0 else 0.0


def _open_camera(camera_index):
    """Open the webcam. MSMF (modern Windows backend) first - the legacy
    DSHOW path delivered corrupted buffers on this machine (static noise)."""
    if sys.platform == "win32":
        cap = cv2.VideoCapture(camera_index, cv2.CAP_MSMF)
        if cap.isOpened():
            return cap
        print(f"[FATIGUE] MSMF open failed at index {camera_index} - trying default backend")
    return cv2.VideoCapture(camera_index)


class FatigueSensor:
    """Background-thread webcam monitor. tick() -> rolling closure 0.0-1.0."""

    def __init__(self, camera_index=None, window_size=WINDOW_SIZE):
        if not MEDIAPIPE_OK:
            raise RuntimeError("mediapipe not installed: pip install mediapipe opencv-python")
        self.camera_index = config.FATIGUE_CAMERA_INDEX if camera_index is None else camera_index
        self.cap = _open_camera(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"No webcam found at index {self.camera_index}")
        self.landmarker = _make_landmarker()
        self.window = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._latest_ear = EAR_OPEN
        self._latest_closure = 0.0
        self._face_ever_seen = False
        self._no_face_warned = False
        self._start_time = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = _process(self.landmarker, rgb)

            ear = self._latest_ear  # freeze last value if face lost
            face_seen = faces is not None
            if face_seen:
                lm = faces[0]
                ear = (eye_aspect_ratio(lm, LEFT_EYE, w, h) +
                       eye_aspect_ratio(lm, RIGHT_EYE, w, h)) / 2.0
            closure = ear_to_closure(ear)

            with self._lock:
                self._latest_ear = ear
                self._latest_closure = closure
                if face_seen:
                    self.window.append(closure)
                    if not self._face_ever_seen:
                        self._face_ever_seen = True
                        print("[FATIGUE] face detected - eye tracking live")

            if not self._face_ever_seen and not self._no_face_warned \
                    and time.time() - self._start_time > 5:
                self._no_face_warned = True
                print("[FATIGUE] no face seen for 5s - check camera angle, cover, or lighting")

            time.sleep(0.03)  # ~30 fps cap, keeps CPU low

    def tick(self) -> float:
        """Rolling-average closure over the last ~1 s (0.0 open .. 1.0 closed)."""
        with self._lock:
            if not self.window:
                return 0.0
            return sum(self.window) / len(self.window)

    def close(self):
        self._running = False
        self._thread.join(timeout=3.0)
        if self._thread.is_alive():
            # Thread stuck in a blocking read - NEVER release underneath it.
            # Releasing mid-read is what wedges the Windows driver.
            print("[FATIGUE] camera thread stuck - leaving handle to OS cleanup")
            return
        self.cap.release()


def run_test():
    """Live calibration/demo overlay. Press 'q' to quit."""
    if not MEDIAPIPE_OK:
        raise SystemExit("mediapipe not installed: pip install mediapipe opencv-python")

    print("Opening camera...")
    cap = _open_camera(config.FATIGUE_CAMERA_INDEX)
    if not cap.isOpened():
        raise SystemExit("No webcam found - check privacy settings / other apps")

    try:
        print("Warming up model... first window may take ~5-10 seconds, please wait")
        landmarker = _make_landmarker()
        window = deque(maxlen=WINDOW_SIZE)

        # ---- Watchdog: reject black, frozen, or static-noise feeds ----
        print("Checking camera feed quality (up to ~10 s)...")
        got_frame = False
        prev = None
        for _ in range(50):
            ok, frame = cap.read()
            if ok and frame is not None:
                if prev is not None:
                    diff = cv2.absdiff(frame, prev).mean()
                    if frame.mean() < 5.0:
                        prev = frame; continue          # black feed
                    if diff > 40.0:
                        prev = frame; continue          # static noise
                    if diff < 0.5:
                        prev = frame; continue          # frozen feed
                    got_frame = True
                    break
                prev = frame.copy()
            time.sleep(0.2)
        if not got_frame:
            raise SystemExit(
                "Camera feed is black, frozen, or noise. Fix checklist:\n"
                "  1) REBOOT the laptop (resets a corrupted driver)\n"
                "  2) open the privacy shutter (HP slide cover)\n"
                "  3) close the Windows Camera app / video-call apps\n"
                "  4) Device Manager: disable + re-enable the webcam"
            )
        print("Camera OK - starting overlay")

        print("Fatigue monitor test - press 'q' to quit")
        print("Close your eyes for a few seconds and watch CLOSURE/AVG rise.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = _process(landmarker, rgb)

            ear, face_seen = EAR_OPEN, False
            if faces:
                face_seen = True
                lm = faces[0]
                ear = (eye_aspect_ratio(lm, LEFT_EYE, w, h) +
                       eye_aspect_ratio(lm, RIGHT_EYE, w, h)) / 2.0
                window.append(ear_to_closure(ear))

            closure = ear_to_closure(ear)
            avg = sum(window) / len(window) if window else 0.0

            color = (0, 200, 0)
            if avg >= config.FATIGUE_CRITICAL:
                color = (0, 0, 255)
            elif avg >= config.FATIGUE_WARN:
                color = (0, 200, 255)

            if not face_seen:
                status = "NO FACE"
            elif avg < config.FATIGUE_WARN:
                status = "ALERT"
            elif avg < config.FATIGUE_CRITICAL:
                status = "MICRO-BREAK"
            else:
                status = "REST NOW"

            cv2.rectangle(frame, (0, 0), (w, 70), (30, 30, 30), -1)
            cv2.putText(frame, f"EAR {ear:.2f}  CLOSURE {closure*100:3.0f}%  AVG {avg*100:3.0f}%",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, status, (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.imshow("KHAAN-SHIELD fatigue monitor (q=quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        # ALWAYS release the camera - even on Ctrl+C
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released cleanly.")


if __name__ == "__main__":
    run_test()