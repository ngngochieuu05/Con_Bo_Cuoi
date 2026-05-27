import json
import os
import socket
import threading
import time
from typing import Any

import psycopg2
import requests


def get_local_ip() -> str:
    """Tự động lấy IP LAN hiện tại (IPv4 của card mạng đang kết nối)."""
    try:
        # Kết nối UDP tới 8.8.8.8 mà không gửi data để OS chọn đúng interface mạng.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


# Đường dẫn tuyệt đối để độc lập với CWD
_DAL_DB = os.path.join(os.path.dirname(__file__), "..", "..", "dal", "db")
CONFIG_PATH = os.path.normpath(os.path.join(_DAL_DB, "app_config.json"))
_RUNTIME_SCHEMA_LOCK = threading.RLock()

# Caching for configuration and active models to prevent database lookup on every frame
_cached_config: dict[str, Any] | None = None
_config_lock = threading.Lock()

_cached_monitor_models: list[dict] | None = None
_cached_disease_models: list[dict] | None = None
_models_lock = threading.Lock()


def _load_db_config() -> dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        db = data.get("database", {})
    except Exception:
        db = {}
    return {
        "host": db.get("host", "localhost"),
        "port": int(db.get("port", 5432)),
        "dbname": db.get("dbname", "ConBoCuoi_DB"),
        "user": db.get("user", "postgres"),
        "password": db.get("password", ""),
    }


def _get_conn():
    conn = psycopg2.connect(**_load_db_config())
    conn.autocommit = False
    return conn


def _default_config() -> dict[str, Any]:
    return {
        "server_url": "http://127.0.0.1:8000",
        "camera_index": 0,
        "camera_capture_index": 0,
        "monitor_camera_index": 0,
        "auto_connect": False,
        "notify_alert": True,
        "app_mode": "desktop",
        "app_port": 8080,
        "yolo_model_mode": "cpu",
        "gemini_api_key": "",
        "telegram": {
            "bot_token": "",
            "chat_id": "",
            "bot_name": "Cattle_Farm_Bot",
        },
        "thresholds": {
            "lying_duration_minutes": 30,
            "fight_iou_threshold": 0.1,
            "fight_velocity_threshold": 40.0,
            "fight_contact_seconds": 5.0,
            "alert_cooldown_seconds": 60,
            "feeding_hours": [[6, 8], [16, 18]],
        },
    }


def _load_legacy_file_config() -> dict[str, Any]:
    default = _default_config()
    if not os.path.exists(CONFIG_PATH):
        return default
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**default, **data}
    except Exception:
        return default


def _ensure_runtime_tables() -> None:
    with _RUNTIME_SCHEMA_LOCK:
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_config (
                        id INTEGER PRIMARY KEY,
                        server_url TEXT NOT NULL DEFAULT 'http://127.0.0.1:8000',
                        camera_index INTEGER NOT NULL DEFAULT 0,
                        camera_capture_index INTEGER NOT NULL DEFAULT 0,
                        monitor_camera_index INTEGER NOT NULL DEFAULT 0,
                        auto_connect BOOLEAN NOT NULL DEFAULT FALSE,
                        notify_alert BOOLEAN NOT NULL DEFAULT TRUE,
                        app_mode VARCHAR(20) NOT NULL DEFAULT 'desktop',
                        app_port INTEGER NOT NULL DEFAULT 8080,
                        yolo_model_mode VARCHAR(20) NOT NULL DEFAULT 'cpu',
                        gemini_api_key TEXT NOT NULL DEFAULT '',
                        telegram_bot_token TEXT NOT NULL DEFAULT '',
                        telegram_chat_id TEXT NOT NULL DEFAULT '',
                        telegram_bot_name TEXT NOT NULL DEFAULT 'Cattle_Farm_Bot',
                        thresholds_json JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_runtime_cache (
                        cache_key TEXT PRIMARY KEY,
                        payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                for ddl in [
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS camera_capture_index INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS monitor_camera_index INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS gemini_api_key TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS telegram_bot_token TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS telegram_chat_id TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS telegram_bot_name TEXT NOT NULL DEFAULT 'Cattle_Farm_Bot'",
                    "ALTER TABLE app_config ADD COLUMN IF NOT EXISTS thresholds_json JSONB NOT NULL DEFAULT '{}'::jsonb",
                ]:
                    cur.execute(ddl)
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
        finally:
            conn.close()


def _row_to_config(row: tuple | None) -> dict[str, Any]:
    default = _default_config()
    if not row:
        return default
    (
        server_url,
        camera_index,
        camera_capture_index,
        monitor_camera_index,
        auto_connect,
        notify_alert,
        app_mode,
        app_port,
        yolo_model_mode,
        gemini_api_key,
        telegram_bot_token,
        telegram_chat_id,
        telegram_bot_name,
        thresholds_json,
    ) = row
    return {
        **default,
        "server_url": server_url or default["server_url"],
        "camera_index": int(camera_index or 0),
        "camera_capture_index": int(camera_capture_index or camera_index or 0),
        "monitor_camera_index": int(monitor_camera_index or camera_index or 0),
        "auto_connect": bool(auto_connect),
        "notify_alert": bool(notify_alert),
        "app_mode": app_mode or default["app_mode"],
        "app_port": int(app_port or default["app_port"]),
        "yolo_model_mode": yolo_model_mode or default["yolo_model_mode"],
        "gemini_api_key": gemini_api_key or "",
        "telegram": {
            "bot_token": telegram_bot_token or "",
            "chat_id": telegram_chat_id or "",
            "bot_name": telegram_bot_name or "Cattle_Farm_Bot",
        },
        "thresholds": thresholds_json or default["thresholds"],
    }


def _write_config_row(conn, config: dict[str, Any]) -> None:
    telegram = config.get("telegram") or {}
    thresholds = config.get("thresholds") or {}
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE app_config
            SET
                server_url = %s,
                camera_index = %s,
                camera_capture_index = %s,
                monitor_camera_index = %s,
                auto_connect = %s,
                notify_alert = %s,
                app_mode = %s,
                app_port = %s,
                yolo_model_mode = %s,
                gemini_api_key = %s,
                telegram_bot_token = %s,
                telegram_chat_id = %s,
                telegram_bot_name = %s,
                thresholds_json = %s::jsonb
            WHERE id = 1
            """,
            (
                config.get("server_url"),
                int(config.get("camera_index", 0) or 0),
                int(config.get("camera_capture_index", config.get("camera_index", 0)) or 0),
                int(config.get("monitor_camera_index", config.get("camera_index", 0)) or 0),
                bool(config.get("auto_connect", False)),
                bool(config.get("notify_alert", True)),
                config.get("app_mode", "desktop"),
                int(config.get("app_port", 8080) or 8080),
                config.get("yolo_model_mode", "cpu"),
                config.get("gemini_api_key", ""),
                telegram.get("bot_token", ""),
                telegram.get("chat_id", ""),
                telegram.get("bot_name", "Cattle_Farm_Bot"),
                json.dumps(thresholds, ensure_ascii=False),
            ),
        )
        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO app_config (
                    id, server_url, camera_index, camera_capture_index, monitor_camera_index,
                    auto_connect, notify_alert, app_mode, app_port, yolo_model_mode,
                    gemini_api_key, telegram_bot_token, telegram_chat_id, telegram_bot_name,
                    thresholds_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    1,
                    config.get("server_url"),
                    int(config.get("camera_index", 0) or 0),
                    int(config.get("camera_capture_index", config.get("camera_index", 0)) or 0),
                    int(config.get("monitor_camera_index", config.get("camera_index", 0)) or 0),
                    bool(config.get("auto_connect", False)),
                    bool(config.get("notify_alert", True)),
                    config.get("app_mode", "desktop"),
                    int(config.get("app_port", 8080) or 8080),
                    config.get("yolo_model_mode", "cpu"),
                    config.get("gemini_api_key", ""),
                    telegram.get("bot_token", ""),
                    telegram.get("chat_id", ""),
                    telegram.get("bot_name", "Cattle_Farm_Bot"),
                    json.dumps(thresholds, ensure_ascii=False),
                ),
            )


def _ensure_config_seed() -> None:
    _ensure_runtime_tables()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT server_url, camera_index, camera_capture_index, monitor_camera_index,
                       auto_connect, notify_alert, app_mode, app_port, yolo_model_mode,
                       gemini_api_key, telegram_bot_token, telegram_chat_id, telegram_bot_name,
                       thresholds_json
                FROM app_config
                WHERE id = 1
                """
            )
            row = cur.fetchone()
        legacy = _load_legacy_file_config()
        if row:
            current = _row_to_config(row)
            merged = {**legacy, **current}
            merged["telegram"] = {
                **(legacy.get("telegram") or {}),
                **(current.get("telegram") or {}),
            }
            merged["thresholds"] = {
                **(legacy.get("thresholds") or {}),
                **(current.get("thresholds") or {}),
            }
            for field in ("gemini_api_key",):
                if not current.get(field) and legacy.get(field):
                    merged[field] = legacy[field]
            if not (current.get("telegram") or {}).get("bot_token") and (legacy.get("telegram") or {}).get("bot_token"):
                merged["telegram"]["bot_token"] = legacy["telegram"]["bot_token"]
            if not (current.get("telegram") or {}).get("chat_id") and (legacy.get("telegram") or {}).get("chat_id"):
                merged["telegram"]["chat_id"] = legacy["telegram"]["chat_id"]
            if not (current.get("telegram") or {}).get("bot_name") and (legacy.get("telegram") or {}).get("bot_name"):
                merged["telegram"]["bot_name"] = legacy["telegram"]["bot_name"]
            _write_config_row(conn, merged)
            conn.commit()
            return
        _write_config_row(conn, legacy)
        conn.commit()
    finally:
        conn.close()


def load_config(force_reload: bool = False) -> dict[str, Any]:
    global _cached_config
    if _cached_config is not None and not force_reload:
        return _cached_config

    with _config_lock:
        if _cached_config is not None and not force_reload:
            return _cached_config

        _ensure_config_seed()
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT server_url, camera_index, camera_capture_index, monitor_camera_index,
                           auto_connect, notify_alert, app_mode, app_port, yolo_model_mode,
                           gemini_api_key, telegram_bot_token, telegram_chat_id, telegram_bot_name,
                           thresholds_json
                    FROM app_config
                    WHERE id = 1
                    """
                )
                row = cur.fetchone()
            conn.rollback()
            _cached_config = _row_to_config(row)
        except Exception:
            _cached_config = _load_legacy_file_config()
        finally:
            conn.close()
    return _cached_config


def save_config(config: dict[str, Any]):
    global _cached_config
    _ensure_config_seed()
    merged = {**load_config(force_reload=True), **config}
    conn = _get_conn()
    try:
        _write_config_row(conn, merged)
        conn.commit()
        with _config_lock:
            _cached_config = merged
    finally:
        conn.close()


def load_cache() -> dict[str, Any]:
    _ensure_runtime_tables()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload_json FROM app_runtime_cache WHERE cache_key = %s",
                ("monitor",),
            )
            row = cur.fetchone()
        conn.rollback()
        if row and row[0]:
            return row[0]
        legacy = {}
        cache_path = os.path.normpath(os.path.join(_DAL_DB, "monitor_cache.json"))
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    legacy = json.load(f)
            except Exception:
                legacy = {}
        if legacy:
            save_cache(legacy)
        return legacy
    except Exception:
        return {}
    finally:
        conn.close()


def save_cache(data: dict[str, Any]):
    _ensure_runtime_tables()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_runtime_cache (cache_key, payload_json, updated_at)
                VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                ON CONFLICT (cache_key) DO UPDATE SET
                    payload_json = EXCLUDED.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                ("monitor", json.dumps(data, ensure_ascii=False)),
            )
        conn.commit()
    finally:
        conn.close()


def fetch_dashboard(server_url: str, timeout: int = 5) -> dict[str, Any]:
    url = f"{server_url.rstrip('/')}/api/dashboard"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if "timestamp" not in data:
        data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return data


def stream_url(server_url: str) -> str:
    return f"{server_url.rstrip('/')}/api/stream"


def fetch_snapshot_base64(server_url: str, timeout: int = 5) -> str:
    import base64

    url = f"{server_url.rstrip('/')}/api/snapshot"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return base64.b64encode(resp.content).decode()


# ─── AI Inference helpers ────────────────────────────────────────────────────

# Behavior class substrings → alert type mapping
_ALERT_TRIGGER_MAP: dict[str, str] = {
    "húc":      "cow_fight",
    "fight":    "cow_fight",
    "fighting": "cow_fight",
    "nằm":      "cow_lie",
    "lying":    "cow_lie",
    "lie":      "cow_lie",
    "bệnh":     "cow_sick",
    "sick":     "cow_sick",
    "disease":  "cow_sick",
    "injury":   "cow_sick",
}

# RGB colors for annotation bounding boxes
_BOX_COLORS: list[tuple[int, int, int]] = [
    (239, 68,  68),
    (249, 115, 22),
    (234, 179,  8),
    (34,  197, 94),
    (20,  184, 166),
    (59,  130, 246),
    (139, 92,  246),
    (236, 72,  153),
]

# ── Loaded model cache (avoid reloading on every frame) ──────────────────────
_model_cache: dict[str, object] = {}   # resolved_path → YOLO instance


def _load_yolo(model_path: str):
    """Load YOLO from path, caching after first load."""
    if model_path not in _model_cache:
        from ultralytics import YOLO
        _model_cache[model_path] = YOLO(model_path)
    return _model_cache[model_path]


def clear_model_cache():
    """Call when admin changes model path/status so stale instances are evicted."""
    global _cached_monitor_models, _cached_disease_models
    _model_cache.clear()
    with _models_lock:
        _cached_monitor_models = None
        _cached_disease_models = None


def get_farmer_cameras(id_user: int) -> list[dict]:
    """Lấy danh sách camera của farmer theo id_user."""
    from dal.camera_chuong_repo import get_by_user
    return get_by_user(id_user)


def get_enabled_models() -> list[dict]:
    """Lấy các model AI đang online (trang_thai='online')."""
    from dal.model_repo import get_models_by_status
    return get_models_by_status("online")


def get_monitor_models() -> list[dict]:
    """Lấy model dùng cho trang Giám Sát: behavior (online)."""
    global _cached_monitor_models
    if _cached_monitor_models is not None:
        return _cached_monitor_models
    with _models_lock:
        if _cached_monitor_models is None:
            _cached_monitor_models = [
                m for m in get_enabled_models()
                if m.get("loai_mo_hinh") == "behavior"
            ]
    return _cached_monitor_models


def get_disease_models() -> list[dict]:
    """Lấy model dùng cho trang Tư Vấn: disease (online)."""
    global _cached_disease_models
    if _cached_disease_models is not None:
        return _cached_disease_models
    with _models_lock:
        if _cached_disease_models is None:
            _cached_disease_models = [
                m for m in get_enabled_models()
                if m.get("loai_mo_hinh") == "disease"
            ]
    return _cached_disease_models


def _resolve_model_path(raw_path: str) -> str:
    """Resolve model path: absolute → as-is, relative → relative to project root."""
    if not raw_path:
        return ""
    if os.path.isabs(raw_path):
        return raw_path
    # Project root = 4 levels up from this file
    # (webapp_system/src/bll/services/ → webapp_system/src/bll/ → … → project root)
    project_root = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )
    return os.path.normpath(os.path.join(project_root, raw_path))


def run_inference(image_path: str, id_user: int, id_camera_chuong: int) -> dict:
    """Chạy YOLO inference trên ảnh.

    Trả về dict:
      models_run       – list[str]: tên model đã chạy
      detections       – list[dict]: [{class, confidence, bbox, model}]
      alerts_created   – list[str]: loại cảnh báo đã tạo
      annotated_base64 – str | None: ảnh kết quả dạng base64 JPEG
      error            – str | None
    """
    result: dict = {
        "models_run":       [],
        "detections":       [],
        "alerts_created":   [],
        "annotated_base64": None,
        "error":            None,
    }

    online_models = get_disease_models()
    if not online_models:
        result["error"] = "Không có model bệnh nào đang hoạt động (loại: disease, trạng thái: online)."
        return result

    if not os.path.isfile(image_path):
        result["error"] = f"Không tìm thấy file ảnh: {image_path}"
        return result

    try:
        from PIL import Image as _PIL, ImageDraw as _Draw
        import io as _io
        import base64 as _b64

        pil_img = _PIL.open(image_path).convert("RGB")
        draw    = _Draw.Draw(pil_img)
        all_detections: list[dict] = []

        for model_info in online_models:
            model_path = _resolve_model_path(model_info.get("duong_dan_file", ""))
            if not model_path or not os.path.isfile(model_path):
                continue  # skip model whose .pt file is not found

            try:
                conf_thresh = float(model_info.get("conf", 0.25))
                iou_thresh  = float(model_info.get("iou",  0.45))
                yolo        = _load_yolo(model_path)
                results     = yolo.predict(
                    source=image_path,
                    conf=conf_thresh,
                    iou=iou_thresh,
                    imgsz=640,
                    verbose=False,
                    save=False,
                )
                r     = results[0]
                names = r.names or {}
                model_name = model_info.get("ten_mo_hinh", model_info.get("loai_mo_hinh", "AI"))
                result["models_run"].append(model_name)

                if r.boxes is not None:
                    for box in r.boxes:
                        cls_id   = int(box.cls[0])
                        conf_val = float(box.conf[0])
                        cls_name = names.get(cls_id, f"cls{cls_id}")
                        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                        color = _BOX_COLORS[cls_id % len(_BOX_COLORS)]

                        # Draw 3-px bounding box
                        for th in range(3):
                            draw.rectangle(
                                [x1 - th, y1 - th, x2 + th, y2 + th],
                                outline=color,
                            )
                        # Label background + text
                        label = f"{cls_name} {conf_val:.0%}"
                        tw = len(label) * 7 + 8
                        draw.rectangle([x1, y1 - 22, x1 + tw, y1], fill=(*color, 210))
                        draw.text((x1 + 4, y1 - 19), label, fill=(255, 255, 255))

                        all_detections.append({
                            "class":      cls_name,
                            "confidence": round(conf_val, 3),
                            "bbox":       [x1, y1, x2, y2],
                            "model":      model_info.get("loai_mo_hinh", ""),
                        })
            except Exception:
                pass  # don't fail the whole inference on one model error

        result["detections"] = all_detections

        # Encode annotated image as base64 JPEG
        buf = _io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        result["annotated_base64"] = _b64.b64encode(buf.getvalue()).decode()

        # Lưu frame mới nhất cho alert (video hoặc camera đều đúng)
        try:
            from bll.services.alert_service import set_last_frame_b64
            set_last_frame_b64(result["annotated_base64"])
        except Exception:
            pass

        # Create alerts for detected anomaly behaviors
        result["alerts_created"] = check_and_create_alert(
            all_detections, id_user, id_camera_chuong
        )

    except Exception as ex:
        result["error"] = f"{type(ex).__name__}: {ex}"

    return result


def check_and_create_alert(
    detections: list[dict], id_user: int, id_camera_chuong: int
) -> list[str]:
    """Kiểm tra detection results và tạo cảnh báo nếu cần.

    Trả về list các loại cảnh báo đã tạo (không trùng lặp).
    """
    from dal.canh_bao_repo import create_alert
    from bll.services.alert_service import process_behavior_alerts

    alerts_created: list[str] = process_behavior_alerts(detections, id_user, id_camera_chuong)
    seen_types: set[str] = set(alerts_created)

    for det in detections:
        cls_lower = det.get("class", "").lower().strip()
        for keyword, alert_type in _ALERT_TRIGGER_MAP.items():
            if alert_type in {"cow_fight", "cow_lie"}:
                continue
            if keyword in cls_lower and alert_type not in seen_types:
                try:
                    create_alert(alert_type, id_user, id_camera_chuong)
                    alerts_created.append(alert_type)
                    seen_types.add(alert_type)
                except Exception:
                    pass
                break

    return alerts_created


def run_inference_frame(frame_bgr, id_user: int, id_camera_chuong: int) -> dict:
    """Chạy YOLO inference trực tiếp trên numpy BGR frame (realtime camera).

    Giống run_inference nhưng nhận numpy array thay vì đường dẫn file.
    Model được cache sau lần load đầu nên không tốn chi phí load lại mỗi frame.
    """
    result: dict = {
        "models_run":       [],
        "detections":       [],
        "alerts_created":   [],
        "annotated_base64": None,
        "error":            None,
    }

    def _encode_frame_base64(frame) -> str | None:
        try:
            import cv2 as _cv2
            import base64 as _b64
            ok, buf = _cv2.imencode(".jpg", frame, [_cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                return None
            return _b64.b64encode(buf.tobytes()).decode()
        except Exception:
            return None

    online_models = get_monitor_models()
    if not online_models:
        result["error"] = "Không có model giám sát nào đang hoạt động (loại: behavior, trạng thái: online)."
        result["annotated_base64"] = _encode_frame_base64(frame_bgr)
        return result

    try:
        import cv2 as _cv2
        from PIL import Image as _PIL, ImageDraw as _Draw
        import io as _io
        import base64 as _b64

        img_rgb = _cv2.cvtColor(frame_bgr, _cv2.COLOR_BGR2RGB)
        pil_img = _PIL.fromarray(img_rgb)
        draw    = _Draw.Draw(pil_img)
        all_detections: list[dict] = []

        for model_info in online_models:
            model_path = _resolve_model_path(model_info.get("duong_dan_file", ""))
            if not model_path or not os.path.isfile(model_path):
                continue

            try:
                conf_thresh = float(model_info.get("conf", 0.25))
                iou_thresh  = float(model_info.get("iou",  0.45))
                yolo        = _load_yolo(model_path)
                results     = yolo.predict(
                    source=frame_bgr,
                    conf=conf_thresh,
                    iou=iou_thresh,
                    imgsz=640,
                    verbose=False,
                    save=False,
                )
                r     = results[0]
                names = r.names or {}
                model_name = model_info.get("ten_mo_hinh", model_info.get("loai_mo_hinh", "AI"))
                result["models_run"].append(model_name)

                if r.boxes is not None:
                    for box in r.boxes:
                        cls_id   = int(box.cls[0])
                        conf_val = float(box.conf[0])
                        cls_name = names.get(cls_id, f"cls{cls_id}")
                        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                        color = _BOX_COLORS[cls_id % len(_BOX_COLORS)]

                        for th in range(3):
                            draw.rectangle(
                                [x1 - th, y1 - th, x2 + th, y2 + th],
                                outline=color,
                            )
                        label = f"{cls_name} {conf_val:.0%}"
                        tw = len(label) * 7 + 8
                        draw.rectangle([x1, y1 - 22, x1 + tw, y1], fill=(*color, 210))
                        draw.text((x1 + 4, y1 - 19), label, fill=(255, 255, 255))

                        all_detections.append({
                            "class":      cls_name,
                            "confidence": round(conf_val, 3),
                            "bbox":       [x1, y1, x2, y2],
                            "model":      model_info.get("loai_mo_hinh", ""),
                        })
            except Exception:
                pass

        result["detections"] = all_detections

        buf = _io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=75)
        result["annotated_base64"] = _b64.b64encode(buf.getvalue()).decode()

        # Lưu frame mới nhất cho alert
        try:
            from bll.services.alert_service import set_last_frame_b64
            set_last_frame_b64(result["annotated_base64"])
        except Exception:
            pass

        result["alerts_created"] = check_and_create_alert(
            all_detections, id_user, id_camera_chuong
        )

    except Exception as ex:
        result["error"] = f"{type(ex).__name__}: {ex}"
        result["annotated_base64"] = _encode_frame_base64(frame_bgr)

    return result


def count_open_alerts() -> int:
    """Đếm số lượng cảnh báo chưa xử lý."""
    from dal.canh_bao_repo import count_open
    return count_open()


def get_all_models_info() -> list[dict]:
    """Lấy danh sách tất cả các mô hình AI."""
    from dal.model_repo import get_all_models
    return get_all_models()


def create_monitor_session(id_user: int, camera_label: str, source_type: str, source_label: str, status: str) -> dict:
    """Tạo một phiên giám sát camera mới."""
    from dal.monitor_session_repo import create_session
    return create_session(id_user=id_user, camera_label=camera_label, source_type=source_type, source_label=source_label, status=status)


def finish_monitor_session(id_session: int, status: str, frame_count: int) -> dict | None:
    """Kết thúc phiên giám sát camera."""
    from dal.monitor_session_repo import finish_session
    return finish_session(id_session, status=status, frame_count=frame_count)


def get_monitor_sessions_by_user(id_user: int) -> list[dict]:
    """Lấy danh sách các phiên giám sát của một người dùng."""
    from dal.monitor_session_repo import get_by_user
    return get_by_user(id_user)
