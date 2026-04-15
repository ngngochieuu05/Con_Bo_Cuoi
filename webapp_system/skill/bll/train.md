# Train YOLOv8 — Nghiệp Vụ Chi Tiết

> Nguồn phân tích: `models/train/train.py`  
> Mục tiêu: Tích hợp chức năng train vào hệ thống webapp (Flet/Python backend)

---

## 1. Tổng quan nghiệp vụ

Chức năng **Train** cho phép người dùng có quyền Admin huấn luyện lại mô hình YOLOv8 phát hiện bệnh trên bò (`disease`) trực tiếp từ giao diện web, thay vì phải chạy script thủ công. Kết quả là file trọng số `.pt` (hoặc `.onnx`) được lưu vào thư mục kết quả, Admin sau đó có thể cập nhật đường dẫn model vào hệ thống.

### Luồng nghiệp vụ tổng quát

```
Admin chọn cấu hình → Validate → Bắt đầu train (subprocess) → Stream log real-time → Hoàn thành → Export model → Cập nhật đường dẫn model
```

---

## 2. Các tham số đầu vào (Input Parameters)

### 2.1 Dataset
| Tham số | Mô tả | Giá trị mặc định |
|---|---|---|
| `data.yaml` | Đường dẫn file cấu hình dataset Roboflow (YOLOv8 format) | `models/dataset/Cattle Desease.v1i.yolov8/data.yaml` |

> **Validate**: File phải tồn tại trên disk trước khi cho phép bắt đầu train.

### 2.2 Loại Task
| Task | Model suffix | Ghi chú |
|---|---|---|
| `Detection` | `.pt` | Phát hiện bounding box — phù hợp cho hệ thống hiện tại |
| `Instance Segmentation` | `-seg.pt` | Vẽ polygon — phức tạp hơn, nặng hơn |

> Khi đổi Task, danh sách model tự động cập nhật suffix tương ứng.

### 2.3 Preset theo VRAM (GPU RTX 4060 8GB)
| Preset | Model | Batch | Img Size | Workers |
|---|---|---|---|---|
| Nhanh (yolov8n - nhẹ nhất) | yolov8n | 32 | 640 | 8 |
| **Cân bằng (yolov8s)** ← mặc định | yolov8s | 16 | 640 | 8 |
| Chất lượng (yolov8m) | yolov8m | 8 | 640 | 8 |
| Cao (yolov8l) | yolov8l | 4 | 640 | 4 |
| Tối đa (yolov8x - nặng nhất) | yolov8x | 2 | 640 | 4 |

### 2.4 Hyperparameters
| Tham số | Kiểu | Mặc định | Mô tả |
|---|---|---|---|
| `model` | string | `yolov8s.pt` | Kiến trúc YOLO (thay đổi theo Preset) |
| `epochs` | int | 50 | Số vòng lặp huấn luyện |
| `batch` | int | 16 | Kích thước batch (phụ thuộc VRAM) |
| `imgsz` | int | 640 | Kích thước ảnh đầu vào (320–1280, bước 32) |
| `lr0` | float | 0.001 | Learning rate ban đầu *(tối ưu: 0.001 thay vì 0.01)* |
| `patience` | int | 30 | Số epoch chờ tối đa nếu không cải thiện (early stop) |
| `workers` | int | 8 | Số luồng DataLoader |
| `device` | string | `"0"` | `"0"` = GPU CUDA 0, `"cpu"` = CPU |
| `optimizer` | string | `AdamW` | `auto`, `SGD`, `Adam`, `AdamW` |
| `amp` | bool | `True` | Auto Mixed Precision (FP16) — tăng tốc GPU |
| `cache` | bool | `False` | Cache dataset vào RAM — nên bật nếu RAM > 16GB |
| `cos_lr` | bool | `True` | Cosine annealing learning rate scheduler |

### 2.5 Data Augmentation (Pro Tuning)
| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `mosaic` | 1.0 | Ghép 4 ảnh thành 1 (1.0 = bật hoàn toàn) |
| `mixup` | 0.2 | Trộn 2 ảnh — tăng độ khó cho model |
| `degrees` | 15 | Xoay ảnh ngẫu nhiên ±15° |
| `hsv_s` | 0.5 | Thay đổi độ bão hòa màu |
| `hsv_v` | 0.4 | Thay đổi độ sáng/tối |

### 2.6 Export Model
| Tuỳ chọn | Hành động |
|---|---|
| `.pt (PyTorch)` | Giữ nguyên file `best.pt` |
| `.onnx (ONNX)` | Export ONNX từ `best.pt`, **xoá** file `.pt` sau đó |
| `.pt + .onnx` | Giữ cả hai |

> **Lưu ý ONNX**: Tự động `pip install onnx onnxslim` vào venv nếu chưa có.

---

## 3. Luồng xử lý backend (Core Logic)

### 3.1 Validate trước khi train
```python
# Bắt buộc
assert Path(yaml_path).exists()   # file data.yaml phải tồn tại
```

### 3.2 Tạo script train động (inline script)
Thay vì gọi API trực tiếp, hệ thống **sinh một Python script string** và chạy qua `subprocess.Popen`. Lý do: tránh block main thread, bắt được stdout/stderr real-time.

**Script được sinh có nội dung:**
```python
from ultralytics import YOLO
import torch

model = YOLO("{model}", task="{detect|segment}")
results = model.train(
    data     = r"{yaml_path}",
    task     = "{detect|segment}",
    epochs   = {epochs},
    batch    = {batch},
    imgsz    = {imgsz},
    lr0      = {lr},
    cos_lr   = {cos_lr},
    optimizer= "{optimizer}",
    patience = {patience},
    workers  = {workers},
    device   = "{device}",
    amp      = {amp},
    cache    = {cache},
    mosaic   = {mosaic},
    mixup    = {mixup},
    degrees  = {degrees},
    hsv_s    = {hsv_s},
    hsv_v    = {hsv_v},
    project  = r"{output_dir}",
    name     = "train_{model}_{epochs}ep",
    exist_ok = True,
    verbose  = True,
)
```

### 3.3 Chạy subprocess (thread riêng)
```python
process = subprocess.Popen(
    [sys.executable, "-c", script],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True, bufsize=1,
    encoding="utf-8", errors="replace",
    cwd=ROOT_DIR,
)
```
- Chạy trong **daemon thread** riêng → không block UI.
- Stream từng dòng stdout → parse log real-time.

### 3.4 Parse log & cập nhật tiến độ
Mỗi dòng stdout được phân tích:
- Tag `[INFO]` → màu xanh dương
- Tag `[DONE]` / `[RESULT]` / `✔` → màu xanh lá (thành công)
- `WARNING` / `warn` → màu vàng
- `Error` / `Traceback` → màu đỏ
- Dòng bắt đầu bằng `Epoch` → màu tím (epoch header)

**Cập nhật Progress bar**: Khi phát hiện pattern `Epoch X/Y` trong log:
```
cur / tot → pct = cur/tot * 100
ETA = (elapsed / cur) * (tot - cur)
```

### 3.5 Kết thúc training
| Return code | Kết quả |
|---|---|
| `0` | Thành công: cập nhật progress 100%, hiển thị thông báo, path kết quả |
| `!= 0` | Lỗi/Dừng: hiển thị thông báo lỗi, giữ log để debug |

### 3.6 Dừng training giữa chừng
```python
process.terminate()   # gửi SIGTERM
```
Cho phép dừng bất cứ lúc nào.

---

## 4. Cấu trúc thư mục kết quả

```
models/runs/
└── train_{model}_{epochs}ep/
    ├── weights/
    │   ├── best.pt        ← trọng số tốt nhất (dùng cho hệ thống)
    │   └── last.pt        ← trọng số epoch cuối
    ├── results.csv        ← metrics theo epoch
    ├── confusion_matrix.png
    ├── val_batch*.jpg
    └── args.yaml          ← cấu hình đã dùng
```

> **Đường dẫn quan trọng**: `runs/train_{model}_{epochs}ep/weights/best.pt`  
> Sau khi train xong, Admin cập nhật đường dẫn này vào DB (bảng model, field `duong_dan_file`).

---

## 5. Kế hoạch tích hợp vào Webapp

### 5.1 Phân quyền
- Chỉ **Admin** mới có quyền truy cập trang Train.
- Route đề xuất: `/admin/train`

### 5.2 API Backend cần thêm (FastAPI / Flask)

#### `POST /api/train/start`
```json
{
  "yaml_path": "models/dataset/...",
  "model": "yolov8s.pt",
  "task": "detect",
  "epochs": 50,
  "batch": 16,
  "imgsz": 640,
  "lr0": 0.001,
  "patience": 30,
  "workers": 8,
  "device": "0",
  "optimizer": "AdamW",
  "amp": true,
  "cache": false,
  "cos_lr": true,
  "mosaic": 1.0,
  "mixup": 0.2,
  "degrees": 15,
  "hsv_s": 0.5,
  "hsv_v": 0.4,
  "output_dir": "models/runs",
  "export_format": ".pt"
}
```
→ Trả về `{ "job_id": "uuid" }`, khởi động subprocess ở background.

#### `GET /api/train/status/{job_id}`
→ Trả về:
```json
{
  "status": "running|done|error|stopped",
  "epoch_current": 15,
  "epoch_total": 50,
  "pct": 30,
  "elapsed": "2m 15s",
  "eta": "5m 10s",
  "log_lines": ["...", "..."],
  "result_path": "models/runs/train_yolov8s_50ep/weights/best.pt"
}
```

#### `POST /api/train/stop/{job_id}`
→ Gọi `process.terminate()`.

### 5.3 Frontend (Flet)
- Form cấu hình giống panel trái của Tkinter app → dùng `ft.Dropdown`, `ft.Slider`, `ft.Checkbox`
- Progress: `ft.ProgressBar` + polling `GET /api/train/status` mỗi 2 giây
- Log streaming: `ft.ListView` cuộn tự động, màu theo tag (`ft.Text(color=...)`)
- Nút **Bắt đầu Train** / **Dừng lại** / **Xoá log**

### 5.4 Sau khi train xong — Cập nhật model
Gọi hàm DAL có sẵn:
```python
update_model_config(id=model_id, conf=0.5, iou=0.5, path="models/runs/.../weights/best.pt")
```
Xem thêm: [`ai.md`](ai.md) — DAL Functions.

---

## 6. Lưu ý kỹ thuật khi tích hợp

| # | Vấn đề | Giải pháp |
|---|---|---|
| 1 | Blocking main thread | Luôn chạy subprocess trong **thread riêng** hoặc **asyncio subprocess** |
| 2 | Nhiều Admin train cùng lúc | Giới hạn 1 job train tại 1 thời điểm (lock/semaphore) |
| 3 | Process zombie khi webapp restart | Lưu `process.pid` vào file, kiểm tra và kill khi khởi động lại |
| 4 | Log quá lớn | Giới hạn buffer log tối đa 1000 dòng trên frontend |
| 5 | CUDA out of memory | Bắt lỗi `RuntimeError: CUDA out of memory` trong log → hiển thị gợi ý giảm batch |
| 6 | ultralytics chưa cài | Kiểm tra `importlib.import_module("ultralytics")` khi startup, cài tự động nếu thiếu |
| 7 | Encoding log | Dùng `encoding="utf-8", errors="replace"` cho subprocess |
| 8 | Path Windows | Dùng `r"..."` hoặc `Path` object khi truyền path vào script |

---

## 7. Các hằng số quan trọng

```python
ROOT_DIR     = Path("models/")                            # thư mục gốc models
DEFAULT_YAML = ROOT_DIR / "dataset" / "Cattle Desease.v1i.yolov8" / "data.yaml"
OUTPUT_DIR   = ROOT_DIR / "runs"                          # thư mục lưu kết quả
PYTHON_EXE   = sys.executable                             # dùng đúng venv hiện tại
```

---

## 8. Tóm tắt nhanh để dev tích hợp

```
1. Admin mở trang /admin/train
2. Chọn preset (mặc định: Cân bằng - yolov8s)
3. Chỉnh hyperparameters nếu cần
4. Nhấn "Bắt đầu Train" → POST /api/train/start → nhận job_id
5. Frontend poll GET /api/train/status/{job_id} mỗi 2s → hiển thị epoch, %, ETA, log
6. Khi done → result_path chứa đường dẫn best.pt
7. Admin nhấn "Cập nhật model hệ thống" → gọi update_model_config() với path mới
8. Model disease trong DB được cập nhật → hệ thống dùng model mới ngay
```

---

## 9. Đã triển khai ✅

> Cập nhật lần cuối: 2026-04-15

### 9.1 Các file đã tạo

| Tầng | File | Mô tả |
|---|---|---|
| **BLL** | `webapp_system/src/bll/services/train_service.py` | Logic train: start/stop job, subprocess, parse log, ETA |
| **UI** | `webapp_system/src/ui/components/admin/train_management.py` | Form Flet: cấu hình, progress bar, log view, nút Áp dụng |
| **UI (Router)** | `webapp_system/src/ui/components/admin/main_admin.py` | Đã thêm nav item "Train AI" + route `"train"` |

### 9.2 Kiến trúc thực tế (theo 3 tầng)

```
ui/components/admin/train_management.py   ← gọi xuống BLL
        ↓
bll/services/train_service.py             ← chạy subprocess train, quản lý TrainJob
        ↓
dal/model_repo.py                         ← update_model_config() sau khi train xong
        ↓
dal/db/models.json                        ← lưu đường dẫn best.pt mới
```

### 9.3 Luồng thực tế trong webapp

```
Admin → Tab "Train AI" (icon: MODEL_TRAINING)
      → Chọn preset / chỉnh params
      → Nhấn "▶ Bắt đầu Train"
      → train_service.start_training() → subprocess Popen (daemon thread)
      → UI poll snapshot() mỗi 2 giây qua threading.Thread
      → Progress bar + log cập nhật real-time
      → Khi done: nút "⚡ Áp dụng model vào hệ thống" xuất hiện
      → Nhấn → dal.model_repo.update_model_config(disease_id, conf, iou, best.pt)
```

### 9.4 Giới hạn thiết kế hiện tại

| # | Giới hạn | Lý do |
|---|---|---|
| 1 | Chỉ 1 job train tại 1 thời điểm | Tránh tranh chấp VRAM / tài nguyên |
| 2 | Poll 2 giây thay vì WebSocket | Flet chạy trong Popen, không cần WS phức tạp |
| 3 | Log giới hạn 1000 dòng buffer, 600 dòng hiển thị | Tránh OOM trên giao diện |
| 4 | Chỉ cập nhật model `disease` sau train | Đây là model được train từ dataset Roboflow cattle disease |

### 9.5 Syntax check

```
OK  bll/services/train_service.py
OK  ui/components/admin/train_management.py
OK  ui/components/admin/main_admin.py
```
