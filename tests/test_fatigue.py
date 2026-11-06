"""Tests for the fatigue module's pure math (no camera needed)."""
from types import SimpleNamespace

from src.fatigue import EAR_CLOSED, EAR_OPEN, LEFT_EYE, ear_to_closure, eye_aspect_ratio


def test_ear_to_closure_open_eye_is_zero():
    assert ear_to_closure(EAR_OPEN) == 0.0


def test_ear_to_closure_closed_eye_is_one():
    assert ear_to_closure(EAR_CLOSED) == 1.0


def test_ear_to_closure_clamps_out_of_range():
    assert ear_to_closure(1.0) == 0.0   # wider open than calibration
    assert ear_to_closure(0.0) == 1.0   # tighter than calibration


def test_eye_aspect_ratio_synthetic_open_eye():
    # Synthetic eye: 100 px wide, 28 px tall -> EAR = 0.28
    pts = {
        33:  SimpleNamespace(x=0,   y=0),    # outer corner
        160: SimpleNamespace(x=40,  y=-14),  # upper 1
        158: SimpleNamespace(x=60,  y=-14),  # upper 2
        133: SimpleNamespace(x=100, y=0),    # inner corner
        153: SimpleNamespace(x=60,  y=14),   # lower 2
        144: SimpleNamespace(x=40,  y=14),   # lower 1
    }
    ear = eye_aspect_ratio(pts, LEFT_EYE, 1, 1)
    assert abs(ear - 0.28) < 0.001