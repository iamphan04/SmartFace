from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import numpy as np
from fraud_engine import cosine_similarity, calculate_fraud_score, get_risk_level, get_confidence

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DB_PATH = "System.db"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/verify-document")
async def verify_document(data: dict):
    mssv = data.get("mssv")
    name = data.get("name", "")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM persons WHERE id = ?", (mssv,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {
                "success": False,
                "decision": "FAIL",
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "face_similarity": 0.0,
                "confidence": 0.0,
                "reasons": ["MSSV not found"]
            }
        
        db_name = row[0]
        name_match = db_name.strip().lower() == name.strip().lower()
        fraud_score, reasons = calculate_fraud_score(face_sim=1.0 if name_match else 0, name_match=name_match)
        risk_level, decision = get_risk_level(fraud_score)
        
        return {
            "success": name_match,
            "decision": decision,
            "risk_score": fraud_score,
            "risk_level": risk_level,
            "face_similarity": 1.0 if name_match else 0.0,
            "confidence": 100.0 if name_match else 0.0,
            "reasons": reasons
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

@app.post("/verify-face")
async def verify_face(data: dict):
    mssv = data.get("mssv")
    embeddings = data.get("embeddings")
    
    if not embeddings:
        return {
            "success": False,
            "decision": "FAIL",
            "risk_score": 100,
            "risk_level": "CRITICAL",
            "face_similarity": 0.0,
            "confidence": 0.0,
            "reasons": ["No embeddings provided"]
        }
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT face_embedding FROM person_id WHERE person_id = ?", (mssv,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return {
                "success": False,
                "decision": "FAIL",
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "face_similarity": 0.0,
                "confidence": 0.0,
                "reasons": ["MSSV not found"]
            }
        
        emb_data = row[0]
        
        # Try binary blob first (from DB)
        try:
            db_embedding = np.frombuffer(emb_data, dtype=np.float32)
        except:
            # Fallback: try JSON/list format
            try:
                import json
                if isinstance(emb_data, bytes):
                    emb_data = emb_data.decode('utf-8')
                db_embedding = np.array(json.loads(emb_data), dtype=np.float32)
            except:
                # Last resort: assume it's already a list-like
                try:
                    db_embedding = np.array(emb_data, dtype=np.float32)
                except:
                    return {
                        "success": False,
                        "decision": "FAIL",
                        "risk_score": 100,
                        "risk_level": "CRITICAL",
                        "face_similarity": 0.0,
                        "confidence": 0.0,
                        "reasons": ["Invalid embedding format in DB"]
                    }
        
        # Ensure embedding is normalized
        if len(db_embedding) == 0:
            raise ValueError("Empty embedding")
        
        scores = []
        for emb in embeddings:
            # Handle embedding as list or array
            if isinstance(emb, (list, tuple)):
                emb = np.array(emb, dtype=np.float32)
            else:
                emb = np.array(emb, dtype=np.float32)
            
            if len(emb) != len(db_embedding):
                continue
            
            score = cosine_similarity(db_embedding, emb)
            scores.append(float(score))
        
        if not scores:
            return {
                "success": False,
                "decision": "FAIL",
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "face_similarity": 0.0,
                "confidence": 0.0,
                "reasons": ["Embedding dimension mismatch"]
            }
        
        avg_similarity = sum(scores) / len(scores)
        fraud_score, reasons = calculate_fraud_score(face_sim=avg_similarity, name_match=True)
        risk_level, decision = get_risk_level(fraud_score)
        confidence = get_confidence(avg_similarity)
        
        return {
            "success": decision == "PASS",
            "decision": decision,
            "risk_score": fraud_score,
            "risk_level": risk_level,
            "face_similarity": round(avg_similarity, 4),
            "confidence": confidence,
            "reasons": reasons,
            "all_scores": [round(s, 4) for s in scores]
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