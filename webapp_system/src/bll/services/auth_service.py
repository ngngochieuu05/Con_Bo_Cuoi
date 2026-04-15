import flet as ft
from dal.tai_khoan_repo import authenticate as _dal_authenticate


def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page):
    """Xác thực tài khoản qua DAL. Trả về vai_tro nếu thành công, None nếu thất bại."""
    user = _dal_authenticate(ten_dang_nhap.strip(), mat_khau)
    if user:
        role = user.get("vai_tro", "farmer")
        page.data["user_role"] = role
        page.data["user_id"] = str(user.get("id_user", ""))
        page.data["ho_ten"] = user.get("ho_ten", "")
        return role
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

