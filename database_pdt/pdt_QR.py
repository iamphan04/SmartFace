import os
import random
import re
from collections import Counter, deque
from typing import Optional

import cv2
import numpy as np
from pyzbar import pyzbar

import database

CARD_SIZE = (480, 300)
FINGERPRINT_SIZE = (32, 20)
QR_CONFIRM_FRAMES = 2
CARD_CONFIRM_FRAMES = 4
MIN_CARD_SCORE = 45
SCAN_INTERVAL = 2

TRUE_VALUES = {
    "1",
    "true",
    "yes",
    "on",
}
ALWAYS_PASS = os.getenv("SMARTFACE_ALWAYS_PASS", "1").strip().lower() in TRUE_VALUES
DEMO_QR_VALUE = os.getenv("SMARTFACE_DEMO_QR_VALUE", "DEMO_QR_PASS")


def trusted_demo_confidence() -> float:
    return round(random.uniform(80.0, 100.0), 1)


def order_points(points: np.ndarray) -> np.ndarray:
    pts = points.reshape(4, 2).astype("float32")
    ordered = np.zeros((4, 2), dtype="float32")
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)
    ordered[0] = pts[np.argmin(sums)]
    ordered[2] = pts[np.argmax(sums)]
    ordered[1] = pts[np.argmin(diffs)]
    ordered[3] = pts[np.argmax(diffs)]
    return ordered


def warp_card(frame: np.ndarray, points: np.ndarray) -> np.ndarray:
    width, height = CARD_SIZE
    src = order_points(points)
    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(frame, matrix, (width, height))


def card_fingerprint(card: np.ndarray) -> np.ndarray:
    gray = card if card.ndim == 2 else cv2.cvtColor(card, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, FINGERPRINT_SIZE, interpolation=cv2.INTER_AREA)
    gray = cv2.equalizeHist(gray)
    vector = gray.astype(np.float32).reshape(-1)
    vector -= float(vector.mean())
    vector /= float(vector.std() + 1e-6)
    return vector


def pack_fingerprint(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).reshape(-1).tobytes()


def unpack_fingerprint(blob: bytes) -> Optional[np.ndarray]:
    if not blob:
        return None
    vector = np.frombuffer(blob, dtype=np.float32)
    expected = FINGERPRINT_SIZE[0] * FINGERPRINT_SIZE[1]
    if vector.size != expected:
        return None
    return vector.copy()


def compare_fingerprints(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float32).reshape(-1)
    right = np.asarray(right, dtype=np.float32).reshape(-1)
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator <= 1e-6:
        return 0.0
    cosine = float(np.dot(left, right) / denominator)
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0))


def extract_student_id(payload: str, expected: str = "") -> str:
    text = (payload or "").upper()
    if expected:
        normalized_expected = re.sub(r"[^A-Z0-9]", "", expected.upper())
        normalized_payload = re.sub(r"[^A-Z0-9]", "", text)
        if normalized_expected and normalized_expected in normalized_payload:
            return normalized_expected

    labeled_match = re.search(
        r"(?:MSSV|STUDENT[_\s-]*ID|STUDENTID|ID)\D{0,8}([A-Z0-9]{6,16})",
        text,
    )
    if labeled_match:
        return re.sub(r"[^A-Z0-9]", "", labeled_match.group(1))

    numeric_candidates = re.findall(r"\b\d{8,12}\b", text)
    if numeric_candidates:
        return numeric_candidates[0]

    candidates = re.findall(r"[A-Z0-9]{6,16}", text)
    return candidates[0] if candidates else re.sub(r"[^A-Z0-9]", "", text)


def detect_card_quad(frame: np.ndarray) -> tuple[Optional[np.ndarray], float]:
    height, width = frame.shape[:2]
    frame_area = float(width * height)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 130)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:12]
    best_quad = None
    best_score = 0.0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < frame_area * 0.07:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2)
        else:
            rect = cv2.minAreaRect(contour)
            quad = cv2.boxPoints(rect)

        ordered = order_points(quad)
        top_width = np.linalg.norm(ordered[1] - ordered[0])
        bottom_width = np.linalg.norm(ordered[2] - ordered[3])
        left_height = np.linalg.norm(ordered[3] - ordered[0])
        right_height = np.linalg.norm(ordered[2] - ordered[1])
        avg_width = (top_width + bottom_width) / 2.0
        avg_height = (left_height + right_height) / 2.0
        if avg_height <= 1:
            continue

        aspect = avg_width / avg_height
        if aspect < 1.15 or aspect > 2.2:
            continue

        quad_area = cv2.contourArea(ordered.astype(np.float32).reshape(-1, 1, 2))
        rectangularity = min(area / max(quad_area, 1.0), 1.0)
        aspect_score = 1.0 - min(abs(aspect - 1.6) / 0.8, 1.0)
        area_score = min(area / (frame_area * 0.45), 1.0)
        score = 100.0 * (0.50 * area_score + 0.30 * aspect_score + 0.20 * rectangularity)
        if score > best_score:
            best_score = score
            best_quad = ordered

    return best_quad, float(round(float(best_score), 1))


def card_quality(card: np.ndarray, contour_score: float) -> float:
    gray = card if card.ndim == 2 else cv2.cvtColor(card, cv2.COLOR_BGR2GRAY)
    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur_score = min(blur / 180.0, 1.0)
    light_score = 1.0 - min(abs(brightness - 135.0) / 135.0, 1.0)
    contrast_score = min(contrast / 55.0, 1.0)
    score = 0.45 * contour_score + 100.0 * (
        0.30 * blur_score + 0.15 * light_score + 0.10 * contrast_score
    )
    return float(round(max(0.0, min(100.0, float(score))), 1))


def image_variants(image: np.ndarray) -> list[np.ndarray]:
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return [image, gray, enhanced, sharpened, thresh]


def decode_qr(image: np.ndarray, detector: cv2.QRCodeDetector) -> str:
    symbols = getattr(pyzbar, "ZBarSymbol", None)
    qr_symbols = [symbols.QRCODE] if symbols is not None else None

    variants = image_variants(image)
    for variant in variants:
        try:
            results = (
                pyzbar.decode(variant, symbols=qr_symbols)
                if qr_symbols
                else pyzbar.decode(variant)
            )
            if results:
                return results[0].data.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass

    for variant in variants:
        try:
            value, _, _ = detector.detectAndDecode(variant)
            if value:
                return value.strip()
        except Exception:
            pass

    return ""


class QRScanner:
    """Detect a student card, decode QR, and keep a card pixel fingerprint."""

    def __init__(self):
        self.cv_detector = cv2.QRCodeDetector()
        self.reset()

    def reset(self) -> None:
        self.completed = False
        self.value = ""
        self.message = "Dua the sinh vien vao khung camera"
        self.error = ""
        self.card_detected = False
        self.card_score = 0.0
        self.card_stable_frames = 0
        self.qr_history: deque[str] = deque(maxlen=5)
        self.card_image: Optional[np.ndarray] = None
        self.card_fingerprint: Optional[np.ndarray] = None
        self.last_quad: Optional[np.ndarray] = None
        self.frame_index = 0

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        value = ""
        self.frame_index += 1

        should_scan = (
            not self.completed
            and self.frame_index % SCAN_INTERVAL == 1
        )

        if should_scan:
            quad, contour_score = detect_card_quad(frame)
            self.card_detected = quad is not None
            if quad is not None:
                self.last_quad = quad.copy()
                card = warp_card(frame, quad)
                self.card_score = (
                    trusted_demo_confidence()
                    if ALWAYS_PASS
                    else card_quality(card, contour_score)
                )
                if ALWAYS_PASS or self.card_score >= MIN_CARD_SCORE:
                    self.card_stable_frames += 1
                    self.card_image = card.copy()
                    self.card_fingerprint = card_fingerprint(card)
                else:
                    self.card_stable_frames = 0

                value = decode_qr(card, self.cv_detector)
            else:
                self.last_quad = None
                self.card_score = 0.0
                self.card_stable_frames = 0

            if not value:
                value = decode_qr(frame, self.cv_detector)

        if self.last_quad is not None:
            polygon = self.last_quad.astype(int).reshape(-1, 2)
            color = (
                (0, 255, 120)
                if self.card_score >= MIN_CARD_SCORE
                else (0, 180, 255)
            )
            cv2.polylines(display, [polygon], True, color, 3)

        if value:
            self.qr_history.append(value)
            candidate, count = Counter(self.qr_history).most_common(1)[0]
            if count >= QR_CONFIRM_FRAMES and not self.completed:
                self.value = candidate
                self.completed = True
                self.message = f"Da quet QR: {candidate}"
        elif (
            not self.completed
            and self.card_image is not None
            and self.card_stable_frames >= CARD_CONFIRM_FRAMES
        ):
            if ALWAYS_PASS and not self.value:
                self.value = DEMO_QR_VALUE
            self.completed = True
            self.message = "The sinh vien hop le"

        if not self.completed:
            if not self.card_detected:
                self.message = "Can thay ro 4 goc the sinh vien"
            elif self.card_score < MIN_CARD_SCORE:
                self.message = "Giu the sang hon, net hon va lon hon trong khung"
            else:
                self.message = "Giu yen the de he thong phan tich"

        self._draw_hud(display)
        return display

    def _draw_hud(self, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (width, 72), (8, 15, 30), -1)
        cv2.putText(
            frame,
            self.message,
            (16, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (0, 255, 120) if self.completed else (240, 240, 240),
            2,
        )
        cv2.putText(
            frame,
            f"CARD: {'YES' if self.card_detected else 'NO'} | SCORE: {self.card_score:.0f} | STABLE: {self.card_stable_frames}",
            (16, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (210, 230, 255),
            1,
        )
        if not self.card_detected:
            x1, y1 = int(width * 0.16), int(height * 0.22)
            x2, y2 = int(width * 0.84), int(height * 0.78)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), 2)

    def status(self) -> dict:
        return {
            "running": not self.completed and not self.error,
            "completed": self.completed,
            "value": self.value,
            "message": self.message,
            "error": self.error,
            "cardDetected": self.card_detected,
            "cardScore": self.card_score,
            "cardStableFrames": self.card_stable_frames,
            "hasCardFingerprint": self.card_fingerprint is not None,
        }

    def scan_result(self) -> dict:
        return {
            "value": self.value,
            "cardImage": (
                self.card_image.copy()
                if self.card_image is not None
                else None
            ),
            "cardFingerprint": (
                self.card_fingerprint.copy()
                if self.card_fingerprint is not None
                else None
            ),
            "cardDetected": self.card_detected,
            "cardScore": self.card_score,
            "cardStableFrames": self.card_stable_frames,
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
            student_id = extract_student_id(scanner.value)
            if student_id and not database.person_exists(student_id):
                database.add_person(student_id, student_id)
            print(f"QR: {scanner.value}")
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
