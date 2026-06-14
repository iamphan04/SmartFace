## Cài đặt
### 1. Cài dependencies
pip install -r requirements.txt
### 2. Chạy server
python -m uvicorn main:app --reload --port 8001
Server chạy tại: `http://127.0.0.1:8001`
**Lưu ý:** Duy phải chạy trước (port 8000)
## API Endpoints
### 1. Health Check
GET /health
Response:
json
{"status": "ok"}
### 2. Verify (Main endpoint)
POST /verify
Request:
json
{
  "mssv": "2125110264",
  "name": "Nguyễn Ngô Huy Thịnh",
  "image": "base64_encoded_image"
}
Response:
json
{
  "success": true,
  "decision": "PASS",
  "risk_score": 15,
  "risk_level": "LOW",
  "face_similarity": 0.92,
  "confidence": 92.0,
  "reasons": []
}
**Risk Levels:**
- `LOW` (0-20): PASS - Safe
- `MEDIUM` (21-50): PASS - Acceptable
- `HIGH` (51-70): FAIL - Risky
- `CRITICAL` (71-100): FAIL - Block
### 3. Register (Forward to Duy)
POST /register
Request:
json
{
  "studentId": "2125110264",
  "fullName": "Nguyễn Ngô Huy Thịnh",
  "dob": "2005-01-01",
  "face_front_b64": "base64_image"
}
## Testing
bash
python test.py
## Architecture
Frontend
    ↓
SmartFace Fraud Engine - Port 8001
    ↓
Database & Face Verification- Port 8000
    ↓
System.db
## Fraud Score Logic
- Face mismatch (< 0.7 similarity): +60
- Name mismatch: +40
- Max score: 100

Decision based on fraud_score:
- ≤ 20: PASS (LOW risk)
- 21-50: PASS (MEDIUM risk)
- 51-70: FAIL (HIGH risk)
- 71-100: FAIL (CRITICAL risk)