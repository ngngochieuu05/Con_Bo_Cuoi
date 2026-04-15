import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Tat Windows Error Reporting de tranh hop thoai loi C++ tu subprocess kill app
try:
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x8007)
except Exception:
    pass

import flet as ft
from ui.components.admin.main_admin import AdminMainScreen
from ui.components.auth.login import LoginScreen
from ui.components.auth.register import RegisterScreen
from ui.components.auth.forgot_password import ForgotPasswordScreen
from ui.components.user.expert.main_expert import ExpertMainScreen
from ui.components.user.framer.main_farmer import FarmerMainScreen
from bll.services.auth_service import perform_logout
from bll.services.monitor_service import load_config, get_local_ip
import dal


def main(page: ft.Page):
    page.title = "Hệ thống giám sát bò AI"
    page.padding = 0
    page.window.min_width = 360
    page.window.min_height = 640
    page.window.width = 393
    page.window.height = 852
    page.window.resizable = True
    # Đánh dấu phông mobile cho build_role_shell dùng
    page.data = {"is_mobile": True}

    def logout_to_login():
        perform_logout(page, show_login)

    def show_dashboard(role: str):
        normalized_role = (role or "farmer").lower()
        if normalized_role not in {"admin", "expert", "farmer"}:
            normalized_role = "farmer"

        page.data["user_role"] = normalized_role

        if normalized_role == "admin":
            control = AdminMainScreen(page, on_logout=logout_to_login)
        elif normalized_role == "expert":
            control = ExpertMainScreen(page, on_logout=logout_to_login)
        else:  # farmer
            control = FarmerMainScreen(page, on_logout=logout_to_login)

        page.clean()
        page.add(control)
        page.update()

    def show_forgot_password():
        page.clean()
        page.add(ForgotPasswordScreen(on_back_to_login=show_login))
        page.update()

    def show_login():
        page.clean()
        page.add(LoginScreen(
            page=page,
            on_login_success=show_dashboard,
            on_switch_to_register=show_register,
            on_forgot_password=show_forgot_password,
        ))
        page.update()

    def show_register():
        page.clean()
        page.add(RegisterScreen(page=page, on_register_success=show_dashboard, on_back_to_login=show_login))
        page.update()

    # Khởi tạo DAL (tạo file JSON nếu chưa có)
    dal.init_all()

    # Xóa session cũ (nếu có) và luôn bắt đầu từ login
    for _k in ("user_role", "user_id", "ho_ten"):
        page.data.pop(_k, None)
    show_login()


if __name__ == "__main__":
    _cfg = load_config()
    _mode = _cfg.get("app_mode", "desktop")
    _port = int(_cfg.get("app_port", 8080))

    if _mode == "web":
        _ip = get_local_ip()
        print("\n" + "=" * 50)
        print(f"  🌐 WEB MODE đang chạy")
        print(f"  💻 Máy tính : http://localhost:{_port}")
        print(f"  📱 Phone/LAN: http://{_ip}:{_port}")
        print("  ✔  Phone cùng WiFi nhập URL trên vào trình duyệt")
        print("=" * 50 + "\n")

    ft.app(
        target=main,
        assets_dir=str(Path(__file__).parent.parent / "data"),
        view=ft.AppView.WEB_BROWSER if _mode == "web" else ft.AppView.FLET_APP,
        host="0.0.0.0" if _mode == "web" else None,
        port=_port if _mode == "web" else 0,
    )
