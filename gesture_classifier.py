import time
from config import CONFIG

SEARCHING = "SEARCHING"
IDLE = "IDLE"
CURSOR = "CURSOR"
INDEX_DOWN = "INDEX_DOWN"
MIDDLE_DOWN = "MIDDLE_DOWN"
LEFT_CLICK = "LEFT_CLICK"
RIGHT_CLICK = "RIGHT_CLICK"
DOUBLE_CLICK = "DOUBLE_CLICK"
DRAGGING = "DRAGGING"
CLICK_DOWN = "CLICK_DOWN"
SCROLLING = "SCROLLING"


class GestureClassifier:
    def __init__(self):
        self.state = SEARCHING
        self.lost_frames = 0
        self.index_down_start = None
        self.fist_start_time = None
        self.scroll_start_time = None
        self.is_dragging = False
        self.unlock_cooldown = 0

    def update(self, landmarks, gestures):
        if self.state in (LEFT_CLICK, RIGHT_CLICK, DOUBLE_CLICK):
            self._transition(IDLE)

        if landmarks is None:
            self.lost_frames += 1
            if self.lost_frames > CONFIG["MAX_LOST_FRAMES"]:
                if self.state != SEARCHING:
                    self._transition(SEARCHING)
                self.is_dragging = False
                self.fist_start_time = None
                self.index_down_start = None
                return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0, "unlock": True, "action": None}
            return {"state": self.state, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}

        self.lost_frames = 0
        if self.unlock_cooldown > 0:
            self.unlock_cooldown -= 1

        if self.state == SEARCHING:
            return self._handle_searching(landmarks, gestures)

        if gestures["closed_fist"]:
            if self.fist_start_time is None:
                self.fist_start_time = time.time()
            if time.time() - self.fist_start_time >= CONFIG["FIST_HOLD_SEC"]:
                self.is_dragging = False
                self.fist_start_time = None
                self.index_down_start = None
                self.unlock_cooldown = 30
                self._transition(SEARCHING)
                return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0, "unlock": True, "action": None}
        else:
            self.fist_start_time = None

        scroll_active = gestures.get("scroll_down") or gestures.get("scroll_up")
        if scroll_active and self.state != SCROLLING:
            if self.scroll_start_time is None:
                self.scroll_start_time = time.time()
            if time.time() - self.scroll_start_time >= CONFIG["SCROLL_HOLD_SEC"]:
                self.is_dragging = False
                self.index_down_start = None
                self.scroll_start_time = None
                self._transition(SCROLLING)
                return {"state": SCROLLING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": gestures.get("scroll_delta", 0), "unlock": False, "action": None}
        else:
            self.scroll_start_time = None

        if self.state == IDLE:
            return self._handle_idle(landmarks, gestures)
        if self.state == CURSOR:
            return self._handle_cursor(landmarks, gestures)
        if self.state == SCROLLING:
            return self._handle_scrolling(landmarks, gestures)
        if self.state == DRAGGING:
            return self._handle_dragging(landmarks, gestures)
        if self.state == CLICK_DOWN:
            return self._handle_click_down(landmarks, gestures)
        if self.state == MIDDLE_DOWN:
            return self._handle_middle_down(landmarks, gestures)

        return {"state": self.state, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}

    def _transition(self, new_state):
        if CONFIG["PRINT_STATE_CHANGES"] and new_state != self.state:
            print(f"[State] {self.state} -> {new_state}")
        self.state = new_state

    def _cursor_pos(self, landmarks):
        return (landmarks[CONFIG["CURSOR_LANDMARK"]].x, landmarks[CONFIG["CURSOR_LANDMARK"]].y)

    def _handle_searching(self, landmarks, gestures):
        if gestures["ok_sign"]:
            self._transition(IDLE)
            return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        return {"state": SEARCHING, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}

    def _handle_idle(self, landmarks, gestures):
        if gestures["ok_sign"]:
            self.is_dragging = True
            self._transition(DRAGGING)
            return {"state": DRAGGING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": "drag_start"}
        if gestures["open_palm"]:
            self._transition(CURSOR)
            return {"state": CURSOR, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}
        if gestures["index_dip_bent"]:
            self.index_down_start = time.time()
            self._transition(CLICK_DOWN)
            return {"state": CLICK_DOWN, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        if gestures["middle_dip_bent"]:
            self._transition(MIDDLE_DOWN)
            return {"state": MIDDLE_DOWN, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        if gestures.get("ring_dip_bent"):
            self._transition(DOUBLE_CLICK)
            return {"state": DOUBLE_CLICK, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": "double_click"}
        return {"state": IDLE, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}

    def _handle_cursor(self, landmarks, gestures):
        if gestures["ok_sign"]:
            self.is_dragging = True
            self._transition(DRAGGING)
            return {"state": DRAGGING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": "drag_start"}
        if gestures["index_dip_bent"]:
            self.index_down_start = time.time()
            self._transition(CLICK_DOWN)
            return {"state": CLICK_DOWN, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        if gestures["middle_dip_bent"]:
            self._transition(MIDDLE_DOWN)
            return {"state": MIDDLE_DOWN, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        if gestures.get("ring_dip_bent"):
            self._transition(DOUBLE_CLICK)
            return {"state": DOUBLE_CLICK, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": "double_click"}
        return {"state": CURSOR, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}

    def _handle_click_down(self, landmarks, gestures):
        if gestures["ok_sign"]:
            self.is_dragging = True
            self.index_down_start = None
            self._transition(DRAGGING)
            return {"state": DRAGGING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": "drag_start"}
        if gestures["index_dip_bent"]:
            return {"state": CLICK_DOWN, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}
        self.index_down_start = None
        self._transition(LEFT_CLICK)
        return {"state": LEFT_CLICK, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": "left_click"}

    def _handle_middle_down(self, landmarks, gestures):
        if not gestures["middle_dip_bent"]:
            self._transition(RIGHT_CLICK)
            return {"state": RIGHT_CLICK, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": "right_click"}
        return {"state": MIDDLE_DOWN, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}

    def _handle_dragging(self, landmarks, gestures):
        if not gestures["ok_sign"]:
            self.is_dragging = False
            self._transition(IDLE)
            return {"state": IDLE, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": "drag_end"}
        return {"state": DRAGGING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}

    def _handle_scrolling(self, landmarks, gestures):
        if gestures.get("scroll_down") or gestures.get("scroll_up"):
            scroll_delta = gestures.get("scroll_delta", 0)
            return {"state": SCROLLING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": scroll_delta, "unlock": False, "action": "scroll"}
        if gestures["ok_sign"]:
            self.is_dragging = True
            self._transition(DRAGGING)
            return {"state": DRAGGING, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": "drag_start"}
        if gestures["open_palm"]:
            self._transition(CURSOR)
            return {"state": CURSOR, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}
        if gestures["index_dip_bent"]:
            self.index_down_start = time.time()
            self._transition(CLICK_DOWN)
            return {"state": CLICK_DOWN, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        if gestures["middle_dip_bent"]:
            self._transition(MIDDLE_DOWN)
            return {"state": MIDDLE_DOWN, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": None}
        if gestures.get("ring_dip_bent"):
            self._transition(DOUBLE_CLICK)
            return {"state": DOUBLE_CLICK, "cursor_pos": None, "scroll_delta": 0, "unlock": False, "action": "double_click"}
        self._transition(IDLE)
        return {"state": IDLE, "cursor_pos": self._cursor_pos(landmarks), "scroll_delta": 0, "unlock": False, "action": None}
