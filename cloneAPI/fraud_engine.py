def calculate_trust_score(data):
    risk = 0
    face_score = data.get('face_match', {}).get('data', {}).get('match_score', 0)
    if face_score < 75: risk += 40
    elif face_score < 85: risk += 20
    
    is_live = data.get('liveness', {}).get('data', {}).get('is_live', False)
    if not is_live: risk += 60
    
    has_mask = data.get('mask', {}).get('data', {}).get('has_mask', False)
    if has_mask: risk += 20
    
    return max(0, min(100, 100 - risk))

def get_decision(score):
    if score >= 70: return "PASS", "✅", "SAFE"
    elif score >= 40: return "FAIL", "⚠️", "SUSPICIOUS"
    else: return "FAIL", "🚨", "HIGH RISK"

def get_reasons(data):
    reasons = []
    face = data.get('face_match', {}).get('data', {}).get('match_score', 0)
    if face < 75: reasons.append(f"Low similarity: {face}%")
    if not data.get('liveness', {}).get('data', {}).get('is_live', False): reasons.append("No liveness")
    if data.get('mask', {}).get('data', {}).get('has_mask', False): reasons.append("Mask detected")
    return reasons