from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from fraud_engine import calculate_fraud_score, get_risk_level, get_confidence

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DUY_API = "http://localhost:8000"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/verify")
async def verify(data: dict):
    """
    Request:
    {
        "mssv": "2125110264",
        "name": "Nguyễn Ngô Huy Thịnh",
        "image": "base64_image"
    }
    """
    mssv = data.get("mssv")
    name = data.get("name", "")
    image = data.get("image")
    
    if not all([mssv, name, image]):
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "face_similarity": 0.0,
            "confidence": 0.0,
            "reasons": ["Missing mssv, name, or image"]
        }
    
    try:
        user_resp = requests.get(f"{DUY_API}/api/users/{mssv}", timeout=5)
        if user_resp.status_code != 200:
            return {
                "success": False,
                "decision": "FAIL",
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "face_similarity": 0.0,
                "confidence": 0.0,
                "reasons": ["MSSV not found"]
            }
        
        user_data = user_resp.json()
        db_name = user_data.get("fullName", "")
        name_match = db_name.strip().lower() == name.strip().lower()
        
        face_resp = requests.post(
            f"{DUY_API}/api/verify-face",
            json={"studentId": mssv, "image": image},
            timeout=10
        )
        
        if face_resp.status_code != 200:
            face_data = {"success": False, "confidence": 0.0}
        else:
            face_data = face_resp.json()
        
        face_success = face_data.get("success", False)
        face_confidence = face_data.get("confidence", 0.0) / 100.0  # Convert 0-100 to 0-1
        
        fraud_score, reasons = calculate_fraud_score(
            face_sim=face_confidence,
            name_match=name_match
        )
        risk_level, decision = get_risk_level(fraud_score)
        
        return {
            "success": decision == "PASS",
            "decision": decision,
            "risk_score": fraud_score,
            "risk_level": risk_level,
            "face_similarity": round(face_confidence, 4),
            "confidence": get_confidence(face_confidence),
            "reasons": reasons
        }
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "face_similarity": 0.0,
            "confidence": 0.0,
            "reasons": [f"Connection error: {str(e)}"]
        }
    
    except Exception as e:
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "face_similarity": 0.0,
            "confidence": 0.0,
            "reasons": [str(e)]
        }

@app.post("/register")
async def register(data: dict):
    """Forward register request to Duy's API"""
    try:
        resp = requests.post(f"{DUY_API}/api/register", json=data, timeout=10)
        return resp.json()
    except Exception as e:
        return {"success": False, "message": str(e)}