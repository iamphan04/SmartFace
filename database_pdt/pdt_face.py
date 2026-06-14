import os
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import database

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "face_landmarker.task"
os.environ.setdefault("MPLCONFIGDIR", str(BASE_DIR.parent / ".cache" / "matplotlib"))

CAPTURE_STEPS = (
    ("front", "Nhin thang vao camera"),
    ("left", "Quay mat nhe sang trai"),
    ("right", "Quay mat nhe sang phai"),
)


def build_detector():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Khong tim thay model: {MODEL_PATH}")
    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(options)


def get_face_bbox(landmarks, width: int, height: int, padding: int = 30):
    xs = [int(point.x * width) for point in landmarks]
    ys = [int(point.y * height) for point in landmarks]
    return (
        max(0, min(xs) - padding),
        max(0, min(ys) - padding),
        min(width, max(xs) + padding),
        min(height, max(ys) + padding),
    )


class FaceScanner:
    """Capture front, left, and right face images from camera frames."""

    def __init__(self, capture_delay: float = 1.8):
        self.capture_delay = max(0.1, capture_delay)
        self.detector = build_detector()
        self.reset()

    def reset(self, student_id: str = "", purpose: str = "register") -> None:
        self.student_id = student_id
        self.purpose = purpose
        self.steps = CAPTURE_STEPS[:1] if purpose == "verify" else CAPTURE_STEPS
        self.step_index = 0
        self.captures: dict[str, np.ndarray] = {}
        self.phase_started_at = time.monotonic()
        self.completed = False
        self.face_detected = False
        self.progress = 0
        self.message = "Dang tim khuon mat"
        self.error = ""

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = cv2.flip(frame, 1)
        height, width = display.shape[:2]
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect(mp_image)
        landmarks = result.face_landmarks[0] if result.face_landmarks else None
        self.face_detected = landmarks is not None
        face_crop = None

        if landmarks is not None:
            x1, y1, x2, y2 = get_face_bbox(landmarks, width, height)
            face_crop = display[y1:y2, x1:x2].copy()
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 120), 2)
            for point in landmarks[::8]:
                cv2.circle(
                    display,
                    (int(point.x * width), int(point.y * height)),
                    1,
                    (0, 255, 120),
                    -1,
                )

        if self.completed:
            self.progress = 100
            self.message = "Da thu thap du lieu khuon mat"
        elif face_crop is None or face_crop.size == 0:
            self.phase_started_at = time.monotonic()
            self.message = "Chua tim thay khuon mat"
        else:
            step_key, instruction = self.steps[self.step_index]
            elapsed = time.monotonic() - self.phase_started_at
            step_progress = min(1.0, elapsed / self.capture_delay)
            self.progress = round(
                ((self.step_index + step_progress) / len(self.steps)) * 100
            )
            self.message = instruction
            if elapsed >= self.capture_delay:
                self.captures[step_key] = face_crop
                self.step_index += 1
                self.phase_started_at = time.monotonic()
                if self.step_index >= len(self.steps):
                    self.completed = True
                    self.progress = 100
                    self.message = "Da thu thap du lieu khuon mat"

        self._draw_hud(display)
        return display

    def _draw_hud(self, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (width, 66), (8, 15, 30), -1)
        cv2.putText(
            frame,
            self.message,
            (16, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 180) if self.face_detected else (80, 120, 255),
            2,
        )
        cv2.putText(
            frame,
            f"ID: {self.student_id} | {self.progress}%",
            (16, 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (230, 230, 230),
            1,
        )
        bar_width = int((width - 32) * self.progress / 100)
        cv2.rectangle(
            frame, (16, height - 18), (width - 16, height - 8), (45, 55, 70), -1
        )
        cv2.rectangle(
            frame,
            (16, height - 18),
            (16 + bar_width, height - 8),
            (0, 220, 160),
            -1,
        )

    def status(self) -> dict:
        step = (
            "complete"
            if self.completed
            else self.steps[min(self.step_index, len(self.steps) - 1)][0]
        )
        return {
            "studentId": self.student_id,
            "purpose": self.purpose,
            "running": not self.completed and not self.error,
            "completed": self.completed,
            "faceDetected": self.face_detected,
            "step": step,
            "progress": self.progress,
            "message": self.message,
            "captures": list(self.captures),
            "error": self.error,
            "detector": "mediapipe",
        }

    def get_captures(self) -> dict[str, np.ndarray]:
        return {key: image.copy() for key, image in self.captures.items()}

    def close(self) -> None:
        self.detector.close()


def main() -> None:
    database.init_database()
    student_id = input("Nhap ma sinh vien: ").strip()
    if not database.person_exists(student_id):
        print("Khong tim thay sinh vien trong database.")
        return

    scanner = FaceScanner()
    scanner.reset(student_id, "register")
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        print("Khong mo duoc camera.")
        scanner.close()
        return

    try:
        while not scanner.completed:
            ok, frame = camera.read()
            if not ok:
                break
            cv2.imshow("SmartFace PDT", scanner.process_frame(frame))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        captures = scanner.get_captures()
        if scanner.completed:
            database.save_face(
                student_id,
                captures["front"],
                captures["left"],
                captures["right"],
            )
    finally:
        camera.release()
        scanner.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
