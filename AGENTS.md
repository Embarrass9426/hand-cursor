# AGENTS.md — hand-cursor

## What this is
Hand-gesture virtual mouse via webcam (OpenCV + MediaPipe + PyAutoGUI). Controls the real system cursor using finger-bend gestures, served through a Flask web UI for testing.

## Run / test
- **Run app**: `python main.py` (requires webcam; opens browser automatically at `http://127.0.0.1:5000`)
- **Run tests**: `python test_all.py`
- No framework test runner — tests are a plain script with assertions.
- No linting, formatting, or type-checking tooling configured.

## Architecture
- `main.py` — Flask+SocketIO server; runs camera loop in background thread, streams JPEG frames and gesture state to web clients. Cursor initializes to hand position on every lock via `cursor_initialized_for_lock` flag.
- `config.py` — plain dict `CONFIG` imported by most modules
- `camera.py` — OpenCV capture, auto-detects working camera index across multiple backends (CAP_DSHOW on Windows, falls back through indices 0-2)
- `hand_tracker.py` — MediaPipe HandLandmarker (VIDEO mode), hand lock/unlock logic, per-landmark smoothing pipeline (deadzone → 1-Euro), gesture debouncer
- `gesture_classifier.py` — state machine (SEARCHING → IDLE → CURSOR/INDEX_DOWN/MIDDLE_DOWN) with double-click timer and drag detection
- `cursor_controller.py` — pyautogui wrapper with OneEuroFilter smoothing for cursor position
- `filters.py` — `OneEuroFilter`, `DeadzoneFilter`, `LandmarkSmoother`
- `debug_overlay.py` — OpenCV drawing utilities
- `templates/index.html` — web UI: webcam feed + click test button + gesture log + draggable box
- `static/css/style.css` — dark industrial dashboard theme
- `static/js/app.js` — SocketIO client, click detection logging, draggable box
- `test_all.py` — import smoke tests + logic tests + HandLandmarker init test

## Gesture vocabulary
- **Lock Hand**: OK Sign — thumb near index, others extended
- **Move Cursor**: Open Palm — all 5 fingers extended (including thumb)
- **Left Click**: Index finger tip drops below PIP joint (`landmarks[8].y > landmarks[6].y`), quick bend & release < 0.3s
- **Drag**: Index finger holds down (> 0.3s = mouse down, release = mouse up)
- **Right Click**: Middle finger tip drops below PIP joint (`landmarks[12].y > landmarks[10].y`), quick bend & release
- **Unlock/Cancel**: Closed Fist — all fingers curled, thumb not extended, held for 1.5s

## Smoothing pipeline
1. **Deadzone Filter** (per-landmark): ignores movement below `DEADZONE_THRESHOLD`
2. **1-Euro Filter** (per-landmark): dynamic smoothing based on hand speed
3. **Gesture Debouncer**: finger must stay bent for `DEBOUNCE_FRAMES` before registering

## Operational gotchas
- **Model download on first run**: `hand_tracker.py` downloads `hand_landmarker.task` from Google Cloud Storage into `$TEMP` (or `/tmp`) if not present. Expect a network hit and brief pause on first run.
- **No `hand_landmarker.task` in repo**: It is `.gitignore`d and fetched at runtime. Do not commit it.
- **Camera auto-detect**: `camera.py` tries multiple indices and backends (CAP_DSHOW on Windows) and only accepts a camera that returns an actual frame. If you have virtual cameras (NVIDIA Broadcast, etc.), the real webcam may be at index 1 or 2.
- **PyAutoGUI failsafe**: `CursorController` sets `pyautogui.FAILSAFE = True`. Moving cursor to screen corner will abort.
- **State machine transitions**: `gesture_classifier.py` uses time-based thresholds (`CLICK_HOLD_THRESHOLD_SEC`, `FIST_HOLD_SEC`) and frame-based lost-frame grace (`MAX_LOST_FRAMES`).
- **Double-click logic**: index released within 0.3s enters `PENDING_CLICK`; re-bend within 0.3s triggers `DOUBLE_CLICK`, otherwise `LEFT_CLICK`.
- **Click detection**: Uses direct tip-vs-PIP Y comparison (`landmarks[8].y > landmarks[6].y`), not angle-based detection. This is simpler and more robust for the webcam perspective.
- **Cursor initialization**: On every hand lock, `cursor.reset_filters()` is called and the cursor snaps to the wrist position immediately. No need for a separate "open palm" gesture to start moving.
- **Flask dependencies**: `flask` and `flask-socketio` required (see `requirements.txt`).

## Constraints
- Python only, no package structure (`from config import CONFIG`, not `from hand_cursor.config`).
- Keep `config.py` as a plain dict — many modules depend on it.
- Do not add type stubs or `__init__.py` unless restructuring the whole project.
