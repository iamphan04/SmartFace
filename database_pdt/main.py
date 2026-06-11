import os
import sqlite3
import base64
import numpy as np
import cv2
from fastapi import FastAPI, HTTPException  
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "System.db")

def decode_base64_to_cv2(b64_string: str) -> np.ndarray:
    """Giải mã chuỗi base64 nhận từ frontend thành định dạng ảnh OpenCV (BGR)."""
    try:
        if "," in b64_string:
            b64_string = b64_string.split(",")[1]
        img_data = base64.b64decode(b64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img_bgr
    except Exception as e:
        raise ValueError(f"Lỗi giải mã ảnh Base64: {e}")

def compare_faces_fallback(img1: np.ndarray, img2: np.ndarray) -> tuple:
    """
    Thuật toán so sánh dự phòng (Fallback) bằng OpenCV Histogram nếu không gọi được pdt_face.
    Trả về: (is_match: bool, confidence: float)
    """
    try:
        hsv_1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
        hsv_2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
        
        hist_1 = cv2.calcHist([hsv_1], [0, 1], None, [50, 60], [0, 180, 0, 256])
        hist_2 = cv2.calcHist([hsv_2], [0, 1], None, [50, 60], [0, 180, 0, 256])
        
        cv2.normalize(hist_1, hist_1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist_2, hist_2, 0, 1, cv2.NORM_MINMAX)
        
        metric = cv2.compareHist(hist_1, hist_2, cv2.HISTCMP_CORREL)
        confidence = float(max(0, metric) * 100)
        
        is_match = confidence > 60.0
        return is_match, confidence
    except Exception:
        return False, 0.0

class RegisterData(BaseModel):
    studentId:    str
    fullName:     str
    dob:          str
    faculty:      Optional[str] = ""
    email:        Optional[str] = ""
    registeredAt: Optional[str] = ""
    face_front_b64: Optional[str] = None

class VerifyFaceData(BaseModel):
    studentId: str
    image: str  

@app.get("/api/users/{student_id}")
def get_user_from_db(student_id: str):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Cơ sở dữ liệu SQLite chưa được khởi tạo.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        try:
            row = cursor.execute("SELECT id, name FROM persons WHERE id = ?", (student_id,)).fetchone()
            if row:
                return {
                    "studentId": row[0],
                    "fullName": row[1],
                    "dob": "15/10/2004",  
                    "faculty": "Công nghệ thông tin",
                    "email": f"{row[0].lower()}@student.edu.vn",
                    "registeredAt": "Database Nội Bộ"
                }
        except Exception:
            pass
            
        try:
            row_user = cursor.execute("SELECT studentId, fullName, dob, faculty, email, registeredAt FROM users WHERE studentId = ?", (student_id,)).fetchone()
            if row_user:
                return {
                    "studentId": row_user[0],
                    "fullName": row_user[1],
                    "dob": row_user[2],
                    "faculty": row_user[3],
                    "email": row_user[4],
                    "registeredAt": row_user[5]
                }
        except Exception:
            pass

        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên ứng với MSSV này trong SQLite.")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn hệ thống: {str(e)}")
    finally:
        conn.close()


@app.post("/api/register")
def register_user(data: RegisterData):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=400, detail=f"Không tìm thấy file database tại: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO persons (id, name)
            VALUES (?, ?)
        """, (data.studentId, data.fullName))
        
        if data.face_front_b64:
            try:
                img_front = decode_base64_to_cv2(data.face_front_b64)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Lỗi xử lý hình ảnh: {str(e)}")

            if img_front is not None:
                success, buffer = cv2.imencode('.jpg', img_front, [cv2.IMWRITE_JPEG_QUALITY, 95])
                if success:
                    conn.execute("""
                        INSERT OR REPLACE INTO person_id (person_id, face_embedding, update_at, created_at)
                        VALUES (?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                    """, (data.studentId, buffer.tobytes()))
                else:
                    raise HTTPException(status_code=500, detail="Không thể nén ảnh sang định dạng JPEG.")
            else:
                raise HTTPException(status_code=400, detail="Ảnh chính diện không hợp lệ.")

        conn.commit()
        return {
            "message": "Đăng ký thành công", 
            "studentId": data.studentId
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi ghi SQLite: {str(e)}")
    finally:
        conn.close()

@app.post("/api/verify-face")
def verify_face(data: VerifyFaceData):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Cơ sở dữ liệu không tồn tại.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        row = cursor.execute("SELECT face_embedding FROM person_id WHERE person_id = ?", (data.studentId,)).fetchone()
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="Sinh viên này chưa đăng ký dữ liệu khuôn mặt.")

        reg_face_bytes = row[0]
        
        nparr = np.frombuffer(reg_face_bytes, np.uint8)
        img_registered = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        try:
            img_captured = decode_base64_to_cv2(data.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Lỗi giải mã ảnh từ camera gửi lên: {str(e)}")

        if img_registered is None or img_captured is None:
            raise HTTPException(status_code=400, detail="Dữ liệu hình ảnh bị lỗi không thể giải nén.")

        success = False
        confidence = 0.0

        try:
            import pdt_face
            
            if hasattr(pdt_face, "verify_faces"):
                success, confidence = pdt_face.verify_faces(img_registered, img_captured)
            elif hasattr(pdt_face, "compare_faces"):
                success, confidence = pdt_face.compare_faces(img_registered, img_captured)
            else:
                success, confidence = compare_faces_fallback(img_registered, img_captured)
        except Exception as e:
            print(f"[Cảnh báo] Không thể chạy pdt_face.py, chuyển sang thuật toán dự phòng: {e}")
            success, confidence = compare_faces_fallback(img_registered, img_captured)

        return {
            "success": success,
            "confidence": confidence,
            "studentId": data.studentId
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý đối sánh: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    print(f"Đang chạy API Server kết nối tới Database: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)