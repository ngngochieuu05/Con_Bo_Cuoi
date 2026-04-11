# Phân tích Chuyên sâu Nghiệp vụ OpenCV trong Dự án

Tài liệu này cung cấp cái nhìn kỹ thuật chi tiết về cách OpenCV (mã nguồn xử lý ảnh) được triển khai trong hệ thống giám sát lái xe, đi sâu vào các thuật toán và thông số cấu hình.

---

## 1. Cơ chế Tiền xử lý & Rendering Luồng Video

Hệ thống không chỉ hiển thị ảnh RAW mà thực hiện một quy trình xử lý đa bước để đảm bảo hiệu năng và độ rõ nét.

### 1.1. Cấu hình Camera Chuyên sâu
- **Backend API**: Sử dụng `cv2.CAP_DSHOW` thay vì mặc định để giải quyết vấn đề khởi động chậm trên Windows.
- **Buffer Control**: Thiết lập `cv2.CAP_PROP_BUFFERSIZE` về `1` để đảm bảo frame nhận được luôn là frame mới nhất, giảm độ trễ (latency) khi xử lý AI.
- **Nén phần cứng**: Ép kiểu mã hóa `MJPG` từ webcam để giảm tải băng thông USB, cho phép chạy đa camera mượt mà hơn.

### 1.2. Thuật toán Letterboxing (Chống méo hình)
Trong hàm `_prepare_display_frame`, OpenCV thực hiện tính toán tỉ lệ khắt khe:
1. Tính `scale = min(target_w / w, target_h / h)`.
2. Resize ảnh gốc theo `scale` bằng `cv2.INTER_AREA` (nếu thu nhỏ) để tránh răng cưa, hoặc `cv2.INTER_CUBIC` (nếu phóng to) để giữ độ mịn.
3. Tạo một "Canvas" đen (`np.zeros`) đúng kích thước UI.
4. Chèn ảnh đã resize vào chính giữa Canvas. Điều này đảm bảo hình ảnh lái xe không bị kéo giãn dù cửa sổ ứng dụng có thay đổi kích thước.

### 1.3. Sharpening (Làm sắc nét)
Sử dụng toán tử tích chập (Convolution) với kernel:
```python
kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
```
Hàm `cv2.filter2D` áp dụng kernel này để làm nổi bật các đường biên (mắt, miệng), giúp việc theo dõi trạng thái lái xe chính xác hơn trong môi trường rung lắc trên cabin.

---

## 2. Logic Nhận diện & Cảnh báo Buồn ngủ (AI Post-processing)

### 2.1. Đồng bộ hóa AI và Frame Rate
Hệ thống chạy 2 luồng FPS khác nhau:
- **Display FPS (~20-30 FPS)**: Đảm bảo hình ảnh mượt mà cho người nhìn.
- **AI Inference (~5 FPS)**: Để giảm tải cho CPU/GPU.
OpenCV đóng vai trò "Cache" ở đây: Kết quả tọa độ (`detections`) từ frame thứ nhất được lưu lại và OpenCV sẽ tiếp tục vẽ chúng lên các frame thứ 2, 3, 4 cho đến khi có kết quả mới. Điều này giúp các Frame hiển thị không bị giật lag.

### 2.2. Xử lý "Bằng chứng" (Evidence Generation)
Khi trạng thái nhắm mắt vượt quá 1.5 giây:
1. Hệ thống gọi `frame.copy()` để lấy snapshot sạch.
2. Vẽ các thông tin vi phạm trực tiếp lên snapshot bằng `cv2.rectangle`.
3. Lưu ảnh bằng `cv2.imwrite` với định dạng `.jpg`.
4. Ảnh này sau đó được hệ thống DAL (Data Access Layer) tự động đăng tải để làm bằng chứng pháp lý hoặc thông báo cho trung tâm điều hành.

---

## 3. Chức năng Login & Oval Face Guide

Đây là phần sử dụng các phép toán hình học OpenCV nhiều nhất.

### 3.1. Thuật toán Khoảng cách Oval
Để xác định khuôn mặt có "khớp" với khung hướng dẫn hay không, hệ thống sử dụng phương trình Ellipse chuẩn hóa:
$$ \frac{(x - x_{center})^2}{a^2} + \frac{(y - y_{center})^2}{b^2} \le 1.5 $$
- **OpenCV Logic**: Tọa độ tâm mặt $(x, y)$ từ Haar Cascade được đưa vào biểu thức trên. Nếu kết quả $\le 1.5$ (có bù margin), `cv2.ellipse` sẽ chuyển sang màu xanh lá cây báo hiệu sẵn sàng chụp.

### 3.2. Hiệu ứng "Focus" (Dynamic Mask)
Quy trình tạo mask:
1. `mask = np.zeros((h, w), dtype=np.uint8)`: Tạo nền đen tuyền.
2. `cv2.ellipse(mask, center, axes, ..., 255, -1)`: Vẽ một hình oval trắng rỗng bên trong.
3. `mask_inv = cv2.bitwise_not(mask)`: Đảo ngược để lấy vùng bên ngoài oval.
4. `cv2.addWeighted`: Trộn ảnh gốc với một phiên bản tối hơn theo tỉ lệ 30-70 trên vùng `mask_inv`.
Kết quả: Tạo ra một giao diện login chuyên nghiệp, làm nổi bật khuôn mặt driver ở giữa.

---

## 4. Trích xuất Đặc trưng Dự phòng (Handcrafted Features)

Khi không có AI chuyên dụng, `Arc_face.py` triển khai một bộ trích xuất đặc trưng thuần OpenCV cực kỳ chi tiết (Handcrafted Features):

### 4.1. Cân bằng Histogram (CLAHE)
Thay vì dùng `cv2.equalizeHist` (thường gây nhiễu), dự án sử dụng **CLAHE**:
- `clipLimit=2.0`: Giới hạn độ tương phản để tránh khuếch đại nhiễu ở vùng tối.
- `tileGridSize=(8, 8)`: Chia ảnh mặt thành các ô 8x8 để xử lý ánh sáng cục bộ. Điều này cực kỳ quan trọng nếu lái xe bị ánh nắng chiếu từ một phía.

### 4.2. Trích xuất Texture (LBP - Local Binary Patterns)
Hệ thống tự triển khai logic LBP bằng vòng lặp pixel:
- Với mỗi pixel, so sánh cường độ với 8 pixel lân cận.
- Nếu lân cận lớn hơn tâm → gán bit 1, ngược lại gán 0.
- 8 bit này tạo thành một số từ 0-255.
- Cuối cùng dùng `cv2.calcHist` để đếm tần suất xuất hiện của các mã này. Đây là "vân tay" đặc trưng cho bề mặt da và hình khối khuôn mặt driver.

### 4.3. Phân tích Biên (Sobel & Laplacian)
- `cv2.Sobel`: Trích xuất các cạnh đứng và ngang của mắt, mũi.
- `cv2.Laplacian`: Xác định độ "sắc" của các chi tiết nhỏ.
Tất cả các vector này (Histogram, Texture, Edges) được `np.concatenate` lại và chuẩn hóa độ dài ($L_2$ Norm) để tạo thành một vector căn cước duy nhất cho việc so khớp login.

---

## 5. Danh sách Kỹ thuật OpenCV Nâng cao trong Cấu trúc Dự án

| Kỹ thuật | File triển khai | Ý nghĩa nghiệp vụ |
| :--- | :--- | :--- |
| **Bitwise Masking** | `camera_preview.py` | Tạo giao diện tập trung khuôn mặt Driver. |
| **Coordinate Norm** | `camera_preview.py` | Kiểm tra độ chuẩn xác của vị trí ngồi lái. |
| **CLAHE Preprocessing**| `Arc_face.py` | Chống chói và bù sáng cho khuôn mặt. |
| **Convolution Filter** | `camera_manager.py` | Tăng độ nét cho camera giám sát hành trình. |
| **JPEG Streaming** | `camera_manager.py` | Nén ảnh Base64 để truyền về UI Flet qua Socket. |
| **Text Size Calc** | `camera_manager.py` | Căn chỉnh nhãn AI tự động không đè lên mặt Driver. |

---

## 6. Tích hợp OpenCV + Flet Desktop (Windows) — Bài học Thực tiễn

Phần này đúc kết kinh nghiệm khi dùng `cv2` kết hợp với **Flet 0.28.x** trên Windows để xây dựng live camera preview trong ứng dụng Flutter desktop.

### 6.1. Cấu hình Camera Khởi động (Windows)
```python
import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)          # PHẢI dùng CAP_DSHOW trên Windows
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)               # Buffer = 1 → luôn lấy frame mới nhất
fourcc = cv2.VideoWriter_fourcc(*"MJPG")
cap.set(cv2.CAP_PROP_FOURCC, fourcc)              # MJPG giảm băng thông USB

# Warm-up: grab vài frame đầu để camera ổn định (tránh frame đen / YUV lỗi)
for _ in range(5):
    cap.grab()

ret, frame = cap.read()
# KHÔNG gọi cap.release() — gây C++ exception trên Windows, để GC tự dọn
```

### 6.2. Hiển thị Base64 trong Flet — `src_base64` vs `src`
**⚠️ LỖI THƯỜNG GẶP**: Flutter desktop KHÔNG render `data:image/jpeg;base64,...` trong property `src` của `ft.Image`.

```python
# ❌ SAI — Flutter desktop bỏ qua data URI trong src
img = ft.Image(src="")
img.src = f"data:image/jpeg;base64,{b64}"

# ✅ ĐÚNG — Dùng property chuyên dụng src_base64 (KHÔNG có prefix)
img = ft.Image(src_base64="")
img.src_base64 = b64   # chỉ chuỗi base64 thuần, không kèm "data:image/jpeg;base64,"
```

### 6.3. Thread Safety trong Flet 0.28.x
```python
# ❌ SAI — gọi control.update() từ background thread gây crash
live_img.update()

# ✅ ĐÚNG — luôn dùng page.update() từ background thread
page.update()
```

### 6.4. Vòng lặp Stream Camera (30 FPS) trong Background Thread
```python
import threading, time, base64, cv2

stop_evt = threading.Event()

def _stream():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    for _ in range(5):
        cap.grab()

    interval = 1.0 / 30
    while not stop_evt.is_set():
        t0 = time.time()
        ret, frame = cap.read()
        if not ret:
            break
        small = cv2.resize(frame, (300, 225))
        _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 60])
        live_img.src_base64 = base64.b64encode(bytes(buf)).decode()
        try:
            page.update()
        except Exception:
            break
        wait = interval - (time.time() - t0)
        if wait > 0:
            time.sleep(wait)
    # KHÔNG gọi cap.release()

t = threading.Thread(target=_stream, daemon=True)
t.start()
```

### 6.5. Video Box Không Hiển Thị (Kích thước 0px)
`ft.Image(src_base64="")` không có kích thước mặc định → bị collapse khi chưa có dữ liệu.

**Giải pháp**: Dùng `ft.Stack` với placeholder Container cố định kích thước:
```python
live_img = ft.Image(src_base64="", width=300, height=225, fit=ft.ImageFit.COVER)

video_box = ft.Stack(
    width=300, height=225,
    controls=[
        ft.Container(width=300, height=225, bgcolor=ft.Colors.BLACK),  # placeholder
        live_img,
    ]
)
```

### 6.6. Subprocess Camera Helper (Single Snapshot)
Khi chỉ cần chụp 1 ảnh, chạy cv2 trong subprocess riêng để tránh C++ crash ảnh hưởng đến process chính:

```python
# _camera_capture.py — chạy dưới dạng subprocess
import sys, cv2, json, tempfile, os

cap = cv2.VideoCapture(int(sys.argv[1]), cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
for _ in range(5):
    cap.grab()
ret, frame = cap.read()
fd, path = tempfile.mkstemp(suffix=".jpg", prefix="cam_snap_")
os.close(fd)
cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
print(json.dumps({"path": path}))
# KHÔNG gọi cap.release()
```

```python
# Caller — gọi subprocess với CREATE_NO_WINDOW
import subprocess, sys, json

result = subprocess.run(
    [sys.executable, "_camera_capture.py", "0"],
    capture_output=True, text=True, timeout=15,
    creationflags=0x08000000   # CREATE_NO_WINDOW
)
obj = json.loads(result.stdout.strip())
img_path = obj["path"]   # dùng path thay vì base64 để tránh data URI lớn
```

### 6.7. Suppress Windows Error Dialog (C++ Crash)
OpenCV trên Windows đôi khi trigger Windows Error Reporting dialog (WER) làm kill process cha. Chặn bằng:
```python
# Thêm vào đầu main.py, TRƯỚC khi import flet
try:
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x8007)
except Exception:
    pass
```

### 6.8. Tóm tắt Checklist Khi Dùng Camera + Flet Desktop

| Vấn đề | Giải pháp |
| :--- | :--- |
| Frame đen / crash khi mở camera | `CAP_DSHOW` + `MJPG` + `BUFFERSIZE=1` + 5x warm-up grab |
| App bị kill do C++ exception | `SetErrorMode(0x8007)` ở đầu `main.py` |
| Subprocess hiện console window | `creationflags=0x08000000` (`CREATE_NO_WINDOW`) |
| `ft.Image.src = "data:..."` không hiện | Dùng `ft.Image.src_base64 = b64` (base64 thuần) |
| `control.update()` crash từ thread | Dùng `page.update()` thay thế |
| Video box bị collapse (0px) | `ft.Stack` với placeholder Container cố định kích thước |
| `cap.release()` gây C++ crash | **KHÔNG gọi** — để GC tự dọn |
