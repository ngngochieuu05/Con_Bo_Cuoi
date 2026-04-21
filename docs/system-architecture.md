# System Architecture — Con Bò Cưới

## High-Level Overview

Con Bò Cưới is a **3-layer desktop/web application** for cattle farm monitoring:

```
┌─────────────────────────────────────────────────────┐
│                    UI LAYER                         │
│  Role-based screens (Admin, Expert, Farmer)        │
│  Shared design system + Flet controls              │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│          BUSINESS LOGIC LAYER                      │
│  Services: auth, config, monitoring, alerts       │
│  Orchestrates UI ↔ DAL interactions              │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│           DATA ACCESS LAYER                        │
│  Repositories (JSON or PostgreSQL-ready)          │
│  BaseRepo abstraction for schema-agnostic access  │
└─────────────────────────────────────────────────────┘
```

**Key Design Principles:**
1. **Separation of Concerns**: UI knows nothing about database; DAL is DB-agnostic
2. **Single Responsibility**: Each layer does one thing well
3. **Dependency Inversion**: Services depend on DAL abstractions, not implementations
4. **Testability**: Mock any layer independently

---

## Layer 1: User Interface (UI)

### Architecture Pattern: Immediate-Mode Rendering

Flet uses immediate-mode paradigm: state changes trigger full re-render. Con Bò Cưới follows this pattern:

```
State (dict) → render() → Controls → page.update()
```

### Role-Based Navigation

Each user role gets a complete, separate navigation shell:

```
┌─────────────────────────────────┐
│  Role Dispatch (main.py)        │
│  ├─ Role: admin                 │
│  │  └─→ AdminMainScreen         │
│  ├─ Role: expert                │
│  │  └─→ ExpertMainScreen        │
│  └─ Role: farmer                │
│     └─→ FarmerMainScreen        │
└─────────────────────────────────┘
```

### Responsive Shell Pattern

Each main screen uses `build_role_shell()` to adapt layout:

```
Desktop (width > 900px):
┌─────────────────────────┐
│  [NAV SIDEBAR]          │
│  ┌────────────────────┐ │
│  │  CONTENT AREA      │ │
│  │  (dynamic)         │ │
│  └────────────────────┘ │
└─────────────────────────┘

Mobile (width ≤ 900px):
┌─────────────────────────┐
│  CONTENT AREA           │
│  (full width)           │
├─────────────────────────┤
│ [NAV BOTTOM BAR]        │
└─────────────────────────┘
```

### Design System (theme.py facade)

Single source of truth for all visual design:

`ui/theme.py` now acts as a compatibility facade. The concrete split lives in:
- `ui/theme_tokens.py`
- `ui/theme_primitives.py`
- `ui/theme_shells.py`
- `ui/theme_auth.py`
- `ui/theme_tables.py`
- `ui/theme_nav.py`

```
theme.py
├── Color Tokens
│   ├── PRIMARY = #4CAF50 (green)
│   ├── SECONDARY = #56CCF2 (blue)
│   ├── WARNING = #F2C94C (amber)
│   ├── DANGER = #FF7A7A (red)
│   └── GLASS_* (frosted glass palette)
│
├── Component Factories
│   ├── glass_container()
│   ├── button_style()
│   ├── status_badge()
│   ├── section_title()
│   ├── empty_state()
│   ├── inline_field()
│   ├── metric_card()
│   ├── data_table()
│   ├── build_role_shell()
│   └── build_auth_shell()
│
└── Utilities
    ├── fmt_dt() → format ISO datetime
    └── responsive helpers
```

### Screen Organization

```
ui/components/
├── auth/
│   ├── login.py          → LoginScreen(page, on_login_success, on_switch_to_register)
│   ├── register.py       → RegisterScreen(page, on_register_success, on_back_to_login)
│   └── forgot_password.py → ForgotPasswordScreen(on_back_to_login)
│
├── admin/
│   ├── main_admin.py     → AdminMainScreen(page, on_logout) [6 screens]
│   ├── dashboard.py      → shows KPI cards + metrics
│   ├── user_management.py → CRUD users, assign roles
│   ├── model_management.py → YOLO config interface
│   ├── oa_management.py  → alert analytics & resolution
│   ├── settings.py       → app config (mode, port, server URL)
│   └── profile_admin.py  → account settings
│
└── user/
    ├── expert/
    │   ├── main_expert.py     → ExpertMainScreen(page, on_logout) [7 screens]
    │   ├── dashboard.py       → KPI + case request table
    │   ├── consulting_review.py → incoming case cards
    │   ├── raw_data_review.py → image annotation interface
    │   ├── utilities.py       → search, export
    │   ├── settings.py
    │   └── profile_expert.py
    │
    └── framer/
        ├── main_farmer.py     → FarmerMainScreen(page, on_logout) [7 screens]
        ├── dashboard.py       → cached KPI cards
        ├── live_monitoring.py → real-time camera feed
        ├── health_consulting.py → chat + stream
        ├── session_history.py → past interactions
        ├── utilities.py
        ├── settings.py
        ├── profile_farmer.py
        └── _camera_capture.py → subprocess for snapshots
```

Current reconciliation after the April 19 refactor:
- `ui/theme.py` is now a stable facade over `theme_tokens.py`, `theme_primitives.py`, `theme_shells.py`, `theme_auth.py`, `theme_tables.py`, and `theme_nav.py`
- `admin/train_management.py` is now an orchestrator over `train_management_form.py`, `train_management_runtime.py`, and `train_management_actions.py`
- `admin/user_management.py` is now an orchestrator over `user_management_cards.py`, `user_management_filters.py`, and `user_management_model_controls.py`
- `user/framer/health_consulting.py` is now an orchestrator over the split `health_consulting_*` modules

### State Management Pattern

All UI state is **functional + closure-based**:

```python
def my_screen(page: ft.Page) -> ft.Control:
    # Local state: never global
    _state = {"selected_tab": "dashboard", "search_text": ""}
    
    def render():
        # Return UI based on current state
        if _state["selected_tab"] == "dashboard":
            return dashboard_content()
        return other_content()
    
    def on_tab_click(tab_name):
        _state["selected_tab"] = tab_name
        content_holder.controls = [render()]
        content_holder.update()
    
    # Return control tree
    return ft.Column(controls=[
        tab_bar,
        content_holder := ft.Container(content=render()),
    ])
```

**Why not Redux?** Flet is immediate-mode; each state change re-renders. Redux adds unnecessary complexity.

### Session Management

Session source of truth is **page.data**, mirrored into **page.client_storage** for legacy UI compatibility:

```python
# After login
page.data["user_role"] = "admin"
page.data["user_id"] = "1"
page.data["ho_ten"] = "Quản trị viên"

# Read session
role = page.data.get("user_role")

# Logout: clear all
for key in ("user_role", "user_id", "ho_ten"):
    page.data.pop(key, None)
```

**Limitation**: Non-persistent (clears on app restart). For production web, upgrade to signed cookies or JWT.

---

## Layer 2: Business Logic (BLL)

### Service Layer Architecture

Two main services orchestrate business logic:

#### auth_service.py

```
┌─────────────────────────────────┐
│    Login Request                │
│  (ten_dang_nhap, mat_khau)      │
└────────────┬────────────────────┘
             │
    ┌────────▼─────────┐
    │ Validate input   │
    │ (non-empty trim) │
    └────────┬─────────┘
             │
    ┌────────▼──────────────────────┐
    │ DAL: authenticate()           │
    │ (PBKDF2 check + legacy SHA256)│
    └────────┬─────────────────────┘
             │
             ├─ User found & hash match?
             │
             ├─YES─┐
             │     ├─ Set page.data (+ mirror client_storage)
             │     ├─ Return role (admin|expert|farmer)
             │
             └─NO──┐
                   └─ Return None
```

**Functions:**
- `login(ten_dang_nhap, mat_khau, page) → role | None`
- `perform_logout(page, callback)` → clear storage, call callback
- `check_logged_in_role(page) → role | None`

#### monitor_service.py

```
Configuration Management
│
├─ load_config() → Read dal/db/app_config.json
├─ save_config(dict) → Write dal/db/app_config.json
│
├─ Config keys:
│  ├─ server_url (API server for optional backend)
│  ├─ camera_index (default camera device)
│  ├─ auto_connect (auto-connect on startup)
│  ├─ notify_alert (show toast alerts)
│  ├─ app_mode (desktop or web)
│  └─ app_port (default 8080)
│
Caching (Offline Support)
│
├─ load_cache() → Read dal/db/monitor_cache.json
├─ save_cache(dict) → Write dal/db/monitor_cache.json
│
Remote API Stubs (Optional Backend)
│
├─ get_local_ip() → Detect LAN IPv4 via UDP socket trick
├─ fetch_dashboard(server_url) → GET /api/dashboard
├─ stream_url(server_url) → Build /api/stream URL
└─ fetch_snapshot_base64(server_url) → GET /api/snapshot → base64
```

### Service Responsibilities

| Service | Responsibility | Never Does |
|---------|-----------------|-----------|
| **auth_service** | Login, logout, session | Direct DB calls, UI rendering |
| **monitor_service** | Config/cache I/O, IP detection, API stubs | Auth, role checks, persistence |

### No Business Logic in UI

✗ Bad: UI calls DAL directly
```python
def on_create_user(e):
    user = tai_khoan_repo.create_user(...)  # Don't do this!
    label.value = f"User created: {user['ho_ten']}"
    page.update()
```

✓ Good: UI calls service
```python
def on_create_user(e):
    user = user_service.create_user(...)  # Service wraps DAL
    label.value = f"User created: {user['ho_ten']}"
    page.update()
```

---

## Layer 3: Data Access (DAL)

### BaseRepo: Database Abstraction

The **BaseRepo** class is the single abstraction for all data access:

```python
class BaseRepo:
    def __init__(self, table_name: str, pk_field: str = "id"):
        # Initialize repo for a specific table
        pass
    
    # READ
    def all() -> list[dict]
    def find_by_id(pk_value) -> dict | None
    def find_one(**kwargs) -> dict | None
    def find_many(**kwargs) -> list[dict]
    
    # WRITE
    def insert(data: dict) -> dict
    def update(pk_value, updates: dict) -> dict | None
    def delete(pk_value) -> bool
    
    # UTILITY
    def count() -> int
    def seed(records: list[dict]) -> None
```

### Current Implementation: JSON

Each table is a JSON file:

```
dal/db/tai_khoan.json:
{
  "records": [
    {
      "id_user": 1,
      "ten_dang_nhap": "admin",
      "mat_khau": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
      "vai_tro": "admin",
      "ho_ten": "Quản trị viên",
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "next_id": 4
}
```

### Migration Path: PostgreSQL

To switch to PostgreSQL, only modify `base_repo.py`:

```python
# Old: JSON
def _load(table_name: str) -> dict:
    with open(_db_path(table_name), "r", encoding="utf-8") as f:
        return json.load(f)

# New: SQLAlchemy
from sqlalchemy import create_engine, text, MetaData, Table

_engine = create_engine("postgresql://...")

def _load(table_name: str) -> dict:
    with _engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table_name}"))
        return {"records": [dict(row) for row in result]}
```

**No other changes needed:** All services and UI continue working.

### Repository Wrappers

Each table gets a specialized repo wrapper:

```
BaseRepo("tai_khoan")
    ↓
tai_khoan_repo.py wraps with:
  - authenticate(ten_dang_nhap, mat_khau_raw)
  - get_user_by_username(ten_dang_nhap)
  - change_password(id_user, new_password_raw)
  - update_user(id_user, updates) [filters mat_khau]
  - init_seed()

BaseRepo("canh_bao_su_co")
    ↓
canh_bao_repo.py wraps with:
  - create_alert(...)
  - resolve_alert(id_canh_bao)
  - count_open() → count alerts with trang_thai == CHUA_XU_LY
  - get_alerts_by_user(id_user)
  - init_seed()

BaseRepo("camera_chuong")
    ↓
camera_chuong_repo.py wraps with:
  - get_by_user(id_user)
  - create_camera(...)
  - delete_camera(id_camera_chuong)
  - init_seed()

BaseRepo("model")
    ↓
model_repo.py wraps with:
  - update_model_config(id, conf, iou, duong_dan_file)
  - update_model_status(id, trang_thai)
  - get_model_by_type(loai_mo_hinh)
  - init_seed()

BaseRepo("hinh_anh_dataset")
    ↓
dataset_repo.py wraps with:
  - add_image(duong_dan, id_user)
  - get_images_pending() → trang_thai == PENDING_REVIEW
  - mark_cleaned(id_hinh_anh)
  - add_behavior(id_hinh_anh, ten_hanh_vi, bounding_box_json)
  - log_review(id_hinh_anh, id_user, hanh_dong)
  - init_seed()
```

### Data Initialization (Seeding)

On app startup, `dal/__init__.py` calls `init_all()`:

```python
def init_all():
    """Seed default data if tables are empty."""
    _seed_users()      # Creates admin, expert01, farmer01
    _seed_models()     # Creates 3 default YOLO configs
    _seed_cameras()    # Creates 3 sample camera bindings
    _seed_alerts()     # Creates 1 sample alert
    _seed_dataset()    # Creates 1 sample image record
```

Each `init_seed()` only populates if the table is empty (idempotent).

---

## Data Model

### Entities & Relationships

```
┌──────────────────┐
│   tai_khoan      │ (users)
│  (id_user) ──────┼──┐
│  - ten_dang_nhap │  │
│  - mat_khau      │  │
│  - vai_tro       │  │
│  - ho_ten        │  │
│  - anh_dai_dien  │  │
└──────────────────┘  │
                      │
                      ├─ 1:N ──→ ┌──────────────────────┐
                      │          │ camera_chuong        │
                      │          │  (id_camera_chuong) ──┐
                      │          │  - id_chuong         │
                      │          │  - khu_vuc_chuong    │
                      │          │  - id_camera         │
                      │          │  - trang_thai        │
                      │          └──────────────────────┘
                      │                  ↓
                      │          1:N → ┌──────────────────────┐
                      │                │ canh_bao_su_co       │
                      │                │  (id_canh_bao) ──┐
                      │                │  - loai_canh_bao │
                      │                │  - trang_thai    │
                      │                │  - created_at    │
                      │                └──────────────────┘
                      │
                      ├─ 1:N ──→ ┌──────────────────────┐
                      │          │ model                │
                      │          │  (id_model)          │
                      │          │  - ten_mo_hinh       │
                      │          │  - loai_mo_hinh      │
                      │          │  - conf, iou         │
                      │          │  - duong_dan_file    │
                      │          └──────────────────────┘
                      │
                      └─ 1:N ──→ ┌──────────────────────┐
                                 │ hinh_anh_dataset     │
                                 │  (id_hinh_anh) ──┐
                                 │  - duong_dan     │
                                 │  - trang_thai    │
                                 └──────────────────┘
                                        ↓
                                 1:N → ┌──────────────────────┐
                                       │ hanh_vi              │
                                       │  (id_hanh_vi)        │
                                       │  - ten_hanh_vi       │
                                       │  - bounding_box      │
                                       └──────────────────────┘

                                       (separate audit table)
                                       ┌──────────────────────┐
                                       │ lich_su_kiem_duyet   │
                                       │  (id_lich_su)        │
                                       │  - thoi_gian_duyet   │
                                       │  - id_user           │
                                       │  - id_hinh_anh       │
                                       │  - hanh_dong         │
                                       └──────────────────────┘
```

### Table Schemas

| Table | PK | Constraints | Purpose |
|-------|----|----|---------|
| **tai_khoan** | id_user | UNIQUE(ten_dang_nhap) | User accounts |
| **camera_chuong** | id_camera_chuong | FK(id_user) | Camera assignments |
| **canh_bao_su_co** | id_canh_bao | FK(id_camera_chuong), FK(id_user) | Alerts |
| **model** | id_model | UNIQUE(ten_mo_hinh) | YOLO configurations |
| **hinh_anh_dataset** | id_hinh_anh | FK(id_user) | Image curation |
| **hanh_vi** | id_hanh_vi | FK(id_hinh_anh) | Annotations |
| **lich_su_kiem_duyet** | id_lich_su | FK(id_user), FK(id_hinh_anh) | Audit log |

---

## Deployment Architectures

### Desktop Deployment

```
┌──────────────────────────────────┐
│  Windows/Mac/Linux Desktop       │
│  ┌────────────────────────────┐  │
│  │  Flet App (main.py)        │  │
│  │  ├─ UI Controls            │  │
│  │  ├─ Services               │  │
│  │  ├─ Repositories           │  │
│  │  └─ JSON DB (dal/db/)      │  │
│  │  ┌────────────────────────┐│  │
│  │  │ Optional: OpenCV       ││  │
│  │  │ - Camera capture       ││  │
│  │  │ - YOLO inference       ││  │
│  │  └────────────────────────┘│  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ Optional: Remote AI Backend││  │
│  │ (Flask/FastAPI on :8000)   │  │
│  │ - Advanced inference       │  │
│  │ - GPU acceleration         │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

**Startup:**
```bash
$ python webapp_system/src/main.py
```

### Web Deployment

```
┌──────────────────────────────────────────┐
│  Server (Docker Container)               │
│  ┌──────────────────────────────────────┐│
│  │  Flet Web App (--web flag)           ││
│  │  ├─ UI (React/Flutter-Web compiled)  ││
│  │  ├─ Services                         ││
│  │  ├─ Repositories                     ││
│  │  └─ PostgreSQL Client (dal/db/)      ││
│  └──────────────────────────────────────┘│
└────────────────────────────────────────────
         ↓ (HTTP requests)
┌────────────────────────────────────────────
│  Browser (Mobile/Desktop)
│  ├─ HTTP GET / POST / WebSocket
│  └─ Renders Flet UI
```

**Startup (web mode):**
```bash
$ python webapp_system/src/main.py --web --port 8080
# Detects app_mode: "web" from app_config.json
# Listens on http://0.0.0.0:8080
# LAN clients access http://{LAN_IP}:8080
```

---

## Key Design Decisions

### 1. Why 3 Layers?

| Layer | Benefit |
|-------|---------|
| **UI** | Decoupled from DB; easier to redesign UI without changing data model |
| **BLL** | Centralized business rules; easier to test; reusable across UI+CLI |
| **DAL** | DB-agnostic; swap JSON for PostgreSQL without touching services/UI |

### 2. Why No ORM (Yet)?

Current: **BaseRepo + JSON**
- Simple, zero dependencies (except requests, opencv)
- Easy to understand for new developers
- No complex migration files

Future: **SQLAlchemy ORM**
- When dataset grows beyond JSON capacity
- Swap only base_repo.py; no other changes

### 3. Why Functional Closures for UI State?

Flet is **immediate-mode**, not declarative (unlike React):
- Each state change re-renders all controls
- Redux would add overhead (selectors, reducers, middleware)
- Closures + dicts are simpler and sufficient

### 4. Why Session in page.data?

Advantage:
- No server-side session storage needed for desktop
- Works offline

Disadvantage:
- Non-persistent (clears on app restart)
- Vulnerable to tampering (no encryption)

**Solution for web:** Switch to signed JWT tokens in HTTP-only cookies.

### 5. Why Multiple Repos (not Single UserService)?

Each repo is domain-specific:
- `tai_khoan_repo`: only user operations
- `camera_chuong_repo`: only camera operations
- `canh_bao_repo`: only alert operations

This follows **Single Responsibility Principle** and makes testing easier.

---

## Integration Points

### Optional AI Backend

The app is fully functional offline. For advanced features, integrate an optional backend:

```
Farmer's Flet App
    │
    ├─ On-device YOLO inference (CPU-based, slow)
    │
    └─ OR connect to optional backend:
       │
       POST /api/dashboard
       POST /api/snapshot
       GET /api/stream
       │
       Backend (Flask/FastAPI on :8000)
       ├─ GPU-accelerated YOLO
       ├─ Advanced analytics
       ├─ Herd behavior trends
       └─ Disease prediction models
```

**Current state:** API stubs exist in `monitor_service.py`. Implement backend separately.

---

## Error Handling Strategy

### Layered Error Recovery

```
UI Error
  ↓
Try Service Layer
  ├─ If service fails: show toast, use cached data
  ├─ If cache missing: show empty state
  └─ If offline: disable features that need network
      ↓
    Try DAL
      ├─ If DAL fails: return None, handle in service
      └─ If data missing: return empty list

Example: Fetch dashboard
  ├─ UI calls: fetch_dashboard(server_url)
  ├─ Service tries: requests.get("/api/dashboard")
  │  ├─ Success: cache result, return data
  │  └─ Timeout/error: load_cache(), use fallback data
  ├─ UI shows: metrics (live if online, cached if offline)
  └─ User experience: seamless offline mode
```

---

## Security Considerations

### Current Limitations (Should Fix)

1. **Passwords:** PBKDF2-HMAC-SHA256 with random salt; legacy SHA256 remains only for login-time migration
   - Recommendation: Keep current PBKDF2 baseline or move to Argon2/bcrypt only if migration budget exists
2. **Session:** page.data is in-process state; page.client_storage is compatibility mirror only
   - Recommendation: Signed JWT in HTTP-only cookies (web only)
3. **Role-Based Access:** UI-only validation
   - Recommendation: Add ACL checks in DAL layer
4. **No HTTPS:** Desktop app doesn't use HTTPS
   - Recommendation: Enforce HTTPS in web mode

### Current Protections

1. **Secrets not logged:** Password handling filters mat_khau
2. **Input validation:** trim whitespace, check non-empty
3. **File isolation:** JSON files in dedicated `dal/db/` directory
4. **No SQL injection:** Using BaseRepo (not string concatenation)

---

## Testing Strategy

### Unit Tests (Each Layer)

```python
# Test DAL independently
def test_tai_khoan_repo_authenticate():
    user = tai_khoan_repo.authenticate("admin", "admin123")
    assert user["vai_tro"] == "admin"
    
    user = tai_khoan_repo.authenticate("admin", "wrong")
    assert user is None

# Test service independently (mock DAL)
def test_auth_service_login(mock_dai_khoan_repo):
    page = MockPage()
    role = auth_service.login("admin", "admin123", page)
    assert role == "admin"
    assert page.data["user_role"] == "admin"

# Test UI independently (mock service)
def test_login_screen(mock_auth_service):
    screen = LoginScreen(page, on_login_success=...)
    # Simulate button click
    # Verify on_login_success called with correct role
```

### Integration Tests

```python
def test_alert_creation_flow():
    # User creates alert via UI
    # Alert saved to repository
    # Admin dashboard reflects new alert
    # Full flow from UI → service → DAL
```

### Manual Testing

1. **Happy path:** admin login → create user → delete user
2. **Error handling:** bad password, missing file, network timeout
3. **Offline mode:** kill server, verify cached data loads
4. **Cross-role:** log in as each role, verify screens differ

---

## Performance & Scalability

### Current Bottlenecks

| Bottleneck | Impact | Solution |
|-----------|--------|----------|
| **JSON file I/O** | File re-read on each query | Implement in-memory cache or PostgreSQL |
| **Snapshot polling** | 2-sec delay per frame | Async thread + WebSocket streaming |
| **YOLO inference** | CPU-bound, blocks UI | Background thread or GPU backend |
| **Session storage** | Non-persistent | Switch to persistent cookies/JWT |

### Optimization Roadmap

1. **Phase 1 (Now):** JSON + in-memory cache (acceptable for <100 users)
2. **Phase 2:** PostgreSQL + connection pooling (supports 500+ users)
3. **Phase 3:** Redis cache + async inference (supports 5000+ concurrent users)
4. **Phase 4:** Kubernetes deployment + horizontal scaling

---

## Summary

Con Bò Cưới's architecture prioritizes **simplicity and maintainability** over premature optimization:

- **3-layer design** decouples concerns
- **BaseRepo abstraction** allows DB migration without code changes
- **Functional closures** manage UI state simply
- **Offline-first** design works with or without backend
- **Incremental hardening:** security improvements can be added layer-by-layer

This design ensures the system is easy to understand, extend, and maintain as the project grows.
