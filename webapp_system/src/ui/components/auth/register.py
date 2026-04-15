import flet as ft
from ui.theme import build_auth_shell, button_style, auth_text_field, auth_dropdown
from bll.services.auth_service import register as bll_register


def RegisterScreen(page: ft.Page = None, on_register_success=None, on_back_to_login=None):
    """Tạo màn hình đăng ký."""
    fullname = auth_text_field("Họ tên", ft.Icons.BADGE)
    username = auth_text_field("Tài khoản", ft.Icons.PERSON)
    password = auth_text_field("Mật khẩu", ft.Icons.LOCK, password=True, can_reveal=True)
    confirm  = auth_text_field("Xác nhận mật khẩu", ft.Icons.LOCK_OUTLINE, password=True, can_reveal=True)
    role_dropdown = auth_dropdown(
        "Vai trò mặc định sau khi đăng ký",
        [("expert", "Chuyên gia"), ("farmer", "Nông dân")],
        "farmer",
    )
    message = ft.Text("", color=ft.Colors.RED_200, size=12)
    btn = ft.ElevatedButton(
        "Đăng ký",
        icon=ft.Icons.PERSON_ADD,
        style=button_style("secondary"),
        height=48,
    )

    def handle_register(e):
        uname = (username.value or "").strip()
        pwd   = password.value or ""
        cpwd  = confirm.value or ""
        hoten = (fullname.value or "").strip()

        if not uname or not pwd:
            message.value = "Vui lòng nhập tài khoản và mật khẩu."
            message.update()
            return
        if pwd != cpwd:
            message.value = "Mật khẩu xác nhận không khớp."
            message.update()
            return

        btn.disabled = True
        btn.update()
        role = role_dropdown.value or "farmer"
        ok, msg_text = bll_register(uname, pwd, hoten, role)
        if not ok:
            message.value = msg_text
            message.update()
            btn.disabled = False
            btn.update()
            return
        if page:
            page.client_storage.set("user_role", role)
            page.client_storage.set("ho_ten", hoten)
        if on_register_success:
            on_register_success(role)

    btn.on_click = handle_register

    return build_auth_shell(
        title="Tạo tài khoản",
        description="Đăng ký nhanh để truy cập hệ thống theo vai trò của bạn.",
        form_controls=[
            fullname,
            username,
            password,
            confirm,
            role_dropdown,
            message,
            ft.Container(height=4),
            btn,
            ft.TextButton(
                "← Quay lại đăng nhập",
                style=ft.ButtonStyle(color=ft.Colors.WHITE70),
                on_click=lambda e: on_back_to_login() if on_back_to_login else None,
            ),
        ],
    )
