import sqlite3
from pathlib import Path

import cv2
<<<<<<< HEAD
from pathlib import Path

DB_PATH = Path(__file__).with_name("System.db")
=======
import numpy as np

DB_PATH = Path(__file__).resolve().parent / "System.db"
>>>>>>> f73ef4913553fc54f4f51ec4df51ed6766b9833c


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    with connect() as conn:
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
                source TEXT NOT NULL DEFAULT 'camera',
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY(student_id) REFERENCES profiles(student_id) ON DELETE CASCADE
            );
<<<<<<< HEAD
        """)
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(face_images)").fetchall()
        }
        if "face_data_left" not in columns:
            conn.execute("ALTER TABLE face_images ADD COLUMN face_data_left BLOB")
        if "face_data_right" not in columns:
            conn.execute("ALTER TABLE face_images ADD COLUMN face_data_right BLOB")
=======

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

>>>>>>> f73ef4913553fc54f4f51ec4df51ed6766b9833c

def add_person(person_id: str, name: str) -> bool:
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO profiles(student_id, full_name) VALUES(?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    updated_at = datetime('now', 'localtime')
                """,
                (person_id.strip().upper(), name.strip()),
            )
        return True
    except sqlite3.Error as exc:
        print(f"Loi add_person: {exc}")
        return False


def get_person(person_id: str):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM profiles WHERE student_id = ?",
            (person_id.strip().upper(),),
        ).fetchone()


def person_exists(person_id: str) -> bool:
    return get_person(person_id) is not None


def encode_jpeg(image: np.ndarray) -> bytes:
    success, buffer = cv2.imencode(
        ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92]
    )
    if not success:
        raise ValueError("Khong encode duoc anh.")
    return buffer.tobytes()


def process_face(image: np.ndarray) -> np.ndarray:
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(gray)


def save_face(
    person_id: str,
    face_bgr: np.ndarray,
    face_bgr_left: np.ndarray,
    face_bgr_right: np.ndarray,
) -> bool:
    student_id = person_id.strip().upper()
    if not person_exists(student_id):
        return False

    raw = [
        encode_jpeg(face_bgr),
        encode_jpeg(face_bgr_left),
        encode_jpeg(face_bgr_right),
    ]
    processed = [
        encode_jpeg(process_face(face_bgr)),
        encode_jpeg(process_face(face_bgr_left)),
        encode_jpeg(process_face(face_bgr_right)),
    ]
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO face_images(
                    student_id, front_image, left_image, right_image, source
                )
                VALUES(?, ?, ?, ?, 'camera')
                ON CONFLICT(student_id) DO UPDATE SET
                    front_image = excluded.front_image,
                    left_image = excluded.left_image,
                    right_image = excluded.right_image,
                    source = 'camera',
                    updated_at = datetime('now', 'localtime')
                """,
                (student_id, *raw),
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
                (student_id, *processed),
            )
        return True
    except sqlite3.Error as exc:
        print(f"Loi save_face: {exc}")
        return False


def get_face(person_id: str) -> np.ndarray | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT front_processed FROM processed_faces WHERE student_id = ?",
            (person_id.strip().upper(),),
        ).fetchone()
<<<<<<< HEAD
    if row:
        arr = np.frombuffer(row[0], dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return None
=======
    if not row:
        return None
    return cv2.imdecode(np.frombuffer(row[0], np.uint8), cv2.IMREAD_GRAYSCALE)
>>>>>>> f73ef4913553fc54f4f51ec4df51ed6766b9833c
