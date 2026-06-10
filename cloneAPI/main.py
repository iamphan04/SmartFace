from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import numpy as np
from fraud_engine import cosine_similarity

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "System.db"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/verify-document")
async def verify_document(data: dict):
    mssv = data.get("mssv")
    name = data.get("name", "")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM persons WHERE id = ?",
        (mssv,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "success": False,
            "decision": "FAIL",
            "reason": "MSSV not found"
        }

    db_name = row[0]

    if db_name.strip().lower() != name.strip().lower():
        return {
            "success": False,
            "decision": "FAIL",
            "reason": "Name mismatch"
        }

    return {
        "success": True,
        "decision": "PASS"
    }


@app.post("/verify-face")
async def verify_face(data: dict):
    mssv = data.get("mssv")
    embeddings = data.get("embeddings")

    if not embeddings:
        return {
            "success": False,
            "decision": "FAIL",
            "reason": "No embeddings provided"
        }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT face_embedding FROM person_id WHERE person_id = ?",
        (mssv,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "success": False,
            "decision": "FAIL",
            "reason": "MSSV not found"
        }

    try:
        print("TYPE",type(row[0]))
        print("LEN:", len(row[0]))
        
        if isinstance(row[0], bytes):
            print("FIRST 100 BYTES:", row[0][:100])
        else:
            print("VALUE:", str(row[0])[:300])
            
        db_embedding = np.frombuffer(
            row[0],
            dtype=np.float32
        )
        scores = []

        for emb in embeddings:
            emb = np.array(emb, dtype=np.float32)

            score = cosine_similarity(
                db_embedding,
                emb
            )

            scores.append(float(score))

        avg_score = sum(scores) / len(scores)

        return {
            "success": True,
            "decision": "PASS" if avg_score >= 0.7 else "FAIL",
            "avg_score": avg_score,
            "all_scores": scores
        }

    except Exception as e:
        return {
            "success": False,
            "decision": "FAIL",
            "reason": str(e)
        }
