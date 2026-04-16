"""
BLL — Dashboard Service (Admin)
Tổng hợp số liệu dashboard: user, model, cảnh báo, camera.
"""
from __future__ import annotations

from dal.tai_khoan_repo import count_users
from dal.model_repo import count_online
from dal.canh_bao_repo import count_open, get_all as _get_alerts
from dal.camera_chuong_repo import get_all_cameras


def get_dashboard_stats() -> dict:
    """
    Trả về dict số liệu tổng hợp cho dashboard:
        users:        int
        models_online: int
        alerts_open:  int
        cameras:      int
    """
    return {
        "users":         count_users(),
        "models_online": count_online(),
        "alerts_open":   count_open(),
        "cameras":       len(get_all_cameras()),
    }


def get_recent_alerts() -> list[dict]:
    """Lấy tất cả cảnh báo (UI tự sort/slice)."""
    return _get_alerts()


def get_all_cameras_info() -> list[dict]:
    """Lấy danh sách camera cho dashboard."""
    return get_all_cameras()
