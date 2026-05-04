import cv2
import base64
import time
import traceback
import webbrowser
from flask import Flask, render_template
from flask_socketio import SocketIO
from config import CONFIG
from camera import Camera
from hand_tracker import HandTracker
from gesture_classifier import GestureClassifier
from cursor_controller import CursorController
from debug_overlay import draw_overlay

app = Flask(__name__)
app.config["SECRET_KEY"] = "hand-cursor-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

running = False


def emit_frame(frame):
    try:
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64 = base64.b64encode(buffer).decode("utf-8")
        socketio.emit("video_frame", {"frame": b64})
    except Exception as e:
        print("[ERROR] emit_frame failed:", e)


def emit_state(state, gestures=None):
    try:
        data = {"state": state}
        if gestures:
            data["gestures"] = {k: v for k, v in gestures.items()}
        socketio.emit("gesture_state", data)
    except Exception as e:
        print("[ERROR] emit_state failed:", e)


def cv_loop(camera, tracker, classifier, cursor):
    global running
    frame_count = 0
    empty_count = 0
    prev_state = None
    cursor_initialized_for_lock = False

    print("[Camera] Background loop started")
    while running:
        try:
            frame = camera.read()
            if frame is None:
                empty_count += 1
                if empty_count % 100 == 0:
                    print(f"[Camera] Warning: {empty_count} empty frames in a row")
                time.sleep(0.01)
                continue
            empty_count = 0

            result = tracker.process_frame(frame)
            landmarks = tracker.get_locked_hand(result)

            if landmarks is not None:
                gestures = tracker.detect_gestures(landmarks)
            else:
                gestures = {
                    k: False
                    for k in [
                        "open_palm",
                        "ok_sign",
                        "closed_fist",
                        "index_bent",
                        "middle_bent",
                        "index_dip_bent",
                        "middle_dip_bent",
                        "scroll_down",
                        "scroll_up",
                        "ring_dip_bent",
                    ]
                }
                gestures["scroll_delta"] = 0

            gesture_result = classifier.update(landmarks, gestures)
            state = gesture_result["state"]

            prev_state = state

            if gesture_result.get("unlock"):
                tracker.force_unlock()
                cursor.reset_filters()
                cursor_initialized_for_lock = False

            was_dragging = getattr(classifier, "_prev_dragging", False)
            if classifier.is_dragging and not was_dragging:
                cursor.drag_press()
            elif not classifier.is_dragging and was_dragging:
                cursor.drag_release()
            classifier._prev_dragging = classifier.is_dragging

            action = gesture_result.get("action")

            # Scroll action must be handled independently of cursor movement
            if action == "scroll":
                scroll_delta = gesture_result.get("scroll_delta", 0)
                if scroll_delta != 0:
                    cursor.scroll(scroll_delta)

            # Cursor tracks in IDLE, CURSOR, CLICK_DOWN, SCROLLING, and DRAGGING states so user can position before clicking
            if state in ("IDLE", "CURSOR", "CLICK_DOWN", "SCROLLING", "DRAGGING") and gesture_result.get("cursor_pos"):
                if not cursor_initialized_for_lock:
                    cursor.reset_filters()
                    cursor_initialized_for_lock = True
                    print(f"[Cursor] Initialized to hand position: ({gesture_result['cursor_pos'][0]:.3f}, {gesture_result['cursor_pos'][1]:.3f})")
                cursor.move(*gesture_result["cursor_pos"])
            elif action == "left_click":
                cursor.click()
            elif action == "right_click":
                cursor.right_click()
            elif action == "double_click":
                cursor.double_click()

            display_frame = draw_overlay(
                frame.copy(),
                result,
                tracker,
                state,
                tracker.locked_hand_label,
            )
            emit_frame(display_frame)
            emit_state(state, gestures)

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[Camera] Streamed {frame_count} frames, state={state}")

            time.sleep(1 / CONFIG["FPS"])
        except Exception as e:
            print("[ERROR] cv_loop exception:")
            traceback.print_exc()
            time.sleep(0.1)

    print("[Camera] Background loop stopped")
    camera.release()
    tracker.release()
    cv2.destroyAllWindows()


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def on_connect():
    print("[SocketIO] Client connected")


@socketio.on("disconnect")
def on_disconnect():
    print("[SocketIO] Client disconnected")


def main():
    global running

    print("[Server] Initializing camera in main thread...")
    camera = Camera()

    print("[Server] Priming camera with one frame...")
    prime = camera.read()
    if prime is None:
        print("[WARNING] First read returned None, retrying...")
        time.sleep(0.5)
        prime = camera.read()
    if prime is not None:
        print(f"[Server] Prime frame shape: {prime.shape}")
    else:
        print("[WARNING] Could not get prime frame, continuing anyway")

    print("[Server] Initializing hand tracker...")
    tracker = HandTracker()

    classifier = GestureClassifier()
    cursor = CursorController()
    running = True

    socketio.start_background_task(cv_loop, camera, tracker, classifier, cursor)
    print("[Server] Background camera task started")

    webbrowser.open(f"http://{CONFIG['FLASK_HOST']}:{CONFIG['FLASK_PORT']}")

    try:
        socketio.run(
            app, host=CONFIG["FLASK_HOST"], port=CONFIG["FLASK_PORT"], debug=False
        )
    finally:
        running = False


if __name__ == "__main__":
    main()
