from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import base64
import cv2
import numpy as np
from PIL import Image
from io import BytesIO

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DB_PATH = "System.db"

@app.post("/verify-document")
async def verify_document(data: dict):
    mssv = data.get('mssv')
    name = data.get('name')
    dob = data.get('dob')
    doc_image = data.get('doc_image')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, dob, img_id FROM person_id WHERE person_id = ?", (mssv,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"success": False, "decision": "FAIL", "reason": "MSSV not found"}
    
    db_name, db_dob, db_doc_img = row
    
    # So sánh thông tin text
    name_match = db_name.lower().strip() == name.lower().strip()
    dob_match = db_dob == dob
    
    if not (name_match and dob_match):
        return {"success": False, "decision": "FAIL", "reason": "Info mismatch"}
    
    # So sánh ảnh giấy tờ
    if doc_image and db_doc_img:
        doc_score = compare_images(db_doc_img, doc_image)
        if doc_score < 0.6:
            return {"success": False, "decision": "FAIL", "reason": "Document image mismatch"}
    
    return {"success": True, "decision": "PASS"}

@app.post("/verify-face")
async def verify_face(data: dict):
    mssv = data.get('mssv')
    images = data.get('images')  # 6 ảnh từ DUY
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT img_id FROM person_id WHERE person_id = ?", (mssv,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return {"success": False, "decision": "FAIL"}
    
    db_img = row[0]
    scores = []
    
    # So sánh 6 ảnh với ảnh trong DB
    for img_base64 in images:
        score = compare_images(db_img, img_base64)
        scores.append(score)
    
    avg_score = sum(scores) / len(scores) if scores else 0
    decision = "PASS" if avg_score >= 0.7 else "FAIL"
    
    return {"success": True, "decision": decision, "score": avg_score, "all_scores": scores}

def compare_images(img1, img2):
    im1 = decode_image(img1)
    im2 = decode_image(img2)
    
    # Resize về cùng kích thước
    h, w = im1.shape[:2]
    im2 = cv2.resize(im2, (w, h))
    
    # So sánh bằng histogram
    hist1 = cv2.calcHist([im1], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
    hist2 = cv2.calcHist([im2], [0, 1, 2], None, [256, 256, 256], [0, 256, 0, 256, 0, 256])
    
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)
    
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_BHATTACHARYYA)
    return 1 - similarity  # 0-1, càng cao càng giống

def decode_image(data):
    if isinstance(data, str):
        data = base64.b64decode(data)
    img = Image.open(BytesIO(data))
    return np.array(img)

@app.get("/health")
async def health():
    return {"status": "ok"}