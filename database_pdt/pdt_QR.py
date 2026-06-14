import cv2
import numpy as np
from pyzbar import pyzbar

import database


class QRScanner:
    """Decode QR data from frames supplied by CameraManager."""

    def __init__(self):
        self.cv_detector = cv2.QRCodeDetector()
        self.reset()

    def reset(self) -> None:
        self.completed = False
        self.value = ""
        self.message = "Dua ma QR vao khung camera"
        self.error = ""

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        value = ""

        try:
            results = pyzbar.decode(frame)
            if results:
                result = results[0]
                value = result.data.decode("utf-8").strip()
                rect = result.rect
                cv2.rectangle(
                    display,
                    (rect.left, rect.top),
                    (rect.left + rect.width, rect.top + rect.height),
                    (0, 255, 120),
                    3,
                )
        except Exception as exc:
            self.error = str(exc)

        if not value:
            try:
                value, points, _ = self.cv_detector.detectAndDecode(frame)
                value = value.strip()
                if points is not None and len(points):
                    polygon = points.astype(int).reshape(-1, 2)
                    cv2.polylines(display, [polygon], True, (0, 255, 120), 3)
            except Exception as exc:
                self.error = str(exc)

        if value and not self.completed:
            self.value = value
            self.completed = True
            self.message = f"Da quet QR: {value}"

        cv2.rectangle(display, (0, 0), (display.shape[1], 58), (8, 15, 30), -1)
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
    database.init_database()
    scanner = QRScanner()
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        print("Khong mo duoc camera.")
        return

    try:
        while not scanner.completed:
            ok, frame = camera.read()
            if not ok:
                print("Khong doc duoc frame camera.")
                break
            cv2.imshow("SmartFace QR", scanner.process_frame(frame))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        if scanner.value:
            if not database.person_exists(scanner.value):
                database.add_person(scanner.value, scanner.value)
            print(f"QR: {scanner.value}")
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
