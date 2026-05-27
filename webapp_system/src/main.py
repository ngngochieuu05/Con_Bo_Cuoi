import os
import socket
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
from bll.services.telegram_bot import start_bot
import dal


def _can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def _is_port_available(port: int) -> bool:
    # Flet web mode nội bộ vẫn bind loopback socket riêng, nên phải kiểm tra cả
    # 127.0.0.1 lẫn địa chỉ any-host để tránh báo "cổng trống" giả.
    return _can_bind("127.0.0.1", port) and _can_bind("0.0.0.0", port)


def _find_available_port(preferred_port: int, max_tries: int = 20) -> int:
    if _is_port_available(preferred_port):
        return preferred_port
    for port in range(preferred_port + 1, preferred_port + max_tries + 1):
        if _is_port_available(port):
            return port
    raise RuntimeError(
        f"Không tìm thấy cổng trống trong dải {preferred_port}-{preferred_port + max_tries}."
    )


def main(page: ft.Page):
    page.title = "Hệ thống giám sát bò AI"
    page.padding = 0
    page.window.min_width = 360
    page.window.min_height = 640
    page.window.width = 393
    page.window.height = 852
    page.window.resizable = True
    # Font hỗ trợ tiếng Việt đầy đủ
    page.fonts = {
        "AppFont": "https://fonts.gstatic.com/s/notosans/v36/o-0mIpQlx3QUlC5A4PNB6Ryti20_6n1iPHjcz6L1SoM-jCpoiyeuvA.woff2",
    }
    page.theme = ft.Theme(
        font_family="Segoe UI",
        color_scheme_seed=ft.Colors.BLUE,
    )
    page.dark_theme = ft.Theme(
        font_family="Segoe UI",
        color_scheme_seed=ft.Colors.BLUE,
    )
    page.theme_mode = ft.ThemeMode.DARK
    # Đánh dấu phông mobile cho build_role_shell dùng
    page.data = {
        "is_mobile": True,
        "upload_dir": str(Path(__file__).parent.parent.parent / "uploads"),
        "app_mode": load_config().get("app_mode", "desktop"),
    }

    def logout_to_login():
        perform_logout(page, show_login)

    def show_dashboard(role: str):
        normalized_role = (role or "farmer").lower()
        if normalized_role not in {"admin", "expert", "farmer"}:
            normalized_role = "farmer"

        stored_user_id = ""
        stored_name = ""
        stored_avatar = ""
        try:
            stored_user_id = page.client_storage.get("user_id") or ""
            stored_name = page.client_storage.get("ho_ten") or ""
            stored_avatar = page.client_storage.get("anh_dai_dien") or ""
        except Exception:
            pass

        if isinstance(page.data, dict):
            page.data["user_role"] = normalized_role
            page.data["user_id"] = str(stored_user_id or page.data.get("user_id", ""))
            page.data["ho_ten"] = stored_name or page.data.get("ho_ten", "")
            page.data["anh_dai_dien"] = stored_avatar or page.data.get("anh_dai_dien", "")
        else:
            page.data = {
                "is_mobile": True,
                "user_role": normalized_role,
                "user_id": str(stored_user_id or ""),
                "ho_ten": stored_name,
                "anh_dai_dien": stored_avatar,
                "upload_dir": str(Path(__file__).parent.parent.parent / "uploads"),
                "app_mode": load_config().get("app_mode", "desktop"),
            }

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
    _preferred_port = int(_cfg.get("app_port", 8080))
    _port = _preferred_port
    _flet_secret = str(
        _cfg.get("flet_secret_key")
        or os.environ.get("FLET_SECRET_KEY")
        or "con-bo-cuoi-local-upload-key-2026"
    )

    if _mode == "web":
        _port = _find_available_port(_preferred_port)
        os.environ["FLET_FORCE_WEB_SERVER"] = "true"
        os.environ["FLET_SECRET_KEY"] = _flet_secret
        _ip = get_local_ip()
        _url = f"http://{_ip}:{_port}"

        # -- In thông tin kết nối --
        print("\n" + "=" * 52)
        print(f"  🌐 WEB MODE đang chạy")
        if _port != _preferred_port:
            print(f"  ⚠ Cổng {_preferred_port} đang bận, chuyển sang {_port}")
        print(f"  💻 Máy tính : http://localhost:{_port}")
        print(f"  📱 Phone/LAN: {_url}")
        print("  🔐 Upload key: đã bật")
        print("=" * 52)

        # -- Tạo QR code trong terminal (ASCII) --
        try:
            import qrcode
            import qrcode.constants

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(_url)
            qr.make(fit=True)
            print("\n  📷 Quét QR bằng điện thoại (cùng WiFi):\n")
            qr.print_ascii(invert=True)

            # -- Lưu ảnh QR ra file để tiện dùng --
            _qr_img_path = Path(__file__).parent.parent.parent / "qr_access.png"
            img = qr.make_image(fill_color="black", back_color="white")
            with open(_qr_img_path, "wb") as _f:
                img.save(_f)
            print(f"\n  💾 QR đã lưu: {_qr_img_path}")
        except Exception as _qr_err:
            print(f"  ⚠  Không tạo được QR: {_qr_err}")

        print("=" * 52 + "\n")
    else:
        os.environ.pop("FLET_FORCE_WEB_SERVER", None)

    _upload_dir = Path(__file__).parent.parent.parent / "uploads"
    _upload_dir.mkdir(exist_ok=True)

    # Khởi động Telegram Bot long polling (daemon thread)
    try:
        start_bot()
    except Exception as _bot_err:
        print(f"[main] Telegram bot không khởi động được: {_bot_err}")

    ft.app(
        target=main,
        assets_dir=str(Path(__file__).parent.parent / "data"),
        upload_dir=str(_upload_dir),
        view=ft.AppView.WEB_BROWSER if _mode == "web" else ft.AppView.FLET_APP,
        host="0.0.0.0" if _mode == "web" else None,
        port=_port if _mode == "web" else 0,
    )
