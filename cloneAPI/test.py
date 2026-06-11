import requests
import json
from mock_embedding import test_cases

BASE_URL = "http://127.0.0.1:8000"

print("=" * 50)
print("Testing SmartFace API")
print("=" * 50)

# HEALTH
print("\n1. HEALTH")

try:
    r = requests.get(f"{BASE_URL}/health")
    print(r.status_code)
    print(r.text)
except Exception as e:
    print(e)

# DOCUMENT
print("\n2. VERIFY DOCUMENT")

try:
    payload = {
        "mssv": "2125110264",
        "name": "Nguyễn Ngô Huy Thịnh"
    }

    r = requests.post(
        f"{BASE_URL}/verify-document",
        json=payload
    )

    print(r.status_code)
    print(r.text)

except Exception as e:
    print(e)

# SAFE
print("\n3. VERIFY FACE SAFE")

try:
    r = requests.post(
        f"{BASE_URL}/verify-face",
        json=test_cases["safe"]
    )

    print(r.status_code)
    print(r.text)

except Exception as e:
    print(e)

# FRAUD
print("\n4. VERIFY FACE FRAUD")

try:
    r = requests.post(
        f"{BASE_URL}/verify-face",
        json=test_cases["fraud"]
    )

    print(r.status_code)
    print(r.text)

except Exception as e:
    print(e)

# NOT FOUND
print("\n5. VERIFY FACE NOT FOUND")

try:
    payload = {
        "mssv": "9999999999",
        "embeddings": test_cases["safe"]["embeddings"]
    }

    r = requests.post(
        f"{BASE_URL}/verify-face",
        json=payload
    )

    print(r.status_code)
    print(r.text)

except Exception as e:
    print(e)

print("\nDONE")
