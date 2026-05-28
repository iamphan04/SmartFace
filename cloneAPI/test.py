import requests

data = {
    "mssv": "2125110264",
    "name": "Nguyễn Ngô Huy Thịnh",
    "dob": "2005-01-01",
    "doc_image": "base64_image_here"
}

# Test verify-document
response = requests.post('http://localhost:8000/verify-document', json=data)
print("Document:", response.json())

# Test verify-face (với 6 ảnh)
face_data = {
    "mssv": "2125110264",
    "images": ["img1_base64", "img2_base64", ...]
}
response = requests.post('http://localhost:8000/verify-face', json=face_data)
print("Face:", response.json())

# Test health
response = requests.get('http://localhost:8000/health')
print("Health:", response.json())