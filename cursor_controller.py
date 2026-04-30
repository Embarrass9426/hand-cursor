import pyautogui
import numpy as np
from config import CONFIG
from filters import OneEuroFilter


class CursorController:
    SAFE_MARGIN = 5

    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
        self.screen_w, self.screen_h = pyautogui.size()
        self.pos_filter = OneEuroFilter(
            mincutoff=CONFIG["ONE_EURO_MIN_CUTOFF"],
            beta=CONFIG["ONE_EURO_BETA"],
            dcutoff=CONFIG["ONE_EURO_DCUTOFF"],
        )
        self.initialized = False
        self.prev_screen_x = self.screen_w // 2
        self.prev_screen_y = self.screen_h // 2

    def move(self, norm_x, norm_y):
        if not self.initialized:
            pyautogui.moveTo(self.screen_w // 2, self.screen_h // 2, _pause=False)
            self.pos_filter = OneEuroFilter(
                mincutoff=CONFIG["ONE_EURO_MIN_CUTOFF"],
                beta=CONFIG["ONE_EURO_BETA"],
                dcutoff=CONFIG["ONE_EURO_DCUTOFF"],
            )
            center_x = self.screen_w / 2
            center_y = self.screen_h / 2
            init_x = (norm_x - 0.5) * CONFIG["CURSOR_SENSITIVITY"] * self.screen_w + center_x
            init_y = (norm_y - 0.5) * CONFIG["CURSOR_SENSITIVITY"] * self.screen_h + center_y
            init_x = int(np.clip(init_x, self.SAFE_MARGIN, self.screen_w - 1 - self.SAFE_MARGIN))
            init_y = int(np.clip(init_y, self.SAFE_MARGIN, self.screen_h - 1 - self.SAFE_MARGIN))
            self.pos_filter.apply(float(init_x), float(init_y))
            self.prev_screen_x = init_x
            self.prev_screen_y = init_y
            self.initialized = True

        center_x = self.screen_w / 2
        center_y = self.screen_h / 2
        mapped_x = (norm_x - 0.5) * CONFIG["CURSOR_SENSITIVITY"] * self.screen_w + center_x
        mapped_y = (norm_y - 0.5) * CONFIG["CURSOR_SENSITIVITY"] * self.screen_h + center_y

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

    def drag_press(self):
        pyautogui.mouseDown(_pause=False)

    def drag_release(self):
        pyautogui.mouseUp(_pause=False)

    def scroll(self, delta):
        amount = int(delta * 100)
        if amount != 0:
            pyautogui.scroll(amount, _pause=False)

    def reset_filters(self):
        self.pos_filter.reset()
        self.initialized = False