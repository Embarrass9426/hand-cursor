import cv2
import numpy as np
import os
import urllib.request
from mediapipe import Image, ImageFormat
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from config import CONFIG
from filters import LandmarkSmoother


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


def calc_finger_angle(landmarks, mcp_idx, pip_idx, wrist_idx=0):
    v1 = np.array([landmarks[wrist_idx].x - landmarks[mcp_idx].x,
                   landmarks[wrist_idx].y - landmarks[mcp_idx].y,
                   landmarks[wrist_idx].z - landmarks[mcp_idx].z])
    v2 = np.array([landmarks[pip_idx].x - landmarks[mcp_idx].x,
                   landmarks[pip_idx].y - landmarks[mcp_idx].y,
                   landmarks[pip_idx].z - landmarks[mcp_idx].z])
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 180.0
    cos_angle = np.dot(v1, v2) / (norm1 * norm2)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))


def get_finger_state(landmarks, mcp_idx, pip_idx, wrist_idx=0):
    angle = calc_finger_angle(landmarks, mcp_idx, pip_idx, wrist_idx)
    if angle > CONFIG["FINGER_EXTENDED_ANGLE"]:
        return "extended"
    elif angle > CONFIG["FINGER_PARTIAL_BEND_ANGLE"]:
        return "partially_bent"
    else:
        return "fully_bent"


def is_finger_extended(landmarks, mcp_idx, pip_idx, wrist_idx=0):
    return calc_finger_angle(landmarks, mcp_idx, pip_idx, wrist_idx) > CONFIG["FINGER_EXTENDED_ANGLE"]


def is_finger_bent(landmarks, mcp_idx, pip_idx, wrist_idx=0):
    state = get_finger_state(landmarks, mcp_idx, pip_idx, wrist_idx)
    return state == "partially_bent"


def is_finger_fully_bent(landmarks, mcp_idx, pip_idx, wrist_idx=0):
    state = get_finger_state(landmarks, mcp_idx, pip_idx, wrist_idx)
    return state == "fully_bent"


def is_thumb_extended(landmarks):
    return calc_distance(landmarks[4], landmarks[0]) / max(calc_distance(landmarks[3], landmarks[0]), 1e-6) > CONFIG.get("THUMB_EXTENDED_DISTANCE_RATIO", 1.0)


def is_index_extended(landmarks):
    return is_finger_extended(landmarks, 5, 6)


def is_middle_extended(landmarks):
    return is_finger_extended(landmarks, 9, 10)


def is_ring_extended(landmarks):
    return is_finger_extended(landmarks, 13, 14)


def is_pinky_extended(landmarks):
    return is_finger_extended(landmarks, 17, 18)


def is_index_tip_below_pip(landmarks):
    return landmarks[8].y > landmarks[6].y


def is_middle_tip_below_pip(landmarks):
    return landmarks[12].y > landmarks[10].y


def is_open_palm(landmarks):
    return (is_thumb_extended(landmarks) and is_index_extended(landmarks) and
            is_middle_extended(landmarks) and is_ring_extended(landmarks) and
            is_pinky_extended(landmarks))


def is_ok_sign(landmarks):
    thumb_index_close = calc_distance(landmarks[4], landmarks[8]) < CONFIG["OK_SIGN_DISTANCE"]
    others_extended = (is_middle_extended(landmarks) and
                       is_ring_extended(landmarks) and
                       is_pinky_extended(landmarks))
    return thumb_index_close and others_extended


def is_closed_fist(landmarks):
    return (not is_thumb_extended(landmarks) and
            is_finger_fully_bent(landmarks, 5, 6) and
            is_finger_fully_bent(landmarks, 9, 10) and
            is_finger_fully_bent(landmarks, 13, 14) and
            is_finger_fully_bent(landmarks, 17, 18))


def is_index_dip_bent(landmarks):
    return calc_distance(landmarks[8], landmarks[7]) < CONFIG["DIP_CLICK_THRESHOLD"]

def is_middle_dip_bent(landmarks):
    return calc_distance(landmarks[12], landmarks[11]) < CONFIG["MIDDLE_DIP_CLICK_THRESHOLD"]

def is_scroll_down(landmarks):
    thumb_near = calc_distance(landmarks[4], landmarks[13]) < CONFIG["SCROLL_DOWN_TOUCH_THRESHOLD"]
    pinky_near = calc_distance(landmarks[20], landmarks[13]) < CONFIG["SCROLL_DOWN_TOUCH_THRESHOLD"]
    return thumb_near and not pinky_near


def is_scroll_up(landmarks):
    thumb_near = calc_distance(landmarks[4], landmarks[13]) < CONFIG["SCROLL_UP_TOUCH_THRESHOLD"]
    pinky_near = calc_distance(landmarks[20], landmarks[4]) < CONFIG["SCROLL_UP_TOUCH_THRESHOLD"]
    return thumb_near and pinky_near


def is_ring_dip_bent(landmarks):
    return calc_distance(landmarks[16], landmarks[15]) < CONFIG["RING_DIP_CLICK_THRESHOLD"]


def calc_scroll_delta(landmarks, gestures):
    if gestures.get("scroll_down"):
        return -CONFIG["SCROLL_SPEED"]
    if gestures.get("scroll_up"):
        return CONFIG["SCROLL_SPEED"]
    return 0


class GestureDebouncer:
    def __init__(self, debounce_frames=3):
        self.debounce_frames = debounce_frames
        self.counters = {}

    def update(self, gestures_dict):
        result = {}
        for name, detected in gestures_dict.items():
            if detected:
                self.counters[name] = self.counters.get(name, 0) + 1
            else:
                self.counters[name] = 0
            result[name] = self.counters[name] >= self.debounce_frames
        return result

    def reset(self):
        self.counters = {}


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
        self.smoother = LandmarkSmoother(CONFIG)
        self.debouncer = GestureDebouncer(CONFIG["DEBOUNCE_FRAMES"])

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
            if is_ok_sign(proxied):
                label = result.handedness[i][0].category_name
                self.locked_hand_label = label
                self.last_wrist_pos = (proxied[0].x, proxied[0].y)
                self.lost_frames = 0
                smoothed = self.smoother.smooth(proxied)
                for j, (sx, sy) in enumerate(smoothed):
                    proxied[j].x = sx
                    proxied[j].y = sy
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
            smoothed = self.smoother.smooth(best_lm)
            for j, (sx, sy) in enumerate(smoothed):
                best_lm[j].x = sx
                best_lm[j].y = sy
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

    def detect_gestures(self, landmarks):
        raw = {
            "open_palm": is_open_palm(landmarks),
            "ok_sign": is_ok_sign(landmarks),
            "closed_fist": is_closed_fist(landmarks),
            "index_bent": is_index_tip_below_pip(landmarks),
            "middle_bent": is_middle_tip_below_pip(landmarks),
            "index_dip_bent": is_index_dip_bent(landmarks),
            "middle_dip_bent": is_middle_dip_bent(landmarks),
            "scroll_down": is_scroll_down(landmarks),
            "scroll_up": is_scroll_up(landmarks),
            "ring_dip_bent": is_ring_dip_bent(landmarks),
        }
        debounced = self.debouncer.update(raw)
        debounced["scroll_delta"] = calc_scroll_delta(landmarks, debounced)
        return debounced

    def release(self):
        self.landmarker.close()