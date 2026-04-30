import cv2
import numpy as np
import os
import urllib.request
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from config import CONFIG


MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"


def _get_model_path():
    temp_dir = os.environ.get("TEMP", "/tmp")
    model_path = os.path.join(temp_dir, "hand_landmarker.task")
    if not os.path.exists(model_path):
        print("Downloading hand_landmarker.model...")
        urllib.request.urlretrieve(MODEL_URL, model_path)
        print("Download complete.")
    return model_path


def calc_distance(p1, p2):
    return np.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)


def is_finger_extended(landmarks, tip_idx, mcp_idx, wrist_idx=0):
    tip_to_wrist = calc_distance(landmarks[tip_idx], landmarks[wrist_idx])
    mcp_to_wrist = calc_distance(landmarks[mcp_idx], landmarks[wrist_idx])
    return tip_to_wrist > (mcp_to_wrist * 1.2)


def is_thumb_index_pinch(landmarks):
    return calc_distance(landmarks[4], landmarks[8]) < CONFIG["PINCH_THRESHOLD"]


def is_thumb_middle_pinch(landmarks):
    thumb_middle_close = calc_distance(landmarks[4], landmarks[12]) < CONFIG["DOUBLE_CLICK_THRESHOLD"]
    thumb_index_open = calc_distance(landmarks[4], landmarks[8]) > CONFIG["OPEN_THRESHOLD"]
    return thumb_middle_close and thumb_index_open


def is_fist(landmarks):
    index_curled = not is_finger_extended(landmarks, 8, 5)
    middle_curled = not is_finger_extended(landmarks, 12, 9)
    ring_curled = not is_finger_extended(landmarks, 16, 13)
    pinky_curled = not is_finger_extended(landmarks, 20, 17)
    return index_curled and middle_curled and ring_curled and pinky_curled


def is_peace_sign(landmarks):
    index_extended = is_finger_extended(landmarks, 8, 5)
    middle_extended = is_finger_extended(landmarks, 12, 9)
    ring_curled = not is_finger_extended(landmarks, 16, 13)
    pinky_curled = not is_finger_extended(landmarks, 20, 17)
    thumb_index_open = calc_distance(landmarks[4], landmarks[8]) > CONFIG["OPEN_THRESHOLD"]
    return index_extended and middle_extended and ring_curled and pinky_curled and thumb_index_open


class _LandmarkProxy:
    def __init__(self, norm_lm):
        self.x = norm_lm.x
        self.y = norm_lm.y
        self.z = norm_lm.z


class HandTracker:
    def __init__(self):
        model_path = _get_model_path()
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=CONFIG.get("MIN_DETECTION_CONFIDENCE", 0.7),
            min_hand_presence_confidence=CONFIG.get("MIN_TRACKING_CONFIDENCE", 0.5),
            min_tracking_confidence=CONFIG.get("MIN_TRACKING_CONFIDENCE", 0.5),
        )
        self.landmarker = HandLandmarker.create_from_options(options)
        self.frame_timestamp_ms = 0
        self.locked_hand_label = None
        self.last_wrist_pos = None
        self.lost_frames = 0

    def process_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
        self.frame_timestamp_ms += 33
        result = self.landmarker.detect_for_video(mp_image, self.frame_timestamp_ms)
        return result

    def get_locked_hand(self, result):
        if not result.hand_landmarks:
            self._increment_lost()
            return None

        if self.locked_hand_label is None:
            return self._try_lock(result)

        return self._maintain_lock(result)

    def _try_lock(self, result):
        for i, landmarks in enumerate(result.hand_landmarks):
            proxied = [_LandmarkProxy(lm) for lm in landmarks]
            if is_thumb_index_pinch(proxied):
                label = result.handedness[i][0].category_name
                self.locked_hand_label = label
                self.last_wrist_pos = (proxied[0].x, proxied[0].y)
                self.lost_frames = 0
                return proxied

        return None

    def _maintain_lock(self, result):
        best_lm = None
        best_dist = float("inf")

        for i, landmarks in enumerate(result.hand_landmarks):
            proxied = [_LandmarkProxy(lm) for lm in landmarks]
            if i >= len(result.handedness):
                continue
            label = result.handedness[i][0].category_name

            if label == self.locked_hand_label:
                if self.last_wrist_pos is not None:
                    d = np.sqrt(
                        (proxied[0].x - self.last_wrist_pos[0]) ** 2
                        + (proxied[0].y - self.last_wrist_pos[1]) ** 2
                    )
                    if d < best_dist:
                        best_dist = d
                        best_lm = proxied
                else:
                    best_lm = proxied

        if best_lm is not None:
            self.last_wrist_pos = (best_lm[0].x, best_lm[0].y)
            self.lost_frames = 0
            return best_lm

        self._increment_lost()
        return None

    def _increment_lost(self):
        self.lost_frames += 1
        if self.lost_frames > CONFIG["MAX_LOST_FRAMES"]:
            self.locked_hand_label = None
            self.last_wrist_pos = None

    def force_unlock(self):
        self.locked_hand_label = None
        self.last_wrist_pos = None
        self.lost_frames = 0

    def release(self):
        self.landmarker.close()