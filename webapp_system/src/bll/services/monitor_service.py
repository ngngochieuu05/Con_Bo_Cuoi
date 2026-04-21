import json
import os
import socket
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values


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
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _ensure_parent(path: str):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _load_env_config() -> dict[str, Any]:
    env_file_values = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}

    def read(name: str) -> Any:
        runtime_value = os.getenv(name)
        return runtime_value if runtime_value is not None else env_file_values.get(name)

    config: dict[str, Any] = {}

    server_url = read("SERVER_URL")
    if server_url:
        config["server_url"] = str(server_url).strip()

    app_mode = read("APP_MODE")
    if app_mode:
        config["app_mode"] = str(app_mode).strip().lower()

    yolo_mode = read("YOLO_DEVICE_MODE")
    if yolo_mode:
        config["yolo_model_mode"] = str(yolo_mode).strip().lower()

    camera_index = _parse_int(read("CAMERA_INDEX"))
    if camera_index is not None:
        config["camera_index"] = camera_index

    app_port = _parse_int(read("APP_PORT"))
    if app_port is not None:
        config["app_port"] = app_port

    auto_connect = _parse_bool(read("AUTO_CONNECT"))
    if auto_connect is not None:
        config["auto_connect"] = auto_connect

    notify_alert = _parse_bool(read("NOTIFY_ALERT"))
    if notify_alert is not None:
        config["notify_alert"] = notify_alert

    return config


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
    env_config = _load_env_config()
    if not os.path.exists(CONFIG_PATH):
        return {**default, **env_config}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**default, **data, **env_config}
    except Exception:
        return {**default, **env_config}


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

