# Code Standards — Con Bò Cưới

## Naming Conventions

### Files & Directories
- **Python files**: kebab-case with descriptive purpose
  - ✓ `auth_service.py`, `camera_capture.py`, `model_management.py`
  - ✗ `authSvc.py`, `cc.py`, `modelMgmt.py`
- **Directories**: kebab-case
  - ✓ `bll/services/`, `ui/components/admin/`
  - ✗ `BLL/Services/`, `UI/Components/Admin/`
- **Modules grouped by domain**: `user/expert/`, `user/farmer/`, not `user_expert/`, `user_farmer/`

### Database Fields
- **Vietnamese snake_case** (exact field names for clarity)
  - ✓ `id_user`, `ten_dang_nhap`, `mat_khau`, `vai_tro`, `ho_ten`, `trang_thai`, `id_camera_chuong`
  - ✗ `userId`, `username`, `password`, `role`, `fullName`, `status`, `cameraStallId`
- **Rationale**: Field names appear in JSON files and DAL queries; match exact database schema

### Python Variables & Functions
- **snake_case** for variables, functions, methods
  - ✓ `user_role`, `fetch_dashboard()`, `create_alert()`
  - ✗ `userRole`, `fetchDashboard()`, `createAlert()`
- **Constants**: UPPER_SNAKE_CASE
  - ✓ `PRIMARY = "#4CAF50"`, `MAX_FILE_SIZE = 10485760`
  - ✗ `primary`, `maxFileSize`
- **Private/Internal**: prefix with `_`
  - ✓ `_state`, `_cache`, `_ensure_parent()`
  - ✗ `state`, `cache`, `ensure_parent()`

### UI Components & Classes
- **PascalCase** for Flet control classes (native convention)
  - ✓ `AdminMainScreen`, `LoginScreen`, `LiveMonitoringController`
  - ✗ `adminMainScreen`, `login_screen`
- **Component factories**: snake_case functions returning controls
  - ✓ `glass_container()`, `status_badge()`, `section_title()`
  - ✗ `glassContainer()`, `StatusBadge()`, `SectionTitle()`

---

## File Organization & Size Limits

### Maximum File Size
- **200 lines per file** (including docstrings, comments, blank lines)
- **Why**: Easier context loading for LLMs, simpler code review, single responsibility principle

### Split Strategy
When a file approaches 200 LOC:

1. **By responsibility**: Extract related functions into new files
   - ✓ If `admin/dashboard.py` grows beyond 200 LOC, split into `admin/dashboard-metrics.py` + `admin/dashboard-alerts.py`
   - ✗ Don't leave a 500-line dashboard.py

2. **By domain**: Group related screens
   - ✓ `expert/consulting_review.py` (single screen), not one mega-file

3. **Services**: One service per responsibility
   - ✓ `auth_service.py` (login/logout only), `monitor_service.py` (config/cache/API)
   - ✗ `user_service.py` (auth + profile + notifications)

### File Structure Template
```python
"""
Module docstring: purpose, key functions, example usage.
"""
import sys
from typing import Any

# Imports: stdlib, third-party, local
import flet as ft
from dal.tai_khoan_repo import authenticate

# Constants: module-level configuration
PRIMARY_COLOR = "#4CAF50"

# Classes: if any (usually avoided in UI factories)
class MyService:
    pass

# Functions: main functions first, helpers last
def public_function():
    pass

def _private_helper():
    pass
```

---

## Imports & Dependencies

### Import Order
1. Standard library (sys, os, json, typing)
2. Third-party (flet, requests, opencv-python)
3. Local modules (dal.*, ui.*)

```python
import os
import json
from typing import Any
from datetime import datetime

import flet as ft
import requests

from dal.tai_khoan_repo import authenticate
from ui.theme import PRIMARY, glass_container
```

### Avoid Global State
- ✗ `GLOBAL_USER = None` (mutable global)
- ✗ `import bll.services; bll.services.current_user = user` (implicit state)
- ✓ Pass session via function args: `login(page)` → stores in `page.client_storage`

### Local Imports (Rare)
Use only if needed to break circular dependencies:
```python
def some_function():
    from dal.model_repo import get_model  # OK: breaks cycle
    return get_model(1)
```

---

## Type Hints & Docstrings

### Function Signatures
Always include return type:
```python
def authenticate(ten_dang_nhap: str, mat_khau_raw: str) -> dict | None:
    """Authenticate user via DAL. Return user record or None."""
    ...

def create_alert(id_camera: int, loai: str, id_user: int) -> dict:
    """Create new alert. Return inserted record."""
    ...
```

### Docstring Style (Google-style)
```python
def fetch_dashboard(server_url: str, timeout: int = 5) -> dict[str, Any]:
    """
    Fetch dashboard metrics from remote server.
    
    Args:
        server_url: Base URL of API server (e.g., http://localhost:8000)
        timeout: Request timeout in seconds (default: 5)
    
    Returns:
        Dictionary with keys: metrics (list), timestamp (str), alerts (int)
    
    Raises:
        requests.Timeout: If server doesn't respond within timeout
        requests.HTTPError: If server returns 4xx/5xx
    
    Example:
        >>> data = fetch_dashboard("http://192.168.1.100:8000")
        >>> print(data["alerts"])
    """
    ...
```

### Type Hint Conventions
```python
# Use | for union types (Python 3.10+)
def find_by_id(pk: int) -> dict | None:
    ...

# Use list[T] not List[T]
def get_all_users() -> list[dict]:
    ...

# Use dict[K, V] not Dict[K, V]
def load_config() -> dict[str, Any]:
    ...

# Use tuple[T, ...] for variable-length
def get_image_dimensions() -> tuple[int, int]:
    ...
```

---

## Code Quality & Style

### Indentation & Spacing
- **Indentation**: 4 spaces (never tabs)
- **Line length**: Keep under 100 characters (readability on 80-char terminals)
- **Blank lines**: 2 between top-level functions, 1 between methods

```python
def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page) -> str | None:
    """..."""
    user = _dal_authenticate(ten_dang_nhap.strip(), mat_khau)
    if user:
        return user.get("vai_tro")
    return None


def perform_logout(page: ft.Page, on_logout_success) -> None:
    """..."""
    for key in ("user_role", "user_id", "ho_ten"):
        try:
            page.client_storage.remove(key)
        except Exception:
            pass
```

### Readability Over Cleverness
✓ Clear:
```python
store = _load(table_name)
if self._pk not in data:
    data = {self._pk: store["next_id"], **data}
    store["next_id"] += 1
```

✗ Clever:
```python
store = _load(table_name) or {"records": [], "next_id": 1}
data = {self._pk: data.get(self._pk) or store.get("next_id", 1), **data}
```

### Variable Naming
- **Descriptive**: `user_role`, `alert_list`, `is_online`
- **Avoid abbreviations**: ✗ `usr_rl`, `alrt_lst`, `is_on`
- **Context-dependent OK**: `x`, `y` (coordinates), `i` (loop index)
- **Avoid single letters for complex objects**: ✗ `u = get_user()`, ✓ `user = get_user()`

---

## Error Handling

### Exception Handling Pattern
```python
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {**default, **data}
except FileNotFoundError:
    # Config not yet created; return defaults
    return default
except json.JSONDecodeError:
    # Config corrupted; log and fall back
    print(f"Warning: {CONFIG_PATH} is invalid JSON")
    return default
except Exception as e:
    # Unexpected error; log details
    print(f"Error loading config: {e}")
    return default
```

### Never Swallow Errors Silently
✗ Bad:
```python
try:
    result = risky_operation()
except Exception:
    pass  # What went wrong? Will debug later...
return result  # result might be undefined!
```

✓ Good:
```python
try:
    result = risky_operation()
except FileNotFoundError:
    print("File not found; using default")
    return default_value
except Exception as e:
    print(f"Unexpected error: {e}")
    raise  # Or return fallback
```

### Security: Never Log Secrets
✗ Bad:
```python
print(f"Logging in as {username} with password {password}")
```

✓ Good:
```python
print(f"Logging in as {username}")
# Or use masked password:
print(f"Logging in as {username}; password: {'*' * len(password)}")
```

---

## UI Component Patterns

### Functional Closures for State
All UI state managed via closures, not classes:

```python
def user_management_screen(page: ft.Page) -> ft.Control:
    """Screen with editable user table."""
    
    # Local state: mutable dict mutated by handlers
    _state = {"selected_user_id": None, "search_text": ""}
    
    def render():
        """Rebuild UI based on _state."""
        users = tai_khoan_repo.get_all_users()
        if _state["search_text"]:
            users = [u for u in users if _state["search_text"].lower() in u["ho_ten"].lower()]
        
        rows = [_user_card(u, on_select, on_delete) for u in users]
        return ft.Column(controls=rows)
    
    def on_select(user_id):
        _state["selected_user_id"] = user_id
        content_holder.controls = [render()]
        content_holder.update()
    
    def on_delete(user_id):
        tai_khoan_repo.delete_user(user_id)
        content_holder.controls = [render()]
        content_holder.update()
    
    def on_search(query):
        _state["search_text"] = query
        content_holder.controls = [render()]
        content_holder.update()
    
    search = ft.TextField(label="Search", on_change=lambda e: on_search(e.control.value))
    content_holder = ft.Container(content=render())
    
    return ft.Column(controls=[search, content_holder])
```

### Component Factories (Not Classes)
Always use functions returning controls, not subclasses:

✓ Good:
```python
def status_badge(label: str, kind: str = "primary") -> ft.Container:
    """Return a colored pill badge."""
    palette = {"primary": PRIMARY, "danger": DANGER}
    color = palette.get(kind, PRIMARY)
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        bgcolor=ft.Colors.with_opacity(0.22, color),
        content=ft.Text(label, size=11, weight=ft.FontWeight.W_600),
    )
```

✗ Avoid:
```python
class StatusBadge(ft.Container):
    def __init__(self, label: str, kind: str = "primary"):
        # Complex lifecycle; Flet handles immediately-mode
        super().__init__(...)
```

### Page Updates
Always use `page.update()`, not `control.update()`:

✓ Good:
```python
def on_button_click(e):
    label.value = "Clicked!"
    page.update()  # Refreshes all controls at once
```

✗ Bad:
```python
def on_button_click(e):
    label.value = "Clicked!"
    label.update()  # Can miss updates; causes racing
```

### Flet API Conventions
- **Colors**: Use `ft.Colors.*` constants (uppercase)
  - ✓ `ft.Colors.WHITE`, `ft.Colors.BLACK45`
  - ✗ `ft.Colors.white`, `ft.Colors.black45`, `"#ffffff"`
- **Icons**: Use `ft.Icons.*` constants
  - ✓ `ft.Icon(ft.Icons.HOME)`
  - ✗ `ft.Icon("home")`
- **Font weights**: Use `ft.FontWeight.*` enums
  - ✓ `weight=ft.FontWeight.W_700`
  - ✗ `weight="bold"`, `weight=700`
- **Border functions**: Use lowercase functions
  - ✓ `ft.border.all(1, color)`, `ft.padding.symmetric(horizontal=8)`
  - ✗ `ft.Border.all()`, `ft.Padding.symmetric()`

---

## Database & Repository Patterns

### BaseRepo Usage
```python
# Always create a repo wrapper, not direct BaseRepo usage
_repo = BaseRepo("tai_khoan", pk_field="id_user")

def get_user_by_id(id_user: int) -> dict | None:
    return _repo.find_by_id(id_user)

def create_user(...) -> dict:
    return _repo.insert({...})
```

### Safe Updates
Never expose direct `mat_khau` updates:

✓ Good:
```python
def update_user(id_user: int, updates: dict) -> dict | None:
    # Filter out sensitive fields
    safe = {k: v for k, v in updates.items() if k not in ("mat_khau", "id_user")}
    return _repo.update(id_user, safe)

def change_password(id_user: int, new_password_raw: str) -> bool:
    result = _repo.update(id_user, {
        "mat_khau": hashlib.sha256(new_password_raw.encode()).hexdigest()
    })
    return result is not None
```

✗ Bad:
```python
def update_user(id_user: int, updates: dict) -> dict | None:
    return _repo.update(id_user, updates)  # Updates mat_khau directly!
```

### Seed Data
```python
_SEED = [
    {
        "id_user": 1,
        "ten_dang_nhap": "admin",
        "mat_khau": hashlib.sha256("admin123".encode()).hexdigest(),
        "vai_tro": "admin",
        "ho_ten": "Quản trị viên",
        "created_at": "2026-01-01T00:00:00",
    },
]

def init_seed():
    _repo.seed(_SEED)  # Only populates if table is empty
```

---

## Encoding & File I/O

### Always Specify UTF-8
```python
# ✓ Good
with open(path, "r", encoding="utf-8") as f:
    return json.load(f)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

✗ Bad:
```python
# Uses system default (e.g., UTF-16LE on Windows PowerShell)
with open(path, "r") as f:
    return json.load(f)
```

### JSON Handling
```python
# Preserve Vietnamese characters
json.dump(data, f, ensure_ascii=False, indent=2)

# Parse with fallback
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except json.JSONDecodeError:
    data = {}  # Default if corrupted
```

---

## Windows-Specific Patterns

### Error Reporting Suppression
```python
# At top of main.py
try:
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x8007)  # Suppress C++ error dialogs
except Exception:
    pass  # Not on Windows; OK to ignore
```

### Camera Capture
```python
import cv2

# Always use CAP_DSHOW on Windows
cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffering
cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

# Read with timeout
ret, frame = cap.read()

# Never call cap.release() on Windows; causes C++ crash
# Just let it be garbage-collected
```

### Subprocess Snapshot
```python
import subprocess
import os

# Use creationflags to hide console window
result = subprocess.run(
    [sys.executable, "_camera_capture.py"],
    capture_output=True,
    creationflags=0x08000000,  # Windows: CREATE_NO_WINDOW
    timeout=5,
)
```

---

## Testing & Validation

### Input Validation
```python
def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page) -> str | None:
    """Validate and authenticate user."""
    # Trim whitespace
    ten_dang_nhap = ten_dang_nhap.strip()
    
    # Check non-empty
    if not ten_dang_nhap or not mat_khau:
        return None
    
    # Delegate to DAL
    user = _dal_authenticate(ten_dang_nhap, mat_khau)
    if user:
        return user.get("vai_tro")
    return None
```

### Output Validation
```python
def fetch_dashboard(server_url: str) -> dict[str, Any]:
    """Fetch and validate dashboard response."""
    url = f"{server_url.rstrip('/')}/api/dashboard"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    
    data = resp.json()
    
    # Ensure required keys exist
    if "metrics" not in data:
        data["metrics"] = []
    
    return data
```

---

## Comments & Documentation

### When to Comment
- **Complex algorithms**: >5 lines of non-obvious logic
- **Workarounds**: Explain why non-standard approach is needed
- **Public APIs**: Always include docstring
- **Gotchas**: Document platform-specific behavior

### When NOT to Comment
✗ Bad:
```python
# Increment counter
i += 1
```

✓ Skip obvious comments; let code speak:
```python
i += 1  # Clear from context
```

### Example: Necessary Comment
```python
def get_local_ip() -> str:
    """Detect LAN IP address.
    
    Uses UDP socket trick: connect to 8.8.8.8 (no data sent) to
    let OS select the correct network interface. Avoids DNS lookup.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # No actual connection established
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
```

---

## Performance & Optimization

### Avoid N+1 Queries
✗ Bad:
```python
users = tai_khoan_repo.get_all_users()
for user in users:
    # Don't re-fetch!
    cameras = camera_chuong_repo.get_by_user(user["id_user"])
```

✓ Good:
```python
users = tai_khoan_repo.get_all_users()
all_cameras = camera_chuong_repo.all()
cameras_by_user = {u["id_user"]: [c for c in all_cameras if c["id_user"] == u["id_user"]] for u in users}
```

### Cache Appropriately
```python
# load_cache() / save_cache() for offline fallback
cache = monitor_service.load_cache()
if cache:
    metrics = cache.get("metrics", [])
else:
    metrics = fetch_dashboard(server_url)
```

### UI Responsiveness
- Never block UI thread with:
  - File I/O (use thread pool if needed)
  - Network calls (use threading or async)
  - Video processing (background thread)
- Always wrap in try/except when using threads

---

## Common Pitfalls to Avoid

| Pitfall | Example | Fix |
|---------|---------|-----|
| **Global state** | `CURRENT_USER = None` | Use page.client_storage |
| **Mutable default args** | `def f(items=[])` | Use `items=None` + `items = items or []` |
| **Swallowing exceptions** | `except Exception: pass` | Log or return fallback value |
| **Password in logs** | `print(f"Login: {user} {password}")` | Log username only |
| **Direct SQL in services** | DAL queries in UI | Keep DAL boundary clean |
| **Circular imports** | `dal/repo.py` imports `ui/screen.py` | Use local imports if unavoidable |
| **Large files** | 500+ LOC in one module | Split by responsibility |
| **Control update racing** | `control.update()` in loop | Use `page.update()` once |
| **Hardcoded paths** | `/home/user/data/config.json` | Use `Path(__file__).parent / "config.json"` |
| **Platform assumptions** | `open(path, "r")` (default encoding) | Always specify `encoding="utf-8"` |

---

## Migration Path: JSON → PostgreSQL

To switch from JSON to PostgreSQL:

1. **Only modify** `dal/base_repo.py`
2. Replace `_load()` / `_save()` with SQLAlchemy queries
3. Keep signature: `BaseRepo(table_name, pk_field)`
4. All services/UI unchanged

Example:
```python
# Current JSON
def _load(table_name):
    return json.load(open(...))

# Replace with
from sqlalchemy import create_engine, text
def _load(table_name):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table_name}"))
        return {"records": [dict(row) for row in result]}
```

---

## Code Review Checklist

Before committing, verify:
- [ ] File size <200 LOC
- [ ] All functions have docstrings
- [ ] Type hints on all public functions
- [ ] No global state
- [ ] Imports in order (stdlib, third-party, local)
- [ ] Error handling with specific exception types
- [ ] Database calls only in DAL
- [ ] UTF-8 encoding specified for file I/O
- [ ] No hardcoded secrets or paths
- [ ] Windows-specific workarounds documented
- [ ] Linting passes (no syntax errors)
- [ ] No `except Exception: pass` (must log or return fallback)
