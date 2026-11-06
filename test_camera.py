"""Minimal camera test - no mediapipe, no threads, just OpenCV."""
import sys

import cv2

for idx in (0, 1, 2):
    if sys.platform == "win32":
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(idx)
    ok, frame = cap.read()
    if ok:
        print(f"CAMERA OK at index {idx} - frame {frame.shape}")
        cv2.imshow("camera test (any key quits)", frame)
        cv2.waitKey(0)
        cap.release()
        break
    print(f"index {idx}: FAILED")
    cap.release()
else:
    print("NO CAMERA FOUND on any index - check privacy settings / other apps")