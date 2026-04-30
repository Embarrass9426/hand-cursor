import time
from config import CONFIG
from hand_tracker import calc_distance, is_finger_extended, is_fist, is_thumb_middle_pinch


SEARCHING = "SEARCHING"
IDLE = "IDLE"
CURSOR = "CURSOR"
PENDING_CLICK = "PENDING_CLICK"
CLICK = "CLICK"
DOUBLE_CLICK = "DOUBLE_CLICK"
DRAG = "DRAG"
SCROLL = "SCROLL"
FIST_HOLD = "FIST_HOLD"


class GestureClassifier:
    def __init__(self):
        self.state = SEARCHING
        self.pinch_start_time = 0
        self.prev_wrist_y = None
        self.lost_frames = 0
        self.is_dragging = False
        self.unlock_cooldown = 0
        self.fist_start_time = None

    def update(self, landmarks):
        if landmarks is None:
            self.lost_frames += 1
            if self.lost_frames > CONFIG["MAX_LOST_FRAMES"]:
                if self.state != SEARCHING:
                    self._transition(SEARCHING)
                self.prev_wrist_y = None
                self.is_dragging = False
                self.fist_start_time = None
                return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0, "unlock": True}
            return {"state": self.state, "cursor_pos": None, "scroll_delta": 0}

        self.lost_frames = 0

        if self.unlock_cooldown > 0:
            self.unlock_cooldown -= 1

        if self.state == SEARCHING:
            return self._handle_searching(landmarks)

        if self.state == FIST_HOLD:
            return self._handle_fist_hold(landmarks)

        if is_fist(landmarks):
            if self.fist_start_time is None:
                self.fist_start_time = time.time()
            hold_duration = time.time() - self.fist_start_time
            if hold_duration >= CONFIG["FIST_HOLD_SEC"]:
                self.is_dragging = False
                self.prev_wrist_y = None
                self.fist_start_time = None
                self.unlock_cooldown = 30
                self._transition(SEARCHING)
                return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0, "unlock": True}
            progress = hold_duration / CONFIG["FIST_HOLD_SEC"]
            return {"state": FIST_HOLD, "cursor_pos": None, "scroll_delta": 0, "fist_progress": progress}
        else:
            self.fist_start_time = None

        thumb_index = calc_distance(landmarks[4], landmarks[8])
        thumb_middle = calc_distance(landmarks[4], landmarks[12])
        wrist = landmarks[0]

        if self.state == IDLE:
            return self._handle_idle(landmarks, thumb_index, thumb_middle, wrist)

        if self.state == CURSOR:
            return self._handle_cursor(landmarks, thumb_index, thumb_middle, wrist)

        if self.state == PENDING_CLICK:
            return self._handle_pending_click(landmarks, thumb_index, thumb_middle, wrist)

        if self.state == DRAG:
            return self._handle_drag(landmarks, thumb_index, wrist)

        if self.state == SCROLL:
            return self._handle_scroll(landmarks, thumb_index, wrist)

        return {"state": self.state, "cursor_pos": None, "scroll_delta": 0}

    def _transition(self, new_state):
        if CONFIG["PRINT_STATE_CHANGES"] and new_state != self.state:
            print(f"[State] {self.state} -> {new_state}")
        self.state = new_state

    def _handle_searching(self, landmarks):
        from hand_tracker import is_thumb_index_pinch

        if is_thumb_index_pinch(landmarks):
            self._transition(IDLE)
            return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0}
        return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0}

    def _handle_idle(self, landmarks, thumb_index, thumb_middle, wrist):
        if is_thumb_middle_pinch(landmarks):
            self._transition(DOUBLE_CLICK)
            return {"state": DOUBLE_CLICK, "cursor_pos": None, "scroll_delta": 0}

        if thumb_index > CONFIG["OPEN_THRESHOLD"]:
            self.prev_wrist_y = wrist.y
            self._transition(CURSOR)
            return {
                "state": CURSOR,
                "cursor_pos": (wrist.x, wrist.y),
                "scroll_delta": 0,
            }

        if thumb_index < CONFIG["PINCH_THRESHOLD"]:
            self.pinch_start_time = time.time()
            self._transition(PENDING_CLICK)
            return {"state": PENDING_CLICK, "cursor_pos": None, "scroll_delta": 0}

        return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0}

    def _handle_cursor(self, landmarks, thumb_index, thumb_middle, wrist):
        if is_thumb_middle_pinch(landmarks):
            self._transition(DOUBLE_CLICK)
            return {"state": DOUBLE_CLICK, "cursor_pos": None, "scroll_delta": 0}

        if thumb_index < CONFIG["PINCH_THRESHOLD"] and thumb_middle > CONFIG["THREE_PINCH_THRESHOLD"]:
            self.pinch_start_time = time.time()
            self._transition(PENDING_CLICK)
            return {"state": PENDING_CLICK, "cursor_pos": None, "scroll_delta": 0}

        if thumb_index < CONFIG["THREE_PINCH_THRESHOLD"] and thumb_middle < CONFIG["THREE_PINCH_THRESHOLD"]:
            self.prev_wrist_y = wrist.y
            self._transition(SCROLL)
            return {"state": SCROLL, "cursor_pos": None, "scroll_delta": 0}

        self.prev_wrist_y = wrist.y
        return {
            "state": CURSOR,
            "cursor_pos": (wrist.x, wrist.y),
            "scroll_delta": 0,
        }

    def _handle_pending_click(self, landmarks, thumb_index, thumb_middle, wrist):
        hold_duration = time.time() - self.pinch_start_time
        drag_progress = min(hold_duration / CONFIG["DRAG_HOLD_SEC"], 1.0)
        pinch_pos = ((landmarks[4].x + landmarks[8].x) / 2, (landmarks[4].y + landmarks[8].y) / 2)

        if hold_duration >= CONFIG["DRAG_HOLD_SEC"]:
            self.is_dragging = True
            self._transition(DRAG)
            return {"state": DRAG, "cursor_pos": (wrist.x, wrist.y), "scroll_delta": 0}

        if thumb_index > CONFIG["OPEN_THRESHOLD"]:
            self._transition(CLICK)
            return {"state": CLICK, "cursor_pos": None, "scroll_delta": 0}

        return {"state": PENDING_CLICK, "cursor_pos": None, "scroll_delta": 0, "drag_progress": drag_progress, "pinch_pos": pinch_pos}

    def _handle_drag(self, landmarks, thumb_index, wrist):
        if thumb_index > CONFIG["OPEN_THRESHOLD"]:
            self.is_dragging = False
            self._transition(IDLE)
            return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0}

        return {
            "state": DRAG,
            "cursor_pos": (wrist.x, wrist.y),
            "scroll_delta": 0,
        }

    def _handle_scroll(self, landmarks, thumb_index, wrist):
        if thumb_index > CONFIG["SCROLL_EXIT_THRESHOLD"]:
            self._transition(IDLE)
            self.prev_wrist_y = None
            return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0}

        scroll_delta = 0
        if self.prev_wrist_y is not None:
            delta_y = wrist.y - self.prev_wrist_y
            scroll_delta = delta_y * CONFIG["SCROLL_SENSITIVITY"]

        self.prev_wrist_y = wrist.y
        return {"state": SCROLL, "cursor_pos": None, "scroll_delta": scroll_delta}

    def _handle_fist_hold(self, landmarks):
        if is_fist(landmarks):
            hold_duration = time.time() - self.fist_start_time if self.fist_start_time else 0
            if hold_duration >= CONFIG["FIST_HOLD_SEC"]:
                self.is_dragging = False
                self.prev_wrist_y = None
                self.fist_start_time = None
                self.unlock_cooldown = 30
                self._transition(SEARCHING)
                return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0, "unlock": True}
            progress = hold_duration / CONFIG["FIST_HOLD_SEC"]
            return {"state": FIST_HOLD, "cursor_pos": None, "scroll_delta": 0, "fist_progress": progress}

        self.fist_start_time = None
        self._transition(IDLE)
        return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0}