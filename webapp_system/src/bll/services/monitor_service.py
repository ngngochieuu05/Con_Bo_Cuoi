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

