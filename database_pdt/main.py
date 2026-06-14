import base64
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist-app"
DB_PATH = Path(os.getenv("SMARTFACE_DB", BASE_DIR / "System.db")).resolve()

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from camera_service import CameraManager  # noqa: E402
from cloneAPI.fraud_engine import (  # noqa: E402
    calculate_fraud_score,
    get_confidence,
    get_risk_level,
)


class RegisterData(BaseModel):
    studentId: str = Field(min_length=1)
    fullName: str = Field(min_length=1)
    dob: str = ""
    faculty: str = ""
    email: str = ""
    registeredAt: str = ""
    face_front_b64: Optional[str] = None
    face_left_b64: Optional[str] = None
    face_right_b64: Optional[str] = None


class VerifyFaceData(BaseModel):
    studentId: str = Field(min_length=1)
    image: str = Field(min_length=1)


class VerifyDocumentData(BaseModel):
    studentId: Optional[str] = None
    mssv: Optional[str] = None
    name: str = ""


app = FastAPI(title="SmartFace API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
camera_manager = CameraManager(
    camera_index=int(os.getenv("SMARTFACE_CAMERA_INDEX", "0"))
)


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect_db()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                student_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                dob TEXT DEFAULT '',
                faculty TEXT DEFAULT '',
                email TEXT DEFAULT '',
                registered_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS face_images (
                student_id TEXT PRIMARY KEY,
                front_image BLOB NOT NULL,
                left_image BLOB NOT NULL,
                right_image BLOB NOT NULL,
                source TEXT NOT NULL DEFAULT 'frontend',
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY(student_id) REFERENCES profiles(student_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS processed_faces (
                student_id TEXT PRIMARY KEY,
                front_processed BLOB NOT NULL,
                left_processed BLOB NOT NULL,
                right_processed BLOB NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'ready',
                processed_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY(student_id) REFERENCES profiles(student_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS check_fail (
                id INTEGER PRIMARY KEY,
                student_id TEXT,
                captured_face BLOB,
                face_similarity REAL NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 0,
                risk_score INTEGER NOT NULL DEFAULT 100,
                risk_level TEXT NOT NULL DEFAULT 'CRITICAL',
                reasons TEXT DEFAULT '',
                checked_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY(student_id) REFERENCES profiles(student_id) ON DELETE SET NULL
            );
            """
        )
        conn.commit()

def decode_image(value: str) -> np.ndarray:
    try:
        encoded = value.split(",", 1)[1] if "," in value else value
        raw = base64.b64decode(encoded, validate=True)
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Du lieu anh base64 khong hop le.") from exc
    if image is None:
        raise HTTPException(status_code=400, detail="Khong the doc anh.")
    return image


def encode_jpeg(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise HTTPException(status_code=400, detail="Khong the nen anh.")
    return buffer.tobytes()


def decode_blob(blob: bytes) -> Optional[np.ndarray]:
    if not blob:
        return None
    return cv2.imdecode(np.frombuffer(blob, np.uint8), cv2.IMREAD_COLOR)


def crop_face(image: np.ndarray) -> np.ndarray:
    gray = (
        image
        if image.ndim == 2
        else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    )
    haarcascades = getattr(getattr(cv2, "data", None), "haarcascades", "")
    cascade_path = f"{haarcascades}haarcascade_frontalface_default.xml"
    if not haarcascades or not Path(cascade_path).is_file():
        return gray

    detector = cv2.CascadeClassifier(cascade_path)
    faces = detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    if len(faces) == 0:
        return gray
    x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
    return gray[y : y + height, x : x + width]


def process_face(image: np.ndarray) -> np.ndarray:
    face = crop_face(image)
    face = cv2.resize(face, (256, 256), interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(face)


def comparison_face(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2 and image.shape == (256, 256):
        return image
    if image.ndim == 3 and image.shape[:2] == (256, 256):
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return process_face(image)


def compare_faces(registered: np.ndarray, captured: np.ndarray) -> float:
    left = cv2.resize(comparison_face(registered), (128, 128))
    right = cv2.resize(comparison_face(captured), (128, 128))

    left_vector = left.astype(np.float32).reshape(-1)
    right_vector = right.astype(np.float32).reshape(-1)
    left_vector -= left_vector.mean()
    right_vector -= right_vector.mean()
    denominator = np.linalg.norm(left_vector) * np.linalg.norm(right_vector)
    correlation = float(np.dot(left_vector, right_vector) / (denominator + 1e-8))

    left_hist = cv2.calcHist([left], [0], None, [64], [0, 256])
    right_hist = cv2.calcHist([right], [0], None, [64], [0, 256])
    histogram = float(cv2.compareHist(left_hist, right_hist, cv2.HISTCMP_CORREL))

    return max(
        0.0,
        min(1.0, 0.75 * max(0.0, correlation) + 0.25 * max(0.0, histogram)),
    )


def user_payload(row: sqlite3.Row) -> dict:
    return {
        "studentId": row["student_id"],
        "fullName": row["full_name"],
        "dob": row["dob"] or "",
        "faculty": row["faculty"] or "",
        "email": row["email"] or "",
        "registeredAt": row["registered_at"] or row["created_at"] or "",
        "hasFace": bool(row["has_face"]),
    }


def user_query() -> str:
    return """
        SELECT p.student_id, p.full_name, p.dob, p.faculty, p.email,
               p.registered_at, p.created_at,
               CASE WHEN pf.student_id IS NOT NULL THEN 1 ELSE 0 END AS has_face
        FROM profiles p
        LEFT JOIN processed_faces pf ON pf.student_id = p.student_id
    """


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.on_event("shutdown")
def shutdown() -> None:
    camera_manager.stop()


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    database_ok = False
    database_error = ""
    try:
        with closing(connect_db()) as conn:
            conn.execute("SELECT 1").fetchone()
        database_ok = True
    except sqlite3.Error as exc:
        database_error = str(exc)

    camera = camera_manager.status()
    healthy = database_ok and not camera["error"]
    return {
        "status": "ok" if healthy else "degraded",
        "service": "SmartFace FastAPI",
        "port": 8000,
        "database": {
            "ok": database_ok,
            "path": str(DB_PATH),
            "error": database_error,
        },
        "frontend": {
            "built": (FRONTEND_DIST / "index.html").is_file(),
            "path": str(FRONTEND_DIST),
        },
        "camera": camera,
    }


@app.post("/api/camera/start")
def start_camera() -> dict:
    if not camera_manager.start():
        raise HTTPException(status_code=503, detail=camera_manager.status()["error"])
    return camera_manager.status()


@app.post("/api/camera/stop")
def stop_camera() -> dict:
    camera_manager.stop()
    return camera_manager.status()


@app.get("/api/camera/status")
def camera_status() -> dict:
    return camera_manager.status()


@app.get("/api/camera/stream")
def camera_stream():
    if not camera_manager.start():
        raise HTTPException(status_code=503, detail=camera_manager.status()["error"])
    return StreamingResponse(
        camera_manager.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.post("/api/face/start/{student_id}")
def start_face_scan(student_id: str, purpose: str = "register") -> dict:
    if purpose not in {"register", "verify"}:
        raise HTTPException(status_code=400, detail="Purpose phai la register hoac verify.")
    if not camera_manager.start_face(student_id.strip().upper(), purpose):
        raise HTTPException(status_code=503, detail=camera_manager.status()["error"])
    return camera_manager.status()


@app.get("/api/face/status")
def face_status() -> dict:
    status = camera_manager.status()
    if not status["mode"].startswith("face_"):
        raise HTTPException(status_code=409, detail="Face scanner chua duoc khoi dong.")
    return status


@app.post("/api/face/cancel")
def cancel_face_scan() -> dict:
    camera_manager.set_idle()
    return camera_manager.status()


@app.post("/api/qr/start")
def start_qr_scan() -> dict:
    if not camera_manager.start_qr():
        raise HTTPException(status_code=503, detail=camera_manager.status()["error"])
    return camera_manager.status()


@app.get("/api/qr/status")
def qr_status() -> dict:
    status = camera_manager.status()
    if status["mode"] != "qr":
        raise HTTPException(status_code=409, detail="QR scanner chua duoc khoi dong.")
    return status


@app.post("/api/qr/stop")
def stop_qr_scan() -> dict:
    camera_manager.set_idle()
    return camera_manager.status()


@app.post("/api/qr/verify/{student_id}")
def verify_qr(student_id: str) -> dict:
    value = camera_manager.qr_value().strip()
    expected = student_id.strip().upper()
    success = bool(value) and value.upper() == expected
    return {
        "success": success,
        "studentId": expected,
        "qrValue": value,
        "message": "QR trung khop." if success else "QR khong trung MSSV.",
    }


@app.get("/api/users")
def list_users() -> list[dict]:
    with closing(connect_db()) as conn:
        rows = conn.execute(
            f"{user_query()} ORDER BY p.created_at DESC, p.student_id"
        ).fetchall()
    return [user_payload(row) for row in rows]


@app.get("/api/users/{student_id}")
def get_user(student_id: str) -> dict:
    with closing(connect_db()) as conn:
        row = conn.execute(
            f"{user_query()} WHERE p.student_id = ?", (student_id.upper(),)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Khong tim thay sinh vien.")
    return user_payload(row)


@app.post("/api/register", status_code=201)
def register_user(data: RegisterData) -> dict:
    student_id = data.studentId.strip().upper()
    images = [
        decode_image(value) if value else None
        for value in (data.face_front_b64, data.face_left_b64, data.face_right_b64)
    ]
    if images[0] is None:
        camera_status = camera_manager.status()
        camera_captures = camera_manager.face_captures()
        if (
            camera_status.get("studentId") == student_id
            and camera_status.get("purpose") == "register"
            and camera_status.get("completed")
        ):
            images = [
                camera_captures.get("front"),
                camera_captures.get("left"),
                camera_captures.get("right"),
            ]
    if images[0] is None:
        raise HTTPException(
            status_code=400,
            detail="Chua co anh khuon mat. Hay quet qua camera FastAPI truoc.",
        )

    if any(image is None for image in images):
        images = [
            images[0],
            images[1] if images[1] is not None else images[0],
            images[2] if images[2] is not None else images[0],
        ]

    raw_blobs = [encode_jpeg(image) for image in images]
    processed_blobs = [encode_jpeg(process_face(image)) for image in images]
    image_source = "camera" if all(value is None for value in (
        data.face_front_b64,
        data.face_left_b64,
        data.face_right_b64,
    )) else "frontend"

    with closing(connect_db()) as conn:
        try:
            conn.execute(
                """
                INSERT INTO profiles(
                    student_id, full_name, dob, faculty, email, registered_at
                )
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    dob = excluded.dob,
                    faculty = excluded.faculty,
                    email = excluded.email,
                    registered_at = excluded.registered_at,
                    updated_at = datetime('now', 'localtime')
                """,
                (
                    student_id,
                    data.fullName.strip(),
                    data.dob,
                    data.faculty,
                    data.email,
                    data.registeredAt,
                ),
            )
            conn.execute(
                """
                INSERT INTO face_images(
                    student_id, front_image, left_image, right_image, source
                )
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    front_image = excluded.front_image,
                    left_image = excluded.left_image,
                    right_image = excluded.right_image,
                    source = excluded.source,
                    updated_at = datetime('now', 'localtime')
                """,
                (student_id, *raw_blobs, image_source),
            )
            conn.execute(
                """
                INSERT INTO processed_faces(
                    student_id, front_processed, left_processed, right_processed
                )
                VALUES(?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    front_processed = excluded.front_processed,
                    left_processed = excluded.left_processed,
                    right_processed = excluded.right_processed,
                    processing_status = 'ready',
                    processed_at = datetime('now', 'localtime')
                """,
                (student_id, *processed_blobs),
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Loi SQLite: {exc}") from exc

    return {"message": "Dang ky thanh cong", "studentId": student_id}


@app.post("/api/verify-face")
def verify_face(data: VerifyFaceData) -> dict:
    captured = decode_image(data.image)
    return verify_face_image(data.studentId, captured)


def verify_face_image(student_id: str, captured: np.ndarray) -> dict:
    student_id = student_id.strip().upper()

    with closing(connect_db()) as conn:
        row = conn.execute(
            """
            SELECT front_processed, left_processed, right_processed
            FROM processed_faces WHERE student_id = ?
            """,
            (student_id,),
        ).fetchone()
        stored_blobs = list(row) if row else []

    registered_images = [decode_blob(blob) for blob in stored_blobs if blob]
    registered_images = [image for image in registered_images if image is not None]
    if not registered_images:
        raise HTTPException(status_code=404, detail="Sinh vien chua co du lieu khuon mat.")

    scores = [compare_faces(image, captured) for image in registered_images]
    similarity = max(scores)
    fraud_score, reasons = calculate_fraud_score(
        face_sim=similarity, name_match=True
    )
    risk_level, decision = get_risk_level(fraud_score)
    result = {
        "success": decision == "PASS",
        "decision": decision,
        "risk_score": fraud_score,
        "risk_level": risk_level,
        "face_similarity": round(similarity, 4),
        "confidence": get_confidence(similarity),
        "reasons": reasons,
        "all_scores": [round(score, 4) for score in scores],
        "studentId": student_id,
    }
    if decision != "PASS":
        with closing(connect_db()) as conn:
            conn.execute(
                """
                INSERT INTO check_fail(
                    student_id, captured_face, face_similarity, confidence,
                    risk_score, risk_level, reasons
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    encode_jpeg(process_face(captured)),
                    result["face_similarity"],
                    result["confidence"],
                    fraud_score,
                    risk_level,
                    ", ".join(reasons),
                ),
            )
            conn.commit()
    return result


@app.post("/api/face/verify/{student_id}")
def verify_captured_face(student_id: str) -> dict:
    status = camera_manager.status()
    captures = camera_manager.face_captures()
    captured = captures.get("front")
    if (
        status.get("purpose") != "verify"
        or status.get("studentId") != student_id.strip().upper()
        or not status.get("completed")
        or captured is None
    ):
        raise HTTPException(
            status_code=409,
            detail="Chua chup xong khuon mat xac thuc.",
        )
    return verify_face_image(student_id, captured)


@app.post("/api/verify-document")
@app.post("/verify-document")
def verify_document(data: VerifyDocumentData) -> dict:
    student_id = (data.studentId or data.mssv or "").strip().upper()
    if not student_id:
        raise HTTPException(status_code=422, detail="Thieu MSSV.")

    with closing(connect_db()) as conn:
        row = conn.execute(
            "SELECT full_name FROM profiles WHERE student_id = ?", (student_id,)
        ).fetchone()
    if not row:
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "confidence": 0.0,
            "reasons": ["MSSV not found"],
        }

    name_match = (
        not data.name
        or row["full_name"].strip().casefold() == data.name.strip().casefold()
    )
    fraud_score, reasons = calculate_fraud_score(
        face_sim=1.0 if name_match else 0.0,
        name_match=name_match,
    )
    risk_level, decision = get_risk_level(fraud_score)
    return {
        "success": decision == "PASS",
        "decision": decision,
        "risk_score": fraud_score,
        "risk_level": risk_level,
        "confidence": 100.0 if name_match else 0.0,
        "reasons": reasons,
        "studentId": student_id,
    }


@app.post("/verify-face")
def verify_face_legacy(data: VerifyFaceData) -> dict:
    return verify_face(data)


if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        requested = (FRONTEND_DIST / full_path).resolve()
        if requested.is_file() and FRONTEND_DIST in requested.parents:
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
