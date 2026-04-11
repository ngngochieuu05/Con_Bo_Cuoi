import flet as ft
from dal.tai_khoan_repo import authenticate as _dal_authenticate


def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page):
    """Xác thực tài khoản qua DAL. Trả về vai_tro nếu thành công, None nếu thất bại."""
    user = _dal_authenticate(ten_dang_nhap.strip(), mat_khau)
    if user:
        role = user.get("vai_tro", "farmer")
        page.client_storage.set("user_role", role)
        page.client_storage.set("user_id", str(user.get("id_user", "")))
        page.client_storage.set("ho_ten", user.get("ho_ten", ""))
        return role
    return None


def perform_logout(page: ft.Page, on_logout_success):
    """Xóa token và đăng xuất."""
    for key in ("user_role", "user_id", "ho_ten"):
        try:
            page.client_storage.remove(key)
        except Exception:
            pass

    if on_logout_success:
        on_logout_success()


def check_logged_in_role(page: ft.Page):
    """Kiểm tra xem người dùng đã đăng nhập chưa."""
    if page.client_storage.contains_key("user_role"):
        return page.client_storage.get("user_role")
    return None

