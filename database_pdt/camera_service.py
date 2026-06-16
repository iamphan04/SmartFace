import threading
import time
from typing import Optional

import cv2
import numpy as np


class CameraManager:
    """Own the physical webcam and expose processed frames to FastAPI."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.lock = threading.RLock()
        self.process_lock = threading.Lock()
        self.camera = None
        self.thread = None
        self.stop_event = threading.Event()
        self.mode = "idle"
        self.session_id = 0
        self.processor = None
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_jpeg: Optional[bytes] = None
        self.last_frame_at = 0.0
        self.error = ""

    def _open(self) -> bool:
        if self.camera is not None and self.camera.isOpened():
            return True
        camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            camera.release()
            camera = cv2.VideoCapture(self.camera_index)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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
        with self.process_lock:
            with self.lock:
                self._close_processor()
                if self.camera is not None:
                    self.camera.release()
                self.camera = None
                self.thread = None
                self.latest_frame = None
                self.latest_jpeg = None
                self.last_frame_at = 0.0
                self.mode = "idle"
                self.processor = None
                self.session_id += 1

    def _close_processor(self) -> None:
        close = getattr(self.processor, "close", None)
        if callable(close):
            close()

    def _capture_loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                camera = self.camera
            if camera is None:
                break

            ok, frame = camera.read()
            if not ok:
                self.error = "Khong doc duoc frame tu camera"
                time.sleep(0.1)
                continue

            try:
                with self.process_lock:
                    with self.lock:
                        processor = self.processor
                        processed_session = self.session_id
                    display = processor.process_frame(frame) if processor else frame
            except Exception as exc:
                with self.lock:
                    if self.session_id == processed_session:
                        self.error = f"Loi xu ly camera: {exc}"
                display = frame

            encoded_ok, encoded = cv2.imencode(
                ".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 76]
            )
            with self.lock:
                if self.session_id != processed_session:
                    continue
                self.latest_frame = display
                self.latest_jpeg = encoded.tobytes() if encoded_ok else None
                self.last_frame_at = time.time()

    def start_face(self, student_id: str, purpose: str) -> bool:
        from pdt_face import FaceScanner

        scanner = FaceScanner()
        scanner.reset(student_id, purpose)
        with self.process_lock:
            with self.lock:
                self._close_processor()
                self.processor = scanner
                self.mode = f"face_{purpose}"
                self.session_id += 1
                self.latest_frame = None
                self.latest_jpeg = None
                self.last_frame_at = 0.0
                self.error = ""
        return self.start()

    def start_qr(self) -> bool:
        from pdt_QR import QRScanner

        scanner = QRScanner()
        with self.process_lock:
            with self.lock:
                self._close_processor()
                self.processor = scanner
                self.mode = "qr"
                self.session_id += 1
                self.latest_frame = None
                self.latest_jpeg = None
                self.last_frame_at = 0.0
                self.error = ""
        return self.start()

    def set_idle(self) -> None:
        with self.process_lock:
            with self.lock:
                self._close_processor()
                self.processor = None
                self.mode = "idle"
                self.session_id += 1
                self.latest_frame = None
                self.latest_jpeg = None
                self.last_frame_at = 0.0

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
                "sessionId": self.session_id,
                "frameReady": self.latest_frame is not None,
                "frameAgeSeconds": frame_age,
                "error": self.error,
                **processor_status,
            }

    def face_captures(self) -> dict[str, np.ndarray]:
        with self.lock:
            if self.mode.startswith("face_"):
                get_captures = getattr(self.processor, "get_captures", None)
                if callable(get_captures):
                    return get_captures()
        return {}

    def qr_value(self) -> str:
        with self.lock:
            if self.mode == "qr":
                return getattr(self.processor, "value", "")
        return ""

    def qr_scan(self) -> dict:
        with self.lock:
            if self.mode != "qr":
                return {}
            scan_result = getattr(self.processor, "scan_result", None)
            if callable(scan_result):
                return scan_result()
            return {"value": getattr(self.processor, "value", "")}

    def jpeg_frame(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def stream(self, session_id: Optional[int] = None):
        while True:
            with self.lock:
                running = self.thread is not None and self.thread.is_alive()
                current_session = self.session_id
                frame = self.latest_jpeg
            if not running or (
                session_id is not None and current_session != session_id
            ):
                break
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
            time.sleep(0.05)
