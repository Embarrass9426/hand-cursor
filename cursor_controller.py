import pyautogui
import numpy as np
from config import CONFIG
from filters import OneEuroFilter


class ScreenMapper:
    def __init__(self, cam_width, cam_height, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        cam_aspect = cam_width / cam_height
        screen_aspect = screen_w / screen_h
        if cam_aspect >= screen_aspect:
            self.effective_w = screen_w
            self.effective_h = int(screen_w / cam_aspect)
        else:
            self.effective_h = screen_h
            self.effective_w = int(screen_h * cam_aspect)
        self.offset_x = (screen_w - self.effective_w) // 2
        self.offset_y = (screen_h - self.effective_h) // 2

    def map(self, norm_x, norm_y, invert_x=True):
        if invert_x:
            norm_x = 1.0 - norm_x
        screen_x = norm_x * self.effective_w + self.offset_x
        screen_y = norm_y * self.effective_h + self.offset_y
        return screen_x, screen_y


class CursorController:
    SAFE_MARGIN = 5

    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
        self.screen_w, self.screen_h = pyautogui.size()
        if CONFIG.get("USE_ABSOLUTE_MAPPING", False):
            self.mapper = ScreenMapper(
                CONFIG.get("FRAME_WIDTH", 1280),
                CONFIG.get("FRAME_HEIGHT", 720),
                self.screen_w,
                self.screen_h,
            )
        else:
            self.mapper = None
        self.pos_filter = OneEuroFilter(
            mincutoff=CONFIG["ONE_EURO_MIN_CUTOFF"],
            beta=CONFIG["ONE_EURO_BETA"],
            dcutoff=CONFIG["ONE_EURO_DCUTOFF"],
        )
        self.initialized = False
        self.prev_screen_x = self.screen_w // 2
        self.prev_screen_y = self.screen_h // 2

    def _map_to_screen(self, norm_x, norm_y):
        if self.mapper is not None:
            return self.mapper.map(norm_x, norm_y, CONFIG.get("INVERT_X", True))
        center_x = self.screen_w / 2
        center_y = self.screen_h / 2
        mapped_x = (norm_x - 0.5) * CONFIG["CURSOR_SENSITIVITY_X"] * self.screen_w + center_x
        mapped_y = (norm_y - 0.5) * CONFIG["CURSOR_SENSITIVITY_Y"] * self.screen_h + center_y
        return mapped_x, mapped_y

    def move(self, norm_x, norm_y):
        mapped_x, mapped_y = self._map_to_screen(norm_x, norm_y)

        if not self.initialized:
            target_x = int(np.clip(mapped_x, self.SAFE_MARGIN, self.screen_w - 1 - self.SAFE_MARGIN))
            target_y = int(np.clip(mapped_y, self.SAFE_MARGIN, self.screen_h - 1 - self.SAFE_MARGIN))
            self.pos_filter = OneEuroFilter(
                mincutoff=CONFIG["ONE_EURO_MIN_CUTOFF"],
                beta=CONFIG["ONE_EURO_BETA"],
                dcutoff=CONFIG["ONE_EURO_DCUTOFF"],
            )
            self.pos_filter.apply(float(target_x), float(target_y))
            self.prev_screen_x = target_x
            self.prev_screen_y = target_y
            pyautogui.moveTo(target_x, target_y, _pause=False)
            self.initialized = True
            return

        sx, sy = self.pos_filter.apply(mapped_x, mapped_y)

        m = self.SAFE_MARGIN
        target_x = int(np.clip(sx, m, self.screen_w - 1 - m))
        target_y = int(np.clip(sy, m, self.screen_h - 1 - m))

        dx = abs(target_x - self.prev_screen_x)
        dy = abs(target_y - self.prev_screen_y)

        deadzone_x = CONFIG["CURSOR_DEADZONE"] * self.screen_w
        deadzone_y = CONFIG["CURSOR_DEADZONE"] * self.screen_h
        if dx < deadzone_x and dy < deadzone_y:
            return

        self.prev_screen_x = target_x
        self.prev_screen_y = target_y
        pyautogui.moveTo(target_x, target_y, _pause=False)

    def click(self):
        pyautogui.click(_pause=False)

    def double_click(self):
        pyautogui.doubleClick(_pause=False)

    def right_click(self):
        pyautogui.click(button="right", _pause=False)

    def drag_press(self):
        pyautogui.mouseDown(_pause=False)

    def drag_release(self):
        pyautogui.mouseUp(_pause=False)

    def scroll(self, delta):
        amount = int(delta)
        if amount != 0:
            pyautogui.scroll(amount, _pause=False)

    def reset_filters(self):
        self.pos_filter.reset()
        self.initialized = False