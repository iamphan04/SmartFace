import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os
import database
import numpy as np
import time

MODEL_PATH = 'face_landmarker.task'
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

star_time = time.time() 
def download_model():
    if not os.path.exists(MODEL_PATH):
        print("Đang tải model AI...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Tải xong!")

def build_detector():
    opts = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1
    )
    return vision.FaceLandmarker.create_from_options(opts)

def get_face_bbox(landmarks, w, h, padding=30):
    xs = [int(lm.x * w) for lm in landmarks]
    ys = [int(lm.y * h) for lm in landmarks]
    return (
        max(0, min(xs) - padding),
        max(0, min(ys) - padding),
        min(w, max(xs) + padding),
        min(h, max(ys) + padding)
    )
def m_eye(lms, h, w)->bool:
    # mat phai mi tren 
    x_right_max = int(lms[159].x*w)
    y_right_max= int(lms[159].y*h)
    # mat phai mi duoi 
    x_right_min = int(lms[145].x*w)
    y_right_min = int(lms[145].y*h)
    # mat trai mi tren
    x_left_max = int(lms[386].x*w)
    y_left_max = int(lms[386].y*h)
    #mat trai mi duoi 
    x_left_min = int(lms[374].x*w)
    y_left_min = int(lms[374].y*h)
    # nham mat trai
    close_eye_left = np.hypot((x_left_max - x_left_min), (y_left_max - y_left_min))
    # nham mat phai
    close_eye_right = np.hypot((x_right_max - x_right_min), (y_right_max-y_right_min))

    if close_eye_left < 10 and close_eye_right < 10:
        return True
    return False

time_talk = None
def save_true(face_crop, h, w, person_id):
    database.save_face(person_id, face_crop)
    print(f"Đã lưu khuôn mặt cho ID: {person_id}")
                # Hiển thị ảnh vừa chụp + thông báo
    confirm = np.zeros((h, w, 3), dtype=np.uint8)
                # Hiển thị ảnh khuôn mặt vừa lưu ở giữa màn hình
    fh, fw = face_crop.shape[:2]
    scale = min(300/fh, 300/fw)
    face_resized = cv2.resize(face_crop, (int(fw*scale), int(fh*scale)))
    fh2, fw2 = face_resized.shape[:2]
    y_offset = h//2 - fh2//2 - 30
    x_offset = w//2 - fw2//2
    confirm[y_offset:y_offset+fh2, x_offset:x_offset+fw2] = face_resized
                
                # Khung viền xanh quanh ảnh
    cv2.rectangle(confirm, (x_offset-2, y_offset-2),
                    (x_offset+fw2+2, y_offset+fh2+2), (0, 255, 0), 2)
                
                # Chữ thông báo
    cv2.putText(confirm, "LUU THANH CONG!", (w//2 - 130, y_offset + fh2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.putText(confirm, f"ID: {person_id}", (w//2 - 100, y_offset + fh2 + 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(confirm, "Cua so se tu dong dong sau 3 giay...", (w//2 - 210, y_offset + fh2 + 125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
    cv2.imshow("chup khuon mat", confirm)
    cv2.waitKey(1)
    time.sleep(10)
    return 

def main():
    database.init_database()
    global star_talk

    person_id = input("Nhập mã người dùng: ").strip()
    if not database.person_exists(person_id):
        print("Không tìm thấy! Hãy chạy qr_scan.py trước.")
        return

    download_model()
    detector = build_detector()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Không mở được camera!")
        return

    print("SPACE = chụp | Q = thoát")
    face_crop = None
    face_right = None
    face_left = None
    lms =None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_img)
        face_crop = None

        if result.face_landmarks:
            lms = result.face_landmarks[0]
            x1, y1, x2, y2 = get_face_bbox(lms, w, h)
            face_crop = frame[y1:y2, x1:x2].copy()

            # Vẽ landmarks
            for lm in lms:
                cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 1, (0, 255, 0), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # HUD
        cv2.rectangle(frame, (0, 0), (w, 70), (0, 0, 0), -1)
        cv2.putText(frame, f"ID: {person_id}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        status = "Nhấn SPACE để chụp" if face_crop is not None else "Chưa thấy mặt!"
        color  = (0, 255, 0)        if face_crop is not None else (0, 0, 255)
        cv2.putText(frame, status, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("chup khuon mat", frame)
        key = cv2.waitKey(1) & 0xFF

        if lms is not None and m_eye(lms, h, w): 
            if time_talk is None:
                time_talk= time.time()
             # SPACE

            star_talk = time.time()- time_talk
            if star_talk >=3:
                if face_crop is  not None:
                    save_true(face_crop, h, w, person_id)
                    break
        else :
            time_talk = None
            


    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()