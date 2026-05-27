import flet as ft

from bll.services.local_chat_store import (
    load_local_profile_snapshot,
    save_local_profile_snapshot,
)
from dal.profile_repo import update_profile_fields
from dal.tai_khoan_repo import (
    authenticate as _dal_authenticate,
    change_password as _dal_change_pwd,
    create_user as _dal_create,
    get_user_by_id as _dal_get_by_id,
    get_user_by_username as _dal_get_by_uname,
    update_user as _dal_update,
)


def _merge_local_profile(user: dict | None) -> dict | None:
    if not user:
        return None
    local = load_local_profile_snapshot(int(user.get("id_user") or 0))
    if not local:
        return user
    merged = dict(user)
    merged.update(local)
    return merged


def login(ten_dang_nhap: str, mat_khau: str, page: ft.Page):
    """Xác thực tài khoản qua DAL. Trả về vai trò nếu thành công."""
    user = _merge_local_profile(_dal_authenticate(ten_dang_nhap.strip(), mat_khau))
    if user:
        role = user.get("vai_tro", "farmer")
        page.data["user_role"] = role
        page.data["user_id"] = str(user.get("id_user", ""))
        page.data["ho_ten"] = user.get("ho_ten", "")
        page.data["anh_dai_dien"] = user.get("anh_dai_dien", "") or ""
        try:
            page.client_storage.set("user_role", role)
            page.client_storage.set("user_id", str(user.get("id_user", "")))
            page.client_storage.set("ho_ten", user.get("ho_ten", ""))
            page.client_storage.set("anh_dai_dien", user.get("anh_dai_dien", "") or "")
        except Exception:
            pass
        try:
            from bll.services.activity_service import log_action

            log_action(user.get("id_user"), "LOGIN", f"{ten_dang_nhap.strip()} ({role})")
        except Exception:
            pass
        return role
    return None


def authenticate(ten_dang_nhap: str, mat_khau: str, page=None) -> dict | None:
    """Xác thực và trả về bản ghi người dùng, không lưu session."""
    return _merge_local_profile(_dal_authenticate(ten_dang_nhap.strip(), mat_khau))


def perform_logout(page: ft.Page, on_logout_success):
    """Xóa session hiện tại và quay về màn đăng nhập."""
    for key in ("user_role", "user_id", "ho_ten"):
        try:
            page.data.pop(key, None)
        except Exception:
            pass
    for key in ("user_role", "user_id", "ho_ten", "anh_dai_dien"):
        try:
            page.client_storage.remove(key)
        except Exception:
            pass

    if on_logout_success:
        on_logout_success()


def check_logged_in_role(page: ft.Page):
    """Kiểm tra vai trò hiện có trong session."""
    if "user_role" in (page.data or {}):
        return page.data.get("user_role")
    return None


def register(ten_dang_nhap: str, mat_khau: str, ho_ten: str, vai_tro: str = "farmer") -> tuple[bool, str, str, int]:
    """
    Đăng ký tài khoản mới.
    Trả về: (thành công, thông báo, deep_link_telegram, id_user)
    """
    uname = ten_dang_nhap.strip()
    if not uname:
        return False, "Tên đăng nhập không được để trống.", "", 0
    if len(mat_khau) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự.", "", 0
    if _dal_get_by_uname(uname):
        return False, f"Tên đăng nhập '{uname}' đã tồn tại.", "", 0

    created = _dal_create(uname, mat_khau, vai_tro, ho_ten.strip())

    deep_link = ""
    if vai_tro == "farmer":
        try:
            from bll.services.telegram_link import get_deep_link

            deep_link = get_deep_link(uname)
        except Exception:
            pass

    return True, "Đăng ký thành công.", deep_link, int(created.get("id_user") or 0)


def get_user_by_id(id_user: int) -> dict | None:
    """Lấy thông tin người dùng theo mã tài khoản."""
    return _merge_local_profile(_dal_get_by_id(id_user))


def get_user_by_username(username: str) -> dict | None:
    """Lấy thông tin người dùng theo tên đăng nhập."""
    return _merge_local_profile(_dal_get_by_uname(username))


def update_profile(id_user: int, updates: dict) -> tuple[bool, str]:
    """Cập nhật hồ sơ người dùng và hồ sơ theo vai trò."""
    user = _merge_local_profile(_dal_get_by_id(id_user))
    if not user:
        return False, "Không tìm thấy tài khoản."

    save_local_profile_snapshot(id_user, updates)

    account_updates = {k: v for k, v in updates.items() if k == "ho_ten"}
    profile_updates = {k: v for k, v in updates.items() if k != "ho_ten"}

    result = user
    if account_updates:
        result = _dal_update(id_user, account_updates)
    if result is None:
        return False, "Không tìm thấy tài khoản."
    result = update_profile_fields(result, profile_updates)
    if result is None:
        return False, "Không tìm thấy tài khoản."
    save_local_profile_snapshot(id_user, result)
    return True, "Đã cập nhật thông tin."


def change_password_safe(id_user: int, mat_khau_cu: str, mat_khau_moi: str) -> tuple[bool, str]:
    """Đổi mật khẩu có xác thực mật khẩu cũ."""
    user = _dal_get_by_id(id_user)
    if not user:
        return False, "Tài khoản không tồn tại."
    if len(mat_khau_moi) < 6:
        return False, "Mật khẩu mới phải có ít nhất 6 ký tự."
    checked = authenticate(user["ten_dang_nhap"], mat_khau_cu, None)
    if checked is None:
        return False, "Mật khẩu cũ không đúng."
    _dal_change_pwd(id_user, mat_khau_moi)
    return True, "Đã đổi mật khẩu thành công."
