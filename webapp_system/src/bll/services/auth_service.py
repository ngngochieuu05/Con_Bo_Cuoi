import flet as ft
from dal.tai_khoan_repo import (
    authenticate as _dal_authenticate,
    get_user_by_id as _dal_get_by_id,
    get_user_by_username as _dal_get_by_uname,
    create_user as _dal_create,
    update_user as _dal_update,
    change_password as _dal_change_pwd,
)


def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page):
    """Xác thực tài khoản qua DAL. Trả về vai_tro nếu thành công, None nếu thất bại."""
    user = _dal_authenticate(ten_dang_nhap.strip(), mat_khau)
    if user:
        role = user.get("vai_tro", "farmer")
        page.data["user_role"] = role
        page.data["user_id"]   = str(user.get("id_user", ""))
        page.data["ho_ten"]    = user.get("ho_ten", "")
        # Ghi activity log
        try:
            from bll.services.activity_service import log_action
            log_action(user.get("id_user"), "LOGIN",
                       f"{ten_dang_nhap.strip()} ({role})")
        except Exception:
            pass
        return role


def authenticate(ten_dang_nhap: str, mat_khau: str, page=None) -> dict | None:
    """Xác thực và trả về user record (không lưu session). page có thể là None."""
    return _dal_authenticate(ten_dang_nhap.strip(), mat_khau)
    return None


def perform_logout(page: ft.Page, on_logout_success):
    """Xóa token và đăng xuất."""
    for key in ("user_role", "user_id", "ho_ten"):
        try:
            page.data.pop(key, None)
        except Exception:
            pass

    if on_logout_success:
        on_logout_success()


def check_logged_in_role(page: ft.Page):
    """Kiểm tra xem người dùng đã đăng nhập chưa."""
    if "user_role" in (page.data or {}):
        return page.data.get("user_role")
    return None


# ── User / Profile ────────────────────────────────────────────────────────────

def register(ten_dang_nhap: str, mat_khau: str, ho_ten: str,
             vai_tro: str = "farmer") -> tuple[bool, str]:
    """
    Đăng ký tài khoản mới.
    Trả về (success, message).
    """
    uname = ten_dang_nhap.strip()
    if not uname:
        return False, "Tên đăng nhập không được để trống."
    if len(mat_khau) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."
    if _dal_get_by_uname(uname):
        return False, f"Tên đăng nhập '{uname}' đã tồn tại."
    _dal_create(uname, mat_khau, vai_tro, ho_ten.strip())
    return True, "Đăng ký thành công."


def get_user_by_id(id_user: int) -> dict | None:
    """Lấy thông tin người dùng theo id."""
    return _dal_get_by_id(id_user)


def update_profile(id_user: int, updates: dict) -> tuple[bool, str]:
    """
    Cập nhật thông tin profile (ho_ten, anh_dai_dien, ...).
    Trả về (success, message).
    """
    result = _dal_update(id_user, updates)
    if result is None:
        return False, "Không tìm thấy tài khoản."
    return True, "Đã cập nhật thông tin."


def change_password_safe(id_user: int, mat_khau_cu: str,
                         mat_khau_moi: str) -> tuple[bool, str]:
    """
    Đổi mật khẩu có xác thực mật khẩu cũ.
    Trả về (success, message).
    """
    user = _dal_get_by_id(id_user)
    if not user:
        return False, "Tài khoản không tồn tại."
    if len(mat_khau_moi) < 6:
        return False, "Mật khẩu mới phải có ít nhất 6 ký tự."
    # Xác thực mật khẩu cũ
    checked = authenticate(user["ten_dang_nhap"], mat_khau_cu, None)
    if checked is None:
        return False, "Mật khẩu cũ không đúng."
    _dal_change_pwd(id_user, mat_khau_moi)
    return True, "Đã đổi mật khẩu thành công."

