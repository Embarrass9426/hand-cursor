import sys
import traceback
import time

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
    assert "FINGER_EXTENDED_ANGLE" in CONFIG
    assert "FINGER_PARTIAL_BEND_ANGLE" in CONFIG
    assert "DEADZONE_THRESHOLD" in CONFIG
    assert "DEBOUNCE_FRAMES" in CONFIG
    assert "DOUBLE_CLICK_WINDOW_SEC" in CONFIG
    assert "FLASK_HOST" in CONFIG
    assert "DIP_CLICK_THRESHOLD" in CONFIG
    assert "SCROLL_TOUCH_THRESHOLD" in CONFIG
    assert "SCROLL_DOWN_TOUCH_THRESHOLD" in CONFIG
    assert "SCROLL_SPEED" in CONFIG
    assert "USE_ABSOLUTE_MAPPING" in CONFIG
    assert "CURSOR_LANDMARK" in CONFIG
    assert "INDEX_TIP_MCP_THRESHOLD" in CONFIG
    assert "RING_DIP_CLICK_THRESHOLD" in CONFIG

def test_import_filters():
    from filters import OneEuroFilter, DeadzoneFilter, LandmarkSmoother
    f = OneEuroFilter()
    x, y = f.apply(0.5, 0.5)
    assert abs(x - 0.5) < 0.01
    assert abs(y - 0.5) < 0.01

def test_import_camera():
    from camera import Camera

def test_import_hand_tracker():
    from hand_tracker import (
        HandTracker, calc_distance, calc_finger_angle, get_finger_state,
        is_finger_bent, is_finger_extended, is_finger_fully_bent,
        is_thumb_extended, is_open_palm, is_index_tip_below_pip, is_middle_tip_below_pip,
        is_ok_sign, is_closed_fist, is_index_dip_bent, is_middle_dip_bent,
        is_scroll_down, is_scroll_up, is_ring_dip_bent, calc_scroll_delta, GestureDebouncer, _LandmarkProxy
    )

def test_import_gesture_classifier():
    from gesture_classifier import (
        GestureClassifier, SEARCHING, IDLE, CURSOR, INDEX_DOWN, MIDDLE_DOWN,
        LEFT_CLICK, RIGHT_CLICK, DOUBLE_CLICK, DRAGGING,
        CLICK_DOWN, SCROLLING
    )

def test_import_cursor_controller():
    from cursor_controller import CursorController, ScreenMapper

def test_import_debug_overlay():
    from debug_overlay import draw_overlay

for name, fn in [
    ("config", test_import_config),
    ("filters", test_import_filters),
    ("camera", test_import_camera),
    ("hand_tracker", test_import_hand_tracker),
    ("gesture_classifier", test_import_gesture_classifier),
    ("cursor_controller", test_import_cursor_controller),
    ("debug_overlay", test_import_debug_overlay),
]:
    test(name, fn)

print()
print("=== Filter Tests ===")

def test_deadzone_filter():
    from filters import DeadzoneFilter
    f = DeadzoneFilter(threshold=0.01)
    x1, y1 = f.apply(0.5, 0.5)
    assert x1 == 0.5 and y1 == 0.5
    x2, y2 = f.apply(0.501, 0.501)
    assert x2 == 0.5 and y2 == 0.5
    x3, y3 = f.apply(0.52, 0.52)
    assert x3 == 0.52 and y3 == 0.52
    f.reset()
    x4, y4 = f.apply(0.1, 0.1)
    assert x4 == 0.1 and y4 == 0.1

def test_landmark_smoother():
    from filters import LandmarkSmoother
    from config import CONFIG
    s = LandmarkSmoother(CONFIG)
    class LM:
        def __init__(self, x, y):
            self.x = x
            self.y = y
    landmarks = [LM(0.1 * i, 0.1 * i) for i in range(21)]
    result = s.smooth(landmarks)
    assert len(result) == 21
    s.reset()

def test_one_euro_filter():
    from filters import OneEuroFilter
    f = OneEuroFilter(mincutoff=1.0, beta=0.007)
    import time as tmod
    tmod.sleep(0.01)
    x1, y1 = f.apply(0.0, 0.0)
    tmod.sleep(0.01)
    x2, y2 = f.apply(1.0, 1.0)
    assert 0 < x2 < 1.0

def test_gesture_debouncer():
    from hand_tracker import GestureDebouncer
    d = GestureDebouncer(debounce_frames=3)
    result = d.update({"a": True, "b": False})
    assert result["a"] is False
    assert result["b"] is False
    result = d.update({"a": True, "b": False})
    assert result["a"] is False
    result = d.update({"a": True, "b": False})
    assert result["a"] is True
    result = d.update({"a": False, "b": False})
    assert result["a"] is False
    d.reset()
    result = d.update({"a": True})
    assert result["a"] is False

for name, fn in [
    ("deadzone_filter", test_deadzone_filter),
    ("landmark_smoother", test_landmark_smoother),
    ("one_euro_filter", test_one_euro_filter),
    ("gesture_debouncer", test_gesture_debouncer),
]:
    test(name, fn)

print()
print("=== Gesture Helper Tests ===")

def make_landmark(x, y, z=0):
    class L:
        pass
    l = L()
    l.x = x
    l.y = y
    l.z = z
    return l


def make_hand(finger_states=None):
    """finger_states: dict like {'index': 'extended', 'middle': 'fully_bent', ...}
    Valid states: 'extended', 'partially_bent', 'fully_bent'
    Default: all fingers 'extended'."""
    if finger_states is None:
        finger_states = {}

    landmarks = [make_landmark(0.5, 0.5, 0) for _ in range(21)]

    landmarks[0] = make_landmark(0.5, 0.9, 0)

    fingers = {
        'index': (5, 6, 7, 8),
        'middle': (9, 10, 11, 12),
        'ring': (13, 14, 15, 16),
        'pinky': (17, 18, 19, 20),
    }

    for name, (mcp, pip, dip, tip) in fingers.items():
        state = finger_states.get(name, 'extended')
        landmarks[mcp] = make_landmark(0.5, 0.7, 0)
        if state == 'extended':
            landmarks[pip] = make_landmark(0.5, 0.5, 0)
            landmarks[dip] = make_landmark(0.5, 0.4, 0)
            landmarks[tip] = make_landmark(0.5, 0.3, 0)
        elif state == 'partially_bent':
            landmarks[pip] = make_landmark(0.55, 0.65, 0)
            landmarks[dip] = make_landmark(0.55, 0.55, 0)
            landmarks[tip] = make_landmark(0.55, 0.5, 0)
        elif state == 'fully_bent':
            landmarks[pip] = make_landmark(0.6, 0.7, 0)
            landmarks[dip] = make_landmark(0.6, 0.8, 0)
            landmarks[tip] = make_landmark(0.6, 0.85, 0)

    thumb_state = finger_states.get('thumb', 'extended')
    if thumb_state == 'extended':
        landmarks[1] = make_landmark(0.4, 0.8, 0)
        landmarks[2] = make_landmark(0.35, 0.7, 0)
        landmarks[3] = make_landmark(0.3, 0.6, 0)
        landmarks[4] = make_landmark(0.25, 0.5, 0)
    else:
        landmarks[1] = make_landmark(0.45, 0.85, 0)
        landmarks[2] = make_landmark(0.48, 0.8, 0)
        landmarks[3] = make_landmark(0.49, 0.75, 0)
        landmarks[4] = make_landmark(0.5, 0.85, 0)

    return landmarks

def test_calc_finger_angle():
    from hand_tracker import calc_finger_angle
    landmarks = [make_landmark(0.5, 0.9, 0) for _ in range(21)]
    landmarks[5] = make_landmark(0.5, 0.7, 0)
    landmarks[6] = make_landmark(0.5, 0.5, 0)
    angle = calc_finger_angle(landmarks, 5, 6, 0)
    assert abs(angle - 180.0) < 1.0
    landmarks[6] = make_landmark(0.6, 0.7, 0)
    angle = calc_finger_angle(landmarks, 5, 6, 0)
    assert abs(angle - 90.0) < 1.0

def test_get_finger_state():
    from hand_tracker import get_finger_state
    landmarks = [make_landmark(0.5, 0.9, 0) for _ in range(21)]
    landmarks[5] = make_landmark(0.5, 0.7, 0)
    landmarks[6] = make_landmark(0.5, 0.5, 0)
    assert get_finger_state(landmarks, 5, 6, 0) == "extended"
    landmarks[6] = make_landmark(0.55, 0.65, 0)
    assert get_finger_state(landmarks, 5, 6, 0) == "partially_bent"
    landmarks[6] = make_landmark(0.6, 0.7, 0)
    assert get_finger_state(landmarks, 5, 6, 0) == "fully_bent"

def test_is_finger_bent():
    from hand_tracker import is_finger_bent
    landmarks = make_hand(finger_states={'index': 'partially_bent'})
    assert is_finger_bent(landmarks, 5, 6)
    landmarks = make_hand(finger_states={'index': 'extended'})
    assert not is_finger_bent(landmarks, 5, 6)
    landmarks = make_hand(finger_states={'index': 'fully_bent'})
    assert not is_finger_bent(landmarks, 5, 6)

def test_is_open_palm():
    from hand_tracker import is_open_palm
    landmarks = make_hand()
    assert is_open_palm(landmarks)
    landmarks = make_hand(finger_states={'index': 'fully_bent'})
    assert not is_open_palm(landmarks)

def test_is_index_tip_below_pip():
    from hand_tracker import is_index_tip_below_pip
    landmarks = make_hand(finger_states={'index': 'fully_bent'})
    assert is_index_tip_below_pip(landmarks)
    landmarks = make_hand(finger_states={'index': 'extended'})
    assert not is_index_tip_below_pip(landmarks)

def test_is_middle_tip_below_pip():
    from hand_tracker import is_middle_tip_below_pip
    landmarks = make_hand(finger_states={'middle': 'fully_bent'})
    assert is_middle_tip_below_pip(landmarks)
    landmarks = make_hand(finger_states={'middle': 'extended'})
    assert not is_middle_tip_below_pip(landmarks)

def test_is_ok_sign():
    from hand_tracker import is_ok_sign
    from config import CONFIG
    landmarks = make_hand()
    landmarks[4].x = 0.5
    landmarks[4].y = 0.5
    landmarks[8].x = 0.5 + CONFIG["OK_SIGN_DISTANCE"] * 0.3
    landmarks[8].y = 0.5
    assert is_ok_sign(landmarks)
    landmarks[8].x = 0.5 + CONFIG["OK_SIGN_DISTANCE"] * 2
    assert not is_ok_sign(landmarks)

def test_is_closed_fist():
    from hand_tracker import is_closed_fist
    landmarks = make_hand(finger_states={
        'thumb': 'not_extended', 'index': 'fully_bent',
        'middle': 'fully_bent', 'ring': 'fully_bent', 'pinky': 'fully_bent'
    })
    assert is_closed_fist(landmarks)
    landmarks = make_hand()
    assert not is_closed_fist(landmarks)

def test_is_index_dip_bent():
    from hand_tracker import is_index_dip_bent
    from config import CONFIG
    landmarks = make_hand()
    # Tip (8) far from DIP (7) → not bent
    assert not is_index_dip_bent(landmarks)
    # Move tip close to DIP
    landmarks[8].x = landmarks[7].x
    landmarks[8].y = landmarks[7].y
    assert is_index_dip_bent(landmarks)

def test_is_middle_dip_bent():
    from hand_tracker import is_middle_dip_bent
    landmarks = make_hand()
    assert not is_middle_dip_bent(landmarks)
    landmarks[12].x = landmarks[11].x
    landmarks[12].y = landmarks[11].y
    assert is_middle_dip_bent(landmarks)

def test_is_scroll_down():
    from hand_tracker import is_scroll_down
    landmarks = make_hand()
    assert not is_scroll_down(landmarks)
    # Thumb tip (4) near ring MCP (13), pinky (20) far away -> scroll down
    ring_mcp_pos = (landmarks[13].x, landmarks[13].y)
    landmarks[4].x = ring_mcp_pos[0]
    landmarks[4].y = ring_mcp_pos[1]
    assert is_scroll_down(landmarks)
    # If pinky (20) also gets near ring MCP (13), it becomes scroll up, not scroll down
    landmarks[20].x = ring_mcp_pos[0]
    landmarks[20].y = ring_mcp_pos[1]
    assert not is_scroll_down(landmarks)

def test_is_scroll_up():
    from hand_tracker import is_scroll_up
    landmarks = make_hand()
    assert not is_scroll_up(landmarks)
    # Thumb tip (4) near ring MCP (13) but pinky (20) far -> not scroll up
    ring_mcp_pos = (landmarks[13].x, landmarks[13].y)
    landmarks[4].x = ring_mcp_pos[0]
    landmarks[4].y = ring_mcp_pos[1]
    assert not is_scroll_up(landmarks)
    # Both thumb tip (4) and pinky tip (20) near ring MCP (13) -> scroll up
    landmarks[20].x = ring_mcp_pos[0]
    landmarks[20].y = ring_mcp_pos[1]
    assert is_scroll_up(landmarks)

def test_calc_scroll_delta():
    from hand_tracker import calc_scroll_delta
    landmarks = make_hand()
    # No gesture -> 0
    assert calc_scroll_delta(landmarks, {}) == 0
    # Scroll down -> negative
    assert calc_scroll_delta(landmarks, {"scroll_down": True}) < 0
    # Scroll up -> positive
    assert calc_scroll_delta(landmarks, {"scroll_up": True}) > 0

def test_is_ring_dip_bent():
    from hand_tracker import is_ring_dip_bent
    from config import CONFIG
    landmarks = make_hand()
    assert not is_ring_dip_bent(landmarks)
    landmarks[16].x = landmarks[15].x
    landmarks[16].y = landmarks[15].y
    assert is_ring_dip_bent(landmarks)

for name, fn in [
    ("calc_finger_angle", test_calc_finger_angle),
    ("get_finger_state", test_get_finger_state),
    ("is_finger_bent", test_is_finger_bent),
    ("is_open_palm", test_is_open_palm),
    ("is_index_tip_below_pip", test_is_index_tip_below_pip),
    ("is_middle_tip_below_pip", test_is_middle_tip_below_pip),
    ("is_ok_sign", test_is_ok_sign),
    ("is_closed_fist", test_is_closed_fist),
    ("is_index_dip_bent", test_is_index_dip_bent),
    ("is_middle_dip_bent", test_is_middle_dip_bent),
    ("is_scroll_down", test_is_scroll_down),
    ("is_scroll_up", test_is_scroll_up),
    ("is_ring_dip_bent", test_is_ring_dip_bent),
    ("calc_scroll_delta", test_calc_scroll_delta),
]:
    test(name, fn)

print()
print("=== GestureClassifier Tests ===")

def test_classifier_starts_searching():
    from gesture_classifier import GestureClassifier, SEARCHING
    gc = GestureClassifier()
    assert gc.state == SEARCHING

def test_classifier_searching_to_idle():
    from gesture_classifier import GestureClassifier, SEARCHING, IDLE
    gc = GestureClassifier()
    result = gc.update(None, {})
    assert result["state"] == SEARCHING
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"ok_sign": True, "open_palm": False, "index_bent": False, "middle_bent": False, "closed_fist": False, "ring_dip_bent": False})
    assert result["state"] == IDLE

def test_classifier_idle_to_cursor():
    from gesture_classifier import GestureClassifier, IDLE, CURSOR
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"open_palm": True, "ok_sign": False, "index_bent": False, "middle_bent": False, "closed_fist": False, "ring_dip_bent": False, "scroll_delta": 0})
    assert result["state"] == CURSOR
    assert result["cursor_pos"] is not None

def test_classifier_lost_frames():
    from gesture_classifier import GestureClassifier, SEARCHING, IDLE
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = IDLE
    gc.lost_frames = 0
    for i in range(CONFIG["MAX_LOST_FRAMES"] - 1):
        result = gc.update(None, {"ring_dip_bent": False})
        assert result["state"] == IDLE
    result = gc.update(None, {})
    assert result["state"] == IDLE
    result = gc.update(None, {"ring_dip_bent": False})
    assert result["state"] == SEARCHING
    assert result["unlock"] is True

def test_classifier_index_click():
    from gesture_classifier import GestureClassifier, IDLE, CLICK_DOWN, LEFT_CLICK
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"index_bent": True, "middle_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False, "index_dip_bent": True, "middle_dip_bent": False})
    assert result["state"] == CLICK_DOWN
    result = gc.update(landmarks, {"index_bent": False, "middle_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False, "index_dip_bent": False, "middle_dip_bent": False})
    assert result["state"] == LEFT_CLICK
    assert result["action"] == "left_click"
    result = gc.update(landmarks, {"index_bent": False, "middle_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False, "index_dip_bent": False, "middle_dip_bent": False})
    assert result["state"] == IDLE

def test_classifier_drag():
    from gesture_classifier import GestureClassifier, IDLE, DRAGGING
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"index_bent": True, "middle_bent": False, "open_palm": False, "ok_sign": True, "closed_fist": False, "index_dip_bent": False, "middle_dip_bent": False, "ring_dip_bent": False})
    assert result["state"] == DRAGGING
    assert result["action"] == "drag_start"
    assert gc.is_dragging is True
    result = gc.update(landmarks, {"index_bent": False, "middle_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "index_dip_bent": False, "middle_dip_bent": False, "ring_dip_bent": False})
    assert result["state"] == IDLE
    assert result["action"] == "drag_end"
    assert gc.is_dragging is False

def test_classifier_drag_priority_over_click():
    from gesture_classifier import GestureClassifier, IDLE, DRAGGING
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"index_dip_bent": True, "middle_dip_bent": False, "open_palm": False, "ok_sign": True, "closed_fist": False, "ring_dip_bent": False})
    assert result["state"] == DRAGGING
    assert result["action"] == "drag_start"

def test_classifier_right_click():
    from gesture_classifier import GestureClassifier, IDLE, MIDDLE_DOWN, RIGHT_CLICK
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"middle_bent": True, "index_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False, "index_dip_bent": False, "middle_dip_bent": True})
    assert result["state"] == MIDDLE_DOWN
    result = gc.update(landmarks, {"middle_bent": False, "index_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False, "index_dip_bent": False, "middle_dip_bent": False})
    assert result["state"] == RIGHT_CLICK
    assert result["action"] == "right_click"
    result = gc.update(landmarks, {"middle_bent": False, "index_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False, "index_dip_bent": False, "middle_dip_bent": False})
    assert result["state"] == IDLE

def test_classifier_ring_double_click():
    from gesture_classifier import GestureClassifier, IDLE, DOUBLE_CLICK
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"ring_dip_bent": True, "index_dip_bent": False, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == DOUBLE_CLICK
    assert result["action"] == "double_click"
    result = gc.update(landmarks, {"ring_dip_bent": False, "index_dip_bent": False, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == IDLE

def test_classifier_scroll_mode():
    from gesture_classifier import GestureClassifier, CURSOR, SCROLLING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = CURSOR
    gc.scroll_start_time = time.time() - CONFIG["SCROLL_HOLD_SEC"] - 0.1
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"scroll_down": True, "scroll_delta": -15, "index_dip_bent": False, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == SCROLLING
    assert result["action"] is None

def test_classifier_scroll_priority():
    from gesture_classifier import GestureClassifier, CURSOR, SCROLLING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = CURSOR
    gc.scroll_start_time = time.time() - CONFIG["SCROLL_HOLD_SEC"] - 0.1
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"scroll_down": True, "scroll_delta": -15, "index_dip_bent": True, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == SCROLLING

def test_classifier_click_down_state():
    from gesture_classifier import GestureClassifier, IDLE, CLICK_DOWN
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"index_dip_bent": True, "middle_dip_bent": False, "ring_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == CLICK_DOWN

def test_classifier_click_down_to_drag():
    from gesture_classifier import GestureClassifier, IDLE, CLICK_DOWN, DRAGGING
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"index_dip_bent": True, "middle_dip_bent": False, "ring_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == CLICK_DOWN
    result = gc.update(landmarks, {"index_dip_bent": True, "middle_dip_bent": False, "ring_dip_bent": False, "open_palm": False, "ok_sign": True, "closed_fist": False})
    assert result["state"] == DRAGGING
    assert result["action"] == "drag_start"

def test_classifier_scroll_delta():
    from gesture_classifier import GestureClassifier, CURSOR, SCROLLING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = CURSOR
    gc.scroll_start_time = time.time() - CONFIG["SCROLL_HOLD_SEC"] - 0.1
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"scroll_up": True, "scroll_delta": 15, "index_dip_bent": False, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == SCROLLING
    assert result["scroll_delta"] == 15
    assert result["action"] is None
    result = gc.update(landmarks, {"scroll_up": True, "scroll_delta": 15, "index_dip_bent": False, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False})
    assert result["state"] == SCROLLING
    assert result["scroll_delta"] == 15
    assert result["action"] == "scroll"

def test_classifier_scroll_override_from_click_down():
    from gesture_classifier import GestureClassifier, CLICK_DOWN, SCROLLING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = CLICK_DOWN
    gc.index_down_start = time.time()
    gc.scroll_start_time = time.time() - CONFIG["SCROLL_HOLD_SEC"] - 0.1
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"scroll_down": True, "scroll_delta": -15, "index_dip_bent": True, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False})
    assert result["state"] == SCROLLING

def test_classifier_scroll_override_from_dragging():
    from gesture_classifier import GestureClassifier, DRAGGING, SCROLLING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = DRAGGING
    gc.is_dragging = True
    gc.scroll_start_time = time.time() - CONFIG["SCROLL_HOLD_SEC"] - 0.1
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"scroll_up": True, "scroll_delta": 15, "index_dip_bent": True, "middle_dip_bent": False, "open_palm": False, "ok_sign": False, "closed_fist": False, "ring_dip_bent": False})
    assert result["state"] == SCROLLING
    assert gc.is_dragging is False

def test_classifier_fist_unlock():
    from gesture_classifier import GestureClassifier, IDLE, SEARCHING
    from config import CONFIG
    gc = GestureClassifier()
    gc.state = IDLE
    landmarks = [make_landmark(0, 0, 0) for _ in range(21)]
    result = gc.update(landmarks, {"closed_fist": True, "open_palm": False, "ok_sign": False, "index_dip_bent": False, "middle_dip_bent": False, "ring_dip_bent": False})
    assert result["state"] == IDLE
    gc.fist_start_time = time.time() - CONFIG["FIST_HOLD_SEC"] - 0.1
    result = gc.update(landmarks, {"closed_fist": True, "open_palm": False, "ok_sign": False, "index_dip_bent": False, "middle_dip_bent": False, "ring_dip_bent": False})
    assert result["state"] == SEARCHING
    assert result["unlock"] is True

for name, fn in [
    ("classifier_starts_searching", test_classifier_starts_searching),
    ("classifier_searching_to_idle", test_classifier_searching_to_idle),
    ("classifier_idle_to_cursor", test_classifier_idle_to_cursor),
    ("classifier_lost_frames", test_classifier_lost_frames),
    ("classifier_index_click", test_classifier_index_click),
    ("classifier_drag", test_classifier_drag),
    ("classifier_drag_priority_over_click", test_classifier_drag_priority_over_click),
    ("classifier_right_click", test_classifier_right_click),
    ("classifier_ring_double_click", test_classifier_ring_double_click),
    ("classifier_scroll_mode", test_classifier_scroll_mode),
    ("classifier_scroll_priority", test_classifier_scroll_priority),
    ("classifier_click_down_state", test_classifier_click_down_state),
    ("classifier_click_down_to_drag", test_classifier_click_down_to_drag),
    ("classifier_scroll_delta", test_classifier_scroll_delta),
    ("classifier_scroll_override_from_click_down", test_classifier_scroll_override_from_click_down),
    ("classifier_scroll_override_from_dragging", test_classifier_scroll_override_from_dragging),
    ("classifier_fist_unlock", test_classifier_fist_unlock),
]:
    test(name, fn)

print()
print("=== CursorController Tests ===")

def test_cursor_right_click():
    from cursor_controller import CursorController
    cc = CursorController()
    assert hasattr(cc, "right_click")

def test_cursor_mapping_direction():
    from cursor_controller import CursorController
    cc = CursorController()
    center_x = cc.screen_w / 2
    center_y = cc.screen_h / 2
    mapped_x_right = (0.6 - 0.5) * 2.0 * cc.screen_w + center_x
    mapped_x_left = (0.4 - 0.5) * 2.0 * cc.screen_w + center_x
    assert mapped_x_right > center_x
    assert mapped_x_left < center_x

for name, fn in [
    ("cursor_right_click", test_cursor_right_click),
    ("cursor_mapping_direction", test_cursor_mapping_direction),
]:
    test(name, fn)

print()
print("=== ScreenMapper Tests ===")

def test_screen_mapper_16x9_screen():
    from cursor_controller import ScreenMapper
    s = ScreenMapper(1280, 720, 1920, 1080)
    assert s.effective_w == 1920
    assert s.effective_h == 1080
    assert s.offset_x == 0
    assert s.offset_y == 0

def test_screen_mapper_wider_screen():
    from cursor_controller import ScreenMapper
    s = ScreenMapper(1280, 720, 2560, 1080)
    assert s.effective_w == 1920
    assert s.effective_h == 1080
    assert s.offset_x == 320

def test_screen_mapper_center_mapping():
    from cursor_controller import ScreenMapper
    s = ScreenMapper(1280, 720, 1920, 1080)
    x, y = s.map(0.5, 0.5, invert_x=False)
    assert abs(x - 960.0) < 1.0
    assert abs(y - 540.0) < 1.0

def test_screen_mapper_invert_x():
    from cursor_controller import ScreenMapper
    s = ScreenMapper(1280, 720, 1920, 1080)
    x1, _ = s.map(0.3, 0.5, invert_x=True)
    x2, _ = s.map(0.7, 0.5, invert_x=True)
    assert x1 > x2

def test_screen_mapper_boundaries():
    from cursor_controller import ScreenMapper
    s = ScreenMapper(1280, 720, 1920, 1080)
    x, y = s.map(0.0, 0.0, invert_x=False)
    assert x == 0.0
    assert y == 0.0
    x, y = s.map(1.0, 1.0, invert_x=False)
    assert x == 1920.0
    assert y == 1080.0

for name, fn in [
    ("screen_mapper_16x9_screen", test_screen_mapper_16x9_screen),
    ("screen_mapper_wider_screen", test_screen_mapper_wider_screen),
    ("screen_mapper_center_mapping", test_screen_mapper_center_mapping),
    ("screen_mapper_invert_x", test_screen_mapper_invert_x),
    ("screen_mapper_boundaries", test_screen_mapper_boundaries),
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
