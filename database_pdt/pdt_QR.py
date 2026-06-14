import cv2
import numpy as np
from pyzbar import pyzbar

import database


class QRScanner:
    """Decode QR data from frames supplied by CameraManager."""

<<<<<<< HEAD
# Các biến quản lý trạng thái thông báo
status_text = "Hay quet QR code..."
status_color = (255, 255, 255) # Mặc định màu trắng
text_display_expiry = 0        # Thời gian hết hạn của thông báo ngắn hạn
save_QR = False 
talk_time = None
img_card = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Không thể kết nối với camera.")
        break
    frame = cv2.flip(frame, 1)
    current_time = time.time() 
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0) # Sử dụng ma trận lọc 3x3 để làm mịn nhẹ
    
    # Đọc QR code từ camera
    barcodes = pyzbar.decode(blurred)
    
    for barcode in barcodes:
        if not save_QR:
            save_QR = True 
            talk_time = current_time
        raw = barcode.data.decode("utf-8")
        
        # Vẽ khung vuông màu xanh lá quanh mã QR đang quét
        rect = barcode.rect
        cv2.rectangle(frame, 
                      (rect.left, rect.top), 
                      (rect.left + rect.width, rect.top + rect.height), 
                      (0, 255, 0), 2)  
        
        # Nếu là mã trùng với mã vừa quét xong thì bỏ qua không xử lý lại
        if raw == last_scanned:
            continue
            
        # Phát hiện mã mới! Tiến hành xử lý
        last_scanned = raw
        
        if database.person_exists(raw):
            status_text = "Thong tin: Da ton tai!"
            status_color = (0, 0, 255) # Màu đỏ cảnh báo
        else:
            name = raw
            database.add_person(raw, name)
            status_text = f"Da quet xong! Da luu: {raw}"
            status_color = (0, 255, 0) # Màu xanh lá thành công
            
        # Đặt thời gian hiển thị thông báo này trong 3 giây
        text_display_expiry = current_time + 3.0

    # LOGIC ĐỔI CHỮ: Nếu hết 3 giây mà không có QR mới, quay về chữ mặc định
    if current_time > text_display_expiry and not save_QR:
        status_text = "Hay quet QR code..."
        status_color = (255, 255, 255) # Quay về màu trắng
        last_scanned = None             # Reset bộ lọc để có thể quét lại chính mã đó nếu muốn

    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (0, 0, 0), -1)

    # HIỂN THỊ CHỮ LÊN MÀN HÌNH
    # Tọa độ (20, 32) là vị trí xuất hiện của chữ (X=20, Y=32)
    cv2.putText(frame, status_text, (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    
    if save_QR :
        star_time = int(current_time - talk_time)
        status_text = f"thoi gian chup the {star_time}"
        cv2.putText(frame,status_text, (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        if star_time >= 5 :
            img_card = frame.copy()
            status_text = f"luu anh the {raw} thanh cong"
            database.save_img_card(raw, img_card)
            cv2.putText(frame,status_text, (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            cv2.waitKey(3000)

            
    cv2.imshow("He thong quet QR", frame)
    
    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
=======
    def __init__(self):
        self.cv_detector = cv2.QRCodeDetector()
        self.reset()

    def reset(self) -> None:
        self.completed = False
        self.value = ""
        self.message = "Dua ma QR vao khung camera"
        self.error = ""

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        value = ""

        try:
            results = pyzbar.decode(frame)
            if results:
                result = results[0]
                value = result.data.decode("utf-8").strip()
                rect = result.rect
                cv2.rectangle(
                    display,
                    (rect.left, rect.top),
                    (rect.left + rect.width, rect.top + rect.height),
                    (0, 255, 120),
                    3,
                )
        except Exception as exc:
            self.error = str(exc)

        if not value:
            try:
                value, points, _ = self.cv_detector.detectAndDecode(frame)
                value = value.strip()
                if points is not None and len(points):
                    polygon = points.astype(int).reshape(-1, 2)
                    cv2.polylines(display, [polygon], True, (0, 255, 120), 3)
            except Exception as exc:
                self.error = str(exc)

        if value and not self.completed:
            self.value = value
            self.completed = True
            self.message = f"Da quet QR: {value}"
>>>>>>> f73ef4913553fc54f4f51ec4df51ed6766b9833c

        cv2.rectangle(display, (0, 0), (display.shape[1], 58), (8, 15, 30), -1)
        cv2.putText(
            display,
            self.message,
            (16, 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (0, 255, 120) if self.completed else (240, 240, 240),
            2,
        )
        return display

    def status(self) -> dict:
        return {
            "running": not self.completed and not self.error,
            "completed": self.completed,
            "value": self.value,
            "message": self.message,
            "error": self.error,
        }


def main() -> None:
    database.init_database()
    scanner = QRScanner()
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        print("Khong mo duoc camera.")
        return

    try:
        while not scanner.completed:
            ok, frame = camera.read()
            if not ok:
                print("Khong doc duoc frame camera.")
                break
            cv2.imshow("SmartFace QR", scanner.process_frame(frame))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if scanner.value:
            if not database.person_exists(scanner.value):
                database.add_person(scanner.value, scanner.value)
            print(f"QR: {scanner.value}")
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
