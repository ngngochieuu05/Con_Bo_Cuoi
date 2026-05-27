# 📡 OA — Tài liệu Nghiệp vụ & Luồng Xử lý Cảnh báo Chi tiết

> **Dự án:** Con Bò Cười (Cattle Monitoring System)
> **Repo:** [github.com/ngngochieuu05/Con_Bo_Cuoi](https://github.com/ngngochieuu05/Con_Bo_Cuoi)
> **Mục tiêu tài liệu:** Mô tả toàn bộ luồng nghiệp vụ + code thực tế cho hệ thống phát hiện hành vi bất thường của bò và gửi cảnh báo Telegram.

---

## 1. Kiến trúc tổng quan

```
Con_Bo_Cuoi/webapp_system/src/
├── main.py                                    # Entry point — khởi tạo Flet app
├── bll/services/
│   ├── auth_service.py                        # Đăng nhập, đăng ký, session
│   └── monitor_service.py                     # Config camera, fetch dashboard API, snapshot
├── dal/
│   ├── __init__.py                            # init_all() — seed toàn bộ data khi start
│   ├── base_repo.py                           # BaseRepo — CRUD generic trên JSON
│   ├── tai_khoan_repo.py                      # Quản lý tài khoản (farmer/expert/admin)
│   ├── camera_chuong_repo.py                  # Quản lý camera theo chuồng
│   ├── canh_bao_repo.py                       # Lưu & truy vấn cảnh báo sự cố
│   ├── model_repo.py                          # Quản lý YOLO model config
│   ├── dataset_repo.py                        # Dataset quản lý
│   └── db/                                    # JSON files (gitignored, runtime)
│       ├── app_config.json
│       ├── monitor_cache.json
│       ├── canh_bao_su_co.json
│       └── camera_chuong.json
└── ui/
    ├── theme.py                               # Glassmorphism design tokens
    └── components/
        ├── auth/                              # Login / Register / Forgot password
        ├── admin/                             # Dashboard admin, quản lý user/camera/model
        └── user/
            ├── expert/                        # Tư vấn, xem dữ liệu health
            └── framer/                        # Farmer: giám sát trực tiếp
                ├── main_farmer.py
                ├── live_monitoring.py         # ★ Core UI giám sát real-time
                ├── _camera_capture.py         # Subprocess chụp ảnh camera local
                ├── dashboard.py
                ├── health_consulting.py
                ├── session_history.py
                ├── settings.py
                └── utilities.py
```

**3 AI Models:**

| Model | Nhiệm vụ | Đầu ra |
|-------|----------|--------|
| `cattle_detect` | Phát hiện và khoanh vùng bò trong frame | `List[BoundingBox + CowID]` |
| `behavior` | Phân loại hành vi | `Standing` / `Lying` / `Running` / `Fighting` |
| `disease` | Nhận diện dấu hiệu bệnh qua ngoại hình | Label bệnh + confidence |

**Config YOLO:** `conf` (0.05–0.95), `iou` (0.05–0.95), path `.pt` model — đọc từ `dal/db/app_config.json`

---

## 2. Hai loại cảnh báo (OA Core)

| # | Loại | `loai_canh_bao` trong DB | Điều kiện | Mức độ |
|---|------|--------------------------|-----------|--------|
| 1 | **Bò bỏ ăn** | `"cow_lie"` | Bò nằm liên tục > ngưỡng phút trong giờ ăn | 🟡 Cảnh báo |
| 2 | **Bò húc nhau** | `"cow_fight"` | 2 bounding box va chạm với vận tốc đột ngột | 🔴 Khẩn cấp |

**Trạng thái cảnh báo:**
- `"CHUA_XU_LY"` — mới phát sinh, chưa có người xử lý
- `"DA_XU_LY"` — đã được farmer/expert xác nhận và xử lý

---

## 3. Luồng khởi động hệ thống (`main.py`)

```python
# main.py — Entry point
import flet as ft
from bll.services.monitor_service import load_config, get_local_ip
import dal

def main(page: ft.Page):
    page.title = "Hệ thống giám sát bò AI"
    page.data = {"is_mobile": True}

    def show_dashboard(role: str):
        normalized_role = (role or "farmer").lower()
        # Lưu thông tin session vào page.data
        page.data["user_role"] = normalized_role

        if normalized_role == "admin":
            control = AdminMainScreen(page, on_logout=logout_to_login)
        elif normalized_role == "expert":
            control = ExpertMainScreen(page, on_logout=logout_to_login)
        else:  # farmer — vai trò chính dùng Live Monitoring
            control = FarmerMainScreen(page, on_logout=logout_to_login)

        page.clean()
        page.add(control)
        page.update()

    # ★ Quan trọng: khởi tạo DAL — tạo JSON files + seed data mẫu
    dal.init_all()

    # Xóa session cũ, luôn bắt đầu từ Login
    for _k in ("user_role", "user_id", "ho_ten"):
        page.data.pop(_k, None)
    show_login()

if __name__ == "__main__":
    _cfg = load_config()
    _mode = _cfg.get("app_mode", "desktop")  # "desktop" | "web"
    _port = int(_cfg.get("app_port", 8080))

    ft.app(
        target=main,
        assets_dir=str(Path(__file__).parent.parent / "data"),
        view=ft.AppView.WEB_BROWSER if _mode == "web" else ft.AppView.FLET_APP,
        host="0.0.0.0" if _mode == "web" else None,
        port=_port if _mode == "web" else 0,
    )
```

**`dal.init_all()` thực thi:**
```python
# dal/__init__.py
def init_all():
    """Gọi khi app khởi động để đảm bảo seed data sẵn sàng."""
    _seed_users()    # tai_khoan.json — tài khoản mẫu
    _seed_models()   # model.json — YOLO models
    _seed_cameras()  # camera_chuong.json — 3 camera mẫu (Khu A/B/C)
    _seed_alerts()   # canh_bao_su_co.json — 2 cảnh báo mẫu
    _seed_dataset()  # dataset.json
```

---

## 4. DAL Layer — Dữ liệu cảnh báo & camera

### 4.1 `BaseRepo` — Generic CRUD trên JSON

```python
# dal/base_repo.py
"""
Base JSON Repository
Cấu trúc file: {"records": [...], "next_id": N}
Khi chuyển sang PostgreSQL: chỉ cần thay thế class này.
"""
class BaseRepo:
    def __init__(self, table_name: str, pk_field: str = "id"):
        self._table = table_name   # → dal/db/{table_name}.json
        self._pk = pk_field

    def all(self) -> list[dict]:
        return list(_load(self._table)["records"])

    def find_by_id(self, pk_value) -> dict | None:
        for rec in self.all():
            if rec.get(self._pk) == pk_value:
                return dict(rec)
        return None

    def find_one(self, **kwargs) -> dict | None:
        """Tìm bản ghi đầu tiên khớp tất cả kwargs."""
        for rec in self.all():
            if all(rec.get(k) == v for k, v in kwargs.items()):
                return dict(rec)
        return None

    def find_many(self, **kwargs) -> list[dict]:
        return [dict(r) for r in self.all()
                if all(r.get(k) == v for k, v in kwargs.items())]

    def insert(self, data: dict) -> dict:
        """Thêm bản ghi mới, tự gán PK nếu chưa có."""
        store = _load(self._table)
        if self._pk not in data:
            data = {self._pk: store["next_id"], **data}
            store["next_id"] += 1
        store["records"].append(data)
        _save(self._table, store)
        return dict(data)

    def update(self, pk_value, updates: dict) -> dict | None:
        store = _load(self._table)
        for i, rec in enumerate(store["records"]):
            if rec.get(self._pk) == pk_value:
                store["records"][i] = {**rec, **updates}
                _save(self._table, store)
                return dict(store["records"][i])
        return None

    def delete(self, pk_value) -> bool:
        store = _load(self._table)
        before = len(store["records"])
        store["records"] = [r for r in store["records"]
                            if r.get(self._pk) != pk_value]
        if len(store["records"]) < before:
            _save(self._table, store)
            return True
        return False

    def seed(self, records: list[dict]) -> None:
        """Khởi tạo dữ liệu mẫu nếu bảng còn trống."""
        store = _load(self._table)
        if store["records"]:
            return   # Đã có dữ liệu → không seed lại
        max_id = max((r.get(self._pk, 0) for r in records), default=0)
        store["records"] = records
        store["next_id"] = max_id + 1
        _save(self._table, store)
```

---

### 4.2 `canh_bao_repo.py` — Repository cảnh báo sự cố

```python
# dal/canh_bao_repo.py
"""
Repository: canh_bao_su_co
Ánh xạ bảng canh_bao_su_co → dal/db/canh_bao_su_co.json
"""
from datetime import datetime
from dal.base_repo import BaseRepo

_repo = BaseRepo("canh_bao_su_co", pk_field="id_canh_bao")

# Dữ liệu seed mặc định khi khởi động lần đầu
_SEED = [
    {
        "id_canh_bao": 1,
        "loai_canh_bao": "cow_fight",    # Bò húc nhau
        "trang_thai": "CHUA_XU_LY",
        "id_user": 3,
        "id_camera_chuong": 1,
        "created_at": "2026-04-10T10:40:00",
    },
    {
        "id_canh_bao": 2,
        "loai_canh_bao": "cow_lie",      # Bò nằm bỏ ăn
        "trang_thai": "DA_XU_LY",
        "id_user": 3,
        "id_camera_chuong": 2,
        "created_at": "2026-04-10T09:15:00",
    },
]

def init_seed():
    _repo.seed(_SEED)

def get_all() -> list[dict]:
    return _repo.all()

def get_by_user(id_user: int) -> list[dict]:
    """Lấy tất cả cảnh báo của một user (farmer)."""
    return _repo.find_many(id_user=id_user)

def get_by_status(trang_thai: str) -> list[dict]:
    """Lọc cảnh báo theo trạng thái: CHUA_XU_LY | DA_XU_LY."""
    return _repo.find_many(trang_thai=trang_thai)

def create_alert(loai_canh_bao: str, id_user: int, id_camera_chuong: int) -> dict:
    """
    Tạo cảnh báo mới khi AI phát hiện bất thường.
    loai_canh_bao: "cow_fight" | "cow_lie"
    Trạng thái mặc định: CHUA_XU_LY
    """
    return _repo.insert({
        "loai_canh_bao": loai_canh_bao,
        "trang_thai": "CHUA_XU_LY",
        "id_user": id_user,
        "id_camera_chuong": id_camera_chuong,
        "created_at": datetime.now().isoformat(),
    })

def resolve_alert(id_canh_bao: int) -> dict | None:
    """Đánh dấu cảnh báo đã được xử lý."""
    return _repo.update(id_canh_bao, {"trang_thai": "DA_XU_LY"})

def count_open() -> int:
    """Đếm số cảnh báo chưa xử lý — hiển thị trên dashboard."""
    return len(get_by_status("CHUA_XU_LY"))
```

**JSON file tương ứng** (`dal/db/canh_bao_su_co.json`):
```json
{
  "records": [
    {
      "id_canh_bao": 1,
      "loai_canh_bao": "cow_fight",
      "trang_thai": "CHUA_XU_LY",
      "id_user": 3,
      "id_camera_chuong": 1,
      "created_at": "2026-04-10T10:40:00"
    },
    {
      "id_canh_bao": 2,
      "loai_canh_bao": "cow_lie",
      "trang_thai": "DA_XU_LY",
      "id_user": 3,
      "id_camera_chuong": 2,
      "created_at": "2026-04-10T09:15:00"
    }
  ],
  "next_id": 3
}
```

---

### 4.3 `camera_chuong_repo.py` — Repository camera chuồng

```python
# dal/camera_chuong_repo.py
"""
Repository: camera_chuong
Ánh xạ bảng camera_chuong → dal/db/camera_chuong.json
"""
from dal.base_repo import BaseRepo

_repo = BaseRepo("camera_chuong", pk_field="id_camera_chuong")

_SEED = [
    {
        "id_camera_chuong": 1,
        "id_chuong": "CHUONG-A",
        "khu_vuc_chuong": "Khu A",
        "id_camera": "CAM-01",
        "id_user": 3,           # Farmer quản lý
        "trang_thai": "online",
        "updated_at": "2026-04-10T10:45:00",
    },
    {
        "id_camera_chuong": 2,
        "id_chuong": "CHUONG-B",
        "khu_vuc_chuong": "Khu B",
        "id_camera": "CAM-03",
        "id_user": 3,
        "trang_thai": "warning",  # Có cảnh báo đang xử lý
        "updated_at": "2026-04-10T10:42:00",
    },
    {
        "id_camera_chuong": 3,
        "id_chuong": "CHUONG-C",
        "khu_vuc_chuong": "Khu C",
        "id_camera": "CAM-07",
        "id_user": 3,
        "trang_thai": "offline",
        "updated_at": "2026-04-10T10:40:00",
    },
]

def init_seed():
    _repo.seed(_SEED)

def get_all() -> list[dict]:
    return _repo.all()

get_all_cameras = get_all  # Alias

def get_by_user(id_user: int) -> list[dict]:
    """Lấy tất cả camera của farmer theo id_user."""
    return _repo.find_many(id_user=id_user)

def get_by_camera_id(id_camera: str) -> dict | None:
    return _repo.find_one(id_camera=id_camera)

def create_camera(id_chuong: str, khu_vuc: str, id_camera: str, id_user: int) -> dict:
    return _repo.insert({
        "id_chuong": id_chuong,
        "khu_vuc_chuong": khu_vuc,
        "id_camera": id_camera,
        "id_user": id_user,
    })

def delete_camera(id_camera_chuong: int) -> bool:
    return _repo.delete(id_camera_chuong)

def count() -> int:
    return _repo.count()
```

**JSON file tương ứng** (`dal/db/camera_chuong.json`):
```json
{
  "records": [
    {"id_camera_chuong": 1, "id_chuong": "CHUONG-A",
     "khu_vuc_chuong": "Khu A", "id_camera": "CAM-01",
     "id_user": 3, "trang_thai": "online"},
    {"id_camera_chuong": 2, "id_chuong": "CHUONG-B",
     "khu_vuc_chuong": "Khu B", "id_camera": "CAM-03",
     "id_user": 3, "trang_thai": "warning"},
    {"id_camera_chuong": 3, "id_chuong": "CHUONG-C",
     "khu_vuc_chuong": "Khu C", "id_camera": "CAM-07",
     "id_user": 3, "trang_thai": "offline"}
  ],
  "next_id": 4
}
```

---

## 5. BLL Layer — Monitor Service & Auth

### 5.1 `monitor_service.py` — Cấu hình & kết nối máy chủ AI

```python
# bll/services/monitor_service.py
import json, os, socket, time
import requests

# Paths tuyệt đối, độc lập với CWD
_DAL_DB = os.path.join(os.path.dirname(__file__), "..", "..", "dal", "db")
CONFIG_PATH = os.path.normpath(os.path.join(_DAL_DB, "app_config.json"))
CACHE_PATH  = os.path.normpath(os.path.join(_DAL_DB, "monitor_cache.json"))


def load_config() -> dict:
    """Đọc app_config.json, merge với default nếu thiếu key."""
    default = {
        "server_url": "http://127.0.0.1:8000",
        "camera_index": 0,
        "auto_connect": False,
        "notify_alert": True,
        "app_mode": "desktop",       # "desktop" | "web"
        "app_port": 8080,
        "yolo_model_mode": "cpu",    # "cpu" | "gpu" | "auto"
    }
    if not os.path.exists(CONFIG_PATH):
        return default
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {**default, **data}      # data ghi đè default


def save_config(config: dict):
    """Lưu cấu hình — dùng khi farmer/admin thay đổi settings."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_cache() -> dict:
    """Đọc monitor_cache.json — dùng khi offline."""
    if not os.path.exists(CACHE_PATH):
        return {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(data: dict):
    """Lưu dữ liệu dashboard vào cache sau mỗi lần poll thành công."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_dashboard(server_url: str, timeout: int = 5) -> dict:
    """
    Gọi API máy chủ AI để lấy dữ liệu dashboard.
    Endpoint: GET {server_url}/api/dashboard
    Response mong đợi:
    {
        "total_cows": 42,
        "active_alerts": 3,
        "cameras_online": 2,
        "timestamp": "2026-04-19 22:30:00",
        "recent_alerts": [
            {"time": "22:28", "type": "cow_fight", "camera": "CAM-01"},
            ...
        ]
    }
    """
    url = f"{server_url.rstrip('/')}/api/dashboard"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if "timestamp" not in data:
        data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return data


def stream_url(server_url: str) -> str:
    """URL của MJPEG stream — gán vào ft.Image.src để hiển thị trực tiếp."""
    return f"{server_url.rstrip('/')}/api/stream"


def fetch_snapshot_base64(server_url: str, timeout: int = 5) -> str:
    """Chụp ảnh tĩnh từ máy chủ, trả về base64 để hiển thị trong Flet."""
    import base64
    url = f"{server_url.rstrip('/')}/api/snapshot"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return base64.b64encode(resp.content).decode()


def get_local_ip() -> str:
    """Lấy IP LAN thực — hiển thị URL cho phone truy cập web mode."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
```

---

### 5.2 `auth_service.py` — Xác thực & phân quyền

```python
# bll/services/auth_service.py
import time, flet as ft
from dal.tai_khoan_repo import authenticate as _dal_authenticate, ...

# Rate limiting: tối đa 5 lần đăng nhập sai trong 5 phút → khóa 15 phút
_MAX_ATTEMPTS = 5
_WINDOW_SECS  = 300    # Sliding window 5 phút
_LOCKOUT_SECS = 900    # Khóa 15 phút
_login_attempts: dict[str, list[float]] = {}


def _is_locked_out(uname: str) -> bool:
    now = time.monotonic()
    attempts = [t for t in _login_attempts.get(uname, []) if now - t < _WINDOW_SECS]
    _login_attempts[uname] = attempts   # Cập nhật sliding window
    return len(attempts) >= _MAX_ATTEMPTS


def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page):
    """
    Xác thực tài khoản. Lưu session vào page.data.
    Returns: vai_tro ("farmer" | "expert" | "admin") nếu OK, None nếu sai
    """
    uname = ten_dang_nhap.strip()
    if _is_locked_out(uname):
        return None     # Tài khoản đang bị khóa tạm thời

    user = _dal_authenticate(uname, mat_khau)   # SHA-256 hash check
    if user:
        _clear_attempts(uname)
        role = user.get("vai_tro", "farmer")
        # Lưu session vào page.data (tương đương session variable)
        page.data["user_role"] = role
        page.data["user_id"]   = str(user.get("id_user", ""))
        page.data["ho_ten"]    = user.get("ho_ten", "")
        return role

    _record_failure(uname)    # Ghi nhận lần đăng nhập thất bại
    return None


def perform_logout(page: ft.Page, on_logout_success):
    """Xóa toàn bộ session data."""
    for key in ("user_role", "user_id", "ho_ten"):
        try:
            page.data.pop(key, None)
        except Exception:
            pass
    if on_logout_success:
        on_logout_success()     # → callback về show_login()


def register(ten_dang_nhap: str, mat_khau: str, ho_ten: str,
             vai_tro: str = "farmer") -> tuple[bool, str]:
    """
    Đăng ký tài khoản mới.
    - Chỉ cho phép role: "farmer" | "expert" (tự đăng ký)
    - Admin phải được tạo bởi admin khác
    Returns: (success: bool, message: str)
    """
    import re
    uname = ten_dang_nhap.strip()
    if len(uname) < 3 or len(uname) > 50:
        return False, "Tên đăng nhập phải từ 3–50 ký tự."
    if not re.match(r"^[a-zA-Z0-9_]+$", uname):
        return False, "Tên đăng nhập chỉ được chứa chữ, số và dấu gạch dưới."
    if len(mat_khau) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."
    if vai_tro not in {"farmer", "expert"}:
        vai_tro = "farmer"      # Default về farmer nếu role không hợp lệ
    if _dal_get_by_uname(uname):
        return False, f"Tên đăng nhập '{uname}' đã tồn tại."
    _dal_create(uname, mat_khau, vai_tro, ho_ten.strip())
    return True, "Đăng ký thành công."
```

---

## 6. Luồng Chụp ảnh Camera Local (`_camera_capture.py`)

File này chạy như **subprocess độc lập** để tránh crash Flutter renderer khi dùng data URI lớn.

```python
# ui/components/user/framer/_camera_capture.py
"""
Helper script chạy trong subprocess độc lập để chụp ảnh camera.
Usage: python _camera_capture.py <camera_index>
Output: JSON {"path": "<path_to_jpg>"} hoặc {"error": "<msg>"}
Lưu ra file thay vì base64 để tránh Flutter renderer crash với data URI lớn.
"""
import json, os, sys, tempfile

def main():
    try:
        idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    except (ValueError, IndexError):
        idx = 0

    try:
        import cv2
    except ImportError:
        print(json.dumps({"error": "opencv_not_installed"}))
        sys.exit(1)

    cap = None
    try:
        # Thử DirectShow trước (Windows), fallback về default
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            print(json.dumps({"error": f"cannot_open_{idx}"}))
            sys.exit(1)

        # Tối ưu: MJPEG + buffer size 1 (lấy frame mới nhất)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G"))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Grab 5 frame đầu để camera warmup (tránh ảnh tối/blur)
        for _ in range(5):
            cap.grab()

        ret, frame = cap.read()
        if not ret:
            print(json.dumps({"error": "no_frame"}))
            sys.exit(1)

        # Lưu ra temp file .jpg, quality 80
        fd, path = tempfile.mkstemp(suffix=".jpg", prefix="cam_snap_")
        os.close(fd)
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(json.dumps({"path": path}))   # Output JSON cho parent process

    finally:
        if cap is not None:
            cap.release()
```

**Cách gọi từ `live_monitoring.py`:**
```python
import subprocess, json, sys

def _capture_local_camera(camera_index: int) -> str | None:
    """Chạy _camera_capture.py trong subprocess, trả về path ảnh."""
    result = subprocess.run(
        [sys.executable, "_camera_capture.py", str(camera_index)],
        capture_output=True, text=True, timeout=10
    )
    data = json.loads(result.stdout)
    if "path" in data:
        return data["path"]   # Đường dẫn file .jpg tạm
    return None               # {"error": "..."} → trả None
```

---

## 7. Luồng Giám sát Trực tiếp (`live_monitoring.py`)

Đây là **màn hình cốt lõi** mà farmer dùng để theo dõi đàn bò real-time.

### 7.1 Kiến trúc `LiveMonitoringController`

```python
# ui/components/user/framer/live_monitoring.py
import threading, time
import flet as ft
from bll.services.monitor_service import (
    fetch_dashboard, fetch_snapshot_base64,
    load_cache, load_config, save_cache, stream_url,
)

class LiveMonitoringController:
    def __init__(self):
        self.config = load_config()
        self.server_url = self.config.get("server_url", "http://127.0.0.1:8000")
        self.is_connected = False
        self._polling = False       # Flag dừng polling thread

        # UI Controls
        self.status_chip  = status_badge("Ngoại tuyến", "danger")
        self.last_update  = ft.Text("", size=11, color=ft.Colors.WHITE70)
        self.stream_image = ft.Image(
            src="", fit="contain", border_radius=12,
            error_content=ft.Column(controls=[
                ft.Icon(ft.Icons.VIDEOCAM_OFF, size=40, color=ft.Colors.WHITE60),
                ft.Text("Không có tín hiệu camera", size=12, color=ft.Colors.WHITE70),
            ]),
        )
        # KPI cards
        self.total_cows    = ft.Text("--", size=24, weight=ft.FontWeight.W_700)
        self.active_alerts = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=DANGER)
        self.camera_online = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=PRIMARY)

        self.log_rows     = ft.Column(spacing=8)
        self.connect_btn  = ft.ElevatedButton(
            "Kết nối máy chủ", icon=ft.Icons.WIFI, on_click=self.toggle_connection
        )
        self.snapshot_btn = ft.OutlinedButton(
            "Chụp ảnh", icon=ft.Icons.CAMERA_ALT,
            on_click=self.take_snapshot, visible=False
        )
        self._build_ui()
```

### 7.2 Luồng kết nối máy chủ AI

```python
    def toggle_connection(self, e):
        """Toggle kết nối/ngắt kết nối với máy chủ AI."""
        if self.is_connected:
            # Ngắt kết nối
            self._polling = False
            self.is_connected = False
            self._set_status(False)
            self.connect_btn.text = "Kết nối máy chủ"
            self.connect_btn.icon = ft.Icons.WIFI
            self.snapshot_btn.visible = False
            self._safe_update(self.connect_btn, self.snapshot_btn)
            self._append_log(time.strftime("%H:%M"), "Đã ngắt kết nối máy chủ", "info")
            return

        # Đang kết nối — disable button tránh double click
        self.connect_btn.text = "Đang kết nối..."
        self.connect_btn.disabled = True
        self._safe_update(self.connect_btn)

        def _connect():
            try:
                # Gọi API để kiểm tra kết nối + lấy data ban đầu
                data = fetch_dashboard(self.server_url)
                save_cache(data)                    # Cache lại để dùng khi offline
                self.is_connected = True
                self._set_status(True)
                self._apply_dashboard_data(data)
                self.connect_btn.text = "Ngắt kết nối"
                self.connect_btn.icon = ft.Icons.WIFI_OFF
                self.snapshot_btn.visible = True
                self._append_log(time.strftime("%H:%M"), "Kết nối máy chủ thành công", "success")
                self._start_polling()               # Bắt đầu polling loop

            except Exception as err:
                # Kết nối thất bại → load cache offline
                self.is_connected = False
                self._set_status(False)
                self.connect_btn.text = "Thử lại"
                self.connect_btn.icon = ft.Icons.WIFI
                self.snapshot_btn.visible = False
                self._append_log(
                    time.strftime("%H:%M"),
                    f"Không kết nối được máy chủ: {str(err)[:60]}",
                    "warning"
                )
                self._load_offline_cache()

            finally:
                self.connect_btn.disabled = False
                self._safe_update(self.connect_btn, self.snapshot_btn)

        threading.Thread(target=_connect, daemon=True).start()
```

### 7.3 Polling Loop — Cập nhật liên tục mỗi 5 giây

```python
    def _start_polling(self):
        """Khởi động polling loop trong background thread."""
        self._polling = True
        # Set MJPEG stream URL trực tiếp vào Image widget
        self.stream_image.src = stream_url(self.server_url)
        self.stream_image.src_base64 = None
        self._safe_update(self.stream_image)

        def _poll_loop():
            while self._polling and self.is_connected:
                try:
                    # GET /api/dashboard mỗi 5 giây
                    data = fetch_dashboard(self.server_url)
                    save_cache(data)                # Cập nhật cache
                    self._apply_dashboard_data(data)

                except Exception as err:
                    # Mất kết nối → dừng polling, load cache
                    self.is_connected = False
                    self._set_status(False)
                    self.connect_btn.text = "Thử lại"
                    self._safe_update(self.connect_btn)
                    self._append_log(
                        time.strftime("%H:%M"),
                        f"Mất kết nối: {str(err)[:60]}",
                        "warning"
                    )
                    self._load_offline_cache()
                    break

                time.sleep(5)   # Poll mỗi 5 giây

        threading.Thread(target=_poll_loop, daemon=True).start()
```

### 7.4 Hiển thị dữ liệu Dashboard

```python
    def _apply_dashboard_data(self, data: dict, offline: bool = False):
        """Cập nhật KPI cards và log từ data API trả về."""
        # Cập nhật 3 KPI chính
        self.total_cows.value    = str(data.get("total_cows", "--"))    # Tổng số bò
        self.active_alerts.value = str(data.get("active_alerts", "--")) # Cảnh báo đang mở
        self.camera_online.value = str(data.get("cameras_online", "--"))# Camera trực tuyến
        self.last_update.value   = f"Cập nhật: {data.get('timestamp', '')}"

        self._safe_update(self.total_cows, self.active_alerts,
                          self.camera_online, self.last_update)

        # Hiển thị 3 cảnh báo gần nhất
        recent_alerts = data.get("recent_alerts", [])[-3:]
        for alert in recent_alerts:
            a_time = alert.get("time", time.strftime("%H:%M"))
            a_type = alert.get("type", "Cảnh báo")
            # Phân loại màu: đỏ cho húc nhau / bất thường, xanh cho thông thường
            kind = "warning" if "Fighting" in a_type or "bat thuong" in a_type.lower() else "info"
            self._append_log(a_time, a_type, kind)

        if offline:
            self._append_log(time.strftime("%H:%M"),
                             "Đang dùng dữ liệu bộ nhớ đệm ngoại tuyến", "info")


    def _append_log(self, time_label: str, message: str, kind: str = "info"):
        """Thêm log entry vào đầu danh sách, giữ tối đa 8 dòng."""
        color = (DANGER if kind == "warning"
                 else (PRIMARY if kind == "success" else ft.Colors.WHITE70))

        self.log_rows.controls.insert(0, ft.Container(
            padding=10, border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            content=ft.Row(controls=[
                ft.Text(time_label, size=11, color=ft.Colors.WHITE60, width=70),
                ft.Text(message, size=12, color=color, expand=True),
            ]),
        ))
        if len(self.log_rows.controls) > 8:
            self.log_rows.controls.pop()    # Xóa log cũ nhất
        self._safe_update(self.log_rows)


    def _load_offline_cache(self):
        """Fallback: đọc cache khi offline."""
        cache = load_cache()
        if cache:
            self._apply_dashboard_data(cache, offline=True)
        else:
            self._append_log(time.strftime("%H:%M"), "Không có dữ liệu bộ nhớ đệm", "warning")
```

### 7.5 Chụp ảnh Snapshot

```python
    def take_snapshot(self, e):
        """Yêu cầu máy chủ AI chụp ảnh tại thời điểm hiện tại."""
        if not self.is_connected:
            self._append_log(time.strftime("%H:%M"), "Cần kết nối máy chủ trước", "warning")
            return

        def _snapshot():
            try:
                # GET /api/snapshot → trả về bytes ảnh
                b64_data = fetch_snapshot_base64(self.server_url)
                # Chuyển từ stream URL sang ảnh tĩnh base64
                self.stream_image.src = ""
                self.stream_image.src_base64 = b64_data
                self._safe_update(self.stream_image)
                self._append_log(time.strftime("%H:%M"), "Đã chụp ảnh từ camera", "success")
            except Exception as err:
                self._append_log(
                    time.strftime("%H:%M"),
                    f"Lỗi chụp ảnh: {str(err)[:60]}",
                    "warning"
                )

        threading.Thread(target=_snapshot, daemon=True).start()


def build_live_monitoring():
    """Factory function — tạo controller và auto-connect nếu config cho phép."""
    controller = LiveMonitoringController()
    if controller.config.get("auto_connect", False):
        # Auto kết nối khi mở màn hình nếu auto_connect=True trong config
        threading.Thread(
            target=lambda: controller.toggle_connection(None),
            daemon=True
        ).start()
    return controller.root
```

---

## 8. Luồng Phát hiện Hành vi & Gửi Cảnh báo (Phase 4 — Thiết kế)

> [!NOTE]
> Phase 4 chưa implement trong repo hiện tại. Phần này mô tả **thiết kế luồng** dựa trên kiến trúc sẵn có.

### 8.1 Scenario A — Bò bỏ ăn (`cow_lie`)

**Nghiệp vụ:** Trong giờ cho ăn, nếu một con bò nằm liên tục vượt ngưỡng → xem là bỏ ăn / có vấn đề sức khoẻ.

```
[Camera stream → YOLO cattle_detect → List[bbox, cow_id]]
          ↓
    behavior model → label: "Lying" | "Standing" | "Running" | "Fighting"
          ↓
    behavior_tracker[cow_id] = {
        "state": "Lying",
        "since": datetime.now()    ← ghi lại thời điểm bắt đầu nằm
    }
          ↓
    Mỗi frame: kiểm tra ngưỡng
    ┌──────────────────────────────────────────────┐
    │ state == "Lying"                              │
    │ AND is_feeding_hour()        ← giờ ăn?       │
    │ AND (now - since) > THRESHOLD (ví dụ: 30min) │
    └──────────────────────────────────────────────┘
          ↓ YES
    Kích hoạt cảnh báo:
    1. canh_bao_repo.create_alert("cow_lie", id_user, id_camera_chuong)
    2. Chụp snapshot frame hiện tại
    3. alert_service.send_photo(token, chat_id, snapshot_path, caption)
    4. Cooldown 60s cho cow_id này (tránh spam)
```

**Code nghiệp vụ mẫu:**
```python
# bll/services/alert_service.py (Phase 4)
import threading
from datetime import datetime
from dal.canh_bao_repo import create_alert

# Thresholds (đọc từ app_config.json)
LYING_THRESHOLD_MINUTES = 30
ALERT_COOLDOWN_SECONDS  = 60

# Tracker state per cow
behavior_tracker: dict[str, dict] = {}
alert_cooldown:   dict[str, float] = {}  # cow_id → last_alert_timestamp
_tracker_lock = threading.Lock()


def update_behavior(cow_id: str, label: str, id_camera: int, id_user: int):
    """
    Gọi mỗi frame từ YOLO behavior model.
    label: "Standing" | "Lying" | "Running" | "Fighting"
    """
    now = datetime.now()

    with _tracker_lock:
        current = behavior_tracker.get(cow_id, {})

        if current.get("state") != label:
            # State thay đổi → reset timer
            behavior_tracker[cow_id] = {"state": label, "since": now}
            return

        # State không đổi → kiểm tra thời gian
        duration_min = (now - current["since"]).total_seconds() / 60

        if label == "Lying" and _is_feeding_hour() and duration_min > LYING_THRESHOLD_MINUTES:
            _trigger_lying_alert(cow_id, duration_min, id_camera, id_user)


def _trigger_lying_alert(cow_id: str, duration_min: float, id_camera: int, id_user: int):
    """Kích hoạt cảnh báo bỏ ăn nếu chưa trong cooldown."""
    import time
    last = alert_cooldown.get(f"lie_{cow_id}", 0)
    if time.time() - last < ALERT_COOLDOWN_SECONDS:
        return   # Còn trong cooldown → bỏ qua

    alert_cooldown[f"lie_{cow_id}"] = time.time()

    # 1. Lưu vào DB JSON
    alert_record = create_alert("cow_lie", id_user, id_camera)

    # 2. Gửi Telegram (non-blocking)
    def _send():
        from bll.services.telegram_alert import send_cow_alert
        send_cow_alert(
            alert_type="cow_lie",
            cow_id=cow_id,
            camera_id=id_camera,
            extra={"duration_min": round(duration_min, 1)}
        )
    threading.Thread(target=_send, daemon=True).start()


def _is_feeding_hour() -> bool:
    """Kiểm tra có đang trong giờ cho ăn không."""
    hour = datetime.now().hour
    # Giờ ăn: 6–8 sáng và 16–18 chiều (configurable)
    return (6 <= hour < 8) or (16 <= hour < 18)
```

---

### 8.2 Scenario B — Bò húc nhau (`cow_fight`)

**Nghiệp vụ:** Tính toán IoU và vận tốc tương đối giữa các bounding box. Va chạm mạnh = IoU cao + vận tốc đột ngột.

```
[Mỗi frame: List[BoundingBox(x1,y1,x2,y2, cow_id)]]
          ↓
    Tính centroid mỗi bò:
    centroid[cow_id] = ((x1+x2)/2, (y1+y2)/2)
          ↓
    Tính velocity so với frame trước:
    velocity[cow_id] = dist(centroid_now, centroid_prev) / dt
          ↓
    Kiểm tra từng cặp (i, j):
    ┌────────────────────────────────────────────────────┐
    │ iou(bbox_i, bbox_j) > IOU_THRESHOLD  (ví dụ: 0.1) │
    │ AND (velocity[i] + velocity[j]) > VEL_THRESHOLD    │
    │ AND key NOT in cooldown                             │
    └────────────────────────────────────────────────────┘
          ↓ YES
    Kích hoạt cảnh báo:
    1. canh_bao_repo.create_alert("cow_fight", id_user, id_camera_chuong)
    2. Chụp snapshot
    3. alert_service.send_photo(token, chat_id, snapshot, caption)
    4. Cooldown 60s cho cặp (cow_i, cow_j)
```

**Code nghiệp vụ mẫu:**
```python
# Tiếp theo trong bll/services/alert_service.py

IOU_THRESHOLD = 0.10    # Bounding box giao nhau 10%+
VEL_THRESHOLD = 40.0    # px/s tương đối

prev_centroids: dict[str, tuple] = {}   # cow_id → (cx, cy)


def check_fight(bboxes: list[dict], id_camera: int, id_user: int, dt: float = 0.033):
    """
    Kiểm tra húc nhau giữa tất cả cặp bò trong frame.
    bboxes: [{"id": "42", "x1":..., "y1":..., "x2":..., "y2":...}, ...]
    dt: thời gian giữa 2 frame (giây), mặc định 1/30s = 33ms
    """
    import math, time

    # 1. Tính centroid và velocity cho từng bò
    centroids = {}
    velocities = {}
    for b in bboxes:
        cid = b["id"]
        cx = (b["x1"] + b["x2"]) / 2
        cy = (b["y1"] + b["y2"]) / 2
        centroids[cid] = (cx, cy)

        if cid in prev_centroids:
            px, py = prev_centroids[cid]
            dist = math.sqrt((cx-px)**2 + (cy-py)**2)
            velocities[cid] = dist / dt   # px/s
        else:
            velocities[cid] = 0.0

    prev_centroids.update(centroids)

    # 2. Kiểm tra từng cặp (i, j)
    with _tracker_lock:
        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                bi, bj = bboxes[i], bboxes[j]
                ci, cj = bi["id"], bj["id"]

                iou = compute_iou(bi, bj)
                rel_vel = velocities.get(ci, 0) + velocities.get(cj, 0)

                if iou > IOU_THRESHOLD and rel_vel > VEL_THRESHOLD:
                    pair_key = f"fight_{min(ci,cj)}_{max(ci,cj)}"
                    last = alert_cooldown.get(pair_key, 0)
                    if time.time() - last < ALERT_COOLDOWN_SECONDS:
                        continue

                    alert_cooldown[pair_key] = time.time()
                    create_alert("cow_fight", id_user, id_camera)

                    def _send(cow_i=ci, cow_j=cj, v=rel_vel):
                        from bll.services.telegram_alert import send_cow_alert
                        send_cow_alert("cow_fight", camera_id=id_camera,
                                       extra={"cow_i": cow_i, "cow_j": cow_j,
                                              "velocity": round(v, 1)})
                    threading.Thread(target=_send, daemon=True).start()


def compute_iou(b1: dict, b2: dict) -> float:
    """Tính Intersection over Union giữa 2 bounding box."""
    x_left   = max(b1["x1"], b2["x1"])
    y_top    = max(b1["y1"], b2["y1"])
    x_right  = min(b1["x2"], b2["x2"])
    y_bottom = min(b1["y2"], b2["y2"])

    if x_right < x_left or y_bottom < y_top:
        return 0.0   # Không giao nhau

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = (b1["x2"] - b1["x1"]) * (b1["y2"] - b1["y1"])
    area2 = (b2["x2"] - b2["x1"]) * (b2["y2"] - b2["y1"])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0
```

---

## 9. Telegram Alert Service (Phase 4)

### 9.1 Gửi tin nhắn & ảnh

```python
# bll/services/telegram_alert.py (Phase 4)
import os, json, requests, threading
from datetime import datetime
from typing import Optional
from dal.canh_bao_repo import get_by_user

# Config bot đọc từ app_config.json
def _get_bot_config() -> dict:
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "dal", "db", "app_config.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("telegram", {"bot_token": "", "chat_id": ""})
    except Exception:
        return {"bot_token": "", "chat_id": ""}


def send_message(token: str, chat_id: str, message: str) -> dict:
    """Gửi text message HTML đến Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_photo(token: str, chat_id: str, image_path: str, caption: str = "") -> dict:
    """Gửi ảnh kèm caption HTML đến Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    if not os.path.exists(image_path):
        return {"ok": False, "error": f"File not found: {image_path}"}
    try:
        with open(image_path, "rb") as img:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"photo": img},
                timeout=20,   # Timeout lớn hơn vì upload ảnh
            )
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_cow_alert(alert_type: str, cow_id: str = None,
                   camera_id: int = None, extra: dict = None):
    """
    Hàm tổng hợp — tự xây caption theo loại cảnh báo và gửi Telegram.
    alert_type: "cow_lie" | "cow_fight"
    """
    bot_cfg = _get_bot_config()
    token   = bot_cfg.get("bot_token", "")
    chat_id = bot_cfg.get("chat_id", "")

    if not token or not chat_id:
        print("[AlertService] Bot token hoặc chat_id chưa cấu hình.")
        return

    extra = extra or {}
    now   = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    if alert_type == "cow_lie":
        duration = extra.get("duration_min", "?")
        caption = f"""🐄 <b>CẢNH BÁO: BÒ BỎ ĂN!</b>

⏰ <b>Thời gian:</b> {now}
🆔 <b>ID Bò:</b> #{cow_id}
📍 <b>Camera:</b> CAM-{camera_id:02d}
⏱️ <b>Nằm liên tục:</b> {duration} phút trong giờ ăn
🩺 <b>Khuyến nghị:</b> Kiểm tra sức khoẻ ngay

<i>Hệ thống Con Bò Cười tự động phát hiện</i>"""

    elif alert_type == "cow_fight":
        cow_i = extra.get("cow_i", "?")
        cow_j = extra.get("cow_j", "?")
        vel   = extra.get("velocity", "?")
        caption = f"""🚨 <b>CẢNH BÁO KHẨN: BÒ HÚC NHAU!</b>

⏰ <b>Thời gian:</b> {now}
🆔 <b>Cặp bò:</b> #{cow_i} ↔ #{cow_j}
📍 <b>Camera:</b> CAM-{camera_id:02d}
⚡ <b>Vận tốc va chạm:</b> {vel} px/s
⚠️ <b>Mức độ:</b> 🔴 Khẩn cấp — Can thiệp ngay!

<i>Hệ thống Con Bò Cười tự động phát hiện</i>"""
    else:
        return

    # Lấy snapshot nếu có (gọi _camera_capture.py subprocess)
    snapshot_path = _take_snapshot_local()
    if snapshot_path:
        send_photo(token, chat_id, snapshot_path, caption)
        os.unlink(snapshot_path)    # Xóa file tạm sau khi gửi
    else:
        send_message(token, chat_id, caption)    # Fallback text-only


def _take_snapshot_local() -> Optional[str]:
    """Gọi subprocess _camera_capture.py để chụp ảnh local."""
    import subprocess, sys
    script = os.path.join(
        os.path.dirname(__file__), "..", "..", "ui",
        "components", "user", "framer", "_camera_capture.py"
    )
    try:
        result = subprocess.run(
            [sys.executable, script, "0"],  # camera_index=0
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        return data.get("path")
    except Exception:
        return None
```

---

### 9.2 Telegram Bot Long Polling (Phase 4)

```python
# bll/services/telegram_bot.py (Phase 4)
import time, threading, requests
from bll.services.telegram_alert import send_message, _get_bot_config

_bot_started = False
_bot_lock    = threading.Lock()


def _polling_loop():
    """Vòng lặp long-polling nhận lệnh từ Telegram."""
    bot_cfg = _get_bot_config()
    token   = bot_cfg.get("bot_token", "")

    if not token:
        print("[CowBot] Bot token chưa cấu hình.")
        return

    last_id = 0
    print("[CowBot] Bot khởi động — bắt đầu long polling...")

    while True:
        try:
            url    = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": last_id + 1, "timeout": 30}
            resp   = requests.get(url, params=params, timeout=35)
            result = resp.json()

            if not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                uid = update.get("update_id", 0)
                if uid > last_id:
                    last_id = uid

                # Xử lý command
                message = update.get("message", {})
                text    = message.get("text", "")
                chat_id = str(message.get("chat", {}).get("id", ""))

                if text.startswith("/") and chat_id:
                    reply = _handle_command(text, chat_id, token)
                    if reply:
                        send_message(token, chat_id, reply)

        except requests.exceptions.Timeout:
            continue        # Long polling timeout bình thường
        except Exception as e:
            print(f"[CowBot] Lỗi: {e}")
            time.sleep(5)


def _handle_command(text: str, chat_id: str, token: str) -> str:
    """Xử lý các lệnh Telegram bot."""
    cmd = text.strip().lower().split()[0]

    if cmd == "/start":
        return """🐄 <b>Hệ thống Con Bò Cười</b>

Chào mừng đến với bot giám sát đàn bò!

<b>📋 Lệnh có sẵn:</b>
/status - Trạng thái hệ thống
/herd - Tình trạng đàn bò hiện tại
/alerts - Danh sách cảnh báo chưa xử lý
/report - Báo cáo cảnh báo hôm nay
/alert_on - Bật cảnh báo
/alert_off - Tắt cảnh báo
/ping - Kiểm tra kết nối"""

    elif cmd == "/ping":
        return "🏓 Pong! Bot đang hoạt động bình thường."

    elif cmd == "/status":
        from dal.canh_bao_repo import count_open
        from dal.camera_chuong_repo import get_all_cameras
        open_alerts = count_open()
        cameras     = get_all_cameras()
        online_cams = sum(1 for c in cameras if c.get("trang_thai") == "online")
        return f"""📊 <b>Trạng thái Hệ thống</b>

🔹 <b>Cảnh báo chưa xử lý:</b> {open_alerts}
🔹 <b>Camera trực tuyến:</b> {online_cams}/{len(cameras)}
🔹 <b>Thời gian:</b> {__import__('datetime').datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"""

    elif cmd == "/alerts":
        from dal.canh_bao_repo import get_by_status
        alerts = get_by_status("CHUA_XU_LY")
        if not alerts:
            return "✅ Không có cảnh báo nào chưa xử lý."
        lines = []
        for a in alerts[-5:]:   # Hiển thị tối đa 5 cảnh báo gần nhất
            loai  = "🐄 Bỏ ăn" if a["loai_canh_bao"] == "cow_lie" else "⚡ Húc nhau"
            cam   = a.get("id_camera_chuong", "?")
            time_ = a.get("created_at", "?")[:16].replace("T", " ")
            lines.append(f"• {loai} | CAM-{cam} | {time_}")
        return "🚨 <b>Cảnh báo chưa xử lý:</b>\n\n" + "\n".join(lines)

    elif cmd == "/alert_on":
        return "🔔 Đã <b>BẬT</b> cảnh báo."

    elif cmd == "/alert_off":
        return "🔕 Đã <b>TẮT</b> cảnh báo."

    else:
        return "❓ Lệnh không hợp lệ. Dùng /start để xem danh sách lệnh."


def start_bot():
    """Khởi động bot trong background daemon thread (singleton)."""
    global _bot_started
    with _bot_lock:
        if _bot_started:
            return
        _bot_started = True
    threading.Thread(target=_polling_loop, daemon=True).start()
```

---

## 10. Liên kết tài khoản Telegram (Token Flow)

```python
# bll/services/telegram_link.py (Phase 4)
import uuid, json, os, threading
from datetime import datetime, timedelta

TOKEN_FILE   = "dal/db/telegram_tokens.json"
TOKEN_TTL_HR = 24           # Token hết hạn sau 24 giờ
_lock        = threading.Lock()


def generate_token(username: str) -> str:
    """
    Tạo token UUID cho user để liên kết Telegram.
    Xóa token cũ của user trước khi tạo mới.
    """
    with _lock:
        data = _load_tokens()
        # Xóa token cũ của user này
        data["tokens"] = {
            t: info for t, info in data["tokens"].items()
            if info.get("username") != username
        }
        token = str(uuid.uuid4())
        now   = datetime.now()
        data["tokens"][token] = {
            "username":   username,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": (now + timedelta(hours=TOKEN_TTL_HR)).strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_tokens(data)
        return token


def validate_token(token: str) -> str | None:
    """
    Validate token. Trả về username nếu hợp lệ.
    Token bị XÓA ngay sau khi validate (one-time use).
    """
    with _lock:
        data = _load_tokens()
        if token not in data["tokens"]:
            return None

        info       = data["tokens"][token]
        expires_at = datetime.strptime(info["expires_at"], "%Y-%m-%d %H:%M:%S")

        if datetime.now() > expires_at:
            del data["tokens"][token]   # Xóa token hết hạn
            _save_tokens(data)
            return None

        username = info.get("username")
        del data["tokens"][token]       # ONE-TIME: xóa sau khi dùng
        _save_tokens(data)
        return username


def bind_telegram(username: str, chat_id: str, tg_username: str = "") -> bool:
    """
    Ghi chat_id vào record tài khoản.
    Dùng tai_khoan_repo để update.
    """
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    if user.get("telegram_chat_id"):
        return False    # Đã liên kết rồi

    update_user(user["id_user"], {
        "telegram_chat_id": chat_id,
        "telegram_username": tg_username,
        "telegram_linked_at": datetime.now().isoformat(),
    })
    return True
```

**Luồng liên kết đầy đủ:**
```
[Farmer nhấn "Liên kết Telegram" trong Settings screen]
          ↓
generate_token(username)        → token = "a3f8e2b1-..."
          ↓
UI hiển thị deep-link:
"https://t.me/cow_alert_bot?start=a3f8e2b1-..."
          ↓
[Farmer click link trên điện thoại → mở Telegram]
          ↓
Bot nhận update: text="/start a3f8e2b1-..."
          ↓
_handle_command("/start a3f8e2b1-...", chat_id="7905261972")
          ↓
validate_token("a3f8e2b1-...")  → username = "farm_nguyen"
          ↓
bind_telegram("farm_nguyen", "7905261972", "@nguyen_tb")
  → tai_khoan_repo.update(id_user, {"telegram_chat_id": "7905261972"})
          ↓
Bot reply: "✅ Liên kết thành công! Bạn sẽ nhận cảnh báo bò..."
```

---

## 11. Cấu trúc Data Files

### `dal/db/app_config.json`
```json
{
  "server_url": "http://127.0.0.1:8000",
  "camera_index": 0,
  "auto_connect": false,
  "notify_alert": true,
  "app_mode": "desktop",
  "app_port": 8080,
  "yolo_model_mode": "cpu",
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "7905261972",
    "bot_name": "cow_alert_bot"
  },
  "thresholds": {
    "lying_duration_minutes": 30,
    "fight_iou_threshold": 0.10,
    "fight_velocity_threshold": 40.0,
    "alert_cooldown_seconds": 60,
    "feeding_hours": [[6, 8], [16, 18]]
  }
}
```

### `dal/db/monitor_cache.json`
```json
{
  "total_cows": 42,
  "active_alerts": 3,
  "cameras_online": 2,
  "timestamp": "2026-04-19 22:30:00",
  "recent_alerts": [
    {"time": "22:28", "type": "cow_fight", "camera": "CAM-01"},
    {"time": "22:15", "type": "cow_lie",   "camera": "CAM-03"}
  ]
}
```

---

## 12. Luồng End-to-End Hoàn chỉnh

```
[App khởi động]
      ↓
dal.init_all()                          ← Seed JSON tables
      ↓
main.py → show_login()
      ↓
auth_service.login(user, pwd, page)     ← SHA-256 + rate limit
      ↓
show_dashboard(role="farmer")
      ↓
FarmerMainScreen → live_monitoring.build_live_monitoring()
      ↓
  [LiveMonitoringController.__init__]
      ↓
  load_config() → server_url, auto_connect
      ↓
  [Farmer nhấn "Kết nối máy chủ"]
      ↓
  toggle_connection → threading.Thread(_connect)
      ↓
  fetch_dashboard("http://127.0.0.1:8000")
    GET /api/dashboard → {total_cows, active_alerts, ...}
      ↓
  save_cache(data)                      ← Lưu offline fallback
  _apply_dashboard_data(data)           ← Cập nhật KPI UI
  _start_polling()                      ← Daemon thread poll mỗi 5s
      ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Máy chủ AI phát hiện hành vi bất thường]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      ↓
  cattle_detect + behavior model inference per frame
      ↓
    ┌──────────────┐       ┌───────────────────┐
    │  cow_lie     │       │   cow_fight        │
    │  (Lying>30m  │       │  (IoU>0.1 AND      │
    │  in feeding  │       │   velocity>40px/s) │
    │  hour)       │       │                    │
    └──────┬───────┘       └────────┬───────────┘
           └──────────┬────────────┘
                      ↓
  canh_bao_repo.create_alert(loai, id_user, id_camera)
    → INSERT vào canh_bao_su_co.json
    → trang_thai = "CHUA_XU_LY"
                      ↓
  _take_snapshot_local()
    → subprocess python _camera_capture.py 0
    → cv2.VideoCapture → grab 5 frames → cv2.imwrite → /tmp/cam_snap_xxx.jpg
                      ↓
  send_photo(token, chat_id, snapshot_path, caption)
    → POST /sendPhoto multipart Telegram API
    → os.unlink(snapshot_path)            ← Dọn file tạm
                      ↓
  [Farmer nhận ảnh + cảnh báo trên Telegram]
                      ↓
  [Farmer gõ /alerts vào bot]
                      ↓
  Long polling nhận, _handle_command("/alerts")
    → canh_bao_repo.get_by_status("CHUA_XU_LY")
    → Reply danh sách cảnh báo chưa xử lý
                      ↓
  [Farmer xử lý → /resolve {id}]
    → canh_bao_repo.resolve_alert(id)
    → tráng_thai: "CHUA_XU_LY" → "DA_XU_LY"
                      ↓
    ↺ Polling loop tiếp tục mỗi 5s...
```

---

## 13. Bảng API Endpoints (Máy chủ AI — Phase 3/4)

| Method | Endpoint | Mô tả | Response |
|--------|----------|-------|----------|
| `GET` | `/api/dashboard` | Dashboard KPI + log cảnh báo gần nhất | `{total_cows, active_alerts, cameras_online, timestamp, recent_alerts[]}` |
| `GET` | `/api/stream` | MJPEG video stream | `multipart/x-mixed-replace` |
| `GET` | `/api/snapshot` | Chụp ảnh tĩnh | `image/jpeg` bytes |
| `POST` | `/api/alert` | (Internal) Máy chủ AI push cảnh báo | `{ok: true}` |
| `GET` | `/api/health` | Kiểm tra máy chủ AI còn chạy | `{status: "ok"}` |

---

## 14. Điểm kỹ thuật cần lưu ý khi implement Phase 4

| # | Vấn đề | Giải pháp |
|---|--------|----------|
| 1 | **Subprocess crash Windows** | `ctypes.windll.kernel32.SetErrorMode(0x8007)` — đã có trong `_camera_capture.py` |
| 2 | **Flutter renderer crash với base64 lớn** | Dùng `tempfile` + path thay vì base64 trong `_camera_capture.py` |
| 3 | **Thread safety `behavior_tracker`** | `threading.Lock()` bảo vệ mọi read/write |
| 4 | **Bò đứng gần nhau ≠ húc nhau** | `velocity gate` — cần CẢ IoU cao VÀ velocity cao mới trigger |
| 5 | **Alert spam** | `alert_cooldown` dict — per cow_id (lie) hoặc per pair (fight), 60s TTL |
| 6 | **Feeding hour hardcode** | Configurable trong `app_config.json["thresholds"]["feeding_hours"]` |
| 7 | **Bot token không có** | `send_message` / `send_photo` trả về `{"ok": False}` — không throw exception |
| 8 | **Offline cache** | `monitor_cache.json` — luôn lưu sau mỗi poll thành công, load khi mất kết nối |
| 9 | **PostgreSQL migration** | Chỉ cần thay `BaseRepo` — toàn bộ `*_repo.py` giữ nguyên interface |
| 10 | **Long polling daemon** | `daemon=True` — thread tự chết khi main process exit, không cần cleanup |


##Luồng liên kết OA_chatID

10. Liên kết tài khoản Telegram (Token Flow) - ĐÃ HOÀN THIỆN
10.1 Mục tiêu
Cho phép farmer liên kết tài khoản Telegram cá nhân để nhận cảnh báo realtime (ảnh + text).
10.2 Luồng nghiệp vụ
textFarmer → Settings → "Liên kết Telegram"
          ↓
generate_token(username) → tạo UUID token (hết hạn 24h, one-time)
          ↓
UI hiển thị: 
   • Token + hướng dẫn
   • Hoặc Deep Link: https://t.me/Cattle_Farm_Bot?start=xxxxxxxx
          ↓
User mở Telegram → gõ /start <token>
          ↓
Bot (long polling) → validate_token(token)
          ↓
✅ Thành công → bind_telegram(username, chat_id)
          ↓
Cập nhật vào tai_khoan_repo: telegram_chat_id, telegram_username, telegram_linked_at
          ↓
Bot reply: "✅ Liên kết thành công! Bạn sẽ nhận cảnh báo từ hệ thống."
10.3 File chính: bll/services/telegram_link_service.py
Python# bll/services/telegram_link_service.py
import uuid, json, os, threading
from datetime import datetime, timedelta
from pathlib import Path

TOKEN_FILE = Path("dal/db/telegram_tokens.json")
TOKEN_TTL_HOURS = 24
_lock = threading.Lock()

def _load_tokens():
    if not TOKEN_FILE.exists():
        return {"tokens": {}}
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_tokens(data):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_token(username: str) -> str:
    """Tạo token liên kết mới"""
    with _lock:
        data = _load_tokens()
        # Xóa token cũ của user
        data["tokens"] = {t: info for t, info in data["tokens"].items() 
                         if info.get("username") != username}
        
        token = str(uuid.uuid4())
        now = datetime.now()
        data["tokens"][token] = {
            "username": username,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=TOKEN_TTL_HOURS)).isoformat(),
        }
        _save_tokens(data)
        return token


def validate_token(token: str) -> str | None:
    """Validate và xóa token (one-time use)"""
    with _lock:
        data = _load_tokens()
        if token not in data["tokens"]:
            return None

        info = data["tokens"][token]
        if datetime.fromisoformat(info["expires_at"]) < datetime.now():
            del data["tokens"][token]
            _save_tokens(data)
            return None

        username = info["username"]
        del data["tokens"][token]   # Xóa ngay sau khi dùng
        _save_tokens(data)
        return username


def bind_telegram(username: str, chat_id: str, tg_username: str = "") -> bool:
    """Lưu chat_id vào tài khoản user"""
    from dal.tai_khoan_repo import get_user_by_username, update_user
    
    user = get_user_by_username(username)
    if not user:
        return False
    if user.get("telegram_chat_id"):
        return False  # Đã liên kết rồi

    update_user(user["id_user"], {
        "telegram_chat_id": chat_id,
        "telegram_username": tg_username,
        "telegram_linked_at": datetime.now().isoformat(),
    })
    return True
10.4 Tích hợp vào telegram_bot.py
Trong hàm _handle_command:
Pythonelif text.startswith("/start "):
    token = text.split(maxsplit=1)[1].strip()
    username = validate_token(token)
    if username:
        # Lấy chat_id và username telegram
        tg_user = message.get("from", {})
        tg_username = tg_user.get("username", "")
        if bind_telegram(username, str(chat_id), tg_username):
            return "✅ <b>Liên kết Telegram thành công!</b>\n\nBạn sẽ nhận được cảnh báo từ hệ thống Con Bò Cười."
        else:
            return "❌ Tài khoản đã được liên kết trước đó."
    else:
        return "❌ Token không hợp lệ hoặc đã hết hạn. Vui lòng tạo link mới tron