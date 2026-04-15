"""
BLL — OA Management (Admin)
Nghiệp vụ quản lý cảnh báo sự cố và trạng thái camera.
"""
from __future__ import annotations

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
