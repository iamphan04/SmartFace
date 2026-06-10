import sqlite3
import numpy as np
import cv2

DB_PATH = "System.db"

def init_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS persons(
                id         TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS face_images(
                person_id  TEXT PRIMARY KEY,
                face_data  BLOB NOT NULL,
                face_data_left BLOB NOT NULL, 
                face_data_right BLOB NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE CASCADE
            );
        """)

def add_person(person_id: str, name: str) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO persons(id, name) VALUES(?, ?)",
                (person_id, name)
            )
        return True
    except sqlite3.Error as e:
        print(f"Lỗi add_person: {e}")
        return False

def get_person(person_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT * FROM persons WHERE id = ?", (person_id,)
        ).fetchone()

def person_exists(person_id: str) -> bool:
    return get_person(person_id) is not None

def save_face(person_id: str, face_bgr: np.ndarray, face_bgr_left: np.ndarray, face_bgr_right: np.ndarray ) -> bool:
    """Nhận ảnh BGR numpy array, nén JPEG rồi lưu vào DB."""
    
    success, buffer = cv2.imencode('.jpg', face_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success:
        print("Lỗi: không encode được ảnh.")
        return False
    success_left, buffer_left = cv2.imencode('.jpg', face_bgr_left, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success_left:
        print("Lỗi: không encode được ảnh trái.")
        return False
    success_right, buffer_right = cv2.imencode('.jpg', face_bgr_right, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success_right:
        print("Lỗi: không encode được ảnh phải.")
        return False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO face_images(person_id, face_data, face_data_left, face_data_right)
                VALUES(?, ?, ?, ?)
            """, (person_id, buffer.tobytes(), buffer_left.tobytes(), buffer_right.tobytes()))
        return True
    except sqlite3.Error as e:
        print(f"Lỗi save_face: {e}")
        return False

def get_face(person_id: str) -> np.ndarray | None:
    """Trả về ảnh BGR numpy array hoặc None."""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT face_data FROM face_images WHERE person_id = ?", (person_id,)
        ).fetchone()
    if row:
        arr = np.frombuffer(row[0], dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return None