import cv2
import sys
from config import CONFIG


class Camera:
    def __init__(self):
        self.cap = self._find_working_camera()
        if self.cap is None:
            raise RuntimeError("No working camera found. Check camera permissions and that no other app is using the webcam.")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["FRAME_WIDTH"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["FRAME_HEIGHT"])
        self.cap.set(cv2.CAP_PROP_FPS, CONFIG["FPS"])
        width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"[Camera] Ready: {width}x{height}")

    def _find_working_camera(self):
        preferred = CONFIG.get("CAMERA_INDEX", 0)
        indices = [preferred] + [i for i in range(3) if i != preferred]
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]

        for idx in indices:
            for backend in backends:
                cap = cv2.VideoCapture(idx, backend)
                if not cap.isOpened():
                    cap.release()
                    continue
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"[Camera] Found working camera at index {idx}, backend {backend}")
                    return cap
                cap.release()

        return None

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        frame = cv2.flip(frame, 1)
        return frame

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            print("[Camera] Released")
