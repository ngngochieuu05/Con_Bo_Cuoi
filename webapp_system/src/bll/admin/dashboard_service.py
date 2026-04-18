"""
BLL — Dashboard Service (Admin)
Tổng hợp số liệu dashboard: user, model, cảnh báo, camera, activity.
"""
from __future__ import annotations

from datetime import date

from dal.tai_khoan_repo import count_users
from dal.model_repo import count_online, get_all_models
from dal.canh_bao_repo import count_open, get_all as _get_alerts
from dal.camera_chuong_repo import get_all_cameras


def _today() -> str:
    return date.today().isoformat()


def get_dashboard_stats() -> dict:
    """
    Trả về dict số liệu tổng hợp cho dashboard:
        users           : int — tổng tài khoản
        models_online   : int — model đang chạy
        models_total    : int — tổng model
        alerts_open     : int — cảnh báo chưa xử lý
        alerts_today    : int — cảnh báo trong ngày
        cameras         : int — tổng camera
        cameras_online  : int — camera đang online
        cameras_offline : int — camera offline
    """
    alerts  = _get_alerts()
    cameras = get_all_cameras()
    today   = _today()
    return {
        "users":           count_users(),
        "models_online":   count_online(),
        "models_total":    len(get_all_models()),
        "alerts_open":     count_open(),
        "alerts_today":    sum(1 for a in alerts if a.get("created_at", "").startswith(today)),
        "cameras":         len(cameras),
        "cameras_online":  sum(1 for c in cameras if c.get("trang_thai") == "online"),
        "cameras_offline": sum(1 for c in cameras if c.get("trang_thai") == "offline"),
    }


def get_recent_alerts() -> list[dict]:
    """Lấy tất cả cảnh báo (UI tự sort/slice)."""
    return _get_alerts()


def get_all_cameras_info() -> list[dict]:
    """Lấy danh sách camera cho dashboard."""
    return get_all_cameras()


def get_recent_activity(limit: int = 10) -> list[dict]:
    """Lấy activity log gần nhất (đã kèm label/kind)."""
    from bll.services.activity_service import get_recent_activities
    return get_recent_activities(limit)
