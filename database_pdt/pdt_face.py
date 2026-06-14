import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "face_landmarker.task"
CAPTURE_STEPS = (
    ("front", "Nhin thang vao camera"),
    ("left", "Quay mat nhe sang trai"),
    ("right", "Quay mat nhe sang phai"),
)


class FaceScanner:
    """Process camera frames for web registration and verification."""

    def __init__(self, capture_delay: float = 1.8):
        self.capture_delay = capture_delay
        self.detector = None
        self.detector_error = ""
        self.reset()

    def reset(self, student_id: str = "", purpose: str = "register") -> None:
        self.student_id = student_id
        self.purpose = purpose
        self.step_index = 0
        self.captures: dict[str, np.ndarray] = {}
        self.phase_started_at = time.monotonic()
        self.started_at = time.monotonic()
        self.completed = False
        self.error = ""
        self.face_detected = False
        self.progress = 0
        self.message = "Dang tim khuon mat..."

    def _build_detector(self):
        if self.detector is not None or self.detector_error:
            return self.detector
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
                num_faces=1,
            )
            self.detector = vision.FaceLandmarker.create_from_options(options)
            self._mp = mp
        except Exception as exc:
            self.detector_error = str(exc)
        return self.detector

    @staticmethod
    def _bbox(landmarks, width: int, height: int, padding: int = 35):
        xs = [int(point.x * width) for point in landmarks]
        ys = [int(point.y * height) for point in landmarks]
        return (
            max(0, min(xs) - padding),
            max(0, min(ys) - padding),
            min(width, max(xs) + padding),
            min(height, max(ys) + padding),
        )

    @staticmethod
    def _fallback_crop(frame: np.ndarray) -> Optional[np.ndarray]:
        """Use OpenCV face detection when MediaPipe is unavailable."""
        haar_root = getattr(getattr(cv2, "data", None), "haarcascades", "")
        cascade_path = Path(haar_root) / "haarcascade_frontalface_default.xml"
        if haar_root and cascade_path.is_file():
            detector = cv2.CascadeClassifier(str(cascade_path))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )
            if len(faces):
                x, y, width, height = max(
                    faces, key=lambda face: face[2] * face[3]
                )
                return frame[y : y + height, x : x + width].copy()

        # Minimal fallback for OpenCV builds that do not bundle Haar cascades.
        height, width = frame.shape[:2]
        side = int(min(height, width) * 0.68)
        x1 = max(0, (width - side) // 2)
        y1 = max(0, (height - side) // 2)
        crop = frame[y1 : y1 + side, x1 : x1 + side]
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if gray_crop.mean() < 8 or gray_crop.std() < 3:
            return None
        return crop.copy()

    def _detect_face(self, frame: np.ndarray):
        detector = self._build_detector()
        if detector is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = self._mp.Image(
                image_format=self._mp.ImageFormat.SRGB,
                data=rgb,
            )
            result = detector.detect(mp_image)
            if result.face_landmarks:
                landmarks = result.face_landmarks[0]
                height, width = frame.shape[:2]
                x1, y1, x2, y2 = self._bbox(landmarks, width, height)
                return frame[y1:y2, x1:x2].copy(), (x1, y1, x2, y2), landmarks

        crop = self._fallback_crop(frame)
        if crop is None:
            return None, None, None
        height, width = frame.shape[:2]
        crop_height, crop_width = crop.shape[:2]
        x1 = max(0, (width - crop_width) // 2)
        y1 = max(0, (height - crop_height) // 2)
        return crop, (x1, y1, x1 + crop_width, y1 + crop_height), None

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = cv2.flip(frame, 1)
        face_crop, box, landmarks = self._detect_face(display)
        self.face_detected = face_crop is not None and face_crop.size > 0

        if box:
            x1, y1, x2, y2 = box
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 120), 2)
        if landmarks:
            height, width = display.shape[:2]
            for point in landmarks[::8]:
                cv2.circle(
                    display,
                    (int(point.x * width), int(point.y * height)),
                    1,
                    (0, 255, 120),
                    -1,
                )

        if self.completed:
            self.message = "Da thu thap du lieu khuon mat"
            self.progress = 100
        elif not self.face_detected:
            self.phase_started_at = time.monotonic()
            self.message = "Chua tim thay khuon mat"
        else:
            steps = CAPTURE_STEPS[:1] if self.purpose == "verify" else CAPTURE_STEPS
            step_key, instruction = steps[self.step_index]
            elapsed = time.monotonic() - self.phase_started_at
            capture_delay = max(0.01, self.capture_delay)
            step_progress = min(1.0, elapsed / capture_delay)
            self.progress = round(
                ((self.step_index + step_progress) / len(steps)) * 100
            )
            self.message = instruction

            if elapsed >= capture_delay:
                self.captures[step_key] = face_crop.copy()
                self.step_index += 1
                self.phase_started_at = time.monotonic()
                if self.step_index >= len(steps):
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
        cv2.rectangle(frame, (16, height - 18), (width - 16, height - 8), (45, 55, 70), -1)
        cv2.rectangle(frame, (16, height - 18), (16 + bar_width, height - 8), (0, 220, 160), -1)

    def status(self) -> dict:
        steps = CAPTURE_STEPS[:1] if self.purpose == "verify" else CAPTURE_STEPS
        current_step = (
            "complete"
            if self.completed
            else steps[min(self.step_index, len(steps) - 1)][0]
        )
        return {
            "studentId": self.student_id,
            "purpose": self.purpose,
            "running": not self.completed and not self.error,
            "completed": self.completed,
            "faceDetected": self.face_detected,
            "step": current_step,
            "progress": self.progress,
            "message": self.message,
            "captures": list(self.captures),
            "error": self.error,
            "detector": "mediapipe" if self.detector is not None else "opencv",
            "detectorWarning": self.detector_error,
        }

    def get_captures(self) -> dict[str, np.ndarray]:
        return {key: image.copy() for key, image in self.captures.items()}


def main() -> None:
    scanner = FaceScanner()
    student_id = input("Nhap ma sinh vien: ").strip()
    scanner.reset(student_id, "register")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Khong mo duoc camera.")
        return
    try:
        while not scanner.completed:
            ok, frame = camera.read()
            if not ok:
                break
            cv2.imshow("SmartFace PDT", scanner.process_frame(frame))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
