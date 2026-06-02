import cv2
from pyzbar import pyzbar
import database
import time

# Khởi tạo database trước khi chạy
database.init_database()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
last_scanned = None

# Các biến quản lý trạng thái thông báo
status_text = "Hay quet QR code..."
status_color = (255, 255, 255) # Mặc định màu trắng
text_display_expiry = 0        # Thời gian hết hạn của thông báo ngắn hạn

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
    if current_time > text_display_expiry:
        status_text = "Hay quet QR code..."
        status_color = (255, 255, 255) # Quay về màu trắng
        last_scanned = None             # Reset bộ lọc để có thể quét lại chính mã đó nếu muốn

    # TẠO KHUNG NỀN ĐEN PHÍA TRÊN ĐỂ CHỮ NỔI BẬT HƠN (Tùy chọn thẩm mỹ)
    # Vẽ một hình chữ nhật màu đen mờ từ góc (0,0) đến (640, 50) để làm nền cho chữ
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (0, 0, 0), -1)

    # HIỂN THỊ CHỮ LÊN MÀN HÌNH
    # Tọa độ (20, 32) là vị trí xuất hiện của chữ (X=20, Y=32)
    cv2.putText(frame, status_text, (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    # Hiển thị cửa sổ Webcam
    cv2.imshow("He thong quet QR", frame)
    
    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows() 