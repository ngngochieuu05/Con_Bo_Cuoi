# Con Bò Cưới — Project Overview & PDR

## Product Vision

"Con Bò Cưới" (Cattle Wedding) is an AI-powered cattle farm monitoring system designed for real-time herd health assessment, behavior detection, and disease alerting. It serves three distinct user roles—farm administrators, animal health experts, and farmers—with tailored interfaces for each.

**Target Users:**
- **Admins**: Farm system managers (user/model/camera provisioning)
- **Experts**: Veterinarians/consultants (health analysis, case review)
- **Farmers**: Herd caretakers (live monitoring, health alerts, session history)

**Core Value Proposition:**
- Automated cattle behavior classification via YOLO-based computer vision
- Real-time health anomaly detection (disease, aggression, heat stress)
- Role-based dashboard analytics with actionable alert workflows
- Offline-capable desktop app + optional web deployment

---

## Technical Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.14 |
| **UI Framework** | Flet 0.28.3 (cross-platform desktop/web) |
| **Computer Vision** | OpenCV, YOLO v8 |
| **Storage** | JSON (development), PostgreSQL-ready (BaseRepo abstraction) |
| **Networking** | Requests, socket (LAN IP detection) |
| **Auth** | PBKDF2-HMAC-SHA256 password hashing, session via page.data (+ legacy client_storage mirror) |

**Entry Point:** `python webapp_system/src/main.py`

**Default Test Users:**
- admin / admin123 (role: admin)
- expert01 / expert123 (role: expert)
- farmer01 / farmer123 (role: farmer)

---

## Functional Requirements

### FR1: Multi-Role Authentication
- Login/register with email-like username (ten_dang_nhap)
- PBKDF2-HMAC-SHA256 password hashing, no plaintext storage
- Session persistence via browser storage (non-persistent; clears on restart)
- Logout with immediate session purge
- Forgot password UI (backend email integration not yet implemented)

### FR2: Admin Dashboard
- User management: CRUD operations, role assignment
- YOLO model management: upload configs, set confidence/IOU thresholds
- Camera provisioning: bind cameras to stalls (chuong), assign users
- Operational analytics: alert resolution tracking, dataset review metrics
- Application settings: desktop/web mode toggle, custom port, restart trigger

### FR3: Expert Workflows
- **Dashboard**: KPI cards (total cattle, active alerts, pending cases)
- **Raw Data Review**: image audit & annotation interface (HITL pipeline)
- **Consulting Review**: incoming case requests from farmers
- **Utilities**: search, export, batch operations
- **Settings**: notification preferences, model assignment per account

### FR4: Farmer Operations
- **Live Monitoring**: real-time camera feed + snapshot polling
- **Health Consulting**: chat interface + streamed camera input
- **Session History**: previous interactions, case outcomes
- **Dashboard**: cached KPI cards (fallback when offline)
- **Utilities**: quick search, export session logs

### FR5: Alert System
- **Alert Types**: cow_fight, cow_lie, cow_sick, heat_high
- **Alert States**: CHUA_XU_LY (pending) → DA_XU_LY (resolved) → QUA_HAN (overdue)
- **Linkage**: alerts tied to cameras, users, and timestamps
- **Notifications**: configurable toast/notification rules

### FR6: YOLO Model Management
- **System-Level**: disease detection (admin-managed)
- **User-Level**: cattle_detect, behavior classification (per-account config)
- **Configuration**: confidence (0.05–0.95), IOU (0.05–0.95), model file path (.pt)
- **Status Tracking**: active/inactive/training states

### FR7: Human-in-the-Loop Dataset Pipeline
- Image collection & curation (PENDING_REVIEW → CLEANED_DATA states)
- Bounding box annotation interface (x_center, y_center, w, h in JSON format)
- Review audit log (lich_su_kiem_duyet) tracking who approved/rejected what

### FR8: Offline Capability
- JSON-based local cache for dashboard metrics
- App functions fully without internet (except video streaming)
- Config/session stored locally, syncs when online

---

## Non-Functional Requirements

### NFR1: Performance
- Dashboard load: <2 seconds (local data) / <5 seconds (remote)
- Snapshot capture: <1 second per frame
- Live stream: 30 FPS target at 640x480 resolution
- UI responsiveness: no blocking operations on main thread

### NFR2: Reliability
- App graceful degradation when backend unreachable
- Camera capture timeout: 5 seconds (prevents hang on disconnected USB)
- OpenCV exception handling (Windows: suppress C++ error dialogs)
- Session recovery on app restart

### NFR3: Security
- Passwords: PBKDF2-HMAC-SHA256 with per-password salt; legacy SHA-256 accepted only for transparent upgrade
- Session: client-side storage (consider encrypted cookies for web deployment)
- Data: no PII in logs, sanitize model file paths
- Role enforcement: UI-level only (backend API should validate on each request)

### NFR4: Scalability
- JSON storage: baseline; PostgreSQL migration path via BaseRepo
- User limits: <500 users recommended for JSON mode
- Camera streams: 1 primary + 3 secondary cameras per role
- Model inference: async/background threads (not blocking UI)

### NFR5: Usability
- Mobile-first responsive design (breakpoint ~900px: sidebar → bottom nav)
- Vietnamese language UI with English technical terminology
- Field validation: non-empty inputs, email format for username
- Error messages: user-friendly, not stack traces

### NFR6: Maintainability
- File size: max 200 LOC per file
- Naming: Vietnamese snake_case for DB fields, kebab-case for filenames
- Dependency injection: services/repos injected via constructor or page context
- No global state: all state is local or stored in page/session helpers

---

## Architectural Highlights

### 3-Layer Pattern

**UI Layer** (`ui/`):
- Role-based main screens (AdminMainScreen, ExpertMainScreen, FarmerMainScreen)
- Shared component library (auth, dashboard, tables, forms)
- Centralized theme system (glass_container, button_style, status_badge)
- Responsive shell: sidebar (desktop) / bottom nav (mobile)

**Business Logic Layer** (`bll/services/`):
- auth_service: login, logout, session check
- monitor_service: config management, remote API stubs, LAN IP detection

**Data Access Layer** (`dal/`):
- BaseRepo: generic CRUD on JSON (PostgreSQL migration ready)
- Specialized repos: tai_khoan (users), camera_chuong, canh_bao (alerts), model, dataset
- Auto-seeding on first run with test accounts & default configurations

### Design System (theme.py)

Centralized, single-source-of-truth for:
- **Color Tokens**: PRIMARY #4CAF50, SECONDARY #56CCF2, WARNING #F2C94C, DANGER #FF7A7A
- **Component Factories**: glass_container(), status_badge(), metric_card(), data_table()
- **Button Styles**: Airbnb-inspired (primary → near-black, hover → Rausch red)
- **Responsive Helpers**: build_role_shell() detects mobile via page.data["is_mobile"]

### State Management

- **Session**: `page.data` is the source of truth (keys: user_role, user_id, ho_ten, anh_dai_dien) with legacy mirror to `page.client_storage`
- **UI State**: functional closures with mutable dicts (e.g., _state = {"key": value})
- **Control Refs**: ref.current.controls = [...] + ref.current.update() for list refreshes
- **No Redux/Context**: keep it simple; Flet doesn't require complex state libraries

---

## Data Model Overview

| Table | Primary Key | Key Fields | Notes |
|-------|-------------|-----------|-------|
| **tai_khoan** | id_user | ten_dang_nhap, mat_khau (PBKDF2 or legacy SHA256), vai_tro, ho_ten | User accounts |
| **camera_chuong** | id_camera_chuong | id_chuong, khu_vuc_chuong, id_camera, id_user, trang_thai | Camera-to-stall binding |
| **canh_bao_su_co** | id_canh_bao | loai_canh_bao, trang_thai (CHUA_XU_LY/DA_XU_LY/QUA_HAN), id_user | Alert events |
| **model** | id_model | ten_mo_hinh, loai_mo_hinh, conf, iou, duong_dan_file | YOLO configs |
| **hinh_anh_dataset** | id_hinh_anh | duong_dan, trang_thai (PENDING_REVIEW/CLEANED_DATA), id_user | Image curation |
| **hanh_vi** | id_hanh_vi | ten_hanh_vi, bounding_box (JSON), id_hinh_anh | Annotations |
| **lich_su_kiem_duyet** | id_lich_su | thoi_gian_duyet, id_user, id_hinh_anh | Audit log |

---

## Acceptance Criteria

### Phase 1: Core System (MVP)
- [ ] Authentication works for 3 user roles
- [ ] Admin can CRUD users and assign roles
- [ ] Farmer sees live camera feed (≥30 FPS)
- [ ] Alerts generate and route to correct user
- [ ] App runs offline with JSON cache

### Phase 2: Expert Features
- [ ] Expert dashboard shows KPIs and case table
- [ ] Raw data review UI with image annotation
- [ ] Consulting review workflow (request → response)
- [ ] Model config persistence (conf/IOU per user)

### Phase 3: Production Hardening
- [ ] PostgreSQL integration (BaseRepo abstraction)
- [ ] Session encryption (web deployment)
- [ ] Bcrypt password hashing
- [ ] Email-based password reset
- [ ] HTTPS enforcement (web mode)

### Phase 4: Advanced Analytics
- [ ] Herd health trend reports
- [ ] Disease prevalence dashboards
- [ ] Model performance metrics (precision/recall)
- [ ] Export to CSV/PDF workflows

---

## Open Questions & Constraints

1. **Email Backend**: Forgot password UI exists but email service not implemented. Recommend Amazon SES or SendGrid integration.
2. **Backend AI Server**: System is fully functional offline with JSON store. Optional Flask/FastAPI backend for advanced inference (e.g., GPU acceleration).
3. **Session Persistence**: current runtime keeps session in `page.data` and mirrors it to `page.client_storage` for compatibility. For production web, implement signed cookies or JWT tokens.
4. **Role-Based Access Control**: Alert resolution currently lacks UI-level role gates. Any authenticated user can resolve alerts. Add ACL checks in DAL layer.
5. **Windows Camera Support**: OpenCV on Windows requires `cv2.CAP_DSHOW` backend + BUFFERSIZE=1. Never call `cap.release()` (C++ crash risk).
6. **Concurrency**: Flet is single-threaded. Background camera polling uses threading; ensure all UI updates via page.update() (not control.update()).

---

## Next Steps

1. **Immediate**: Fix password hashing (add bcrypt library)
2. **Short-term**: Implement email-based password reset
3. **Mid-term**: Integrate PostgreSQL via SQLAlchemy (no UI changes needed)
4. **Long-term**: Build advanced analytics dashboard and mobile-first responsive refinement
