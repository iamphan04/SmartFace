import os
import time
from collections import deque
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
MIN_FACE_QUALITY = 36
MIN_STABLE_FRAMES = 2
MAX_CAPTURE_CANDIDATES = 8
LANDMARK_DRAW_STEP = 14


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


def face_crop_quality(face_crop: np.ndarray) -> float:
    if face_crop is None or face_crop.size == 0:
        return 0.0
    gray = (
        face_crop
        if face_crop.ndim == 2
        else cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    )
    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur_score = min(blur / 100.0, 1.0)
    light_score = 1.0 - min(abs(brightness - 128.0) / 128.0, 1.0)
    contrast_score = min(contrast / 45.0, 1.0)
    score = 100.0 * (
        0.55 * blur_score + 0.25 * light_score + 0.20 * contrast_score
    )
    return float(round(float(score), 1))


class FaceScanner:
    """Capture front, left, and right face images from camera frames."""

    def __init__(self, capture_delay: float = 1.15):
        self.capture_delay = max(0.1, capture_delay)
        self.detector = build_detector()
        self.reset()

    def reset(self, student_id: str = "", purpose: str = "register") -> None:
        self.student_id = student_id
        self.purpose = purpose
        self.steps = CAPTURE_STEPS[:1] if purpose == "verify" else CAPTURE_STEPS
        self.active_capture_delay = 0.65 if purpose == "verify" else self.capture_delay
        self.step_index = 0
        self.captures: dict[str, np.ndarray] = {}
        self.phase_started_at = time.monotonic()
        self.completed = False
        self.face_detected = False
        self.face_quality = 0.0
        self.stable_frames = 0
        self.last_face_state = None
        self.capture_candidates: deque[tuple[float, np.ndarray]] = deque(
            maxlen=MAX_CAPTURE_CANDIDATES
        )
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
        face_state = None
        quality_ok = False

        if landmarks is not None:
            x1, y1, x2, y2 = get_face_bbox(landmarks, width, height)
            face_crop = display[y1:y2, x1:x2].copy()
            face_width = max(1, x2 - x1)
            face_height = max(1, y2 - y1)
            center_x = (x1 + x2) / (2 * width)
            center_y = (y1 + y2) / (2 * height)
            face_scale = max(face_width / width, face_height / height)
            center_offset = abs(center_x - 0.5) + abs(center_y - 0.5)
            face_state = (center_x, center_y, face_scale)
            self.face_quality = face_crop_quality(face_crop)
            quality_ok = (
                self.face_quality >= MIN_FACE_QUALITY
                and 0.14 <= face_scale <= 0.78
                and center_offset <= 0.55
            )
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 120), 2)
            for index, point in enumerate(landmarks):
                if index % LANDMARK_DRAW_STEP != 0:
                    continue
                cv2.circle(
                    display,
                    (int(point.x * width), int(point.y * height)),
                    1,
                    (0, 255, 120),
                    -1,
                )
            cv2.putText(
                display,
                f"Q: {self.face_quality:.0f} | STABLE: {self.stable_frames}",
                (x1, max(18, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (0, 255, 120) if quality_ok else (0, 180, 255),
                1,
            )

        if self.completed:
            self.progress = 100
            self.message = "Da thu thap du lieu khuon mat"
        elif face_crop is None or face_crop.size == 0:
            self.stable_frames = 0
            self.last_face_state = None
            self.capture_candidates.clear()
            self.phase_started_at = time.monotonic()
            self.message = "Chua tim thay khuon mat"
        elif not quality_ok:
            self.stable_frames = 0
            self.last_face_state = face_state
            self.capture_candidates.clear()
            self.phase_started_at = time.monotonic()
            self.message = "Giu mat o giua khung, du sang va net hon"
        else:
            step_key, instruction = self.steps[self.step_index]
            if self._face_is_stable(face_state):
                self.stable_frames += 1
            else:
                self.stable_frames = 1
                self.phase_started_at = time.monotonic()
                self.capture_candidates.clear()
            self.last_face_state = face_state

            self.capture_candidates.append((self.face_quality, face_crop.copy()))
            elapsed = time.monotonic() - self.phase_started_at
            step_progress = min(1.0, elapsed / self.active_capture_delay)
            self.progress = round(
                ((self.step_index + step_progress) / len(self.steps)) * 100
            )
            self.message = (
                instruction
                if self.stable_frames >= MIN_STABLE_FRAMES
                else "Giu yen khuon mat trong khung"
            )
            if (
                elapsed >= self.active_capture_delay
                and self.stable_frames >= MIN_STABLE_FRAMES
            ):
                best_quality, best_crop = max(
                    self.capture_candidates,
                    key=lambda item: item[0],
                )
                self.captures[step_key] = best_crop
                self.step_index += 1
                self.phase_started_at = time.monotonic()
                self.capture_candidates.clear()
                self.stable_frames = 0
                self.face_quality = best_quality
                if self.step_index >= len(self.steps):
                    self.completed = True
                    self.progress = 100
                    self.message = "Da thu thap du lieu khuon mat"

        self._draw_hud(display)
        return display

    def _face_is_stable(self, face_state) -> bool:
        if self.last_face_state is None or face_state is None:
            return True
        center_x, center_y, scale = face_state
        last_x, last_y, last_scale = self.last_face_state
        center_delta = abs(center_x - last_x) + abs(center_y - last_y)
        scale_delta = abs(scale - last_scale)
        return center_delta <= 0.14 and scale_delta <= 0.20

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
            "faceQuality": self.face_quality,
            "stableFrames": self.stable_frames,
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
