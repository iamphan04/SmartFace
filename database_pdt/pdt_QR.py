import time

import cv2
import numpy as np


class QRScanner:
    """Decode one QR value from frames supplied by the shared camera."""

    def __init__(self):
        self.cv_detector = cv2.QRCodeDetector()
        self.reset()

    def reset(self) -> None:
        self.started_at = time.monotonic()
        self.completed = False
        self.value = ""
        self.message = "Dua ma QR vao khung camera"
        self.error = ""

    @staticmethod
    def _decode_pyzbar(frame: np.ndarray):
        try:
            from pyzbar import pyzbar

            results = pyzbar.decode(frame)
            if not results:
                return "", None
            result = results[0]
            value = result.data.decode("utf-8").strip()
            rect = result.rect
            box = (
                rect.left,
                rect.top,
                rect.left + rect.width,
                rect.top + rect.height,
            )
            return value, box
        except Exception:
            return "", None

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        value, box = self._decode_pyzbar(frame)

        if not value:
            try:
                value, points, _ = self.cv_detector.detectAndDecode(frame)
                value = value.strip()
                if points is not None and len(points):
                    points = points.astype(int).reshape(-1, 2)
                    cv2.polylines(display, [points], True, (0, 255, 120), 3)
            except Exception as exc:
                self.error = str(exc)

        if box:
            x1, y1, x2, y2 = box
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 120), 3)

        if value and not self.completed:
            self.value = value
            self.completed = True
            self.message = f"Da quet QR: {value}"

        width = display.shape[1]
        cv2.rectangle(display, (0, 0), (width, 58), (8, 15, 30), -1)
        cv2.putText(
            display,
            self.message,
            (16, 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (0, 255, 120) if self.completed else (240, 240, 240),
            2,
        )
        return display

    def status(self) -> dict:
        return {
            "running": not self.completed and not self.error,
            "completed": self.completed,
            "value": self.value,
            "message": self.message,
            "error": self.error,
        }


def main() -> None:
    scanner = QRScanner()
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Khong mo duoc camera.")
        return
    try:
        while not scanner.completed:
            ok, frame = camera.read()
            if not ok:
                break
            cv2.imshow("SmartFace QR", scanner.process_frame(frame))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        if scanner.value:
            print(scanner.value)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
