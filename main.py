import cv2
from config import CONFIG
from camera import Camera
from hand_tracker import HandTracker
from gesture_classifier import GestureClassifier, SEARCHING, IDLE, CLICK, DOUBLE_CLICK, CURSOR, SCROLL, DRAG, FIST_HOLD
from cursor_controller import CursorController
from debug_overlay import draw_overlay


def main():
    camera = Camera()
    tracker = HandTracker()
    classifier = GestureClassifier()
    cursor = CursorController()

    print("Hand Cursor Controller started. Press 'q' to quit.")
    print("Pinch thumb+index to lock. Hold fist 1.5s to unlock.")

    try:
        while True:
            frame = camera.read()
            if frame is None:
                continue

            result = tracker.process_frame(frame)
            landmarks = tracker.get_locked_hand(result)

            was_dragging = classifier.is_dragging
            gesture_result = classifier.update(landmarks)
            state = gesture_result["state"]

            if gesture_result.get("unlock"):
                tracker.force_unlock()
                cursor.reset_filters()
                landmarks = None

            if classifier.is_dragging and not was_dragging:
                cursor.drag_press()
            elif not classifier.is_dragging and was_dragging:
                cursor.drag_release()

            if state == CURSOR and gesture_result["cursor_pos"] is not None:
                cursor.move(gesture_result["cursor_pos"][0], gesture_result["cursor_pos"][1])
            elif state == CLICK:
                cursor.click()
                classifier.state = IDLE
            elif state == DOUBLE_CLICK:
                cursor.double_click()
                classifier.state = IDLE
            elif state == DRAG and gesture_result["cursor_pos"] is not None:
                cursor.move(gesture_result["cursor_pos"][0], gesture_result["cursor_pos"][1])
            elif state == SCROLL and gesture_result["scroll_delta"] != 0:
                cursor.scroll(gesture_result["scroll_delta"])

            if CONFIG["SHOW_DEBUG_WINDOW"]:
                display_frame = frame.copy()
                drag_progress = gesture_result.get("drag_progress", 0.0)
                pinch_pos = gesture_result.get("pinch_pos")
                fist_progress = gesture_result.get("fist_progress", 0.0)
                display_frame = draw_overlay(
                    display_frame,
                    result,
                    tracker,
                    state,
                    tracker.locked_hand_label,
                    drag_progress=drag_progress,
                    pinch_pos=pinch_pos,
                    fist_progress=fist_progress,
                )
                cv2.imshow("Hand Cursor Controller", display_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if classifier.is_dragging:
            cursor.drag_release()
        camera.release()
        tracker.release()
        cv2.destroyAllWindows()
        print("Hand Cursor Controller stopped.")


if __name__ == "__main__":
    main()