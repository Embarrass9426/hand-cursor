import cv2
import numpy as np
from mediapipe.tasks.python.vision import HandLandmarksConnections, drawing_utils, drawing_styles
from gesture_classifier import SEARCHING, IDLE, CURSOR, MIDDLE_DOWN, LEFT_CLICK, RIGHT_CLICK, DOUBLE_CLICK, DRAGGING, CLICK_DOWN, SCROLLING

STATE_COLORS = {
    SEARCHING: (128, 128, 128),
    IDLE: (0, 255, 255),
    CURSOR: (0, 255, 0),
    MIDDLE_DOWN: (0, 165, 255),
    LEFT_CLICK: (0, 0, 255),
    RIGHT_CLICK: (255, 0, 0),
    DOUBLE_CLICK: (255, 0, 255),
    DRAGGING: (0, 140, 255),
    CLICK_DOWN: (0, 165, 255),
    SCROLLING: (255, 200, 0),
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

    color = STATE_COLORS.get(state, (255, 255, 255))
    label = state
    if locked_label:
        label = f"{state} [{locked_label}]"

    cv2.putText(
        frame, label, (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA,
    )

    if state == CURSOR:
        cv2.putText(frame, "MOVING", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
    elif state == MIDDLE_DOWN:
        cv2.putText(frame, "MIDDLE DOWN", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)
    elif state == DRAGGING:
        cv2.putText(frame, "DRAGGING", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2, cv2.LINE_AA)
    elif state == LEFT_CLICK:
        cv2.putText(frame, "LEFT CLICK", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
    elif state == RIGHT_CLICK:
        cv2.putText(frame, "RIGHT CLICK", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv2.LINE_AA)
    elif state == DOUBLE_CLICK:
        cv2.putText(frame, "DOUBLE CLICK", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2, cv2.LINE_AA)
    elif state == CLICK_DOWN:
        cv2.putText(frame, "CLICK DOWN", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)
    elif state == SCROLLING:
        cv2.putText(frame, "SCROLLING", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2, cv2.LINE_AA)

    lock_text = "LOCKED" if locked_label else "UNLOCKED"
    lock_color = (0, 255, 0) if locked_label else (0, 0, 255)
    cv2.putText(frame, lock_text, (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, lock_color, 2, cv2.LINE_AA)

    return frame
