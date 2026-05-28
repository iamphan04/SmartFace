MOCK_CASES = {
    "safe": {"face_match": {"status": "success", "data": {"match_score": 92}}, "liveness": {"status": "success", "data": {"is_live": True}}, "mask": {"status": "success", "data": {"has_mask": False}}, "embedding": [0.12, -0.55, 0.91] * 170},
    "suspicious": {"face_match": {"status": "success", "data": {"match_score": 68}}, "liveness": {"status": "success", "data": {"is_live": True}}, "mask": {"status": "success", "data": {"has_mask": False}}},
    "fraud_replay": {"face_match": {"status": "success", "data": {"match_score": 85}}, "liveness": {"status": "error", "message": "Replay"}, "mask": {"status": "success", "data": {"has_mask": False}}},
    "fraud_mismatch": {"face_match": {"status": "success", "data": {"match_score": 31}}, "liveness": {"status": "success", "data": {"is_live": True}}, "mask": {"status": "success", "data": {"has_mask": False}}},
    "fraud_mask": {"face_match": {"status": "success", "data": {"match_score": 65}}, "liveness": {"status": "success", "data": {"is_live": True}}, "mask": {"status": "success", "data": {"has_mask": True}}}
}