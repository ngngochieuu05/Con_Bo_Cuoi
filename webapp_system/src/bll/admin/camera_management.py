"""
BLL — Camera Management (Admin)
Nghiệp vụ quản lý camera: CRUD, đổi trạng thái.
"""
from __future__ import annotations

from dal.camera_chuong_repo import (
    get_all,
    get_by_user,
    get_by_camera_id,
    create_camera as _dal_create,
    update_camera as _dal_update,
    update_camera_status as _dal_update_status,
    delete_camera as _dal_delete,
)

_VALID_STATUSES = {"online", "offline", "warning"}


def list_cameras() -> list[dict]:
    return get_all()


def create_camera(
    id_chuong: str,
    khu_vuc: str,
    id_camera: str,
    id_user: int,
) -> tuple[bool, str]:
    id_chuong  = id_chuong.strip()
    id_camera  = id_camera.strip()
    khu_vuc    = khu_vuc.strip()
    if not id_chuong or not id_camera or not khu_vuc:
        return False, "Vui lòng điền đầy đủ thông tin camera."
    if get_by_camera_id(id_camera):
        return False, f"Camera ID '{id_camera}' đã tồn tại."
    _dal_create(id_chuong, khu_vuc, id_camera, id_user)
    return True, f"Đã thêm camera '{id_camera}'."


def update_camera(id_camera_chuong: int, updates: dict) -> tuple[bool, str]:
    result = _dal_update(id_camera_chuong, updates)
    if result is None:
        return False, f"Không tìm thấy camera ID={id_camera_chuong}."
    return True, "Đã cập nhật camera."


def set_camera_status(id_camera_chuong: int, trang_thai: str) -> tuple[bool, str]:
    if trang_thai not in _VALID_STATUSES:
        return False, f"Trạng thái không hợp lệ: {trang_thai}."
    result = _dal_update_status(id_camera_chuong, trang_thai)
    if result is None:
        return False, f"Không tìm thấy camera ID={id_camera_chuong}."
    return True, f"Trạng thái đã cập nhật → {trang_thai}."


def delete_camera(id_camera_chuong: int) -> tuple[bool, str]:
    ok = _dal_delete(id_camera_chuong)
    if not ok:
        return False, f"Không tìm thấy camera ID={id_camera_chuong}."
    return True, f"Đã xóa camera ID={id_camera_chuong}."
