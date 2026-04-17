<div align="center">

# 🐄 Con Bò Cưới

**Hệ thống giám sát bò thông minh bằng AI**

_AI-Powered Cattle Monitoring System_

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flet](https://img.shields.io/badge/Flet-0.28.3-00A8E8?style=flat-square)](https://flet.dev)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-FF6B35?style=flat-square)](https://ultralytics.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/ngngochieuu05/Con_Bo_Cuoi?style=flat-square)](https://github.com/ngngochieuu05/Con_Bo_Cuoi/issues)
[![Last Commit](https://img.shields.io/github/last-commit/ngngochieuu05/Con_Bo_Cuoi?style=flat-square)](https://github.com/ngngochieuu05/Con_Bo_Cuoi/commits)

<br/>

> Ứng dụng desktop/web đa nền tảng giám sát đàn bò theo thời gian thực — phát hiện hành vi bất thường, cảnh báo dịch bệnh và kết nối chuyên gia thú y qua AI.

</div>

---

## ✨ Tính năng nổi bật

| Tính năng | Mô tả |
|-----------|-------|
| 🎯 **Phát hiện bò bằng YOLO** | Nhận diện và khoanh vùng từng con bò qua camera thời gian thực |
| 🧠 **Phân loại hành vi** | Tự động nhận diện: nằm, đánh nhau, stress nhiệt, bất thường |
| 🚨 **Cảnh báo dịch bệnh** | AI phát hiện dấu hiệu bệnh và gửi alert ngay lập tức |
| 👥 **3 vai trò người dùng** | Admin, Chuyên gia (Expert), Nông dân (Farmer) — giao diện riêng biệt |
| 💬 **Tư vấn AI** | Farmer chat trực tiếp với AI + gửi ảnh chụp từ camera |
| 📊 **Dashboard analytics** | KPI cards, biểu đồ cảnh báo, lịch sử phiên giám sát |
| 🖥️ **Desktop + Web** | Chạy offline (desktop) hoặc triển khai web qua LAN |
| 🔌 **Camera tích hợp** | Hỗ trợ camera USB, IP camera, snapshot và live stream |

---

## 🖼️ Giao diện

<div align="center">

| Admin Dashboard | Expert Consulting | Farmer Monitoring |
|:-:|:-:|:-:|
| Quản lý người dùng, model AI, camera | Review ca bệnh, phân tích dữ liệu | Xem trực tiếp, tư vấn sức khỏe |

</div>

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                      UI Layer                           │
│  admin/   expert/   farmer/   auth/   theme.py          │
│  Glassmorphism UI · Airbnb buttons · Role-based shell   │
├─────────────────────────────────────────────────────────┤
│                   BLL Layer (Services)                  │
│  auth_service.py · monitor_service.py · tu_van_ai.py   │
│  Login/logout · YOLO config · AI chat · Camera stream  │
├─────────────────────────────────────────────────────────┤
│                   DAL Layer (Repos)                     │
│  base_repo.py · *_repo.py · dal/db/*.json              │
│  JSON store → PostgreSQL-ready (swap base_repo only)   │
└─────────────────────────────────────────────────────────┘
```

**3-layer architecture** — UI gọi BLL → BLL gọi DAL → DAL đọc/ghi JSON. Thiết kế để dễ dàng chuyển sang PostgreSQL chỉ bằng cách thay `base_repo.py`.

---

## 🤖 AI Models

| Model | Cấp độ | Chức năng |
|-------|--------|-----------|
| `cattle_detect` | User-level | Phát hiện & khoanh vùng bò (bounding boxes) |
| `behavior` | User-level | Phân loại hành vi (nằm, đứng, đánh nhau...) |
| `disease` | System-level | Phát hiện dấu hiệu dịch bệnh (admin quản lý) |

Cấu hình: `conf` (0.05–0.95) · `iou` (0.05–0.95) · file `.pt` model

---

## 📦 Cài đặt

### Yêu cầu hệ thống

- Python 3.14+
- Windows 10/11 (desktop mode) hoặc Linux/macOS (web mode)
- Webcam / IP Camera (tùy chọn)
- GPU CUDA (khuyến nghị cho YOLO inference)

### 1. Clone repository

```bash
git clone https://github.com/ngngochieuu05/Con_Bo_Cuoi.git
cd Con_Bo_Cuoi
```

### 2. Tạo virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r webapp_system/requirements.txt
```

> **GPU (CUDA 12.x):**
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> pip install ultralytics
> ```
>
> **CPU only:**
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
> pip install ultralytics
> ```

### 4. Chạy ứng dụng

```bash
# Desktop mode (mặc định)
python webapp_system/src/main.py
```

**Web mode** — chỉnh `webapp_system/src/dal/db/app_config.json` trước:
```json
{
  "app_mode": "web",
  "app_port": 8080
}
```
```bash
python webapp_system/src/main.py
# → http://localhost:8080
# → http://<LAN_IP>:8080  (cho thiết bị cùng WiFi)
```

---

## 🔑 Tài khoản mặc định

| Vai trò | Tên đăng nhập | Mật khẩu |
|---------|--------------|----------|
| **Admin** | `admin` | `admin123` |
| **Expert** | `expert01` | `expert123` |
| **Farmer** | `farmer01` | `farmer123` |

> ⚠️ Thay đổi mật khẩu trước khi deploy production.

---

## 📁 Cấu trúc thư mục

```
Con_Bo_Cuoi/
├── webapp_system/
│   ├── requirements.txt
│   └── src/
│       ├── main.py                  # Entry point
│       ├── bll/
│       │   └── services/
│       │       ├── auth_service.py  # Login, logout, session
│       │       └── monitor_service.py # YOLO config, camera, AI calls
│       ├── dal/
│       │   ├── base_repo.py         # Generic CRUD (JSON / DB-ready)
│       │   ├── *_repo.py            # Repo per entity
│       │   └── db/                  # Runtime JSON files (gitignored)
│       └── ui/
│           ├── theme.py             # Design tokens + shared components
│           └── components/
│               ├── auth/            # Login, register, forgot password
│               ├── admin/           # Dashboard, user/model/camera mgmt
│               └── user/
│                   ├── expert/      # Consulting, data review, dashboard
│                   └── framer/      # Live monitoring, health consulting
└── docs/                            # Tài liệu kỹ thuật
    ├── system-architecture.md
    ├── code-standards.md
    ├── design-guidelines.md
    └── project-roadmap.md
```

---

## 🎨 Design System

Toàn bộ UI dùng **Glassmorphism** + **Airbnb button style**, tập trung tại `ui/theme.py`:

```python
from ui.theme import glass_container, button_style, build_role_shell

# Frosted-glass card
glass_container(content=my_widget, padding=24, radius=28)

# Airbnb button
ft.ElevatedButton("Submit", style=button_style("primary"))

# Full app shell với header + nav
build_role_shell(page, role="farmer", content=my_screen)
```

---

## 📚 Tài liệu

| Tài liệu | Mô tả |
|----------|-------|
| [System Architecture](./docs/system-architecture.md) | Kiến trúc 3 lớp, data flow, deployment |
| [Code Standards](./docs/code-standards.md) | Convention, naming rules, review checklist |
| [Design Guidelines](./docs/design-guidelines.md) | Color tokens, components, responsive |
| [Project Roadmap](./docs/project-roadmap.md) | 6 phases từ MVP đến production |
| [Codebase Summary](./docs/codebase-summary.md) | Module reference, ER diagram |

---

## 🛠️ Tech Stack

| Thành phần | Công nghệ |
|-----------|-----------|
| **Language** | Python 3.14 |
| **UI Framework** | [Flet](https://flet.dev) 0.28.3 |
| **Computer Vision** | OpenCV 4.13+ |
| **AI/ML** | YOLOv8 (Ultralytics) · PyTorch |
| **Image Processing** | Pillow 12+ · NumPy 2.4+ |
| **Data Storage** | JSON (dev) · PostgreSQL-ready |
| **Auth** | SHA-256 hashing · session via page.data |
| **HTTP** | Requests 2.33+ |

---

## 🗺️ Roadmap

- [x] **Phase 1** — MVP: Auth, Admin CRUD, basic UI
- [x] **Phase 2** — Expert UI: Consulting dashboard, AI insights
- [ ] **Phase 3** — YOLO integration: Live detection, behavior alerts
- [ ] **Phase 4** — Alert system: Real-time notifications, case workflows
- [ ] **Phase 5** — Production: PostgreSQL, deployment, performance
- [ ] **Phase 6** — Community: Plugin ecosystem, open API

---

## 🤝 Đóng góp

Mọi đóng góp đều được hoan nghênh!

```bash
# 1. Fork repo
# 2. Tạo nhánh tính năng
git checkout -b feat/ten-tinh-nang

# 3. Commit theo conventional commits
git commit -m "feat: mô tả tính năng"

# 4. Push và tạo Pull Request
git push origin feat/ten-tinh-nang
```

**Quy tắc:**
- Mỗi file tối đa 200 dòng code
- Dùng `ft.Colors.*` và `ft.Icons.*` (uppercase) — không dùng `ft.colors.*`
- Mọi UI component phải dùng helpers từ `ui/theme.py`
- Đặt tên file theo kebab-case

---

## 👥 Nhóm phát triển

| Thành viên | Vai trò |
|-----------|---------|
| **Tran Tan Dat** | Developer — Expert UI, YOLO integration |
| **Nguyen Ngoc Hieu** | Developer — Farmer UI, Auth |

---

## 📄 License

Dự án này được phân phối dưới giấy phép **MIT**. Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

---

<div align="center">

Made with ❤️ by the Con Bò Cưới team

⭐ Nếu dự án hữu ích, hãy để lại một star!

</div>
