<div align="center">

<a href="#english-version">🇬🇧 English</a> · <a href="#vietnamese-version">🇻🇳 Tiếng Việt</a>

<br/>

<img src="img/header_composite.jpg" alt="Con Bò Cười — HD LGBT" width="760" />

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flet](https://img.shields.io/badge/Flet-0.28.3-00A8E8?style=flat-square)](https://flet.dev)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-FF6B35?style=flat-square)](https://ultralytics.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/ngngochieuu05/Con_Bo_Cuoi?style=flat-square)](https://github.com/ngngochieuu05/Con_Bo_Cuoi/issues)
[![Last Commit](https://img.shields.io/github/last-commit/ngngochieuu05/Con_Bo_Cuoi?style=flat-square)](https://github.com/ngngochieuu05/Con_Bo_Cuoi/commits)

</div>

---

<a id="english-version"></a>

## 🇬🇧 English

> A cross-platform desktop/web application for real-time cattle herd monitoring — detecting abnormal behavior, disease alerts, and connecting farmers with veterinary experts through AI.

### ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **YOLO Cattle Detection** | Detect and localize each cow in real-time via camera |
| 🧠 **Behavior Classification** | Auto-classify: lying, fighting, heat stress, anomalies |
| 🚨 **Disease Alerts** | AI flags disease signs and sends instant alerts |
| 👥 **3 User Roles** | Admin, Expert, Farmer — each with a dedicated dashboard |
| 💬 **AI Consulting** | Farmers chat with AI + send camera snapshots for review |
| 📊 **Analytics Dashboard** | KPI cards, alert charts, session history |
| 🖥️ **Desktop + Web** | Offline desktop app or LAN web deployment |
| 🔌 **Camera Integration** | USB camera, IP camera, snapshot & live stream support |

### 🏗️ Architecture

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

### 🤖 AI Models

| Model | Level | Function |
|-------|-------|----------|
| `cattle_detect` | User-level | Detect & localize cattle (bounding boxes) |
| `behavior` | User-level | Classify behavior (lying, standing, fighting...) |
| `disease` | System-level | Disease sign detection (admin-managed) |

Config params: `conf` (0.05–0.95) · `iou` (0.05–0.95) · `.pt` model file path

### 📦 Installation

**Requirements:** Python 3.14+ · Windows 10/11 (desktop) or Linux/macOS (web) · Webcam / IP Camera (optional) · GPU CUDA (recommended)

```bash
# 1. Clone
git clone https://github.com/ngngochieuu05/Con_Bo_Cuoi.git
cd Con_Bo_Cuoi

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r webapp_system/requirements.txt

# GPU (CUDA 12.x)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# CPU only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics

# 4. Run
python webapp_system/src/main.py
```

**Web mode** — edit `webapp_system/src/dal/db/app_config.json`:

```json
{ "app_mode": "web", "app_port": 8080 }
```

### 📁 Project Structure

```
Con_Bo_Cuoi/
├── webapp_system/
│   ├── requirements.txt
│   └── src/
│       ├── main.py                  # Entry point
│       ├── bll/services/            # Business logic
│       │   ├── auth_service.py      # Login, logout, session
│       │   └── monitor_service.py   # YOLO config, camera, AI calls
│       ├── dal/                     # Data access layer
│       │   ├── base_repo.py         # Generic CRUD (JSON / DB-ready)
│       │   └── db/                  # Runtime JSON files (gitignored)
│       └── ui/
│           ├── theme.py             # Design tokens + shared components
│           └── components/
│               ├── auth/            # Login, register, forgot password
│               ├── admin/           # Dashboard, user/model/camera mgmt
│               └── user/
│                   ├── expert/      # Consulting, data review
│                   └── framer/      # Live monitoring, health consulting
└── docs/                            # Technical documentation
```

### 🎨 Design System

All UI uses **Glassmorphism** + **Airbnb button style**, centralized in `ui/theme.py`:

```python
from ui.theme import glass_container, button_style, build_role_shell

glass_container(content=my_widget, padding=24, radius=28)
ft.ElevatedButton("Submit", style=button_style("primary"))
build_role_shell(page, role="farmer", content=my_screen)
```

> Always use `ft.Colors.*` and `ft.Icons.*` (uppercase). Never inline glass styles.

### 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.14 |
| UI Framework | [Flet](https://flet.dev) 0.28.3 |
| Computer Vision | OpenCV 4.13+ |
| AI/ML | YOLOv8 (Ultralytics) · PyTorch |
| Image Processing | Pillow 12+ · NumPy 2.4+ |
| Data Storage | JSON (dev) · PostgreSQL-ready |
| Auth | SHA-256 hashing · session via page.data |

### 🗺️ Roadmap

- [x] **Phase 1** — MVP: Auth, Admin CRUD, basic UI
- [x] **Phase 2** — Expert UI: Consulting dashboard, AI insights
- [ ] **Phase 3** — YOLO integration: Live detection, behavior alerts
- [ ] **Phase 4** — Alert system: Real-time notifications, case workflows
- [ ] **Phase 5** — Production: PostgreSQL, deployment, performance
- [ ] **Phase 6** — Community: Plugin ecosystem, open API

### 🔒 Security

We take security seriously. Please read our full [Security Policy](SECURITY.md) before reporting.

**Quick summary:**

- **Do NOT** open a public GitHub issue for vulnerabilities — email maintainers directly
- Passwords hashed with SHA-256 · sessions cleared on logout · no credentials in repo
- Default seed accounts use weak passwords — **change before any production deployment**

→ See [SECURITY.md](SECURITY.md) for supported versions, reporting instructions, and known limitations.

### 🤝 Contributing

Contributions of all kinds are welcome — bug fixes, features, docs, and tests.

#### Getting Started

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/<your-username>/Con_Bo_Cuoi.git
cd Con_Bo_Cuoi

# 3. Create a feature branch
git checkout -b feat/your-feature-name

# 4. Set up the dev environment
python -m venv .venv && .venv\Scripts\activate
pip install -r webapp_system/requirements.txt
```

#### Development Rules

| Rule | Detail |
|------|--------|
| **File size** | Max 200 LOC per file — split larger files |
| **Flet API** | Use `ft.Colors.*` / `ft.Icons.*` (uppercase only) |
| **UI components** | Always use helpers from `ui/theme.py` — no inline styles |
| **File naming** | kebab-case for Python/JS/shell files |
| **Commits** | Follow [Conventional Commits](https://conventionalcommits.org) |
| **Language** | Code, comments, and commit messages in English |

#### Commit Message Format

```
feat: add live camera snapshot for farmer dashboard
fix: resolve page.data isinstance error on web mode
docs: update system architecture diagram
refactor: split consulting_review into smaller modules
```

#### Pull Request Checklist

- [ ] Code follows the style guidelines (max 200 LOC, `ui/theme.py` helpers)
- [ ] No hardcoded credentials or secrets
- [ ] Tested on desktop mode (Windows)
- [ ] PR description clearly explains the change and motivation
- [ ] Linked to a relevant issue (if applicable)

#### Reporting Bugs

Open an [issue](https://github.com/ngngochieuu05/Con_Bo_Cuoi/issues) and include:

- Steps to reproduce
- Expected vs actual behavior
- Python version, OS, and Flet version
- Screenshots or error logs (if applicable)

### 👥 Team

| Member | Role |
|--------|------|
| **Tran Tan Dat** | Developer — Expert UI, YOLO integration |
| **Nguyen Ngoc Hieu** | Developer — Farmer UI, Auth |

### 📄 License

Distributed under the **MIT License** — see [LICENSE](LICENSE) for full text.

---

<a id="vietnamese-version"></a>

## 🇻🇳 Tiếng Việt

> Ứng dụng desktop/web đa nền tảng giám sát đàn bò theo thời gian thực — phát hiện hành vi bất thường, cảnh báo dịch bệnh và kết nối chuyên gia thú y qua AI.

### ✨ Tính năng nổi bật

| Tính năng | Mô tả |
|-----------|-------|
| 🎯 **Phát hiện bò bằng YOLO** | Nhận diện và khoanh vùng từng con bò qua camera thời gian thực |
| 🧠 **Phân loại hành vi** | Tự động nhận diện: nằm, đánh nhau, stress nhiệt, bất thường |
| 🚨 **Cảnh báo dịch bệnh** | AI phát hiện dấu hiệu bệnh và gửi alert ngay lập tức |
| 👥 **3 vai trò người dùng** | Admin, Chuyên gia, Nông dân — giao diện riêng biệt |
| 💬 **Tư vấn AI** | Farmer chat với AI + gửi ảnh chụp từ camera để xem xét |
| 📊 **Dashboard analytics** | KPI cards, biểu đồ cảnh báo, lịch sử phiên giám sát |
| 🖥️ **Desktop + Web** | Chạy offline (desktop) hoặc triển khai web qua LAN |
| 🔌 **Tích hợp Camera** | Hỗ trợ USB, IP camera, snapshot và live stream |

### 📦 Cài đặt

**Yêu cầu:** Python 3.14+ · Windows 10/11 (desktop) hoặc Linux/macOS (web) · Camera (tùy chọn) · GPU CUDA (khuyến nghị)

```bash
# 1. Clone
git clone https://github.com/ngngochieuu05/Con_Bo_Cuoi.git
cd Con_Bo_Cuoi

# 2. Tạo môi trường ảo
python -m venv .venv && .venv\Scripts\activate

# 3. Cài đặt thư viện
pip install -r webapp_system/requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install ultralytics

# 4. Chạy ứng dụng
python webapp_system/src/main.py
```

**Web mode** — chỉnh `webapp_system/src/dal/db/app_config.json`:

```json
{ "app_mode": "web", "app_port": 8080 }
```

### 🔒 Bảo mật

Xem chính sách bảo mật đầy đủ tại [SECURITY.md](SECURITY.md).

**Tóm tắt:**

- **Không** mở public issue — liên hệ maintainers trực tiếp qua email
- Mật khẩu hash SHA-256 · session xóa khi đăng xuất · không commit credential
- Tài khoản seed mặc định có mật khẩu yếu — **thay đổi trước khi deploy production**

→ Xem [SECURITY.md](SECURITY.md) để biết phiên bản được hỗ trợ, hướng dẫn báo cáo, và các giới hạn đã biết.

### 🤝 Đóng góp

```bash
# 1. Fork repo trên GitHub
# 2. Clone fork của bạn
git clone https://github.com/<username>/Con_Bo_Cuoi.git

# 3. Tạo nhánh tính năng
git checkout -b feat/ten-tinh-nang

# 4. Commit và push
git commit -m "feat: mô tả thay đổi"
git push origin feat/ten-tinh-nang
# → Tạo Pull Request
```

**Quy tắc phát triển:**

- Tối đa 200 dòng code mỗi file
- Dùng `ft.Colors.*` / `ft.Icons.*` (chữ hoa)
- Mọi UI component phải dùng helpers từ `ui/theme.py`
- Tên file theo kebab-case
- Commit theo [Conventional Commits](https://conventionalcommits.org)

**Báo cáo lỗi:** Mở [issue](https://github.com/ngngochieuu05/Con_Bo_Cuoi/issues) kèm: bước tái hiện lỗi, kết quả mong đợi vs thực tế, phiên bản Python/OS/Flet, screenshot hoặc log lỗi.

### 🗺️ Lộ trình phát triển

- [x] **Phase 1** — MVP: Xác thực, quản lý Admin, UI cơ bản
- [x] **Phase 2** — UI Chuyên gia: Dashboard tư vấn, AI insights
- [ ] **Phase 3** — YOLO: Phát hiện trực tiếp, cảnh báo hành vi
- [ ] **Phase 4** — Alert system: Thông báo thời gian thực
- [ ] **Phase 5** — Production: PostgreSQL, triển khai, hiệu năng
- [ ] **Phase 6** — Cộng đồng: Plugin ecosystem, open API

### 📄 Giấy phép

Phân phối dưới **MIT License** — xem file [LICENSE](LICENSE).

---

<div align="center">

Made with ❤️ by the Con Bò Cười team

⭐ Nếu dự án hữu ích, hãy để lại một star!

[🔝 Back to top](#)

</div>
