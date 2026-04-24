# Codebase Summary — Con Bò Cưới

## Project Structure

```
Con_Bo_Cuoi/
├── webapp_system/src/
│   ├── main.py                      # Entry point, page routing, role dispatch
│   ├── bll/                         # Business Logic Layer
│   │   ├── __init__.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── auth_service.py      # Login, logout, session management
│   │       └── monitor_service.py   # Config, LAN IP, remote API stubs
│   ├── dal/                         # Data Access Layer
│   │   ├── __init__.py              # init_all() seeding orchestrator
│   │   ├── base_repo.py             # Generic JSON CRUD (PostgreSQL-ready)
│   │   ├── tai_khoan_repo.py        # User accounts
│   │   ├── camera_chuong_repo.py    # Camera-to-stall bindings
│   │   ├── canh_bao_repo.py         # Alert events
│   │   ├── model_repo.py            # YOLO configurations
│   │   ├── dataset_repo.py          # Image curation & annotations
│   │   └── db/                      # Runtime JSON files (auto-created)
│   │       ├── tai_khoan.json
│   │       ├── camera_chuong.json
│   │       ├── canh_bao_su_co.json
│   │       ├── models.json
│   │       ├── hinh_anh_dataset.json
│   │       ├── hanh_vi.json
│   │       ├── lich_su_kiem_duyet.json
│   │       ├── app_config.json
│   │       └── monitor_cache.json
│   └── ui/                          # User Interface Layer
│       ├── __init__.py
│       ├── theme.py                 # Design system (colors, components, tokens)
│       └── components/
│           ├── __init__.py
│           ├── auth/                # Login, register, forgot password
│           │   ├── __init__.py
│           │   ├── login.py
│           │   ├── register.py
│           │   └── forgot_password.py
│           ├── admin/               # Admin-only screens
│           │   ├── __init__.py
│           │   ├── main_admin.py    # Navigation shell
│           │   ├── dashboard.py     # KPI overview
│           │   ├── user_management.py  # CRUD users
│           │   ├── model_management.py # YOLO configs
│           │   ├── oa_management.py    # Alert analytics
│           │   ├── settings.py         # App config & restart
│           │   └── profile_admin.py    # Account settings
│           └── user/                # Role-based user screens
│               ├── __init__.py
│               ├── expert/
│               │   ├── __init__.py
│               │   ├── main_expert.py     # Navigation shell
│               │   ├── dashboard.py       # KPI + case table
│               │   ├── consulting_review.py
│               │   ├── raw_data_review.py # Image annotation
│               │   ├── utilities.py       # Search, export
│               │   ├── settings.py
│               │   └── profile_expert.py
│               └── framer/            # Farmer-specific screens
│                   ├── __init__.py
│                   ├── main_farmer.py     # Navigation shell
│                   ├── dashboard.py       # Cached KPIs
│                   ├── live_monitoring.py # Real-time feed
│                   ├── health_consulting.py
│                   ├── session_history.py
│                   ├── utilities.py
│                   ├── settings.py
│                   ├── profile_farmer.py
│                   └── _camera_capture.py # Subprocess for snapshots
```

---

## Module Reference

### main.py
**Purpose**: Application entry point and top-level routing.

**Key Functions**:
- `main(page: ft.Page)` — Initialize app, set up navigation callbacks
- Callbacks: `show_login()`, `show_dashboard(role)`, `show_register()`, `show_forgot_password()`
- Init sequence: DAL seed → clear old session → show login screen
- Mode detection: reads config to run desktop or web mode

**Key Behaviors**:
- Windows error suppression (SetErrorMode 0x8007) to prevent C++ dialog crashes
- Window size: 393x852 (mobile default), resizable
- Sets `page.data["is_mobile"] = True` for theme.py responsive breakpoint

---

### bll/services/auth_service.py
**Purpose**: Handle authentication and session lifecycle.

**Functions**:
- `login(ten_dang_nhap, mat_khau, page)` → Calls DAL, stores session in page.data and mirrors to client_storage, returns role or None
- `perform_logout(page, callback)` → Clears keys (user_role, user_id, ho_ten), fires callback
- `check_logged_in_role(page)` → Returns stored role or None (used in recovery logic)

**Session Keys**:
- `user_role`: admin|expert|farmer
- `user_id`: numeric user ID
- `ho_ten`: display name

---

### bll/services/monitor_service.py
**Purpose**: Configuration management, caching, and remote API stubs.

**Functions**:
- `get_local_ip()` — UDP socket trick (no actual connection) to detect LAN IPv4
- `load_config()` / `save_config(dict)` — JSON at `dal/db/app_config.json`
- `load_cache()` / `save_cache(dict)` — Fallback dashboard cache at `dal/db/monitor_cache.json`
- `fetch_dashboard(server_url, timeout=5)` — GET /api/dashboard
- `stream_url(server_url)` — Builds /api/stream URL
- `fetch_snapshot_base64(server_url, timeout=5)` — GET /api/snapshot → base64

**Config Keys**:
- `server_url` (default: http://127.0.0.1:8000)
- `camera_index` (0-3)
- `auto_connect` (bool)
- `notify_alert` (bool)
- `app_mode` (desktop|web)
- `app_port` (default: 8080)

---

### dal/base_repo.py
**Purpose**: Generic JSON-based CRUD abstraction (database-agnostic).

**Class**: BaseRepo
- Constructor: `BaseRepo(table_name, pk_field="id")`
- Read: `all()`, `find_by_id(pk)`, `find_one(**kwargs)`, `find_many(**kwargs)`
- Write: `insert(data)`, `update(pk, updates)`, `delete(pk)`
- Utility: `count()`, `seed(records)`

**Storage Format**:
```json
{
  "records": [{...}, {...}],
  "next_id": 5
}
```

**Key Design**: No SQL; trivial to swap JSON for PostgreSQL/SQLAlchemy without touching services or UI.

---

### dal/tai_khoan_repo.py
**Purpose**: User account persistence.

**Functions**:
- `init_seed()` — Populate default test accounts (admin, expert01, farmer01)
- `get_all_users()`, `get_user_by_id(id)`, `get_user_by_username(ten_dang_nhap)`
- `authenticate(ten_dang_nhap, mat_khau_raw)` → PBKDF2-HMAC-SHA256 check with legacy SHA256 fallback, returns user or None
- `create_user(ten_dang_nhap, mat_khau_raw, vai_tro, ho_ten)`
- `update_user(id, updates)` — Filters out mat_khau and id_user (no direct password edit via this function)
- `change_password(id, new_password_raw)` — Dedicated password setter
- `delete_user(id)`, `count_users()`

**Test Credentials**:
- admin / admin123
- expert01 / expert123
- farmer01 / farmer123

---

### dal/camera_chuong_repo.py
**Purpose**: Bind cameras to cattle stalls and assign monitoring users.

**Fields**: id_camera_chuong, id_chuong, khu_vuc_chuong, id_camera, id_user, trang_thai (online|warning|offline)

**Common Operations**:
- `get_by_user(id_user)` → All cameras assigned to user
- `create_camera(id_chuong, khu_vuc_chuong, id_camera, id_user)`
- `delete_camera(id_camera_chuong)`
- Status update: change trang_thai for alert escalation

---

### dal/canh_bao_repo.py
**Purpose**: Alert event storage and lifecycle tracking.

**Fields**: id_canh_bao, loai_canh_bao (cow_fight|cow_lie|cow_sick|heat_high), trang_thai (CHUA_XU_LY|DA_XU_LY|QUA_HAN), id_user, id_camera_chuong, created_at

**Key Functions**:
- `create_alert(...)` — Auto-set trang_thai to CHUA_XU_LY
- `resolve_alert(id_canh_bao)` → Set trang_thai to DA_XU_LY
- `count_open()` → Count alerts with trang_thai == CHUA_XU_LY (for admin dashboard)
- `get_alerts_by_user(id_user)`

---

### dal/model_repo.py
**Purpose**: YOLO model configuration and metadata.

**Fields**: id_model, ten_mo_hinh, loai_mo_hinh (cattle_detect|behavior|disease), trang_thai (active|inactive), conf, iou, duong_dan_file

**Scope**:
- System-level (disease): admin manages
- User-level (cattle_detect, behavior): farmer/expert configure per account

**Operations**:
- `update_model_config(id, conf, iou, duong_dan_file)`
- `update_model_status(id, trang_thai)`
- `get_model_by_type(loai_mo_hinh)` → Returns single or list

---

### dal/dataset_repo.py
**Purpose**: Human-in-the-loop image curation and annotation.

**Tables**:
1. **hinh_anh_dataset**: id, duong_dan, trang_thai (PENDING_REVIEW|CLEANED_DATA), id_user, created_at
2. **hanh_vi** (behaviors): id, ten_hanh_vi, bounding_box (JSON: x_center, y_center, w, h), id_hinh_anh
3. **lich_su_kiem_duyet** (audit): id, thoi_gian_duyet, id_user, id_hinh_anh, hanh_dong (approved|rejected)

**Operations**:
- `add_image(duong_dan, id_user)` → Create PENDING_REVIEW entry
- `get_images_pending()`
- `add_behavior(id_hinh_anh, ten_hanh_vi, bounding_box_json)`
- `log_review(id_hinh_anh, id_user, hanh_dong)` → Audit trail
- `mark_cleaned(id_hinh_anh)` → Set trang_thai to CLEANED_DATA

---

### ui/theme.py
**Purpose**: Compatibility facade over the split design system modules.

**Color Tokens**:
- PRIMARY: #4CAF50 (green)
- SECONDARY: #56CCF2 (blue)
- WARNING: #F2C94C (amber)
- DANGER: #FF7A7A (red)
- TEXT_DARK: #06131B
- GLASS_BG: White 16% opacity (frosted glass effect)

**Primary modules**:
- `theme_tokens.py` â€” colors and glass tokens
- `theme_primitives.py` â€” cards, badges, fields, empty states
- `theme_shells.py` â€” background and role shell
- `theme_auth.py` â€” auth fields and auth shell
- `theme_tables.py`, `theme_nav.py` â€” shared table and nav helpers

**Facade exports**:
- `glass_container(content, width, height, padding=24, radius=28)` — Frosted glass panel
- `button_style(kind="primary", radius=8)` — Returns ButtonStyle (Airbnb-inspired)
- `status_badge(label, kind)` — Colored pill badge
- `section_title(icon_name, text, subtitle)` — Header with icon
- `empty_state(text)` — Placeholder for empty lists
- `inline_field(label, icon, value, password, ...)` — Text input (compact)
- `build_role_shell(selected, render_callback, page)` — Responsive shell (sidebar desktop, bottom nav mobile)
- `build_background()` — 3-layer stack: bg image + dark overlay + content
- `build_auth_shell(content)` — Auth page wrapper

**Responsive Breakpoint**: ~900px width (set in build_role_shell)

---

### ui/components/auth/
**login.py**: TextField for username/password, "Remember me" option, login button, error toast
**register.py**: Username, password, confirm password, full name, dropdown for role
**forgot_password.py**: Email input (UI only; no email backend yet)

---

### ui/components/admin/
**main_admin.py**: Navigation shell (sidebar/bottom nav) with 6 screens
**dashboard.py**: KPIs (total users, cameras, open alerts, pending reviews)
**train_management.py**: Thin builder; delegates form, runtime polling, and install/apply actions to `train_management_*`
**user_management.py**: Account workspace wrapper with KPI strip and filter/search block
**model_management.py**: Registry wrapper with summary metrics, type filters, and production/testing semantics
**model_management_cards.py**: Per-model workflow card with bottom-sheet actions for config save, testing, apply-to-production, and disable
**oa_management.py**: Alert/analytics workspace with mobile-first drilldown tabs and action sheet
**settings.py**: Config form (server URL, camera index, mode, port), restart button triggers `os.execv()`
**profile_admin.py**: Display name, avatar, change password form

---

### ui/components/user/expert/
**main_expert.py**: Navigation shell with 7 screens for expert role
**dashboard.py**: KPI cards + case request table (status, priority, assignee)
**consulting_review.py**: Card-based list of incoming cases, accept/decline/chat buttons
**raw_data_review.py**: Image viewer with bounding box overlay, annotation form
**utilities.py**: Search form, export options, batch operations
**settings.py**: Notification preferences, model assignment per account
**profile_expert.py**: Similar to admin profile

---

### ui/components/user/framer/
**main_farmer.py**: Navigation shell with 7 screens for farmer role
**dashboard.py**: Cached KPI cards (loads from monitor_cache.json if offline)
**live_monitoring.py**: LiveMonitoringController (polling snapshots at ~2 sec intervals), image display, stream URL
**health_consulting.py**: Thin builder; delegates selection, AI chat, expert chat, widgets, and camera flow to `health_consulting_*`
**session_history.py**: Table of past consulting sessions, outcome summaries
**utilities.py**: Quick search, session export
**settings.py**: Notification, camera index, auto-connect toggle
**profile_farmer.py**: Display name, avatar, password change
**_camera_capture.py**: Subprocess script for single snapshot (Windows workaround for MJPG codec issues)

---

## Key Architectural Patterns

### 1. 3-Layer Separation
- **UI**: No database calls; all queries via services
- **Services**: Stateless; orchestrate BL, config, session
- **DAL**: Single source of truth for data; BaseRepo swappable

### 2. Functional Closures for State
```python
_state = {"selected": "dashboard"}
def render():
    if _state["selected"] == "dashboard":
        return dashboard_screen()
    return None
```
No Redux; simpler for Flet's immediate-mode nature.

### 3. Role-Based UI Dispatch
```python
if role == "admin":
    control = AdminMainScreen(...)
elif role == "expert":
    control = ExpertMainScreen(...)
else:
    control = FarmerMainScreen(...)
```
Each role gets entirely separate screens; no shared logic for navigation.

### 4. Windows-Specific Camera Handling
```python
# Always use cv2.CAP_DSHOW on Windows
cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
# Never call cap.release() on Windows (C++ exception)
```

### 5. BaseRepo for DB Abstraction
Current: JSON with BaseRepo
Migration: Replace BaseRepo.__init__/__read__/__write__ with SQLAlchemy Session — no UI/service changes needed.

---

## Data Flow Example: Alert Resolution

1. **User clicks "Resolve Alert"** (oa_management.py)
2. **UI calls** `canh_bao_repo.resolve_alert(id_canh_bao)`
3. **DAL updates** the record: `{"trang_thai": "DA_XU_LY", ...}`
4. **JSON file** written to `dal/db/canh_bao_su_co.json`
5. **UI refreshes** alert table by re-querying repo
6. **Optional**: Push notification via NotificationService (not yet implemented)

---

## Code Standards Applied

| Standard | Implementation |
|----------|-----------------|
| **File Size** | Keep <200 LOC; split by responsibility |
| **Naming** | Vietnamese snake_case for DB fields; kebab-case for files |
| **Comments** | Docstrings for functions; inline for logic >3 lines |
| **Imports** | `from ui.theme import ...` (not `from ../theme`) |
| **Encoding** | Always `open(path, 'w', encoding='utf-8')` |
| **No Globals** | State is local closures or auth/session helpers |
| **Error Handling** | Try/except on file I/O, network calls, subprocess |
| **Type Hints** | Function signatures include return types |

---

## Dependencies (requirements.txt outline)

```
flet==0.28.3
requests
opencv-python
PyYAML
python-dotenv
# Optional for future:
psycopg2-binary  # PostgreSQL
bcrypt           # Better hashing
fastapi          # Backend server
```

---

## Notes for Future Developers

1. **Password Hashing**: Runtime already uses PBKDF2-HMAC-SHA256 and auto-upgrades legacy SHA256 on successful login.
2. **Session Persistence**: `page.data` is the source of truth; legacy `page.client_storage` is still mirrored for older UI code. For production web, use signed cookies or JWT.
3. **Email Integration**: Forgot password UI exists but no backend. Integrate with SES or SendGrid.
4. **Concurrency**: Camera polling uses threading; always call `page.update()`, not `control.update()`.
5. **PostgreSQL Migration**: Only modify base_repo.py; rest of codebase is DB-agnostic by design.
6. **Role-Based Access Control**: Add ACL checks in DAL repos (currently UI-only).
7. **Video Streaming**: Optional backend (Flask/FastAPI) for GPU-accelerated YOLO inference. JSON mode works fully offline.
