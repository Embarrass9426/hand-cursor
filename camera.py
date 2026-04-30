import cv2
from config import CONFIG


class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(CONFIG["CAMERA_INDEX"])
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera at index {CONFIG['CAMERA_INDEX']}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["FRAME_WIDTH"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["FRAME_HEIGHT"])
        self.cap.set(cv2.CAP_PROP_FPS, CONFIG["FPS"])

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        frame = cv2.flip(frame, 1)
        return frame

    def release(self):
        self.cap.release()