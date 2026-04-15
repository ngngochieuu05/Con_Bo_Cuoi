"""
BLL — User Management (Admin)
Nghiệp vụ quản lý tài khoản người dùng: CRUD, đổi mật khẩu.
Chỉ Admin mới có quyền.
"""
from __future__ import annotations

from dal.tai_khoan_repo import (
    get_all_users as _dal_all,
    get_user_by_id,
    get_user_by_username,
    create_user as _dal_create,
    update_user as _dal_update,
    delete_user as _dal_delete,
    change_password as _dal_change_pwd,
)

_ALLOWED_ROLES = {"admin", "expert", "farmer"}


def list_users() -> list[dict]:
    """Lấy tất cả tài khoản."""
    return _dal_all()


def create_user(ten_dang_nhap: str, mat_khau: str,
                vai_tro: str, ho_ten: str = "") -> tuple[bool, str]:
    """
    Tạo tài khoản mới.
    Trả về (success, message).
    """
    uname = ten_dang_nhap.strip()
    if not uname:
        return False, "Tên đăng nhập không được để trống."
    if vai_tro not in _ALLOWED_ROLES:
        return False, f"Vai trò không hợp lệ: {vai_tro}."
    if len(mat_khau) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."
    if get_user_by_username(uname):
        return False, f"Tên đăng nhập '{uname}' đã tồn tại."
    _dal_create(uname, mat_khau, vai_tro, ho_ten.strip())
    return True, f"Đã tạo tài khoản '{uname}'."


def update_user(id_user: int, updates: dict) -> tuple[bool, str]:
    """Cập nhật thông tin tài khoản (ngoại trừ mật khẩu)."""
    if not updates:
        return False, "Không có thông tin cập nhật."
    result = _dal_update(id_user, updates)
    if result is None:
        return False, f"Không tìm thấy tài khoản ID={id_user}."
    return True, "Đã cập nhật tài khoản."


def delete_user(id_user: int) -> tuple[bool, str]:
    """Xoá tài khoản."""
    ok = _dal_delete(id_user)
    if not ok:
        return False, f"Không tìm thấy tài khoản ID={id_user}."
    return True, f"Đã xoá tài khoản ID={id_user}."


def reset_password(id_user: int, mat_khau_moi: str) -> tuple[bool, str]:
    """Admin đặt lại mật khẩu (không cần mật khẩu cũ)."""
    if len(mat_khau_moi) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."
    ok = _dal_change_pwd(id_user, mat_khau_moi)
    if not ok:
        return False, f"Không tìm thấy tài khoản ID={id_user}."
    return True, "Đã đặt lại mật khẩu."
