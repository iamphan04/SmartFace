import threading
import time
from typing import Optional

import cv2
import numpy as np

from pdt_QR import QRScanner
from pdt_face import FaceScanner


class CameraManager:
    """Own the physical webcam and expose processed frames to FastAPI."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.lock = threading.RLock()
        self.camera = None
        self.thread = None
        self.stop_event = threading.Event()
        self.mode = "idle"
        self.processor = None
        self.latest_frame: Optional[np.ndarray] = None
        self.last_frame_at = 0.0
        self.error = ""

    def _open(self) -> bool:
        if self.camera is not None and self.camera.isOpened():
            return True
        camera = cv2.VideoCapture(self.camera_index)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if not camera.isOpened():
            camera.release()
            self.error = f"Khong mo duoc camera index {self.camera_index}"
            return False
        self.camera = camera
        self.error = ""
        return True

    def start(self) -> bool:
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return True
            if not self._open():
                return False
            self.stop_event.clear()
            self.thread = threading.Thread(
                target=self._capture_loop,
                name="smartface-camera",
                daemon=True,
            )
            self.thread.start()
            return True

    def stop(self) -> None:
        self.stop_event.set()
        thread = self.thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        with self.lock:
            if self.camera is not None:
                self.camera.release()
            self.camera = None
            self.thread = None
            self.latest_frame = None
            self.last_frame_at = 0.0
            self.mode = "idle"
            self.processor = None

    def _capture_loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                camera = self.camera
                processor = self.processor
            if camera is None:
                break

            ok, frame = camera.read()
            if not ok:
                self.error = "Khong doc duoc frame tu camera"
                time.sleep(0.1)
                continue

            try:
                display = processor.process_frame(frame) if processor else frame
            except Exception as exc:
                self.error = f"Loi xu ly camera: {exc}"
                display = frame

            with self.lock:
                self.latest_frame = display
                self.last_frame_at = time.time()
            time.sleep(0.01)

    def start_face(self, student_id: str, purpose: str) -> bool:
        scanner = FaceScanner()
        scanner.reset(student_id, purpose)
        with self.lock:
            self.processor = scanner
            self.mode = f"face_{purpose}"
        return self.start()

    def start_qr(self) -> bool:
        with self.lock:
            self.processor = QRScanner()
            self.mode = "qr"
        return self.start()

    def set_idle(self) -> None:
        with self.lock:
            self.processor = None
            self.mode = "idle"

    def status(self) -> dict:
        with self.lock:
            running = self.thread is not None and self.thread.is_alive()
            processor_status = self.processor.status() if self.processor else {}
            frame_age = (
                round(time.time() - self.last_frame_at, 2)
                if self.last_frame_at
                else None
            )
            return {
                "running": running,
                "opened": bool(self.camera is not None and self.camera.isOpened()),
                "cameraIndex": self.camera_index,
                "mode": self.mode,
                "frameReady": self.latest_frame is not None,
                "frameAgeSeconds": frame_age,
                "error": self.error,
                **processor_status,
            }

    def face_captures(self) -> dict[str, np.ndarray]:
        with self.lock:
            if isinstance(self.processor, FaceScanner):
                return self.processor.get_captures()
        return {}

    def qr_value(self) -> str:
        with self.lock:
            if isinstance(self.processor, QRScanner):
                return self.processor.value
        return ""

    def jpeg_frame(self) -> Optional[bytes]:
        with self.lock:
            frame = self.latest_frame.copy() if self.latest_frame is not None else None
        if frame is None:
            return None
        ok, encoded = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82]
        )
        return encoded.tobytes() if ok else None

    def stream(self):
        while True:
            frame = self.jpeg_frame()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
            time.sleep(0.04)
