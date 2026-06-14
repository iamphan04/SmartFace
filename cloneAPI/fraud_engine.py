import numpy as np
from numpy.linalg import norm

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (norm(v1) * norm(v2) + 1e-8)

def calculate_fraud_score(face_sim=None, name_match=True):
    """Tính fraud score (0-100)"""
    score = 0
    reasons = []
    
    if face_sim is None or face_sim < 0.7:
        sim_str = f"{face_sim:.2f}" if face_sim is not None else "0.00"
        score += 60
        reasons.append(f"Face mismatch: {sim_str}")
    
    if not name_match:
        score += 40
        reasons.append("Name mismatch")
    
    return min(100, score), reasons

def get_risk_level(fraud_score):
    """fraud_score → (risk_level, decision)"""
    if fraud_score <= 20:
        return "LOW", "PASS"
    elif fraud_score <= 50:
        return "MEDIUM", "PASS"
    elif fraud_score <= 70:
        return "HIGH", "FAIL"
    else:
        return "CRITICAL", "FAIL"

def get_confidence(face_sim):
    """face_sim → confidence% (0-100)"""
    if face_sim is None:
        return 0.0
    return round(min(100, face_sim * 100), 1)