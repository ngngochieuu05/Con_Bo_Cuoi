import json
import os
import socket
import time
from typing import Any

import requests


def get_local_ip() -> str:
    """Tự động lấy IP LAN hiện tại (IPv4 của card mạng đang kết nối)."""
    try:
        # Kết nối UDP tới 8.8.8.8 (không gửi data) để OS chọn interface đúng
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

# Đường dẫn tuyệt đối để độc lập với CWD
_DAL_DB = os.path.join(os.path.dirname(__file__), "..", "..", "dal", "db")
CONFIG_PATH = os.path.normpath(os.path.join(_DAL_DB, "app_config.json"))
CACHE_PATH  = os.path.normpath(os.path.join(_DAL_DB, "monitor_cache.json"))


def _ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_config() -> dict[str, Any]:
    default = {
        "server_url": "http://127.0.0.1:8000",
        "camera_index": 0,
        "auto_connect": False,
        "notify_alert": True,
        "app_mode": "desktop",
        "app_port": 8080,
        "yolo_model_mode": "cpu",  # cpu | gpu | auto
    }
    if not os.path.exists(CONFIG_PATH):
        return default
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**default, **data}
    except Exception:
        return default


def save_config(config: dict[str, Any]):
    _ensure_parent(CONFIG_PATH)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_cache() -> dict[str, Any]:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(data: dict[str, Any]):
    _ensure_parent(CACHE_PATH)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    _model_cache.clear()


def get_farmer_cameras(id_user: int) -> list[dict]:
    """Lấy danh sách camera của farmer theo id_user."""
    from dal.camera_chuong_repo import get_by_user
    return get_by_user(id_user)


def get_enabled_models() -> list[dict]:
    """Lấy các model AI đang online (trang_thai='online')."""
    from dal.model_repo import get_models_by_status
    return get_models_by_status("online")


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

    online_models = get_enabled_models()
    if not online_models:
        result["error"] = "Không có model nào đang hoạt động (trang_thai='online')."
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

    alerts_created: list[str] = []
    seen_types: set[str]      = set()

    for det in detections:
        cls_lower = det.get("class", "").lower().strip()
        for keyword, alert_type in _ALERT_TRIGGER_MAP.items():
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

    online_models = get_enabled_models()
    if not online_models:
        result["error"] = "Không có model nào đang hoạt động."
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

        result["alerts_created"] = check_and_create_alert(
            all_detections, id_user, id_camera_chuong
        )

    except Exception as ex:
        result["error"] = f"{type(ex).__name__}: {ex}"

    return result
