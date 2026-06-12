import requests
import json

BASE_URL = "http://127.0.0.1:8001"

print("=" * 50)
print("Testing SmartFace Fraud Engine API")
print("=" * 50)

# 1. HEALTH
print("\n1. HEALTH")
try:
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# 2. VERIFY - PASS case
print("\n2. VERIFY - PASS (Valid MSSV, Name Match)")
try:
    payload = {
        "mssv": "2125110264",
        "name": "Nguyễn Ngô Huy Thịnh",
        "image": "fake_base64_image_data"
    }
    r = requests.post(f"{BASE_URL}/verify", json=payload)
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# 3. VERIFY - FAIL case (Name mismatch)
print("\n3. VERIFY - FAIL (Name Mismatch)")
try:
    payload = {
        "mssv": "2125110264",
        "name": "Tên Sai",
        "image": "fake_base64_image_data"
    }
    r = requests.post(f"{BASE_URL}/verify", json=payload)
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# 4. VERIFY - NOT FOUND
print("\n4. VERIFY - NOT FOUND (Invalid MSSV)")
try:
    payload = {
        "mssv": "9999999999",
        "name": "Test",
        "image": "fake_base64_image_data"
    }
    r = requests.post(f"{BASE_URL}/verify", json=payload)
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# 5. VERIFY - Missing data
print("\n5. VERIFY - MISSING DATA")
try:
    payload = {
        "mssv": "2125110264"
        # missing name, image
    }
    r = requests.post(f"{BASE_URL}/verify", json=payload)
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 50)
print("DONE")
print("=" * 50)