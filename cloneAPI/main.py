import os

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fraud_engine import calculate_fraud_score, get_confidence, get_risk_level

SMARTFACE_API = os.getenv("SMARTFACE_API_URL", "http://127.0.0.1:8001")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "upstream": SMARTFACE_API}


@app.post("/verify")
async def verify(data: dict):
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
            "reasons": ["Missing mssv, name, or image"],
        }

    try:
        user_resp = requests.get(f"{SMARTFACE_API}/api/users/{mssv}", timeout=5)
        if user_resp.status_code != 200:
            return {
                "success": False,
                "decision": "FAIL",
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "face_similarity": 0.0,
                "confidence": 0.0,
                "reasons": ["MSSV not found"],
            }

        user_data = user_resp.json()
        db_name = user_data.get("fullName", "")
        name_match = db_name.strip().lower() == name.strip().lower()

        face_resp = requests.post(
            f"{SMARTFACE_API}/api/verify-face",
            json={"studentId": mssv, "image": image},
            timeout=10,
        )
        face_data = (
            {"success": False, "confidence": 0.0}
            if face_resp.status_code != 200
            else face_resp.json()
        )
        face_confidence = face_data.get("confidence", 0.0) / 100.0

        fraud_score, reasons = calculate_fraud_score(
            face_sim=face_confidence,
            name_match=name_match,
        )
        risk_level, decision = get_risk_level(fraud_score)

        return {
            "success": decision == "PASS",
            "decision": decision,
            "risk_score": fraud_score,
            "risk_level": risk_level,
            "face_similarity": round(face_confidence, 4),
            "confidence": get_confidence(face_confidence),
            "reasons": reasons,
        }

    except requests.exceptions.RequestException as exc:
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "face_similarity": 0.0,
            "confidence": 0.0,
            "reasons": [f"Connection error: {exc}"],
        }
    except Exception as exc:
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "face_similarity": 0.0,
            "confidence": 0.0,
            "reasons": [str(exc)],
        }


@app.post("/register")
async def register(data: dict):
    try:
        resp = requests.post(f"{SMARTFACE_API}/api/register", json=data, timeout=10)
        return resp.json()
    except Exception as exc:
        return {"success": False, "message": str(exc)}
