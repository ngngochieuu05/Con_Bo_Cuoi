# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Con Bò Cưới** — "Hệ thống giám sát bò AI": an AI-powered cattle monitoring desktop/web app built with Python + Flet. Three user roles (admin, expert, farmer) get distinct dashboards. YOLO models detect cattle, classify behavior, and flag disease.

## Running the App

```bash
# Desktop mode (default)
python webapp_system/src/main.py

# Web mode — edit webapp_system/src/dal/db/app_config.json first:
# { "app_mode": "web", "app_port": 8080 }
python webapp_system/src/main.py
```

Default seed accounts: `admin/admin123`, `expert01/expert123`, `farmer01/farmer123`.

## Architecture

All application code lives under `webapp_system/src/` in a strict 3-layer structure:

```
webapp_system/src/
├── main.py              # Entry point — page routing + role dispatch
├── bll/services/        # Business Logic Layer
│   ├── auth_service.py  # Login, logout, session helpers
│   └── monitor_service.py # Config, cache, HTTP calls to AI server
├── dal/                 # Data Access Layer (JSON file store)
│   ├── base_repo.py     # Generic CRUD: insert/update/delete/find_*
│   ├── *_repo.py        # One repo per entity (tai_khoan, camera_chuong, canh_bao, model, dataset)
│   └── db/              # Runtime JSON files (gitignored; seeded on first run)
└── ui/
    ├── theme.py          # ALL shared design tokens and reusable components
    └── components/
        ├── auth/         # login, register, forgot_password screens
        ├── admin/        # dashboard, user_management, model_management, oa_management, settings, profile
        ├── user/expert/  # dashboard, consulting_review, raw_data_review, utilities, settings, profile
        └── user/framer/  # dashboard, live_monitoring, health_consulting, session_history, utilities, settings, profile
```

**Data flow:** UI calls BLL services → BLL calls DAL repos → DAL reads/writes JSON in `dal/db/`. The DAL is designed to swap to SQLAlchemy/PostgreSQL by replacing `base_repo.py` only.

## Key Design Conventions

### UI — Glassmorphism + Airbnb buttons (`ui/theme.py`)

Every screen must use helpers from `ui/theme.py` — never inline glass styles:

| Helper | Purpose |
|--------|---------|
| `glass_container(content, ...)` | Frosted-glass card wrapper for all panels |
| `build_background(content)` | 3-layer background stack (image → dark overlay → content) |
| `build_role_shell(...)` | Full shell with header + nav + glass content area (mobile: bottom nav; desktop: sidebar) |
| `build_auth_shell(title, desc, controls)` | Auth page wrapper |
| `button_style(kind)` | Airbnb-style ButtonStyle (`"primary"`, `"secondary"`, `"surface"`, `"warning"`, `"danger"`) |
| `status_badge(label, kind)` | Colored status pill |
| `data_table(headers, rows, col_flex)` | Glassmorphism table with hover |
| `inline_field(...)` / `auth_text_field(...)` | Styled TextFields |
| `metric_card(title, value, icon, accent)` | KPI card |

### Flet API rules (version 0.82)

- **Always** use `ft.Colors.*` and `ft.Icons.*` (uppercase). The old `ft.colors.*` / `ft.icons.*` is deprecated and will raise errors.
- Use `ft.FontWeight.W_700` not the string `"bold"` or `"w700"`.
- Use `ft.border.all(...)` (lowercase module) not `ft.Border.all(...)`.
- `ft.BoxShadow` offset must be `ft.Offset(x, y)`, not a tuple.

### Camera / OpenCV (Windows)

- Always open with `cv2.VideoCapture(idx, cv2.CAP_DSHOW)` + `BUFFERSIZE=1` + `MJPG` fourcc + 5 warm-up `grab()` calls.
- **Never** call `cap.release()` on Windows — it triggers a C++ exception; let GC clean up.
- For live streaming, update Flet image via `img.src_base64 = b64_str` (pure base64, no `data:image/...` prefix). Call `page.update()` from background threads, never `control.update()`.
- Single snapshot: run `_camera_capture.py` as a subprocess with `creationflags=0x08000000` (CREATE_NO_WINDOW).
- The `SetErrorMode(0x8007)` call at the top of `main.py` suppresses Windows Error Reporting dialogs from OpenCV crashes.

### DAL / Data model

- `BaseRepo` is the only persistence class. Table name → `dal/db/{table}.json`.
- All repo files expose typed wrapper functions (`get_all_*`, `get_*_by_id`, `update_*`, etc.) — BLL never calls `BaseRepo` directly.
- Passwords are SHA-256 hashed (no salt). Field names use Vietnamese snake_case (`ten_dang_nhap`, `vai_tro`, `trang_thai`).

### AI Models

Three YOLO models stored in `dal/db/models.json`:
- `cattle_detect` — user-level, detects/locates cattle (bounding boxes)
- `behavior` — user-level, classifies behavior
- `disease` — system-level, admin-managed

YOLO config params: `conf` (0.05–0.95), `iou` (0.05–0.95), `duong_dan_file` (must end in `.pt`).

## Skill Reference Docs

Domain-specific gotchas are documented under `webapp_system/skill/`:
- `skill/bll/ai.md` — YOLO model management, DAL functions, UI patterns for model config
- `skill/ui/ui.md` — Glassmorphism workflow, Flet version notes, common syntax errors
- `skill/dal/opencv.md` — OpenCV integration with Flet on Windows, thread safety, camera patterns

## Encoding Pitfall

When writing Python files on Windows via PowerShell, `Set-Content` defaults to UTF-16LE (BOM). This causes `U+FEFF SyntaxError`. Always write with `open(path, 'w', encoding='utf-8')` from Python. Strip existing BOM with `data[3:]` if `data.startswith(b'\xef\xbb\xbf')`.
