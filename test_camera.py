import cv2
import sys
import time


def try_backend(index, backend_name, backend_code):
    print(f"\n--- Trying camera index {index}, backend {backend_name} ---")
    cap = cv2.VideoCapture(index, backend_code)
    if not cap.isOpened():
        print(f"  FAILED: could not open")
        cap.release()
        return False

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"  Opened: {width}x{height}")

    print("  Reading frame...")
    ret, frame = cap.read()
    if not ret or frame is None:
        print("  FAILED: first read returned None")
        cap.release()
        return False

    print(f"  SUCCESS: frame shape {frame.shape}")
    cv2.imwrite(f"camera_test_{index}_{backend_name}.jpg", frame)
    print(f"  Saved: camera_test_{index}_{backend_name}.jpg")

    cap.release()
    return True


def main():
    print("=" * 60)
    print("Camera Test Script")
    print("Platform:", sys.platform)
    print("OpenCV version:", cv2.__version__)
    print("=" * 60)

    backends = []
    if sys.platform == "win32":
        backends = [
            ("CAP_DSHOW", cv2.CAP_DSHOW),
            ("CAP_MSMF", cv2.CAP_MSMF),
            ("CAP_VFW", cv2.CAP_VFW),
            ("CAP_ANY", cv2.CAP_ANY),
        ]
    else:
        backends = [
            ("CAP_V4L2", cv2.CAP_V4L2),
            ("CAP_ANY", cv2.CAP_ANY),
        ]

    any_success = False
    for index in range(3):
        for name, code in backends:
            try:
                if try_backend(index, name, code):
                    any_success = True
            except Exception as e:
                print(f"  EXCEPTION: {e}")

    print("\n" + "=" * 60)
    if any_success:
        print("At least one camera + backend combination worked.")
        print("Check the saved .jpg files to see which one.")
    else:
        print("NO camera worked with any backend.")
        print("Possible causes:")
        print("  - Camera is being used by another app (Zoom, Teams, etc.)")
        print("  - Camera permissions are blocked for Python")
        print("  - No camera is connected")
        print("  - Camera driver needs to be updated")
    print("=" * 60)


if __name__ == "__main__":
    main()
