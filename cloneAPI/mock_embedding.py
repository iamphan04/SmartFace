import numpy as np
import json

def generate_mock_embedding(seed=None):
    if seed is not None:
        np.random.seed(int(seed))
    emb = np.random.randn(512).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    return emb.tolist()
MSSV = "2125110264"
DB_EMBEDDING = generate_mock_embedding(seed=42)
REQUEST_EMBEDDINGS_SAFE = [
    generate_mock_embedding(seed=int(42 + i)) for i in range(6)
]
REQUEST_EMBEDDINGS_FRAUD = [
    generate_mock_embedding(seed=int(100 + i)) for i in range(6)
]
test_cases = {
    "safe": {
        "mssv": MSSV,
        "embeddings": REQUEST_EMBEDDINGS_SAFE
    },
    "fraud": {
        "mssv": MSSV,
        "embeddings": REQUEST_EMBEDDINGS_FRAUD
    }
}
if __name__ == "__main__":
    from fraud_engine import cosine_similarity  
    print("=== Mock Embedding Test ===\n")
    scores_safe = [
        cosine_similarity(np.array(DB_EMBEDDING), np.array(e)) 
        for e in REQUEST_EMBEDDINGS_SAFE
    ]
    avg_safe = sum(scores_safe) / len(scores_safe)
    print(f"SAFE case:")
    print(f"  Scores: {[f'{s:.4f}' for s in scores_safe]}")
    print(f"  Avg: {avg_safe:.4f}")
    print(f"  Decision: {'PASS' if avg_safe >= 0.7 else 'FAIL'}\n")
    scores_fraud = [
        cosine_similarity(np.array(DB_EMBEDDING), np.array(e)) 
        for e in REQUEST_EMBEDDINGS_FRAUD
    ]
    avg_fraud = sum(scores_fraud) / len(scores_fraud)
    print(f"FRAUD case:")
    print(f"  Scores: {[f'{s:.4f}' for s in scores_fraud]}")
    print(f"  Avg: {avg_fraud:.4f}")
    print(f"  Decision: {'PASS' if avg_fraud >= 0.7 else 'FAIL'}\n")
    print("✅ Data ready for API testing")