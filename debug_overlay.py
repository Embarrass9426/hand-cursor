import cv2
import numpy as np
from mediapipe.tasks.python.vision import HandLandmarksConnections, drawing_utils, drawing_styles
from gesture_classifier import SEARCHING, IDLE, CURSOR, PENDING_CLICK, CLICK, DOUBLE_CLICK, DRAG, SCROLL, FIST_HOLD

STATE_COLORS = {
    SEARCHING: (128, 128, 128),
    IDLE: (0, 255, 255),
    CURSOR: (0, 255, 0),
    PENDING_CLICK: (0, 165, 255),
    CLICK: (0, 0, 255),
    DOUBLE_CLICK: (255, 0, 255),
    DRAG: (0, 140, 255),
    SCROLL: (255, 255, 0),
    FIST_HOLD: (0, 0, 200),
}


def draw_progress_arc(frame, cx, cy, progress, radius=30, thickness=3, color_combo=((0, 165, 255), (0, 255, 0))):
    color = color_combo[1] if progress >= 0.8 else color_combo[0]
    end_angle = int(360 * progress)
    cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, end_angle, color, thickness, cv2.LINE_AA)


def draw_overlay(frame, result, hand_tracker, state, locked_label, drag_progress=0.0, pinch_pos=None, fist_progress=0.0):
    h, w = frame.shape[:2]

    if result.hand_landmarks:
        for landmarks in result.hand_landmarks:
            drawing_utils.draw_landmarks(
                frame,
                landmarks,
                HandLandmarksConnections.HAND_CONNECTIONS,
                drawing_styles.get_default_hand_landmarks_style(),
                drawing_styles.get_default_hand_connections_style(),
            )

    if state == FIST_HOLD and fist_progress > 0:
        cx, cy = w // 2, h // 2
        draw_progress_arc(frame, cx, cy, fist_progress, radius=50, thickness=5, color_combo=((0, 0, 200), (0, 0, 255)))
        pct = int(fist_progress * 100)
        cv2.putText(frame, f"UNLOCKING... {pct}%", (cx - 80, cy + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

    color = STATE_COLORS.get(state, (255, 255, 255))
    label = state
    if locked_label:
        label = f"{state} [{locked_label}]"

    cv2.putText(
        frame, label, (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA,
    )

    if state == SCROLL:
        cv2.putText(frame, "SCROLL MODE", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
    elif state == CURSOR:
        cv2.putText(frame, "MOVING", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
    elif state == PENDING_CLICK:
        pct = int(drag_progress * 100)
        cv2.putText(frame, f"HOLDING... {pct}%", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)
        if pinch_pos is not None and drag_progress > 0:
            draw_progress_arc(frame, int(pinch_pos[0] * w), int(pinch_pos[1] * h), drag_progress)
    elif state == DRAG:
        cv2.putText(frame, "DRAGGING", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2, cv2.LINE_AA)

    lock_text = "LOCKED" if locked_label else "UNLOCKED"
    lock_color = (0, 255, 0) if locked_label else (0, 0, 255)
    cv2.putText(frame, lock_text, (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, lock_color, 2, cv2.LINE_AA)

    return frame