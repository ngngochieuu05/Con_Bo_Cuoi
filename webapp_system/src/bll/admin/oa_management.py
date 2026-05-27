"""
BLL — OA Management (Admin)
Nghiệp vụ quản lý cảnh báo sự cố và trạng thái camera.
"""
from __future__ import annotations

from datetime import date, datetime

from dal.canh_bao_repo import (
    get_all as _get_all_alerts,
    get_by_status,
    resolve_alert as _dal_resolve,
)
from dal.camera_chuong_repo import get_all_cameras as _get_cameras


def get_all_alerts() -> list[dict]:
    """Lấy toàn bộ cảnh báo sự cố."""
    return _get_all_alerts()


def get_pending_alerts() -> list[dict]:
    """Lấy cảnh báo chưa xử lý."""
    return get_by_status("CHUA_XU_LY")


def get_today_alerts() -> list[dict]:
    """Lấy cảnh báo trong ngày hôm nay."""
    today = date.today().isoformat()
    return [a for a in _get_all_alerts() if str(a.get("created_at", "")).startswith(today)]


def get_stats() -> dict:
    """
    Trả về stats tổng hợp cho admin dashboard:
    {total, open, done, today_total, today_open, by_type, cameras_online, cameras_total}
    """
    all_alerts = _get_all_alerts()
    cameras    = _get_cameras()
    today      = date.today().isoformat()

    today_alerts = [a for a in all_alerts if str(a.get("created_at", "")).startswith(today)]

    by_type: dict[str, int] = {}
    for a in all_alerts:
        t = a.get("loai_canh_bao", "other")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total":          len(all_alerts),
        "open":           sum(1 for a in all_alerts if a.get("trang_thai") == "CHUA_XU_LY"),
        "done":           sum(1 for a in all_alerts if a.get("trang_thai") == "DA_XU_LY"),
        "today_total":    len(today_alerts),
        "today_open":     sum(1 for a in today_alerts if a.get("trang_thai") == "CHUA_XU_LY"),
        "by_type":        by_type,
        "cameras_online": sum(1 for c in cameras if c.get("trang_thai") == "online"),
        "cameras_total":  len(cameras),
    }


def resolve_alert(id_canh_bao: int) -> tuple[bool, str]:
    """
    Đánh dấu cảnh báo đã xử lý.
    Trả về (success, message).
    """
    result = _dal_resolve(id_canh_bao)
    if result is None:
        return False, f"Không tìm thấy cảnh báo ID={id_canh_bao}."
    return True, "Đã xử lý cảnh báo."


def get_all_cameras() -> list[dict]:
    """Lấy danh sách tất cả camera chuồng."""
    return _get_cameras()
