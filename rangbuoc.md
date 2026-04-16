# Ràng buộc & Quy chuẩn Code — Con Bò Cuối App

> Tài liệu này là **luật bất thành văn** cho toàn bộ dự án.  
> Mọi AI / developer khi chạm vào codebase **phải đọc và tuân theo** trước khi viết code.

---

## 1. Kiến trúc 3 tầng bắt buộc

```
UI  →  BLL  →  DAL
```

| Tầng | Vị trí | Trách nhiệm | KHÔNG được làm |
|---|---|---|---|
| **UI** | `src/ui/` | Render giao diện Flet, bắt sự kiện, gọi BLL | Truy cập DB, chứa logic nghiệp vụ |
| **BLL** | `src/bll/` | Xử lý logic, validate, điều phối nghiệp vụ | Gọi thẳng JSON/DB, render widget |
| **DAL** | `src/dal/` | Đọc/ghi dữ liệu (JSON → sau này PostgreSQL) | Chứa logic nghiệp vụ, gọi BLL |

> ⚠️ **Tuyệt đối không** để UI gọi thẳng DAL (bỏ qua BLL).

---

## 2. Cấu trúc thư mục chuẩn

```
Con_Bo_Cuoi_App/
├── models/                          # Model YOLOv8 (.pt), dataset, runs
│   ├── dataset/Cattle Desease.v1i.yolov8/data.yaml
│   ├── runs/                        # Kết quả train
│   └── train/train.py               # Script train Tkinter (tham khảo)
│
└── webapp_system/
    ├── data/                        # Assets (ảnh, logo, backround.png)
    ├── skill/                       # Tài liệu nghiệp vụ (*.md) — KHÔNG code tại đây
    │   ├── bll/                     # Docs cho từng tính năng BLL
    │   ├── dal/
    │   └── ui/
    └── src/                         # Toàn bộ code Python chạy được
        ├── main.py                  # Entry point duy nhất
        ├── ui/
        │   ├── theme.py             # Design system (màu, widget helpers)
        │   └── components/
        │       ├── admin/           # Màn hình Admin
        │       │   ├── main_admin.py        # Router admin
        │       │   ├── dashboard.py
        │       │   ├── model_management.py
        │       │   ├── train_management.py
        │       │   ├── user_management.py
        │       │   ├── oa_management.py
        │       │   ├── settings.py
        │       │   └── profile_admin.py
        │       ├── auth/            # Login / Register / Forgot password
        │       └── user/
        │           ├── expert/      # Màn hình Expert
        │           └── framer/      # Màn hình Farmer
        ├── bll/
        │   ├── ai_core.py           # Logic AI / YOLO inference
        │   ├── admin/               # Logic nghiệp vụ Admin
        │   ├── user/
        │   │   ├── expert/
        │   │   └── farmer/
        │   └── services/            # Services dùng chung
        │       ├── auth_service.py
        │       ├── monitor_service.py
        │       └── train_service.py
        └── dal/
            ├── base_repo.py         # CRUD JSON chung — không sửa trừ khi đổi DB
            ├── model_repo.py
            ├── tai_khoan_repo.py
            ├── camera_chuong_repo.py
            ├── canh_bao_repo.py
            ├── dataset_repo.py
            └── db/                  # File JSON (models.json, tai_khoan.json, ...)
```

---

## 3. Quy tắc đặt tên

### 3.1 File
| Loại | Quy tắc | Ví dụ |
|---|---|---|
| UI page | `snake_case.py` | `train_management.py`, `user_management.py` |
| UI router | `main_{role}.py` | `main_admin.py`, `main_expert.py` |
| BLL service | `{chuc_nang}_service.py` | `train_service.py`, `auth_service.py` |
| DAL repo | `{bang}_repo.py` | `model_repo.py`, `tai_khoan_repo.py` |
| Tài liệu | `{chuc_nang}.md` trong `skill/` | `train.md`, `ai.md` |

### 3.2 Hàm & biến
| Loại | Quy tắc | Ví dụ |
|---|---|---|
| Hàm public BLL/DAL | `snake_case` | `start_training()`, `get_model_by_type()` |
| Hàm private (nội bộ module) | `_snake_case` | `_run()`, `_parse_line()` |
| Hàm builder UI | `build_{ten_man_hinh}()` | `build_train_management()`, `build_admin_dashboard()` |
| Hằng số | `UPPER_SNAKE_CASE` | `DEFAULT_YAML`, `PRESETS`, `PRIMARY` |
| Biến trạng thái UI | `{ten}_ref` (ft.Ref) | `log_list_ref`, `prog_bar_ref` |
| Dict state nội bộ | `_state = {}` | `_state = {"conf": 0.5}` |

### 3.3 DB / JSON fields
- Dùng **tiếng Việt không dấu** cho field của bảng: `ho_ten`, `loai_mo_hinh`, `trang_thai`
- PK field: `id_{ten_bang}` → `id_model`, `id_tai_khoan`
- Thời gian: `created_at`, `updated_at` (ISO-8601 string)

---

## 4. Quy tắc UI (Flet)

### 4.1 Bắt buộc dùng helpers từ `ui/theme.py`
```python
# ✅ ĐÚNG
from ui.theme import glass_container, button_style, status_badge, section_title

# ❌ SAI — tự tạo Container/Button style inline
ft.Container(bgcolor="#1a1a2e", border_radius=16, ...)
```

| Helper | Dùng cho |
|---|---|
| `glass_container(content, padding, radius)` | Card / panel chính |
| `button_style("primary"\|"danger"\|"warning"\|"secondary")` | Tất cả ElevatedButton |
| `status_badge(label, kind)` | Badge trạng thái |
| `section_title(icon_name, text)` | Tiêu đề section |
| `empty_state(text)` | Khi list rỗng |
| `data_table(headers, rows, col_flex)` | Bảng dữ liệu |
| `metric_card(title, value, icon, accent)` | Card số liệu |
| `inline_field(label, icon, ...)` | TextField trong form |
| `fmt_dt(iso_str)` | Format ngày giờ |

### 4.2 Màu sắc — chỉ dùng biến từ theme.py
```python
from ui.theme import PRIMARY, SECONDARY, WARNING, DANGER
# PRIMARY   = "#4CAF50"  (xanh lá)
# SECONDARY = "#56CCF2"  (xanh dương nhạt)
# WARNING   = "#F2C94C"  (vàng)
# DANGER    = "#FF7A7A"  (đỏ nhạt)
```
> Màu riêng cho từng page → khai báo hằng `_UPPERCASE` đầu file đó.

### 4.3 Pattern builder function
Mỗi màn hình là **một hàm thuần** trả về `ft.Control`, KHÔNG class:
```python
def build_ten_man_hinh() -> ft.Control:
    # state nội bộ bằng dict hoặc ft.Ref
    _state = {}
    some_ref = ft.Ref[ft.Text]()
    
    def on_click(e): ...
    
    return ft.Column(controls=[...])
```

### 4.4 Cập nhật UI từ thread nền
```python
# ✅ ĐÚNG — dùng .after() hoặc kiểm tra .page trước khi .update()
if control.page:
    control.value = "new"
    control.update()

# ❌ SAI — gọi .update() không điều kiện từ thread nền (crash)
control.update()
```

### 4.5 Router Admin
Thêm màn hình mới vào Admin → sửa **2 chỗ** trong `main_admin.py`:
```python
# 1. Import
from ui.components.admin.ten_man_hinh import build_ten_man_hinh

# 2. Đăng ký vào views + navigation_items
views = { ..., "key": build_ten_man_hinh }
navigation_items = [ ..., ("key", "Nhãn", "ICON_NAME") ]
```

---

## 5. Quy tắc BLL

### 5.1 Validate trước, gọi DAL sau
```python
# ✅ ĐÚNG
def save_something(path: str) -> tuple[bool, str]:
    if not path.endswith(".pt"):
        return False, "File phải có đuôi .pt"
    dal.update(...)
    return True, "Đã lưu"
```

### 5.2 Services dùng chung → đặt trong `bll/services/`
- Nếu logic dùng ở nhiều role (admin + expert) → tạo file trong `bll/services/`
- Logic chỉ của 1 role → đặt trong `bll/admin/` hoặc `bll/user/expert/`, `bll/user/farmer/`

### 5.3 Threading
- Mọi tác vụ dài (subprocess, network, file I/O) → **daemon thread riêng**
- Không block UI thread
- Dùng `threading.Lock()` khi truy cập shared state

### 5.4 Subprocess (train/AI)
```python
subprocess.Popen(
    [sys.executable, "-c", script],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1,
    encoding="utf-8", errors="replace",   # bắt buộc errors="replace"
)
```

---

## 6. Quy tắc DAL

### 6.1 Chỉ dùng BaseRepo — không đọc JSON trực tiếp
```python
# ✅ ĐÚNG
_repo = BaseRepo("models", pk_field="id_model")
def get_model_by_type(loai): return _repo.find_one(loai_mo_hinh=loai)

# ❌ SAI
with open("db/models.json") as f: data = json.load(f)
```

### 6.2 Mỗi bảng = 1 file repo
- 1 file `.py` cho 1 bảng JSON
- Tên file: `{ten_bang}_repo.py`
- Luôn có `init_seed()` để khởi tạo dữ liệu mẫu

### 6.3 Luôn cập nhật `updated_at`
```python
def update_something(id, data):
    data["updated_at"] = datetime.now().isoformat()
    return _repo.update(id, data)
```

### 6.4 Chuẩn bị đổi DB
`base_repo.py` là **điểm thay thế duy nhất** khi chuyển từ JSON sang PostgreSQL.  
Tất cả repo chỉ gọi `_repo.find_one()`, `_repo.all()`, `_repo.update()`... — không gọi JSON trực tiếp.

---

## 7. Encoding & Path

### 7.1 Encoding
```python
# Luôn dùng utf-8 khi đọc/ghi file
open(path, "r", encoding="utf-8")
open(path, "w", encoding="utf-8")

# Subprocess → bắt buộc
encoding="utf-8", errors="replace"
```

### 7.2 Path
```python
# ✅ ĐÚNG — dùng pathlib
from pathlib import Path
ROOT = Path(__file__).parent.parent

# ❌ SAI — hardcode string
path = "D:\\DACS\\Con_Bo_Cuoi_App\\models"
```

### 7.3 Tính đường dẫn đến `models/`
```
train_service.py nằm ở: src/bll/services/
→ Lên 4 cấp để đến Con_Bo_Cuoi_App/
→ Path(__file__).parent.parent.parent.parent / "models"
```

---

## 8. Tài liệu nghiệp vụ (skill/)

Mỗi tính năng **phức tạp** phải có file `.md` trong `webapp_system/skill/`:

```
skill/
├── bll/
│   ├── train.md    ← nghiệp vụ train model
│   └── ai.md       ← nghiệp vụ YOLO / model config
├── dal/
└── ui/
```

File `.md` phải có:
1. **Tổng quan nghiệp vụ** — mục đích, luồng chính
2. **Tham số đầu vào** — bảng đầy đủ với giá trị mặc định
3. **Luồng xử lý backend** — code mẫu hoặc pseudocode
4. **Lưu ý kỹ thuật** — gotchas, encoding, path
5. **Đã triển khai** — danh sách file đã tạo, syntax check

---

## 9. Phân quyền theo role

| Chức năng | Admin | Expert | Farmer |
|---|---|---|---|
| Dashboard tổng quan | ✅ | ✅ | ✅ |
| Quản lý tài khoản | ✅ | ❌ | ❌ |
| Cấu hình model YOLO | ✅ | ❌ | ❌ |
| **Train model AI** | ✅ | ❌ | ❌ |
| Xem thống kê OA | ✅ | ✅ | ❌ |
| Cài đặt hệ thống | ✅ | ❌ | ❌ |
| Nhận diện / AI inference | ✅ | ✅ | ✅ |

---

## 10. Checklist trước khi commit code

- [ ] Syntax check: `python -c "import ast; ast.parse(open('file.py').read())"`
- [ ] Không có `import` thừa
- [ ] Không hardcode path Windows (`D:\\...`)
- [ ] UI không gọi thẳng DAL (bỏ qua BLL)
- [ ] Màu sắc dùng biến từ `theme.py`, không tự ghi hex inline
- [ ] Threading: mọi tác vụ dài trong daemon thread
- [ ] Encoding: `utf-8` + `errors="replace"` với subprocess
- [ ] `updated_at` được cập nhật khi save DAL
- [ ] Nếu feature mới phức tạp → có file `.md` trong `skill/`