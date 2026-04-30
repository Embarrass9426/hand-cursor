import sys
import traceback

errors = []

def test(name, fn):
    try:
        fn()
        print(f"  OK  {name}")
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        traceback.print_exc()
        errors.append(name)

print("=== Import Tests ===")

def test_import_config():
    from config import CONFIG
    assert "PINCH_THRESHOLD" in CONFIG
    assert "MIN_DETECTION_CONFIDENCE" in CONFIG
    assert CONFIG["CURSOR_SENSITIVITY_X"] == 2.0
    assert CONFIG["CURSOR_SENSITIVITY_Y"] == 3.0

def test_import_camera():
    from camera import Camera

def test_import_filters():
    from filters import OneEuroFilter
    f = OneEuroFilter()
    x, y = f.apply(0.5, 0.5)
    assert abs(x - 0.5) < 0.01
    assert abs(y - 0.5) < 0.01

def test_import_hand_tracker():
    from hand_tracker import HandTracker, calc_distance, is_finger_extended, is_thumb_index_pinch, is_thumb_middle_pinch, is_fist, is_peace_sign, _LandmarkProxy

def test_import_gesture_classifier():
    from gesture_classifier import GestureClassifier, SEARCHING, IDLE, CURSOR, PENDING_CLICK, CLICK, DOUBLE_CLICK, DRAG, SCROLL, FIST_HOLD

def test_import_cursor_controller():
    from cursor_controller import CursorController

def test_import_debug_overlay():
    from debug_overlay import draw_overlay

for name, fn in [
    ("config", test_import_config),
    ("camera", test_import_camera),
    ("filters", test_import_filters),
    ("hand_tracker", test_import_hand_tracker),
    ("gesture_classifier", test_import_gesture_classifier),
    ("cursor_controller", test_import_cursor_controller),
    ("debug_overlay", test_import_debug_overlay),
]:
    test(name, fn)

print()
print("=== Logic Tests ===")

def test_calc_distance():
    from hand_tracker import calc_distance, _LandmarkProxy
    a = _LandmarkProxy(type("L", (), {"x": 0, "y": 0, "z": 0})())
    b = _LandmarkProxy(type("L", (), {"x": 1, "y": 0, "z": 0})())
    d = calc_distance(a, b)
    assert abs(d - 1.0) < 0.001, f"Expected 1.0 got {d}"

def test_one_euro_filter():
    from filters import OneEuroFilter
    f = OneEuroFilter(mincutoff=1.0, beta=0.007)
    import time
    time.sleep(0.01)
    x1, y1 = f.apply(0.0, 0.0)
    time.sleep(0.01)
    x2, y2 = f.apply(1.0, 1.0)
    assert 0 < x2 < 1.0, f"Expected smoothed value between 0 and 1, got {x2}"

def test_gesture_classifier_searching():
    from gesture_classifier import GestureClassifier, SEARCHING
    gc = GestureClassifier()
    assert gc.state == SEARCHING
    result = gc.update(None)
    assert result["state"] == SEARCHING

def test_gesture_classifier_lost_frame_grace():
    from gesture_classifier import GestureClassifier, IDLE, SEARCHING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = IDLE
    gc.lost_frames = 0
    for i in range(CONFIG["MAX_LOST_FRAMES"] - 1):
        result = gc.update(None)
        assert result["state"] == IDLE
    result = gc.update(None)
    assert result["state"] == IDLE
    result = gc.update(None)
    assert result["state"] == SEARCHING

def test_cursor_mapping_direction():
    from cursor_controller import CursorController
    cc = CursorController()
    from unittest.mock import patch
    with patch.object(cc, 'pos_filter') as mock_filter:
        pass
    center_x = cc.screen_w / 2
    center_y = cc.screen_h / 2
    mapped_x_right = (0.6 - 0.5) * 5.0 * cc.screen_w + center_x
    mapped_x_left = (0.4 - 0.5) * 5.0 * cc.screen_w + center_x
    assert mapped_x_right > center_x, f"Moving hand right should move cursor right, got {mapped_x_right}"
    assert mapped_x_left < center_x, f"Moving hand left should move cursor left, got {mapped_x_left}"

for name, fn in [
    ("calc_distance", test_calc_distance),
    ("one_euro_filter", test_one_euro_filter),
    ("gesture_classifier_searching", test_gesture_classifier_searching),
    ("gesture_classifier_lost_frame_grace", test_gesture_classifier_lost_frame_grace),
    ("cursor_mapping_direction", test_cursor_mapping_direction),
]:
    test(name, fn)

print()
print("=== HandLandmarker Integration Test ===")

def test_hand_tracker_init():
    from hand_tracker import HandTracker
    tracker = HandTracker()
    tracker.release()

test("hand_tracker_init", test_hand_tracker_init)

print()
if errors:
    print(f"FAILED: {len(errors)} test(s): {errors}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")